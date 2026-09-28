from __future__ import absolute_import

import datetime
import json
import time

import plexnet
from kodi_six import xbmc
from kodi_six import xbmcgui
from plexnet import plexapp
from six.moves import range

from lib import util
from lib.util import T
from . import busy
from . import dropdown
from . import home
from . import kodigui
from . import opener
from . import optionsdialog
from . import navintent


class _CatalogHub(object):
    """Just enough of a hub (title + hubIdentifier) for LibraryWindow.homeHubDisplayTitle() to
    re-label a Manage Hubs catalog entry, which stores those as plain fields."""
    def __init__(self, title, hub_identifier):
        self.title = title
        self.hubIdentifier = hub_identifier


class HubSlide(object):
    """One hub slide (step 11 stage C in the navigation review): group 51 from one offset to
    another over duration seconds, eased (smoothstep), timed by the clock - each step goes where
    the elapsed time says, so a late step shortens the slide instead of stretching it. The host
    steps it from the view's wait loop, on the main thread (MultiWindow.addTicker()), and lands it
    early when the next press or a swap needs it settled.

    view and list_gen are what it belongs to: the host drops it, without touching its control,
    once either has moved on. clock is time.time, or a stand-in in tests."""

    def __init__(self, control, x, start_y, end_y, duration, view, list_gen, timing, clock=time.time):
        self.control = control
        self.x = x
        self.start_y = start_y
        self.end_y = end_y
        self.duration = duration
        self.view = view
        self.list_gen = list_gen
        self.timing = timing
        self.clock = clock
        self.started = None
        self.landed = False
        self.drawn = 0
        self.firstStepAt = None
        self._y = start_y

    def start(self):
        self.started = self.clock()

    def step(self):
        """Move to where the clock says; lands at the end. True while still moving."""
        if self.landed:
            return False
        t = (self.clock() - self.started) / self.duration
        if t >= 1:
            self.land()
            return False
        eased = t * t * (3 - 2 * t)
        y = int(round(self.start_y + (self.end_y - self.start_y) * eased))
        if y != self._y:
            self.control.setPosition(self.x, y)
            self._y = y
            self.drawn += 1
            if self.firstStepAt is None:
                self.firstStepAt = self.timing.elapsedMs()
        return True

    def land(self):
        """Snap to the end, once."""
        if self.landed:
            return
        self.landed = True
        if self._y != self.end_y:
            self.control.setPosition(self.x, self.end_y)
            self._y = self.end_y
            self.drawn += 1

    def logTiming(self, outcome=None):
        """The "Slide timing" line (step 11 stage A): what ran before the rows moved, then the
        animation - moves drawn, and when the first one landed after the press."""
        util.DEBUG_LOG("Slide timing: {0}: {1} ms ({2}, animation {3}: {4} steps, first at {5}){6}",
                       self.timing.name, int(self.timing.elapsedMs()), self.timing.stepsText(),
                       int((self.clock() - self.started) * 1000) if self.started else 0, self.drawn,
                       int(self.firstStepAt) if self.firstStepAt is not None else '-',
                       ' - ' + outcome if outcome else '')


class HubsMixin(object):
    """LibraryWindow's hub engine: the Recommended view's rows, the hero, the slide, hub settings
    and list-item creation. A mixin for the same reason as GridMixin (library_grid.py)."""

    # ------------------------------------------------------------------------------------------
    # Display types, hub settings, hub visibility and ordering, and list-item creation. Ported,
    # verbatim where possible, from home.py's HomeWindow (quiet-orbiting-heron.md, Recommended-tab
    # sharing), whose Home screen this view replaced.
    # ------------------------------------------------------------------------------------------

    # Hub identifier prefixes that indicate 16x9 display format
    HUB_PREFIXES_16X9 = ('video.', 'music.videos.')

    # Hub identifiers that have mixed content (movies + episodes) - always use poster format
    HUBS_MIXED_CONTENT = {
        'continueWatching',  # Combined continue watching hub (modern Plex clients) - mixed movies/episodes
        'tv.inprogress', 'tv.ondeck', 'movie.inprogress',
    }
    # The server's old separate home.continue (episodes, 16:9) / home.ondeck (show posters) pair
    # no longer reaches here at all - plexserver.hubs() always substitutes the combined
    # continueWatching hub (removed outright 2026-09-21, along with the
    # hubs_use_new_continue_watching setting that used to choose).

    def getHubDisplayType(self, hub, identifier):
        """Determine the display type for a hub: 'poster', 'ar16x9', or 'square'.

        With dynamic hub templating, all hubs support all display types via
        conditional visibility based on the hub.display.4XX window property.
        """
        # Mixed content hubs (like Continue Watching) always use poster
        if identifier in self.HUBS_MIXED_CONTENT:
            return 'poster'

        # Check identifier prefixes first (works even if items not loaded yet)
        if identifier:
            for prefix, display_type in self.HUB_DISPLAY_DEFAULTS.items():
                if identifier.startswith(prefix):
                    return display_type

            # Check for keywords in identifier (e.g., 'recentlyAddedAlbums' contains 'album')
            identifier_lower = identifier.lower()
            for keyword in self.HUB_SQUARE_KEYWORDS:
                if keyword in identifier_lower:
                    return 'square'
            for keyword in self.HUB_16X9_KEYWORDS:
                if keyword in identifier_lower:
                    return 'ar16x9'

        # Check hub's type attribute (Plex sets this to indicate content type)
        if hub:
            hub_type = getattr(hub, 'type', None)
            if hub_type in ('episode', 'clip', 'video'):
                return 'ar16x9'
            elif hub_type in ('album', 'artist', 'photo', 'track', 'playlist'):
                return 'square'

        # Detect from hub content as fallback
        if hub and hub.items:
            item_type = getattr(hub.items[0], 'type', None)
            # 16x9 content types - episodes, clips, videos
            if item_type in ('episode', 'clip', 'video'):
                return 'ar16x9'
            # Square content types - albums, artists, photos, tracks, playlists
            elif item_type in ('album', 'artist', 'photo', 'track', 'playlist'):
                return 'square'

        # Default to poster for everything else (movies, shows, mixed content)
        return 'poster'

    # Hub identifiers that should NOT show progress (watchlist/discovery hubs)
    HUBS_NO_PROGRESS = {
        'watchlist.continueWatching', 'watchlist.coming-soon', 'watchlist.recently-added',
        'home.top_watchlisted', 'home.coming-soon', 'home.trending-friends',
        'home.trending-for-you', 'home.new-for-you',
    }
    # Same set, reused for a different reason: these are curated/algorithmic Discover-sourced
    # hubs, not library listings - live-confirmed hub.more reports True for them (Watchlist's
    # Coming Soon/Recently Added, both well under a page) even though there's nothing more the
    # server will actually return, so they get no "See more" item (_bindHubToControl()). Was
    # HUBS_NO_PAGINATION, gating the old in-row "load more" placeholder for the same reason.
    # Kept as its own separately-named constant (not just reusing HUBS_NO_PROGRESS directly at
    # each call site) since the two exclusions exist for different reasons and may not always
    # coincide, even though they currently do.
    HUBS_NO_SEE_MORE = HUBS_NO_PROGRESS

    def getHubRenderFlags(self, hub, identifier):
        """Get rendering flags for a hub based on identifier patterns and content.

        Returns dict with: with_progress, do_updates, text2lines, ar16x9, with_art, no_labels
        All hubs get sensible defaults - no fixed index mapping.
        """
        # Default flags - most hubs want these
        flags = {
            'with_progress': True,
            'do_updates': True,
            'text2lines': True,
            'ar16x9': False,
            'with_art': False,
            # Square music hubs (album/artist/track items) render bare art with no caption
            # underneath, on request (2026-09-20) - hub_itemlayout_square.xml.tpl reads this as
            # hub.nolabels.<id>. Photo/playlist square hubs keep their captions. Decided by the
            # hub's own type or its first item's, the same way display type is auto-detected
            # (TYPE_TO_DISPLAY) - identifier prefixes alone don't cover e.g. per-section
            # 'hub.music.*' hubs vs the home screen's merged 'home.music.*' ones.
            'no_labels': self._hubIsMusic(hub),
        }

        # Watchlist/discovery hubs don't show progress
        if identifier in self.HUBS_NO_PROGRESS:
            flags['with_progress'] = False

        # Mixed content hubs (continue watching, on deck, in progress) always use poster
        # Don't auto-detect from content as they contain both movies and episodes
        if identifier in self.HUBS_MIXED_CONTENT:
            return flags

        # Check if identifier matches a known display type prefix
        # This prevents content-based detection from overriding the intended display
        identifier_has_known_prefix = False
        if identifier:
            # Check 16x9 prefixes first
            for prefix in self.HUB_PREFIXES_16X9:
                if identifier.startswith(prefix):
                    flags['ar16x9'] = True
                    flags['with_art'] = True  # 16x9 hubs use art/thumb images
                    identifier_has_known_prefix = True
                    break

            # Check poster/square prefixes from HUB_DISPLAY_DEFAULTS
            # Also set ar16x9 flags if the display type is ar16x9
            if not identifier_has_known_prefix:
                for prefix, display_type in self.HUB_DISPLAY_DEFAULTS.items():
                    if identifier.startswith(prefix):
                        identifier_has_known_prefix = True
                        if display_type == 'ar16x9':
                            flags['ar16x9'] = True
                            flags['with_art'] = True
                        break

        # Only detect from hub content if identifier doesn't have a known prefix
        # This prevents "tv.recentlyadded" (poster) from being detected as 16x9 due to episode content
        if not identifier_has_known_prefix and not flags['ar16x9'] and hub and hub.items:
            item_type = getattr(hub.items[0], 'type', None)
            if item_type in ('episode', 'clip', 'video'):
                flags['ar16x9'] = True
                flags['with_art'] = True  # 16x9 hubs use art/thumb images

        return flags

    MUSIC_ITEM_TYPES = ('album', 'artist', 'track')

    @classmethod
    def _hubIsMusic(cls, hub):
        """Whether hub holds music items (see getHubRenderFlags()'s no_labels)."""
        if hub is None:
            return False
        if getattr(hub, 'type', None) in cls.MUSIC_ITEM_TYPES:
            return True
        items = getattr(hub, 'items', None)
        return bool(items) and getattr(items[0], 'type', None) in cls.MUSIC_ITEM_TYPES

    # Display type mapping for auto-detection based on item type
    TYPE_TO_DISPLAY = {
        # 16x9 wide format
        'episode': 'ar16x9',
        'clip': 'ar16x9',
        'video': 'ar16x9',
        # Square format
        'album': 'square',
        'artist': 'square',
        'photo': 'square',
        'track': 'square',
        # Poster format (default for movies, shows, seasons)
        'movie': 'poster',
        'show': 'poster',
        'season': 'poster',
    }

    # Display type defaults for known hub identifiers (by prefix)
    # This ensures correct display regardless of hub content
    HUB_DISPLAY_DEFAULTS = {
        # TV/Show hubs - always poster (shows, not episodes)
        'tv.': 'poster',
        'show.': 'poster',
        # Movie hubs - always poster
        'movie.': 'poster',
        # Music hubs - always square (various prefix patterns)
        'music.': 'square',
        'artist.': 'square',
        'album.': 'square',
        'hub.music.': 'square',
        'track.': 'square',
        # Photo hubs - square
        'photo.': 'square',
        'hub.photo.': 'square',
        # Video hubs - ar16x9
        'video.': 'ar16x9',
        'hub.video.': 'ar16x9',
        # Playlist hubs - both square (name + item count below the art). 'playlists.audio'/
        # 'playlists.video' are the Playlists library section's own two hubs; 'home.playlists' is
        # the separate "recently viewed playlists" row Plex serves directly on the home screen.
        'playlists.audio': 'square',
        'playlists.video': 'square',
        'home.playlists': 'square',
        # Watchlist/discover hubs - always poster (mixed movies + episodes, matches Pannal's original intent)
        'watchlist.': 'poster',
        # Home merged hubs
        'home.television.': 'poster',
        'home.movies.': 'poster',
        'home.music.': 'square',
        'home.photos.': 'square',
        'home.videos.': 'ar16x9',
        # Hub prefixed variants
        'hub.tv.': 'poster',
        'hub.show.': 'poster',
        'hub.movie.': 'poster',
        'hub.artist.': 'square',
        'hub.album.': 'square',
        'hub.track.': 'square',
    }

    # Identifiers that indicate square display (contains these substrings)
    HUB_SQUARE_KEYWORDS = ('album', 'artist', 'track', 'music', 'photo', 'playlist')

    # Identifiers that indicate ar16x9 display (contains these substrings)
    HUB_16X9_KEYWORDS = ('episode', 'clip', 'video')

    def loadNavSettings(self):
        """Per-section show/hide/pin/order preferences - ported from HomeWindow.loadLibrarySettings()
        (home.py) under a new name, see __init__'s own comment for why. Same setting key
        buildSectionList() used to read directly, every call, as a throwaway local - this makes it
        real state sectionMenu() can mutate and persist.
        """
        setting_key = 'home.settings.{}.{}'.format(plexapp.SERVERMANAGER.selectedServer.uuid[-8:], plexapp.ACCOUNT.ID)
        data = util.getSetting(setting_key, '')
        self.navSettings = {}
        try:
            self.navSettings = json.loads(data)
        except ValueError:
            pass
        except:
            util.ERROR()

    def saveNavSettings(self):
        if self.navSettings:
            setting_key = 'home.settings.{}.{}'.format(plexapp.SERVERMANAGER.selectedServer.uuid[-8:],
                                                        plexapp.ACCOUNT.ID)
            util.setSetting(setting_key, json.dumps(self.navSettings))

    def loadHubSettings(self):
        # NOTE: setting key is scoped by server uuid + account ID, not by window class - hub
        # visibility/order preferences are meant to be user+server-wide, shared between Home and
        # any section's Recommended tab, not per-window. Ported verbatim from HomeWindow; the key
        # itself has no "home"-specific prefix (it's 'hub.settings.*', distinct from
        # 'home.settings.*' used by loadLibrarySettings/saveLibrarySettings, which is NOT ported
        # here since it's unrelated to hub rendering).
        setting_key = 'hub.settings.{}.{}'.format(plexapp.SERVERMANAGER.selectedServer.uuid[-8:], plexapp.ACCOUNT.ID)
        data = util.getSetting(setting_key, '')
        self.hubSettings = {}
        try:
            loaded = json.loads(data)

            # Convert "__home__" key back to None (JSON doesn't support None keys)
            for key, value in loaded.items():
                if key == '_version':
                    continue  # Skip legacy version key
                if key == '__home__':
                    self.hubSettings[None] = value
                else:
                    self.hubSettings[key] = value
        except ValueError:
            pass
        except:
            util.ERROR()

        if self._migrateOldContinueWatching(self.hubSettings):
            self.saveHubSettings()

    # The server's old separate Continue Watching / On Deck home hubs, dropped outright
    # (2026-09-21) in favour of the combined continueWatching hub the modern clients show -
    # plexserver.hubs() no longer yields them, so a saved hub config still naming one would
    # leave the user with no Continue Watching row at all (a custom config only shows what it
    # lists). Was previously a per-mode choice (hubs_use_new_continue_watching), toggled by a
    # both-ways mapping in getEnabledHubsForSection()/sortHubsByUserOrder()/showHubSettingsDialog();
    # now a one-way, one-time rewrite of the saved config on load instead.
    OLD_CONTINUE_WATCHING_IDS = ('home.continue', 'home.ondeck')

    @classmethod
    def _migrateOldContinueWatching(cls, hub_settings):
        """Rewrites every section's saved hub list in place: the old home.continue/home.ondeck
        entries become one continueWatching entry at the earliest of their positions (or just
        disappear if continueWatching is already listed), orders renumbered. Every section, not
        just Home - a library's custom config can pull Home's hubs in cross-section, under the
        same catalog ids. Returns whether anything changed (the caller saves)."""
        changed = False
        for section_config in (hub_settings or {}).values():
            hubs = section_config.get('hubs') if isinstance(section_config, dict) else None
            if not hubs:
                continue
            old = [h for h in hubs if h.get('catalog_id', h.get('identifier')) in cls.OLD_CONTINUE_WATCHING_IDS]
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

    def saveHubSettings(self):
        setting_key = 'hub.settings.{}.{}'.format(plexapp.SERVERMANAGER.selectedServer.uuid[-8:],
                                                  plexapp.ACCOUNT.ID)
        # Convert None key to "__home__" for JSON storage
        to_save = {}
        for key, value in self.hubSettings.items():
            if key is None:
                to_save['__home__'] = value
            else:
                to_save[key] = value
        json_str = json.dumps(to_save)
        util.setSetting(setting_key, json_str)

    def getEnabledHubsForSection(self, section_key):
        """Get list of enabled hub catalog_ids for a section.

        Not in Stage C's originally-requested method list, but ported alongside isHubHidden()
        below since isHubHidden() calls self.getEnabledHubsForSection() directly - without this,
        isHubHidden() would raise AttributeError on every call, not just when hubSettings is
        unpopulated. Section-generic (reads only self.hubSettings/util.getSetting), same as the
        methods explicitly requested - no HomeWindow-specific coupling.
        """
        if not self.hubSettings:
            return None

        # Normalize key to string (hubSettings uses string keys)
        config_key = str(section_key) if section_key is not None else None
        section_config = self.hubSettings.get(config_key)
        if not section_config or not section_config.get('custom'):
            return None

        # No old/new Continue Watching identifier mapping any more - loadHubSettings() migrates
        # saved configs to continueWatching once, up front.
        return {h.get('catalog_id', h.get('identifier')) for h in section_config.get('hubs', [])}

    def isHubHidden(self, identifier, section_key=None):
        """Check if user has explicitly hidden this hub.

        Args:
            identifier: The clean hub identifier (e.g., 'movie.recentlyadded')
            section_key: The section key to check configuration for
        """
        # Normalize key for config lookup
        config_key = str(section_key) if section_key is not None else None
        section_config = self.hubSettings.get(config_key) if self.hubSettings else None

        if not section_config or not section_config.get('custom'):
            # No custom config - show all native hubs from Plex
            return False

        # Build catalog_id for this hub in this section
        if section_key is None:
            catalog_id = identifier
        else:
            catalog_id = '{}:{}'.format(section_key, identifier)

        enabled = self.getEnabledHubsForSection(section_key)
        if enabled is None:
            return False
        return catalog_id not in enabled

    def sortHubsByUserOrder(self, hubs, is_home=False, section_key=None):
        """Sort hubs by user-defined order, preserving server order for unordered hubs."""
        # Normalize key to string (hubSettings uses string keys)
        config_key = str(section_key) if section_key is not None else None

        # Get section config if available (config_key can be None for Home)
        section_config = None
        if self.hubSettings:
            section_config = self.hubSettings.get(config_key)

        # Build lookup for user-defined order
        user_order = {}
        if section_config and section_config.get('custom'):
            for idx, hub_config in enumerate(section_config.get('hubs', [])):
                cat_id = hub_config.get('catalog_id', hub_config.get('identifier'))
                user_order[cat_id] = hub_config.get('order', idx)

        # Pre-compute hub index lookup for O(1) access instead of O(n) per hub
        hubs_list = list(hubs)
        hub_index = {id(hub): idx for idx, hub in enumerate(hubs_list)}

        def get_order(hub):
            identifier = hub.getCleanHubIdentifier(is_home=is_home)

            # Build catalog_id
            if section_key is None:
                catalog_id = identifier
            else:
                catalog_id = '{}:{}'.format(section_key, identifier)

            # Check user-defined order
            if catalog_id in user_order:
                return (0, user_order[catalog_id])  # User-ordered hubs first

            # Fall back to server order (use pre-computed index)
            return (1, hub_index.get(id(hub), 999))

        return sorted(hubs_list, key=get_order)

    def _discoverHubsSync(self):
        """Synchronous hub discovery for the Manage Hubs dialog - ported from
        HomeWindow._discoverHubsSync() (home.py), called lazily the first time
        showHubSettingsDialog() runs and self.availableHubs is still empty. Also builds
        self.allSections (not part of HomeWindow's own version - see __init__'s comment), needed by
        _ensureCustomConfigExists()'s backfill path. HomeWindow additionally keeps an eager,
        always-on background DiscoverHubsTask that pre-populates availableHubs before the user ever
        opens Manage Hubs - not ported, see __init__'s own comment for why paying for discovery only
        when the dialog actually opens is sufficient here.
        """
        if not plexapp.SERVERMANAGER.selectedServer:
            return

        sections_to_query = [home.home_section]

        try:
            library_sections = plexapp.SERVERMANAGER.selectedServer.library.sections()
            sections_to_query.extend(library_sections)
        except:
            return

        try:
            pl = plexapp.SERVERMANAGER.selectedServer.playlists()
            if pl:
                sections_to_query.append(home.playlists_section)
        except:
            pass

        availableHubs = {}
        allSections = {}

        for section in sections_to_query:
            if section.key is not None:
                allSections[str(section.key)] = section
            try:
                section_key = section.key
                section_type = getattr(section, 'type', 'unknown')
                section_title = getattr(section, 'title', T(32411, 'Unknown'))

                hubs = section.server.hubs(section_key, count=home.HUB_PAGE_SIZE)

                for hub in hubs:
                    clean_identifier = hub.getCleanHubIdentifier(is_home=(section_key is None))

                    if section_key is None:
                        catalog_id = clean_identifier
                    else:
                        catalog_id = '{}:{}'.format(section_key, clean_identifier)

                    native_display = 'poster'
                    if hub.items:
                        item_type = hub.items[0].type
                        native_display = self.TYPE_TO_DISPLAY.get(item_type, 'poster')

                    hub_title = hub.title
                    if not hub_title:
                        hub_title = home.PLAYLIST_HUB_TITLES.get(clean_identifier, clean_identifier)

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
            except Exception:
                pass

        # A library's own hub promoted to Home by the server is catalogued as a Home hub, so
        # Manage Hubs labelled it "[Home]" like every other - which for Other Videos' in-progress
        # hub meant a second, indistinguishable "Continue Watching [Home]" next to the real
        # combined one (live-reported 2026-09-21). homeHubDisplayTitle() names the library in
        # the title when the bare title is shared by another Home entry (same rule the row
        # itself uses, against the catalog's Home entries here rather than the visible rows);
        # resolved against the allSections just built here rather than the sidebar, so a
        # library hidden from the sidebar still labels. Title only - source_section_title stays
        # "Home", it's what the dialog groups by.
        home_entries = [_CatalogHub(info['title'], info['hubIdentifier'])
                        for info in availableHubs.values() if info['source_section_key'] is None]
        ambiguous = self.ambiguousHubTitles(home_entries)
        for hub_info in availableHubs.values():
            if hub_info['source_section_key'] is None:
                hub_info['title'] = self.homeHubDisplayTitle(
                    _CatalogHub(hub_info['title'], hub_info['hubIdentifier']), ambiguous, allSections.get)

        self.availableHubs = availableHubs
        self.allSections = allSections

    def _ensureCustomConfigExists(self, section_key):
        """Ensure custom hub config exists for a section, initializing with defaults if needed.
        Returns True if config was just created, False if it already existed. Ported verbatim from
        HomeWindow._ensureCustomConfigExists() (home.py)."""
        if not self.hubSettings:
            self.hubSettings = {}

        config_key = str(section_key) if section_key is not None else None

        if config_key in self.hubSettings and self.hubSettings[config_key].get('custom'):
            return False

        if config_key not in self.hubSettings:
            self.hubSettings[config_key] = {'custom': False, 'hubs': []}

        section_config = self.hubSettings[config_key]
        section_config['custom'] = True
        section_config['hubs'] = []

        is_home = config_key is None
        cached_hubs = self.sectionHubs.get(section_key, [])

        for hub in cached_hubs:
            hub_identifier = hub.getCleanHubIdentifier(is_home=is_home)
            if is_home:
                cat_id = hub_identifier
            else:
                cat_id = '{}:{}'.format(section_key, hub_identifier)

            section_config['hubs'].append({
                'catalog_id': cat_id,
                'identifier': hub_identifier,
                'order': len(section_config['hubs'])
            })

            if cat_id not in self.availableHubs:
                source_title = T(32332, 'Home')
                source_type = 'home'
                if section_key is not None:
                    source_section = self.allSections.get(str(section_key))
                    if source_section:
                        source_title = str(source_section.title)
                        source_type = str(source_section.type)

                self.availableHubs[cat_id] = {
                    'catalog_id': str(cat_id),
                    'identifier': str(hub_identifier),
                    'title': str(hub.title) if hub.title else home.PLAYLIST_HUB_TITLES.get(hub_identifier, hub_identifier),
                    'hubIdentifier': str(hub.hubIdentifier) if hub.hubIdentifier else hub_identifier,
                    'source_section_key': section_key,
                    'source_section_title': source_title,
                    'source_section_type': source_type,
                    'native_display': self.TYPE_TO_DISPLAY.get(hub.items[0].type, 'poster') if hub.items else 'poster',
                    'item_count': len(hub.items) if hub.items else 0,
                }

        self.saveHubSettings()
        self._hubsSettingsChanged = True
        return True

    def _disableHub(self, catalog_id, section_key):
        """Disable a hub by removing it from the enabled list. Ported verbatim from
        HomeWindow._disableHub() (home.py)."""
        if not self.hubSettings:
            return

        config_key = str(section_key) if section_key is not None else None
        section_config = self.hubSettings.get(config_key)
        if not section_config or not section_config.get('custom'):
            return

        hubs = section_config.get('hubs', [])
        for hub_config in hubs[:]:
            if hub_config.get('catalog_id') == catalog_id:
                hubs.remove(hub_config)
                break

        for idx, hub_config in enumerate(hubs):
            hub_config['order'] = idx

        self.saveHubSettings()

    def _canMoveHub(self, catalog_id, section_key):
        """Check if a hub can move up or down in the order. Ported verbatim from
        HomeWindow._canMoveHub() (home.py)."""
        config_key = str(section_key) if section_key is not None else None

        if self.hubSettings:
            section_config = self.hubSettings.get(config_key)
            if section_config and section_config.get('custom'):
                hubs = section_config.get('hubs', [])
                if len(hubs) <= 1:
                    return False, False

                current_idx = None
                for idx, hub_config in enumerate(hubs):
                    if hub_config.get('catalog_id') == catalog_id:
                        current_idx = idx
                        break

                if current_idx is None:
                    return False, False

                can_move_up = current_idx > 0
                can_move_down = current_idx < len(hubs) - 1
                return can_move_up, can_move_down

        cached_hubs = self.sectionHubs.get(section_key, [])
        can_move = len(cached_hubs) > 1
        return can_move, can_move

    def _moveHubToPosition(self, catalog_id, section_key, from_visual_pos, to_visual_pos, optionsList):
        """Move a hub from one visual position to another - ported verbatim from
        HomeWindow._moveHubToPosition() (home.py)."""
        if not self.hubSettings or from_visual_pos == to_visual_pos:
            return

        config_key = str(section_key) if section_key is not None else None
        section_config = self.hubSettings.get(config_key)
        if not section_config or not section_config.get('custom'):
            return

        hubs = section_config.get('hubs', [])

        from_idx = from_visual_pos
        to_idx = to_visual_pos

        if from_idx < 0 or from_idx >= len(hubs):
            return
        if to_idx < 0 or to_idx >= len(hubs):
            return

        hub = hubs.pop(from_idx)
        hubs.insert(to_idx, hub)

        for idx, hub_config in enumerate(hubs):
            hub_config['order'] = idx

    def _restoreHubOrder(self, section_key, optionsList):
        """Restore hub order from saved settings after a cancelled move - ported verbatim from
        HomeWindow._restoreHubOrder() (home.py)."""
        self.loadHubSettings()
        if optionsList:
            self._refreshHubSettingsDialog(optionsList, section_key)

    def resetSectionHubs(self, section_key):
        """Reset hub configuration for a section to defaults - ported verbatim from
        HomeWindow.resetSectionHubs() (home.py)."""
        config_key = str(section_key) if section_key is not None else None
        if self.hubSettings and config_key in self.hubSettings:
            del self.hubSettings[config_key]
            self.saveHubSettings()

    def _buildHubSettingsOptions(self, section_key, section_title):
        """Build the list of option dicts for the hub settings dialog - ported verbatim from
        HomeWindow._buildHubSettingsOptions() (home.py)."""
        config_key = str(section_key) if section_key is not None else None
        section_config = self.hubSettings.get(config_key, {}) if self.hubSettings else {}
        has_custom_config = section_config.get('custom', False)
        configured_hubs = section_config.get('hubs', []) if has_custom_config else []

        configured_catalog_ids = {h.get('catalog_id', h.get('identifier')) for h in configured_hubs}

        hub_states = {}
        for catalog_id, hub_info in self.availableHubs.items():
            if has_custom_config:
                is_enabled = catalog_id in configured_catalog_ids
            else:
                hub_source_key = hub_info.get('source_section_key')
                if section_key is None:
                    is_enabled = (hub_source_key is None)
                else:
                    is_enabled = (str(hub_source_key) == str(section_key) if hub_source_key is not None else False)
            hub_states[catalog_id] = (is_enabled, hub_info)

        def make_option(catalog_id, hub_info, is_enabled, position=None):
            base_title = hub_info.get('title', catalog_id)
            if 'collection' in hub_info.get('identifier', ''):
                base_title = u'{} ({})'.format(base_title, T(32382, 'Collection'))
            source_label = hub_info.get('source_section_title', T(32411, 'Unknown'))
            if position is not None:
                display_title = u'{}. {} [{}]'.format(position, base_title, source_label)
            else:
                display_title = u'{} [{}]'.format(base_title, source_label)
            indicator = 'script.plex/indicators/circle-19.png' if is_enabled else ''
            return {
                'key': 'toggle_hub',
                'catalog_id': catalog_id,
                'identifier': hub_info.get('identifier', catalog_id),
                'hub_info': hub_info,
                'enabled': is_enabled,
                'display': display_title,
                'indicator': indicator,
                'has_submenu': is_enabled,
            }

        options = []
        enabled_hubs_shown = set()
        if has_custom_config and configured_hubs:
            for idx, hub_config in enumerate(configured_hubs):
                cat_id = hub_config.get('catalog_id', hub_config.get('identifier'))
                if cat_id in hub_states:
                    is_enabled, hub_info = hub_states[cat_id]
                    if is_enabled:
                        options.append(make_option(cat_id, hub_info, True, position=idx + 1))
                        enabled_hubs_shown.add(cat_id)
        else:
            ordered_catalog_ids = []
            cached_hubs = self.sectionHubs.get(section_key, [])
            is_home = section_key is None
            for hub in cached_hubs:
                identifier = hub.getCleanHubIdentifier(is_home=is_home)
                if is_home:
                    catalog_id = identifier
                else:
                    catalog_id = '{}:{}'.format(section_key, identifier)
                if catalog_id in hub_states:
                    is_enabled, hub_info = hub_states[catalog_id]
                    if is_enabled:
                        ordered_catalog_ids.append((catalog_id, hub_info))
            for idx, (catalog_id, hub_info) in enumerate(ordered_catalog_ids):
                options.append(make_option(catalog_id, hub_info, True, position=idx + 1))
                enabled_hubs_shown.add(catalog_id)

        if options:
            options.append(dropdown.SEPARATOR)

        hubs_by_source = {}
        for catalog_id, (is_enabled, hub_info) in hub_states.items():
            if catalog_id in enabled_hubs_shown:
                continue
            source = hub_info.get('source_section_title', T(32411, 'Unknown'))
            if source not in hubs_by_source:
                hubs_by_source[source] = []
            hubs_by_source[source].append((catalog_id, hub_info, is_enabled))

        def source_sort_key(x):
            if str(x) == str(section_title):
                return (0, str(x))
            if str(x) == 'Home':
                return (1, str(x))
            return (2, str(x))

        sorted_sources = sorted(hubs_by_source.keys(), key=source_sort_key)
        for source in sorted_sources:
            if options and options[-1] != dropdown.SEPARATOR:
                options.append(dropdown.SEPARATOR)
            for catalog_id, hub_info, is_enabled in sorted(hubs_by_source[source], key=lambda x: x[1].get('title', '')):
                options.append(make_option(catalog_id, hub_info, is_enabled))

        options.append(dropdown.SEPARATOR)
        options.append({'key': 'refresh_hubs', 'display': T(34093, "Refresh Hub List")})
        options.append({'key': 'reset_hubs', 'display': T(34081, "Reset to Default")})

        return options

    def showHubSettingsDialog(self, section):
        """Show dialog to manage hubs for the given section - ported from
        HomeWindow.showHubSettingsDialog() (home.py), minus its own trailing showHubs() refresh call
        (no equivalent on this window - sectionMenu()'s 'manage_hubs' caller handles the refresh
        instead, via self._hubsSettingsChanged - see that branch's own comment)."""
        self._managingHubsForSection = section.key
        self._hubsSettingsChanged = False

        if not self.availableHubs:
            with busy.BusyContext(delay=True, delay_time=0.2):
                self._discoverHubsSync()
            if not self.availableHubs:
                return

        section_key = section.key
        section_title = section.title if hasattr(section, 'title') else 'Home'
        self._managingHubsForSectionTitle = section_title

        options = self._buildHubSettingsOptions(section_key, section_title)
        if not options:
            return

        try:
            dropdown.showDropdown(
                options,
                pos=(460, 200),
                close_direction='none',
                set_dropdown_prop=False,
                with_indicator=True,
                header=T(34082, "Manage Hubs: {}").format(section_title),
                align_items="left",
                close_only_with_back=True,
                options_callback=self.onHubSettingToggle,
                suboption_callback=self._hubSubOptionCallback,
                dialog_props=getattr(self, 'carriedProps', None),
                move_mode_callback=self._onHubMoveCallback,
            )
        except Exception as e:
            util.ERROR('Hub Settings: Error showing dropdown: {}'.format(e))
            return

    def _hubSubOptionCallback(self, choice):
        """Return sub-menu options for an enabled hub, or None if no sub-menu needed. Ported
        verbatim from HomeWindow._hubSubOptionCallback() (home.py)."""
        if choice.get('key') != 'toggle_hub' or not choice.get('enabled'):
            return None

        catalog_id = choice.get('catalog_id')
        section_key = getattr(self, '_managingHubsForSection', None)

        can_move_up, can_move_down = self._canMoveHub(catalog_id, section_key)
        can_move = can_move_up or can_move_down

        options = []
        if can_move:
            options.append({'key': 'move', 'display': T(34089, 'Move')})
        options.append({'key': 'disable', 'display': T(34085, 'Disable')})
        return options

    def onHubSettingToggle(self, optionsList, mli):
        """Callback when a hub is toggled in the settings dialog - ported verbatim from
        HomeWindow.onHubSettingToggle() (home.py)."""
        choice = mli.dataSource
        if not choice:
            return

        if choice.get('key') == 'refresh_hubs':
            section_key = getattr(self, '_managingHubsForSection', self.section.key)
            section_title = getattr(self, '_managingHubsForSectionTitle', '')
            self._discoverHubsSync()
            options = self._buildHubSettingsOptions(section_key, section_title)
            return ('rebuild', options, 0)

        if choice.get('key') == 'reset_hubs':
            section_key = getattr(self, '_managingHubsForSection', self.section.key)
            section_title = getattr(self, '_managingHubsForSectionTitle', '')
            self.resetSectionHubs(section_key)
            self._hubsSettingsChanged = True
            options = self._buildHubSettingsOptions(section_key, section_title)
            return ('rebuild', options, 0)

        if choice.get('key') != 'toggle_hub':
            return

        catalog_id = choice.get('catalog_id', choice.get('identifier'))
        section_key = getattr(self, '_managingHubsForSection', self.section.key)
        is_currently_enabled = choice.get('enabled', False)

        if is_currently_enabled:
            config_created = self._ensureCustomConfigExists(section_key)
            if config_created:
                self._refreshHubSettingsDialog(optionsList, section_key)

            sub = choice.get('sub')
            if not sub:
                return None

            if sub.get('key') == 'move':
                self._movingHubCatalogId = catalog_id
                self._movingHubSectionKey = section_key
                self._movingHubOptionsList = optionsList
                return 'enter_move_mode_sub'

            elif sub.get('key') == 'disable':
                focus_pos = optionsList.getSelectedPos()
                self._disableHub(catalog_id, section_key)
                self._hubsSettingsChanged = True
                section_title = getattr(self, '_managingHubsForSectionTitle', '')
                options = self._buildHubSettingsOptions(section_key, section_title)
                return ('rebuild', options, focus_pos)

            return None
        else:
            new_enabled = True

        config_key = str(section_key) if section_key is not None else None

        if not self.hubSettings:
            self.hubSettings = {}

        need_init = config_key not in self.hubSettings or not self.hubSettings.get(config_key, {}).get('custom')

        if config_key not in self.hubSettings:
            self.hubSettings[config_key] = {'custom': False, 'hubs': []}

        section_config = self.hubSettings[config_key]

        if need_init:
            section_config['custom'] = True
            section_config['hubs'] = []
            is_home = section_key is None

            cached_hubs = self.sectionHubs.get(section_key, [])

            for hub in cached_hubs:
                hub_identifier = hub.getCleanHubIdentifier(is_home=is_home)
                if is_home:
                    cat_id = hub_identifier
                else:
                    cat_id = '{}:{}'.format(section_key, hub_identifier)

                if cat_id in self.availableHubs:
                    section_config['hubs'].append({
                        'catalog_id': cat_id,
                        'identifier': hub_identifier,
                        'order': len(section_config['hubs'])
                    })

        hub_found = False
        for hub_config in section_config['hubs']:
            config_cat_id = hub_config.get('catalog_id', hub_config.get('identifier'))
            if config_cat_id == catalog_id:
                hub_found = True
                if not new_enabled:
                    section_config['hubs'].remove(hub_config)
                break

        if new_enabled and not hub_found:
            hub_info = choice.get('hub_info', {})
            section_config['hubs'].append({
                'catalog_id': catalog_id,
                'identifier': hub_info.get('identifier', catalog_id),
                'order': len(section_config['hubs'])
            })

        self.saveHubSettings()
        self._hubsSettingsChanged = True

        focus_pos = optionsList.getSelectedPos()
        section_title = getattr(self, '_managingHubsForSectionTitle', '')
        options = self._buildHubSettingsOptions(section_key, section_title)
        return ('rebuild', options, focus_pos)

    def _onHubMoveCallback(self, action, mli, old_pos, new_pos):
        """Handle move-mode callbacks from the dropdown dialog - ported verbatim from
        HomeWindow._onHubMoveCallback() (home.py)."""
        section_key = getattr(self, '_movingHubSectionKey', None)
        catalog_id = getattr(self, '_movingHubCatalogId', None)
        optionsList = getattr(self, '_movingHubOptionsList', None)

        if action == 'move':
            if catalog_id:
                self._moveHubToPosition(catalog_id, section_key, old_pos, new_pos, optionsList)
            return
        elif action == 'confirm':
            if optionsList:
                self._refreshHubSettingsDialog(optionsList, section_key)
            self.saveHubSettings()
            self._hubsSettingsChanged = True
        elif action == 'cancel':
            if catalog_id and optionsList:
                self._restoreHubOrder(section_key, optionsList)

        self._movingHubCatalogId = None
        self._movingHubSectionKey = None
        self._movingHubOptionsList = None

    def _refreshHubSettingsDialog(self, optionsList, section_key):
        """Refresh the hub settings dropdown to reflect new order - ported verbatim from
        HomeWindow._refreshHubSettingsDialog() (home.py)."""
        config_key = str(section_key) if section_key is not None else None
        section_config = self.hubSettings.get(config_key, {}) if self.hubSettings else {}
        has_custom_config = section_config.get('custom', False)
        configured_hubs = section_config.get('hubs', []) if has_custom_config else []

        enabled_order = {}
        for idx, hub_config in enumerate(configured_hubs):
            cat_id = hub_config.get('catalog_id', hub_config.get('identifier'))
            enabled_order[cat_id] = idx + 1

        for mli in optionsList:
            ds = mli.dataSource
            if not ds or ds.get('key') != 'toggle_hub':
                continue

            catalog_id = ds.get('catalog_id', ds.get('identifier'))
            hub_info = ds.get('hub_info', {})
            hub_source_key = hub_info.get('source_section_key')

            if has_custom_config:
                is_enabled = catalog_id in enabled_order
            else:
                if section_key is None:
                    is_enabled = (hub_source_key is None)
                else:
                    is_enabled = (str(hub_source_key) == str(section_key) if hub_source_key is not None else False)

            ds['enabled'] = is_enabled
            indicator = 'script.plex/indicators/circle-19.png' if is_enabled else ''
            mli.setProperty('indicator', indicator)
            mli.setThumbnailImage(indicator)

            base_title = hub_info.get('title', catalog_id)
            source_label = hub_info.get('source_section_title', T(32411, 'Unknown'))

            if has_custom_config and is_enabled:
                position = enabled_order[catalog_id]
                display_title = u'{}. {} [{}]'.format(position, base_title, source_label)
            else:
                display_title = u'{} [{}]'.format(base_title, source_label)

            ds['display'] = display_title
            mli.setLabel(display_title)

    # Thumb dimensions for hub-tile ListItems specifically (Recommended tab / hub rows) - NOT the
    # same as the module-level THUMB_POSTER_DIM/THUMB_AR16X9_DIM/THUMB_SQUARE_DIM near the top of
    # this file (those size the library grid's own poster panel tiles). Ported verbatim from
    # HomeWindow with the same names, deliberately scoped as self.THUMB_* / class attributes so
    # they don't collide with the bare module-level names used elsewhere in this file.
    THUMB_POSTER_DIM = util.scaleResolution(244, 361)
    # 512x288 since the 16:9 hub tile grew to the episode screen's art size
    # (hub_itemlayout_ar16x9.xml.tpl) - was 352x198.
    THUMB_AR16X9_DIM = util.scaleResolution(512, 288)
    # 240 since the square hub tile grew to 240 art (hub_itemlayout_square.xml.tpl) - was 220.
    THUMB_SQUARE_DIM = util.scaleResolution(240, 240)

    def createGrandparentedListItem(self, obj, thumb_w, thumb_h, with_grandparent_title=False):
        if with_grandparent_title and obj.get('grandparentTitle') and obj.title:
            title = u'{0} - {1}'.format(obj.grandparentTitle, obj.title)
        else:
            title = obj.get('grandparentTitle') or obj.get('parentTitle') or obj.title or ''
        mli = kodigui.ManagedListItem(title, thumbnailImage=obj.defaultThumb.asTranscodedImageURL(thumb_w, thumb_h), data_source=obj)
        return mli

    def createParentedListItem(self, obj, thumb_w, thumb_h, with_parent_title=False):
        if with_parent_title and obj.parentTitle and obj.title:
            title = u'{0} - {1}'.format(obj.parentTitle, obj.title)
        else:
            title = obj.parentTitle or obj.title or ''

        mli = kodigui.ManagedListItem(title, thumbnailImage=obj.defaultThumb.asTranscodedImageURL(thumb_w, thumb_h), data_source=obj)

        return mli

    def createSimpleListItem(self, obj, thumb_w, thumb_h):
        mli = kodigui.ManagedListItem(obj.title or '', thumbnailImage=obj.defaultThumb.asTranscodedImageURL(thumb_w, thumb_h), data_source=obj)
        return mli

    def createEpisodeListItem(self, obj, wide=False):
        mli = self.createGrandparentedListItem(obj, *(self.THUMB_AR16X9_DIM if wide else self.THUMB_POSTER_DIM))
        if obj.index:
            subtitle = u'{0} • {1}'.format(T(32310, 'S').format(obj.parentIndex), T(32311, 'E').format(obj.index))
        else:
            subtitle = obj.originallyAvailableAt.asDatetime('%m/%d/%y')

        if wide:
            mli.setLabel2(u'{0} - {1}'.format(util.shortenText(obj.title, 35), subtitle))
        else:
            mli.setLabel2(subtitle)

        mli.setProperty('thumb.fallback', 'script.plex/thumb_fallbacks/show.png')
        # Top-right "E3" badge on the 16:9 hub tile (hub_itemlayout_ar16x9.xml.tpl) - same
        # property/format EpisodesWindow.createListItem() sets for the episode screen's own row.
        mli.setProperty('episode.number', obj.index and T(32311, 'E').format(obj.index) or '')
        if not obj.isWatched:
            mli.setProperty('unwatched', '1')
        mli.setBoolProperty('watched', obj.isFullyWatched)
        return mli

    def createSeasonListItem(self, obj, wide=False):
        mli = self.createParentedListItem(obj, *self.THUMB_POSTER_DIM)
        # mli.setLabel2('Season {0}'.format(obj.index))
        mli.setProperty('thumb.fallback', 'script.plex/thumb_fallbacks/show.png')
        mli.setLabel2(obj.title)

        if not obj.isWatched:
            mli.setProperty('unwatched.count', str(obj.unViewedLeafCount))
            mli.setBoolProperty('unwatched.count.large', obj.unViewedLeafCount > 999)
        mli.setBoolProperty('watched', obj.isFullyWatched)
        return mli

    def createMovieListItem(self, obj, wide=False):
        if wide:
            thumb = obj.defaultArt.asTranscodedImageURL(*self.THUMB_AR16X9_DIM)
        else:
            thumb = obj.defaultThumb.asTranscodedImageURL(*self.THUMB_POSTER_DIM)
        mli = kodigui.ManagedListItem(obj.defaultTitle, obj.year, thumbnailImage=thumb, data_source=obj)
        mli.setProperty('thumb.fallback', 'script.plex/thumb_fallbacks/movie.png')
        if not obj.isWatched:
            mli.setProperty('unwatched', '1')
        mli.setBoolProperty('watched', obj.isFullyWatched)
        return mli

    def createShowListItem(self, obj, wide=False):
        mli = self.createSimpleListItem(obj, *self.THUMB_POSTER_DIM)
        mli.setProperty('thumb.fallback', 'script.plex/thumb_fallbacks/show.png')
        if not obj.isWatched:
            mli.setProperty('unwatched.count', str(obj.unViewedLeafCount))
            mli.setBoolProperty('unwatched.count.large', obj.unViewedLeafCount > 999)
        mli.setBoolProperty('watched', obj.isFullyWatched)
        return mli

    def createAlbumListItem(self, obj, wide=False):
        mli = self.createParentedListItem(obj, *self.THUMB_SQUARE_DIM)
        mli.setLabel2(obj.title)
        mli.setProperty('thumb.fallback', 'script.plex/thumb_fallbacks/music.png')
        return mli

    def createTrackListItem(self, obj, wide=False):
        # Hub tiles only (CREATE_LI_MAP/createListItem()) - the library grid and list views build
        # their own items in _chunkCallback() instead, which is where the track-row properties
        # script-plex-listview-tracks.xml.tpl reads are set.
        mli = self.createGrandparentedListItem(obj, *self.THUMB_SQUARE_DIM)
        mli.setLabel2(obj.title)
        mli.setProperty('thumb.fallback', 'script.plex/thumb_fallbacks/music.png')
        return mli

    def createPhotoListItem(self, obj, wide=False):
        mli = self.createSimpleListItem(obj, *self.THUMB_SQUARE_DIM)
        if obj.type == 'photo':
            mli.setLabel2(obj.originallyAvailableAt.asDatetime('%d %B %Y'))
            # Real photos vary wildly in aspect ratio and shouldn't be cropped like posters/art -
            # the template shows the whole image letterboxed instead when this is set (matches Plex's
            # own photo hub behavior). Folders (photodirectory) keep the normal cropped-fill look
            # since their thumb is a composite grid, not a single photo.
            mli.setProperty('is.photo', '1')
        mli.setProperty('thumb.fallback', 'script.plex/thumb_fallbacks/photo.png')
        return mli

    def createClipListItem(self, obj, wide=False):
        mli = self.createGrandparentedListItem(obj, *self.THUMB_AR16X9_DIM, with_grandparent_title=True)
        mli.setProperty('thumb.fallback', 'script.plex/thumb_fallbacks/movie16x9.png')
        return mli

    def createArtistListItem(self, obj, wide=False):
        mli = self.createSimpleListItem(obj, *self.THUMB_SQUARE_DIM)
        mli.setProperty('thumb.fallback', 'script.plex/thumb_fallbacks/music.png')
        return mli

    def createPlaylistListItem(self, obj, wide=False):
        w, h = self.THUMB_SQUARE_DIM
        # 'thumb' matches what the playlist detail screen shows (playlist.py's playlist.thumb
        # property uses composite.asTranscodedImageURL() with no media= param, i.e. PMS's default
        # composite rendition) - was 'art' for video playlists back when this tile was ar16x9 and
        # a backdrop-style image suited the wide shape; square tiles should match instead.
        thumb = obj.buildComposite(width=w, height=h, media='thumb')

        # Second line is the total runtime (on request, 2026-09-20 - was the item count; the
        # hero's own line still carries both), in the hero's own hours/minutes format; '' for an
        # empty playlist, which leaves the tile with just its title.
        mli = kodigui.ManagedListItem(
            util.colorizeEmoji(obj.title) or '',
            util.durationToHoursMinutes(obj.get('duration') and obj.duration.asInt()),
            # thumbnailImage=obj.composite.asTranscodedImageURL(*self.THUMB_DIMS[obj.playlistType]['item.thumb']),
            thumbnailImage=thumb,
            data_source=obj
        )
        mli.setProperty('thumb.fallback', 'script.plex/thumb_fallbacks/{0}.png'.format(obj.playlistType == 'audio' and 'music' or 'movie'))
        return mli

    def createCollectionListItem(self, obj, wide=False):
        w, h = self.THUMB_POSTER_DIM
        # a collection often has no poster of its own; the library grid falls back to the
        # composite of its members, so match that here
        if obj.defaultThumb:
            thumb = obj.defaultThumb.asTranscodedImageURL(w, h)
        else:
            thumb = obj.server.getImageTranscodeURL(obj.artCompositeURL(w * 2, h * 2), w, h)

        mli = kodigui.ManagedListItem(obj.title or '', thumbnailImage=thumb, data_source=obj)
        mli.setProperty('thumb.fallback', 'script.plex/thumb_fallbacks/movie.png')
        return mli

    def unhandledHub(self, self2, obj, wide=False):
        util.DEBUG_LOG('Unhandled Hub item: {0}', obj.type)

    CREATE_LI_MAP = {
        'episode': createEpisodeListItem,
        'season': createSeasonListItem,
        'movie': createMovieListItem,
        'show': createShowListItem,
        'album': createAlbumListItem,
        'track': createTrackListItem,
        'photo': createPhotoListItem,
        'photodirectory': createPhotoListItem,
        'clip': createClipListItem,
        'artist': createArtistListItem,
        'playlist': createPlaylistListItem,
        'collection': createCollectionListItem
    }

    def createListItem(self, obj, wide=False):
        return self.CREATE_LI_MAP.get(obj.type, self.unhandledHub)(self, obj, wide)

    # ------------------------------------------------------------------------------------------
    # Stage D2 (quiet-orbiting-heron.md): the rotation-ring/anchor positioning engine, ported
    # from HomeWindow's own _bindAllHubSlots()/_startHubSlide()/_finishHubSlide()/
    # _settleHubSlide()/_roleLocalY()/etc. (home.py). Replaces D1's flat, non-rotating static
    # bind (index i always held hub i, rendered at raw template fallback coordinates) with the
    # real anchor-centered model: self.focusedHubIndex (which hub is logically focused)
    # determines which of the 5 physical controls (HUB_ROTATION_RING) plays which ROLE
    # (anchor/peek-above/peek-below/two-above/two-below), rotating as focus moves rather than
    # rebinding content on every move - see HUB_ROTATION_RING's own comment below.
    #
    # Deliberately NOT a port of showHub()/_showHub() (hero-art/spoiler/cache-clearing logic far
    # beyond what's needed here - see _bindHubToControl() below), _captureHubPosition()/
    # self._hubReselectPositions (reselect-position memory - a hub rebound to a different
    # physical control resets to its first item, not the scroll position it last had), or
    # _prepareHubSlideHero()/_setNoHeroArt()/updateHeroFrom() (hero-art
    # background sync - LibraryWindow has no hero-art concept yet at all). See this plan file's
    # "Next step: Recommended-tab sharing" section (Stage D2) for the full scoping rationale.
    # ------------------------------------------------------------------------------------------

    # Permanent geometric order of the 4 physical controls (see
    # docs/notes/home-hub-fixed-focus-position-status.md for the full history behind this design,
    # ported from HomeWindow.HUB_ROTATION_RING). Which ROLE (-1 above / 0 anchor / +1 peek-below /
    # +2 below) a given control id currently plays rotates as focus moves - tracked by
    # self._anchorRingPos (index into this tuple) - rather than roles being permanently glued to
    # one control id with content rebound to match every move. A control that already has
    # correct, already-rendered content for a hub keeps it and just repositions; only the one
    # control "wrapping around" per move (see _startHubSlide()) ever needs a fresh content bind.
    #
    # Four, not HomeWindow's five (2026-09-24): with the hero overlay always shown, only the
    # anchor and a partial peek-below are ever on screen at rest - role -1's bottom edge sits at
    # ANCHOR_ABS_Y - ROW_GAP (461), above grouplist 50's clip line (518), and role +2 starts at
    # y >= 1188 even under the shortest rows, below the screen. A slide shows one more: going
    # down, +2 slides up into peek-below; going up, -1 slides down into the anchor. So -1..+2
    # covers both directions, and the wrapping control always moves between the two roles that
    # are never on screen (-1 -> +2 going down, +2 -> -1 going up). The old -2 role was never
    # visible at all; dropping it takes one 70KB list control out of the window XML.
    HUB_ROTATION_RING = (401, 400, 402, 403)
    # The ring's lowest role; the others follow in ring order up to HUB_MAX_ROLE.
    HUB_MIN_ROLE = -1
    HUB_MAX_ROLE = HUB_MIN_ROLE + len(HUB_ROTATION_RING) - 1
    # Each ring control's own wrapper control id (script-plex-recommended.xml.tpl groups
    # 500-503) - fixed, structural, so "moving" a control between roles means repositioning
    # *its* wrapper, not re-parenting the list control itself. Ported verbatim from
    # HomeWindow.HUB_WRAPPER_FOR_CONTROL.
    HUB_WRAPPER_FOR_CONTROL = {400: 500, 401: 501, 402: 502, 403: 503}

    # A row's own real rendered height (template-declared, pre-vscale units), keyed by the same
    # (display_type, text2lines) values getHubDisplayType()/getHubRenderFlags() already report.
    # poster: hub_itemlayout_poster.xml.tpl's item group starts at posy=52, the card group 3
    # below that, then 360 of art, plus the same 31px bottom margin every other type uses:
    # 52+3+360+31 = 446. Was 464 - a leftover from when the poster grew to 240x360 and this was
    # only partly recomputed, leaving poster rows 18px more slack under the art than square/16:9
    # rows; evened out on request (2026-09-20). Keep this in sync with that file's own
    # posy/height if either changes again, or rows will start overlapping their neighbours
    # (_roleLocalY() stacks rows using this value, not the template's own real rendered size).
    # square: hub_itemlayout_square.xml.tpl's item group starts at posy=52 (poster's own offset,
    # all three types share it now), the card group 3 below that, then 240 art with the caption
    # at 250 (+35) or, with text2lines, a second at 277 (+35), plus the same ~31px bottom margin:
    # 52+3+285+31 = 371 / 52+3+312+31 = 398. ROW_CONTENT_HEIGHT_SQUARE_NO_LABELS: music hubs hide
    # both captions (getHubRenderFlags()'s no_labels), so the row ends at the art itself:
    # 52+3+240+31 = 326.
    # ar16x9: hub_itemlayout_ar16x9.xml.tpl has no captions at all any more (the episode-screen
    # card), so text2lines makes no difference: 52+3+288+31 = 374 either way.
    ROW_CONTENT_HEIGHT = {
        ('poster', False): 446, ('poster', True): 446,
        ('square', False): 371, ('square', True): 398,
        ('ar16x9', False): 374, ('ar16x9', True): 374,
    }
    ROW_CONTENT_HEIGHT_SQUARE_NO_LABELS = 326
    # Fixed gap between any two adjacent rows, either direction - used by _roleLocalY()'s
    # stacking recurrence. Ported verbatim from HomeWindow.ROW_GAP.
    ROW_GAP = 25
    # The anchor's own absolute resting position (script-plex-recommended.xml.tpl's group 51,
    # local y-offset GROUP51_BASELINE_OFFSET below, sitting inside grouplist 50 at its fixed
    # posy=518 - 518 + (-32) = 486). Ported from HomeWindow.ANCHOR_ABS_Y; used by
    # _setRoleGeometry() to size peek-below's clip height to reach exactly to the screen bottom.
    # Was 424, then 516 (+92, dropping the focused row on request), now 486 (-30, raising the
    # whole stack on request, 2026-09-20) - each time in lockstep with grouplist 50's own posy in
    # the template (the clip line) so GROUP51_BASELINE_OFFSET stays put; every other row's
    # position is computed relative to the anchor via _roleLocalY(), so those two moving
    # together is sufficient to shift the whole rotation-ring stack as one unit.
    ANCHOR_ABS_Y = 486
    # The local y-offset group 51 must always be explicitly set to via setPosition() to sit at
    # its correct resting position - group 51 has no correct position at all until Python sets
    # it (see that control's own comment in the template for why grouplist 50's auto-stacking
    # can't be relied on for this). Set to this for the first row on every fresh 'recommended'
    # entry, in onFirstInit(); _group51Y() adds the stack offset for any other row.
    # -32, not the 381 it once was: the hero overlay used to be conditional, with grouplist 50
    # shifting down 413px (its old Conditional animation) whenever it showed and this offset
    # counter-shifting by the same amount to keep the anchor at ANCHOR_ABS_Y. The overlay is
    # unconditional now, so both halves are baked in: 50 sits at 518 permanently and this is the
    # old 381 - 413. Negative is fine - it was already this value live whenever hero art showed.
    GROUP51_BASELINE_OFFSET = -32
    # The group every row wrapper sits in (script-plex-recommended.xml.tpl). Since step 11 stage B
    # in the navigation review it's what a slide moves: each wrapper has a fixed place in one tall
    # stack (_stackY()), and this group's offset (_group51Y()) puts the focused row on the anchor
    # line. One setPosition() per slide step instead of one per row, and the rows can't land on
    # different frames.
    GROUP51_ID = 51
    # How long a hub slide takes (HubSlide, timed by the clock). Ported from HomeWindow, which
    # took 12 fixed steps of HUB_SLIDE_TIME / 12 and so stretched whenever a step ran late.
    HUB_SLIDE_TIME = 0.25
    # Hero art/info overlay (plan item 11) - ported from HomeWindow's own constants (home.py).
    # The overlay is unconditional - shown for every focused hub item, whatever its type (the old
    # HERO_ART_TYPES / _typeHasHeroArt() movie-and-TV-only gate is gone, and with it the
    # two-position row layout it drove - see GROUP51_BASELINE_OFFSET above) - so no_hero_art is
    # only ever True while nothing is bound at all: a fresh 'recommended' entry before its hubs
    # land (onFirstInit(), hiding the previous section's stale overlay) and a section with no
    # hubs (_bindAllHubSlots()'s empty branch). Pure visibility now, no layout effect.
    # CLEAR_LOGO_DIM: the clearlogo image's own render bounds. CLEAR_LOGO_DIM_EPISODE: smaller
    # variant used when the focused hub item is an episode or a rolled-up season (setHeroInfo()'s
    # hero.small_logo), leaving room for the second text line underneath within the same budget (script-plex-recommended.xml.tpl's own
    # comment on the hero-info group has the exact numbers) - the show's clearlogo itself (same
    # source image either way, see setHeroInfo()) is just requested/rendered smaller.
    # Item types that get the hero *info* overlay (title/summary etc., left) but not the hero
    # *art* box (top-right, default_background.xml.tpl) - setHeroInfo() writes hero.no_art for
    # these and the art box's own <visible> reads it. Playlists on request (2026-09-20): their
    # only art is the composite grid, which isn't a background image.
    HERO_NO_ART_TYPES = ('playlist',)
    CLEAR_LOGO_DIM = util.scaleResolution(722, 162)
    CLEAR_LOGO_DIM_EPISODE = util.scaleResolution(660, 98)

    def _hubRowHeight(self, hub):
        """A row's own real rendered height (pre-vscale template units) for whichever hub it's
        currently showing - used by _roleLocalY()'s stacking recurrence. hub=None (nothing bound
        at some intermediate offset, e.g. the empty-hubs case) falls back to the tallest real
        case (poster). Ported from HomeWindow._hubRowHeight() (home.py) - is_home adapted per
        this file's own convention (self.section.key is None)."""
        if hub is None:
            return self.ROW_CONTENT_HEIGHT[('poster', False)]
        is_home = self.section.key is None
        identifier = hub.getCleanHubIdentifier(is_home=is_home)
        display_type = self.getHubDisplayType(hub, identifier)
        flags = self.getHubRenderFlags(hub, identifier)
        if display_type == 'square' and flags['no_labels']:
            return self.ROW_CONTENT_HEIGHT_SQUARE_NO_LABELS
        return self.ROW_CONTENT_HEIGHT.get(
            (display_type, flags['text2lines']), self.ROW_CONTENT_HEIGHT[('poster', False)]
        )

    def _stackY(self, hub_index):
        """Where hub_index's row sits in the one tall stack of rows, from the first hub's top
        (pre-vscale template units): every row above it, each with a ROW_GAP after it. An index
        above the first hub or past the last uses _hubRowHeight(None)'s fallback, as
        _roleLocalY() does - which is the difference of two of these."""
        def step(index):
            hub = self.visibleHubs[index] if 0 <= index < len(self.visibleHubs) else None
            return self._hubRowHeight(hub) + self.ROW_GAP

        if hub_index >= 0:
            return sum(step(k) for k in range(hub_index))
        return -sum(step(k) for k in range(hub_index, 0))

    def _group51Y(self, focused_index):
        """Group 51's y (pixels) that puts focused_index's row on the anchor line. Each part is
        scaled on its own, so the anchor lands exactly on the baseline whatever the rounding."""
        return (util.vscale(self.GROUP51_BASELINE_OFFSET, r=0)
                - util.vscale(self._stackY(focused_index), r=0))

    def _placeStack(self, focused_index):
        """Move group 51 so focused_index's row is on the anchor line, at rest."""
        group = self.getControl(self.GROUP51_ID)
        group.setPosition(group.getPosition()[0], self._group51Y(focused_index))

    def _roleLocalY(self, role_offset, focused_index):
        """The local y-offset (within group 51's frame, pre-vscale template units) whichever
        control currently plays role_offset (0 = anchor, negative = above it, positive = below
        it) must sit at. Ported verbatim from HomeWindow._roleLocalY() (home.py) - see that
        method's own docstring for the full stacking-recurrence reasoning."""
        if role_offset == 0:
            return 0
        step = 1 if role_offset > 0 else -1
        y = 0
        for k in range(0, role_offset, step):
            hub_index = focused_index + (k if step > 0 else k + step)
            hub = self.visibleHubs[hub_index] if 0 <= hub_index < len(self.visibleHubs) else None
            y += step * (self._hubRowHeight(hub) + self.ROW_GAP)
        return y

    def _setRoleGeometry(self, wrapper, role_offset, focused_index):
        """Position (and, for peek-below, size) wrapper for role_offset - shared by the initial
        bind (_recommendedHubsCallback()) and _startHubSlide(). The wrapper goes to its hub's place
        in the stack (_stackY()); group 51's offset (_placeStack()) does the rest. Ported from
        HomeWindow._setRoleGeometry() (home.py), which placed wrappers relative to the anchor."""
        y = self._roleLocalY(role_offset, focused_index)
        wrapper.setPosition(0, util.vscale(self._stackY(focused_index + role_offset), r=0))
        if role_offset == 1:
            wrapper.setHeight(util.vscale(self.height - self.ANCHOR_ABS_Y - y, r=0))
        return y

    # ------------------------------------------------------------------------------------------
    # Plan item 11 (quiet-orbiting-heron.md): hero art/info overlay (title/clearlogo/meta-row/
    # summary for the focused hub item), ported from HomeWindow's own
    # updateHeroFrom()/setHeroInfo()/_setNoHeroArt() (home.py). Sequenced
    # after item 10 (hub interactivity) deliberately - hero art has to update as the focused
    # *item* changes, not just the focused hub, which needs item 10's horizontal-move handling to
    # exist first. The background art box itself (default_background.xml.tpl) is shared
    # infrastructure every window already includes via default.xml.tpl - only the text overlay
    # (title/logo/summary) needed porting into script-plex-recommended.xml.tpl; nothing here
    # needed template changes beyond that one block.
    # ------------------------------------------------------------------------------------------

    def updateHeroFrom(self, ds):
        """Like updateBackgroundFrom, but also drives the hero info overlay (clearlogo/title, meta
        row, summary) from the same item, and clears no_hero_art - the overlay shows for every
        bound item, whatever its type. Ported from HomeWindow.updateHeroFrom() (home.py) - see that
        method's own docstring for why this wraps updateBackgroundFrom rather than folding into
        it.

        no_hero_art is cleared last, once everything is written: on a fresh view (hidden by
        _hideStaleHero()) the properties underneath still hold the last visit's values, and
        clearing it first showed them while setHeroInfo() worked through its writes -
        live-caught 2026-09-24 as the previous item's time-left pill (remainingTime, written
        last) flickering on section changes on the AM6B, where each write is slow enough for
        Kodi to render frames in between."""
        result = self.updateBackgroundFrom(ds)
        self.setHeroInfo(ds)
        self._setNoHeroArt(False)
        return result

    def setHeroInfo(self, ds):
        """Populates the Window properties script-plex-recommended.xml.tpl's own hero-overlay
        block reads. Ported verbatim from HomeWindow.setHeroInfo() (home.py) - see that method's
        own docstring for why every field is read defensively (hub items aren't always Video
        subclasses).

        `ds is None`, not `not ds`: a freshly-listed Playlist (home.playlists hub) is falsy -
        BasePlaylist.__len__() returns len(self._items), empty until the playlist is actually
        opened - so a truthiness check silently skipped every field write for playlist items,
        leaving the previous row's film title/summary in the overlay (live-reported 2026-09-20).
        Same trap showPanelClicked() documents."""
        if ds is None:
            return

        ds_type = getattr(ds, 'type', '') or ''
        title = getattr(ds, 'title', '') or ''
        # Two-line treatment (small clearlogo with a second text line under it, or the big
        # fallback heading alone): episodes, and the rolled-up season items Plex puts in mixed
        # recently-added hubs when several episodes of one season land together (on request,
        # 2026-09-20). For a season the heading/fallback is the *show's* name (ds.title is just
        # "Season 11") and the second line is the season name, mirroring episode-title-under-
        # show-logo. hero.subtitle carries that second line for both; hero.small_logo gates the
        # template's small-logo/second-line variant.
        small_logo = ds_type in ('episode', 'season')
        subtitle = ''
        if ds_type == 'season':
            subtitle = title
            title = getattr(ds, 'parentTitle', '') or title
        elif ds_type == 'episode':
            subtitle = title
        elif ds_type == 'playlist':
            # Playlists (on request, 2026-09-20): the template renders the heading in the episode
            # screen's no-logo title style and this line where the episode title would go -
            # "<n> items" + bullet + total runtime (util.durationToHoursMinutes(): hours and
            # minutes even past a day, All Music is 146h - not durationToShortText()'s day
            # rollover, but its no-space style so it reads like the other rows' durations).
            parts = [T(35055, '{0} items').format(getattr(ds, 'leafCount', None) and ds.leafCount.asInt() or 0)]
            runtime = util.durationToHoursMinutes(getattr(ds, 'duration', None) and ds.duration.asInt())
            if runtime:
                parts.append(runtime)
            subtitle = u' \u2022 '.join(parts)
        self.setProperty('title', util.colorizeEmoji(title))
        self.setProperty('hero.subtitle', util.colorizeEmoji(subtitle))
        self.setProperty('hero.type', ds_type)
        self.setBoolProperty('hero.small_logo', small_logo)
        self.setBoolProperty('hero.no_art', ds_type in self.HERO_NO_ART_TYPES)
        logo_dim = self.CLEAR_LOGO_DIM_EPISODE if small_logo else self.CLEAR_LOGO_DIM
        self.setProperty('clear.logo', util.clearLogoFrom(ds, *logo_dim))

        episode_code = ''
        if ds_type == 'episode':
            season_num = getattr(ds, 'parentIndex', None)
            episode_num = getattr(ds, 'index', None)
            if season_num is not None and episode_num is not None:
                episode_code = u'S{0} E{1} • '.format(season_num.asInt(), episode_num.asInt())
        self.setProperty('episode.code', episode_code)

        duration = getattr(ds, 'duration', None)
        # Not for playlists - their runtime is already in hero.subtitle above, and nothing else
        # of theirs belongs on the meta row.
        self.setProperty('duration', ds_type != 'playlist' and duration and util.durationToShortText(duration.asInt(), noSpaces=True) or '')

        summary = getattr(ds, 'summary', None)
        # Capped (util.SUMMARY_BOX_MAX_CHARS) - live-reported lag moving along the Recently
        # Played Music row (2026-09-20) that the hero-sync timing showed wasn't Python at all;
        # see that constant's own comment.
        self.setProperty('summary', util.summaryForBox(summary))

        date_text = ''
        if ds_type == 'episode':
            air_date = getattr(ds, 'originallyAvailableAt', None)
            if air_date:
                try:
                    # Day without zero-padding ("1 Sep, 2026", not "01 Sep, 2026") - matches
                    # EpisodesWindow.setItemInfo()'s own copy of this format (episodes.py), which
                    # this was itself the reference for. strftime always zero-pads %d, so the day
                    # is pulled off the parsed datetime directly instead.
                    parsed = datetime.datetime.strptime(str(air_date), '%Y-%m-%d')
                    date_text = u'{0} {1}'.format(parsed.day, parsed.strftime('%b, %Y'))
                except Exception:
                    util.DEBUG_LOG('setHeroInfo: air date parse failed for {}', ds)
        elif ds_type != 'season':
            # No year for seasons (on request) - the server's own value is inconsistent for them
            # anyway (some carry `year`, others only the show's `parentYear`).
            year = getattr(ds, 'year', None)
            date_text = year and str(year) or ''
        self.setProperty('date', date_text)

        content_rating = getattr(ds, 'contentRating', None)
        self.setProperty('content.rating', content_rating and str(content_rating).split('/', 1)[-1] or '')

        # No genres: the hero's meta row leaves them out, and nothing read the 'info' property
        # this used to fill. Filling it cost a server round trip on the main thread on every hub
        # move: genres() reloads a hub movie, and an episode's genres property fetches its show
        # (20-50 ms each on the AM6B).
        # The rest of the shared meta row (CommonMixin.META_ROW_PROPERTIES) this hero has no
        # value for.
        self.blankMetaRow('genres.short', 'unavailable')

        self.setProperty('studios', getattr(ds, 'studio', None) or '')

        view_offset = getattr(ds, 'viewOffset', None)
        remaining = ''
        if view_offset is not None:
            try:
                if view_offset.asInt():
                    remaining = T(33615, "{time} left").format(time=ds.remainingTimeString)
            except Exception:
                util.DEBUG_LOG('setHeroInfo: remainingTime failed for {}', ds)
        self.setProperty('remainingTime', remaining)

    def _setNoHeroArt(self, no_hero_art):
        """Single choke point for every no_hero_art write - the "nothing bound yet" hide for the
        hero overlay and art box (see the constants block's own comment above). Pure property
        write: this used to also reposition group 51 between two rest offsets in lockstep with
        the template's own Conditional clip-shift animation; both are gone now that the overlay
        is unconditional (GROUP51_BASELINE_OFFSET's own comment)."""
        self.setBoolProperty('no_hero_art', no_hero_art)

    def _previewSelectedItem(self, hub):
        """Best-effort guess at which item hub will actually end up focused on, for previewing the
        hero block (_prepareHubSlideHero()/_bindAllHubSlots()) before the real reselect has
        happened - the physical control this hub is about to land in may still hold different
        content at this point, so this works directly off hub.items rather than a live control.
        Ported from HomeWindow._previewSelectedItem() (home.py) - now that plan item 10 Group A
        actually ported reselect-position memory (self._hubReselectPositions), this is no longer
        the no-op-to-items[0] stand-in _prepareHubSlideHero()'s docstring used to describe; mirrors
        _bindHubToControl()'s own reselect resolution (ratingKey first, then position), reading
        the same self._hubReselectPositions entry that method will use moments later. Falls back
        to the hub's first item when there's no remembered position (never-visited hub) or it
        can't be resolved (the hub's content shrank).

        Every remembered position is within hub.items by construction now: a row holds at most
        home.HUB_ROW_MAX_ITEMS, all fetched up front (SectionHubsTask), so the old reach-extension
        step (_ensureHubReselectReach()/_extendHubToPosition(), which grew a first page to cover a
        position reached by in-row pagination last visit) is gone along with that pagination."""
        if not hub.items:
            return None
        is_home = self.section.key is None
        identifier = hub.getCleanHubIdentifier(is_home=is_home)
        reselect = self._hubReselectPositions.get(identifier)
        if reselect:
            rk, pos = reselect
            if rk is not None:
                for item in hub.items:
                    if item.ratingKey and str(item.ratingKey) == rk:
                        return item
            if pos is not None and 0 <= pos < len(hub.items):
                return hub.items[pos]
        return hub.items[0]

    def _resetHubsToTop(self):
        """The Home rule's in-place half (onReInit()'s go_root branch, when Home is already the
        view on screen): land on the first hub row, item 0, as if Home had just been opened -
        without rebuilding the window. Forgets every row's remembered position, rebinds the ring
        from hub 0 on item 0 (which also puts the hero on hub 0's first item), and focuses the
        anchor row. Returns the control id it focused, for the host's routeFocus() go_root wait - the sidebar
        when there are no hubs, the same exception a section with no content gets."""
        self._settleHubSlide()
        self._hubReselectPositions = {}
        if not self.visibleHubs or not self.hubControls:
            self.setFocusId(self.SECTION_LIST_ID)
            return self.SECTION_LIST_ID

        self.focusedHubIndex = 0
        self._anchorRingPos = self.HUB_ROTATION_RING.index(self.HUB_CONTROL_ID)
        # _bindHubToControl() selects item 0 in every row it binds, now that nothing is remembered.
        self._bindAllHubSlots()

        target = self._anchorControlId()
        # Pre-seeded for the same reason onFirstInit() does it: the programmatic focus below must
        # not look like a native arrival from outside the hub range to hubFocus().
        self.lastFocusID = target
        self.setFocusId(target)
        return target

    def _prepareHubSlideHero(self):
        """Sync the hero art/info overlay to the hub about to become the anchor
        (self.visibleHubs[self.focusedHubIndex] - the caller already advanced focusedHubIndex to
        it), immediately, before the slide's own row movement starts - see
        HomeWindow._prepareHubSlideHero()'s own docstring (home.py) for why (both directions need
        to update at the same moment the scroll begins, not just the losing-hero-art one).

        Uses _previewSelectedItem(), not new_hub.items[0] - live-confirmed regression without it:
        this hub's remembered scroll position (self._hubReselectPositions) is very often not item
        0, and checkHubItem() won't correct this preview to the real selected item until the slide
        finishes - using items[0] unconditionally showed the wrong item's title/summary/art for
        that whole window (and permanently, if the user never nudges left/right afterward) on
        every move into a hub scrolled past its first item."""
        new_hub = self.visibleHubs[self.focusedHubIndex]
        new_ds = self._previewSelectedItem(new_hub)
        # Written before no_hero_art is cleared - see updateHeroFrom().
        self.setHeroInfo(new_ds)
        self.updateBackgroundFrom(new_ds)
        self._setNoHeroArt(False)

    def _updateHeroFromFocusedHubItem(self, control_id):
        """Sync the hero art/info overlay to whichever item is currently selected in hub-row
        control_id - called on horizontal (left/right) movement within a hub row, via
        checkHubItem() below. Port of the hero-art-relevant slice of HomeWindow.checkHubItem()
        (home.py) - just the hero-info replica update, mirroring updateHeroFrom() rather than
        calling it directly for the same reason checkHubItem() does (own docstring, home.py):
        updateHeroFrom() always calls updateBackgroundFrom() unconditionally, ignoring the
        dynamicBackgrounds setting - hero info (title/summary) should still update regardless of
        that setting, only the background art panel itself is gated on it."""
        control = self.hubControls[control_id - self.HUB_CONTROL_ID]
        mli = control.getSelectedItem()
        # `is None`, not truthiness - unopened Playlist objects are falsy (see setHeroInfo()).
        if not mli or mli.dataSource is None:
            return
        ds = mli.dataSource
        # Written before no_hero_art is cleared - see updateHeroFrom().
        self.setHeroInfo(ds)
        self.updateBackgroundFrom(ds)
        self._setNoHeroArt(False)

    # ------------------------------------------------------------------------------------------
    # Input: the Recommended view's own handlers (RecommendedWindow's viewAction(), viewClick() and
    # viewFocus()), each called after the host's shared routing (kodigui.MultiWindowView).

    def hubAction(self, action):
        """The Recommended view's own actions, from the host's routeAction() after its shared
        steps: on a hub row (control ids 400-4xx), Up and Down slide the rows, Left and Right sync
        the hero, Back returns the row to its first item, and the context menu opens the hub
        menu. True when the action was used; False lets the host's Back and Home handling and
        then Kodi's own have it - Left and Right always go on to Kodi, which moves the row's cursor
        itself."""
        controlID = self.getFocusId()
        if not 399 < controlID < 500:
            return False

        if self._hubJustEnteredFromOutside:
            # Live-confirmed double-delivery (HUBDBG investigation): this same action
            # already carried focus into the hub range natively (via a control outside
            # it - the tabs row 320, the audio widget 204, or the sidebar rail 9001 -
            # all landing here through 50's <defaultcontrol> chain, via <ondown> or, for
            # the sidebar, <onright>) - Kodi delivers it here a second time *after* that
            # navigation has already happened, which hubFocus() flagged for us (see its own
            # comment; this method can't tell "just arrived" apart from "already settled
            # here" - by the time it runs, the native move, if any, is already done either
            # way).
            #
            # Checked and consumed here, before branching on action_id below - not only
            # inside the MOVE_UP/MOVE_DOWN branch, where it originally lived: the replay
            # carries whatever direction *caused* the entry (e.g. a RIGHT out of the
            # sidebar, handled by the MOVE_LEFT/MOVE_RIGHT branch below, via
            # checkHubItem()), not necessarily UP/DOWN - a flag left un-consumed by that
            # branch stayed True and then wrongly swallowed the user's next, genuinely
            # separate UP/DOWN press instead, live-confirmed as "after any sidebar
            # interaction, the first up or down press does nothing." Consuming
            # unconditionally here, for whatever action this replay actually is, is what
            # keeps it from ever surviving to affect a later, unrelated real press.
            self._hubJustEnteredFromOutside = False
            return True
        action_id = action.getId()
        if action_id in (xbmcgui.ACTION_MOVE_UP, xbmcgui.ACTION_MOVE_DOWN):
            # Topmost hub, pressing up: exit the rotation ring entirely instead of the
            # silent no-op _startHubSlide() falls into at focusedHubIndex 0 - same role
            # XML onup plays for grid content (library_posters.xml.tpl etc.), just done
            # here in Python since hub-to-hub vertical nav is already fully Python-owned.
            # Prefers the section-tabs row (plan item 0) when it's actually on screen;
            # falls back to the audio widget (204) when the tabs are hidden (a 'mixed'
            # section has none) so pressing up still lands somewhere reachable rather
            # than nowhere - the same condition every XML onup/onright path into 204
            # already gates on (e.g. section_tabs.xml.tpl's own onright).
            if action_id == xbmcgui.ACTION_MOVE_UP and self.focusedHubIndex == 0:
                if self.tabList and self.section.TYPE != 'mixed':
                    self.setFocusId(self.TAB_LIST_ID)
                    return True
                elif xbmc.getCondVisibility(
                        'Player.HasAudio + String.IsEmpty(Window(10000).Property(script.plex.theme_playing))'):
                    self.setFocusId(self.PLAYER_STATUS_BUTTON_ID)
                    return True
            self._startHubSlide(-1 if action_id == xbmcgui.ACTION_MOVE_UP else 1)
            return True
        elif action_id in (xbmcgui.ACTION_MOVE_LEFT, xbmcgui.ACTION_MOVE_RIGHT):
            # Plan items 10 (Group A)/11: sync hero art/info to the item this move is
            # landing on, plus pagination/reselect-position memory (checkHubItem(),
            # all hooked into this same call site). Reads
            # getSelectedItem() directly, same as MOVE_SET's own dynamic-background
            # update does for the grid (GridMixin.gridAction()) - Kodi's native container
            # cursor is already at the new position by the time this runs (that existing,
            # proven pattern is what this one's modeled on), not the old one, so no
            # special before/after ordering is needed here. Deliberately doesn't
            # return True (checkHubItem()'s return value only matters for the NAV_BACK
            # case below) - the actual cursor movement is Kodi's own native list
            # behavior, not something this method does; False hands the action on like
            # anything else unhandled here.
            self.checkHubItem(controlID, action=action)
        elif action in (xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_PREVIOUS_MENU):
            # Only reached when self._backStack is empty (the host's routeAction() pops the
            # chain first otherwise) - i.e. a hub row focused on the root 'recommended'
            # tab, no chain in progress. checkHubItem() resets to item 0 first if not
            # already there (returns False, swallowed here); only lets the action
            # propagate to the host's Back handling once already at item 0 - same shape
            # as HomeWindow's own onAction() routing (home.py).
            if not self.checkHubItem(controlID, action=action):
                return True
        elif action == xbmcgui.ACTION_CONTEXT_MENU:
            # Hub-item context menu - ported from HomeWindow's identical routing
            # (home.py's onAction(), `elif action == xbmcgui.ACTION_CONTEXT_MENU:`
            # inside its own `elif 399 < controlID < 500:` branch). Same return-value
            # -> serverRefresh() handoff as sectionMenu()'s trigger in the host's routeAction().
            show_section = self.hubMenu(controlID)
            if not show_section:
                return True
            self.serverRefresh(section=show_section)
            return True
        return False

    def hubClick(self, controlID):
        """The Recommended view's own clicks: every click the host's routeClick() didn't use."""
        if controlID == self.TAB_LIST_ID:
            self.tabListClicked()
        elif 399 < controlID < 500:
            self.hubItemClicked(controlID)
        elif controlID == self.PLAYER_STATUS_BUTTON_ID:
            self.showAudioPlayer()

    def hubFocus(self, controlID):
        """The Recommended view's own focus handling: every focus event the host's routeFocus()
        didn't drop."""
        # Flags "just crossed into the hub-row range (399-500) from a control outside it" for
        # hubAction() to consume - live-confirmed Kodi behavior: a directional
        # action that exits a native container via its own <onup>/<ondown>/<onright> (the tabs
        # row 320, the audio widget 204, or the sidebar rail 9001, all landing on a hub control
        # via 50's <defaultcontrol> chain) gets delivered to hubAction() a SECOND time *after*
        # native navigation has already moved focus - onFocus(<hub control>) fires before
        # hubAction()'s own getFocusId() for that same press, i.e. the move already happened once
        # by the time our Python code runs at all. Without this guard, hubAction()
        # treated that replay as a second, independent move and acted on it again (silently
        # continuing on to the next row on entry, or swallowing the next real press after a
        # sidebar interaction, depending on which action the replay carried).
        #
        # Computed here, not in hubAction(): this is the only place that reliably knows what
        # controlID had focus *immediately before* this one (self.lastFocusID, not yet
        # overwritten below) - hubAction()'s own getFocusId() can't tell "just arrived from
        # outside" apart from "already settled here", since by the time it runs the native move,
        # if any, has already completed either way. Consumed (reset to False) the first time
        # hubAction() checks it, before branching on the action's own direction -
        # the replay carries whatever direction caused the entry, not necessarily UP/DOWN - so
        # it never survives to affect a later, unrelated real press; those never re-fire onFocus
        # for the same control anyway, since in-hub vertical nav is entirely Python-owned
        # (_startHubSlide()), not native.
        redirect_landed = controlID == self._hubEntryRedirect
        self._hubEntryRedirect = None
        if not redirect_landed:
            was_outside_hub = not (399 < (self.lastFocusID or -1) < 500)
            self._hubJustEnteredFromOutside = (399 < controlID < 500) and was_outside_hub

            # Entering the rows from outside (tabs, sidebar, audio widget) lands wherever Kodi's
            # group focus memory says - the row control that last had focus. That's the anchor
            # unless a slide finished while focus was outside the rows (_finishHubSlide() leaves
            # focus alone then), so correct it here. The arrival's own flag stays set for the
            # replayed action; the redirect's event (redirect_landed above) doesn't recompute
            # it, whichever order the two arrive in, and lastFocusID is pre-seeded to the anchor.
            if self._hubJustEnteredFromOutside and self.visibleHubs:
                anchor_id = self._anchorControlId()
                if controlID != anchor_id:
                    self.reselectActiveSection(controlID, self.lastFocusID)
                    self.lastFocusID = anchor_id
                    self._hubEntryRedirect = anchor_id
                    self.setFocusId(anchor_id)
                    return

        self.recordFocus(controlID)

    def checkHubItem(self, control_id, action=None):
        """Horizontal (left/right) in-row hub navigation - hero-art sync (delegated to
        _updateHeroFromFocusedHubItem() above) and reselect-position memory, both hooked into
        this one call site (hubAction()). Port of HomeWindow.checkHubItem()
        (home.py), plan item 10 Group A (quiet-orbiting-heron.md). In-row pagination (the old
        "load more" placeholder this also used to trigger) is gone - a row is capped at
        home.HUB_ROW_MAX_ITEMS, see _bindHubToControl().

        Round-robin wraparound (the old hubs_round_robin setting) was deliberately dropped after
        this landed, not ported: pressing Left at a row's first item already exits to the sidebar
        (native template onleft neighbor, nothing Python-side to override), and NAV_BACK already
        jumps back to item 0 - between the two, a mid-row "wrap past the end" gesture wasn't worth
        the extra state/complexity (self._lastSelectedItem, the old double-press detector, is gone
        too - nothing else in this file ever needed it).

        self.section.key is None replaces HomeWindow's lastSection is-home check (this file's own
        is_home convention throughout - see _hubRowHeight()'s docstring). self.tasks.add() (not
        .append()+a separate cleanTasks() call, the old shape) - Tasks.add() (backgroundthread.py)
        already self-prunes dead tasks. Drops self._anyItemAction (HomeWindow-only bookkeeping, no
        equivalent consumer here).

        Return value matters only for the NAV_BACK/PREVIOUS_MENU case (every other caller/action
        ignores it): True means "nothing to do here, let it propagate" (already at item 0);
        False means "handled" (jumped back to item 0) - the caller should swallow the action.
        """
        control = self.hubControls[control_id - self.HUB_CONTROL_ID]
        mli = control.getSelectedItem()
        # The "See more" item (is.more) has no dataSource - nothing to sync the hero to, and not
        # a position worth remembering (the reselect would land on it, not on content).
        is_valid_mli = mli and mli.getProperty('is.more') != '1'

        if action in (xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_PREVIOUS_MENU):
            pos = control.getSelectedPos()
            if pos is not None and pos > 0:
                control.selectItem(0)
                self.updateHeroFrom(control[0].dataSource)
                # Forget the remembered position too - selectItem() is Python-initiated, so the
                # MOVE_SET path below that normally records the reselect position never runs
                # for it, and the stale entry would put the row straight back where it was the
                # next time it's rebuilt (sliding far enough for the wrap-control rebind,
                # _bindHubToControl()) - live-reported 2026-09-21.
                if control.dataSource:
                    identifier = control.dataSource.getCleanHubIdentifier(is_home=self.section.key is None)
                    self._hubReselectPositions.pop(identifier, None)
                return False
            # Already at item 0 - nothing for this method to do; tell the caller to let the
            # NAV_BACK/PREVIOUS_MENU action propagate instead of swallowing it.
            return True

        if is_valid_mli:
            self._updateHeroFromFocusedHubItem(control_id)

            # Reselect-position memory - remember this hub's scroll position so navigating away
            # and back (a different hub rebound to this same physical control, or a fresh
            # 'recommended' entry later in the session) doesn't always reset to item 0. Restored
            # in _bindHubToControl().
            if control.dataSource:
                is_home = self.section.key is None
                identifier = control.dataSource.getCleanHubIdentifier(is_home=is_home)
                pos = control.getSelectedPos()
                if pos is not None and mli.dataSource is not None:
                    self._hubReselectPositions[identifier] = (str(mli.dataSource.ratingKey), pos)

    def hubSeeMoreClicked(self, hub):
        """The row's trailing "See more" item (is.more, _bindHubToControl()) was clicked. Meant
        to open a grid of the hub's full listing (hub.key / hub.hubKey is that endpoint) - that
        screen isn't built yet, so this only logs for now (on request, 2026-09-21: the item and
        the 20-item row cap first, the grid afterwards)."""
        util.DEBUG_LOG('Hub "See more" clicked (grid not built yet): {0}', hub)

    def _anchorControlId(self):
        """Whichever physical control (400-403) is currently serving the anchor role. Ported
        verbatim from HomeWindow._anchorControlId() (home.py)."""
        return self.HUB_ROTATION_RING[self._anchorRingPos]

    @property
    def currentHub(self):
        """The hub bound to whichever control is currently anchored - ported verbatim from
        HomeWindow.currentHub() (home.py). Used by hubMenu() below."""
        if self.hubControls:
            control = self.hubControls[self._anchorControlId() - self.HUB_CONTROL_ID]
            if control:
                return control.dataSource
        return None

    @property
    def carriedProps(self):
        """Window properties to carry over to a new window opened on top of this one (auto-play
        from a hub item, see hubItemClicked() below) - ported verbatim from
        HomeWindow.carriedProps (home.py). The new window class temporarily invalidates this one
        while a dialog is showing rather than rendering the underlying window, and the properties
        vanish - without carrying hub.text2lines.<id> over explicitly, a text2lines-enabled hub
        row loses its title2 label once the dialog closes and this window is shown again. Every
        other call site in this file already reads this defensively (getattr(self, 'carriedProps',
        None)) expecting it to exist eventually - it never did until now."""
        anchor_id = self._anchorControlId()
        if self.hubControls and self.hubControls[anchor_id - self.HUB_CONTROL_ID].dataSource:
            hub = self.hubControls[anchor_id - self.HUB_CONTROL_ID].dataSource
            return {'hub.text2lines.{0}'.format(anchor_id): '1',
                    'hub.nolabels.{0}'.format(anchor_id): self._hubIsMusic(hub) and '1' or ''}

    def _ringRoleOffset(self, control_id, ring_pos=None):
        """control_id's current role-offset (HUB_MIN_ROLE -1 above / 0 anchor / +1 peek-below /
        HUB_MAX_ROLE +2 below) relative to ring_pos (an index into HUB_ROTATION_RING -
        defaults to the current anchor's own position, self._anchorRingPos, when not given).
        Ported verbatim from HomeWindow._ringRoleOffset() (home.py)."""
        if ring_pos is None:
            ring_pos = self._anchorRingPos
        ring = self.HUB_ROTATION_RING
        return ((ring.index(control_id) - ring_pos - self.HUB_MIN_ROLE) % len(ring)) + self.HUB_MIN_ROLE

    def hubItemClicked(self, hub_control_id):
        """Open whatever's focused in a hub row (controls 400-403). Port of
        HomeWindow.hubItemClicked() (home.py): generic opener.open() dispatch, since hub items
        span many different types across different hubs, unlike the grid's own section-TYPE-
        scoped showPanelClicked().

        Plan item 10, Group B (quiet-orbiting-heron.md), all three ported here:
        - in-progress auto-resume (home_inprogress_resume setting)
        - season/episode -> show redirection for discover/watchlist hub items
        - hub-becomes-empty cleanup after the click (an item removed/deleted, a watchlist item
          dropped on open, etc. leaving this row with fewer items than before)

        watchlist-specific extra_kwargs (live-confirmed gap, fixed here): this window's own
        contentMode can be 'recommended' for a section whose TYPE is 'movies_shows' (Watchlist,
        e.g. if that's the last tab persisted for it - see reset()'s own contentMode comment), in
        which case clicks land here, not showPanelClicked() - which never gets a chance to set
        from_watchlist/directly_from_watchlist at all. Without it, the opened window's own
        getLibrarySectionId() legitimately finds nothing real to match (discover items report the
        literal string "watchlist"), so its sidebar has nothing to highlight. Same detection
        showPanelClicked() uses (self.section.TYPE, not per-hub cross-section sourcing -
        hubMenu()'s own _crossSectionSource - which would be a separate, currently unhandled case
        even there). Independent of and additive to the per-item is_watchlist redirection below -
        one answers "is this section the Watchlist", the other "is this particular item a
        discover/watchlist item" (a hub on a real library section can still surface one, e.g.
        cross-section hubs), same as HomeWindow kept them separate.
        """
        control = self.hubControls[hub_control_id - self.HUB_CONTROL_ID]
        mli = control.getSelectedItem()
        # `is None`, not truthiness: an unopened Playlist (home.playlists hub) is falsy -
        # BasePlaylist.__len__() is its item count, empty until opened - so a truthiness check
        # silently swallowed every playlist click here (live-reported 2026-09-20). Same trap
        # showPanelClicked()/setHeroInfo() document.
        if not mli or mli.dataSource is None:
            if mli and mli.getProperty('is.more') == '1':
                self.hubSeeMoreClicked(control.dataSource)
            return

        # In-progress auto-resume - ported from HomeWindow.hubItemClicked() (home.py).
        auto_play = False
        if util.getSetting('home_inprogress_resume'):
            if mli.dataSource.TYPE in ('episode', 'movie') and mli.dataSource.in_progress:
                auto_play = True

        use_ds = mli.dataSource

        extra_kwargs = {
            'entry_section_id': self.entrySectionId,
            'entry_from_watchlist': self.entryFromWatchlist,
        }
        if self.section.TYPE == 'movies_shows':
            extra_kwargs['from_watchlist'] = True
            extra_kwargs['directly_from_watchlist'] = True
            extra_kwargs['external_item'] = True

        # Season/episode -> show redirection for discover hub items - ported from
        # HomeWindow.hubItemClicked() (home.py). A discover/watchlist hub can surface a season or
        # episode directly (e.g. "New Episodes"); there's no real section context for either on
        # its own, so redirect straight to the show instead of a dead-end info screen.
        if mli.dataSource.is_watchlist:
            extra_kwargs['from_watchlist'] = True
            extra_kwargs['external_item'] = True
            if mli.dataSource.TYPE in ('season', 'episode'):
                use_ds = mli.dataSource.show()

        # context=self (hashed-orbiting-pizza.md Phase 4): hub items span many object types
        # (unlike the grid's own type-scoped showPanelClicked()), so this keeps using
        # opener.open()'s shared dispatch rather than duplicating it locally - context=self lets
        # every chain-aware branch call self.openWindow(...)/swapTo() instead of unconditionally
        # opening a real nested window.
        #
        # Except when auto_play is set: every context-aware *Clicked() branch in opener.py checks
        # `if context is not None` BEFORE looking at auto_play at all, routing straight to
        # context.openWindow() -> swapTo() - which just constructs the target shell normally and
        # shows it, never consulting auto_play (that kwarg only means anything to handleOpen()'s
        # own branch, reached when context is None: create the window unshown - show=False,
        # never added to Kodi's window history - call doAutoPlay() on it directly, and tear it
        # down without ever displaying it). So passing context=self here would silently show the
        # normal info/preplay screen instead of resuming - live-confirmed regression. Bypassing
        # context for this one case doesn't reintroduce a second real window either way: the
        # handleOpen() auto_play path never opens anything itself, it goes straight to playback.
        command = opener.open(use_ds, context=None if auto_play else self, auto_play=auto_play,
                               dialog_props=self.carriedProps if auto_play else None, **extra_kwargs)

        if not command and self.navRequestPending():
            # Only posted (openWindow(); the opener returns ''): the open runs once this returns,
            # so the check below would hold it up by a server round trip (15-50 ms on the AM6B),
            # and Back rebuilds this view with fresh rows anyway - as grid clicks already skip it
            # (3c). Blocking opens (auto-play, photos) still come back here and tidy the row.
            return

        # Hub-becomes-empty cleanup - ported from HomeWindow.hubItemClicked() (home.py).
        # MediaItem.exists() checks the deleted/deletedAt flags; a full check is also tried since
        # we still want to show the media if it's still valid but has deleted files.
        if not mli.dataSource.exists() and not mli.dataSource.exists(force_full_check=True):
            try:
                control.removeItem(mli.pos())
            except (ValueError, TypeError):
                pass

        if not control.size():
            # this hub is now empty - drop it from the logical list and rebind whatever's left
            # (visibleHubs has no "holes", so any in-range index is automatically valid).
            if self.visibleHubs:
                del self.visibleHubs[self.focusedHubIndex]
            if self.visibleHubs:
                self.focusedHubIndex = min(self.focusedHubIndex, len(self.visibleHubs) - 1)
                self._bindAllHubSlots()
                anchor_id = self._anchorControlId()
                if self.getFocusId() != anchor_id:
                    self.setFocusId(anchor_id)
            else:
                self.setFocusId(self.SECTION_LIST_ID)

        self.processCommand(command)

    def hubMenu(self, hubControlID):
        """Context menu (ACTION_CONTEXT_MENU) for whichever item is focused in a hub row - ported
        from HomeWindow.hubMenu() (home.py), adapted to this window's own state. Triggered from
        hubAction() on a hub row (399 < controlID < 500), which owns the return-value ->
        serverRefresh() handoff, same shape as sectionMenu()'s own trigger.

        Two adaptations from the original, both deliberate scope-narrowing rather than a straight
        port:
        - `self.toggleWatched(item=ds, state=True)`/`self._updateOnDeckHubs()` -> this window's own
          `toggleWatched(mli, ...)` (takes a ManagedListItem, not a raw item) and a direct
          `updateUnwatchedAndProgress(mli)` call instead. HomeWindow's `_updateOnDeckHubs()` is a
          background-task machinery (UpdateHubTask/getCurrentHubsPositions) tied to Home's own
          incremental hub-refresh system, which this window doesn't have (its hubs are fetched once
          per section swap, see `_recommendedHubsCallback()`'s own docstring) - not ported. Mark
          watched/unwatched here only updates the tile's own display in place; the hub's item *list*
          itself (e.g. an item newly eligible for On Deck) stays as it was until the section is next
          reopened, a known, accepted narrowing matching this window's existing simpler hub-refresh
          model elsewhere.
        - `add_to_home` (adding a library's hub to Home as a cross-section hub) is not ported at
          all - it depends on `_crossSectionSource`/`getCombinedHubsForSection()`-style cross-section
          hub aggregation, none of which exists on this window (Manage Hubs' own port explicitly
          left this out too, see that section's progress notes). `disable_hub` still works: it only
          needs `_ensureCustomConfigExists()`/`_disableHub()`, both already ported.
        """
        hub = self.currentHub
        if not hub:
            return

        control = self.hubControls[hubControlID - self.HUB_CONTROL_ID]
        mli = control.getSelectedItem()
        if not mli:
            return

        if mli.dataSource is None or mli.dataSource is kodigui.DUMMY_DATA_SOURCE:
            return

        ds = mli.dataSource

        # Determine the hub's source section and catalog_id. (HomeWindow's original also computed a
        # lastSection-is-home flag here for the 'add_to_home' option's own visibility check
        # - not ported, see this method's own docstring, so only hub_is_home below is needed.)
        cross_source = hub.__dict__.get('_crossSectionSource')
        hub_source_key = cross_source if cross_source is not None else self.section.key
        hub_is_home = hub_source_key is None
        clean_identifier = hub.getCleanHubIdentifier(is_home=hub_is_home)

        # Build catalog_id for Manage Hubs integration
        if hub_is_home:
            catalog_id = clean_identifier
        else:
            catalog_id = '{}:{}'.format(hub_source_key, clean_identifier)

        hub_title = hub.__dict__.get('_displayTitle') or hub.title or clean_identifier
        if hub_is_home:
            hub_title = self.homeHubDisplayTitle(hub, self.ambiguousHubTitles(self.visibleHubs))

        select_base = 0

        options = []
        has_prev = False
        is_watchlist = self.section == home.watchlist_section
        # Don't allow disabling hubs for watchlist or main CW/On Deck hubs
        if not is_watchlist and hub.hubIdentifier != "continueWatching":
            options.append({'key': 'disable_hub', 'display': T(33659, "Disable Hub: {}").format(hub_title)})
            has_prev = True

        if ds.TYPE in ('episode', 'season', 'movie', 'show'):
            if has_prev:
                options.append(dropdown.SEPARATOR)

            has_mp = False
            if not mli.getProperty('watched'):
                options.append({'key': 'mark_watched', 'display': T(32319, "Mark Played")})
                select_base = has_prev and 1 or 0
                has_mp = True

            if ds.isFullyWatched or ds.isWatched or ds.viewedLeafCount.asInt() > 0:
                options.append({'key': 'mark_unwatched', 'display': T(32318, "Mark Unplayed")})
                select_base = has_prev and 1 or has_mp and 0
                has_mp = True

            if ds.TYPE in ('episode', 'movie'):
                if (hub.hubIdentifier == "continueWatching" or
                        clean_identifier in ("tv.inprogress", "movie.inprogress")):
                    # allow removing items from CW / On Deck
                    options.append(dropdown.SEPARATOR)
                    options.append({'key': 'remove_cw', 'display': T(33662, "Remove from Continue Watching")})
                    if not has_mp:
                        select_base = 1
                if util.getSetting('home_inprogress_resume') and ds.in_progress:
                    # this is an in progress item that would be auto resumed; add specific entry to visit media instead
                    options.insert(0, dropdown.SEPARATOR)
                    options.insert(1, {'key': 'start_over', 'display': T(32317, 'Play from beginning')})
                    options.insert(2, {'key': 'to_item', 'display': T(33019, "Visit media item")})
                    select_base = 1
                elif ds.in_progress:
                    options.insert(0, dropdown.SEPARATOR)
                    options.insert(1, {'key': 'start_over', 'display': T(32317, 'Play from beginning')})
                    options.insert(2, {'key': 'resume', 'display': T(32429, "Resume from {}").format(util.timeDisplay(ds.viewOffset.asInt()).lstrip('0').lstrip(':'))})

            if ds.TYPE in ('episode', 'season'):
                options.append(dropdown.SEPARATOR)
                options.append({'key': 'to_show', 'display': T(32323, "Go To Show")})

            if 'items' in util.getSetting('cache_requests'):
                options.append({'key': 'cache_reset', 'display': T(33728, "Clear cache for item")})

        if not options:
            return

        choice = dropdown.showDropdown(
            options,
            pos=(660, 441),
            close_direction='none',
            set_dropdown_prop=False,
            header=T(33030, 'Choose action for: {}').format(hub.title),
            select_index=select_base,
            align_items="left",
            dialog_props=getattr(self, 'carriedProps', None)
        )

        if not choice:
            return

        elif choice["key"] == "disable_hub":
            # Disable hub via Manage Hubs settings (same as disabling in the dialog). Returning
            # self.section hands off to hubAction()'s serverRefresh() call, same pattern
            # sectionMenu()'s own 'manage_hubs'/'refresh_hubs' choices use - forces the section
            # to reopen, which re-triggers hub fetching/isHubHidden() filtering and so drops the
            # now-disabled hub from view.
            section_key = self.section.key
            self._ensureCustomConfigExists(section_key)
            self._disableHub(catalog_id, section_key)
            return self.section

        elif choice["key"] in ("mark_watched", "mark_unwatched"):
            if util.getSetting('home_confirm_actions'):
                button = optionsdialog.show(
                    T(32319, "Mark Played") if choice["key"] == "mark_watched" else T(32318, "Mark Unplayed"),
                    u"{} {}".format(mli.label, mli.label2),
                    T(32328, 'Yes'),
                    T(32329, 'No'),
                    dialog_props=getattr(self, 'carriedProps', None)
                )

                if button != 0:
                    return

            if choice["key"] == "mark_watched":
                self.toggleWatched(mli)

            elif choice["key"] == "mark_unwatched":
                mli.dataSource.markUnwatched()
                self.updateUnwatchedAndProgress(mli)

        elif choice["key"] == "remove_cw":
            if util.getSetting('home_confirm_actions'):
                button = optionsdialog.show(
                    T(33662, "Remove from Continue Watching"),
                    u"{} {}".format(mli.label, mli.label2),
                    T(32328, 'Yes'),
                    T(32329, 'No'),
                    dialog_props=getattr(self, 'carriedProps', None)
                )

                if button != 0:
                    return

            ds.removeFromContinueWatching()
            # Force a reopen (unlike mark_watched/mark_unwatched's in-place tile update) - the
            # whole point of removing an item from Continue Watching is for it to disappear from
            # the hub, which an in-place property update on this one tile can't do.
            return self.section

        elif choice["key"] == "to_show":
            try:
                command = opener.open(ds.show(), context=self, dialog_props=getattr(self, 'carriedProps', None))
                if navintent.isNoData(command):
                    raise util.NoDataException
            except kodigui.NO_DATA_ERRORS:
                # the server's own errors too: ds.show() fetches the show, and a 404 there
                # (show deleted) fell through to routeAction(), which logs it with no notice
                util.ERROR("No data - deleted or server disconnected?", notify=True, time_ms=5000)
                return

        elif choice["key"] == "to_item":
            try:
                command = opener.open(ds, context=self, dialog_props=getattr(self, 'carriedProps', None))
                if navintent.isNoData(command):
                    raise util.NoDataException
            except kodigui.NO_DATA_ERRORS:
                util.ERROR("No data - deleted or server disconnected?", notify=True, time_ms=5000)
                return

        elif choice["key"] == "start_over":
            try:
                command = opener.open(ds, auto_play=True, start_over=True, dialog_props=getattr(self, 'carriedProps', None))
                if navintent.isNoData(command):
                    raise util.NoDataException
            except kodigui.NO_DATA_ERRORS:
                util.ERROR("No data - deleted or server disconnected?", notify=True, time_ms=5000)
                return
            return

        elif choice["key"] == "resume":
            try:
                command = opener.open(ds, auto_play=True, dialog_props=getattr(self, 'carriedProps', None))
                if navintent.isNoData(command):
                    raise util.NoDataException
            except kodigui.NO_DATA_ERRORS:
                util.ERROR("No data - deleted or server disconnected?", notify=True, time_ms=5000)
                return
            return

        elif choice["key"] == "cache_reset":
            try:
                util.DEBUG_LOG('Clearing requests cache for {}...', ds)
                ds.clearCache()
            except Exception as e:
                util.DEBUG_LOG("Couldn't clear cache: {}", e)

    @staticmethod
    def promotedHubSourceKey(hub_identifier):
        """The library section key a server-promoted Home hub belongs to, or None for Home's
        own hubs. On Home the server lists a library's own hubs alongside Home's (promoted="1"),
        told apart only by a trailing section-id suffix on the hubIdentifier -
        video.inprogress.32, movie.recentlyreleased.22, music.recent.played.10 - where Home's
        own carry none (home.movies.recent, continueWatching). A section's own hub listing
        uses two suffixes (section + instance, movie.recentlyadded.22.1 - see
        BaseHub.getCleanHubIdentifier(), plexlibrary.py), so the section is the last numeric
        part before any second numeric one, never blindly the last."""
        parts = (hub_identifier or '').split('.')
        digits = []
        while parts and parts[-1].isdigit():
            digits.append(parts.pop())
        if not digits or not parts:
            return None
        return digits[-1]

    @staticmethod
    def ambiguousHubTitles(hubs):
        """The titles (lower-cased) more than one of `hubs` shares - the set
        homeHubDisplayTitle() disambiguates against. Bare titles only: a hub's own _displayTitle
        isn't consulted, that's this same mechanism's output."""
        seen, dupes = set(), set()
        for hub in hubs:
            title = (getattr(hub, 'title', None) or '').lower()
            if title:
                (dupes if title in seen else seen).add(title)
        return dupes

    def homeHubDisplayTitle(self, hub, ambiguous, lookup=None):
        """The title a hub shows under on Home. A library hub promoted onto Home by the server
        gets its library named ("Continue Watching – Other Videos"), but only when its bare
        title is ambiguous - shared with another hub on Home (`ambiguous`, from
        ambiguousHubTitles() over whatever set the caller shows: the visible rows, or the Manage
        Hubs catalog). The case: Other Videos' own in-progress hub is titled plain "Continue
        Watching", indistinguishable from the combined continueWatching hub next to it (live-
        reported 2026-09-21, first in Manage Hubs, then the row itself). Not every promoted hub
        (Recently Released Movies etc.) - on request, only the ambiguous ones; and an en dash,
        not home.attributeCrossSectionHub()'s em dash, also on request. Home's own hubs stay
        bare, as does one whose title already is the library's name. `lookup` resolves a
        section key to its section (default: the sidebar's own list, sectionByKey()); an
        unresolvable key (hidden library) leaves the title bare rather than guessing."""
        title = hub.__dict__.get('_displayTitle') or hub.title or ''
        if not title or title.lower() not in ambiguous:
            return title
        source_key = self.promotedHubSourceKey(getattr(hub, 'hubIdentifier', None))
        if source_key is None:
            return title
        section = (lookup or self.sectionByKey)(source_key)
        if section is None or not section.title or section.title.lower() == title.lower():
            return title
        return u'{} – {}'.format(title, section.title)

    def _bindHubToControl(self, hub, control_index):
        """Populate physical hub-row control HUB_CONTROL_ID + control_index with hub's content -
        the properties/dataSource/items population D1's flat _recommendedHubsCallback() did
        inline for every control unconditionally, factored out here since both the initial full
        bind and _startHubSlide()'s wrap-control rebind need to do exactly this for one control
        at a time. Deliberately NOT HomeWindow.showHub()/_showHub() - those also handle hero-art/
        spoiler/cache-clearing, out of scope for D2 (see this block's own header comment).
        Reselect-position restoration (plan item 10, Group A) and the row's trailing "See more"
        item (is.more - hubItemClicked() is what acts on it) are handled here though; the former
        ported from that same HomeWindow.showHub()."""
        is_home = self.section.key is None
        identifier = hub.getCleanHubIdentifier(is_home=is_home)

        display_type = self.getHubDisplayType(hub, identifier)
        flags = self.getHubRenderFlags(hub, identifier)
        title = hub.__dict__.get('_displayTitle') or hub.title or ''
        if is_home:
            title = self.homeHubDisplayTitle(hub, self.ambiguousHubTitles(self.visibleHubs))

        # Row title label reads $INFO[Window.Property(hub.{{ id - 100 }})] (id 500-503, so
        # property name is hub.400 .. hub.403) - same property name/format
        # HomeWindow._showHub() sets (home.py). hub.display.4NN drives which of
        # hub_itemlayout_{poster,square,ar16x9}.xml.tpl actually renders each item - without it
        # every itemlayout's <itemlayout condition="..."> is false and the list shows no visible
        # content even with items bound.
        self.setProperty('hub.display.4{0:02d}'.format(control_index), display_type)
        self.setProperty('hub.4{0:02d}'.format(control_index), title)
        self.setProperty('hub.text2lines.4{0:02d}'.format(control_index), flags['text2lines'] and '1' or '')
        self.setProperty('hub.nolabels.4{0:02d}'.format(control_index), flags['no_labels'] and '1' or '')

        control = self.hubControls[control_index]
        control.dataSource = hub
        # [:HUB_ROW_MAX_ITEMS]: SectionHubsTask already fetches exactly that many, so this is a
        # no-op for a server hub; it's for anything that builds hub.items some other way
        # (PlaylistHub's own fixed fetch, plexlibrary.py) - the cap is the row's, not the fetch's.
        items = [mli for mli in
                (self.createListItem(obj, wide=flags['with_art'])
                 for obj in hub.items[:home.HUB_ROW_MAX_ITEMS]) if mli]

        # getHubRenderFlags() above already computes with_progress (hub-identifier-based - e.g.
        # False for watchlist/discovery hubs via HUBS_NO_PROGRESS), but nothing ever acted on it -
        # createListItem()'s own create*ListItem() family (createMovieListItem()/
        # createEpisodeListItem()/etc.) never sets the 'progress' property at all, matching
        # HomeWindow's own identical methods (home.py) byte-for-byte - HomeWindow's progress bar
        # comes entirely from this post-processing step instead (its own showHub(), home.py:5359-
        # 5362), which was one of the pieces this method's own docstring already calls out as
        # deliberately out of scope for the D2 port ("reselect-position restoration and hero-art/
        # spoiler/cache-clearing") - with_progress itself just wasn't named there explicitly and
        # ended up silently dropped along with them. Live-confirmed regression: the Continue
        # Watching/On Deck progress bar (present in the old HomeWindow UI) never appeared on this
        # window's Recommended tab at all. Fixed here rather than in createListItem() itself, same
        # division of responsibility HomeWindow's own code uses (per-item-type builders vs.
        # per-hub-context binding).
        if flags['with_progress']:
            for mli in items:
                mli.setProperty('progress', util.getProgressImage(mli.dataSource))

        # Trailing "See more" item, when the row's cap cut the hub short (hub.more: the server
        # had more than the HUB_ROW_MAX_ITEMS asked for; the len() check covers items built some
        # other way, see the slice above). Replaces the old in-row "load more" placeholder
        # (is.end + ExtendHubTask pagination) - on request, 2026-09-21: a row loads all of its
        # items up front and never pages. Its empty label/no dataSource is what checkHubItem()/
        # hubItemClicked() key off (is.more); the label is the item's own caption
        # (hub_itemlayout_*.xml.tpl's "See more" pill reads ListItem.Label). HUBS_NO_SEE_MORE:
        # hubs whose hub.more flag lies (see its own comment).
        #
        # Reselect-position memory (plan item 10, Group A) - ported from
        # HomeWindow._hubReselectPositions, restored here since every rebind path (the initial
        # full bind and _startHubSlide()'s wrap-control rebind) funnels through this one method.
        # ratingKey resolution first, falling back to the stored position; the bounds check is
        # for a position that no longer exists (the hub's real content shrank). No "select ahead,
        # then back" any more: the row is a fixedlist now (script-plex-recommended.xml.tpl), which
        # places a selected item deterministically (pinned at the row's start, or spread across
        # the last slots when the tail fits), not "scrolled the minimum to bring it on-screen".
        if ((hub.more.asBool() or len(hub.items) > home.HUB_ROW_MAX_ITEMS)
                and identifier not in self.HUBS_NO_SEE_MORE):
            more = kodigui.ManagedListItem(T(35093, 'See more'))
            more.setBoolProperty('is.more', True)
            items.append(more)

        control.replaceItems(items)

        # Item 0 unless there's a remembered position: the native control keeps whatever it had
        # selected across replaceItems()/reset(), which may belong to a different hub (a slide's
        # wrap rebind) or to before an in-place Home reset (_resetHubsToTop()).
        selected = 0
        reselect = self._hubReselectPositions.get(identifier)
        if reselect and items:
            rk, pos = reselect
            resolved = next((i for i, mli in enumerate(items)
                              if mli.dataSource and str(mli.dataSource.ratingKey) == rk), pos)
            if resolved is not None and 0 <= resolved < len(items):
                selected = resolved
        if items:
            control.selectItem(selected)

    def _recommendedHubsFetchedFor(self, generation):
        """SectionHubsTask's callback for a fetch on a worker (onFirstInit()'s 'recommended'
        branch): posts the bind to the main thread (MultiWindow.postUI()), where it runs once this
        view has finished initialising."""
        def callback(section, hubs, reselect_pos_dict=None):
            self.postUI('bind hubs', self._bindFetchedHubs, args=(section, hubs, generation))
        return callback

    def _bindFetchedHubs(self, section, hubs, generation):
        started = time.time()
        self._recommendedHubsCallback(section, hubs, generation)
        swapStarted = self.__dict__.get('_lastSwapStarted')
        util.DEBUG_LOG("Library: hub rows bound in {0} ms (fetched on a worker), {1} ms after the request",
                       int((time.time() - started) * 1000),
                       int((time.time() - swapStarted) * 1000) if swapStarted else '?')
        if (generation == self._listGeneration and not self.closing
                and self.contentMode == 'recommended'):
            self._focusAnchorHub()

    def _focusAnchorHub(self):
        """After a fresh bind (_recommendedHubsCallback()), focus the anchor row."""
        # Explicitly (re-)assert focus on the anchor hub row - ported from
        # HomeWindow.applyInitialHubFocus() (home.py), which only ever did this once, the very
        # first hubs draw of a whole session - broadened 2026-09-04 (live-reported) to run on
        # every fresh 'recommended' entry. Since 3d the bind lands after the window is up (the
        # fetch runs on a worker), and focus still goes to the anchor then, wherever it is: the
        # sidebar click that opened the section expects to land in the content. A restored
        # hub/item position (_captureHostedShellRestoreState()'s chain, or _bindHubToControl()'s own
        # self._hubReselectPositions) gets selected via plain Python selectItem() calls, all
        # before this window has ever painted - live-confirmed Kodi doesn't reliably render a
        # focus ring for a pre-selected item from that alone, only once the control's focus is
        # genuinely (re-)asserted like this does; needing an unrelated input (Kodi's own
        # cursor-move on the very next repaint that follows) before the ring appeared was the
        # visible symptom. Harmless when nothing needed restoring - the anchor control was
        # already going to end up focused by native <defaultcontrol> in the common case, this
        # just makes it explicit/unconditional instead of leaving it to chance.
        if self.visibleHubs:
            # Live-confirmed regression from the setFocusId() call itself (2026-09-04): it
            # triggers a real onFocus(<hub control>) callback the same as any other focus
            # move, and hubFocus()'s own _hubJustEnteredFromOutside detector (see its own
            # docstring) can't tell this deliberate, one-time initial focus apart from a
            # genuine native cross-container arrow move (sidebar/tabs -> hub row) - it read
            # self.lastFocusID as still outside the hub range (None, or wherever native
            # default control focus happened to leave it) and set the flag exactly as if a
            # real duplicate native replay were coming to swallow. None ever arrives after a
            # programmatic setFocusId(), so the flag just sat there and silently ate the
            # user's very next real navigation press instead - symptoms ranged from a dead
            # first move (hero/reselect-position not updating) to a dead first "load more"
            # trigger, both self-correcting on a second press. Pre-seeding lastFocusID to the
            # anchor control itself - true in spirit, there's no real prior focus to speak of
            # on a window that has never painted - makes hubFocus()'s own was_outside_hub read
            # False regardless of exactly when its callback actually runs relative to this
            # line, rather than trying to race a reset against it afterward.
            self.lastFocusID = self._anchorControlId()
            self.setFocusId(self._anchorControlId())

    def _recommendedHubsCallback(self, section, hubs, generation):
        """Bind a section's hub rows into the Recommended view, on the main thread: posted by
        _recommendedHubsFetchedFor() once a worker has fetched them (3d in the navigation
        review). generation is _listGeneration when the
        fetch was scheduled; a swap since then makes the bind stale, and it's dropped.

        The bind changes control geometry (getControl(), _setRoleGeometry()'s setPosition()/
        setHeight()), so it stays on the main thread. Doing it on a worker was once blamed for a
        native crash entering/leaving 'recommended'; that turned out to be xbmc/xbmc#27239 (see
        windowutils.SKIN_RELOAD_DEFER_SECONDS), but the rule stays as general caution.

        Builds self.hubControls itself only on the main thread (onFirstInit(), see there) rather
        than here - constructing a ManagedControlList calls getControl(), a Kodi native call, and
        every control-list mapping is fixed for this swap's whole lifetime regardless of which
        thread eventually binds hub content into it.

        Stage D2: this is the only place a fresh 'recommended' bind ever happens (fired exactly
        once per swap, see onFirstInit()'s own comment) - the anchor-centered role-based bind
        (HomeWindow._bindAllHubSlots()'s own shape, home.py) replaces D1's flat per-index bind.
        Always resets self.focusedHubIndex/self._anchorRingPos to their canonical start, same as
        _bindAllHubSlots() - a fresh bind has no "sticky" rotation state to preserve.
        """
        def stale():
            return (generation != self._listGeneration or self.closing
                    or self.contentMode != 'recommended')

        if stale():
            util.DEBUG_LOG("Library: _recommendedHubsCallback() declined - stale (gen {0} != {1}, "
                           "closing={2}, mode={3})", generation, self._listGeneration, self.closing,
                           self.contentMode)
            return

        with self.lock:
            if stale():
                util.DEBUG_LOG("Library: _recommendedHubsCallback() declined post-lock - stale")
                return

            # Defensive, mirroring doRefill()'s identical clear in the other direction: a grid
            # restore request (_pendingRestoreItemPos) only ever gets consumed by fillShows()/
            # fillPlaylists()/fillPhotos(), none of which this 'recommended' path leads to.
            self._pendingRestoreItemPos = None

            is_home = section.key is None
            # A hub can be returned by the server with zero current items (e.g. a personalized/
            # dynamic hub with nothing to show right now). Left in, such a hub would still
            # occupy a role slot in the rotation (the geometry math below has no item-count
            # check), so its control would have a real position but zero bound ListItems -
            # live-confirmed as "Control 403 ... has been asked to focus, but it can't" (the
            # wrapper's own <visible> is gated on Container(...).NumItems>0, so an empty-but-
            # positioned row can never actually be focused, needing an extra press to skip past).
            #
            # isHubHidden() applies the user's own saved hub visibility preferences (Stage C's
            # ported method, self.hubSettings now populated by onFirstInit()'s loadHubSettings()
            # call) - same filter HomeWindow._showHubs() applies (home.py, right next to its own
            # "skip hubs with no content" check this mirrors). Without it, a hub the user has
            # explicitly hidden from their real Home screen still showed up here - live-confirmed
            # (pinnedContentDirectoryID is identical between HomeWindow's own requests and this
            # one, so the fetch itself was never the difference; the missing filter was).
            sorted_hubs = [hub for hub in self.sortHubsByUserOrder(hubs, is_home=is_home, section_key=section.key)
                          if hub.items and not self.isHubHidden(hub.getCleanHubIdentifier(is_home=is_home), section.key)]
            self.sectionHubs[section.key] = sorted_hubs
            self.visibleHubs = sorted_hubs
            # One-shot: popBack() asked to land back on a specific hub row (_pendingRestoreHubId,
            # set via _captureRootRestoreState()/popBack()) - find it by its stable identifier,
            # not position (sortHubsByUserOrder()/hub visibility can shift index between visits).
            # Falls back to the canonical start (hub 0) if there's nothing pending, or the
            # remembered hub isn't in this fetch any more (e.g. it emptied out or got hidden).
            # Item-within-that-hub restoration is already handled separately and automatically by
            # self._hubReselectPositions (_bindHubToControl()/_previewSelectedItem() below) - only
            # *which* hub is anchor is new here.
            restoreHubId = self._pendingRestoreHubId
            self._pendingRestoreHubId = None
            self.focusedHubIndex = 0
            if restoreHubId:
                for i, hub in enumerate(sorted_hubs):
                    if hub.getCleanHubIdentifier(is_home=is_home) == restoreHubId:
                        self.focusedHubIndex = i
                        break
            self._anchorRingPos = self.HUB_ROTATION_RING.index(self.HUB_CONTROL_ID)

            # no_hero_art is written explicitly in every branch of _bindAllHubSlots() below (via
            # updateHeroFrom()/_setNoHeroArt()), never left implicit: a property that's never been
            # written at all reads as empty in Kodi, same as explicitly set to '' - which is the
            # *shown* state, not the hidden one. Group 51's position is no longer tied to it - set
            # once per entry in onFirstInit() (GROUP51_BASELINE_OFFSET's own comment).

            self._bindAllHubSlots()
            util.DEBUG_LOG("Library: _recommendedHubsCallback() bound {0} hub(s) for {1}, anchor={2}",
                           min(len(sorted_hubs), len(self.hubControls)), section.key,
                           self._anchorControlId())

    def _bindAllHubSlots(self):
        """Bind all 5 physical hub-row controls to their current roles, from
        self.visibleHubs/self.focusedHubIndex (already set by the caller) - factored out of
        _recommendedHubsCallback()'s own per-control loop (Stage D2) since it's also needed
        outside a fresh section bind: plan item 10's Group B (hubItemClicked()'s empty-hub
        cleanup, after visibleHubs shrinks) and Group A (returning to a hub row whose reselect
        position should be restored - handled by _bindHubToControl() itself, called from here).
        Ported in spirit from HomeWindow._bindAllHubSlots() (home.py) - "visibleHubs by
        construction only ever contains non-empty hubs, so any in-range index is automatically
        valid" (focusFirstValidHub()'s own comment there) still applies verbatim here.

        All four rows, every time. A fresh entry and an in-place Home reset used to bind the two
        off-screen ones 0.2 s later from a timer thread (defer_peek); measured on the AM6B (step
        11 stage A in the navigation review, F1), that didn't shorten either, so it went."""
        if not self.visibleHubs:
            for index in range(len(self.hubControls)):
                self.hubControls[index].reset()
                self.setProperty('hub.display.4{0:02d}'.format(index), '')
            self.setBoolProperty('hub.has_prev', False)
            self.setBoolProperty('hub.has_next', False)
            self._setNoHeroArt(True)
            self.setProperty('hub.anchor_id', str(self._anchorControlId()))
            self._placeStack(self.focusedHubIndex)
            for control_id in self.HUB_ROTATION_RING:
                role = self._ringRoleOffset(control_id)
                wrapper = self.getControl(self.HUB_WRAPPER_FOR_CONTROL[control_id])
                self._setRoleGeometry(wrapper, role, self.focusedHubIndex)
            return

        self.setProperty('hub.anchor_id', str(self._anchorControlId()))

        # Seed hero art/info from the anchor hub's own remembered-position item (or its first item
        # if there's no reselect memory for it yet - see _previewSelectedItem()) before binding
        # any controls - same ordering HomeWindow._bindAllHubSlots() uses and for the same reason
        # (own comment there): binding the anchor first means the hero state is already settled by
        # the time the other slots populate, so nothing else can race it. Live-confirmed regression
        # using items[0] unconditionally here: a hub revisited later in the session (reselect
        # memory now persists for the whole LibraryWindow lifetime, see __init__'s own comment)
        # would show its first item's hero art/background even though _bindHubToControl() (called
        # below, per control) correctly restored the remembered *selection*.
        anchor_hub = self.visibleHubs[self.focusedHubIndex]
        anchor_ds = self._previewSelectedItem(anchor_hub)
        self.updateHeroFrom(anchor_ds)

        # Group 51 first, then each row placed and bound in turn: an empty row isn't shown (the
        # template's NumItems condition), so a row appears already in place.
        self._placeStack(self.focusedHubIndex)

        for control_id in sorted(self.HUB_ROTATION_RING, key=lambda cid: abs(self._ringRoleOffset(cid))):
            role = self._ringRoleOffset(control_id)
            index = control_id - self.HUB_CONTROL_ID
            wrapper = self.getControl(self.HUB_WRAPPER_FOR_CONTROL[control_id])
            self._setRoleGeometry(wrapper, role, self.focusedHubIndex)

            hub_index = self.focusedHubIndex + role
            hub_exists = 0 <= hub_index < len(self.visibleHubs)
            if role == -1:
                self.setBoolProperty('hub.has_prev', hub_exists)
            elif role == 1:
                self.setBoolProperty('hub.has_next', hub_exists)

            if not hub_exists:
                self.hubControls[index].reset()
                self.setProperty('hub.display.4{0:02d}'.format(index), '')
                continue

            self._bindHubToControl(self.visibleHubs[hub_index], index)

    def _startHubSlide(self, delta):
        """Move the logical focus delta positions (+1 down / -1 up) and animate the transition.
        No-ops at the top/bottom of the hub stack. Ported from HomeWindow._startHubSlide()
        (home.py) - see that method's own docstring for the full rotation-ring reasoning (content
        stays glued to whichever control it's already bound to; ROLE rotates instead; exactly one
        control - the ring's extreme opposite the direction of travel - "wraps around" and needs
        a fresh content bind, always safely off-screen).

        Deliberately drops _captureHubPosition()/self._hubReselectPositions (reselect-position
        memory) entirely - not stubbed, just not called, same scope boundary as
        _recommendedHubsCallback()/_bindHubToControl() above. _prepareHubSlideHero() (hero-art
        sync) is real again as of plan item 11 - see that method's own docstring. Calls
        self._bindHubToControl() for the wrap control's fresh bind instead of HomeWindow.showHub().

        The animation is a HubSlide (step 11 in the navigation review): group 51 alone moves, timed
        by the clock and stepped from the view's wait loop on the main thread (_tickHubSlide()).
        It belongs to the view showing now and to self._listGeneration (bumped by every swap),
        and is dropped without touching its control once either has moved on. Note self.closing
        (LibraryWindow's own "session ending"), not self._closing, which MultiWindow.__getattr__
        would resolve against whichever view is current.
        """
        if not self.visibleHubs:
            return
        new_index = self.focusedHubIndex + delta
        if not (0 <= new_index < len(self.visibleHubs)):
            return

        list_gen = self._listGeneration
        # "Slide timing" line (step 11 stage A in the navigation review): what runs before the rows
        # move, then the animation itself, logged when it ends or is cut short.
        timing = kodigui.StepTiming('{0} to row {1}'.format('down' if delta > 0 else 'up', new_index))

        # Finish any still-running slide from a fast preceding press first, so this transition
        # always starts from a settled, consistent state instead of fighting or compounding with
        # one already in flight.
        self._settleHubSlide()
        timing.mark('settle')

        old_focused_index = self.focusedHubIndex
        self.focusedHubIndex = new_index

        old_ring_pos = self._anchorRingPos
        new_ring_pos = (old_ring_pos + delta) % len(self.HUB_ROTATION_RING)
        self._anchorRingPos = new_ring_pos
        self.setProperty('hub.anchor_id', str(self._anchorControlId()))

        self._prepareHubSlideHero()
        timing.mark('hero')

        # The one control wrapping around: currently at the extreme role opposite the direction
        # of travel - its data isn't valid for any role in the new arrangement, so it needs a
        # fresh content bind and a position snap to its new role. Done synchronously,
        # immediately - its old and new roles are the ring's two extremes, -1 -> +2 going down
        # and +2 -> -1 going up, neither ever on screen (HUB_ROTATION_RING's own comment), so
        # there's nothing to collide with.
        if delta > 0:
            wrap_role, wrap_new_role = self.HUB_MIN_ROLE, self.HUB_MAX_ROLE
        else:
            wrap_role, wrap_new_role = self.HUB_MAX_ROLE, self.HUB_MIN_ROLE
        wrap_control_id = next(cid for cid in self.HUB_ROTATION_RING
                                if self._ringRoleOffset(cid, ring_pos=old_ring_pos) == wrap_role)
        wrap_index = wrap_control_id - self.HUB_CONTROL_ID
        wrap_wrapper = self.getControl(self.HUB_WRAPPER_FOR_CONTROL[wrap_control_id])
        self._setRoleGeometry(wrap_wrapper, wrap_new_role, new_index)

        wrap_hub_index = new_index + wrap_new_role
        wrap_hub_exists = 0 <= wrap_hub_index < len(self.visibleHubs)
        if wrap_hub_exists:
            self._bindHubToControl(self.visibleHubs[wrap_hub_index], wrap_index)
        else:
            self.hubControls[wrap_index].reset()
            self.setProperty('hub.display.4{0:02d}'.format(wrap_index), '')
        # No hub.has_next update here - the wrap control's new role is -1 or +2, never +1, so it
        # never owns that state; whichever mover below lands on +1 does. It does own has_prev when
        # it lands on -1 (going up).
        if wrap_new_role == -1:
            self.setBoolProperty('hub.has_prev', wrap_hub_exists)
        timing.mark('wrap bind')

        # The other 3 controls keep their places in the stack and their content (already correct
        # for their new role - see this method's own docstring); only the new peek-below's height
        # and the has_next/has_prev flags change.
        for cid in self.HUB_ROTATION_RING:
            if cid == wrap_control_id:
                continue
            new_role = self._ringRoleOffset(cid, ring_pos=new_ring_pos)
            if new_role == 1:
                wrapper = self.getControl(self.HUB_WRAPPER_FOR_CONTROL[cid])
                end_y = self._roleLocalY(new_role, new_index)
                wrapper.setHeight(util.vscale(self.height - self.ANCHOR_ABS_Y - end_y, r=0))
                self.setBoolProperty('hub.has_next', True)
            elif new_role == -1:
                self.setBoolProperty('hub.has_prev', True)

        # The one mover: group 51, from the old anchor's offset to the new one's (_group51Y()).
        group = self.getControl(self.GROUP51_ID)
        slide = HubSlide(group, group.getPosition()[0], self._group51Y(old_focused_index),
                         self._group51Y(new_index), self.HUB_SLIDE_TIME, self.__dict__.get('_current'),
                         list_gen, timing)

        # Native focus moves to the destination row now, not when the slide finishes: Kodi hands a
        # Left/Right to whichever row has focus before any of this code sees it, so a Right pressed
        # mid-slide scrolled the row being left, and focus only then landed on the new row
        # (live-reported 2026-09-26). _finishHubSlide() still corrects focus if it's elsewhere.
        if 399 < self.getFocusId() < 500:
            self.setFocusId(self._anchorControlId())

        if self.closing or self._listGeneration != list_gen:
            # Tearing down, or a swap already landed on this same call (not expected - nothing
            # yields in between - but cheap to cover): land it now rather than animate.
            slide.land()
            self._finishHubSlide()
            return

        self.setBoolProperty('hub.sliding', True)
        timing.mark('setup')
        slide.start()
        self._hubSlide = slide
        self.addTicker(self._tickHubSlide)

    def _hubSlideLive(self, slide):
        """Whether slide still belongs to what's showing: the same view, no swap since it started
        (_listGeneration) and the session not ending. Otherwise its control may be gone."""
        return (not self.closing and self._listGeneration == slide.list_gen
                and self.__dict__.get('_current') is slide.view)

    def _tickHubSlide(self, now):
        """The running slide's ticker (MultiWindow.addTicker()), once per wait slice on the main
        thread: one step, then finish once it lands. False when there's nothing left to step."""
        slide = self._hubSlide
        if slide is None:
            return False
        if not self._hubSlideLive(slide):
            self._hubSlide = None
            slide.logTiming('dropped, its view has gone')
            return False
        if slide.step():
            return True
        self._hubSlide = None
        self._finishHubSlide()
        slide.logTiming()
        return False

    def _finishHubSlide(self):
        """Slide-completion - deliberately NOT a full _recommendedHubsCallback() rebuild (that
        would rebind all 4 controls' content unconditionally, defeating the ring design's whole
        point). Both the wrap control and the movers' content/position are already fully
        handled, synchronously, by _startHubSlide() itself - this just clears hub.sliding
        (re-showing the anchor's own title label) and moves native Kodi focus to whichever
        control the ring now says is the anchor. Ported from HomeWindow._finishHubSlide()
        (home.py), minus its checkHubItem(anchor_id) call - horizontal in-hub navigation/
        reselect-preview is out of scope for D2."""
        self.setBoolProperty('hub.sliding', False)
        anchor_id = self._anchorControlId()
        # Only while focus is still in the hub rows (on the control that was the anchor when the
        # slide started). A press that left them mid-slide - Up from the first row to the tabs, or
        # Left to the sidebar - must not be pulled back when the slide lands (live-caught
        # 2026-09-24: fast Up presses into the tab bar bounced back to the row).
        focus_id = self.getFocusId()
        if 399 < focus_id < 500 and focus_id != anchor_id:
            self.setFocusId(anchor_id)

    def _settleHubSlide(self):
        """Land the slide in progress at once and finish it: the next press starts from a settled
        state, and a swap (switchTab(), openSection()) lands it while its view is still there. On
        the main thread, like the steps, so nothing else can be moving the group at the same time.
        A slide whose view has already gone is just dropped."""
        slide = self._hubSlide
        if slide is None:
            return
        self._hubSlide = None
        if not self._hubSlideLive(slide):
            slide.logTiming('dropped, its view has gone')
            return
        slide.land()
        self._finishHubSlide()
        slide.logTiming('cut short')
