# coding=utf-8
"""
The first-screenful pause (step 12 stage E in the navigation review, TEMPORARY): on the grid opens
that pause, a grid's first chunk is written as its first screenful, a wait, then the rest - two
_chunkCallback() calls, so the wait holds no lock. The real _chunkCallbackFor() is bound onto a
small double that records the calls.

Importing lib.windows.library starts lib.player's monitor thread unless abort_requested is set
first - same guard the other lib.windows.* tests use for the same reason.
"""

from __future__ import absolute_import

import time

from kodienv import ENV

ENV.abort_requested = True
from lib.windows import library_grid  # noqa: E402

from .base import KodiTestCase  # noqa: E402


class FakeGrid(object):
    _chunkCallbackFor = library_grid.GridMixin._chunkCallbackFor

    def __init__(self, pause):
        self.firstScreenPause = pause
        self._firstChunkTiming = (3, time.time(), None)
        self.calls = []

    def _chunkCallback(self, items, start, generation=None):
        self.calls.append((len(items), start, generation))


class FirstScreenPauseTest(KodiTestCase):
    def setUp(self):
        super(FirstScreenPauseTest, self).setUp()
        self.waits = []
        monitor = library_grid.util.MONITOR
        orig = monitor.waitForAbort
        self.addCleanup(setattr, monitor, 'waitForAbort', orig)
        monitor.waitForAbort = lambda seconds: self.waits.append(seconds) or False

    def test_the_first_screenful_then_a_wait_then_the_rest(self):
        grid = FakeGrid(pause=True)
        grid._chunkCallbackFor(3)(list(range(240)), 0)
        n = library_grid.CHUNK_SCREENFUL
        self.assertEqual([(n, 0, 3), (240 - n, n, 3)], grid.calls)
        self.assertEqual([library_grid.FIRST_SCREEN_PAUSE_SECONDS], self.waits)

    def test_no_pause_writes_it_in_one(self):
        grid = FakeGrid(pause=False)
        grid._chunkCallbackFor(3)(list(range(240)), 0)
        self.assertEqual([(240, 0, 3)], grid.calls)
        self.assertEqual([], self.waits)

    def test_a_chunk_no_bigger_than_a_screenful_isnt_split(self):
        grid = FakeGrid(pause=True)
        grid._chunkCallbackFor(3)(list(range(library_grid.CHUNK_SCREENFUL)), 0)
        self.assertEqual(1, len(grid.calls))

    def test_only_the_first_chunk_pauses(self):
        grid = FakeGrid(pause=True)
        callback = grid._chunkCallbackFor(3)
        callback(list(range(240)), 0)
        callback(list(range(240)), 240)
        self.assertEqual((240, 240, 3), grid.calls[-1])
        self.assertEqual(1, len(self.waits))
