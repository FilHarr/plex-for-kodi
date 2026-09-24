# coding=utf-8
"""
Rendered-text width estimation for the skin's own fonts.

Kodi has no way to measure a string's actual rendered pixel width from Python (no
Control.getTextWidth() or similar), so anything that sizes a control to fit its own label - the
media info pills (media_info_pills.py), the Seasons button row's Play/Resume pill (subitems.py) -
has to estimate it here instead.

CHAR_WIDTHS are the real per-character advance widths read straight out of InterUI.ttf via
fontTools, in font design units (2048/em), so they're point-size independent: measureTextWidth()
scales them by whichever size is asked for. InterUI is the typeface behind every font in the
"Default" skin.plextuary fontset, which lookandfeel.font in guisettings.xml confirms is what's
actually active; font8/font10/font12 are the same face at 18/23/25pt (xml/font.xml). Printable
ASCII only - anything else (accented language names, CJK) falls back to CHAR_WIDTH_FALLBACK, an
unweighted average across the table.

If the active Kodi "Skin Fonts" setting ever changes away from "Default", these stop matching the
real typeface in use and would need re-measuring against whichever font file replaces it.
"""

import math

UNITS_PER_EM = 2048

FONT8_POINT_SIZE = 18
FONT10_POINT_SIZE = 23
FONT12_POINT_SIZE = 25

CHAR_WIDTHS = {
    ' ': 550, '!': 589, '"': 954, '#': 1297, '$': 1314, '%': 2011, '&': 1319, "'": 614,
    '(': 800, ')': 800, '*': 1328, '+': 1328, ',': 550, '-': 1328, '.': 550, '/': 738,
    '0': 1328, '1': 1328, '2': 1328, '3': 1328, '4': 1328, '5': 1328, '6': 1328, '7': 1328,
    '8': 1328, '9': 1328, ':': 550, ';': 550, '<': 1328, '=': 1328, '>': 1328, '?': 1047,
    '@': 1978, 'A': 1413, 'B': 1340, 'C': 1496, 'D': 1478, 'E': 1231, 'F': 1209, 'G': 1528,
    'H': 1522, 'I': 550, 'J': 1169, 'K': 1376, 'L': 1158, 'M': 1850, 'N': 1543, 'O': 1566,
    'P': 1308, 'Q': 1566, 'R': 1318, 'S': 1314, 'T': 1322, 'U': 1524, 'V': 1413, 'W': 2018,
    'X': 1397, 'Y': 1390, 'Z': 1288, '[': 800, ']': 800, '^': 965, '_': 934,
    '`': 661, 'a': 1150, 'b': 1254, 'c': 1170, 'd': 1254, 'e': 1194, 'f': 758, 'g': 1256,
    'h': 1211, 'i': 496, 'j': 496, 'k': 1124, 'l': 496, 'm': 1794, 'n': 1210, 'o': 1228,
    'p': 1254, 'q': 1254, 'r': 771, 's': 1081, 't': 670, 'u': 1211, 'v': 1151, 'w': 1676,
    'x': 1118, 'y': 1151, 'z': 1131, '{': 800, '|': 681, '}': 800, '~': 1328,
}

CHAR_WIDTH_FALLBACK = sum(CHAR_WIDTHS.values()) / len(CHAR_WIDTHS)


# The skin's own coordinate height (1080i): font sizes and control widths are in these pixels.
SKIN_HEIGHT = 1080


def renderScale():
    """Screen pixels per skin pixel. Kodi loads a font at point_size x this (so 36px on a 2160p
    screen, 18px at 1080p for font8) and lays text out at that size. Uses the resolution read once
    at startup (util.DISPLAY_RESOLUTION) rather than asking Kodi per measurement: every Python GUI
    call feeds Kodi's frame throttle, and the resolution very rarely changes mid-session. Kodi's
    skin zoom setting also scales fonts and isn't accounted for (default 0%)."""
    try:
        from lib import util
        return util.DISPLAY_RESOLUTION[1] / float(SKIN_HEIGHT) or 1.0
    except Exception:
        return 1.0


def measureTextWidth(text, point_size, scale=None):
    """Estimated rendered width of `text` in skin pixels at `point_size`, the way Kodi lays it out on
    this screen: FreeType's hinting rounds each glyph's advance to whole pixels at the size the font
    is actually rendered at (point_size x scale), so that's summed and scaled back to skin pixels.

    Used to sum the exact, unrounded advances, which matches only at high resolutions. At 1080p
    the rounding mostly goes up for this font, and 'English (TrueHD Atmos 7.1)' measured 238.4
    against the 241 Kodi actually lays out - 1px over its 240px audio-pill label box, so it scrolled
    on the 1080p AM6B but not on a 2160p PC (239.5 there, where each rounding error is halved in
    skin pixels). Live-reported 2026-09-24. Kerning still isn't modelled (it only narrows).

    scale: screen pixels per skin pixel; defaults to renderScale()."""
    if scale is None:
        scale = renderScale()
    size = point_size * scale
    screen_px = sum(math.floor(CHAR_WIDTHS.get(ch, CHAR_WIDTH_FALLBACK) * size / UNITS_PER_EM + 0.5)
                    for ch in (text or ''))
    return screen_px / scale
