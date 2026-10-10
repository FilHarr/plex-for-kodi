# coding=utf-8
"""
The show's screen (seasons) redrawn from the show fetched again (ShowWindow._refreshShow()): back
from playing it, its season counts and ticks and its Play/Resume episode stood as they were before
(the user, 2026-10-10); after the screensaver or sleep too (refreshAfterIdle(), via the host). An
artist's screen, a ShowWindow too, isn't.

Importing lib.windows.* starts lib.player's monitor thread unless abort_requested is set first.
"""

from __future__ import absolute_import

from unittest import mock

from kodienv import ENV

ENV.abort_requested = True
from lib.windows import subitems  # noqa: E402

from .base import KodiTestCase  # noqa: E402


class ShowRefreshTest(KodiTestCase):
    def setUp(self):
        super(ShowRefreshTest, self).setUp()
        win = self.win = subitems.ShowWindow.__new__(subitems.ShowWindow)
        win.initialized = True
        win.isExternal = False
        win.mediaItem = mock.Mock()
        win.playLabelResolvedFor = 'show'
        win.updateProperties = mock.Mock()
        win.fill = mock.Mock()
        patcher = mock.patch.object(subitems.plexapp.util.APP, 'nowplayingmanager', create=True)
        self.nowPlaying = patcher.start()
        self.addCleanup(patcher.stop)

    def test_the_show_fetched_again_and_redrawn(self):
        self.win._refreshShow('test')
        self.nowPlaying.waitForTimelines.assert_called_once_with(subitems.episodes.TIMELINE_WAIT)
        self.win.mediaItem.reload.assert_called_once_with(includeExtras=1, includeExtrasCount=10, includeOnDeck=1)
        self.assertIsNone(self.win.playLabelResolvedFor)
        self.win.updateProperties.assert_called_once_with()
        self.win.fill.assert_called_once_with(update=True)

    def test_not_before_it_has_opened_nor_for_a_show_from_outside_the_library(self):
        for attr, value in (('initialized', False), ('isExternal', True)):
            self.win.initialized, self.win.isExternal = True, False
            setattr(self.win, attr, value)
            self.win._refreshShow('test')
        self.win.mediaItem.reload.assert_not_called()

    def test_a_show_that_did_not_reload_stands(self):
        self.win.mediaItem.reload.side_effect = Exception('no answer')
        self.win._refreshShow('test')
        self.win.fill.assert_not_called()

    def test_after_idle_not_while_a_video_plays(self):
        import xbmc
        xbmc.Player.playing_video = True
        try:
            self.win.refreshAfterIdle('screensaver')
        finally:
            xbmc.Player.playing_video = False
        self.win.mediaItem.reload.assert_not_called()
        self.win.refreshAfterIdle('screensaver')
        self.win.mediaItem.reload.assert_called_once_with(includeExtras=1, includeExtrasCount=10, includeOnDeck=1)

    def test_an_artists_screen_is_left(self):
        artist = subitems.ArtistWindow.__new__(subitems.ArtistWindow)
        artist.__dict__.update(self.win.__dict__)
        artist.refreshAfterIdle('wake')
        artist.mediaItem.reload.assert_not_called()
