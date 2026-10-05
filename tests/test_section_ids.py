# coding=utf-8
"""
Library ids and catalog ids that stay unique across servers (lib/windows/section_ids.py), and the
one-time move of the per-server sidebar and hub settings to account-wide keys under those ids.

The move must not change anything the user sees: the selected server's order, hidden libraries and
hub configs (Home's included) come through as they were, two servers' library "1" stay apart, and
running it twice does nothing.

Importing lib.windows.* starts lib.player's monitor thread unless abort_requested is set first.
"""

from __future__ import absolute_import

import json
from unittest import mock

from kodienv import ENV

ENV.abort_requested = True
from lib.windows import home, library_hubs, section_ids  # noqa: E402
from plexnet import plexlibrary  # noqa: E402

from .base import KodiTestCase  # noqa: E402

ANIMAL = 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa00001111'
OSCAR = 'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb00002222'


class Server(object):
    def __init__(self, uuid):
        self.uuid = uuid


class Section(object):
    def __init__(self, key, server=None, title='Movies', type_='movie'):
        self.key = key
        self.server = server
        self.title = title
        self.type = type_


class Hub(object):
    getCleanHubIdentifier = plexlibrary.BaseHub.getCleanHubIdentifier

    def __init__(self, hubIdentifier, server, items=(1,)):
        self.hubIdentifier = hubIdentifier
        self.server = server
        self.items = list(items)
        self.title = None
        self._identifier = None


class IdsTest(KodiTestCase):
    def test_a_library_is_its_server_and_key(self):
        self.assertEqual(ANIMAL + ':1', section_ids.sectionId(Section('1', Server(ANIMAL))))

    def test_home_playlists_and_watchlist_keep_their_ids(self):
        self.assertIsNone(section_ids.sectionId(Section(None, Server(ANIMAL))))
        self.assertEqual('playlists', section_ids.sectionId(Section('playlists', Server(ANIMAL))))
        self.assertEqual('/library/sections/watchlist',
                         section_ids.sectionId(Section('/library/sections/watchlist', Server(ANIMAL))))

    def test_a_library_hub_is_from_its_library(self):
        section = Section('3', Server(ANIMAL))
        hub = Hub('movie.recentlyadded.3', section.server)
        self.assertEqual(ANIMAL + ':3|movie.recentlyadded', section_ids.hubCatalogId(hub, section))

    def test_a_home_hub_is_from_its_server(self):
        hub = Hub('home.movies.recent.3.1', Server(OSCAR))
        self.assertEqual(OSCAR + '|home.movies.recent',
                         section_ids.hubCatalogId(hub, Section(None, Server(ANIMAL))))

    def test_hub_settings_are_a_librarys_or_a_servers_homes(self):
        self.assertEqual(ANIMAL + ':1', section_ids.hubSettingsId(Section('1', Server(ANIMAL))))
        # one Home config for every server's rows (Phase 7); Phase 5's per-server ones merge into it
        self.assertEqual('__home__', section_ids.hubSettingsId(Section(None, Server(ANIMAL))))

    def test_homes_continue_watching_is_every_servers(self):
        hub = Hub('continueWatching', Server(OSCAR))
        self.assertEqual('continueWatching', section_ids.hubCatalogId(hub, Section(None, Server(ANIMAL))))

    def test_parse_splits_source_from_identifier(self):
        self.assertEqual((ANIMAL + ':3', 'movie.recentlyadded'),
                         section_ids.parseCatalogId(ANIMAL + ':3|movie.recentlyadded'))
        self.assertEqual((OSCAR, 'home.movies.recent'), section_ids.parseCatalogId(OSCAR + '|home.movies.recent'))


class RekeyTest(KodiTestCase):
    def test_catalog_ids(self):
        rekey = section_ids.rekeyCatalogId
        self.assertEqual(ANIMAL + ':3|movie.recentlyadded', rekey('3:movie.recentlyadded', ANIMAL))
        self.assertEqual(ANIMAL + ':3|custom.collection.3.37180', rekey('3:custom.collection.3.37180', ANIMAL))
        self.assertEqual('playlists|playlists.audio', rekey('playlists:playlists.audio', ANIMAL))
        self.assertEqual(ANIMAL + '|home.movies.recent', rekey('home.movies.recent', ANIMAL))
        self.assertEqual(ANIMAL + '|continueWatching', rekey('continueWatching', ANIMAL))

    def test_a_new_catalog_id_is_left_alone(self):
        for cid in (ANIMAL + ':3|movie.recentlyadded', OSCAR + '|home.movies.recent'):
            self.assertEqual(cid, section_ids.rekeyCatalogId(cid, ANIMAL))

    def test_nav_settings(self):
        nav = {'1': {'show': False}, 'playlists': {'show': False},
               '/library/sections/watchlist': {'show': True},
               'order': ['playlists', '2', '/library/sections/watchlist', '1']}
        self.assertEqual({ANIMAL + ':1': {'show': False}, 'playlists': {'show': False},
                          '/library/sections/watchlist': {'show': True},
                          'order': ['playlists', ANIMAL + ':2', '/library/sections/watchlist', ANIMAL + ':1']},
                         section_ids.rekeyNavSettings(nav, ANIMAL))

    def test_hub_settings(self):
        stored = {
            '_version': 2,
            '__home__': {'custom': True, 'hubs': [
                {'catalog_id': 'continueWatching', 'identifier': 'continueWatching', 'order': 0},
                {'catalog_id': '3:movie.recentlyadded', 'identifier': 'movie.recentlyadded', 'order': 1},
                {'identifier': 'home.music.recent', 'order': 2},
            ]},
            '3': {'custom': True, 'hubs': [
                {'catalog_id': '3:movie.inprogress', 'identifier': 'movie.inprogress', 'order': 0},
            ]},
            'playlists': {'custom': False, 'hubs': []},
        }
        self.assertEqual({
            ANIMAL + ':__home__': {'custom': True, 'hubs': [
                {'catalog_id': ANIMAL + '|continueWatching', 'identifier': 'continueWatching', 'order': 0},
                {'catalog_id': ANIMAL + ':3|movie.recentlyadded', 'identifier': 'movie.recentlyadded', 'order': 1},
                {'catalog_id': ANIMAL + '|home.music.recent', 'identifier': 'home.music.recent', 'order': 2},
            ]},
            ANIMAL + ':3': {'custom': True, 'hubs': [
                {'catalog_id': ANIMAL + ':3|movie.inprogress', 'identifier': 'movie.inprogress', 'order': 0},
            ]},
            'playlists': {'custom': False, 'hubs': []},
        }, section_ids.rekeyHubSettings(stored, ANIMAL))

    def test_old_continue_watching_is_replaced_before_rekeying(self):
        stored = {'__home__': {'custom': True, 'hubs': [
            {'catalog_id': 'home.ondeck', 'order': 0}, {'catalog_id': 'home.movies.recent', 'order': 1}]}}
        self.assertEqual([ANIMAL + '|continueWatching', ANIMAL + '|home.movies.recent'],
                         [h['catalog_id'] for h in section_ids.rekeyHubSettings(stored, ANIMAL)[ANIMAL + ':__home__']['hubs']])


class MigrateOldContinueWatchingTest(KodiTestCase):
    """section_ids.migrateOldContinueWatching(), run on each server's stored hub settings as they're
    moved: the server's old separate home.continue/home.ondeck home hubs no longer exist
    (plexserver.hubs() always substitutes the combined continueWatching hub), so a custom config
    still listing them must list continueWatching instead or the row vanishes."""

    migrate = staticmethod(section_ids.migrateOldContinueWatching)

    def test_old_pair_becomes_one_continue_watching_entry_at_the_earliest_position(self):
        settings = {None: {'custom': True, 'hubs': [
            {'catalog_id': 'home.movies.recent', 'order': 0},
            {'catalog_id': 'home.continue', 'order': 1},
            {'catalog_id': 'home.ondeck', 'order': 2},
            {'catalog_id': 'home.music.recent', 'order': 3},
        ]}}
        self.assertTrue(self.migrate(settings))
        self.assertEqual(
            [('home.movies.recent', 0), ('continueWatching', 1), ('home.music.recent', 2)],
            [(h['catalog_id'], h['order']) for h in settings[None]['hubs']])

    def test_old_entries_just_drop_when_continue_watching_is_already_listed(self):
        settings = {None: {'custom': True, 'hubs': [
            {'catalog_id': 'continueWatching', 'order': 0},
            {'catalog_id': 'home.ondeck', 'order': 1},
        ]}}
        self.assertTrue(self.migrate(settings))
        self.assertEqual(['continueWatching'], [h['catalog_id'] for h in settings[None]['hubs']])

    def test_every_section_is_rewritten_not_just_home(self):
        settings = {'3': {'custom': True, 'hubs': [
            {'catalog_id': 'home.continue', 'order': 0},
            {'catalog_id': '3:movie.recentlyadded', 'order': 1},
        ]}}
        self.assertTrue(self.migrate(settings))
        self.assertEqual(['continueWatching', '3:movie.recentlyadded'],
                         [h['catalog_id'] for h in settings['3']['hubs']])

    def test_a_config_without_the_old_ids_is_left_alone(self):
        hubs = [{'catalog_id': 'home.movies.recent', 'order': 0}]
        settings = {None: {'custom': True, 'hubs': hubs}, '3': {'custom': False}}
        self.assertFalse(self.migrate(settings))
        self.assertIs(hubs, settings[None]['hubs'])

    def test_empty_or_missing_settings_are_fine(self):
        self.assertFalse(self.migrate({}))
        self.assertFalse(self.migrate(None))


class MigrateCase(KodiTestCase):
    def setUp(self):
        super(MigrateCase, self).setUp()
        self.animal, self.oscar = Server(ANIMAL), Server(OSCAR)
        # the server selected when the add-on last ran: the old settings' (legacyServer())
        self.settings = {'lastServerId.7': ANIMAL}
        self.writes = []
        self.manager = mock.Mock(serversByUuid={ANIMAL: self.animal, OSCAR: self.oscar})
        self.manager.getServers.return_value = [self.oscar, self.animal]

        def setSetting(key, value):
            self.writes.append(key)
            self.settings[key] = value

        for patcher in (
                mock.patch.object(section_ids.plexapp, 'SERVERMANAGER', self.manager),
                mock.patch.object(section_ids.plexapp, 'ACCOUNT', mock.Mock(ID='7')),
                mock.patch.object(section_ids.util, 'getSetting',
                                  lambda key, default=None: self.settings.get(key, default)),
                mock.patch.object(section_ids.util, 'setSetting', setSetting),
                mock.patch.object(section_ids, '_migrated', set())):
            patcher.start()
            self.addCleanup(patcher.stop)

    def store(self, key, value):
        self.settings[key] = json.dumps(value)

    def stored(self, key):
        return json.loads(self.settings[key])


class MigrateTest(MigrateCase):
    def setUp(self):
        super(MigrateTest, self).setUp()
        # both servers have a library "1"
        self.animalNav = {'1': {'show': False}, 'playlists': {'show': False},
                          'order': ['2', 'playlists', '/library/sections/watchlist', '1']}
        self.oscarNav = {'1': {'show': False}, '4': {'show': True},
                         '/library/sections/watchlist': {'show': False}, 'order': ['4', '1']}
        self.animalHubs = {
            '__home__': {'custom': True, 'hubs': [{'catalog_id': 'home.movies.recent', 'order': 0}]},
            '1': {'custom': True, 'hubs': [{'catalog_id': '1:movie.inprogress', 'order': 0}]}}
        self.oscarHubs = {
            '__home__': {'custom': True, 'hubs': [{'catalog_id': 'home.music.recent', 'order': 0}]},
            '1': {'custom': True, 'hubs': [{'catalog_id': '1:artist.recentlyadded', 'order': 0}]},
            'playlists': {'custom': True, 'hubs': []}}
        self.store('home.settings.00001111.7', self.animalNav)
        self.store('home.settings.00002222.7', self.oscarNav)
        self.store('hub.settings.00001111.7', self.animalHubs)
        self.store('hub.settings.00002222.7', self.oscarHubs)
        self.old = dict(self.settings)

    def test_the_selected_servers_sidebar_comes_through_whole(self):
        section_ids.migrate()
        nav = self.stored('sidebar.7')
        self.assertEqual(['{0}:2'.format(ANIMAL), 'playlists', '/library/sections/watchlist', ANIMAL + ':1'],
                         nav['order'][:4])
        self.assertEqual({'show': False}, nav[ANIMAL + ':1'])
        self.assertEqual({'show': False}, nav['playlists'])

    def test_other_servers_add_only_their_libraries(self):
        section_ids.migrate()
        nav = self.stored('sidebar.7')
        self.assertEqual({'show': False}, nav[OSCAR + ':1'])
        self.assertEqual({'show': True}, nav[OSCAR + ':4'])
        # Oscar's hidden Watchlist would hide it on Animal too
        self.assertNotIn('/library/sections/watchlist', nav)
        self.assertEqual([OSCAR + ':4', OSCAR + ':1'], nav['order'][4:])

    def test_hub_settings_libraries_and_homes_from_every_server(self):
        section_ids.migrate()
        hubs = self.stored('hub.settings.7')
        self.assertEqual([ANIMAL + '|home.movies.recent'], [h['catalog_id'] for h in hubs[ANIMAL + ':__home__']['hubs']])
        self.assertEqual([OSCAR + '|home.music.recent'], [h['catalog_id'] for h in hubs[OSCAR + ':__home__']['hubs']])
        self.assertEqual([ANIMAL + ':1|movie.inprogress'], [h['catalog_id'] for h in hubs[ANIMAL + ':1']['hubs']])
        self.assertEqual([OSCAR + ':1|artist.recentlyadded'], [h['catalog_id'] for h in hubs[OSCAR + ':1']['hubs']])
        self.assertNotIn('playlists', hubs)

    def test_the_old_keys_are_never_written(self):
        section_ids.migrate()
        self.assertEqual(['hub.settings.7', 'sidebar.7'], self.writes)
        for key, value in self.old.items():
            self.assertEqual(value, self.settings[key])

    def test_migrating_twice_changes_nothing(self):
        section_ids.migrate()
        after = dict(self.settings)
        section_ids._migrated.clear()
        section_ids.migrate()
        self.assertEqual(after, self.settings)
        self.assertEqual(2, len(self.writes))

    def test_waits_for_the_old_settings_server_to_be_known(self):
        self.manager.serversByUuid = {OSCAR: self.oscar}
        section_ids.migrate()
        self.assertEqual([], self.writes)
        self.manager.serversByUuid[ANIMAL] = self.animal
        section_ids.migrate()
        self.assertIn('sidebar.7', self.settings)


class NothingToMigrateTest(MigrateCase):
    def test_an_old_account_with_no_settings_is_marked_done(self):
        section_ids.migrate()
        self.assertEqual({}, self.stored('sidebar.7'))
        self.assertEqual({}, self.stored('hub.settings.7'))

    def test_a_new_account_has_nothing_to_move(self):
        # never had a server selected: onboarding (sidebar_model.loadNavSettings()), not migration
        del self.settings['lastServerId.7']
        section_ids.migrate()
        self.assertEqual([], self.writes)
        self.assertIn('7', section_ids._migrated)


class SameAsBeforeTest(MigrateCase):
    """What the readers make of the moved settings is what they made of the old ones."""

    class Hubs(library_hubs.HubsMixin):
        def __init__(self):
            self.sectionHubs = {}
            self.loadHubSettings()

    def setUp(self):
        super(SameAsBeforeTest, self).setUp()
        self.home = Section(None, self.animal, title='Home')
        self.movies = Section('1', self.animal)
        self.store('hub.settings.00001111.7', {
            '__home__': {'custom': True, 'hubs': [
                {'catalog_id': 'home.television.recent', 'order': 0},
                {'catalog_id': 'continueWatching', 'order': 1}]},
            '1': {'custom': True, 'hubs': [
                {'catalog_id': '1:movie.inprogress', 'order': 0},
                {'catalog_id': '1:movie.recentlyadded', 'order': 1}]}})
        self.store('home.settings.00001111.7', {
            '2': {'show': False}, 'order': ['/library/sections/watchlist', '3', '1']})
        for patcher in (mock.patch.object(library_hubs.util, 'getSetting',
                                          lambda key, default=None: self.settings.get(key, default)),):
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_home_hubs_hidden_and_ordered_as_before(self):
        win = self.Hubs()
        cw = Hub('continueWatching', self.animal)
        movies = Hub('home.movies.recent.1.1', self.animal)
        tv = Hub('home.television.recent.2.1', self.animal)
        hubs = [cw, movies, tv]
        self.assertEqual([tv, cw], [h for h in win.sortHubsByUserOrder(hubs, self.home)
                                    if not win.isHubHidden(h, self.home)])

    def test_library_hubs_hidden_and_ordered_as_before(self):
        win = self.Hubs()
        added = Hub('movie.recentlyadded.1', self.animal)
        progress = Hub('movie.inprogress.1', self.animal)
        genre = Hub('movie.by.genre.1', self.animal)
        self.assertEqual([progress, added], [h for h in win.sortHubsByUserOrder([added, genre, progress], self.movies)
                                             if not win.isHubHidden(h, self.movies)])

    def test_another_servers_home_without_a_config_shows_every_hub(self):
        # live 2026-10-04: Animal's Home config hid every one of Oscar's Home rows
        win = self.Hubs()
        oscarHome = Section(None, self.oscar, title='Home')
        hubs = [Hub('continueWatching', self.oscar), Hub('home.movies.recent.1.1', self.oscar)]
        # as the bind does: the saved rows reconciled with the rows sent, first
        win._reconcileWithHubs(oscarHome, hubs)
        self.assertEqual(hubs, [h for h in win.sortHubsByUserOrder(hubs, oscarHome)
                                if not win.isHubHidden(h, oscarHome)])

    def test_another_servers_library_1_has_no_config(self):
        win = self.Hubs()
        other = Section('1', self.oscar)
        genre = Hub('movie.by.genre.1', self.oscar)
        self.assertFalse(win.isHubHidden(genre, other))

    def test_sidebar_hidden_and_ordered_as_before(self):
        # the account-wide show/hide setting this move writes (sidebar_model turns it into the
        # list of picked libraries next, sidebar_model.migrateToList())
        section_ids.migrate()
        nav = section_ids.loadJson(section_ids.sidebarKey())
        self.assertEqual({'show': False}, nav[ANIMAL + ':2'])
        self.assertNotIn(ANIMAL + ':1', nav)
        self.assertEqual([ANIMAL + ':3', ANIMAL + ':1'], nav['order'][1:])


class PlaylistsPerServerTest(KodiTestCase):
    """The old single Playlists entry - the selected server's - becomes that server's own (plan
    7.2b): in the sidebar and in its Manage Hubs config."""

    def test_the_sidebar_entry_and_order(self):
        nav = {'entries': ['/library/sections/watchlist', 'playlists', 'a:1'],
               'order': ['/library/sections/watchlist', 'playlists', 'a:1', 'a:2']}
        self.assertEqual((True, False), section_ids.migratePlaylists(nav, None, 'a'))
        self.assertEqual(['/library/sections/watchlist', 'a:playlists', 'a:1'], nav['entries'])
        self.assertEqual('a:playlists', nav['order'][1])
        self.assertEqual((False, False), section_ids.migratePlaylists(nav, None, 'a'))

    def test_its_hub_settings(self):
        hubs = {'playlists': {'custom': True, 'hubs': [{'catalog_id': 'playlists|playlists.audio'}],
                              'order': ['playlists|playlists.audio', 'playlists|playlists.video'],
                              'hidden': ['playlists|playlists.video']}}
        self.assertEqual((False, True), section_ids.migratePlaylists(None, hubs, 'a'))
        config = hubs['a:playlists']
        self.assertEqual('a:playlists|playlists.audio', config['hubs'][0]['catalog_id'])
        self.assertEqual(['a:playlists|playlists.video'], config['hidden'])
        self.assertNotIn('playlists', hubs)

    def test_a_servers_playlists_section_is_its_own(self):
        server = Server('a')
        section = home.playlistsSection(server)
        self.assertIs(section, home.playlistsSection(server))
        self.assertEqual('a:playlists', section_ids.sectionId(section))
        self.assertIs(server, section.server)
        self.assertTrue(home.isPlaylists(section))


class LegacyServerTest(KodiTestCase):
    """The server settings from before account-wide keys belong to: the one selected when the add-on
    last ran (plan Phase 9: nothing is selected any more)."""

    def check(self, settings, servers, selected=None):
        manager = mock.Mock(serversByUuid=servers, selectedServer=selected)
        with mock.patch.object(section_ids.plexapp, 'SERVERMANAGER', manager), \
                mock.patch.object(section_ids.plexapp, 'ACCOUNT', mock.Mock(ID='7')), \
                mock.patch.object(section_ids.util, 'getSetting',
                                  lambda key, default=None: settings.get(key, default)):
            return section_ids.legacyServer()

    def test_the_server_last_selected(self):
        animal, oscar = Server('a'), Server('o')
        self.assertIs(animal, self.check({'lastServerId.7': 'a'}, {'a': animal, 'o': oscar}, selected=oscar))

    def test_none_while_that_server_is_not_known_yet(self):
        self.assertIsNone(self.check({'lastServerId.7': 'a'}, {}, selected=Server('o')))
