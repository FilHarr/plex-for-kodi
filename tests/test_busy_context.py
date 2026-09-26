# coding=utf-8
"""
Busy contexts pass an exception in their block on instead of swallowing it: callers used to carry
on as if the block had succeeded (S3 in the navigation review).
"""

from __future__ import absolute_import

from kodienv import ENV

ENV.abort_requested = True
from plexnet import plexapp  # noqa: E402
from lib.windows import busy  # noqa: E402

from .base import KodiTestCase  # noqa: E402

try:
    from unittest import mock
except ImportError:
    import mock


class Failed(Exception):
    pass


class FakeBusyWindow(object):
    """The context's control flow is under test, not Kodi's window."""
    ctx = None

    def __init__(self):
        self.isOpen = True

    @classmethod
    def create(cls, show=True, **kwargs):
        return cls()

    def show(self):
        pass

    def doClose(self):
        self.isOpen = False


class FakeWindowTestCase(KodiTestCase):
    def setUp(self):
        super(FakeWindowTestCase, self).setUp()
        patcher = mock.patch.object(busy.BusyWindow, 'create', FakeBusyWindow.create)
        patcher.start()
        self.addCleanup(patcher.stop)


class BusyContextTest(FakeWindowTestCase):
    def test_an_exception_in_the_block_is_passed_on(self):
        with self.assertRaises(Failed):
            with busy.BusyContext():
                raise Failed()

    def test_the_busy_window_still_closes(self):
        ctx = busy.BusyContext()
        with self.assertRaises(Failed):
            with ctx:
                window = ctx.w
                raise Failed()
        self.assertIsNone(ctx.w)
        self.assertFalse(window.isOpen)

    def test_a_block_that_succeeds_carries_on(self):
        ran = []
        with busy.BusyContext():
            ran.append(1)
        ran.append(2)
        self.assertEqual([1, 2], ran)


class BusySignalContextTest(FakeWindowTestCase):
    def test_a_failed_block_does_not_wait_for_its_signal(self):
        ctx = busy.BusySignalContext(plexapp.util.APP, 'test:never', wait_max=10, delay=False)
        with mock.patch.object(busy.util.MONITOR, 'waitFor') as waitFor:
            with self.assertRaises(Failed):
                with ctx:
                    raise Failed()
        self.assertFalse(waitFor.called)
        self.assertFalse(plexapp.util.APP.has_signal('test:never', ctx.onSignal))
