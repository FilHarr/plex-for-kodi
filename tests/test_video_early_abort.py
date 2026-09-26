# coding=utf-8
"""
Back pressed after play() but before playback has started. Closing then couldn't stop it (doClose()
only stops a playing video), so Kodi played it behind a black screen with the session ended. The
window waits for playback to start (playerPlaybackStarted() closes and stops it); a second press
still closes at once.
"""

from __future__ import absolute_import

import threading

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
        h._blackoutLock = threading.RLock()
        h._blackoutGen = 1
        with mock.patch.object(h, 'ensureCorrectVolume'), mock.patch.object(h, 'hideOSD'):
            h.sessionEnded()
        h.blackoutDialog.doClose.assert_called_once_with()
        self.assertFalse(h.blackoutShown)


class BlackoutLiftTest(KodiTestCase):
    """The playback blackout used to lift as soon as the seek-on-start landed. Kodi then switched
    the display's refresh rate, a second or so of black screen with the skin's buffering circle
    over it (AM6B, 2026-09-27). It now lifts once the picture has run unbroken for a moment."""

    def setUp(self):
        super(BlackoutLiftTest, self).setUp()
        h = self.handler = player.SeekPlayerHandler.__new__(player.SeekPlayerHandler)
        h.player = mock.Mock()
        h.player.isPlayingVideo.return_value = True
        h.blackoutShown = True
        h._blackoutLock = threading.RLock()
        h._blackoutGen = 1
        self.caching = False
        for patcher in (mock.patch.object(h, 'stop_blackout'),
                        mock.patch.object(player.util.MONITOR, 'waitForAbort', return_value=False),
                        mock.patch.object(player.xbmc, 'getCondVisibility',
                                          side_effect=lambda cond: self.caching)):
            patcher.start()
            self.addCleanup(patcher.stop)

    def _clock(self, *times):
        self.handler.player.getTime.side_effect = list(times) + [times[-1]] * 200

    def test_a_refresh_rate_switch_restarts_the_wait(self):
        # the clock runs briefly, goes back when the display switches, then runs on
        self._clock(0.05, 0.05, 0.19, -0.02, 0.2, 0.5)
        self.handler._liftBlackoutWhenPlaying(1)
        self.handler.stop_blackout.assert_called_once_with()
        self.assertEqual(6, self.handler.player.getTime.call_count)

    def test_it_waits_while_kodi_is_caching(self):
        self._clock(0.0, 0.6, 0.7, 0.8)
        calls = []

        def caching(cond):
            calls.append(cond)
            return len(calls) < 2
        player.xbmc.getCondVisibility.side_effect = caching
        self.handler._liftBlackoutWhenPlaying(1)
        self.handler.stop_blackout.assert_called_once_with()
        self.assertEqual(3, self.handler.player.getTime.call_count)

    def test_a_session_ended_meanwhile_leaves_it_alone(self):
        def ended():
            self.handler._blackoutGen += 1
            return 0.0
        self.handler.player.getTime.side_effect = ended
        self.handler._liftBlackoutWhenPlaying(1)
        self.assertFalse(self.handler.stop_blackout.called)

    def test_a_stuck_picture_lifts_after_the_timeout(self):
        self._clock(0.0)
        self.handler._liftBlackoutWhenPlaying(1)
        self.handler.stop_blackout.assert_called_once_with()

    def test_video_stopping_lifts_at_once(self):
        self.handler.player.isPlayingVideo.return_value = False
        self.handler._liftBlackoutWhenPlaying(1)
        self.handler.stop_blackout.assert_called_once_with()
        self.assertFalse(self.handler.player.getTime.called)
