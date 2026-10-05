"""
A section's saved hub config (Manage Hubs) against the rows the server sends now.

A custom config is {'custom': True, 'hubs': [{'catalog_id', 'identifier', 'order', ...}], 'hidden':
[catalog ids], 'reconciled': [server uuids]}: the rows shown, in order, and the rows hidden. Which
rows exist is the server's (Plex's Manage Recommendations), so a row in neither list is new - one
switched on in Plex since, a newly pinned library's, or the other form of Recently Added after Plex's
merge setting flipped - and it shows, placed beside its neighbour in the server's own order
(reconcile()). A row the config lists that the server no longer sends keeps its place and state.

Configs from before 'hidden' was kept showed only what they listed, so for them an unlisted row is
hidden, not new: each server's rows are taken that way the first time they're seen ('reconciled'
records which servers' have been), and Home's catalog ids of then, which dropped a row's library
(legacy ids), are rewritten to today's.
"""
from __future__ import absolute_import

HIDDEN = 'hidden'
RECONCILED = 'reconciled'
# Home configs of 7.1 recorded the servers whose rows they covered; rows of any other showed
LEGACY_SERVERS = 'servers'

# Plex's merged Recently Added rows (its "merge recently added" setting on) and the per-library rows
# each replaces (setting off), by stable id: home.movies.recent <-> movie.recentlyadded.<library>
MERGED_ROWS = {
    'home.movies.recent': 'movie.recentlyadded',
    'home.television.recent': 'tv.recentlyadded',
    'home.music.recent': 'music.recent.added',
    'home.photos.recent': 'photo.recent',
    'home.videos.recent': 'video.recent',
}


def homeRowId(hub_identifier):
    """A Home row's identifier as it's saved: the server's, less what changes from one request to
    the next. A library's row keeps its library (movie.recentlyadded.22 - two movie libraries each
    have one) but not its pick (movie.genre.22.71 picks a genre, movie.by.actor.or.director.22.155600
    a person, each request); a merged row loses its first library (home.movies.recent.22 ->
    home.movies.recent: the first of the pinned libraries, which pinning changes). A collection's
    row keeps its collection (custom.collection.2.63624)."""
    parts = (hub_identifier or '').split('.')
    if parts[0] == 'home':
        while len(parts) > 1 and parts[-1].isdigit():
            parts.pop()
        return '.'.join(parts)
    if 'collection' in parts:
        return hub_identifier
    for i, part in enumerate(parts):
        if part.isdigit():
            return '.'.join(parts[:i + 1])
    return hub_identifier


def rowBase(hub_identifier):
    """A row's identifier without its library or pick: movie.genre.22.71 -> movie.genre,
    music.popular.10 -> music.popular - what Plex's Manage Recommendations lists it as."""
    parts = (hub_identifier or '').split('.')
    for i, part in enumerate(parts):
        if part.isdigit():
            return '.'.join(parts[:i])
    return hub_identifier


def picksPerRequest(hub_identifier):
    """Whether the row picks something on each request, carried in its identifier (a genre,
    movie.genre.22.71; a person, movie.by.actor.or.director.22.155600) - it can come back empty on
    one request and not the next. Not Home's merged rows (home.movies.recent.22) or a collection."""
    parts = (hub_identifier or '').split('.')
    if parts[0] == 'home' or 'collection' in parts:
        return False
    return len([p for p in parts if p.isdigit()]) > 1


# Plex's generic titles for the rows whose title names what they picked this time, as its Manage
# Recommendations lists them (checked against Animal, PMS 1.43.4, 2026-10-05). The server's own come
# first (manageTitles(), localised): only the owner may read them, so these stand in for a shared
# or managed user.
GENERIC_TITLES = {
    'movie.genre': 'Top Movies in (Genre)',
    'movie.by.actor.or.director': 'Top Movies by (Actor or Director)',
    'tv.moreingenre': 'More in (Genre)',
    'tv.morefromnetwork': 'More from (Network)',
    'music.top.period': 'Top Albums from (Year)',
    'music.recent.genre': 'Top Albums from (Genre)',
    'music.recent.artist': 'More by (Artist)',
    'music.popular': 'Most Played in (Month)',
    'music.vault': "Haven't Played in (Time)",
    'music.recent.label': 'More from (Label)',
    'photo.random.year': 'Photos from (Year)',
    'photo.random.decade': 'Photos from (Decade)',
    'photo.random.dayormonth': 'Photos from (Day or Month)',
}


def genericTitle(hub_identifier, manage_titles=None):
    """The title a row's kind goes by when its own names this request's pick ("Top Movies in
    Musical" -> "Top Movies in [Genre]"), or None for a row whose title doesn't change. Plex's
    placeholder in square brackets, which keeps it apart from a library named in round ones
    ("Recently Released Movies (Films)"). manage_titles: the server's own, {base: title}."""
    base = rowBase(hub_identifier)
    title = (manage_titles or {}).get(base) or GENERIC_TITLES.get(base)
    if not title or '(' not in title:
        return None
    return title.replace('(', '[').replace(')', ']')


def _source(catalog_id):
    return catalog_id.partition('|')[0] if '|' in catalog_id else ''


def _identifier(catalog_id):
    return catalog_id.partition('|')[2] if '|' in catalog_id else catalog_id


def counterparts(catalog_id, catalog_ids):
    """The ids in catalog_ids that are catalog_id's other form across Plex's merge setting: for a
    merged row its server's per-library rows, for a per-library row its server's merged row."""
    source, identifier = _source(catalog_id), _identifier(catalog_id)
    unmerged = MERGED_ROWS.get(identifier)
    found = []
    for other in catalog_ids:
        if _source(other) != source or other == catalog_id:
            continue
        ident = _identifier(other)
        if unmerged:
            base, _, key = ident.rpartition('.')
            if base == unmerged and key.isdigit():
                found.append(other)
        else:
            base, _, key = identifier.rpartition('.')
            if key.isdigit() and MERGED_ROWS.get(ident) == base:
                found.append(other)
    return found


def _isLegacy(config, server):
    """Whether this server's rows are still to be taken as a config of before 'hidden' had them:
    unlisted = hidden. Asked before reconcile() adds 'hidden'."""
    if server in config.get(RECONCILED, ()):
        return False
    if LEGACY_SERVERS in config:
        # a Home config of 7.1: rows of a server it covered were hidden unless listed (Continue
        # Watching's too); any other server's showed
        return server in config[LEGACY_SERVERS] or server == ''
    return HIDDEN not in config


def reconcile(config, rows):
    """Brings a custom config up to date with the rows the server sends now. rows: [(catalog_id,
    legacy_id, server_uuid, entry)] in the server's default order (Continue Watching's server is
    ''), entry the dict to save for a new row ({'catalog_id', 'identifier', 'title'...}). Rewrites
    config in place; returns whether it changed."""
    if not config or not config.get('custom'):
        return False
    legacyServers = set(server for _, _, server, _ in rows if _isLegacy(config, server))
    hubs = config.setdefault('hubs', [])
    changed = HIDDEN not in config or RECONCILED not in config
    hidden = config.setdefault(HIDDEN, [])
    reconciled = config.setdefault(RECONCILED, [])

    def shownIndex(catalog_id):
        for i, h in enumerate(hubs):
            if h.get('catalog_id', h.get('identifier')) == catalog_id:
                return i
        return None

    def known(catalog_id):
        return shownIndex(catalog_id) is not None or catalog_id in hidden

    present = [row[0] for row in rows]

    # a config of before: its ids of then, and an unlisted row hidden
    renamed = {}
    for catalog_id, legacy_id, server, entry in rows:
        if server not in legacyServers or known(catalog_id):
            continue
        at = shownIndex(legacy_id) if legacy_id and legacy_id != catalog_id else None
        if legacy_id in renamed:
            # a second row under the one legacy id (Films' and Movies' Recently Released were both
            # movie.recentlyreleased): shown after the first
            hubs.insert(renamed[legacy_id] + 1, dict(entry))
            renamed[legacy_id] += 1
        elif at is not None:
            hubs[at] = dict(hubs[at], catalog_id=catalog_id, identifier=entry.get('identifier', catalog_id))
            renamed[legacy_id] = at
        elif legacy_id and legacy_id in hidden:
            hidden[hidden.index(legacy_id)] = catalog_id
        else:
            hidden.append(catalog_id)
        changed = True

    # new rows: shown, beside their neighbour in the server's order
    placed = {}  # merged row -> its per-library rows placed after it so far
    for index, (catalog_id, _, server, entry) in enumerate(rows):
        if known(catalog_id):
            continue
        other = counterparts(catalog_id, [h.get('catalog_id') for h in hubs] + hidden)
        if other:
            # Plex's merge setting flipped: the row takes its other form's state and place
            shown = [o for o in other if shownIndex(o) is not None]
            if not shown:
                hidden.append(catalog_id)
                changed = True
                continue
            if _identifier(catalog_id) in MERGED_ROWS:
                # where the first of its libraries' rows was
                position = min(shownIndex(o) for o in shown)
            else:
                # after the merged row, and after its other libraries' rows placed already
                merged = shown[0]
                placed[merged] = placed.get(merged, 0) + 1
                position = shownIndex(merged) + placed[merged]
        else:
            position = None
            for before in reversed(present[:index]):
                i = shownIndex(before)
                if i is not None:
                    position = i + 1
                    break
            if position is None:
                for after in present[index + 1:]:
                    i = shownIndex(after)
                    if i is not None:
                        position = i
                        break
            if position is None:
                position = len(hubs)
        hubs.insert(position, dict(entry))
        changed = True

    for server in sorted(set(server for _, _, server, _ in rows)):
        if server not in reconciled:
            reconciled.append(server)
            changed = True
    if changed:
        for i, h in enumerate(hubs):
            h['order'] = i
    return changed


def hide(config, catalog_id):
    """A shown row hidden (Manage Hubs' Disable)."""
    hubs = config.get('hubs', [])
    config['hubs'] = [h for h in hubs if h.get('catalog_id', h.get('identifier')) != catalog_id]
    for i, h in enumerate(config['hubs']):
        h['order'] = i
    hidden = config.setdefault(HIDDEN, [])
    if catalog_id not in hidden:
        hidden.append(catalog_id)


def show(config, entry):
    """A hidden row shown again, at the end."""
    catalog_id = entry['catalog_id']
    hidden = config.setdefault(HIDDEN, [])
    if catalog_id in hidden:
        hidden.remove(catalog_id)
    hubs = config.setdefault('hubs', [])
    if not any(h.get('catalog_id', h.get('identifier')) == catalog_id for h in hubs):
        hubs.append(dict(entry, order=len(hubs)))


def moveShown(config, shown_ids, from_pos, to_pos):
    """Moves a row from one place to another among the rows the dialog shows (shown_ids, in order):
    rows the config lists but the server no longer sends keep their own places."""
    hubs = config.get('hubs', [])
    slots = [i for i, h in enumerate(hubs) if h.get('catalog_id', h.get('identifier')) in shown_ids]
    if not (0 <= from_pos < len(slots) and 0 <= to_pos < len(slots)) or from_pos == to_pos:
        return False
    moving = [hubs[i] for i in slots]
    moving.insert(to_pos, moving.pop(from_pos))
    for slot, h in zip(slots, moving):
        hubs[slot] = h
    for i, h in enumerate(hubs):
        h['order'] = i
    return True
