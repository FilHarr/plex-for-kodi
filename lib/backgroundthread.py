from __future__ import absolute_import
import itertools
import threading
import six.moves.queue
import heapq
from kodi_six import xbmc
from .monitor import MONITOR
from .settings_util import getSetting
from . import logging
from .kodi_util import ENABLE_HIGH_CONCURRENCY
from plexnet import threadutils
from six.moves import range


# Idle seconds a worker waits for more work before its thread exits. Keeps one thread per worker
# across a burst of chunk requests while the user scrolls, instead of a new thread per chunk.
WORKER_IDLE_SECONDS = 5.0

# Tie-break for tasks sharing a priority (addTasksToFront()/moveToFront() can produce equal ones),
# so heap order is FIFO among them and never falls back to comparing anything else.
_taskSequence = itertools.count()


class Tasks(list):
    def add(self, task):
        # Rebuilt rather than remove()d while iterating, which skipped the item after each removal
        # and let finished tasks pile up on long-lived owners (LibraryWindow.tasks).
        self[:] = [t for t in self if t.isValid()]

        if isinstance(task, list):
            self += task
        else:
            self.append(task)

    def cancel(self):
        while self:
            self.pop().cancel()

    def kill(self):
        """Cancel this owner's tasks and move on without waiting for any of them: BGThreader.reset()
        leaves in-flight tasks to finish on their old workers and hands everything still queued to
        fresh ones. Used to join every worker, so a swap (openSection()/switchTab()) or an exit
        waited on whatever HTTP requests were in flight, retries included, and on tasks other
        windows had queued. Late results are covered by each callback's own staleness checks
        (_listGeneration, isCanceled(), closing)."""
        self.cancel()
        BGThreader.reset()


class Task:
    def __init__(self, priority=None):
        self._priority = priority
        self._seq = next(_taskSequence)
        self._canceled = False
        self.finished = False

    def _sortKey(self):
        return self._priority, self._seq

    def __lt__(self, other):
        return self._sortKey() < other._sortKey()

    def __le__(self, other):
        return self._sortKey() <= other._sortKey()

    def __gt__(self, other):
        return self._sortKey() > other._sortKey()

    def __bool__(self):
        return self.isValid()

    def start(self):
        BGThreader.addTask(self)

    def _run(self):
        self.run()
        self.finished = True

    def run(self):
        pass

    def cancel(self):
        self._canceled = True

    def isCanceled(self):
        return self._canceled or MONITOR.abortRequested()

    def isValid(self):
        return not self.finished and not self._canceled


class MutablePriorityQueue(six.moves.queue.PriorityQueue):
    """A PriorityQueue whose items' priorities can change while queued (reprioritize()). Used to
    sort the whole queue on every get() to cope with that; now the heap is restored once, when a
    priority actually changes."""

    def lowest(self):
        """Return the lowest priority item in the queue (not reliable!)."""
        with self.mutex:
            return self.queue[0] if self.queue else None

    def reprioritize(self, item, priority):
        with self.mutex:
            item._priority = priority
            heapq.heapify(self.queue)

    def drain(self):
        """Remove and return everything still queued, in priority order."""
        with self.mutex:
            items = sorted(self.queue)
            del self.queue[:]
            return items


class BackgroundWorker:
    def __init__(self, queue, name=None):
        self._queue = queue
        self.name = name
        self._thread = None
        self._abort = False
        self._task = None
        # Set by a worker thread that has found the queue empty and is on its way out, so start()
        # starts a new thread instead of counting on it (see _queueLoop()).
        self._exiting = False

    def _runTask(self, task):
        if task._canceled:
            return
        try:
            task._run()
        except:
            logging.ERROR()

    def abort(self):
        self._abort = True
        return self

    def aborted(self):
        return self._abort or MONITOR.abortRequested()

    def start(self):
        if self._thread and self._thread.is_alive() and not self._exiting:
            return

        self._exiting = False
        self._thread = threadutils.KillableThread(target=self._queueLoop, name='BACKGROUND-WORKER({0})'.format(self.name))
        self._thread.start()

    def _queueLoop(self):
        if self._queue.empty():
            return

        logging.DEBUG_LOG('BGThreader: ({0}): Active', self.name)
        while not self.aborted():
            try:
                # Waits a while for more work rather than exiting as soon as the queue is empty,
                # which started a new thread for almost every chunk request while scrolling.
                self._task = self._queue.get(timeout=WORKER_IDLE_SECONDS)
            except six.moves.queue.Empty:
                # Marked exiting before the last look at the queue: a task put() after that look
                # is followed by a start() that sees _exiting and starts a new thread, so no task
                # is left waiting on a thread that has already decided to go.
                self._exiting = True
                if self._queue.empty() or self._thread is not threading.current_thread():
                    # Empty, or start() has already replaced this thread for the new work.
                    logging.DEBUG_LOG('BGThreader ({0}): Idle', self.name)
                    return
                self._exiting = False
                continue
            try:
                self._runTask(self._task)
            finally:
                self._queue.task_done()
                self._task = None

    def shutdown(self):
        self.abort()

        if self._task:
            self._task.cancel()

        if self._thread and self._thread.is_alive():
            logging.DEBUG_LOG('BGThreader: thread ({0}): Waiting...', self.name)
            self._thread.join()
            logging.DEBUG_LOG('BGThreader: thread ({0}): Done', self.name)

    def alive(self):
        return bool(self._thread and self._thread.is_alive())


class BackgroundThreader:
    def __init__(self, name=None, worker_count=5):
        self.name = name
        self._queue = MutablePriorityQueue()
        self._abort = False
        self._priority = -1
        self.workers = [BackgroundWorker(self._queue, 'queue.{0}:worker.{1}'.format(self.name, x)) for x in range(worker_count)]

    def _nextPriority(self):
        self._priority += 1
        return self._priority

    def abort(self):
        self._abort = True
        for w in self.workers:
            w.abort()
        return self

    def aborted(self):
        return self._abort or MONITOR.abortRequested()

    def shutdown(self):
        self.abort()

        for w in self.workers:
            w.shutdown()

    def addTask(self, task):
        task._priority = self._nextPriority()
        self._queue.put(task)
        self.startWorkers()

    def addTasks(self, tasks):
        for t in tasks:
            t._priority = self._nextPriority()
            self._queue.put(t)

        self.startWorkers()

    def addTasksToFront(self, tasks):
        lowest = self.getLowestPrority()
        if lowest is None:
            return self.addTasks(tasks)

        p = lowest - len(tasks)
        for t in tasks:
            t._priority = p
            self._queue.put(t)
            p += 1

        self.startWorkers()

    def startWorkers(self):
        for w in self.workers:
            w.start()

    def working(self):
        """True while anything is queued or running. Counted by the queue itself (put() raises it,
        task_done() lowers it): a live worker thread no longer means work, since idle workers wait
        WORKER_IDLE_SECONDS before exiting."""
        with self._queue.mutex:
            return self._queue.unfinished_tasks > 0

    def alive(self):
        return any(w.alive() for w in self.workers)

    def getLowestPrority(self):
        lowest = self._queue.lowest()
        if not lowest:
            return None

        return lowest._priority

    def moveToFront(self, qitem):
        lowest = self.getLowestPrority()
        if lowest is None:
            return

        self._queue.reprioritize(qitem, lowest - 1)

    def drainQueued(self):
        return self._queue.drain()


class ThreaderManager:
    def __init__(self, worker_count=5):
        self.index = 0
        self.abandoned = []
        self.worker_count = worker_count
        self.threader = BackgroundThreader(str(self.index), worker_count=worker_count)

    def __getattr__(self, name):
        return getattr(self.threader, name)

    def reset(self):
        """Hand the work over to a fresh threader without waiting for the current one: its workers
        finish only the task each is already running, then stop; everything still queued (other
        owners' tasks included, not just the caller's) moves to the new threader in the same
        order, minus anything already cancelled. See Tasks.kill()."""
        old = self.threader
        if not old.working():
            return

        self.index += 1
        # New threader first: a Task.start() racing this lands on one threader or the other,
        # never on one that's already been drained.
        self.threader = BackgroundThreader(str(self.index), worker_count=self.worker_count)
        old.abort()
        carried = [t for t in old.drainQueued() if not t._canceled]
        if carried:
            self.threader.addTasks(carried)
        self.abandoned = [a for a in self.abandoned if a.alive()]
        if old.alive():
            self.abandoned.append(old)
        logging.DEBUG_LOG('BGThreader: reset to threader {0}, carried {1} queued task(s), {2} abandoned '
                          'threader(s) still finishing', self.index, len(carried), len(self.abandoned))

    def shutdown(self):
        self.threader.shutdown()
        for a in self.abandoned:
            a.shutdown()

# clamp worker count to 3 maximum if we're below python 3.14
BGThreader = ThreaderManager(worker_count=min(getSetting('worker_count', 3), ENABLE_HIGH_CONCURRENCY and 32 or 3))
