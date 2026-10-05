# coding=utf-8
"""
Home from Plex's own Home rows (plan 7.2b): the request Plex's apps send, Home rows' saved ids, and a
custom hub config kept up to date with the rows Plex sends - new rows shown beside their neighbour,
Plex's "merge recently added" setting flipping, configs of before taken as they were meant.

Checked live (2026-10-05, PMS 1.43.3 and 1.43.4) before this was built:
- /hubs/promoted with pinnedContentDirectoryID and contentDirectoryID gives what Plex's apps show:
  the rows Plex has on Home for the user, merged or per library by Plex's setting, the libraries in
  the order sent; with merging off the pinned list alone doesn't limit a library's rows.
- Rows' identifiers carry a per-request pick (movie.genre.22.71) or, merged, the first pinned
  library (home.movies.recent.22).

Importing lib.windows.* starts lib.player's monitor thread unless abort_requested is set first.
"""

from __future__ import absolute_import

import xml.etree.ElementTree as ET
from unittest import mock

from kodienv import ENV

ENV.abort_requested = True
from lib.windows import home, hub_config, library, library_hubs, section_ids  # noqa: E402
from plexnet import plexserver  # noqa: E402

from .base import KodiTestCase  # noqa: E402

ANIMAL = 'animal-uuid-0000aaaa'
OSCAR = 'oscar-uuid-0000bbbb'


def row(identifier, server=ANIMAL, legacy=None):
    """(catalog_id, legacy_id, server, entry) as the window hands them to reconcile()."""
    if identifier == 'continueWatching':
        return ('continueWatching', 'continueWatching', '', {'catalog_id': 'continueWatching'})
    cid = u'{0}|{1}'.format(server, identifier)
    return (cid, u'{0}|{1}'.format(server, legacy) if legacy else cid, server, {'catalog_id': cid})


def shown(config):
    return [h['catalog_id'].split('|')[-1] for h in config['hubs']]


def hidden(config):
    return [cid.split('|')[-1] for cid in config['hidden']]


def cid(identifier):
    return identifier if identifier == 'continueWatching' else ANIMAL + '|' + identifier


def custom(*ids, **kw):
    """A config of these shown rows; with order=[ids] a config of today, whose 'order' has its hidden
    ones in their places too."""
    config = {'custom': True, 'hubs': [{'catalog_id': cid(i)} for i in ids]}
    if 'order' in kw:
        kw['order'] = [cid(i) for i in kw['order']]
    config.update(kw)
    return config


def ordered(config):
    return [c.split('|')[-1] for c in config['order']]


class RowIdTest(KodiTestCase):
    def test_a_librarys_row_keeps_its_library(self):
        self.assertEqual('movie.recentlyadded.22', hub_config.homeRowId('movie.recentlyadded.22'))

    def test_a_rows_pick_is_dropped(self):
        self.assertEqual('movie.genre.22', hub_config.homeRowId('movie.genre.22.71'))
        self.assertEqual('movie.by.actor.or.director.22',
                         hub_config.homeRowId('movie.by.actor.or.director.22.155600'))

    def test_a_merged_row_drops_its_first_library(self):
        self.assertEqual('home.movies.recent', hub_config.homeRowId('home.movies.recent.22'))
        self.assertEqual('home.movies.recent', hub_config.homeRowId('home.movies.recent.2'))

    def test_homes_own_and_continue_watching_unchanged(self):
        for identifier in ('home.playlists', 'continueWatching', 'home.movies.recent'):
            self.assertEqual(identifier, hub_config.homeRowId(identifier))

    def test_a_collection_keeps_its_collection(self):
        self.assertEqual('custom.collection.2.63624', hub_config.homeRowId('custom.collection.2.63624'))

    def test_films_and_movies_rows_stay_apart_on_home(self):
        class Hub(object):
            def __init__(self, identifier):
                self.hubIdentifier = identifier
                self.server = mock.Mock(uuid=ANIMAL)
        ids = [section_ids.hubCatalogId(Hub(i), home.home_section)
               for i in ('movie.recentlyadded.22', 'movie.recentlyadded.2')]
        self.assertEqual([ANIMAL + '|movie.recentlyadded.22', ANIMAL + '|movie.recentlyadded.2'], ids)


class ReconcileTest(KodiTestCase):
    def test_a_new_row_goes_after_its_neighbour_wherever_that_is(self):
        # the user put Films' Recently Released last; Plex now sends Recently Added after it
        config = custom('continueWatching', 'movie.genre.22', 'movie.recentlyreleased.22', hidden=[])
        rows = [row('continueWatching'), row('movie.recentlyreleased.22'), row('movie.recentlyadded.22'),
                row('movie.genre.22')]
        self.assertTrue(hub_config.reconcile(config, rows))
        self.assertEqual(['continueWatching', 'movie.genre.22', 'movie.recentlyreleased.22',
                          'movie.recentlyadded.22'], shown(config))
        self.assertEqual([0, 1, 2, 3], [h['order'] for h in config['hubs']])

    def test_a_new_first_row_goes_before_the_next(self):
        config = custom('movie.genre.22', 'continueWatching', hidden=[])
        hub_config.reconcile(config, [row('movie.recentlyreleased.22'), row('movie.genre.22')])
        self.assertEqual(['movie.recentlyreleased.22', 'movie.genre.22', 'continueWatching'], shown(config))

    def test_new_rows_in_a_run_stay_in_plexs_order(self):
        config = custom('continueWatching', hidden=[])
        hub_config.reconcile(config, [row('continueWatching'), row('tv.recentlyaired.18'),
                                      row('tv.recentlyadded.18', server=OSCAR)])
        self.assertEqual(['continueWatching', 'tv.recentlyaired.18', 'tv.recentlyadded.18'], shown(config))

    def test_a_hidden_row_stays_hidden(self):
        config = custom('continueWatching', hidden=[ANIMAL + '|movie.genre.22'], reconciled=['', ANIMAL],
                        order=['continueWatching', 'movie.genre.22'], ordered=False)
        self.assertFalse(hub_config.reconcile(config, [row('continueWatching'), row('movie.genre.22')]))
        self.assertEqual(['continueWatching'], shown(config))

    def test_a_row_plex_stops_sending_keeps_its_place(self):
        config = custom('continueWatching', 'movie.genre.22', 'home.playlists', hidden=[])
        hub_config.reconcile(config, [row('continueWatching'), row('home.playlists')])
        self.assertEqual(['continueWatching', 'movie.genre.22', 'home.playlists'], shown(config))

    def test_nothing_new_changes_nothing(self):
        config = custom('continueWatching', 'movie.genre.22', hidden=[], reconciled=['', ANIMAL],
                        order=['continueWatching', 'movie.genre.22'], ordered=False)
        self.assertFalse(hub_config.reconcile(config, [row('continueWatching'), row('movie.genre.22')]))

    def test_no_custom_config_is_left_alone(self):
        config = {'custom': False, 'hubs': []}
        self.assertFalse(hub_config.reconcile(config, [row('movie.genre.22')]))
        self.assertEqual({'custom': False, 'hubs': []}, config)


class MergeFlipTest(KodiTestCase):
    """Plex's "merge recently added" setting flipped: the other form takes the state and the place
    (the user's rule, 2026-10-05)."""

    def test_merging_off_the_libraries_rows_take_the_merged_rows_place(self):
        config = custom('continueWatching', 'home.movies.recent', 'movie.genre.22', hidden=[])
        hub_config.reconcile(config, [row('continueWatching'), row('movie.recentlyadded.22'),
                                      row('movie.genre.22'), row('movie.recentlyadded.2')])
        self.assertEqual(['continueWatching', 'home.movies.recent', 'movie.recentlyadded.22',
                          'movie.recentlyadded.2', 'movie.genre.22'], shown(config))

    def test_merging_off_with_the_merged_row_hidden_hides_them(self):
        config = custom('continueWatching', hidden=[ANIMAL + '|home.movies.recent'])
        hub_config.reconcile(config, [row('continueWatching'), row('movie.recentlyadded.22'),
                                      row('movie.recentlyadded.2')])
        self.assertEqual(['continueWatching'], shown(config))
        self.assertEqual(['home.movies.recent', 'movie.recentlyadded.22', 'movie.recentlyadded.2'],
                         hidden(config))

    def test_merging_on_the_merged_row_takes_the_first_shown_ones_place(self):
        config = custom('continueWatching', 'movie.genre.22', 'movie.recentlyadded.2', hidden=[ANIMAL + '|movie.recentlyadded.22'])
        hub_config.reconcile(config, [row('continueWatching'), row('home.movies.recent'), row('movie.genre.22')])
        self.assertEqual(['continueWatching', 'movie.genre.22', 'home.movies.recent', 'movie.recentlyadded.2'],
                         shown(config))

    def test_merging_on_with_every_librarys_row_hidden_hides_it(self):
        config = custom('continueWatching', hidden=[ANIMAL + '|movie.recentlyadded.22', ANIMAL + '|movie.recentlyadded.2'])
        hub_config.reconcile(config, [row('continueWatching'), row('home.movies.recent')])
        self.assertEqual(['continueWatching'], shown(config))
        self.assertIn('home.movies.recent', hidden(config))

    def test_flipping_back_restores_what_was_saved(self):
        # merged row hidden by the user before; the per-library rows shown since: back on, the
        # merged row's own saved state wins
        config = custom('continueWatching', 'movie.recentlyadded.22', hidden=[ANIMAL + '|home.movies.recent'],
                        reconciled=['', ANIMAL],
                        order=['continueWatching', 'home.movies.recent', 'movie.recentlyadded.22'], ordered=False)
        self.assertFalse(hub_config.reconcile(config, [row('continueWatching'), row('home.movies.recent')]))
        self.assertEqual(['continueWatching', 'movie.recentlyadded.22'], shown(config))

    def test_another_servers_rows_are_not_counterparts(self):
        config = custom('continueWatching', 'home.movies.recent', hidden=[])
        hub_config.reconcile(config, [row('continueWatching'), row('home.movies.recent'),
                                      row('movie.recentlyadded.1', server=OSCAR)])
        self.assertEqual(['continueWatching', 'home.movies.recent', 'movie.recentlyadded.1'], shown(config))

    def test_each_type_pairs_with_its_own(self):
        self.assertEqual([], hub_config.counterparts(ANIMAL + '|home.movies.recent', [ANIMAL + '|tv.recentlyadded.18']))
        self.assertEqual([ANIMAL + '|tv.recentlyadded.18'],
                         hub_config.counterparts(ANIMAL + '|home.television.recent', [ANIMAL + '|tv.recentlyadded.18']))
        self.assertEqual([ANIMAL + '|home.music.recent'],
                         hub_config.counterparts(ANIMAL + '|music.recent.added.10', [ANIMAL + '|home.music.recent']))


class LegacyConfigTest(KodiTestCase):
    """Configs from before hidden rows were kept: what they didn't list was hidden, and stays so."""

    def test_a_librarys_unlisted_rows_are_hidden(self):
        config = {'custom': True, 'hubs': [{'catalog_id': 'lib|movie.inprogress'}]}
        rows = [('lib|movie.inprogress', 'lib|movie.inprogress', ANIMAL, {'catalog_id': 'lib|movie.inprogress'}),
                ('lib|movie.genre', 'lib|movie.genre', ANIMAL, {'catalog_id': 'lib|movie.genre'})]
        self.assertTrue(hub_config.reconcile(config, rows))
        self.assertEqual(['lib|movie.inprogress'], [h['catalog_id'] for h in config['hubs']])
        self.assertEqual(['lib|movie.genre'], config['hidden'])
        # and from then on a row it hasn't seen is new
        hub_config.reconcile(config, rows + [('lib|movie.curated', 'lib|movie.curated', ANIMAL,
                                              {'catalog_id': 'lib|movie.curated'})])
        self.assertEqual(['lib|movie.inprogress', 'lib|movie.curated'], [h['catalog_id'] for h in config['hubs']])

    def test_homes_old_ids_are_renamed_in_place(self):
        config = custom('home.VIRTUAL.movies.recentlyreleased', 'continueWatching', servers=[ANIMAL])
        hub_config.reconcile(config, [row('continueWatching'),
                                      row('movie.recentlyreleased.22', legacy='home.VIRTUAL.movies.recentlyreleased'),
                                      row('movie.genre.22', legacy='movie.genre')])
        self.assertEqual(['movie.recentlyreleased.22', 'continueWatching'], shown(config))
        self.assertEqual(['movie.genre.22'], hidden(config))

    def test_two_rows_once_under_one_old_id_both_take_its_place(self):
        # Films' and Movies' Recently Released were both movie.recentlyreleased on Home
        config = custom('movie.recentlyreleased', 'continueWatching', servers=[ANIMAL])
        hub_config.reconcile(config, [row('continueWatching'),
                                      row('movie.recentlyreleased.22', legacy='movie.recentlyreleased'),
                                      row('movie.recentlyreleased.2', legacy='movie.recentlyreleased')])
        self.assertEqual(['movie.recentlyreleased.22', 'movie.recentlyreleased.2', 'continueWatching'], shown(config))

    def test_a_server_the_old_home_config_did_not_cover_has_new_rows(self):
        config = custom('continueWatching', 'home.movies.recent', servers=[ANIMAL])
        hub_config.reconcile(config, [row('continueWatching'), row('home.movies.recent'), row('home.music.recent'),
                                      row('home.movies.recent', server=OSCAR)])
        self.assertEqual(['continueWatching', 'home.movies.recent', 'home.movies.recent'], shown(config))
        self.assertEqual([OSCAR + '|home.movies.recent'], [h['catalog_id'] for h in config['hubs']][2:])
        self.assertEqual(['home.music.recent'], hidden(config))

    def test_a_covered_server_offline_at_first_is_taken_the_old_way_later(self):
        config = custom('continueWatching', servers=[ANIMAL, OSCAR])
        hub_config.reconcile(config, [row('continueWatching'), row('home.music.recent')])
        self.assertEqual([ANIMAL, ''], sorted(config['reconciled'], reverse=True))
        hub_config.reconcile(config, [row('continueWatching'), row('home.music.recent'),
                                      row('home.movies.recent', server=OSCAR)])
        self.assertEqual(['continueWatching'], shown(config))
        self.assertIn(OSCAR + '|home.movies.recent', config['hidden'])


class MoveTest(KodiTestCase):
    def test_a_move_among_the_listed_rows_leaves_the_others_in_place(self):
        config = custom('a', 'gone', 'b', 'c')
        listed = [ANIMAL + '|a', ANIMAL + '|b', ANIMAL + '|c']
        self.assertTrue(hub_config.move(config, listed, 2, 0))
        self.assertEqual(['c', 'gone', 'a', 'b'], shown(config))

    def test_hidden_and_shown_again_in_its_place(self):
        config = custom('a', 'b', 'c', hidden=[], order=['a', 'b', 'c'])
        hub_config.hide(config, ANIMAL + '|b')
        self.assertEqual((['a', 'c'], ['b'], ['a', 'b', 'c']), (shown(config), hidden(config), ordered(config)))
        hub_config.show(config, {'catalog_id': ANIMAL + '|b'})
        self.assertEqual((['a', 'b', 'c'], []), (shown(config), hidden(config)))

    def test_a_hidden_row_moves_too(self):
        config = custom('a', 'c', hidden=[ANIMAL + '|b'], order=['a', 'b', 'c'])
        listed = [cid(i) for i in ('a', 'b', 'c')]
        hub_config.move(config, listed, 1, 0)
        self.assertEqual((['b', 'a', 'c'], ['a', 'c']), (ordered(config), shown(config)))
        hub_config.show(config, {'catalog_id': ANIMAL + '|b'})
        self.assertEqual(['b', 'a', 'c'], shown(config))

    def test_a_new_config_shows_every_row_in_order(self):
        config = hub_config.newConfig([{'catalog_id': cid('a'), 'title': 'A'}, {'catalog_id': cid('b')}])
        self.assertEqual((['a', 'b'], [], ['a', 'b']), (shown(config), hidden(config), ordered(config)))
        self.assertEqual('A', config['hubs'][0]['title'])


class OrderTest(KodiTestCase):
    """Ordering and visibility apart (the user, 2026-10-05): every row has a place, shown or hidden."""

    def test_a_new_row_goes_after_its_neighbour_even_a_hidden_one(self):
        config = custom('continueWatching', 'movie.genre.22', hidden=[ANIMAL + '|movie.recentlyreleased.22'],
                        reconciled=['', ANIMAL],
                        order=['continueWatching', 'movie.genre.22', 'movie.recentlyreleased.22'])
        hub_config.reconcile(config, [row('continueWatching'), row('movie.recentlyreleased.22'),
                                      row('movie.recentlyadded.22'), row('movie.genre.22')])
        self.assertEqual(['continueWatching', 'movie.genre.22', 'movie.recentlyreleased.22', 'movie.recentlyadded.22'],
                         ordered(config))
        self.assertEqual(['continueWatching', 'movie.genre.22', 'movie.recentlyadded.22'], shown(config))

    def test_a_config_of_before_gives_its_hidden_rows_their_neighbours_place(self):
        # shown rows in the user's order; the hidden ones had none
        config = custom('continueWatching', 'movie.genre.22', 'tv.recentlyaired.18',
                        hidden=[ANIMAL + '|movie.recentlyreleased.22', ANIMAL + '|home.playlists'], reconciled=['', ANIMAL])
        self.assertTrue(hub_config.reconcile(config, [
            row('continueWatching'), row('movie.recentlyreleased.22'), row('movie.genre.22'),
            row('tv.recentlyaired.18'), row('home.playlists')]))
        self.assertEqual(['continueWatching', 'movie.recentlyreleased.22', 'movie.genre.22', 'tv.recentlyaired.18',
                          'home.playlists'], ordered(config))
        self.assertEqual(['continueWatching', 'movie.genre.22', 'tv.recentlyaired.18'], shown(config))

    def test_merging_off_with_the_merged_row_hidden_they_take_its_place(self):
        config = custom('continueWatching', 'movie.genre.22', hidden=[ANIMAL + '|home.movies.recent'],
                        reconciled=['', ANIMAL], order=['continueWatching', 'home.movies.recent', 'movie.genre.22'])
        hub_config.reconcile(config, [row('continueWatching'), row('movie.recentlyadded.22'),
                                      row('movie.genre.22'), row('movie.recentlyadded.2')])
        self.assertEqual(['continueWatching', 'home.movies.recent', 'movie.recentlyadded.22', 'movie.recentlyadded.2',
                          'movie.genre.22'], ordered(config))
        self.assertEqual(['continueWatching', 'movie.genre.22'], shown(config))


def server(uuid, name):
    s = mock.Mock(uuid=uuid, offline=False, gone=False)
    s.name = name
    return s


class Item(object):
    type = 'movie'

    def __init__(self, section='22'):
        self.section = section

    def getLibrarySectionId(self):
        return self.section


class Hub(object):
    def __init__(self, identifier, items, srv, title=None):
        self.hubIdentifier = identifier
        self.items = list(items)
        self.server = srv
        self.title = title or identifier

    def getCleanHubIdentifier(self, is_home=False):
        return self.hubIdentifier


class ManageHubsCase(KodiTestCase):
    """Manage Hubs on Home with Plex's rows: a row the config shows that Plex no longer sends is
    left out, its place kept (the user's choice, 2026-10-05); a library's row Plex sends empty this
    time (its pick found nothing) is offered, Plex's merged rows with no library behind them
    aren't."""

    def setUp(self):
        super(ManageHubsCase, self).setUp()
        self.animal, self.oscar = server(ANIMAL, 'Animal'), server(OSCAR, 'Oscar')
        self.animal.hubs = mock.Mock(return_value=[Hub('continueWatching', [Item()], self.animal),
                                                   Hub('movie.recentlyadded.22', [Item()], self.animal,
                                                       title='Recently Added in Films'),
                                                   Hub('movie.by.actor.or.director.22.155600', [], self.animal,
                                                       title='Top Movies with A$AP Rocky'),
                                                   Hub('home.music.recent.10', [], self.animal)])
        manager = mock.Mock(selectedServer=self.animal, serversByUuid={ANIMAL: self.animal, OSCAR: self.oscar})
        manager.getServers.return_value = [self.animal]
        patcher = mock.patch.object(library.plexapp, 'SERVERMANAGER', manager)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.win = library.LibraryWindow.__new__(library.LibraryWindow)
        self.win.saveHubSettings = lambda: None
        self.win.sectionHubs = {}
        self.win.hubSettings = {'__home__': {'custom': True, 'hidden': [], 'hubs': [
            {'catalog_id': 'continueWatching'},
            {'catalog_id': ANIMAL + '|movie.genre.22', 'title': 'Top Movies in (Genre)'},
            {'catalog_id': ANIMAL + '|movie.recentlyadded.22'}]}}
        self.win._homeServers = lambda: [(self.animal, ['22'])]
        self.win._homeRowPositions = lambda: {}
        self.win._discoverHubsSync(home.home_section)

    def rows(self):
        return [o['display'] for o in self.win._buildHubSettingsOptions(home.home_section, 'Home')
                if o and o.get('key') == 'toggle_hub']


class ManageHubsTest(ManageHubsCase):
    def test_hidden_rows_in_their_place_unnumbered(self):
        hub_config.hide(self.win.hubSettings['__home__'], ANIMAL + '|movie.recentlyadded.22')
        self.win.hubSettings['__home__']['order'].insert(1, ANIMAL + '|movie.recentlyadded.22')
        self.win.hubSettings['__home__']['order'].pop()
        self.assertEqual([u'1. continueWatching', u'Recently Added in Films'], self.rows()[:2])

    def test_a_row_no_longer_sent_is_left_out_with_its_place_kept(self):
        self.assertEqual([u'1. continueWatching', u'2. Recently Added in Films'], self.rows()[:2])
        self.win._moveHubToPosition(ANIMAL + '|movie.recentlyadded.22', home.home_section, 1, 0, None)
        self.assertEqual([ANIMAL + '|movie.recentlyadded.22', ANIMAL + '|movie.genre.22', 'continueWatching'],
                         [h['catalog_id'] for h in self.win.hubSettings['__home__']['hubs']][:3])

    def test_a_librarys_empty_row_is_offered_homes_own_empty_one_is_not(self):
        self.assertIn(ANIMAL + '|movie.by.actor.or.director.22', self.win.availableHubs)
        self.assertNotIn(ANIMAL + '|home.music.recent', self.win.availableHubs)


class HomeRequestTest(KodiTestCase):
    """Home asks as Plex's apps do: /hubs/promoted with both library lists; Continue Watching with
    the one it honours."""

    def test_home_and_continue_watching_requests(self):
        srv = plexserver.PlexServer.__new__(plexserver.PlexServer)
        srv.currentHubs = None
        asked = []

        def query(path, params=None, **kw):
            asked.append((path.split('?')[0], dict(params or {})))
            return ET.fromstring('<MediaContainer size="0"/>')
        srv.query = query
        srv.hubs(None, count=20, section_ids=['22', '2', 'playlists'])
        (promoted, home_params), (cw, cw_params) = asked
        self.assertEqual('/hubs/promoted', promoted)
        self.assertEqual('22,2,playlists', home_params['contentDirectoryID'])
        self.assertEqual('22,2', home_params['pinnedContentDirectoryID'])
        self.assertEqual('/hubs/continueWatching', cw)
        self.assertNotIn('pinnedContentDirectoryID', cw_params)
        self.assertEqual('22,2,playlists', cw_params['contentDirectoryID'])

    def test_a_merged_rows_library_is_not_named(self):
        self.assertIsNone(library_hubs.HubsMixin.promotedHubSourceKey('home.movies.recent.22'))
        self.assertEqual('22', library_hubs.HubsMixin.promotedHubSourceKey('movie.recentlyreleased.22'))


class RowsOnScreenTest(ManageHubsCase):
    """Manage Hubs reloads Home on closing when the rows it was sent aren't the rows on screen: Plex's
    toggles or merge setting changed since Home was shown (live 2026-10-05)."""

    def setUp(self):
        super(RowsOnScreenTest, self).setUp()
        self.win.section = home.home_section
        self.win._hubsSettingsChanged = False

    def test_the_same_rows_reload_nothing(self):
        films = Hub('movie.recentlyadded.22', [Item()], self.animal)
        self.win.sectionHubs = {'__home__': [Hub('continueWatching', [Item()], self.animal), films]}
        self.win._noteRowsOnScreenStale(home.home_section)
        self.assertFalse(self.win._hubsSettingsChanged)

    def test_other_rows_reload_home(self):
        merged = Hub('home.movies.recent.22', [Item()], self.animal)
        self.win.sectionHubs = {'__home__': [Hub('continueWatching', [Item()], self.animal), merged]}
        self.win._noteRowsOnScreenStale(home.home_section)
        self.assertTrue(self.win._hubsSettingsChanged)

    def test_another_section_on_screen_is_left_alone(self):
        self.win.section = mock.Mock(key='22', server=self.animal)
        self.win._noteRowsOnScreenStale(home.home_section)
        self.assertFalse(self.win._hubsSettingsChanged)


class SidebarChangeTest(KodiTestCase):
    def window(self, section, mode='recommended'):
        win = library.LibraryWindow.__new__(library.LibraryWindow)
        win.section, win.contentMode, win._backStack = section, mode, []
        win.closing = win._shuttingDown = False
        win.refreshHubsInPlace = mock.Mock(return_value=True)
        return win

    def test_home_showing_refreshes_its_rows_in_place(self):
        win = self.window(home.home_section)
        win.reloadHomeRows('test')
        win.refreshHubsInPlace.assert_called_once_with('test')

    def test_not_home_no_refresh(self):
        win = self.window(mock.Mock(key='22'))
        win.reloadHomeRows('test')
        win.refreshHubsInPlace.assert_not_called()


class GenericTitleTest(KodiTestCase):
    """Rows whose title names what they picked this time go by their kind in Manage Hubs (the user,
    2026-10-05; the rows checked against Animal)."""

    def test_a_pick_becomes_its_kind_in_square_brackets(self):
        self.assertEqual('Top Movies in [Genre]', hub_config.genericTitle('movie.genre.22.71'))
        self.assertEqual('Top Movies by [Actor or Director]',
                         hub_config.genericTitle('movie.by.actor.or.director.22.155600'))
        self.assertEqual('Most Played in [Month]', hub_config.genericTitle('music.popular.10'))
        self.assertEqual('More in [Genre]', hub_config.genericTitle('tv.moreingenre.18'))

    def test_the_servers_own_titles_first(self):
        self.assertEqual('Meilleurs films [Genre]',
                         hub_config.genericTitle('movie.genre.22.71', {'movie.genre': 'Meilleurs films (Genre)'}))

    def test_a_row_whose_title_does_not_change_keeps_it(self):
        for identifier in ('movie.recentlyadded.22', 'home.movies.recent.22', 'continueWatching', 'tv.toprated.18'):
            self.assertIsNone(hub_config.genericTitle(identifier, {'tv.toprated': 'Top Rated TV'}), identifier)

    def test_rows_that_pick_per_request(self):
        self.assertTrue(hub_config.picksPerRequest('movie.genre.22.71'))
        self.assertTrue(hub_config.picksPerRequest('movie.by.actor.or.director.22.155600'))
        for identifier in ('movie.genre.22', 'music.popular.10', 'home.movies.recent.22',
                           'custom.collection.2.63624', 'continueWatching'):
            self.assertFalse(hub_config.picksPerRequest(identifier), identifier)


class ManageHubsTitlesTest(ManageHubsCase):
    def test_a_picked_rows_title_is_its_kind_and_it_asks_as_home_does(self):
        self.animal.hubs.return_value.append(Hub('movie.genre.22.71', [Item()], self.animal, title='Top Movies in Musical'))
        self.win._discoverHubsSync(home.home_section)
        self.assertEqual('Top Movies in [Genre]', self.win.availableHubs[ANIMAL + '|movie.genre.22']['title'])
        self.assertEqual(home.HUB_ROW_MAX_ITEMS, self.animal.hubs.call_args[1]['count'])

    def test_a_pick_empty_this_time_reloads_nothing(self):
        self.win.section = home.home_section
        self.win._hubsSettingsChanged = False
        self.win.hubSettings = {}
        self.animal.hubs.return_value.append(Hub('movie.genre.22.71', [Item()], self.animal))
        self.win._discoverHubsSync(home.home_section)
        # on Home it came back empty (not shown); the dialog's request found one
        self.win.sectionHubs = {'__home__': [Hub('continueWatching', [Item()], self.animal),
                                             Hub('movie.recentlyadded.22', [Item()], self.animal)]}
        self.win._noteRowsOnScreenStale(home.home_section)
        self.assertFalse(self.win._hubsSettingsChanged)


class SavedOrderTest(KodiTestCase):
    """Visibility and order saved apart (the user, 2026-10-05): hiding a row saves no order - it
    keeps following the server's (on Home the sidebar's) until a row is moved."""

    rows = [row('continueWatching'), row('movie.recentlyreleased.22'), row('movie.genre.22'), row('tv.recentlyaired.18')]

    def test_hiding_keeps_the_servers_order(self):
        config = hub_config.newConfig([r[3] for r in self.rows])
        hub_config.hide(config, ANIMAL + '|movie.genre.22')
        self.assertFalse(hub_config.hasOrder(config))
        # the sidebar moved TV above Films: the server's order changes, and so does the config's
        hub_config.reconcile(config, [self.rows[0], self.rows[3], self.rows[1], self.rows[2]])
        self.assertEqual(['continueWatching', 'tv.recentlyaired.18', 'movie.recentlyreleased.22'], shown(config))
        self.assertEqual(['movie.genre.22'], hidden(config))

    def test_moving_a_row_saves_the_order(self):
        config = hub_config.newConfig([r[3] for r in self.rows])
        hub_config.move(config, [r[0] for r in self.rows], 3, 1)
        self.assertTrue(hub_config.hasOrder(config))
        hub_config.reconcile(config, [self.rows[0], self.rows[3], self.rows[2], self.rows[1]])
        self.assertEqual(['continueWatching', 'tv.recentlyaired.18', 'movie.recentlyreleased.22', 'movie.genre.22'],
                         shown(config))

    def test_a_row_not_sent_keeps_its_place_after_the_one_it_followed(self):
        config = hub_config.newConfig([r[3] for r in self.rows])
        hub_config.reconcile(config, [self.rows[0], self.rows[3], self.rows[1]])
        self.assertEqual(['continueWatching', 'tv.recentlyaired.18', 'movie.recentlyreleased.22', 'movie.genre.22'],
                         ordered(config))

    def test_a_config_from_before_in_the_servers_order_has_none(self):
        config = custom('continueWatching', 'movie.recentlyreleased.22', 'tv.recentlyaired.18',
                        hidden=[ANIMAL + '|movie.genre.22'], reconciled=['', ANIMAL])
        hub_config.reconcile(config, self.rows)
        self.assertFalse(hub_config.hasOrder(config))
        self.assertEqual(['movie.genre.22'], hidden(config))

    def test_a_config_from_before_in_its_own_order_keeps_it(self):
        config = custom('continueWatching', 'tv.recentlyaired.18', 'movie.recentlyreleased.22',
                        hidden=[ANIMAL + '|movie.genre.22'], reconciled=['', ANIMAL])
        hub_config.reconcile(config, self.rows)
        self.assertTrue(hub_config.hasOrder(config))
        self.assertEqual(['continueWatching', 'tv.recentlyaired.18', 'movie.recentlyreleased.22'], shown(config))

    def test_one_converted_this_week_is_checked_too(self):
        # 'order' already, no 'ordered' yet
        config = custom('continueWatching', 'movie.recentlyreleased.22', 'movie.genre.22', 'tv.recentlyaired.18',
                        hidden=[], reconciled=['', ANIMAL],
                        order=['continueWatching', 'movie.recentlyreleased.22', 'movie.genre.22', 'tv.recentlyaired.18'])
        hub_config.reconcile(config, self.rows)
        self.assertFalse(hub_config.hasOrder(config))


class RowLibraryTest(KodiTestCase):
    def test_the_entry_each_row_is_from(self):
        for identifier, library in (('movie.genre.22.71', '22'), ('home.movies.recent.22', '22'),
                                    ('tv.recentlyaired.18', '18'), ('home.playlists', 'playlists'),
                                    ('continueWatching', None), ('home.ondeck', None)):
            self.assertEqual(library, hub_config.rowLibrary(identifier), identifier)


class LibraryRequestTest(KodiTestCase):
    def test_a_library_asks_for_its_playlists_row(self):
        # Plex sends "Library Playlists" only when asked, as Plex Web does (live 2026-10-05)
        srv = plexserver.PlexServer.__new__(plexserver.PlexServer)
        srv.currentHubs = None
        asked = []

        def query(path, params=None, **kw):
            asked.append((path, dict(params or {})))
            return ET.fromstring('<MediaContainer size="0"/>')
        srv.query = query
        srv.hubs('23', count=20)
        self.assertEqual([('/hubs/sections/23', {'includeMarkers': 1, 'includeLibraryPlaylists': 1, 'count': 20})],
                         asked)
