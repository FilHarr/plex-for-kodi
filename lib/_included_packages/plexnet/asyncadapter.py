from __future__ import absolute_import
import time
import selectors
import socket
import six
import os
import datetime

from kodi_six import xbmc
from requests.packages.urllib3 import HTTPConnectionPool, HTTPSConnectionPool
from requests.packages.urllib3.connection import HTTPConnection
from requests.packages.urllib3.poolmanager import PoolManager, proxy_from_url
from requests.packages.urllib3.exceptions import ConnectTimeoutError
try:
    from requests.packages.urllib3.connectionpool import VerifiedHTTPSConnection
except ImportError:
    # urllib3 >= 2.1.0
    from requests.packages.urllib3.connection import HTTPSConnection as VerifiedHTTPSConnection

import weakref
import requests
from requests.adapters import HTTPAdapter, Retry
from requests.compat import urlparse
from requests_cache import CachedSession

#from six.moves.http_client import HTTPConnection
import errno

DEFAULT_POOLBLOCK = False
SSL_KEYWORDS = ('key_file', 'cert_file', 'cert_reqs', 'ca_certs',
                'ssl_version')

DEBUG_REQUESTS = False
TEMP_PATH = None

WIN_WSAEINVAL = 10022
WIN_EWOULDBLOCK = 10035
WIN_EALREADY = 10037
WIN_ECONNRESET = 10054
WIN_EISCONN = 10056
WIN_ENOTCONN = 10057
WIN_EHOSTUNREACH = 10065

# connect_ex() answers for a non-blocking connect: already done, or under way
CONNECTED = (errno.EISCONN, WIN_EISCONN)
CONNECTING = (errno.EINPROGRESS, errno.EWOULDBLOCK, errno.EALREADY, WIN_EWOULDBLOCK, WIN_EALREADY)
# how long each wait for the connect lasts before checking for a cancel or the deadline
CONNECT_POLL = 0.05
# connect failures that are already an answer (see isDefinitiveConnectFailure())
DEFINITIVE_CONNECT_ERRNOS = frozenset((errno.ECONNREFUSED, errno.EHOSTUNREACH, errno.ENETUNREACH,
                                       10061, WIN_EHOSTUNREACH, 10051))

MAX_RETRIES = 3
# of those, how many may go to connect timeouts
CONNECT_RETRIES = 1
REQUESTS_CACHE_EXPIRY = 72


def ABORT_FLAG_FUNCTION():
    if STOP_RETRYING_REQUESTS and DEBUG_REQUESTS:
        xbmc.log('AsyncVerifiedHTTPSConnection: Abort flag set!', xbmc.LOGINFO)
    return STOP_RETRYING_REQUESTS


class CanceledException(Exception):
    pass


class AsyncTimeout(float):
    def __repr__(self):
        return '{0}({1})'.format(float(self), self.getConnectTimeout())

    def __str__(self):
        return repr(self)

    @classmethod
    def fromTimeout(cls, t):
        if isinstance(t, AsyncTimeout):
            return t

        try:
            return AsyncTimeout(float(t)) or DEFAULT_TIMEOUT
        except TypeError:
            return DEFAULT_TIMEOUT

    def setConnectTimeout(self, val):
        self._connectTimout = val
        return self

    def getConnectTimeout(self):
        if hasattr(self, '_connectTimout'):
            return self._connectTimout

        return self


DEFAULT_TIMEOUT = AsyncTimeout(5).setConnectTimeout(5)

class AsyncConnectionMixin:
    def __str__(self):
        return '{0}({1})'.format(self.__class__.__name__, self.identifier)

    def __repr__(self):
        return str(self)

    def _check_timeout(self):
        if time.time() > self.deadline:
            raise ConnectTimeoutError('connection timed out: {0}'.format(str(self)))

    def create_connection(self, address, timeout=None, source_address=None):
        """Connect to *address* and return the socket object.

        Convenience function.  Connect to *address* (a 2-tuple ``(host,
        port)``) and return the socket object.  Passing the optional
        *timeout* parameter will set the timeout on the socket instance
        before attempting to connect.  If no *timeout* is supplied, the
        global default timeout setting returned by :func:`getdefaulttimeout`
        is used.  If *source_address* is set it must be a tuple of (host, port)
        for the socket to bind as a source address before making the connection.
        An host of '' or port 0 tells the OS to use the default.
        """
        if DEBUG_REQUESTS:
            xbmc.log(
                '{3}.create_connection: {0} {1} {2}'.format(address, timeout, repr(timeout), self.__class__.__name__),
                xbmc.LOGINFO)
        timeout = AsyncTimeout.fromTimeout(timeout)
        self._timeout = timeout
        self.identifier = address

        host, port = address
        err = None
        for res in socket.getaddrinfo(host, port, 0, socket.SOCK_STREAM):
            af, socktype, proto, canonname, sa = res
            sock = None
            try:
                sock = socket.socket(af, socktype, proto)
                sock.setblocking(False)  # this is obviously critical
                self.deadline = time.time() + timeout.getConnectTimeout()
                # sock.settimeout(timeout)

                if source_address:
                    sock.bind(source_address)
                for msg in self._connect(sock, sa):
                    if self._canceled or ABORT_FLAG_FUNCTION():
                        raise CanceledException('Request canceled: {0}'.format(str(self)))
                sock.setblocking(True)
                return sock

            except socket.error as _:
                err = _
                if sock is not None:
                    #sock.shutdown(socket.SHUT_RDWR)
                    sock.close()

        if err is not None:
            raise err
        else:
            raise socket.error("getaddrinfo returns an empty list")

    def _connect(self, sock, sa):
        """Starts a non-blocking connect and waits for the OS to finish it, a slice at a time so
        cancels and the deadline are honoured. It used to poll connect_ex() instead, which can't
        tell a failed connect from one still trying (on Windows both read WSAEINVAL), so a refused
        or unreachable address always ran to the deadline - each retry again. The selector reports
        a failed connect too (on Windows through select()'s exception set, which SelectSelector
        folds into writable), and SO_ERROR says which."""
        status = sock.connect_ex(sa)
        if not status or status in CONNECTED:
            return
        if status not in CONNECTING:
            raise socket.error(status, errno.errorcode.get(status, 'connect failed'))

        selector = selectors.DefaultSelector()
        try:
            selector.register(sock, selectors.EVENT_WRITE)
            while not self._canceled and not ABORT_FLAG_FUNCTION():
                self._check_timeout()
                if selector.select(CONNECT_POLL):
                    error = sock.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
                    if error:
                        raise socket.error(error, errno.errorcode.get(error, 'connect failed'))
                    return
                yield
        finally:
            selector.close()

        if DEBUG_REQUESTS:
            xbmc.log('{1}._connect: Canceled: {0}'.format(self.identifier, self.__class__.__name__), xbmc.LOGINFO)
        raise CanceledException('Request canceled: {0}'.format(str(self)))

    def _new_conn(self):
        sock = self.create_connection(
            address=(self.host, self.port),
            timeout=self.timeout
        )

        return sock

    def cancel(self):
        self._canceled = True


class AsyncVerifiedHTTPSConnection(AsyncConnectionMixin, VerifiedHTTPSConnection):
    __slots__ = ("_canceled", "deadline", "deadline_extended", "identifier", "_timeout")

    def __init__(self, *args, **kwargs):
        super(AsyncVerifiedHTTPSConnection, self).__init__(*args, **kwargs)
        self._canceled = False
        self.deadline = 0
        self.identifier = None
        self.deadline_extended = False
        self._timeout = AsyncTimeout(DEFAULT_TIMEOUT)


class AsyncHTTPConnection(AsyncConnectionMixin, HTTPConnection):
    __slots__ = ("_canceled", "deadline", "deadline_extended", "identifier", "_timeout")

    def __init__(self, *args, **kwargs):
        super(AsyncHTTPConnection, self).__init__(*args, **kwargs)
        self._canceled = False
        self.deadline = 0
        self.identifier = None
        self.deadline_extended = False
        self._timeout = AsyncTimeout(DEFAULT_TIMEOUT)



class AsyncHTTPConnectionPool(HTTPConnectionPool):
    __slots__ = ("connections",)

    def __init__(self, *args, **kwargs):
        HTTPConnectionPool.__init__(self, *args, **kwargs)
        # Weak: every connection the pool ever made used to stay listed (L5 in the navigation review).
        self.connections = weakref.WeakSet()

    def _new_conn(self):
        """
        Return a fresh :class:`httplib.HTTPConnection`.
        """
        self.num_connections += 1

        extra_params = {}
        if six.PY2:
            extra_params['strict'] = self.strict

        conn = AsyncHTTPConnection(host=self.host, port=self.port, timeout=self.timeout.connect_timeout, **extra_params)

        # Backport fix LP #1412545
        if getattr(conn, '_tunnel_host', None):
            # TODO: Fix tunnel so it doesn't depend on self.sock state.
            conn._tunnel()
            # Mark this connection as not reusable
            conn.auto_open = 0

        self.connections.add(conn)

        return conn

    def cancel(self):
        for c in list(self.connections):
            c.cancel()


class AsyncHTTPSConnectionPool(HTTPSConnectionPool):
    __slots__ = ("connections",)

    def __init__(self, *args, **kwargs):
        HTTPSConnectionPool.__init__(self, *args, **kwargs)
        # Weak, as in AsyncHTTPConnectionPool.
        self.connections = weakref.WeakSet()

    def _new_conn(self):
        """
        Return a fresh :class:`httplib.HTTPSConnection`.
        """
        self.num_connections += 1

        actual_host = self.host
        actual_port = self.port
        if self.proxy is not None:
            actual_host = self.proxy.host
            actual_port = self.proxy.port

        connection_class = AsyncVerifiedHTTPSConnection

        extra_params = {}
        if six.PY2:
            extra_params['strict'] = self.strict
        connection = connection_class(host=actual_host, port=actual_port, timeout=self.timeout.connect_timeout, **extra_params)

        self.connections.add(connection)

        try:
            return self._prepare_conn(connection)
        except AttributeError:
            # urllib3 2.1.0
            return connection

    def cancel(self):
        for c in list(self.connections):
            c.cancel()


pool_classes_by_scheme = {
    'http': AsyncHTTPConnectionPool,
    'https': AsyncHTTPSConnectionPool,
}


class AsyncPoolManager(PoolManager):
    def _new_pool(self, scheme, host, port, request_context=None):
        """
        Create a new :class:`ConnectionPool` based on host, port and scheme.

        This method is used to actually create the connection pools handed out
        by :meth:`connection_from_url` and companion methods. It is intended
        to be overridden for customization.
        """
        pool_cls = pool_classes_by_scheme[scheme]
        kwargs = self.connection_pool_kw
        if scheme == 'http':
            kwargs = self.connection_pool_kw.copy()
            for kw in SSL_KEYWORDS:
                kwargs.pop(kw, None)

        return pool_cls(host, port, **kwargs)


class AsyncHTTPAdapter(HTTPAdapter):
    def cancel(self):
        for c in self.connections:
            try:
                c.cancel()
            except:
                pass

    def init_poolmanager(self, connections, maxsize, block=DEFAULT_POOLBLOCK):
        """Initializes a urllib3 PoolManager. This method should not be called
        from user code, and is only exposed for use when subclassing the
        :class:`HTTPAdapter <requests.adapters.HTTPAdapter>`.

        :param connections: The number of urllib3 connection pools to cache.
        :param maxsize: The maximum number of connections to save in the pool.
        :param block: Block when no free connections are available.
        """
        # save these values for pickling
        self._pool_connections = connections
        self._pool_maxsize = maxsize
        self._pool_block = block

        self.poolmanager = AsyncPoolManager(num_pools=connections, maxsize=maxsize, block=block)
        self.connections = []

    def get_connection(self, url, proxies=None):
        """Returns a urllib3 connection for the given URL. This should not be
        called from user code, and is only exposed for use when subclassing the
        :class:`HTTPAdapter <requests.adapters.HTTPAdapter>`.

        :param url: The URL to connect to.
        :param proxies: (optional) A Requests-style dictionary of proxies used on this request.
        """
        proxies = proxies or {}
        proxy = proxies.get(urlparse(url.lower()).scheme)

        if proxy:
            proxy_headers = self.proxy_headers(proxy)

            if proxy not in self.proxy_manager:
                self.proxy_manager[proxy] = proxy_from_url(
                    proxy,
                    proxy_headers=proxy_headers,
                    num_pools=self._pool_connections,
                    maxsize=self._pool_maxsize,
                    block=self._pool_block
                )

            conn = self.proxy_manager[proxy].connection_from_url(url)
        else:
            # Only scheme should be lower case
            parsed = urlparse(url)
            url = parsed.geturl()
            conn = self.poolmanager.connection_from_url(url)

        # Once each: this ran per request and never removed anything, so the long-lived server
        # session's list grew by one (mostly the same pool) per request (L5).
        if conn not in self.connections:
            self.connections.append(conn)
        return conn

STOP_RETRYING_REQUESTS = False


def connectFailureCause(error):
    """The socket error behind a failed request when it was a definite no - refused (nothing
    listening), no route to the host or network, or no such name (a socket.gaierror) - else None.
    urllib3 and requests wrap it (a refused connect arrives as ProtocolError("Connection aborted.",
    ConnectionRefusedError)), so this follows the wrapping down."""
    pending = [error]
    seen = set()
    while pending:
        err = pending.pop()
        if err is None or id(err) in seen or len(seen) > 12:
            continue
        seen.add(id(err))
        if isinstance(err, socket.gaierror):
            return err
        if isinstance(err, OSError) and getattr(err, 'errno', None) in DEFINITIVE_CONNECT_ERRNOS:
            return err
        pending.extend(a for a in getattr(err, 'args', ()) if isinstance(a, BaseException))
        pending.extend((getattr(err, 'reason', None), getattr(err, 'original_error', None),
                        err.__cause__, err.__context__))
    return None


def isDefinitiveConnectFailure(error):
    """Whether a failed request already got a definite no (see connectFailureCause()). Asking
    again gets the same answer, so it isn't retried. A connect timeout (a lost packet, say) or a
    connection dropped mid-answer still is."""
    return connectFailureCause(error) is not None


class StoppableRetry(Retry):
    """Retries that give up at once when retrying is switched off (STOP_RETRYING_REQUESTS, while
    a screen closes) or the failure is already a definite answer. It never changes itself: the
    adapter hands this same object to every request through it, so setting total = 0 here (as it
    once did) took the retries away from the whole session for good."""
    def increment(self, method=None, url=None, response=None, error=None, _pool=None, _stacktrace=None):
        if STOP_RETRYING_REQUESTS or (error is not None and isDefinitiveConnectFailure(error)):
            return Retry.increment(self.new(total=0), method, url, response, error, _pool, _stacktrace)
        return super(StoppableRetry, self).increment(method, url, response, error, _pool, _stacktrace)


class AsyncSessionMixin(object):
    def mountAsyncAdapters(self, retries=None):
        """retries: None for the user's max_retries setting, of which at most CONNECT_RETRIES go
        to connect timeouts (a server that never answers would otherwise hold the caller for
        every attempt); a number to override both."""
        if retries is None:
            make = lambda: StoppableRetry(total=MAX_RETRIES, connect=min(CONNECT_RETRIES, MAX_RETRIES))
        else:
            make = lambda: StoppableRetry(total=retries, connect=retries)
        self.mount('https://', AsyncHTTPAdapter(max_retries=make()))
        self.mount('http://', AsyncHTTPAdapter(max_retries=make()))

    def cancel(self):
        for v in self.adapters.values():
            v.close()
            v.cancel()


class PlainSession(AsyncSessionMixin, requests.Session):
    """A session without the request cache, for http.HttpRequest's one-off requests, which never
    use it: a cached session opens the SQLite cache and creates its three tables each time one is
    built, once per request (E8 in the navigation review)."""
    def __init__(self, retries=None):
        requests.Session.__init__(self)
        self.mountAsyncAdapters(retries)

    def request(self, method, url, *args, **kwargs):
        kwargs.pop('with_cache', None)
        if DEBUG_REQUESTS:
            xbmc.log("PlainSession.request: %s %s" % (method, url), xbmc.LOGINFO)
        return requests.Session.request(self, method, url, *args, **kwargs)


# Free space in the cache database worth a VACUUM, which rewrites the whole file.
VACUUM_FREE_BYTES = 8 * 1024 * 1024


def vacuumIfWorthIt(session):
    """Deleting cached responses leaves free pages that SQLite reuses, so the file doesn't grow
    for want of a VACUUM. One ran after every cache invalidation (a watched toggle, say) and
    rewrote the whole file each time (L4 in the navigation review); now only once this much of it
    is free."""
    with session.cache.responses.connection() as con:
        free = con.execute("PRAGMA freelist_count").fetchone()[0] * con.execute("PRAGMA page_size").fetchone()[0]
    if free >= VACUUM_FREE_BYTES:
        session.cache.vacuum()


class Session(AsyncSessionMixin, CachedSession):
    def __init__(self, *args, **kwargs):
        kwargs['cache_name'] = os.path.join(TEMP_PATH, "pm4k_requests_cache")
        kwargs['backend'] = "sqlite"
        kwargs['fast_save'] = True
        if REQUESTS_CACHE_EXPIRY:
            kwargs['expire_after'] = datetime.timedelta(hours=REQUESTS_CACHE_EXPIRY)
        CachedSession.__init__(self, *args, **kwargs)
        self.mountAsyncAdapters()

    def request(self, method, url, *args, **kwargs):
        self._is_cache_disabled = not kwargs.pop('with_cache', False)
        if DEBUG_REQUESTS:
            xbmc.log("Session.request: (cache enabled: %s) %s %s" % (not self._is_cache_disabled, method, url), xbmc.LOGINFO)
        return CachedSession.request(self, method, url, *args, **kwargs)
