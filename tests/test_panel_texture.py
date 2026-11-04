# coding=utf-8
"""
The colour panel (lib/panel_texture.py): the whole panel as one small generated texture, set on one image with
setImage() (includes/background_panel.xml.tpl); and the hero art over it through a cut-out
(includes/default_background.xml.tpl).

Importing lib.windows.* starts lib.player's monitor thread unless abort_requested is set first - same
guard the other lib.windows.* tests use for the same reason.
"""

from __future__ import absolute_import

import copy
import io
import math
import os
import xml.etree.ElementTree as ET

from kodienv import ENV

ENV.abort_requested = True
from PIL import Image  # noqa: E402

from lib import panel_texture, util  # noqa: E402
from lib.templating.context import TEMPLATE_CONTEXTS  # noqa: E402
from lib.windows import kodigui, library  # noqa: E402

from .base import KodiTestCase, MEDIA_DIR, make_engine  # noqa: E402
from .test_templates import render_theme  # noqa: E402

# PANEL_CORNERS order: topLeft, topRight, bottomLeft, bottomRight
VALUES = ('FF400000', 'FF004000', 'FF000040', 'FF404040')


class FakeImage(object):
    def __init__(self):
        self.images = []

    def setImage(self, path, useCache=True):
        self.images.append((path, useCache))


class FakeWindow(object):
    PANEL_CORNERS = kodigui.BaseWindow.PANEL_CORNERS
    PANEL_TEXTURE_CONTROLS = kodigui.BaseWindow.PANEL_TEXTURE_CONTROLS
    _setPanelCorners = kodigui.BaseWindow._setPanelCorners
    _paintPanelTexture = kodigui.BaseWindow._paintPanelTexture
    repaintPanel = kodigui.BaseWindow.repaintPanel

    def __init__(self, loaded=True, cover=False):
        if cover:
            self.PANEL_TEXTURE_CONTROLS = kodigui.BaseWindow.PANEL_COVER_TEXTURE_CONTROLS
        self.loaded = loaded
        self.started = loaded
        self.controls = dict((cid, FakeImage()) for cid in self.PANEL_TEXTURE_CONTROLS)
        self._panelColors = ('', '', '', '')
        self._panelTexture = ''
        self._absentPanelCopies = set()
        self.props = {}
        self.asked = []

    def setProperty(self, key, value):
        self.props[key] = value

    def getControl(self, cid):
        self.asked.append(cid)
        if not self.loaded or cid not in self.controls:
            raise RuntimeError('Non-Existent Control {0}'.format(cid))
        return self.controls[cid]

    def image(self, cid=2109):
        images = self.controls[cid].images
        return images[-1][0] if images else None


class PanelTextureCase(KodiTestCase):
    def setUp(self):
        super(PanelTextureCase, self).setUp()
        self.addCleanup(setattr, util, 'PROFILE', util.PROFILE)
        self.addCleanup(setattr, panel_texture, '_pruned', panel_texture._pruned)
        util.PROFILE = self.mktemp('profile')
        panel_texture._pruned = False


class TextureTest(PanelTextureCase):
    def pixels(self, values):
        with open(panel_texture.textureFor(values), 'rb') as fp:
            im = Image.open(io.BytesIO(fp.read()))
            im.load()
        return im

    def test_the_texture_is_a_grid_png_kodi_can_load(self):
        im = self.pixels(VALUES)
        self.assertEqual(('PNG', 'RGB', (panel_texture.GRID_WIDTH, panel_texture.GRID_HEIGHT)),
                         (im.format, im.mode, im.size))

    def test_each_corner_is_its_own_colour(self):
        im = self.pixels(VALUES)
        w, h = im.size
        tl, tr, bl, br = im.getpixel((0, 0)), im.getpixel((w - 1, 0)), im.getpixel((0, h - 1)), im.getpixel((w - 1, h - 1))
        self.assertEqual(0, tl.index(max(tl)))  # red
        self.assertEqual(1, tr.index(max(tr)))  # green
        self.assertEqual(2, bl.index(max(bl)))  # blue
        self.assertTrue(abs(br[0] - br[1]) <= 2 and abs(br[1] - br[2]) <= 2)  # grey

    def test_a_corner_reaches_almost_across_and_the_middle_still_has_colour(self):
        # the falloff: gone 95% of the way across, so the far side of the screen has none of it, and the middle,
        # where every corner is faint, isn't left black
        im = self.pixels(('FFFF0000', '', '', ''))
        w, h = im.size
        self.assertEqual((0, 0, 0), im.getpixel((w - 1, h - 1)))
        self.assertGreater(im.getpixel((int(w * 0.9), 0))[0], 0)
        self.assertEqual(0, im.getpixel((w - 1, 0))[0])
        self.assertGreater(im.getpixel((w // 2, h // 2))[0], 40)

    def test_the_dithers_darkening_is_lifted_back_out(self):
        im = self.pixels(('FF808080', '', '', ''))
        # the top left texel's centre is a little way in, where the corner's weight is just under 1
        weight = 1 - math.hypot(0.5 / panel_texture.GRID_WIDTH, 0.5 / panel_texture.GRID_HEIGHT) * panel_texture.REACH
        self.assertAlmostEqual(0x80 * weight / panel_texture.DITHER_MEAN, im.getpixel((0, 0))[0], delta=0.6)

    def test_the_dither_mean_matches_the_asset(self):
        with Image.open(os.path.join(MEDIA_DIR, 'script.plex', 'masks', 'panel-dither.png')) as im:
            self.assertEqual((1920, 1080), im.size)
            grey = im.convert('L')
            pixels = grey.tobytes()
        self.assertAlmostEqual(panel_texture.DITHER_MEAN, sum(pixels) / float(len(pixels)) / 255, places=6)

    def test_the_hero_arts_cutout(self):
        with Image.open(os.path.join(MEDIA_DIR, 'script.plex', 'masks', 'hero-art-cutout.png')) as cut:
            self.assertEqual(((1280, 720), 'RGBA'), (cut.size, cut.mode))
            # white: it only sets the art's opacity
            self.assertEqual(((255, 255),) * 3, cut.convert('RGB').getextrema())
            alpha = cut.getchannel('A')
            # the art in full at the screen's top right corner, gone at the box's left and bottom edges
            self.assertEqual(255, alpha.getpixel((1279, 0)))
            self.assertEqual(0, alpha.getpixel((0, 0)))
            self.assertEqual(0, alpha.getpixel((1279, 719)))
            # nothing of the art along those edges, which would draw them as lines on every item change
            self.assertEqual((0, 0), alpha.crop((0, 0, 1, 720)).getextrema())
            self.assertEqual((0, 0), alpha.crop((0, 719, 1280, 720)).getextrema())
            # ~31% of the art over the middle of the box, dithered by a few levels (docs/notes/hero-art-cutout.py)
            middle = alpha.crop((600, 330, 680, 390))
            self.assertAlmostEqual(78, sum(middle.tobytes()) / float(len(middle.tobytes())), delta=1)
            # the fully shown and fully gone areas aren't dithered
            self.assertEqual((255, 255), alpha.crop((1260, 0, 1280, 20)).getextrema())
            self.assertEqual((0, 0), alpha.crop((0, 700, 20, 720)).getextrema())

    def test_no_colours_is_no_texture(self):
        self.assertEqual('', panel_texture.textureFor(('', '', '', '')))

    def test_the_same_colours_reuse_their_file(self):
        first = panel_texture.textureFor(VALUES)
        self.assertEqual(first, panel_texture.textureFor(VALUES))
        self.assertNotEqual(first, panel_texture.textureFor(('FF400000', 'FF004000', 'FF000040', 'FF404041')))
        self.assertEqual(2, len(os.listdir(panel_texture.folder())))

    def test_old_files_are_pruned_once_per_run(self):
        folder = panel_texture.folder()
        os.makedirs(folder)
        for i in range(panel_texture.PRUNE_ABOVE + 5):
            path = os.path.join(folder, 'old{0:04d}.png'.format(i))
            open(path, 'wb').close()
            os.utime(path, (1000 + i, 1000 + i))
        panel_texture.textureFor(VALUES)
        left = sorted(os.listdir(folder))
        self.assertEqual(panel_texture.PRUNE_TO + 1, len(left))
        # the newest of the old ones stay
        self.assertIn('old{0:04d}.png'.format(panel_texture.PRUNE_ABOVE + 4), left)
        self.assertNotIn('old0000.png', left)
        # and not again this run
        open(os.path.join(folder, 'late.png'), 'wb').close()
        for i in range(panel_texture.PRUNE_ABOVE):
            open(os.path.join(folder, 'more{0:04d}.png'.format(i)), 'wb').close()
        panel_texture.textureFor(('FF101010', '', '', ''))
        self.assertIn('late.png', os.listdir(folder))


class SoftCurveTest(PanelTextureCase):
    def test_dark_corners_are_left_alone_and_bright_ones_rolled_off(self):
        self.assertEqual(0.1, util.softPanelValue(0.1))
        values = [util.softPanelValue(v / 255.0) * 255 for v in (102, 128, 178, 217, 255)]
        self.assertEqual(sorted(values), values)
        self.assertLess(values[-1], (util.SOFT_PANEL_KNEE + util.SOFT_PANEL_ROLLOFF) * 255)
        self.assertEqual([93, 106, 119, 123], [int(round(v)) for v in values[:4]])

    def test_the_corners_use_the_curve(self):
        # a bright corner rolled off, not capped at 0.3 (which gave FF4C2626)
        self.assertEqual('FF7C3E3E', util.backgroundPanelCorners({'topLeft': 'ff8080'})['topLeft'])


class WindowTest(PanelTextureCase):
    def test_colours_go_onto_the_one_image(self):
        w = FakeWindow()
        w._setPanelCorners(dict(zip(w.PANEL_CORNERS, VALUES)))
        self.assertEqual(panel_texture.textureFor(VALUES), w.image())
        # not through Kodi's texture cache, and no layer property: the image fades by itself
        self.assertEqual([False], [cache for _, cache in w.controls[2109].images])
        self.assertEqual({}, w.props)

    def test_no_colours_clear_it(self):
        w = FakeWindow()
        w._setPanelCorners(dict(zip(w.PANEL_CORNERS, VALUES)))
        w._setPanelCorners({})
        self.assertEqual('', w.image())

    def test_a_texture_set_before_the_controls_exist_is_painted_at_first_init(self):
        w = FakeWindow(loaded=False)
        w._setPanelCorners(dict(zip(w.PANEL_CORNERS, VALUES)))
        self.assertIsNone(w.image())
        w.loaded = w.started = True
        w.repaintPanel()
        self.assertEqual(panel_texture.textureFor(VALUES), w.image())

    def test_a_first_init_repaint_of_nothing_asks_for_nothing(self):
        w = FakeWindow()
        w.repaintPanel()
        self.assertEqual([], w.asked)

    def test_the_recommended_views_cover_copy_gets_the_same_texture(self):
        # and only there: Kodi logs every getControl() of a control a window hasn't got
        self.assertEqual((2109,), kodigui.BaseWindow.PANEL_TEXTURE_CONTROLS)
        self.assertEqual(kodigui.BaseWindow.PANEL_COVER_TEXTURE_CONTROLS, library.RecommendedWindow.PANEL_TEXTURE_CONTROLS)
        w = FakeWindow(cover=True)
        w._setPanelCorners(dict(zip(w.PANEL_CORNERS, VALUES)))
        self.assertEqual(w.image(2109), w.image(2119))

    def test_a_window_without_the_panel_is_asked_once(self):
        w = FakeWindow()
        w.controls = {}
        w._setPanelCorners(dict(zip(w.PANEL_CORNERS, VALUES)))
        w._setPanelCorners({'topLeft': 'FF999999'})
        self.assertEqual([2109], w.asked)


class TemplateTest(KodiTestCase):
    """The panel is one image, in every window that has it, with the hero art over it through its cut-out."""
    MAIN_WINDOWS = ("posters", "ar16x9", "pre_play", "episodes", "recommended", "photo", "music_player",
                    "music_current_playlist")
    CORNER_IDS = set(str(i) for i in list(range(2101, 2109)) + list(range(2111, 2119)))

    def render(self):
        return render_theme(make_engine(self.mktemp(), context=copy.deepcopy(TEMPLATE_CONTEXTS)), "modern-colored")

    def test_the_panel_is_one_image(self):
        rendered = self.render()
        for window in self.MAIN_WINDOWS:
            root = ET.fromstring(rendered[window])
            ids = [c.get("id") for c in root.iter("control")]
            with self.subTest(window=window):
                self.assertFalse(self.CORNER_IDS & set(ids))
                self.assertEqual(1, ids.count("2109"))
                self.assertEqual(1 if window == "recommended" else 0, ids.count("2119"))
                image = [c for c in root.iter("control") if c.get("id") == "2109"][0]
                self.assertEqual("script.plex/masks/panel-dither.png", image.find("texture").get("diffuse"))
                self.assertEqual(("1920", "1080"), (image.findtext("width"), image.findtext("height")))
                # the music screens' static panel swaps without a fade
                static = window.startswith("music_")
                self.assertEqual(None if static else "200", image.findtext("fadetime"))

    def test_the_hero_art_is_the_box_over_the_panel_through_its_cutout(self):
        rendered = self.render()
        for window in ("pre_play", "episodes", "recommended", "collection"):
            root = ET.fromstring(rendered[window])
            controls = list(root.iter("control"))
            art = [c for c in controls if "Window.Property(background)" in (c.findtext("texture") or "")]
            with self.subTest(window=window):
                self.assertEqual(2 if window == "recommended" else 1, len(art))
                for a in art:
                    # 1280x720 at x=640, unzoomed, full strength, its cut-out pinned to the box
                    self.assertEqual(("640", "0", "1280", "720"),
                                     tuple(a.findtext(k) for k in ("posx", "posy", "width", "height")))
                    self.assertEqual("script.plex/masks/hero-art-cutout.png", a.find("texture").get("diffuse"))
                    self.assertIsNone(a.findtext("colordiffuse"))
                    self.assertEqual("false", a.find("aspectratio").get("scalediffuse"))
                # over the panel, and nothing drawn back over the art: a second fading layer inside the box drew
                # its edges as lines on every item change
                ids = [c.get("id") for c in controls]
                self.assertLess(ids.index("2109"), controls.index(art[0]))
                self.assertFalse({"2110", "2120"} & set(ids))

