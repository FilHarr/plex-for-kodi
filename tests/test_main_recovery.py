# coding=utf-8
"""
L2 in the navigation review: when the background window's XML turns out broken, main() recompiles
the templates and tries once more. It used to call itself from inside its own Cron block, so a
second Cron thread ran beside the first, and a background window that stayed broken restarted
forever. Now each attempt's Cron stops before the next starts, and a second failure ends the addon.

Importing lib.main starts lib.player's monitor thread unless abort_requested is set first - same
guard the other lib.windows.* tests use for the same reason.
"""

from __future__ import absolute_import

import contextlib

from kodienv import ENV

ENV.abort_requested = True
from lib import main  # noqa: E402

from .base import KodiTestCase  # noqa: E402


class FakeCron(object):
    def __init__(self, test):
        self.test = test

    def __call__(self, interval):
        return self

    def __enter__(self):
        self.test.events.append('cron start')
        self.test.crons += 1
        self.test.maxCrons = max(self.test.maxCrons, self.test.crons)
        return self

    def __exit__(self, *exc):
        self.test.events.append('cron stop')
        self.test.crons -= 1


class FakeBackgroundWindow(object):
    def __init__(self, errored):
        self._errored = errored

    def waitForOpen(self):
        return True

    def modal(self):
        pass


class MainRecoveryTest(KodiTestCase):
    def setUp(self):
        super(MainRecoveryTest, self).setUp()
        self.events = []
        self.errors = []
        self.crons = 0
        self.maxCrons = 0
        self.windows = []
        saved = {}

        def patch(obj, name, value):
            saved[(obj, name)] = getattr(obj, name)
            setattr(obj, name, value)

        def create(function=None):
            window = FakeBackgroundWindow(self.windows.pop(0))
            self.events.append('window errored' if window._errored else 'window ran')
            return window

        def log(msg, *args, **kwargs):
            if kwargs.get('level') == main.xbmc.LOGERROR:
                self.errors.append(msg)

        patch(main, 'render_templates', lambda force=False: self.events.append('render force=%s' % force))
        patch(main.util, 'Cron', FakeCron(self))
        patch(main.util, 'cleanupCacheFolder', lambda: self.events.append('cleanup'))
        patch(main.util, 'LOG', log)
        patch(main.kodigui, 'GlobalProperty', lambda name: contextlib.contextmanager(lambda: (yield))())
        patch(main.background.BackgroundWindow, 'create', staticmethod(create))
        self.addCleanup(lambda: [setattr(obj, name, value) for (obj, name), value in saved.items()])

    def test_a_normal_start_renders_once_and_runs_one_cron(self):
        self.windows = [False]
        main.main()
        self.assertEqual(['render force=False', 'cleanup', 'cron start', 'window ran', 'cron stop'],
                         self.events)
        self.assertEqual([], self.errors)

    def test_one_error_recompiles_with_the_first_cron_stopped(self):
        self.windows = [True, False]
        main.main()
        self.assertEqual(['render force=False', 'cleanup', 'cron start', 'window errored', 'cron stop',
                          'render force=True', 'cron start', 'window ran', 'cron stop'], self.events)
        self.assertEqual(1, self.maxCrons)
        self.assertEqual([], self.errors)

    def test_a_second_error_ends_it(self):
        self.windows = [True, True, False]
        main.main()
        self.assertEqual(['render force=False', 'cleanup', 'cron start', 'window errored', 'cron stop',
                          'render force=True', 'cron start', 'window errored', 'cron stop'], self.events)
        self.assertEqual(1, self.maxCrons)
        self.assertEqual(1, len(self.errors))
        self.assertEqual([False], self.windows)
