# coding=utf-8
"""
The signal audit (F3 in the navigation review): a window whose signal handler runs off the main
thread, or after the window closed, is logged once per handler, signal and reason.
"""

from __future__ import absolute_import

import threading

from kodienv import ENV

ENV.abort_requested = True
from plexnet import signalsmixin  # noqa: E402
from lib.windows import kodigui  # noqa: E402

from .base import KodiTestCase  # noqa: E402

try:
    from unittest import mock
except ImportError:
    import mock


class Screen(kodigui.BaseWindow):
    def onThing(self, **kwargs):
        pass


class Emitter(signalsmixin.SignalsMixin):
    pass


class SignalAuditTest(KodiTestCase):
    def setUp(self):
        super(SignalAuditTest, self).setUp()
        kodigui._signalAuditSeen.clear()
        self.screen = Screen.__new__(Screen)
        self.screen._closing = False
        self.emitter = Emitter()
        self.emitter.on('thing', self.screen.onThing)

    def _logged(self, trigger):
        with mock.patch.object(kodigui.util, 'DEBUG_LOG') as log:
            trigger()
        return [call.args for call in log.call_args_list]

    def test_the_audit_is_installed(self):
        self.assertIs(kodigui._auditSignal, signalsmixin.AUDIT)

    def test_an_open_window_on_the_main_thread_is_not_logged(self):
        self.assertEqual([], self._logged(lambda: self.emitter.trigger('thing')))

    def test_a_closed_window_is_logged_once(self):
        self.screen._closing = True
        logged = self._logged(lambda: [self.emitter.trigger('thing') for _ in range(3)])
        self.assertEqual(1, len(logged))
        self.assertEqual(('thing', 'Emitter', 'Screen', 'onThing', 'after its window closed'), logged[0][1:])

    def test_a_delivery_off_the_main_thread_names_the_thread(self):
        def fromThread():
            t = threading.Thread(target=self.emitter.trigger, args=('thing',), name='PLAYER:MONITOR')
            t.start()
            t.join()
        logged = self._logged(fromThread)
        self.assertEqual(1, len(logged))
        self.assertEqual('on thread PLAYER:MONITOR', logged[0][5])
