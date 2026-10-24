from __future__ import absolute_import

import re
from threading import Timer

from lib import util
from lib.util import T
from . import kodigui
from .mixins.text_metrics import FONT10_POINT_SIZE, measureTextWidth


def destructive(label):
    """An answer that can't be undone (Delete's, Empty Trash's Yes), in the muted red the menus' Delete rows use."""
    return u'[COLOR FFD45B55]{0}[/COLOR]'.format(label)


def confirmDelete(item, **kwargs):
    """Delete's confirm: Really delete? over the item as its menu names it (grid_labels.menuHeading(): "Show (S1 •
    E2)") - the one item action that names it, as it can't be undone. True for Yes."""
    from . import grid_labels
    return show(T(32326, 'Really delete?'), grid_labels.menuHeading(item), destructive(T(32328, 'Yes')),
                T(32329, 'No'), **kwargs) == 0


def messageLines(text, width=580):
    """How many lines `text` takes in the message box's font10, wrapped at word boundaries the way Kodi's
    textbox does - at 580, 10 short of the box's 590, so a guess either way errs towards a line more. Kodi's
    formatting tags ([B], [COLOR ...]) take no room. An empty line still counts."""
    lines = 0
    for para in re.sub(r'\[/?[A-Z]+[^\]]*\]', '', text or '').split('\n'):
        current = ''
        for word in para.split(' '):
            candidate = (current + ' ' + word).strip()
            if current and measureTextWidth(candidate, FONT10_POINT_SIZE) > width:
                lines += 1
                current = word
            else:
                current = candidate
        lines += 1
    return lines


class OptionsDialog(kodigui.BaseDialog):
    """
    The confirm and message box (script-plex-options_dialog.xml.tpl): a heading, a message and up to three answers
    in a row - in the settings and pickers' style, centred on the screen, as tall as its message needs.
    show() returns the index of the answer chosen, or None.
    """
    xmlFile = 'script-plex-options_dialog.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    BUTTON_IDS = (1001, 1002, 1003)
    FRAME_GROUP_ID = 200
    FRAME_BACKDROP_ID = 201
    FRAME_SHADOW_ID = 202
    # the answers' grouplist (100) sits in this plain group: Kodi's Python can't fetch a grouplist
    BUTTONS_GROUP_ID = 203
    MESSAGE_ID = 300

    DEFAULT_ID = 1001
    # The frame, in the template's skin pixels: 640 wide; the heading's 66; the message's lines of font10 (Inter at 23:
    # a 27.8 cell, which Kodi's textbox steps by) - up to 12, then it scrolls; 20; the answers' 55; 20.
    FRAME_WIDTH = 640
    HEADING = 66
    LINE_HEIGHT = 28
    # The message box reaches this far past its last line, into the gap above the answers: Kodi puts a line's baseline
    # at the font's tallest glyph (its bbox - GUIFontTTF.cpp, Load()), not its ascender - for Inter at 23, 25.5 down,
    # 3.2 lower than the 27.8 line spacing allows for - so a g or y on the last line reached 30.5 in a 28 box and lost
    # its tail. Less than a line: the box never shows part of another.
    DESCENDER_ROOM = 4
    MAX_LINES = 12
    GAP = 20
    BUTTONS = 55

    def fitFrame(self):
        """The message box as tall as the message's lines, the answers under it and the panel and shadow round both,
        centred on the screen. No message (an item action's confirm: its heading alone, "Mark Played?"), no message
        box: the answers straight under the heading, whose 66 leaves the gap a message would."""
        if (self.info or '').strip():
            lines = max(1, min(messageLines(self.info), self.MAX_LINES))
            message = lines * self.LINE_HEIGHT
            gap = self.GAP
        else:
            message = gap = 0
        height = self.HEADING + message + gap + self.BUTTONS + self.GAP
        try:
            self.getControl(self.MESSAGE_ID).setHeight(util.vscalei(message + self.DESCENDER_ROOM) if message else 0)
            self.getControl(self.BUTTONS_GROUP_ID).setPosition(20, util.vscalei(self.HEADING + message + gap))
            self.getControl(self.FRAME_BACKDROP_ID).setHeight(util.vscalei(height))
            self.getControl(self.FRAME_SHADOW_ID).setHeight(util.vscalei(height + 80))
            self.getControl(self.FRAME_GROUP_ID).setPosition((self.width - self.FRAME_WIDTH) // 2,
                                                             util.vscalei((self.height - height) // 2))
        except (RuntimeError, SystemError) as e:
            # the template's start, a one-line message, stays
            util.LOG('OptionsDialog: no frame controls to fit: {}', e)

    def __init__(self, *args, **kwargs):
        kodigui.BaseDialog.__init__(self, *args, **kwargs)
        self.header = kwargs.get('header')
        self.info = kwargs.get('info')
        self.button0 = kwargs.get('button0')
        self.button1 = kwargs.get('button1')
        self.button2 = kwargs.get('button2')
        self.actionCallback = kwargs.get('action_callback')
        self.buttonChoice = None
        self.select = kwargs.get('select', 0)
        self.delayButtons = kwargs.get('delay_buttons', False)
        self.closeTimeout = kwargs.get('close_timeout', None)
        self._close_timer = None

    def onFirstInit(self):
        self.setProperty('header', self.header)
        self.setProperty('info', self.info)
        self.setProperty('delay_buttons', bool(self.delayButtons) and '1' or '')

        if self.button2:
            self.setProperty('button.2', self.button2)

        if self.button1:
            self.setProperty('button.1', self.button1)

        if self.button0:
            self.setProperty('button.0', self.button0)

        # sized and placed before it's shown (initialized)
        self.fitFrame()
        self.setBoolProperty('initialized', True)

        if not self.delayButtons:
            self.setup_buttons()

        if self.delayButtons:
            Timer(self.delayButtons, self.setup_buttons).start()

        if self.closeTimeout:
            self._close_timer = Timer(self.closeTimeout, self.doClose)
            self._close_timer.start()


    def setup_buttons(self):
        self.setProperty('enable_buttons', '1')
        if self.delayButtons:
            util.MONITOR.waitForAbort(0.1)
            self.setFocusId(self.BUTTON_IDS[self.select])

    def onAction(self, action):
        controlID = self.getFocusId()
        actionID = action.getId()

        if self.actionCallback:
            res = self.actionCallback(self, actionID, controlID)
            if res:
                return

        kodigui.BaseDialog.onAction(self, action)

    def doClose(self, **kw):
        if self._close_timer and self._close_timer.is_alive():
            self._close_timer.cancel()

        super(OptionsDialog, self).doClose()

    def onClick(self, controlID):
        if controlID in self.BUTTON_IDS:
            self.buttonChoice = self.BUTTON_IDS.index(controlID)
            self.doClose()


def show(header, info, button0=None, button1=None, button2=None, action_callback=None, dialog_props=None, select=0,
         delay_buttons=None, close_timeout=None):
    w = OptionsDialog.open(header=header, info=info, button0=button0, button1=button1, button2=button2, select=select,
                           action_callback=action_callback, dialog_props=dialog_props, delay_buttons=delay_buttons,
                           close_timeout=close_timeout)
    choice = w.buttonChoice
    ref = util.windowRef(w)
    del w
    util.collectIfAlive(ref)
    return choice
