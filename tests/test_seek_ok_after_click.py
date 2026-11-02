# coding=utf-8
"""
OK that applies a seek in the player (live on the PC, 2026-11-02): Kodi runs SeekDialog.onClick() for it, then
onAction() for the same key. onClick() applied the seek and hid the OSD, which moves focus to the skip button when
one's showing - and onAction() then pressed it: a seek into the credits skipped them, ending the episode into
post-play. Ending the seek with Play, which isn't a click, never did.

Importing lib.windows.* starts lib.player's monitor thread unless abort_requested is set first.
"""

from __future__ import absolute_import

from unittest import mock

from kodienv import ENV

ENV.abort_requested = True
from kodi_six import xbmcgui  # noqa: E402
from lib.windows import seekdialog  # noqa: E402

from .base import KodiTestCase  # noqa: E402

SeekDialog = seekdialog.SeekDialog


class Action(object):
    """Kodi's Action compares equal to its ID"""

    def __init__(self, actionId):
        self.actionId = actionId

    def getId(self):
        return self.actionId

    def getButtonCode(self):
        return 0

    def __eq__(self, other):
        return self.actionId == (other.getId() if isinstance(other, Action) else other)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.actionId)


class OkAfterClickTest(KodiTestCase):
    def setUp(self):
        KodiTestCase.setUp(self)
        d = self.dialog = SeekDialog.__new__(SeekDialog)
        marker = mock.Mock(final=True, type='credits')
        d.__dict__.update(_ignoreInput=False, _focusArrived=None, _clickAppliedSeekAt=None, idleTime=None,
                          _playerNativePPIActive=False, _applyingSeek=False, _seeking=True,
                          _currentMarker={'marker': marker})
        for name in ('resetTimeout', 'resetAutoSeekTimer', 'doSeek', 'hideOSD', 'handleFinalMarker'):
            setattr(d, name, mock.Mock())
        d.scanAction = mock.Mock(return_value=False)
        d.getProperty = mock.Mock(return_value='')
        # where hideOSD() put focus: the skip button, showing for the credits
        d.getFocusId = mock.Mock(return_value=SeekDialog.SKIP_MARKER_BUTTON_ID)

    def test_the_ok_that_applied_a_seek_does_not_press_the_skip_button(self):
        self.dialog.onClick(SeekDialog.MAIN_BUTTON_ID)
        self.dialog.doSeek.assert_called_once_with()
        self.dialog.onAction(Action(xbmcgui.ACTION_SELECT_ITEM))
        self.dialog.handleFinalMarker.assert_not_called()

    def test_the_same_from_the_osd_hidden_seek(self):
        self.dialog.onClick(SeekDialog.NO_OSD_BUTTON_ID)
        self.dialog.doSeek.assert_called_once_with()
        self.dialog.onAction(Action(xbmcgui.ACTION_SELECT_ITEM))
        self.dialog.handleFinalMarker.assert_not_called()

    def test_the_next_ok_presses_it(self):
        self.dialog.onClick(SeekDialog.MAIN_BUTTON_ID)
        self.dialog.onAction(Action(xbmcgui.ACTION_SELECT_ITEM))
        self.dialog.onAction(Action(xbmcgui.ACTION_SELECT_ITEM))
        self.dialog.handleFinalMarker.assert_called_once()

    def test_ok_on_the_skip_button_still_skips(self):
        self.dialog._seeking = False
        self.dialog.onAction(Action(xbmcgui.ACTION_SELECT_ITEM))
        self.dialog.handleFinalMarker.assert_called_once()
