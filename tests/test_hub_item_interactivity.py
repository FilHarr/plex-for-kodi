# coding=utf-8
"""
lib/windows/library.py's LibraryWindow.hubItemClicked() - quiet-orbiting-heron.md item 10, Group B
(the "click-time behavior" gaps ported from HomeWindow.hubItemClicked(), home.py): in-progress
auto-resume and season/episode -> show redirection for discover/watchlist hub items. Both are pure
decisions (a setting/type/flag check feeding into what gets passed to opener.open()) extractable
without constructing a real LibraryWindow - the real, bound hubItemClicked() is called directly
against a lightweight FakeLibraryWindow double instead, same style test_search_context.py/
test_opener_context.py use for their own real-method/opener call-routing tests.

Hub-becomes-empty cleanup (Group B's third piece) and Group A's rotation-ring/pagination/
wraparound/reselect-position machinery are not covered here - both are native-window/control-list
dependent (isLastItem()/getManagedItemPosition()/waitFor()-driven selection), same "live-verified
only" boundary this codebase already draws for the rest of the rotation-ring engine (D2/item 11).

Importing lib.windows.library starts lib.player's monitor thread unless abort_requested is set
first - same guard the other lib.windows.* tests use for the same reason.
"""

from __future__ import absolute_import

from kodienv import ENV

ENV.abort_requested = True
from lib.windows import library  # noqa: E402

from .base import KodiTestCase  # noqa: E402


class FakeShow(object):
    TYPE = 'show'


class FakeHubDataSource(object):
    def __init__(self, type_, in_progress=False, is_watchlist=False, show=None, rating_key=1):
        self.TYPE = type_
        self.in_progress = in_progress
        self.is_watchlist = is_watchlist
        self.ratingKey = rating_key
        self._show = show

    def show(self):
        return self._show

    def exists(self, force_full_check=False):
        # Keep hubItemClicked()'s empty-hub cleanup branch inert - out of scope here (see module
        # docstring), it's not what these tests are checking.
        return True


class FakeManagedListItem(object):
    def __init__(self, data_source):
        self.dataSource = data_source

    def pos(self):
        return 0


class FakeHubControl(object):
    def __init__(self, selected_item):
        self._selected = selected_item
        self.dataSource = 'fake-hub'

    def getSelectedItem(self):
        return self._selected

    def size(self):
        return 1

    def removeItem(self, index):
        pass


class FakeSection(object):
    TYPE = 'movie'


class FakeLibraryWindow(object):
    """Carries only the attributes/constants the real, bound hubItemClicked() (imported directly
    off library.LibraryWindow below) actually touches - not a real LibraryWindow instance."""

    hubItemClicked = library.LibraryWindow.hubItemClicked
    carriedProps = library.LibraryWindow.carriedProps
    _hubIsMusic = library.LibraryWindow._hubIsMusic
    MUSIC_ITEM_TYPES = library.LibraryWindow.MUSIC_ITEM_TYPES
    _anchorControlId = library.LibraryWindow._anchorControlId
    # HUB_CONTROL_ID lives on RecommendedWindow (the template-backed content shell), not
    # LibraryWindow itself - a real LibraryWindow instance resolves self.HUB_CONTROL_ID via
    # MultiWindow.__getattr__ delegation to self._current (a live RecommendedWindow) while the
    # 'recommended' tab is showing. HUB_ROTATION_RING is a real LibraryWindow class attribute.
    HUB_CONTROL_ID = library.RecommendedWindow.HUB_CONTROL_ID
    HUB_ROTATION_RING = library.LibraryWindow.HUB_ROTATION_RING

    def __init__(self, control):
        self.hubControls = [control]
        self._anchorRingPos = self.HUB_ROTATION_RING.index(self.HUB_CONTROL_ID)
        self.entrySectionId = None
        self.entryFromWatchlist = False
        self.section = FakeSection()
        self.visibleHubs = []
        self.focusedHubIndex = 0
        self.processedCommands = []

    def processCommand(self, command):
        self.processedCommands.append(command)


class HubItemClickedRedirectionTest(KodiTestCase):
    """Season/episode -> show redirection for discover/watchlist hub items (Group B item 2)."""

    def test_watchlist_episode_redirects_to_its_show(self):
        show = FakeShow()
        episode = FakeHubDataSource('episode', is_watchlist=True, show=show)
        control = FakeHubControl(FakeManagedListItem(episode))
        window = FakeLibraryWindow(control)

        opened = []
        original_open = library.opener.open
        library.opener.open = lambda obj, **kwargs: opened.append((obj, kwargs)) or ''
        try:
            window.hubItemClicked(window.HUB_CONTROL_ID)
        finally:
            library.opener.open = original_open

        self.assertEqual(1, len(opened))
        self.assertIs(show, opened[0][0])

    def test_non_watchlist_episode_opens_itself(self):
        episode = FakeHubDataSource('episode', is_watchlist=False)
        control = FakeHubControl(FakeManagedListItem(episode))
        window = FakeLibraryWindow(control)

        opened = []
        original_open = library.opener.open
        library.opener.open = lambda obj, **kwargs: opened.append((obj, kwargs)) or ''
        try:
            window.hubItemClicked(window.HUB_CONTROL_ID)
        finally:
            library.opener.open = original_open

        self.assertEqual(1, len(opened))
        self.assertIs(episode, opened[0][0])

    def test_watchlist_movie_is_not_redirected(self):
        # is_watchlist redirection only applies to season/episode - a watchlist movie should
        # still open itself.
        movie = FakeHubDataSource('movie', is_watchlist=True)
        control = FakeHubControl(FakeManagedListItem(movie))
        window = FakeLibraryWindow(control)

        opened = []
        original_open = library.opener.open
        library.opener.open = lambda obj, **kwargs: opened.append((obj, kwargs)) or ''
        try:
            window.hubItemClicked(window.HUB_CONTROL_ID)
        finally:
            library.opener.open = original_open

        self.assertEqual(1, len(opened))
        self.assertIs(movie, opened[0][0])


class HubItemClickedAutoResumeTest(KodiTestCase):
    """In-progress auto-resume (Group B item 1, home_inprogress_resume setting)."""

    def _clickWithSetting(self, data_source, setting_value):
        control = FakeHubControl(FakeManagedListItem(data_source))
        window = FakeLibraryWindow(control)

        opened = []
        original_open = library.opener.open
        original_get_setting = library.util.getSetting
        library.opener.open = lambda obj, **kwargs: opened.append((obj, kwargs)) or ''
        library.util.getSetting = lambda key, *a, **kw: (
            setting_value if key == 'home_inprogress_resume' else original_get_setting(key, *a, **kw))
        try:
            window.hubItemClicked(window.HUB_CONTROL_ID)
        finally:
            library.opener.open = original_open
            library.util.getSetting = original_get_setting

        self.assertEqual(1, len(opened))
        return opened[0][1]

    def test_in_progress_episode_with_setting_enabled_auto_plays(self):
        episode = FakeHubDataSource('episode', in_progress=True)
        kwargs = self._clickWithSetting(episode, True)
        self.assertTrue(kwargs['auto_play'])

    def test_auto_play_bypasses_context_so_handleOpen_actually_sees_it(self):
        # Regression guard: every context-aware opener.py *Clicked() branch checks
        # `if context is not None` BEFORE looking at auto_play at all, routing straight to
        # context.openWindow() - which never consults auto_play. Passing context=self here
        # unconditionally silently drops auto-resume (live-confirmed). context must be None
        # whenever auto_play is True, so opener.open() actually reaches handleOpen()'s own
        # auto_play handling.
        episode = FakeHubDataSource('episode', in_progress=True)
        kwargs = self._clickWithSetting(episode, True)
        self.assertTrue(kwargs['auto_play'])
        self.assertIsNone(kwargs['context'])

    def test_in_progress_movie_with_setting_disabled_does_not_auto_play(self):
        movie = FakeHubDataSource('movie', in_progress=True)
        kwargs = self._clickWithSetting(movie, False)
        self.assertFalse(kwargs['auto_play'])

    def test_not_auto_playing_keeps_context_for_chain_hosting(self):
        # The normal (non-auto-play) click path must still pass context=self through, so
        # chain-aware types keep swapping in place instead of opening a second real window.
        movie = FakeHubDataSource('movie', in_progress=False)
        kwargs = self._clickWithSetting(movie, False)
        self.assertFalse(kwargs['auto_play'])
        self.assertIsNotNone(kwargs['context'])

    def test_in_progress_show_type_never_auto_plays(self):
        # home_inprogress_resume only applies to episode/movie - a show-type hub item (e.g. a
        # season/show surfaced directly) should never auto-play even with the setting on.
        show = FakeHubDataSource('show', in_progress=True)
        kwargs = self._clickWithSetting(show, True)
        self.assertFalse(kwargs['auto_play'])

    def test_not_in_progress_does_not_auto_play_even_with_setting_enabled(self):
        episode = FakeHubDataSource('episode', in_progress=False)
        kwargs = self._clickWithSetting(episode, True)
        self.assertFalse(kwargs['auto_play'])
