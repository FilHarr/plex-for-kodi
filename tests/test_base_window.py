# coding=utf-8
"""
kodigui.ensureBaseWindow(): before each screen shows, Kodi should be showing the base window
(BackgroundWindow), since a screen returns to the window that was active when it was shown.
Otherwise it's reactivated first - once one screen remembered Kodi's own home, every screen
after it showed Kodi on each change.
"""

from __future__ import absolute_import

from kodienv import ENV

ENV.abort_requested = True
from lib.windows import kodigui  # noqa: E402

from .base import KodiTestCase  # noqa: E402

try:
    from unittest import mock
except ImportError:
    import mock


class EnsureBaseWindowTest(KodiTestCase):
    def _run(self, current, active='1', base=13001):
        with mock.patch.object(kodigui, 'BASE_WINDOW_ID', base), \
                mock.patch.object(kodigui.util, 'getGlobalProperty', return_value=active), \
                mock.patch.object(kodigui.xbmcgui, 'getCurrentWindowId', return_value=current), \
                mock.patch.object(kodigui.xbmc, 'executebuiltin') as builtin:
            kodigui.ensureBaseWindow('RecommendedWindow')
        return builtin

    def test_nothing_to_do_while_the_base_window_shows(self):
        self.assertFalse(self._run(current=13001).called)

    def test_another_window_brings_the_base_window_back_first(self):
        builtin = self._run(current=10000)
        builtin.assert_called_once_with('ActivateWindow(13001)', True)

    def test_left_alone_while_the_addon_is_minimised(self):
        self.assertFalse(self._run(current=10000, active='').called)

    def test_left_alone_before_the_base_window_is_known(self):
        self.assertFalse(self._run(current=10000, base=None).called)
