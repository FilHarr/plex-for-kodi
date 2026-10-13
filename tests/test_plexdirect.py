# coding=utf-8
"""
lib/windows/plexdirect.py - writing servers' plex.direct names to advancedsettings.xml, as
handle_plexdirect says, ported from upstream HomeWindow.checkPlexDirectHosts().

The servers are stand-ins with just the attributes the check reads; the hosts manager is a real
one over a real (temporary) advancedsettings.xml, so a write is checked in the file itself.
"""

from __future__ import absolute_import

import os
from unittest import mock

from kodienv import ENV

from lib.windows import plexdirect

from .base import KodiTestCase
from .test_advancedsettings import ADV_PATH, AdvSingletonMixin, hosts_manager, read_adv

PD_1 = "https://192-168-1-10.abc123.plex.direct:32400"
PD_2 = "https://192-168-1-11.def456.plex.direct:32400"


class FakeConnection(object):
    def __init__(self, address, resolved=True):
        self.address = address
        self.pdHostnameResolved = resolved


class FakeServer(object):
    def __init__(self, name, addresses, resolved=True, rebind=True, sourceType=None, sameNetwork=True):
        self.name = name
        self.connections = [FakeConnection(a, resolved) for a in addresses]
        self.activeConnection = None
        self.sourceType = sourceType
        self.dnsRebindingProtection = rebind
        self.sameNetwork = sameNetwork
        self.anyLANConnection = sameNetwork

    @property
    def anyPDHostNotResolvable(self):
        return any(".plex.direct:" in c.address and not c.pdHostnameResolved for c in self.connections)

    def __repr__(self):
        return self.name


class PlexDirectTest(AdvSingletonMixin, KodiTestCase):
    def setUp(self):
        AdvSingletonMixin.setUp(self)
        self.pdm = hosts_manager()
        self.posted = []
        self.dialogs = []
        self.notifications = []
        self.answers = []
        patchers = [
            mock.patch.object(plexdirect, 'pdm', self.pdm),
            mock.patch.object(plexdirect, '_declined', set()),
            mock.patch.object(plexdirect, '_promptPosted', False),
            mock.patch.object(plexdirect.plexapp, 'MANAGER', mock.Mock(gotResources=False)),
            mock.patch.object(plexdirect.plexapp, 'ACCOUNT', mock.Mock(isOffline=False)),
            mock.patch.object(plexdirect.optionsdialog, 'show', side_effect=self._show),
            mock.patch.object(plexdirect.util, 'showNotification',
                              side_effect=lambda msg, header=None, **kw: self.notifications.append(header)),
        ]
        for name, value in (('honorPlextvDnsrebind', True), ('honorPlextvPam', True), ('ignoreDockerV4', True)):
            patchers.append(mock.patch.object(plexdirect.util.addonSettings, name, value, create=True))
        for p in patchers:
            p.start()
            self.addCleanup(p.stop)
        self.setHandling('ask')

    def _show(self, header, info, *buttons, **kwargs):
        self.dialogs.append(buttons)
        return self.answers.pop(0) if self.answers else None

    def setHandling(self, value, force=False):
        ENV.settings['handle_plexdirect'] = value
        ENV.settings['force_pd_mapping'] = 'true' if force else 'false'

    def check(self, servers, source="myplex"):
        plexdirect.check(servers, source=source, post=self.posted.append)

    def runPosted(self):
        while self.posted:
            self.posted.pop(0)()

    def mapped(self):
        if not os.path.exists(os.path.join(ENV.profile_root, ADV_PATH)):
            return ""
        return read_adv()

    def test_never_does_nothing(self):
        self.setHandling('never')
        self.check([FakeServer("a", [PD_1])])
        self.assertEqual([], self.posted)
        self.assertNotIn("plex.direct", self.mapped())

    def test_always_writes_at_once_with_a_notification(self):
        self.setHandling('always')
        self.check([FakeServer("a", [PD_1, "http://192.168.1.10:32400"])])
        self.assertEqual([], self.posted)
        self.assertIn('<entry name="192-168-1-10.abc123.plex.direct">192.168.1.10</entry>', self.mapped())
        self.assertEqual(1, len(self.notifications))
        self.assertEqual([], self.dialogs)

    def test_ask_posts_the_question_and_yes_writes(self):
        self.check([FakeServer("a", [PD_1]), FakeServer("b", [PD_2])])
        self.assertEqual(1, len(self.posted))
        self.assertNotIn("plex.direct", self.mapped())

        self.answers = [0, 0]
        self.runPosted()
        self.assertIn("192-168-1-10.abc123.plex.direct", self.mapped())
        self.assertIn("192-168-1-11.def456.plex.direct", self.mapped())
        # the question, then the first-time "restart Kodi" dialog
        self.assertEqual(2, len(self.dialogs))

    def test_a_second_check_while_the_question_waits_posts_nothing_more(self):
        self.check([FakeServer("a", [PD_1])])
        self.check([FakeServer("b", [PD_2])])
        self.assertEqual(1, len(self.posted))

    def test_always_answer_switches_the_setting(self):
        self.check([FakeServer("a", [PD_1])])
        self.answers = [1, 0]
        self.runPosted()
        self.assertEqual('always', ENV.settings['handle_plexdirect'])
        self.assertIn("plex.direct", self.mapped())

    def test_never_answer_switches_the_setting_and_writes_nothing(self):
        self.check([FakeServer("a", [PD_1])])
        self.answers = [2]
        self.runPosted()
        self.assertEqual('never', ENV.settings['handle_plexdirect'])
        self.assertNotIn("plex.direct", self.mapped())
        self.assertFalse(self.pdm.differs)

    def test_dismissed_hosts_are_not_asked_about_again(self):
        servers = [FakeServer("a", [PD_1])]
        self.check(servers)
        self.runPosted()  # no answer: dismissed
        self.assertNotIn("plex.direct", self.mapped())
        self.check(servers)
        self.assertEqual([], self.posted)

    def test_a_new_host_after_a_dismissal_is_asked_about(self):
        self.check([FakeServer("a", [PD_1])])
        self.runPosted()
        self.check([FakeServer("a", [PD_1]), FakeServer("b", [PD_2])])
        self.assertEqual(1, len(self.posted))

    def test_mapped_hosts_arent_asked_about_again(self):
        self.setHandling('always')
        servers = [FakeServer("a", [PD_1])]
        self.check(servers)
        self.notifications = []
        self.check(servers)
        self.assertEqual([], self.notifications)

    def test_stored_servers_wait_for_plextv_while_online(self):
        self.setHandling('always')
        self.check([FakeServer("a", [PD_1])], source="stored")
        self.assertNotIn("plex.direct", self.mapped())

    def test_stored_servers_map_once_plextv_resources_are_in(self):
        self.setHandling('always')
        plexdirect.plexapp.MANAGER.gotResources = True
        self.check([FakeServer("a", [PD_1])], source="stored")
        self.assertIn("plex.direct", self.mapped())

    def test_stored_servers_map_while_offline(self):
        self.setHandling('always')
        plexdirect.plexapp.ACCOUNT.isOffline = True
        self.check([FakeServer("a", [PD_1])], source="stored")
        self.assertIn("plex.direct", self.mapped())

    def test_a_server_without_rebind_protection_is_skipped(self):
        self.setHandling('always')
        self.check([FakeServer("a", [PD_1], rebind=False)])
        self.assertNotIn("plex.direct", self.mapped())

    def test_unless_its_name_doesnt_resolve(self):
        self.setHandling('always')
        self.check([FakeServer("a", [PD_1], rebind=False, resolved=False)])
        self.assertIn("plex.direct", self.mapped())

    def test_force_maps_regardless(self):
        self.setHandling('always', force=True)
        self.check([FakeServer("a", [PD_1], rebind=False)], source="stored")
        self.assertIn("plex.direct", self.mapped())

    def test_docker_addresses_are_left_out(self):
        self.setHandling('always')
        self.check([FakeServer("a", ["https://172-17-0-2.abc123.plex.direct:32400"])])
        self.assertNotIn("plex.direct", self.mapped())

    def test_a_check_without_a_poster_never_asks(self):
        plexdirect.check([FakeServer("a", [PD_1])], source="myplex", post=None)
        self.assertEqual([], self.dialogs)
        self.assertNotIn("plex.direct", self.mapped())
