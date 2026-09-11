# coding=utf-8

from kodi_six import xbmc, xbmcgui
from lib import util
from .. import optionsdialog
from lib.i18n import T


class CommonMixin(object):
    @classmethod
    def isWatchedAction(cls, action):
        return action == xbmcgui.ACTION_NONE and action.getButtonCode() == 61527

    def retractToButtonRow(self):
        """Back out of the extras/hub rows without leaving the screen, by focusing the screen's own
        main button row (MAIN_BUTTON_GROUP_ID, 300 on every window using this) - onFocus() clears
        on.extras from there, which retracts the reveal slide, so this is the same thing the user
        would get by navigating back up.

        Replaces the older jump to OPTIONS_GROUP_ID (the header, group 200): these screens all blank
        header_topleft in favour of the sidebar, so group 200 is left with no reliably focusable
        child and Kodi drops focus entirely - see the ACTION_CONTEXT_MENU comment in the callers'
        own onAction() for the full story.

        Returns True when focus actually landed on the row. False means it couldn't (Episodes hides
        its whole button row under disable_playback, and the group can raise outright when it isn't
        there) - callers must then fall through to their normal Back handling rather than leave the
        window with nothing focused.
        """
        group_id = self.MAIN_BUTTON_GROUP_ID
        try:
            self.setFocusId(group_id)
        except (SystemError, RuntimeError):
            return False
        return xbmc.getCondVisibility('ControlGroup({0}).HasFocus(0)'.format(group_id))

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
