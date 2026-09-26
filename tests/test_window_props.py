# coding=utf-8
"""
BaseWindow.setProperty() writes to its own window only. It used to write a second time through
xbmcgui.Window(self._winID), three GUI-locked calls for one property, and before the window was
open that fell back to whichever window was on screen (F2 in the navigation review). Carried
properties (window_props/dialog_props) still go to the window underneath too: the hub-row labels
LibraryWindow.carriedProps restores depend on it.
"""

from __future__ import absolute_import

from kodienv import ENV

ENV.abort_requested = True
from lib.windows import kodigui  # noqa: E402

from .base import KodiTestCase  # noqa: E402


class WindowPropsTest(KodiTestCase):
    def _window(self):
        window = kodigui.BaseWindow.__new__(kodigui.BaseWindow)
        window._closing = False
        window._winID = None
        window.windowId = 13001
        return window

    def test_a_property_goes_to_this_window_only(self):
        ENV.current_window_id = 10025
        window = self._window()
        window.setProperty('title', 'Alien')
        self.assertEqual(ENV.window_props[13001].get('title'), 'Alien')
        self.assertNotIn('title', ENV.window_props[10025])

    def test_carried_props_also_reach_the_window_underneath(self):
        ENV.current_window_id = 10025
        window = self._window()
        kodigui.applyCarriedProps(window, {'hub.text2lines.400': '1'})
        self.assertEqual(ENV.window_props[13001].get('hub.text2lines.400'), '1')
        self.assertEqual(ENV.window_props[10025].get('hub.text2lines.400'), '1')
