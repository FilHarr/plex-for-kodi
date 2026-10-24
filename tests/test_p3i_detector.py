# coding=utf-8
"""
p3i's black-border/L5 detection skipped for a Direct Stream or transcode (lib/p3i_detector.py, from
pannal/plex-for-kodi f6412cb5): its startup pause held playback for minutes, or for good, on a stream that
can't seek (AM6B, T5 dev, 2026-10-19). Direct Play keeps it; Kodi without p3i's API is asked once and
otherwise left alone.

A fake p3i stands in for Kodi's JSON-RPC: SetSkipNext publishes the skip with a new token, the play request
takes it (as Kodi does when the request is submitted), and ClearSkipNext clears it only for the newest,
untaken token. _playVideo() runs for real; the Plex decision, the handler's dialog and Kodi's player are
stubs. Importing lib.player starts its monitor thread unless abort_requested is set first.
"""

from __future__ import absolute_import

import json
from types import SimpleNamespace
from unittest import mock

from kodienv import ENV

ENV.abort_requested = True
from lib import p3i_detector, player  # noqa: E402

from .base import KodiTestCase  # noqa: E402


class FakeP3i(object):
    def __init__(self, available=True):
        self.available = available
        self.calls = []
        self.armed = False
        self.generation = 0

    def rpc(self, raw):
        request = json.loads(raw)
        method = request['method'].split('.')[-1]
        self.calls.append(method)
        if not self.available:
            return json.dumps({'jsonrpc': '2.0', 'error': {'code': -32601, 'message': 'Method not found.'}, 'id': 1})
        if method == 'GetCapabilities':
            result = {'version': 1, 'supported': True, 'ownedskip': True}
        elif method == 'SetSkipNext':
            self.generation += 1
            self.armed = True
            result = {'version': 1, 'status': 'armed', 'token': str(self.generation)}
        elif method == 'ClearSkipNext':
            cleared = self.armed and request['params']['token'] == str(self.generation)
            if cleared:
                self.armed = False
            result = {'version': 1, 'status': 'cleared' if cleared else 'unchanged'}
        else:
            raise AssertionError(method)
        return json.dumps({'jsonrpc': '2.0', 'result': result, 'id': 1})

    def take(self):
        """Kodi submitting a video request: takes the skip, if one's armed."""
        taken, self.armed = self.armed, False
        return taken


class P3iTestCase(KodiTestCase):
    available = True

    def setUp(self):
        super(P3iTestCase, self).setUp()
        self.p3i = FakeP3i(self.available)
        for target, attr, value in ((p3i_detector, '_supported', None),
                                    (p3i_detector.xbmc, 'executeJSONRPC', self.p3i.rpc)):
            patcher = mock.patch.object(target, attr, value)
            patcher.start()
            self.addCleanup(patcher.stop)


class ModuleTest(P3iTestCase):
    def test_arming_hands_back_its_token(self):
        self.assertEqual('1', p3i_detector.arm_skip())
        self.assertTrue(self.p3i.armed)

    def test_its_own_token_clears_it(self):
        token = p3i_detector.arm_skip()
        p3i_detector.clear_skip(token)
        self.assertFalse(self.p3i.armed)

    def test_an_older_token_leaves_a_newer_skip_alone(self):
        old = p3i_detector.arm_skip()
        p3i_detector.arm_skip()
        p3i_detector.clear_skip(old)
        self.assertTrue(self.p3i.armed)

    def test_nothing_to_clear_asks_nothing(self):
        p3i_detector.clear_skip(None)
        self.assertEqual([], self.p3i.calls)

    def test_capabilities_are_asked_once(self):
        for unused in range(3):
            p3i_detector.arm_skip()
        self.assertEqual(1, self.p3i.calls.count('GetCapabilities'))

    def test_a_reply_without_owned_skip_is_unsupported(self):
        for reply in ({'version': 1, 'supported': True},                    # no ownedskip
                      {'version': 2, 'supported': True, 'ownedskip': True},  # another version
                      {'version': 1, 'supported': False, 'ownedskip': True}):
            with self.subTest(reply=reply):
                p3i_detector._supported = None
                with mock.patch.object(p3i_detector, '_rpc', return_value=reply):
                    self.assertFalse(p3i_detector.supported())

    def test_a_broken_reply_is_unsupported(self):
        for raw in ('not json', json.dumps({'result': 'armed'}), json.dumps([])):
            with self.subTest(raw=raw):
                p3i_detector._supported = None
                with mock.patch.object(p3i_detector.xbmc, 'executeJSONRPC', return_value=raw):
                    self.assertFalse(p3i_detector.supported())
                    self.assertIsNone(p3i_detector.arm_skip())


class StockKodiTest(P3iTestCase):
    available = False

    def test_asked_once_then_left_alone(self):
        for unused in range(3):
            self.assertIsNone(p3i_detector.arm_skip())
        self.assertEqual(['GetCapabilities'], self.p3i.calls)


def _number(value):
    return SimpleNamespace(asInt=lambda: value)


class Handler(player.SeekPlayerHandler):
    def setup(self, *args, **kwargs):
        # the seek dialog is a native window
        self.dialog = SimpleNamespace(baseOffset=0)

    def getIntroOffset(self, *args, **kwargs):
        return None


class Playback(player.PlexPlayer):
    def __init__(self, p3i):
        player.PlexPlayer.__init__(self)
        self.p3i = p3i
        self.handler = Handler(self, 'session')
        art = SimpleNamespace(asTranscodedImageURL=lambda *a, **kw: 'image')
        self.video = SimpleNamespace(defaultArt=art, defaultThumb=art, type='movie', title='Movie',
                                     grandparentTitle='', duration=_number(600000), year=_number(2020),
                                     summary='', guid='imdb://test', chapters=[],
                                     settings=SimpleNamespace(getGlobal=lambda key: 'client'))
        self.plays = []
        self.failPlay = False

    def isPlaying(self):
        return False

    def stopAndWait(self, *args, **kwargs):
        pass

    def play(self, url, li):
        if self.failPlay:
            raise RuntimeError('play refused')
        # Kodi takes the skip with the request, before opening it
        self.plays.append((url, self.p3i.take()))


class PlayVideoTest(P3iTestCase):
    def setUp(self):
        super(PlayVideoTest, self).setUp()
        self.meta = SimpleNamespace(streamUrls=['https://pms.invalid/library/parts/1/2/file.mkv'],
                                    path='/media/movie.mkv', playStart=0, isMapped=False,
                                    isTranscoded=False, size=100)
        self.decision = SimpleNamespace(metadata=self.meta, build=lambda: None, getBifUrl=lambda: '',
                                        getServerDecision=lambda: self.decision)
        for target, attr, value in ((player.plexplayer, 'PlexPlayer', lambda *a, **kw: self.decision),
                                    (player.util, 'CE_SB_LAV_SWITCH', False),
                                    # setInfo() rather than the stubs' missing getVideoInfoTag()
                                    (player.util, 'KODI_VERSION_MAJOR', 19),
                                    (player.util, 'getSetting', lambda key, *a, **kw: False)):
            patcher = mock.patch.object(target, attr, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.p = Playback(self.p3i)

    def skips(self):
        return [taken for url, taken in self.p.plays]

    def test_direct_play_keeps_detection(self):
        self.p._playVideo()
        self.assertEqual([False], self.skips())
        self.assertNotIn('SetSkipNext', self.p3i.calls)

    def test_direct_stream_or_transcode_skips_it(self):
        self.meta.isTranscoded = True
        self.meta.streamUrls = ['https://pms.invalid/video/:/transcode/universal/start.mkv?directStream=1']
        self.p._playVideo()
        self.assertEqual([True], self.skips())
        # taken with the request: nothing left armed for the next video
        self.assertFalse(self.p3i.armed)
        self.assertNotIn('ClearSkipNext', self.p3i.calls)

    def test_the_servers_final_decision_decides(self):
        # the client asked for Direct Play; the server sent a transcode
        final = SimpleNamespace(**vars(self.meta))
        final.isTranscoded = True
        changed = SimpleNamespace(metadata=final, getBifUrl=lambda: '')
        with mock.patch.object(self.decision, 'getServerDecision', lambda: changed):
            self.p._playVideo()
        self.assertEqual([True], self.skips())

    def test_each_play_is_decided_on_its_own(self):
        for transcoded in (True, False, True):
            self.meta.isTranscoded = transcoded
            self.p._playVideo()
        self.assertEqual([True, False, True], self.skips())
        self.assertEqual(1, self.p3i.calls.count('GetCapabilities'))

    def test_a_play_that_never_happens_takes_its_skip_back(self):
        self.meta.isTranscoded = True
        self.p.failPlay = True
        with self.assertRaises(RuntimeError):
            self.p._playVideo()
        self.assertFalse(self.p3i.armed)
        self.assertIn('ClearSkipNext', self.p3i.calls)
        # the next Direct Play isn't skipped by a leftover
        self.p.failPlay = False
        self.meta.isTranscoded = False
        self.p._playVideo()
        self.assertEqual([False], self.skips())


class PlayVideoStockKodiTest(PlayVideoTest):
    available = False

    def test_direct_stream_or_transcode_skips_it(self):
        # nothing to skip without the API: plays as before
        self.meta.isTranscoded = True
        self.p._playVideo()
        self.assertEqual([False], self.skips())
        self.assertEqual(['GetCapabilities'], self.p3i.calls)

    def test_the_servers_final_decision_decides(self):
        pass

    def test_each_play_is_decided_on_its_own(self):
        for transcoded in (True, False, True):
            self.meta.isTranscoded = transcoded
            self.p._playVideo()
        self.assertEqual([False, False, False], self.skips())
        self.assertEqual(['GetCapabilities'], self.p3i.calls)

    def test_a_play_that_never_happens_takes_its_skip_back(self):
        self.meta.isTranscoded = True
        self.p.failPlay = True
        with self.assertRaises(RuntimeError):
            self.p._playVideo()
        self.assertNotIn('ClearSkipNext', self.p3i.calls)
