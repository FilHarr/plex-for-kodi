# coding=utf-8
"""
Search across servers (plan Phase 8): one search, wherever it's opened from, asks every server the
sidebar has libraries from - everything on each, no library scoping (the user, 2026-10-05: nothing
on screen says a search from inside a library would be any different, and the dialog's own type
buttons narrow it). One row per type, the servers' items merged by Plex's own relevance score, each
tile naming its server on a multi-server account.

Checked live before this was built (Animal and Oscar, 2026-10-05): /hubs/search answers in 60-150 ms
on the LAN, and every result carries a score.

Importing lib.windows.* starts lib.player's monitor thread unless abort_requested is set first.
"""

from __future__ import absolute_import

import json
import threading
from unittest import mock

from kodienv import ENV

ENV.abort_requested = True
from lib.windows import search  # noqa: E402
from plexnet import plexobjects  # noqa: E402

from .base import KodiTestCase  # noqa: E402


def server(uuid, name, offline=False):
    s = mock.Mock(uuid=uuid, offline=offline, gone=False)
    s.name = name
    return s


class Item(object):
    def __init__(self, title, score, srv=None):
        self.title = title
        self.attrs = {'score': score}
        self.server = srv

    def get(self, key, default=None):
        return self.attrs.get(key, default)


class Hub(object):
    def __init__(self, type_, title, items):
        self.type = type_
        self.title = title
        self.items = list(items)
        self.size = plexobjects.PlexValue(str(len(items)))


def titles(rows):
    return [(h.title, [i.title for i in h.items]) for h in rows]


class MergeTest(KodiTestCase):
    def test_one_row_per_type_by_score_best_first(self):
        animal = [Hub('movie', 'Movies', [Item('Alien', '0.93'), Item('Aliens', '0.53')]),
                  Hub('show', 'Shows', [Item('Alien: Earth', '0.53')])]
        oscar = [Hub('movie', 'Movies', [Item('The Lion King', '0.33'), Item('Alien Nation', '0.71')]),
                 Hub('actor', 'Actors', [Item('Alan Rickman', '0.32')])]
        rows = search.mergeResults([animal, oscar])
        self.assertEqual([('Movies', ['Alien', 'Alien Nation', 'Aliens', 'The Lion King']),
                          ('Shows', ['Alien: Earth']), ('Actors', ['Alan Rickman'])], titles(rows))
        self.assertEqual(4, rows[0].size.asInt())

    def test_a_tie_keeps_the_servers_order(self):
        rows = search.mergeResults([[Hub('movie', 'Movies', [Item('A copy', '0.5')])],
                                    [Hub('movie', 'Movies', [Item('O copy', '0.5')])]])
        self.assertEqual(['A copy', 'O copy'], [i.title for i in rows[0].items])


class FanOutTest(KodiTestCase):
    def test_every_server_asked_once_offline_ones_not(self):
        animal, oscar, down = server('a', 'Animal'), server('o', 'Oscar'), server('d', 'Down', offline=True)
        animal.hubs.return_value = [Hub('movie', 'Movies', [Item('Alien', '0.9')])]
        oscar.hubs.return_value = [Hub('movie', 'Movies', [Item('Alien Nation', '0.7')])]
        rows, missing = search.searchServers('alien', [animal, oscar, down])
        animal.hubs.assert_called_once_with(count=search.SEARCH_LIMIT, search_query='alien')
        oscar.hubs.assert_called_once_with(count=search.SEARCH_LIMIT, search_query='alien')
        down.hubs.assert_not_called()
        self.assertEqual([('Movies', ['Alien', 'Alien Nation'])], titles(rows))
        self.assertEqual(['Down'], missing)

    def test_a_server_that_fails_or_is_too_slow_is_left_out(self):
        animal, oscar, slow = server('a', 'Animal'), server('o', 'Oscar'), server('s', 'Slow')
        animal.hubs.return_value = [Hub('movie', 'Movies', [Item('Alien', '0.9')])]
        oscar.hubs.side_effect = Exception('no answer')
        release = threading.Event()
        self.addCleanup(release.set)
        slow.hubs.side_effect = lambda **kw: release.wait(5) and []
        with mock.patch.object(search, 'SEARCH_TIMEOUT', 0.2):
            rows, missing = search.searchServers('alien', [animal, oscar, slow])
        self.assertEqual([('Movies', ['Alien'])], titles(rows))
        self.assertEqual(['Oscar', 'Slow'], missing)

    def test_the_sidebars_servers_in_its_order_else_every_server(self):
        animal, oscar = server('a', 'Animal'), server('o', 'Oscar')
        manager = mock.Mock(serversByUuid={'a': animal, 'o': oscar})
        manager.getServers.return_value = [oscar, animal]
        nav = {'entries': ['/library/sections/watchlist', 'o:1', 'a:22', 'o:playlists', 'gone:5']}
        with mock.patch.object(search.plexapp, 'SERVERMANAGER', manager), \
                mock.patch.object(search.plexapp, 'ACCOUNT', mock.Mock(ID='7')), \
                mock.patch.object(search.util, 'getSetting', lambda key, default=None: default), \
                mock.patch.object(search.sidebar_model.section_ids, 'loadJson', lambda key: nav):
            self.assertEqual([oscar, animal], search.searchedServers())
            # a sidebar with no libraries (a new account): every server on the account, by name
            nav['entries'] = ['/library/sections/watchlist']
            self.assertEqual([animal, oscar], search.searchedServers())


class ServerNameTest(KodiTestCase):
    def test_named_only_with_more_than_one_server(self):
        animal, oscar = server('a', 'Animal'), server('o', 'Oscar')
        manager = mock.Mock()
        with mock.patch.object(search.plexapp, 'SERVERMANAGER', manager):
            manager.getServers.return_value = [animal, oscar]
            self.assertEqual('Oscar', search.resultServerName(Item('x', '1', oscar)))
            manager.getServers.return_value = [animal]
            self.assertEqual('', search.resultServerName(Item('x', '1', animal)))


class HistoryTest(KodiTestCase):
    def test_the_old_servers_history_becomes_the_accounts(self):
        # the server selected when the add-on last ran (section_ids.legacyServer())
        settings = {'search.history.0000aaaa.7': json.dumps(['alien', 'reacher']),
                    'lastServerId.7': 'uuid-0000aaaa'}
        dlg = search.SearchWindow.__new__(search.SearchWindow)
        account = mock.Mock(ID='7')
        manager = mock.Mock(serversByUuid={'uuid-0000aaaa': server('uuid-0000aaaa', 'Animal')})
        with mock.patch.object(search.plexapp, 'ACCOUNT', account), \
                mock.patch.object(search.plexapp, 'SERVERMANAGER', manager), \
                mock.patch.object(search.util, 'getSetting', lambda key, default=None: settings.get(key, default)), \
                mock.patch.object(search.util, 'setSetting', lambda key, value: settings.__setitem__(key, value)):
            self.assertEqual(['alien', 'reacher'], dlg.loadSearchHistory())
            self.assertEqual(json.dumps(['alien', 'reacher']), settings['search.history.7'])
            dlg.addToHistory('neagley')
            self.assertEqual(['neagley', 'alien', 'reacher'], json.loads(settings['search.history.7']))


class ChosenServersTest(KodiTestCase):
    """The servers button (SearchWindow.chooseServers()): the account's choice, saved, wins over the
    sidebar's servers; at least one stays chosen."""

    def setUp(self):
        super(ChosenServersTest, self).setUp()
        self.animal, self.oscar, self.other = server('a', 'Animal'), server('o', 'Oscar'), server('x', 'Other')
        self.other.owned = False
        manager = mock.Mock(serversByUuid={'a': self.animal, 'o': self.oscar, 'x': self.other})
        manager.getServers.return_value = [self.other, self.animal, self.oscar]
        self.settings = {}
        self.nav = {'entries': ['o:1', 'a:22']}
        for patch in (mock.patch.object(search.plexapp, 'SERVERMANAGER', manager),
                      mock.patch.object(search.plexapp, 'ACCOUNT', mock.Mock(ID='7')),
                      mock.patch.object(search.sidebar_model.section_ids, 'loadJson', lambda key: self.nav),
                      mock.patch.object(search.util, 'getSetting',
                                        lambda key, default=None: self.settings.get(key, default)),
                      mock.patch.object(search.util, 'setSetting',
                                        lambda key, value: self.settings.__setitem__(key, value))):
            patch.start()
            self.addCleanup(patch.stop)

    def toggle(self, dlg, uuid):
        options = dlg._serverOptions()
        mli = mock.Mock(dataSource=[o for o in options if o['uuid'] == uuid][0])
        return dlg._onServerToggle(mock.Mock(getSelectedPos=lambda: 0), mli)

    def test_the_list_is_every_server_the_sidebars_first(self):
        self.assertEqual([self.oscar, self.animal, self.other], search.accountServers())

    def test_a_choice_is_saved_and_searched(self):
        dlg = search.SearchWindow.__new__(search.SearchWindow)
        self.assertEqual([self.oscar, self.animal], search.searchedServers())
        result = self.toggle(dlg, 'x')
        self.assertEqual('rebuild', result[0])
        self.assertEqual(['o', 'a', 'x'], json.loads(self.settings['search.servers.7']))
        self.toggle(dlg, 'o')
        self.assertEqual([self.animal, self.other], search.searchedServers())
        on = dict((o['uuid'], not o['indicator_dim']) for o in dlg._serverOptions())
        self.assertEqual({'o': False, 'a': True, 'x': True}, on)

    def test_the_last_chosen_server_stays(self):
        dlg = search.SearchWindow.__new__(search.SearchWindow)
        self.toggle(dlg, 'o')
        self.assertIsNone(self.toggle(dlg, 'a'))
        self.assertEqual([self.animal], search.searchedServers())

    def test_a_choice_of_servers_all_gone_falls_back_to_the_sidebars(self):
        self.settings['search.servers.7'] = json.dumps(['gone'])
        self.assertEqual([self.oscar, self.animal], search.searchedServers())


class Media(object):
    """A video's version as plexmedia.PlexMedia has it: get() answers with plain strings (live,
    2026-10-06 - its asInt() isn't there to call)."""

    def __init__(self, width, bitrate, resolution):
        self.attrs = {'width': str(width), 'bitrate': str(bitrate), 'videoResolution': resolution}

    def get(self, key, default=None):
        return self.attrs.get(key, default)


class Copy(object):
    """A search result as dedupeResults() reads it: guid, library, server, score, progress and its
    first version."""

    TYPE = 'movie'

    def __init__(self, title, guid, library, srv, score='0.5', viewOffset='', width=0, bitrate=0, resolution='',
                 lastViewedAt=''):
        self.title = title
        self.server = srv
        self.attrs = {'guid': guid, 'librarySectionTitle': library, 'score': score, 'viewOffset': viewOffset,
                      'lastViewedAt': lastViewedAt,
                      'librarySectionID': {'Films': '1', 'Movies': '2'}.get(library, '9')}
        self.media = [Media(width, bitrate, resolution)] if width or bitrate else []

    def get(self, key, default=''):
        return plexobjects.PlexValue(self.attrs.get(key, default))


class DedupeTest(KodiTestCase):
    """Copies of one thing - in two libraries of a server, or on two servers - are one result
    (dedupeResults()), by the agent's guid. Live 2026-10-06: Animal lists Alien in Films and in
    Movies, both plex://movie/5d7768254de0ee001fcc83a5."""

    ALIEN = 'plex://movie/5d7768254de0ee001fcc83a5'

    def setUp(self):
        super(DedupeTest, self).setUp()
        self.animal, self.oscar = server('a', 'Animal'), server('o', 'Oscar')

    def rows(self, items, type_='movie', positions=None):
        return search.dedupeResults([Hub(type_, 'Movies', items)], [self.animal, self.oscar], positions)

    def test_one_film_in_two_libraries_is_one_result(self):
        films = Copy('Alien', self.ALIEN, 'Films', self.animal, '0.93')
        movies = Copy('Alien', self.ALIEN, 'Movies', self.animal, '0.93')
        aliens = Copy('Aliens', 'plex://movie/5d776827961905001eb91337', 'Films', self.animal, '0.53')
        rows = self.rows([films, movies, aliens])
        self.assertEqual(['Alien', 'Aliens'], [i.title for i in rows[0].items])
        self.assertEqual(2, rows[0].size.asInt())
        self.assertEqual([films, movies], search.copiesOf(rows[0].items[0]))
        self.assertEqual([], search.copiesOf(rows[0].items[1]))

    def test_a_language_suffix_is_the_same_thing(self):
        rows = self.rows([Copy('Alien', 'com.plexapp.agents.imdb://tt0078748?lang=en', 'Films', self.animal),
                          Copy('Alien', 'com.plexapp.agents.imdb://tt0078748?lang=de', 'Movies', self.animal)])
        self.assertEqual(1, len(rows[0].items))

    def test_unmatched_files_arent_merged(self):
        rows = self.rows([Copy('Home video', 'local://1', 'Films', self.animal),
                          Copy('Home video', 'local://1', 'Films', self.oscar)])
        self.assertEqual(2, len(rows[0].items))

    def test_playlists_arent_merged(self):
        rows = self.rows([Copy('Mix', 'x://1', '', self.animal), Copy('Mix', 'x://1', '', self.oscar)], 'playlist')
        self.assertEqual(2, len(rows[0].items))

    def person(self, srv, library, tagKey='5d7768253c3c2a001fbcac3e', name='Alan Rickman'):
        copy = Copy(name, '', library, srv)
        copy.TYPE = 'Role'
        copy.attrs['tagKey'] = tagKey
        return copy

    def test_one_person_in_every_library_is_one_result(self):
        # live 2026-10-06: Alan Rickman in Films and Movies on Animal, and in Films on Oscar
        oscarFilms = self.person(self.oscar, 'Films')
        animalFilms = self.person(self.animal, 'Films')
        rows = self.rows([oscarFilms, animalFilms, self.person(self.animal, 'Movies'),
                          self.person(self.animal, 'Films', tagKey='5d776826eb5d26001f1dd578', name='Alan Tudyk')],
                         'actor')
        self.assertEqual(['Alan Rickman', 'Alan Tudyk'], [i.title for i in rows[0].items])
        # the sidebar's first server's
        self.assertIs(animalFilms, rows[0].items[0])
        self.assertEqual(3, len(search.copiesOf(rows[0].items[0])))

    def test_people_without_a_key_arent_merged(self):
        rows = self.rows([self.person(self.animal, 'Films', tagKey=''), self.person(self.oscar, 'Films', tagKey='')],
                         'director')
        self.assertEqual(2, len(rows[0].items))

    def test_the_part_watched_copy_opens(self):
        best = Copy('Alien', self.ALIEN, 'Movies', self.oscar, viewOffset='1619778', width=1920)
        rows = self.rows([Copy('Alien', self.ALIEN, 'Films', self.animal, width=3840), best])
        self.assertIs(best, rows[0].items[0])

    def test_of_two_part_watched_the_one_watched_last(self):
        last = Copy('Alien', self.ALIEN, 'Movies', self.oscar, viewOffset='500', lastViewedAt='1759700000')
        rows = self.rows([Copy('Alien', self.ALIEN, 'Films', self.animal, viewOffset='9000', lastViewedAt='1759000000',
                               width=3840), last], positions={('a', '1'): 0})
        self.assertIs(last, rows[0].items[0])

    def test_an_unpinned_library_after_one_pinned_low(self):
        # a place is the entry's index in the whole sidebar: past the number of libraries
        pinned = Copy('Alien', self.ALIEN, 'Films', self.animal, width=1920)
        rows = self.rows([Copy('Alien', self.ALIEN, 'Movies', self.oscar, width=3840), pinned],
                         positions={('a', '1'): 7, ('a', '5'): 2})
        self.assertIs(pinned, rows[0].items[0])

    def test_then_a_pinned_library_whatever_the_quality(self):
        # the user, 2026-10-06: a pinned library, and one pinned high, is the one watched from
        pinned = Copy('Alien', self.ALIEN, 'Films', self.animal, width=1920)
        rows = self.rows([Copy('Alien', self.ALIEN, 'Movies', self.oscar, width=3840), pinned],
                         positions={('a', '1'): 3})
        self.assertIs(pinned, rows[0].items[0])

    def test_the_library_pinned_higher(self):
        higher = Copy('Alien', self.ALIEN, 'Movies', self.animal, width=1920)
        rows = self.rows([Copy('Alien', self.ALIEN, 'Films', self.animal, width=3840), higher],
                         positions={('a', '1'): 4, ('a', '2'): 1})
        self.assertIs(higher, rows[0].items[0])

    def test_part_watched_still_first(self):
        watched = Copy('Alien', self.ALIEN, 'Movies', self.oscar, viewOffset='1000')
        rows = self.rows([Copy('Alien', self.ALIEN, 'Films', self.animal), watched],
                         positions={('a', '1'): 0})
        self.assertIs(watched, rows[0].items[0])

    def test_then_the_best_quality(self):
        best = Copy('Alien', self.ALIEN, 'Movies', self.oscar, width=3840, bitrate=40000)
        rows = self.rows([Copy('Alien', self.ALIEN, 'Films', self.animal, width=1920, bitrate=12453), best])
        self.assertIs(best, rows[0].items[0])

    def test_then_the_sidebars_first_server(self):
        best = Copy('Alien', self.ALIEN, 'Films', self.animal, width=1920)
        rows = self.rows([Copy('Alien', self.ALIEN, 'Films', self.oscar, width=1920), best])
        self.assertIs(best, rows[0].items[0])

    def test_a_merged_result_keeps_the_first_copys_place(self):
        rows = self.rows([Copy('Alien', self.ALIEN, 'Films', self.animal, '0.93'),
                          Copy('Aliens', 'plex://movie/2', 'Films', self.animal, '0.6'),
                          Copy('Alien', self.ALIEN, 'Movies', self.oscar, '0.4', width=3840)])
        self.assertEqual(['Alien', 'Aliens'], [i.title for i in rows[0].items])
        self.assertEqual('Movies', rows[0].items[0].get('librarySectionTitle'))


class PlacesLineTest(KodiTestCase):
    """The line under a result's type: where it is (placesLine())."""

    def setUp(self):
        super(PlacesLineTest, self).setUp()
        self.animal, self.oscar = server('a', 'Animal'), server('o', 'Oscar')
        manager = mock.Mock()
        manager.getServers.return_value = [self.animal, self.oscar]
        patch = mock.patch.object(search.plexapp, 'SERVERMANAGER', manager)
        patch.start()
        self.addCleanup(patch.stop)

    def merged(self, *copies):
        rows = search.dedupeResults([Hub('movie', 'Movies', list(copies))], [self.animal, self.oscar])
        return rows[0].items[0]

    def test_copies_on_one_server_it_and_how_many_others(self):
        item = self.merged(Copy('Alien', DedupeTest.ALIEN, 'Films', self.animal),
                           Copy('Alien', DedupeTest.ALIEN, 'Movies', self.animal))
        self.assertEqual(u'Animal + 1', search.placesLine(item))

    def test_copies_on_one_server_of_a_single_server_account_still_name_it(self):
        search.plexapp.SERVERMANAGER.getServers.return_value = [self.animal]
        item = self.merged(Copy('Alien', DedupeTest.ALIEN, 'Films', self.animal),
                           Copy('Alien', DedupeTest.ALIEN, 'Movies', self.animal))
        self.assertEqual(u'Animal + 1', search.placesLine(item))

    def test_the_server_is_the_one_it_opens_on(self):
        # the part-watched copy on Oscar is the one opened (pickCopy()), though Animal is first
        item = self.merged(Copy('Alien', DedupeTest.ALIEN, 'Films', self.animal),
                           Copy('Alien', DedupeTest.ALIEN, 'Movies', self.animal),
                           Copy('Alien', DedupeTest.ALIEN, 'Films', self.oscar, viewOffset='60000'))
        self.assertEqual(u'Oscar + 2', search.placesLine(item))

    def test_a_person_nothing(self):
        def person(srv):
            copy = Copy('Alan Rickman', '', 'Films', srv)
            copy.TYPE = 'Role'
            copy.attrs['tagKey'] = '5d7768253c3c2a001fbcac3e'
            return copy
        rows = search.dedupeResults([Hub('actor', 'Actors', [person(self.animal), person(self.oscar)])],
                                    [self.animal, self.oscar])
        self.assertTrue(search.copiesOf(rows[0].items[0]))
        self.assertEqual('', search.placesLine(rows[0].items[0]))
        self.assertEqual('', search.placesLine(person(self.oscar)))

    def test_one_copy_its_server(self):
        self.assertEqual('Oscar', search.placesLine(Copy('Alien', DedupeTest.ALIEN, 'Films', self.oscar)))

    def test_the_open_from_rows(self):
        copy = Copy('Alien', DedupeTest.ALIEN, 'Films', self.animal, width=1920, bitrate=12453, resolution='1080')
        self.assertTrue(search.copyLabel(copy, True).startswith(u'Films \u00b7 Animal \u00b7 1080p ('))
        self.assertEqual('Films', search.copyLabel(Copy('Alien', DedupeTest.ALIEN, 'Films', self.animal), False))


def copy(title, guid, library, srv, ratingKey, **kwargs):
    item = Copy(title, guid, library, srv, **kwargs)
    item.attrs['ratingKey'] = ratingKey
    return item


class LookupCopiesTest(KodiTestCase):
    """Past its limit Plex sometimes sends one library's copies and leaves the other's out (shows
    for "the" at 30 all from TV, none from TV shows, live 2026-10-07), so each server searched is
    asked for the results' guids (lookupCopies(), /library/all?guid=), and the copies it has join
    their results (dedupeResults()'s found)."""

    ALIEN = 'plex://movie/5d7768254de0ee001fcc83a5'
    EARTH = 'plex://show/6413cd3a5ea8bbd1c9e8e3ab'

    def setUp(self):
        super(LookupCopiesTest, self).setUp()
        self.animal, self.oscar = server('a', 'Animal'), server('o', 'Oscar')

    def test_a_copy_the_search_left_out_joins_its_result(self):
        films = copy('Alien', self.ALIEN, 'Films', self.animal, '1')
        found = {self.ALIEN: [copy('Alien', self.ALIEN, 'Films', self.animal, '1'),
                              copy('Alien', self.ALIEN, 'Movies', self.animal, '2'),
                              copy('Alien', self.ALIEN, 'Films', self.oscar, '1')]}
        rows = search.dedupeResults([Hub('movie', 'Movies', [films])], [self.animal, self.oscar], None, found)
        self.assertEqual(1, len(rows[0].items))
        # the search's own copy once, not again as the lookup's
        self.assertEqual(3, len(search.copiesOf(rows[0].items[0])))

    def test_a_copy_found_makes_no_result_of_its_own(self):
        films = copy('Alien', self.ALIEN, 'Films', self.animal, '1')
        found = {self.EARTH: [copy('Alien: Earth', self.EARTH, 'TV', self.animal, '7')]}
        rows = search.dedupeResults([Hub('movie', 'Movies', [films])], [self.animal], None, found)
        self.assertEqual([films], rows[0].items)
        self.assertEqual([], search.copiesOf(films))

    def test_a_copy_found_can_be_the_one_opened(self):
        films = copy('Alien', self.ALIEN, 'Films', self.animal, '1')
        watching = copy('Alien', self.ALIEN, 'Films', self.oscar, '1', viewOffset='60000', lastViewedAt='100')
        rows = search.dedupeResults([Hub('movie', 'Movies', [films])], [self.animal, self.oscar], None,
                                    {self.ALIEN: [watching]})
        self.assertIs(watching, rows[0].items[0])

    def test_each_server_asked_once_a_type_for_the_results_guids(self):
        rows = [Hub('movie', 'Movies', [copy('Alien', self.ALIEN + '?lang=en', 'Films', self.animal, '1'),
                                        copy('Mine', 'local://9', 'Films', self.animal, '9')]),
                Hub('show', 'Shows', [copy('Alien: Earth', self.EARTH, 'TV', self.animal, '7')]),
                Hub('actor', 'Actors', [copy('Alan Rickman', '', 'Films', self.animal, '3')])]
        asked = []
        lock = threading.Lock()

        def listItems(srv, path, params):
            with lock:
                asked.append((srv.name, path, params['type'], params['guid'], params['excludeFields']))
            if srv is self.oscar and params['type'] == 1:
                return [copy('Alien', self.ALIEN, 'Films', self.oscar, '1')]
            return []

        with mock.patch.object(search.plexobjects, 'listItems', side_effect=listItems):
            found = search.lookupCopies(rows, [self.animal, self.oscar])
        self.assertEqual(sorted([('Animal', '/library/all', 1, self.ALIEN, 'summary'),
                                 ('Animal', '/library/all', 2, self.EARTH, 'summary'),
                                 ('Oscar', '/library/all', 1, self.ALIEN, 'summary'),
                                 ('Oscar', '/library/all', 2, self.EARTH, 'summary')]), sorted(asked))
        self.assertEqual([self.ALIEN], list(found))
        self.assertEqual(['o'], [item.server.uuid for item in found[self.ALIEN]])

    def test_a_server_that_fails_adds_nothing(self):
        rows = [Hub('movie', 'Movies', [copy('Alien', self.ALIEN, 'Films', self.animal, '1')])]

        def listItems(srv, path, params):
            if srv is self.oscar:
                raise IOError('down')
            return [copy('Alien', self.ALIEN, 'Movies', self.animal, '2')]

        with mock.patch.object(search.plexobjects, 'listItems', side_effect=listItems), \
                mock.patch.object(search.util, 'ERROR'):
            found = search.lookupCopies(rows, [self.animal, self.oscar])
        self.assertEqual(1, len(found[self.ALIEN]))


class Episode(object):
    def __init__(self, title, show):
        self.title = title
        self.attrs = {'title': title, 'grandparentTitle': show}

    def get(self, key, default=None):
        return plexobjects.PlexValue(self.attrs.get(key, default) or '')


class ShowNameEpisodesTest(KodiTestCase):
    """Episodes Plex sends only because their show's name matches are dropped
    (dropShowNameEpisodes(), the user, 2026-10-07): checked live, all 30 of "arrow"'s episodes and 28
    of "frasier"'s were those - no reason= marks them."""

    def kept(self, query, *episodes):
        rows = search.dropShowNameEpisodes([Hub('episode', 'Episodes', list(episodes))], query)
        return [e.title for e in rows[0].items], rows[0].size.asInt()

    def test_the_shows_name_alone_drops_it(self):
        self.assertEqual((['Frasier Crane\'s Day Off'], 1),
                         self.kept('frasier', Episode('The Matchmaker', 'Frasier'),
                                   Episode('Frasier Crane\'s Day Off', 'Frasier')))

    def test_its_own_title_keeps_it(self):
        # the start of a word, or anywhere in one
        self.assertEqual(['Starling City', 'Superstar'],
                         self.kept('star', Episode('Starling City', 'Arrow'), Episode('Superstar', 'Glee'))[0])

    def test_a_match_it_cant_explain_stays(self):
        # neither title has it: Plex matched some other way (a corrected spelling, say)
        self.assertEqual(['Aliens'], self.kept('alein', Episode('Aliens', 'Doctor Who'))[0])

    def test_every_word_typed(self):
        self.assertEqual(['Chapter 1: The Mandalorian'],
                         self.kept('the mandalorian', Episode('Chapter 1: The Mandalorian', 'The Mandalorian'),
                                   Episode('Chapter 8: Redemption', 'The Mandalorian'))[0])

    def test_case_and_accents_ignored(self):
        self.assertEqual([], self.kept('pokemon', Episode('Pikachu!', u'Pokémon'))[0])

    def test_other_rows_untouched(self):
        rows = search.dropShowNameEpisodes([Hub('show', 'Shows', [Episode('Arrow', 'Arrow')])], 'arrow')
        self.assertEqual(1, len(rows[0].items))


class SupersededLookupTest(KodiTestCase):
    def test_overtaken_no_lookup(self):
        animal = server('a', 'Animal')
        animal.hubs.return_value = [Hub('movie', 'Movies', [Item('Alien', '0.9')])]
        with mock.patch.object(search, 'lookupCopies') as lookup:
            rows, missing = search.searchServers('alien', [animal], superseded=lambda: True)
        self.assertIsNone(rows)
        lookup.assert_not_called()


class SearchLimitSettingTest(KodiTestCase):
    """The search_limit setting (Settings > Main, 50 by default) is what each server is asked for."""

    def asked(self, setting):
        animal = server('a', 'Animal')
        animal.hubs.return_value = []
        real = search.util.getSetting
        with mock.patch.object(search.util, 'getSetting',
                               lambda key, default=None: setting if key == 'search_limit' else real(key, default)):
            search.searchServers('alien', [animal])
        return animal.hubs.call_args[1]['count']

    def test_the_setting(self):
        self.assertEqual(100, self.asked(100))

    def test_unset_50(self):
        self.assertEqual(50, self.asked(None))


class CollectionHubBuildTest(KodiTestCase):
    """plexnet builds a search's collections - Directory type="tag" - as media.Collection; it had no
    class for them, so the row came back empty (live, 2026-10-07)."""

    def test_tags_become_collections(self):
        from xml.etree import ElementTree
        from plexnet import plexlibrary, media
        xml = ElementTree.fromstring(
            '<Hub type="collection" hubIdentifier="collection" size="1" title="Collections">'
            '<Directory type="tag" tag="Star Wars Collection" id="84183" librarySectionID="22"'
            ' librarySectionTitle="Films" librarySectionType="1" thumb="https://image.tmdb.org/x.jpg"'
            ' key="/library/sections/22/all?collection=84183"/></Hub>')
        hub = plexlibrary.Hub(xml, server=mock.Mock())
        self.assertEqual([media.Collection], [type(i) for i in hub.items])
        self.assertEqual(('Star Wars Collection', '84183'), (hub.items[0].tag, hub.items[0].get('id')))


class Tag(object):
    """A search's collection as Plex sends it: its tag (plexnet media.Collection)."""

    def __init__(self, name, tagID, libraryID, library, libraryType, srv):
        self.tag = name
        self.server = srv
        self.attrs = {'id': tagID, 'librarySectionID': libraryID, 'librarySectionTitle': library,
                      'librarySectionType': libraryType}

    def get(self, key, default=''):
        return plexobjects.PlexValue(self.attrs.get(key, default) or '')


class RealCollection(object):
    TYPE = 'collection'

    def __init__(self, title, index):
        self.title = title
        self.attrs = {'index': index}

    def get(self, key, default=''):
        return plexobjects.PlexValue(self.attrs.get(key, default) or '')

    def set(self, key, value):
        self.attrs[key] = value


class ResolveCollectionsTest(KodiTestCase):
    """A search's collection tags become the collections they are: one request per library, by
    the tags' ids as the collections' index (resolveCollections(), live 2026-10-07)."""

    def setUp(self):
        super(ResolveCollectionsTest, self).setUp()
        self.animal = server('a', 'Animal')

    def test_each_library_asked_once_and_the_tags_replaced(self):
        tags = [Tag('Star Trek', '84090', '22', 'Films', '1', self.animal),
                Tag('Skywalker Saga', '2793', '2', 'Movies', '1', self.animal),
                Tag('Star Wars', '84183', '22', 'Films', '1', self.animal)]
        asked = []
        lock = threading.Lock()

        def listItems(srv, path, params):
            with lock:
                asked.append((path, params['index']))
            return {'/library/sections/22/collections': [RealCollection('Star Wars', '84183'),
                                                          RealCollection('Star Trek', '84090')],
                    '/library/sections/2/collections': [RealCollection('Skywalker Saga', '2793')]}[path]

        rows = [Hub('collection', 'Collections', tags)]
        with mock.patch.object(search.plexobjects, 'listItems', side_effect=listItems):
            search.resolveCollections(rows)
        self.assertEqual(sorted([('/library/sections/22/collections', '84090,84183'),
                                 ('/library/sections/2/collections', '2793')]), sorted(asked))
        # the tags' order, each with its tag's library
        self.assertEqual(['Star Trek', 'Skywalker Saga', 'Star Wars'], [c.title for c in rows[0].items])
        self.assertEqual(['Films', 'Movies', 'Films'], [u'{0}'.format(c.get('librarySectionTitle')) for c in rows[0].items])
        self.assertEqual(3, rows[0].size.asInt())

    def test_one_not_found_is_dropped(self):
        rows = [Hub('collection', 'Collections', [Tag('Gone', '1', '22', 'Films', '1', self.animal),
                                                  Tag('Here', '2', '22', 'Films', '1', self.animal)])]
        with mock.patch.object(search.plexobjects, 'listItems', lambda srv, path, params: [RealCollection('Here', '2')]):
            search.resolveCollections(rows)
        self.assertEqual(['Here'], [c.title for c in rows[0].items])

    def test_other_rows_untouched(self):
        rows = [Hub('movie', 'Movies', [Item('Alien', '0.9')])]
        with mock.patch.object(search.plexobjects, 'listItems') as listItems:
            search.resolveCollections(rows)
        listItems.assert_not_called()


class Version(object):
    """A version (Media) with an id, as chooseVersion() sets it selected."""

    def __init__(self, mediaID, width, bitrate, resolution):
        self.id = mediaID
        self.attrs = {'width': str(width), 'bitrate': str(bitrate), 'videoResolution': resolution}

    def get(self, key, default=None):
        return self.attrs.get(key, default)

    def set(self, key, value):
        self.attrs[key] = value


class VersionsTest(KodiTestCase):
    """A copy's versions (the user, 2026-10-07): the pick judges a copy by its best, Open from has a
    row for each, and the one picked opens chosen."""

    def setUp(self):
        super(VersionsTest, self).setUp()
        self.animal = server('a', 'Animal')

    def copy(self, library, *versions, **kwargs):
        item = copy('Alien: Romulus', DedupeTest.ALIEN, library, self.animal, kwargs.get('ratingKey', '1'))
        item.media = list(versions)
        item.chosen = []
        item.setMediaChoice = item.chosen.append
        return item

    def test_a_copy_is_judged_by_its_best_version(self):
        # Films lists its 1080p first, its 4K second
        films = self.copy('Films', Version('1', 1920, 6188, '1080'), Version('2', 3840, 61599, '4k'))
        movies = self.copy('Movies', Version('3', 1920, 9000, '1080'), ratingKey='2')
        self.assertIs(films, search.pickCopy([movies, films], {'a': 0}))

    def test_open_from_a_row_per_version(self):
        k4, hd = Version('1', 3840, 61599, '4k'), Version('2', 1920, 6188, '1080')
        films = self.copy('Films', k4, hd)
        movies = self.copy('Movies', Version('3', 1920, 6188, '1080'), ratingKey='2')
        films.searchCopies = [films, movies]
        self.assertEqual([(films, k4), (films, hd), (movies, None)], search.openFromEntries(films))
        self.assertEqual(u'Films · Animal · 1080p (6.2 Mbps)', search.copyLabel(films, True, hd))
        self.assertTrue(search.copyLabel(movies, True).startswith(u'Movies · Animal · 1080p'))

    def test_one_copy_with_versions_has_rows_too(self):
        films = self.copy('Films', Version('1', 3840, 61599, '4k'), Version('2', 1920, 6188, '1080'))
        self.assertEqual(2, len(search.openFromEntries(films)))

    def test_a_show_one_row_a_copy(self):
        show = self.copy('TV')
        show.TYPE = 'show'
        self.assertEqual([(show, None)], search.openFromEntries(show))

    def test_the_version_picked_opens_chosen(self):
        k4, hd = Version('1', 3840, 61599, '4k'), Version('2', 1920, 6188, '1080')
        films = self.copy('Films', k4, hd)
        search.chooseVersion(films, hd)
        self.assertEqual(([hd], 1, ''), (films.chosen, hd.get('selected'), k4.get('selected')))


class SearchHubContainerTest(KodiTestCase):
    """A search's hubs have no key; their container's address was '', which plexnet logged as
    FATAL once per hub with results, every search (124 lines in one day's log)."""

    def test_no_fatal_for_a_keyless_hub(self):
        from xml.etree import ElementTree
        from plexnet import plexlibrary, util as plexnetUtil
        from plexnet import video  # noqa: F401 - registers the film type the hub builds
        xml = ElementTree.fromstring(
            '<Hub type="movie" hubIdentifier="movie" size="1" title="Movies">'
            '<Video type="movie" title="Alien" ratingKey="1" key="/library/metadata/1"/></Hub>')
        with mock.patch.object(plexnetUtil, 'FATAL') as fatal:
            hub = plexlibrary.Hub(xml, server=mock.Mock())
        fatal.assert_not_called()
        self.assertEqual(1, len(hub.items))
