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
    server = mock.Mock(uuid=uuid, offline=False, gone=False)
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
        self.owned = True
        self.offline = False
        self.gone = False
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
        # an account that used the add-on before account-wide keys, Animal selected
        # (section_ids.legacyServer()); a new account is OnboardingTest's
        self.settings = {'lastServerId.1': UUID}
        self.account = mock.Mock(title='Phil', username='phil', ID='1', thumb='', isOffline=False)
        self.account.safeUserThumb.return_value = 'avatar.png'
        self.manager = mock.Mock(serversByUuid={UUID: self.server, OTHER: OSCAR})
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
        playlists = [mli for mli in items if home.isPlaylists(mli.dataSource)][0]
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

    def test_a_server_still_on_its_first_test_is_not_asked_yet(self):
        testing = fakeServer(OTHER, 'Oscar')
        testing.activeConnection = None
        self.manager.serversByUuid[OTHER] = testing
        self.store('1', 'other:7')
        self.build(Shell())
        self.assertEqual([], self.startedFetches)
        self.assertFalse(sidebar_model.hasListed(testing))

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

    @staticmethod
    def offline(sectionList):
        return [mli.getLabel() for mli in sectionList.items if mli.getProperty('is.offline')]

    def test_a_library_whose_server_is_offline_dims(self):
        self.listed(OTHER, [Section('7', 'Films', server=OSCAR)])
        self.store('watchlist', '1', 'other:7', 'other:8')
        OSCAR.offline = True
        try:
            self.assertEqual(['Films', 'Library 8'], self.offline(self.build(Shell())))
        finally:
            OSCAR.offline = False

    def test_a_library_whose_server_is_not_on_the_account_dims(self):
        self.manager.serversByUuid = {UUID: self.server}
        self.store('1', 'other:7')
        self.assertEqual(['Library 7'], self.offline(self.build(Shell())))

    def test_the_sidebars_servers_are_watched(self):
        self.store('watchlist', '1', 'other:7', '2')
        sidebar_model.loadNavSettings()
        self.manager.setWatchedServers.assert_called_with(set([UUID, OTHER]))

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
        win.playlist = mock.Mock(server=self.server)
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

    def test_a_move_takes_its_place_in_the_order_and_the_sidebar_follows(self):
        nav = self.nav()
        sidebar_model.moveEntry(nav, UUID + ':3', 0)
        self.assertEqual([UUID + ':3', section_ids.WATCHLIST_ID, section_ids.playlistsId(UUID), UUID + ':1', UUID + ':2'],
                         nav['entries'])

    def test_unpinning_keeps_the_place_and_pinning_puts_it_back(self):
        nav = self.nav()
        sidebar_model.unpin(nav, UUID + ':1')
        self.assertNotIn(UUID + ':1', nav['entries'])
        self.assertIn(UUID + ':1', nav['libraries'])
        sidebar_model.moveEntry(nav, UUID + ':3', 0)
        sidebar_model.pin(nav, UUID + ':1')
        self.assertEqual([UUID + ':3', section_ids.WATCHLIST_ID, section_ids.playlistsId(UUID), UUID + ':1', UUID + ':2'],
                         nav['entries'])

    def test_reset_order(self):
        self.listed(OTHER, [Section('7', 'Films', server=OSCAR)])
        self.store('other:7', '3', 'playlists', '1', 'watchlist')
        nav = self.nav()
        sidebar_model.resetOrder(nav)
        # a server's Playlists after its libraries
        self.assertEqual([section_ids.WATCHLIST_ID, UUID + ':1', UUID + ':3', section_ids.playlistsId(UUID), OTHER + ':7'],
                         nav['entries'])

    def test_reset_order_puts_the_accounts_own_servers_first(self):
        # by name, a shared server would come first; nothing is selected to go first any more
        OSCAR.owned, OSCAR.name = False, 'Aardvark'
        self.addCleanup(setattr, OSCAR, 'name', 'Oscar')
        self.listed(OTHER, [Section('7', 'Films', server=OSCAR)])
        self.store('other:7', '1', 'watchlist')
        nav = self.nav()
        nav['libraries'][OTHER + ':7']['server'] = 'Aardvark'
        sidebar_model.resetOrder(nav)
        self.assertEqual([section_ids.WATCHLIST_ID, UUID + ':1', OTHER + ':7'], nav['entries'])


class PickerTest(SidebarCase):
    """LibraryWindow's Libraries picker: one list of every library in the user's order, the sidebar
    being the pinned ones (the user's design, 2026-10-05); each row its pin and Move."""

    def window(self, servers, listed):
        win = library.LibraryWindow.__new__(library.LibraryWindow)
        win.navSettings = None
        win._pickerServers = servers
        win._pickerListed = listed
        win._pickerChanged = False
        self.manager.getServers.return_value = servers
        return win

    @staticmethod
    def rows(options):
        """'--' a separator; a row is its title, ' / subtitle' if it has one, ' [x]' if pinned."""
        def row(o):
            if not o:
                return '--'
            if o['key'] != 'library':
                return o['display']
            pinned = o['indicator'] == library.LibraryWindow.PICKER_PINNED
            assert o['indicator_dim'] is not pinned, 'pinned full white, unpinned dimmed'
            subtitle = o['properties']['subtitle']
            return o['display'] + (subtitle and ' / ' + subtitle or '') + (pinned and ' [x]' or '')
        return [row(o) for o in options]

    def films(self):
        return Section('7', 'Films', server=OSCAR)

    def test_one_list_pinned_first_as_ordered_then_the_rest_by_server(self):
        self.store('watchlist', '3', '1')
        win = self.window([self.server, OSCAR], {UUID: [MOVIES, TV, MUSIC], OTHER: [self.films()]})
        self.assertEqual(['Watchlist [x]', 'Music / Animal [x]', 'Movies / Animal [x]',
                          'TV Shows / Animal', 'Films / Oscar', '--', 'Reset library order'],
                         self.rows(win._libraryPickerOptions()))

    def test_each_servers_playlists_its_own_row_after_its_libraries(self):
        self.store('watchlist', '3', '1')
        win = self.window([self.server, OSCAR], {UUID: [MOVIES, TV, MUSIC], OTHER: [self.films()]})
        win._pickerPlaylists = {UUID: True, OTHER: True}
        self.assertEqual(['Watchlist [x]', 'Music / Animal [x]', 'Movies / Animal [x]', 'TV Shows / Animal',
                          'Playlists / Animal', 'Films / Oscar', 'Playlists / Oscar'],
                         self.rows(win._libraryPickerOptions())[:7])
        # pinned, it's that server's sidebar entry
        self.choose(win, section_ids.playlistsId(OTHER))
        self.assertEqual(section_ids.playlistsId(OTHER), win.navSettings['entries'][-1])

    def test_a_server_with_no_playlists_any_more_leaves_the_list(self):
        win = self.window([self.server], {UUID: [MOVIES, TV, MUSIC]})
        win._pickerPlaylists = {UUID: True}
        win._libraryPickerOptions()
        win._pickerPlaylists = {UUID: False}
        self.assertNotIn('Playlists', self.rows(win._libraryPickerOptions()))

    def test_one_server_no_server_line(self):
        win = self.window([self.server], {UUID: [MOVIES, TV, MUSIC]})
        self.assertEqual(['Watchlist [x]', 'Playlists [x]', 'Movies [x]', 'TV Shows [x]', 'Music [x]'],
                         self.rows(win._libraryPickerOptions())[:5])

    def test_a_server_that_does_not_answer_says_so_with_its_libraries_still_listed(self):
        self.store('1', 'other:7', other_7=('Films', 'movie'))
        win = self.window([self.server, OSCAR], {UUID: [MOVIES], OTHER: None})
        self.assertIn(u"Films / Oscar isn't responding [x]", self.rows(win._libraryPickerOptions()))

    def test_an_unpinned_library_gone_from_its_server_leaves_the_list(self):
        win = self.window([self.server], {UUID: [MOVIES, TV, MUSIC]})
        win._libraryPickerOptions()
        sidebar_model.unpin(win.navSettings, UUID + ':2')
        win._pickerListed = {UUID: [MOVIES, MUSIC]}
        self.assertNotIn('TV Shows', self.rows(win._libraryPickerOptions()))

    def choose(self, win, sid, column='pin'):
        row = dict([o for o in win._libraryPickerOptions() if o and o.get('sid') == sid][0], column=column)
        optionsList = mock.Mock()
        optionsList.getSelectedPos.return_value = 3
        return win._onLibraryPickerChoice(optionsList, mock.Mock(dataSource=row))

    def test_select_on_the_pin_pins_and_unpins_in_place(self):
        win = self.window([self.server, OSCAR], {UUID: [MOVIES, TV, MUSIC], OTHER: [self.films()]})
        self.assertEqual('rebuild', self.choose(win, OTHER + ':7')[0])
        self.assertEqual(OTHER + ':7', win.navSettings['entries'][-1])
        self.assertTrue(win._pickerChanged)
        self.choose(win, UUID + ':2')
        self.assertNotIn(UUID + ':2', win.navSettings['entries'])
        self.assertEqual(['Watchlist [x]', 'Playlists / Animal [x]', 'Movies / Animal [x]', 'TV Shows / Animal',
                          'Music / Animal [x]', 'Films / Oscar [x]'], self.rows(win._libraryPickerOptions())[:6])

    def test_select_on_move_picks_the_row_up(self):
        win = self.window([self.server], {UUID: [MOVIES, TV, MUSIC]})
        self.assertEqual('enter_move_mode', self.choose(win, UUID + ':1', column='move'))
        self.assertFalse(win._pickerChanged)

    def test_a_dropped_row_takes_its_place_pinned_or_not(self):
        win = self.window([self.server, OSCAR], {UUID: [MOVIES, TV, MUSIC], OTHER: [self.films()]})
        win._libraryPickerOptions()
        # Films (unpinned, row 5) dropped at the top
        win._onLibraryPickerMove('confirm', mock.Mock(dataSource={'sid': OTHER + ':7'}), 5, 0)
        self.assertEqual(['Films / Oscar', 'Watchlist [x]', 'Playlists / Animal [x]'],
                         self.rows(win._libraryPickerOptions())[:3])
        # Music (pinned, row 4) dropped second: the sidebar follows
        win._onLibraryPickerMove('confirm', mock.Mock(dataSource={'sid': UUID + ':3'}), 4, 1)
        self.assertEqual([UUID + ':3', section_ids.WATCHLIST_ID], win.navSettings['entries'][:2])
        self.assertTrue(win._pickerChanged)

    def test_a_cancelled_move_changes_nothing(self):
        win = self.window([self.server], {UUID: [MOVIES, TV, MUSIC]})
        win._onLibraryPickerMove('cancel', mock.Mock(dataSource={'sid': UUID + ':3'}), 4, 4)
        self.assertFalse(win._pickerChanged)

    def test_reset_order(self):
        self.store('3', 'watchlist', '1')
        win = self.window([self.server], {UUID: [MOVIES, TV, MUSIC]})
        reset = [o for o in win._libraryPickerOptions() if o and o['key'] == 'reset_order'][0]
        optionsList = mock.Mock()
        optionsList.getSelectedPos.return_value = 0
        win._onLibraryPickerChoice(optionsList, mock.Mock(dataSource=reset))
        self.assertEqual([section_ids.WATCHLIST_ID, UUID + ':1', UUID + ':3'], win.navSettings['entries'])


class OpenFromPickerTest(SidebarCase):
    """The picker's third action: open the library (the row itself). Not pinned, it gets a temporary
    sidebar entry at the end while it's the section open (the user's design, 2026-10-05)."""
    window = PickerTest.window
    choose = PickerTest.choose

    def setUp(self):
        super(OpenFromPickerTest, self).setUp()
        self.addCleanup(sidebar_model.setTemporary, None)

    def test_select_on_the_row_closes_with_the_library_to_open(self):
        win = self.window([self.server], {UUID: [MOVIES, TV, MUSIC]})
        win._pickerOpen = None
        self.assertEqual('close', self.choose(win, UUID + ':2', column='open'))
        self.assertEqual((UUID + ':2', TV), win._pickerOpen)
        self.assertFalse(win._pickerChanged)

    def test_a_library_not_listed_opens_as_a_placeholder(self):
        self.store('1', 'other:7', other_7=('Films', 'movie'))
        win = self.window([self.server, OSCAR], {UUID: [MOVIES], OTHER: None})
        win._pickerOpen = None
        self.choose(win, OTHER + ':7', column='open')
        self.assertIsInstance(win._pickerOpen[1], sidebar_model.LibraryPlaceholder)

    def opened(self, win, sid, section):
        win._sidebarTarget = lambda: win
        win._deferOpenSection = mock.Mock()
        win._openFromPicker(sid, section)
        win._deferOpenSection.assert_called_once_with(section, force=True)

    def test_opening_is_left_to_open_section(self):
        # which follows the section (sidebar_model.followSection()), however it was reached
        win = self.window([self.server], {UUID: [MOVIES, TV, MUSIC]})
        self.opened(win, UUID + ':2', TV)
        self.assertIsNone(sidebar_model.temporary())

    def test_open_section_follows_the_section(self):
        nav = {'entries': [UUID + ':1']}
        with mock.patch.object(sidebar_model, 'followSection') as follow:
            win = library.LibraryWindow.__new__(library.LibraryWindow)
            win.navSettings = nav
            win.section = MOVIES
            win.view_gone = None
            for name in ('tasks', '_settleHubSlide', '_retireListItems'):
                setattr(win, name, mock.Mock())
            win._hubReselectPositions = {}
            # the rest of the swap is the window's; the follow comes before any of it
            with mock.patch.object(library, '_invalidateSectionHasCollectionsCache', side_effect=StopIteration):
                with self.assertRaises(StopIteration):
                    library.LibraryWindow.openSection(win, TV, view_gone=True)
        follow.assert_called_once_with(TV, nav)

    def closed(self, win, section, opening=None):
        win.section = section
        win._pickerOpen = opening
        win._followOpenSection()

    def test_the_open_section_unpinned_keeps_a_temporary_entry(self):
        # unpinned in the picker while open, it stays on screen: not with no sidebar entry (the
        # user, 2026-10-06), but the temporary one at the end until another section opens
        self.store('watchlist', '1', '2')
        win = self.window([self.server], {UUID: [MOVIES, TV, MUSIC]})
        sidebar_model.removeEntry(win.sidebarNavSettings(), UUID + ':2')
        self.closed(win, TV)
        self.assertEqual(UUID + ':2', sidebar_model.temporary())
        self.assertEqual(UUID + ':2', win._sidebarTemporary)
        self.assertEqual([self.watchlist, MOVIES, TV], sidebar_model.sections(win.navSettings))

    def test_another_library_unpinned_gets_none(self):
        self.store('watchlist', '1', '2')
        win = self.window([self.server], {UUID: [MOVIES, TV, MUSIC]})
        sidebar_model.removeEntry(win.sidebarNavSettings(), UUID + ':2')
        self.closed(win, MOVIES)
        self.assertIsNone(sidebar_model.temporary())

    def test_not_when_the_picker_opens_another_library(self):
        self.store('watchlist', '1', '2')
        win = self.window([self.server], {UUID: [MOVIES, TV, MUSIC]})
        sidebar_model.removeEntry(win.sidebarNavSettings(), UUID + ':2')
        self.closed(win, TV, opening=(UUID + ':1', MOVIES))
        self.assertIsNone(sidebar_model.temporary())

    def test_pinned_again_its_temporary_entry_goes(self):
        self.store('watchlist', '1', '2')
        win = self.window([self.server], {UUID: [MOVIES, TV, MUSIC]})
        sidebar_model.setTemporary(UUID + ':3')
        win.sidebarNavSettings()['entries'].append(UUID + ':3')
        self.closed(win, MUSIC)
        self.assertIsNone(sidebar_model.temporary())
        self.assertEqual([self.watchlist, MOVIES, TV, MUSIC], sidebar_model.sections(win.navSettings))

    def test_home_has_no_entry_to_keep(self):
        self.store('watchlist', '1', '2')
        win = self.window([self.server], {UUID: [MOVIES, TV, MUSIC]})
        sidebar_model.setTemporary(UUID + ':3')
        self.closed(win, home.home_section)
        self.assertIsNone(sidebar_model.temporary())

    def test_a_hosted_screen_goes_home_to_it(self):
        win = self.window([self.server], {UUID: [MOVIES, TV, MUSIC]})
        screen = mock.Mock()
        win._sidebarTarget = lambda: screen
        win._openFromPicker(UUID + ':2', TV)
        screen.goHome.assert_called_once_with(section=TV, force=True)


class FollowSectionTest(KodiTestCase):
    """Every way into a library - the sidebar, the picker, "Go to <library>" from an item, a film
    reached from a credit in another library, Back - goes through LibraryWindow.openSection(), which
    gives one with no sidebar entry the temporary one while it's open (the user, 2026-10-06)."""

    def setUp(self):
        super(FollowSectionTest, self).setUp()
        self.addCleanup(sidebar_model.setTemporary, None)
        self.nav = {'entries': [section_ids.WATCHLIST_ID, UUID + ':1']}

    def test_an_unpinned_library_gets_it(self):
        self.assertTrue(sidebar_model.followSection(TV, self.nav))
        self.assertEqual(UUID + ':2', sidebar_model.temporary())
        self.assertFalse(sidebar_model.followSection(TV, self.nav), 'unchanged: already its')

    def test_a_pinned_one_or_home_lets_it_go(self):
        sidebar_model.followSection(TV, self.nav)
        self.assertTrue(sidebar_model.followSection(MOVIES, self.nav))
        self.assertIsNone(sidebar_model.temporary())
        sidebar_model.followSection(TV, self.nav)
        sidebar_model.followSection(home.home_section, self.nav)
        self.assertIsNone(sidebar_model.temporary())

    def test_a_folder_or_collection_comes_under_its_library(self):
        folder = Section('/library/sections/2/folder', 'Some folder', library_id='2')
        self.assertEqual(UUID + ':2', sidebar_model.entryIdFor(folder))
        sidebar_model.followSection(folder, self.nav)
        self.assertEqual(UUID + ':2', sidebar_model.temporary())

    def test_on_its_own_server(self):
        self.assertEqual(OTHER + ':1', sidebar_model.entryIdFor(Section('1', 'Films', server=OSCAR)))

    def test_nothing_without_a_library(self):
        self.assertIsNone(sidebar_model.entryIdFor(Section('/library/collections/9', 'A collection')))
        self.assertIsNone(sidebar_model.entryIdFor(home.home_section))


class LibraryOfTest(KodiTestCase):
    """"Go to <library>" from the music player, an album or a photo folder: the library itself, not
    its key - a key is only looked up in the sidebar (LibraryWindow.resolveSection()), and one that
    isn't pinned went to Home instead."""

    def item(self, key='2'):
        item = mock.Mock(server=ANIMAL)
        item.getLibrarySectionId.return_value = key
        return item

    def test_the_servers_own_section(self):
        with mock.patch.object(sidebar_model, 'serverSections', return_value=[MOVIES, TV]):
            self.assertIs(TV, sidebar_model.libraryOf(self.item('2')))

    def test_else_one_made_from_the_item(self):
        made = Section('2', 'TV Shows')
        with mock.patch.object(sidebar_model, 'serverSections', return_value=None), \
                mock.patch.object(sidebar_model.plexlibrary.LibrarySection, 'fromFilter', return_value=made):
            self.assertIs(made, sidebar_model.libraryOf(self.item('2')))

    def test_else_its_key(self):
        with mock.patch.object(sidebar_model, 'serverSections', return_value=None), \
                mock.patch.object(sidebar_model.plexlibrary.LibrarySection, 'fromFilter', side_effect=AttributeError):
            self.assertEqual('2', sidebar_model.libraryOf(self.item('2')))
