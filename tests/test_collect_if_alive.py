# coding=utf-8
"""
util.collectIfAlive(): a closed window or dialog is collected only when it outlived its caller's
last reference. Every close used to force a full collection, 100-300 ms on the AM6B (E4 in the
navigation review).
"""

from __future__ import absolute_import

import gc

from kodienv import ENV  # noqa: F401

from lib import util

from .base import KodiTestCase

try:
    from unittest import mock
except ImportError:
    import mock


class Closed(object):
    pass


class Slotted(object):
    __slots__ = ('x',)


class CollectIfAliveTest(KodiTestCase):
    def _run(self, window):
        ref = util.windowRef(window)
        del window
        with mock.patch.object(util.gc, 'collect', wraps=gc.collect) as collect:
            util.collectIfAlive(ref)
        return collect

    def test_a_window_freed_by_refcounting_is_not_collected(self):
        self.assertFalse(self._run(Closed()).called)

    def test_a_window_in_a_cycle_is_collected(self):
        window = Closed()
        window.me = window
        ref = util.windowRef(window)
        del window
        with mock.patch.object(util.gc, 'collect', wraps=gc.collect) as collect:
            util.collectIfAlive(ref)
        collect.assert_called_once_with(2)
        self.assertIsNone(ref())

    def test_a_window_held_elsewhere_is_collected_and_survives(self):
        holder = [Closed()]
        collect = self._run(holder[0])
        self.assertTrue(collect.called)
        self.assertEqual(1, len(holder))

    def test_one_that_cannot_be_weakly_referenced_is_collected(self):
        self.assertIsNone(util.windowRef(Slotted()))
        with mock.patch.object(util.gc, 'collect') as collect:
            util.collectIfAlive(None)
        collect.assert_called_once_with(2)
