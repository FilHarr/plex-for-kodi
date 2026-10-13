# coding=utf-8
"""
Back on a library grid from playback started by its Play or Shuffle: the tiles it played are read
again and updated in place (LibraryWindow._updateGridAfterPlayback()). Filled again, every tile went
to its placeholder and back (AM6B, 2026-10-13). A grid sorted or filtered by watching is still filled
again: playback can move its tiles or drop them.

Importing lib.windows.* starts lib.player's monitor thread unless abort_requested is set first.
"""

from __future__ import absolute_import

from unittest import mock

from kodienv import ENV

ENV.abort_requested = True
from lib.windows import library  # noqa: E402
from plexnet import plexobjects  # noqa: E402

from .base import KodiTestCase  # noqa: E402


def video(type_, key, show=None):
    v = mock.Mock(type=plexobjects.PlexValue(type_), ratingKey=plexobjects.PlexValue(key))
    v.get = lambda field: plexobjects.PlexValue(show or '') if field == 'grandparentRatingKey' else ''
    return v


def tile(key):
    return mock.Mock(dataSource=mock.Mock(ratingKey=plexobjects.PlexValue(key)))


class GridAfterPlaybackTest(KodiTestCase):
    def setUp(self):
        super(GridAfterPlaybackTest, self).setUp()
        win = self.win = library.LibraryWindow.__new__(library.LibraryWindow)
        win.sort = 'titleSort'
        win.boolFilters = {}
        win.closing = False
        win._listGeneration = 3
        self.tiles = [tile('10'), tile('20'), tile('30')]
        win.showPanelControl = self.tiles
        win.showWatchState = mock.Mock()
        win.postUI = lambda name, fn, args=(), kwargs=None: fn(*args)
        win._refillGridAfterPlayback = mock.Mock(return_value=None)
        patches = [mock.patch.object(library.player.PLAYER, 'off'),
                   mock.patch.object(library.plexapp.util.APP, 'nowplayingmanager', create=True),
                   mock.patch.object(library.threading, 'Thread',
                                     side_effect=lambda target, name: mock.Mock(start=target))]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

    def played(self, *videos):
        for v in videos:
            self.win._onGridPlaybackVideo(video=v)

    def test_a_film_names_its_own_tile_an_episode_its_shows(self):
        self.played(video('movie', '10'), video('episode', '99', show='30'))
        self.assertEqual({'10', '30'}, self.win._playedTileKeys)

    def test_the_tiles_played_are_read_again_and_shown(self):
        self.played(video('movie', '10'), video('movie', '30'))
        self.assertIsNone(self.win._updateGridAfterPlayback())
        self.tiles[0].dataSource.reload.assert_called_once_with()
        self.tiles[1].dataSource.reload.assert_not_called()
        self.assertEqual([self.tiles[0], self.tiles[2]], [c[0][0] for c in self.win.showWatchState.call_args_list])
        self.win._refillGridAfterPlayback.assert_not_called()

    def test_a_grid_sorted_by_watching_is_filled_again(self):
        self.win.sort = 'lastViewedAt'
        self.played(video('movie', '10'))
        self.win._updateGridAfterPlayback()
        self.win._refillGridAfterPlayback.assert_called_once_with()
        self.win.showWatchState.assert_not_called()

    def test_an_unplayed_filter_is_filled_again(self):
        self.win.boolFilters = {'unwatched': True}
        self.played(video('movie', '10'))
        self.win._updateGridAfterPlayback()
        self.win._refillGridAfterPlayback.assert_called_once_with()

    def test_a_grid_rebuilt_meanwhile_is_left_alone(self):
        self.played(video('movie', '10'))

        def rebuilt(name, fn, args=(), kwargs=None):
            self.win._listGeneration += 1
            fn(*args)
        self.win.postUI = rebuilt
        self.win._updateGridAfterPlayback()
        self.win.showWatchState.assert_not_called()

    def test_stops_listening_on_return(self):
        self.played(video('movie', '10'))
        self.win._updateGridAfterPlayback()
        library.player.PLAYER.off.assert_called_once_with('new.video', self.win._onGridPlaybackVideo)
