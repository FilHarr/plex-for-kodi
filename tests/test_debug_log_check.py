# coding=utf-8
"""
P2 in the navigation review: with the addon's debug setting off, DEBUG_LOG used to ask Kodi
whether its own debug logging was on - a GUI-locked call - for every suppressed line. The answer
is now cached, and read again at most every KODI_DEBUG_RECHECK_SECONDS.
"""

from __future__ import absolute_import

from kodienv import ENV

ENV.abort_requested = True
from lib import logging as addon_logging  # noqa: E402
from lib.addonsettings import addonSettings  # noqa: E402

from .base import KodiTestCase  # noqa: E402


class Clock(object):
    def __init__(self, now=1000.0):
        self.now = now

    def time(self):
        return self.now


class DebugLogCheckTest(KodiTestCase):
    def setUp(self):
        super(DebugLogCheckTest, self).setUp()
        self.calls = []
        self._cond = addon_logging.xbmc.getCondVisibility
        self._time = addon_logging.time
        self._debug = addonSettings.debug
        self._log = addon_logging.log
        self.clock = Clock()
        addon_logging.xbmc.getCondVisibility = lambda cond: self.calls.append(cond) or False
        addon_logging.time = self.clock
        addon_logging.log = lambda *a, **k: None
        addonSettings.debug = False
        addon_logging._kodiDebug = (False, None)

    def tearDown(self):
        addon_logging.xbmc.getCondVisibility = self._cond
        addon_logging.time = self._time
        addon_logging.log = self._log
        addonSettings.debug = self._debug
        addon_logging._kodiDebug = (False, None)
        super(DebugLogCheckTest, self).tearDown()

    def test_kodi_is_asked_once_for_many_lines(self):
        for _ in range(50):
            addon_logging.DEBUG_LOG('line')
        self.assertEqual(1, len(self.calls))

    def test_asked_again_after_the_recheck_interval(self):
        addon_logging.DEBUG_LOG('line')
        self.clock.now += addon_logging.KODI_DEBUG_RECHECK_SECONDS
        addon_logging.DEBUG_LOG('line')
        self.assertEqual(2, len(self.calls))

    def test_the_addons_own_debug_setting_skips_the_check(self):
        addonSettings.debug = True
        addon_logging.DEBUG_LOG('line')
        self.assertEqual([], self.calls)
