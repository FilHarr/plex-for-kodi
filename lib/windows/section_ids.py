"""
Ids for libraries and hub rows that stay unique across servers, and the account-wide settings keyed
by them: the sidebar's show/hide/order preferences and the hub settings (Manage Hubs).

A library's id is "<server uuid>:<section key>", since a section key is only unique on its own
server (two servers both have a library "1"). Playlists and Watchlist aren't one server's and keep
their own ids, "playlists" and "/library/sections/watchlist". Home has none in the sidebar (None).
Its hub settings are each server's own until Home shows hubs from several servers:
"<server uuid>:__home__" (hubSettingsId()).

A hub row's catalog id is "<source>|<identifier>". The source is the library's id for a library's
hub, and the server's uuid for a hub on that server's Home (its /hubs): two servers' Homes can both
have a "home.movies.recent".

Both settings used to be kept per server ('home.settings.<uuid[-8:]>.<account>' and
'hub.settings.<uuid[-8:]>.<account>'), under bare section keys and "<key>:<identifier>" catalog ids.
migrate() copies them into the account-wide keys once. It never writes the old keys, so an older
build still finds its settings as they stood at the upgrade.
"""
from __future__ import absolute_import

import json
import threading

from plexnet import plexapp

from lib import util


PLAYLISTS_ID = 'playlists'
WATCHLIST_ID = '/library/sections/watchlist'
HOME_STORAGE_KEY = '__home__'


def sectionId(section):
    """The library's id across servers: None for Home, the fixed id for Playlists and Watchlist,
    otherwise "<server uuid>:<key>"."""
    key = section.key
    if key is None or key in (PLAYLISTS_ID, WATCHLIST_ID):
        return key
    return u'{0}:{1}'.format(section.server.uuid, key)


def hubSettingsId(section):
    """Where a section's hub settings are kept: its library id, or for Home, the Home of the server
    it's showing."""
    if section.key is None:
        return u'{0}:{1}'.format(section.server.uuid, HOME_STORAGE_KEY)
    return sectionId(section)


def catalogId(source, identifier):
    return u'{0}|{1}'.format(source, identifier)


def hubCatalogId(hub, section):
    """The catalog id of a hub fetched for `section`. On Home its source is the server whose Home
    it's on (the hub's own server); elsewhere, the library."""
    is_home = section.key is None
    source = hub.server.uuid if is_home else sectionId(section)
    return catalogId(source, hub.getCleanHubIdentifier(is_home=is_home))


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


_migrated = set()
_migrateLock = threading.Lock()


def migrate():
    """Copies the per-server settings of every known server into the account-wide keys, once per
    account: the account-wide sidebar key, written last, marks it done. The selected server's are
    taken whole (mergeSettings()).

    Waits for a selected server, which is when the known servers are. A server not known yet
    then (plex.tv down at that startup, with no cached resources) has its settings left behind:
    they stay under its old keys and are never read again."""
    account = plexapp.ACCOUNT.ID
    with _migrateLock:
        if account in _migrated:
            return
        if util.getSetting(sidebarKey(), ''):
            _migrated.add(account)
            return
        manager = plexapp.SERVERMANAGER
        selected = manager.selectedServer
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
