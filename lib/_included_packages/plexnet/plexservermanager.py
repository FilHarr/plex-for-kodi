from __future__ import absolute_import
import json
import threading

import six.moves.urllib.parse

from . import http
from . import plexconnection
from . import plexresource
from . import plexserver
from . import signalsmixin
from . import callback
from . import plexapp
from . import gdm
from . import util
from six.moves import range


class PlexServerManager(signalsmixin.SignalsMixin):
    def __init__(self):
        signalsmixin.SignalsMixin.__init__(self)
        # obj.Append(ListenersMixin())
        self.serversByUuid = {}
        self.transcodeServer = None
        self.channelServer = None
        self.deferReachabilityTimer = None
        self.reachabilityNeverTested = True
        # Signed in, until plex.tv's resources answer: see beginDiscovery()
        self.waitingForResources = False
        # The servers that matter: those with libraries in the sidebar (setWatchedServers()). Each
        # is retested while it's offline, and taken as gone only when plex.tv stops listing it -
        # see serverMatters().
        self.watchedServerUuids = frozenset()
        # The offline retests, by server uuid: [timer, step] (see scheduleOfflineRetry())
        self.offlineRetries = {}
        self._stateLock = threading.Lock()
        # Whether the account's servers are known (serversKnown()): plex.tv has answered (or
        # failed to), or the last run's were loaded
        self.resourcesAnswered = False
        self.storedLoaded = False

        self.beginDiscovery()
        self.loadState()

        plexapp.util.APP.on("change:user", callback.Callable(self.onAccountChange))
        plexapp.util.APP.on("change:allow_insecure", callback.Callable(self.onSecurityChange))
        plexapp.util.APP.on("change:manual_connections", callback.Callable(self.onManualConnectionChange))

    def serversKnown(self):
        """Whether the account's servers are known: plex.tv has answered (or failed to, its cache or
        the known servers standing in), or the last run's were loaded. Home opens then (main.py)."""
        return self.resourcesAnswered or self.storedLoaded

    @property
    def allConnections(self):
        return [c.address for s in list(self.serversByUuid.values()) for c in s.connections if s.connections]

    def getServer(self, uuid=None):
        if uuid is None:
            return None
        elif uuid == "myplex":
            from . import myplexserver
            return myplexserver.MyPlexServer()
        elif uuid == "plexdiscover":
            return self.getDiscoverServer()
        else:
            return self.serversByUuid[uuid]

    def getDiscoverServer(self):
        from . import myplexserver
        return myplexserver.PlexDiscoverServer()

    def getServers(self):
        servers = []
        for uuid in list(self.serversByUuid.keys()):
            if uuid != "myplex":
                servers.append(self.serversByUuid[uuid])

        return servers

    @property
    def connectedServers(self):
        return filter(lambda s: s.activeConnection, self.getServers())

    def hasPendingRequests(self):
        for server in self.getServers():
            if server.pendingReachabilityRequests:
                return True

        return False

    def serverMatters(self, server):
        """One with libraries in the sidebar (setWatchedServers())."""
        return server is not None and server.uuid in self.watchedServerUuids

    def setWatchedServers(self, uuids):
        """The servers the sidebar has libraries from (the UI says, whenever its list is loaded or
        changed): retested while they're offline, and gone only when plex.tv drops them. One that
        stops mattering stops being retested."""
        uuids = frozenset(uuids)
        if uuids == self.watchedServerUuids:
            return
        dropped = self.watchedServerUuids - uuids
        self.watchedServerUuids = uuids
        for uuid in dropped:
            server = self.serversByUuid.get(uuid)
            if server is not None and not self.serverMatters(server):
                self.cancelOfflineRetry(server)
        self.resumeOfflineRetry()

    def removeServer(self, server, source=None):
        """A server none of the sources lists any more. For one that matters (serverMatters()), only
        plex.tv's list (with the account signed in) means the account no longer has it: that's
        gone - see onServerGone(). Any other way of losing it - a GDM broadcast that went unanswered
        once, a manual entry removed, signing out - keeps it, offline, and retested."""
        matters = self.serverMatters(server)
        if matters:
            if source != plexresource.ResourceConnection.SOURCE_MYPLEX or not plexapp.ACCOUNT.isSignedIn:
                util.LOG("{0} is no longer listed by {1}, keeping it as offline", repr(server.name), source)
                self.setServerOnline(server, False)
                return

        del self.serversByUuid[server.uuid]

        self.trigger('remove:server')

        if matters:
            self.onServerGone(server)

        if server == self.transcodeServer:
            util.LOG("The selected transcode server went away")
            self.transcodeServer = None

        if server == self.channelServer:
            util.LOG("The selected channel server went away")
            self.channelServer = None

    def onServerGone(self, server):
        """plex.tv no longer lists a server the sidebar has libraries from: the account doesn't have
        it any more (removed, or the share revoked), so it won't be back - unlike an offline one,
        it isn't retested. 'gone:server' (server=) lets the UI take its libraries out."""
        util.LOG("{0} is no longer on this account", repr(server.name))
        server.gone = True
        self.cancelOfflineRetry(server)
        with self._stateLock:
            server.offline = True
        self.trigger('gone:server', server=server)

    def updateFromConnectionType(self, servers, source):
        self.markDevicesAsRefreshing()

        for server in servers:
            self.mergeServer(server)

        if source == plexresource.ResourceConnection.SOURCE_MYPLEX:
            self.resourcesAnswered = True
            self.waitingForResources = False

        if not self.waitingForResources:
            self.deviceRefreshComplete(source)
            self.updateReachability(True)
            self.saveState()

    def resourcesUnavailable(self):
        """plex.tv couldn't give us resources: stop waiting for them and test the servers we
        already know (stored, discovered, manual) instead."""
        self.resourcesAnswered = True
        self.waitingForResources = False
        self.updateReachability(True)

    def updateFromDiscovery(self, server):
        merged = self.mergeServer(server)

        if not merged.activeConnection:
            merged.updateReachability(False, True)
        else:
            # self.notifyAboutDevice(merged, True)
            pass

    def markDevicesAsRefreshing(self):
        for uuid in list(self.serversByUuid.keys()):
            self.serversByUuid[uuid].markAsRefreshing()

    def mergeServer(self, server):
        if server.uuid in self.serversByUuid:
            existing = self.serversByUuid[server.uuid]
            existing.merge(server)
            util.DEBUG_LOG("Merged {0}", repr(server.name))
            return existing
        else:
            self.serversByUuid[server.uuid] = server
            util.DEBUG_LOG("Added new server {0}", repr(server.name))
            self.trigger("new:server", server=server)
            return server

    def deviceRefreshComplete(self, source):
        toRemove = []
        for uuid in list(self.serversByUuid.keys()):
            if not self.serversByUuid[uuid].markUpdateFinished(source):
                toRemove.append(uuid)

        for uuid in toRemove:
            if uuid not in self.serversByUuid:
                util.DEBUG_LOG("Server {} lost - removing", uuid)
                continue

            server = self.serversByUuid[uuid]

            util.DEBUG_LOG("Server {0} has no more connections - removing", repr(server.name))
            # self.notifyAboutDevice(server, False)
            self.removeServer(server, source)

    def updateReachability(self, force=False, defer=False):
        # We don't need to test any servers unless we are signed in and authenticated.
        if not plexapp.ACCOUNT.isAuthenticated and plexapp.ACCOUNT.isActive():
            util.LOG("Ignore testing server reachability until we're authenticated")
            return

        self.reachabilityNeverTested = False

        # Every server is tested at once: there's no one server to start with (and test first)
        # any more - the sidebar's are all wanted (plan Phase 9.3).
        if defer:
            self.deferUpdateReachability()
        else:
            if self.deferReachabilityTimer:
                self.deferReachabilityTimer.cancel()
                self.deferReachabilityTimer = None

            util.LOG("Updating reachability for all devices: force={0}", force)
            for uuid in list(self.serversByUuid.keys()):
                self.serversByUuid[uuid].updateReachability(force)

    def cancelReachability(self):
        if self.deferReachabilityTimer:
            self.deferReachabilityTimer.cancel()
            self.deferReachabilityTimer = None
        self.cancelOfflineRetry()

        for uuid in list(self.serversByUuid.keys()):
            self.serversByUuid[uuid].cancelReachability()

    # Seconds between retests of a server that matters while it's offline: the first few soon (a
    # restart, a Wi-Fi blip), then once a minute for as long as it stays down.
    OFFLINE_RETRY_DELAYS = (5, 10, 30, 60)

    def onServerSuspect(self, server):
        """PlexServer.markSuspect(): a query to server got no answer, and its connections are being
        retested. Says so at once ('suspect:server', server=), before the retest's verdict, unless
        it's already known to be offline: the retests are what's running then."""
        with self._stateLock:
            if server.offline or server.gone or server.suspect:
                return
            server.suspect = True
        self.trigger('suspect:server', server=server)

    def setServerOnline(self, server, online):
        """Records whether a server can be reached and, when that changes, says so: 'online:server'
        or 'offline:server' (server=). Results arrive on one HTTP thread per connection, hence the
        lock - only the call that actually changes the state signals. A suspect server
        (onServerSuspect()) that turns out to be reachable after all says 'recovered:server': the
        query that failed has left something empty that's worth loading again. That's decided once
        the retest round has ended: mid-round, a result counts as reachable while the connection
        the query failed on is still the active one, untested yet (live-caught on the PC: Oscar
        "answered after all" 2 ms before the round ended offline)."""
        settled = server.pendingReachabilityRequests <= 0
        with self._stateLock:
            recovered = online and settled and server.suspect and not server.offline
            if settled:
                server.suspect = False
            if online and settled:
                # Answering now, so the next query that goes unanswered is news: retest at once,
                # not up to 30 s later (PlexServer.markSuspect()). Live on the PC: Plex stopped
                # again 18 s after it came back, and the empty view that followed said nothing.
                server._lastSuspectRetest = 0
            if server.offline != (not online):
                server.offline = not online
                changed = True
            else:
                changed = False

        if self.serverMatters(server):
            if online:
                self.cancelOfflineRetry(server)
            elif not self._retryTimer(server) and not server.gone:
                # a retest round that ended still offline schedules the next one
                self.scheduleOfflineRetry(server)

        if changed:
            util.LOG("{0} is {1}", repr(server.name), online and "online again" or "offline")
            self.trigger(online and 'online:server' or 'offline:server', server=server)
        elif recovered:
            util.LOG("{0} answers after all", repr(server.name))
            self.trigger('recovered:server', server=server)

    def _retryTimer(self, server):
        return self.offlineRetries.get(server.uuid, (None, 0))[0]

    def scheduleOfflineRetry(self, server):
        step = self.offlineRetries.get(server.uuid, (None, 0))[1]
        delay = self.OFFLINE_RETRY_DELAYS[min(step, len(self.OFFLINE_RETRY_DELAYS) - 1)]
        util.DEBUG_LOG("Retesting {0} in {1}s", repr(server.name), delay)
        timer = plexapp.createTimer(delay * 1000, callback.Callable(self.onOfflineRetryTimer, forcedArgs=[server]))
        self.offlineRetries[server.uuid] = [timer, step + 1]
        util.APP.addTimer(timer)

    def cancelOfflineRetry(self, server=None):
        """Stops retesting a server (it's back, stopped mattering or is gone), or every server (the
        device is going to sleep), and starts the delays from the beginning next time."""
        uuids = [server.uuid] if server is not None else list(self.offlineRetries)
        for uuid in uuids:
            timer = self.offlineRetries.pop(uuid, (None, 0))[0]
            if timer:
                timer.cancel()

    def resumeOfflineRetry(self):
        """Retests every server that matters and is offline, unless one is already scheduled: back
        from sleep or a screensaver (which cancel them), or a server newly in the sidebar."""
        for server in self.getServers():
            if self.serverMatters(server) and server.offline and not server.gone and not self._retryTimer(server):
                self.scheduleOfflineRetry(server)

    def retestServerNow(self, server):
        """The user asked ("Try again"): retest a server now, not at the next step of its offline
        backoff. If it's still down, the round's verdict schedules the next step as usual
        (setServerOnline()). Returns whether a retest is under way."""
        if not server or server.gone:
            return False
        timer = self._retryTimer(server)
        if timer:
            timer.cancel()
            self.offlineRetries[server.uuid][0] = None
        util.LOG("Retesting {0} now, as asked", repr(server.name))
        server.resetLastTest()
        server.updateReachability(True)
        if server.pendingReachabilityRequests <= 0:
            # nothing to test: no round will end with a verdict, so give it now
            self.updateReachabilityResult(server, bool(server.activeConnection))
            return False
        return True

    def onOfflineRetryTimer(self, server):
        retry = self.offlineRetries.get(server.uuid)
        if retry:
            retry[0] = None
        if not server.offline or server.gone or not self.serverMatters(server):
            # back, off the account (retesting can't bring it back), or no longer of interest
            return

        if not server.connections:
            # dropped by a source other than plex.tv (see removeServer()): only a fresh list -
            # discovery included - can bring its connections back
            util.LOG("Offline server {0} has no connections, asking for the server lists again", repr(server.name))
            plexapp.refreshResources(True)
        else:
            util.LOG("Retesting offline server {0}", repr(server.name))
            server.resetLastTest()
            server.updateReachability(True)

        if server.pendingReachabilityRequests <= 0 and server.offline and not self._retryTimer(server):
            # nothing got started, so no round will end to schedule the next try
            self.scheduleOfflineRetry(server)

    def updateReachabilityResult(self, server, reachable=False):
        if reachable:
            self.setServerOnline(server, True)
        elif server.pendingReachabilityRequests <= 0:
            # Offline only once the round has settled: a single connection's failure (and the
            # active connection's own retest) can come in while the rest are still being tried.
            self.setServerOnline(server, False)

        if reachable:
            self.trigger('reachable:server', server=server)
        else:
            if server == self.transcodeServer:
                util.LOG("The selected transcode server is not reachable")
                self.transcodeServer = None

            if server == self.channelServer:
                util.LOG("The selected channel server is not reachable")
                self.channelServer = None

    def compareServers(self, first, second):
        if not first or not first.isSupported:
            return second and -1 or 0
        elif not second:
            return 1
        elif first.owned != second.owned:
            return first.owned and 1 or -1
        elif first.isLocalConnection() != second.isLocalConnection():
            return first.isLocalConnection() and 1 or -1
        else:
            return 0

    def loadState(self):
        jstring = util.INTERFACE.getRegistry("PlexServerManager")
        if not jstring:
            return

        try:
            obj = json.loads(jstring)
        except:
            util.ERROR()
            obj = None

        if not obj:
            util.ERROR_LOG("Failed to parse PlexServerManager JSON")
            return

        for serverObj in obj['servers']:
            server = plexserver.createPlexServerForName(serverObj['uuid'], serverObj['name'])
            server.owned = bool(serverObj.get('owned'))
            server.sameNetwork = serverObj.get('sameNetwork')
            server.dnsRebindingProtection = serverObj.get('dnsRebindingProtection')

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

                address = conn['address']

                # local mode only considers direct LAN connections; plex.direct needs public DNS
                if util.LOCAL_MODE and (not conn['isLocal'] or ".plex.direct" in address):
                    if not conn['isLocal'] or ".plex.direct" not in address:
                        continue

                    # local plex.direct hostnames embed the LAN IP; synthesize a direct
                    # connection from it, so servers that were never GDM-discovered and have
                    # no manual IP (e.g. the server sits on another subnet - GDM broadcasts
                    # don't cross those) still survive going local. Plain http, so servers
                    # requiring secure connections won't accept it - same limitation as
                    # manually added IPs.
                    try:
                        pUrl = six.moves.urllib.parse.urlparse(address)
                        address = 'http://' + util.hostPort(util.parsePlexDirectHost(pUrl.hostname), pUrl.port)
                        util.DEBUG_LOG("[LOCAL] synthesized {0} from {1}", address, conn['address'])
                    except:
                        continue

                # synthesized connections can collide with a stored plain one (and vice versa)
                if any(c.address == address for c in server.connections):
                    continue

                isFallback = hasSecureConn and conn['address'][:5] != "https" and not util.LOCAL_OVER_SECURE
                sources = plexconnection.PlexConnection.SOURCE_BY_VAL[conn['sources']]
                connection = plexconnection.PlexConnection(sources, address, conn['isLocal'], conn['token'], isFallback)

                # Keep the secure connection on top
                if connection.isSecure and not util.LOCAL_OVER_SECURE:
                    server.connections.insert(0, connection)
                elif not connection.isSecure and util.LOCAL_OVER_SECURE:
                    server.connections.insert(0, connection)
                else:
                    server.connections.append(connection)

            if util.LOCAL_MODE and not server.connections:
                util.DEBUG_LOG("[LOCAL] skipping server {0} (no local connections)", repr(server.name))
                continue

            self.serversByUuid[server.uuid] = server

        util.LOG("Loaded {0} servers from registry", len(obj['servers']))
        self.storedLoaded = bool(self.serversByUuid)
        util.APP.trigger("loaded:server_connections", servers=self.serversByUuid.values(), source="stored")
        self.updateReachability()

    def saveState(self):
        # Serialize our important information to JSON and save it to the registry.
        # We'll always update server info upon connecting, so we don't need much
        # info here. We do have to use roArray instead of roList, because Brightscript.

        obj = {}

        servers = self.getServers()
        obj['servers'] = []

        hosts = []

        for server in servers:
            # Don't save secondary servers. They should be discovered through GDM or myPlex.
            if not server.isSecondary():
                serverObj = {
                    'name': server.name,
                    'uuid': server.uuid,
                    'owned': server.owned,
                    'sameNetwork': server.sameNetwork,
                    'dnsRebindingProtection': server.dnsRebindingProtection,
                    'connections': []
                }

                for i in range(len(server.connections)):
                    conn = server.connections[i]
                    hosts.append(conn.address)
                    serverObj['connections'].append({
                        'sources': conn.sources,
                        'address': conn.address,
                        'isLocal': conn.isLocal,
                        'isSecure': conn.isSecure,
                        'token': conn.token
                    })

                obj['servers'].append(serverObj)

        # lastServerId.<account> isn't written any more: it now says which server the settings from
        # before account-wide keys belong to (lib/windows/section_ids.legacyServer()), so it stays
        # as the last run that selected a server left it (plan Phase 9.2). Nothing selects one now.

        util.APP.trigger("loaded:server_connections", servers=servers, source="myplex")
        util.INTERFACE.setRegistry("PlexServerManager", json.dumps(obj))

    def clearState(self):
        util.INTERFACE.setRegistry("PlexServerManager", '')

    def isValidForTranscoding(self, server):
        return server and server.activeConnection and server.owned and not server.synced and not server.isSecondary()

    def getChannelServer(self):
        if not self.channelServer or not self.channelServer.isReachable():
            self.channelServer = None

            # Attempt to find a server that supports channels and transcoding
            for s in self.getServers():
                if s.supportsVideoTranscoding and s.allowChannelAccess and s.isReachable() and self.compareServers(self.channelServer, s) < 0:
                    self.channelServer = s

            # Fallback to any server that supports channels
            if not self.channelServer:
                for s in self.getServers():
                    if s.allowChannelAccess and s.isReachable() and self.compareServers(self.channelServer, s) < 0:
                        self.channelServer = s

            if self.channelServer:
                util.LOG("Setting channel server to {0}", self.channelServer)

        return self.channelServer

    def getTranscodeServer(self, transcodeType=None):
        """A server to transcode for a synced one (PlexServer.getImageTranscodeURL()), which can't
        itself: the best reachable server that isn't synced and can transcode transcodeType, or
        None. It was the selected server's stand-in; there's no selected server now (Phase 9.3)."""
        transcodeSupport = {
            'audio': "supportsAudioTranscoding",
            'video': "supportsVideoTranscoding",
            'photo': "supportsPhotoTranscoding"
        }.get(transcodeType)

        if self.transcodeServer and self.transcodeServer.isReachable():
            return self.transcodeServer

        self.transcodeServer = None
        for server in self.getServers():
            if not server.synced and server.isReachable() and self.compareServers(self.transcodeServer, server) < 0:
                if not transcodeSupport or getattr(server, transcodeSupport, False):
                    self.transcodeServer = server

        if self.transcodeServer:
            util.LOG("Using {0} as the {1} transcode server", self.transcodeServer, transcodeType or '')
        return self.transcodeServer

    def beginDiscovery(self):
        """A fresh look for the account's servers (startup, another account, local mode): the
        transcode and channel servers are picked again, and while signed in, no list but plex.tv's
        settles which servers the account has until plex.tv has answered (updateFromConnectionType()).
        This was the start of the selected-server search, the rest of which is gone (Phase 9.3)."""
        self.transcodeServer = None
        self.channelServer = None
        self.waitingForResources = plexapp.ACCOUNT.isSignedIn
        if util.LOCAL_OVER_SECURE:
            util.WARN_LOG("Preferring local server connections over secure ones!")

    def onAccountChange(self, account, reallyChanged=False):
        # Clear any AudioPlayer data before invalidating the active server
        if reallyChanged:
            # AudioPlayer().Cleanup()
            # PhotoPlayer().Cleanup()

            util.DEBUG_LOG("Account really changed, clearing all servers")

            # Clear the transcode servers on user change
            self.transcodeServer = None
            self.channelServer = None
            self.cancelReachability()

        if account.isSignedIn:
            # If the user didn't really change, such as selecting the previous user
            # on the lock screen, then we don't need to clear anything. We can
            # avoid a costly round of reachability checks.

            if not reallyChanged:
                return

            # A request to refresh resources has already been kicked off. We need
            # to clear out any connections for the previous user and then look for
            # this one's.

            self.updateFromConnectionType([], plexresource.ResourceConnection.SOURCE_MYPLEX)
            self.updateFromConnectionType([], plexresource.ResourceConnection.SOURCE_DISCOVERED)
            self.updateFromConnectionType([], plexresource.ResourceConnection.SOURCE_MANUAL)
            # another user's servers: known once plex.tv answers for them
            self.resourcesAnswered = self.storedLoaded = False

            self.beginDiscovery()

            if reallyChanged:
                util.DEBUG_LOG("User really changed, refreshing resources now")
                plexapp.refreshResources()
        else:
            # Clear servers/connections from plex.tv
            self.updateFromConnectionType([], plexresource.ResourceConnection.SOURCE_MYPLEX)

    def deferUpdateReachability(self, addTimer=True, logInfo=True):
        if addTimer and not self.deferReachabilityTimer:
            self.deferReachabilityTimer = plexapp.createTimer(1000, callback.Callable(self.onDeferUpdateReachabilityTimer), repeat=True)
            util.APP.addTimer(self.deferReachabilityTimer)
        else:
            if self.deferReachabilityTimer:
                self.deferReachabilityTimer.reset()

        if self.deferReachabilityTimer and logInfo:
            util.LOG('Defer update reachability for all devices a few seconds: GDMactive={0}', gdm.DISCOVERY.isActive())

    def onDeferUpdateReachabilityTimer(self):
        if self.deferReachabilityTimer:
            self.deferReachabilityTimer.cancel()
        self.deferReachabilityTimer = None
        self.updateReachability(True)

    def checkServersAlive(self):
        """The light, frequent check (PlexServer.checkAlive()) on every server that matters, so one
        that stops answering while nothing is using it is noticed within a check's interval."""
        for server in self.getServers():
            if self.serverMatters(server):
                server.checkAlive()

    def periodicReachabilityCheck(self):
        """Re-test reachability on every server that matters (serverMatters()) to detect network
        changes (e.g. WiFi -> mobile)."""
        if not plexapp.ACCOUNT.isAuthenticated:
            return

        for server in self.getServers():
            if not self.serverMatters(server) or server.gone:
                continue
            oldConn = server.activeConnection
            oldAddr = oldConn and oldConn.address or None

            util.LOG("Periodic reachability check for {0}", repr(server.name))
            server.resetLastTest()
            server.updateReachability(True)

            # Log if the connection changed immediately (synchronous connections).
            # Most changes will be detected asynchronously via onReachabilityResult.
            newConn = server.activeConnection
            newAddr = newConn and newConn.address or None
            if oldAddr and newAddr and oldAddr != newAddr:
                util.LOG("Periodic reachability: active connection changed from {0} to {1}", oldAddr, newAddr)

    def resetLastTest(self):
        for uuid in list(self.serversByUuid.keys()):
            self.serversByUuid[uuid].resetLastTest()

    def clearServers(self):
        self.cancelReachability()
        self.serversByUuid = {}
        self.saveState()

    def onSecurityChange(self, value=None):
        # If the security policy changes, then we will need to allow all
        # connections to be retested by resetting the last test. We can
        # simply call `self.resetLastTest()` to allow all connection to be
        # tested when the server dropdown is enable, but we may as well
        # test all the connections immediately.

        plexapp.refreshResources(True)

    def onManualConnectionChange(self, value=None):
        # Clear all manual connections on change. A sidebar server that only had a manual
        # connection is kept meanwhile: removeServer() keeps it, offline. (This used to try to put
        # such a server back itself, reading .sources off a list - it would have raised had it
        # ever run.)
        self.updateFromConnectionType([], plexresource.ResourceConnection.SOURCE_MANUAL)

    def refreshManualConnections(self):
        manualConnections = self.getManualConnections()
        if not manualConnections:
            util.DEBUG_LOG("No manual connections.")
            return

        util.LOG("Refreshing {0} manual connections", len(manualConnections))

        for conn in manualConnections:
            # Default to http, as the server will need to be signed in for https to work,
            # so the client should too. We'd also have to allow hostname entry, instead of
            # IP address for the cert to validate.

            proto = "http"
            port = conn.port or "32400"
            serverAddress = "{0}://{1}".format(proto, util.hostPort(conn.connection, port))

            request = http.HttpRequest(serverAddress + "/identity", retries=0)
            context = request.createRequestContext("manual_connections",
                                                   callback.Callable(self.onManualConnectionsResponse),
                                                   timeout=util.CONN_CHECK_TIMEOUT)
            context.serverAddress = serverAddress
            context.address = conn.connection
            context.proto = proto
            context.port = port
            context.token = conn.token
            context.name = conn.name
            util.APP.startRequest(request, context)

    def onManualConnectionsResponse(self, request, response, context):
        if not response.isSuccess():
            return

        data = response.getBodyXml()
        if data is not None:
            serverAddress = context.serverAddress
            util.DEBUG_LOG("Received manual connection response for {0}", serverAddress)

            machineID = data.attrib.get('machineIdentifier')
            name = context.name or context.address
            if not name or not machineID:
                return

            # TODO(rob): Do we NOT want to consider manual connections local?
            conn = plexconnection.PlexConnection(plexresource.ResourceConnection.SOURCE_MANUAL, serverAddress, True,
                                                 context.token)
            server = plexserver.createPlexServerForConnection(conn)
            server.uuid = machineID
            server.name = name
            server.sourceType = plexresource.ResourceConnection.SOURCE_MANUAL
            self.updateFromConnectionType([server], plexresource.ResourceConnection.SOURCE_MANUAL)

    def getManualConnections(self):
        manualConnections = []

        jstring = util.INTERFACE.getPreference('manual_connections')
        if jstring:
            connections = json.loads(jstring)
            if isinstance(connections, list):
                for conn in connections:
                    conn = util.AttributeDict(conn)
                    if conn.connection:
                        manualConnections.append(conn)

        return manualConnections

# TODO(schuyler): Notifications


MANAGER = PlexServerManager()
