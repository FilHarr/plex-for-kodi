# coding=utf-8

from lib import backgroundthread, logging as log
from lib.windows import kodigui, windowutils


class SimpleTask(backgroundthread.Task):
    def setup(self, func, cb, *args, **kwargs):
        self.func = func
        self.cb = cb
        self.args = args
        self.kwargs = kwargs
        return self

    def run(self):
        try:
            if not self.isCanceled():
                self.func(*self.args, **self.kwargs)
        except kodigui.ScreenClosed as e:
            log.DEBUG_LOG("Task stopped, its screen closed ({}): {}", e, self.func)
        except:
            log.ERROR("Task failed: {} (args: {}, kwargs: {})", self.func, self.args, self.kwargs)
        finally:
            self.cb(self)


class TasksMixin(object):
    def __init__(self):
        self.tasks = backgroundthread.Tasks()
        # Every list this screen creates goes through it (kodigui.WriteGuard); doClose() closes it.
        self._writeGuard = kodigui.WriteGuard()

    # Both add their tasks to self.tasks, so doClose() cancels the ones still queued: they fill this
    # screen's rows, and since the host closes a swapped-out screen natively (freeing its controls),
    # one left to run after that wrote into freed controls from a worker (F5 in the navigation
    # review). A running one is stopped by the write guard instead (doClose()). Nothing is queued
    # once the screen has closed.
    def postpone_simple(self, func, *args, **kwargs):
        if self.tasks is None:
            return
        task = SimpleTask().setup(func, self.default_callback, *args, **kwargs)
        self.tasks.add(task)
        backgroundthread.BGThreader.addTask(task)

    def batch_simple(self, tasks):
        if self.tasks is None:
            return
        batch = []
        for func, args, kwargs in tasks:
            task = SimpleTask().setup(func, self.default_callback, *(args or []), **(kwargs or {}))
            batch.append(task)
        self.tasks.add(batch)
        backgroundthread.BGThreader.addTasks(batch)

    def default_callback(self, task):
        try:
            self.tasks.remove(task)
            del task
        except:
            pass

    def doClose(self):
        # Closed first: from here on this screen's lists and their items raise
        # kodigui.ScreenClosed instead of reaching Kodi, and close() waits only for a call already
        # in progress - so a fill still fetching can't write once the host closes this screen
        # natively (freeing its controls), and closing doesn't wait for its request (F5 in the
        # navigation review).
        guard = getattr(self, '_writeGuard', None)
        if guard is not None:
            guard.close()
        tasks, self.tasks = self.tasks, None
        if not tasks:
            return
        try:
            log.DEBUG_LOG("Killing {} tasks".format(len(tasks)))
            windowutils.HOME.stopRetryingRequests()
            tasks.kill()
        except:
            pass
        finally:
            windowutils.HOME.stopRetryingRequests(False)