# coding=utf-8
"""
I8 in the navigation review: a hosted view's input reaches LibraryWindow by name, not by the host
overwriting the view's callbacks. kodigui.BaseWindow.routeActionToHost() is the first line of every
hosted shell's onAction(); kodigui.MultiWindowView forwards the grid and Recommended views' five
callbacks to the host. Both hold the host through a weak reference (_hostRef), and drop a late
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
    def __init__(self, routed=True):
        self._current = None
        self.routed = routed
        self.calls = []

    def routeAction(self, action):
        self.calls.append(('action', action))
        return self.routed

    def _onFirstInit(self):
        self.calls.append(('firstInit',))

    def onReInit(self):
        self.calls.append(('reInit',))

    def onClick(self, controlID):
        self.calls.append(('click', controlID))

    def onFocus(self, controlID):
        self.calls.append(('focus', controlID))


class FakeWindowBase(object):
    """Stands in for ControlledWindow: the view's own default onAction()."""
    _hostRef = None
    hostedBy = kodigui.BaseWindow.hostedBy
    routeActionToHost = kodigui.BaseWindow.routeActionToHost

    def __init__(self):
        self.defaultActions = []

    def onAction(self, action):
        self.defaultActions.append(action)


class FakeThinView(kodigui.MultiWindowView, FakeWindowBase):
    pass


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
    def test_every_callback_goes_to_the_host(self):
        host = FakeHost()
        view = hosted(FakeThinView(), host)
        view.onFirstInit()
        view.onReInit()
        view.onClick(101)
        view.onFocus(102)
        view.onAction('a')
        self.assertEqual([('firstInit',), ('reInit',), ('click', 101), ('focus', 102), ('action', 'a')],
                         host.calls)
        self.assertEqual([], view.defaultActions)

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

    def test_librarys_grid_and_recommended_views_are_multiwindow_views(self):
        for cls in (library.PostersWindow, library.PostersSmallWindow, library.ListView16x9Window,
                    library.SquaresWindow, library.ListViewSquareWindow, library.TrackListWindow,
                    library.RecommendedWindow):
            mro = cls.__mro__
            self.assertIn(kodigui.MultiWindowView, mro, cls.__name__)
            self.assertLess(mro.index(kodigui.MultiWindowView), mro.index(kodigui.ControlledWindow),
                            '{0}: MultiWindowView must come before ControlledWindow'.format(cls.__name__))
            for name in ('onFirstInit', 'onReInit', 'onClick', 'onFocus', 'onAction'):
                self.assertIs(getattr(kodigui.MultiWindowView, name), getattr(cls, name),
                              '{0}.{1} overrides the forward'.format(cls.__name__, name))


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
