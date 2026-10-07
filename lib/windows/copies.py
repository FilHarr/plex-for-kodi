# coding=utf-8
"""
Copies of one title - in two libraries of a server, or on two servers - and their versions: what
makes two items the same title, which copy opens, and the Open from list of every version of every
copy. Search (search.py), Continue Watching (home.mergeContinueWatching()) and the person page
(person.py) share these (the user, 2026-10-07).
"""
from __future__ import absolute_import

from plexnet import util as plexnetUtil

from lib.util import T


def sameTitleKey(item):
    """What makes two items copies of one title: the agent's guid, less any language suffix
    (?lang=en - an older agent's, so the same film in libraries of two languages matches). None -
    a title of its own - for one with no guid or a server-only one: local:// and a library with no
    agent's (tv.plex.agents.none://98691, checked live) are just the item's number on its server,
    and the same number on another server is another video."""
    guid = u'{0}'.format(item.get('guid') or '')
    if not guid or guid.startswith('local://') or '.agents.none://' in guid:
        return None
    return guid.split('?', 1)[0]


def _versions(item):
    """An item's versions (its Media), [] for one with none (a show, a person)."""
    try:
        return list(item.media or [])
    except Exception:
        return []


def _int(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _quality(item):
    """A copy's best version's (width, bitrate), for pickCopy(); (0, 0) if it has none. The best,
    not the first: Plex's order is its own, and a copy with a 4K version second was judged by its
    1080p (the user, 2026-10-07). Read with _int(): a video's versions (plexmedia.PlexMedia)
    answer get() with plain strings."""
    return max([(_int(media.get('width')), _int(media.get('bitrate'))) for media in _versions(item)] or [(0, 0)])


def pickCopy(copies, serverOrder, positions=None):
    """Which copy of a title opens (the user, 2026-10-06): one part-watched - of several, the one
    watched last (as Continue Watching keeps, home.mergeContinueWatching()); then the one in the
    library highest in the sidebar - pinned beats unpinned whatever the quality: a library pinned,
    and pinned high, is the one watched from (positions: {(server uuid, library key): place},
    sidebar_model.entryPositions()); then the best quality; then the one on the server first in the
    sidebar (serverOrder: uuid -> place); then the first. The others are on Open from."""
    positions = positions or {}
    # past every pinned library: a place is the entry's index in the whole sidebar, Watchlist and
    # Playlists included, so it can be higher than the number of libraries
    unpinned = max(positions.values()) + 1 if positions else 0

    def rank(indexed):
        i, item = indexed
        partWatched = bool(item.get('viewOffset').asInt())
        viewed = item.get('lastViewedAt').asInt() if partWatched else 0
        width, bitrate = _quality(item)
        uuid = getattr(getattr(item, 'server', None), 'uuid', None)
        place = positions.get((uuid, u'{0}'.format(item.get('librarySectionID') or '')), unpinned)
        return (not partWatched, -viewed, place, -width, -bitrate,
                serverOrder.get(uuid, len(serverOrder)), i)
    return min(enumerate(copies), key=rank)[1]


# The types whose versions Open from offers one by one, the one picked opened chosen
# (chooseVersion()): the ones with a version to play
VERSIONED_TYPES = ('movie', 'episode')


def versionEntries(copies):
    """Open from's rows for a title's copies: (copy, version) for each version of each copy that
    has more than one - a film's 4K and 1080p in one library are two rows - else (copy, None)."""
    entries = []
    for copy in copies:
        versions = _versions(copy) if copy.TYPE in VERSIONED_TYPES else []
        if len(versions) > 1:
            entries.extend((copy, media) for media in versions)
        else:
            entries.append((copy, None))
    return entries


def chooseVersion(copy, media):
    """copy opened with media its chosen version, as pre-play's Choose Version does
    (preplayutils.chooseVersion()): pre-play keeps it through its first load, and the episode
    screen gives it to its own copy of the episode (EpisodesPaginator._carryVersion())."""
    for version in _versions(copy):
        version.set('selected', '')
    media.set('selected', 1)
    copy.setMediaChoice(media)


def copyLabel(copy, multiServer, media=None):
    """A row in the Open from list: the copy's library, its server on a multi-server account, then
    the quality of media - a version of it, else its first - "Films · Animal · 1080p (12.5 Mbps)",
    the dot the cards' lines use (the user, 2026-10-07)."""
    parts = [u'{0}'.format(copy.get('librarySectionTitle') or '')]
    server = getattr(copy, 'server', None)
    if multiServer and server is not None:
        parts.append(server.name)
    if media is None:
        versions = _versions(copy)
        media = versions[0] if versions else None
    if media is not None:
        resolution = u'{0}'.format(media.get('videoResolution') or '')
        resolution = resolution + 'p' if resolution.isdigit() else resolution.upper()
        bitrate = _int(media.get('bitrate'))
        rate = plexnetUtil.bitrateToString(bitrate * 1000) if bitrate else ''
        if resolution and rate:
            parts.append(u'{0} ({1})'.format(resolution, rate))
        else:
            parts.append(resolution or rate)
    return u' · '.join(part for part in parts if part)


def chooseFrom(entries, multiServer):
    """The Open from list for entries (versionEntries()): the (copy, version) picked, its version
    chosen on it (chooseVersion()); None if dismissed."""
    from . import dropdown
    choice = dropdown.showDropdown(
        options=[{'key': i, 'display': copyLabel(copy, multiServer, media)} for i, (copy, media) in enumerate(entries)],
        pos=(660, 441),
        close_direction='none',
        set_dropdown_prop=False,
        header=T(35151, 'Open from'),
        align_items='left'
    )
    if choice is None:
        return None
    copy, media = entries[choice['key']]
    if media is not None:
        chooseVersion(copy, media)
    return copy, media
