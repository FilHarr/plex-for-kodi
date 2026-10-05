# coding=utf-8
"""
Starting without a selected server (plan Phase 9.2): Home opens once the account's servers are
known - the last run's, or plex.tv's answer (or its failing) - and fills in as each answers; Home
says so when none of its servers is answering; and a new account starts with no libraries, Home
opening the Libraries picker until one is pinned (the user's choice, 2026-10-05: onboarding, not a
default sidebar of some server's libraries).

Importing lib.windows.* starts lib.player's monitor thread unless abort_requested is set first.
"""

from __future__ import absolute_import

from unittest import mock

from kodienv import ENV

ENV.abort_requested = True
from lib.windows import home, library, section_ids, sidebar_model  # noqa: E402
from plexnet import plexresource  # noqa: E402

from .base import KodiTestCase  # noqa: E402
from .test_server_state import ManagerTestCase, make_server, ANIMAL, OSCAR  # noqa: E402
from .test_sidebar_model import SidebarCase  # noqa: E402

MYPLEX = plexresource.ResourceConnection.SOURCE_MYPLEX


class ServersKnownTest(ManagerTestCase):
    def setUp(self):
        super(ServersKnownTest, self).setUp()
        self.manager.resourcesAnswered = self.manager.storedLoaded = False

    def test_known_once_plex_tv_answers(self):
        self.assertFalse(self.manager.serversKnown())
        with mock.patch.object(self.manager, 'saveState'), mock.patch.object(self.manager, 'updateReachability'):
            self.manager.updateFromConnectionType([self.animal], MYPLEX)
        self.assertTrue(self.manager.serversKnown())

    def test_known_when_plex_tv_fails_too(self):
        with mock.patch.object(self.manager, 'updateReachability'):
            self.manager.resourcesUnavailable()
        self.assertTrue(self.manager.serversKnown())

    def test_the_last_runs_servers_count(self):
        self.manager.storedLoaded = True
        self.assertTrue(self.manager.serversKnown())


class NewAccountTest(SidebarCase):
    def setUp(self):
        super(NewAccountTest, self).setUp()
        # never had a server selected, nothing stored
        del self.settings['lastServerId.1']
        del self.settings['sidebar.1']

    def test_a_new_account_starts_with_no_libraries(self):
        nav = sidebar_model.loadNavSettings()
        self.assertEqual([section_ids.WATCHLIST_ID], nav['entries'])
        self.assertTrue(nav[sidebar_model.ONBOARDING])
        self.assertIn('sidebar.1', self.settings)

    def test_onboarding_ends_with_a_library_pinned(self):
        nav = sidebar_model.loadNavSettings()
        self.assertFalse(sidebar_model.endOnboarding(nav))
        nav['entries'].append(ANIMAL + ':1')
        self.assertTrue(sidebar_model.endOnboarding(nav))
        self.assertNotIn(sidebar_model.ONBOARDING, nav)


class OfferOnboardingTest(KodiTestCase):
    def window(self, nav):
        win = library.LibraryWindow.__new__(library.LibraryWindow)
        win.sidebarNavSettings = lambda: nav
        win.postUI = mock.Mock()
        return win

    def test_the_picker_opens_once_a_session(self):
        win = self.window({'entries': [], sidebar_model.ONBOARDING: True})
        win.offerOnboarding()
        win.offerOnboarding()
        win.postUI.assert_called_once_with('onboarding', win.showLibraryPicker)

    def test_not_once_libraries_are_picked(self):
        win = self.window({'entries': [ANIMAL + ':1']})
        win.offerOnboarding()
        win.postUI.assert_not_called()


class NoneRespondingTest(KodiTestCase):
    """Home's "isn't responding" panel: every server it has rows from down, not just one."""

    def setUp(self):
        super(NoneRespondingTest, self).setUp()
        self.animal, self.oscar = make_server(ANIMAL, 'Animal'), make_server(OSCAR, 'Oscar')
        self.win = library.LibraryWindow.__new__(library.LibraryWindow)
        self.props = {}
        self.win.setProperty = lambda key, value: self.props.__setitem__(key, value)
        self.win.getProperty = lambda key: self.props.get(key, '')
        self.win.section = home.home_section
        self.win.contentMode = 'recommended'
        self.win.visibleHubs = []
        self.win._isHostedShell = False
        self.win.closing = False
        self.win._homeServers = lambda: [(self.animal, ['1']), (self.oscar, ['2'])]

    def test_shown_only_when_every_home_server_is_down(self):
        self.animal.offline = True
        self.assertFalse(self.win.updateServerUnavailable())
        self.oscar.offline = True
        self.assertTrue(self.win.updateServerUnavailable())
        self.assertEqual('None of your servers are responding', self.props['server.unavailable'])

    def test_try_again_retests_each_of_them(self):
        self.animal.offline = self.oscar.offline = True
        manager = mock.Mock()
        manager.retestServerNow.return_value = True
        self.win.addTicker = mock.Mock()
        with mock.patch.object(library.plexapp, 'SERVERMANAGER', manager):
            self.win.retryServerNow()
        self.assertEqual([self.animal, self.oscar], [c[0][0] for c in manager.retestServerNow.call_args_list])

    def test_a_new_account_with_no_servers_on_home_shows_nothing(self):
        self.win._homeServers = lambda: []
        self.assertFalse(self.win.updateServerUnavailable())
