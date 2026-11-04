# coding=utf-8
"""
The smooth colour panel (the smooth_colour_panel setting, core.smooth_panel in the templates): the whole panel as
one small generated texture, which Kodi stretches over the screen with bilinear filtering, in place of the four
tinted corner layers of includes/background_panel.xml.tpl. One opaque draw instead of four masked ones (eight while
they crossfade), and the falloff is code rather than a mask asset.

The look is that of Plex's own apps: each corner's weight is 1 - distance / 0.95 in screen-normalised coordinates,
so a colour fades out 95% of the way across; starting from black, the colour is pulled towards the bottom right,
bottom left, top right and top left corners by their weights, in that order. The grid is fine enough that the GPU's
bilinear stretch shows no creases where its straight lines meet. The corner colours arrive already toned
(util.backgroundPanelCorners(), util.softPanelValue()).

The hero art goes over it through a cut-out of its own (masks/hero-art-cutout.png,
includes/default_background.xml.tpl), so wherever there's no art - none, still loading, mid-fade - this panel is
what shows.

Files go to the add-on's profile, named for their colours, so the same item reuses its file; Kodi loads them like
any other image (not through its texture cache: the template's image isn't background="true", and setImage() is
told not to cache). Old ones are pruned once per run.
"""
from __future__ import absolute_import

import hashlib
import math
import os
import struct
import zlib

from . import util

# The grid Kodi stretches: 60px between samples at 1080p, fine enough that the bilinear stretch of the cone-shaped
# falloff shows no creases
GRID_WIDTH = 32
GRID_HEIGHT = 18
# 1 / 0.95: a corner's colour is gone 95% of the way across
REACH = 1.052631
# The mean of masks/panel-dither.png, the multiplying dither the template draws this texture through (see
# docs/notes/panel-dither.py, which prints it): the colours are lifted by its inverse so the dither leaves the
# panel's brightness where it was.
DITHER_MEAN = 0.9649937269274994
# Bump when the texture's maths changes, so no old file is reused for the same colours
VERSION = 3

# Pruned once per run, oldest first, when the folder holds more than PRUNE_ABOVE
PRUNE_ABOVE = 400
PRUNE_TO = 200

# Pulled towards each corner in this order: (x, y) and its index in the PANEL_CORNERS order the colours
# arrive in (kodigui.BaseWindow.PANEL_CORNERS: topLeft, topRight, bottomLeft, bottomRight)
_CORNER_ORDER = ((1.0, 1.0, 3), (0.0, 1.0, 2), (1.0, 0.0, 1), (0.0, 0.0, 0))

_pruned = False


def _rgb(argb):
    """A corner's 'AARRGGBB' as 0-1 floats, or None for a corner without a colour."""
    if not argb or len(argb) != 8:
        return None
    try:
        return tuple(int(argb[i:i + 2], 16) / 255.0 for i in (2, 4, 6))
    except ValueError:
        return None


def grid(values):
    """The panel's colours at the centre of each grid texel, as rows of bytes (R, G, B per texel). values: the 4
    corners' 'AARRGGBB' in PANEL_CORNERS order, '' for a corner without one - left out, as a corner with no colour
    is transparent in the 4-layer panel."""
    corners = [_rgb(v) for v in values]
    pulls = [(cx, cy, corners[i]) for cx, cy, i in _CORNER_ORDER if corners[i] is not None]
    lift = 1.0 / DITHER_MEAN
    rows = []
    for j in range(GRID_HEIGHT):
        # texel centres: Kodi's bilinear stretch puts texel i's value at (i + 0.5) / width of the screen
        y = (j + 0.5) / GRID_HEIGHT
        row = bytearray()
        for i in range(GRID_WIDTH):
            x = (i + 0.5) / GRID_WIDTH
            r = g = b = 0.0
            for cx, cy, colour in pulls:
                w = 1.0 - math.hypot(x - cx, y - cy) * REACH
                if w <= 0.0:
                    continue
                r += (colour[0] - r) * w
                g += (colour[1] - g) * w
                b += (colour[2] - b) * w
            row.extend(min(255, int(round(c * lift * 255))) for c in (r, g, b))
        rows.append(bytes(row))
    return rows


def png(rows, width=GRID_WIDTH, height=GRID_HEIGHT):
    """8-bit RGB PNG bytes from rows of R, G, B bytes - Kodi's Python has no image library."""
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xFFFFFFFF)

    raw = b''.join(b'\x00' + row for row in rows)  # filter type 0 on every row
    return (b'\x89PNG\r\n\x1a\n' +
            chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)) +
            chunk(b'IDAT', zlib.compress(raw, 9)) +
            chunk(b'IEND', b''))


def folder():
    return os.path.join(util.PROFILE, 'panel')


def textureFor(values):
    """The texture file for the 4 corners' colours (PANEL_CORNERS order, 'AARRGGBB' or ''), written if it isn't there
    yet - or '' for no colours at all, which clears the panel to the window's own colour, as the 4-layer panel's
    transparent corners do."""
    if not any(values):
        return ''
    # named for the dither's mean too, which the colours are lifted by: a new dither never reuses an old file
    path = os.path.join(folder(), '{0}.png'.format(
        hashlib.sha1('{0}|{1!r}|{2}'.format(VERSION, DITHER_MEAN, '|'.join(values)).encode('utf-8')).hexdigest()[:20]))
    try:
        if os.path.exists(path):
            # used again: kept the longest by the pruning, which goes by age
            os.utime(path, None)
            return path
        if not os.path.isdir(folder()):
            os.makedirs(folder())
        prune()
        # written aside and moved into place, so Kodi never reads half a file
        tmp = path + '.tmp'
        with open(tmp, 'wb') as fp:
            fp.write(png(grid(values)))
        os.replace(tmp, path)
        return path
    except OSError as e:
        util.ERROR('Colour panel: no texture for {0}: {1}'.format(values, e), notify=False)
        return ''


def prune():
    """Once per run, before the run's first new file: the oldest files go once there are more than PRUNE_ABOVE.
    Not later - a window open now may repaint from a file it was given earlier (BaseWindow.repaintPanel())."""
    global _pruned
    if _pruned:
        return
    _pruned = True
    try:
        names = [n for n in os.listdir(folder()) if n.endswith('.png')]
        if len(names) <= PRUNE_ABOVE:
            return
        paths = sorted((os.path.join(folder(), n) for n in names), key=os.path.getmtime)
        for p in paths[:len(paths) - PRUNE_TO]:
            os.remove(p)
        util.DEBUG_LOG('Colour panel: pruned {0} old textures', len(paths) - PRUNE_TO)
    except OSError as e:
        util.LOG('Colour panel: pruning failed: {0}', e)
