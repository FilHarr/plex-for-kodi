# coding=utf-8
"""
The colour panel's corners (includes/default_background.xml.tpl) are painted from Python with
setColorDiffuse() rather than read from $INFO[Window.Property(...)]: Kodi resolves an $INFO colour
against the topmost modal dialog while one is open, so every picker or dialog turned the panel dark.
The real kodigui.BaseWindow methods are bound onto a small double whose controls record their colour.

Importing lib.windows.* starts lib.player's monitor thread unless abort_requested is set first - same
guard the other lib.windows.* tests use for the same reason.
"""

from __future__ import absolute_import

from kodienv import ENV

ENV.abort_requested = True
from lib import util  # noqa: E402
from lib.windows import kodigui, library  # noqa: E402

from .base import KodiTestCase  # noqa: E402


class FakeControl(object):
    def __init__(self):
        self.colour = None

    def setColorDiffuse(self, colour):
        self.colour = colour


class FakeWindow(object):
    PANEL_CORNERS = kodigui.BaseWindow.PANEL_CORNERS
    PANEL_CORNER_CONTROLS = kodigui.BaseWindow.PANEL_COVER_CONTROLS
    PANEL_CROSSFADE = True
    _setPanelCorners = kodigui.BaseWindow._setPanelCorners
    _paintPanelLayer = kodigui.BaseWindow._paintPanelLayer
    repaintPanel = kodigui.BaseWindow.repaintPanel

    def __init__(self, loaded=True, cover=False):
        self.loaded = loaded
        self.props = {}
        # the panel's own corners, and the Recommended view's cover copy's when it has one
        copies = [layer[i] for layer in self.PANEL_CORNER_CONTROLS.values() for i in range(2 if cover else 1)]
        self.controls = dict((cid, FakeControl()) for ids in copies for cid in ids)
        self._panelLayer = 'a'
        self._panelColors = ('', '', '', '')
        self._panelLayerColors = {'a': ('', '', '', ''), 'b': ('', '', '', '')}
        self._absentPanelCopies = set()
        self.started = loaded
        self.asked = []

    def setProperty(self, key, value):
        self.props[key] = value

    def getControl(self, cid):
        self.asked.append(cid)
        if not self.loaded or cid not in self.controls:
            raise RuntimeError('Non-Existent Control {0}'.format(cid))
        return self.controls[cid]

    def colours(self, layer, copy=0):
        return [self.controls[cid].colour for cid in self.PANEL_CORNER_CONTROLS[layer][copy]]


CORNERS = {'topLeft': 'FF101010', 'topRight': 'FF202020', 'bottomLeft': 'FF303030', 'bottomRight': 'FF404040'}


class PanelColoursTest(KodiTestCase):
    def setUp(self):
        super(PanelColoursTest, self).setUp()
        self.addCleanup(setattr, util.addonSettings, 'dbgCrossfade', util.addonSettings.dbgCrossfade)
        util.addonSettings.dbgCrossfade = True

    def test_new_colours_go_on_the_hidden_layer_which_is_then_shown(self):
        w = FakeWindow()
        w._setPanelCorners(CORNERS)
        self.assertEqual('b', w.props['background_panel_layer'])
        self.assertEqual(['FF101010', 'FF202020', 'FF303030', 'FF404040'], w.colours('b'))
        self.assertEqual([None] * 4, w.colours('a'))

        w._setPanelCorners({'topLeft': 'FF999999'})
        self.assertEqual('a', w.props['background_panel_layer'])
        self.assertEqual('FF999999', w.colours('a')[0])

    def test_a_corner_without_a_colour_is_transparent(self):
        w = FakeWindow()
        w._setPanelCorners({'topLeft': 'FF101010'})
        self.assertEqual(['FF101010', '00000000', '00000000', '00000000'], w.colours('b'))

    def test_no_property_carries_a_corner_colour(self):
        w = FakeWindow()
        w._setPanelCorners(CORNERS)
        self.assertEqual(['background_panel_layer'], list(w.props))

    def test_colours_set_before_the_controls_exist_are_painted_at_first_init(self):
        w = FakeWindow(loaded=False)
        w._setPanelCorners(CORNERS)
        self.assertEqual([None] * 4, w.colours('b'))

        w.loaded = True
        w.repaintPanel()
        self.assertEqual(['FF101010', 'FF202020', 'FF303030', 'FF404040'], w.colours('b'))
        # layer a never had colours: left as the template starts it (transparent), not asked for
        self.assertEqual([None] * 4, w.colours('a'))

    def test_without_crossfade_layer_a_is_painted_and_shown(self):
        util.addonSettings.dbgCrossfade = False
        w = FakeWindow()
        w._setPanelCorners(CORNERS)
        self.assertEqual('a', w.props['background_panel_layer'])
        self.assertEqual(['FF101010', 'FF202020', 'FF303030', 'FF404040'], w.colours('a'))

    def test_the_recommended_views_cover_copy_is_painted_the_same(self):
        w = FakeWindow(cover=True)
        w._setPanelCorners(CORNERS)
        self.assertEqual(w.colours('b'), w.colours('b', copy=1))
        self.assertEqual(['FF101010', 'FF202020', 'FF303030', 'FF404040'], w.colours('b', copy=1))

        w._setPanelCorners({'topLeft': 'FF999999'})
        self.assertEqual(['FF999999', '00000000', '00000000', '00000000'], w.colours('a', copy=1))

    def test_a_window_without_the_panel_is_left_alone(self):
        w = FakeWindow()
        w.controls = {}
        w._setPanelCorners(CORNERS)  # no exception
        w.repaintPanel()

    def test_only_recommended_asks_for_the_cover_copy(self):
        # Kodi logs every getControl() miss: the cover copy is on Recommended alone
        self.assertEqual(kodigui.BaseWindow.PANEL_COVER_CONTROLS, library.RecommendedWindow.PANEL_CORNER_CONTROLS)
        for layer in ('a', 'b'):
            self.assertEqual(1, len(kodigui.BaseWindow.PANEL_CORNER_CONTROLS[layer]))
            self.assertEqual(kodigui.BaseWindow.PANEL_CORNER_CONTROLS[layer][0],
                             kodigui.BaseWindow.PANEL_COVER_CONTROLS[layer][0])

    def test_a_first_init_repaint_of_nothing_asks_for_nothing(self):
        # user select has no panel: its repaint at first init logged an error for each layer
        w = FakeWindow()
        w.controls = {}
        w.repaintPanel()
        self.assertEqual([], w.asked)

    def test_a_copy_a_loaded_window_hasnt_got_isnt_asked_for_again(self):
        # Kodi logs every getControl() miss
        w = FakeWindow()
        w._setPanelCorners(CORNERS)
        cover = kodigui.BaseWindow.PANEL_COVER_CONTROLS['b'][1][0]
        self.assertEqual(1, w.asked.count(cover))
        w._setPanelCorners(CORNERS)
        w._setPanelCorners(CORNERS)
        self.assertEqual(1, w.asked.count(cover))
        self.assertEqual(['FF101010', 'FF202020', 'FF303030', 'FF404040'], w.colours('b'))

    def test_a_copy_missing_before_the_window_loads_is_tried_again(self):
        w = FakeWindow(loaded=False)
        w._setPanelCorners(CORNERS)
        w.loaded = w.started = True
        w.repaintPanel()
        self.assertEqual(['FF101010', 'FF202020', 'FF303030', 'FF404040'], w.colours('b'))

    def test_the_static_panel_paints_layer_a_and_sets_no_property(self):
        # the music screens': one layer, always shown - nothing to flip, nothing reading the property
        w = FakeWindow()
        w.PANEL_CROSSFADE = False
        w._setPanelCorners(CORNERS)
        w._setPanelCorners({'topLeft': 'FF999999'})
        self.assertEqual(['FF999999', '00000000', '00000000', '00000000'], w.colours('a'))
        self.assertEqual([None] * 4, w.colours('b'))
        self.assertEqual({}, w.props)
