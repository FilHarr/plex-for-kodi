# coding=utf-8
"""
The "Categories" tab follow-up to hashed-orbiting-pizza.md: lib/windows/genres.py's
GenreBrowserWindow is promoted from a dropdown-only, always-standalone window to a genuine third
tab (Recommended/Library/Categories) in LibraryWindow's own tab row, hosted the same way the seven
original shells are (swapTo()), for section.TYPE in ('movie', 'show') only.

Three pieces get their own coverage here, each narrow (matching test_library_chain.py's own
"deliberately narrow" philosophy for onAction()/onClick()-style dispatch tests):

1. library.py's buildTabList() only adds the Categories item for movie/show sections.
2. library.py's onClick() TAB_LIST_ID branch dispatches to browseGenres() (deferred) for the
   categories item, switchTab() (deferred) for everything else - unchanged from before.
3. genres.py's own onClick() TAB_LIST_ID branch (new - GenreBrowserWindow had no tab-list handling
   at all before this) delegates a Library/Recommended click to self._chainHost.switchTab()
   (deferred), and does nothing for a categories click (already showing it) or when un-hosted.

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


class FakeTimer(object):
    """Stand-in for threading.Timer - records construction/start instead of actually deferring,
    same shape test_library_chain.py's own FakeTimer uses (kept local here rather than shared,
    per this file's self-contained-fakes convention)."""
    instances = []

    def __init__(self, interval, function, args=None, kwargs=None):
        self.interval = interval
        self.function = function
        self.args = args or ()
        self.kwargs = kwargs or {}
        self.started = False
        FakeTimer.instances.append(self)

    def start(self):
        self.started = True


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


buildTabList = library.LibraryWindow.buildTabList
libraryOnClick = library.LibraryWindow.onClick
genresOnClick = genres.GenreBrowserWindow.onClick
tabListNeedsRebuild = library.LibraryWindow._tabListNeedsRebuild


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


class BuildTabListCategoriesGatingTest(KodiTestCase):
    class FakeHost(object):
        def __init__(self, section_type):
            self.section = FakeSection(section_type)
            self._tabListIsPlaylists = False
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


class LibraryOnClickTabDispatchTest(KodiTestCase):
    class FakeHost(object):
        SECTION_LIST_ID = 1  # distinct from TAB_LIST_ID, never matched in these tests
        TAB_LIST_ID = 320

        def __init__(self, selected_mode, is_playlists=False):
            self.tabList = FakeTabListContainer(selected_mode)
            self._tabListIsPlaylists = is_playlists
            self.movingSection = False

        def browseGenres(self):
            pass

        def switchTab(self, mode):
            pass

    def setUp(self):
        FakeTimer.instances = []
        self._originalTimer = library.threading.Timer
        library.threading.Timer = FakeTimer

    def tearDown(self):
        library.threading.Timer = self._originalTimer

    def test_categories_click_defers_to_browseGenres(self):
        host = self.FakeHost('categories')

        libraryOnClick(host, host.TAB_LIST_ID)

        self.assertEqual(1, len(FakeTimer.instances))
        timer = FakeTimer.instances[0]
        self.assertEqual(host.browseGenres, timer.function)
        self.assertTrue(timer.started)

    def test_library_click_defers_to_switchTab_unchanged(self):
        host = self.FakeHost('library')

        libraryOnClick(host, host.TAB_LIST_ID)

        self.assertEqual(1, len(FakeTimer.instances))
        timer = FakeTimer.instances[0]
        self.assertEqual(host.switchTab, timer.function)
        self.assertEqual(('library',), timer.args)


class GenresOnClickDelegationTest(KodiTestCase):
    class FakeChainHost(object):
        def __init__(self):
            self.switchTab = self._switchTab
            self.switchTabCalls = []

        def _switchTab(self, mode):
            self.switchTabCalls.append(mode)

    class FakeGenresHost(object):
        SECTION_LIST_ID = 1
        PLAYER_STATUS_BUTTON_ID = 2
        GENRE_PANEL_ID = 3
        TAB_LIST_ID = 320

        def __init__(self, selected_mode, chain_host):
            self.tabList = FakeTabListContainer(selected_mode)
            self._chainHost = chain_host

    def setUp(self):
        FakeTimer.instances = []
        self._originalTimer = genres.threading.Timer
        genres.threading.Timer = FakeTimer

    def tearDown(self):
        genres.threading.Timer = self._originalTimer

    def test_library_click_delegates_to_the_hosts_switchTab(self):
        chainHost = self.FakeChainHost()
        host = self.FakeGenresHost('library', chainHost)

        genresOnClick(host, host.TAB_LIST_ID)

        self.assertEqual(1, len(FakeTimer.instances))
        timer = FakeTimer.instances[0]
        self.assertEqual(chainHost.switchTab, timer.function)
        self.assertEqual(('library',), timer.args)
        self.assertTrue(timer.started)

    def test_recommended_click_delegates_to_the_hosts_switchTab(self):
        chainHost = self.FakeChainHost()
        host = self.FakeGenresHost('recommended', chainHost)

        genresOnClick(host, host.TAB_LIST_ID)

        self.assertEqual(('recommended',), FakeTimer.instances[0].args)

    def test_categories_click_is_a_noop_already_showing_it(self):
        chainHost = self.FakeChainHost()
        host = self.FakeGenresHost('categories', chainHost)

        genresOnClick(host, host.TAB_LIST_ID)

        self.assertEqual([], FakeTimer.instances)

    def test_without_a_live_chain_host_does_nothing(self):
        """Defensive - browseGenres() always goes through a self-hosting LibraryWindow in
        practice, so _chainHost should never actually be None here, but this must not raise if
        it somehow is."""
        host = self.FakeGenresHost('library', None)

        genresOnClick(host, host.TAB_LIST_ID)

        self.assertEqual([], FakeTimer.instances)
