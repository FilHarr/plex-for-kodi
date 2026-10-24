# coding=utf-8
"""
The menu key's item menu on the library grids (GridMixin.itemOptions()) and the Collection screen's grid
(BoundedGridWindow.itemMenu()), in the option picker headed by the item:
- a film, show, season or episode: Mark Played/Unplayed - or Remove from watchlist on the Watchlist's grid - and
  Go To Show for a season or episode;
- a collection, artist, album or playlist: Play and Shuffle, and Go to Artist for an album;
- a track: Go to Album, Go to Artist.
Anything else (a photo, a folder, an empty collection) has none, and the key does nothing there. The screens run
Mark Played/Unplayed and Remove from watchlist themselves, as each redraws its own tiles; run() the rest.
"""
from __future__ import absolute_import

from plexnet import playqueue

from lib import util
from lib.util import T
from . import grid_labels
from . import opener
from .dialog import showOptionsDialog

VIDEO_TYPES = ('episode', 'season', 'movie', 'show')
# played as a whole, a server play queue of it: Play/Shuffle
PLAYABLE_TYPES = ('collection', 'artist', 'album', 'playlist')


def collectionPlayable(collection):
    """Something in it, of a type a play queue can be made from (playqueue.PlayQueueFactory - video or audio)."""
    return (collection.get('childCount').asInt() > 0 and
            bool(playqueue.PlayQueueFactory().getContentType(collection)))


def playable(item):
    """An artist or album always: a library's have tracks, and the grid's album listing carries no leafCount
    (Play/Shuffle never showed on albums while this asked it - live, 2026-10-23)."""
    if item.TYPE == 'collection':
        return collectionPlayable(item)
    if item.TYPE == 'playlist':
        return item.get('leafCount').asInt() > 0
    return item.TYPE in ('artist', 'album')


def playItem(window, item, shuffle=False):
    """The whole of item as a server play queue, in its own order or shuffled - the way Plex's own clients play one,
    and the Artist and Album screens' Play/Shuffle (createPlayQueueForItem()). A collection's queue is its children
    listing (library://<section>/directory//library/collections/<id>/children); PMS expands a show collection into
    its episodes itself (checked live, 2026-09-30: a one-show collection gave a 12-episode queue)."""
    pq = playqueue.createPlayQueueForItem(item, options={'shuffle': shuffle})
    if not pq:
        util.DEBUG_LOG('itemmenu: no play queue for {}', item)
        return
    window.processCommand(opener.open(pq, context=window))


def options(mli, watchlist=False):
    """The menu's rows for mli's item, (key, label); none for an item it has nothing for."""
    ds = mli.dataSource
    if ds.TYPE in VIDEO_TYPES:
        if watchlist:
            # we don't want mark watched for watchlist items
            return [('remove_from_watchlist', T(34011, "Remove from watchlist"))]
        rows = []
        if not mli.getProperty('watched'):
            rows.append(('mark_watched', T(32319, "Mark Played")))
        if (ds.isFullyWatched or ds.isWatched or
                (ds.TYPE in ("show", "season") and 0 < ds.unViewedLeafCount < ds.leafCount)):
            rows.append(('mark_unwatched', T(32318, "Mark Unplayed")))
        if ds.TYPE in ('episode', 'season'):
            rows.append(('to_show', T(32323, "Go To Show")))
        return rows

    rows = []
    if ds.TYPE in PLAYABLE_TYPES and playable(ds):
        rows += [('play', T(33020, 'Play')), ('shuffle', T(32935, 'Shuffle'))]
    if ds.TYPE == 'track':
        rows.append(('to_album', T(32300, 'Go to Album')))
    if ds.TYPE in ('album', 'track'):
        rows.append(('to_artist', T(32301, 'Go to Artist')))
    return rows


def choose(mli, rows, **kwargs):
    """The picker for rows, headed by mli's item: the key chosen, or None."""
    return showOptionsDialog(grid_labels.menuHeading(mli.dataSource), rows, non_playback=True, menu=True, **kwargs)


# the rating key each "Go to" opens, from the item the menu's for
_GO_TO_KEYS = {
    'to_show': lambda ds: ds.get('grandparentRatingKey') if ds.TYPE == 'episode' else ds.get('parentRatingKey'),
    'to_album': lambda ds: ds.get('parentRatingKey'),
    'to_artist': lambda ds: ds.get('grandparentRatingKey') if ds.TYPE == 'track' else ds.get('parentRatingKey'),
}


def run(window, mli, choice, **open_kwargs):
    """Play/Shuffle and the Go to rows, from window; True if choice was one of them. open_kwargs go to what a Go to
    opens (the screen's entry_section_id), as its own clicks pass them."""
    ds = mli.dataSource
    if choice in ('play', 'shuffle'):
        playItem(window, ds, shuffle=choice == 'shuffle')
        return True
    if choice in _GO_TO_KEYS:
        key = _GO_TO_KEYS[choice](ds)
        if key:
            window.processCommand(opener.open(u'{0}'.format(key), context=window, server=ds.getServer(),
                                              **open_kwargs))
        return True
    return False
