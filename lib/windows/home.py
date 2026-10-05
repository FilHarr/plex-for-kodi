from __future__ import absolute_import

import threading
import time

import plexnet
from kodi_six import xbmcgui
from plexnet import plexapp, plexlibrary, plexobjects

from lib import backgroundthread
from lib import util
from lib.path_mapping import pmm
from lib.util import T
from . import hub_config
from . import background
from .section_ids import CONTINUE_WATCHING_ID


HUBS_REFRESH_INTERVAL = 300  # 5 Minutes
REACHABILITY_CHECK_INTERVAL = 600  # 10 Minutes
PATH_MAPPING_PROBE_INTERVAL = 60  # 1 Minute
HUB_PAGE_SIZE = 10
# Hard cap on what a Recommended hub row shows, fetched in one go (SectionHubsTask below) - no
# in-row pagination past it. A row with more than this (hub.more) ends in a "See more" item
# instead (LibraryWindow._bindHubToControl(), library.py). On request, 2026-09-21.
HUB_ROW_MAX_ITEMS = 20

MOVE_SET = frozenset(
    (
        xbmcgui.ACTION_MOVE_LEFT,
        xbmcgui.ACTION_MOVE_RIGHT,
        xbmcgui.ACTION_MOVE_UP,
        xbmcgui.ACTION_MOVE_DOWN,
        xbmcgui.ACTION_MOUSE_MOVE,
        xbmcgui.ACTION_PAGE_UP,
        xbmcgui.ACTION_PAGE_DOWN,
        xbmcgui.ACTION_FIRST_PAGE,
        xbmcgui.ACTION_LAST_PAGE,
        xbmcgui.ACTION_MOUSE_WHEEL_DOWN,
        xbmcgui.ACTION_MOUSE_WHEEL_UP
    )
)

NO_HUB = "__NO_HUB__"

PLAYLIST_HUB_TITLES = {
    'playlists.audio': T(34094, 'Audio Playlists'),
    'playlists.video': T(34095, 'Video Playlists'),
}

class HubsList(list):
    identifier = NO_HUB
    def init(self):
        self.lastUpdated = time.time()
        self.invalid = False
        return self


def getRequiredSourceSections(hub_settings, section_key):
    """Source section keys a section's custom hub config pulls cross-section hubs from.

    Extracted from the now-deleted HomeWindow (not currently wired into LibraryWindow - see
    getCombinedHubsForSection's own docstring)."""
    required = set()

    if not hub_settings:
        return required

    config_key = str(section_key) if section_key is not None else None
    section_config = hub_settings.get(config_key)
    if not section_config or not section_config.get('custom'):
        return required

    for hub_config in section_config.get('hubs', []):
        catalog_id = hub_config.get('catalog_id', '')
        if ':' in str(catalog_id):
            source_key = catalog_id.split(':')[0]
            required.add(source_key)
        else:
            required.add(None)  # Home section hub

    return required


def getEnabledHubsForSection(hub_settings, section_key):
    """Enabled hub catalog_ids for a section's custom hub config.

    Extracted from the now-deleted HomeWindow (not currently wired into LibraryWindow - see
    getCombinedHubsForSection's own docstring)."""
    if not hub_settings:
        return None

    config_key = str(section_key) if section_key is not None else None
    section_config = hub_settings.get(config_key)
    if not section_config or not section_config.get('custom'):
        return None

    # No old/new Continue Watching identifier mapping here any more - the old home.continue/
    # home.ondeck pair is gone (plexserver.hubs() only ever yields continueWatching) and saved
    # configs are migrated on load (LibraryWindow.loadHubSettings(), library.py).
    return {h.get('catalog_id', h.get('identifier')) for h in section_config.get('hubs', [])}


def getCombinedHubsForSection(section, section_hubs, hub_settings, include_cross_section=True,
                               fetch_missing_sections=None):
    """Combine a section's native hubs with any cross-section hubs its custom config pulls in.

    Extracted from the now-deleted HomeWindow as a standalone function rather than ported to
    LibraryWindow - quiet-orbiting-heron.md's item 10 (cross-section hub aggregation, e.g. an
    "Add to Home" action) is explicit future work, not yet wired to any live window. Kept here,
    tests intact, so that work has a starting point instead of only a git-history reference.

    fetch_missing_sections(missing_keys), if given, is called when a required source section
    isn't cached in section_hubs yet - HomeWindow's own version kicked off a background
    SectionHubsTask fetch there; callers that don't need that (e.g. tests) can leave it as None.
    """
    section_key = section.key
    is_home = section_key is None

    # Get native hubs for this section
    native_hubs = section_hubs.get(section_key)
    if native_hubs is None:
        return None

    # Check if we have custom config with cross-section hubs
    if not include_cross_section:
        return native_hubs

    # Normalize key to string (hubSettings uses string keys)
    config_key = str(section_key) if section_key is not None else None
    section_config = hub_settings.get(config_key) if hub_settings else None

    if not section_config or not section_config.get('custom'):
        # No custom config - show native hubs from Plex as-is
        return native_hubs

    # Get enabled hub catalog_ids
    enabled_catalog_ids = getEnabledHubsForSection(hub_settings, section_key)
    if enabled_catalog_ids is None:
        return native_hubs

    # Get required source sections
    required_sources = getRequiredSourceSections(hub_settings, section_key)

    # Helper to find section in section_hubs (handles string/int key mismatch)
    def find_in_section_hubs(key):
        if key in section_hubs:
            return section_hubs[key]
        # Try string version of key
        str_key = str(key) if key is not None else None
        for cached_key in section_hubs:
            if str(cached_key) == str_key:
                return section_hubs[cached_key]
        return None

    # Check if all required source sections are cached
    missing_sources = []
    for source_key in required_sources:
        str_section_key = str(section_key) if section_key is not None else None
        str_source_key = str(source_key) if source_key is not None else None
        if str_source_key != str_section_key and find_in_section_hubs(source_key) is None:
            missing_sources.append(source_key)

    if missing_sources:
        if fetch_missing_sections:
            fetch_missing_sections(missing_sources)
        # Filter native hubs based on enabled list while waiting
        filtered_native = []
        for hub in native_hubs:
            clean_id = hub.getCleanHubIdentifier(is_home=is_home)
            if section_key is None:
                catalog_id = clean_id
            else:
                catalog_id = '{}:{}'.format(section_key, clean_id)
            if catalog_id in enabled_catalog_ids:
                hub._crossSectionSource = section_key
                hub._catalogId = catalog_id
                filtered_native.append(hub)
        result = HubsList(filtered_native)
        result.identifier = section_key
        result.lastUpdated = native_hubs.lastUpdated
        result.invalid = native_hubs.invalid
        return result

    # Combine hubs from all required sources
    combined = []
    seen_identifiers = set()

    for source_key in required_sources:
        source_hubs = find_in_section_hubs(source_key) or []
        source_is_home = source_key is None or str(source_key) == 'None'

        for hub in source_hubs:
            clean_id = hub.getCleanHubIdentifier(is_home=source_is_home)

            if source_key is None:
                catalog_id = clean_id
            else:
                catalog_id = '{}:{}'.format(source_key, clean_id)

            if catalog_id not in enabled_catalog_ids:
                continue

            # Dedup on the hub itself, not on catalog_id: the clean identifier strips the
            # numeric suffixes Plex uses to tell same-type sections apart, so two libraries'
            # "Recently Added" home hubs share one catalog_id and the second would vanish.
            dedup_key = (str(source_key), hub.hubIdentifier)
            if dedup_key in seen_identifiers:
                continue
            seen_identifiers.add(dedup_key)

            hub._crossSectionSource = source_key
            hub._catalogId = catalog_id
            combined.append(hub)

    # Sort by user's configured order
    configured_hubs = section_config.get('hubs', [])
    catalog_id_to_order = {h.get('catalog_id', h.get('identifier')): i for i, h in enumerate(configured_hubs)}

    def get_order(hub):
        cat_id = getattr(hub, '_catalogId', None)
        if cat_id and cat_id in catalog_id_to_order:
            return catalog_id_to_order[cat_id]
        return 999

    combined.sort(key=get_order)

    result = HubsList(combined)
    result.identifier = section_key
    result.lastUpdated = native_hubs.lastUpdated
    result.invalid = native_hubs.invalid

    return result


def attributeCrossSectionHub(all_sections, hub, section, is_home):
    """Set _displayTitle on a hub shown outside its source section, naming the source.

    A hub rendered in a foreign section is indistinguishable from a native one, so it
    always gets its source library appended. A substring test is not enough to skip
    that: a library named "Movies" also matches "Recently Released Movies", leaving
    foreign hubs unattributed; only an outright identical title stays bare.

    Extracted from the now-deleted HomeWindow (not currently wired into LibraryWindow - see
    getCombinedHubsForSection's own docstring)."""
    source_key = hub.__dict__.get('_crossSectionSource') if '_crossSectionSource' in hub.__dict__ else "__UNDEF__"
    source_is_home = source_key is None
    if not hub.title:
        return

    if source_key is None and hub.hubIdentifier:
        parts = hub.hubIdentifier.rsplit('.', 2)
        if len(parts) >= 2 and parts[-2].isdigit():
            source_key = parts[-2]
    if not source_is_home and source_key != "__UNDEF__" and section.key != source_key:
        # hub's source is a different library than the current section
        section_obj = all_sections.get(str(source_key))
        if section_obj and section_obj.title.lower() != hub.title.lower():
            hub._displayTitle = u'{} — {}'.format(hub.title, section_obj.title)
    elif source_is_home and not is_home:
        # hub's source is Home
        hub._displayTitle = u'{} — {}'.format(hub.title, T(32332, 'Home'))



class SectionHubsTask(backgroundthread.Task):
    def setup(self, section, callback, reselect_pos_dict=None):
        self.section = section
        self.callback = callback
        self.reselect_pos_dict = reselect_pos_dict
        return self

    def run(self):
        if self.isCanceled():
            return

        if not self.section.server:
            return

        try:
            hubs = HubsList(self.section.server.hubs(self.section.key, count=HUB_ROW_MAX_ITEMS)).init()
            hubs.identifier = self.section.key
            if self.isCanceled():
                return
            self.callback(self.section, hubs, reselect_pos_dict=self.reselect_pos_dict)
        except plexnet.exceptions.BadRequest:
            util.DEBUG_LOG('404 on section: {0}', repr(self.section.title))
            hubs = HubsList().init()
            hubs.invalid = True
            self.callback(self.section, hubs)
        except:
            util.ERROR("No data - deleted or server disconnected?", notify=True, time_ms=5000)
            util.DEBUG_LOG('Generic exception when fetching section: {0}', repr(self.section.title))
            hubs = HubsList().init()
            hubs.invalid = True
            self.callback(self.section, hubs)



# Home waits for every server's rows, but no longer than this once one has answered: the rows bind
# together, and a server slower than that has its rows added in place when they come (D8's first
# variant, plan Phase 7). 1 s (the user, 2026-10-05; was 2 s): since late rows are added in place
# the wait buys less, and on the AM6B both servers answered within 0.4 s, unaffected either way.
HOME_LATE_SERVER_BUDGET = 1.0
# ...and for a first answer at all no longer than this (and for a late one)
HOME_FETCH_TIMEOUT = 20.0
# D8's second variant, to compare live: bind as soon as the first server answers, and add each
# other server's rows in place as they come.
HOME_BIND_PROGRESSIVE = False


def keepLibraries(hub, keys):
    """A row's items from these libraries only: what the request asked for (contentDirectoryID),
    checked again, as a server's older versions don't all honour the filter. An item with no
    library (a playlist) stays."""
    hub.items = [item for item in hub.items
                 if not item.getLibrarySectionId() or str(item.getLibrarySectionId()) in keys]
    return hub


def mergeContinueWatching(hubs, positions=None):
    """One Continue Watching row from each server's: most recently watched first, each item once
    (decided 2026-10-05). A film in two libraries comes back twice, once per library, with the same
    progress (a server keeps a guid's watch state in step) - the copy from the library highest in
    the sidebar stays (positions: {(server uuid, library key): place}), so the user picks which by
    their sidebar order; on two servers, which don't share progress, the one watched last stays.
    At most HUB_ROW_MAX_ITEMS. One server's row keeps its "See more"; a merged one has none - its
    later pages would be per server."""
    if not hubs:
        return None
    positions = positions or {}
    entries = [(getattr(hub.server, 'uuid', None), item) for hub in hubs for item in hub.items]

    def rank(entry):
        uuid, item = entry
        viewed = item.lastViewedAt.asInt() if item.get('lastViewedAt') else 0
        place = positions.get((uuid, str(item.getLibrarySectionId())))
        return (-viewed, place if place is not None else len(positions))

    items, seen = [], set()
    for _, item in sorted(entries, key=rank):
        guid = item.get('guid')
        if guid and guid in seen:
            continue
        seen.add(guid)
        items.append(item)
    merged = hubs[0]
    merged.items = items[:HUB_ROW_MAX_ITEMS]
    if len(hubs) > 1:
        merged.more = plexobjects.PlexValue('0', merged)
    return merged


def sidebarOrder(rows, positions):
    """Home's rows from every server in the sidebar's order (the user, 2026-10-05: libraries of
    different servers interleave there, so their rows do on Home). rows: [(server uuid, hub)], each
    server's in its own order (Plex's, its libraries in sidebar order), servers in sidebar order;
    positions: {(server uuid, entry key): place in the sidebar}. Each row goes by its library's place
    (hub_config.rowLibrary()), a library's rows in Plex's order; one from no entry stays after the
    row before it from its server, or first."""
    placed = []
    last = {}
    for index, (uuid, hub) in enumerate(rows):
        library = hub_config.rowLibrary(hub.hubIdentifier)
        position = positions.get((uuid, library)) if library is not None else None
        if position is None:
            position = last.get(uuid, -1)
        last[uuid] = position
        placed.append((position, index, uuid, hub))
    placed.sort(key=lambda row: (row[0], row[1]))
    return [(uuid, hub) for _, _, uuid, hub in placed]


def combineHomeHubs(answers, servers, positions=None):
    """Home's rows from each server's answer, as D5's default order has them before the user's
    own (LibraryWindow.sortHubsByUserOrder()): one merged Continue Watching row, then every server's
    rows in sidebar order (sidebarOrder(); without positions, each server's together, servers in
    sidebar order). answers: {uuid: [Hub]}; servers: [(server, keys)]."""
    continueWatching, rows = [], []
    for server, keys in servers:
        for hub in answers.get(server.uuid) or ():
            if hub.hubIdentifier == CONTINUE_WATCHING_ID:
                continueWatching.append(keepLibraries(hub, keys))
            else:
                rows.append((server.uuid, keepLibraries(hub, keys)))
    if positions:
        rows = sidebarOrder(rows, positions)
    merged = mergeContinueWatching(continueWatching, positions)
    return HubsList(([merged] if merged is not None else []) + [hub for _, hub in rows]).init()


class HomeHubsTask(backgroundthread.Task):
    """Home's rows from every server with libraries in the sidebar, asked together (a thread
    each), then combined (combineHomeHubs()) and handed to the callback: when all have answered,
    or HOME_LATE_SERVER_BUDGET after the first did (HOME_BIND_PROGRESSIVE: as soon as the first
    has). A server that answers after that has every row so far handed to lateCallback, to rebind
    in place. servers: [(server, keys)] in sidebar order, keys being its sidebar entries
    (libraries, 'playlists'). A server known to be offline isn't asked; one still on its first
    connection test is, once that finds a connection."""

    def setup(self, section, callback, servers, positions=None, lateCallback=None):
        self.section = section
        self.callback = callback
        self.servers = servers
        self.positions = positions
        self.lateCallback = lateCallback
        return self

    def _combined(self, answers):
        hubs = combineHomeHubs(dict(answers), self.servers, self.positions)
        hubs.identifier = None
        return hubs

    def _fetch(self, server, keys, answers):
        deadline = time.time() + HOME_FETCH_TIMEOUT
        if not server.activeConnection and server.pendingReachabilityRequests <= 0:
            # Its first connection test hasn't started: at start-up the selected server is tested
            # first and the others a few seconds later, and Home is asking now (live 2026-10-04:
            # every start bound Home without Oscar's rows).
            server.updateReachability(True)
        while (not server.activeConnection and server.pendingReachabilityRequests > 0
               and time.time() < deadline and not self.isCanceled()):
            util.MONITOR.waitForAbort(0.05)
        if self.isCanceled() or server.offline or not server.activeConnection:
            return
        try:
            answers[server.uuid] = server.hubs(None, count=HUB_ROW_MAX_ITEMS, section_ids=list(keys))
        except plexnet.exceptions.BadRequest:
            util.DEBUG_LOG('Home: {0} would not give its rows', repr(server.name))
        except:
            util.ERROR()

    def run(self):
        if self.isCanceled():
            return
        started = time.time()
        answers = {}
        threads = []
        for server, keys in self.servers:
            if server.offline or server.gone:
                continue
            thread = threading.Thread(target=self._fetch, args=(server, keys, answers),
                                      name='home.' + server.name)
            thread.daemon = True
            thread.start()
            threads.append((server, thread))

        firstAnswer = None
        while any(thread.is_alive() for _, thread in threads) and not self.isCanceled():
            now = time.time()
            if answers and firstAnswer is None:
                firstAnswer = now
                if HOME_BIND_PROGRESSIVE:
                    break
            if firstAnswer is not None and now - firstAnswer > HOME_LATE_SERVER_BUDGET:
                break
            if now - started > HOME_FETCH_TIMEOUT:
                break
            util.MONITOR.waitForAbort(0.02)
        if self.isCanceled():
            return

        late = [server.name for server, thread in threads if thread.is_alive()]
        util.DEBUG_LOG('Home: rows from {0} of {1} servers in {2} ms{3}', len(answers), len(threads),
                       int((time.time() - started) * 1000), late and ' (not waited for: {0})'.format(', '.join(late)) or '')
        bound = set(answers)
        self.callback(self.section, self._combined(answers))
        if late and self.lateCallback:
            # the rest, in place as they come - on a thread of its own, not holding a worker
            waiter = threading.Thread(target=self._awaitLate, args=(threads, answers, bound, started),
                                      name='home.late')
            waiter.daemon = True
            waiter.start()

    def _awaitLate(self, threads, answers, bound, started):
        deadline = started + HOME_FETCH_TIMEOUT
        while not self.isCanceled():
            alive = any(thread.is_alive() for _, thread in threads)
            if set(answers) != bound:
                added = [server.name for server, _ in threads if server.uuid in set(answers) - bound]
                bound = set(answers)
                util.DEBUG_LOG('Home: rows from {0} came late ({1} ms), added in place', ', '.join(added),
                               int((time.time() - started) * 1000))
                self.lateCallback(self.section, self._combined(answers))
            if not alive or time.time() > deadline:
                return
            util.MONITOR.waitForAbort(0.1)


class PathMappingProbeTask(backgroundthread.Task):
    """Checks the Kodi-side roots of mapped libraries. Runs in the background because a
    dead SMB/NFS share blocks for the full mount timeout, which would stall the section
    list every time Home is drawn.
    """
    def setup(self, targets, callback):
        self.targets = targets
        self.callback = callback
        return self

    def run(self):
        changed = False
        announce = []
        util.DEBUG_LOG("Path mapping probe: checking {} root(s)", len(self.targets))
        for server_name, map_path, title in self.targets:
            if self.isCanceled():
                return

            if pmm.verifyMapping(server_name, map_path):
                changed = True
            util.DEBUG_LOG("Path mapping probe: {} -> {}", map_path,
                           pmm.isMappingBroken(server_name, map_path) and "unreachable" or "ok")

            if (pmm.isMappingBroken(server_name, map_path)
                    and pmm.claimNotification(server_name, map_path, "root")):
                announce.append(title or map_path)

        if self.isCanceled():
            return

        if announce:
            # one popup for the whole run: Kodi queues notifications, so one per library
            # would keep the screen covered for 5s * number of mapped libraries
            pmm.notify(T(35037, "Path mapping unavailable for: {}").format(" / ".join(announce)))

        if changed:
            self.callback()


class UpdateHubTask(backgroundthread.Task):
    def setup(self, hub, callback, reselect_pos=None):
        self.hub = hub
        self.callback = callback
        self.reselect_pos = reselect_pos
        return self

    def run(self):
        if self.isCanceled():
            return

        if not plexapp.SERVERMANAGER.serversByUuid:
            # signed out: no servers
            return

        try:
            self.hub.reload(limit=HUB_PAGE_SIZE)
            if self.isCanceled():
                return
            self.callback(self.hub, reselect_pos=self.reselect_pos)
        except plexnet.exceptions.BadRequest:
            util.DEBUG_LOG('404 on hub: {0}', repr(self.hub.hubIdentifier))
        except util.NoDataException:
            util.ERROR("No data - deleted or server disconnected?", notify=True, time_ms=5000)
        except:
            util.DEBUG_LOG('Something went wrong when updating hub: {0}', repr(self.hub.hubIdentifier))


class ExtendHubTask(backgroundthread.Task):
    def setup(self, hub, callback, canceledCallback=None, size=HUB_PAGE_SIZE, reselect_pos=None):
        self.hub = hub
        self.callback = callback
        self.canceledCallback = canceledCallback
        self.size = size
        self.reselect_pos = reselect_pos
        return self

    def run(self):
        if self.isCanceled():
            if self.canceledCallback:
                self.canceledCallback(self.hub)
            return

        if not plexapp.SERVERMANAGER.serversByUuid:
            # signed out: no servers
            return

        try:
            size = self.size
            if self.reselect_pos is not None:
                rk, pos = self.reselect_pos
                if pos == -1:
                    # we need the full hub if we want to round-robin
                    size = util.addonSettings.hubsRrMax
            start = self.hub.offset.asInt() + self.hub.size.asInt()
            items = self.hub.extend(start=start, size=size)
            if self.isCanceled():
                if self.canceledCallback:
                    self.canceledCallback(self.hub)
                return
            # Hub.extend() (plexlibrary.py) only returns the newly-fetched page - it doesn't append
            # to self.hub.items, so without this, hub.items stays frozen at its original first-page
            # size for the object's whole lifetime. That's invisible as long as the same physical
            # control stays bound to a hub forever (pagination then lives only in that control's own
            # ManagedControlList), but any full rebuild from hub.items - _bindAllHubSlots() re-binding
            # a previously-paginated hub after navigating away and back, or a peek row bind - would
            # silently drop everything past the first page, stranding any remembered position beyond
            # it. Keeping hub.items itself authoritative fixes every rebuild path at once.
            self.hub.items.extend(items)
            self.callback(self.hub, items, reselect_pos=self.reselect_pos)
        except plexnet.exceptions.BadRequest:
            util.DEBUG_LOG('404 on hub: {0}', repr(self.hub.hubIdentifier))
            if self.canceledCallback:
                self.canceledCallback(self.hub)
        except util.NoDataException:
            util.ERROR("No data - deleted or server disconnected?", notify=True, time_ms=5000)
        except:
            util.DEBUG_LOG('Something went wrong when extending hub: {0}', repr(self.hub.hubIdentifier))
            util.ERROR()


class VirtualSection(object):
    locations = []
    isMapped = False
    mappedPaths = []
    mappingBroken = False

    # Home and Watchlist are no server's: Home's rows come from every Home server
    # (LibraryWindow._homeServers()), Watchlist's from plex.tv
    server = None

    def getServer(self):
        # LibrarySettings.__init__ (library.py) calls this unconditionally on whatever section
        # it's given, real or virtual - PlexObject.getServer() is just `return self.server`, so
        # mirror that here rather than requiring every VirtualSection to be a real PlexObject.
        return self.server


class _EmptySectionResultType(object):
    # Just enough of section.all()/.folder()'s real return shape for LibraryWindow.fill()'s
    # totalSize.asInt() check to see zero items and take its own existing empty-content path.
    totalSize = plexobjects.PlexValue('0')


_EmptySectionResult = _EmptySectionResultType()


class HomeSection(VirtualSection):
    key = None
    type = 'home'
    title = T(32332, 'Home')

    locations = []
    isMapped = False

    # Enough of a real-section surface for LibraryWindow's construction path (LibrarySettings,
    # reset()'s TYPE/DEFAULT_SORT/key handling) to not crash when opening home_section as
    # LibraryWindow(section=home_section). Deliberately hand-written rather than subclassing
    # LibrarySection/PlexObject - Home has no poster-grid query to inherit, its content is
    # entirely hub-based (SectionHubsTask), so none of that machinery would ever be used.
    TYPE = 'mixed'
    DEFAULT_SORT = 'titleSort'
    DEFAULT_SORT_DESC = False
    # LibraryWindow.fill()'s own collectionMode lookup (self.section.settings.get(...)) expects
    # every real LibrarySection's live server-fetched dict. Home has no such settings to fetch -
    # empty means "always take the fallback default" there, harmless since Home's Library-tab
    # content is a placeholder until Recommended-tab sharing lands.
    settings = {}

    def getLibrarySectionId(self):
        # key stays None - that's Home's identity sentinel throughout this file's hub logic, not
        # something to change here. This is only reached by LibraryWindow.reset()'s
        # viewtype-setting-key fallback, so any stable literal works.
        return 'home'

    # LibraryWindow's poster-grid content-fetch surface (fill(), library.py) - Home has no
    # poster-grid query at all, so these are a deliberate, permanent "no content" stand-in:
    # opening LibraryWindow(home_section) shows a clean empty Library tab rather than crashing.
    # Real content there is Recommended-tab sharing's job (porting SectionHubsTask into
    # LibraryWindow's own tabs) - until then, Home's actual content isn't reachable through this
    # window at all.
    def jumpList(self, *args, **kwargs):
        # None -> library.py's fill() already falls back to all() below when a jump list is
        # unavailable for the current sort/type combo - the exact same fallback a real section
        # takes when the server's own jumpList endpoint doesn't support it.
        return None

    def all(self, *args, **kwargs):
        return _EmptySectionResult

    def folder(self, *args, **kwargs):
        return _EmptySectionResult


home_section = HomeSection()

watchlist_section = None


class PlaylistsSection(VirtualSection):
    """A server's playlists, as a section: a sidebar entry of its own per server,
    "<server uuid>:playlists" (sidebarId, which section_ids.sectionId() honours), shown and placed
    like a library (plan 7.2b). One per server (playlistsSection()). Made with no server, it's the
    selected server's (the old single entry, while its setting is moved over)."""
    key = 'playlists'
    type = 'playlists'
    title = T(32333, 'Playlists')

    def __init__(self, server=None):
        self._server = server
        if server is not None:
            self.sidebarId = u'{0}:playlists'.format(server.uuid)

    @property
    def server(self):
        return self._server

    locations = []
    isMapped = False

    # Enough of a real-section surface for LibraryWindow's construction path (LibrarySettings,
    # reset()'s TYPE/DEFAULT_SORT/key handling) to not crash when opening
    # LibraryWindow(section=playlists_section) - Playlists port, ported from the Sidebar-Tab-
    # Unification branch's identical addition (mirrors HomeSection's own docstring/reasoning above).
    TYPE = 'playlists'
    DEFAULT_SORT = 'titleSort'
    DEFAULT_SORT_DESC = False
    settings = {}

    def getLibrarySectionId(self):
        # key is already a real, non-None string ('playlists'), unlike HomeSection's key=None
        # sentinel - this only matters for reset()'s key.isdigit() fallback, so any stable literal
        # works; reusing self.key keeps it obviously consistent rather than a second literal.
        return self.key


_playlistsSections = {}


def playlistsSection(server):
    """The server's Playlists section - the same object each time, so the sidebar's entry, the view
    and its screens all compare equal."""
    section = _playlistsSections.get(server.uuid)
    if section is None or section.server is not server:
        section = _playlistsSections[server.uuid] = PlaylistsSection(server)
    return section


def isPlaylists(section):
    return getattr(section, 'TYPE', None) == 'playlists' and isinstance(section, PlaylistsSection)
