# coding=utf-8
"""
Each screen paints its own hero art (step 12 stage C in the navigation review): a new window's
first frame shows its own item's art or none, never the previous screen's, and the check that
skips an unchanged URL is per window. The real kodigui.BaseWindow methods are bound onto a small
double that records its property writes.

Importing lib.windows.library starts lib.player's monitor thread unless abort_requested is set
first - same guard the other lib.windows.* tests use for the same reason.
"""

from __future__ import absolute_import

from kodienv import ENV

ENV.abort_requested = True
from lib import util  # noqa: E402
from lib.windows import collection  # noqa: E402
from lib.windows import kodigui  # noqa: E402
from lib.windows import library_grid  # noqa: E402
from lib.windows import playlist  # noqa: E402
from lib.windows import tracks  # noqa: E402

from .base import KodiTestCase  # noqa: E402


class FakeItem(object):
    def __init__(self, name):
        self.name = name

    def get(self, key, default=None):
        return {'ratingKey': self.name}.get(key, default)


class FakeWindow(object):
    windowSetBackground = kodigui.BaseWindow.windowSetBackground
    paintInitialBackground = kodigui.BaseWindow.paintInitialBackground
    initialBackgroundURL = kodigui.BaseWindow.initialBackgroundURL
    backgroundItem = kodigui.BaseWindow.backgroundItem
    updateBackgroundFrom = kodigui.BaseWindow.updateBackgroundFrom
    updatePanelFrom = kodigui.BaseWindow.updatePanelFrom

    def __init__(self, item=None):
        self._bgURL = None
        self.item = item
        self.writes = []
        self.panels = []

    def setProperty(self, key, value):
        self.writes.append((key, value))

    def backgroundURLFor(self, ds):
        return ds.name and 'art:' + ds.name

    def _setPanelCorners(self, corners):
        self.panels.append(corners)


class OwnItemWindow(FakeWindow):
    def backgroundItem(self):
        return self.item


class SettingsCase(KodiTestCase):
    def setUp(self):
        super(SettingsCase, self).setUp()
        for name, value in (('dynamicBackgrounds', True), ('dbgCrossfade', True)):
            self.addCleanup(setattr, util.addonSettings, name, getattr(util.addonSettings, name))
            setattr(util.addonSettings, name, value)


class FirstPaintTest(SettingsCase):
    def test_a_window_that_knows_its_item_paints_its_art(self):
        window = OwnItemWindow(FakeItem('album'))
        window.paintInitialBackground()
        self.assertEqual([('background_static', 'art:album'), ('background', 'art:album')], window.writes)

    def test_a_window_without_an_item_clears_the_art(self):
        window = FakeWindow()
        window.paintInitialBackground()
        self.assertEqual([('background_static', ''), ('background', '')], window.writes)

    def test_an_item_without_art_clears_it_too(self):
        window = OwnItemWindow(FakeItem(''))
        window.paintInitialBackground()
        self.assertEqual([('background_static', ''), ('background', '')], window.writes)

    def test_the_previous_screens_art_is_never_painted(self):
        OwnItemWindow(FakeItem('before')).paintInitialBackground()
        window = FakeWindow()
        window.paintInitialBackground()
        self.assertNotIn('art:before', [v for _, v in window.writes])

    def test_the_screens_own_later_paint_of_the_same_art_is_skipped(self):
        window = OwnItemWindow(FakeItem('album'))
        window.paintInitialBackground()
        del window.writes[:]
        window.updateBackgroundFrom(FakeItem('album'))
        self.assertEqual([], window.writes)


class PerWindowSkipTest(SettingsCase):
    def test_another_window_showing_the_url_doesnt_skip_this_ones_write(self):
        first, second = FakeWindow(), FakeWindow()
        first.windowSetBackground('art:x')
        second.windowSetBackground('art:x')
        self.assertEqual([('background_static', 'art:x'), ('background', 'art:x')], second.writes)

    def test_the_same_url_again_on_one_window_is_skipped(self):
        window = FakeWindow()
        window.windowSetBackground('art:x')
        window.windowSetBackground('art:x')
        self.assertEqual(2, len(window.writes))

    def test_no_art_clears_both_layers(self):
        # Cleared, not a placeholder image: the hero box then draws nothing and the colour panel
        # shows through.
        window = FakeWindow()
        window.windowSetBackground('art:x')
        del window.writes[:]
        window.windowSetBackground(None)
        self.assertEqual([('background_static', ''), ('background', '')], window.writes)


class GridPanelOnlyTest(SettingsCase):
    def test_a_grid_press_writes_the_panel_and_no_art(self):
        window = FakeWindow()
        window.updatePanelFrom(FakeItem('movie'))
        self.assertEqual(1, len(window.panels))
        self.assertEqual([], window.writes)

    def test_the_grid_code_has_no_art_writes_left(self):
        import inspect
        source = inspect.getsource(library_grid)
        self.assertNotIn('updateBackgroundFrom(', source)
        self.assertNotIn('windowSetBackground(', source)


class ScreensOwnItemTest(KodiTestCase):
    def test_album_and_collection_name_their_own_item(self):
        album = object.__new__(tracks.AlbumWindow)
        album.__dict__['album'] = 'the album'
        self.assertEqual('the album', tracks.AlbumWindow.backgroundItem(album))
        coll = object.__new__(collection.CollectionWindow)
        coll.__dict__['collection'] = 'the collection'
        self.assertEqual('the collection', collection.CollectionWindow.backgroundItem(coll))

    def test_playlist_paints_its_composite_first(self):
        class Composite(object):
            def __bool__(self):
                return True
            __nonzero__ = __bool__

            def asTranscodedImageURL(self, w, h, **kwargs):
                return 'composite %dx%d' % (w, h)

        class FakePlaylist(object):
            composite = Composite()

        window = object.__new__(playlist.PlaylistWindow)
        window.__dict__['playlist'] = FakePlaylist()
        orig = util.addonSettings.backgroundResolutionScalePerc
        util.addonSettings.backgroundResolutionScalePerc = 100
        self.addCleanup(setattr, util.addonSettings, 'backgroundResolutionScalePerc', orig)
        self.assertEqual('composite %dx%d' % kodigui.HERO_ART_SIZE,
                         playlist.PlaylistWindow.initialBackgroundURL(window))
