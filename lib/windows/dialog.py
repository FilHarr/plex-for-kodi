# coding=utf-8
from __future__ import absolute_import

from kodi_six import xbmc
from kodi_six import xbmcgui

import plexnet
from lib import util
from lib.windows import kodigui


# An option's key marking it a group break (optionGroup()): a row with no card that focus passes over
GROUP = object()


def optionGroup(title=''):
    """A break between groups of options, as an option of its own: a row's space with no card, blank or with title
    in it as the heading of those under it - as the album screen's disc rows. Never chosen: focus passes over it,
    so not first or last, and never two together."""
    return (GROUP, title)


def groupedOptions(*groups):
    """options from groups of them, a blank optionGroup() between those with any in."""
    options = []
    for group in (g for g in groups if g):
        if options:
            options.append(optionGroup())
        options.extend(group)
    return options


class SelectDialog(kodigui.BaseDialog, util.CronReceiver):
    """
    The option picker (script-plex-settings_select_dialog.xml.tpl): the Settings dialog's and the video player's
    buttons'. Fixed 876 high - its heading, 13 rows of 61 (the template's 793, then it scrolls) and 20 under the
    last card - centred between the video player's clock and elapsed time (their boxes end at 100 and start at 982,
    so 103-979), its right edge 10 from the screen's: the Settings dialog's frame, so it opens exactly over it.
    """
    xmlFile = 'script-plex-settings_select_dialog.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    OPTIONS_LIST_ID = 100
    FRAME_GROUP_ID = 200
    FRAME_BACKDROP_ID = 201
    FRAME_SHADOW_ID = 202
    ROW_HEIGHT = util.vscalei(61)  # the template's row pitch (55 cards, 6 apart)
    FRAME_X = 1290  # the backdrop's right edge, 20 past the 600 list, at 1910
    FRAME_TOP = 103
    FRAME_HEIGHT = 876
    LIST_HEIGHT = 793

    def __init__(self, *args, **kwargs):
        kodigui.BaseDialog.__init__(self, *args, **kwargs)
        self.heading = kwargs.get('heading')
        self.options = kwargs.get('options')
        self.selectedIdx = kwargs.get('selected_idx')
        self.choice = None
        self.nonPlayback = kwargs.get('non_playback')
        self.lastSelectedItem = self.selectedIdx if self.selectedIdx is not None else 0
        self.roundRobin = kwargs.get('round_robin', True)
        self.trim = kwargs.get('trim', True)
        # Called with a choice before the dialog closes on it: returning (options, selected_idx) keeps it open with
        # those instead - for a choice that opens something of its own over it and comes back (Download subtitles).
        self.onChoice = kwargs.get('on_choice')
        # Opened over another picker (Subtitles' Download subtitles): that one's dim is already behind it, so this
        # draws none of its own (option_card_frame.xml.tpl) - set before it's shown, so not even for a frame.
        if kwargs.get('nested'):
            self.setProperty('nested', '1')
        # A screen's first pop-up, its rows actions (an item's menu, Choose action): the options in the More settings
        # rows' font (option_card_frame.xml.tpl), as the first pop-up on pre-play, Episodes and Seasons is
        if kwargs.get('menu'):
            self.setProperty('menu', '1')
        # A sidebar section's menu: next to the sidebar (option_card_frame.xml.tpl)
        if kwargs.get('beside_sidebar'):
            self.setProperty('beside_sidebar', '1')
        # The dim held over the gap to whatever a choice opens next (kodigui.holdDialogDim()); the caller releases it
        self.holdDim = kwargs.get('hold_dim', False)

    def onFirstInit(self):
        self.optionsList = kodigui.ManagedControlList(self, self.OPTIONS_LIST_ID, 8)
        self.setProperty('heading', self.heading)
        self.showOptions()
        util.CRON.registerReceiver(self)

    def onAction(self, action):
        try:
            if not xbmc.getCondVisibility('Player.HasMedia') and not self.nonPlayback:
                self.doClose()
                return
        except:
            util.ERROR()

        up = action in (xbmcgui.ACTION_MOVE_UP, xbmcgui.ACTION_PAGE_UP)
        if (up or action in (xbmcgui.ACTION_MOVE_DOWN, xbmcgui.ACTION_PAGE_DOWN)) and \
                self.getFocusId() == self.OPTIONS_LIST_ID:
            # Kodi has made the move by now: round from one end to the other, and on past a group row
            to_pos = None
            last_index = self.optionsList.size() - 1
            pos = self.optionsList.control.getSelectedPosition()
            first = self.firstOption()

            if last_index > 0:
                if self.roundRobin and action == xbmcgui.ACTION_MOVE_UP and self.lastSelectedItem == first \
                        and pos <= first:
                    to_pos = last_index

                elif self.roundRobin and action == xbmcgui.ACTION_MOVE_DOWN and self.lastSelectedItem == last_index \
                        and pos == last_index:
                    to_pos = first

                elif self.isGroup(pos):
                    to_pos = pos - 1 if up else pos + 1
                    if not 0 <= to_pos <= last_index or self.isGroup(to_pos):
                        to_pos = first if up else last_index

                if to_pos is not None:
                    self.optionsList.setSelectedItemByPos(to_pos)
                    self.lastSelectedItem = to_pos
                    return

                self.lastSelectedItem = pos

        kodigui.BaseDialog.onAction(self, action)

    def onClick(self, controlID):
        if controlID == self.OPTIONS_LIST_ID:
            self.setChoice()

    def onClosed(self):
        util.CRON.cancelReceiver(self)

    def tick(self):
        if self.nonPlayback:
            return

        if not xbmc.getCondVisibility('Player.HasMedia'):
            self.doClose()
            return

    def isGroup(self, pos):
        return 0 <= pos < len(self.options) and self.options[pos][0] is GROUP

    def firstOption(self):
        return next((i for i in range(len(self.options)) if not self.isGroup(i)), 0)

    def setChoice(self):
        mli = self.optionsList.getSelectedItem()
        if not mli:
            return

        choice = self.options[self.optionsList.getSelectedPosition()][0]
        if choice is GROUP:
            # a mouse's click; a remote never lands here
            return
        if self.onChoice:
            refreshed = self.onChoice(choice)
            if refreshed is not None:
                self.options, self.selectedIdx = refreshed
                self.showOptions()
                return

        self.choice = choice
        if self.holdDim:
            kodigui.holdDialogDim()
        self.doClose()

    def showOptions(self):
        self.optionsList.reset()
        self.optionsList.addItems(self.optionItems())
        self.fitFrame(len(self.options))
        self.selectOption()

    def selectOption(self):
        """Focus on the current option (selectedIdx), else the first that isn't a group row."""
        if self.selectedIdx is not None:
            self.optionsList.selectItem(self.selectedIdx)
        elif self.isGroup(0):
            self.optionsList.selectItem(self.firstOption())
        self.lastSelectedItem = self.selectedIdx if self.selectedIdx is not None else self.firstOption()

        self.setFocusId(self.OPTIONS_LIST_ID)

    def optionItems(self):
        items = []
        for option in self.options:
            ds, title1 = option[0], option[1]
            if ds is GROUP:
                # no card, its title (if any) as a heading (option_card_frame.xml.tpl)
                item = kodigui.ManagedListItem(title1 or '', data_source=None)
                item.setProperty('group', '1')
                items.append(item)
                continue
            title2 = ''
            if isinstance(title1, (list, set, tuple)):
                title1, title2 = title1
            item = kodigui.ManagedListItem(title1, self.trim and plexnet.util.trimString(title2, limit=40) or title2,
                                           data_source=ds)
            if len(option) > 2:
                # its own tick, for a list of switches rather than one choice (Playback Settings: on)
                ticked = option[2]
            else:
                # the current option, ticked (the template), when there's a choice of more than one
                ticked = len(self.options) > 1 and len(items) == self.selectedIdx
            item.setProperty('current', '1' if ticked else '')
            # a row's own properties (option_card_frame.xml.tpl): 'more', for one that opens more choices
            for key, value in (option[3] if len(option) > 3 else {}).items():
                item.setProperty(key, value)
            items.append(item)
        return items

    def fitFrame(self, rows):
        """The list as many rows high as there are, up to the template's 13 (then it scrolls), in the fixed frame."""
        header = util.vscalei(66)
        height = util.vscalei(self.FRAME_HEIGHT)
        self.optionsList.setHeight(min(rows * self.ROW_HEIGHT, util.vscalei(self.LIST_HEIGHT)))
        self.getControl(self.FRAME_BACKDROP_ID).setHeight(height)
        self.getControl(self.FRAME_SHADOW_ID).setHeight(height + util.vscalei(80))
        self.getControl(self.FRAME_GROUP_ID).setPosition(self.FRAME_X, util.vscalei(self.FRAME_TOP) + header)


class SidebarMenuDialog(SelectDialog):
    """A sidebar section's menu (LibraryWindow.sectionMenu()): the option picker beside the sidebar, without the
    zorder that keeps the others above the video player's OSD, so what its rows open over it opens on top
    (script-plex-sidebar_menu.xml.tpl)."""
    xmlFile = 'script-plex-sidebar_menu.xml'


class UserMenuDialog(SelectDialog):
    """
    The sidebar's user menu (script-plex-user_menu.xml.tpl): the picker's cards in a frame of their own, with no
    heading, as tall as its options - its panel's top at 42, where the in-screen dropdown it replaced started, and
    its left edge at 325, as the sidebar's other menus'.
    """
    xmlFile = 'script-plex-user_menu.xml'

    FRAME_X = 345  # the list's left, 20 inside the panel's
    FRAME_TOP = 42  # the panel's top
    PAD = 17  # panel above the first row and below the last (their cards 3 in: 20 to each)

    def fitFrame(self, rows):
        """The panel round the rows, up to the template's 13 (then it scrolls)."""
        listHeight = min(rows * self.ROW_HEIGHT, util.vscalei(self.LIST_HEIGHT))
        height = listHeight + util.vscalei(2 * self.PAD)
        self.optionsList.setHeight(listHeight)
        self.getControl(self.FRAME_BACKDROP_ID).setHeight(height)
        self.getControl(self.FRAME_SHADOW_ID).setHeight(height + util.vscalei(80))
        self.getControl(self.FRAME_GROUP_ID).setPosition(self.FRAME_X, util.vscalei(self.FRAME_TOP + self.PAD))


# Pickers open now (showOptionsDialog() blocks while one is): one opened while another is, is over it
_openPickers = [0]


def pickerOpen():
    """Whether a picker is open now: a dialog opened over it (a sidebar menu's Empty Trash confirm or Manage
    recommended rows) is nested, the picker's dim already behind it (option_card_frame.xml.tpl)."""
    return _openPickers[0] > 0


def showOptionsDialog(heading, options, non_playback=False, selected_idx=None, trim=True, on_choice=None,
                      dialog_props=None, menu=False, beside_sidebar=False, hold_dim=False, user_menu=False, cls=None,
                      **kwargs):
    """
    selected_idx: the current option, focused and ticked (an option with its own tick flag, a third element, is
    only focused). A fourth element, a dict, is the row's own properties: {'more': '1'} for one that opens more
    choices of its own (a chevron where the tick goes, the tick instead when it's ticked). on_choice: see SelectDialog. dialog_props: carried onto it and the window beneath
    (kodigui.applyCarriedProps()). menu: a screen's first pop-up, its options actions rather than a choice of
    values - in the More settings rows' bold font. beside_sidebar: a sidebar section's menu, next to the sidebar.
    hold_dim: a choice may open another dialog (a confirm, Manage recommended rows) - the dim held over the gap
    (kodigui.holdDialogDim()), released by the next dialog or by the caller (kodigui.releasesDialogDim()).
    user_menu: the sidebar's user menu's own frame (UserMenuDialog), under the user button, heading or not.
    cls: a SelectDialog subclass to open instead (the add-on's Settings: settings.SettingsPickerDialog), kwargs
    any more of its own.
    """
    nested = _openPickers[0] > 0
    _openPickers[0] += 1
    try:
        cls = cls or (UserMenuDialog if user_menu else SelectDialog)
        w = cls.open(heading=heading, options=options, non_playback=non_playback, selected_idx=selected_idx,
                              trim=trim, on_choice=on_choice, dialog_props=dialog_props, nested=nested, menu=menu,
                              beside_sidebar=beside_sidebar, hold_dim=hold_dim, **kwargs)
    finally:
        _openPickers[0] -= 1
    choice = w.choice
    ref = util.windowRef(w)
    del w
    util.collectIfAlive(ref)
    return choice
