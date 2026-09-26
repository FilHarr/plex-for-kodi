# coding=utf-8
"""
Back pressed after play() but before playback has started. Closing then couldn't stop it (doClose()
only stops a playing video), so Kodi played it behind a black screen with the session ended. The
window waits for playback to start (playerPlaybackStarted() closes and stops it); a second press
still closes at once.
"""

from __future__ import absolute_import

from kodienv import ENV

ENV.abort_requested = True
from kodi_six import xbmcgui  # noqa: E402
from lib import player  # noqa: E402
from lib.windows import videoplayer, kodigui  # noqa: E402

from .base import KodiTestCase  # noqa: E402

try:
    from unittest import mock
except ImportError:
    import mock


class EarlyAbortTest(KodiTestCase):
    def setUp(self):
        super(EarlyAbortTest, self).setUp()
        self.window = videoplayer.VideoPlayerWindow.__new__(videoplayer.VideoPlayerWindow)
        self.window.postPlayMode = False
        self.window.earlyAbortRequested = False
        patcher = mock.patch.object(kodigui.ControlledWindow, 'onAction')
        self.baseOnAction = patcher.start()
        self.addCleanup(patcher.stop)

    def _back(self, playing):
        with mock.patch.object(player.PLAYER, 'isPlayingVideo', return_value=playing):
            self.window.onAction(xbmcgui.ACTION_NAV_BACK)

    def test_back_before_playback_starts_waits_for_it(self):
        self._back(playing=False)
        self.assertTrue(self.window.earlyAbortRequested)
        self.assertFalse(self.baseOnAction.called)

    def test_a_second_back_closes_at_once(self):
        self._back(playing=False)
        self._back(playing=False)
        self.assertTrue(self.baseOnAction.called)

    def test_back_once_playing_closes_at_once(self):
        self._back(playing=True)
        self.assertTrue(self.window.earlyAbortRequested)
        self.assertTrue(self.baseOnAction.called)

    def test_playback_starting_closes_an_aborted_window(self):
        self._back(playing=False)
        with mock.patch.object(self.window, 'doClose') as doClose:
            self.window.playerPlaybackStarted()
        doClose.assert_called_once_with()


class AbortedSessionTeardownTest(KodiTestCase):
    """Closing on av.started ran inside PlexPlayer.onAVStarted(), which then went on to the
    handler's onAVStarted() for the stopped video, and the playback-start blackout was left up:
    Kodi wouldn't bring back the screen underneath while its dialog was open."""

    def test_on_av_started_stops_when_a_handler_ended_the_session(self):
        handler = mock.Mock()
        p = player.PLAYER

        def endSession(**kwargs):
            p.sessionID = None

        with mock.patch.object(p, 'sessionID', 'abc'), mock.patch.object(p, 'handler', handler), \
                mock.patch.object(p, 'pauseAfterPlaybackStarted', False), \
                mock.patch.object(p, 'isExternalPlayer', return_value=False, create=True), \
                mock.patch.object(p, 'isPlayingVideo', return_value=True), \
                mock.patch.object(p, 'getTime', return_value=0.0):
            p.on('av.started', endSession)
            try:
                p.onAVStarted()
            finally:
                p.off('av.started', endSession)
        self.assertFalse(handler.onAVStarted.called)

    def test_ending_a_session_lifts_the_blackout(self):
        h = player.SeekPlayerHandler.__new__(player.SeekPlayerHandler)
        h.player = mock.Mock(lavSettingControl=None, _originalAlternateSeek=False)
        h.ended = False
        h.sessionID = 'abc'
        h.blackoutShown = True
        h.blackout = True
        h.prePlayVolume = None
        h.blackoutDialog = mock.Mock(isOpen=True)
        with mock.patch.object(h, 'ensureCorrectVolume'), mock.patch.object(h, 'hideOSD'):
            h.sessionEnded()
        h.blackoutDialog.doClose.assert_called_once_with()
        self.assertFalse(h.blackoutShown)
