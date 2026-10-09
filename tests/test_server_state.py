# coding=utf-8
"""
A server's online/offline state, and the selected server going away.

The selected server used to be unselected the moment a reachability round found it unreachable -
silently, with no signal - leaving ~120 places in the UI reading .uuid/.name off None, and a stale
server search free to "settle for the best server found" and switch the whole UI to another one.
Now it stays selected and goes offline: 'offline:server' / 'online:server' fire on changes, plexnet
retests it with a backoff while it's down, and the Library window shows it and reloads on return.

Nothing used to notice a server dying mid-session either - queries against it just failed. A query
that gets no answer now has the server retested (markSuspect()).
"""

from __future__ import absolute_import

from kodienv import ENV

ENV.abort_requested = True
import requests  # noqa: E402
from plexnet import myplexaccount, plexapp, plexconnection, plexobjects, plexserver  # noqa: E402
from plexnet import util as pnUtil  # noqa: E402

from .base import KodiTestCase, ensure_plex_interface  # noqa: E402

try:
    from unittest import mock
except ImportError:
    import mock

ensure_plex_interface()
# The module builds a MANAGER as it's imported, which reads the account and hooks itself onto the
# shared APP's signals - other tests would then trip over it. Import it unhooked (myplexserver
# imports it too).
with mock.patch.object(plexapp, "ACCOUNT", myplexaccount.ACCOUNT), mock.patch.object(pnUtil.APP, "on"):
    from plexnet import plexservermanager  # noqa: E402
    from plexnet import myplexserver  # noqa: E402

from lib.windows import library  # noqa: E402

ANIMAL = "2612ca44f1aff44ba1b3963c7df4c3e9d99f1b0d"
OSCAR = "50c3d0b05067c152d84935cdea0ac8af7fc31d06"


class FakeTimer(object):
    def __init__(self, delay_ms):
        self.delay = delay_ms / 1000.0
        self.canceled = False

    def cancel(self):
        self.canceled = True


def make_server(uuid, name):
    server = plexserver.createPlexServerForName(uuid, name)
    conn = plexconnection.PlexConnection(plexconnection.PlexConnection.SOURCE_DISCOVERED,
                                         "http://192.168.1.7:32400", True, "tok", skipLocalCheck=True)
    server.connections.append(conn)
    server.activeConnection = conn
    server.isSupported = True
    return server


class ManagerTestCase(KodiTestCase):
    def setUp(self):
        KodiTestCase.setUp(self)
        account = mock.Mock(ID="1", isSignedIn=True, isAuthenticated=True)
        self.timers = []
        for patcher in (mock.patch.object(plexapp, "ACCOUNT", account),
                        mock.patch.object(pnUtil.APP, "on"),
                        mock.patch.object(pnUtil.APP, "addTimer"),
                        mock.patch.object(plexapp, "createTimer", side_effect=self._timer)):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.manager = plexservermanager.PlexServerManager()
        self.animal = make_server(ANIMAL, "Animal")
        self.oscar = make_server(OSCAR, "Oscar")
        self.manager.serversByUuid = {ANIMAL: self.animal, OSCAR: self.oscar}
        self.signals = []
        self.manager.on('offline:server', lambda server=None, **kw: self.signals.append(('offline', server.name)))
        self.manager.on('online:server', lambda server=None, **kw: self.signals.append(('online', server.name)))
        self.manager.on('suspect:server', lambda server=None, **kw: self.signals.append(('suspect', server.name)))
        self.manager.on('recovered:server',
                        lambda server=None, **kw: self.signals.append(('recovered', server.name)))

    def _timer(self, delay_ms, function, repeat=False):
        timer = FakeTimer(delay_ms)
        timer.function = function
        self.timers.append(timer)
        return timer

    def watch(self, *servers):
        """The sidebar has libraries from servers too (setWatchedServers()): they matter."""
        self.manager.setWatchedServers(self.manager.watchedServerUuids | set(s.uuid for s in servers))

    def round_ended(self, server, reachable):
        """The last result of a reachability round for server."""
        server.pendingReachabilityRequests = 0
        if not reachable:
            server.activeConnection = None
        self.manager.updateReachabilityResult(server, reachable)

    def delays(self):
        return [t.delay for t in self.timers]


class OfflineTest(ManagerTestCase):
    def test_one_failure_mid_round_is_not_offline(self):
        self.watch(self.animal)
        self.animal.pendingReachabilityRequests = 3
        self.manager.updateReachabilityResult(self.animal, False)
        self.assertFalse(self.animal.offline)
        self.assertEqual([], self.signals)

    def test_a_round_ending_unreachable_puts_a_sidebar_server_offline_and_retests_it(self):
        self.watch(self.animal)
        self.round_ended(self.animal, False)
        self.assertTrue(self.animal.offline)
        self.assertEqual([('offline', 'Animal')], self.signals)
        self.assertEqual([5], self.delays())

    def test_the_change_is_signalled_once(self):
        self.watch(self.animal)
        self.round_ended(self.animal, False)
        self.round_ended(self.animal, False)
        self.assertEqual([('offline', 'Animal')], self.signals)
        self.assertEqual([5], self.delays())  # one retest pending at a time

    def test_coming_back_is_signalled_and_stops_the_retests(self):
        self.watch(self.animal)
        self.round_ended(self.animal, False)
        self.animal.activeConnection = self.animal.connections[0]
        self.round_ended(self.animal, True)
        self.assertFalse(self.animal.offline)
        self.assertEqual([('offline', 'Animal'), ('online', 'Animal')], self.signals)
        self.assertTrue(self.timers[0].canceled)
        self.assertNotIn(ANIMAL, self.manager.offlineRetries)

    def test_retests_back_off(self):
        self.watch(self.animal)
        self.round_ended(self.animal, False)
        with mock.patch.object(self.animal, "updateReachability"):
            for _ in range(5):
                self.manager.onOfflineRetryTimer(self.animal)  # starts nothing, so it schedules the next itself
        self.assertEqual([5, 10, 30, 60, 60, 60], self.delays())

    def test_a_retest_round_ending_offline_schedules_the_next(self):
        self.watch(self.animal)
        self.round_ended(self.animal, False)
        with mock.patch.object(self.animal, "updateReachability",
                               side_effect=lambda force: setattr(self.animal, "pendingReachabilityRequests", 2)):
            self.manager.onOfflineRetryTimer(self.animal)
        self.assertEqual([5], self.delays())  # the round is under way; its end schedules the next
        self.round_ended(self.animal, False)
        self.assertEqual([5, 10], self.delays())

    def test_servers_not_in_the_sidebar_go_offline_without_retests(self):
        self.watch(self.animal)
        self.round_ended(self.oscar, False)
        self.assertTrue(self.oscar.offline)
        self.assertEqual([('offline', 'Oscar')], self.signals)
        self.assertEqual([], self.delays())

    def test_a_server_the_sidebar_has_libraries_from_is_retested_too(self):
        self.watch(self.animal)
        self.watch(self.oscar)
        self.round_ended(self.oscar, False)
        self.assertEqual([5], self.delays())
        with mock.patch.object(self.oscar, "updateReachability"):
            self.manager.onOfflineRetryTimer(self.oscar)
        self.assertEqual([5, 10], self.delays())

    def test_each_server_backs_off_on_its_own(self):
        self.watch(self.animal)
        self.watch(self.oscar)
        self.round_ended(self.animal, False)
        with mock.patch.object(self.animal, "updateReachability"):
            self.manager.onOfflineRetryTimer(self.animal)
        self.round_ended(self.oscar, False)
        self.assertEqual([5, 10, 5], self.delays())

    def test_a_server_newly_in_the_sidebar_that_is_offline_is_retested(self):
        self.watch(self.animal)
        self.round_ended(self.oscar, False)
        self.assertEqual([], self.delays())
        self.watch(self.oscar)
        self.assertEqual([5], self.delays())

    def test_one_leaving_the_sidebar_stops_being_retested(self):
        self.watch(self.animal)
        self.watch(self.oscar)
        self.round_ended(self.oscar, False)
        self.manager.setWatchedServers([])
        self.assertTrue(self.timers[0].canceled)
        self.assertNotIn(OSCAR, self.manager.offlineRetries)

    def test_the_periodic_check_covers_the_sidebars_servers(self):
        self.watch(self.animal)
        self.watch(self.oscar)
        with mock.patch.object(self.animal, "updateReachability") as animal, \
                mock.patch.object(self.oscar, "updateReachability") as oscar:
            self.manager.periodicReachabilityCheck()
        animal.assert_called_once_with(True)
        oscar.assert_called_once_with(True)


class AliveCheckTest(ManagerTestCase):
    """The light check between full rounds (PlexServer.checkAlive()): one /identity request on the
    connection in use, for every server that matters; only a failure retests all its connections."""

    def started(self):
        started = []
        patcher = mock.patch.object(pnUtil.APP, "startRequest",
                                    side_effect=lambda request, context: started.append((request, context)))
        patcher.start()
        self.addCleanup(patcher.stop)
        return started

    def test_one_request_on_the_connection_in_use(self):
        started = self.started()
        self.assertTrue(self.animal.checkAlive())
        self.assertEqual(["http://192.168.1.7:32400/identity"], [r.url for r, c in started])

    def test_not_while_offline_suspect_untested_or_mid_round(self):
        started = self.started()
        for setup in (lambda: setattr(self.animal, "offline", True),
                      lambda: setattr(self.animal, "suspect", True),
                      lambda: setattr(self.animal, "activeConnection", None),
                      lambda: setattr(self.animal, "pendingReachabilityRequests", 1)):
            server = make_server(ANIMAL, "Animal")
            self.animal = server
            setup()
            self.assertFalse(server.checkAlive())
        self.assertEqual([], started)

    def answer(self, response):
        started = self.started()
        self.animal.checkAlive()
        request, context = started[0]
        with mock.patch.object(self.animal, "markSuspect") as suspect:
            context.completionCallback(request, response, context)
        return suspect

    def test_an_answer_is_all(self):
        self.answer(mock.Mock(isSuccess=lambda: True)).assert_not_called()

    def test_no_answer_retests_every_connection(self):
        self.answer(mock.Mock(isSuccess=lambda: False, getStatus=lambda: 0)).assert_called_once_with()

    def test_a_gateway_error_counts(self):
        # a reverse proxy answering for a server that's down
        self.answer(mock.Mock(isSuccess=lambda: False, getStatus=lambda: 502)).assert_called_once_with()

    def test_every_server_that_matters_is_checked(self):
        self.watch(self.animal)
        with mock.patch.object(self.animal, "checkAlive") as animal, mock.patch.object(self.oscar, "checkAlive") as oscar:
            self.manager.checkServersAlive()
            oscar.assert_not_called()
            self.watch(self.oscar)
            self.manager.checkServersAlive()
        self.assertEqual(2, animal.call_count)
        oscar.assert_called_once_with()


class SuspectSignalTest(ManagerTestCase):
    """A query with no answer is said at once ('suspect:server'), before the retest's verdict:
    offline, or 'recovered:server' when it answers after all."""

    def test_a_query_with_no_answer_is_said_at_once(self):
        self.watch(self.animal)
        self.manager.onServerSuspect(self.animal)
        self.assertTrue(self.animal.suspect)
        self.assertEqual([('suspect', 'Animal')], self.signals)

    def test_once_per_retest(self):
        self.watch(self.animal)
        self.manager.onServerSuspect(self.animal)
        self.manager.onServerSuspect(self.animal)
        self.assertEqual([('suspect', 'Animal')], self.signals)

    def test_not_while_it_is_known_to_be_offline(self):
        self.watch(self.animal)
        self.round_ended(self.animal, False)
        self.manager.onServerSuspect(self.animal)
        self.assertEqual([('offline', 'Animal')], self.signals)
        self.assertFalse(self.animal.suspect)

    def test_answering_after_all_is_recovered(self):
        self.watch(self.animal)
        self.manager.onServerSuspect(self.animal)
        self.round_ended(self.animal, True)
        self.assertEqual([('suspect', 'Animal'), ('recovered', 'Animal')], self.signals)
        self.assertFalse(self.animal.suspect)

    def test_a_reachable_result_mid_round_decides_nothing(self):
        # the connection the query failed on is still the active one until its own result is in
        self.watch(self.animal)
        self.manager.onServerSuspect(self.animal)
        self.animal.pendingReachabilityRequests = 2
        self.manager.updateReachabilityResult(self.animal, True)
        self.assertEqual([('suspect', 'Animal')], self.signals)
        self.assertTrue(self.animal.suspect)
        self.round_ended(self.animal, False)
        self.assertEqual([('suspect', 'Animal'), ('offline', 'Animal')], self.signals)

    def test_once_it_answers_the_next_failure_retests_at_once(self):
        self.animal._lastSuspectRetest = 12345.0  # a retest just ran
        self.round_ended(self.animal, True)
        self.assertEqual(0, self.animal._lastSuspectRetest)

    def test_not_answering_is_offline(self):
        self.watch(self.animal)
        self.manager.onServerSuspect(self.animal)
        self.round_ended(self.animal, False)
        self.assertEqual([('suspect', 'Animal'), ('offline', 'Animal')], self.signals)
        self.assertFalse(self.animal.suspect)

    def test_marking_a_server_says_so(self):
        with mock.patch.object(plexservermanager, "MANAGER", self.manager), \
                mock.patch.object(self.animal, "updateReachability",
                                  side_effect=lambda force: setattr(self.animal, "pendingReachabilityRequests", 1)):
            self.animal.markSuspect()
        self.assertEqual([('suspect', 'Animal')], self.signals)

    def test_marking_a_server_with_nothing_to_test_gives_the_verdict_at_once(self):
        self.watch(self.animal)
        self.animal.activeConnection = None
        with mock.patch.object(plexservermanager, "MANAGER", self.manager), \
                mock.patch.object(self.animal, "updateReachability"):
            self.animal.markSuspect()
        self.assertEqual([('suspect', 'Animal'), ('offline', 'Animal')], self.signals)

    def test_try_again_retests_now_instead_of_at_the_next_step(self):
        self.watch(self.animal)
        self.round_ended(self.animal, False)
        with mock.patch.object(self.animal, "updateReachability",
                               side_effect=lambda force: setattr(self.animal, "pendingReachabilityRequests", 2)):
            self.assertTrue(self.manager.retestServerNow(self.animal))
        self.assertTrue(self.timers[0].canceled)
        self.round_ended(self.animal, False)
        self.assertEqual([5, 10], self.delays())  # still offline: the backoff carries on


class ServerListTest(ManagerTestCase):
    def test_signed_in_only_plex_tvs_list_settles_the_servers(self):
        # until plex.tv has answered, a GDM round that misses a server doesn't count against it
        self.assertTrue(self.manager.waitingForResources)
        with mock.patch.object(self.manager, "deviceRefreshComplete") as settle, \
                mock.patch.object(self.manager, "saveState"), \
                mock.patch.object(self.manager, "updateReachability"):
            self.manager.updateFromConnectionType([], DISCOVERED)
            settle.assert_not_called()
            self.manager.updateFromConnectionType([], MYPLEX)
            self.manager.updateFromConnectionType([], DISCOVERED)
        self.assertEqual([mock.call(MYPLEX), mock.call(DISCOVERED)], settle.call_args_list)
        self.assertFalse(self.manager.waitingForResources)
        self.assertTrue(self.manager.serversKnown())

    def test_nothing_is_selected(self):
        # every server is as good as another (plan Phase 9.3): an answer picks none of them
        self.round_ended(self.oscar, True)
        self.assertFalse(hasattr(self.manager, 'selectedServer'))

    def test_another_dropped_server_is_removed(self):
        self.watch(self.animal)
        self.manager.removeServer(self.oscar, MYPLEX)
        self.assertNotIn(OSCAR, self.manager.serversByUuid)

    def test_a_sidebar_server_missing_from_discovery_is_kept_offline(self):
        self.watch(self.animal)
        self.watch(self.oscar)
        self.manager.removeServer(self.oscar, DISCOVERED)
        self.assertIn(OSCAR, self.manager.serversByUuid)
        self.assertTrue(self.oscar.offline)
        self.assertFalse(self.oscar.gone)

    def test_a_sidebar_server_plex_tv_drops_is_gone(self):
        self.watch(self.animal)
        self.watch(self.oscar)
        gone = []
        self.manager.on('gone:server', lambda server=None, **kw: gone.append(server))
        self.manager.removeServer(self.oscar, MYPLEX)
        self.assertNotIn(OSCAR, self.manager.serversByUuid)
        self.assertTrue(self.oscar.gone)
        self.assertEqual([self.oscar], gone)
        self.assertIn(ANIMAL, self.manager.serversByUuid)


MYPLEX = plexconnection.PlexConnection.SOURCE_MYPLEX
DISCOVERED = plexconnection.PlexConnection.SOURCE_DISCOVERED


class GoneTest(ManagerTestCase):
    """A server plex.tv no longer lists is off the account: removed, not kept as unavailable.
    Unavailable (offline) is only for a server the account still has that isn't answering."""

    def setUp(self):
        ManagerTestCase.setUp(self)
        self.gone = []
        self.manager.on('gone:server', lambda server=None, **kw: self.gone.append(server))
        patcher = mock.patch.object(self.manager, "saveState")
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_dropped_by_plex_tv_it_is_removed_and_not_retested(self):
        self.watch(self.animal)
        self.manager.removeServer(self.animal, MYPLEX)
        self.assertNotIn(ANIMAL, self.manager.serversByUuid)
        self.assertTrue(self.animal.gone)
        self.assertTrue(self.animal.offline)
        self.assertEqual([self.animal], self.gone)
        self.round_ended(self.animal, False)
        self.assertEqual([], self.delays(), "no retests: it isn't coming back by being retested")

    def test_listed_again_it_is_on_the_account_again(self):
        self.watch(self.animal)
        self.manager.removeServer(self.animal, MYPLEX)
        relisted = make_server(ANIMAL, "Animal")
        self.assertIs(relisted, self.manager.mergeServer(relisted))
        self.assertIs(relisted, self.manager.serversByUuid[ANIMAL])
        self.assertFalse(relisted.gone)

    def test_a_missed_discovery_reply_keeps_it_offline(self):
        # GDM is UDP broadcast: one unanswered round says nothing about the account
        self.watch(self.animal)
        self.manager.removeServer(self.animal, DISCOVERED)
        self.assertIn(ANIMAL, self.manager.serversByUuid)
        self.assertFalse(self.animal.gone)
        self.assertTrue(self.animal.offline)
        self.assertEqual([], self.gone)
        self.assertEqual([5], self.delays())

    def test_signing_out_does_not_count(self):
        self.watch(self.animal)
        plexapp.ACCOUNT.isSignedIn = False
        self.manager.removeServer(self.animal, MYPLEX)
        self.assertFalse(self.animal.gone)
        self.assertEqual([], self.gone)


class SuspectTest(KodiTestCase):
    """A query that gets no answer has its server retested - at most every 30 s."""

    def setUp(self):
        KodiTestCase.setUp(self)
        ensure_plex_interface()
        self.server = make_server(OSCAR, "Oscar")
        self.clock = [1000.0]
        for patcher in (mock.patch.object(plexserver.time, "time", side_effect=lambda: self.clock[0]),
                        # markSuspect() tells the manager (SuspectSignalTest covers what it does then)
                        mock.patch.object(plexservermanager, "MANAGER", mock.Mock())):
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_retests_are_spaced_out(self):
        with mock.patch.object(self.server, "updateReachability") as retest:
            self.server.markSuspect()
            self.clock[0] += 10
            self.server.markSuspect()
            self.clock[0] += 25
            self.server.markSuspect()
        self.assertEqual(2, retest.call_count)

    def test_plex_tv_is_never_retested(self):
        with mock.patch.object(plexapp, "ACCOUNT", mock.Mock(authToken="tok")):
            mps = myplexserver.MyPlexServer()
        with mock.patch.object(mps, "updateReachability") as retest:
            mps.markSuspect()
        retest.assert_not_called()

    def answer(self, outcome):
        def get(url, **kwargs):
            if isinstance(outcome, Exception):
                raise outcome
            return outcome
        self.server.session.get = get

    def test_a_query_with_no_answer_marks_it(self):
        self.answer(requests.exceptions.ConnectTimeout("connect timed out"))
        with mock.patch.object(self.server, "markSuspect") as suspect:
            self.assertIsNone(self.server.query("/library/sections"))
        suspect.assert_called_once_with()

    def test_a_gateway_error_marks_it(self):
        response = mock.Mock(status_code=502)
        self.answer(response)
        with mock.patch.object(self.server, "markSuspect") as suspect:
            with self.assertRaises(Exception):
                self.server.query("/library/sections")
        suspect.assert_called_once_with()

    def test_while_it_is_retested_queries_fail_at_once(self):
        self.server.suspect = True
        self.server.session.get = mock.Mock()
        self.assertIsNone(self.server.query("/library/sections"))
        self.server.session.get.assert_not_called()

    def test_the_collections_check_skips_a_server_being_retested_and_remembers_nothing(self):
        section = mock.Mock(key="1", server=self.server, TYPE="movie")
        self.server.suspect = True
        library.SectionTabsCheckTask(section, None).run()
        section.all.assert_not_called()
        self.assertNotIn((self.server.uuid, "1"), library._sectionHasCollectionsCache)

    def test_a_reload_with_no_answer_fails_quietly(self):
        item = plexobjects.PlexObject(None, server=self.server)
        item.key = "/library/metadata/1"
        with mock.patch.object(self.server, "query", return_value=None), \
                mock.patch.object(plexobjects.util, "ERROR") as error:
            item.reload()
        self.assertTrue(item.reloadFailed)
        error.assert_not_called()


class LibraryWindowTest(KodiTestCase):
    """A server not answering, coming back, or leaving the account, as the Library window shows it:
    the "isn't responding" panel and toasts follow the server of what's on screen, the sidebar dims a
    library whose server is offline, and a server gone from the account takes its libraries out of
    the sidebar."""

    def setUp(self):
        KodiTestCase.setUp(self)
        ensure_plex_interface()
        self.server = make_server(ANIMAL, "Animal")
        servers = mock.Mock()
        servers.getServers.return_value = [self.server]
        account = mock.Mock(title="Phil", username="phil", ID="1", thumb="")
        # the sidebar's servers: the Libraries button's icon says when none is answering
        self.sidebarServers = [self.server]
        for patcher in (mock.patch.object(library.plexapp, "SERVERMANAGER", servers),
                        mock.patch.object(library.plexapp, "ACCOUNT", account),
                        mock.patch.object(library.sidebar_model, "sidebarServers", lambda: self.sidebarServers),
                        mock.patch.object(library.util, "showNotification")):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.win = library.LibraryWindow.__new__(library.LibraryWindow)
        self.props = {}
        self.win.setProperty = lambda key, value: self.props.__setitem__(key, value)
        self.win.getProperty = lambda key: self.props.get(key, '')
        # a library of Animal's on screen, in the sidebar
        self.section = mock.Mock(server=self.server)
        self.win.section = self.section
        self.win.navSettings = {'version': 2, 'entries': [ANIMAL + ':1'], 'libraries': {ANIMAL + ':1': {}}}
        self.win._rebuildSidebar = mock.Mock()
        self.win._backStack = []
        self.win._shuttingDown = False
        self.win._isHostedShell = False
        self.win.closing = False
        self.win.contentMode = 'recommended'
        self.win.visibleHubs = []
        self.win.openSection = mock.Mock()

    def test_every_sidebar_server_offline_shows_the_error_icon(self):
        oscar = make_server(OSCAR, "Oscar")
        self.sidebarServers = [self.server, oscar]
        self.server.offline = True
        self.win.displayServerAndUser()
        self.assertEqual('script.plex/home/device/plex.png', self.props['server.icon'])
        oscar.offline = True
        self.win.displayServerAndUser()
        self.assertEqual('script.plex/home/device/error.png', self.props['server.icon'])
        # the button below the sidebar is the Libraries picker's now; its icon still says it
        self.assertEqual('Libraries', self.props['server.name'])

    def test_coming_back_reloads_the_section_in_place(self):
        self.win.onServerOnline(server=self.server)
        self.win.openSection.assert_called_once_with(self.win.section, force=True, fresh=False)
        self.assertEqual('script.plex/home/device/plex.png', self.props['server.icon'])

    def test_coming_back_leaves_an_open_screen_chain_alone(self):
        self.win._backStack = [("entry", {})]
        self.win.onServerOnline(server=self.server)
        self.win.openSection.assert_not_called()

    def gone_setup(self):
        oscar = OSCAR
        self.win.navSettings = {'version': 2, 'entries': ['playlists', ANIMAL + ':1', oscar + ':2', ANIMAL + ':3'],
                                'libraries': {ANIMAL + ':1': {}, oscar + ':2': {}, ANIMAL + ':3': {}}}
        self.win.hubSettings = {ANIMAL + ':1': {}, ANIMAL + ':__home__': {}, oscar + ':2': {}, 'playlists': {}}
        self.win.saveNavSettings = mock.Mock()
        self.win.saveHubSettings = mock.Mock()
        self.win._rebuildSidebar = mock.Mock()

    def test_a_gone_server_leaves_the_sidebar_with_its_hub_settings(self):
        self.gone_setup()
        self.win.onServerGone(server=self.server)
        self.assertEqual(['playlists', OSCAR + ':2'], self.win.navSettings['entries'])
        self.assertEqual({OSCAR + ':2': {}, 'playlists': {}}, self.win.hubSettings)
        self.win.saveNavSettings.assert_called_once_with()
        self.win.saveHubSettings.assert_called_once_with()
        self.win._rebuildSidebar.assert_called_once_with()
        self.assertEqual(["Animal is no longer available to this account. Its libraries were removed from the sidebar."],
                         self.toasts())

    def test_a_gone_server_with_nothing_in_the_sidebar_says_nothing(self):
        self.gone_setup()
        self.win.onServerGone(server=make_server("someone-else", "Elsewhere"))
        self.assertEqual([], self.toasts())

    def test_another_servers_library_on_screen_follows_that_server(self):
        oscar = make_server(OSCAR, "Oscar")
        self.win.section = mock.Mock(server=oscar)
        oscar.suspect = True
        self.win.onServerSuspect(server=oscar)
        self.assertEqual("Oscar isn't responding", self.props['server.unavailable'])
        self.win.onServerSuspect(server=self.server)
        self.assertEqual(["Oscar isn't responding. Retrying..."], self.toasts())

    def test_a_sidebar_server_going_offline_or_coming_back_rebuilds_the_sidebar(self):
        oscar = make_server(OSCAR, "Oscar")
        self.win.navSettings = {'version': 2, 'entries': [OSCAR + ':2'], 'libraries': {}}
        self.win._rebuildSidebar = mock.Mock()
        self.win.onServerOffline(server=oscar)
        self.win.onServerOnline(server=oscar)
        self.assertEqual(2, self.win._rebuildSidebar.call_count)
        self.win.openSection.assert_not_called()

    def test_a_home_server_answering_again_refreshes_homes_rows(self):
        """A refresh that met the blip kept Home's rows; the server's recovery fetches them again
        (AM6B after a wake, 2026-10-09)."""
        oscar = make_server(OSCAR, "Oscar")
        self.win.section = library.home.home_section
        self.win._homeServers = lambda: [(oscar, ['1'])]
        self.win.refreshHubsInPlace = mock.Mock()
        self.win.onServerRecovered(server=oscar)
        self.win.refreshHubsInPlace.assert_called_once_with('Oscar answers again')

    def test_dropping_idle_connections_leaves_a_working_session(self):
        srv = plexserver.PlexServer.__new__(plexserver.PlexServer)
        srv.session = plexserver.http.Session()
        adapter = srv.session.get_adapter('https://example.invalid/')
        adapter.poolmanager.connection_from_url('https://example.invalid/')
        self.assertEqual(1, len(adapter.poolmanager.pools))
        srv.dropIdleConnections()
        self.assertEqual(0, len(adapter.poolmanager.pools))
        adapter.poolmanager.connection_from_url('https://example.invalid/')
        self.assertEqual(1, len(adapter.poolmanager.pools))

    def test_other_servers_are_ignored(self):
        self.win.onServerSuspect(server=make_server(OSCAR, "Oscar"))
        self.win.onServerOffline(server=make_server(OSCAR, "Oscar"))
        self.win.onServerRecovered(server=make_server(OSCAR, "Oscar"))
        self.win.onServerOnline(server=make_server(OSCAR, "Oscar"))
        self.win.openSection.assert_not_called()
        self.assertEqual({}, self.props)

    def toasts(self):
        return [c[0][0] for c in library.util.showNotification.call_args_list]

    def test_no_answer_is_said_at_once_and_only_once(self):
        self.server.suspect = True
        self.win.onServerSuspect(server=self.server)
        self.server.suspect, self.server.offline = False, True
        self.win.onServerOffline(server=self.server)
        self.assertEqual(["Animal isn't responding. Retrying..."], self.toasts())

    def test_offline_found_in_the_background_is_said_too(self):
        self.server.offline = True
        self.win.onServerOffline(server=self.server)
        self.assertEqual(["Animal isn't responding. Retrying..."], self.toasts())

    def test_after_coming_back_it_is_said_again_next_time(self):
        self.server.offline = True
        self.win.onServerOffline(server=self.server)
        self.server.offline = False
        self.win.onServerOnline(server=self.server)
        self.server.offline = True
        self.win.onServerOffline(server=self.server)
        self.assertEqual(2, self.toasts().count("Animal isn't responding. Retrying..."))

    def test_an_empty_view_says_why(self):
        self.server.suspect = True
        self.win.onServerSuspect(server=self.server)
        self.assertEqual("Animal isn't responding", self.props['server.unavailable'])
        self.assertEqual("Retrying automatically.", self.props['server.unavailable.detail'])

    def test_a_view_with_rows_keeps_them(self):
        self.win.visibleHubs = ["a hub"]
        self.server.offline = True
        self.win.onServerOffline(server=self.server)
        self.assertEqual('', self.props.get('server.unavailable', ''))

    def test_an_empty_grid_says_why_instead_of_no_content(self):
        self.win.contentMode = 'posters'
        self.props['no.content'] = '1'
        self.server.offline = True
        self.assertTrue(self.win.updateServerUnavailable())

    def test_coming_back_clears_it(self):
        self.server.offline = True
        self.win.onServerOffline(server=self.server)
        self.server.offline = False
        self.win.onServerOnline(server=self.server)
        self.assertEqual('', self.props['server.unavailable'])

    def test_answering_after_all_reloads_an_empty_view_quietly(self):
        self.server.suspect = True
        self.win.onServerSuspect(server=self.server)
        self.server.suspect = False
        self.win.onServerRecovered(server=self.server)
        self.win.openSection.assert_called_once_with(self.win.section, force=True, fresh=False)
        self.assertEqual('', self.props['server.unavailable'])
        self.assertEqual(1, len(self.toasts()))

    def test_answering_after_all_leaves_a_full_view_alone(self):
        self.win.visibleHubs = ["a hub"]
        self.win.onServerRecovered(server=self.server)
        self.win.openSection.assert_not_called()

    def came_back(self):
        self.win._tickers = []
        self.win.postUI = mock.Mock()
        self.win.onServerOnline(server=self.server)

    def test_coming_back_to_an_empty_section_reloads_it_again_shortly(self):
        self.came_back()
        self.win._retryEmptyAfterReturn()  # the reload's bind: still nothing (Plex still loading)
        tick = self.win._tickers[0]
        self.assertTrue(tick(0))  # not due yet
        self.assertFalse(tick(library.time.time() + 4))
        self.win.postUI.assert_called_once_with('reload after the server came back', self.win.openSection,
                                                args=(self.section,), kwargs={'force': True, 'fresh': False})

    def test_rows_end_the_retries(self):
        self.came_back()
        self.win.visibleHubs = ["a hub"]
        self.win._retryEmptyAfterReturn()
        self.assertEqual([], self.win._tickers)
        self.assertIsNone(self.win._returnReload)

    def test_the_retries_give_up(self):
        self.came_back()
        for _ in library.LibraryWindow.RETURN_RELOAD_DELAYS:
            self.win._retryEmptyAfterReturn()
        self.win._retryEmptyAfterReturn()
        self.assertEqual(len(library.LibraryWindow.RETURN_RELOAD_DELAYS), len(self.win._tickers))

    def test_moving_to_another_section_ends_them(self):
        self.came_back()
        self.win._retryEmptyAfterReturn()
        self.win.section = "another section"
        self.assertFalse(self.win._tickers[0](library.time.time() + 60))
        self.win.postUI.assert_not_called()

    def test_try_again_says_so_until_the_round_ends(self):
        self.server.offline = True
        self.win.updateServerUnavailable()
        library.plexapp.SERVERMANAGER.retestServerNow.return_value = True
        self.win._tickers = []
        self.server.pendingReachabilityRequests = 2
        self.win.retryServerNow()
        self.assertEqual("Trying again...", self.props['server.unavailable.detail'])
        self.assertTrue(self.win._tickServerRetry(0))
        self.server.pendingReachabilityRequests = 0
        self.assertFalse(self.win._tickServerRetry(0))
        self.assertEqual("Retrying automatically.", self.props['server.unavailable.detail'])


class TickTest(KodiTestCase):
    """LibraryWindow.tick(), sleep and wake - ported from HomeWindow, which took them with it when
    it was retired (12675d11): the periodic reachability check was a setting that did nothing, and
    waking did nothing at all. The rows are refreshed in place: on wake, and every 5 minutes (plan
    7.3)."""

    def setUp(self):
        KodiTestCase.setUp(self)
        ensure_plex_interface()
        self.servers = mock.Mock()
        self.posted = []
        for patcher in (mock.patch.object(library.plexapp, "SERVERMANAGER", self.servers),
                        mock.patch.object(library.time, "time", return_value=10000.0)):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.win = library.LibraryWindow.__new__(library.LibraryWindow)
        self.win._shuttingDown = False
        self.win._ignoreTick = False
        self.win._lastReachabilityCheck = 10000.0 - library.LibraryWindow.REACHABILITY_CHECK_INTERVAL - 1
        self.win._backStack = []
        self.win.contentMode = 'recommended'
        self.win.section = "the section"
        self.win.openSection = mock.Mock()
        self.win.closing = False
        self.win._isHostedShell = False
        self.win._listGeneration = 3
        self.win.started = []
        self.win._startHubsFetch = lambda callback, late=None: self.win.started.append((callback, late))
        self.win._captureRootRestoreState = lambda: {'_restoreHubId': 'movie.recentlyadded'}
        self.win.postUI = lambda name, fn, args=(), kwargs=None: self.posted.append((name, fn, args))
        ENV.settings["recheck_server_connections"] = "true"

    def test_it_is_a_whole_cron_receiver(self):
        # util.CRON calls halfHour() and day() on every receiver as well as tick(); without them
        # the call fell through MultiWindow.__getattr__() to the view and raised (live, 20:00)
        self.assertIsInstance(self.win, library.util.CronReceiver)
        self.assertFalse(self.win.halfHour())
        self.assertFalse(self.win.day())
        self.assertIs(library.LibraryWindow.tick, type(self.win).tick)

    def test_the_periodic_check_runs_when_due(self):
        self.win.tick()
        self.servers.periodicReachabilityCheck.assert_called_once_with()
        self.win.tick()  # not again until another interval has passed
        self.assertEqual(1, self.servers.periodicReachabilityCheck.call_count)

    def test_a_light_check_every_minute_between_full_ones(self):
        self.win.tick()  # the full round is due: it counts as this minute's check too
        self.servers.checkServersAlive.assert_not_called()
        with mock.patch.object(library.time, "time", return_value=10000.0 + library.LibraryWindow.SERVER_ALIVE_INTERVAL + 1):
            self.win.tick()
            self.win.tick()  # not again within the minute
        self.servers.checkServersAlive.assert_called_once_with()
        self.assertEqual(1, self.servers.periodicReachabilityCheck.call_count)

    def test_the_light_check_follows_the_setting_too(self):
        ENV.settings["recheck_server_connections"] = "false"
        self.win._lastAliveCheck = 0
        self.win.tick()
        self.servers.checkServersAlive.assert_not_called()

    def test_the_periodic_check_follows_its_setting(self):
        ENV.settings["recheck_server_connections"] = "false"
        self.win.tick()
        self.servers.periodicReachabilityCheck.assert_not_called()

    def test_nothing_ticks_while_paused_or_playing(self):
        self.win._ignoreTick = True
        self.win.tick()
        self.win._ignoreTick = False
        import xbmc
        xbmc.Player.playing_video = True
        self.win.tick()
        self.servers.periodicReachabilityCheck.assert_not_called()

    def test_the_rows_are_refreshed_every_5_minutes(self):
        self.win._lastHubsRefresh = 10000.0 - library.LibraryWindow.HUBS_REFRESH_INTERVAL - 1
        self.win.tick()
        self.assertEqual([('refresh rows', self.win.refreshHubsInPlace, ('every 5 minutes',))],
                         [p for p in self.posted if p[0] == 'refresh rows'])
        self.posted[:] = []
        self.win.tick()  # not again until another 5 minutes
        self.assertEqual([], [p for p in self.posted if p[0] == 'refresh rows'])

    def test_waking_refreshes_the_rows_in_place(self):
        self.win.refreshLastSection()
        self.assertEqual(1, len(self.win.started))
        self.win.openSection.assert_not_called()
        self.servers.resumeOfflineRetry.assert_called_once_with()

    def test_a_refresh_leaves_a_grid_a_chain_or_a_video_alone(self):
        import xbmc
        for setup in (lambda: setattr(self.win, 'contentMode', 'library'),
                      lambda: setattr(self.win, '_backStack', [("entry", {})]),
                      lambda: setattr(xbmc.Player, 'playing_video', True)):
            self.win.contentMode, self.win._backStack, xbmc.Player.playing_video = 'recommended', [], False
            setup()
            self.assertFalse(self.win.refreshHubsInPlace('test'))
        self.assertEqual([], self.win.started)

    def test_sleep_pauses_ticks_and_offline_retests(self):
        self.win._onSleep()
        self.assertTrue(self.win._ignoreTick)
        self.servers.cancelOfflineRetry.assert_called_once_with()

    def test_waking_checks_the_server_then_refreshes(self):
        self.win._ignoreTick = True
        animal = mock.Mock()
        self.servers.serversByUuid = {'animal': animal}
        self.win._afterWake(0)
        # pre-sleep connections dropped first (PlexServer.dropIdleConnections())
        animal.dropIdleConnections.assert_called_once_with()
        self.servers.periodicReachabilityCheck.assert_called_once_with()
        self.servers.resumeOfflineRetry.assert_called_once_with()
        self.assertEqual(['refresh after wake'], [p[0] for p in self.posted])

    def test_waking_can_restart_instead(self):
        ENV.settings["action_on_wake"] = "restart"
        self.win._onWake()
        self.assertEqual([('restart on wake', self.win._closeSessionWithOption, ('restart',))], self.posted)

    def test_waking_waits_on_its_own_thread(self):
        ENV.settings["action_on_wake"] = "wait_5"
        with mock.patch.object(library.threading, "Thread") as thread:
            self.win._onWake()
        self.assertEqual((5,), thread.call_args[1]["args"])
        thread.return_value.start.assert_called_once_with()


class ResumeRetryTest(ManagerTestCase):
    def test_resuming_retests_an_offline_sidebar_server(self):
        self.watch(self.animal)
        self.round_ended(self.animal, False)
        self.manager.cancelOfflineRetry()  # gone to sleep
        self.manager.resumeOfflineRetry()
        self.assertEqual([5, 5], self.delays())

    def test_resuming_leaves_an_online_or_gone_server_alone(self):
        self.watch(self.animal)
        self.manager.resumeOfflineRetry()
        self.animal.offline = self.animal.gone = True
        self.manager.resumeOfflineRetry()
        self.assertEqual([], self.delays())


class PlaybackManagerSignalsTest(KodiTestCase):
    def test_deinit_unhooks_everything_it_hooked(self):
        from lib import playback_utils

        class Emitter(object):
            def __init__(self):
                self.hooked = []

            def on(self, signal, handler):
                self.hooked.append((signal, handler))

            def off(self, signal, handler):
                self.hooked.remove((signal, handler))

        emitter = Emitter()
        with mock.patch.object(playback_utils.plexapp.util, "APP", emitter):
            manager = playback_utils.PlaybackManager()
            self.assertTrue(emitter.hooked)
            manager.deinit()
        self.assertEqual([], emitter.hooked)


class UpdatePromptTest(KodiTestCase):
    """The update checker's questions, answered from LibraryWindow.tick() - HomeWindow's
    service_responder() went with it in 12675d11, so an update was never offered."""

    def setUp(self):
        KodiTestCase.setUp(self)
        ensure_plex_interface()
        self.props = {}
        self.posted = []
        for patcher in (mock.patch.object(library.util, "getGlobalProperty",
                                          side_effect=lambda key, **kw: self.props.get(key, '')),
                        mock.patch.object(library.util, "setGlobalProperty",
                                          side_effect=lambda key, val, **kw: self.props.__setitem__(key, val)),
                        mock.patch.object(library.util, "waitForConsumption"),
                        mock.patch.object(library.plexapp, "SERVERMANAGER", mock.Mock())):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.win = library.LibraryWindow.__new__(library.LibraryWindow)
        self.win._shuttingDown = False
        self.win._ignoreTick = False
        self.win._backStack = []
        self.win._updatePromptPosted = False
        self.win._updateSourceChanged = None
        self.win.postUI = lambda name, fn, args=(), kwargs=None: self.posted.append(name)
        self.win.stopRetryingRequests = mock.Mock()
        self.win._closeSessionWithOption = mock.Mock()

    def test_an_offered_update_is_asked_about_once(self):
        self.props['notify_update'] = '1.15.0'
        self.win.tick()
        self.win.tick()
        self.assertEqual(['update available'], self.posted)

    def test_it_waits_while_a_screen_is_open_on_top(self):
        self.props['notify_update'] = '1.15.0'
        self.win._backStack = [("entry", {})]
        self.win.tick()
        self.assertEqual([], self.posted)

    def answer(self, button):
        self.props.update(notify_update='1.15.0', update_available='1.15.0')
        self.win._updatePromptPosted = True
        with mock.patch.object(library.optionsdialog, "show", return_value=button):
            self.win._promptUpdate()

    def test_yes_tells_the_checker_and_closes_for_it(self):
        self.answer(0)
        self.assertEqual('commence', self.props['update_response'])
        self.assertEqual('', self.props['notify_update'])
        self.win._closeSessionWithOption.assert_called_once_with('update')
        self.win.stopRetryingRequests.assert_called_once_with()
        self.assertFalse(self.win._updatePromptPosted)

    def test_later_tells_the_checker_and_carries_on(self):
        self.answer(1)
        self.assertEqual('cancel', self.props['update_response'])
        self.win._closeSessionWithOption.assert_not_called()
        self.assertFalse(self.win._updatePromptPosted)

    def test_a_changed_update_source_is_passed_on(self):
        self.win._onUpdateSourceChanged(value='beta')
        self.win.tick()
        self.assertEqual('beta', self.props['update_source_changed'])
        self.assertIsNone(self.win._updateSourceChanged)


class EmptyLibraryTest(KodiTestCase):
    """A library section whose rows come back with nothing in any of them is empty, and the
    Recommended view says so - the grid's "no content" message."""

    class Host(object):
        _recommendedHubsCallback = library.HubsMixin._recommendedHubsCallback
        HUB_CONTROL_ID = 400
        HUB_ROTATION_RING = [401, 400, 402, 403]

        def __init__(self):
            self.props = {}
            self._listGeneration = 1
            self.closing = False
            self.contentMode = 'recommended'
            self.lock = library.threading.Lock()
            self.sectionHubs = {}
            self._pendingRestoreHubId = None
            self.hubControls = []

        def setBoolProperty(self, key, value):
            self.props[key] = value and '1' or ''

        def sortHubsByUserOrder(self, hubs, **kwargs):
            return list(hubs)

        def _reconcileWithHubs(self, *args):
            pass

        _visibleHubsFor = library.HubsMixin._visibleHubsFor

        def isHubHidden(self, *args):
            return False

        def _bindAllHubSlots(self):
            pass

        def updateServerUnavailable(self):
            pass

        def _retryEmptyAfterReturn(self):
            pass

        def _anchorControlId(self):
            return 400

        def _noteSectionEmpty(self, empty):
            self.noted = empty

    def hub(self, items):
        return mock.Mock(items=items, getCleanHubIdentifier=lambda **kw: 'h')

    def bind(self, hubs, key="1", **server_state):
        self.host = self.Host()
        server = mock.Mock(offline=False, suspect=False, uuid=ANIMAL)
        server.configure_mock(**server_state)
        self.host._recommendedHubsCallback(mock.Mock(key=key, server=server), hubs, 1)
        return self.host.props.get('no.content')

    def test_rows_with_nothing_in_them_say_the_library_is_empty(self):
        self.assertEqual('1', self.bind([self.hub([]), self.hub([])]))

    def test_rows_with_items_do_not(self):
        self.assertEqual('', self.bind([self.hub([]), self.hub(["an item"])]))

    def test_home_does_not(self):
        self.assertEqual('', self.bind([], key=None))

    def test_a_failed_fetch_does_not(self):
        hubs = mock.MagicMock()
        hubs.__iter__.return_value = iter([])
        hubs.invalid = True
        self.assertEqual('', self.bind(hubs))

    def test_it_is_remembered_for_the_tabs_row(self):
        self.bind([self.hub([])])
        self.assertTrue(self.host.noted)
        self.bind([self.hub(["an item"])])
        self.assertFalse(self.host.noted)

    def test_a_server_being_retested_says_nothing_about_the_library(self):
        self.assertEqual('', self.bind([], suspect=True))
        self.assertFalse(hasattr(self.host, 'noted'))


class SectionTabsTest(KodiTestCase):
    """The tabs row only shows when it has something to switch between."""

    def setUp(self):
        KodiTestCase.setUp(self)
        self.win = library.LibraryWindow.__new__(library.LibraryWindow)
        self.props = {}
        self.win.setProperty = lambda key, value: self.props.__setitem__(key, value)
        self.win.setBoolProperty = lambda key, value: self.props.__setitem__(key, value and '1' or '')
        self.win._tabListIsPlaylists = False
        self.win._tabListPlaylistTypes = ()
        self.win.section = mock.Mock(TYPE='movie', key='1', server=mock.Mock(uuid=ANIMAL))
        self.addCleanup(library._emptySections.clear)

    def playlists(self, *types):
        self.win.section.TYPE = 'playlists'
        self.win._viewPlaylists = [mock.Mock(playlistType=t) for t in types]
        self.win._tabListIsPlaylists = True
        self.win._tabListPlaylistTypes = self.win._playlistTypes()

    def test_a_library_with_content_shows_it(self):
        self.assertFalse(self.win._hideSectionTabs())

    def test_home_does_not(self):
        self.win.section.TYPE = 'mixed'
        self.assertTrue(self.win._hideSectionTabs())

    def test_an_empty_library_does_not_and_hides_it_at_once(self):
        self.win._noteSectionEmpty(True)
        self.assertEqual('1', self.props['hide.section_tabs'])
        self.assertTrue(self.win._hideSectionTabs())

    def test_a_library_that_gains_content_shows_it_again(self):
        self.win._noteSectionEmpty(True)
        self.win._noteSectionEmpty(False)
        self.assertEqual('', self.props['hide.section_tabs'])

    def test_both_kinds_of_playlist_get_a_tab_each(self):
        self.playlists('video', 'audio', 'video')
        self.assertEqual(('audio', 'video'), self.win._tabListPlaylistTypes)
        self.assertFalse(self.win._hideSectionTabs())

    def test_one_kind_of_playlist_gets_no_tabs_row(self):
        self.playlists('video')
        self.assertEqual(('video',), self.win._tabListPlaylistTypes)
        self.assertTrue(self.win._hideSectionTabs())

    def test_playlists_open_on_a_tab_that_has_some(self):
        self.win.section.TYPE = 'playlists'
        self.win._viewPlaylists = [mock.Mock(playlistType='video')]
        self.win._tabListHasCategories = self.win._tabListHasCollections = False
        settings = mock.Mock(itemType='audio')
        settings.setItemType.side_effect = lambda t: setattr(settings, 'itemType', t)
        self.win.librarySettings = settings
        self.win._tabListNeedsRebuild(self.win.section)
        self.assertEqual('video', self.win.itemType)
