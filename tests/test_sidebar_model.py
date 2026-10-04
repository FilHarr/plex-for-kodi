# coding=utf-8
"""
The one sidebar builder (windowutils.SidebarMixin.buildSectionList(), sidebar_model.py) that
replaced ten copies: its entries and their order, each screen's highlight rule, the server and
user labels, and the cached Playlists check that keeps a query off the main thread.

Importing lib.windows.windowutils starts lib.player's monitor thread unless abort_requested is set
first - same guard the other lib.windows.* tests use for the same reason.
"""

from __future__ import absolute_import

from unittest import mock

from kodienv import ENV

ENV.abort_requested = True
from lib.windows import genres, home, library, person, playlist, sidebar_model, windowutils  # noqa: E402

from .base import KodiTestCase  # noqa: E402


class Section(object):
    def __init__(self, key, title, type_='movie', library_id=None):
        self.key = key
        self.title = title
        self.type = type_
        self._libraryId = library_id

    def getLibrarySectionId(self):
        return self._libraryId

    def __repr__(self):
        return '<Section {0}>'.format(self.key)


MOVIES = Section('1', 'Movies')
TV = Section('2', 'TV Shows', 'show')
MUSIC = Section('3', 'Music', 'artist')


class Server(object):
    def __init__(self, uuid='server-uuid-0000aaaa', playlists=(), sections=(MOVIES, TV, MUSIC)):
        self.uuid = uuid
        self.name = 'Animal'
        self.offline = False
        self.suspect = False
        self.isSecure = True
        self.isLocal = False
        self._playlists = list(playlists)
        self._sections = list(sections)
        self.playlistQueries = 0
        self.library = mock.Mock()
        self.library.sections = lambda: list(self._sections)

    def playlists(self):
        self.playlistQueries += 1
        return list(self._playlists)


class FakeList(object):
    def __init__(self):
        self.items = []
        self.selected = None

    def reset(self):
        self.items = []

    def addItems(self, items):
        self.items.extend(items)

    def selectItem(self, pos):
        self.selected = pos


class Watchlist(Section):
    def has_data(self):
        return True


class SidebarCase(KodiTestCase):
    def setUp(self):
        super(SidebarCase, self).setUp()
        self.server = Server()
        self.settings = {}
        self.account = mock.Mock(title='Phil', username='phil', ID='1', thumb='', isOffline=False)
        self.account.safeUserThumb.return_value = 'avatar.png'
        manager = mock.Mock(selectedServer=self.server)
        self.watchlist = Watchlist('/library/sections/watchlist', 'Watchlist')
        self.startedChecks = []
        for patcher in (
                mock.patch.object(sidebar_model.plexapp, 'SERVERMANAGER', manager),
                mock.patch.object(sidebar_model.plexapp, 'ACCOUNT', self.account),
                mock.patch.object(sidebar_model.util, 'getSetting',
                                  lambda key, default=None: self.settings.get(key, default)),
                mock.patch.object(sidebar_model.util, 'getUserSetting', lambda key, default=None: default),
                mock.patch.object(home, 'watchlist_section', self.watchlist),
                mock.patch.object(sidebar_model.PlaylistsCheckTask, 'start',
                                  lambda task: self.startedChecks.append(task)),
                mock.patch.dict(sidebar_model._hasPlaylists, clear=True),
                mock.patch.object(sidebar_model, '_playlistsChecking', set())):
            patcher.start()
            self.addCleanup(patcher.stop)

    def navSettings(self, value):
        import json
        self.settings['home.settings.0000aaaa.1'] = json.dumps(value)

    def build(self, win):
        win.sectionList = FakeList()
        win.buildSectionList()
        return win.sectionList

    @staticmethod
    def labels(sectionList):
        return [mli.getLabel() for mli in sectionList.items]

    @staticmethod
    def active(sectionList):
        return [mli.getLabel() for mli in sectionList.items if mli.getProperty('is.active')]


class Shell(windowutils.SidebarMixin):
    """A drilled-into screen with the default rule (PrePlay, Episodes, Show, Album, Collection)."""

    def __init__(self, entrySectionId=None, entryFromWatchlist=False):
        self.entrySectionId = entrySectionId
        self.entryFromWatchlist = entryFromWatchlist
        self.props = {}

    def setProperty(self, key, value):
        self.props[key] = value


class EntriesTest(SidebarCase):
    def test_search_home_watchlist_then_libraries(self):
        self.assertEqual(['Search', 'Home', 'Watchlist', 'Movies', 'TV Shows', 'Music'],
                         self.labels(self.build(Shell())))

    def test_playlists_only_when_the_server_has_some(self):
        self.server._playlists = ['a playlist']
        self.assertIn('Playlists', self.labels(self.build(Shell())))

    def test_hidden_entries_are_dropped_and_the_order_kept(self):
        self.navSettings({'2': {'show': False}, '/library/sections/watchlist': {'show': False},
                          'order': ['3', '1']})
        self.assertEqual(['Search', 'Home', 'Music', 'Movies'], self.labels(self.build(Shell())))

    def test_items_carry_their_markers(self):
        self.server._playlists = ['a playlist']
        items = self.build(Shell()).items
        self.assertTrue(items[0].getProperty('is.search'))
        self.assertTrue(items[1].getProperty('is.home'))
        self.assertIs(home.home_section, items[1].dataSource)
        playlists = [mli for mli in items if mli.dataSource is home.playlists_section][0]
        self.assertTrue(playlists.getProperty('is.playlists'))
        self.assertTrue(all(mli.getProperty('item') for mli in items))


class HighlightTest(SidebarCase):
    def test_the_entry_section_is_highlighted_and_selected(self):
        sectionList = self.build(Shell(entrySectionId='2'))
        self.assertEqual(['TV Shows'], self.active(sectionList))
        self.assertEqual(4, sectionList.selected)

    def test_watchlist_only_when_no_section_matches(self):
        self.assertEqual(['Watchlist'], self.active(self.build(Shell(entrySectionId='watchlist',
                                                                     entryFromWatchlist=True))))
        self.assertEqual(['Movies'], self.active(self.build(Shell(entrySectionId='1', entryFromWatchlist=True))))

    def test_nothing_highlighted_without_an_entry_section(self):
        sectionList = self.build(Shell())
        self.assertEqual([], self.active(sectionList))
        self.assertIsNone(sectionList.selected)

    def test_a_person_follows_the_screen_the_role_came_from(self):
        win = person.PersonWindow.__new__(person.PersonWindow)
        win.sectionId, win.cameFromWatchlist = '3', False
        self.assertEqual(['Music'], self.active(self.build(win)))
        win.sectionId, win.cameFromWatchlist = None, True
        self.assertEqual(['Watchlist'], self.active(self.build(win)))

    def test_genres_follow_their_section(self):
        win = genres.GenreBrowserWindow.__new__(genres.GenreBrowserWindow)
        win.section = TV
        self.assertEqual(['TV Shows'], self.active(self.build(win)))

    def test_a_playlist_highlights_playlists(self):
        self.server._playlists = ['a playlist']
        win = playlist.PlaylistWindow.__new__(playlist.PlaylistWindow)
        self.assertEqual(['Playlists'], self.active(self.build(win)))


class LibraryHighlightTest(SidebarCase):
    def window(self, section, entrySectionId=None, entryFromWatchlist=False):
        win = library.LibraryWindow.__new__(library.LibraryWindow)
        win.section = section
        win.entrySectionId = entrySectionId
        win.entryFromWatchlist = entryFromWatchlist
        win.navSettings = {}
        return win

    def build(self, win):
        # LibraryWindow.buildSectionList() makes Watchlist afresh first; that's plex.tv's business
        with mock.patch.object(sidebar_model, 'refreshWatchlistSection'):
            return SidebarCase.build(self, win)

    def test_home(self):
        sectionList = self.build(self.window(home.home_section))
        self.assertEqual(['Home'], self.active(sectionList))
        self.assertEqual(1, sectionList.selected)

    def test_a_library(self):
        self.assertEqual(['TV Shows'], self.active(self.build(self.window(TV))))

    def test_a_collection_highlights_its_library(self):
        collection = Section('/library/collections/9', 'A collection', library_id='1')
        self.assertEqual(['Movies'], self.active(self.build(self.window(collection))))

    def test_an_entry_section_wins_over_the_collections_library(self):
        collection = Section('/library/collections/9', 'A collection', library_id='1')
        self.assertEqual(['Music'], self.active(self.build(self.window(collection, entrySectionId='3'))))

    def test_watchlist_when_entered_from_it(self):
        collection = Section('/library/collections/9', 'A collection')
        self.assertEqual(['Watchlist'], self.active(self.build(self.window(collection, entryFromWatchlist=True))))

    def test_its_own_nav_settings_are_used(self):
        win = self.window(home.home_section)
        win.navSettings = {'1': {'show': False}}
        self.assertNotIn('Movies', self.labels(self.build(win)))


class PlaylistsCheckTest(SidebarCase):
    def test_first_build_asks_then_the_answer_is_reused_and_checked_off_the_main_thread(self):
        self.server._playlists = ['a playlist']
        self.assertTrue(sidebar_model.hasPlaylists(self.server))
        self.assertEqual(1, self.server.playlistQueries)
        self.assertEqual([], self.startedChecks)

        self.assertTrue(sidebar_model.hasPlaylists(self.server))
        self.assertEqual(1, self.server.playlistQueries)
        self.assertEqual(1, len(self.startedChecks))

    def test_a_changed_answer_calls_back_once(self):
        changed = []
        sidebar_model.hasPlaylists(self.server)
        sidebar_model.hasPlaylists(self.server, onChange=lambda: changed.append(1))
        self.server._playlists = ['a new playlist']
        self.startedChecks[0].run()
        self.assertEqual([1], changed)
        self.assertTrue(sidebar_model.hasPlaylists(self.server))

    def test_no_call_back_when_unchanged(self):
        changed = []
        sidebar_model.hasPlaylists(self.server)
        sidebar_model.hasPlaylists(self.server, onChange=lambda: changed.append(1))
        self.startedChecks[0].run()
        self.assertEqual([], changed)

    def test_one_check_at_a_time_per_server(self):
        sidebar_model.hasPlaylists(self.server)
        sidebar_model.hasPlaylists(self.server)
        sidebar_model.hasPlaylists(self.server)
        self.assertEqual(1, len(self.startedChecks))
        self.startedChecks[0].run()
        sidebar_model.hasPlaylists(self.server)
        self.assertEqual(2, len(self.startedChecks))

    def test_an_offline_server_is_not_asked(self):
        self.server.offline = True
        self.assertFalse(sidebar_model.hasPlaylists(self.server))
        self.assertEqual(0, self.server.playlistQueries)

    def test_a_failed_answer_is_not_remembered(self):
        def fails():
            self.server.suspect = True
            return None
        self.server.playlists = fails
        sidebar_model.hasPlaylists(self.server)
        self.assertNotIn(self.server.uuid, sidebar_model._hasPlaylists)

    def test_the_playlists_view_answer_is_remembered(self):
        sidebar_model.notePlaylists(self.server, ['a playlist'])
        self.assertTrue(sidebar_model.hasPlaylists(self.server))
        self.assertEqual(0, self.server.playlistQueries)


class ServerAndUserTest(SidebarCase):
    def test_labels(self):
        win = Shell()
        win.displayServerAndUser()
        self.assertEqual({'user.name': 'Phil', 'user.avatar': 'avatar.png', 'user.avatar.letter': 'P',
                          'server.name': 'Animal', 'server.icon': 'script.plex/home/device/plex.png',
                          'server.iconmod': 'script.plex/home/device/lock.png', 'server.iconmod2': ''},
                         win.props)

    def test_an_offline_server_shows_the_error_icon_on_every_screen(self):
        self.server.offline = True
        win = Shell()
        win.displayServerAndUser()
        self.assertEqual('script.plex/home/device/error.png', win.props['server.icon'])
