from __future__ import absolute_import
import ast
from xml.etree import ElementTree
import six.moves.urllib.request, six.moves.urllib.parse, six.moves.urllib.error

from . import plexapp
from . import plexconnection
from . import plexserver
from . import myplexrequest
from . import callback
from . import util


RESOURCES_CACHE = "mpaResources2"         # /api/v2/resources
LEGACY_RESOURCES_CACHE = "mpaResources"   # /pms/resources, before 2026-10


class MyPlexManager(object):
    gotResources = False

    def __init__(self):
        self.gotResources = False

    def publish(self):
        util.LOG('MyPlexManager().publish() - NOT IMPLEMENTED')
        return  # TODO: ----------------------------------------------------------------------------------------------------------------------------- IMPLEMENT?
        request = myplexrequest.MyPlexRequest("/devices/" + util.INTERFACE.getGlobal("clientIdentifier"))
        context = request.createRequestContext("publish")

        addrs = util.INTERFACE.getGlobal("roDeviceInfo").getIPAddrs()

        for iface in addrs:
            request.addParam(six.moves.urllib.parse.quote("Connection[][uri]"), "http://{0):8324".format(addrs[iface]))

        util.APP.startRequest(request, context, "_method=PUT")

    def refreshResources(self, force=False):
        util.LOG('MyPlexManager().refreshResources() - Force: {}', force)
        if force:
            plexapp.SERVERMANAGER.resetLastTest()

        # v2: the older /pms/resources ignores includeIPv6 (checked 2026-10-02), so servers only
        # reachable over IPv6 away from home looked like they had no remote connection at all
        request = myplexrequest.MyPlexRequest("/api/v2/resources")
        context = request.createRequestContext("resources", callback.Callable(self.onResourcesResponse),
                                               timeout=util.PLEXTV_TIMEOUT)

        if plexapp.ACCOUNT.isSecure:
            request.addParam("includeHttps", "1")
        request.addParam("includeIPv6", "1")

        util.APP.startRequest(request, context)

    @staticmethod
    def cachedResources():
        """The last good resources answer: the v2 one, or else one the older endpoint left. v2
        answers get their own key, so an older build never reads one (it would find no
        connections in it). One saved as bytes, as every build did until 2026-10-12, sits in the
        settings as their repr - b'<?xml ...' - which no parser reads: decoded back here."""
        cached = (util.INTERFACE.getRegistry(RESOURCES_CACHE, None, "xml_cache") or
                  util.INTERFACE.getRegistry(LEGACY_RESOURCES_CACHE, None, "xml_cache"))
        if cached and cached[:2] in ("b'", 'b"'):
            try:
                cached = ast.literal_eval(cached).decode('utf-8')
            except (ValueError, SyntaxError, UnicodeDecodeError):
                return None
        return cached

    def _parsedCachedResources(self):
        """cachedResources() parsed, or None if there's none or it doesn't parse - it used to
        raise there, out of onResourcesResponse() (live 2026-10-12, plex.tv timing out)."""
        cached = self.cachedResources()
        if not cached:
            return None
        try:
            return ElementTree.fromstring(cached)
        except ElementTree.ParseError as e:
            util.WARN_LOG("Cached resources don't parse: {0}", e)
            return None

    def onResourcesResponse(self, request, response, context):
        servers = []

        response.parseResponse()

        # Save the last successful response to cache
        if response.isSuccess() and response.event:
            # the text, not bytes: a setting holds bytes as their repr (cachedResources())
            util.INTERFACE.setRegistry(RESOURCES_CACHE, response.event.text, "xml_cache")
            util.DEBUG_LOG("Saved resources response to registry")
        # Load the last successful response from cache
        else:
            data = self._parsedCachedResources()
            if data is None:
                # No answer and nothing cached that reads. Passing an empty list on would strip
                # every plex.tv connection (and its token) from the servers we already know, so
                # keep them.
                util.WARN_LOG("No plex.tv resources (status {0}) and none cached, keeping known servers",
                              response.getStatus())
                plexapp.SERVERMANAGER.resourcesUnavailable()
                return
            response.parseFakeXMLResponse(data)
            util.DEBUG_LOG("Using cached resources")

        if response.container:
            for resource in response.container:
                util.DEBUG_LOG(
                    "Parsed resource from plex.tv: type:{0} clientIdentifier:{1} name:{2} product:{3} provides:{4}".format(
                        resource.type,
                        resource.clientIdentifier,
                        resource.name.encode('utf-8'),
                        resource.product.encode('utf-8'),
                        resource.provides.encode('utf-8')
                    )
                )

                for conn in resource.connections:
                    util.DEBUG_LOG('  {0}', conn)

                if 'server' in resource.provides or resource.product == "Plex Media Server":
                    server = plexserver.createPlexServerForResource(resource)
                    util.DEBUG_LOG('  {0}', server)
                    servers.append(server)

            self.gotResources = True
        plexapp.SERVERMANAGER.updateFromConnectionType(servers, plexconnection.PlexConnection.SOURCE_MYPLEX)
        util.APP.trigger("loaded:myplex_servers", servers=servers, source="myplex")


MANAGER = MyPlexManager()
