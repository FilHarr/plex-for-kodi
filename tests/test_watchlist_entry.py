# coding=utf-8
"""
Watchlist's sidebar entry follows the setting and the pin (the user, 2026-10-05), not plex.tv: the
section is made without asking plex.tv for anything, and an empty Watchlist, or plex.tv not
answering just then (live 2026-10-05: a 429 rate limit at startup), no longer leaves it out of the
sidebar. The screen asks for the items when it's opened.

Importing lib.windows.* starts lib.player's monitor thread unless abort_requested is set first.
"""

from __future__ import absolute_import

from unittest import mock

from kodienv import ENV

ENV.abort_requested = True
from lib.windows import home, sidebar_model  # noqa: E402
from plexnet import plexlibrary  # noqa: E402

from .base import KodiTestCase  # noqa: E402
from .test_sidebar_model import SidebarCase, Shell  # noqa: E402


class SectionTest(KodiTestCase):
    def test_made_without_asking_plex_tv(self):
        discover = mock.Mock()
        section = plexlibrary.WatchlistSection(None, server=discover)
        discover.query.assert_not_called()
        self.assertIs(discover, section.server)
        self.assertEqual('/library/sections/watchlist', section.key)
        self.assertEqual('movies_shows', section.TYPE)

    def test_the_sidebar_makes_one_while_the_setting_is_on(self):
        account = mock.Mock(isOffline=False)
        with mock.patch.object(sidebar_model.plexapp, 'ACCOUNT', account), \
                mock.patch.object(sidebar_model.plexapp, 'SERVERMANAGER', mock.Mock()), \
                mock.patch.object(sidebar_model.util, 'getUserSetting', lambda key, default=None: default), \
                mock.patch.object(home, 'watchlist_section', None):
            sidebar_model.refreshWatchlistSection()
            self.assertIsInstance(home.watchlist_section, plexlibrary.WatchlistSection)


class EmptyWatchlist(object):
    """A Watchlist with nothing in it: the sidebar never asks."""
    key = '/library/sections/watchlist'
    title = 'Watchlist'
    TYPE = 'movies_shows'
    type = 'mixed'
    server = None

    def has_data(self):
        raise AssertionError('the sidebar asked plex.tv whether the Watchlist has anything in it')


class SidebarEntryTest(SidebarCase):
    def test_an_empty_watchlist_is_still_in_the_sidebar(self):
        self.store('watchlist', '1')
        with mock.patch.object(home, 'watchlist_section', EmptyWatchlist()):
            self.assertEqual(['Search', 'Home', 'Watchlist', 'Movies'], self.labels(self.build(Shell())))
