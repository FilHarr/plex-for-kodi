# coding=utf-8
"""
plex.tv's Discover limiting requests (a 429, live 2026-10-05 for over half an hour), ported from
pannal/plex-for-kodi 4f9b12d1: the 429 isn't retried by urllib3 (which would sleep its Retry-After
on the asking thread), it starts a cooldown during which Discover isn't asked at all - asking only
prolongs the limit - and it reaches the screens as RateLimited, with the wait, for their notice.

Importing lib.windows.* starts lib.player's monitor thread unless abort_requested is set first.
"""

from __future__ import absolute_import

from unittest import mock

from kodienv import ENV

ENV.abort_requested = True
from .test_server_state import make_server  # noqa: E402 - imports plexnet's server manager safely
from lib.windows import preplay  # noqa: E402
from lib import util  # noqa: E402
from plexnet import exceptions, myplexserver, plexserver  # noqa: E402

from .base import KodiTestCase  # noqa: E402

URL = 'https://discover.provider.plex.tv/library/sections/watchlist/all?X-Plex-Token=tok'


class LimitedServer(plexserver.PlexServer):
    RATE_LIMIT_COOLDOWN = True


def limited():
    server = make_server('discover-uuid', 'discover.plex.tv')
    server.__class__ = LimitedServer
    server.buildUrl = lambda path, includeToken=False: URL
    return server


def response(status, retry_after=None):
    r = mock.Mock(status_code=status, text='<MediaContainer/>')
    r.headers = {'Retry-After': retry_after} if retry_after is not None else {}
    return r


class RetryAfterTest(KodiTestCase):
    def test_seconds_a_date_or_the_default(self):
        self.assertEqual(30, plexserver.retryAfterSeconds('30'))
        self.assertEqual(60, plexserver.retryAfterSeconds(None))
        self.assertEqual(7, plexserver.retryAfterSeconds('soon', default=7))
        self.assertEqual(0, plexserver.retryAfterSeconds('Wed, 21 Oct 2015 07:28:00 GMT'))


class CooldownTest(KodiTestCase):
    def setUp(self):
        super(CooldownTest, self).setUp()
        patcher = mock.patch.dict(plexserver._RATE_LIMIT_UNTIL, clear=True)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.server = limited()
        self.get = mock.Mock(return_value=response(429, '45'))
        self.get.__name__ = 'get'
        self.server.session = mock.Mock(get=self.get)

    def test_a_429_is_a_rate_limit_with_its_wait(self):
        with self.assertRaises(exceptions.RateLimited) as caught:
            self.server.query('/library/sections/watchlist/all')
        self.assertEqual(45, caught.exception.retry_after)
        self.assertFalse(caught.exception.from_cooldown)
        # still a BadRequest, as every caller already handles
        self.assertIsInstance(caught.exception, exceptions.BadRequest)

    def test_then_plex_tv_is_not_asked_until_the_wait_is_over(self):
        with self.assertRaises(exceptions.RateLimited):
            self.server.query('/a')
        with self.assertRaises(exceptions.RateLimited) as caught:
            self.server.query('/b')
        self.assertTrue(caught.exception.from_cooldown)
        self.assertEqual(1, self.get.call_count)

    def test_asked_again_once_it_is(self):
        with self.assertRaises(exceptions.RateLimited):
            self.server.query('/a')
        self.get.return_value = response(200)
        with mock.patch.object(plexserver, '_cooldownTime', lambda: 10 ** 12):
            self.assertIsNotNone(self.server.query('/b'))
        self.assertEqual(2, self.get.call_count)

    def test_another_server_has_no_cooldown(self):
        # a PMS answering 429 is an ordinary refusal
        server = make_server('pms-uuid', 'Animal')
        server.buildUrl = lambda path, includeToken=False: 'http://192.168.1.7:32400/x?X-Plex-Token=tok'
        server.session = mock.Mock(get=self.get)
        with self.assertRaises(exceptions.BadRequest) as caught:
            server.query('/x')
        self.assertNotIsInstance(caught.exception, exceptions.RateLimited)
        self.assertEqual({}, plexserver._RATE_LIMIT_UNTIL)


class DiscoverRetryTest(KodiTestCase):
    def test_a_429_is_not_retried_by_urllib3(self):
        retry = myplexserver.DiscoverRetry(total=3)
        self.assertFalse(retry.is_retry('GET', 429, has_retry_after=True))
        self.assertTrue(retry.is_retry('GET', 503, has_retry_after=True))


class WatchlistNoticeTest(KodiTestCase):
    def test_with_the_wait_when_plex_tv_said(self):
        with mock.patch.object(util, 'showNotification') as notify:
            util.notifyWatchlistUnavailable(exceptions.RateLimited(45))
            util.notifyWatchlistUnavailable(exceptions.BadRequest('(503)'))
        self.assertEqual(['Plex is temporarily limiting Watchlist requests. Try again in 45 seconds.',
                          "Your Watchlist isn't available right now"],
                         [c[0][0] for c in notify.call_args_list])


class WatchlistItemTest(KodiTestCase):
    def test_a_refused_item_closes_with_the_notice(self):
        win = preplay.PrePlayWindow.__new__(preplay.PrePlayWindow)
        win.isExternal = True
        win.video = mock.Mock(reloadFailed=True, reloadError=exceptions.RateLimited(45))
        win.watchlist_setup = win.paintClickedItem = mock.Mock()
        # setup()'s busy spinner: a real window, which the test stubs can't make
        with mock.patch.object(preplay.util, 'notifyWatchlistUnavailable') as notify, \
                mock.patch.object(preplay.busy, 'BusyWindow'):
            with self.assertRaises(util.NoDataException):
                win.setup()
        notify.assert_called_once_with(win.video.reloadError)
