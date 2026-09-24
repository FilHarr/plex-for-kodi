# coding=utf-8
"""
lib/windows/mixins/text_metrics.measureTextWidth() models Kodi's layout: each glyph's advance is
rounded to whole pixels at the size the font is rendered at on this screen, then scaled back to skin
pixels. Summing exact advances instead under-measured at 1080p: 'English (TrueHD Atmos 7.1)' came to
238.4 against the 241 Kodi lays out, overflowing its 240px audio-pill label box on the 1080p AM6B
only (live-reported 2026-09-24).
"""

from __future__ import absolute_import

from kodienv import ENV

ENV.abort_requested = True
from lib.windows.mixins import text_metrics  # noqa: E402
from lib.windows.mixins.media_info_pills import MediaInfoPillsMixin  # noqa: E402

from .base import KodiTestCase  # noqa: E402

ATMOS = 'English (TrueHD Atmos 7.1)'


class MeasureTextWidthTest(KodiTestCase):
    def test_rounds_per_glyph_at_the_render_size(self):
        self.assertEqual(241, text_metrics.measureTextWidth(ATMOS, text_metrics.FONT8_POINT_SIZE, scale=1.0))
        self.assertEqual(239.5, text_metrics.measureTextWidth(ATMOS, text_metrics.FONT8_POINT_SIZE, scale=2.0))

    def test_rounds_half_up_like_freetype(self):
        # '.' is 550 units: 4.834px at 18px -> 5; ' ' likewise. A 1024-unit glyph at 1px/unit-ish
        # scale lands on exactly .5 and must round up, not to even.
        self.assertEqual(5, text_metrics.measureTextWidth('.', 18, scale=1.0))
        original = dict(text_metrics.CHAR_WIDTHS)
        try:
            text_metrics.CHAR_WIDTHS['~'] = 1024  # 1024 * 1 / 2048 = 0.5
            self.assertEqual(1, text_metrics.measureTextWidth('~', 1, scale=1.0))
        finally:
            text_metrics.CHAR_WIDTHS.clear()
            text_metrics.CHAR_WIDTHS.update(original)

    def test_default_scale_follows_the_display_resolution(self):
        from lib import util
        original = util.DISPLAY_RESOLUTION
        try:
            util.DISPLAY_RESOLUTION = [1920, 1080]
            self.assertEqual(241, text_metrics.measureTextWidth(ATMOS, 18))
            util.DISPLAY_RESOLUTION = [3840, 2160]
            self.assertEqual(239.5, text_metrics.measureTextWidth(ATMOS, 18))
        finally:
            util.DISPLAY_RESOLUTION = original


class _Ctrl(object):
    def __init__(self):
        self.width = None
        self.pos = (0, 0)

    def setWidth(self, width):
        self.width = width

    def setPosition(self, x, y):
        self.pos = (x, y)

    def getPosition(self):
        return self.pos


class AtmosPillTest(KodiTestCase):
    def test_the_audio_label_fits_at_1080p(self):
        from lib import util
        original = util.DISPLAY_RESOLUTION
        util.DISPLAY_RESOLUTION = [1920, 1080]
        try:
            pills = MediaInfoPillsMixin()
            group, image, label, icon = _Ctrl(), _Ctrl(), _Ctrl(), _Ctrl()
            pills.resizeInfoPill(group, image, label, ATMOS, pills.AUDIO_PILL_MAX_WIDTH, 785, icon_ctrl=icon)
        finally:
            util.DISPLAY_RESOLUTION = original
        self.assertGreaterEqual(label.width, 241, 'label box must hold the 241px Kodi lays out at 1080p')
