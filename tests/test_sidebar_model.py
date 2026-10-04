# coding=utf-8
"""
The one sidebar builder (windowutils.SidebarMixin.buildSectionList(), sidebar_model.py) that
replaced ten copies: its entries and their order, each screen's highlight rule, the server and
user labels, and the cached Playlists check that keeps a query off the main thread. Since the
sidebar became the libraries picked from any server: the stored list, its migration from the
show/hide setting, placeholders for libraries a server hasn't listed yet, and the picker's ticks.

Importing lib.windows.windowutils starts lib.player's monitor thread unless abort_requested is set
first - same guard the other lib.windows.* tests use for the same reason.
"""

from __future__ import absolute_import

import json
from unittest import mock

from kodienv import ENV

ENV.abort_requested = True
from lib.windows import genres, home, library, person, playlist, section_ids, sidebar_model, windowutils  # noqa: E402

from .base import KodiTestCase  # noqa: E402


UUID = 'server-uuid-0000aaaa'
OTHER = 'other-uuid-0000bbbb'


def fakeServer(uuid, name):
    server = mock.Mock(uuid=uuid, offline=False)
    server.name = name
    return server


ANIMAL = fakeServer(UUID, 'Animal')
OSCAR = fakeServer(OTHER, 'Oscar')


class Section(object):
    server = ANIMAL

    def __init__(self, key, title, type_='movie', library_id=None, server=None):
        self.key = key
        self.title = title
        self.type = type_
        self._libraryId = library_id
        if server is not None:
            self.server = server

    def getLibrarySectionId(self):
        return self._libraryId

    def __repr__(self):
        return '<Section {0}>'.format(self.key)


MOVIES = Section('1', 'Movies')
TV = Section('2', 'TV Shows', 'show')
MUSIC = Section('3', 'Music', 'artist')


class Server(object):
    def __init__(self, uuid=UUID, playlists=()):
        self.uuid = uuid
        self.name = 'Animal'
        self.offline = False
        self.suspect = False
        self.isSecure = True
        self.isLocal = False
        self._playlists = list(playlists)
        self.playlistQueries = 0

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


NAMES = {'1': ('Movies', 'movie'), '2': ('TV Shows', 'show'), '3': ('Music', 'artist')}


class SidebarCase(KodiTestCase):
    def setUp(self):
        super(SidebarCase, self).setUp()
        self.server = Server()
        self.settings = {}
        self.account = mock.Mock(title='Phil', username='phil', ID='1', thumb='', isOffline=False)
        self.account.safeUserThumb.return_value = 'avatar.png'
        self.manager = mock.Mock(selectedServer=self.server, serversByUuid={UUID: self.server, OTHER: OSCAR})
        # one server on the account unless a test says otherwise
        self.manager.getServers.return_value = [self.server]
        self.watchlist = Watchlist('/library/sections/watchlist', 'Watchlist')
        self.startedChecks = []
        self.startedFetches = []
        for patcher in (
                mock.patch.object(sidebar_model.plexapp, 'SERVERMANAGER', self.manager),
                mock.patch.object(sidebar_model.plexapp, 'ACCOUNT', self.account),
                mock.patch.object(sidebar_model.util, 'getSetting',
                                  lambda key, default=None: self.settings.get(key, default)),
                mock.patch.object(sidebar_model.util, 'setSetting',
                                  lambda key, value: self.settings.__setitem__(key, value)),
                mock.patch.object(sidebar_model.util, 'getUserSetting', lambda key, default=None: default),
                mock.patch.object(home, 'watchlist_section', self.watchlist),
                mock.patch.object(section_ids, 'migrate', lambda: None),
                mock.patch.object(sidebar_model.PlaylistsCheckTask, 'start',
                                  lambda task: self.startedChecks.append(task)),
                mock.patch.dict(sidebar_model._hasPlaylists, clear=True),
                mock.patch.object(sidebar_model, '_playlistsChecking', set()),
                mock.patch.object(sidebar_model.SectionsFetchTask, 'start',
                                  lambda task: self.startedFetches.append(task)),
                mock.patch.dict(sidebar_model._serverSections, clear=True),
                mock.patch.object(sidebar_model, '_sectionsFetching', set())):
            patcher.start()
            self.addCleanup(patcher.stop)
        # Animal has listed its libraries
        self.listed(UUID, [MOVIES, TV, MUSIC])
        self.store('watchlist', 'playlists', '1', '2', '3')

    @staticmethod
    def listed(uuid, sections):
        sidebar_model._serverSections[uuid] = (sidebar_model.time.time(), list(sections))

    def store(self, *keys, **titles):
        """Store the sidebar as these entries: 'watchlist', 'playlists', a library key on Animal
        ('1'), or one on Oscar ('other:1'; titles: other_1=('Films', 'movie'))."""
        entries, libraries = [], {}
        for key in keys:
            if key == 'watchlist':
                entries.append(section_ids.WATCHLIST_ID)
            elif key == 'playlists':
                entries.append(section_ids.PLAYLISTS_ID)
            else:
                other = key.startswith('other:')
                bare = key.partition(':')[2] if other else key
                sid = '{0}:{1}'.format(OTHER if other else UUID, bare)
                entries.append(sid)
                title, type_ = titles.get(key.replace(':', '_')) or NAMES.get(bare, ('Library ' + bare, 'movie'))
                libraries[sid] = {'title': title, 'type': type_, 'server': 'Oscar' if other else 'Animal'}
        self.settings['sidebar.1'] = json.dumps({'version': 2, 'entries': entries, 'libraries': libraries})

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

    def test_the_stored_list_is_the_sidebar_in_its_order(self):
        self.store('3', 'watchlist', '1')
        self.assertEqual(['Search', 'Home', 'Music', 'Watchlist', 'Movies'], self.labels(self.build(Shell())))

    def test_items_carry_their_markers(self):
        self.server._playlists = ['a playlist']
        items = self.build(Shell()).items
        self.assertTrue(items[0].getProperty('is.search'))
        self.assertTrue(items[1].getProperty('is.home'))
        self.assertIs(home.home_section, items[1].dataSource)
        playlists = [mli for mli in items if mli.dataSource is home.playlists_section][0]
        self.assertTrue(playlists.getProperty('is.playlists'))
        self.assertTrue(all(mli.getProperty('item') for mli in items))

    def test_a_library_its_server_has_not_listed_shows_from_what_is_stored(self):
        self.store('1', 'other:7')
        sectionList = self.build(Shell())
        self.assertEqual(['Search', 'Home', 'Movies', 'Library 7'], self.labels(sectionList))
        placeholder = sectionList.items[3].dataSource
        self.assertIsInstance(placeholder, sidebar_model.LibraryPlaceholder)
        self.assertEqual(OTHER + ':7', section_ids.sectionId(placeholder))
        self.assertIs(OSCAR, placeholder.server)
        # Oscar is asked on a worker; the build doesn't wait
        self.assertEqual([OSCAR], [task.server for task in self.startedFetches])

    def test_a_server_answering_rebuilds(self):
        self.store('1', 'other:7')
        changed = []
        sidebar_model.sections(sidebar_model.loadNavSettings(), onChange=lambda: changed.append(1))
        with mock.patch.object(sidebar_model, 'fetchServerSections',
                               lambda server: [Section('7', 'Films', server=OSCAR)]):
            self.startedFetches[0].run()
        self.assertEqual([1], changed)

    def test_a_server_that_does_not_answer_changes_nothing(self):
        self.store('1', 'other:7')
        changed = []
        sidebar_model.sections(sidebar_model.loadNavSettings(), onChange=lambda: changed.append(1))
        with mock.patch.object(sidebar_model, 'fetchServerSections', lambda server: None):
            self.startedFetches[0].run()
        self.assertEqual([], changed)

    def test_a_renamed_library_updates_what_is_stored(self):
        self.listed(UUID, [Section('1', 'Films')])
        self.store('1')
        self.assertEqual(['Search', 'Home', 'Films'], self.labels(self.build(Shell())))
        self.assertEqual('Films', json.loads(self.settings['sidebar.1'])['libraries'][UUID + ':1']['title'])

    @staticmethod
    def serverLines(sectionList):
        return [mli.getProperty('server.name') for mli in sectionList.items]

    def test_with_one_server_entries_are_one_line(self):
        self.assertEqual([''] * 6, self.serverLines(self.build(Shell())))

    def test_with_more_than_one_server_libraries_name_theirs_under_the_title(self):
        self.manager.getServers.return_value = [self.server, OSCAR]
        self.listed(OTHER, [Section('1', 'Movies', server=OSCAR)])
        self.store('watchlist', '1', 'other:1', 'other:7')
        sectionList = self.build(Shell())
        self.assertEqual(['Search', 'Home', 'Watchlist', 'Movies', 'Movies', 'Library 7'], self.labels(sectionList))
        # Watchlist isn't one server's; Oscar's library 7 is a placeholder, named from what's stored
        self.assertEqual(['', '', '', 'Animal', 'Oscar', 'Oscar'], self.serverLines(sectionList))


class HighlightTest(SidebarCase):
    def test_the_entry_section_is_highlighted_and_selected(self):
        sectionList = self.build(Shell(entrySectionId='2'))
        self.assertEqual(['TV Shows'], self.active(sectionList))
        self.assertEqual(4, sectionList.selected)

    def test_watchlist_only_when_no_section_matches(self):
        self.assertEqual(['Watchlist'], self.active(self.build(Shell(entrySectionId='watchlist',
                                                                     entryFromWatchlist=True))))
        self.assertEqual(['Movies'], self.active(self.build(Shell(entrySectionId='1', entryFromWatchlist=True))))

    def test_a_key_on_two_servers_follows_the_screens_server(self):
        self.listed(OTHER, [Section('1', 'Films', server=OSCAR)])
        self.store('1', 'other:1')
        shell = Shell(entrySectionId='1')
        shell.video = mock.Mock(server=OSCAR)
        self.assertEqual(['Films'], self.active(self.build(shell)))
        shell.video = mock.Mock(server=ANIMAL)
        self.assertEqual(['Movies'], self.active(self.build(shell)))

    def test_nothing_highlighted_without_an_entry_section(self):
        sectionList = self.build(Shell())
        self.assertEqual([], self.active(sectionList))
        self.assertIsNone(sectionList.selected)

    def test_a_person_follows_the_screen_the_role_came_from(self):
        win = person.PersonWindow.__new__(person.PersonWindow)
        win.role = mock.Mock(server=ANIMAL)
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
        win.navSettings = None
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

    def test_the_same_key_on_another_server_is_another_library(self):
        self.listed(OTHER, [Section('2', 'Films', server=OSCAR)])
        self.store('2', 'other:2')
        self.assertEqual(['Films'], self.active(self.build(self.window(Section('2', 'Films', server=OSCAR)))))

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
        win.navSettings = {'version': 2, 'entries': [UUID + ':2'], 'libraries': {}}
        self.assertEqual(['Search', 'Home', 'TV Shows'], self.labels(self.build(win)))


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
                          'server.name': 'Libraries', 'server.icon': 'script.plex/home/device/plex.png',
                          'server.iconmod': '', 'server.iconmod2': ''},
                         win.props)

    def test_an_offline_server_shows_the_error_icon_on_every_screen(self):
        self.server.offline = True
        win = Shell()
        win.displayServerAndUser()
        self.assertEqual('script.plex/home/device/error.png', win.props['server.icon'])


class MigrationTest(SidebarCase):
    """The show/hide setting (Phase 5's: the selected server's libraries, each shown unless hidden)
    becomes the list of what's in the sidebar, showing the same entries in the same order."""

    def migrate(self, old, sections=(MOVIES, TV, MUSIC)):
        with mock.patch.object(sidebar_model, 'fetchServerSections', lambda server: list(sections)):
            return sidebar_model.migrateToList(old, self.server)

    def test_everything_shown_in_the_servers_order(self):
        new = self.migrate({})
        self.assertEqual([section_ids.WATCHLIST_ID, section_ids.PLAYLISTS_ID, UUID + ':1', UUID + ':2', UUID + ':3'],
                         new['entries'])
        self.assertEqual({'title': 'TV Shows', 'type': 'show', 'server': 'Animal'}, new['libraries'][UUID + ':2'])

    def test_hidden_ones_are_left_out_and_the_order_kept(self):
        new = self.migrate({UUID + ':2': {'show': False}, section_ids.WATCHLIST_ID: {'show': False},
                            'order': [None, section_ids.PLAYLISTS_ID, UUID + ':3', UUID + ':1']})
        self.assertEqual([section_ids.PLAYLISTS_ID, UUID + ':3', UUID + ':1'], new['entries'])
        self.assertNotIn(UUID + ':2', new['libraries'])

    def test_not_in_the_order_comes_first_as_it_did(self):
        new = self.migrate({'order': [UUID + ':3', UUID + ':1']})
        self.assertEqual([section_ids.WATCHLIST_ID, section_ids.PLAYLISTS_ID, UUID + ':2', UUID + ':3', UUID + ':1'],
                         new['entries'])

    def test_no_answer_means_try_again_later(self):
        with mock.patch.object(sidebar_model, 'fetchServerSections', lambda server: None):
            self.assertIsNone(sidebar_model.migrateToList({}, self.server))

    def test_loading_moves_it_once(self):
        self.settings['sidebar.1'] = json.dumps({UUID + ':2': {'show': False}})
        with mock.patch.object(sidebar_model, 'fetchServerSections', lambda server: [MOVIES, TV, MUSIC]):
            nav = sidebar_model.loadNavSettings()
        self.assertEqual(2, nav['version'])
        self.assertNotIn(UUID + ':2', nav['entries'])
        self.assertEqual(nav, json.loads(self.settings['sidebar.1']))

    def test_while_it_cannot_be_moved_nothing_is_saved(self):
        self.settings['sidebar.1'] = old = json.dumps({UUID + ':2': {'show': False}})
        with mock.patch.object(sidebar_model, 'fetchServerSections', lambda server: None):
            nav = sidebar_model.loadNavSettings()
            sidebar_model.saveNavSettings(nav)
        self.assertEqual([section_ids.WATCHLIST_ID, section_ids.PLAYLISTS_ID], nav['entries'])
        self.assertEqual(old, self.settings['sidebar.1'])


class ListEditTest(SidebarCase):
    def nav(self):
        return sidebar_model.loadNavSettings()

    def test_add_goes_to_the_end_with_its_details(self):
        nav = self.nav()
        sidebar_model.addEntry(nav, Section('7', 'Films', server=OSCAR))
        self.assertEqual(OTHER + ':7', nav['entries'][-1])
        self.assertEqual({'title': 'Films', 'type': 'movie', 'server': 'Oscar'}, nav['libraries'][OTHER + ':7'])

    def test_remove(self):
        nav = self.nav()
        sidebar_model.removeEntry(nav, UUID + ':2')
        self.assertNotIn(UUID + ':2', nav['entries'])
        self.assertNotIn(UUID + ':2', nav['libraries'])

    def test_a_move_keeps_entries_not_showing_after_it(self):
        nav = self.nav()
        sidebar_model.reorder(nav, [UUID + ':3', UUID + ':1', UUID + ':2'])
        self.assertEqual([UUID + ':3', UUID + ':1', UUID + ':2', section_ids.WATCHLIST_ID, section_ids.PLAYLISTS_ID],
                         nav['entries'])

    def test_reset_order(self):
        self.listed(OTHER, [Section('7', 'Films', server=OSCAR)])
        self.store('other:7', '3', 'playlists', '1', 'watchlist')
        nav = self.nav()
        sidebar_model.resetOrder(nav)
        self.assertEqual([section_ids.WATCHLIST_ID, section_ids.PLAYLISTS_ID, UUID + ':1', UUID + ':3', OTHER + ':7'],
                         nav['entries'])


class PickerTest(SidebarCase):
    """LibraryWindow's Libraries picker: what it lists, and its ticks."""

    def window(self, listed):
        win = library.LibraryWindow.__new__(library.LibraryWindow)
        win.navSettings = None
        win._pickerServers = listed
        win._pickerChanged = False
        return win

    @staticmethod
    def rows(options):
        """'--' a separator, '# name' a heading, '  name' a row set in under one; ' [x]' if pinned."""
        def row(o):
            if not o:
                return '--'
            if o.get('heading'):
                return '# ' + o['display']
            pinned = o['indicator'] == library.LibraryWindow.PICKER_PINNED
            assert o['indicator_dim'] is not pinned, 'pinned full white, unpinned dimmed'
            return (o.get('inset') and '  ' or '') + o['display'] + (pinned and ' [x]' or '')
        return [row(o) for o in options]

    def test_each_server_a_heading_over_its_libraries_ticked_when_in_the_sidebar(self):
        win = self.window([(self.server, [MOVIES, TV, MUSIC]), (OSCAR, [Section('7', 'Films', server=OSCAR)])])
        self.store('watchlist', '1', '3')
        self.assertEqual(['Watchlist [x]', 'Playlists', '--',
                          '# Animal', '  Movies [x]', '  TV Shows', '  Music [x]', '--',
                          '# Oscar', '  Films'],
                         self.rows(win._libraryPickerOptions()))

    def test_a_server_that_does_not_answer_says_so_and_keeps_its_entries_removable(self):
        win = self.window([(self.server, [MOVIES]), (OSCAR, None)])
        self.store('1', 'other:7', other_7=('Films', 'movie'))
        self.assertEqual(['Watchlist', 'Playlists', '--', '# Animal', '  Movies [x]', '--',
                          "# Oscar isn't responding", '  Films [x]'],
                         self.rows(win._libraryPickerOptions()))

    def test_a_heading_does_nothing(self):
        win = self.window([(self.server, [MOVIES])])
        headingRow = [o for o in win._libraryPickerOptions() if o and o.get('heading')][0]
        self.assertIsNone(win._onLibraryPickerToggle(mock.Mock(), mock.Mock(dataSource=headingRow)))
        self.assertFalse(win._pickerChanged)

    def test_toggling_adds_and_removes(self):
        films = Section('7', 'Films', server=OSCAR)
        win = self.window([(self.server, [MOVIES]), (OSCAR, [films])])
        optionsList = mock.Mock()
        optionsList.getSelectedPos.return_value = 4
        filmsRow = [o for o in win._libraryPickerOptions() if o and o.get('sid') == OTHER + ':7'][0]
        result = win._onLibraryPickerToggle(optionsList, mock.Mock(dataSource=filmsRow))
        self.assertEqual('rebuild', result[0])
        self.assertEqual(OTHER + ':7', win.navSettings['entries'][-1])
        self.assertTrue(win._pickerChanged)
        win._onLibraryPickerToggle(optionsList, mock.Mock(dataSource=filmsRow))
        self.assertNotIn(OTHER + ':7', win.navSettings['entries'])
