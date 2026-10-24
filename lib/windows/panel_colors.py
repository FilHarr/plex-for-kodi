# coding=utf-8
"""Which colours an item's colour panel takes (coloursFor(), kodigui.updatePanelFrom()): an
episode its season's, or its show's when the season has none - not its own - wherever it is shown
(the user, 2026-10-09); an album its cover's, and a track its album's cover's (2026-10-23); anything
else its own.

Albums: Plex makes an album's UltraBlurColors from its background art, which an album inherits from
its artist - so every album of an artist came out the same (checked on Animal, 2026-10-23: 8 of
Barenaked Ladies' 11 albums, 9 of Metallica's, all exactly their artist's background's). PMS works
out colours for any image it serves, /services/ultrablur/colors?url=<image path> (20-70 ms each,
no batching; the official app asks it too), so an album's are asked for from its cover (thumb).

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
# (server uuid, ratingKey) -> (its poster's stamp, its colours (a dict of the four corners), or None
# for none). The stamp: another poster, or a metadata refresh, gets new colours (_stale()).
CACHE = collections.OrderedDict()
_lock = threading.Lock()


def stamp(url):
    """A Plex art URL's stamp - /library/metadata/100952/thumb/1791848398 -> 1791848398 - which
    changes when the art does or is refreshed; 0 for none. Not a time to read: it can run hours
    ahead, and a refresh can make it smaller."""
    tail = u'{0}'.format(url or '').rstrip('/').rsplit('/', 1)[-1]
    return int(tail) if tail.isdigit() else 0


def _cached(uuid, key):
    """The colours kept for key; None for none, False when not asked yet."""
    with _lock:
        kept = CACHE.get((uuid, key))
    return kept[1] if kept is not None else False


def _stale(uuid, key, poster):
    """Whether key's colours need asking for: never asked, or another poster (poster: its URL as an
    item shows it) than the one they were made from - a new one, or a metadata refresh, which
    makes them again. Another, not only a newer: a refresh can give a smaller stamp (House of the
    Dragon's season 3, 1791873605 to 1791848895, 2026-10-13). An item with no poster URL asks
    nothing. Every place that warms them has current stamps: Continue Watching's, which Plex gives
    out of date, are brought up to date first (home.freshenWatchHistoryRows())."""
    with _lock:
        kept = CACHE.get((uuid, key))
    if kept is None:
        return True
    current = stamp(poster)
    return bool(current) and current != kept[0]


def _store(uuid, key, colours, poster=None):
    with _lock:
        CACHE[(uuid, key)] = (stamp(poster), colours)
        CACHE.move_to_end((uuid, key))
        while len(CACHE) > CACHE_MAX:
            CACHE.popitem(last=False)


def _fetch(server, keys):
    """Colours for each key, in batches; stored with its poster's stamp, None for one that has
    none. keys: {ratingKey: poster URL as the items show it}, in order; only those _stale()."""
    missing = [key for key, poster in keys.items() if _stale(server.uuid, key, poster)]
    for start in range(0, len(missing), BATCH):
        batch = missing[start:start + BATCH]
        data = server.query('/library/metadata/{0}'.format(','.join(batch)))
        if data is None:
            # no connection (plexserver.query()): no answer, nothing stored
            return
        found = {}
        for elem in data:
            colours = elem.find('UltraBlurColors')
            found[elem.attrib.get('ratingKey')] = (dict(colours.attrib) if colours is not None else None,
                                                   elem.attrib.get('thumb'))
        for key in batch:
            colours, poster = found.get(key, (None, None))
            _store(server.uuid, key, colours, poster)


def _fetchCovers(server, covers):
    """Colours for each album from its cover, one request each (the endpoint takes one image); stored
    with the cover's stamp, None for one it gave none for. covers: {album ratingKey: cover URL}, in
    order; only those _stale()."""
    for key, cover in covers.items():
        if not cover or not _stale(server.uuid, key, cover):
            continue
        try:
            data = server.query('/services/ultrablur/colors', params={'url': cover})
        except plexnet.exceptions.RateLimited:
            # asked again once the server's ready (warm() logs it)
            raise
        except plexnet.exceptions.BadRequest as e:
            # This cover's refused, not the server: kept as none, as one it gave no colours for, till the cover
            # changes - Animal answers one cover with a 500 every time, and it was asked again on every warm
            # (2026-10-23)
            util.DEBUG_LOG('Panel colours: no colours for {0}: {1}', cover, e)
            _store(server.uuid, key, None, cover)
            continue
        if data is None:
            # no connection (plexserver.query()): no answer, nothing stored
            return
        colours = data.find('UltraBlurColors')
        _store(server.uuid, key, dict(colours.attrib) if colours is not None else None, cover)


def _isEpisode(item):
    return getattr(item, 'TYPE', None) == 'episode' and bool(item.get('parentRatingKey'))


def _albumCover(item):
    """(album ratingKey, its cover's URL) for an album, or a track's album; None for anything else."""
    kind = getattr(item, 'TYPE', None)
    if kind == 'album' and item.get('ratingKey'):
        return str(item.get('ratingKey')), item.get('thumb')
    if kind == 'track' and item.get('parentRatingKey'):
        return str(item.get('parentRatingKey')), item.get('parentThumb')
    return None


def warm(items, episodes=True, covers=False):
    """Fetches what items' panels take that isn't cached yet: the seasons (and, for a season without
    colours, the show) of the episodes among them, in batches - cheap enough to wait for before they
    show - and with covers, the colours of the albums' covers (a track's: its album's), one request
    each, so warmCovers() after they show. On a worker: it asks the server. No request without
    episodes, or with covers, albums or tracks."""
    byServer = collections.OrderedDict()
    for item in items or ():
        wanted = (episodes and _isEpisode(item)) or (covers and _albumCover(item))
        if wanted and getattr(item, 'server', None) is not None:
            byServer.setdefault(item.server.uuid, (item.server, []))[1].append(item)
    for server, members in byServer.values():
        try:
            if covers:
                found = collections.OrderedDict()
                for m in members:
                    cover = _albumCover(m)
                    if cover:
                        found.setdefault(*cover)
                if found:
                    _fetchCovers(server, found)
            episodes_ = [m for m in members if episodes and _isEpisode(m)]
            if not episodes_:
                continue
            seasons = collections.OrderedDict()
            for e in episodes_:
                seasons.setdefault(str(e.parentRatingKey), e.get('parentThumb'))
            _fetch(server, seasons)
            shows = collections.OrderedDict()
            for e in episodes_:
                if not _cached(server.uuid, str(e.parentRatingKey)) and e.get('grandparentRatingKey'):
                    shows.setdefault(str(e.grandparentRatingKey), e.get('grandparentThumb'))
            if shows:
                _fetch(server, shows)
        except plexnet.exceptions.BadRequest as e:
            util.DEBUG_LOG('Panel colours: {0} refused them: {1}', repr(server.name), e)
        except Exception:
            util.ERROR()


def warmHubs(hubs):
    """warm() for every item of these rows, and warmLater() for their albums' and tracks' covers."""
    items = [item for hub in hubs for item in (getattr(hub, 'items', None) or ())]
    warm(items)
    warmLater(items)


def warmCovers(items):
    """The album covers' colours among items (a track's: its album's) - for after they show, or for
    the one album a screen is of (the Album screen, the music player)."""
    warm(items, episodes=False, covers=True)


# warmLater()'s items, for its one worker: one cover request at a time, however fast a grid is scrolled
_LATER = collections.deque()
_laterWorker = [None]


def warmLater(items):
    """warmCovers() on a worker of its own, for items fetched where nothing should wait for it (a
    library grid's chunks, the Artist screen's album rows, the Home and Recommended rows, a
    collection's or See more's grid); their next focus takes the colours."""
    items = [item for item in items or () if _albumCover(item)]
    if not items:
        return
    with _lock:
        _LATER.append(items)
        if _laterWorker[0] is not None and _laterWorker[0].is_alive():
            return
        t = threading.Thread(target=_warmLaterRun, name='panel colours')
        t.daemon = True
        _laterWorker[0] = t
    t.start()


def _warmLaterRun():
    while True:
        with _lock:
            if not _LATER:
                _laterWorker[0] = None
                return
            items = _LATER.popleft()
        try:
            warmCovers(items)
        except Exception:
            util.ERROR()
        if util.MONITOR.abortRequested():
            # Kodi's closing: the rest of the queue isn't worth its requests
            with _lock:
                _LATER.clear()
                _laterWorker[0] = None
            return


def coloursFor(ds):
    """The colours ds's panel takes: an episode's season's, else its show's; an album's cover's, or a
    track's album's cover's - all from CACHE (never a request); else - and for anything else - its
    own ultraBlurColors (getattr: only Video, Audio, Photo and collections have them;
    PlexObject.get() would make up a truthy value)."""
    if getattr(ds, 'server', None) is not None:
        uuid = ds.server.uuid
        colours = None
        if _isEpisode(ds):
            colours = (_cached(uuid, str(ds.parentRatingKey))
                       or (ds.get('grandparentRatingKey') and _cached(uuid, str(ds.grandparentRatingKey))))
        else:
            cover = _albumCover(ds)
            colours = cover and _cached(uuid, cover[0])
        if colours:
            return colours
    return getattr(ds, 'ultraBlurColors', None)
