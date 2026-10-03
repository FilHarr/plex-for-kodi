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


class SearchContext(dict):
    def __getattr__(self, attr):
        return self.get(attr)

    def __setattr__(self, attr, value):
        self[attr] = value


class PlexServerManager(signalsmixin.SignalsMixin):
    def __init__(self):
        signalsmixin.SignalsMixin.__init__(self)
        # obj.Append(ListenersMixin())
        self.serversByUuid = {}
        self.selectedServer = None
        self.transcodeServer = None
        self.channelServer = None
        self.deferReachabilityTimer = None
        self.reachabilityNeverTested = True
        # Retests the selected server while it's offline (see scheduleOfflineRetry())
        self.offlineRetryTimer = None
        self.offlineRetryStep = 0
        self._stateLock = threading.Lock()

        self.startSelectedServerSearch()
        self.loadState()

        plexapp.util.APP.on("change:user", callback.Callable(self.onAccountChange))
        plexapp.util.APP.on("change:allow_insecure", callback.Callable(self.onSecurityChange))
        plexapp.util.APP.on("change:manual_connections", callback.Callable(self.onManualConnectionChange))

    def getSelectedServer(self):
        return self.selectedServer

    @property
    def allConnections(self):
        return [c.address for s in list(self.serversByUuid.values()) for c in s.connections if s.connections]

    def setSelectedServer(self, server, force=False):
        # Don't do anything if the server is already selected.
        if self.selectedServer and self.selectedServer == server:
            return False

        if server:
            # Don't select servers that don't have connections.
            if not server.activeConnection:
                return False

            # Don't select servers that are not supported
            if not server.isSupported:
                return False

        if not self.selectedServer or force:
            util.LOG("Setting selected server to {0}", server)
            self.selectedServer = server
            self.cancelOfflineRetry()

            if server:
                # The search for a server to start with is over: from here on, only the user
                # changes servers. A later reachability result settling for the "best" server
                # found would otherwise switch servers under them.
                if self.searchContext:
                    self.searchContext.active = False

                prefs = server.getPrefs() if server.owned else None
                if prefs:
                    util.LOG("Got and stored server prefs for {0}", server.name)
                    for pref in prefs:
                        if pref.get("id") in ("LibraryVideoPlayedThreshold", "LibraryVideoPlayedAtBehaviour"):
                            server.prefs[str(pref.get("id"))] = pref.get("value").asInt()
                    util.INTERFACE.setRegistry("PlexServerPrefs", json.dumps(server.prefs), sec=server.uuid[-8:])
                else:
                    # not owned, or the server didn't answer (an owned server always has prefs;
                    # storing the empty answer used to wipe the cached ones)
                    util.LOG("{0}: no prefs from the server ({1}), trying cached ones",
                             server.name, server.owned and "no answer" or "not owned")
                    try:
                        server.prefs = json.loads(util.INTERFACE.getRegistry("PlexServerPrefs", sec=server.uuid[-8:]))
                        util.DEBUG_LOG("Cached server prefs loaded for {0}", server.name)
                    except:
                        pass

                # Update our saved state.
                self.saveState(setPreferred=True)

                # Notify anyone who might care.
                util.APP.trigger("change:selectedServer", server=server)

                return True
        return False

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

    def removeServer(self, server, source=None):
        """A server none of the sources lists any more. For the selected one, only plex.tv's list
        (with the account signed in) means the account no longer has it: that's gone - see
        onSelectedServerGone(). Any other way of losing it - a GDM broadcast that went unanswered
        once, a manual entry removed, signing out - keeps it selected, offline, and retested; the
        selection is never cleared under the UI, which can't survive having none."""
        if server == self.selectedServer:
            if source != plexresource.ResourceConnection.SOURCE_MYPLEX or not plexapp.ACCOUNT.isSignedIn:
                util.LOG("The selected server {0} is no longer listed by {1}, keeping it as offline",
                         repr(server.name), source)
                self.setServerOnline(server, False)
                return

        del self.serversByUuid[server.uuid]

        self.trigger('remove:server')

        if server == self.selectedServer:
            self.onSelectedServerGone(server)

        if server == self.transcodeServer:
            util.LOG("The selected transcode server went away")
            self.transcodeServer = None

        if server == self.channelServer:
            util.LOG("The selected channel server went away")
            self.channelServer = None

    def onSelectedServerGone(self, server):
        """plex.tv no longer lists the selected server: the account doesn't have it any more
        (removed, or the share revoked), so it won't be back - unlike an offline one, it isn't
        retested. Switches to the best server that answers, saying so ('gone:selectedServer',
        server=, replacement=), or with none keeps the gone one selected until the user picks
        another (the UI can't survive having none)."""
        util.LOG("The selected server {0} is no longer on this account", repr(server.name))
        server.gone = True
        self.cancelOfflineRetry()
        with self._stateLock:
            server.offline = True

        replacement = None
        for candidate in self.getServers():
            if candidate.isReachable() and self.compareServers(replacement, candidate) < 0:
                replacement = candidate

        self.trigger('gone:selectedServer', server=server, replacement=replacement)
        if replacement:
            self.setSelectedServer(replacement, force=True)

    def updateFromConnectionType(self, servers, source):
        self.markDevicesAsRefreshing()

        for server in servers:
            self.mergeServer(server)

        if self.searchContext and source == plexresource.ResourceConnection.SOURCE_MYPLEX:
            self.searchContext.waitingForResources = False

        if not self.searchContext.waitingForResources:
            self.deviceRefreshComplete(source)
            self.updateReachability(True, True)
            self.saveState()

    def resourcesUnavailable(self):
        """plex.tv couldn't give us resources: stop waiting for them and test the servers we
        already know (stored, discovered, manual) instead."""
        if self.searchContext:
            self.searchContext.waitingForResources = False
        self.updateReachability(True, True)

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
        elif self.selectedServer is not None and self.selectedServer.gone and self.selectedServer.uuid == server.uuid:
            # The gone server is still selected (nothing else answered) and plex.tv lists it again
            # (a share restored): take that same object back. A new one beside it would read as
            # "already selected" to setSelectedServer() (it compares uuid and owner), so it could
            # never be picked.
            existing = self.selectedServer
            existing.gone = False
            existing.merge(server)
            self.serversByUuid[server.uuid] = existing
            util.LOG("The selected server {0} is back on this account", repr(server.name))
            self.trigger("new:server", server=existing)
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

    def updateReachability(self, force=False, preferSearch=False, defer=False):
        # We don't need to test any servers unless we are signed in and authenticated.
        if not plexapp.ACCOUNT.isAuthenticated and plexapp.ACCOUNT.isActive():
            util.LOG("Ignore testing server reachability until we're authenticated")
            return

        self.reachabilityNeverTested = False

        # To improve reachability performance and app startup, we'll try to test the
        # preferred server first, and defer the connection tests for a few seconds.

        hasPreferredServer = bool(self.searchContext.preferredServer)
        preferredServerExists = hasPreferredServer and self.searchContext.preferredServer in self.serversByUuid

        if preferSearch and hasPreferredServer and preferredServerExists:
            # Update the preferred server immediately if requested and exits
            util.LOG("Updating reachability for preferred server: force={0}", force)
            self.serversByUuid[self.searchContext.preferredServer].updateReachability(force)
            self.deferUpdateReachability()
        elif defer:
            self.deferUpdateReachability()
        elif hasPreferredServer and not preferredServerExists and gdm.DISCOVERY.isActive():
            # Defer the update if requested or if GDM discovery is enabled and
            # active while the preferred server doesn't exist.

            util.LOG("Defer update reachability until GDM has finished to help locate the preferred server")
            self.deferUpdateReachability(True, False)
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

    # Seconds between retests of the selected server while it's offline: the first few soon (a
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

        if server is self.selectedServer:
            if online:
                self.cancelOfflineRetry()
            elif not self.offlineRetryTimer and not server.gone:
                # a retest round that ended still offline schedules the next one
                self.scheduleOfflineRetry()

        if changed:
            util.LOG("{0} is {1}", repr(server.name), online and "online again" or "offline")
            self.trigger(online and 'online:server' or 'offline:server', server=server)
        elif recovered:
            util.LOG("{0} answers after all", repr(server.name))
            self.trigger('recovered:server', server=server)

    def scheduleOfflineRetry(self):
        delay = self.OFFLINE_RETRY_DELAYS[min(self.offlineRetryStep, len(self.OFFLINE_RETRY_DELAYS) - 1)]
        self.offlineRetryStep += 1
        util.DEBUG_LOG("Retesting {0} in {1}s", repr(self.selectedServer and self.selectedServer.name), delay)
        self.offlineRetryTimer = plexapp.createTimer(delay * 1000, callback.Callable(self.onOfflineRetryTimer))
        util.APP.addTimer(self.offlineRetryTimer)

    def cancelOfflineRetry(self):
        """Stops retesting (the server is back, another was selected, or the device is going to
        sleep) and starts the delays from the beginning next time."""
        if self.offlineRetryTimer:
            self.offlineRetryTimer.cancel()
            self.offlineRetryTimer = None
        self.offlineRetryStep = 0

    def resumeOfflineRetry(self):
        """Back from sleep or a screensaver (which cancel the retests): retest the selected server
        again if it's still offline."""
        server = self.selectedServer
        if server and server.offline and not server.gone and not self.offlineRetryTimer:
            self.scheduleOfflineRetry()

    def retestSelectedServerNow(self):
        """The user asked ("Try again"): retest the selected server now, not at the next step of
        the offline backoff. If it's still down, the round's verdict schedules the next step as
        usual (setServerOnline()). Returns whether a retest is under way."""
        server = self.selectedServer
        if not server or server.gone:
            return False
        if self.offlineRetryTimer:
            self.offlineRetryTimer.cancel()
            self.offlineRetryTimer = None
        util.LOG("Retesting {0} now, as asked", repr(server.name))
        server.resetLastTest()
        server.updateReachability(True)
        if server.pendingReachabilityRequests <= 0:
            # nothing to test: no round will end with a verdict, so give it now
            self.updateReachabilityResult(server, bool(server.activeConnection))
            return False
        return True

    def onOfflineRetryTimer(self):
        self.offlineRetryTimer = None
        server = self.selectedServer
        if not server or not server.offline:
            return

        if server.gone:
            return  # off the account: retesting can't bring it back (onSelectedServerGone())

        if not server.connections:
            # dropped by a source other than plex.tv (see removeServer()): only a fresh list -
            # discovery included - can bring its connections back
            util.LOG("Offline server {0} has no connections, asking for the server lists again", repr(server.name))
            plexapp.refreshResources(True)
        else:
            util.LOG("Retesting offline server {0}", repr(server.name))
            server.resetLastTest()
            server.updateReachability(True)

        if server.pendingReachabilityRequests <= 0 and server.offline and not self.offlineRetryTimer:
            # nothing got started, so no round will end to schedule the next try
            self.scheduleOfflineRetry()

    def updateReachabilityResult(self, server, reachable=False):
        searching = not self.selectedServer and self.searchContext and self.searchContext.active

        if reachable:
            self.setServerOnline(server, True)
        elif server.pendingReachabilityRequests <= 0:
            # Offline only once the round has settled: a single connection's failure (and the
            # active connection's own retest) can come in while the rest are still being tried.
            self.setServerOnline(server, False)

        if reachable:
            # If we're in the middle of a search for our selected server, see if
            # this is a candidate.
            self.trigger('reachable:server', server=server)
            if searching:
                # If this is what we were hoping for, select it
                if server.uuid == self.searchContext.preferredServer:
                    self.setSelectedServer(server, True)
                elif server.synced:
                    self.searchContext.fallbackServer = server
                elif self.compareServers(self.searchContext.bestServer, server) < 0:
                    self.searchContext.bestServer = server
        else:
            # If this is what we were hoping for, see if there are any more pending
            # requests to hope for.

            if searching and server.uuid == self.searchContext.preferredServer and server.pendingReachabilityRequests <= 0:
                self.searchContext.preferredServer = None

            # The selected server stays selected while unreachable (it's offline - see
            # setServerOnline()); clearing it, as this once did, left the UI with no server.

            if server == self.transcodeServer:
                util.LOG("The selected transcode server is not reachable")
                self.transcodeServer = None

            if server == self.channelServer:
                util.LOG("The selected channel server is not reachable")
                self.channelServer = None

        # See if we should settle for the best we've found so far.
        self.checkSelectedServerSearch()

    def checkSelectedServerSearch(self, skip_preferred=False, skip_owned=False):
        if self.selectedServer:
            return self.selectedServer
        elif self.searchContext and self.searchContext.active:
            # If we're still waiting on the resources response then there's no
            # reason to settle, so don't even iterate over our servers.

            if self.searchContext.waitingForResources:
                util.DEBUG_LOG("Still waiting for plex.tv resources")
                return

            waitingForPreferred = False
            waitingForOwned = False
            waitingForAnything = False
            waitingToTestAll = bool(self.deferReachabilityTimer)

            if skip_preferred:
                self.searchContext.preferredServer = None
                if self.deferReachabilityTimer:
                    self.deferReachabilityTimer.cancel()
                    self.deferReachabilityTimer = None

            if not skip_owned:
                # Iterate over all our servers and see if we're waiting on any results
                servers = self.getServers()
                pendingCount = 0
                for server in servers:
                    if server.pendingReachabilityRequests > 0:
                        pendingCount += server.pendingReachabilityRequests
                        if server.uuid == self.searchContext.preferredServer:
                            waitingForPreferred = True
                        elif server.owned:
                            waitingForOwned = True
                        else:
                            waitingForAnything = True

                pendingString = "{0} pending reachability tests".format(pendingCount)

            if waitingForPreferred:
                util.LOG("Still waiting for preferred server: " + pendingString)
            elif waitingToTestAll:
                util.LOG("Preferred server not reachable, testing all servers now")
                self.updateReachability(True, False, False)
            elif waitingForOwned and (not self.searchContext.bestServer or not self.searchContext.bestServer.owned):
                util.LOG("Still waiting for an owned server: " + pendingString)
            elif waitingForAnything and not self.searchContext.bestServer:
                util.LOG("Still waiting for any server: {0}", pendingString)
            else:
                # No hope for anything better, let's select what we found
                util.LOG("Settling for the best server we found")
                self.setSelectedServer(self.searchContext.bestServer or self.searchContext.fallbackServer, True)
                return self.selectedServer

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
        util.APP.trigger("loaded:server_connections", servers=self.serversByUuid.values(), source="stored")
        self.updateReachability(False, True)

    def saveState(self, setPreferred=False):
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

        if self.selectedServer and not self.selectedServer.synced and not self.selectedServer.isSecondary() \
                and setPreferred:
            util.INTERFACE.setPreference("lastServerId.{}".format(plexapp.ACCOUNT.ID), self.selectedServer.uuid)

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
        if not self.selectedServer:
            return None

        transcodeMap = {
            'audio': "supportsAudioTranscoding",
            'video': "supportsVideoTranscoding",
            'photo': "supportsPhotoTranscoding"
        }
        transcodeSupport = transcodeMap[transcodeType]

        # Try to use a better transcoding server for synced or secondary servers
        if self.selectedServer.synced or self.selectedServer.isSecondary():
            if self.transcodeServer and self.transcodeServer.isReachable():
                return self.transcodeServer

            self.transcodeServer = None
            for server in self.getServers():
                if not server.synced and server.isReachable() and self.compareServers(self.transcodeServer, server) < 0:
                    if not transcodeSupport or server.transcodeSupport:
                        self.transcodeServer = server

            if self.transcodeServer:
                transcodeTypeString = transcodeType or ''
                util.LOG("Found a better {0} transcode server than {1}, using: {2}", transcodeTypeString, self.selectedServer, self.transcodeServer)
                return self.transcodeServer

        return self.selectedServer

    def startSelectedServerSearch(self, reset=False, ID=None):
        if reset:
            self.selectedServer = None
            self.transcodeServer = None
            self.channelServer = None

        ID = ID is not None and ID or plexapp.ACCOUNT.ID
        pServ = util.INTERFACE.getPreference("lastServerId.{}".format(ID), '')
        util.DEBUG_LOG("Preferred server for {0} is: {1}", ID, pServ)
        # Keep track of some information during our search

        self.searchContext = SearchContext({
            'bestServer': None,
            'preferredServer': pServ,
            'waitingForResources': plexapp.ACCOUNT.isSignedIn,
            # until a server is selected (setSelectedServer())
            'active': True
        })

        util.LOG("Starting selected server search, hoping for {0}", self.searchContext.preferredServer)
        if util.LOCAL_OVER_SECURE:
            util.WARN_LOG("Preferring local server connections over secure ones!")

    def onAccountChange(self, account, reallyChanged=False):
        # Clear any AudioPlayer data before invalidating the active server
        if reallyChanged:
            # AudioPlayer().Cleanup()
            # PhotoPlayer().Cleanup()

            util.DEBUG_LOG("Account really changed, clearing all servers")

            # Clear selected and transcode servers on user change
            self.selectedServer = None
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
            # to clear out any connections for the previous user and then start
            # our selected server search.

            self.updateFromConnectionType([], plexresource.ResourceConnection.SOURCE_MYPLEX)
            self.updateFromConnectionType([], plexresource.ResourceConnection.SOURCE_DISCOVERED)
            self.updateFromConnectionType([], plexresource.ResourceConnection.SOURCE_MANUAL)

            self.startSelectedServerSearch(True, ID=account.ID)

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
        if not self.selectedServer and self.searchContext:
            for server in self.getServers():
                if server.pendingReachabilityRequests > 0 and server.uuid == self.searchContext.preferredServer:
                    util.DEBUG_LOG(
                        'Still waiting on {0} responses from preferred server: {1}'.format(
                            server.pendingReachabilityRequests, self.searchContext.preferredServer
                        )
                    )
                    return

        if self.deferReachabilityTimer:
            self.deferReachabilityTimer.cancel()
        self.deferReachabilityTimer = None
        self.updateReachability(True, False, False)

    def periodicReachabilityCheck(self):
        """Re-test reachability on the selected server to detect network changes (e.g. WiFi -> mobile)."""
        if not plexapp.ACCOUNT.isAuthenticated or not self.selectedServer or self.selectedServer.gone:
            return

        server = self.selectedServer
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
        # Clear all manual connections on change. A selected server that only had a manual
        # connection isn't unselected meanwhile: removeServer() keeps it, offline. (This used to
        # try to put such a server back itself, reading .sources off a list - it would have
        # raised had it ever run.)
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
# TODO(schuyler): Transcode (and primary) server selection


MANAGER = PlexServerManager()
