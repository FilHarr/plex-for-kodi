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
        animal.hubs.assert_called_once_with(count=10, search_query='alien')
        oscar.hubs.assert_called_once_with(count=10, search_query='alien')
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
        dlg = search.SearchDialog.__new__(search.SearchDialog)
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
    """The servers button (SearchDialog.chooseServers()): the account's choice, saved, wins over the
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
        dlg = search.SearchDialog.__new__(search.SearchDialog)
        self.assertEqual([self.oscar, self.animal], search.searchedServers())
        result = self.toggle(dlg, 'x')
        self.assertEqual('rebuild', result[0])
        self.assertEqual(['o', 'a', 'x'], json.loads(self.settings['search.servers.7']))
        self.toggle(dlg, 'o')
        self.assertEqual([self.animal, self.other], search.searchedServers())
        on = dict((o['uuid'], not o['indicator_dim']) for o in dlg._serverOptions())
        self.assertEqual({'o': False, 'a': True, 'x': True}, on)

    def test_the_last_chosen_server_stays(self):
        dlg = search.SearchDialog.__new__(search.SearchDialog)
        self.toggle(dlg, 'o')
        self.assertIsNone(self.toggle(dlg, 'a'))
        self.assertEqual([self.animal], search.searchedServers())

    def test_a_choice_of_servers_all_gone_falls_back_to_the_sidebars(self):
        self.settings['search.servers.7'] = json.dumps(['gone'])
        self.assertEqual([self.oscar, self.animal], search.searchedServers())
