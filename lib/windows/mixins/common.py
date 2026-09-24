# coding=utf-8

from kodi_six import xbmc, xbmcgui
from lib import util
from .. import optionsdialog
from lib.i18n import T


class CommonMixin(object):
    @classmethod
    def isWatchedAction(cls, action):
        return action == xbmcgui.ACTION_NONE and action.getButtonCode() == 61527

    # Where Back retracts to from the extras rows; None means the button row (MAIN_BUTTON_GROUP_ID).
    # Episodes points it at its episode row instead, on request.
    BACK_RETRACT_ID = None

    def retractFromExtras(self):
        """Back out of the extras/hub rows without leaving the screen, by focusing BACK_RETRACT_ID
        (the screen's own button row, MAIN_BUTTON_GROUP_ID, unless it names another) - onFocus()
        clears on.extras from there, which retracts the reveal slide, so this is the same thing the
        user would get by navigating back up.

        Replaces the older jump to OPTIONS_GROUP_ID (the header, group 200): these screens all blank
        header_topleft in favour of the sidebar, so group 200 is left with no reliably focusable
        child and Kodi drops focus entirely - see the ACTION_CONTEXT_MENU comment in the callers'
        own onAction() for the full story.

        Returns True when focus was sent to the target. False means it couldn't be (a hidden target,
        e.g. Episodes' button row under disable_playback, or one that raises outright when it isn't
        there) - callers must then fall through to their normal Back handling rather than leave the
        window with nothing focused.

        Decided by the target's visibility, not by checking HasFocus afterwards: setFocusId() only
        queues the focus change for Kodi's GUI thread, so an immediate HasFocus check races it and,
        in practice, always loses (logged False on all 8 retracts in a live run, 2026-09-24). Show
        was where it showed: Back left the screen instead of retracting.

        Also clears on.extras and resets hub.focus to 0 straight away rather than leaving that to
        onFocus(). Pre-play and Artist never reset hub.focus there (their rows only ever step down
        to the button row through tier 0), so a jump from a deeper row like Related left the rows
        scrolled up and the focused buttons out of view.
        """
        target_id = self.BACK_RETRACT_ID or self.MAIN_BUTTON_GROUP_ID
        if not xbmc.getCondVisibility('Control.IsVisible({0})'.format(target_id)):
            return False
        try:
            self.setFocusId(target_id)
        except (SystemError, RuntimeError):
            return False
        self.setProperty('on.extras', '')
        self.setProperty('hub.focus', '0')
        return True

    def backResetRows(self):
        """{control id: ManagedControlList} of the rows Back returns to their first item before
        anything else. Each screen lists its own; the screen's main row (Show's seasons, Episodes'
        episodes) is left out, since its selection is what the screen is showing."""
        return {}

    def backToRowStartOrRetract(self):
        """The shared handleBack() of the screens with extras rows: a scrolled row goes back to its
        first item, then (unless fast_back is on) the extras rows retract (retractFromExtras()).
        Returns False when neither applies, so Back leaves the screen."""
        row = self.backResetRows().get(self.getFocusId())
        if row:
            pos = row.getSelectedPos()
            if pos is not None and pos > 0:
                row.selectItem(0)
                return True
        if not util.addonSettings.fastBack and self.getProperty('on.extras'):
            return self.retractFromExtras()
        return False

    def toggleWatched(self, item, state=None, **kw):
        """

        :param item:
        :param state: the state we want to set watched to
        :param kw:
        :return:
        """
        if state is None:
            state = not item.isFullyWatched

        if util.getSetting('home_confirm_actions') and item.TYPE in ('season', 'show'):
            if item.TYPE == 'season':
                title = u"{} - {}".format(item.parentTitle, item.title)
            else:
                title = item.title
            button = optionsdialog.show(
                T(32319, "Mark Played") if state else T(32318, "Mark Unplayed"),  title,
                T(32328, 'Yes'),
                T(32329, 'No'),
                dialog_props=getattr(self, "carriedProps", getattr(self, "dialogProps", None))
            )

            if button != 0:
                return

        util.DEBUG_LOG("Toggling watched for {} to: {}", item, state)

        if state:
            item.markWatched(**kw)
            return True
        else:
            item.markUnwatched(**kw)
            return False
