# coding=utf-8
"""
lib/windows/opener.py's additive `context` parameter from hashed-orbiting-pizza.md's Phase 4
item 1: `open()`/`playableClicked()` accept an optional `context` (the calling window, a
UtilMixin instance) - when provided, the movie branch calls `context.openWindow(...)` (chain-
aware: swaps in place if `context` is a live chain host, else falls back to `handleOpen()`
itself) instead of unconditionally calling the module-level `handleOpen()`. `context=None` (the
default, used by every caller not yet migrated) preserves the exact pre-Phase-4 behavior - locked
in here as a regression check, not just the new behavior.

Phase 4 items 2-5 wire the same `context`-passthrough shape into episode/show/artist/season/album/
director/actor. Item 8 is structurally different - `sectionClicked()`/`genreClicked()` don't call
`context.openWindow(a_class, ...)` at all, since there's no new shell class involved; instead they
call `context._liveChainHost().swapToSection(section, filter_=...)` directly, reusing the host's
own section-rendering in place.

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
from lib.windows import episodes  # noqa: E402
from lib.windows import subitems  # noqa: E402
from lib.windows import tracks  # noqa: E402
from lib.windows import person as person_window  # noqa: E402
from lib.windows import playlist  # noqa: E402
from lib.windows import collection as collection_window  # noqa: E402

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
        made chain-aware yet (e.g. a video clip, still played directly) must be a pure no-op for
        that branch - locks in that context is genuinely additive/inert, not a blanket behavior
        change."""
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


class FakeTyped(object):
    def __init__(self, type_):
        self.TYPE = type_


class ItemClickedFunctionsTest(KodiTestCase):
    """Phase 4 items 2-5: episode/show/artist/season/album/director/actor all get the same
    additive context shape playableClicked() got in item 1 - with a live context, swap in place
    via context.openWindow(); without one (the default), fall back to handleOpen() unchanged."""

    def test_episode_with_context_swaps_in_place(self):
        context = FakeContext()
        episode = FakeTyped('episode')

        result = opener.episodeClicked(episode, context=context)

        self.assertEqual([(episodes.EpisodesWindow, {'episode': episode})], context.openWindowCalls)
        self.assertEqual('', result)

    def test_show_with_context_swaps_in_place(self):
        context = FakeContext()
        show = FakeTyped('show')

        opener.showClicked(show, context=context)

        self.assertEqual([(subitems.ShowWindow, {'media_item': show})], context.openWindowCalls)

    def test_a_single_season_show_opens_its_season_at_once_from_a_standalone_window(self):
        """3f stage E: a standalone context (no chain host) used to open the season 0.15 s later
        from a threading.Timer, a blocking open on the timer's thread. It opens on the calling
        thread now, before showClicked() returns."""
        from plexnet.plexobjects import PlexValue

        class SingleSeasonShow(FakeTyped):
            def __init__(self, season):
                FakeTyped.__init__(self, 'show')
                self.season = season

            def get(self, attr):
                return PlexValue('1' if attr == 'skipChildren' else '')

            def seasons(self):
                return [self.season]

        context = FakeContext()
        context._liveChainHost = lambda: None
        season = FakeTyped('season')

        self.assertEqual('', opener.showClicked(SingleSeasonShow(season), context=context))

        self.assertEqual([(episodes.EpisodesWindow, {'season': season})], context.openWindowCalls)

    def test_artist_with_context_swaps_in_place(self):
        context = FakeContext()
        artist = FakeTyped('artist')

        opener.artistClicked(artist, context=context)

        self.assertEqual([(subitems.ArtistWindow, {'media_item': artist})], context.openWindowCalls)

    def test_season_with_context_swaps_in_place(self):
        context = FakeContext()
        season = FakeTyped('season')

        opener.seasonClicked(season, context=context)

        self.assertEqual([(episodes.EpisodesWindow, {'season': season})], context.openWindowCalls)

    def test_album_with_context_swaps_in_place(self):
        context = FakeContext()
        album = FakeTyped('album')

        opener.albumClicked(album, context=context)

        self.assertEqual([(tracks.AlbumWindow, {'album': album})], context.openWindowCalls)

    def test_director_with_context_swaps_in_place(self):
        context = FakeContext()
        director = FakeTyped('Director')

        opener.directorClicked(director, context=context)

        self.assertEqual([(person_window.DirectorWindow, {'role': director})], context.openWindowCalls)

    def test_actor_with_context_swaps_in_place(self):
        context = FakeContext()
        actor = FakeTyped('Role')

        opener.actorClicked(actor, context=context)

        self.assertEqual([(person_window.ActorWindow, {'role': actor})], context.openWindowCalls)

    def test_playlist_with_context_swaps_in_place(self):
        context = FakeContext()
        pl = FakeTyped('playlist')

        opener.playlistClicked(pl, context=context)

        self.assertEqual([(playlist.PlaylistWindow, {'playlist': pl})], context.openWindowCalls)

    def test_collection_with_context_opens_its_grid(self):
        # as the Collections tab does - it went down sectionClicked() and showed as a library
        context = FakeContext()
        col = FakeTyped('collection')

        self.assertEqual('', opener.collectionClicked(col, context=context))

        self.assertEqual([(collection_window.CollectionWindow, {'collection': col})], context.openWindowCalls)

    def test_without_context_each_falls_back_to_handleOpen_unchanged(self):
        """Regression check, all eight at once - context=None must behave exactly as before this
        session's change for every one of them."""
        handleOpenCalls = []

        def fakeHandleOpen(winclass, **kwargs):
            handleOpenCalls.append((winclass, kwargs))
            return ''

        originalHandleOpen = opener.handleOpen
        opener.handleOpen = fakeHandleOpen
        try:
            opener.episodeClicked(FakeTyped('episode'))
            opener.showClicked(FakeTyped('show'))
            opener.artistClicked(FakeTyped('artist'))
            opener.seasonClicked(FakeTyped('season'))
            opener.albumClicked(FakeTyped('album'))
            opener.directorClicked(FakeTyped('Director'))
            opener.actorClicked(FakeTyped('Role'))
            opener.playlistClicked(FakeTyped('playlist'))
        finally:
            opener.handleOpen = originalHandleOpen

        self.assertEqual(8, len(handleOpenCalls))


class OpenDispatchContextForwardingTest(KodiTestCase):
    """open()'s own TYPE dispatch must actually forward context into each of the item 2-5
    branches above - the functions being correctly context-aware (tested above) means nothing if
    open() itself doesn't pass context through to them."""

    def test_dispatch_forwards_context_for_each_wired_type(self):
        cases = [
            ('episode', episodes.EpisodesWindow, {'episode': None}),
            ('show', subitems.ShowWindow, {'media_item': None}),
            ('artist', subitems.ArtistWindow, {'media_item': None}),
            ('season', episodes.EpisodesWindow, {'season': None}),
            ('album', tracks.AlbumWindow, {'album': None}),
            ('Director', person_window.DirectorWindow, {'role': None}),
            ('Role', person_window.ActorWindow, {'role': None}),
            ('playlist', playlist.PlaylistWindow, {'playlist': None}),
        ]
        for type_, expectedClass, kwargTemplate in cases:
            context = FakeContext()
            obj = FakeTyped(type_)
            expectedKwargs = {k: (obj if v is None else v) for k, v in kwargTemplate.items()}

            opener.open(obj, context=context)

            self.assertEqual([(expectedClass, expectedKwargs)], context.openWindowCalls,
                              "TYPE={0}".format(type_))


class FakeChainHost(object):
    def __init__(self):
        self.swapToSectionCalls = []

    def swapToSection(self, section, filter_=None):
        self.swapToSectionCalls.append((section, filter_))


class FakeChainedContext(object):
    """A UtilMixin-shaped double whose _liveChainHost() resolves to a caller-supplied host (or
    None, matching a not-yet-hosted/closed caller) - the same shape opener.py's own
    sectionClicked() reads directly (windowutils.py's UtilMixin.openWindow() reads it too)."""

    def __init__(self, host):
        self._host = host

    def _liveChainHost(self):
        return self._host


class FakeServerRef(object):
    uuid = 'a-server-uuid'


class FakeSection(object):
    """The handleOpen()-fallback branch of sectionClicked() reads TYPE/key/server.uuid (to build
    a viewtype setting key) before ever touching filter_ - a bare string stand-in (fine for the
    in-place swapToSection() path, which never inspects section at all) isn't enough here."""
    TYPE = 'movie'
    key = '1'
    server = FakeServerRef()


class SectionClickedContextTest(KodiTestCase):
    """Phase 4 item 8: structurally different from items 1-5 above - there's no new shell class,
    so sectionClicked()/genreClicked() call context._liveChainHost().swapToSection(...) directly
    instead of context.openWindow(a_class, ...)."""

    def test_with_a_live_chain_host_swaps_the_section_in_place(self):
        host = FakeChainHost()
        context = FakeChainedContext(host)

        result = opener.sectionClicked('a-section', filter_='a-filter', context=context)

        self.assertEqual([('a-section', 'a-filter')], host.swapToSectionCalls)
        self.assertEqual('', result)

    def test_extra_kwargs_are_dropped_on_the_in_place_path(self):
        """came_from etc. are only meaningful to a freshly-constructed LibraryWindow's own
        __init__, never read by openSection()/swapToSection() - confirming they're silently
        dropped here, not smuggled through and later raising a TypeError."""
        host = FakeChainHost()
        context = FakeChainedContext(host)

        opener.sectionClicked('a-section', context=context, came_from='some-ratingkey')

        self.assertEqual([('a-section', None)], host.swapToSectionCalls)

    def test_without_a_live_host_falls_back_to_handleOpen_unchanged(self):
        from lib.windows import library

        context = FakeChainedContext(None)  # not (yet) a chain host - e.g. a closed/stale caller
        handleOpenCalls = []

        def fakeHandleOpen(winclass, **kwargs):
            handleOpenCalls.append((winclass, kwargs))
            return ''

        originalHandleOpen = opener.handleOpen
        opener.handleOpen = fakeHandleOpen
        try:
            opener.sectionClicked(FakeSection(), context=context)
        finally:
            opener.handleOpen = originalHandleOpen

        self.assertEqual(1, len(handleOpenCalls))
        self.assertEqual(library.LibraryWindow, handleOpenCalls[0][0])

    def test_without_context_falls_back_to_handleOpen_unchanged(self):
        """Regression check - context=None (every caller not yet migrated) must behave exactly as
        before this session's change."""
        from lib.windows import library

        handleOpenCalls = []

        def fakeHandleOpen(winclass, **kwargs):
            handleOpenCalls.append((winclass, kwargs))
            return ''

        originalHandleOpen = opener.handleOpen
        opener.handleOpen = fakeHandleOpen
        try:
            opener.sectionClicked(FakeSection())
        finally:
            opener.handleOpen = originalHandleOpen

        self.assertEqual(1, len(handleOpenCalls))
        self.assertEqual(library.LibraryWindow, handleOpenCalls[0][0])


class GenreClickedContextTest(KodiTestCase):
    def test_forwards_context_and_builds_the_genre_filter(self):
        from plexnet import plexlibrary

        class FakeGenre(object):
            FILTER = 'genre'
            id = '5'
            tag = 'Action'

        fakeSection = object()
        originalFromFilter = plexlibrary.LibrarySection.fromFilter
        plexlibrary.LibrarySection.fromFilter = staticmethod(lambda filter_: fakeSection)

        calls = []
        originalSectionClicked = opener.sectionClicked

        def fakeSectionClicked(section, filter_=None, context=None, **kwargs):
            calls.append((section, filter_, context))
            return ''

        opener.sectionClicked = fakeSectionClicked
        try:
            context = object()
            opener.genreClicked(FakeGenre(), context=context)
        finally:
            plexlibrary.LibrarySection.fromFilter = originalFromFilter
            opener.sectionClicked = originalSectionClicked

        self.assertEqual(1, len(calls))
        section, filter_, ctx = calls[0]
        self.assertIs(fakeSection, section)
        self.assertEqual({'type': 'genre', 'display': 'Genre', 'sub': {'val': '5', 'display': 'Action'}}, filter_)
        self.assertIs(context, ctx)


class PhotoDirectoryClickedContextTest(KodiTestCase):
    """Regression test for a gap found after Phase 4/5: photoDirectoryClicked() forwarded neither
    its own context param (didn't have one) nor did open()'s TYPE == 'photodirectory' branch pass
    context through to it - so a photodirectory reached generically (a hub, search) always opened
    standalone even though sectionClicked() underneath already supports hosting it. Mirrors
    GenreClickedContextTest's shape - same structurally-different-from-items-1-5 pattern."""

    def test_forwards_context_to_sectionClicked(self):
        calls = []
        originalSectionClicked = opener.sectionClicked

        def fakeSectionClicked(section, filter_=None, context=None, **kwargs):
            calls.append((section, filter_, context))
            return ''

        opener.sectionClicked = fakeSectionClicked
        try:
            context = object()
            photodirectory = object()
            opener.photoDirectoryClicked(photodirectory, context=context)
        finally:
            opener.sectionClicked = originalSectionClicked

        self.assertEqual([(photodirectory, None, context)], calls)

    def test_open_dispatch_forwards_context_for_photodirectory(self):
        calls = []
        originalPhotoDirectoryClicked = opener.photoDirectoryClicked

        def fakePhotoDirectoryClicked(photodirectory, context=None, **kwargs):
            calls.append((photodirectory, context))
            return ''

        opener.photoDirectoryClicked = fakePhotoDirectoryClicked
        try:
            context = object()
            obj = FakeTyped('photodirectory')
            opener.open(obj, context=context)
        finally:
            opener.photoDirectoryClicked = originalPhotoDirectoryClicked

        self.assertEqual([(obj, context)], calls)


class CollectionClickedContextTest(KodiTestCase):
    """Same gap, same fix, found during hashed-orbiting-pizza.md's Phase 5 dead-branch audit:
    open()'s TYPE == 'collection' branch didn't pass context through to collectionClicked(), so a
    collection reached generically (a hub, search) always opened standalone. collectionClicked()
    itself now opens the collection's grid (CollectionWindow) through the context, as the
    Collections tab does - not sectionClicked(), which showed it as a library with 404ing rows
    (live, 2026-10-07; ItemClickedFunctionsTest.test_collection_with_context_opens_its_grid)."""

    def test_doesnt_go_through_sectionClicked(self):
        calls = []
        originalSectionClicked = opener.sectionClicked
        opener.sectionClicked = lambda *args, **kwargs: calls.append(args)
        try:
            opener.collectionClicked(object(), context=FakeContext())
        finally:
            opener.sectionClicked = originalSectionClicked

        self.assertEqual([], calls)

    def test_open_dispatch_forwards_context_for_collection(self):
        calls = []
        originalCollectionClicked = opener.collectionClicked

        def fakeCollectionClicked(collection, context=None, **kwargs):
            calls.append((collection, context))
            return ''

        opener.collectionClicked = fakeCollectionClicked
        try:
            context = object()
            obj = FakeTyped('collection')
            opener.open(obj, context=context)
        finally:
            opener.collectionClicked = originalCollectionClicked

        self.assertEqual([(obj, context)], calls)


class OpenByKeyTest(KodiTestCase):
    """A rating key opens on the server it came with: two servers can have the same key, and there's
    no selected server to fall back on any more (plan Phase 9)."""

    def test_a_key_opens_on_its_own_server(self):
        from unittest import mock
        server = mock.Mock()
        opened = []
        real_open = opener.open
        with mock.patch.object(opener, 'open', lambda obj, context=None, **kwargs: opened.append(obj)):
            real_open('99097', server=server)
        server.getObject.assert_called_once_with('/library/metadata/99097')
        self.assertEqual([server.getObject.return_value], opened)

    def test_a_key_without_a_server_is_a_mistake(self):
        with self.assertRaises(KeyError):
            opener.open('99097')
