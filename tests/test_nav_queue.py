# coding=utf-8
"""
S1 in the navigation review: navigation requests (section opens, tab switches, Back, server
changes, go Home) are posted to the host (kodigui.MultiWindow.postNav()) and run on the main thread
from the current view's wait loop (ControlledBase.wait() -> runPendingNav()), instead of each
starting a threading.Timer that ran the swap on its own thread.

Importing lib.windows.* starts lib.player's monitor thread unless abort_requested is set first.
"""

from __future__ import absolute_import

import threading
import weakref

from kodienv import ENV

ENV.abort_requested = True
from lib import util  # noqa: E402
from lib.windows import kodigui  # noqa: E402

from .base import KodiTestCase  # noqa: E402

try:
    from unittest import mock
except ImportError:
    import mock


class Host(object):
    postNav = kodigui.MultiWindow.postNav
    runPendingNav = kodigui.MultiWindow.runPendingNav
    navWaitInterval = kodigui.MultiWindow.navWaitInterval
    postUI = kodigui.MultiWindow.postUI
    _runPendingUI = kodigui.MultiWindow._runPendingUI
    NAV_DEFER_SECONDS = 0.0
    NAV_INIT_HOLD_MAX_SECONDS = 3.0

    def __init__(self, delay=0.0):
        self.NAV_DEFER_SECONDS = delay
        self._navLock = threading.Lock()
        self._navPending = []
        self._uiPending = []
        self._allClosed = False
        self._current = None
        self.ran = []

    def record(self, name):
        return lambda *a, **k: self.ran.append((name, a, k))


class View(object):
    def __init__(self, ready=True):
        self.finishedInit = ready


class Clock(object):
    """Stands in for kodigui's time module."""
    def __init__(self, now=1000.0):
        self.now = now

    def time(self):
        return self.now


class _ClockCase(KodiTestCase):
    def setUp(self):
        super(_ClockCase, self).setUp()
        self._time = kodigui.time
        self.clock = Clock()
        kodigui.time = self.clock

    def tearDown(self):
        kodigui.time = self._time
        super(_ClockCase, self).tearDown()


class PostNavTest(_ClockCase):
    def test_a_new_request_replaces_pending_ones(self):
        host = Host()
        host.postNav('openSection', host.record('a'))
        host.postNav('switchTab', host.record('b'))
        self.assertEqual(['switchTab'], [r[0] for r in host._navPending])

    def test_stacked_requests_queue_behind_each_other(self):
        host = Host()
        host.postNav('popBack', host.record('back1'), stack=True)
        host.postNav('popBack', host.record('back2'), stack=True)
        view = View()
        host.runPendingNav(view)
        host.runPendingNav(view)
        self.assertEqual(['back1', 'back2'], [r[0] for r in host.ran])

    def test_one_request_per_run(self):
        """The next one waits for the next wait-loop tick - by then usually on the new view."""
        host = Host()
        host.postNav('popBack', host.record('back1'), stack=True)
        host.postNav('popBack', host.record('back2'), stack=True)
        host.runPendingNav(View())
        self.assertEqual(['back1'], [r[0] for r in host.ran])

    def test_args_and_kwargs_reach_the_call(self):
        host = Host()
        host.postNav('openSection', host.record('open'), args=('s',), kwargs={'force': True})
        host.runPendingNav(View())
        self.assertEqual([('open', ('s',), {'force': True})], host.ran)


class RunPendingNavTest(_ClockCase):
    def test_waits_until_due(self):
        host = Host(delay=0.15)
        host.postNav('openSection', host.record('open'))
        self.clock.now += 0.1
        host.runPendingNav(View())
        self.assertEqual([], host.ran)
        self.clock.now += 0.1
        host.runPendingNav(View())
        self.assertEqual(1, len(host.ran))

    def test_holds_while_the_view_is_still_opening(self):
        host = Host()
        host.postNav('popBack', host.record('back'), stack=True)
        host.runPendingNav(View(ready=False))
        self.assertEqual([], host.ran)
        host.runPendingNav(View(ready=True))
        self.assertEqual(1, len(host.ran))

    def test_runs_anyway_once_the_hold_runs_out(self):
        """A view whose onFirstInit() raised never sets finishedInit."""
        host = Host()
        host.postNav('popBack', host.record('back'), stack=True)
        self.clock.now += host.NAV_INIT_HOLD_MAX_SECONDS + 0.1
        host.runPendingNav(View(ready=False))
        self.assertEqual(1, len(host.ran))

    def test_a_closed_host_runs_nothing(self):
        host = Host()
        host.postNav('openSection', host.record('open'))
        host._allClosed = True
        host.runPendingNav(View())
        self.assertEqual([], host.ran)

    def test_an_error_is_logged_and_the_request_dropped(self):
        host = Host()

        def boom():
            raise RuntimeError('swap failed')
        host.postNav('openSection', boom)
        errors = []
        original = util.ERROR
        util.ERROR = lambda *a, **k: errors.append(True)
        try:
            host.runPendingNav(View())
        finally:
            util.ERROR = original
        self.assertEqual([True], errors)
        self.assertEqual([], host._navPending)


class PostUITest(_ClockCase):
    """UI updates from other threads (postUI()): all run, in order, before navigation."""

    def test_every_update_runs_in_order(self):
        host = Host()
        host.postUI('a', host.record('a'))
        host.postUI('b', host.record('b'), kwargs={'server': 's'})
        host.runPendingNav(View())
        self.assertEqual([('a', (), {}), ('b', (), {'server': 's'})], host.ran)

    def test_navigation_never_replaces_an_update(self):
        host = Host()
        host.postUI('update', host.record('update'))
        host.postNav('openSection', host.record('open'))
        host.runPendingNav(View())
        self.assertEqual(['update', 'open'], [r[0] for r in host.ran])

    def test_held_while_the_view_is_still_opening(self):
        host = Host()
        host.postUI('update', host.record('update'))
        host.runPendingNav(View(ready=False))
        self.assertEqual([], host.ran)
        self.clock.now += host.NAV_INIT_HOLD_MAX_SECONDS + 0.1
        host.runPendingNav(View(ready=False))
        self.assertEqual(1, len(host.ran))

    def test_an_update_that_starts_a_swap_leaves_navigation_for_the_new_view(self):
        host = Host()
        view = View()
        view._closing = False

        def swap():
            view._closing = True
        host.postUI('serverRefresh', swap)
        host.postNav('popBack', host.record('back'), stack=True)
        host.runPendingNav(view)
        self.assertEqual([], host.ran)
        self.assertEqual(1, len(host._navPending))

    def test_is_due_at_once(self):
        host = Host(delay=0.15)
        host.postUI('update', host.record('update'))
        self.assertEqual(0.02, host.navWaitInterval())


class NavWaitIntervalTest(_ClockCase):
    def test_nothing_pending_keeps_the_usual_interval(self):
        self.assertIsNone(Host().navWaitInterval())

    def test_waits_only_until_the_next_request_is_due(self):
        host = Host(delay=0.15)
        host.postNav('openSection', host.record('open'))
        self.clock.now += 0.1
        self.assertAlmostEqual(0.05, host.navWaitInterval())


class FakeMonitor(object):
    wait_interval = 0.1

    def __init__(self, view, ticks):
        self.view = view
        self.ticks = ticks
        self.intervals = []

    def waitFor(self, interval=None):
        self.intervals.append(interval)
        if len(self.intervals) >= self.ticks:
            self.view._closing = True
        return False


class WaitLoopTest(KodiTestCase):
    def setUp(self):
        super(WaitLoopTest, self).setUp()
        self._monitor = kodigui.MONITOR

    def tearDown(self):
        kodigui.MONITOR = self._monitor
        super(WaitLoopTest, self).tearDown()

    def _view(self):
        view = kodigui.ControlledWindow.__new__(kodigui.ControlledWindow)
        view._closing = False
        view.finishedInit = True
        return view

    def test_a_hosted_views_wait_loop_runs_the_hosts_requests(self):
        host = Host()
        view = self._view()
        view._hostRef = weakref.ref(host)
        host._current = view
        host.postNav('openSection', host.record('open'))
        kodigui.MONITOR = FakeMonitor(view, ticks=2)

        view.wait()

        self.assertEqual(1, len(host.ran))

    def test_a_view_that_is_not_hosted_just_waits(self):
        # in short slices: Kodi only runs queued callbacks between them (WAIT_SLICE_SECONDS)
        view = self._view()
        kodigui.MONITOR = FakeMonitor(view, ticks=2)
        view.wait()
        self.assertEqual([kodigui.WAIT_SLICE_SECONDS] * 2, kodigui.MONITOR.intervals)

    def test_a_pending_request_can_shorten_the_slice_but_never_lengthen_it(self):
        host = Host()
        view = self._view()
        view._hostRef = weakref.ref(host)
        host._current = view
        host.navWaitInterval = lambda: 0.1
        kodigui.MONITOR = FakeMonitor(view, ticks=1)
        view.wait()
        self.assertEqual([kodigui.WAIT_SLICE_SECONDS], kodigui.MONITOR.intervals)


class FakeEmitter(object):
    def __init__(self):
        self.handlers = {}

    def on(self, signal, handler):
        self.handlers.setdefault(signal, []).append(handler)

    def off(self, signal, handler):
        self.handlers.get(signal, []).remove(handler)

    def trigger(self, signal, **kwargs):
        for handler in list(self.handlers.get(signal, [])):
            handler(**kwargs)


class ServerSignalsTest(KodiTestCase):
    """LibraryWindow.hookSignals(): plexnet raises these on its own threads, and every handler
    touches controls, so each only posts its work (live-caught as a native crash in a server
    switch: 'reachable:server' updated the server list from plexnet's reachability timer)."""

    def test_handlers_post_instead_of_running_and_unhook_cleanly(self):
        from lib.windows import library
        manager, app, monitor = FakeEmitter(), FakeEmitter(), FakeEmitter()
        cron = mock.Mock()
        originals = library.plexapp.SERVERMANAGER, library.plexapp.util.APP, util.MONITOR, util.CRON
        library.plexapp.SERVERMANAGER, library.plexapp.util.APP, util.MONITOR, util.CRON = manager, app, monitor, cron
        try:
            host = Host()
            calls = []
            for name in ('displayServerAndUser', 'onServerReachable',
                         'onServerSuspect', 'onServerRecovered', 'onServerOffline',
                         'onServerOnline', 'onServerGone', '_onSleep', '_onWake',
                         '_onUpdateSourceChanged'):
                setattr(host, name, (lambda n: lambda **kw: calls.append((n, kw)))(name))
            host._postedHandler = library.LibraryWindow._postedHandler.__get__(host)
            library.LibraryWindow.hookSignals(host)

            manager.trigger('reachable:server', server='oscar')
            manager.trigger('suspect:server', server='animal')
            manager.trigger('recovered:server', server='animal')
            manager.trigger('offline:server', server='animal')
            manager.trigger('online:server', server='animal')
            manager.trigger('gone:server', server='oscar')
            self.assertEqual([], calls, 'nothing may run on the signalling thread')
            self.assertEqual(['displayServerAndUser', 'onServerReachable',
                              'onServerSuspect', 'onServerRecovered',
                              'onServerOffline', 'onServerOnline', 'onServerGone'],
                             [u[0] for u in host._uiPending])

            host.runPendingNav(View())
            self.assertEqual([('displayServerAndUser', {'server': 'oscar'}),
                              ('onServerReachable', {'server': 'oscar'}),
                              ('onServerSuspect', {'server': 'animal'}),
                              ('onServerRecovered', {'server': 'animal'}),
                              ('onServerOffline', {'server': 'animal'}),
                              ('onServerOnline', {'server': 'animal'}),
                              ('onServerGone', {'server': 'oscar'})], calls)

            # sleep and wake: pausing runs in place (it only sets flags), and waking threads its own
            # wait before it posts the refresh; the screensaver or a blanked display ending posts a
            # refresh of the rows in place
            monitor.trigger('system.sleep')
            monitor.trigger('system.wakeup')
            self.assertEqual(['_onSleep', '_onWake'], [c[0] for c in calls[-2:]])
            self.assertEqual(['dpms.deactivated', 'screensaver.deactivated', 'system.sleep', 'system.wakeup'],
                             sorted(monitor.handlers))
            cron.registerReceiver.assert_called_once_with(host)

            library.LibraryWindow.unhookSignals(host)
            self.assertEqual([], [h for hs in manager.handlers.values() for h in hs])
            self.assertEqual([], [h for hs in app.handlers.values() for h in hs])
            self.assertEqual([], [h for hs in monitor.handlers.values() for h in hs])
            cron.cancelReceiver.assert_called_once_with(host)
        finally:
            library.plexapp.SERVERMANAGER, library.plexapp.util.APP, util.MONITOR, util.CRON = originals


class OpenWindowTest(KodiTestCase):
    """I2 in the navigation review: an item open (UtilMixin.openWindow()) is posted to the chain's
    host like every other swap, not run inside the click."""

    def _shell(self, host):
        from lib.windows import windowutils
        shell = windowutils.UtilMixin()
        shell._chainHost = host
        return shell

    def test_posts_the_swap_to_the_host(self):
        host = Host()
        swaps = []
        host.swapTo = lambda cls, **kw: swaps.append((cls, kw))
        self._shell(host).openWindow(View, video='v')
        self.assertEqual([], swaps, 'the swap may not run inside the click')
        host.runPendingNav(View())
        self.assertEqual([(View, {'video': 'v'})], swaps)

    def test_a_double_click_opens_once(self):
        host = Host()
        swaps = []
        host.swapTo = lambda cls, **kw: swaps.append(cls)
        shell = self._shell(host)
        shell.openWindow(View)
        shell.openWindow(View)
        host.runPendingNav(View())
        host.runPendingNav(View())
        self.assertEqual([View], swaps)
