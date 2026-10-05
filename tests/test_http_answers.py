# coding=utf-8
"""
An async request answers its callback exactly once, whatever happened to it.

Requests that failed to connect (refused, timed out, unreachable, no such host) used to return
without calling back at all: http.HttpRequest._startAsync() caught ConnectionError and just
unlisted itself, and the TimeoutException it expected for timeouts was never raised. Anything
counting on the answer waited for the rest of the session - a server's reachability test stayed
"pending" and was never run again (live: Animal's Docker-bridge address 192.168.90.15), and with
plex.tv unreachable neither the cached resources nor the account's offline mode ever kicked in.

Also covered: the callers that start seeing failures because of it (play queues, home users,
plex.tv resources), cancel() racing the answer, and how long a failure takes - the connect now
fails as soon as the OS knows, and reachability tests make one attempt (measured on the dev PC:
refused 10.1 s -> 2.0 s, unreachable 10.1 s -> 2.6 s, each now with an answer).
"""

from __future__ import absolute_import

import errno
import socket
import sys
import threading
import time
import types

from kodienv import ENV

ENV.abort_requested = True
import requests  # noqa: E402
import urllib3  # noqa: E402
import plexnet  # noqa: E402
from plexnet import exceptions as plexExceptions, plexlibrary  # noqa: E402
from plexnet import (asyncadapter, callback, http, myplexaccount, myplexmanager, plexapp, plexconnection,  # noqa: E402
                     playqueue, plexresult, plexserver, util as pnUtil)

from .base import KodiTestCase, ensure_plex_interface  # noqa: E402

try:
    from unittest import mock
except ImportError:
    import mock

UUID = "50c3d0b05067c152d84935cdea0ac8af7fc31d06"
ROOT_XML = ('<MediaContainer machineIdentifier="{0}" version="1.43.3.10896" friendlyName="Oscar" '
            'transcoderVideo="1"/>').format(UUID)

def wrapped(socket_error):
    """A connect failure as requests raises it: urllib3 files the socket error under ProtocolError,
    gives up with MaxRetryError, and requests wraps that in ConnectionError."""
    return requests.exceptions.ConnectionError(urllib3.exceptions.MaxRetryError(
        None, "/", urllib3.exceptions.ProtocolError("Connection aborted.", socket_error)))


FAILURES = [
    ("connect timeout", requests.exceptions.ConnectTimeout("connect timed out")),
    ("read timeout", requests.exceptions.ReadTimeout("read timed out")),
    ("name lookup", wrapped(socket.gaierror(11001, "getaddrinfo failed"))),
    ("refused", wrapped(ConnectionRefusedError(errno.ECONNREFUSED, "refused"))),
    ("no route", wrapped(OSError(errno.EHOSTUNREACH, "no route to host"))),
    ("dropped", urllib3.exceptions.ProtocolError("connection aborted")),
    ("anything else", ValueError("boom")),
]


class FakeResponse(object):
    def __init__(self, status=200, text=ROOT_XML):
        self.status_code = status
        self.text = text
        self.content = text.encode("utf-8")
        self.reason = "OK"
        self.ok = 200 <= status < 300
        self.headers = {}

    def close(self):
        pass


class Answers(object):
    def __init__(self):
        self.calls = []

    def done(self, request, response, context):
        self.calls.append(response.getStatus())


def request_with(answers, url="http://192.168.90.15:32400/"):
    req = http.HttpRequest(url)
    ctx = req.createRequestContext("test", callback.Callable(answers.done))
    ctx.request = req
    return req, ctx


class AnswerOnceTest(KodiTestCase):
    def setUp(self):
        KodiTestCase.setUp(self)
        ensure_plex_interface()

    def test_every_failure_answers_once_with_an_empty_response(self):
        for name, error in FAILURES:
            with self.subTest(failure=name):
                answers = Answers()
                req, ctx = request_with(answers)
                with mock.patch.object(req.session, "get", side_effect=error):
                    req._startAsync(context=ctx)
                self.assertEqual([0], answers.calls)

    def test_a_success_answers_with_its_status(self):
        answers = Answers()
        req, ctx = request_with(answers)
        with mock.patch.object(req.session, "get", return_value=FakeResponse(200)):
            req._startAsync(context=ctx)
        self.assertEqual([200], answers.calls)

    def test_a_handler_that_raises_still_unlists_the_request(self):
        req = http.HttpRequest("http://192.168.90.15:32400/")
        ctx = req.createRequestContext("test", callback.Callable(self._raiser))
        pnUtil.APP.pendingRequests[req.getIdentity()] = ctx
        with mock.patch.object(req.session, "get", return_value=FakeResponse(200)):
            req._startAsync(context=ctx)
        self.assertNotIn(req.getIdentity(), pnUtil.APP.pendingRequests)

    def _raiser(self, request, response, context):
        raise ValueError("handler bug")

    def test_cancel_before_the_answer_stops_it(self):
        answers = Answers()
        req, ctx = request_with(answers)
        self.assertTrue(req.cancel())
        with mock.patch.object(req.session, "get", return_value=FakeResponse(200)):
            req._startAsync(context=ctx)
        self.assertEqual([], answers.calls)

    def test_cancel_after_the_answer_reports_it_was_too_late(self):
        answers = Answers()
        req, ctx = request_with(answers)
        with mock.patch.object(req.session, "get", return_value=FakeResponse(200)):
            req._startAsync(context=ctx)
        self.assertFalse(req.cancel())
        self.assertEqual([200], answers.calls)

    def test_a_request_that_fails_at_once_does_not_stay_listed(self):
        # Listed before its thread starts: unlisting can otherwise run first and leak the entry.
        answers = Answers()
        req, ctx = request_with(answers, "http://nonexistent.invalid:32400/")
        with mock.patch.object(req.session, "get",
                               side_effect=requests.exceptions.ConnectionError("getaddrinfo failed")):
            pnUtil.APP.startRequest(req, ctx)
            req.thread.join(5)
        self.assertEqual([0], answers.calls)
        self.assertNotIn(req.getIdentity(), pnUtil.APP.pendingRequests)

    def test_failures_are_named_for_the_log(self):
        names = [http.describeFailure(e) for _, e in FAILURES]
        self.assertEqual(["connect timeout", "read timeout", "name lookup failed", "refused", "no route to host",
                          "connection dropped", "ValueError"], names)


class ReachabilityRoundTest(KodiTestCase):
    """A round of reachability tests settles the server's counts whatever each test did."""

    def setUp(self):
        KodiTestCase.setUp(self)
        ensure_plex_interface()
        # PlexServer reports each result to plexservermanager.MANAGER. The real module builds that
        # on import and hooks it onto the shared APP's signals, which other tests then trip over,
        # so it gets a stand-in.
        stand_in = types.ModuleType("plexnet.plexservermanager")
        stand_in.MANAGER = mock.Mock()
        for patcher in (mock.patch.dict(sys.modules, {"plexnet.plexservermanager": stand_in}),
                        mock.patch.object(plexnet, "plexservermanager", stand_in, create=True)):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.server = plexserver.createPlexServerForName(UUID, "Oscar")
        self.good = plexconnection.PlexConnection(plexconnection.PlexConnection.SOURCE_DISCOVERED,
                                                  "http://192.168.1.69:32400", True, "tok",
                                                  skipLocalCheck=True)
        self.dead = plexconnection.PlexConnection(plexconnection.PlexConnection.SOURCE_MYPLEX,
                                                  "http://192.168.90.15:32400", True, "tok",
                                                  skipLocalCheck=True)
        self.server.connections = [self.good, self.dead]

    def _get(self, url, **kwargs):
        if "192.168.90.15" in url:
            raise requests.exceptions.ConnectTimeout("connect timed out")
        return FakeResponse(200)

    def _join(self):
        for conn in self.server.connections:
            if conn.request is not None and conn.request.thread is not None:
                conn.request.thread.join(5)

    def test_a_failed_test_reports_unreachable_and_settles(self):
        with mock.patch("plexnet.asyncadapter.PlainSession.get", autospec=True,
                        side_effect=lambda s, url, **kw: self._get(url, **kw)):
            self.server.updateReachability(force=True)
            self._join()

        self.assertEqual(0, self.server.pendingReachabilityRequests)
        self.assertFalse(self.dead.hasPendingRequest)
        self.assertEqual(self.dead.STATE_UNREACHABLE, self.dead.state)
        self.assertEqual(self.good.STATE_REACHABLE, self.good.state)
        self.assertIs(self.good, self.server.activeConnection)

    def test_canceling_a_test_in_flight_settles_its_count(self):
        release = threading.Event()

        def slow(session, url, **kwargs):
            release.wait(5)
            return FakeResponse(200)

        with mock.patch("plexnet.asyncadapter.PlainSession.get", autospec=True, side_effect=slow):
            self.server.updateReachability(force=True)
            self.assertEqual(2, self.server.pendingReachabilityRequests)
            self.server.cancelReachability()
            self.assertEqual(0, self.server.pendingReachabilityRequests)
            release.set()
            self._join()

        # the canceled tests never answer, so nothing counts them down a second time
        self.assertEqual(0, self.server.pendingReachabilityRequests)
        self.assertFalse(self.good.hasPendingRequest)
        self.assertFalse(self.dead.hasPendingRequest)

    def test_a_forced_local_refresh_leaves_tests_in_flight_alone(self):
        # It used to zero every pending count to clear tests whose answers never came; with the
        # answers now always coming, that sent the counts negative instead.
        release = threading.Event()
        # spec'd: a call to anything else (the old resetReachabilityState()) fails the test
        manager = mock.Mock(spec=["serversByUuid", "resetLastTest", "updateReachability",
                                  "refreshManualConnections"], serversByUuid={UUID: self.server})
        manager.resetLastTest.side_effect = self.server.resetLastTest
        manager.updateReachability.side_effect = lambda force: None
        with mock.patch("plexnet.asyncadapter.PlainSession.get", autospec=True,
                        side_effect=lambda s, url, **kw: release.wait(5) and FakeResponse(200)), \
                mock.patch.object(pnUtil, "LOCAL_MODE", True), \
                mock.patch.object(plexapp, "SERVERMANAGER", manager), \
                mock.patch("plexnet.gdm.DISCOVERY"):
            self.server.updateReachability(force=True)
            plexapp.refreshResources(True)
            self.assertEqual(2, self.server.pendingReachabilityRequests)
            release.set()
            self._join()
        manager.resetLastTest.assert_called_once_with()
        self.assertEqual(0, self.server.pendingReachabilityRequests)

    def test_a_non_xml_answer_counts_as_unreachable(self):
        with mock.patch("plexnet.asyncadapter.PlainSession.get", autospec=True,
                        return_value=FakeResponse(200, "<html><body>Sign in to the Wi-Fi</body>")):
            self.server.connections = [self.good]
            self.server.updateReachability(force=True)
            self._join()
        self.assertEqual(self.good.STATE_UNREACHABLE, self.good.state)
        self.assertEqual(0, self.server.pendingReachabilityRequests)


class FakeSocket(object):
    def __init__(self, connect_status, so_error=0):
        self.connect_status = connect_status
        self.so_error = so_error

    def connect_ex(self, sa):
        return self.connect_status

    def getsockopt(self, level, option):
        return self.so_error


class FakeSelector(object):
    def __init__(self, ready):
        self.ready = ready

    def register(self, sock, events):
        pass

    def select(self, timeout=None):
        return [("key", asyncadapter.selectors.EVENT_WRITE)] if self.ready else []

    def close(self):
        pass


class ConnectTest(KodiTestCase):
    """The connect waits for the OS to finish it rather than polling connect_ex(), which on Windows
    reads the same for "refused" as for "still trying" - so a refused address ran to the deadline,
    every retry again (8 s for one refused query, measured)."""

    def setUp(self):
        KodiTestCase.setUp(self)
        ensure_plex_interface()
        ENV.abort_requested = False
        self.conn = asyncadapter.AsyncHTTPConnection(host="192.168.1.69", port=32400)
        self.conn.deadline = time.time() + 0.3

    def connect(self, sock, ready):
        with mock.patch.object(asyncadapter.selectors, "DefaultSelector", lambda: FakeSelector(ready)):
            for _ in self.conn._connect(sock, ("192.168.1.69", 32400)):
                pass

    def test_a_refused_connect_fails_as_soon_as_the_os_says_so(self):
        started = time.time()
        with self.assertRaises(socket.error) as caught:
            self.connect(FakeSocket(errno.EINPROGRESS, so_error=errno.ECONNREFUSED), ready=True)
        self.assertEqual(errno.ECONNREFUSED, caught.exception.errno)
        self.assertLess(time.time() - started, 0.2)

    def test_a_finished_connect_returns(self):
        self.connect(FakeSocket(asyncadapter.WIN_EWOULDBLOCK), ready=True)

    def test_an_immediate_failure_is_raised_without_waiting(self):
        with self.assertRaises(socket.error):
            self.connect(FakeSocket(errno.ENETUNREACH), ready=False)

    def test_nothing_happening_runs_to_the_deadline(self):
        with self.assertRaises(urllib3.exceptions.ConnectTimeoutError):
            self.connect(FakeSocket(errno.EINPROGRESS), ready=False)

    def test_a_cancel_stops_the_wait(self):
        self.conn.cancel()
        with self.assertRaises(asyncadapter.CanceledException):
            self.connect(FakeSocket(errno.EINPROGRESS), ready=False)


class RetriesTest(KodiTestCase):
    def setUp(self):
        KodiTestCase.setUp(self)
        ensure_plex_interface()

    def retries(self, request):
        return request.session.get_adapter("http://192.168.1.69:32400/").max_retries.total

    def test_requests_retry_as_the_setting_says(self):
        self.assertEqual(asyncadapter.MAX_RETRIES, self.retries(http.HttpRequest("http://192.168.1.69:32400/")))

    def test_a_request_can_ask_for_no_retries(self):
        self.assertEqual(0, self.retries(http.HttpRequest("http://192.168.1.69:32400/", retries=0)))

    def test_interactive_requests_leave_a_connect_timeout_to_the_server_retest(self):
        retry = http.HttpRequest("http://192.168.1.69:32400/").session.get_adapter("http://x/").max_retries
        self.assertEqual(0, retry.connect)
        self.assertEqual(asyncadapter.MAX_RETRIES, retry.total)

    def test_reachability_tests_make_one_attempt(self):
        server = plexserver.createPlexServerForName(UUID, "Oscar")
        conn = plexconnection.PlexConnection(plexconnection.PlexConnection.SOURCE_DISCOVERED,
                                             "http://192.168.1.69:32400", True, "tok", skipLocalCheck=True)
        with mock.patch.object(pnUtil.APP, "startRequest"):
            conn.testReachability(server)
        self.assertEqual(0, self.retries(conn.request))


class RetryRulesTest(KodiTestCase):
    """Which failures are retried. A definite answer (refused, no route, no such name) is never
    asked again; a connect timeout once; a connection dropped mid-answer up to max_retries."""

    REFUSED = urllib3.exceptions.ProtocolError("Connection aborted.", ConnectionRefusedError(errno.ECONNREFUSED, "refused"))
    WIN_REFUSED = urllib3.exceptions.ProtocolError("Connection aborted.", OSError(10061, "WSAECONNREFUSED"))
    NO_NAME = urllib3.exceptions.ProtocolError("Connection aborted.", socket.gaierror(11001, "getaddrinfo failed"))
    NO_ROUTE = urllib3.exceptions.ProtocolError("Connection aborted.", OSError(errno.EHOSTUNREACH, "no route"))
    CONNECT_TIMEOUT = urllib3.exceptions.ConnectTimeoutError("connect timed out")
    DROPPED = urllib3.exceptions.ProtocolError("Connection aborted.", ConnectionResetError(errno.ECONNRESET, "reset"))

    def setUp(self):
        KodiTestCase.setUp(self)
        ensure_plex_interface()

    def test_definite_answers_are_recognised(self):
        for error in (self.REFUSED, self.WIN_REFUSED, self.NO_NAME, self.NO_ROUTE):
            with self.subTest(error=repr(error)):
                self.assertTrue(asyncadapter.isDefinitiveConnectFailure(error))
        for error in (self.CONNECT_TIMEOUT, self.DROPPED):
            with self.subTest(error=repr(error)):
                self.assertFalse(asyncadapter.isDefinitiveConnectFailure(error))

    def retry(self):
        return asyncadapter.StoppableRetry(total=3, connect=1)

    def test_a_definite_answer_is_not_retried(self):
        with self.assertRaises(urllib3.exceptions.MaxRetryError):
            self.retry().increment("GET", "/", error=self.REFUSED)

    def test_a_connect_timeout_is_retried_once(self):
        once = self.retry().increment("GET", "/", error=self.CONNECT_TIMEOUT)
        with self.assertRaises(urllib3.exceptions.MaxRetryError):
            once.increment("GET", "/", error=self.CONNECT_TIMEOUT)

    def test_a_dropped_connection_keeps_its_retries(self):
        retry = self.retry()
        for _ in range(3):
            retry = retry.increment("GET", "/", error=self.DROPPED)
        with self.assertRaises(urllib3.exceptions.MaxRetryError):
            retry.increment("GET", "/", error=self.DROPPED)

    def test_switching_retries_off_leaves_the_shared_object_alone(self):
        # the adapter hands the same Retry to every request; changing it removed retries for good
        retry = self.retry()
        with mock.patch.object(asyncadapter, "STOP_RETRYING_REQUESTS", True):
            with self.assertRaises(urllib3.exceptions.MaxRetryError):
                retry.increment("GET", "/", error=self.DROPPED)
        self.assertEqual(3, retry.total)
        self.assertIsNotNone(retry.increment("GET", "/", error=self.DROPPED))


class QueryTest(KodiTestCase):
    """PlexServer.query() - the synchronous path - answers None for every way of not getting an
    answer. A read timeout used to escape as an exception while a connect failure returned None."""

    def setUp(self):
        KodiTestCase.setUp(self)
        ensure_plex_interface()
        conn = plexconnection.PlexConnection(plexconnection.PlexConnection.SOURCE_DISCOVERED,
                                             "http://192.168.1.69:32400", True, "tok", skipLocalCheck=True)
        self.server = plexserver.createPlexServerForConnection(conn)
        self.server.name = "Oscar"

    def answer(self, outcome):
        def get(url, **kwargs):
            if isinstance(outcome, Exception):
                raise outcome
            return outcome
        self.server.session.get = get

    def test_every_transport_failure_is_none(self):
        for name, error in FAILURES[:-1] + [("chunked", requests.exceptions.ChunkedEncodingError("cut"))]:
            with self.subTest(failure=name):
                self.answer(error)
                self.assertIsNone(self.server.query("/library/sections"))

    def test_an_error_status_still_raises(self):
        self.answer(FakeResponse(500, ""))
        with self.assertRaises(plexExceptions.BadRequest):
            self.server.query("/library/sections")

    def test_no_connection_is_none_without_refreshing_resources(self):
        self.server.activeConnection = None
        with mock.patch.object(pnUtil, "MANAGER") as manager:
            self.assertIsNone(self.server.query("/library/sections"))
        manager.refreshResources.assert_not_called()

    def test_library_sections_are_empty_when_the_server_does_not_answer(self):
        self.answer(requests.exceptions.ConnectTimeout("connect timed out"))
        library = plexlibrary.Library(None, server=self.server)
        self.assertEqual([], library.sections())


def failed_result(server=None, path="/"):
    result = plexresult.PlexServerResult(server, path)
    result.setResponse(None)
    return result


class FailingCallersTest(KodiTestCase):
    """Callers that only ever saw error statuses before, and now also see connection failures."""

    def setUp(self):
        KodiTestCase.setUp(self)
        ensure_plex_interface()

    def test_a_failed_play_queue_request_ends_the_wait(self):
        pq = playqueue.PlayQueue(plexserver.createPlexServerForName(UUID, "Oscar"), "audio")
        ctx = http.RequestContext()
        ctx.requestType = "create"
        pq.onResponse(None, failed_result(), ctx)
        self.assertTrue(pq.failed)
        # returns at once instead of spinning on responded
        self.assertFalse(pq.waitForInitialization())

    def test_failed_home_users_keep_the_known_list(self):
        account = myplexaccount.MyPlexAccount()
        account.homeUsers = ["kept"]
        account.onHomeUsersUpdateResponse(None, failed_result(), None)
        self.assertEqual(["kept"], account.homeUsers)

    def test_no_resources_and_no_cache_keeps_the_known_servers(self):
        manager = myplexmanager.MyPlexManager()
        servers = mock.Mock()
        with mock.patch.object(pnUtil.INTERFACE, "getRegistry", return_value=None), \
                mock.patch.object(plexapp, "SERVERMANAGER", servers):
            manager.onResourcesResponse(None, failed_result(), None)
        servers.resourcesUnavailable.assert_called_once_with()
        servers.updateFromConnectionType.assert_not_called()
