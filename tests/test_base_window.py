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


class RestoreTest(KodiTestCase):
    """Restoring from minimised replaced Kodi's home with the last screen, which then returned to
    Kodi's home: it showed for a moment on the next screen change after every restore (AM6B,
    2026-09-27). The base window now replaces Kodi's home, and the screen shows over it."""

    def _restore(self, base=13001):
        from lib import monitor, util
        with mock.patch.object(kodigui, 'BASE_WINDOW_ID', base), \
                mock.patch.object(kodigui.BaseFunctions, 'lastWinID', 13004), \
                mock.patch.object(kodigui.BaseFunctions, 'restoring', False), \
                mock.patch.object(util, 'reInitAddon'), \
                mock.patch.object(monitor, '_setGlobalProperty'), \
                mock.patch.object(monitor.xbmc, 'executebuiltin') as builtin:
            monitor.MONITOR.onNotification('script.plexmod', 'Other.RESTORE', '{}')
            self.assertTrue(kodigui.BaseFunctions.restoring)
        return [c.args for c in builtin.call_args_list]

    def test_the_screen_comes_back_over_the_base_window(self):
        self.assertEqual([('ReplaceWindow(13001)', True), ('ActivateWindow(13004)',)], self._restore())

    def test_without_a_base_window_the_screen_replaces_kodis_home(self):
        self.assertEqual([('ReplaceWindow(13004)',)], self._restore(base=None))


class FakeAction(object):
    def __init__(self, actionId):
        self.actionId = actionId

    def getId(self):
        return self.actionId


class SkipsBuiltinsTest(KodiTestCase):
    """A builtin (the power key's ShutDown(), say) reaches the window as an action while Kodi runs
    it on its main thread; touching a control then could deadlock the two over the GIL, so every
    window's onAction skips it (kodigui._skippingBuiltins())."""

    def setUp(self):
        super(SkipsBuiltinsTest, self).setUp()
        seen = self.seen = []

        class Screen(kodigui.ControlledWindow):
            def __init__(self):
                pass

            def onAction(self, action):
                seen.append(action.getId())

        class ViewMixin(object):
            def onAction(self, action):
                seen.append(('view', action.getId()))

        class View(ViewMixin, kodigui.ControlledWindow):
            def __init__(self):
                pass

        self.screen = Screen()
        self.view = View()

    def test_a_builtin_never_reaches_the_window(self):
        self.screen.onAction(FakeAction(kodigui.ACTION_BUILT_IN_FUNCTION))
        self.assertEqual([], self.seen)

    def test_other_actions_do(self):
        self.screen.onAction(FakeAction(kodigui.xbmcgui.ACTION_NAV_BACK))
        self.assertEqual([kodigui.xbmcgui.ACTION_NAV_BACK], self.seen)

    def test_an_inherited_onaction_skips_it_too(self):
        self.view.onAction(FakeAction(kodigui.ACTION_BUILT_IN_FUNCTION))
        self.view.onAction(FakeAction(kodigui.xbmcgui.ACTION_NAV_BACK))
        self.assertEqual([('view', kodigui.xbmcgui.ACTION_NAV_BACK)], self.seen)
