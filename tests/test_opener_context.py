# coding=utf-8
"""
lib/windows/opener.py's additive `context` parameter from hashed-orbiting-pizza.md's Phase 4
item 1: `open()`/`playableClicked()` accept an optional `context` (the calling window, a
UtilMixin instance) - when provided, the movie branch calls `context.openWindow(...)` (chain-
aware: swaps in place if `context` is a live chain host, else falls back to `handleOpen()`
itself) instead of unconditionally calling the module-level `handleOpen()`. `context=None` (the
default, used by every caller not yet migrated) preserves the exact pre-Phase-4 behavior - locked
in here as a regression check, not just the new behavior.

Only the movie branch (`playableClicked()`) is wired so far - every other dispatch branch in
`open()` ignores `context` entirely until its own Phase 4 item threads it through; not tested here
since there's nothing branch-specific to regress yet.

`handleOpen()` itself is never actually invoked for real here (it constructs and opens a real,
blocking native Kodi window) - the `context=None` regression test monkeypatches the module-level
`opener.handleOpen` with a recording fake instead, same shape as this suite's other module-level-
singleton monkeypatches (e.g. `windowutils.HOME`).

Importing lib.windows.opener starts lib.player's monitor thread unless abort_requested is set
first - same guard the other lib.windows.* tests use for the same reason.
"""

from __future__ import absolute_import

from kodienv import ENV

ENV.abort_requested = True
from lib.windows import opener  # noqa: E402
from lib.windows import preplay  # noqa: E402

from .base import KodiTestCase  # noqa: E402


class FakeMovie(object):
    TYPE = 'movie'


class FakeContext(object):
    def __init__(self):
        self.openWindowCalls = []

    def openWindow(self, window_class, **kwargs):
        self.openWindowCalls.append((window_class, kwargs))


class FakeServer(object):
    def __init__(self, obj):
        self._obj = obj

    def getObject(self, key):
        return self._obj


class PlayableClickedTest(KodiTestCase):
    def test_with_a_live_context_swaps_in_place_via_openWindow(self):
        context = FakeContext()
        movie = FakeMovie()

        result = opener.playableClicked(movie, context=context)

        self.assertEqual([(preplay.PrePlayWindow, {'video': movie})], context.openWindowCalls)
        self.assertEqual('', result)

    def test_from_watchlist_resolves_to_the_watchlist_shell(self):
        context = FakeContext()
        movie = FakeMovie()

        opener.playableClicked(movie, context=context, from_watchlist=True)

        self.assertEqual([(preplay.PrePlayWindowWL, {'video': movie, 'from_watchlist': True})],
                          context.openWindowCalls)

    def test_without_a_context_falls_back_to_handleOpen_unchanged(self):
        """Regression check - context=None (every caller not yet migrated) must behave exactly
        as before this session's change: handleOpen() gets called, openWindow() never does."""
        movie = FakeMovie()
        handleOpenCalls = []

        def fakeHandleOpen(winclass, **kwargs):
            handleOpenCalls.append((winclass, kwargs))
            return 'FAKE_EXIT_COMMAND'

        originalHandleOpen = opener.handleOpen
        opener.handleOpen = fakeHandleOpen
        try:
            result = opener.playableClicked(movie)
        finally:
            opener.handleOpen = originalHandleOpen

        self.assertEqual([(preplay.PrePlayWindow, {'video': movie})], handleOpenCalls)
        self.assertEqual('FAKE_EXIT_COMMAND', result)


class OpenDispatchContextTest(KodiTestCase):
    def test_context_reaches_playableClicked_for_a_movie_object(self):
        context = FakeContext()
        movie = FakeMovie()

        opener.open(movie, context=context)

        self.assertEqual([(preplay.PrePlayWindow, {'video': movie})], context.openWindowCalls)

    def test_context_survives_the_string_resolution_recursive_call(self):
        """open() called with a ratingKey string re-resolves the real object via the server, then
        recurses into open() again - context must not get dropped along the way. Passing server=
        explicitly (a real kwarg open() already accepts, popped before use) avoids touching the
        real plexapp.SERVERMANAGER singleton."""
        context = FakeContext()
        movie = FakeMovie()
        server = FakeServer(movie)

        opener.open('12345', context=context, server=server)

        self.assertEqual([(preplay.PrePlayWindow, {'video': movie})], context.openWindowCalls)

    def test_a_branch_not_yet_wired_for_context_ignores_it_and_behaves_as_before(self):
        """Regression check: passing context for an object type whose dispatch branch hasn't been
        made chain-aware yet (anything but movie) must be a pure no-op for that branch - locks in
        that context is genuinely additive/inert, not a blanket behavior change."""
        class FakeClip(object):
            TYPE = 'clip'

        played = []
        originalPlay = None
        from lib.windows import videoplayer
        originalPlay = videoplayer.play
        videoplayer.play = lambda **kw: played.append(kw)
        try:
            opener.open(FakeClip(), context=FakeContext())
        finally:
            videoplayer.play = originalPlay

        self.assertEqual(1, len(played))
