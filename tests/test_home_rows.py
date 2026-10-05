# coding=utf-8
"""
Home's rows from every server with libraries in the sidebar (Phase 7 of the libraries-from-every-
server plan): each server asked together for its sidebar libraries' rows, Continue Watching merged
into one row, one Home order for every server's rows, and the server named after a row's title.

Checked live (2026-10-04) before this was built: PMS ignores (1.43.3) or half-honours (1.43.4) the
pinnedContentDirectoryID filter Home used to send; contentDirectoryID limits every row on both, so
it's sent, and each row's items are still checked against the libraries asked for.

Importing lib.windows.* starts lib.player's monitor thread unless abort_requested is set first.
"""

from __future__ import absolute_import

import threading
from unittest import mock

from kodienv import ENV

ENV.abort_requested = True
from lib.windows import home, library, library_hubs, section_ids  # noqa: E402
from plexnet import plexobjects  # noqa: E402

from .base import KodiTestCase  # noqa: E402

ANIMAL = 'animal-uuid-0000aaaa'
OSCAR = 'oscar-uuid-0000bbbb'


def server(uuid, name, offline=False, connected=True):
    s = mock.Mock(uuid=uuid, offline=offline, gone=False, pendingReachabilityRequests=0)
    s.name = name
    s.activeConnection = connected and mock.Mock() or None
    return s


class Item(object):
    def __init__(self, title, section=None, viewed=0, guid=None):
        self.title = title
        self._section = section
        self.attrs = {'lastViewedAt': str(viewed) if viewed else '', 'guid': guid or 'plex://' + title}
        self.lastViewedAt = plexobjects.PlexValue(str(viewed))
        self.type = 'movie'

    def get(self, key, default=None):
        return self.attrs.get(key) or default

    def getLibrarySectionId(self):
        return self._section

    def __repr__(self):
        return self.title


class Hub(object):
    def __init__(self, identifier, items, srv, title=None):
        self.hubIdentifier = identifier
        self.items = list(items)
        self.server = srv
        self.title = title or identifier
        self.more = plexobjects.PlexValue('1')
        self._identifier = None

    def getCleanHubIdentifier(self, is_home=False):
        return self.hubIdentifier

    def __repr__(self):
        return '<Hub {0}@{1}>'.format(self.hubIdentifier, self.server.name)


class CombineTest(KodiTestCase):
    def setUp(self):
        super(CombineTest, self).setUp()
        self.animal, self.oscar = server(ANIMAL, 'Animal'), server(OSCAR, 'Oscar')

    def test_continue_watching_is_one_row_most_recent_first(self):
        a = Hub('continueWatching', [Item('a1', '22', 300), Item('a2', '23', 100)], self.animal)
        o = Hub('continueWatching', [Item('o1', '1', 200)], self.oscar)
        merged = home.mergeContinueWatching([a, o])
        self.assertEqual(['a1', 'o1', 'a2'], [i.title for i in merged.items])
        self.assertFalse(merged.more.asBool(), 'no "See more": its later pages would be per server')

    def test_the_same_item_on_two_servers_once(self):
        a = Hub('continueWatching', [Item('film', '22', 300, guid='plex://movie/x')], self.animal)
        o = Hub('continueWatching', [Item('film', '1', 100, guid='plex://movie/x')], self.oscar)
        self.assertEqual(1, len(home.mergeContinueWatching([a, o]).items))

    def test_capped_at_a_rows_maximum(self):
        a = Hub('continueWatching', [Item('a%d' % i, '22', 1000 - i) for i in range(15)], self.animal)
        o = Hub('continueWatching', [Item('o%d' % i, '1', 500 - i) for i in range(15)], self.oscar)
        self.assertEqual(home.HUB_ROW_MAX_ITEMS, len(home.mergeContinueWatching([a, o]).items))

    def test_one_servers_continue_watching_stays_as_it_came(self):
        a = Hub('continueWatching', [Item('a1', '22', 300)], self.animal)
        self.assertIs(a, home.mergeContinueWatching([a]))
        self.assertTrue(a.more.asBool())

    def test_rows_continue_watching_first_then_each_server_in_sidebar_order(self):
        answers = {
            ANIMAL: [Hub('continueWatching', [Item('a1', '22', 300)], self.animal),
                     Hub('home.movies.recent', [Item('m', '22')], self.animal)],
            OSCAR: [Hub('home.television.recent', [Item('t', '2')], self.oscar),
                    Hub('continueWatching', [Item('o1', '1', 400)], self.oscar)],
        }
        rows = home.combineHomeHubs(answers, [(self.oscar, ['1', '2']), (self.animal, ['22'])])
        self.assertEqual(['continueWatching', 'home.television.recent', 'home.movies.recent'],
                         [h.hubIdentifier for h in rows])
        self.assertEqual(['o1', 'a1'], [i.title for i in rows[0].items])

    def test_items_from_libraries_not_asked_for_are_dropped(self):
        # a server that doesn't honour the filter (live: Oscar ignores pinnedContentDirectoryID)
        hub = Hub('home.movies.recent', [Item('in', '22'), Item('out', '2'), Item('playlist')], self.animal)
        home.keepLibraries(hub, ['22'])
        self.assertEqual(['in', 'playlist'], [i.title for i in hub.items])


class HomeHubsTaskTest(KodiTestCase):
    def run_task(self, servers, slow=()):
        got = []
        release = threading.Event()

        def hubs(srv):
            def answer(section, count=None, section_ids=None):
                if srv.uuid in slow:
                    release.wait(5)
                return [Hub('home.movies.recent', [Item(srv.name, section_ids[0])], srv)]
            return answer

        for srv, keys in servers:
            srv.hubs = mock.Mock(side_effect=hubs(srv))
        task = home.HomeHubsTask().setup(home.home_section, lambda section, rows: got.append(rows), servers)
        with mock.patch.object(home, 'HOME_LATE_SERVER_BUDGET', 0.2):
            task.run()
        release.set()
        return got[0]

    def test_every_server_asked_for_its_sidebar_libraries(self):
        animal, oscar = server(ANIMAL, 'Animal'), server(OSCAR, 'Oscar')
        rows = self.run_task([(animal, ['22', 'playlists']), (oscar, ['1'])])
        self.assertEqual(['Animal', 'Oscar'], [h.items[0].title for h in rows])
        animal.hubs.assert_called_once_with(None, count=home.HUB_ROW_MAX_ITEMS, section_ids=['22', 'playlists'])

    def test_an_offline_server_is_not_asked(self):
        animal, oscar = server(ANIMAL, 'Animal'), server(OSCAR, 'Oscar', offline=True)
        rows = self.run_task([(animal, ['22']), (oscar, ['1'])])
        oscar.hubs.assert_not_called()
        self.assertEqual(['Animal'], [h.items[0].title for h in rows])

    def test_a_slow_server_misses_the_bind_once_another_has_answered(self):
        animal, oscar = server(ANIMAL, 'Animal'), server(OSCAR, 'Oscar')
        rows = self.run_task([(animal, ['22']), (oscar, ['1'])], slow=[OSCAR])
        self.assertEqual(['Animal'], [h.items[0].title for h in rows])

    def test_one_whose_first_test_has_not_started_is_tested_now(self):
        # live 2026-10-04: at start-up the selected server is tested first and the others a few
        # seconds later, so Home bound without Oscar's rows
        animal = server(ANIMAL, 'Animal', connected=False)

        def test(force):
            animal.activeConnection = mock.Mock()
        animal.updateReachability = mock.Mock(side_effect=test)
        rows = self.run_task([(animal, ['22'])])
        animal.updateReachability.assert_called_once_with(True)
        self.assertEqual(['Animal'], [h.items[0].title for h in rows])

    def test_one_still_on_its_first_test_is_asked_once_it_has_a_connection(self):
        animal = server(ANIMAL, 'Animal', connected=False)
        animal.pendingReachabilityRequests = 2

        def connect():
            animal.activeConnection = mock.Mock()
        threading.Timer(0.1, connect).start()
        rows = self.run_task([(animal, ['22'])])
        self.assertEqual(['Animal'], [h.items[0].title for h in rows])


class HomeConfigTest(KodiTestCase):
    def test_per_server_configs_merge_into_one_selected_first(self):
        settings = {
            OSCAR + ':__home__': {'custom': True, 'hubs': [{'catalog_id': OSCAR + '|home.music.recent', 'order': 0},
                                                           {'catalog_id': OSCAR + '|continueWatching', 'order': 1}]},
            ANIMAL + ':__home__': {'custom': True, 'hubs': [{'catalog_id': ANIMAL + '|home.movies.recent', 'order': 1},
                                                            {'catalog_id': ANIMAL + '|continueWatching', 'order': 0}]},
            # Continue Watching listed by a second server's config too: it's one row now
            ANIMAL + ':22': {'custom': True, 'hubs': []},
        }
        self.assertTrue(section_ids.mergeHomeConfigs(settings, ANIMAL))
        merged = settings['__home__']
        self.assertEqual(['continueWatching', ANIMAL + '|home.movies.recent', OSCAR + '|home.music.recent'],
                         [h['catalog_id'] for h in merged['hubs']])
        self.assertEqual([0, 1, 2], [h['order'] for h in merged['hubs']])
        self.assertEqual([ANIMAL, OSCAR], merged['servers'])
        self.assertEqual(['__home__', ANIMAL + ':22'], sorted(settings))

    def test_a_server_without_a_custom_config_is_not_covered(self):
        settings = {ANIMAL + ':__home__': {'custom': True, 'hubs': []},
                    OSCAR + ':__home__': {'custom': False, 'hubs': []}}
        section_ids.mergeHomeConfigs(settings, ANIMAL)
        self.assertEqual([ANIMAL], settings['__home__']['servers'])

    def test_nothing_to_merge(self):
        settings = {'__home__': {'custom': True, 'hubs': []}}
        self.assertFalse(section_ids.mergeHomeConfigs(settings, ANIMAL))

    class Hubs(library_hubs.HubsMixin):
        def __init__(self, settings):
            self.hubSettings = settings
            self.sectionHubs = {}
            self.availableHubs = {}

        def saveHubSettings(self):
            pass

    def test_rows_of_a_server_the_config_does_not_cover_still_show(self):
        animal, oscar = server(ANIMAL, 'Animal'), server(OSCAR, 'Oscar')
        win = self.Hubs({'__home__': {'custom': True, 'servers': [ANIMAL],
                                      'hubs': [{'catalog_id': ANIMAL + '|home.movies.recent', 'order': 0}]}})
        hubs = [Hub('home.movies.recent', [], animal), Hub('home.music.recent', [], animal),
                Hub('home.music.recent', [], oscar)]
        win._reconcileWithHubs(home.home_section, hubs)
        self.assertEqual([False, True, False], [win.isHubHidden(h, home.home_section) for h in hubs])

    def test_continue_watching_follows_the_config_whatever_server_it_came_from(self):
        oscar = server(OSCAR, 'Oscar')
        win = self.Hubs({'__home__': {'custom': True, 'servers': [ANIMAL],
                                      'hubs': [{'catalog_id': ANIMAL + '|home.movies.recent', 'order': 0}]}})
        self.assertTrue(win.isHubHidden(Hub('continueWatching', [], oscar), home.home_section))

    def test_a_config_made_now_keeps_its_hidden_rows(self):
        animal, oscar = server(ANIMAL, 'Animal'), server(OSCAR, 'Oscar')
        win = self.Hubs({})
        win.sectionHubs['__home__'] = [Hub('a', [], animal), Hub('b', [], oscar)]
        manager = mock.Mock(serversByUuid={ANIMAL: animal, OSCAR: oscar})
        manager.getServers.return_value = [animal, oscar]
        with mock.patch.object(library_hubs.plexapp, 'SERVERMANAGER', manager):
            win._ensureCustomConfigExists(home.home_section)
        config = win.hubSettings['__home__']
        self.assertEqual([], config['hidden'])
        self.assertNotIn('servers', config)
        win._disableHub(OSCAR + '|b', home.home_section)
        self.assertEqual([ANIMAL + '|a'], [h['catalog_id'] for h in config['hubs']])
        self.assertEqual([OSCAR + '|b'], config['hidden'])


class LibraryWindowHomeTest(KodiTestCase):
    def setUp(self):
        super(LibraryWindowHomeTest, self).setUp()
        self.animal, self.oscar = server(ANIMAL, 'Animal'), server(OSCAR, 'Oscar')
        self.manager = mock.Mock(selectedServer=self.animal, serversByUuid={ANIMAL: self.animal, OSCAR: self.oscar})
        self.manager.getServers.return_value = [self.animal, self.oscar]
        patcher = mock.patch.object(library.plexapp, 'SERVERMANAGER', self.manager)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.win = library.LibraryWindow.__new__(library.LibraryWindow)

    def test_home_asks_each_server_for_its_sidebar_libraries_in_sidebar_order(self):
        self.win.navSettings = {'version': 2, 'libraries': {},
                                'entries': ['/library/sections/watchlist', OSCAR + ':1', ANIMAL + ':22',
                                            'playlists', OSCAR + ':2', 'gone-uuid:5']}
        self.assertEqual([(self.oscar, ['1', '2']), (self.animal, ['22', 'playlists'])], self.win._homeServers())

    def test_a_row_names_its_server_with_more_than_one(self):
        self.assertEqual('Oscar', self.win.homeRowServerName(Hub('home.movies.recent', [], self.oscar)))
        self.assertEqual('', self.win.homeRowServerName(Hub('continueWatching', [], self.oscar)))
        self.manager.getServers.return_value = [self.animal]
        self.assertEqual('', self.win.homeRowServerName(Hub('home.movies.recent', [], self.animal)))


class DiscoveryTest(KodiTestCase):
    """Manage Hubs' catalogue (LibraryWindow._discoverHubsSync()) is the managed section's own rows
    only: Home's from every Home server (labelled with their server on an account with more than
    one), or a library's own."""

    class Section(object):
        def __init__(self, key, title, srv, type_='movie'):
            self.key, self.title, self.server, self.type = key, title, srv, type_

    def setUp(self):
        super(DiscoveryTest, self).setUp()
        self.animal, self.oscar = server(ANIMAL, 'Animal'), server(OSCAR, 'Oscar')

        def rows(srv):
            return lambda section, count=None, section_ids=None: (
                [Hub('continueWatching', [Item('x', section_ids[0], 5)], srv),
                 Hub('home.movies.recent', [Item('y', section_ids[0])], srv, title='Recently Added Movies')]
                if section is None else [Hub('movie.recentlyadded', [Item('z', section)], srv, title='Recently Added')])
        self.animal.hubs = mock.Mock(side_effect=rows(self.animal))
        self.oscar.hubs = mock.Mock(side_effect=rows(self.oscar))
        manager = mock.Mock(selectedServer=self.animal, serversByUuid={ANIMAL: self.animal, OSCAR: self.oscar})
        manager.getServers.return_value = [self.animal, self.oscar]
        patcher = mock.patch.object(library.plexapp, 'SERVERMANAGER', manager)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.win = library.LibraryWindow.__new__(library.LibraryWindow)
        self.win.hubSettings = {}
        self.win.sectionHubs = {}
        self.win._homeServers = lambda: [(self.animal, ['22']), (self.oscar, ['1'])]

    def labels(self):
        return dict((cid, info['source_section_title']) for cid, info in self.win.availableHubs.items())

    def test_home_lists_every_home_servers_rows_with_their_server(self):
        self.win._discoverHubsSync(home.home_section)
        self.assertEqual({'continueWatching': 'Home',
                          ANIMAL + '|home.movies.recent': u'Home · Animal',
                          OSCAR + '|home.movies.recent': u'Home · Oscar'}, self.labels())

    def test_home_rows_name_their_server_only_with_more_than_one(self):
        # on the row's second line (Manage Hubs' card rows, as the Libraries picker's)
        self.win._discoverHubsSync(home.home_section)
        rows = self.win.availableHubs
        self.assertEqual('Oscar', rows[OSCAR + '|home.movies.recent']['server_label'])
        self.assertEqual('Animal', rows[ANIMAL + '|home.movies.recent']['server_label'])
        self.assertEqual('', rows['continueWatching']['server_label'])
        label = library.LibraryWindow._hubOptionLabel
        self.assertEqual(u'2. Recently Added Movies', label('x', rows[ANIMAL + '|home.movies.recent'], 2))

    def test_no_source_label_otherwise(self):
        label = library.LibraryWindow._hubOptionLabel
        self.assertEqual('1. Recently Added', label('x', {'title': 'Recently Added'}, 1))
        self.assertEqual('Sci-Fi (Collection)', label('x', {'title': 'Sci-Fi', 'identifier': 'custom.collection.1.2'}))

    def test_a_library_lists_its_own_rows_only(self):
        self.win._discoverHubsSync(self.Section('1', 'Films', self.oscar))
        self.assertEqual({OSCAR + ':1|movie.recentlyadded': 'Films'}, self.labels())
        self.animal.hubs.assert_not_called()


class ManageHomeTest(KodiTestCase):
    """The Manage Hubs dialog on Home after "Reset to default", with rows from a server Home hadn't
    shown yet (live 2026-10-04): every row is numbered in Home's default order, disabling one keeps
    the rest, and a row the server can't fill (Oscar's recent photos, with no photo library) isn't
    offered."""

    def setUp(self):
        super(ManageHomeTest, self).setUp()
        self.animal, self.oscar = server(ANIMAL, 'Animal'), server(OSCAR, 'Oscar')
        self.animal.hubs = mock.Mock(return_value=[Hub('continueWatching', [Item('c', '22', 5)], self.animal),
                                                   Hub('home.movies.recent', [Item('m', '22')], self.animal)])
        self.oscar.hubs = mock.Mock(return_value=[Hub('home.movies.recent', [Item('f', '1')], self.oscar),
                                                  Hub('home.photos.recent', [], self.oscar)])
        manager = mock.Mock(selectedServer=self.animal, serversByUuid={ANIMAL: self.animal, OSCAR: self.oscar})
        manager.getServers.return_value = [self.animal, self.oscar]
        for patcher in (mock.patch.object(library.plexapp, 'SERVERMANAGER', manager),
                        mock.patch.object(library.util, 'setSetting')):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.win = library.LibraryWindow.__new__(library.LibraryWindow)
        self.win.hubSettings = {}
        self.win.saveHubSettings = lambda: None
        # Home showed Animal's rows only (before the reset, or before Oscar answered)
        self.win.sectionHubs = {'__home__': [self.animal.hubs.return_value[1]]}
        self.win._homeServers = lambda: [(self.animal, ['22']), (self.oscar, ['1'])]
        self.win._discoverHubsSync(home.home_section)

    def rows(self):
        """Each row as its title, ' / ' its second line if it has one."""
        return [o['display'] + (o.get('properties', {}).get('subtitle') and ' / ' + o['properties']['subtitle'] or '')
                for o in self.win._buildHubSettingsOptions(home.home_section, 'Home') if o]

    def test_an_empty_row_is_not_offered(self):
        self.assertNotIn(OSCAR + '|home.photos.recent', self.win.availableHubs)

    def test_an_empty_row_in_the_config_is_not_offered_either(self):
        # it can't show, so there's nothing to take out (Plex's merged rows come back empty when no
        # pinned library feeds them)
        self.win.hubSettings = {'__home__': {'custom': True, 'hubs': [{'catalog_id': OSCAR + '|home.photos.recent'}]}}
        self.win._discoverHubsSync(home.home_section)
        self.assertNotIn(OSCAR + '|home.photos.recent', self.win.availableHubs)

    def test_every_row_numbered_in_homes_default_order(self):
        self.assertEqual([u'1. continueWatching', u'2. home.movies.recent / Animal',
                          u'3. home.movies.recent / Oscar'], self.rows()[:3])

    def choose(self, catalog_id, column):
        row = dict([o for o in self.win._buildHubSettingsOptions(home.home_section, 'Home')
                    if o and o.get('catalog_id') == catalog_id][0], column=column)
        optionsList = mock.Mock()
        optionsList.getSelectedPos.return_value = 1
        optionsList.__iter__ = lambda s: iter([])
        return self.win.onHubSettingToggle(optionsList, mock.Mock(dataSource=row))

    def test_the_toggle_tile_hides_and_shows(self):
        self.win._managingHubsForSection = home.home_section
        self.win._managingHubsForSectionTitle = 'Home'
        self.assertEqual('rebuild', self.choose(ANIMAL + '|home.movies.recent', 'pin')[0])
        self.assertEqual([ANIMAL + '|home.movies.recent'], self.win.hubSettings['__home__']['hidden'])
        rows = [o for o in self.win._buildHubSettingsOptions(home.home_section, 'Home') if o]
        hidden = [o for o in rows if o.get('catalog_id') == ANIMAL + '|home.movies.recent'][0]
        self.assertEqual(('1', True), (hidden['properties']['nomove'], hidden['indicator_dim']))
        self.choose(ANIMAL + '|home.movies.recent', 'pin')
        self.assertEqual([], self.win.hubSettings['__home__']['hidden'])

    def test_move_picks_up_a_shown_row_only(self):
        self.win._managingHubsForSection = home.home_section
        self.assertEqual('enter_move_mode', self.choose(OSCAR + '|home.movies.recent', 'move'))
        self.win._disableHub(OSCAR + '|home.movies.recent', home.home_section)
        self.assertIsNone(self.choose(OSCAR + '|home.movies.recent', 'move'))

    def test_disabling_one_keeps_the_rest(self):
        self.win._ensureCustomConfigExists(home.home_section)
        self.win._disableHub(ANIMAL + '|home.movies.recent', home.home_section)
        self.assertEqual(['continueWatching', OSCAR + '|home.movies.recent'],
                         [h['catalog_id'] for h in self.win.hubSettings['__home__']['hubs']])
        self.assertEqual([ANIMAL + '|home.movies.recent'], self.win.hubSettings['__home__']['hidden'])
