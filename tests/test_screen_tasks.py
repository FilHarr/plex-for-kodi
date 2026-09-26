# coding=utf-8
"""
F5 in the navigation review: a screen's background row fills (TasksMixin.postpone_simple()/
batch_simple()) belong to the screen, so closing it cancels the ones still queued - the host
closes a swapped-out screen natively, freeing its controls, and a fill left to run afterwards
wrote into them from a worker.

Importing lib.windows.* starts lib.player's monitor thread unless abort_requested is set first.
"""

from __future__ import absolute_import

from kodienv import ENV

ENV.abort_requested = True
from lib import backgroundthread  # noqa: E402
from lib.windows.mixins import tasks as tasks_mixin  # noqa: E402

from .base import KodiTestCase  # noqa: E402


class Screen(tasks_mixin.TasksMixin):
    pass


class ScreenTasksTest(KodiTestCase):
    def setUp(self):
        super(ScreenTasksTest, self).setUp()
        self.queued = []
        self._addTask = backgroundthread.BGThreader.addTask
        self._addTasks = backgroundthread.BGThreader.addTasks
        backgroundthread.BGThreader.addTask = lambda task: self.queued.append(task)
        backgroundthread.BGThreader.addTasks = lambda tasks: self.queued.extend(tasks)
        # Task.isCanceled() is also true once Kodi asks to abort, which the test environment does.
        self._abortRequested = backgroundthread.MONITOR.abortRequested
        backgroundthread.MONITOR.abortRequested = lambda: False

    def tearDown(self):
        backgroundthread.BGThreader.addTask = self._addTask
        backgroundthread.BGThreader.addTasks = self._addTasks
        backgroundthread.MONITOR.abortRequested = self._abortRequested
        super(ScreenTasksTest, self).tearDown()

    def test_fills_belong_to_the_screen(self):
        screen = Screen()
        screen.batch_simple([(lambda: None, None, None), (lambda: None, None, None)])
        screen.postpone_simple(lambda: None)
        self.assertEqual(3, len(self.queued))
        self.assertEqual(set(self.queued), set(screen.tasks))

    def test_a_fill_runs(self):
        ran = []
        screen = Screen()
        screen.postpone_simple(lambda: ran.append(1))
        self.queued[0].run()
        self.assertEqual([1], ran)

    def test_a_cancelled_fill_does_not_run(self):
        ran = []
        screen = Screen()
        screen.postpone_simple(lambda: ran.append(1))
        task = self.queued[0]
        task.cancel()
        task.run()
        self.assertEqual([], ran)

    def test_a_closed_screen_queues_nothing(self):
        screen = Screen()
        screen.tasks = None
        screen.postpone_simple(lambda: None)
        screen.batch_simple([(lambda: None, None, None)])
        self.assertEqual([], self.queued)


class FakeHome(object):
    def stopRetryingRequests(self, stop=True):
        pass


class FakeControl(object):
    def __init__(self):
        self.calls = []

    def addItems(self, items):
        self.calls.append(('addItems', len(items)))

    def reset(self):
        self.calls.append('reset')


class FakeWindow(object):
    def __init__(self, guard):
        self._writeGuard = guard
        self.control = FakeControl()

    def getControl(self, control_id):
        return self.control


class WriteGuardTest(ScreenTasksTest):
    """Closing the screen stops its lists reaching Kodi, without waiting for fills still fetching."""

    def setUp(self):
        super(WriteGuardTest, self).setUp()
        from lib.windows import windowutils
        self._home = windowutils.HOME
        windowutils.HOME = FakeHome()
        self.screen = Screen()
        self.window = FakeWindow(self.screen._writeGuard)
        self.list = tasks_mixin.kodigui.ManagedControlList(self.window, 100, 5)

    def tearDown(self):
        from lib.windows import windowutils
        windowutils.HOME = self._home
        super(WriteGuardTest, self).tearDown()

    def test_an_open_screens_list_reaches_kodi(self):
        self.list.reset()
        self.assertEqual(['reset'], self.window.control.calls)

    def test_after_close_a_list_call_raises_instead(self):
        self.screen.doClose()
        with self.assertRaises(tasks_mixin.kodigui.ScreenClosed):
            self.list.reset()
        self.assertEqual([], self.window.control.calls)

    def test_a_fill_stopped_by_the_close_is_not_an_error(self):
        errors = []
        original = tasks_mixin.log.ERROR
        tasks_mixin.log.ERROR = lambda *a, **k: errors.append(a)
        try:
            self.screen.postpone_simple(self.list.reset)
            task = self.queued[0]
            self.screen.doClose()
            task._canceled = False   # as if a worker had already picked it up
            task.run()
        finally:
            tasks_mixin.log.ERROR = original
        self.assertEqual([], errors)
        self.assertEqual([], self.window.control.calls)

    def test_a_list_on_a_window_without_a_guard_is_unchanged(self):
        control = FakeControl()
        window = type('W', (), {'getControl': lambda self, cid: control})()
        plain = tasks_mixin.kodigui.ManagedControlList(window, 100, 5)
        self.assertIs(control, plain.control)
