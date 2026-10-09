# coding=utf-8
"""Which colours an item's colour panel takes (coloursFor(), kodigui.updatePanelFrom()): an
episode its season's, or its show's when the season has none - not its own - wherever it is shown
(the user, 2026-10-09); anything else its own.

Why: Plex makes an episode's colours (UltraBlurColors) from its own thumbnail, the screen grab,
while the art behind it is its season's or show's background, and opening it opens the season's
screen (EpisodesWindow), whose panel is the season's. A season's colours mostly come from its
poster (checked on Animal, 2026-10-09: 10 of 12; every one of 34 seasons had some).

An episode's data carries only its own, so coloursFor() reads them from CACHE, never asking the
server itself: it runs as focus moves. Every place that fetches episodes to show fills it first,
on the worker that fetched them (warm()/warmHubs()) - the Recommended and Home rows
(home.SectionHubsTask, Home's per-server fetch), the See more grids' chunks, the library grid's
chunks, the Collection and folder screens' pages, post-play's episode - in batches of
/library/metadata/<key>,<key>,..., so focus finds them there. Checked live on Animal: 130 episodes
in both TV libraries' rows, 34 seasons in one 48 ms request. An episode not warmed, or whose season
and show have none, or a server that refused, keeps its own colours, as before."""
from __future__ import absolute_import

import collections
import threading

import plexnet
from lib import util

# Keys per batch request: /library/metadata/<keys> answered 40 at once (checked 2026-10-08)
BATCH = 40
CACHE_MAX = 500
# (server uuid, ratingKey) -> its colours (a dict of the four corners), or None for none
CACHE = collections.OrderedDict()
_lock = threading.Lock()


def _cached(uuid, key):
    """The colours kept for key; None for none, False when not asked yet."""
    with _lock:
        return CACHE.get((uuid, key), False)


def _store(uuid, key, colours):
    with _lock:
        CACHE[(uuid, key)] = colours
        CACHE.move_to_end((uuid, key))
        while len(CACHE) > CACHE_MAX:
            CACHE.popitem(last=False)


def _fetch(server, keys):
    """Colours for each key not cached yet, in batches; stored, None for one that has none."""
    missing = [key for key in keys if _cached(server.uuid, key) is False]
    for start in range(0, len(missing), BATCH):
        batch = missing[start:start + BATCH]
        data = server.query('/library/metadata/{0}'.format(','.join(batch)))
        if data is None:
            # no connection (plexserver.query()): no answer, nothing stored
            return
        found = {}
        for elem in data:
            colours = elem.find('UltraBlurColors')
            found[elem.attrib.get('ratingKey')] = dict(colours.attrib) if colours is not None else None
        for key in batch:
            _store(server.uuid, key, found.get(key))


def _isEpisode(item):
    return getattr(item, 'TYPE', None) == 'episode' and bool(item.get('parentRatingKey'))


def warm(items):
    """Fetches the seasons (and, for a season without colours, the show) of the episodes among
    items that aren't cached yet. On a worker: it asks the server. No request without episodes."""
    byServer = collections.OrderedDict()
    for item in items or ():
        if _isEpisode(item) and item.server is not None:
            byServer.setdefault(item.server.uuid, (item.server, []))[1].append(item)
    for server, episodes in byServer.values():
        try:
            _fetch(server, list(collections.OrderedDict.fromkeys(str(e.parentRatingKey) for e in episodes)))
            shows = [str(e.grandparentRatingKey) for e in episodes
                     if not _cached(server.uuid, str(e.parentRatingKey)) and e.get('grandparentRatingKey')]
            if shows:
                _fetch(server, list(collections.OrderedDict.fromkeys(shows)))
        except plexnet.exceptions.BadRequest as e:
            util.DEBUG_LOG('Panel colours: {0} refused the seasons: {1}', repr(server.name), e)
        except Exception:
            util.ERROR()


def warmHubs(hubs):
    """warm() for every item of these rows."""
    warm([item for hub in hubs for item in (getattr(hub, 'items', None) or ())])


def coloursFor(ds):
    """The colours ds's panel takes: an episode's season's, else its show's, from CACHE (never a
    request); else - and for anything else - its own ultraBlurColors (getattr: only Video,
    Audio, Photo and collections have them; PlexObject.get() would make up a truthy value)."""
    if _isEpisode(ds) and getattr(ds, 'server', None) is not None:
        uuid = ds.server.uuid
        colours = (_cached(uuid, str(ds.parentRatingKey))
                   or (ds.get('grandparentRatingKey') and _cached(uuid, str(ds.grandparentRatingKey))))
        if colours:
            return colours
    return getattr(ds, 'ultraBlurColors', None)
