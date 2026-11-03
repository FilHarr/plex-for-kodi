# coding=utf-8
"""
The account going offline (plex.tv answering unexpectedly, or not at all) and coming back.

Offline used to last the session: nothing asked plex.tv again before the next start or sign-in, and
the Watchlist - its sidebar entry and every screen's Add/Remove buttons - stayed off with no word of
why. plex.tv is now asked again with a backoff while the account is offline; its answer brings the
Watchlist back ('account:online'), and an item screen shown again sets its watchlist up afresh.

Any 4xx used to sign out, a 429 or a 408 too. Only a 401 or a 403 does now - and never the retry's,
which would sign out under a screen in use.
"""

from __future__ import absolute_import

import time

from kodienv import ENV

ENV.abort_requested = True
from plexnet import http, myplexaccount, plexapp  # noqa: E402
from plexnet import util as pnUtil  # noqa: E402

from .base import KodiTestCase, ensure_plex_interface  # noqa: E402
from .test_server_state import FakeTimer  # noqa: E402
from lib.windows import library  # noqa: E402
from lib.windows.mixins import watchlist  # noqa: E402

try:
    from unittest import mock
except ImportError:
    import mock

ACCOUNT_XML = ('<user id="1" title="Phil" username="phil" email="e@x" thumb="http://t/a?x=1" '
               'authenticationToken="tok"><profile_settings/></user>')


def response(status):
    resp = mock.Mock()
    resp.isSuccess.return_value = 200 <= status < 300
    resp.getStatus.return_value = status
    if resp.isSuccess.return_value:
        from xml.etree import ElementTree
        resp.getBodyXml.return_value = ElementTree.fromstring(ACCOUNT_XML)
    return resp


def context(background=False):
    ctx = http.RequestContext()
    ctx.background = background
    return ctx


class AccountTestCase(KodiTestCase):
    def setUp(self):
        KodiTestCase.setUp(self)
        ensure_plex_interface()
        self.account = myplexaccount.MyPlexAccount()
        self.account.ID = "1"
        self.account.authToken = "tok"
        self.account.isSignedIn = True
        # a known home: no home user fetch on success
        self.account.homeUsers = [myplexaccount.HomeUser({"id": "1", "title": "Phil"})]
        self.account.lastHomeUserUpdate = time.time()
        self.timers = []
        self.triggered = []

        def createTimer(delay_ms, function, **kw):
            timer = FakeTimer(delay_ms)
            timer.function = function
            self.timers.append(timer)
            return timer

        for patcher in (mock.patch.object(plexapp, "createTimer", createTimer),
                        mock.patch.object(pnUtil.APP, "addTimer"),
                        mock.patch.object(pnUtil.APP, "clearInitializer"),
                        mock.patch.object(pnUtil.APP, "trigger",
                                          side_effect=lambda signal, **kw: self.triggered.append(signal)),
                        mock.patch.object(pnUtil, "LOCAL_MODE", False),
                        mock.patch.object(pnUtil, "MANAGER", mock.Mock(), create=True),
                        mock.patch.object(plexapp, "refreshResources"),
                        mock.patch.object(self.account, "saveState"),
                        mock.patch.object(self.account, "signOut")):
            patcher.start()
            self.addCleanup(patcher.stop)

    def answer(self, status, background=False):
        self.account.onAccountResponse(None, response(status), context(background))

    def fire(self):
        """The pending retry's timer going off."""
        timer = self.account.offlineRetry
        self.assertIsNotNone(timer)
        with mock.patch.object(self.account, "verifyAccount") as verify:
            timer.function()
        return verify


class OfflineRetryTest(AccountTestCase):
    def test_an_unexpected_answer_goes_offline_and_asks_again_later(self):
        self.answer(503)
        self.assertTrue(self.account.isOffline)
        self.assertEqual([30], [t.delay for t in self.timers])

    def test_no_answer_at_all_too(self):
        self.answer(0)
        self.assertTrue(self.account.isOffline)
        self.assertEqual(1, len(self.timers))

    def test_the_retry_asks_in_the_background_and_backs_off(self):
        self.answer(503)
        for expected in (60, 300, 300):
            verify = self.fire()
            verify.assert_called_once_with(background=True)
            self.answer(503, background=True)
            self.assertEqual(expected, self.timers[-1].delay)

    def test_one_retry_at_a_time(self):
        self.answer(503)
        # Offline Mode in the user menu, failing while the retry waits
        self.answer(503)
        self.assertEqual(1, len(self.timers))

    def test_the_retry_drops_a_switch_flag_left_from_an_offline_switch(self):
        self.answer(503)
        self.account.switchUser = True
        self.fire()
        self.assertFalse(self.account.switchUser)

    def test_back_online_says_so_and_stops_asking(self):
        self.answer(503)
        timer = self.account.offlineRetry
        self.fire()
        self.answer(200, background=True)
        self.assertFalse(self.account.isOffline)
        self.assertIn("account:online", self.triggered)
        self.assertNotIn("change:user", self.triggered)
        self.assertTrue(timer.canceled or self.account.offlineRetry is None)
        self.assertEqual(0, self.account.offlineRetryStep)

    def test_an_answer_when_never_offline_says_nothing(self):
        self.answer(200)
        self.assertNotIn("account:online", self.triggered)

    def test_not_in_local_mode(self):
        with mock.patch.object(pnUtil, "LOCAL_MODE", True):
            self.answer(503)
        self.assertEqual([], self.timers)

    def test_not_without_a_token(self):
        self.account.authToken = None
        self.answer(503)
        self.assertEqual([], self.timers)

    def test_a_timer_going_off_in_local_mode_asks_nothing(self):
        self.answer(503)
        with mock.patch.object(pnUtil, "LOCAL_MODE", True):
            verify = self.fire()
        verify.assert_not_called()

    def test_sleep_cancels_and_wake_starts_again_from_the_first_delay(self):
        self.answer(503)
        self.fire()
        self.answer(503, background=True)
        timer = self.account.offlineRetry
        self.account.cancelOfflineRetry()
        self.assertTrue(timer.canceled)
        self.account.resumeOfflineRetry()
        self.assertEqual(30, self.timers[-1].delay)

    def test_wake_while_online_asks_nothing(self):
        self.account.resumeOfflineRetry()
        self.assertEqual([], self.timers)


class SignOutTest(AccountTestCase):
    def test_a_refused_token_signs_out(self):
        for status in (401, 403):
            self.account.signOut.reset_mock()
            self.answer(status)
            self.account.signOut.assert_called_once_with(True)

    def test_other_4xx_go_offline_instead(self):
        for status in (404, 408, 429):
            self.account.isOffline = False
            self.account.cancelOfflineRetry()
            self.answer(status)
            self.account.signOut.assert_not_called()
            self.assertTrue(self.account.isOffline, status)

    def test_the_retry_never_signs_out(self):
        self.answer(503)
        self.fire()
        self.answer(401, background=True)
        self.account.signOut.assert_not_called()
        self.assertTrue(self.account.isOffline)
        # nor keeps asking with a token plex.tv refuses
        self.assertIsNone(self.account.offlineRetry)


class OnAccountOnlineTest(KodiTestCase):
    def test_the_watchlist_comes_back_to_the_sidebar(self):
        win = mock.Mock(_shuttingDown=False)
        with mock.patch.object(library.sidebar_model, "refreshWatchlistSection") as refresh:
            library.LibraryWindow.onAccountOnline(win, account=None)
        refresh.assert_called_once_with()
        win._rebuildSidebar.assert_called_once_with()

    def test_not_while_shutting_down(self):
        win = mock.Mock(_shuttingDown=True)
        with mock.patch.object(library.sidebar_model, "refreshWatchlistSection") as refresh:
            library.LibraryWindow.onAccountOnline(win)
        refresh.assert_not_called()


class Screen(watchlist.WatchlistUtilsMixin):
    def __init__(self):
        super(Screen, self).__init__()
        self.props = {}

    def setBoolProperty(self, key, value):
        self.props[key] = bool(value)


class WatchlistReinitTest(KodiTestCase):
    def setUp(self):
        KodiTestCase.setUp(self)
        self.pnAccount = mock.Mock(isOffline=True)
        for patcher in (mock.patch.object(watchlist.pnUtil, "ACCOUNT", self.pnAccount, create=True),
                        mock.patch.object(watchlist.util, "getUserSetting", return_value=True)):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.item = mock.Mock(guid="plex://show/abc")

    def test_a_screen_opened_offline_gets_its_buttons_when_shown_again_online(self):
        screen = Screen()
        self.assertFalse(screen.watchlist_setup(self.item))
        self.assertFalse(screen.props["watchlist_enabled"])
        self.pnAccount.isOffline = False
        self.assertTrue(screen.watchlist_reinit(self.item))
        self.assertTrue(screen.props["watchlist_enabled"])

    def test_already_on_it_isnt_news(self):
        self.pnAccount.isOffline = False
        screen = Screen()
        screen.watchlist_setup(self.item)
        self.assertFalse(screen.watchlist_reinit(self.item))

    def test_going_offline_meanwhile_hides_them(self):
        self.pnAccount.isOffline = False
        screen = Screen()
        screen.watchlist_setup(self.item)
        self.pnAccount.isOffline = True
        screen.watchlist_reinit(self.item)
        self.assertFalse(screen.props["watchlist_enabled"])

    def test_a_screen_that_never_set_it_up_stays_without(self):
        # an artist's: ShowWindow's onReInit(), never its watchlist_setup()
        self.pnAccount.isOffline = False
        screen = Screen()
        self.assertFalse(screen.watchlist_reinit(self.item))
        self.assertNotIn("watchlist_enabled", screen.props)
