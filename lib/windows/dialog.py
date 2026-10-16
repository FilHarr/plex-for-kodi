# coding=utf-8
from __future__ import absolute_import

from kodi_six import xbmc
from kodi_six import xbmcgui

import plexnet
from lib import util
from lib.windows import kodigui


class SelectDialog(kodigui.BaseDialog, util.CronReceiver):
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
    FRAME_X = 660  # centres the 600-wide list
    ROW_HEIGHT = util.vscalei(64)  # the template's row pitch (58 cards, 6 apart)
    MAX_ROWS = 10

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

        if self.roundRobin and action in (xbmcgui.ACTION_MOVE_UP, xbmcgui.ACTION_MOVE_DOWN) and \
                self.getFocusId() == self.OPTIONS_LIST_ID:
            to_pos = None
            last_index = self.optionsList.size() - 1

            if last_index > 0:
                if action == xbmcgui.ACTION_MOVE_UP and self.lastSelectedItem == 0 and self.optionsList.topHasFocus():
                    to_pos = last_index

                elif action == xbmcgui.ACTION_MOVE_DOWN and self.lastSelectedItem == last_index \
                        and self.optionsList.bottomHasFocus():
                    to_pos = 0

                if to_pos is not None:
                    self.optionsList.setSelectedItemByPos(to_pos)
                    self.lastSelectedItem = to_pos
                    return

                self.lastSelectedItem = self.optionsList.control.getSelectedPosition()

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

    def setChoice(self):
        mli = self.optionsList.getSelectedItem()
        if not mli:
            return

        choice = self.options[self.optionsList.getSelectedPosition()][0]
        if self.onChoice:
            refreshed = self.onChoice(choice)
            if refreshed is not None:
                self.options, self.selectedIdx = refreshed
                self.showOptions()
                return

        self.choice = choice
        self.doClose()

    def showOptions(self):
        items = []
        for ds, title1 in self.options:
            title2 = ''
            if isinstance(title1, (list, set, tuple)):
                title1, title2 = title1
            item = kodigui.ManagedListItem(title1, self.trim and plexnet.util.trimString(title2, limit=40) or title2,
                                           data_source=ds)
            # the current option, ticked (the template), when there's a choice of more than one
            item.setProperty('current', '1' if len(self.options) > 1 and len(items) == self.selectedIdx else '')
            items.append(item)

        self.optionsList.reset()
        self.optionsList.addItems(items)
        self.fitFrame(len(items))

        if self.selectedIdx is not None:
            self.optionsList.selectItem(self.selectedIdx)

        self.setFocusId(self.OPTIONS_LIST_ID)

    def fitFrame(self, rows):
        """
        The card frame (the template's group 200) fitted to the options: the list as many rows high as there are, up
        to 10 (then it scrolls); the backdrop the list plus its heading's 66 and 17 below
        (the last card's 3 and these: 20 under it, as at the sides); the shadow 40
        past that each way; all centred on the screen.
        """
        listHeight = min(rows, self.MAX_ROWS) * self.ROW_HEIGHT
        header = util.vscalei(66)
        self.optionsList.setHeight(listHeight)
        self.getControl(self.FRAME_BACKDROP_ID).setHeight(listHeight + header + util.vscalei(17))
        self.getControl(self.FRAME_SHADOW_ID).setHeight(listHeight + header + util.vscalei(97))
        top = max(0, (self.height - listHeight - header - util.vscalei(17)) // 2)
        self.getControl(self.FRAME_GROUP_ID).setPosition(self.FRAME_X, top + header)


class SideSelectDialog(SelectDialog):
    """
    The video player's Subtitles picker (script-plex-settings_select_dialog_side.xml.tpl): the option picker at a
    fixed 876 high - its heading, 13 rows of 61 (the template's 793, then it scrolls) and 20 under the last card -
    centred between the clock and the elapsed time (their boxes end at 100 and start at 982, so 103-979), its
    right edge 10 from the screen's.
    """
    xmlFile = 'script-plex-settings_select_dialog_side.xml'
    ROW_HEIGHT = util.vscalei(61)  # the template's row pitch (55 cards, 6 apart)
    FRAME_X = 1290  # the backdrop's right edge, 20 past the 600 list, at 1910
    FRAME_TOP = 103
    FRAME_HEIGHT = 876
    LIST_HEIGHT = 793

    def fitFrame(self, rows):
        header = util.vscalei(66)
        height = util.vscalei(self.FRAME_HEIGHT)
        self.optionsList.setHeight(min(rows * self.ROW_HEIGHT, util.vscalei(self.LIST_HEIGHT)))
        self.getControl(self.FRAME_BACKDROP_ID).setHeight(height)
        self.getControl(self.FRAME_SHADOW_ID).setHeight(height + util.vscalei(80))
        self.getControl(self.FRAME_GROUP_ID).setPosition(self.FRAME_X, util.vscalei(self.FRAME_TOP) + header)


def showOptionsDialog(heading, options, non_playback=False, selected_idx=None, trim=True, side=False, on_choice=None):
    """
    selected_idx: the current option, focused and ticked. side: the video player's tall right-hand picker
    (SideSelectDialog), not the centred one. on_choice: see SelectDialog.
    """
    w = (side and SideSelectDialog or SelectDialog).open(heading=heading, options=options, non_playback=non_playback,
                                                         selected_idx=selected_idx, trim=trim, on_choice=on_choice)
    choice = w.choice
    ref = util.windowRef(w)
    del w
    util.collectIfAlive(ref)
    return choice
