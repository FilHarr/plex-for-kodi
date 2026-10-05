"""
What the sidebar shows, apart from which entry is highlighted: its entries (Search, Home, Watchlist,
Playlists, the libraries), the stored list behind them, and the labels below them.
windowutils.SidebarMixin turns these into list items and window properties; each window keeps only
its own highlight rule (sidebarActiveSection()).

The sidebar is the libraries the user pinned, from any server on the account, in the user's order -
both set in the Libraries picker (LibraryWindow.showLibraryPicker()), which lists every library in
that order, pinned or not. One setting per account, section_ids.sidebarKey():

    {"version": 2,
     "order": ["/library/sections/watchlist", "playlists", "<server uuid>:<key>", ...],
     "entries": [the pinned ones, in that order],
     "libraries": {"<server uuid>:<key>": {"title": ..., "type": ..., "server": <server name>}}}

"order" came later: without it, the order is the pinned entries', and the picker adds the rest after
them (pickerOrder()).

A library is shown from its server's own list (serverSections(), fetched on a worker and kept),
and until its server has answered, by a LibraryPlaceholder made from what's stored, which looks
the same. Watchlist and Playlists aren't one server's; Playlists is still the selected server's. With more than one
server on the account, each library shows its server's name under its title (serverName()).
"""
from __future__ import absolute_import

import json
import threading
import time

import plexnet
from plexnet import plexapp, plexlibrary

from lib import backgroundthread
from lib import util
from lib.util import T
from . import home
from . import section_ids
from .section_ids import sectionId, PLAYLISTS_ID, WATCHLIST_ID
# section_ids' own, kept here for the windows that call them by this module: the screensaver can't
# import this one (its home import), so they live there
from .section_ids import sidebarServers, awaitConnection  # noqa: F401

SIDEBAR_VERSION = 2


class LibraryPlaceholder(object):
    """A sidebar library its server hasn't listed (yet): its server hasn't answered since the add-on
    started, isn't on the account any more, or (missing) no longer has it. Made from the title and
    type kept in the sidebar setting, so it shows like the library itself; live() swaps it for the
    real one, asking the server then if need be."""
    isPlaceholder = True

    def __init__(self, sid, meta, server, missing=False):
        self.sidebarId = sid
        self.key = sid.partition(':')[2]
        self.title = meta.get('title') or ''
        self.type = meta.get('type') or 'movie'
        self.serverName = meta.get('server') or ''
        self.server = server
        self.missing = missing

    def __eq__(self, other):
        return isinstance(other, LibraryPlaceholder) and other.sidebarId == self.sidebarId

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash(self.sidebarId)

    def __repr__(self):
        return '<LibraryPlaceholder {0} {1!r}>'.format(self.sidebarId, self.title)


def libraryMeta(section):
    return {'title': section.title, 'type': section.type, 'server': section.server.name}


# The stored list

# A new account's sidebar is marked so: no libraries until the user picks them, and Home opens the
# Libraries picker until a library is pinned (LibraryWindow.offerOnboarding(), the user's choice,
# 2026-10-05: onboarding, not a default sidebar of some server's libraries)
ONBOARDING = 'onboarding'


def loadNavSettings():
    """The sidebar's stored list (see this module's docstring), moved over from the older show/hide
    dict the first time; a new account's (onboarding), the first time there is none."""
    section_ids.migrate()
    nav = section_ids.loadJson(section_ids.sidebarKey())
    if not nav and not section_ids.hasLegacySettings():
        nav = {'version': SIDEBAR_VERSION, 'entries': [WATCHLIST_ID], 'libraries': {}, ONBOARDING: True}
        util.LOG('Sidebar: a new account - no libraries until some are picked')
        saveNavSettings(nav)
        return nav
    legacy = section_ids.legacyServer()
    if nav.get('version') == SIDEBAR_VERSION:
        if legacy is not None and section_ids.migratePlaylists(nav, None, legacy.uuid)[0]:
            # the old single Playlists entry is that server's own now
            util.LOG('Sidebar: Playlists is {0}\'s own entry now', legacy.name)
            saveNavSettings(nav)
        watchServers(nav)
        return nav
    migrated = migrateToList(nav, legacy)
    if migrated is None:
        # the server didn't list its libraries: try again next time, keep nothing now
        util.LOG('Sidebar: the old settings\' server did not list its libraries, sidebar setting not moved yet')
        return {'version': SIDEBAR_VERSION, 'entries': [WATCHLIST_ID, PLAYLISTS_ID], 'libraries': {},
                'unsaved': True}
    saveNavSettings(migrated)
    return migrated


def endOnboarding(nav):
    """A new account's sidebar has a library pinned: onboarding is over. Whether it ended."""
    if nav.get(ONBOARDING) and any(':' in sid for sid in nav.get('entries', ())):
        del nav[ONBOARDING]
        util.LOG('Sidebar: libraries picked, onboarding over')
        return True
    return False


def saveNavSettings(nav):
    watchServers(nav)
    if nav.get('unsaved'):
        return
    util.setSetting(section_ids.sidebarKey(), json.dumps(nav))


def watchServers(nav):
    """Tell plexnet which servers the sidebar has libraries from: it retests those while they're
    offline, and takes one as gone only when plex.tv drops it (PlexServerManager.serverMatters())."""
    plexapp.SERVERMANAGER.setWatchedServers(set(sid.partition(':')[0] for sid in nav.get('entries', ()) if ':' in sid))


def isOffline(section):
    """A library entry whose server isn't answering, or isn't on the account any more: it dims."""
    if ':' not in (sectionId(section) or ''):
        return False
    server = section.server
    return server is None or server.offline or server.gone


def migrateToList(nav, server):
    """The sidebar as it showed under the older setting ({id: {"show": bool}, "order": [ids]}, the
    selected server's libraries only, a library shown unless hidden): the same entries in the same
    order, now as the list of what's in it. A hidden library isn't in it. Needs the selected server's
    libraries; None if it doesn't list them."""
    sections = fetchServerSections(server) if server else None
    if sections is None:
        return None

    def shown(sid):
        return sid not in nav or nav[sid].get('show', True)

    ids = [sid for sid in (WATCHLIST_ID, PLAYLISTS_ID) if shown(sid)]
    libraries = {}
    for section in sections:
        sid = sectionId(section)
        if shown(sid):
            ids.append(sid)
            libraries[sid] = libraryMeta(section)

    order = nav.get('order')
    if order:
        # as the older sidebar sorted: by the saved order, anything not in it first
        ids.sort(key=lambda sid: order.index(sid) if sid in order else -1)

    util.LOG('Sidebar: moved to the library list ({0} entries)', len(ids))
    return {'version': SIDEBAR_VERSION, 'entries': ids, 'libraries': libraries}


def _order(nav):
    """The full order: every entry the picker lists, pinned or not."""
    if 'order' not in nav:
        nav['order'] = list(nav.get('entries', ()))
    return nav['order']


def _pinnedInOrder(nav, pinned):
    nav['entries'] = [sid for sid in _order(nav) if sid in pinned]


def addEntry(nav, section):
    """Pin a library: where it is in the order, or at the end if it's new to it."""
    sid = sectionId(section)
    if ':' in sid:
        nav['libraries'][sid] = libraryMeta(section)
    pin(nav, sid)


def pin(nav, sid):
    """Pin an entry by its id (Watchlist and Playlists have no library to describe)."""
    if sid not in _order(nav):
        nav['order'].append(sid)
    _pinnedInOrder(nav, set(nav['entries']) | {sid})


def unpin(nav, sid):
    """Unpin an entry: it leaves the sidebar, keeping its place in the order."""
    _order(nav)
    _pinnedInOrder(nav, set(nav['entries']) - {sid})


def removeEntry(nav, sid):
    """Drop an entry altogether (its server has left the account)."""
    if sid in _order(nav):
        nav['order'].remove(sid)
    if sid in nav['entries']:
        nav['entries'].remove(sid)
    nav['libraries'].pop(sid, None)


def moveEntry(nav, sid, index):
    """Move an entry to `index` in the order; the sidebar follows if it's pinned."""
    order = _order(nav)
    if sid not in order:
        return
    order.remove(sid)
    order.insert(max(0, min(index, len(order))), sid)
    _pinnedInOrder(nav, set(nav['entries']))


def pickerOrder(nav, listed, servers, playlists=None):
    """The picker's rows, in the user's order: the stored order, then anything new to it - Watchlist,
    and each listed server's libraries in its own order then its Playlists, servers as given. A
    library gone from a server that listed its libraries leaves, unless it's pinned (the sidebar
    shows it as missing until it's unpinned); so does one of a server no longer on the account,
    unless pinned, and a server's Playlists once it has none. listed: {uuid: [LibrarySection] or
    None (didn't answer)}; playlists: {uuid: whether it has any}. Stores the order and each
    library's title, type and server, and returns it."""
    playlists = playlists or {}
    order = _order(nav)
    pinned = set(nav.get('entries', ()))
    onAccount = set(server.uuid for server in servers)
    keep = []
    for sid in order:
        uuid, sep, key = sid.partition(':')
        if sep and sid not in pinned:
            if uuid not in onAccount:
                continue
            if key == section_ids.PLAYLISTS_KEY:
                if playlists.get(uuid) is False:
                    continue
            else:
                sections = listed.get(uuid)
                if sections is not None and key not in [str(s.key) for s in sections]:
                    continue
        keep.append(sid)
    if WATCHLIST_ID not in keep:
        keep.insert(0, WATCHLIST_ID)
    for server in servers:
        for section in listed.get(server.uuid) or ():
            sid = sectionId(section)
            nav['libraries'][sid] = libraryMeta(section)
            if sid not in keep:
                keep.append(sid)
        if playlists.get(server.uuid):
            sid = section_ids.playlistsId(server.uuid)
            nav['libraries'][sid] = libraryMeta(home.playlistsSection(server))
            if sid not in keep:
                keep.append(sid)
    nav['order'] = keep
    for sid in list(nav['libraries']):
        if sid not in keep:
            del nav['libraries'][sid]
    return keep


def resetOrder(nav):
    """Watchlist, then the libraries by server - the account's own servers first, then by name -
    each server's in its own order, then its Playlists. Pins stay as they are."""
    def position(sid):
        if sid == WATCHLIST_ID:
            return (0, '', 0)
        if sid == PLAYLISTS_ID:
            return (1, '', 0)
        uuid, _, key = sid.partition(':')
        known = _knownSections(uuid) or []
        keys = [str(s.key) for s in known]
        meta = nav['libraries'].get(sid, {})
        server = plexapp.SERVERMANAGER.serversByUuid.get(uuid)
        name = meta.get('server') or (server.name if server is not None else '')
        owned = server is not None and bool(getattr(server, 'owned', False))
        return (2 if owned else 3, name.lower(), keys.index(key) if key in keys else len(keys))

    _order(nav).sort(key=position)
    _pinnedInOrder(nav, set(nav['entries']))


# Each server's libraries, kept by server uuid: {uuid: (fetched at, [LibrarySection])}. Fetched on a
# worker, never on the main thread for a sidebar build, and asked again after SECTIONS_RECHECK s.
_serverSections = {}
_sectionsLock = threading.Lock()
_sectionsFetching = set()
SECTIONS_RECHECK = 60


def fetchServerSections(server):
    """The server's libraries, asked now: None if it doesn't answer. (plexnet's
    server.library.sections() answers an empty list then, which would read as "no libraries".)"""
    if server is None or server.offline:
        return None
    path = '/library/sections'
    try:
        data = server.query(path)
    except plexnet.exceptions.BadRequest as e:
        util.DEBUG_LOG('Sidebar: {0} would not list its libraries: {1}', server.name, e)
        return None
    if data is None:
        return None
    library = plexlibrary.Library(data, server=server)
    sections = []
    for elem in data:
        cls = plexlibrary.SECTION_TYPES.get(elem.attrib.get('type'))
        if cls:
            sections.append(cls(elem, initpath=path, server=server, container=library))
    _noteSections(server, sections)
    return sections


def _noteSections(server, sections):
    with _sectionsLock:
        _serverSections[server.uuid] = (time.time(), sections)


def knownSections(uuid):
    """The server's libraries as last listed (serverSections()), or None if it hasn't yet."""
    return _knownSections(uuid)


def _knownSections(uuid):
    with _sectionsLock:
        known = _serverSections.get(uuid)
    return known[1] if known else None


def _signature(sections):
    return [(str(s.key), s.title, s.type) for s in sections or ()]


def serverSections(server, onChange=None):
    """The server's libraries as last fetched, or None if it hasn't answered yet. Asked again on a
    worker when that answer is older than SECTIONS_RECHECK s; onChange() runs (on that worker) if
    the new answer differs - the sidebar is rebuilt then."""
    with _sectionsLock:
        known = _serverSections.get(server.uuid)
    if known is None or time.time() - known[0] > SECTIONS_RECHECK:
        _fetchLater(server, known and known[1], onChange)
    return known[1] if known else None


def hasListed(server):
    """Whether the server has listed its libraries since the add-on started."""
    return _knownSections(server.uuid) is not None


def _fetchLater(server, known, onChange):
    # Not before its first connection test has found a connection: the query would fail at once
    # and have it retested (PlexServer.markSuspect()) while that test is still running.
    # LibraryWindow.onServerReachable() rebuilds once it answers, which asks then.
    if server.offline or not server.activeConnection:
        return
    with _sectionsLock:
        if server.uuid in _sectionsFetching:
            return
        _sectionsFetching.add(server.uuid)
    SectionsFetchTask(server, known, onChange).start()


class SectionsFetchTask(backgroundthread.Task):
    def __init__(self, server, known, onChange):
        backgroundthread.Task.__init__(self)
        self.server = server
        self.known = known
        self.onChange = onChange

    def run(self):
        try:
            if self.isCanceled():
                return
            answer = fetchServerSections(self.server)
            if answer is None:
                return
            if (self.known is None or _signature(answer) != _signature(self.known)) and self.onChange \
                    and not self.isCanceled():
                util.DEBUG_LOG('Sidebar: {0} listed its libraries, rebuilding', self.server.name)
                self.onChange()
        except:
            util.ERROR()
        finally:
            with _sectionsLock:
                _sectionsFetching.discard(self.server.uuid)


# Why live() couldn't give a placeholder's library
UNANSWERED = 'unanswered'
MISSING = 'missing'


def live(section):
    """(the real section for a sidebar entry, None) - itself, unless it's a placeholder: its
    server is asked now. (None, UNANSWERED) if the server isn't on the account any more or doesn't
    answer; (None, MISSING) if it answers without the library."""
    if not isinstance(section, LibraryPlaceholder):
        return section, None
    if section.server is None:
        return None, UNANSWERED
    sections = fetchServerSections(section.server)
    if sections is None:
        return None, UNANSWERED
    for candidate in sections:
        if str(candidate.key) == section.key:
            return candidate, None
    return None, MISSING


def refreshWatchlistSection():
    """Build home.watchlist_section afresh, when the watchlist is on. LibraryWindow does this for
    each sidebar it builds; the other screens show the one it made. Nothing is asked of plex.tv
    (the screen asks when it's opened): the setting and the pin decide whether Watchlist is in the
    sidebar (the user, 2026-10-05), not whether it has anything in it or plex.tv answered just
    then."""
    if plexapp.ACCOUNT.isOffline or not util.getUserSetting("use_watchlist", True):
        return
    section = plexlibrary.WatchlistSection(None, server=plexapp.SERVERMANAGER.getDiscoverServer())
    section.title = T(34000, 'Watchlist')
    home.watchlist_section = section


# Whether each server has any playlists, by server uuid: the sidebar shows Playlists only then.
_hasPlaylists = {}
_playlistsLock = threading.Lock()
_playlistsChecking = set()


def notePlaylists(server, playlists):
    """Record a playlists answer fetched elsewhere (the Playlists section's own view), so the next
    sidebar build doesn't ask again. A failed fetch, which leaves the server suspect, says
    nothing."""
    if server is None or server.suspect or server.offline:
        return
    with _playlistsLock:
        _hasPlaylists[server.uuid] = bool(playlists)


def hasPlaylists(server, onChange=None):
    """Whether to show Playlists for this server. Asked on the main thread for every sidebar build,
    and a blocking query there holds up the whole screen - up to the connect timeout on a server
    that has just died. So a known answer is used as it stands, and checked again on a worker for
    next time: onChange() runs (on that worker) if it turns out to have changed. Only a server never
    asked yet is asked here, as every build used to."""
    with _playlistsLock:
        known = _hasPlaylists.get(server.uuid)
    if known is None:
        if server.offline:
            return False
        answer = server.playlists()
        notePlaylists(server, answer)
        return bool(answer)
    _checkPlaylistsLater(server, known, onChange)
    return known


def _checkPlaylistsLater(server, known, onChange):
    with _playlistsLock:
        if server.uuid in _playlistsChecking:
            return
        _playlistsChecking.add(server.uuid)
    PlaylistsCheckTask(server, known, onChange).start()


class PlaylistsCheckTask(backgroundthread.Task):
    def __init__(self, server, known, onChange):
        backgroundthread.Task.__init__(self)
        self.server = server
        self.known = known
        self.onChange = onChange

    def run(self):
        try:
            if self.isCanceled() or self.server.offline:
                return
            answer = self.server.playlists()
            notePlaylists(self.server, answer)
            with _playlistsLock:
                now = _hasPlaylists.get(self.server.uuid)
            if now is not None and now != self.known and self.onChange and not self.isCanceled():
                util.DEBUG_LOG('Sidebar: {0} {1} playlists now', self.server.name, 'has' if now else 'has no')
                self.onChange()
        except:
            util.ERROR()
        finally:
            with _playlistsLock:
                _playlistsChecking.discard(self.server.uuid)


# An entry opened from the Libraries picker that isn't pinned: shown at the end of the sidebar while
# it's the section open (the user's design, 2026-10-05), so everything that goes by the sidebar -
# its highlight, Back, its menu - works as for a pinned one. One at a time, for every screen's
# sidebar; LibraryWindow.openSection() lets it go when another section opens.
_temporary = None


def setTemporary(sid):
    global _temporary
    _temporary = sid


def temporary():
    return _temporary


def leaveTemporaryFor(section):
    """The section now open isn't the temporary entry's: it goes. Returns whether it did."""
    global _temporary
    if _temporary is None or sectionId(section) == _temporary:
        return False
    _temporary = None
    return True


def sections(nav, onChange=None):
    """The sidebar's entries after Search and Home, in the user's order: Watchlist and Playlists when
    they're in it and there's something to show, and the libraries - live where their server has
    listed them, placeholders where it hasn't - then the temporary entry, if one's open.
    onChange() (on a worker) when a server's answer changes what this showed."""
    manager = plexapp.SERVERMANAGER
    entries = []
    renamed = False
    ids = list(nav.get('entries', ()))
    if _temporary is not None and _temporary not in ids:
        ids.append(_temporary)
    for sid in ids:
        if sid == WATCHLIST_ID:
            if (not plexapp.ACCOUNT.isOffline and util.getUserSetting("use_watchlist", True)
                    and home.watchlist_section):
                entries.append(home.watchlist_section)
        elif section_ids.isPlaylistsId(sid):
            # a server's Playlists (the old single entry: the old settings' server's), when it has any
            uuid = sid.partition(':')[0] if ':' in sid else None
            server = manager.serversByUuid.get(uuid) if uuid else section_ids.legacyServer()
            if server and hasPlaylists(server, onChange=onChange):
                entries.append(home.playlistsSection(server))
        elif sid:
            entry = _libraryEntry(nav, sid, onChange)
            if entry.__dict__.get('sidebarId') is None:
                meta = libraryMeta(entry)
                if nav['libraries'].get(sid) != meta:
                    nav['libraries'][sid] = meta
                    renamed = True
            entries.append(entry)
    if renamed:
        saveNavSettings(nav)
    return entries


def _libraryEntry(nav, sid, onChange):
    uuid, _, key = sid.partition(':')
    server = plexapp.SERVERMANAGER.serversByUuid.get(uuid)
    meta = nav.get('libraries', {}).get(sid, {})
    known = serverSections(server, onChange) if server else None
    if known is not None:
        for section in known:
            if str(section.key) == key:
                return section
    return LibraryPlaceholder(sid, meta, server, missing=known is not None)


def serverName(section):
    """The server a library entry is from, for the second line under its title - only when the
    account has more than one server, and only for libraries (Watchlist and Playlists aren't one
    server's). Empty otherwise: the entry keeps its one line."""
    if len(plexapp.SERVERMANAGER.getServers()) < 2 or ':' not in (sectionId(section) or ''):
        return ''
    if section.server is not None:
        return section.server.name
    return section.__dict__.get('serverName') or ''


def matchSection(entries, key, fromWatchlist=False, server=None):
    """The entry for a library key; failing that, Watchlist when the screen was reached from it.
    key can be a real section's key, empty, or "watchlist" (what discover items report), which
    matches no entry and so falls through to the Watchlist check. Two servers can both have a
    library with this key: the one on `server` then, if given."""
    if key:
        matches = [section for section in entries if section.key == key]
        if server is not None:
            matches = [section for section in matches
                       if section.server is not None and section.server.uuid == server.uuid] or matches
        if matches:
            return matches[0]
    if fromWatchlist:
        return home.watchlist_section
    return None


def serverAndUserProperties():
    """The window properties for the user's avatar and name, and the Libraries button below the
    sidebar (it opens the picker). Its icon says when none of the sidebar's servers is answering."""
    account = plexapp.ACCOUNT
    title = account.title or account.username or ' '
    props = [
        ('user.name', title),
        ('user.avatar', account.safeUserThumb(account.ID, thumb=account.thumb)),
        ('user.avatar.letter', title[0].upper()),
    ]

    servers = sidebarServers()
    if servers and all(server.offline for server in servers):
        icon = 'script.plex/home/device/error.png'
    else:
        icon = 'script.plex/home/device/plex.png'
    props += [('server.name', T(33722, 'Libraries')),
              ('server.icon', icon),
              ('server.iconmod', ''),
              ('server.iconmod2', '')]
    return props
