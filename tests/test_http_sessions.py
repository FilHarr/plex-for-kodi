# coding=utf-8
"""
HttpRequest's session has no request cache (E8 in the navigation review: a cached session opened
the SQLite cache per request, and HttpRequest never caches). The adapter lists each pool once and
pools hold their connections weakly (L5). A cache invalidation vacuums only once enough of the
database is free (L4).
"""

from __future__ import absolute_import

import contextlib
import gc

from kodienv import ENV

ENV.abort_requested = True
from requests_cache import CachedSession  # noqa: E402
from plexnet import asyncadapter, http  # noqa: E402

from .base import KodiTestCase  # noqa: E402

try:
    from unittest import mock
except ImportError:
    import mock


class PlainSessionTest(KodiTestCase):
    def test_http_requests_get_a_session_without_the_cache(self):
        request = http.HttpRequest('http://example.com/')
        self.assertIsInstance(request.session, asyncadapter.PlainSession)
        self.assertNotIsInstance(request.session, CachedSession)

    def test_it_mounts_the_async_adapters(self):
        session = asyncadapter.PlainSession()
        self.assertIsInstance(session.adapters['https://'], asyncadapter.AsyncHTTPAdapter)
        self.assertIsInstance(session.adapters['http://'], asyncadapter.AsyncHTTPAdapter)

    def test_a_with_cache_argument_is_dropped(self):
        session = asyncadapter.PlainSession()
        with mock.patch('requests.Session.request') as request:
            session.request('GET', 'http://example.com/', with_cache=True)
        self.assertNotIn('with_cache', request.call_args[1])


class ConnectionListTest(KodiTestCase):
    def test_the_adapter_lists_each_pool_once(self):
        adapter = asyncadapter.AsyncHTTPAdapter()
        for _ in range(3):
            adapter.get_connection('http://example.com/a')
        self.assertEqual(1, len(adapter.connections))

    def test_a_pool_forgets_connections_nothing_uses(self):
        pool = asyncadapter.AsyncHTTPConnectionPool('example.com', 80)
        conn = pool._new_conn()
        self.assertEqual(1, len(pool.connections))
        del conn
        gc.collect()
        self.assertEqual(0, len(pool.connections))


class FakeCon(object):
    def __init__(self, free_pages, page_size):
        self.answers = {'PRAGMA freelist_count': free_pages, 'PRAGMA page_size': page_size}

    def execute(self, sql):
        return mock.Mock(fetchone=mock.Mock(return_value=(self.answers[sql],)))


class VacuumTest(KodiTestCase):
    def _session(self, free_pages):
        con = FakeCon(free_pages, 4096)
        session = mock.Mock()
        session.cache.responses.connection = contextlib.contextmanager(lambda: (yield con))
        return session

    def test_a_little_free_space_is_left_for_sqlite_to_reuse(self):
        session = self._session(free_pages=10)
        asyncadapter.vacuumIfWorthIt(session)
        self.assertFalse(session.cache.vacuum.called)

    def test_lots_of_free_space_is_vacuumed(self):
        session = self._session(free_pages=asyncadapter.VACUUM_FREE_BYTES // 4096)
        asyncadapter.vacuumIfWorthIt(session)
        self.assertTrue(session.cache.vacuum.called)
