"""
A section's saved hub config (Manage Hubs) against the rows the server sends now.

A custom config is {'custom': True, 'order': [catalog ids], 'hidden': [catalog ids], 'hubs':
[{'catalog_id', 'identifier', 'order', ...}], 'reconciled': [server uuids]}: every row the config
knows, in order, shown or hidden - ordering and visibility apart, as the Libraries picker's order
and pins (the user, 2026-10-05). 'hubs' is the shown ones in that order, what Home and the sorting
read; it follows the other two (_sync()). The order is the user's only once they've moved a row
('ordered'): until then it's the server's, kept to whatever it sends now - Plex's own, and on Home
the sidebar's - so hiding a row doesn't fix Home's order. Which rows exist is the server's (Plex's
Manage Recommendations), so a row the config doesn't know is new - one switched on in Plex since, a
newly pinned library's, or the other form of Recently Added after Plex's merge setting flipped - and
it shows, placed after its neighbour in the server's own order (reconcile()). A row the config knows
that the server no longer sends keeps its place and state.

Older configs had no 'order': only the shown rows had a place, and before that, no 'hidden' either,
so an unlisted row was hidden, not new. Each server's rows are taken that way the first time they're
seen ('reconciled' records which servers' have been), Home's catalog ids of then, which dropped a
row's library (legacy ids), are rewritten to today's, and a hidden row gets the place its neighbour
in the server's order gives it. A config from before 'ordered' counts as ordered by the user only if
its order isn't the server's (the user's rule, 2026-10-05).
"""
from __future__ import absolute_import

HIDDEN = 'hidden'
ORDER = 'order'
ORDERED = 'ordered'
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


def rowLibrary(hub_identifier):
    """The sidebar entry a Home row is from, by its key on its server: a library's row its library
    (movie.genre.22.71 -> '22'), a merged row its first library (home.movies.recent.22 -> '22'),
    Recent Playlists 'playlists'; None for one from no entry (Continue Watching)."""
    if hub_identifier == 'home.playlists':
        return 'playlists'
    for part in (hub_identifier or '').split('.'):
        if part.isdigit():
            return part
    return None


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


def _id(entry):
    return entry.get('catalog_id', entry.get('identifier'))


def _order(config):
    """The full order, made from an older config's shown rows then its hidden ones if it has none
    yet (reconcile() places those properly, by the rows sent)."""
    if ORDER not in config:
        order = [_id(h) for h in config.get('hubs', [])]
        config[ORDER] = order + [cid for cid in config.get(HIDDEN, []) if cid not in order]
    return config[ORDER]


def fullOrder(config):
    """Every row the config knows, shown or hidden, in the user's order."""
    return list(_order(config))


def _sync(config, entries=None):
    """'hubs' from the order and what's hidden: the shown rows' entries, in order. entries: entries
    to use for rows that have none yet (a row shown again), by catalog id."""
    known = dict((_id(h), h) for h in config.get('hubs', []))
    known.update(entries or {})
    hidden = set(config.get(HIDDEN, ()))
    hubs = []
    for cid in _order(config):
        if cid not in hidden:
            entry = dict(known.get(cid) or {'catalog_id': cid}, order=len(hubs))
            hubs.append(entry)
    config['hubs'] = hubs


def _place(order, present, index):
    """Where a row of the rows sent (present, in the server's order; this one at index) goes in the
    order: after the nearest row before it the order has, else before the nearest after it, else
    at the end."""
    for before in reversed(present[:index]):
        if before in order:
            return order.index(before) + 1
    for after in present[index + 1:]:
        if after in order:
            return order.index(after)
    return len(order)


def reconcile(config, rows):
    """Brings a custom config up to date with the rows the server sends now. rows: [(catalog_id,
    legacy_id, server_uuid, entry)] in the server's default order (Continue Watching's server is
    ''), entry the dict to save for a new row ({'catalog_id', 'identifier', 'title'...}). Rewrites
    config in place; returns whether it changed."""
    if not config or not config.get('custom'):
        return False
    legacyServers = set(server for _, _, server, _ in rows if _isLegacy(config, server))
    changed = HIDDEN not in config or RECONCILED not in config or ORDER not in config
    hadOrder = ORDER in config
    hidden = config.setdefault(HIDDEN, [])
    reconciled = config.setdefault(RECONCILED, [])
    order = _order(config)
    entries = dict((_id(h), h) for h in config.get('hubs', []))
    present = [row[0] for row in rows]

    # a config of before: its ids of then, an unlisted row hidden
    renamed = {}
    for catalog_id, legacy_id, server, entry in rows:
        if server not in legacyServers or catalog_id in order:
            continue
        if legacy_id in renamed:
            # a second row under the one legacy id (Films' and Movies' Recently Released were both
            # movie.recentlyreleased): after the first, in the same state
            order.insert(renamed[legacy_id] + 1, catalog_id)
            renamed[legacy_id] += 1
            if renamed.get(legacy_id + '|hidden'):
                hidden.append(catalog_id)
        elif legacy_id and legacy_id != catalog_id and legacy_id in order:
            at = order.index(legacy_id)
            order[at] = catalog_id
            renamed[legacy_id] = at
            if legacy_id in hidden:
                hidden[hidden.index(legacy_id)] = catalog_id
                renamed[legacy_id + '|hidden'] = True
            elif legacy_id in entries:
                entries[catalog_id] = dict(entries.pop(legacy_id), catalog_id=catalog_id,
                                           identifier=entry.get('identifier', catalog_id))
        else:
            hidden.append(catalog_id)
        changed = True

    if not hadOrder:
        # hidden rows had no place: each goes where its neighbour in the server's order puts it
        shown = [cid for cid in order if cid not in hidden]
        for cid in [cid for cid in order if cid in hidden]:
            order.remove(cid)
        order[:] = shown
        for index, cid in enumerate(present):
            if cid in hidden and cid not in order:
                order.insert(_place(order, present, index), cid)
        order.extend(cid for cid in hidden if cid not in order)

    # new rows: shown, after their neighbour in the server's order
    placed = {}  # merged row -> its per-library rows placed after it so far
    for index, (catalog_id, _, server, entry) in enumerate(rows):
        if catalog_id in order:
            continue
        entries[catalog_id] = dict(entry)
        other = counterparts(catalog_id, order)
        if other:
            # Plex's merge setting flipped: the row takes its other form's state and place
            shown = [o for o in other if o not in hidden]
            if not shown:
                hidden.append(catalog_id)
            if _identifier(catalog_id) in MERGED_ROWS:
                # where the first of its libraries' rows was (a shown one, if any is)
                position = min(order.index(o) for o in (shown or other))
            else:
                # after the merged row, and after its other libraries' rows placed already
                merged = (shown or other)[0]
                placed[merged] = placed.get(merged, 0) + 1
                position = order.index(merged) + placed[merged]
        else:
            position = _place(order, present, index)
        order.insert(position, catalog_id)
        changed = True

    if ORDERED not in config:
        # a config from before: the user's order only if it isn't the server's
        sent = [cid for cid in order if cid in present]
        config[ORDERED] = sent != [cid for cid in present if cid in sent]
        changed = True
    if not config[ORDERED]:
        # the server's order, as it is now; a row it doesn't send stays after the row it followed
        following = _serverOrder(order, present)
        if following != order:
            order[:] = following
            changed = True

    for server in sorted(set(server for _, _, server, _ in rows)):
        if server not in reconciled:
            reconciled.append(server)
            changed = True
    if changed:
        _sync(config, entries)
    return changed


def _serverOrder(order, present):
    """order rearranged to the server's (present, the rows it sends, in its order); a row it doesn't
    send keeps its place after whichever row it followed."""
    out = [cid for cid in present if cid in order]
    for index, cid in enumerate(order):
        if cid in out:
            continue
        before = [o for o in order[:index] if o in out]
        out.insert(out.index(before[-1]) + 1 if before else 0, cid)
    return out


def hasOrder(config):
    """Whether the user has ordered the rows themselves (moved one), rather than only hidden some."""
    return bool(config and config.get('custom') and config.get(ORDERED))


def hide(config, catalog_id):
    """A row hidden, keeping its place (Manage Hubs' eye)."""
    order = _order(config)
    if catalog_id not in order:
        order.append(catalog_id)
    hidden = config.setdefault(HIDDEN, [])
    if catalog_id not in hidden:
        hidden.append(catalog_id)
    _sync(config)


def show(config, entry):
    """A hidden row shown again, where it was (at the end if the config didn't know it)."""
    catalog_id = entry['catalog_id']
    order = _order(config)
    if catalog_id not in order:
        order.append(catalog_id)
    hidden = config.setdefault(HIDDEN, [])
    if catalog_id in hidden:
        hidden.remove(catalog_id)
    _sync(config, {catalog_id: entry})


def move(config, listed_ids, from_pos, to_pos):
    """Moves a row from one place to another among the rows the dialog lists (listed_ids, in order,
    shown or hidden): rows the config knows but the server no longer sends keep their own places."""
    order = _order(config)
    slots = [i for i, cid in enumerate(order) if cid in listed_ids]
    if not (0 <= from_pos < len(slots) and 0 <= to_pos < len(slots)) or from_pos == to_pos:
        return False
    moving = [order[i] for i in slots]
    moving.insert(to_pos, moving.pop(from_pos))
    for slot, cid in zip(slots, moving):
        order[slot] = cid
    # the order is the user's from now on
    config[ORDERED] = True
    _sync(config)
    return True


def newConfig(rows):
    """A custom config of these rows ([entry] in their default order), every one shown."""
    config = {'custom': True, ORDER: [_id(e) for e in rows], HIDDEN: [], ORDERED: False}
    _sync(config, dict((_id(e), e) for e in rows))
    return config
