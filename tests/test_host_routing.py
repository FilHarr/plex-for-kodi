# coding=utf-8
"""
I8 in the navigation review: a hosted view's input reaches LibraryWindow by name, not by the host
overwriting the view's callbacks. kodigui.BaseWindow.routeActionToHost() is the first line of every
hosted shell's onAction(); kodigui.MultiWindowView sends the grid and Recommended views' input
through the host's shared routing first, then to the view's own handlers (I4). Both hold the host through a weak reference (_hostRef), and drop a late
callback on a view the host has already swapped out (hostedBy()).

The host side (LibraryWindow.routeAction()) is covered in test_library_chain.OnActionTest.

Importing lib.windows.* starts lib.player's monitor thread unless abort_requested is set first.
"""

from __future__ import absolute_import

import gc
import inspect
import weakref

from kodienv import ENV

ENV.abort_requested = True
from lib.windows import (collection, episodes, genres, kodigui, library, person, playlist,  # noqa: E402
                         preplay, subitems, tracks, windowutils)

from .base import KodiTestCase  # noqa: E402


class FakeHost(object):
    def __init__(self, routed=True, clickRouted=False, focusRouted=False):
        self._current = None
        self.routed = routed
        self.clickRouted = clickRouted
        self.focusRouted = focusRouted
        self.calls = []

    def routeAction(self, action):
        self.calls.append(('action', action))
        return self.routed

    def routeClick(self, controlID):
        self.calls.append(('routeClick', controlID))
        return self.clickRouted

    def routeFocus(self, controlID):
        self.calls.append(('routeFocus', controlID))
        return self.focusRouted

    def _onFirstInit(self):
        self.calls.append(('firstInit',))

    def onReInit(self):
        self.calls.append(('reInit',))

    def postNav(self, name, fn, args=(), kwargs=None, stack=False):
        self.calls.append(('postNav', name, fn, args, stack))


class FakeWindowBase(object):
    """Stands in for ControlledWindow: the view's own default onAction()."""
    _hostRef = None
    started = True
    hostedBy = kodigui.BaseWindow.hostedBy
    routeActionToHost = kodigui.BaseWindow.routeActionToHost
    routeClickToHost = kodigui.BaseWindow.routeClickToHost
    ignoresInput = kodigui.BaseWindow.ignoresInput

    def __init__(self):
        self.defaultActions = []

    def onAction(self, action):
        self.defaultActions.append(action)


class FakeThinView(kodigui.MultiWindowView, FakeWindowBase):
    def __init__(self):
        FakeWindowBase.__init__(self)
        self.viewCalls = []

    def viewClick(self, controlID):
        self.viewCalls.append(('click', controlID))

    def viewFocus(self, controlID):
        self.viewCalls.append(('focus', controlID))


def hosted(view, host):
    view._hostRef = weakref.ref(host)
    host._current = view
    return view


class RouteActionToHostTest(KodiTestCase):
    def test_a_window_never_hosted_handles_its_own_actions(self):
        self.assertFalse(FakeWindowBase().routeActionToHost('a'))

    def test_the_hosts_current_view_goes_through_routeAction(self):
        host = FakeHost(routed=True)
        view = hosted(FakeWindowBase(), host)
        self.assertTrue(view.routeActionToHost('a'))
        self.assertEqual([('action', 'a')], host.calls)

    def test_an_action_the_host_hands_back_is_handled_by_the_view(self):
        host = FakeHost(routed=False)
        view = hosted(FakeWindowBase(), host)
        self.assertFalse(view.routeActionToHost('a'))

    def test_a_view_swapped_out_drops_late_actions(self):
        """Replaces clearing onAction to None on the outgoing shell."""
        host = FakeHost()
        view = hosted(FakeWindowBase(), host)
        host._current = FakeWindowBase()
        self.assertTrue(view.routeActionToHost('a'))
        self.assertEqual([], host.calls)

    def test_a_closed_host_drops_late_actions(self):
        """MultiWindow._open()'s teardown dels _current."""
        host = FakeHost()
        view = hosted(FakeWindowBase(), host)
        del host._current
        self.assertTrue(view.routeActionToHost('a'))

    def test_the_view_does_not_keep_the_host_alive(self):
        host = FakeHost()
        view = hosted(FakeWindowBase(), host)
        del host
        gc.collect()
        self.assertIsNone(view.hostedBy())
        self.assertTrue(view.routeActionToHost('a'))


class MultiWindowViewTest(KodiTestCase):
    def test_input_goes_to_the_host_first_then_to_the_views_own_handlers(self):
        host = FakeHost()
        view = hosted(FakeThinView(), host)
        view.onFirstInit()
        view.onReInit()
        view.onClick(101)
        view.onFocus(102)
        view.onAction('a')
        self.assertEqual([('firstInit',), ('reInit',), ('routeClick', 101), ('routeFocus', 102),
                          ('action', 'a')], host.calls)
        self.assertEqual([('click', 101), ('focus', 102)], view.viewCalls)
        self.assertEqual([], view.defaultActions)

    def test_a_click_the_host_used_never_reaches_the_view(self):
        """The sidebar's clicks (LibraryWindow.routeClick())."""
        view = hosted(FakeThinView(), FakeHost(clickRouted=True))
        view.onClick(9000)
        self.assertEqual([], view.viewCalls)

    def test_a_focus_event_the_host_dropped_never_reaches_the_view(self):
        """The go_root wait (LibraryWindow.routeFocus())."""
        view = hosted(FakeThinView(), FakeHost(focusRouted=True))
        view.onFocus(9001)
        self.assertEqual([], view.viewCalls)

    def test_an_action_the_host_hands_back_reaches_the_views_default(self):
        """Replaces the host's forward through the saved _currentOnAction."""
        host = FakeHost(routed=False)
        view = hosted(FakeThinView(), host)
        view.onAction('a')
        self.assertEqual(['a'], view.defaultActions)

    def test_a_view_swapped_out_forwards_nothing(self):
        host = FakeHost()
        view = hosted(FakeThinView(), host)
        host._current = FakeThinView()
        view.onFocus(102)
        view.onClick(101)
        view.onAction('a')
        self.assertEqual([], host.calls)
        self.assertEqual([], view.defaultActions)
        self.assertEqual([], view.viewCalls)

    def test_librarys_grid_and_recommended_views_are_multiwindow_views(self):
        for cls in (library.PostersWindow, library.PostersSmallWindow,
                    library.SquaresWindow, library.ListViewSquareWindow, library.TrackListWindow,
                    library.RecommendedWindow):
            mro = cls.__mro__
            self.assertIn(kodigui.MultiWindowView, mro, cls.__name__)
            self.assertLess(mro.index(kodigui.MultiWindowView), mro.index(kodigui.ControlledWindow),
                            '{0}: MultiWindowView must come before ControlledWindow'.format(cls.__name__))
            for name in ('onFirstInit', 'onReInit', 'onClick', 'onFocus', 'onAction'):
                # unwrap: onAction comes wrapped, to skip builtins (kodigui._skippingBuiltins())
                self.assertIs(getattr(kodigui.MultiWindowView, name), inspect.unwrap(getattr(cls, name)),
                              '{0}.{1} overrides the forward'.format(cls.__name__, name))
            for name in ('viewAction', 'viewClick', 'viewFocus'):
                self.assertIsNot(getattr(kodigui.MultiWindowView, name), getattr(cls, name),
                                 '{0} has no {1} of its own'.format(cls.__name__, name))


class ViewHandlersTest(KodiTestCase):
    """I4: each of LibraryWindow's views names its own handlers on the host - the grid views the
    grid's (library_grid.py), Recommended the hub engine's (library_hubs.py)."""

    class Host(object):
        def __init__(self):
            self._current = None
            self.calls = []

        def __getattr__(self, name):
            if name.startswith(('grid', 'hub')):
                return lambda *args: self.calls.append((name,) + args) or 'result'
            raise AttributeError(name)

    def _view(self, cls):
        host = self.Host()
        view = object.__new__(cls)
        view._hostRef = weakref.ref(host)
        host._current = view
        return view, host

    def test_the_grid_views(self):
        for cls in (library.PostersWindow, library.PostersSmallWindow,
                    library.SquaresWindow, library.ListViewSquareWindow, library.TrackListWindow):
            view, host = self._view(cls)
            self.assertEqual('result', view.viewAction('a'))
            view.viewClick(101)
            view.viewFocus(151)
            self.assertEqual('result', view.handleBack())
            self.assertEqual([('gridAction', 'a'), ('gridClick', 101), ('gridFocus', 151), ('gridBack',)],
                             host.calls, cls.__name__)

    def test_the_recommended_view(self):
        view, host = self._view(library.RecommendedWindow)
        self.assertEqual('result', view.viewAction('a'))
        view.viewClick(400)
        view.viewFocus(401)
        self.assertEqual([('hubAction', 'a'), ('hubClick', 400), ('hubFocus', 401)], host.calls)

    def test_recommended_has_no_back_step_before_the_chain_pops(self):
        """Its row's Back to item 0 is in hubAction(), after the chain: a Recommended view reached
        mid-chain goes back up the chain first, as before I4."""
        view, host = self._view(library.RecommendedWindow)
        self.assertFalse(view.handleBack())
        self.assertEqual([], host.calls)


class HostedShellsRouteFirstTest(KodiTestCase):
    """Every class LibraryWindow can host as a real shell (everything opened through
    openWindow()/swapTo()) must hand its actions to the host before doing anything else - a shell
    that forgot would lose the sidebar popups, Back through the chain and the Home button."""

    SHELLS = (preplay.PrePlayWindow, preplay.PrePlayWindowWL, episodes.EpisodesWindow,
              subitems.ShowWindow, subitems.ArtistWindow, tracks.AlbumWindow, playlist.PlaylistWindow,
              person.ActorWindow, person.DirectorWindow, collection.CollectionWindow,
              collection.SubDirWindow, genres.GenreBrowserWindow)

    def test_onAction_starts_by_routing_to_the_host(self):
        for cls in self.SHELLS:
            self.assertTrue(library.LibraryWindow._isRealShell(cls), cls.__name__)
            body = inspect.getsource(cls.onAction).split('\n')[1:]
            code = [l.strip() for l in body if l.strip() and not l.strip().startswith('#')]
            self.assertEqual('if self.routeActionToHost(action):', code[0], cls.__name__)
            self.assertEqual('return', code[1], cls.__name__)

    def test_focus_starts_by_dropping_stale_calls(self):
        """The host frees a swapped-out shell's controls, but Kodi can still deliver its queued
        onFocus (kodigui.BaseWindow.ignoresInput())."""
        for cls in self.SHELLS:
            body = inspect.getsource(cls.onFocus).split('\n')[1:]
            code = [l.strip() for l in body if l.strip() and not l.strip().startswith('#')]
            self.assertEqual('if self.ignoresInput():', code[0], cls.__name__)
            self.assertEqual('return', code[1], cls.__name__)

    def test_clicks_start_with_the_host(self):
        """routeClickToHost() drops stale clicks as ignoresInput() does, and hands the sidebar's
        clicks to the host (I3 in the navigation review)."""
        for cls in self.SHELLS:
            body = inspect.getsource(cls.onClick).split('\n')[1:]
            code = [l.strip() for l in body if l.strip() and not l.strip().startswith('#')]
            self.assertEqual('if self.routeClickToHost(controlID):', code[0], cls.__name__)
            self.assertEqual('return', code[1], cls.__name__)


class RouteClickToHostTest(KodiTestCase):
    class Host(object):
        def __init__(self, handles):
            self.handles = handles
            self.clicks = []

        def routeClick(self, controlID):
            self.clicks.append(controlID)
            return self.handles

    def _window(self, host=None, started=True):
        window = kodigui.BaseWindow.__new__(kodigui.BaseWindow)
        window._hostRef = None
        window.started = started
        if host is not None:
            window._hostRef = weakref.ref(host)
            host._current = window
        return window

    def test_an_unhosted_window_handles_its_own_clicks(self):
        self.assertFalse(self._window().routeClickToHost(9001))

    def test_the_host_sees_a_hosted_click_first(self):
        host = self.Host(handles=True)
        self.assertTrue(self._window(host).routeClickToHost(250))
        self.assertEqual([250], host.clicks)

    def test_a_click_the_host_passes_on_comes_back(self):
        host = self.Host(handles=False)
        self.assertFalse(self._window(host).routeClickToHost(101))

    def test_a_click_before_the_window_started_is_dropped(self):
        host = self.Host(handles=False)
        self.assertTrue(self._window(host, started=False).routeClickToHost(101))
        self.assertEqual([], host.clicks)


class LibraryRouteClickTest(KodiTestCase):
    """The sidebar's clicks, written once on the host for its own views and hosted screens."""

    class Screen(object):
        def __init__(self):
            self.calls = []

        def sectionClicked(self):
            self.calls.append('sectionClicked')

        def setBoolProperty(self, key, value):
            self.calls.append((key, value))

        def setFocusId(self, controlID):
            self.calls.append(('focus', controlID))

    class Host(object):
        routeClick = library.LibraryWindow.routeClick
        SECTION_LIST_ID = library.LibraryWindow.SECTION_LIST_ID
        USER_LIST_ID = library.LibraryWindow.USER_LIST_ID
        SERVER_LIST_ID = library.LibraryWindow.SERVER_LIST_ID
        USER_BUTTON_ID = library.LibraryWindow.USER_BUTTON_ID
        SERVER_RETRY_BUTTON_ID = library.LibraryWindow.SERVER_RETRY_BUTTON_ID

        def __init__(self, screen, moving=None):
            self.screen = screen
            self.movingSection = moving
            self.calls = []

        def _sidebarTarget(self):
            return self.screen

        def doUserOption(self, target=None):
            self.calls.append(('doUserOption', target))

        def selectServer(self):
            pass

        def postNav(self, name, fn, **kwargs):
            self.calls.append(('postNav', name))

    def test_a_section_click_runs_the_showing_screens_own_handler(self):
        screen = self.Screen()
        self.assertTrue(self.Host(screen).routeClick(library.LibraryWindow.SECTION_LIST_ID))
        self.assertEqual(['sectionClicked'], screen.calls)

    def test_no_section_opens_while_one_is_being_moved(self):
        screen = self.Screen()
        self.assertTrue(self.Host(screen, moving=object()).routeClick(library.LibraryWindow.SECTION_LIST_ID))
        self.assertEqual([], screen.calls)

    def test_the_user_dropdown_acts_on_the_showing_screen(self):
        screen = self.Screen()
        host = self.Host(screen)
        self.assertTrue(host.routeClick(library.LibraryWindow.USER_LIST_ID))
        self.assertEqual([('doUserOption', screen)], host.calls)
        self.assertEqual([('show.options', False), ('focus', library.LibraryWindow.USER_BUTTON_ID)], screen.calls)

    def test_the_server_dropdown_posts_the_switch(self):
        screen = self.Screen()
        host = self.Host(screen)
        self.assertTrue(host.routeClick(library.LibraryWindow.SERVER_LIST_ID))
        self.assertEqual([('postNav', 'selectServer')], host.calls)
        self.assertEqual([('show.servers', False)], screen.calls)

    def test_other_clicks_go_back_to_the_screen(self):
        self.assertFalse(self.Host(self.Screen()).routeClick(101))


class IgnoresInputTest(KodiTestCase):
    class Host(object):
        pass

    def _window(self):
        window = kodigui.BaseWindow.__new__(kodigui.BaseWindow)
        window.started = True
        return window

    def test_a_window_never_hosted_is_never_stale(self):
        self.assertFalse(self._window().ignoresInput())

    def test_the_hosts_current_window_is_live(self):
        host, window = self.Host(), self._window()
        host._current = window
        window._hostRef = weakref.ref(host)
        self.assertFalse(window.ignoresInput())

    def test_a_swapped_out_window_is_stale(self):
        host, window = self.Host(), self._window()
        host._current = self._window()
        window._hostRef = weakref.ref(host)
        self.assertTrue(window.ignoresInput())

    def test_a_current_window_that_has_not_started_init_ignores_input(self):
        """The host's shared lists still wrap the previous view's freed controls until then."""
        host, window = self.Host(), self._window()
        host._current = window
        window._hostRef = weakref.ref(host)
        window.started = False
        self.assertTrue(window.ignoresInput())


class EarlyInputTest(KodiTestCase):
    """Input on a view that hasn't started its first init: focus, clicks and most actions are
    dropped; Back is posted to run once the view is ready."""

    def test_focus_click_and_moves_are_dropped(self):
        host = FakeHost()
        view = hosted(FakeThinView(), host)
        view.started = False
        view.onFocus(9000)
        view.onClick(9000)
        view.onAction('up')
        self.assertEqual([], host.calls)
        self.assertEqual([], view.defaultActions)

    def test_back_is_posted_for_when_the_view_is_ready(self):
        host = FakeHost()
        view = hosted(FakeThinView(), host)
        view.started = False
        back = library.xbmcgui.ACTION_NAV_BACK
        view.onAction(back)
        self.assertEqual(1, len(host.calls))
        kind, _name, fn, args, stack = host.calls[0]
        self.assertEqual(('postNav', view.onAction, (back,), True), (kind, fn, args, stack))
        view.started = True
        fn(*args)
        self.assertEqual(('action', back), host.calls[-1])


class ChainHostIsWeakTest(KodiTestCase):
    class Shell(windowutils.UtilMixin):
        pass

    class Host(object):
        _allClosed = False

    def test_chain_host_round_trips_and_clears(self):
        shell, host = self.Shell(), self.Host()
        shell._chainHost = host
        self.assertIs(host, shell._chainHost)
        self.assertIs(host, shell._liveChainHost())
        shell._chainHost = None
        self.assertIsNone(shell._chainHost)

    def test_the_shell_does_not_keep_the_host_alive(self):
        shell, host = self.Shell(), self.Host()
        shell._chainHost = host
        del host
        gc.collect()
        self.assertIsNone(shell._chainHost)
        self.assertIsNone(shell._liveChainHost())

    def test_a_self_hosting_window_makes_no_cycle(self):
        """LibraryWindow points _chainHost at itself."""
        shell = self.Shell()
        shell._chainHost = shell
        ref = weakref.ref(shell)
        del shell
        self.assertIsNone(ref(), 'freed by refcounting alone, no gc.collect() needed')
