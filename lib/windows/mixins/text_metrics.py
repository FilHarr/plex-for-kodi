# coding=utf-8
"""
Rendered-text width estimation for the skin's own fonts.

Kodi has no way to measure a string's actual rendered pixel width from Python (no
Control.getTextWidth() or similar), so anything that sizes a control to fit its own label - the
media info pills (media_info_pills.py), the Seasons button row's Play/Resume pill (subitems.py) -
has to estimate it here instead.

CHAR_WIDTHS are the real per-character advance widths read straight out of the skin's
Inter-Regular.ttf via fontTools, in font design units (2048/em), so they're point-size independent:
measureTextWidth() scales them by whichever size is asked for. Inter 4 Regular is the face behind
every regular font in the "Default" skin.plextuary fontset (since 2026-10-01 - was InterUI.ttf,
whose advances differed by up to ~2%), which lookandfeel.font in guisettings.xml confirms is what's
actually active; font8/font10/font12 are the same face at 18/23/25pt (xml/font.xml). Its digits and
colon are the tabular ones the skin's copy maps in (1328 / 550 - InterUI's exactly). Printable
ASCII plus the common typographic punctuation and accented letters - anything else (CJK, rarer
accents) falls back to CHAR_WIDTH_FALLBACK, an unweighted average across the ASCII table.

If the active Kodi "Skin Fonts" setting ever changes away from "Default", these stop matching the
real typeface in use and would need re-measuring against whichever font file replaces it.
"""

import math

UNITS_PER_EM = 2048

FONT8_POINT_SIZE = 18
FONT10_POINT_SIZE = 23
FONT12_POINT_SIZE = 25
# font20_title: Inter Bold at 20pt (measureTextWidth(bold=True)).
FONT20_TITLE_POINT_SIZE = 20

CHAR_WIDTHS = {
    ' ': 576, '!': 589, '"': 954, '#': 1297, '$': 1314, '%': 2011, '&': 1319, "'": 614,
    '(': 747, ')': 747, '*': 1026, '+': 1355, ',': 590, '-': 942, '.': 590, '/': 738,
    '0': 1328, '1': 1328, '2': 1328, '3': 1328, '4': 1328, '5': 1328, '6': 1328, '7': 1328,
    '8': 1328, '9': 1328, ':': 550, ';': 618, '<': 1355, '=': 1355, '>': 1355, '?': 1047,
    '@': 1978, 'A': 1413, 'B': 1340, 'C': 1496, 'D': 1478, 'E': 1231, 'F': 1209, 'G': 1528,
    'H': 1522, 'I': 550, 'J': 1169, 'K': 1376, 'L': 1158, 'M': 1850, 'N': 1543, 'O': 1566,
    'P': 1308, 'Q': 1566, 'R': 1318, 'S': 1314, 'T': 1322, 'U': 1524, 'V': 1413, 'W': 2018,
    'X': 1397, 'Y': 1390, 'Z': 1288, '[': 747, ']': 747, '^': 965, '_': 934, '`': 661,
    'a': 1150, 'b': 1254, 'c': 1170, 'd': 1254, 'e': 1194, 'f': 758, 'g': 1256, 'h': 1211,
    'i': 496, 'j': 496, 'k': 1124, 'l': 496, 'm': 1794, 'n': 1210, 'o': 1228, 'p': 1254,
    'q': 1254, 'r': 771, 's': 1081, 't': 670, 'u': 1211, 'v': 1151, 'w': 1676, 'x': 1118,
    'y': 1151, 'z': 1131, '{': 873, '|': 681, '}': 873, '~': 1355,
}

CHAR_WIDTH_FALLBACK = sum(CHAR_WIDTHS.values()) / len(CHAR_WIDTHS)

# Typographic punctuation and accented letters common in Plex summaries, added after the fallback
# is taken so it stays the ASCII average (2026-09-30). The ellipsis matters most: summaryForBox()
# ends every cut summary with one, and at the fallback's 1171 it was measured ~6px narrow at 20pt.
CHAR_WIDTHS.update({
    u'\u2019': 534, u'\u2018': 534, u'\u201c': 902, u'\u201d': 902, u'\u2014': 2048, u'\u2013': 1024,
    u'\u2026': 1770, u'\u2022': 1152, u'\u00e9': 1194, u'\u00e8': 1194, u'\u00ea': 1194, u'\u00eb': 1194,
    u'\u00e1': 1150, u'\u00e0': 1150, u'\u00e2': 1150, u'\u00e4': 1150, u'\u00f3': 1228, u'\u00f6': 1228,
    u'\u00f8': 1228, u'\u00fa': 1211, u'\u00fc': 1211, u'\u00ed': 496, u'\u00f1': 1210, u'\u00e7': 1170,
    u'\u00c9': 1231, u'\u00d6': 1566, u'\u00dc': 1524, u'\u00b7': 590, u'\u00a0': 576,
})

# The *_title fonts' face: Inter 4.001 Bold (skin.plextuary/fonts/Inter-Bold.ttf, extracted from
# the Inter .ttc - on request, 2026-10-01), a real bold in place of Kodi's synthetic one on InterUI.
# Same design units and the same vertical metrics as InterUI, so only the advances differ. Same
# characters as CHAR_WIDTHS; anything else falls back to their average. Digits and colon are the
# tabular ones (zero.tf..colon.tf) the skin's copy maps in place of the proportional defaults -
# Kodi applies no OpenType features, so tnum can't be switched on (on request, 2026-10-01).
BOLD_CHAR_WIDTHS = {
    ' ': 485, '!': 692, '"': 1130, '#': 1329, '$': 1341, '%': 2080, '&': 1376, "'": 694,
    '(': 772, ')': 772, '*': 1145, '+': 1390, ',': 684, '-': 958, '.': 684, '/': 795,
    '0': 1324, '1': 1324, '2': 1324, '3': 1324, '4': 1324, '5': 1324, '6': 1324, '7': 1324,
    '8': 1324, '9': 1324, ':': 550, ';': 702, '<': 1390, '=': 1390, '>': 1390, '?': 1146,
    '@': 2081, 'A': 1529, 'B': 1355, 'C': 1515, 'D': 1479, 'E': 1244, 'F': 1202, 'G': 1537,
    'H': 1530, 'I': 575, 'J': 1197, 'K': 1473, 'L': 1158, 'M': 1908, 'N': 1561, 'O': 1578,
    'P': 1327, 'Q': 1591, 'R': 1345, 'S': 1341, 'T': 1367, 'U': 1499, 'V': 1529, 'W': 2125,
    'X': 1512, 'Y': 1497, 'Z': 1360, '[': 772, ']': 772, '^': 997, '_': 975, '`': 748,
    'a': 1189, 'b': 1291, 'c': 1205, 'd': 1291, 'e': 1220, 'f': 815, 'g': 1294, 'h': 1275,
    'i': 555, 'j': 555, 'k': 1188, 'l': 555, 'm': 1869, 'n': 1275, 'o': 1256, 'p': 1291,
    'q': 1291, 'r': 834, 's': 1147, 't': 750, 'u': 1275, 'v': 1228, 'w': 1741, 'x': 1188,
    'y': 1233, 'z': 1173, '{': 960, '|': 761, '}': 960, '~': 1390, u'\u2019': 636, u'\u2018': 636,
    u'\u201c': 1106, u'\u201d': 1089, u'\u2014': 2048, u'\u2013': 1024, u'\u2026': 2052, u'\u2022': 971, u'\u00e9': 1220, u'\u00e8': 1220,
    u'\u00ea': 1220, u'\u00eb': 1220, u'\u00e1': 1189, u'\u00e0': 1189, u'\u00e2': 1189, u'\u00e4': 1189, u'\u00f3': 1256, u'\u00f6': 1256,
    u'\u00f8': 1256, u'\u00fa': 1275, u'\u00fc': 1275, u'\u00ed': 555, u'\u00f1': 1275, u'\u00e7': 1205, u'\u00c9': 1244, u'\u00d6': 1578,
    u'\u00dc': 1499, u'\u00b7': 684, u'\u00a0': 485,
}

BOLD_CHAR_WIDTH_FALLBACK = sum(BOLD_CHAR_WIDTHS.values()) / len(BOLD_CHAR_WIDTHS)


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


def measureTextWidth(text, point_size, scale=None, bold=False):
    """Estimated rendered width of `text` in skin pixels at `point_size`, the way Kodi lays it out on
    this screen: FreeType's hinting rounds each glyph's advance to whole pixels at the size the font
    is actually rendered at (point_size x scale), so that's summed and scaled back to skin pixels.

    bold: one of the *_title fonts, which are Inter Bold (BOLD_CHAR_WIDTHS) rather than this table's
    InterUI. They used to be InterUI with <style>bold</style>, which Kodi fakes by emboldening the
    outlines (CGUIFontTTF::SetGlyphStrength(), GUIFontTTF.cpp); a real bold face replaced that.
    (<style>lighten</style>, on the regular fonts, is the same call at -size/48; it isn't modelled,
    being under half a pixel at 1080p - where it rounds away - and only ever narrowing.)

    Used to sum the exact, unrounded advances, which matches only at high resolutions. At 1080p
    the rounding mostly goes up for this font, and 'English (TrueHD Atmos 7.1)' measured 238.4
    against the 241 Kodi actually lays out - 1px over its 240px audio-pill label box, so it scrolled
    on the 1080p AM6B but not on a 2160p PC (239.5 there, where each rounding error is halved in
    skin pixels). Live-reported 2026-09-24. Kerning still isn't modelled (it only narrows).

    scale: screen pixels per skin pixel; defaults to renderScale()."""
    if scale is None:
        scale = renderScale()
    size = point_size * scale
    widths, fallback = (BOLD_CHAR_WIDTHS, BOLD_CHAR_WIDTH_FALLBACK) if bold else (CHAR_WIDTHS, CHAR_WIDTH_FALLBACK)
    screen_px = sum(math.floor(widths.get(ch, fallback) * size / UNITS_PER_EM + 0.5) for ch in (text or ''))
    return screen_px / scale
