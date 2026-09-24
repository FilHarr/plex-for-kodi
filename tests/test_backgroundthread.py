# coding=utf-8
"""
lib/backgroundthread.py after E3/P5 in the navigation review:

- Tasks.kill() cancels its owner's tasks and resets the threader instead of joining every worker,
  so a swap or exit no longer waits on in-flight requests. Queued tasks from other owners carry
  over to the new threader rather than being dropped.
- The queue is a real heap with a sequence tie-break; moveToFront() re-heaps once instead of
  get() sorting the whole queue each time.
- Idle workers wait for more work before exiting, so working() counts unfinished tasks, not live
  threads.
- Tasks.add() prunes finished tasks without skipping any.
"""

from __future__ import absolute_import

import threading
import time

from kodienv import ENV

ENV.abort_requested = True
from lib import backgroundthread  # noqa: E402

from .base import KodiTestCase  # noqa: E402


class RecordingTask(backgroundthread.Task):
    def __init__(self, name, log, gate=None):
        backgroundthread.Task.__init__(self)
        self.name = name
        self.log = log
        self.gate = gate

    def run(self):
        if self.gate is not None:
            self.gate.wait(5)
        self.log.append(self.name)


def wait_until(predicate, timeout=5.0):
    end = time.time() + timeout
    while time.time() < end:
        if predicate():
            return True
        time.sleep(0.01)
    return predicate()


class _ThreaderCase(KodiTestCase):
    def setUp(self):
        super(_ThreaderCase, self).setUp()
        self._idle = backgroundthread.WORKER_IDLE_SECONDS
        backgroundthread.WORKER_IDLE_SECONDS = 0.2
        self.manager = backgroundthread.ThreaderManager(worker_count=1)

    def tearDown(self):
        self.manager.shutdown()
        backgroundthread.WORKER_IDLE_SECONDS = self._idle
        super(_ThreaderCase, self).tearDown()


class TasksAddTest(KodiTestCase):
    def test_prunes_every_finished_task(self):
        """remove() while iterating skipped the task after each removed one."""
        tasks = backgroundthread.Tasks()
        done = [backgroundthread.Task() for _ in range(4)]
        for t in done:
            t.finished = True
        tasks += done
        live = backgroundthread.Task()
        tasks.add(live)
        self.assertEqual([live], list(tasks))


class QueueOrderTest(KodiTestCase):
    def test_equal_priorities_come_out_first_in_first_out(self):
        q = backgroundthread.MutablePriorityQueue()
        tasks = [backgroundthread.Task(priority=0) for _ in range(5)]
        for t in tasks:
            q.put(t)
        self.assertEqual(tasks, [q.get_nowait() for _ in tasks])

    def test_reprioritize_moves_a_queued_task_to_the_front(self):
        q = backgroundthread.MutablePriorityQueue()
        tasks = [backgroundthread.Task(priority=p) for p in range(5)]
        for t in tasks:
            q.put(t)
        q.reprioritize(tasks[3], -1)
        self.assertIs(tasks[3], q.lowest())
        self.assertEqual([tasks[3], tasks[0], tasks[1], tasks[2], tasks[4]], [q.get_nowait() for _ in tasks])


class WorkerTest(_ThreaderCase):
    def test_runs_tasks_in_priority_order_and_reports_idle(self):
        log = []
        gate = threading.Event()
        self.manager.addTask(RecordingTask('first', log, gate))
        self.manager.addTasks([RecordingTask('b', log), RecordingTask('c', log)])
        self.manager.addTasksToFront([RecordingTask('front', log)])
        self.assertTrue(self.manager.working())
        gate.set()
        self.assertTrue(wait_until(lambda: not self.manager.working()))
        self.assertEqual(['first', 'front', 'b', 'c'], log)

    def test_an_idle_worker_picks_up_new_work_without_a_new_thread(self):
        log = []
        self.manager.addTask(RecordingTask('a', log))
        self.assertTrue(wait_until(lambda: not self.manager.working()))
        thread = self.manager.threader.workers[0]._thread
        self.assertTrue(thread.is_alive(), 'still waiting for work')
        self.manager.addTask(RecordingTask('b', log))
        self.assertTrue(wait_until(lambda: log == ['a', 'b']))
        self.assertIs(thread, self.manager.threader.workers[0]._thread)

    def test_idle_workers_exit_and_restart_for_new_work(self):
        log = []
        self.manager.addTask(RecordingTask('a', log))
        self.assertTrue(wait_until(lambda: not self.manager.threader.alive()))
        self.manager.addTask(RecordingTask('b', log))
        self.assertTrue(wait_until(lambda: log == ['a', 'b']))


class KillTest(_ThreaderCase):
    def test_kill_does_not_wait_for_an_in_flight_task(self):
        log = []
        gate = threading.Event()
        blocker = RecordingTask('in-flight', log, gate)
        self.manager.addTask(blocker)
        self.assertTrue(wait_until(lambda: self.manager.threader.workers[0]._task is blocker))

        original = backgroundthread.BGThreader
        backgroundthread.BGThreader = self.manager
        try:
            tasks = backgroundthread.Tasks()
            tasks.add(blocker)
            started = time.time()
            tasks.kill()
            self.assertLess(time.time() - started, 0.5, 'kill() must not join the worker')
        finally:
            backgroundthread.BGThreader = original
        self.assertTrue(blocker._canceled)
        gate.set()

    def test_reset_carries_other_owners_queued_tasks_to_the_new_threader(self):
        log = []
        gate = threading.Event()
        self.manager.addTask(RecordingTask('in-flight', log, gate))
        self.assertTrue(wait_until(lambda: self.manager.threader.workers[0]._task is not None))
        mine = RecordingTask('mine', log)
        theirs = [RecordingTask('theirs-1', log), RecordingTask('theirs-2', log)]
        self.manager.addTasks([mine] + theirs)
        mine.cancel()
        old = self.manager.threader

        self.manager.reset()

        self.assertIsNot(old, self.manager.threader)
        self.assertEqual(1, len(self.manager.threader.workers), 'keeps the configured worker count')
        self.assertTrue(wait_until(lambda: log == ['theirs-1', 'theirs-2']))
        gate.set()
        self.assertTrue(wait_until(lambda: 'in-flight' in log))
        self.assertNotIn('mine', log)

    def test_reset_with_nothing_to_do_keeps_the_threader(self):
        old = self.manager.threader
        self.manager.reset()
        self.assertIs(old, self.manager.threader)
