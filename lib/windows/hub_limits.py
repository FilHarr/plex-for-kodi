# coding=utf-8
"""How far a Recommended row and its "See more" grid reach (spec: ~/.claude/plans/see-all-grid.md,
the user, 2026-10-09).

- Recently Released and Recently Watched rows (films, episodes, other videos, Recently Played
  Music) are cut to a date window, see_more_recent_months - 3, 6, 9 or 12 months, 12 by default.
  The row and its grid both: the row keeps the items its window holds, and the grid lists the same
  window from the server (gridKey).
- Recently Added rows keep their items; their grid holds at most see_more_added_limit (50 by
  default). Plex's server stops Recently Added TV and Photos at 50 whatever is asked.
- Every other row reaches as far as the server's list does.

A row has "See more" only when its list, so limited, holds more than its own HUB_ROW_MAX_ITEMS.

Why the windows: Recently Released Episodes is every episode by air date (7,148 on Animal), where
Plex already windows Recently Released Movies to a year (its key carries originallyAvailableAt>=-1y);
a heavy watcher's Recently Watched Episodes runs to thousands too (3,209). Recently Added rows empty
under a window (Music: none in a year), so they get a count instead. Checked live 2026-10-09."""
from __future__ import absolute_import

import datetime
import re
import time

from lib import util

# Rows cut to a date window: the base identifier (no section suffix) and the date it's sorted by
WINDOW_ROWS = {
    'movie.recentlyreleased': 'originallyAvailableAt',
    'tv.recentlyaired': 'originallyAvailableAt',
    'movie.recentlyviewed': 'lastViewedAt',
    'tv.recentlyviewed': 'lastViewedAt',
    'video.recentlyviewed': 'lastViewedAt',
    'music.recent.played': 'lastViewedAt',
}
# Rows whose grid holds at most see_more_added_limit items
ADDED_ROWS = frozenset((
    'movie.recentlyadded', 'tv.recentlyadded', 'music.recent.added', 'photo.recent', 'video.recent',
    'home.movies.recent', 'home.television.recent', 'home.music.recent', 'home.photos.recent',
    'home.videos.recent',
))

DEFAULT_MONTHS = 12
DEFAULT_ADDED_LIMIT = 50


def baseIdentifier(hub):
    """movie.recentlyadded.22 -> movie.recentlyadded: the row without its library (and instance)."""
    return re.sub(r'(\.\d+)+$', '', getattr(hub, 'hubIdentifier', None) or '')


def recentMonths():
    return util.getSetting('see_more_recent_months', DEFAULT_MONTHS)


def addedLimit():
    return max(util.getSetting('see_more_added_limit', DEFAULT_ADDED_LIMIT), 0)


def cutoffDate(months, today=None):
    """The window's first day: `months` calendar months before today (a 31st going back to a
    shorter month lands on its last day)."""
    today = today or datetime.date.today()
    month = today.month - months
    year = today.year + (month - 1) // 12
    month = (month - 1) % 12 + 1
    for day in (today.day, 30, 29, 28):
        try:
            return datetime.date(year, month, day)
        except ValueError:
            continue


def _inWindow(item, field, cutoff):
    value = str(item.get(field) or '')
    if not value:
        return False
    if field == 'originallyAvailableAt':
        return value[:10] >= cutoff.isoformat()
    try:
        return datetime.date.fromtimestamp(int(value)) >= cutoff
    except ValueError:
        return False


def _withArg(key, arg):
    return key + ('&' if '?' in key else '?') + arg


def apply(hub, rowMax):
    """Limits one fetched row (a plexnet Hub, on the worker that fetched it) and notes what its grid
    lists: hub.gridKey, hub.gridMax (None: the whole list) and hub.seeMore. A windowed row's items
    are cut to the window here; one still full at rowMax asks the server how many the window holds
    (a size-0 request, about 30 ms). Rows of no rule are left alone (seeMore stays unset)."""
    base = baseIdentifier(hub)
    key = getattr(hub, 'key', None)
    if not key:
        return
    if base in WINDOW_ROWS:
        field = WINDOW_ROWS[base]
        cutoff = cutoffDate(recentMonths())
        hub.items = [item for item in hub.items if _inWindow(item, field, cutoff)]
        # the same window from the server: a date filter it applies itself (relative or absolute,
        # >> or not - all checked; an absolute date keeps it the row's own cutoff)
        hub.gridKey = _withArg(key, '{0}>>={1}'.format(field, cutoff.isoformat()))
        hub.gridMax = None
        hub.seeMore = False
        if len(hub.items) >= rowMax and hub.more.asBool():
            total = _total(hub.server, hub.gridKey)
            hub.seeMore = total is not None and total > rowMax
    elif base in ADDED_ROWS:
        limit = addedLimit()
        hub.gridKey = key
        hub.gridMax = limit
        hub.seeMore = limit > rowMax and (hub.more.asBool() or len(hub.items) > rowMax)


def applyAll(hubs, rowMax):
    for hub in hubs or ():
        try:
            apply(hub, rowMax)
        except Exception:
            util.ERROR()


def _total(server, key):
    started = time.time()
    try:
        data = server.query(key, limit=0)
    except Exception as e:
        util.DEBUG_LOG('Hub limits: no count for {0}: {1}', key, e)
        return None
    if data is None:
        return None
    total = data.attrib.get('totalSize')
    util.DEBUG_LOG('Hub limits: {0} in the window ({1} ms)', total, int((time.time() - started) * 1000))
    return int(total) if total is not None else None


def hasSeeMore(hub, rowMax):
    """Whether the row ends in "See more": its limited list's say when apply() had a rule for it,
    otherwise the server's - more than the row asked for."""
    seeMore = hub.__dict__.get('seeMore')
    if seeMore is not None:
        return seeMore
    return hub.more.asBool() or len(hub.items) > rowMax
