# coding=utf-8
"""
Going local and back online in one session (live 2026-10-06, after plan Phase 9.3):
- in local mode a GDM round that misses a server (Animal never answers GDM) no longer takes away the
  LAN connections plex.tv's list had found for it, which left it offline with nothing to retest;
- back online, plex.tv's list of servers is asked for and Home waits for it, instead of opening on
  local mode's token-less connections (Oscar refused everything, 401, for 1¾ min);
- a library refusing the collections check is logged in a line, not as a traceback.

Importing lib.windows.* starts lib.player's monitor thread unless abort_requested is set first.
"""

from __future__ import absolute_import

from unittest import mock

from kodienv import ENV

ENV.abort_requested = True
from .test_server_state import ManagerTestCase, make_server  # noqa: E402 - imports plexnet's server manager safely
from lib import plex  # noqa: E402
from lib.windows import library  # noqa: E402
from plexnet import exceptions, plexresource  # noqa: E402
from plexnet import util as pnUtil  # noqa: E402

from .base import KodiTestCase  # noqa: E402

MYPLEX = plexresource.ResourceConnection.SOURCE_MYPLEX
DISCOVERED = plexresource.ResourceConnection.SOURCE_DISCOVERED
MANUAL = plexresource.ResourceConnection.SOURCE_MANUAL


class LocalModeListsTest(ManagerTestCase):
    def setUp(self):
        super(LocalModeListsTest, self).setUp()
        self.manager.waitingForResources = False
        for patcher in (mock.patch.object(pnUtil, 'LOCAL_MODE', True),
                        mock.patch.object(self.manager, 'saveState'),
                        mock.patch.object(self.manager, 'updateReachability')):
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_a_gdm_round_that_misses_a_server_keeps_its_connections(self):
        self.manager.setWatchedServers([self.animal.uuid])
        connections = list(self.animal.connections)
        self.manager.updateFromConnectionType([], DISCOVERED)
        self.assertEqual(connections, self.animal.connections)
        self.assertFalse(self.animal.offline)

    def test_nor_does_plex_tvs_list_going(self):
        with mock.patch.object(self.manager, 'deviceRefreshComplete') as settle:
            self.manager.updateFromConnectionType([], MYPLEX)
        settle.assert_not_called()

    def test_a_manual_entry_removed_still_goes(self):
        with mock.patch.object(self.manager, 'deviceRefreshComplete') as settle:
            self.manager.updateFromConnectionType([], MANUAL)
        settle.assert_called_once_with(MANUAL)

    def test_online_a_gdm_round_still_settles(self):
        with mock.patch.object(pnUtil, 'LOCAL_MODE', False), \
                mock.patch.object(self.manager, 'deviceRefreshComplete') as settle:
            self.manager.updateFromConnectionType([], DISCOVERED)
        settle.assert_called_once_with(DISCOVERED)


class RediscoverTest(ManagerTestCase):
    def test_plex_tvs_list_is_asked_for_and_waited_for(self):
        self.manager.resourcesAnswered = self.manager.storedLoaded = True
        with mock.patch.object(plex.plexapp, 'refreshResources') as refresh:
            self.manager.rediscover()
        refresh.assert_called_once_with(True)
        self.assertFalse(self.manager.serversKnown())
        self.assertTrue(self.manager.waitingForResources)  # signed in: no other list settles them


class InitTest(KodiTestCase):
    """plex.init() going online: rediscovers only when local mode ran before it, in this session."""

    def init(self, was_local, token='tok'):
        manager = mock.Mock()
        event = mock.MagicMock(timed_out=False)
        event.__enter__.return_value = event
        with mock.patch.object(plex, 'CallbackEvent', return_value=event), \
                mock.patch.object(plex.plexapp, 'init'), \
                mock.patch.object(plex.plexapp, 'SERVERMANAGER', manager), \
                mock.patch.object(plex.plexapp, 'ACCOUNT', mock.Mock(ID='1', authToken=token)), \
                mock.patch.object(plex, 'PLEX_INTERFACE'), \
                mock.patch.object(plex.plexnet_util, 'LOCAL_MODE', was_local):
            self.assertTrue(plex.init(local=False))
        return manager

    def test_back_online_after_local_mode(self):
        self.init(was_local=True).rediscover.assert_called_once_with()

    def test_not_on_an_ordinary_start(self):
        self.init(was_local=False).rediscover.assert_not_called()


class CollectionsCheckTest(KodiTestCase):
    def test_a_refusal_is_a_line_not_a_traceback(self):
        server = make_server('refusing-uuid', 'Oscar')
        section = mock.Mock(key='1', server=server, title='Films')
        section.all.side_effect = exceptions.BadRequest('(401) unauthorized')
        with mock.patch.object(library.util, 'ERROR') as error, mock.patch.object(library.util, 'LOG') as log:
            self.assertIsNone(library._askSection(section, 'collections', library._countCollections))
        error.assert_not_called()
        self.assertIn('(401) unauthorized', str(log.call_args))
