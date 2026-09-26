# coding=utf-8
"""
Waits for Kodi's GUI thread sleep instead of calling MONITOR.waitFor(), which runs the thread's
queued callbacks inside the wait - a click could run in the middle of a screen's setup (F6 in the
navigation review).
"""

from __future__ import absolute_import

import time

from kodienv import ENV

ENV.abort_requested = True
from lib.windows import kodigui  # noqa: E402

from .base import KodiTestCase  # noqa: E402

try:
    from unittest import mock
except ImportError:
    import mock


class WaitForVisibilityTest(KodiTestCase):
    def setUp(self):
        super(WaitForVisibilityTest, self).setUp()
        patcher = mock.patch.object(kodigui.util.MONITOR, 'waitFor',
                                    side_effect=AssertionError('ran queued callbacks'))
        patcher.start()
        self.addCleanup(patcher.stop)
        # Not aborting, or the wait would end at once and prove nothing.
        abort = mock.patch.object(kodigui.util.MONITOR, 'abortRequested', return_value=False)
        abort.start()
        self.addCleanup(abort.stop)

    def test_it_returns_once_the_control_is_visible_without_waiting_on_the_monitor(self):
        answers = iter([False, False, True])
        started = time.time()
        with mock.patch.object(kodigui.xbmc, 'getCondVisibility', side_effect=lambda cond: next(answers)):
            kodigui.waitForVisibility(301, amount=2)
        self.assertLess(time.time() - started, 0.5)

    def test_it_gives_up_at_its_deadline(self):
        started = time.time()
        with mock.patch.object(kodigui.xbmc, 'getCondVisibility', return_value=False):
            kodigui.waitForVisibility(301, amount=0.1)
        self.assertGreaterEqual(time.time() - started, 0.1)
        self.assertLess(time.time() - started, 1.0)
