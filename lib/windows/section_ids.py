"""
Ids for libraries and hub rows that stay unique across servers, and the account-wide settings keyed
by them: the sidebar's show/hide/order preferences and the hub settings (Manage Hubs).

A library's id is "<server uuid>:<section key>", since a section key is only unique on its own
server (two servers both have a library "1"). Playlists and Watchlist aren't one server's and keep
their own ids, "playlists" and "/library/sections/watchlist". Home has none in the sidebar (None);
its hub settings are kept under "__home__" - one order for every server's Home rows (hubSettingsId(),
mergeHomeConfigs()).

A hub row's catalog id is "<source>|<identifier>". The source is the library's id for a library's
hub, and the server's uuid for a hub on that server's Home (its /hubs/promoted): two servers' Homes
can both have a "home.movies.recent". A Home row's identifier keeps its library
(hub_config.homeRowId()).

Both settings used to be kept per server ('home.settings.<uuid[-8:]>.<account>' and
'hub.settings.<uuid[-8:]>.<account>'), under bare section keys and "<key>:<identifier>" catalog ids.
migrate() copies them into the account-wide keys once. It never writes the old keys, so an older
build still finds its settings as they stood at the upgrade.
"""
from __future__ import absolute_import

import json
import threading
import time

from plexnet import plexapp

from lib import util

from .hub_config import homeRowId


# The old single Playlists entry, the selected server's; each server has its own now,
# "<server uuid>:playlists" (playlistsId())
PLAYLISTS_ID = 'playlists'
PLAYLISTS_KEY = 'playlists'


def playlistsId(uuid):
    return u'{0}:{1}'.format(uuid, PLAYLISTS_KEY)


def isPlaylistsId(sid):
    return sid == PLAYLISTS_ID or (sid or '').endswith(':' + PLAYLISTS_KEY)


def migratePlaylists(nav, hub_settings, uuid):
    """The old single Playlists entry - the selected server's - becomes that server's own: in the
    sidebar's entries and order, and its Manage Hubs config (key and catalog ids). Rewrites both in
    place; returns (nav changed, hub settings changed)."""
    new = playlistsId(uuid)
    navChanged = hubsChanged = False
    for name in ('entries', 'order'):
        ids = (nav or {}).get(name)
        if ids and PLAYLISTS_ID in ids:
            ids[ids.index(PLAYLISTS_ID)] = new
            navChanged = True
    config = (hub_settings or {}).pop(PLAYLISTS_ID, None)
    if config is not None:
        prefix = PLAYLISTS_ID + '|'
        if isinstance(config, dict):
            for h in config.get('hubs', []):
                if h.get('catalog_id', '').startswith(prefix):
                    h['catalog_id'] = new + h['catalog_id'][len(PLAYLISTS_ID):]
            for name in ('order', 'hidden'):
                if config.get(name):
                    config[name] = [new + c[len(PLAYLISTS_ID):] if c.startswith(prefix) else c
                                    for c in config[name]]
        hub_settings.setdefault(new, config)
        hubsChanged = True
    return navChanged, hubsChanged
WATCHLIST_ID = '/library/sections/watchlist'
HOME_STORAGE_KEY = '__home__'
# Home's Continue Watching is one row from every server: its catalog id carries none
CONTINUE_WATCHING_ID = 'continueWatching'


def sectionId(section):
    """The library's id across servers: None for Home, the fixed id for Watchlist, otherwise
    "<server uuid>:<key>" - a server's Playlists "<server uuid>:playlists". A sidebar placeholder
    (sidebar_model.LibraryPlaceholder) and a server's Playlists section carry their own."""
    stored = section.__dict__.get('sidebarId')
    if stored:
        return stored
    key = section.key
    if key is None or key in (PLAYLISTS_ID, WATCHLIST_ID):
        return key
    return u'{0}:{1}'.format(section.server.uuid, key)


def hubSettingsId(section):
    """Where a section's hub settings are kept: its library id, or "__home__" for Home."""
    if section.key is None:
        return HOME_STORAGE_KEY
    return sectionId(section)


# A Home config's servers: rows from a server it doesn't list follow its own rows in their default
# order, rather than being hidden by a custom config made before that server was in the sidebar.
HOME_SERVERS = 'servers'


def mergeHomeConfigs(hub_settings, selectedUuid=None):
    """Home's hub settings were each server's own ("<uuid>:__home__", while servers were switched
    between); Home now shows every server's rows in one order. Their custom configs become one, the
    selected server's rows first, each server's in its own order; the servers covered are recorded
    (HOME_SERVERS), so the rows of one that had no custom config still show. Rewrites hub_settings
    in place; returns whether anything changed."""
    old = [key for key in hub_settings if key and key.endswith(':' + HOME_STORAGE_KEY)]
    if not old:
        return False
    old.sort(key=lambda key: (key.partition(':')[0] != selectedUuid, key))
    hubs, servers = [], []
    for key in old:
        config = hub_settings.pop(key)
        if isinstance(config, dict) and config.get('custom'):
            servers.append(key.partition(':')[0])
            for h in sorted(config.get('hubs', []), key=lambda h: h.get('order', 999)):
                if parseCatalogId(h.get('catalog_id', ''))[1] == CONTINUE_WATCHING_ID:
                    # one row from every server now: listed once, where the first config had it
                    if any(x['catalog_id'] == CONTINUE_WATCHING_ID for x in hubs):
                        continue
                    h = dict(h, catalog_id=CONTINUE_WATCHING_ID)
                hubs.append(h)
    if servers and HOME_STORAGE_KEY not in hub_settings:
        for i, h in enumerate(hubs):
            h['order'] = i
        hub_settings[HOME_STORAGE_KEY] = {'custom': True, 'hubs': hubs, HOME_SERVERS: servers}
    return True


def catalogId(source, identifier):
    return u'{0}|{1}'.format(source, identifier)


def hubCatalogId(hub, section):
    """The catalog id of a hub fetched for `section`. On Home its source is the server whose Home
    it's on (the hub's own server) - except Continue Watching, one row from every server, which
    is just "continueWatching" - and its identifier the row's own, less what changes between
    requests (homeRowId()); elsewhere, the library and the cleaned identifier."""
    if section.key is None:
        identifier = homeRowId(hub.hubIdentifier)
        if identifier == CONTINUE_WATCHING_ID:
            return CONTINUE_WATCHING_ID
        return catalogId(hub.server.uuid, identifier)
    return catalogId(sectionId(section), hub.getCleanHubIdentifier())


def legacyHubCatalogId(hub, section):
    """The catalog id a Home row had before 7.2b, which dropped its library
    (getCleanHubIdentifier()): what older saved configs list (hub_config.reconcile()). A library's
    hub's is unchanged."""
    if section.key is None:
        identifier = hub.getCleanHubIdentifier(is_home=True)
        if identifier == CONTINUE_WATCHING_ID:
            return CONTINUE_WATCHING_ID
        return catalogId(hub.server.uuid, identifier)
    return hubCatalogId(hub, section)


def parseCatalogId(catalog_id):
    """(source, identifier). The source is a library id, Playlists' or Watchlist's id, or a server
    uuid (a Home hub)."""
    source, _, identifier = catalog_id.partition('|')
    return source, identifier


def sidebarKey():
    return 'sidebar.{0}'.format(plexapp.ACCOUNT.ID)


def hubSettingsKey():
    return 'hub.settings.{0}'.format(plexapp.ACCOUNT.ID)


def loadJson(key):
    try:
        return json.loads(util.getSetting(key, '')) or {}
    except ValueError:
        return {}
    except:
        util.ERROR()
        return {}


# Migration from the per-server settings.

def _isBareKey(key):
    """A section key as the per-server settings stored it: digits only."""
    return key is not None and str(key).isdigit()


def _rekeySection(key, uuid):
    # Home's config as each server's, as Home was then; mergeHomeConfigs() makes them one
    if _isBareKey(key) or key == HOME_STORAGE_KEY:
        return u'{0}:{1}'.format(uuid, key)
    return key


def rekeyCatalogId(catalog_id, uuid):
    """'3:movie.recentlyadded' -> '<uuid>:3|movie.recentlyadded'; 'playlists:playlists.audio' ->
    'playlists|playlists.audio'; a Home hub's bare 'home.movies.recent' -> '<uuid>|home.movies.recent'.
    An id that's already new-style is left alone."""
    if not catalog_id or '|' in catalog_id:
        return catalog_id
    source, sep, identifier = catalog_id.partition(':')
    if sep and _isBareKey(source):
        return catalogId(_rekeySection(source, uuid), identifier)
    if sep and source in (PLAYLISTS_ID, WATCHLIST_ID):
        return catalogId(source, identifier)
    return catalogId(uuid, catalog_id)


def rekeyNavSettings(nav, uuid):
    """One server's sidebar settings ({key: {"show": ...}, "order": [keys]}) under library ids."""
    out = {}
    for key, value in nav.items():
        if key == 'order':
            out[key] = [_rekeySection(k, uuid) for k in value]
        else:
            out[_rekeySection(key, uuid)] = value
    return out


# The server's old separate Continue Watching / On Deck home hubs, dropped outright (2026-09-21) in
# favour of the combined continueWatching hub the modern clients show - plexserver.hubs() no longer
# yields them, so a saved hub config still naming one would leave the user with no Continue
# Watching row at all (a custom config only shows what it lists).
OLD_CONTINUE_WATCHING_IDS = ('home.continue', 'home.ondeck')


def migrateOldContinueWatching(hub_settings):
    """Rewrites every section's saved hub list in place, on the old per-server ids: the old
    home.continue/home.ondeck entries become one continueWatching entry at the earliest of their
    positions (or just disappear if continueWatching is already listed), orders renumbered. Every
    section, not just Home - a library's custom config can pull Home's hubs in cross-section,
    under the same catalog ids. Returns whether anything changed."""
    changed = False
    for section_config in (hub_settings or {}).values():
        hubs = section_config.get('hubs') if isinstance(section_config, dict) else None
        if not hubs:
            continue
        old = [h for h in hubs if h.get('catalog_id', h.get('identifier')) in OLD_CONTINUE_WATCHING_IDS]
        if not old:
            continue
        kept = [h for h in hubs if h not in old]
        if not any(h.get('catalog_id', h.get('identifier')) == 'continueWatching' for h in kept):
            kept.append({'catalog_id': 'continueWatching',
                         'order': min(h.get('order', 999) for h in old)})
        kept.sort(key=lambda h: h.get('order', 999))
        for i, h in enumerate(kept):
            h['order'] = i
        section_config['hubs'] = kept
        changed = True
    return changed


def rekeyHubSettings(hub_settings, uuid):
    """One server's stored hub settings (Home under "__home__") under library ids and the server's
    Home id, with every catalog id rewritten."""
    hub_settings = dict(hub_settings)
    hub_settings.pop('_version', None)
    migrateOldContinueWatching(hub_settings)
    out = {}
    for key, value in hub_settings.items():
        if isinstance(value, dict) and value.get('hubs'):
            value = dict(value, hubs=[
                dict(h, catalog_id=rekeyCatalogId(h.get('catalog_id', h.get('identifier')), uuid))
                for h in value['hubs']])
        out[_rekeySection(key, uuid)] = value
    return out


def _isServersOwn(key):
    """A library's id, or a server's Home id: settings only one server's could have."""
    return key is not None and ':' in key


def mergeSettings(selected, others):
    """The account's settings (sidebar or hub, already rekeyed) from each server's. The selected
    server's are taken whole, so what it shows now doesn't change. The other servers add their own
    libraries' and Home's entries, which can't collide, and their libraries go on the end of the
    sidebar order, keeping their order among themselves. Their Playlists and Watchlist settings,
    which would change the selected server's, are dropped."""
    merged = dict(selected)
    for settings in others:
        for key, value in settings.items():
            if key == 'order':
                order = merged.setdefault('order', [])
                order.extend(k for k in value if _isServersOwn(k) and k not in order)
            elif _isServersOwn(key):
                merged.setdefault(key, value)
    return merged


def legacyServer():
    """The server settings from before account-wide keys belong to: the one selected when the add-on
    last ran (plexnet's lastServerId.<account>) - the only one the sidebar, Home and search history
    were kept for. None for an account with no such settings (hasLegacySettings()), and while that
    server isn't known yet (try again later)."""
    uuid = util.getSetting('lastServerId.{0}'.format(plexapp.ACCOUNT.ID), '')
    return plexapp.SERVERMANAGER.serversByUuid.get(uuid) if uuid else None


def hasLegacySettings():
    """Whether the account used the add-on before account-wide keys: a server was selected for it
    (legacyServer()). A new account, or one new to this device, has none - onboarding."""
    return bool(util.getSetting('lastServerId.{0}'.format(plexapp.ACCOUNT.ID), ''))


_migrated = set()
_migrateLock = threading.Lock()


def migrate():
    """Copies the per-server settings of every known server into the account-wide keys, once per
    account: the account-wide sidebar key, written last, marks it done. The selected server's are
    taken whole (mergeSettings()).

    Waits for that server (legacyServer()) to be known, which is when the known servers are. A
    server not known yet then (plex.tv down at that startup, with no cached resources) has its
    settings left behind: they stay under its old keys and are never read again."""
    account = plexapp.ACCOUNT.ID
    with _migrateLock:
        if account in _migrated:
            return
        if util.getSetting(sidebarKey(), ''):
            _migrated.add(account)
            return
        manager = plexapp.SERVERMANAGER
        if not hasLegacySettings():
            # nothing from before to move (loadNavSettings() starts a new account's sidebar)
            _migrated.add(account)
            return
        selected = legacyServer()
        if not selected:
            return
        others = [s for s in manager.getServers() if s.uuid != selected.uuid]

        def rekeyed(server):
            suffix = '{0}.{1}'.format(server.uuid[-8:], account)
            return (rekeyNavSettings(loadJson('home.settings.{0}'.format(suffix)), server.uuid),
                    rekeyHubSettings(loadJson('hub.settings.{0}'.format(suffix)), server.uuid))

        nav, hubs = rekeyed(selected)
        rest = [rekeyed(server) for server in others]
        nav = mergeSettings(nav, [n for n, _ in rest])
        hubs = mergeSettings(hubs, [h for _, h in rest])

        util.DEBUG_LOG('Settings: sidebar and hub settings moved to account-wide keys '
                       '({0} sidebar entries, {1} hub configs, from {2} servers)',
                       len(nav), len(hubs), len(others) + 1)
        util.setSetting(hubSettingsKey(), json.dumps(hubs))
        util.setSetting(sidebarKey(), json.dumps(nav))
        _migrated.add(account)


def sidebarServers():
    """The servers the sidebar has entries from, in sidebar order. Read as stored: no migration, no
    fetch (loadNavSettings()), so any thread can ask; empty until the sidebar has been moved over."""
    manager = plexapp.SERVERMANAGER
    servers, seen = [], set()
    for sid in loadJson(sidebarKey()).get('entries', ()):
        uuid, sep, _ = sid.partition(':')
        server = manager.serversByUuid.get(uuid) if sep else None
        if server is not None and uuid not in seen:
            seen.add(uuid)
            servers.append(server)
    return servers


def awaitConnection(server, timeout):
    """A server's first connection test, started if it hasn't been, and waited for (timeout s at
    most): whether it found one. Asking a server before then gets no answer - at start-up, or on a
    new account, none has been tested yet."""
    if server.activeConnection:
        return True
    if server.offline:
        return False
    if server.pendingReachabilityRequests <= 0:
        server.updateReachability(True)
    end = time.time() + timeout
    while not server.activeConnection and server.pendingReachabilityRequests > 0 and time.time() < end:
        if util.MONITOR.waitForAbort(0.05):
            break
    return bool(server.activeConnection)
