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
        patcher = mock.patch.object(plexserver.time, "time", side_effect=lambda: self.clock[0])
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
        self.win.section = "the section"
        self.win._backStack = []
        self.win._shuttingDown = False
        self.win.openSection = mock.Mock()

    def test_an_offline_server_shows_the_error_icon(self):
        self.server.offline = True
        self.win.displayServerAndUser()
        self.assertEqual('script.plex/home/device/error.png', self.props['server.icon'])
        self.assertEqual('Animal', self.props['server.name'])

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
        self.win.onServerOffline(server=make_server(OSCAR, "Oscar"))
        self.win.onServerOnline(server=make_server(OSCAR, "Oscar"))
        self.win.openSection.assert_not_called()
        self.assertEqual({}, self.props)
