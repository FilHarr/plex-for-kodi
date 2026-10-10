# coding=utf-8
"""
Episodes added to a season while away - watching one of its episodes, or with the screensaver up or
the box asleep - reach its list: the season reloaded, and the list built again when its episode
count has moved (EpisodesWindow._rebuildEpisodeListIfStale()). The paginator only ever reached
as far as the count it was built with, so new ones at the end couldn't be scrolled to, and the pick
after playback couldn't land on them (the user, 2026-10-10). The screensaver, display and wake
refreshes reach the screen through its host (LibraryWindow.refreshAfterIdle()).

Importing lib.windows.* starts lib.player's monitor thread unless abort_requested is set first.
"""

from __future__ import absolute_import

from unittest import mock

from kodienv import ENV

ENV.abort_requested = True
from lib.windows import episodes, library  # noqa: E402

from .base import KodiTestCase  # noqa: E402


class Episode(object):
    def __init__(self, ratingKey):
        self.ratingKey = ratingKey


class Item(object):
    def __init__(self, episode=None, card=False, more=False):
        self.dataSource = episode
        self.props = {'is.season.card': '1'} if card else {}
        if more:
            # the paginator's right boundary marker: more episodes to page in
            self.props.update({'is.boundary': '1', 'right.boundary': '1'})

    def getProperty(self, key):
        return self.props.get(key, '')


class EpisodeList(list):
    """The episodes row: its items, which is selected, and what was selected since."""
    selected = None

    def getSelectedItem(self):
        return self.selected

    def selectItem(self, pos):
        self.selected = self[pos]


class RebuildTest(KodiTestCase):
    def setUp(self):
        super(RebuildTest, self).setUp()
        win = self.win = episodes.EpisodesWindow.__new__(episodes.EpisodesWindow)
        win.closing = False
        win.season = mock.Mock(leafCount='10')
        win.episodesPaginator = self.paginator = mock.Mock(leafCount=10, centerEpisode=None)
        win.tasks = mock.Mock()
        self.e3, self.e4 = Episode('3'), Episode('4')
        win.episodeListControl = self.list = EpisodeList([Item(card=True), Item(self.e3), Item(self.e4)])
        self.list.selected = self.list[2]
        win.fillEpisodes = mock.Mock()

    def test_the_same_count_nothing_rebuilt(self):
        self.assertFalse(self.win._rebuildEpisodeListIfStale('test'))
        self.win.season.reload.assert_called_once_with(**episodes.VIDEO_RELOAD_KW)
        self.win.fillEpisodes.assert_not_called()

    def test_a_new_count_the_list_built_again_around_the_selected_episode(self):
        self.win.season.leafCount = '12'
        self.assertTrue(self.win._rebuildEpisodeListIfStale('test'))
        self.paginator.reset.assert_called_once_with()
        self.assertEqual(12, self.paginator.leafCount)
        self.assertIs(self.e4, self.paginator.centerEpisode)
        self.win.tasks.cancel.assert_called_once_with()
        self.win.fillEpisodes.assert_called_once_with(update=True)

    def test_back_from_playback_around_the_episode_played(self):
        self.win.season.leafCount = '12'
        played = Episode('9')
        self.win._rebuildEpisodeListIfStale('test', center=played)
        self.assertIs(played, self.paginator.centerEpisode)

    def test_on_the_season_card_from_the_start(self):
        self.win.season.leafCount = '12'
        self.list.selected = self.list[0]
        self.win._rebuildEpisodeListIfStale('test')
        self.assertIs(False, self.paginator.centerEpisode)

    def test_the_selection_kept_wherever_it_lands(self):
        self.win.season.leafCount = '12'
        rebuilt = [Item(Episode('2')), Item(Episode('3')), Item(Episode('4')), Item(Episode('5'))]

        def fill(update=False):
            self.list[:] = rebuilt
            self.list.selected = rebuilt[0]
        self.win.fillEpisodes.side_effect = fill
        self.win._rebuildEpisodeListIfStale('test', keep_selection=True)
        self.assertIs(rebuilt[2], self.list.selected)

    def test_the_episode_after_the_last_played_not_loaded_the_list_built_again_around_it(self):
        """Autoplay ran past the page loaded around where Play was pressed: the pick stayed there."""
        self.list.append(Item(more=True))
        self.assertTrue(self.win._rebuildEpisodeListIfStale('test', center=self.e4, need_after=self.e4))
        self.assertIs(self.e4, self.paginator.centerEpisode)
        self.win.fillEpisodes.assert_called_once_with(update=True)

    def test_the_last_played_not_loaded_at_all_the_same(self):
        played = Episode('30')
        self.assertTrue(self.win._rebuildEpisodeListIfStale('test', center=played, need_after=played))

    def test_the_episode_after_loaded_nothing_rebuilt(self):
        self.assertFalse(self.win._rebuildEpisodeListIfStale('test', center=self.e3, need_after=self.e3))
        self.win.fillEpisodes.assert_not_called()

    def test_the_seasons_last_episode_nothing_rebuilt(self):
        self.assertFalse(self.win._rebuildEpisodeListIfStale('test', center=self.e4, need_after=self.e4))
        self.win.fillEpisodes.assert_not_called()

    def test_a_season_that_did_not_reload_is_left(self):
        self.win.season.reload.side_effect = Exception('no answer')
        self.assertFalse(self.win._rebuildEpisodeListIfStale('test'))
        self.win.fillEpisodes.assert_not_called()


class Screen(object):
    """A hosted screen with its own refresh after idle."""
    def __init__(self):
        self.reasons = []

    def refreshAfterIdle(self, reason):
        self.reasons.append(reason)


class HostRoutingTest(KodiTestCase):
    def setUp(self):
        super(HostRoutingTest, self).setUp()
        win = self.win = library.LibraryWindow.__new__(library.LibraryWindow)
        win._isHostedShell = False
        win._current = None
        win.refreshHubsInPlace = mock.Mock()

    def test_the_rows_when_no_screen_is_open(self):
        self.win.refreshAfterIdle('screensaver')
        self.win.refreshHubsInPlace.assert_called_once_with('screensaver')

    def test_a_screen_with_its_own_refresh_has_it(self):
        self.win._isHostedShell, self.win._current = True, Screen()
        self.win.refreshAfterIdle('wake')
        self.assertEqual(['wake'], self.win._current.reasons)
        self.win.refreshHubsInPlace.assert_not_called()

    def test_a_screen_without_one_is_left(self):
        self.win._isHostedShell, self.win._current = True, object()
        self.win.refreshAfterIdle('display')
        self.win.refreshHubsInPlace.assert_not_called()


class ProgressSeasonKeyTest(KodiTestCase):
    """The player files progress under each episode's season; a skipChildren show's screen has the
    show as its season, and looked progress up under the show's key - never found, so back from
    playback the server wasn't asked what was watched and the episode just finished stayed selected
    (the user, 2026-10-10)."""

    def setUp(self):
        super(ProgressSeasonKeyTest, self).setUp()
        self.win = episodes.EpisodesWindow.__new__(episodes.EpisodesWindow)
        self.win.show_ = mock.Mock(ratingKey='1402')
        episode = Episode('1405')
        episode.parentRatingKey = '1403'
        self.win.episodeListControl = EpisodeList([Item(card=True), Item(episode)])

    def tearDown(self):
        episodes.VIDEO_PROGRESS.clear()
        super(ProgressSeasonKeyTest, self).tearDown()

    def test_a_season_its_own_key(self):
        self.win.season = mock.Mock(ratingKey='1403')
        self.assertEqual('1403', self.win._progressSeasonKey())

    def test_a_skipchildren_show_the_season_its_episodes_are_in(self):
        self.win.season = self.win.show_
        self.assertEqual('1403', self.win._progressSeasonKey())

    def test_no_list_yet_the_one_season_progress_was_filed_under(self):
        self.win.season = self.win.show_
        self.win.episodeListControl = None
        episodes.VIDEO_PROGRESS['1402'] = {'1403': {'1405': True}}
        self.assertEqual('1403', self.win._progressSeasonKey())
