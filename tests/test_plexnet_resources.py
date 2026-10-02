# coding=utf-8
"""
The server list from plex.tv, and IPv6.

The addon asked the older /pms/resources endpoint, which ignores includeIPv6 (checked live,
2026-10-02): a server whose only way in from outside is IPv6 (the user's "Oscar") looked as if it
had no remote connection at all. It now asks /api/v2/resources, whose servers carry the same
attributes but nest their connections (<resource><connections><connection>) where the older answer
listed them directly (<Device><Connection>). Both shapes still parse - a cached answer from before
the switch is the older one.

Also: an IPv6 address written into a URL by hand needs brackets, and a device without IPv6 fails
those connections at once, which counts as a definite answer (not retried).
"""

from __future__ import absolute_import

import errno
import socket
from xml.etree import ElementTree

from kodienv import ENV

ENV.abort_requested = True
import urllib3  # noqa: E402
from plexnet import asyncadapter, myplexmanager, plexapp, plexobjects, util as pnUtil  # noqa: E402

from .base import KodiTestCase, ensure_plex_interface  # noqa: E402

try:
    from unittest import mock
except ImportError:
    import mock

OWN = "aaaa1111bbbb2222cccc3333dddd4444eeee5555"
SHARED = "ffff6666aaaa7777bbbb8888cccc9999dddd0000"
V6 = "2a10:d585:3de7:daf7:51cf:5671:851f:4e6e"
V6_HOST = V6.replace(":", "-")

SERVERS = [
    # (clientIdentifier, name, owned, sourceTitle, [(address, port, uri, local, IPv6)])
    (OWN, "Oscar", "1", "", [
        ("192.168.1.69", "32400", "https://192-168-1-69.hash.plex.direct:32400", "1", "0"),
        (V6, "32400", "https://{0}.hash.plex.direct:32400".format(V6_HOST), "0", "1"),
    ]),
    (SHARED, "Friend", "0", "A Friend", [
        ("203.0.113.9", "32400", "https://203-0-113-9.hash2.plex.direct:32400", "0", "0"),
    ]),
]


def v2_answer():
    resources = []
    for cid, name, owned, source, conns in SERVERS:
        connections = "".join(
            '<connection protocol="https" address="{0}" port="{1}" uri="{2}" local="{3}" relay="0" IPv6="{4}"/>'
            .format(*c) for c in conns)
        resources.append(
            '<resource name="{1}" product="Plex Media Server" productVersion="1.43.3" platform="Windows" '
            'clientIdentifier="{0}" provides="server" owned="{2}" sourceTitle="{3}" accessToken="tok" '
            'httpsRequired="0" synced="0" relay="0" dnsRebindingProtection="0" publicAddressMatches="1" '
            'presence="1" lastSeenAt="2026-10-02T08:59:05Z"><connections>{4}</connections></resource>'
            .format(cid, name, owned, source, connections))
    return "<resources>{0}</resources>".format("".join(resources))


def legacy_answer():
    devices = []
    for cid, name, owned, source, conns in SERVERS:
        if cid == OWN:
            conns = conns[:1]  # the older endpoint leaves the IPv6 connection out
        connections = "".join('<Connection protocol="https" address="{0}" port="{1}" uri="{2}" local="{3}"/>'
                              .format(*c[:4]) for c in conns)
        source_attr = ' sourceTitle="{0}"'.format(source) if source else ''
        devices.append(
            '<Device name="{1}" product="Plex Media Server" productVersion="1.43.3" platform="Windows" '
            'clientIdentifier="{0}" provides="server" owned="{2}"{3} accessToken="tok" httpsRequired="0" '
            'synced="0" presence="1" lastSeenAt="1790931545">{4}</Device>'
            .format(cid, name, owned, source_attr, connections))
    return '<MediaContainer size="{0}">{1}</MediaContainer>'.format(len(devices), "".join(devices))


class ResourcesTest(KodiTestCase):
    def setUp(self):
        KodiTestCase.setUp(self)
        ensure_plex_interface()
        # building a connection would otherwise ping it and look its name up
        for patcher in (mock.patch.object(pnUtil, "CHECK_LOCAL", False),
                        mock.patch.object(pnUtil, "NO_HOST_CHECK", True)):
            patcher.start()
            self.addCleanup(patcher.stop)

    def servers(self, xml):
        container = plexobjects.PlexServerContainer(ElementTree.fromstring(xml), initpath="/api/v2/resources",
                                                    address="/api/v2/resources")
        return {s.uuid: s for s in container}

    def test_the_v2_answer_brings_the_ipv6_connection(self):
        oscar = self.servers(v2_answer())[OWN]
        self.assertIn("https://{0}.hash.plex.direct:32400".format(V6_HOST), [c.address for c in oscar.connections])
        self.assertEqual(2, len(oscar.connections))

    def test_both_shapes_give_the_same_servers(self):
        new, old = self.servers(v2_answer()), self.servers(legacy_answer())
        self.assertEqual(set(old), set(new))
        for uuid in old:
            with self.subTest(server=old[uuid].name):
                for attr in ("name", "owned", "owner", "synced"):
                    self.assertEqual(getattr(old[uuid], attr), getattr(new[uuid], attr), attr)
                self.assertTrue(set(c.address for c in old[uuid].connections) <=
                                set(c.address for c in new[uuid].connections))

    def test_your_own_server_has_no_owner_in_either_shape(self):
        # v2 sends sourceTitle="" where the older answer left it out; owner takes part in __eq__
        self.assertIsNone(self.servers(v2_answer())[OWN].owner)
        self.assertIsNone(self.servers(legacy_answer())[OWN].owner)
        self.assertEqual("A Friend", self.servers(v2_answer())[SHARED].owner)

    def test_the_insecure_variant_of_an_ipv6_connection_is_a_valid_url(self):
        xml = v2_answer().replace('httpsRequired="0"', 'httpsRequired="1"', 1)
        addresses = [c.address for c in self.servers(xml)[OWN].connections]
        self.assertIn("http://[{0}]:32400".format(V6), addresses)


class HostPortTest(KodiTestCase):
    def test_ipv4_and_names_are_left_alone(self):
        self.assertEqual("192.168.1.69:32400", pnUtil.hostPort("192.168.1.69", 32400))
        self.assertEqual("plex.example:443", pnUtil.hostPort("plex.example", "443"))

    def test_ipv6_goes_in_brackets_once(self):
        self.assertEqual("[{0}]:32400".format(V6), pnUtil.hostPort(V6, 32400))
        self.assertEqual("[::1]:32400", pnUtil.hostPort("[::1]", 32400))


class ResourcesRequestTest(KodiTestCase):
    def setUp(self):
        KodiTestCase.setUp(self)
        ensure_plex_interface()

    def test_the_request_asks_v2_for_ipv6(self):
        account = mock.Mock(isSecure=True, authToken="tok")
        servers = mock.Mock()
        with mock.patch.object(plexapp, "ACCOUNT", account), mock.patch.object(plexapp, "SERVERMANAGER", servers), \
                mock.patch.object(pnUtil.APP, "startRequest") as start:
            myplexmanager.MyPlexManager().refreshResources()
        url = start.call_args[0][0].url
        self.assertIn("/api/v2/resources", url)
        self.assertIn("includeIPv6=1", url)
        self.assertIn("includeHttps=1", url)

    def registry(self, values):
        return lambda reg, default=None, sec=None: values.get(reg, default)

    def test_the_cache_prefers_the_v2_answer(self):
        with mock.patch.object(pnUtil.INTERFACE, "getRegistry",
                               side_effect=self.registry({"mpaResources2": "new", "mpaResources": "old"})):
            self.assertEqual("new", myplexmanager.MyPlexManager.cachedResources())

    def test_an_older_cache_still_serves_until_v2_answers(self):
        with mock.patch.object(pnUtil.INTERFACE, "getRegistry",
                               side_effect=self.registry({"mpaResources": "old"})):
            self.assertEqual("old", myplexmanager.MyPlexManager.cachedResources())


class NoIPv6HereTest(KodiTestCase):
    def test_a_device_without_ipv6_fails_definitely(self):
        for code in (errno.EADDRNOTAVAIL, errno.EAFNOSUPPORT, errno.ENETUNREACH, 10049, 10047):
            with self.subTest(errno=code):
                error = urllib3.exceptions.ProtocolError("Connection aborted.", OSError(code, "no IPv6"))
                self.assertTrue(asyncadapter.isDefinitiveConnectFailure(error))

    def test_a_plex_direct_ipv6_name_resolves_to_its_address(self):
        family, _, _, _, address = socket.getaddrinfo("{0}.hash.plex.direct".format(V6_HOST), 32400)[0]
        self.assertEqual(socket.AF_INET6, family)
        self.assertEqual((V6, 32400), address)
