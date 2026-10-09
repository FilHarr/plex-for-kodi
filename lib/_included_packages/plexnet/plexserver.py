# -*- coding: utf-8 -*-
from __future__ import absolute_import

import time
import re
import json
import math
import threading
from email.utils import parsedate_tz, mktime_tz

import six
import urllib3.exceptions

from . import http
from . import util
from . import exceptions
from . import compat

from xml.etree import ElementTree
from . import signalsmixin
from . import plexobjects
from . import plexresource
from . import plexlibrary
from . import asyncadapter
from . import callback
from six.moves import range
from six.moves.urllib.parse import urlsplit, parse_qs

# from plexapi.client import Client
# from plexapi.playqueue import PlayQueue


TOTAL_QUERIES = 0

# statuses a reverse proxy gives when the server behind it doesn't answer
GATEWAY_ERRORS = (502, 503, 504)
# at most one retest per this many seconds per server for queries that got no answer (markSuspect())
SUSPECT_RETEST_SECONDS = 30

# what query() treats as "no answer" (not programming errors such as an invalid URL)
TRANSPORT_ERRORS = (http.requests.exceptions.ConnectionError, http.requests.exceptions.Timeout,
                    http.requests.exceptions.ChunkedEncodingError,
                    http.requests.exceptions.ContentDecodingError, urllib3.exceptions.ProtocolError)
DEFAULT_BASEURI = 'http://localhost:32400'

CACHE_MAP = {}


# A rate-limiting server's 429 (RATE_LIMIT_COOLDOWN): until when it isn't asked again, by
# (scheme, host, token) - every Discover object shares its limit, another user doesn't. Asking
# while it's refusing only prolongs it (live 2026-10-05: plex.tv's Discover answered 429 for over
# half an hour while the sidebar, rows and item checks kept asking). From pannal 4f9b12d1.
_RATE_LIMIT_UNTIL = {}
_RATE_LIMIT_LOCK = threading.Lock()
_cooldownTime = getattr(time, 'monotonic', time.time)


def retryAfterSeconds(value, default=60):
    """A Retry-After header's wait: seconds, or an HTTP date; default when it's missing or bad."""
    try:
        value = value.strip()
        if re.match(r'^[0-9]+$', value):
            return max(0, int(value))
        date = parsedate_tz(value)
        if date is not None:
            return max(0, int(math.ceil(mktime_tz(date) - time.time())))
    except (AttributeError, TypeError, ValueError, OverflowError):
        pass
    return default


class PlexServer(plexresource.PlexResource, signalsmixin.SignalsMixin):
    TYPE = 'PLEXSERVER'
    # a 429 starts a cooldown (_RATE_LIMIT_UNTIL): the Discover server's
    RATE_LIMIT_COOLDOWN = False
    DEFER_HUBS = False

    def __init__(self, data=None):
        signalsmixin.SignalsMixin.__init__(self)
        plexresource.PlexResource.__init__(self, data)
        self.accessToken = None
        self.multiuser = False
        self.isSupported = None
        self.hasFallback = False
        self.supportsAudioTranscoding = False
        self.supportsVideoTranscoding = False
        self.supportsPhotoTranscoding = False
        self.supportsVideoRemuxOnly = False
        self.supportsScrobble = True
        self.allowsMediaDeletion = False
        self.allowChannelAccess = False
        self.activeConnection = None
        self.serverClass = None

        self.pendingReachabilityRequests = 0
        self.pendingSecureRequests = 0
        self._reachabilityLock = threading.RLock()
        # Known to be unreachable: its last reachability round ended with no working connection
        # (PlexServerManager.setServerOnline())
        self.offline = False
        # No longer on the account - plex.tv stopped listing it (PlexServerManager.onServerGone())
        self.gone = False
        # A query got no answer and its connections are being retested (markSuspect()); cleared by
        # the retest's verdict (PlexServerManager.setServerOnline())
        self.suspect = False
        self._lastSuspectRetest = 0

        self.features = {}
        self.librariesByUuid = {}

        self.server = self
        self.session = http.Session()

        self.owner = None
        self.owned = False
        self.synced = False
        self.sameNetwork = False
        self.uuid = None
        self.name = None
        self.platform = None
        self.versionNorm = None
        self.rawVersion = None
        self.transcodeSupport = False
        self.currentHubs = None
        self.dnsRebindingProtection = False

        if data is None:
            return

        # or None: /api/v2/resources gives your own servers an empty sourceTitle where the older
        # endpoint left it out, and owner takes part in __eq__
        self.owner = data.attrib.get('sourceTitle') or None
        self.owned = data.attrib.get('owned') == '1'
        self.synced = data.attrib.get('synced') == '1'
        self.sameNetwork = data.attrib.get('publicAddressMatches') == '1'
        self.uuid = data.attrib.get('clientIdentifier')
        self.name = data.attrib.get('name')
        self.platform = data.attrib.get('platform')
        self.rawVersion = data.attrib.get('productVersion')
        if self.rawVersion and "server" in data.attrib.get('provides', 'server'):
            self.versionNorm = util.normalizedVersion(self.rawVersion)
        self.transcodeSupport = data.attrib.get('transcodeSupport') == '1'
        self.dnsRebindingProtection = data.attrib.get('dnsRebindingProtection') == '1'

    def __eq__(self, other):
        if not other:
            return False
        if self.__class__ != other.__class__:

            return False
        return self.uuid == other.uuid and self.owner == other.owner

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        return "<PlexServer {0} owned: {1} uuid: {2} version: {3} connection: {4}>"\
            .format(repr(self.name), self.owned, self.uuid, self.versionNorm, self.activeConnection)

    def __repr__(self):
        return self.__str__()

    def close(self):
        self.session.cancel()

    def dropIdleConnections(self):
        """Closes the connections kept open for reuse (the session's pools), so the next requests
        open new ones. After the system sleeps, those sockets are dead but still pooled, and a
        request that picks one up waits out the timeout: live on the AM6B (2026-10-09), Home's
        refresh after wake hung 5 s on both servers and marked them suspect, while the wake's
        connection tests - new connections - answered in milliseconds. A connection in use isn't in
        a pool, so a request under way is left alone."""
        for adapter in list(self.session.adapters.values()):
            try:
                adapter.close()
                connections = getattr(adapter, 'connections', None)
                if connections is not None:
                    del connections[:]
            except Exception:
                util.ERROR()

    def get(self, attr, default=None):
        return default

    @property
    def isSecure(self):
        if self.activeConnection:
            return self.activeConnection.isSecure

    @property
    def isLocal(self):
        if self.activeConnection:
            return self.activeConnection.isLocal

    @property
    def anyLANConnection(self):
        return any(c.localVerified for c in self.connections)

    @property
    def anyPDHostNotResolvable(self):
        return any(".plex.direct:" in c.address and not c.pdHostnameResolved for c in self.connections)

    def getObject(self, key, assume_container=False):
        data = self.query(key)

        container = self
        if not assume_container:
            container = plexobjects.PlexContainer(data, initpath=key, server=self, address=key)
        return plexobjects.buildItem(self, data[0], key, container=container)

    def getPrefs(self):
        return plexobjects.listItems(self, "/:/prefs", bytag=True, cachable=False, not_cachable=True)

    def hubs(self, section=None, count=None, search_query=None, section_ids=None):
        hubs = []

        params = {"includeMarkers": 1}
        if search_query:
            q = '/hubs/search'
            params['query'] = search_query.lower()
            if section:
                # what limits a search to one library: PMS ignores sectionId here, and
                # librarySectionID and pinnedContentDirectoryID too (checked live, PMS 1.43.4)
                params['contentDirectoryID'] = section

            if count is not None:
                params['limit'] = count
        else:
            q = '/hubs'
            if section:
                if section == 'playlists':
                    audio = plexlibrary.AudioPlaylistHub(False, server=self.server)
                    video = plexlibrary.VideoPlaylistHub(False, server=self.server)
                    if audio.items:
                        hubs.append(audio)
                    if video.items:
                        hubs.append(video)
                    return hubs
                else:
                    q = '/hubs/sections/%s' % section
                    # a library's own playlists row ("Library Playlists") only comes when asked for,
                    # as Plex Web does (checked live 2026-10-05, PMS 1.43.4)
                    params['includeLibraryPlaylists'] = 1
            else:
                # Home's rows as Plex's own apps ask for them (checked live 2026-10-05, PMS 1.43.3
                # and 1.43.4): only the rows Plex has on Home for this user - its Manage
                # Recommendations toggles, "shared Home" ones for a shared or managed user - with
                # its "merge recently added" setting applied, from these libraries, in their
                # order (and 'playlists' for the recent playlists row, where it is in the list).
                # The merged rows follow pinnedContentDirectoryID, every other row
                # contentDirectoryID (with merging off the pinned one doesn't limit a library's
                # rows), so both.
                q = '/hubs/promoted'
                if section_ids:
                    params['contentDirectoryID'] = ",".join(section_ids)
                    params['pinnedContentDirectoryID'] = ",".join(k for k in section_ids if k != 'playlists')

            if count is not None:
                params['count'] = count

        data = self.query(q, params=params)
        container = plexobjects.PlexContainer(data, initpath=q, server=self, address=q)

        self.currentHubs = {} if self.currentHubs is None else self.currentHubs

        # Home always gets the combined Continue Watching hub (/hubs/continueWatching, what the
        # modern Plex clients show) in place of the server's old separate home.continue/home.ondeck
        # pair, which are dropped below. Used to be the hubs_use_new_continue_watching preference;
        # the old pair was removed outright (2026-09-21), the preference with it.
        newCW = not search_query and not section

        if newCW:
            cq = '/hubs/continueWatching'
            cparams = dict((k, v) for k, v in params.items() if k != 'pinnedContentDirectoryID')
            if section_ids:
                cq += util.joinArgs(cparams)

            cdata = self.query(cq, params=cparams)
            if cdata and len(cdata) > 0:
                ccontainer = plexobjects.PlexContainer(cdata, initpath=cq, server=self, address=cq)
                self.currentHubs[cdata[0].attrib.get('hubIdentifier')] = cdata[0].attrib.get('title')
                hubs.append(plexlibrary.Hub(cdata[0], server=self, container=ccontainer))

        if data:
            for elem in data:
                hubIdent = elem.attrib.get('hubIdentifier')
                self.currentHubs["{}:{}".format(section, hubIdent)] = elem.attrib.get('title')

                # Skip the old-style continue/ondeck hubs - the combined continueWatching hub
                # above replaces them
                if newCW and hubIdent and (hubIdent.startswith('home.continue') or hubIdent.startswith('home.ondeck')):
                    continue

                hubs.append(plexlibrary.Hub(elem, server=self, container=container))

        if section_ids:
            # the same libraries for each row's later pages ("See more"); a merged row's key
            # carries its pinned libraries already
            paging = dict((k, v) for k, v in params.items() if k != 'pinnedContentDirectoryID')
            for hub in hubs:
                if "contentDirectoryID" not in hub.key:
                    hub.key += util.joinArgs(paging, '?' not in hub.key)

        return hubs

    def playlists(self, start=0, size=10, hub=None):
        try:
            return plexobjects.listItems(self, '/playlists/all')
        except exceptions.BadRequest:
            return None

    @property
    def library(self):
        if self.platform == 'cloudsync':
            return plexlibrary.Library(None, server=self)
        else:
            return plexlibrary.Library(self.query('/library/'), server=self)

    @property
    def sessions(self):
        if self.owned:
            return plexobjects.listItems(self, '/status/sessions')
        raise exceptions.ServerNotOwned

    def findVideoSession(self, session_id, rating_key):
        for item in self.sessions:
            if item.session and item.session.id == session_id and item.ratingKey == rating_key:
                return item

    def buildUrl(self, path, includeToken=False):
        if self.activeConnection:
            return self.activeConnection.buildUrl(self, path, includeToken)
        else:
            util.WARN_LOG("Server connection is None, returning an empty url")
            return ""

    def query(self, path, method=None, raw=False, **kwargs):
        if method and isinstance(method, six.string_types):
            method = getattr(self.session, method)
        else:
            method = method or self.session.get

        limit = kwargs.pop("limit", None)
        params = kwargs.pop("params", None)
        cachable = kwargs.pop("cachable", False)
        cache_ref = kwargs.pop("cache_ref", None)
        if params:
            if limit is None:
                limit = params.get("limit", None)
            path += util.joinArgs(params, '?' not in path)

        offset = kwargs.pop("offset", None)
        if kwargs:
            path += util.joinArgs(kwargs, '?' not in path)
            kwargs.clear()

        url = self.buildUrl(path, includeToken=True)

        if self.suspect:
            # A query has just gone unanswered and the connections are being retested
            # (markSuspect()): fail at once rather than have every query wait out a timeout of its
            # own meanwhile. The retest decides - and if the server answers after all,
            # 'recovered:server' gets a view this left empty loaded again.
            util.WARN_LOG("{0} is being retested, returning None", repr(self.name))
            return None

        # No active connection: the server is already known to be unreachable. This used to start a
        # forced plex.tv resource refresh as well, once per query, which turned every query against
        # an unreachable server into a refresh storm (mvanbaak/plex-for-kodi ee7c68f5).
        if not url:
            util.WARN_LOG("No connection to {0}, returning None", repr(self.name))
            self.markSuspect()
            return None

        cooldownKey = None
        if self.RATE_LIMIT_COOLDOWN:
            parsed = urlsplit(url)
            cooldownKey = (parsed.scheme, parsed.netloc, parse_qs(parsed.query).get('X-Plex-Token', [None])[0])
            with _RATE_LIMIT_LOCK:
                remaining = _RATE_LIMIT_UNTIL.get(cooldownKey, 0) - _cooldownTime()
                if remaining > 0:
                    raise exceptions.RateLimited(int(math.ceil(remaining)), from_cooldown=True)
                _RATE_LIMIT_UNTIL.pop(cooldownKey, None)

        # add offset/limit
        offset = offset or 0

        if limit is not None:
            url = http.addUrlParam(url, "X-Plex-Container-Start=%s" % offset)
            url = http.addUrlParam(url, "X-Plex-Container-Size=%s" % limit)

        with_cache = False
        if cachable and cache_ref:
            kwargs['with_cache'] = with_cache = True

        util.LOG('{0} (cache enabled: {2}) {1}', method.__name__.upper(), re.sub('X-Plex-Token=[^&]+', 'X-Plex-Token=****', url), with_cache)
        try:
            response = method(url, **kwargs)
            if response.status_code == 429 and cooldownKey is not None:
                delay = retryAfterSeconds(response.headers.get('Retry-After'))
                with _RATE_LIMIT_LOCK:
                    _RATE_LIMIT_UNTIL[cooldownKey] = max(_cooldownTime() + delay, _RATE_LIMIT_UNTIL.get(cooldownKey, 0))
                util.WARN_LOG('{0} is limiting requests: not asked again for {1} s', self.name, delay)
                raise exceptions.RateLimited(delay)
            if response.status_code not in (200, 201):
                if response.status_code in GATEWAY_ERRORS:
                    # a proxy in front of the server answering for it: the server itself may be down
                    self.markSuspect()
                codename = http.status_codes.get(response.status_code, ['Unknown'])[0]
                raise exceptions.BadRequest('({0}) {1}'.format(response.status_code, codename))

            # caching
            if hasattr(response, "from_cache") and with_cache:
                if util.DEBUG_REQUESTS:
                    util.LOG('{0} (from cache: {2}) {1}', method.__name__.upper(),
                             re.sub('X-Plex-Token=[^&]+', 'X-Plex-Token=****', url), response.from_cache)

                # scope for server+user; URLs itself don't need to be scoped as they differ on X-Plex-Token and domain
                base_key = util.INTERFACE.getRCBaseKey()

                if base_key not in util.CACHED_PLEX_URLS:
                    util.CACHED_PLEX_URLS[base_key] = {}

                base = util.CACHED_PLEX_URLS[base_key]

                if cache_ref not in base:
                    base[cache_ref] = []

                # fixme: this could be faster with a dict
                if url not in base[cache_ref]:
                    base[cache_ref].append(url)
                    if util.DEBUG_REQUESTS:
                        util.DEBUG_LOG('Storing URL for cached response in {0}: {1}: {2}'.format(base_key, cache_ref, url))

            data = response.text.encode('utf8')
        except asyncadapter.CanceledException:
            return None
        except TRANSPORT_ERRORS as e:
            # Every way of not getting an answer ends the same: None. A read timeout used to raise
            # instead, while a connect failure returned None.
            util.WARN_LOG("Query failed ({0}): {1}", http.describeFailure(e),
                          re.sub('X-Plex-Token=[^&]+', 'X-Plex-Token=****', url))
            self.markSuspect()
            return None

        if raw:
            return data
        return ElementTree.fromstring(data) if data else None

    def getImageTranscodeURL(self, path, width, height, **extraOpts):
        if not path:
            return ''

        eOpts = {"minSize": 1, "upscale": 1}
        eOpts.update(extraOpts)

        params = ("&width=%s&height=%s" % (width, height)) + ''.join(["&%s=%s" % (key, eOpts[key]) for key in eOpts])

        if "://" in path:
            imageUrl = self.convertUrlToLoopBack(path)
        else:
            imageUrl = "http://127.0.0.1:" + self.getLocalServerPort() + path

        path = "/photo/:/transcode?url=" + compat.quote_plus(imageUrl) + params

        # Try to use a better server to transcode for synced servers
        if self.synced:
            from . import plexservermanager
            transcodeServer = plexservermanager.MANAGER.getTranscodeServer("photo")
            if transcodeServer:
                return transcodeServer.buildUrl(path, True)

        if self.activeConnection:
            return self.activeConnection.simpleBuildUrl(self, path)
        else:
            util.WARN_LOG("Server connection is None, returning an empty url")
            return ""

    def isReachable(self, onlySupported=True):
        if onlySupported and not self.isSupported:
            return False

        return self.activeConnection and self.activeConnection.state == plexresource.ResourceConnection.STATE_REACHABLE

    def isLocalConnection(self):
        return self.activeConnection and (self.sameNetwork or self.activeConnection.isLocal)

    def isRequestToServer(self, url):
        if not self.activeConnection:
            return False

        if ':' in self.activeConnection.address[8:]:
            schemeAndHost = self.activeConnection.address.rsplit(':', 1)[0]
        else:
            schemeAndHost = self.activeConnection.address

        return url.startswith(schemeAndHost)

    def hasLocalModeConnection(self):
        # whether this server is usable in local mode: only plain LAN connections count,
        # plex.direct hostnames need public DNS
        for i in range(len(self.connections)):
            try:
                conn = self.connections[i]
            except IndexError:
                continue
            if conn.isLocal and ".plex.direct" not in conn.address:
                return True
        return False

    def getToken(self):
        # local mode: per-user identity comes from the harvested per-server access token
        # (the PMS validates those against its own DB; its transcoder rejects plex.tv
        # account tokens of managed users), falling back to the account token; the stored
        # connection tokens belong to whoever last fetched the plex.tv resources
        if util.LOCAL_MODE and util.ACCOUNT:
            token = (util.ACCOUNT.serverTokens or {}).get(self.uuid)
            if token:
                return token
            if util.ACCOUNT.authToken:
                return util.ACCOUNT.authToken

        # It's dangerous to use for each here, because it may reset the index
        # on self.connections when something else was in the middle of an iteration.

        for i in range(len(self.connections)):
            try:
                conn = self.connections[i]
            except IndexError:
                continue
            if conn.token:
                return conn.token

        return None

    def getLocalServerPort(self):
        # TODO(schuyler): The correct thing to do here is to iterate over local
        # connections and pull out the port. For now, we're always returning 32400.

        return '32400'

    def collectDataFromRoot(self, data):
        # Make sure we're processing data for our server, and not some other
        # server that happened to be at the same IP.
        if self.uuid != data.attrib.get('machineIdentifier'):
            util.LOG("Got a reachability response, but from a different server")
            return False

        self.serverClass = data.attrib.get('serverClass')
        self.supportsAudioTranscoding = data.attrib.get('transcoderAudio') == '1'
        self.supportsVideoTranscoding = data.attrib.get('transcoderVideo') == '1' or data.attrib.get('transcoderVideoQualities')
        self.supportsVideoRemuxOnly = data.attrib.get('transcoderVideoRemuxOnly') == '1'
        self.supportsPhotoTranscoding = data.attrib.get('transcoderPhoto') == '1' or (
            not data.attrib.get('transcoderPhoto') and not self.synced and not self.isSecondary()
        )
        self.allowChannelAccess = data.attrib.get('allowChannelAccess') == '1' or (
            not data.attrib.get('allowChannelAccess') and self.owned and not self.synced and not self.isSecondary()
        )
        self.supportsScrobble = not self.isSecondary() or self.synced
        self.allowsMediaDeletion = not self.synced and self.owned and data.attrib.get('allowMediaDeletion') == '1'
        self.multiuser = data.attrib.get('multiuser') == '1'
        self.name = data.attrib.get('friendlyName') or self.name
        self.platform = data.attrib.get('platform')

        # TODO(schuyler): Process transcoder qualities

        self.rawVersion = data.attrib.get('version')
        if self.rawVersion:
            self.versionNorm = util.normalizedVersion(self.rawVersion)

        features = {
            'mkvTranscode': '0.9.11.11',
            'themeTranscode': '0.9.14.0',
            'allPartsStreamSelection': '0.9.12.5',
            'claimServer': '0.9.14.2',
            'streamingBrain': '1.2.0'
        }

        for f, v in features.items():
            if util.normalizedVersion(v) <= self.versionNorm:
                self.features[f] = True

        appMinVer = util.INTERFACE.getGlobal('minServerVersionArr', '0.0.0.0')
        self.isSupported = self.isSecondary() or util.normalizedVersion(appMinVer) <= self.versionNorm

        util.DEBUG_LOG("Server information updated from reachability check: {0}", self)

        return True

    def updateReachability(self, force=True, allowFallback=False):
        if not force and self.activeConnection and self.activeConnection.state != plexresource.ResourceConnection.STATE_UNKNOWN:
            return

        util.LOG('Updating reachability for {0}: conns={1}, allowFallback={2}', repr(self.name), len(self.connections), allowFallback)

        epoch = time.time()
        retrySeconds = 60
        minSeconds = 10
        for i in range(len(self.connections)):
            conn = self.connections[i]
            if conn.hasPendingRequest and not self.settleStaleTest(conn, epoch):
                util.DEBUG_LOG("Skip reachability test for {0} (has pending request)", conn)
                continue
            diff = epoch - (conn.lastTestedAt or 0)
            if (diff < minSeconds or (not self.isSecondary() and self.isReachable() and diff < retrySeconds)) and \
                    not conn.state == "unauthorized":
                util.DEBUG_LOG("Skip reachability test for {0} (checked {1} secs ago)", conn, diff)
            else:
                conn.testReachability(self, allowFallback)

        if self.pendingReachabilityRequests <= 0:
            if util.LOCAL_MODE and self.hasFallback and not allowFallback:
                # Nothing secure was tested: local mode never tests a plex.direct connection
                # (PlexConnection.testReachability()), and a server whose only secure connections
                # are plex.direct - Oscar, the dev PC - is left with its plain LAN address, the
                # insecure fallback. That round starts when the secure tests finish
                # (onReachabilityResult()), and with none started none ever finished: the server
                # sat offline in local mode (AM6B, 2026-10-09). Start it now.
                self.updateReachability(force, True)
                return
            self.trigger("completed:reachability")

    def markSuspect(self):
        """A query to this server got no answer: retest its connections now rather than whenever
        something next happens to, so a server that went down shows as offline (and one that came
        back as online) - at most every SUSPECT_RETEST_SECONDS. Nothing else noticed a server dying
        mid-session; queries against it just kept failing."""
        now = time.time()
        if now - self._lastSuspectRetest < SUSPECT_RETEST_SECONDS:
            return
        self._lastSuspectRetest = now
        util.LOG("A query to {0} got no answer, retesting its connections", repr(self.name))
        from . import plexservermanager
        plexservermanager.MANAGER.onServerSuspect(self)
        self.resetLastTest()
        self.updateReachability(True)
        if self.pendingReachabilityRequests <= 0:
            # nothing to test (no connections): no round will end with a verdict, so give it now
            plexservermanager.MANAGER.updateReachabilityResult(self, bool(self.activeConnection))

    def checkAlive(self):
        """A light check that the server still answers, between full reachability rounds: one
        request on the connection in use, for /identity - the smallest thing it serves, no token
        needed. Only a failure costs more: it retests every connection (markSuspect()), which puts the
        server offline if none answers. A gateway error counts as a failure - a reverse proxy in front
        of the server keeps accepting connections while the server behind it is down. Skipped while
        the server is offline, gone, suspect or already being tested: those have their own retests.
        Returns whether a check was started."""
        conn = self.activeConnection
        if conn is None or self.offline or self.gone or self.suspect or self.pendingReachabilityRequests > 0:
            return False
        request = http.HttpRequest(conn.buildUrl(self, "/identity"), retries=0)
        context = request.createRequestContext("alive", callback.Callable(self.onAliveResponse),
                                               timeout=util.CONN_CHECK_TIMEOUT)
        context.server = self
        util.addPlexHeaders(request, self.getToken())
        util.APP.startRequest(request, context)
        return True

    def onAliveResponse(self, request, response, context):
        if getattr(context, "canceled", False) or response.isSuccess():
            return
        util.LOG("{0} didn't answer a check ({1})", repr(self.name), response.getStatus())
        self.markSuspect()

    def onReachabilityTestStarting(self, connection):
        """Counts a test in before it can possibly answer - PlexConnection.testReachability() calls
        this ahead of starting the request. Counting after it had started let a quick answer count
        down first (going negative, completing the round early) and then be marked pending again,
        for good."""
        with self._reachabilityLock:
            connection.hasPendingRequest = True
            connection.pendingSince = time.time()
            self.pendingReachabilityRequests += 1
            if connection.isSecure:
                self.pendingSecureRequests += 1
            first = self.pendingReachabilityRequests == 1

        if first:
            self.trigger("started:reachability")

    def settleStaleTest(self, conn, now):
        """A test still pending long after it could possibly have finished lost its answer
        somewhere: count it as unreachable rather than skip the connection for the rest of the
        session. Returns whether it did."""
        since = getattr(conn, 'pendingSince', None)
        if not since or now - since < staleTestSeconds():
            return False
        if conn.request is not None and not conn.request.cancel():
            return False  # its answer is being delivered right now

        util.WARN_LOG("Reachability test for {0} lost its answer ({1:.0f}s), counting it as unreachable",
                      conn.address, now - since)
        conn.state = conn.STATE_UNREACHABLE
        conn.getScore(True)
        self.onReachabilityResult(conn)
        return True

    def cancelReachability(self):
        canceled = False
        with self._reachabilityLock:
            for i in range(len(self.connections)):
                conn = self.connections[i]
                if conn.cancelReachability():
                    canceled = True
                    self.pendingReachabilityRequests -= 1
                    if conn.isSecure:
                        self.pendingSecureRequests -= 1
            settled = canceled and self.pendingReachabilityRequests <= 0

        if settled:
            self.trigger("completed:reachability")

    def onReachabilityResult(self, connection):
        # Results arrive on one HTTP thread per connection, often several at once: the counts and
        # the pick of the active connection are made under the lock, the signals after it.
        with self._reachabilityLock:
            connection.lastTestedAt = time.time()
            connection.hasPendingRequest = None
            connection.pendingSince = None
            self.pendingReachabilityRequests -= 1
            if connection.isSecure:
                self.pendingSecureRequests -= 1

            util.DEBUG_LOG("Reachability result for {0}: {1} is {2}", repr(self.name), connection.address, connection.state)

            # Noneate active connection if the state is unreachable
            if self.activeConnection and self.activeConnection.state != plexresource.ResourceConnection.STATE_REACHABLE:
                self.activeConnection = None

            # Pick a best connection. If we already had an active connection and
            # it's still reachable, stick with it. (replace with local if
            # available)
            best = self.activeConnection
            for i in range(len(self.connections) - 1, -1, -1):
                try:
                    conn = self.connections[i]
                except IndexError:
                    continue

                util.DEBUG_LOG("Connection score: {0}, {1}", conn.address, lambda: conn.getScore(True))

                if not best or conn.getScore() > best.getScore():
                    best = conn

            if best and best.state == best.STATE_REACHABLE:
                if (best.isSecure or util.LOCAL_OVER_SECURE) or self.pendingSecureRequests <= 0:
                    util.DEBUG_LOG("Using connection for {0} for now: {1}", repr(self.name), best.address)
                    self.activeConnection = best
                else:
                    util.DEBUG_LOG("Found a good connection for {0}, but holding out for better", repr(self.name))

            settled = self.pendingReachabilityRequests <= 0

        if settled:
            # Retest the server with fallback enabled. hasFallback will only
            # be True if there are available insecure connections and fallback
            # is allowed.

            if self.hasFallback:
                self.updateReachability(False, True)
            else:
                self.trigger("completed:reachability")

        util.LOG("Active connection for {0} is {1}", repr(self.name), self.activeConnection)

        from . import plexservermanager
        plexservermanager.MANAGER.updateReachabilityResult(self, bool(self.activeConnection))

    def markAsRefreshing(self):
        for i in range(len(self.connections)):
            conn = self.connections[i]
            conn.refreshed = False

    def markUpdateFinished(self, source):
        # Any connections for the given source which haven't been refreshed should
        # be removed. Since removing from a list is hard, we'll make a new list.
        toKeep = []
        hasSecureConn = False

        for i in range(len(self.connections)):
            try:
                conn = self.connections[i]
            except IndexError:
                util.DEBUG_LOG("Connection lost during iteration")
                continue
            if not conn.refreshed:
                conn.sources = conn.sources & (~source)

                # If we lost our plex.tv connection, don't remember the token.
                if source == conn.SOURCE_MYPLEX:
                    conn.token = None

            if conn.sources:
                if conn.address[:5] == "https":
                    hasSecureConn = True
                toKeep.append(conn)
            else:
                util.DEBUG_LOG("Removed connection {0} for {1} after updating connections for {2}", conn, repr(self.name), source)
                if conn == self.activeConnection:
                    util.DEBUG_LOG("Active connection lost")
                    self.activeConnection = None

        # Update fallback flag if our connections have changed
        if len(toKeep) != len(self.connections):
            for conn in toKeep:
                conn.isFallback = hasSecureConn and conn.address[:5] != "https" and not util.LOCAL_OVER_SECURE

        self.connections = toKeep

        return len(self.connections) > 0

    def merge(self, other):
        # Wherever this other server came from, assume its information is better
        # except for manual connections.

        if other.sourceType != plexresource.ResourceConnection.SOURCE_MANUAL:
            self.name = other.name
            self.versionNorm = other.versionNorm
            self.sameNetwork = other.sameNetwork

        if other.sourceType == plexresource.ResourceConnection.SOURCE_MANUAL and util.LOCAL_OVER_SECURE:
            self.sameNetwork = other.sameNetwork

        # Merge connections
        for otherConn in other.connections:
            merged = False
            for i in range(len(self.connections)):
                myConn = self.connections[i]
                if myConn == otherConn:
                    myConn.merge(otherConn)
                    merged = True
                    break

            if not merged:
                self.connections.append(otherConn)

        # If the other server has a token, then it came from plex.tv, which
        # means that its ownership information is better than ours. But if
        # it was discovered, then it may incorrectly claim to be owned, so
        # we stick with whatever we already had.

        if other.getToken():
            self.owned = other.owned
            self.owner = other.owner

    def supportsFeature(self, feature):
        return feature in self.features

    def getVersion(self):
        if not self.versionNorm:
            return ''

        return str(self.versionNorm)

    def convertUrlToLoopBack(self, url):
        # If the URL starts with our server URL, replace it with 127.0.0.1:32400.
        if self.isRequestToServer(url):
            url = 'http://127.0.0.1:32400/' + url.split('://', 1)[-1].split('/', 1)[-1]
        return url

    def resetLastTest(self):
        for i in range(len(self.connections)):
            conn = self.connections[i]
            conn.lastTestedAt = None

    def isSecondary(self):
        return self.serverClass == "secondary"

    def getLibrarySectionByUuid(self, uuid=None):
        if not uuid:
            return None
        return self.librariesByUuid[uuid]

    def setLibrarySectionByUuid(self, uuid, library):
        self.librariesByUuid[uuid] = library

    def hasInsecureConnections(self):
        if util.INTERFACE.getPreference('allow_insecure') == 'always':
            return False

        # True if we have any insecure connections we have disallowed
        for i in range(len(self.connections)):
            conn = self.connections[i]
            if not conn.isSecure and conn.state == conn.STATE_INSECURE:
                return True

        return False

    def hasSecureConnections(self):
        for i in range(len(self.connections)):
            conn = self.connections[i]
            if conn.isSecure:
                return True

        return False

    def getLibrarySectionPrefs(self, uuid):
        # TODO: Make sure I did this right - ruuk
        librarySection = self.getLibrarySectionByUuid(uuid)

        if librarySection and librarySection.key:
            # Query and store the prefs only when asked for. We could just return the
            # items, but it'll be more useful to store the pref ids in an associative
            # array for ease of selecting the pref we need.

            if not librarySection.sectionPrefs:
                path = "/library/sections/{0}/prefs".format(librarySection.key)
                data = self.query(path)
                if data:
                    librarySection.sectionPrefs = {}
                    for elem in data:
                        item = plexobjects.buildItem(self, elem, path)
                        if item.id:
                            librarySection.sectionPrefs[item.id] = item

            return librarySection.sectionPrefs

        return None

    def swizzleUrl(self, url, includeToken=False):
        m = re.search(r"^\w+://.+?(/.+)", url)
        newUrl = m and m.group(1) or None
        return self.buildUrl(newUrl or url, includeToken)

    def hasHubs(self):
        return self.platform != 'cloudsync'

    @property
    def address(self):
        return self.activeConnection.address

    @classmethod
    def deSerialize(cls, jstring):
        try:
            serverObj = json.loads(jstring)
        except:
            util.ERROR()
            util.ERROR_LOG("Failed to deserialize PlexServer JSON")
            return

        from . import plexconnection

        server = createPlexServerForName(serverObj['uuid'], serverObj['name'])
        server.owned = bool(serverObj.get('owned'))
        server.sameNetwork = serverObj.get('sameNetwork')

        hasSecureConn = False
        for i in range(len(serverObj.get('connections', []))):
            conn = serverObj['connections'][i]
            if conn['address'][:5] == "https":
                hasSecureConn = True
                break

        for i in range(len(serverObj.get('connections', []))):
            conn = serverObj['connections'][i]
            if conn['address'].endswith(":None"):
                continue

            isFallback = hasSecureConn and conn['address'][:5] != "https" and not util.LOCAL_OVER_SECURE
            sources = plexconnection.PlexConnection.SOURCE_BY_VAL[conn['sources']]
            connection = plexconnection.PlexConnection(sources, conn['address'], conn['isLocal'], conn['token'], isFallback)

            # Keep the secure connection on top
            if connection.isSecure and not util.LOCAL_OVER_SECURE:
                server.connections.insert(0, connection)
            elif not connection.isSecure and util.LOCAL_OVER_SECURE:
                server.connections.insert(0, connection)
            else:
                server.connections.append(connection)

            if conn.get('active'):
                server.activeConnection = connection

        return server

    def serialize(self, full=False):
        serverObj = {
            'name': self.name,
            'uuid': self.uuid,
            'owned': self.owned,
            'connections': []
        }

        if full:
            for conn in self.connections:
                serverObj['connections'].append({
                    'sources': conn.sources,
                    'address': conn.address,
                    'isLocal': conn.isLocal,
                    'isSecure': conn.isSecure,
                    'token': conn.token
                })
                if conn == self.activeConnection:
                    serverObj['connections'][-1]['active'] = True
        else:
            serverObj['connections'] = [{
                'sources': self.activeConnection.sources,
                'address': self.activeConnection.address,
                'isLocal': self.activeConnection.isLocal,
                'isSecure': self.activeConnection.isSecure,
                'token': self.activeConnection.token or self.getToken(),
                'active': True
            }]

        return json.dumps(serverObj)


def staleTestSeconds():
    """Longer than any reachability test can take: every attempt timing out on both connect and
    read, plus a margin."""
    timeout = util.CONN_CHECK_TIMEOUT
    connect = float(timeout.getConnectTimeout()) if hasattr(timeout, 'getConnectTimeout') else float(timeout)
    return (connect + float(timeout)) * (asyncadapter.MAX_RETRIES + 1) + 5


def dummyPlexServer():
    return createPlexServer()


def createPlexServer():
    return PlexServer()


def createPlexServerForConnection(conn):
    obj = createPlexServer()
    obj.connections.append(conn)
    obj.activeConnection = conn
    return obj


def createPlexServerForName(uuid, name):
    obj = createPlexServer()
    obj.uuid = uuid
    obj.name = name
    return obj


def createPlexServerForResource(resource):
    # resource.__class__ = PlexServer
    # resource.server = resource
    # resource.session = http.Session()
    resource.DEFER_HUBS = False
    return resource
