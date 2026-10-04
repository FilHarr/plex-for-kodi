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

    def select(self, server):
        self.manager.selectedServer = server
        self.manager.searchContext.active = False

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
        self.select(self.animal)
        self.animal.pendingReachabilityRequests = 3
        self.manager.updateReachabilityResult(self.animal, False)
        self.assertFalse(self.animal.offline)
        self.assertEqual([], self.signals)

    def test_a_round_ending_unreachable_puts_the_selected_server_offline_but_keeps_it(self):
        self.select(self.animal)
        self.round_ended(self.animal, False)
        self.assertTrue(self.animal.offline)
        self.assertIs(self.animal, self.manager.selectedServer)
        self.assertEqual([('offline', 'Animal')], self.signals)
        self.assertEqual([5], self.delays())

    def test_the_change_is_signalled_once(self):
        self.select(self.animal)
        self.round_ended(self.animal, False)
        self.round_ended(self.animal, False)
        self.assertEqual([('offline', 'Animal')], self.signals)
        self.assertEqual([5], self.delays())  # one retest pending at a time

    def test_coming_back_is_signalled_and_stops_the_retests(self):
        self.select(self.animal)
        self.round_ended(self.animal, False)
        self.animal.activeConnection = self.animal.connections[0]
        self.round_ended(self.animal, True)
        self.assertFalse(self.animal.offline)
        self.assertEqual([('offline', 'Animal'), ('online', 'Animal')], self.signals)
        self.assertTrue(self.timers[0].canceled)
        self.assertEqual(0, self.manager.offlineRetryStep)

    def test_retests_back_off(self):
        self.select(self.animal)
        self.round_ended(self.animal, False)
        with mock.patch.object(self.animal, "updateReachability"):
            for _ in range(5):
                self.manager.onOfflineRetryTimer()  # starts nothing, so it schedules the next itself
        self.assertEqual([5, 10, 30, 60, 60, 60], self.delays())

    def test_a_retest_round_ending_offline_schedules_the_next(self):
        self.select(self.animal)
        self.round_ended(self.animal, False)
        with mock.patch.object(self.animal, "updateReachability",
                               side_effect=lambda force: setattr(self.animal, "pendingReachabilityRequests", 2)):
            self.manager.onOfflineRetryTimer()
        self.assertEqual([5], self.delays())  # the round is under way; its end schedules the next
        self.round_ended(self.animal, False)
        self.assertEqual([5, 10], self.delays())

    def test_other_servers_go_offline_without_retests(self):
        self.select(self.animal)
        self.round_ended(self.oscar, False)
        self.assertTrue(self.oscar.offline)
        self.assertEqual([('offline', 'Oscar')], self.signals)
        self.assertEqual([], self.delays())

    def test_no_switch_to_another_server_mid_session(self):
        self.select(self.animal)
        self.round_ended(self.animal, False)
        self.manager.searchContext.bestServer = self.oscar
        self.round_ended(self.oscar, True)
        self.assertIs(self.animal, self.manager.selectedServer)


class SuspectSignalTest(ManagerTestCase):
    """A query with no answer is said at once ('suspect:server'), before the retest's verdict:
    offline, or 'recovered:server' when it answers after all."""

    def test_a_query_with_no_answer_is_said_at_once(self):
        self.select(self.animal)
        self.manager.onServerSuspect(self.animal)
        self.assertTrue(self.animal.suspect)
        self.assertEqual([('suspect', 'Animal')], self.signals)

    def test_once_per_retest(self):
        self.select(self.animal)
        self.manager.onServerSuspect(self.animal)
        self.manager.onServerSuspect(self.animal)
        self.assertEqual([('suspect', 'Animal')], self.signals)

    def test_not_while_it_is_known_to_be_offline(self):
        self.select(self.animal)
        self.round_ended(self.animal, False)
        self.manager.onServerSuspect(self.animal)
        self.assertEqual([('offline', 'Animal')], self.signals)
        self.assertFalse(self.animal.suspect)

    def test_answering_after_all_is_recovered(self):
        self.select(self.animal)
        self.manager.onServerSuspect(self.animal)
        self.round_ended(self.animal, True)
        self.assertEqual([('suspect', 'Animal'), ('recovered', 'Animal')], self.signals)
        self.assertFalse(self.animal.suspect)

    def test_a_reachable_result_mid_round_decides_nothing(self):
        # the connection the query failed on is still the active one until its own result is in
        self.select(self.animal)
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
        self.select(self.animal)
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
        self.select(self.animal)
        self.animal.activeConnection = None
        with mock.patch.object(plexservermanager, "MANAGER", self.manager), \
                mock.patch.object(self.animal, "updateReachability"):
            self.animal.markSuspect()
        self.assertEqual([('suspect', 'Animal'), ('offline', 'Animal')], self.signals)

    def test_try_again_retests_now_instead_of_at_the_next_step(self):
        self.select(self.animal)
        self.round_ended(self.animal, False)
        with mock.patch.object(self.animal, "updateReachability",
                               side_effect=lambda force: setattr(self.animal, "pendingReachabilityRequests", 2)):
            self.assertTrue(self.manager.retestSelectedServerNow())
        self.assertTrue(self.timers[0].canceled)
        self.round_ended(self.animal, False)
        self.assertEqual([5, 10], self.delays())  # still offline: the backoff carries on


class SelectionTest(ManagerTestCase):
    def test_selecting_a_server_ends_the_startup_search(self):
        self.assertTrue(self.manager.searchContext.active)
        with mock.patch.object(self.manager, "saveState"):
            self.assertTrue(self.manager.setSelectedServer(self.oscar, True))
        self.assertFalse(self.manager.searchContext.active)

    def test_an_owned_server_that_does_not_answer_keeps_its_cached_prefs(self):
        self.oscar.owned = True
        with mock.patch.object(self.manager, "saveState"), \
                mock.patch.object(self.oscar, "getPrefs", return_value=[]), \
                mock.patch.object(pnUtil.INTERFACE, "getRegistry", return_value='{"LibraryVideoPlayedThreshold": 90}'), \
                mock.patch.object(pnUtil.INTERFACE, "setRegistry") as store:
            self.manager.setSelectedServer(self.oscar, True)
        self.assertEqual({"LibraryVideoPlayedThreshold": 90}, self.oscar.prefs)
        self.assertNotIn("PlexServerPrefs", [c[0][0] for c in store.call_args_list])

    def test_another_dropped_server_is_removed(self):
        self.select(self.animal)
        self.manager.removeServer(self.oscar, MYPLEX)
        self.assertNotIn(OSCAR, self.manager.serversByUuid)


MYPLEX = plexconnection.PlexConnection.SOURCE_MYPLEX
DISCOVERED = plexconnection.PlexConnection.SOURCE_DISCOVERED


class GoneTest(ManagerTestCase):
    """A server plex.tv no longer lists is off the account: removed, not kept as unavailable.
    Unavailable (offline) is only for a server the account still has that isn't answering."""

    def setUp(self):
        ManagerTestCase.setUp(self)
        self.gone = []
        self.manager.on('gone:selectedServer',
                        lambda server=None, replacement=None, **kw: self.gone.append((server, replacement)))
        patcher = mock.patch.object(self.manager, "saveState")
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_dropped_by_plex_tv_it_is_removed_and_another_server_takes_over(self):
        self.select(self.animal)
        self.oscar.activeConnection.state = self.oscar.activeConnection.STATE_REACHABLE
        self.manager.removeServer(self.animal, MYPLEX)
        self.assertNotIn(ANIMAL, self.manager.serversByUuid)
        self.assertTrue(self.animal.gone)
        self.assertEqual([(self.animal, self.oscar)], self.gone)
        self.assertIs(self.oscar, self.manager.selectedServer)
        self.assertEqual([], self.delays())

    def test_with_nothing_else_answering_it_stays_selected_until_another_is_picked(self):
        self.select(self.animal)
        self.manager.removeServer(self.animal, MYPLEX)
        self.assertIs(self.animal, self.manager.selectedServer)
        self.assertEqual([(self.animal, None)], self.gone)
        self.assertTrue(self.animal.offline)
        self.round_ended(self.animal, False)
        self.assertEqual([], self.delays(), "no retests: it isn't coming back by being retested")

    def test_listed_again_it_comes_back_as_the_same_server(self):
        self.select(self.animal)
        self.manager.removeServer(self.animal, MYPLEX)
        relisted = make_server(ANIMAL, "Animal")
        self.assertIs(self.animal, self.manager.mergeServer(relisted))
        self.assertIs(self.animal, self.manager.serversByUuid[ANIMAL])
        self.assertFalse(self.animal.gone)

    def test_a_missed_discovery_reply_keeps_it_offline(self):
        # GDM is UDP broadcast: one unanswered round says nothing about the account
        self.select(self.animal)
        self.manager.removeServer(self.animal, DISCOVERED)
        self.assertIn(ANIMAL, self.manager.serversByUuid)
        self.assertFalse(self.animal.gone)
        self.assertTrue(self.animal.offline)
        self.assertEqual([], self.gone)
        self.assertEqual([5], self.delays())

    def test_signing_out_does_not_count(self):
        self.select(self.animal)
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
        section = mock.Mock(key="1", server=self.server)
        self.server.suspect = True
        self.assertFalse(library._sectionHasCollections(section))
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
    """The interim UI: the sidebar shows the selected server unreachable, and coming back reloads
    the section in place."""

    def setUp(self):
        KodiTestCase.setUp(self)
        ensure_plex_interface()
        self.server = make_server(ANIMAL, "Animal")
        servers = mock.Mock(selectedServer=self.server)
        account = mock.Mock(title="Phil", username="phil", ID="1", thumb="")
        for patcher in (mock.patch.object(library.plexapp, "SERVERMANAGER", servers),
                        mock.patch.object(library.plexapp, "ACCOUNT", account),
                        mock.patch.object(library.util, "showNotification")):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.win = library.LibraryWindow.__new__(library.LibraryWindow)
        self.props = {}
        self.win.setProperty = lambda key, value: self.props.__setitem__(key, value)
        self.win.getProperty = lambda key: self.props.get(key, '')
        self.win.section = "the section"
        self.win._backStack = []
        self.win._shuttingDown = False
        self.win._isHostedShell = False
        self.win.closing = False
        self.win.contentMode = 'recommended'
        self.win.visibleHubs = []
        self.win.openSection = mock.Mock()

    def test_an_offline_server_shows_the_error_icon(self):
        self.server.offline = True
        self.win.displayServerAndUser()
        self.assertEqual('script.plex/home/device/error.png', self.props['server.icon'])
        # the button below the sidebar is the Libraries picker's now; its icon still says it
        self.assertEqual('Libraries', self.props['server.name'])

    def test_coming_back_reloads_the_section_in_place(self):
        self.win.onServerOnline(server=self.server)
        self.win.openSection.assert_called_once_with("the section", force=True, fresh=False)
        self.assertEqual('script.plex/home/device/plex.png', self.props['server.icon'])

    def test_coming_back_leaves_an_open_screen_chain_alone(self):
        self.win._backStack = [("entry", {})]
        self.win.onServerOnline(server=self.server)
        self.win.openSection.assert_not_called()

    def test_a_gone_server_says_where_it_switched_to(self):
        self.win.onSelectedServerGone(server=self.server, replacement=make_server(OSCAR, "Oscar"))
        message = library.util.showNotification.call_args[0][0]
        self.assertIn("Animal", message)
        self.assertIn("Oscar", message)

    def test_a_gone_server_with_nothing_to_switch_to_asks_for_another(self):
        self.server.offline = True
        self.win.onSelectedServerGone(server=self.server, replacement=None)
        self.assertIn("Choose another server", library.util.showNotification.call_args[0][0])
        self.assertEqual('script.plex/home/device/error.png', self.props['server.icon'])

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
        self.win.openSection.assert_called_once_with("the section", force=True, fresh=False)
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
                                                args=("the section",), kwargs={'force': True, 'fresh': False})

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
        library.plexapp.SERVERMANAGER.retestSelectedServerNow.return_value = True
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
    waking did nothing at all. Refreshing hubs is wake-only until rows can be rebound in place."""

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

    def test_the_tick_does_not_refresh_hubs(self):
        # HomeWindow's 5-minute refresh waits for a rebind-in-place refresh (the plan's Phase 7)
        self.win._hubsBoundAt = 0.0
        ENV.cond_visibility["System.IdleTime(60)"] = True
        self.win.tick()
        self.assertEqual([], self.posted)

    def test_a_refresh_reloads_the_recommended_view_in_place(self):
        self.win.refreshLastSection()
        self.win.openSection.assert_called_once_with("the section", force=True, fresh=False)
        self.servers.resumeOfflineRetry.assert_called_once_with()

    def test_a_refresh_lands_back_on_the_same_hub_row(self):
        # the rebuilt view starts on the first row unless told otherwise, as Back tells it
        seen = []
        self.win.openSection = mock.Mock(side_effect=lambda *a, **kw: seen.append(self.win._pendingRestoreHubId) or True)
        self.win.refreshLastSection()
        self.assertEqual(['movie.recentlyadded'], seen)

    def test_a_declined_refresh_drops_the_pending_row(self):
        self.win.openSection = mock.Mock(return_value=False)
        self.win.refreshLastSection()
        self.assertIsNone(self.win._pendingRestoreHubId)

    def test_a_refresh_leaves_a_grid_a_chain_or_a_video_alone(self):
        import xbmc
        for setup in (lambda: setattr(self.win, 'contentMode', 'library'),
                      lambda: setattr(self.win, '_backStack', [("entry", {})]),
                      lambda: setattr(xbmc.Player, 'playing_video', True)):
            self.win.contentMode, self.win._backStack, xbmc.Player.playing_video = 'recommended', [], False
            setup()
            self.win.refreshLastSection()
        self.win.openSection.assert_not_called()

    def test_sleep_pauses_ticks_and_offline_retests(self):
        self.win._onSleep()
        self.assertTrue(self.win._ignoreTick)
        self.servers.cancelOfflineRetry.assert_called_once_with()

    def test_waking_checks_the_server_then_refreshes(self):
        self.win._ignoreTick = True
        self.win._afterWake(0)
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
    def test_resuming_retests_an_offline_selected_server(self):
        self.select(self.animal)
        self.round_ended(self.animal, False)
        self.manager.cancelOfflineRetry()  # gone to sleep
        self.manager.resumeOfflineRetry()
        self.assertEqual([5, 5], self.delays())

    def test_resuming_leaves_an_online_or_gone_server_alone(self):
        self.select(self.animal)
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
