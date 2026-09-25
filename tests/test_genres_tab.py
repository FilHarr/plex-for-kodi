# coding=utf-8
"""
The "Categories" tab follow-up to hashed-orbiting-pizza.md: lib/windows/genres.py's
GenreBrowserWindow is promoted from a dropdown-only, always-standalone window to a genuine third
tab (Recommended/Library/Categories) in LibraryWindow's own tab row, hosted the same way the seven
original shells are (swapTo()), for section.TYPE in ('movie', 'show') only.

Also covers its own follow-up, the Collections tab: unlike Categories (a whole separate hosted
shell), Collections is an ITEM_TYPE='collection' selection presented as a tab - same shape as
Playlists' Music/Video tabs (_applyItemTypeChoice()), gated on an actual existence probe
(_sectionHasCollections()), positioned between Library and Categories.

Pieces covered here, each narrow (matching test_library_chain.py's own "deliberately narrow"
philosophy for onAction()/onClick()-style dispatch tests):

1. library.py's buildTabList() only adds the Categories item for movie/show sections, and the
   Collections item only when self._tabListHasCollections.
2. library.py's _tabListNeedsRebuild() tracks the Collections boundary the same way it already
   tracks Categories/playlists.
3. library.py's onClick() TAB_LIST_ID branch dispatches to browseGenres() (deferred) for the
   categories item, switchToCollections() (deferred) for the collections item, switchTab()
   (deferred, now with item_type=self._libraryTabItemType() for a 'library' click) for everything
   else.
4. genres.py's own onClick() TAB_LIST_ID branch delegates a Library/Recommended click to
   self._chainHost.switchTab() (deferred, same item_type threading as library.py's own), and does
   nothing for a categories click (already showing it) or when un-hosted.
5. library.py's switchTab()'s itemTypeChanging bypass of its own no-op guard, and
   switchToCollections()'s branch between an in-place refill vs. a real contentMode swap.

Real kodigui.ManagedListItem construction works fine in this test harness (confirmed directly) -
used here for real, rather than faked, since buildTabList()'s own gating logic is exactly what's
under test in part 1. The containing ManagedControlList is a lightweight fake throughout (matches
test_library_chain.py's own FakeHostWindow.sectionList = object() pattern) - only .reset()/
.addItems()/.getSelectedItem() are ever touched by the code under test here.

Importing lib.windows.library/genres starts lib.player's monitor thread unless abort_requested is
set first - same guard the other lib.windows.* tests use for the same reason.
"""

from __future__ import absolute_import

from kodienv import ENV

ENV.abort_requested = True
from lib.windows import library  # noqa: E402
from lib.windows import genres  # noqa: E402

from .base import KodiTestCase  # noqa: E402


class FakePost(object):
    """One MultiWindow.postNav() call, recorded by NavRecorder instead of queued."""

    def __init__(self, name, function, args, kwargs, stack):
        self.name = name
        self.function = function
        self.args = tuple(args)
        self.kwargs = dict(kwargs or {})
        self.stack = stack


class NavRecorder(object):
    """Mix into a fake host: postNav() records what would be queued."""

    def postNav(self, name, fn, args=(), kwargs=None, stack=False):
        self.__dict__.setdefault('posts', []).append(FakePost(name, fn, args, kwargs, stack))


class FakeSection(object):
    def __init__(self, type_):
        self.TYPE = type_


class FakeTabListContainer(object):
    """Stands in for the real kodigui.ManagedControlList - only the operations buildTabList()/
    onClick() actually call on it."""

    def __init__(self, selected_mode=None):
        self.items = []
        self._selectedMode = selected_mode

    def reset(self):
        self.items = []

    def addItems(self, items):
        self.items.extend(items)

    def getSelectedItem(self):
        if self._selectedMode is None:
            return None
        return FakeSelectedItem(self._selectedMode)


class FakeSelectedItem(object):
    def __init__(self, mode):
        self._mode = mode

    def getProperty(self, key):
        if key == 'content.mode':
            return self._mode
        return ''


class FakeLibrarySettings(object):
    """Same shape as test_library_chain.py's own fake of the same name (kept local here rather
    than shared, per this file's self-contained-fakes convention) - only setItemType() is ever
    touched by _tabListNeedsRebuild()'s new reset-on-vanish path."""

    def __init__(self):
        self.itemTypeCalls = []

    def setItemType(self, item_type):
        self.itemTypeCalls.append(item_type)
        return ''


buildTabList = library.LibraryWindow.buildTabList
libraryOnClick = library.LibraryWindow.onClick
genresOnClick = genres.GenreBrowserWindow.onClick
tabListNeedsRebuild = library.LibraryWindow._tabListNeedsRebuild
switchTab = library.LibraryWindow.switchTab
switchToCollections = library.LibraryWindow.switchToCollections
libraryTabItemType = library.LibraryWindow._libraryTabItemType


def patchSectionHasCollections(testcase, return_value=False):
    """_tabListNeedsRebuild() calls the real, module-level _sectionHasCollections() for any
    movie/show/artist FakeSection - that function expects a real LibrarySection (section.all(...)),
    which FakeSection doesn't implement. Tests that don't care about the Collections boundary
    itself patch this to a fixed, cheap return instead of exercising the real probe/its
    try/except fallback."""
    original = library._sectionHasCollections
    library._sectionHasCollections = lambda section: return_value
    testcase.addCleanup(lambda: setattr(library, '_sectionHasCollections', original))


class TabListNeedsRebuildTest(KodiTestCase):
    """Live-confirmed bug: onFirstInit() used to compare only the playlists/non-playlists
    boundary, so a swap between two non-playlists sections that differ only in
    Categories-eligibility silently kept showing/hiding Categories based on stale state - the
    Categories tab either failed to appear for a movie/show section, or wrongly lingered for a
    section that shouldn't have it, depending on whichever section this LibraryWindow instance's
    tab list happened to be built for first."""

    class FakeHost(object):
        def __init__(self):
            self._tabListIsPlaylists = False
            self._tabListHasCategories = False
            self._tabListHasCollections = False
            self.librarySettings = FakeLibrarySettings()

    def setUp(self):
        patchSectionHasCollections(self, return_value=False)

    def _setItemType(self, value):
        original = library.ITEM_TYPE
        library.ITEM_TYPE = value
        self.addCleanup(lambda: setattr(library, 'ITEM_TYPE', original))

    def test_show_to_movie_does_not_need_a_rebuild(self):
        """Both get Categories - crosses neither boundary."""
        host = self.FakeHost()
        tabListNeedsRebuild(host, FakeSection('show'))

        self.assertFalse(tabListNeedsRebuild(host, FakeSection('movie')))

    def test_show_to_artist_needs_a_rebuild(self):
        """The exact bug scenario - neither is 'playlists', so the old playlists-only comparison
        missed this entirely."""
        host = self.FakeHost()
        tabListNeedsRebuild(host, FakeSection('show'))

        self.assertTrue(tabListNeedsRebuild(host, FakeSection('artist')))

    def test_artist_to_movie_needs_a_rebuild(self):
        """The other direction of the same bug - a section built first for a non-Categories
        type must still gain the tab when a Categories-eligible section is entered next."""
        host = self.FakeHost()
        tabListNeedsRebuild(host, FakeSection('artist'))

        self.assertTrue(tabListNeedsRebuild(host, FakeSection('movie')))

    def test_playlists_boundary_still_triggers_a_rebuild_on_its_own(self):
        """Regression guard for the pre-existing behavior this method replaced - must not have
        been lost while fixing the Categories boundary."""
        host = self.FakeHost()
        tabListNeedsRebuild(host, FakeSection('movie'))

        self.assertTrue(tabListNeedsRebuild(host, FakeSection('playlists')))

    def test_updates_the_tracked_flags_even_when_no_rebuild_is_needed(self):
        host = self.FakeHost()
        tabListNeedsRebuild(host, FakeSection('artist'))

        self.assertFalse(host._tabListIsPlaylists)
        self.assertFalse(host._tabListHasCategories)
        self.assertFalse(host._tabListHasCollections)

    def test_collections_boundary_triggers_a_rebuild_on_its_own(self):
        """A section type staying the same (movie -> movie) but crossing the collections-existence
        boundary (e.g. the probe result changed - unusual but not impossible mid-session) still
        needs a rebuild, independent of the other two boundaries."""
        host = self.FakeHost()
        patchSectionHasCollections(self, return_value=False)
        tabListNeedsRebuild(host, FakeSection('movie'))

        patchSectionHasCollections(self, return_value=True)
        self.assertTrue(tabListNeedsRebuild(host, FakeSection('movie')))
        self.assertTrue(host._tabListHasCollections)

    def test_resets_item_type_when_collections_vanish_while_still_selected(self):
        """The follow-up bug to the caching fix: returning to a section left on the Collections
        tab restores ITEM_TYPE='collection' from LibrarySettings before this probe ever runs
        (openSection() -> LibrarySettings.__init__()) - if every collection has since been
        removed, has_collections goes False, but without this reset ITEM_TYPE would stay stuck on
        'collection' with no tab left to represent it, silently emptying the Library grid."""
        patchSectionHasCollections(self, return_value=False)
        self._setItemType('collection')
        host = self.FakeHost()

        tabListNeedsRebuild(host, FakeSection('movie'))

        self.assertEqual(['movie'], host.librarySettings.itemTypeCalls)

    def test_does_not_reset_item_type_when_collections_still_present(self):
        patchSectionHasCollections(self, return_value=True)
        self._setItemType('collection')
        host = self.FakeHost()

        tabListNeedsRebuild(host, FakeSection('movie'))

        self.assertEqual([], host.librarySettings.itemTypeCalls)

    def test_does_not_reset_item_type_when_it_was_never_collection(self):
        """The far more common case (item type is 'movie', 'episode', etc.) must not trigger a
        spurious LibrarySettings write on every rebuild."""
        patchSectionHasCollections(self, return_value=False)
        self._setItemType('movie')
        host = self.FakeHost()

        tabListNeedsRebuild(host, FakeSection('movie'))

        self.assertEqual([], host.librarySettings.itemTypeCalls)

    def test_collections_probe_only_runs_for_relevant_section_types(self):
        """photo/photodirectory/movies_shows/playlists structurally can't have collections - the
        probe (real network call in production) must never even run for them."""
        host = self.FakeHost()
        probeCalls = []
        original = library._sectionHasCollections
        library._sectionHasCollections = lambda section: probeCalls.append(section) or False
        self.addCleanup(lambda: setattr(library, '_sectionHasCollections', original))

        for section_type in ('photo', 'photodirectory', 'movies_shows', 'playlists'):
            tabListNeedsRebuild(host, FakeSection(section_type))

        self.assertEqual([], probeCalls)


class BuildTabListCategoriesGatingTest(KodiTestCase):
    class FakeHost(object):
        def __init__(self, section_type):
            self.section = FakeSection(section_type)
            self._tabListIsPlaylists = False
            self._tabListHasCollections = False
            self.contentMode = 'library'
            self.tabList = FakeTabListContainer()

        def updateActiveTabMarker(self, active_override=None):
            pass

    def _modesFor(self, section_type):
        host = self.FakeHost(section_type)
        buildTabList(host)
        return [mli.getProperty('content.mode') for mli in host.tabList.items]

    def test_categories_appears_after_library_for_movie_and_show(self):
        for section_type in ('movie', 'show'):
            self.assertEqual(['recommended', 'library', 'categories'], self._modesFor(section_type),
                              "section.TYPE={0}".format(section_type))

    def test_categories_absent_for_other_section_types(self):
        for section_type in ('artist', 'photo', 'photodirectory', 'movies_shows'):
            self.assertEqual(['recommended', 'library'], self._modesFor(section_type),
                              "section.TYPE={0}".format(section_type))


class BuildTabListCollectionsGatingTest(KodiTestCase):
    """self._tabListHasCollections drives this directly (the real network probe is
    _tabListNeedsRebuild()'s job, covered separately above) - buildTabList() itself just trusts
    the flag, same as it already trusts self._tabListHasCategories."""

    class FakeHost(object):
        def __init__(self, section_type, has_collections):
            self.section = FakeSection(section_type)
            self._tabListIsPlaylists = False
            self._tabListHasCollections = has_collections
            self.contentMode = 'library'
            self.tabList = FakeTabListContainer()

        def updateActiveTabMarker(self, active_override=None):
            pass

    def _modesFor(self, section_type, has_collections):
        host = self.FakeHost(section_type, has_collections)
        buildTabList(host)
        return [mli.getProperty('content.mode') for mli in host.tabList.items]

    def test_sits_between_library_and_categories_for_movie_and_show(self):
        for section_type in ('movie', 'show'):
            self.assertEqual(['recommended', 'library', 'collections', 'categories'],
                              self._modesFor(section_type, True),
                              "section.TYPE={0}".format(section_type))

    def test_sits_after_library_when_no_categories_tab_exists(self):
        """artist sections can have Collections (the old dropdown offered it) but never get a
        Categories tab - Collections should still appear, right after Library."""
        self.assertEqual(['recommended', 'library', 'collections'], self._modesFor('artist', True))

    def test_absent_when_the_flag_is_false_regardless_of_section_type(self):
        for section_type in ('movie', 'show', 'artist'):
            self.assertNotIn('collections', self._modesFor(section_type, False),
                              "section.TYPE={0}".format(section_type))


class LibraryOnClickTabDispatchTest(KodiTestCase):
    class FakeHost(NavRecorder):
        SECTION_LIST_ID = 1  # distinct from TAB_LIST_ID, never matched in these tests
        TAB_LIST_ID = 320

        def __init__(self, selected_mode, is_playlists=False, library_tab_item_type=None):
            self.tabList = FakeTabListContainer(selected_mode)
            self._tabListIsPlaylists = is_playlists
            self.movingSection = False
            self._library_tab_item_type = library_tab_item_type
            self.posts = []

        def browseGenres(self):
            pass

        def switchToCollections(self):
            pass

        def switchTab(self, mode, item_type=None):
            pass

        def _libraryTabItemType(self):
            return self._library_tab_item_type

    def test_categories_click_defers_to_browseGenres(self):
        host = self.FakeHost('categories')

        libraryOnClick(host, host.TAB_LIST_ID)

        self.assertEqual(1, len(host.posts))
        post = host.posts[0]
        self.assertEqual(host.browseGenres, post.function)

    def test_collections_click_defers_to_switchToCollections(self):
        host = self.FakeHost('collections')

        libraryOnClick(host, host.TAB_LIST_ID)

        self.assertEqual(1, len(host.posts))
        post = host.posts[0]
        self.assertEqual(host.switchToCollections, post.function)

    def test_library_click_defers_to_switchTab_unchanged(self):
        host = self.FakeHost('library')

        libraryOnClick(host, host.TAB_LIST_ID)

        self.assertEqual(1, len(host.posts))
        post = host.posts[0]
        self.assertEqual(host.switchTab, post.function)
        self.assertEqual(('library',), post.args)
        self.assertEqual({'item_type': None}, post.kwargs)

    def test_library_click_threads_the_item_type_reset(self):
        """A Library click while ITEM_TYPE is stuck on 'collection' (left over from Collections)
        must pass the host's own _libraryTabItemType() result through to switchTab()."""
        host = self.FakeHost('library', library_tab_item_type='movie')

        libraryOnClick(host, host.TAB_LIST_ID)

        self.assertEqual({'item_type': 'movie'}, host.posts[0].kwargs)

    def test_recommended_click_never_passes_an_item_type(self):
        host = self.FakeHost('recommended', library_tab_item_type='movie')

        libraryOnClick(host, host.TAB_LIST_ID)

        self.assertEqual({'item_type': None}, host.posts[0].kwargs)


class GenresOnClickDelegationTest(KodiTestCase):
    class FakeChainHost(NavRecorder):
        def __init__(self, library_tab_item_type=None):
            self.posts = []
            self.switchTab = self._switchTab
            self.switchTabCalls = []
            self._library_tab_item_type = library_tab_item_type

        def _switchTab(self, mode, item_type=None):
            self.switchTabCalls.append((mode, item_type))

        def _libraryTabItemType(self):
            return self._library_tab_item_type

    class FakeGenresHost(object):
        SECTION_LIST_ID = 1
        PLAYER_STATUS_BUTTON_ID = 2
        GENRE_PANEL_ID = 3
        TAB_LIST_ID = 320

        def ignoresInput(self):
            return False

        def __init__(self, selected_mode, chain_host):
            self.tabList = FakeTabListContainer(selected_mode)
            self._chainHost = chain_host

    def test_library_click_delegates_to_the_hosts_switchTab(self):
        chainHost = self.FakeChainHost()
        host = self.FakeGenresHost('library', chainHost)

        genresOnClick(host, host.TAB_LIST_ID)

        self.assertEqual(1, len(chainHost.posts))
        post = chainHost.posts[0]
        self.assertEqual(chainHost.switchTab, post.function)
        self.assertEqual(('library',), post.args)
        self.assertEqual({'item_type': None}, post.kwargs)

    def test_library_click_threads_the_hosts_item_type_reset(self):
        """If ITEM_TYPE was left stuck on 'collection' from before Categories was entered, a
        Library-tab click from within Categories must reset it too, same as library.py's own
        TAB_LIST_ID branch - delegated here via the host's own _libraryTabItemType()."""
        chainHost = self.FakeChainHost(library_tab_item_type='movie')
        host = self.FakeGenresHost('library', chainHost)

        genresOnClick(host, host.TAB_LIST_ID)

        self.assertEqual({'item_type': 'movie'}, chainHost.posts[0].kwargs)

    def test_recommended_click_delegates_to_the_hosts_switchTab(self):
        chainHost = self.FakeChainHost(library_tab_item_type='movie')
        host = self.FakeGenresHost('recommended', chainHost)

        genresOnClick(host, host.TAB_LIST_ID)

        self.assertEqual(('recommended',), chainHost.posts[0].args)
        # Recommended never touches item type, even if Library's own reset would have fired.
        self.assertEqual({'item_type': None}, chainHost.posts[0].kwargs)

    def test_categories_click_is_a_noop_already_showing_it(self):
        chainHost = self.FakeChainHost()
        host = self.FakeGenresHost('categories', chainHost)

        genresOnClick(host, host.TAB_LIST_ID)

        self.assertEqual([], getattr(host._chainHost, "posts", []))

    def test_without_a_live_chain_host_does_nothing(self):
        """Defensive - browseGenres() always goes through a self-hosting LibraryWindow in
        practice, so _chainHost should never actually be None here, but this must not raise if
        it somehow is."""
        host = self.FakeGenresHost('library', None)

        genresOnClick(host, host.TAB_LIST_ID)

        self.assertEqual([], getattr(host._chainHost, "posts", []))
