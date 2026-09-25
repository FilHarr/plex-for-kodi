from __future__ import absolute_import

import time

import plexnet
from kodi_six import xbmcgui
from plexnet import plexapp, plexlibrary, plexobjects

from lib import backgroundthread
from lib import util
from lib.path_mapping import pmm
from lib.util import T
from . import kodigui
from . import background


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
    def setup(self, section, callback, section_keys=None, reselect_pos_dict=None):
        self.section = section
        self.callback = callback
        self.section_keys = section_keys
        self.reselect_pos_dict = reselect_pos_dict
        return self

    def run(self):
        if self.isCanceled():
            return

        if not plexapp.SERVERMANAGER.selectedServer or not self.section.server:
            # Could happen during sign-out for instance
            return

        try:
            hubs = HubsList(self.section.server.hubs(self.section.key, count=HUB_ROW_MAX_ITEMS,
                                                                      section_ids=self.section_keys)).init()
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

        if not plexapp.SERVERMANAGER.selectedServer:
            # Could happen during sign-out for instance
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

        if not plexapp.SERVERMANAGER.selectedServer:
            # Could happen during sign-out for instance
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


class DiscoverHubsTask(backgroundthread.Task):
    """Background task to discover all available hubs across all library sections."""

    def setup(self, sections, callback):
        self.sections = sections  # List of all sections (including home_section)
        self.callback = callback
        return self

    def run(self):
        if self.isCanceled():
            return

        if not plexapp.SERVERMANAGER.selectedServer:
            return

        availableHubs = {}

        for section in self.sections:
            if self.isCanceled():
                return

            try:
                section_key = section.key
                section_type = getattr(section, 'type', 'unknown')
                section_title = getattr(section, 'title', T(32411, 'Unknown'))

                # Fetch hubs for this section
                hubs = section.server.hubs(section_key, count=HUB_PAGE_SIZE)

                for hub in hubs:
                    clean_identifier = hub.getCleanHubIdentifier(is_home=(section_key is None))

                    # Create section-specific catalog identifier
                    # Home hubs: use clean identifier (e.g., "home.continue")
                    # Library hubs: prefix with section key (e.g., "1:movie.recentlyadded")
                    if section_key is None:
                        catalog_id = clean_identifier
                    else:
                        catalog_id = '{}:{}'.format(section_key, clean_identifier)

                    # Determine native display type from hub content
                    native_display = 'poster'  # Default
                    if hub.items:
                        item_type = hub.items[0].type
                        native_display = {
                            'episode': 'ar16x9', 'clip': 'ar16x9', 'video': 'ar16x9',
                            'album': 'square', 'artist': 'square', 'photo': 'square', 'track': 'square',
                        }.get(item_type, 'poster')

                    # Resolve hub title — playlist hubs have no server-provided title
                    hub_title = hub.title
                    if not hub_title:
                        hub_title = PLAYLIST_HUB_TITLES.get(clean_identifier, clean_identifier)

                    # Store hub info - each section's hubs are stored separately
                    if catalog_id not in availableHubs:
                        availableHubs[catalog_id] = {
                            'catalog_id': str(catalog_id),
                            'identifier': str(clean_identifier),
                            'title': str(hub_title),
                            'hubIdentifier': str(hub.hubIdentifier),
                            'source_section_key': section_key,
                            'source_section_title': str(section_title) if section_title else T(32411, 'Unknown'),
                            'source_section_type': str(section_type) if section_type else 'unknown',
                            'native_display': native_display,
                            'item_count': len(hub.items) if hub.items else 0,
                        }

            except plexnet.exceptions.BadRequest:
                pass
            except Exception as e:
                pass


        if not self.isCanceled():
            self.callback(availableHubs)


class VirtualSection(object):
    locations = []
    isMapped = False
    mappedPaths = []
    mappingBroken = False

    @property
    def server(self):
        return plexapp.SERVERMANAGER.selectedServer

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
    key = 'playlists'
    type = 'playlists'
    title = T(32333, 'Playlists')

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


playlists_section = PlaylistsSection()


class ServerListItem(kodigui.ManagedListItem):
    uuid = None

    def hookSignals(self):
        self.dataSource.on('completed:reachability', self.onReachability)
        self.dataSource.on('started:reachability', self.onReachability)

    def unHookSignals(self):
        try:
            self.dataSource.off('completed:reachability', self.onReachability)
            self.dataSource.off('started:reachability', self.onReachability)
        except:
            pass

    def setRefreshing(self):
        self.safeSetProperty('status', 'refreshing.gif')

    def safeSetProperty(self, key, value):
        # For if we catch the item in the middle of being removed
        try:
            self.setProperty(key, value)
            return True
        except AttributeError:
            pass

        return False

    def safeSetLabel(self, value, func="setLabel"):
        if value is None:
            return False
        try:
            getattr(self, func)(value)
            return True
        except AttributeError:
            pass

        return False

    def safeGetDSProperty(self, prop):
        return getattr(self.dataSource, prop, None)

    def onReachability(self, **kwargs):
        plexapp.util.APP.trigger('sli:reachability:received')
        # plexnet raises this on its own threads, and onUpdate() sets list item properties and
        # labels, so it's posted to the main thread (MultiWindow.postUI()) rather than run here.
        # Live-caught 2026-09-24 (crash dump): the plex.tv resource refresh started by opening the
        # server popup checked reachability just as a server switch showed the new Home view, and
        # this updated a row of the outgoing view's server list from that thread - a null read
        # inside Kodi. Only when there's no live host (e.g. at shutdown) does it run in place.
        from . import windowutils
        host = windowutils.HOME
        if host is not None and not host._allClosed:
            host.postUI('ServerListItem.onUpdate', self.onUpdate, kwargs=kwargs)
            return
        return self.onUpdate(**kwargs)

    def onUpdate(self, **kwargs):
        if not self.listItem:  # ex. can happen on Kodi shutdown
            return

        if self.dataSource == kodigui.DUMMY_DATA_SOURCE:
            return

        # this looks a little ridiculous, but we're experiencing timing issues here
        isSupported = self.safeGetDSProperty("isSupported")
        isReachable = False
        isReachableFunc = self.safeGetDSProperty("isReachable")
        isSecure = self.safeGetDSProperty("isSecure")
        isLocal = self.safeGetDSProperty("isLocal")
        name = self.safeGetDSProperty("name")
        pendingReachabilityRequests = self.safeGetDSProperty("pendingReachabilityRequests")
        owned = not self.safeGetDSProperty("owned") and self.safeGetDSProperty("owner") or ''
        if isReachableFunc:
            isReachable = isReachableFunc()

        if not isSupported or not isReachable:
            if pendingReachabilityRequests is not None and pendingReachabilityRequests > 0:
                self.safeSetProperty('status', 'refreshing.gif')
            else:
                self.safeSetProperty('status', 'unreachable.png')
        else:
            self.safeSetProperty('status', isSecure and 'secure.png' or '')
            self.safeSetProperty('secure', isSecure and '1' or '')
            self.safeSetProperty('local', isLocal and '1' or '')

        if plexapp.SERVERMANAGER.selectedServer:
            self.safeSetProperty('current', plexapp.SERVERMANAGER.selectedServer.uuid == self.uuid and '1' or '')
        if name:
            self.safeSetLabel(name)

        if owned:
            self.safeSetLabel(owned, func="setLabel2")

    def onDestroy(self):
        self.unHookSignals()

