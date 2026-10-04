from __future__ import absolute_import

import json
import threading
import time
import weakref

import plexnet
import six
import six.moves.urllib.error
import six.moves.urllib.parse
import six.moves.urllib.request
from kodi_six import xbmc
from kodi_six import xbmcgui
from plexnet import plexapp
from plexnet import plexobjects
from plexnet import util as pnUtil
from six.moves import range

from lib import backgroundthread
from lib import player
from lib import util
from lib.path_mapping import pmm
from lib.util import T
from . import background
from . import busy
from . import collection
from . import dropdown
from . import home
from . import kodigui
from . import optionsdialog
from . import search
from . import section_ids
from . import sidebar_model
from . import navintent
from . import windowutils
from .library_grid import GridMixin, TYPE_PLURAL
from .library_hubs import HubsMixin
from .mixins.playbackbtn import PlaybackBtnMixin
from .mixins.common import CommonMixin


# Sort keys the addon used to persist under its own spelling, mapped to the server's (as
# /sorts advertises them, and as SORT_KEYS/serverSortOptions() now key them). Applied when a
# stored 'sort' setting is read back; both spellings sort identically server-side, this just
# keeps an old setting matching its menu entry.
LEGACY_SORT_KEYS = {
    'resolution': 'mediaHeight',
    'photos.titleSort': 'photo.titleSort',
}


# Music sections pin their view type to the item type rather than honouring the per-section
# viewtype.<uuid>.<key> setting every other section type toggles: Artists, Albums and the
# Collections tab are always the grid, Tracks is always the list (a track is a row, not a card).
# Keyed by item type (LibrarySettings.itemType); a type absent from here - or any section that isn't music - keeps the
# ordinary stored-setting behaviour. Values are VIEWS_SQUARE keys, not window classes, because
# those classes are defined far below this point in the module.
MUSIC_VIEWTYPE_BY_ITEM_TYPE = {
    'artist': 'panel',
    'album': 'panel',
    'collection': 'panel',
    'track': 'list',
}


_sectionHasCollectionsCache = {}

# Sections found empty (server uuid, section key): their tab row is hidden as soon as they open
# next time, rather than shown while loading and then taken away. Dropped the moment one shows
# content. LibraryWindow._noteSectionEmpty().
_emptySections = set()

def _sectionHasCollections(section):
    """Cheap existence probe (X-Plex-Container-Size=0, same shape as collection.py's own
    leafCount probe) for the Collections tab's visibility gate.

    Cached in a module-level dict keyed by (server uuid, section key), NOT as an attribute on the
    section object itself - live-confirmed as the actual reason the Collections tab never appeared
    at all: PlexObject.__getattr__ (plexobjects.py) auto-vivifies ANY undefined attribute access
    into an empty PlexValue('', self) instead of raising AttributeError, and even writes that
    sentinel back onto the instance via setattr() as a side effect of the lookup itself - so
    getattr(section, '<made-up-name>', None) can never see a real cache miss (default None); the
    very first check already returns that non-None empty sentinel, short-circuiting before the
    real probe ever ran. No exception, nothing to log - exactly the symptom seen live. A plain
    module-level dict sidesteps PlexObject entirely.

    Scoped to "for as long as we're in that section", not the process lifetime: openSection()
    evicts a section's entry the moment it actually swaps to it (see its own call to
    _invalidateSectionHasCollectionsCache()), so re-entering a section always re-probes live
    (picks up collections created/removed since the last visit) while every onFirstInit() within
    that same visit - including content-mode swaps, which trigger onFirstInit() too, not just
    section changes - reuses the cached answer instead of re-hitting the server each time.

    Callers are expected to only call this for section types the item-type dropdown already
    offered 'collection' for (movie/show/artist) - no point probing types that structurally can't
    have any."""
    cache_key = (section.server.uuid, section.key)
    if cache_key in _sectionHasCollectionsCache:
        return _sectionHasCollectionsCache[cache_key]
    if section.server.offline or section.server.suspect:
        # Not answering (or being retested): no tab, and nothing cached, so the next visit asks
        # again. This runs on the main thread as a view opens, and live on the AM6B (2026-10-03)
        # asking a server that had stopped answering held the screen for its connect timeout.
        return False
    try:
        has = bool(section.all(start=0, size=0, type_=plexobjects.SEARCHTYPES.get('collection')).totalSize.asInt())
    except:
        util.ERROR()
        has = False
    _sectionHasCollectionsCache[cache_key] = has
    return has

def _invalidateSectionHasCollectionsCache(section):
    """Called from openSection() the moment it actually swaps to `section`, so the next
    _sectionHasCollections() call for it (from _tabListNeedsRebuild(), via onFirstInit()
    immediately after) re-probes live instead of trusting a possibly stale answer left over from
    a previous visit - see _sectionHasCollections()'s own docstring for the caching scheme this is
    half of."""
    _sectionHasCollectionsCache.pop((section.server.uuid, section.key), None)

class LibrarySettings(object):
    def __init__(self, section_or_server_id):
        self.sectionType = None
        # The section's current item type ('movie', 'episode', 'album', 'collection', 'audio'...):
        # this section's saved choice, or its own type. Owned here, per section and per window -
        # it used to be the module global library.ITEM_TYPE, which every window and worker shared
        # (3e in the navigation review). Keys getSetting()/setSetting()'s per-type settings.
        self.itemType = None
        # showWholeLibrary(): an item type for this view only, in place of the saved one
        self._itemTypeOverride = None
        if isinstance(section_or_server_id, six.string_types):
            self.serverID = section_or_server_id
            self.sectionID = None
        else:
            self.serverID = section_or_server_id.getServer().uuid
            self.sectionID = section_or_server_id.key
            # Fallback for _loadSettings() below, when this section has never had its own
            # ITEM_TYPE saved (getItemType() returns None) - the section's own native type,
            # not whatever a completely different, previously-open section left the ITEM_TYPE
            # module global at.
            self.sectionType = section_or_server_id.TYPE

        self._loadSettings()

    def _loadSettings(self):
        if not self.sectionID:
            self._settings = {}
            return

        self._settings = self._readSettings()

        # Live-confirmed bug without the sectionType fallback: a section that's never had its
        # own ITEM_TYPE saved (getItemType() returns None) fell all the way through to the bare
        # ITEM_TYPE module global - whatever a completely different, previously-open section
        # left it at (e.g. Music's 'album'), not anything valid for *this* section - silently
        # sending the wrong type= filter to the server and rendering as "No content available"
        # even though the library genuinely has content. sectionType (this section's own native
        # type, set in __init__) is the correct fallback for a never-configured section; the
        # bare ITEM_TYPE global is now only reached for the string-serverID construction (no real
        # section to derive a type from at all).
        self.itemType = self.getItemType() or self.sectionType
        util.setGlobalProperty('item.type', str(self.itemType))

    def getItemType(self):
        if self._itemTypeOverride:
            return self._itemTypeOverride

        if not self._settings or self.sectionID not in self._settings:
            return None

        return self._settings[self.sectionID].get('ITEM_TYPE')

    def setItemType(self, item_type):
        assert item_type is not None, "Invalid type: None"
        self._itemTypeOverride = None
        self.itemType = item_type
        util.setGlobalProperty('item.type', str(item_type))
        self._mutate(lambda entry: entry.update({'ITEM_TYPE': item_type}))

    def showWholeLibrary(self):
        """A view filtered by a genre (or director, actor...) shows the whole library's items in it,
        not the Collections tab's: the section's own type in place of a saved 'collection', for
        this view only. Not saved, so the section still opens on Collections, and Back returns to
        it, as before. Live, 2026-10-04: Collections, then Categories, then a genre showed the
        collections in that genre."""
        if self.itemType == 'collection' and self.sectionType:
            self._itemTypeOverride = self.itemType = self.sectionType
            util.setGlobalProperty('item.type', str(self.itemType))

    def getContentMode(self):
        """Persisted per-section tab choice ('library'/'recommended', quiet-orbiting-heron.md plan
        item 0/"Same reasoning applies one level down" - tab selection sticky per-section, the same
        way sort/filter/item-type already are). A straight read: the live value is
        LibraryWindow.contentMode."""
        if not self._settings or self.sectionID not in self._settings:
            return None

        return self._settings[self.sectionID].get('CONTENT_MODE')

    def setContentMode(self, content_mode):
        self._mutate(lambda entry: entry.update({'CONTENT_MODE': content_mode}))

    def _readSettings(self):
        """The whole server's persisted settings blob, every section in it, as it stands NOW."""
        jsonString = util.getSetting('library.settings.{0}'.format(self.serverID), '')
        settings = {}
        try:
            settings = json.loads(jsonString)
        except ValueError:
            pass
        except:
            util.ERROR()

        return settings if isinstance(settings, dict) else {}

    def _mutate(self, apply_):
        """Apply one change to this section's own entry, against the blob as it stands right now.

        Read-modify-write, deliberately, rather than serialising self._settings: one blob holds
        EVERY section's settings for the server, and every LibrarySettings instance used to hold
        its own whole-blob snapshot from construction time and rewrite all of it on any change.
        Whichever instance wrote last therefore silently reverted everything any other instance
        had written since - a live-confirmed lost update: choosing Albums in the music section
        (setItemType) was reverted to the previously persisted 'track' by a later write from an
        instance constructed before that choice, so the section reopened on Tracks. Re-reading
        here means a stale instance can only overwrite the one field it actually touched.

        Sectionless instances (HomeSection, whose key is None, and the bare-serverID
        construction) write nothing at all: _loadSettings() above leaves them an empty snapshot,
        so serialising it wiped every real section's settings from the blob, and nothing ever
        reads what they store anyway (getItemType() and friends can't match a None sectionID
        against the "null" key json.dumps() writes it as).
        """
        if not self.sectionID:
            return

        settings = self._readSettings()
        apply_(settings.setdefault(self.sectionID, {}))
        self._settings = settings
        util.setSetting('library.settings.{0}'.format(self.serverID), json.dumps(settings))

    def setSection(self, section_id):
        self.sectionID = section_id

    def getSetting(self, setting, default=None):
        if not self._settings or self.sectionID not in self._settings:
            return default

        if self.itemType not in self._settings[self.sectionID]:
            return default

        return self._settings[self.sectionID][self.itemType].get(setting, default)

    def setSetting(self, setting, value):
        def apply_(entry):
            entry.setdefault(self.itemType, {})[setting] = value

        self._mutate(apply_)


def logHomeReset(window, note=None):
    """The "Home reset timing" line (step 11 stage A in the navigation review, F1): an in-place
    reset to Home's root, from the press (navigate()) through the queue, Kodi reactivating the
    window (show()), the reset itself (onReInit()) and the target row's focus event
    (routeFocus()). A module function so the routing tests' stand-in hosts need nothing extra."""
    timing = window.__dict__.get('_homeResetTiming')
    if timing is None:
        return
    window._homeResetTiming = None
    util.DEBUG_LOG("Home reset timing: {0} ms ({1}){2}", int(timing.elapsedMs()), timing.stepsText(),
                   ' - ' + note if note else '')


# util.CronReceiver: tick() (see there) - and its halfHour()/day() no-ops, which util.CRON calls on
# every receiver too; without them the call fell through MultiWindow.__getattr__() to the view.
class LibraryWindow(GridMixin, HubsMixin, PlaybackBtnMixin, kodigui.MultiWindow, windowutils.UtilMixin, windowutils.SidebarMixin, CommonMixin,
                    util.CronReceiver):
    bgXML = 'script-plex-blank.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'

    # Needs to be an even multiple of 6(posters) and 10(small posters) and 12(list)
    # so that we fill an entire row
    CHUNK_SIZE = 240
    CHUNK_OVERCOMMIT = 6

    # Plan item 0 (quiet-orbiting-heron.md): section-tabs row control id (includes/
    # section_tabs.xml.tpl). Defined directly on LibraryWindow (the outer, persisting object),
    # not on a specific inner shell class - unlike e.g. POSTERS_PANEL_ID, this control exists
    # identically in every content-mode's template, so it doesn't need per-shell delegation.
    TAB_LIST_ID = 320

    # hubFocus()'s "just crossed into the hub range from outside it" flag, consumed by
    # hubAction() - see hubFocus()'s own comment (library_hubs.py) for the double-delivery bug this
    # guards against. Class-level default so it's never missing before the first focus event.
    _hubJustEnteredFromOutside = False
    # The anchor control hubFocus() just redirected an arrival to (see there), so that redirect's
    # own focus event leaves _hubJustEnteredFromOutside as the real arrival set it.
    _hubEntryRedirect = None

    def __init__(self, *args, **kwargs):
        PlaybackBtnMixin.__init__(self)
        kodigui.MultiWindow.__init__(self, *args, **kwargs)
        windowutils.UtilMixin.__init__(self)
        self.section = kwargs.get('section')

        # Sidebar entry-section persistence (ported from Sidebar-Tab-Unification's
        # mellow-pondering-magpie.md, 2026-08-18) - see preplay.py's PrePlayWindow.__init__ for the
        # full reasoning. Only ever set when this instance was opened as a drilled-in child (a
        # collection/subDir view) of an ancestor tracking its own inherited entry section - a real
        # top-level section reached directly via the sidebar never passes this, so it stays None
        # here and sidebarActiveSection() falls back to exactly its pre-existing self.section-based
        # computation.
        self.entrySectionId = kwargs.get('entry_section_id')
        self.entryFromWatchlist = kwargs.get('entry_from_watchlist', False)

        self.filter = kwargs.get('filter_')
        self.subDir = kwargs.get('subDir')

        # Descendant-chain hosting (hashed-orbiting-pizza.md Phase 1) - lets this same
        # LibraryWindow instance swapTo() any of the seven real descendant shell types
        # (PrePlayWindow, EpisodesWindow, ...) in place, instead of opening each as a real
        # nested window. _backStack holds two entry shapes: (ShellClass, kwargs) to reconstruct
        # a shell, or (None, {'section':..., 'filter_':...}) to restore this window's own grid -
        # the latter is pushed once, automatically, the moment a chain starts (see swapTo()),
        # so the *last* pop of any chain reveals the grid again instead of running off the end.
        self._backStack = []
        self._nextKwargs = {}
        self._currentKwargs = {}
        self._isHostedShell = False
        # Consumed one-shot by popBack()'s (None, {...}) branch to restore whatever grid item /
        # hub row was focused when a chain started, instead of always landing back on item 0 /
        # hub 0 - see _captureRootRestoreState()'s own docstring for the full picture. Set just
        # before openSection() is called from popBack(), read (and cleared) by fillShows()/
        # fillPlaylists() and _recommendedHubsCallback() respectively, whichever one the restored
        # section's own contentMode actually lands on.
        self._pendingRestoreItemPos = None
        self._pendingRestoreHubId = None
        # Resolve to self as chain host, unconditionally - windowutils.UtilMixin.openWindow()
        # checks self._liveChainHost() to decide whether a click should swapTo() in place or
        # fall back to opener.handleOpen(); pointing this at self lets LibraryWindow's own
        # click-handlers reuse that exact generic path, same as every hosted shell. navigate()
        # and processCommand() below check `self is HOME` rather than delegating to
        # _liveChainHost(), which would resolve back to self and recurse forever.
        self._chainHost = self
        # 'library' (poster/grid, default) or 'recommended' (hubs) - a second swap dimension
        # alongside view-type (panel/panel2/.../list), not a replacement for it. See
        # quiet-orbiting-heron.md's Stage A/B/C/D breakdown for Recommended-tab sharing. Real
        # value determined below, once self.librarySettings exists (its persisted per-section
        # choice is one of the inputs) - this placeholder never actually reaches reset() (which
        # is what first reads it for real), just keeps the attribute defined this early in case
        # anything between here and there looks at it.
        self.contentMode = 'library'
        self.keyItems = {}
        self.firstOfKeyItems = {}
        self.tasks = backgroundthread.Tasks()
        self.backgroundSet = False
        self.showPanelControl = None
        self.keyListControl = None
        self.sectionList = None
        self.lastItem = None
        # The letter updateKey() last wrote to the key property and the letter list (library_grid).
        self._shownKey = None
        self.lastFocusID = None
        self.lastNonOptionsFocusID = None
        self.refill = False
        # Bumped every time doRefill() rebuilds showPanelControl. Used to detect that
        # the panel (and its ListItems) was replaced while a modal child window was open,
        # so we never touch a freed ListItem afterwards (see showPanelClicked).
        self._listGeneration = 0
        self.subOptionCache = {}
        self._filterTypeByKey = {}
        self.closing = False

        self.dcpjPos = 0
        self.dcpjThread = None
        self.dcpjTimeout = 0


        self.cleared = True
        self.librarySettings = LibrarySettings(self.section)
        if self.filter:
            self.librarySettings.showWholeLibrary()

        # Sections with no library-grid content at all (home_section, so far the only one - see
        # its own TYPE comment, home.py) unconditionally force 'recommended' - 'library' is
        # permanently empty there regardless of anything persisted (see openSection()'s identical
        # check for the in-place-swap case, and its own longer comment for why this can't just be
        # left to whatever was last saved). An explicit content_mode kwarg (no current caller
        # passes one, but the parameter's existed since before this) wins next - a caller with a
        # specific reason to land on a particular tab should get it, not the user's last choice.
        # Otherwise, restore this section's own persisted choice (item 0's own "sticky per-section,
        # same as sort/filter/item-type" design point, not built until now) - falling back to
        # Recommended if this section has never had a tab choice saved yet (the user's choice,
        # 2026-09-25; Playlists keeps its grid - see openSection()).
        if self.section and self.section.TYPE == 'mixed':
            self.contentMode = 'recommended'
        elif kwargs.get('content_mode'):
            self.contentMode = kwargs['content_mode']
        elif self.section and self.section.TYPE == 'playlists':
            self.contentMode = 'library'
        elif self.filter:
            # filtered by a genre etc.: the whole library, as in openSection()
            self.contentMode = 'library'
        else:
            self.contentMode = self.librarySettings.getContentMode() or 'recommended'

        # Session-lifecycle surface (quiet-orbiting-heron.md's Cold Start + windowutils.HOME
        # migration plan) - ported from HomeWindow, which owns all of this today. closeOption is
        # read by main.py's outer loop once this window's session ends (quit/exit/restart/update/
        # recompile/sign-out/switch/etc. - see shutdown()/closeWRecompileTpls() below for the
        # methods that set it). _shuttingDown is read directly, unguarded, by player.py's
        # playQueueCallback() - must exist before anything else can run, not just before
        # shutdown() is ever called.
        # go_root/_goRootAwaitFocus are consumed by onReInit()/routeAction()/routeFocus() below - see
        # those for the full mechanism, ported from HomeWindow's own go_root handling.
        self.closeOption = None
        self._shuttingDown = False
        self.go_root = False
        self._goRootAwaitFocus = None
        self._goRootAwaitUntil = 0
        # One-shot: onFirstInit() below clears the cold-start busy spinner (background.setBusy())
        # the moment the first real content is confirmed showing, same timing main.py's old
        # create()+waitForOpen() two-step gave HomeWindow - but only once, not on every later
        # section/tab swap's own onFirstInit() re-entry (self._openBaseWinID stays set for this
        # instance's whole life, this flag doesn't).
        self._coldStartSignaled = False
        # Reentrancy guard for the exit-confirmation dialog (routeAction()'s NAV_BACK handling,
        # confirmExit() below) - ported from HomeWindow's identical guard (home.py).
        self._checkingForExit = False

        self.reset()

        # Reentrant: serverRefresh() holds it while it calls openSection(), which takes it to
        # invalidate the list (_listGeneration).
        self.lock = threading.RLock()

        # The hub engine's settings (HubsMixin, library_hubs.py): loadHubSettings() fills
        # hubSettings on every swap into the Recommended view (onFirstInit()), and sectionHubs
        # caches each section's fetched hubs. Initial values as HomeWindow.__init__'s, which they
        # were ported from (quiet-orbiting-heron.md, Recommended-tab sharing).
        self.hubSettings = None
        self.sectionHubs = {}

        # Stage 3 (section-item context menu + Manage Hubs dialog): navSettings holds the same
        # per-section show/hide/pin/order preferences buildSectionList() already read as a local,
        # throwaway dict on every call - promoted to real state (loadNavSettings()/
        # saveNavSettings() below) so sectionMenu() can mutate and persist it. Ported from
        # HomeWindow.librarySettings (home.py) under a different attribute name: self.librarySettings
        # is already taken on this window by the per-section LibrarySettings object (sort/filter/
        # content-mode state, see __init__ above) - an unrelated thing despite the name collision
        # with HomeWindow's dict.
        self.navSettings = None
        # Hub catalog for the Manage Hubs dialog - every hub from every section, not just whichever
        # one the user has actually visited (self.sectionHubs only ever holds those). Populated
        # lazily by _discoverHubsSync() the first time Manage Hubs opens, same lazy-discovery path
        # HomeWindow itself falls back to (home.py) - the eager, always-on background
        # DiscoverHubsTask HomeWindow also has isn't ported here: nothing else on this window needs
        # an up-front catalog, so paying for it only when the user actually opens Manage Hubs is
        # narrower and sufficient.
        self.availableHubs = {}
        # All sections (including hidden ones), keyed by str(section.key) - populated alongside
        # availableHubs by _discoverHubsSync(), used only by _ensureCustomConfigExists()'s backfill
        # path to label a hub whose section isn't in availableHubs yet.
        self.allSections = {}
        # Section-reorder ("Move") mode - ported from HomeWindow's identical state (home.py).
        self.movingSection = False
        self._initialMovingSectionPos = None

        # Stage D2 (quiet-orbiting-heron.md): rotation-ring/anchor positioning state, ported
        # from HomeWindow's own __init__ (home.py) - same names, no reason to rename. These are
        # just safe pre-bind defaults, not meaningful positions - _recommendedHubsCallback()
        # resets visibleHubs/focusedHubIndex/_anchorRingPos on every fresh bind anyway, matching
        # HomeWindow._bindAllHubSlots()'s own behavior. _anchorRingPos can't be seeded from
        # HUB_ROTATION_RING.index(self.HUB_CONTROL_ID) here the way HomeWindow's own __init__
        # does it - self.HUB_CONTROL_ID only resolves via MultiWindow.__getattr__ delegation to
        # whichever concrete window self._current currently is, and self._current is still None
        # this early in construction - so 0 is just a placeholder, always overwritten before
        # it's ever read for real.
        self.visibleHubs = []
        self.focusedHubIndex = 0
        self._anchorRingPos = 0
        # The hub slide in progress (library_hubs.HubSlide), or None.
        self._hubSlide = None
        # Built once per LibraryWindow lifetime, then rebound via newControl() on every later
        # 'recommended' entry - see onFirstInit()'s own comment for why (a fresh discard-and-
        # recreate every entry, the original shape here, is the one remaining structural
        # difference from self.tabList/self.sectionList's proven-safe repeated-newControl()
        # pattern - live-confirmed 20+ plain section-to-section swaps clean, only 'recommended'
        # entries ever crash).
        self.hubControls = None

        # Plan item 10, Group A (quiet-orbiting-heron.md): reselect-position memory. Ported from
        # HomeWindow._hubReselectPositions (home.py) - same name/shape (identifier -> (ratingKey,
        # pos)). Scoped to one visit: cleared on every fresh entry (openSection()/switchTab() with
        # fresh=True - a sidebar click, tab switch, go-root or server change) and by the Home
        # rule's in-place reset (_resetHubsToTop()), kept only through popBack() and
        # swapToSection(). Within a visit it keeps a row's position when the row rotates off the
        # ring and back, and lets Back from a hosted screen land on the right item
        # (_captureRootRestoreState() only records which row).
        self._hubReselectPositions = {}

        # Plan item 0 (quiet-orbiting-heron.md): the section-tabs row (Library/Recommended).
        # Built once per LibraryWindow lifetime in onFirstInit() (same pattern as
        # self.sectionList) - the underlying native control gets torn down/rebuilt on every
        # content-mode swap, but the ManagedControlList/its items persist across that via
        # newControl(), same as the sidebar's own list does.
        self.tabList = None
        # Which flavor of tabList's 2 items is currently built - Recommended/Library normally,
        # or Music/Video for the Playlists section (which has no real hub content for a
        # Recommended tab, and no separate Library-tab concept since it's grid-only always).
        # Unlike the sectionList/tabList "build once, rebind forever" pattern this otherwise
        # follows, this one genuinely needs full content swapped out - tracked here so
        # onFirstInit() knows to call buildTabList() again (not just newControl()) exactly when
        # a section swap crosses the playlists/non-playlists boundary.
        self._tabListIsPlaylists = False
        # Same idea, second independent boundary: whether the Categories tab should be present
        # (section.TYPE in ('movie', 'show') only) - see onFirstInit()'s own comment.
        self._tabListHasCategories = False
        # Third independent boundary: whether the Collections tab should be present - gated on
        # section.TYPE in ('movie', 'show', 'artist') (same types the item-type dropdown used to
        # offer 'collection' for) AND an actual existence probe (_sectionHasCollections()), unlike
        # Categories which never checks genre existence.
        self._tabListHasCollections = False
        # Fourth: which playlist types the Playlists section's tabs are for - only those the
        # server has (_playlistTypes()).
        self._tabListPlaylistTypes = ()

        # Stage 3 (quiet-orbiting-heron.md's Cold Start plan): user-options dropdown (control 250,
        # includes/sidebar_dropdowns.xml.tpl - shared, generic markup, already wired into every
        # content-mode template). Built once per LibraryWindow lifetime in onFirstInit(), same
        # pattern as self.sectionList/self.tabList above.
        self.userList = None

        # Stage 3: server-switch dropdown (control 260, same shared include). Same
        # build-once-in-onFirstInit() pattern as self.userList above. changingServer mirrors
        # HomeWindow's identical flag (home.py) - selectServer()/onSelectedServerChange() below
        # use it to suppress the normal back-navigation/exit-confirm handling mid-switch.
        self.serverList = None
        self.changingServer = False

    def onColdStart(self):
        """Called once, only when this construction is the app's top-level, session-owning window
        (MultiWindow.open()'s base_win_id contract - see main.py's cold-start call, Stage 2 of
        quiet-orbiting-heron.md's Cold Start plan). Mirrors HomeWindow.__init__'s own identical
        self-registration (home.py) - other modules resolve this window via windowutils.HOME
        (main.py, monitor.py, player.py, mixins/tasks.py, kodigui.py's recompile-recovery path,
        windowutils.py's own GoHomeMixin/shutdownHome()). Deliberately NOT done unconditionally in
        __init__: opener.handleOpen()'s ordinary sidebar-navigation path constructs/discards many
        short-lived LibraryWindow instances per session (entering any library section from
        outside), and stomping the real singleton on every one of those would break every other
        module's windowutils.HOME reference the moment the user left the section again.
        """
        windowutils.HOME = self

    def squareViews(self):
        """The view map for a square-tiled section: the music one, or the shared default."""
        return VIEWS_SQUARE_MUSIC if self.section.TYPE == 'artist' else VIEWS_SQUARE

    @property
    def itemType(self):
        """This section's current item type (LibrarySettings.itemType); None before the first
        section loads, and on Home, which has none."""
        settings = self.__dict__.get('librarySettings')
        return settings.itemType if settings is not None else None

    def forcedViewWindow(self):
        """The window class this section/item-type combination is pinned to, or None to honour
        the stored viewtype setting.

        Only music sections pin anything (MUSIC_VIEWTYPE_BY_ITEM_TYPE) - Photos and Playlists
        keep their grid/list toggle. ITEM_TYPE can still be unset the first time a section is
        opened, hence the section-type fallback, which resolves to 'artist' (the grid) for music.
        """
        if self.section.TYPE != 'artist':
            return None

        viewtype = MUSIC_VIEWTYPE_BY_ITEM_TYPE.get(self.itemType or self.section.TYPE)
        return self.squareViews().get(viewtype) if viewtype else None

    def reset(self):
        PlaybackBtnMixin.reset(self)
        util.setGlobalProperty('sort', '')
        util.setGlobalProperty('sort.alpha', '')

        if self.section.TYPE == 'playlists' and self.itemType not in ('audio', 'video'):
            # LibrarySettings._loadSettings() only corrects ITEM_TYPE from persisted state - on a
            # genuine first-ever visit (nothing persisted yet) it falls back to the bare module
            # global, which is whatever the *previously* open section (e.g.
            # 'movie'/'collection') left it at. fillPlaylists() filters by playlistType == ITEM_TYPE,
            # so an uncorrected stale value would silently show zero playlists. Corrected here,
            # once, before anything below reads ITEM_TYPE - setItemType() persists it too, so this
            # only ever fires on that first visit. Ported from the Sidebar-Tab-Unification branch's
            # identical fix (commit f0e6340f).
            self.librarySettings.setItemType('audio')

        # Active boolean filters as {filter_key: True}. Start clean on upgrade: old
        # filter.unwatched/filter.hdr/filter.dovi keys are intentionally not read.
        self.boolFilters = self.librarySettings.getSetting('filter.bools', {}) or {}
        self.filter = self.filter or self.librarySettings.getSetting('filter', None)
        self.sort = self.librarySettings.getSetting('sort', self.section.DEFAULT_SORT)
        self.sort = LEGACY_SORT_KEYS.get(self.sort, self.sort)
        self.sortDesc = self.librarySettings.getSetting('sort.desc', self.section.DEFAULT_SORT_DESC)

        self.alreadyFetchedChunkList = set()
        self.finalChunkPosition = 0

        if self.section.TYPE == 'movies_shows':
            self.CHUNK_SIZE = min(100, util.addonSettings.libraryChunkSize)
        else:
            self.CHUNK_SIZE = util.addonSettings.libraryChunkSize

        key = self.section.key
        if not key or not key.isdigit():
            key = self.section.getLibrarySectionId()
        viewtype = util.getSetting('viewtype.{0}.{1}'.format(self.section.server.uuid, key))

        if self.contentMode == 'recommended':
            self.setWindows(VIEWS_RECOMMENDED.get('all'))
            self.setDefault(VIEWS_RECOMMENDED.get('panel'))
        elif self.section.TYPE in ('artist', 'photo', 'photodirectory', 'playlists'):
            # Both classes stay available either way - the pin only decides which one starts,
            # and _applyItemTypeChoice() below still has to be able to swap between them when
            # the item type changes.
            views = self.squareViews()
            self.setWindows(views.get('all'))
            self.setDefault(self.forcedViewWindow() or views.get(viewtype))
        else:
            self.setWindows(VIEWS_POSTER.get('all'))
            self.setDefault(VIEWS_POSTER.get(viewtype))

    @staticmethod
    def _isRealShell(cls):
        """True for the seven real descendant shell types (PrePlayWindow, EpisodesWindow, ...) -
        full, independent windows with their own onClick/onFocus/onFirstInit/onAction. False for
        LibraryWindow's own thin view-type children (PostersWindow etc.), which carry
        MULTI_WINDOW_ID and no real handlers of their own - confirmed via grep, none of the seven
        shells define this attribute. See _setupCurrent()'s bifurcation below."""
        return not hasattr(cls, 'MULTI_WINDOW_ID')

    def _setupCurrent(self, cls):
        # Swap logging, kept from the hosted-screen crash investigation (hashed-orbiting-pizza.md):
        # with the lines below and in openSection() and MultiWindow._open(), it places a native
        # crash within a swap from the log alone. One on 2026-09-28 is still unexplained (the
        # navigation review's follow-ups).
        util.DEBUG_LOG("Library: _setupCurrent({0}) real_shell_count={1} isHostedShell(before)={2}",
                        cls, getattr(self, '_realShellHostCount', 0), self._isHostedShell)

        # The sidebar lists' native controls belong to the outgoing window (_sidebarListGuard())
        self._closeSidebarGuard()

        # Hosted shells reach the host only through weak references (_hostRef, _chainHost -
        # windowutils.UtilMixin; I8 in the navigation review routes their input by name through
        # them). They used to hold it strongly (_chainHost, plus the host's bound
        # onAction/onFirstInit patched onto them), a reference cycle with self._current that
        # refcounting alone can't free, so an outgoing shell could outlive its swap until
        # Python's cyclic GC happened to run. That was the suspected cause of a native crash in
        # the hosted-screen investigation (hashed-orbiting-pizza.md): the same faulting
        # instruction and address - a "not-found sentinel used as a pointer" read at
        # 0xFFFFFFFFFFFFFFFF - across 5 captures, only after a real shell had been hosted more
        # than once before a section switch, on the theory that Kodi reuses the outgoing window's
        # ID for the next one. Never proven, and not seen since the cycle went. The forced
        # gc.collect() and 0.15 s sleep that used to follow every real-shell teardown
        # (_forceCollectOutgoing()) are gone too: the step 4 baseline on the AM6B
        # (2026-09-26) timed them at 260-430 ms of every Back, and without them Back to
        # Recommended went from ~600 to ~250 ms to first init, with no freeze or crash in a
        # rapid-Back stress run. Python's automatic gc still collects the cycles
        # (plexobjects' item<->container), on its own schedule.
        #
        # _chainHost is still cleared on the outgoing shell: a call already in flight on another
        # thread from before this swap must find no chain host (_liveChainHost() -> None), not act
        # on the host's new current window. Its input needs no clearing - hostedBy() drops a late
        # callback on a window that's no longer current.
        #
        # Its native window is closed here too, while it's still Kodi's active window and before
        # the next one is shown. doClose() only flags it, and closing used to be left to a forced
        # collection disposing it - which only happens if nothing else still references
        # it. Tasks still running for it after Tasks.kill() stopped joining the workers do (e.g.
        # its watchlist checks), and live-caught 2026-09-24: Back on an Episodes screen still
        # loading swapped to Home, then Kodi re-activated the old Episodes window over it
        # (its onReInit() ran after Home's onFirstInit()), where every input was dropped as
        # coming from a window that's no longer current - the addon looked frozen.
        outgoingShell = self._current
        outgoingWasRealShell = outgoingShell is not None and getattr(outgoingShell, '_chainHost', None) is not None
        if outgoingWasRealShell:
            outgoingShell._chainHost = None
            util.DEBUG_LOG("Library: _setupCurrent() closing outgoing {0}'s native window", outgoingShell)
            dismissStarted = time.time()
            outgoingShell.forceDismiss()
            timing = self.__dict__.get('_swapTiming')
            if timing is not None:
                timing.add('native close', (time.time() - dismissStarted) * 1000)
        del outgoingShell

        if not self._isRealShell(cls):
            self._isHostedShell = False
            kodigui.MultiWindow._setupCurrent(self, cls)
            if issubclass(cls, RecommendedWindow):
                self._hideStaleHero()
            util.DEBUG_LOG("Library: _setupCurrent({0}) thin-proxy branch complete", cls)
            return

        self._realShellHostCount = getattr(self, '_realShellHostCount', 0) + 1
        self._isHostedShell = True
        # The grid or Recommended view this may be replacing is gone once _current moves on, but
        # swapTo() changes neither section nor tab, so nothing else told in-flight list work it's
        # stale. Live-caught 2026-09-25 (AM6B crash log): a grid chunk fetched just before an item
        # opened from that grid wrote into its freed list items - a segfault in
        # CGUIListItem::SetProperty on the worker. See _retireListItems().
        self._retireListItems()
        self._current = cls(cls.xmlFile, cls.path, cls.theme, cls.res, **self._nextKwargs)
        self._currentKwargs = self._nextKwargs
        # Both weak (see the top of this method): _hostRef routes the shell's routeAction() through
        # routeAction() (kodigui.BaseWindow.routeActionToHost()), _chainHost is what its
        # navigation calls (openWindow(), goHome(), ...) find as the chain's host.
        self._current._hostRef = weakref.ref(self)
        self._current._chainHost = self
        # Phase 2 (hashed-orbiting-pizza.md): hand the host's own sectionList object to the
        # shell - its onFirstInit() sees a non-None sectionList and rebinds via newControl()
        # instead of rebuilding, so is.active (and everything else about which section is
        # highlighted) carries over untouched for the whole chain. self is always the host here
        # (never a shell), and the host's own sectionList is never rebuilt across its own swaps,
        # so this is the same single object handed to every shell in the chain, forward or
        # backward (popBack() reconstructs via this same method).
        self._current.sectionList = self.sectionList

        # The host's close.windows handler, which base MultiWindow._onFirstInit() registers for its
        # own views. Registration is idempotent (SignalsMixin.on()), and the host has normally
        # been registered since its first view anyway. Deliberately NOT the rest of
        # _onFirstInit(): LibraryWindow.onFirstInit() is real logic keyed to LibraryWindow's own
        # templates (sectionList/tabList/userList/serverList, POSTERS_PANEL_ID focus) and would
        # run broken against a real shell's native window (e.g. PrePlayWindow's XML has none of
        # those controls). Nor does the shell get self._properties replayed onto it the way a
        # thin view does. Live-confirmed bug without that exclusion: self._properties accumulates
        # whatever LibraryWindow's own 'recommended'-mode hero display last set via
        # updateHeroFrom()/setHeroInfo() (clear.logo/summary/etc. for the focused hub item) and
        # nothing overwrites those specific keys again once the user is just browsing an
        # ordinary grid - so they sit frozen at whatever hub item was focused when Home's hubs
        # first drew this session. A real shell like PrePlayWindow happens to use the same
        # property names for its own, unrelated metadata panel, so replaying the host's cache
        # briefly showed that frozen, unrelated content until the shell's own setInfo()
        # overwrote it. A real shell has its own independent metadata logic; it was never meant
        # to inherit the host's display-state cache the way a thin view is.
        plexapp.util.APP.on('close.windows', self.onCloseSignal)

        # onFocus/onReInit aren't routed through the host for real shells - unlike LibraryWindow's
        # own thin view-type children (kodigui.MultiWindowView), these carry real business logic
        # of their own. Their onAction() calls routeActionToHost() first, and their onClick()
        # routeClickToHost(), which hands the sidebar's clicks to routeClick().
        # Swap logging - see this method's first log line.
        util.DEBUG_LOG("Library: _setupCurrent({0}) real-shell branch complete, real_shell_count={1}",
                        cls, self._realShellHostCount)

    def _hideStaleHero(self):
        """Called on a fresh Recommended view before it's shown. Its hero (clear logo, title,
        summary, art) otherwise shows the last Recommended visit's item until the first row binds:
        Kodi reuses window ids and a new window starts with the properties the id last held, then
        _onFirstInit() replays the host's cached string properties, hero ones included, and
        onFirstInit()'s own no_hero_art hide only lands after both (live-reported 2026-09-24,
        more visible on the AM6B). no_hero_art hides the overlay and the art box until the first
        bind clears it - the hide onFirstInit() already applies, just in time. (Compared live
        against hiding only the text, via a blank title; hiding both was the one kept.)

        Written with xbmcgui.WindowXML.setProperty() directly, not the view's setProperty():
        before a window is shown, BaseWindow.setProperty() takes Kodi's current window id - the
        outgoing view's - as its own _winID and writes there (live: a section change raised
        "Window id does not exist" for the already-disposed outgoing view, so the hide never
        applied). Bool properties aren't in the host's replay cache (setBoolProperty() resolves to
        the view), so nothing overwrites this before the bind."""
        util.DEBUG_LOG("Library: hiding the stale hero before show")
        xbmcgui.WindowXML.setProperty(self._current, 'no_hero_art', '1')

    def _retireListItems(self):
        """Mark the list items in-flight work is writing into as stale (_listGeneration), and wait
        for the one item being written right now. Call before anything that frees them: a view
        swap, a section or tab switch, a grid rebuild.

        Live-caught 2026-09-25 (AM6B crash logs): a grid chunk still being written when the view
        was replaced - an item opened from the grid, then a sidebar switch from a loading Music
        grid - segfaulted in CGUIListItem::SetProperty on the worker. _chunkCallback() checks the
        generation before every item, under self.lock, so bumping first and then taking the lock
        waits for at most one item. Taking the lock first waited for the whole chunk, up to a
        second on the AM6B."""
        self._listGeneration += 1
        with self.lock:
            pass

    def _captureRootRestoreState(self):
        """Extra entries merged into the (None, {...}) root-restore _backStack entry (swapTo()/
        swapToSection() below), so popBack() can land back on whichever grid item or hub row was
        actually focused the moment a chain started, instead of always resetting to item 0 / the
        first hub - live-reported as jarring on a large grid or a hub row entered partway down.
        Best-effort: an empty dict is a safe no-op for popBack() (falls back to its existing
        default-position behavior), used whenever nothing focused is identifiable (e.g. an empty
        section, or hub focus not settled on a real hub yet).

        Deliberately keys off self.contentMode, not which control currently has native focus -
        this only ever runs while self is genuinely showing its own grid/hubs (the "not
        _isHostedShell" branch in both callers), so contentMode alone is enough to know which of
        the two restore shapes applies; no need to inspect self.getFocusId()."""
        if self.contentMode == 'recommended':
            index = self.focusedHubIndex
            # The row an item was just opened from, when the click landed on the row a slide was
            # leaving (hubItemClicked()) - only while focus hasn't moved since.
            opened = self.__dict__.pop('_openedFromHub', None)
            if opened is not None and opened[0] == index:
                index = opened[1]
            if self.visibleHubs and 0 <= index < len(self.visibleHubs):
                hub = self.visibleHubs[index]
                identifier = hub.getCleanHubIdentifier(is_home=self.section.key is None)
                return {'_restoreHubId': identifier}
            return {}
        if self.showPanelControl:
            mli = self.showPanelControl.getSelectedItem()
            if mli:
                return {'_restoreItemPos': mli.pos()}
        return {}

    def _captureHostedShellRestoreState(self):
        """Extra entries merged into the (ShellClass, kwargs) hosted-shell _backStack entry
        (swapTo()/swapToSection() below), so popBack() can restore focus within a hosted shell's
        own grid too, not just LibraryWindow's own (_captureRootRestoreState()) - live-reported as
        never restored at all for collection.py's CollectionWindow/SubDirWindow, the two hosted
        shells with their own grid concept.

        Deliberately scoped to collection.BoundedGridWindow only - the seven real shells are
        otherwise too structurally different from each other (PrePlayWindow/EpisodesWindow/
        ShowWindow/ArtistWindow/GenreBrowserWindow each have their own, unrelated internal
        state/control shape) to share one generic restore mechanism; out of scope here.

        Captures the item's *absolute* position in the full list, not its raw control-relative
        index - BoundedGridPaginator's sliding-window model (pagination.py) only ever materializes
        a page of items around the current offset, so a control-relative index means nothing once
        reconstructed fresh later. Control index 0 is a left-boundary sentinel, not a real item,
        whenever this page doesn't start at the real beginning of the list (offset > 0) - skipped
        via the same "-1" shift collection.py's own jumpToPosition() uses in reverse.
        _selectInitialItem() (collection.py) is what actually consumes this - it can select
        directly within the freshly (re)loaded initial page for a small absolute position, or
        re-fetch the right page via BoundedGridPaginator.jumpToPosition() for one beyond it; falls
        back to the shell's own existing item-0 default only if neither applies (e.g. the position
        no longer exists at all)."""
        current = self._current
        if (isinstance(current, collection.BoundedGridWindow) and current.paginator is not None
                and current.gridControl):
            mli = current.gridControl.getSelectedItem()
            if mli and not mli.getProperty('is.boundary'):
                relative = mli.pos()
                offset = current.paginator.offset
                if offset > 0:
                    relative -= 1
                return {'_restoreItemPos': offset + relative}
        return {}

    def swapTo(self, cls, push=True, chain_root=None, **kwargs):
        """Swap this already-open, already-hosting LibraryWindow to one of the seven real
        descendant shell types in place - same construct-fresh-via-_open()'s-loop pattern
        openSection()/switchTab() already use, just targeting a real shell class instead of one
        of LibraryWindow's own thin view-type proxies. See _backStack's own comment (__init__)
        for the two entry shapes pushed here.

        chain_root: a section that replaces the whole chain as the only way back, instead of
        pushing the current screen - post-play's opens (videoplayer.play()), so Back from what
        they open lands on that section's own view. If the chain started from that same section,
        unfiltered, it collapses to that start, so Back finds the section as it was left (row or
        grid position, and each row's item); otherwise the section opens fresh, like a sidebar
        click, and the old chain's remembered hub positions are dropped."""
        if chain_root is not None:
            root = self._chainRootEntry()
            rootKwargs = root[1] if root else {}
            section = rootKwargs.get('section')
            if (section is not None and not rootKwargs.get('filter_')
                    and getattr(section, 'key', None) == chain_root.key):
                self._backStack = [root]
            else:
                self._backStack = [(None, {'section': chain_root, 'filter_': None})]
                self._hubReselectPositions = {}
                # The sidebar marks the section Back now goes to, not the one playback started
                # from (F4 in the navigation review).
                self.updateActiveSectionMarker(chain_root)
        elif push and self._current is not None:
            if self._isHostedShell:
                entryKwargs = dict(self._currentKwargs)
                entryKwargs.update(self._captureHostedShellRestoreState())
                self._backStack.append((self._current.__class__, entryKwargs))
            else:
                # Genesis swap out of LibraryWindow's own grid: push root-restore state so the
                # *last* pop of this chain reveals the grid again instead of running off the
                # stack - this is what makes _backStack empty mean "never started a chain"
                # unambiguously, every time.
                entryKwargs = {'section': self.section, 'filter_': self.filter}
                entryKwargs.update(self._captureRootRestoreState())
                self._backStack.append((None, entryKwargs))
        self._next = cls
        self._nextKwargs = kwargs
        self._current.doClose()

    def viewClosed(self, view):
        """MultiWindow's hook, as each view's modal() returns. A hosted screen whose setup found its
        item gone (deleted, or the server unreachable) closes itself with navintent.noData() as its
        exitCommand. Nothing had asked for another screen, so _open() would set the same one up
        again, from the same _next and kwargs, and it would fail the same way. Go back instead, as
        Back would, with the notice the hub menu's opens show."""
        if self._allClosed or not self._isHostedShell \
                or not navintent.isNoData(getattr(view, 'exitCommand', None)):
            return
        util.DEBUG_LOG("Library: {0} couldn't load its item, going back", type(view).__name__)
        self._goBackFromFailedScreen()

    def viewFailed(self, error):
        """MultiWindow's hook: a hosted screen raised as it was constructed (_setupCurrent()), before
        it was ever shown - Episodes loads its show there. Go back as viewClosed() does."""
        if self._allClosed or not self._isHostedShell:
            return False
        util.DEBUG_LOG("Library: {0} couldn't load its item, going back", self._next)
        self._goBackFromFailedScreen()
        return True

    def _goBackFromFailedScreen(self):
        util.ERROR("No data - deleted or server disconnected?", notify=True, time_ms=5000)
        if self._backStack:
            self.popBack(view_gone=True)
        else:
            self.openSection(self.section, force=True, fresh=False, view_gone=True)

    def _chainRootEntry(self):
        """The root-restore entry this chain would unwind to: the stack's first entry, or - with
        no chain yet, the host showing its own section - the one a genesis swap would push now."""
        if self._backStack:
            entry = self._backStack[0]
            return entry if entry[0] is None else None
        if self._current is not None and not self._isHostedShell:
            entryKwargs = {'section': self.section, 'filter_': self.filter}
            entryKwargs.update(self._captureRootRestoreState())
            return None, entryKwargs
        return None

    def _popBackIfChained(self):
        """A posted Back (routeAction()): the chain can have emptied since it was posted - a
        section switch, or an earlier Back that was the last one - so check at run time."""
        if self._backStack:
            self.popBack()
        else:
            util.DEBUG_LOG("Library: posted Back found no chain left, ignored")

    def popBack(self, view_gone=False):
        """view_gone: the current view has already closed (viewClosed()), so openSection() mustn't
        decline for it not being Kodi's current window."""
        entry = self._backStack.pop()
        cls, kwargs = entry
        if cls is None:
            # _restoreItemPos/_restoreHubId (_captureRootRestoreState()) aren't real
            # openSection() kwargs - peel them off into the pending-restore attributes fillShows()/
            # fillPlaylists()/_recommendedHubsCallback() each consume one-shot, whichever one this
            # section's contentMode actually lands on.
            kwargs = dict(kwargs)
            self._pendingRestoreItemPos = kwargs.pop('_restoreItemPos', None)
            self._pendingRestoreHubId = kwargs.pop('_restoreHubId', None)
            # force=True: section == self.section will be true here (root state is never
            # mutated while a shell is hosted), which openSection()'s own no-op guard would
            # otherwise decline.
            if view_gone:
                kwargs['view_gone'] = True
            if not self.openSection(force=True, fresh=False, **kwargs):
                # Declined - the current view isn't Kodi's current window yet (Back pressed as a
                # screen was still opening; its _winID is only set once its onInit() runs). Keep
                # the entry, so the chain is intact for the next Back: live-caught 2026-09-24,
                # losing it left an Episodes screen with an empty chain, where the next Back
                # offered to exit the addon.
                self._pendingRestoreItemPos = None
                self._pendingRestoreHubId = None
                self._backStack.append(entry)
        else:
            self.swapTo(cls, push=False, **kwargs)

    def swapToSection(self, section, filter_=None):
        """hashed-orbiting-pizza.md Phase 4 item 8: genre/director/actor-tag filtered browsing
        (opener.sectionClicked()/genreClicked(), clicked from a hosted shell's own "go to
        section" option) reuses this LibraryWindow's own section-rendering in place, instead of
        opener.handleOpen() opening a second nested LibraryWindow. Not swapTo(cls, ...) - there's
        no new shell class involved, just different section/filter content on the same host, so
        openSection() (the same in-place swap sidebar clicks already use) does the actual work.
        Not the goHome(section=...) bubble either - that unwinds by closing, which would destroy
        whatever chain (e.g. a hosted PrePlayWindow) this was clicked from, instead of preserving
        it for Back to return to.

        openSection() unconditionally clears _backStack before returning - correct for its own
        ordinary callers (an explicit sidebar click really should abandon any chain in progress,
        see its own comment), wrong here, where the whole point is to preserve the chain. Capture
        the entry first (same two shapes swapTo() itself pushes) and re-append it after.

        Bug fixed here: the entry alone isn't enough - whatever was ALREADY on _backStack before
        this call (e.g. the root-restore entry pushed when a chain first entered a hosted shell)
        needs preserving too, not just the one entry for returning to *this* call's own shell.
        Without capturing the whole preceding stack, a second swapToSection() deeper in the same
        chain (e.g. genres.py's GenreBrowserWindow: enter Categories, click a genre, then Back
        twice) would only ever remember one hop back - the second Back would find an empty stack
        and fall through to ordinary NAV_BACK handling instead of unwinding the rest of the chain.
        """
        precedingBackStack = self._backStack
        if self._isHostedShell:
            entryKwargs = dict(self._currentKwargs)
            entryKwargs.update(self._captureHostedShellRestoreState())
            entry = (self._current.__class__, entryKwargs)
        else:
            entryKwargs = {'section': self.section, 'filter_': self.filter}
            entryKwargs.update(self._captureRootRestoreState())
            entry = (None, entryKwargs)
        # Only when the swap happened: a declined openSection() leaves _backStack as it was, and
        # appending anyway would make Back "return" to the screen still showing.
        if self.openSection(section, filter_=filter_, force=True, fresh=False):
            self._backStack = precedingBackStack + [entry]

    def switchTab(self, mode, item_type=None):
        """Swap this already-open window between content modes ('library' grid vs.
        'recommended' hubs) in place, the same construct-fresh-via-_open()'s-loop pattern
        openSection() already uses for section swaps - see that method's own docstring for why
        in-place mutation, not a fresh object, is the safe shape here.

        Also reached (mode always 'library'/'recommended', never 'categories') when leaving the
        Categories tab (genres.py's GenreBrowserWindow, hosted via browseGenres()'s swapTo()) back
        to an ordinary tab - self.contentMode is deliberately never mutated to 'categories' (see
        browseGenres()/tabListClicked()), so it still holds whatever content mode
        was active before Categories was entered.

        item_type: optional - the Collections tab isn't a real contentMode either (like
        Categories, it stays 'library'), so escaping it (a Library-tab click, from this window's
        own onClick() or genres.py's delegation) needs to explicitly reset ITEM_TYPE back to this
        section's own native type, not just leave it stuck on 'collection'. None (every other
        caller) leaves ITEM_TYPE untouched, exactly today's behavior. switchToCollections() is the
        entry point for the opposite direction (switching *to* 'collection'), calling this
        directly with item_type='collection' only when a real contentMode swap is needed too (i.e.
        starting from 'recommended' or a hosted shell) - see its own docstring.
        """
        try:
            isCurrent = self.is_current_window
        except AttributeError:
            isCurrent = False

        if not isCurrent:
            util.DEBUG_LOG("Library: switchTab() declined - {0} not current window (descendant open, or closing)", self)
            return False

        itemTypeChanging = item_type is not None and item_type != self.itemType

        # self._isHostedShell: a real shell (Categories) can be fronting the *same* contentMode
        # string the user is now clicking - e.g. they left from 'library', contentMode is still
        # 'library', and they click the Library tab from inside Categories to return. A bare
        # `mode == self.contentMode` would wrongly treat that as a no-op and leave Categories
        # showing. itemTypeChanging is the same idea for Collections, which doesn't front a
        # different contentMode at all - without it, Library-tab-from-Collections (contentMode
        # stays 'library' throughout) would wrongly no-op too.
        if mode == self.contentMode and not self._isHostedShell and not itemTypeChanging:
            return False

        self.tasks.kill()
        # Land any hub slide in progress (_startHubSlide()) while its view is still there, before
        # doClose() below tears the native window down. It used to run on its own thread, which
        # could still be mid-setPosition() on a control about to stop existing (live-confirmed as a
        # native invalid-pointer-read crash); it steps on this thread now, so this just lands it.
        # A no-op when no slide is running.
        self._settleHubSlide()
        self._retireListItems()
        # A tab switch is a fresh entry - see _hubReselectPositions' own comment (__init__).
        self._hubReselectPositions = {}
        self.contentMode = mode
        if item_type is not None:
            self.librarySettings.setItemType(item_type)
        # An explicit tab click is exactly the case that should abandon any chain in progress -
        # same reasoning openSection() already documents for itself (sidebar clicks). Without
        # this, leaving Categories via a direct tab click (rather than Back/popBack()) would leave
        # its root-restore back-stack entry stale, to be wrongly popped by some later, unrelated
        # NAV_BACK.
        self._backStack = []
        # Persist per-section, same "sticky" treatment sort/filter/item-type already get - see
        # LibrarySettings.getContentMode()'s own docstring. Unconditional even for a TYPE=='mixed'
        # section (home_section) switching to 'library' (permanently empty there) - harmless to
        # save, since openSection()'s own TYPE=='mixed' check always forces 'recommended' back on
        # next entry regardless of what's persisted, never actually reads this value for such a
        # section.
        self.librarySettings.setContentMode(mode)
        self.reset()
        self.refill = True

        util.DEBUG_LOG("Library: switchTab() swapping in place to {0}", mode)
        self._current.doClose()
        return True

    def _libraryTabItemType(self):
        """Item type to request when the Library tab is clicked, from anywhere (this window's own
        onClick(), or a hosted Categories shell delegating back via genres.py) - resets away from
        'collection' back to this section's own native type (movie/show/artist are all valid
        ITEM_TYPE values for their own section, same values the item-type dropdown used to offer
        directly) if that's where Collections left ITEM_TYPE, otherwise None so switchTab() leaves
        whatever finer-grained choice (e.g. 'folder' for movies, 'episode' for shows) untouched."""
        return self.section.TYPE if self.itemType == 'collection' else None

    def switchToCollections(self):
        """Collections tab (buildTabList()): an ITEM_TYPE='collection' selection presented as a
        tab, same shape as Playlists' Music/Video tabs (_applyItemTypeChoice()) - not a real third
        contentMode, the grid still renders through the ordinary 'library' contentMode, just
        filtered to collections.

        Needs its own entry point rather than always calling _applyItemTypeChoice() directly
        because Collections can be reached from the Recommended tab too (or from Categories, a
        hosted shell fronting 'library'), which need a real contentMode swap - persisting the
        item-type choice via switchTab()'s item_type param before that swap is enough; the
        reconstruction naturally re-derives ITEM_TYPE from the now-persisted LibrarySettings value
        (LibrarySettings._loadSettings()), no separate post-reconstruction hook needed. Only when
        already showing the ordinary library grid (contentMode == 'library', not hosting a shell)
        is the cheaper in-place refill (_applyItemTypeChoice(), no window reconstruction) enough -
        keep_focus=False there so this still moves focus onto the grid like the switchTab() branch
        below does natively, rather than _applyItemTypeChoice()'s own default (built for its
        dropdown-result caller, which wants the opposite).
        """
        if self.contentMode == 'library' and not self._isHostedShell:
            self._applyItemTypeChoice('collection', keep_focus=False)
        else:
            self.switchTab('library', item_type='collection')

    def browseGenres(self):
        from . import genres as genres_window
        self.swapTo(genres_window.GenreBrowserWindow, section=self.section)

    def openSection(self, section, filter_=None, force=False, fresh=True, view_gone=False):
        """Swap this already-open window to a different section in place, reusing the same
        outer LibraryWindow object rather than closing and reconstructing a new one - see the
        Home-ControlledWindow plan's "One window, not two" / thread-safety discussion. Safe to
        call from the sidebar debounce thread: this only mutates state and flags the current
        view-type shell closed, the actual reconstruct-and-modal happens back on _open()'s own
        loop, on whichever thread already owns it - never a new blocking .modal() call here.

        Deliberately a no-op if a descendant window (opened via a poster/cast click etc.) is
        currently on top of self: forceDismiss()-style dismissal only reaches self, not anything
        pushed on top of it, so mutating section state here while a child is still holding
        references into it (e.g. ShowWindow's parent_list=self.showPanelControl) would corrupt
        that child's view rather than switch it cleanly. Actually unwinding a drill chain for a
        sidebar-driven section switch is windowutils.py's _dispatchSectionOpen() - any descendant
        (nested LibraryWindow or otherwise) now bubbles via goHome(section=...) instead of ever
        reaching openSection() directly, so this guard shouldn't actually fire via that path any
        more (Home-ControlledWindow plan, item 4) - kept as defense in depth for any other caller
        (e.g. onReInit()'s go_root handling below) that might still race against a not-yet-closed
        descendant.

        force=True skips the "already on this section" no-op below - for serverRefresh() (Stage
        3's server-switch popup): a server switch can leave `section` pointing at the exact same
        Section object (home_section is a shared singleton, and switching servers while already
        on Home is the common case) while the actual content underneath it has completely
        changed. Live-confirmed as a bug without this: the sidebar rebuilt correctly for the new
        server, but the content pane never reloaded, and Home stayed silently stale until the
        user detoured through a different section first (which, being genuinely != self.section,
        did trigger a real reload and incidentally left self.section pointing at the new server's
        data, making Home reachable again from there).

        fresh=True (every caller except popBack() and swapToSection()) opens the section as if for
        the first time: the hub rows' remembered positions (_hubReselectPositions) are cleared.
        Saved per-section preferences (sort, filters, view type, tab) are not navigation state and
        always apply.

        view_gone=True (viewClosed(), via popBack()): the current view closed itself, so it isn't
        Kodi's current window, but nothing is open on top of this window either.
        """
        try:
            isCurrent = view_gone or self.is_current_window
        except AttributeError:
            # _current already torn down for real (session/window closing) - decline the same
            # as a descendant-on-top; nothing here to safely act on either way.
            isCurrent = False

        if not isCurrent:
            util.DEBUG_LOG("Library: openSection() declined - {0} not current window (descendant open, or closing)", self)
            return False

        if not force and section == self.section:
            return False

        self.tasks.kill()
        # Settle any in-flight hub-slide animation before doClose() below - see switchTab()'s
        # identical call for why (this section may currently be showing its own Recommended tab).
        self._settleHubSlide()
        if fresh:
            self._hubReselectPositions = {}
        # Bumped here, not just inside doRefill(), so a suspended call elsewhere that captured
        # showPanelControl/mli.dataSource before this swap can detect the invalidation the moment
        # it actually happens, not only once _open()'s loop gets back around to rebuilding.
        self._retireListItems()

        self.section = section
        # Force a fresh live Collections probe for the section we're now entering, rather than
        # trusting whatever was cached from a previous visit - see _sectionHasCollections()'s own
        # docstring. Harmless no-op for section types that were never eligible for the probe in
        # the first place (nothing to evict).
        _invalidateSectionHasCollectionsCache(section)
        # hashed-orbiting-pizza.md Phase 4: a sidebar section click reaches here even while a
        # descendant chain is hosted (bubbled via PrePlayWindow etc.'s own goHome(section=...),
        # windowutils.py's GoHomeMixin/_dispatchSectionOpen(), landing on this deferred call) -
        # an explicit sidebar click is exactly the case that should abandon any chain in
        # progress, not just leave it dangling. Without this, _backStack keeps whatever
        # root-restore entry the chain pushed on its way in, live-confirmed to cause real
        # breakage on the *next* unrelated NAV_BACK/chain: routeAction()'s NAV_BACK intercept below
        # only checks "is _backStack non-empty," not whether a chain is actually still active, so
        # a stale entry here gets wrongly popped later, jumping back to whatever section this
        # abandoned chain started from instead of behaving like an ordinary section view.
        self._backStack = []
        self.filter = filter_
        self.subDir = None
        self.keyItems = {}
        self.firstOfKeyItems = {}
        self.subOptionCache = {}
        self._filterTypeByKey = {}
        self.lastItem = None
        self._shownKey = None
        self.lastFocusID = None
        self.lastNonOptionsFocusID = None

        # Rebuilt before contentMode is decided below, not after - the new section's own
        # persisted tab choice (getContentMode()) has to come from *this* section's settings, not
        # the outgoing one's.
        self.librarySettings = LibrarySettings(self.section)
        if filter_:
            self.librarySettings.showWholeLibrary()

        if self.section.TYPE == 'mixed':
            # Sections with no library-grid content at all (home_section, so far the only one -
            # see its own TYPE comment, home.py) have nothing to show on the 'library' tab -
            # forcing 'recommended' here, unconditionally, regardless of anything persisted (a
            # user could otherwise land on the permanently-empty grid if they'd last clicked
            # Library while on Home, before ever navigating away and back), is what makes folding
            # home_section into this same in-place swap (rather than goHome()'s separate window)
            # not a regression: without this, landing on Home while contentMode was still
            # 'library' would show an empty grid instead of Home's real hub content. Must run
            # before self.reset() below, which reads self.contentMode to pick VIEWS_RECOMMENDED
            # vs. VIEWS_POSTER/VIEWS_SQUARE - setting it after would use the stale value for this
            # swap's own reset() call.
            self.contentMode = 'recommended'
        elif self.section.TYPE == 'playlists':
            # Playlists has no 'recommended' hub content either (fillPlaylists() is the only
            # fill() path for this TYPE, regardless of contentMode - reset()'s own VIEWS_SQUARE
            # branch is what its Audio/Video ITEM_TYPE tabs actually depend on) - unconditional
            # like the TYPE=='mixed' branch above, for the same reason: the ordinary carry-over
            # logic below would otherwise leave contentMode stuck on 'recommended' whenever this
            # section is entered straight from Home or Watchlist (both of which use 'recommended'
            # themselves), and reset() checks contentMode == 'recommended' *before* it ever looks
            # at self.section.TYPE, so that stale value would load the hub-style Recommended
            # view-shell instead of the squares/tabs one - live-confirmed: no Audio/Video split
            # and a black background (that shell doesn't read 'background' the way the
            # playlists grid used to set it). Arriving from an ordinary library section never
            # hit this, since none of them force contentMode to 'recommended' in the first place.
            self.contentMode = 'library'
        elif filter_:
            # A genre (or director, actor...) clicked through to: the whole library filtered by it,
            # whichever tab the section was last left on - its Collections tab, live, showed the
            # collections in that genre instead. Not saved as the section's tab.
            self.contentMode = 'library'
        else:
            # Ordinary sections (real library-grid content): restore this section's own last tab
            # choice, the same "sticky per-section" treatment sort/filter/item-type already get
            # (LibrarySettings.getItemType() and friends). With none saved, Recommended - not the
            # previous section's tab, which it used to carry over, so a section opened on
            # whichever tab the section before it happened to be on (the user's choice,
            # 2026-09-25).
            self.contentMode = self.librarySettings.getContentMode() or 'recommended'

        self.reset()
        self.refill = True
        self.updateActiveSectionMarker(section)

        # Swap logging - see _setupCurrent()'s first log line.
        util.DEBUG_LOG("Library: openSection() swapping in place to {0}, current={1} next={2} "
                        "isHostedShell={3} real_shell_count={4} backStack_len={5}",
                        section, self._current, self._next, self._isHostedShell,
                        getattr(self, '_realShellHostCount', 0), len(self._backStack))
        self._current.doClose()
        util.DEBUG_LOG("Library: openSection() self._current.doClose() returned")
        return True

    def updateActiveSectionMarker(self, active_section):
        """Update is.active on the persistent sectionList to highlight active_section, without
        rebuilding the whole list - buildSectionList() only sets is.active once, at first build.
        """
        if not self.sectionList:
            return

        for i in range(self.sectionList.size()):
            mli = self.sectionList[i]
            if not mli:
                continue
            if mli.dataSource is not None and mli.dataSource.key == active_section.key:
                mli.setProperty('is.active', '1')
            elif mli.getProperty('is.active'):
                mli.setProperty('is.active', '')

    def sectionByKey(self, key):
        """The sidebar's section object for a library section key, or None. For callers that only
        hold a key (getLibrarySectionId()) - resolveSection() resolves those through here, the
        way HomeWindow's old 'HOME:<key>' handler matched the same list."""
        if not self.sectionList:
            return None
        key = str(key)
        for i in range(self.sectionList.size()):
            mli = self.sectionList[i]
            if mli and mli.dataSource is not None and mli.dataSource.key is not None                     and str(mli.dataSource.key) == key:
                return mli.dataSource
        return None

    def setWatchlistDirty(self, *args, **kwargs):
        if self.section.TYPE == 'movies_shows':
            util.DEBUG_LOG("Library: Watchlist item state changed, setting dirty")
            self.refill = True

    @busy.dialog()
    def doClose(self, **kw):
        self.closing = True
        pnUtil.APP.off("watchlist:modified", self.setWatchlistDirty)
        util.MONITOR.off("library.back_home", self.goHomeRoot)
        self.tasks.kill()
        kodigui.MultiWindow.doClose(self)

    def closeWRecompileTpls(self):
        """Ported from HomeWindow (home.py) - see quiet-orbiting-heron.md's Cold Start plan.
        Reached indirectly for every non-cold-start window via windowutils.HOME.
        closeWRecompileTpls() (kodigui.py's XMLBase.onInit() recompile-recovery path) once this
        window is windowutils.HOME - unlike HomeWindow, LibraryWindow's own inner shells never
        take that code's direct self.closeWRecompileTpls() branch themselves (self there is always
        the concrete inner shell, e.g. RecommendedWindow, never this outer object - confirmed by
        reading XMLBase.onInit(), no separate fix needed on that side).
        """
        self._shuttingDown = True
        self.closeOption = "recompile"
        self.doClose()

    def stopRetryingRequests(self, state=True):
        """Ported from HomeWindow (home.py) - a plain toggle on a global, not a TasksMixin method.
        mixins/tasks.py's TasksMixin.doClose() (used by EpisodesWindow/PrePlayWindow/SubItemsWindow)
        calls windowutils.HOME.stopRetryingRequests() directly - resolves here once this window is
        windowutils.HOME.
        """
        util.DEBUG_LOG("{} request retries", state and "Disabling" or "Enabling")
        plexnet.asyncadapter.STOP_RETRYING_REQUESTS = state

    def shutdown(self):
        """Ported from HomeWindow.shutdown() (home.py) - see quiet-orbiting-heron.md's Cold Start
        plan. unhookSignals() now ported too (Stage 3's server popup). HomeWindow's own version
        also resets its serverList control and calls storeLastBG() (persists the focused hub's
        background art for next cold start) here - storeLastBG() depends on a LibraryWindow-shaped
        equivalent of Home's visibleHubs-based background persistence that doesn't exist yet, and
        the serverList reset isn't needed - this window's own serverList is rebuilt wholesale by
        showServers() on next open, never assumed empty in between the way HomeWindow's is.
        """
        util.DEBUG_LOG("Library: shutdown called")
        self._shuttingDown = True
        self.stopRetryingRequests()
        self.unhookSignals()
        self._closeSidebarGuard()

    def processCommand(self, command):
        """UtilMixin.processCommand() (windowutils.py), for the result of a blocking open. At Home, a
        NavIntent (navintent.py) has arrived, not left: Home took it when it was issued, and closing
        here, as the base class does for every window it passes through, would tear down the whole
        session, since nothing sits underneath this window any more (live-confirmed: the Home
        button from a descendant closed the addon, before this override).

        One exception: a closeSession() intent from a nested library window (Exit chosen inside a
        collection, say) ends the session here, as it arrives, rather than waiting for returnHere()'s
        posted copy: the collection closing would otherwise reveal the library underneath first
        (live-confirmed regression, when closeOption was set on Home before the bubble instead).
        """
        if navintent.isNavIntent(command) and not navintent.isNoData(command) \
                and self is windowutils.HOME:
            # Arrived: Home took the intent when it was issued (GoHomeMixin.leaveFor() ->
            # returnHere()). Only ending the session is still decided here.
            if command.kind == navintent.NavIntent.CLOSE_SESSION:
                self.navigate(command)
            return
        # Any other window: UtilMixin.processCommand() closes this one and passes an intent on, or
        # raises for noData(). It can't recurse through _chainHost pointing at self: it only
        # delegates to a host that isn't this window.
        windowutils.UtilMixin.processCommand(self, command)

    def confirmExit(self):
        """Ported verbatim from HomeWindow.confirmExit() (home.py) - self-contained, no
        Home-specific state. See routeAction()'s NAV_BACK handling below for the caller."""
        lBtnExit = T(32336, 'Exit')
        lBtnQuit = T(32704, 'Quit Kodi')
        modifier = util.getSetting('exit_default_is_quit') and "quit" or "exit"

        ret = plexnet.util.AttributeDict(button=None, modifier=modifier)

        def actionCallback(dialog, actionID, controlID):
            if actionID == xbmcgui.ACTION_CONTEXT_MENU and controlID == dialog.BUTTON_IDS[0]:
                control = dialog.getControl(controlID)
                if control.getLabel() == lBtnExit:
                    control.setLabel(lBtnQuit)
                    ret.modifier = "quit"
                else:
                    control.setLabel(lBtnExit)
                    ret.modifier = "exit"

        button = optionsdialog.show(
            T(32334, 'Confirm Exit'),
            T(32335, 'Are you ready to exit Plex?'),
            modifier == "exit" and lBtnExit or lBtnQuit,
            T(32924, 'Minimize'),
            T(32337, 'Cancel'),
            action_callback=actionCallback
        )
        ret.button = button
        return ret

    def _sidebarTarget(self):
        """Whichever window object the sidebar's server/user dropdown UI must actually read/write
        controls on right now: self._current (the live, currently-modal real shell) while one is
        hosted, self otherwise. Needed because routeAction() runs on this host even when a real
        shell owns the screen (the shell's routeAction() routes through it first, so shared chrome
        like the sidebar is handled centrally) - but self's own
        native window has already been closed (doClose()) in favor of the shell's by then (see
        MultiWindow._open()'s .modal() loop). getFocusId() reads still resolve against whatever's
        genuinely on screen (that's how routeAction()'s SERVER_BUTTON_ID/USER_BUTTON_ID branches get
        reached at all while hosted), but *writes* - getControl(...).setHeight()/.setPosition(),
        ManagedControlList mutations, setFocusId() - do not: live-confirmed 100% reproducible
        native Kodi crash (minidump captured) the moment showUserMenu()/showServers() ran those
        against self while a real shell was actually modal. Every control-touching call in
        showUserMenu()/showServers()/doUserOption()/selectServer() must go through this, not self,
        for exactly that reason. self.userList/self.serverList themselves stay owned by self (the
        host) - only rebound (ManagedControlList.newControl(), same proven-safe pattern
        self.sectionList/self.tabList/self.hubControls already use to survive a real content swap)
        to whichever native control target.getControl() actually reaches, immediately before use."""
        return self._current if self._isHostedShell else self

    def _sidebarListGuard(self):
        """The WriteGuard (kodigui) for binding the shared sidebar lists - sectionList, tabList,
        userList, serverList - to the current window's native controls. These lists outlive
        every swap; the controls don't, and the objects getControl() and getListItem() hand back
        don't keep them alive (only constructors take a reference - Kodi's
        PythonSwig.cpp.template), so a write after the swap reaches freed memory. Live-caught
        2026-10-03 (AM6B crash log): the reachability check after wake updated a server list
        item, bound on Home, with an Episodes screen open - a segfault in GuiLock on the main
        thread. _setupCurrent() closes the guard before each swap, and shutdown() at the end;
        from then on writes raise kodigui.ScreenClosed, until the next binding gets a new one."""
        guard = self.__dict__.get('_sidebarGuard')
        if guard is None or guard.closed:
            guard = self._sidebarGuard = kodigui.WriteGuard()
        return guard

    def _closeSidebarGuard(self):
        guard = self.__dict__.get('_sidebarGuard')
        if guard is not None:
            guard.close()

    def showUserMenu(self, mouse=False):
        """Ported from HomeWindow.showUserMenu() (home.py) - see quiet-orbiting-heron.md's Cold
        Start plan, Stage 3. Builds/shows the shared user-options dropdown (control 250,
        includes/sidebar_dropdowns.xml.tpl) - already wired into every content-mode template, no
        markup changes needed."""
        items = []
        if util.getGlobalProperty("update_available"):
            items.append(kodigui.ManagedListItem(T(33670, 'Update available'), data_source='update'))
        if plexapp.ACCOUNT.isSignedIn:
            if not len(plexapp.ACCOUNT.homeUsers) and not util.addonSettings.cacheHomeUsers:
                plexapp.ACCOUNT.updateHomeUsers(refreshSubscription=True)

            if len(plexapp.ACCOUNT.homeUsers) > 1:
                items.append(kodigui.ManagedListItem(T(32342, 'Switch User'), data_source='switch'))
            else:
                items.append(kodigui.ManagedListItem(T(32980, 'Refresh Users'), data_source='refresh_users'))
        elif plexapp.ACCOUNT.isOffline and plexapp.util.LOCAL_MODE:
            from lib import localmode
            if len(plexapp.ACCOUNT.homeUsers) > 1:
                items.append(kodigui.ManagedListItem(T(32342, 'Switch User'), data_source='switch'))
            if localmode.isAccountLess():
                items.append(kodigui.ManagedListItem(T(35042, 'Local users'), data_source='local_users'))
        items.append(kodigui.ManagedListItem(T(32343, 'Settings'), data_source='settings'))
        if plexapp.ACCOUNT.isSignedIn:
            items.append(kodigui.ManagedListItem(T(35019, 'Go local'), data_source='go_local'))
            items.append(kodigui.ManagedListItem(T(32344, 'Sign Out'), data_source='signout'))
        elif plexapp.ACCOUNT.isOffline:
            if plexapp.util.LOCAL_MODE:
                items.append(kodigui.ManagedListItem(T(35020, 'Go online'), data_source='go_online'))
            else:
                items.append(kodigui.ManagedListItem(T(32459, 'Offline Mode'), data_source='go_online'))
        else:
            items.append(kodigui.ManagedListItem(T(32460, 'Sign In'), data_source='signin'))
        items.append(kodigui.ManagedListItem(T(32924, 'Minimize'), data_source='minimize'))
        items.append(kodigui.ManagedListItem(T(32336, 'Exit'), data_source='exit'))

        if len(items) > 1:
            items[0].setProperty('first', '1')
            items[-1].setProperty('last', '1')
        else:
            items[0].setProperty('only', '1')
        # somehow dynamically setting the list height here doesn't work. We need a height that's
        # bigger than our possible available items in the template

        target = self._sidebarTarget()
        # Rebind first, not after - .reset()/.addItems() below operate on whatever self.userList's
        # own .control currently points at, so this has to land before them. newControlEmpty(), not
        # newControl(): about to repaint via addItems() anyway, so skip newControl()'s own redundant
        # repaint-then-immediately-discard of whatever this list held from its last showing.
        self.userList.newControlEmpty(target, guard=self._sidebarListGuard())
        self.userList.reset()
        self.userList.addItems(items)
        itemHeight = util.vscale(66, r=0)

        self.userList.setHeight((len(items) * itemHeight))
        target.getControl(self.USER_MENU_GROUP_ID).setHeight((len(items) * itemHeight))
        target.getControl(self.USER_MENU_BG_ID).setHeight((len(items) * itemHeight) + 80)

        if not mouse:
            target.setFocusId(self.USER_LIST_ID)

    def _closeSessionWithOption(self, option, shutting_down=False):
        """Every doUserOption() branch that ends a session (go_online while local, signout, exit,
        the switch/signin/go_local catch-all) needs to act on the TRUE top-level session
        (windowutils.HOME), not necessarily self. self can be a second, nested LibraryWindow:
        opener.sectionClicked() (collections, photo directories, filtered sections) constructs one
        when there's no live chain to reuse. With one, it swaps the section into that chain in
        place (swapToSection()) - every in-app route passes its window as context today, so a
        nested instance is rare. When they were the norm, choosing Exit from within a collection
        just closed that nested instance, revealing the library grid underneath instead of
        exiting (live-confirmed regression, fixed here).
        """
        target = windowutils.HOME
        if shutting_down:
            target._shuttingDown = True
            util.DEBUG_LOG("Library: Initiating shutdown, setting background")
            background.setShutdown()
        else:
            util.DEBUG_LOG("Killing last background image")
            target.windowSetBackground(None)

        # Home sets closeOption and closes as it acts on the intent (navigate()). From a nested
        # instance, this leaves for Home like any other window outside the chain
        # (GoHomeMixin.leaveFor(), the Home button's path from a descendant), and Home acts on it
        # as it arrives there (processCommand()).
        self.navigate(navintent.closeSession(option))

    def doUserOption(self, force_option=None, target=None):
        """Ported from HomeWindow.doUserOption() (home.py) - see quiet-orbiting-heron.md's Cold
        Start plan, Stage 3. Adaptations: dialog_props reads carriedProps defensively (getattr,
        CommonMixin's own pattern) since LibraryWindow doesn't define it; storeLastBG() stays
        unported (see shutdown()'s own comment) - HomeWindow's version isn't called from here
        anyway, only from confirmExit()'s minimize branch and shutdown() itself, neither of which
        call it here either; every session-ending branch routes through _closeSessionWithOption()
        above instead of closing self directly - see that method's own comment for why.

        target: explicit override for _sidebarTarget() - routeClick()'s USER_LIST_ID branch below
        always has the right answer already (self when this call originated on self, the calling
        shell itself when a real shell forwarded its own click here - see e.g.
        preplay.PrePlayWindow.onClick()) and passing it avoids re-deriving it from self._current,
        which would be wrong for that forwarded case (self._current is never the caller here, the
        caller *is* self._current already forwarding to its host)."""
        target = target or self._sidebarTarget()
        if not force_option:
            mli = self.userList.getSelectedItem()
            if not mli:
                return

            option = mli.dataSource
        else:
            option = force_option

        target.setFocusId(self.USER_BUTTON_ID)

        if option == 'settings':
            from . import settings
            settings.openWindow()
        elif option == 'update':
            self.setBoolProperty('show.options', False)
            self.setProperty('busy', '1')
            target.setFocusId(self.SECTION_LIST_ID)
            util.setGlobalProperty('update_requested', '1', wait=True)
        elif option == 'go_online':
            if plexapp.util.LOCAL_MODE:
                # leave local mode via a clean re-init (re-verifies the account or opens sign-in)
                self._closeSessionWithOption(option)
                return
            plexapp.ACCOUNT.refreshAccount()
        elif option == 'refresh_users':
            plexapp.ACCOUNT.updateHomeUsers(refreshSubscription=True)
            return True
        elif option == 'local_users':
            from lib import localmode
            localmode.seedUsersFromServer(reselect=True)
            return True
        elif option == 'signout':
            button = optionsdialog.show(
                T(32344, 'Sign Out'),
                T(33669, 'Really sign out?'),
                T(32329, 'No'),
                T(32328, 'Yes'),
                dialog_props=getattr(self, 'carriedProps', None)
            )

            if button != 1:
                return
            self._closeSessionWithOption(option)
        elif option == 'exit':
            self._closeSessionWithOption("exit", shutting_down=True)
            return
        elif option == 'minimize':
            util.setGlobalProperty('is_active', '')
            xbmc.executebuiltin('ActivateWindow(10000)')
            return
        else:
            self._closeSessionWithOption(option)

    def hookSignals(self):
        """Server-list-relevant subset of HomeWindow.hookSignals() (home.py) - only what
        showServers()/selectServer() below actually need to stay live: new/removed/reachable
        servers update the open dropdown's contents, change:selectedServer drives the real
        post-switch refresh (serverRefresh() below). HomeWindow's much larger signal set also
        covers hub-rendering/theme/spoiler/wake-sleep concerns that don't apply to this narrower
        port - out of scope here, not an oversight. Called once, only for the true root
        (onFirstInit()'s guard below) - a nested LibraryWindow instance's own server dropdown
        still works (selectServer() below operates on whichever self opened it), it just doesn't
        live-update while open, and doesn't drive its own refresh - see selectServer()'s own
        comment for why only windowutils.HOME reacting to the actual switch is correct.

        Each handler is posted to the main thread (MultiWindow.postUI()) rather than run where
        the signal fires: plexnet raises these on its own threads (e.g. the deferred reachability
        update's timer), and every one of them touches controls. Live-caught 2026-09-24 as a
        native crash during a server switch - see postUI(). change:selectedServer is raised on
        the main thread, inside selectServer()'s busy context; posting it too moves the refresh
        and its section swap out of that context, onto a clean tick of their own.
        """
        self._serverSignalHandlers = (
            (plexapp.SERVERMANAGER, 'new:server', self._postedHandler('onNewServer', self.onNewServer)),
            (plexapp.SERVERMANAGER, 'remove:server', self._postedHandler('onRemoveServer', self.onRemoveServer)),
            (plexapp.SERVERMANAGER, 'reachable:server',
             self._postedHandler('onReachableServer', self.onReachableServer)),
            (plexapp.SERVERMANAGER, 'reachable:server',
             self._postedHandler('displayServerAndUser', self.displayServerAndUser)),
            (plexapp.util.APP, 'change:selectedServer',
             self._postedHandler('onSelectedServerChange', self.onSelectedServerChange)),
            (plexapp.SERVERMANAGER, 'suspect:server', self._postedHandler('onServerSuspect', self.onServerSuspect)),
            (plexapp.SERVERMANAGER, 'recovered:server',
             self._postedHandler('onServerRecovered', self.onServerRecovered)),
            (plexapp.SERVERMANAGER, 'offline:server', self._postedHandler('onServerOffline', self.onServerOffline)),
            (plexapp.SERVERMANAGER, 'online:server', self._postedHandler('onServerOnline', self.onServerOnline)),
            (plexapp.SERVERMANAGER, 'gone:selectedServer',
             self._postedHandler('onSelectedServerGone', self.onSelectedServerGone)),
            # Sleep and wake (monitor.py), ported from HomeWindow, which went with it in 12675d11.
            # Pausing only sets flags, so it runs where it's signalled; waking waits on its own
            # thread (_onWake()) and posts the refresh. HomeWindow also refreshed when a
            # screensaver or a blanked display ended (and every 5 minutes); those wait for a
            # refresh that rebinds rows in place rather than rebuilding the view - see
            # refreshLastSection().
            (util.MONITOR, 'system.sleep', self._onSleep),
            (util.MONITOR, 'system.wakeup', self._onWake),
            # Settings' update source; passed on to the update checker by tick()
            (plexapp.util.APP, 'change:update_source', self._onUpdateSourceChanged),
        )
        for emitter, signal, handler in self._serverSignalHandlers:
            emitter.on(signal, handler)

        # tick() - the update checker's hand-offs and the periodic reachability check
        self._ignoreTick = False
        self._lastReachabilityCheck = time.time()
        self._updateSourceChanged = None
        self._updatePromptPosted = False
        if util.CRON:
            util.CRON.registerReceiver(self)

    def _postedHandler(self, name, fn):
        """A signal handler that posts fn, with the signal's arguments, to the main thread."""
        def handler(*args, **kwargs):
            self.postUI(name, fn, args=args, kwargs=kwargs)
        return handler

    def unhookSignals(self):
        for emitter, signal, handler in getattr(self, '_serverSignalHandlers', ()):
            emitter.off(signal, handler)
        self._serverSignalHandlers = ()
        if util.CRON:
            util.CRON.cancelReceiver(self)

    # The recheck_server_connections setting's interval. (Was periodic_reachability_check, renamed
    # when its default turned on: Kodi keeps a stored value across a default change, and every
    # install had "false" stored under the old id.)
    REACHABILITY_CHECK_INTERVAL = 600

    def tick(self):
        """util.CRON, about once a second, on its own thread - root only (hookSignals()). Ported
        from HomeWindow.tick(), which went with it in 12675d11, leaving the periodic reachability
        check a setting that did nothing. HomeWindow's tick also refreshed Home's hubs every 5
        minutes; that waits for a refresh that rebinds rows in place (see refreshLastSection())."""
        if self._shuttingDown or self.__dict__.get('_ignoreTick'):
            return

        self._answerUpdateChecker()

        if xbmc.Player().isPlayingVideo():
            return

        now = time.time()
        if (util.getSetting('recheck_server_connections', True) and
                now - self.__dict__.get('_lastReachabilityCheck', now) > self.REACHABILITY_CHECK_INTERVAL):
            self._lastReachabilityCheck = now
            plexapp.SERVERMANAGER.periodicReachabilityCheck()

    def _onUpdateSourceChanged(self, value=None, **kwargs):
        self._updateSourceChanged = value

    def _answerUpdateChecker(self):
        """The update checker (update_checker.py, a service) talks to the UI through global
        properties: a changed update source goes to it as update_source_changed, and when it finds
        an update it sets notify_update and waits for update_response. HomeWindow's tick did both
        (its service_responder()); both went with it in 12675d11, so an update was never offered -
        the checker gave up with "No user response". The question is asked on the main thread,
        and only with no screen open on top, as HomeWindow only asked on Home."""
        source = self.__dict__.get('_updateSourceChanged')
        if source:
            self._updateSourceChanged = None
            util.setGlobalProperty('update_source_changed', source, wait=True)

        if (util.getGlobalProperty('notify_update') and not self.__dict__.get('_updatePromptPosted')
                and not self._backStack):
            self._updatePromptPosted = True
            self.postUI('update available', self._promptUpdate)

    def _promptUpdate(self):
        """Ported from HomeWindow.service_responder()/doUpdate() (develop_kodi21 home.py)."""
        try:
            if self._shuttingDown or self._backStack or not util.getGlobalProperty('notify_update'):
                return
            is_downgrade = bool(util.getGlobalProperty('update_is_downgrade', consume=True))
            button = optionsdialog.show(
                T(33670, 'Update available'),
                T(33671, 'Current: {current_version}\nNew: {new_version}\n\nChangelog:\n{changelog}').format(
                    current_version=util.ADDON.getAddonInfo('version'),
                    new_version=util.getGlobalProperty('update_available'),
                    changelog=util.getGlobalProperty('update_changelog'),
                ),
                T(33683, 'Exit, download and install'),
                T(33684, 'Later') if not is_downgrade else T(32329, 'No'),
                delay_buttons=1.8, big=True, close_timeout=3600
            )
            resp = "commence" if button == 0 else "cancel"
            util.setGlobalProperty('update_response', resp, wait=True)
            util.setGlobalProperty('notify_update', '', wait=True)

            if resp == "commence":
                # wait for the checker to take the answer before closing
                try:
                    util.waitForConsumption('update_response', timeout=200)
                except Exception:
                    pass
                util.LOG("Library: closing for the update")
                self._ignoreTick = True
                self.stopRetryingRequests()
                self._closeSessionWithOption('update')
        finally:
            self._updatePromptPosted = False

    def _onSleep(self, *args, **kwargs):
        """System sleep: no reachability checks or offline retests until wake (_onWake())."""
        util.LOG("Library: system sleep, pausing updates")
        self._ignoreTick = True
        plexapp.SERVERMANAGER.cancelOfflineRetry()

    def _onWake(self, *args, **kwargs):
        """System wake: wait as action_on_wake says - the network takes a moment to come back, and
        testing at once would only put the server offline - then retest the server and refresh;
        or restart, if so set. The wait runs on its own thread: neither the notification thread
        nor the UI loop should block on it."""
        if self._shuttingDown:
            return
        action = util.getSetting('action_on_wake', util.altSeekRecommended and 'wait_5' or 'wait_1')
        util.LOG("Library: wake, action: {0}", action)
        if action == 'restart':
            self.postUI('restart on wake', self._closeSessionWithOption, args=('restart',))
            return
        seconds = int(action.split('_')[1]) if action.startswith('wait_') else 0
        threading.Thread(target=self._afterWake, args=(seconds,), name='LIBRARY-WAKE').start()

    def _afterWake(self, seconds):
        if seconds:
            with busy.ProgressDialog(T(33073, 'Wait after wakeup'), T(33074, 'Waiting {} second(s)').format(seconds)) as pd:
                waited = 0
                while waited < seconds:
                    if util.MONITOR.waitForAbort(0.5):
                        return
                    waited += 0.5
                    pd.update(int(waited * 100 / seconds))
        if self._shuttingDown:
            return
        self._lastReachabilityCheck = time.time()
        plexapp.SERVERMANAGER.periodicReachabilityCheck()
        plexapp.SERVERMANAGER.resumeOfflineRetry()
        self.postUI('refresh after wake', self.refreshLastSection)

    def refreshLastSection(self, *args, **kwargs):
        """Reload the section's Recommended view after waking from sleep - its hubs were fetched
        before it, and Continue Watching, On Deck or Recently Added may well have moved on since.
        Rebuilt by openSection() (the window stays): this view has no refresh that rebinds rows
        in place like HomeWindow's _bindAllHubSlots() yet, so until it has, wake is the only
        trigger (HomeWindow's screensaver/blank-display/5-minute ones wait for it - see the plan's
        Phase 7). Lands back on the same hub row, as Back does, and each row keeps its item
        position (fresh=False). Not with a screen chain open, a library grid showing (its scroll
        position would be lost) or a video playing."""
        self._ignoreTick = False
        plexapp.SERVERMANAGER.resumeOfflineRetry()
        if (self._shuttingDown or self._backStack or self.contentMode != 'recommended' or
                xbmc.Player().isPlayingVideo()):
            return
        util.LOG("Library: refreshing {0} after wake/idle", self.section)
        # without this the rebuilt view starts on the first row (_recommendedHubsCallback())
        self._pendingRestoreHubId = self._captureRootRestoreState().get('_restoreHubId')
        if not self.openSection(self.section, force=True, fresh=False):
            self._pendingRestoreHubId = None

    def showServers(self, from_refresh=False, mouse=False):
        """Ported from HomeWindow.showServers() (home.py) - see quiet-orbiting-heron.md's Cold
        Start plan, Stage 3. Builds/shows the shared server-switch dropdown (control 260,
        includes/sidebar_dropdowns.xml.tpl) - same include showUserMenu() above already uses."""
        target = self._sidebarTarget()
        with self.lock:
            selection = None
            if from_refresh:
                try:
                    mli = self.serverList.getSelectedItem()
                except kodigui.ScreenClosed:
                    mli = None  # bound to a window a swap has closed (_sidebarListGuard())
                if mli:
                    selection = mli.uuid

            servers = sorted(
                plexapp.SERVERMANAGER.getServers(),
                key=lambda x: (x.owned and '0' or '1') + x.name.lower()
            )

            if plexapp.util.LOCAL_MODE:
                # local mode can only ever use servers with a plain LAN connection
                servers = [s for s in servers if s.hasLocalModeConnection()]

            items = []
            for s in servers:
                item = home.ServerListItem(s.name, not s.owned and s.owner or '', data_source=s)
                item.uuid = s.uuid
                item.onUpdate()
                if plexapp.SERVERMANAGER.selectedServer:
                    item.setProperty('current', plexapp.SERVERMANAGER.selectedServer.uuid == s.uuid and '1' or '')
                items.append(item)

            if len(items) > 1:
                items[0].setProperty('first', '1')
                items[-1].setProperty('last', '1')
            elif items:
                items[0].setProperty('only', '1')

            # Rebind first, not after - see showUserMenu()'s own comment on this same pattern.
            # newControl(), not newControlEmpty(): from_refresh can reach here with the list
            # already showing (a live server/reachability update, not a fresh open), and unlike
            # showUserMenu()'s unconditional reset()+addItems(), replaceItems() above only
            # repaints when the item count actually changed - newControlEmpty()'s own repaint-skip
            # would leave a stale/empty list on screen in the common case where it doesn't.
            self.serverList.newControl(target, guard=self._sidebarListGuard())
            self.serverList.replaceItems(items)
            itemHeight = util.vscale(100, r=0)

            listHeight = min(len(items), 9) * itemHeight
            target.getControl(self.SERVER_MENU_BG_ID).setHeight(listHeight + 80)

            # Position dropdown so it grows upward from the server button area
            buttonY = util.vscale(990, r=0)
            dropdownY = buttonY - listHeight
            target.getControl(self.SERVER_MENU_GROUP_ID).setPosition(80, dropdownY)

            for item in items:
                if item.dataSource != kodigui.DUMMY_DATA_SOURCE:
                    item.hookSignals()

            if selection:
                for mli in self.serverList:
                    if mli.uuid == selection:
                        self.serverList.selectItem(mli.pos())

            if not from_refresh and items and not mouse:
                target.setFocusId(self.SERVER_LIST_ID)

            if not from_refresh:
                # Forced: opening the list is asking how the servers are now. Unforced, a server
                # checked reachable in the last minute wasn't retested, so one that had just gone
                # down still looked fine and could be picked (live, 2026-10-02).
                plexapp.refreshResources(True)

    def selectServer(self, uuid=None):
        """Ported from HomeWindow.selectServer() (home.py). One addition HomeWindow never
        needed: it was always the one true root, so the change:selectedServer signal this
        triggers (hooked only on windowutils.HOME - see hookSignals()) always landed back on the
        same object that called this. Here self can be a nested, non-root LibraryWindow instance
        (e.g. a movie collection) - the busy/focus/reachability calls below still run harmlessly
        on whichever self invoked this, but once a real switch actually happens, unwind back to
        the root the same way goHome() already does elsewhere, with_root=True so its own
        go_root/onReInit() machinery lands on home_section once HOME is current again.
        serverRefresh() below may fire first (via the signal, synchronously, before this method's
        own unwind call at the end) while HOME is still backgrounded behind this nested instance -
        its own openSection() call just declines harmlessly then, the same guard every other
        in-place section swap already relies on - the goHome(with_root=True) unwind below is what
        actually completes the landing, once HOME is current again.
        """
        if self._shuttingDown:
            return

        if not uuid:
            mli = self.serverList.getSelectedItem()
            if not mli:
                return
            server = mli.dataSource
        else:
            server = plexapp.SERVERMANAGER.getServer(uuid)
            if not server:
                return

        prevUUID = plexapp.SERVERMANAGER.selectedServer.uuid

        self.changingServer = True
        self._sidebarTarget().setFocusId(self.SECTION_LIST_ID)

        if not self._shuttingDown and not server.isReachable():
            if server.pendingReachabilityRequests > 0:
                util.messageDialog(T(32339, 'Server is not accessible'), T(32340, 'Connection tests are in '
                                                                                  'progress. Please wait.'))
            else:
                util.messageDialog(
                    T(32339, 'Server is not accessible'), T(32341, 'Server is not accessible. Please sign into '
                                                                   'your server and check your connection.')
                )
            self.changingServer = False
            return

        changed = False
        try:
            with busy.BusySignalContext(plexapp.util.APP, "change:selectedServer") as bc:
                changed = plexapp.SERVERMANAGER.setSelectedServer(server, force=True)
                if not changed:
                    bc.ignoreSignal = True
                    self.changingServer = False
                else:
                    util.setSetting('previous_server.{}'.format(plexapp.ACCOUNT.ID), prevUUID)
        except Exception:
            # Otherwise left set for the session. The navigation queue logs the exception.
            self.changingServer = False
            raise

        if changed and self is not windowutils.HOME:
            self.goHome(with_root=True)

    def onNewServer(self, **kwargs):
        self.showServers(from_refresh=True)

    def onRemoveServer(self, **kwargs):
        self.onNewServer()

    def onReachableServer(self, server=None, **kwargs):
        for mli in self.serverList:
            if mli.uuid == server.uuid:
                mli.unHookSignals()
                mli.dataSource = server
                mli.hookSignals()
                mli.onUpdate()
                return
        else:
            self.onNewServer()

    # The "isn't responding" panel's button (includes/server_unavailable.xml.tpl)
    SERVER_RETRY_BUTTON_ID = 2600

    def onServerSuspect(self, server=None, **kwargs):
        """A query to the selected server got no answer, and its connections are being retested:
        say so now, before the verdict - offline (onServerOffline()) or answering after all
        (onServerRecovered()). Waiting for the verdict, as this once did, kept the user waiting
        for a second connect timeout and the retest on top."""
        if server is None or server is not plexapp.SERVERMANAGER.selectedServer:
            return
        self._notifyUnavailable(server)
        self.updateServerUnavailable()

    def onServerOffline(self, server=None, **kwargs):
        """The selected server stopped answering: it stays selected (plexnet retests it, backing
        off), the sidebar shows it as unreachable, and an empty view says so in place
        (updateServerUnavailable()). Opening the server list retests at once. The toast only if
        onServerSuspect() hasn't already shown it - a retest in the background finds it down too.
        Interim - the libraries-from-any-server sidebar replaces this with per-library state."""
        if server is None or server is not plexapp.SERVERMANAGER.selectedServer:
            return
        self.displayServerAndUser()
        self._notifyUnavailable(server)
        self.updateServerUnavailable()

    def onServerRecovered(self, server=None, **kwargs):
        """The selected server answered its retest after all (a blip): a view the failed query left
        empty is loaded again, quietly - the toast already said it was retrying."""
        if server is None or server is not plexapp.SERVERMANAGER.selectedServer:
            return
        self._unavailableNotified = None
        self.updateServerUnavailable()
        if (not self._backStack and not self._shuttingDown and not self._isHostedShell
                and self._viewIsEmpty()):
            self._reloadAfterReturn()

    # After a server comes back, a reload that still finds the section empty tries again after
    # these many seconds: Plex answers its connection test before it has loaded its libraries (live
    # on the PC, 2026-10-03: 4.5 s after Plex started, its hubs came back with no items in them).
    RETURN_RELOAD_DELAYS = (3, 10)

    def _reloadAfterReturn(self):
        """onServerOnline()/onServerRecovered(): reload the section in place, watched by
        _retryEmptyAfterReturn() in case it comes back empty."""
        self._returnReload = (self.section, list(self.RETURN_RELOAD_DELAYS))
        self.openSection(self.section, force=True, fresh=False)

    def _retryEmptyAfterReturn(self):
        """After a fill or bind: if the server has just come back (_reloadAfterReturn()) and this
        section is still empty, reload it again shortly - RETURN_RELOAD_DELAYS, then give up. Only
        while the same section stays on screen with nothing open on top."""
        pending = self.__dict__.get('_returnReload')
        if not pending:
            return
        section, delays = pending
        if section is not self.section or not delays or self._isHostedShell or not self._viewIsEmpty():
            self._returnReload = None
            return
        delay = delays.pop(0)
        due = time.time() + delay
        util.DEBUG_LOG("Library: {0} still empty after the server came back, reloading in {1}s", section, delay)

        def tick(now):
            if self.section is not section or self.closing or self._backStack or self._isHostedShell:
                self._returnReload = None
                return False
            if now < due:
                return True
            self.postUI('reload after the server came back', self.openSection, args=(section,),
                        kwargs={'force': True, 'fresh': False})
            return False
        self.addTicker(tick)

    def _notifyUnavailable(self, server):
        """The "isn't responding" toast: once, until the server answers again."""
        if self.__dict__.get('_unavailableNotified') == server.uuid:
            return
        self._unavailableNotified = server.uuid
        util.showNotification(T(35125, "{0} isn't responding. Retrying...").format(server.name), time_ms=5000)

    def _viewIsEmpty(self):
        if self.contentMode == 'recommended':
            return not self.visibleHubs
        return bool(self.getProperty('no.content') or self.getProperty('no.content.filtered'))

    def updateServerUnavailable(self):
        """Show or clear the "isn't responding" panel (includes/server_unavailable.xml.tpl): in
        place of an empty grid or Recommended view while the selected server is suspect (a query got
        no answer and its connections are being retested) or offline, so the view says why it's
        empty and offers "Try again". Empty, it used to say nothing, or "no content" for a grid.
        Returns whether it shows."""
        server = plexapp.SERVERMANAGER.selectedServer
        show = bool(server and (server.offline or server.suspect) and not server.gone
                    and not self._isHostedShell and not self.closing and self._viewIsEmpty())
        if show:
            self.setProperty('server.unavailable.detail',
                             T(35131, 'Trying again...') if self.__dict__.get('_serverRetrying')
                             else T(35130, 'Retrying automatically.'))
            self.setProperty('server.unavailable', T(35129, "{0} isn't responding").format(server.name))
        elif self.getProperty('server.unavailable'):
            self.setProperty('server.unavailable', '')
        return show

    def retryServerNow(self):
        """The panel's "Try again": retest the selected server at once rather than at the next step
        of the backoff. The panel says so until the round ends (_tickServerRetry()); if the server
        answers, onServerOnline() reloads the view."""
        if self.__dict__.get('_serverRetrying') or not plexapp.SERVERMANAGER.retestSelectedServerNow():
            return
        self._serverRetrying = True
        self.updateServerUnavailable()
        self.addTicker(self._tickServerRetry)

    def _tickServerRetry(self, now):
        server = plexapp.SERVERMANAGER.selectedServer
        if server and server.pendingReachabilityRequests > 0 and not self.closing:
            return True
        self._serverRetrying = False
        self.updateServerUnavailable()
        return False

    def onSelectedServerGone(self, server=None, replacement=None, **kwargs):
        """plex.tv no longer lists the selected server: the account doesn't have it any more. With
        a replacement, plexnet has already switched to it (change:selectedServer follows and
        refreshes as for any switch); with none, it stays selected, shown unreachable, until the
        user picks another."""
        if server is None:
            return
        if replacement is not None:
            message = T(35127, '{0} is no longer available to this account. Switched to {1}.').format(
                server.name, replacement.name)
        else:
            self.displayServerAndUser()
            message = T(35128, '{0} is no longer available to this account. Choose another server.').format(
                server.name)
        util.showNotification(message, time_ms=8000)

    def onServerOnline(self, server=None, **kwargs):
        """The selected server answers again: show it so, and reload what's on screen - its rows
        came back empty while it was gone. Not with a screen chain open on top (the item screens
        handle their own failed loads), and only the section's own view is reloaded, in place."""
        if server is None or server is not plexapp.SERVERMANAGER.selectedServer:
            return
        self._unavailableNotified = None
        self.displayServerAndUser()
        self.updateServerUnavailable()
        util.showNotification(T(35126, '{0} is back').format(server.name), time_ms=3000)
        if not self._backStack and not self._shuttingDown:
            self._reloadAfterReturn()

    def onSelectedServerChange(self, **kwargs):
        if self.serverRefresh():
            self.setFocusId(self.SECTION_LIST_ID)
            self.changingServer = False

    def serverRefresh(self, section=None):
        """LibraryWindow-shaped equivalent of HomeWindow.serverRefresh() (home.py) - that
        version's @busy.dialog()-wrapped fullyRefreshHome()/loadLibrarySettings() rebuild Home's
        own hub-fetching state, none of which exists here. What a server switch actually needs on
        this window is narrower: refresh the sidebar avatar/server labels, rebuild the section
        list for the new server's libraries, and land on a section that still exists there
        (home_section, same default fullyRefreshHome() itself uses) - openSection() below is the
        same in-place swap every other section change already goes through, so it inherits that
        method's own is_current_window decline guard for free (see selectServer()'s comment for
        why that matters here).

        force=True on the openSection() call below - live-confirmed regression without it:
        switching servers while already on Home (the common case, since selectServer()'s own
        goHome(with_root=True) unwind also lands here) leaves `target == self.section` true
        (home_section is a shared singleton), so openSection()'s own "already there" no-op guard
        silently skipped the reload - sidebar rebuilt correctly for the new server, but the
        content pane stayed on the old server's stale hubs, and clicking Home again did nothing
        (same equality check, same no-op) until the user detoured through a different section
        first.
        """
        with self.lock:
            self.displayServerAndUser()
            if not plexapp.SERVERMANAGER.selectedServer:
                self.setFocusId(self.USER_BUTTON_ID)
                return False

            self.loadHubSettings()
            self.loadNavSettings()
            self.buildSectionList()

            target = section or home.home_section
            self.openSection(target, force=True)
            return True

    def onFirstInit(self):
        timing = kodigui.StepTiming('Grid open')
        if self._openBaseWinID is not None and not self._coldStartSignaled:
            # Cold start (main.py) - the first real content is now confirmed showing (this native
            # onInit() callback only fires once Kodi has actually activated the window), so this is
            # the equivalent moment main.py's old create()+waitForOpen() two-step used to clear the
            # busy spinner at, just driven by the real event instead of a separate poll.
            self._coldStartSignaled = True
            background.setBusy(False)

        pnUtil.APP.on("watchlist:modified", self.setWatchlistDirty)
        util.MONITOR.on("library.back_home", self.goHomeRoot)

        # Fetched afresh by each view, before the tabs row below needs them (_sectionPlaylists())
        self._viewPlaylists = None

        # The sidebar lists are bound to this view's controls under the host's guard, which the
        # next swap closes (_sidebarListGuard()).
        sidebarGuard = self._sidebarListGuard()
        if self.sectionList is None:
            self.loadNavSettings()
            self.sectionList = kodigui.ManagedControlList(self, self.SECTION_LIST_ID, 15, guard=sidebarGuard)
            self.buildSectionList()
            self.displayServerAndUser()
        else:
            self.sectionList.newControl(self, guard=sidebarGuard)
        # newControl() re-adds the items to a fresh native control whose selection starts at index
        # 0 (Search) - reselect the active section so the collapsed rail shows it from the first
        # frame (SidebarMixin._selectActiveSection()'s rule).
        self._selectActiveSection()

        if self.tabList is None:
            self.tabList = kodigui.ManagedControlList(self, self.TAB_LIST_ID, 5, guard=sidebarGuard)
            self._tabListNeedsRebuild(self.section)  # just to set the tracked flags - always builds below regardless
            self.buildTabList()
        else:
            self.tabList.newControl(self, guard=sidebarGuard)
            if self._tabListNeedsRebuild(self.section):
                self.buildTabList()
            else:
                self.updateActiveTabMarker()
        # Set every fresh onFirstInit() (every content-mode/section swap) - section_tabs.xml.tpl
        # gates control 320's own <visible> on this; hubAction()'s hub-row MOVE_UP interception
        # (library_hubs.py) also checks it directly before redirecting focus there, since a hidden
        # control can't usefully receive focus.
        self.setBoolProperty('hide.section_tabs', self._hideSectionTabs())

        if self.userList is None:
            self.userList = kodigui.ManagedControlList(self, self.USER_LIST_ID, 5, guard=sidebarGuard)
        else:
            self.userList.newControl(self, guard=sidebarGuard)

        if self.serverList is None:
            self.serverList = kodigui.ManagedControlList(self, self.SERVER_LIST_ID, 10, guard=sidebarGuard)
            if self is windowutils.HOME:
                # Only the true root reacts to server-list-relevant signals - see hookSignals()'s
                # own comment for why a nested instance's dropdown still works without them.
                self.hookSignals()
        else:
            self.serverList.newControl(self, guard=sidebarGuard)
        timing.mark('controls')
        # A new view starts without the "isn't responding" panel or the "no content" message; its
        # first fill or bind decides (updateServerUnavailable(), _recommendedHubsCallback(), the
        # grid's fill). The host carries properties over to each view, so they're cleared here
        # rather than left to the last view's state.
        for key in ('server.unavailable', 'no.content', 'no.content.playlists'):
            if self.getProperty(key):
                self.setProperty(key, '')

        if self.contentMode == 'recommended':
            # RecommendedWindow has none of the poster-grid controls (POSTERS_PANEL_ID/
            # KEY_LIST_ID) doRefill() below binds against; its hub rows are bound here instead.
            self.refill = False

            # Stage D (quiet-orbiting-heron.md): fires every swap into 'recommended' -
            # onFirstInit() only runs when _setupCurrent() constructs a fresh _current, which for
            # this content mode only happens on a switchTab()/openSection() swap (VIEWS_RECOMMENDED
            # has a single view type, so nothing else re-triggers it). Index i always holds control
            # id HUB_CONTROL_ID+i (400-403), same fixed mapping HomeWindow.hubControls uses - no
            # rotation here (deliberately out of scope), so this mapping is also the final one for
            # this swap's whole lifetime.

            # Populates self.hubSettings from the user's already-saved hub visibility/order
            # preferences (loadHubSettings(), ported from HomeWindow) so
            # _recommendedHubsCallback()'s isHubHidden() filter below has real data to check
            # against, instead of always seeing "nothing hidden" (self.hubSettings starts None).
            # Synchronous (a single setting read), fine on the main thread here alongside the
            # rest of this one-time setup.
            self.loadHubSettings()

            # Group 51 has no correct position at all until Python sets it explicitly - grouplist
            # 50 auto-stacks its only child flush to 0, ignoring the declared posy (see that
            # control's own comment in script-plex-recommended.xml.tpl). This shell's control 51
            # is brand new every 'recommended' entry (RecommendedWindow gets torn down and
            # reconstructed by switchTab()/openSection() like any other view-type swap), so it's
            # positioned here, once per entry, at the first row's offset. The hub engine moves it
            # from then on: every bind (_placeStack()) and every slide (_startHubSlide()).
            g51 = self.getControl(51)
            g51.setPosition(g51.getPosition()[0], util.vscale(self.GROUP51_BASELINE_OFFSET, r=0))

            # Built once (self.hubControls starts None, see __init__), rebound via newControl()
            # on every later 'recommended' entry - same shape self.tabList/self.sectionList
            # already use just below, live-proven safe across 20+ plain section-to-section swaps.
            # This used to unconditionally discard and freshly construct all 5
            # ManagedControlLists on every single entry - the one remaining structural difference
            # from tabList/sectionList once that comparison was actually run, and live-confirmed
            # as the fix for a native access-violation crash (heap/vtable corruption) that
            # otherwise built up over a handful of 'recommended' round trips with no consistent
            # trigger point (sometimes right after the bind, sometimes on the way back out,
            # sometimes mid-click - the hallmark of accumulating corruption rather than a single
            # deterministic bug).
            if self.hubControls is None:
                self.hubControls = (
                    kodigui.ManagedControlList(self, self.HUB_CONTROL_ID, 5),
                    kodigui.ManagedControlList(self, self.HUB_CONTROL_ID + 1, 3),
                    kodigui.ManagedControlList(self, self.HUB_CONTROL_ID + 2, 3),
                    kodigui.ManagedControlList(self, self.HUB_CONTROL_ID + 3, 3),
                )
            else:
                # newControlEmpty(), not newControl(): this section's hub content is about to
                # be replaced wholesale by the hub bind below anyway, so repainting whatever
                # the *previous* section's Recommended tab last left in these items (newControl()'s
                # normal behavior - correct for tabList/sectionList/userList/serverList just
                # above, whose content genuinely carries over unchanged across a section swap)
                # would otherwise flash that stale content on screen for the ~100-200ms gap
                # until _recommendedHubsCallback()/replaceItems() actually lands. Live-confirmed
                # as the cause of a jarring "previous section's hubs" flash on every swap into a
                # section whose Recommended tab was already visible earlier this session.
                for hc in self.hubControls:
                    hc.newControlEmpty(self)

            # Same stale-content problem as the hub tiles above, for the hero overlay (art box
            # top-right, title/summary/etc. panel left) - updateHeroFrom()/setHeroInfo() only run
            # once the hub bind below actually lands, so without this, whatever the *previous*
            # section's Recommended tab last set title/clear.logo/summary/background/etc. to just
            # sits there, fully visible, for that same gap. no_hero_art is exactly this signal:
            # the hero-art box (default_background.xml.tpl) and the info overlay (script-plex-
            # recommended.xml.tpl) are both hidden while it's set, regardless of whatever stale
            # property values are still sitting underneath, until the real callback below binds
            # the anchor hub and clears it.
            self._setNoHeroArt(True)

            # Snapshot now (main thread, same moment the task is scheduled) so the callback can
            # tell a stale fetch (a swap landed before it ran) from a current one - same idiom as
            # _chunkCallbackFor()'s _listGeneration snapshot.
            generation = self._listGeneration

            # SectionHubsTask's 3rd arg (section_keys, passed to the server as section_ids)
            # restricts which sections' hubs get included in a home_section fetch -
            # HomeWindow.wantedSections's whole purpose (home.py), built from the same
            # navSettings-based hidden-section check the sidebar applies (sidebar_model.sections()). Leaving this unset (server default: no restriction)
            # live-confirmed as sections hidden from the sidebar still contributing hub rows -
            # more rows than the real Home screen shows, one of them empty (a hidden section
            # with no visible content), which native Kodi list-focus can land geometry on but
            # not actually focus, needing an extra press to skip past. self.sectionList is
            # already built by this point (see the branch above) and already filtered the same
            # way - reused directly rather than re-deriving navSettings here. Real library
            # section keys are purely numeric strings (same key.isdigit() distinction already
            # used elsewhere in this file), which naturally excludes the Search/Home/Watchlist/
            # Playlists entries also in this list.
            section_keys = [mli.dataSource.key for mli in self.sectionList
                            if mli.dataSource and mli.dataSource.key and mli.dataSource.key.isdigit()]
            # Fetched on a worker (3d / E2 in the navigation review: inline, a server that stopped
            # answering froze everything, Back included, for 20 s or more), and the bind posted
            # back to this thread (_bindFetchedHubs()) - the bind changes control geometry
            # (_setRoleGeometry()), which stays on the main thread. The window shows its sidebar
            # and tabs meanwhile, with the hero hidden (no_hero_art, above). A hub cache was tried
            # too and dropped (the user's choice, 2026-09-26): it saved ~230 ms per Back on the
            # AM6B, not enough to be felt, against up to 5 minutes of staleness.
            callback = self._recommendedHubsFetchedFor(generation)
            task = home.SectionHubsTask().setup(self.section, callback, section_keys)
            self.tasks.add(task)
            backgroundthread.BGThreader.addTasksToFront([task])

            self.setBoolProperty("initialized", True)
        elif self.showPanelControl and not self.refill:
            self.showPanelControl.newControl(self)
            self.keyListControl.newControl(self)
            self.showPanelControl.selectItem(0)
            self.setFocusId(self.VIEWTYPE_BUTTON_ID)
            self.setBoolProperty("initialized", True)
        else:
            self._gridTiming = timing
            try:
                self.doRefill()
            finally:
                self._gridTiming = None
            timing.log()

    def _consumeRestoreItemPos(self, count):
        """One-shot: the grid position popBack() asked to land back on (_captureRootRestoreState()/
        self._pendingRestoreItemPos), clamped to the freshly (re)loaded item count, or 0 if
        there's nothing pending or it's out of range (e.g. the section's content changed size
        since the position was captured). Clears the pending state regardless of outcome, so a
        request that doesn't apply to this fill (e.g. it was captured for 'recommended' mode, and
        this section unexpectedly landed on 'library' instead) can't leak into some later,
        unrelated fill(). Called from fillShows()/fillPlaylists()/fillPhotos() in place of each
        one's own hardcoded selectItem(0)."""
        pos = self._pendingRestoreItemPos
        self._pendingRestoreItemPos = None
        if pos is not None and 0 <= pos < count:
            return pos
        return 0

    def doRefill(self):
        # Defensive: a hub-row restore request (_pendingRestoreHubId) only ever gets consumed by
        # _recommendedHubsCallback(), which doRefill() never leads to (see the 'recommended'
        # branch above, which returns before reaching here) - clear it here too so a mismatched
        # capture (contentMode ended up 'library'/'playlists' instead of 'recommended') can't sit
        # around and wrongly apply to some later, unrelated 'recommended' entry.
        self._pendingRestoreHubId = None
        # The previous panel's ListItems are about to be freed and replaced; bump the
        # generation so any caller holding a stale ListItem reference can detect it.
        self._retireListItems()
        self.showPanelControl = kodigui.ManagedControlList(self, self.POSTERS_PANEL_ID, 5)

        # 'playlists' deliberately excluded (unlike photodirectory/collection): it still needs the
        # ITEM_TYPE (Audio/Video) button visible - script-plex-squares.xml.tpl's own control 312
        # visibility handles that, and controls 211/311/310 (genre/category filters, which playlists
        # have no concept of) are hidden there directly by checking Window.Property(media) instead.
        hideFilterOptions = self.section.TYPE in ('photodirectory', 'collection')

        self.keyListControl = kodigui.ManagedControlList(self, self.KEY_LIST_ID, 27)
        self.setProperty('disable_playback', self.section.TYPE == 'movies_shows' and '1' or '')
        self.setProperty('subDir', self.subDir and '1' or '')
        self.setProperty('no.options', self.section.TYPE != 'photodirectory' and '1' or '')
        self.setProperty('unwatched.hascount', self.section.TYPE == 'show' and '1' or '')
        util.setGlobalProperty('sort', self.sort)
        # Seed the filter display from current state (value filter + any active booleans),
        # not just unwatched, since boolFilters persists across sessions.
        self.updateFilterDisplay()
        display = self.sortDisplay()
        if display is None:
            self.resetSort()
        else:
            self.setProperty('sort.display', display)
            self.updateSortIcon()
        self.setProperty('media.itemType', self.itemType or self.section.TYPE)
        self.setProperty('media.type', TYPE_PLURAL.get(self.itemType or self.section.TYPE, self.section.TYPE))
        self.setProperty('media', self.section.TYPE)
        self.setProperty('hide.filteroptions', hideFilterOptions and '1' or '')
        # Library grid screens never want the sharp top-right hero-art box
        # (default_background.xml.tpl) - only Recommended's hub-focused item does. no_hero_art is
        # otherwise only ever written by the Recommended-tab hero-art code (updateHeroFrom()/
        # _setNoHeroArt(), only reachable from contentMode == 'recommended'), so without this,
        # whatever a previous visit to Recommended last left the property at just persists
        # unchanged into library mode - not reliably hidden, just whatever it happened to be.
        #
        # Belt-and-braces only, as of the library.xml.tpl change: that template now passes
        # suppress_hero_art=True into default_background.xml.tpl, so the hero-art controls aren't
        # rendered into any template in this chain at all and there is nothing left for this
        # property to hide. Kept because it costs nothing and keeps the property honest for
        # anything that reads it, but note it CANNOT be relied on by itself - onFirstInit()'s
        # `elif self.showPanelControl and not self.refill` fast path skips doRefill() entirely on
        # every view-type swap, so on a swapped-into window this never runs (live-confirmed: the
        # hero-art box stayed visible through every view cycle until the section was left and
        # re-entered). The same fast path drops nine other property writes from this method.
        self._setNoHeroArt(True)

        self.setTitle()
        self.setBoolProperty("initialized", True)
        kodigui.markStep(self.__dict__.get('_gridTiming'), 'refill setup')
        self.fill()
        self.refill = False
        self._retryEmptyAfterReturn()
        if self.updateServerUnavailable():
            self.setFocusId(self.SERVER_RETRY_BUTTON_ID)
        elif self.getProperty('no.content') or self.getProperty('no.content.filtered'):
            self.setFocusId(self.SECTION_LIST_ID)
        else:
            self.setFocusId(self.POSTERS_PANEL_ID)

    def _deferOpenSection(self, section, force=False):
        """Open section in place, as a posted navigation request (MultiWindow.postNav()), for the
        "self is HOME" case both this class's own goHome() and windowutils.py's
        SidebarMixin._dispatchSectionOpen() use.

        force=True (threaded through from an explicit sidebar click on the already-active section,
        SidebarMixin.sectionClicked()) is passed straight through to openSection() - otherwise its
        own `section == self.section` no-op would swallow a click that's meant to reset the section
        in place, the same case serverRefresh() already carries force=True through for.

        Used to be a single-flight threading.Timer, after a live-confirmed kodi.log showed 7
        concurrent openSection() calls on 7 different threads racing to mutate
        self.section/self._current/self._backStack (a held-down Home button the prime suspect).
        cancel() couldn't stop a timer already mid-run, so that only narrowed the race. Posted
        requests all run one at a time on the main thread, and a newer one replaces any still
        pending.
        """
        self.postNav('openSection', self.openSection, args=(section,), kwargs={'force': force})

    def navigate(self, intent):
        """GoHomeMixin.navigate() (windowutils.py), for the window that acts on a NavIntent
        (navintent.py). Reached from this window's own views and hosted screens (the Home button,
        goHome() and goHomeRoot(), a sidebar click inside a screen, the screensaver's
        library.back_home and monitor.py's on-sleep action).

        As Home (windowutils.HOME): posted, like every other swap (MultiWindow.postNav()). A section
        wins over root - no caller asks for both, and a root reset would just be replaced by the
        section's own fresh open. The old goHome() override did the same, and fell back to the
        mixin's descendant-oriented dismiss-and-show for any other instance, which here would kill
        the whole session: forceDismiss() also dismisses self._background (the _MWBackground
        hosting the session's outer modal() call) and closeWithCommand() doClose()s.

        Any other LibraryWindow (a nested one outside the chain, e.g. a collection opened
        blocking) leaves for Home like any other window. Checking `self is HOME` here, rather than
        delegating to _liveChainHost(), is what keeps a window that hosts itself from calling
        itself forever - what GoHomeMixin's old ...Direct() variants existed for."""
        if self is not windowutils.HOME:
            self.leaveFor(intent)
            return
        util.DEBUG_LOG('Navigate: {0} at Home', intent)
        if intent.kind == navintent.NavIntent.CLOSE_SESSION:
            # Not posted: ending the session closes this window, which the queue's own wait loop
            # runs inside. main.py reads closeOption once this window's modal() returns.
            # A nested window's close reaches here twice, as it arrives (processCommand()) and
            # from returnHere(); the second finds the session already closing.
            if not self._allClosed:
                self.closeOption = intent.option
                self.doClose()
            return
        section = self.resolveSection(intent.section)
        if section is not None and (section != self.section or intent.force):
            self._deferOpenSection(section, force=intent.force)
        elif intent.root:
            self._homeResetTiming = kodigui.StepTiming('Home reset')
            self.postNav('goHomeRoot', self._goRootNow)

    def returnHere(self, intent):
        """Home, from a window outside the chain that's closing (GoHomeMixin.leaveFor()). Posted: the
        queue runs from this window's own view once control has unwound back to it, so after every
        window the intent still passes through has closed. Coming to the front at once, while those
        were still open above it, left Kodi on the blank base window once they closed for real
        (live on the AM6B, 2026-09-27: "Go to Music" from the current playlist over the music
        player)."""
        util.DEBUG_LOG('Navigate: {0} returning Home, once the closing windows are gone', intent)
        self.postNav('returnHere', self._returnHereNow, args=(intent,))

    def _returnHereNow(self, intent):
        """The posted half of returnHere(): come back to the front, reset to the root if asked
        (show()/onReInit()), and open the section if one was asked for - force=True, as every
        reconstruction in this family, since intent.force is what decided it when the section is
        already showing."""
        util.DEBUG_LOG('Navigate: {0} back at Home', intent)
        if intent.kind == navintent.NavIntent.CLOSE_SESSION:
            self.navigate(intent)
            return
        section = self.resolveSection(intent.section)
        self.go_root = intent.root
        self.show()
        if section is not None and (section != self.section or intent.force):
            self.postNav('openSection', self.openSection, args=(section,), kwargs={'force': True})

    def resolveSection(self, section):
        """A section asked for by key - a str, or plexobjects.PlexValue, from getLibrarySectionId():
        the music player's / Album screen's / photo directory's "Go to <section>" - as the
        sidebar's own section object. openSection() on a bare key blew up on `section.server`
        (live, 2026-09-18); None (going to the root) if the sidebar has no such section."""
        if isinstance(section, six.string_types):
            key, section = section, self.sectionByKey(section)
            if section is None:
                util.DEBUG_LOG('Navigate: no sidebar section for key {0}, going to root', key)
        return section

    def _goRootNow(self):
        """The posted half of goHome(with_root=True)/goHomeRoot(): go to Home's root, first row,
        item 0 - rebuilt if a section or chain is showing, reset in place if Home already is (see
        show()/onReInit())."""
        kodigui.markStep(self.__dict__.get('_homeResetTiming'), 'queued')
        self.go_root = True
        self.show()

    def _needsRootReconstruct(self):
        """True if reaching go_root's true root (home_section, no chain in progress) requires a
        real reconstruction (openSection()) rather than just a focus reset - i.e. either we're not
        already showing home_section, or a real-shell chain (_isHostedShell/_backStack - swapTo(),
        __init__'s own comment) is currently hosted on top of it. self.section never changes while
        a chain is hosted (popBack()'s own comment: "root state is never mutated while a shell is
        hosted"), so section alone isn't enough to detect a chain opened *from* home_section - the
        exact case that was missing before this method existed. Shared by show()/onReInit() below
        so both act on the same decision."""
        return self._isHostedShell or bool(self._backStack) or self.section != home.home_section

    def show(self, **kwargs):
        """MultiWindow has no native show() of its own (kodigui.py) - unlike HomeWindow's own
        show() override (home.py), which just calls super().show() then checks go_root inline.
        Delegate to whichever concrete shell is currently active (the closest equivalent to
        "reactivate this window"), then run the same go_root check - monitor.py's actionHome() and
        windowutils.py's GoHomeMixin/SidebarMixin.goHomeRoot() all just set self.go_root and call
        self.show(), expecting exactly this contract. Guarded on self._current existing: show()
        can be reached (windowutils.HOME.show()) after real teardown has already del'd it.

        Skips reactivating self._current when onReInit() below is about to reconstruct anyway
        (_needsRootReconstruct()) - live-confirmed bug otherwise: self._current.show() natively
        reactivates whatever real shell is currently hosted (e.g. EpisodesWindow), which is enough
        to re-trigger that shell's own onReInit() (never monkeypatched to the host's - see
        _setupCurrent()'s own comment) before this method's own onReInit() call below ever gets to
        close it - EpisodesWindow.onReInit() in particular re-selects an episode from watch
        progress, visibly jumping focus to the wrong one for a fraction of a second before the
        real teardown/reconstruct lands. Only the lightweight "already on home_section, no chain"
        case below still needs this reactivation at all.
        """
        reconstructing = self.go_root and self._needsRootReconstruct()
        if self._current and not reconstructing:
            self._current.show(**kwargs)
            kodigui.markStep(self.__dict__.get('_homeResetTiming'), 'reactivate')
        if reconstructing:
            # A rebuild, not an in-place reset: the Swap timing line covers it.
            self._homeResetTiming = None
        if self.go_root:
            self.onReInit()

    def onReInit(self):
        # The grid's Play and "Shuffle All" guard (playButtonClicked()) clears once the view shows
        # again, e.g. back from the player, as PlaybackBtnMixin.onReInit() does. This override
        # used to skip it, so after one Play both did nothing until a section or tab switch.
        PlaybackBtnMixin.onReInit(self)
        # Another window may have written the global key property meanwhile.
        self._shownKey = None

        if self.go_root:
            # Ported from HomeWindow's onReInit() go_root handling (home.py) - see
            # quiet-orbiting-heron.md's Cold Start plan. Consumed by the Home-button action
            # (MultiWindow.goHomeAction(), kodigui.py) and goHome()/goHomeRoot()
            # (windowutils.py's GoHomeMixin/SidebarMixin) - all three just set self.go_root and
            # call self.show(), same contract HomeWindow's version already has.
            self.go_root = False
            if self._needsRootReconstruct():
                # Deferred, not called inline: openSection()'s doClose()-based swap, nested
                # synchronously under this native onReInit() callback, is the same shape as the
                # confirmed Kodi core OnAction() reentrancy crash this plan's "Known Kodi core bug"
                # section documents (SKIN_RELOAD_DEFER_SECONDS, windowutils.py) - untested whether
                # onReInit() is actually exposed to it the same way OnAction() is, so deferring
                # here too rather than assuming it's safe.
                #
                # force=True unconditionally: needed whenever _needsRootReconstruct() returned True
                # because of a hosted chain rather than a differing section (self.section can
                # already equal home_section in that case - popBack()'s own comment on why root
                # state never changes while a shell is hosted - which openSection()'s own no-op
                # guard would otherwise wrongly honor). Harmless when the section genuinely differs
                # too, same as every other force=True caller in this dispatch family.
                #
                # The rebuilt Home view lands on the first row, item 0 by itself: openSection() is
                # fresh by default, and onFirstInit() focuses the anchor row.
                self.postNav('openSection', self.openSection, args=(home.home_section,), kwargs={'force': True})
            else:
                # Already showing Home: reset it in place to the first row, item 0 (the Home
                # rule), then have routeFocus() ignore the stray focus event this window's
                # reactivation fires, until the reset's own focus event arrives (see routeFocus()).
                # Not needed on the rebuild branch above - the new window sets its own focus.
                self._goRootAwaitFocus = self._resetHubsToTop()
                self._goRootAwaitUntil = time.time() + 1.0
                kodigui.markStep(self.__dict__.get('_homeResetTiming'), 'reset')
            return

        if self.refill and self.contentMode != 'recommended':
            self.doRefill()
        if player.PLAYER.bgmPlaying:
            player.PLAYER.stopAndWait(fade=util.addonSettings.themeMusicFade, deferred=True)

    def _dispatchNativeAction(self, action):
        """routeAction() below funnels both its branches through here instead of calling
        kodigui.MultiWindow.routeAction() directly, to intercept NAV_BACK/PREVIOUS_MENU before that
        base class's own default handling (self.doClose(), kodigui.py) - correct for an ordinary
        in-session LibraryWindow (closing just reveals whatever opened it, e.g. Home used to be),
        wrong once this IS the cold-start root (windowutils.HOME): there's nothing left underneath
        to reveal, so a bare doClose() here silently exits the whole addon. Live-confirmed
        regression (pressing back exited with no confirmation), fixed here - ported from
        HomeWindow's own NAV_BACK handling (home.py's onAction()).
        """
        if (action == xbmcgui.ACTION_PREVIOUS_MENU or action == xbmcgui.ACTION_NAV_BACK) and self is windowutils.HOME:
            if self.changingServer:
                # fixme: cheap way of avoiding an early exit after a server change - ported from
                # HomeWindow's identical guard (home.py's onAction()).
                return True

            if self.section != home.home_section:
                # Not at the true root yet: Back goes to Home's root, the same intent as the Home
                # button, posted like every other swap (navigate()).
                self.navigate(navintent.home(root=True))
                return True

            if self._checkingForExit or util.getSetting('disable_exit_on_back', False):
                return True

            try:
                self._checkingForExit = True
                ex = self.confirmExit()
                # 0 = exit; 1 = minimize; 2/None = cancel
                if ex.button in (2, None):
                    return True
                elif ex.button == 1:
                    util.setGlobalProperty('is_active', '')
                    xbmc.executebuiltin('ActivateWindow(10000)')
                    return True
                elif ex.button == 0:
                    self._shuttingDown = True
                    background.setShutdown()
                    self.navigate(navintent.closeSession("quit" if ex.modifier == "quit" else "exit"))
                    return True
            finally:
                self._checkingForExit = False
            return True

        return kodigui.MultiWindow.routeAction(self, action)

    def routeAction(self, action):
        """Every action on the current view comes here first, through routeActionToHost(): the
        first line of each hosted screen's onAction(), and of kodigui.MultiWindowView's for the
        grid and Recommended views. Returns True when the action was used here; False hands it
        back to the view's own onAction().

        The order: sidebar popups; the view's own Back steps (handleBack()), then Back through the
        chain; the sidebar, server and user buttons; the grid's or Recommended's own handler
        (viewAction()); then Back at Home's root and the Home button (_dispatchNativeAction()).
        This method reads only the controls every view shares; each view's own controls are read
        by its own handler (I4 in the navigation review)."""
        if self._shuttingDown:
            return True

        # belt: real user input ends the post-go_root wait (see routeFocus()), in case the reset's own
        # focus event never arrives.
        if self._goRootAwaitFocus is not None:
            logHomeReset(self, 'input before the focus event')
        self._goRootAwaitFocus = None

        # Dismiss the sidebar user/server popup first, before it can ever reach the back-stack
        # pop below - see dismissSidebarPopupOnBack()'s own comment (windowutils.py) for the bug
        # this fixes: back while the popup was open used to pop the descendant chain a step
        # instead of just closing the popup.
        if action in (xbmcgui.ACTION_PREVIOUS_MENU, xbmcgui.ACTION_NAV_BACK) and \
                self.dismissSidebarPopupOnBack(target=self._sidebarTarget()):
            return True

        # The showing view's own Back steps (handleBack()) come before the chain pops below, so
        # they apply mid-chain too: a hosted screen's (kodigui.BaseWindow), and the grid's snap to
        # item 0 (GridMixin.gridBack()), e.g. in a collection's grid reached with a non-empty
        # _backStack. Which actions count as Back is the view's (BACK_ACTIONS). On an error, Back
        # still pops rather than doing nothing.
        if action in getattr(self._current, 'BACK_ACTIONS', ()):
            try:
                if self._current.handleBack():
                    return True
            except Exception:
                util.ERROR()

        # Descendant-chain back-stack (hashed-orbiting-pizza.md Phase 1) - swapTo() always
        # pushes a root-restore entry on the genesis swap out of this window's own grid, so
        # _backStack is guaranteed non-empty whenever a real shell is hosted; an empty stack
        # therefore unambiguously means "never started a chain," falling through to every branch
        # below exactly as before. Must return immediately, never fall through to the outgoing
        # shell's own onAction() - every real shell sets dismissOnClose = True, so a fallthrough
        # would double-process the same NAV_BACK.
        #
        # Posted, not called inline (MultiWindow.postNav()): popBack()/swapTo() end in the same
        # doClose()-based reconstruct openSection()/switchTab() use, and running that from inside
        # routeAction() itself is the shape hashed-orbiting-pizza.md's Phase 3 flagged as a live
        # open risk (the documented Kodi core OnAction() reentrancy bug SKIN_RELOAD_DEFER_SECONDS
        # exists for). stack=True: two quick Backs go up two levels, each once the previous one's
        # new view is ready.
        if action in (xbmcgui.ACTION_PREVIOUS_MENU, xbmcgui.ACTION_NAV_BACK) and self._backStack:
            self.postNav('popBack', self._popBackIfChained, stack=True)
            return True

        try:
            controlID = self.getFocusId()
            if controlID == self.SECTION_LIST_ID:
                if self.movingSection:
                    # Section-reorder ("Move") mode - ported from HomeWindow's identical routing
                    # (home.py's onAction()). sectionMover() owns every action while active; nothing
                    # below in this method (the context menu) should also react.
                    self.sectionMover(self.movingSection, action)
                    return True
                if action == xbmcgui.ACTION_CONTEXT_MENU:
                    # Section-item context menu - ported from HomeWindow's identical routing
                    # (home.py's onAction()).
                    show_section = self.sectionMenu()
                    if not show_section:
                        return True
                    self.serverRefresh(section=show_section)
                    return True
            elif controlID == self.SERVER_BUTTON_ID:
                # Stage 3 (quiet-orbiting-heron.md's Cold Start plan) - ported from HomeWindow's
                # identical SERVER_BUTTON_ID handling (home.py's onAction()). selectServer() below
                # is deferred, not called inline: it can end in an openSection()/doClose()-based
                # swap once the resulting change:selectedServer signal reaches serverRefresh() -
                # same reentrancy reasoning as switchTab()'s own deferred dispatch (see
                # windowutils.SKIN_RELOAD_DEFER_SECONDS).
                #
                # This whole routeAction() runs for a real hosted shell too (its onAction() calls
                # routeActionToHost() first - kodigui.BaseWindow), but self here is still the *host* - and the host's own native window has already been
                # closed (doClose()) in favor of the shell's, once a real shell is showing (see
                # MultiWindow._open()'s .modal() loop). showServers()/selectServer()/doUserOption()
                # below are all _sidebarTarget()-aware (see that method's own comment) precisely
                # because of this - every control write they do lands on self._current, the
                # genuinely live window, not self.
                if action == xbmcgui.ACTION_SELECT_ITEM:
                    self.showServers()
                    return True
                elif action == xbmcgui.ACTION_CONTEXT_MENU and util.getUserSetting('previous_server', None):
                    uuid = util.getUserSetting('previous_server', None)
                    if uuid != plexapp.SERVERMANAGER.selectedServer.uuid:
                        self.postNav('selectServer', self.selectServer, args=(uuid,))
                    return True
                elif action == xbmcgui.ACTION_MOUSE_LEFT_CLICK:
                    self.showServers(mouse=True)
                    self.setBoolProperty('show.servers', True)
                    return True
            elif controlID == self.USER_BUTTON_ID:
                # Stage 3 (quiet-orbiting-heron.md's Cold Start plan) - ported from HomeWindow's
                # identical USER_BUTTON_ID handling (home.py's onAction()). See SERVER_BUTTON_ID's
                # own comment just above on why this is safe against a real hosted shell too.
                if action == xbmcgui.ACTION_SELECT_ITEM:
                    self.showUserMenu()
                    return True
                elif action == xbmcgui.ACTION_CONTEXT_MENU and util.getSetting('previous_user'):
                    # fast-switch to the previous user, if not protected
                    uid = util.getSetting('previous_user')
                    if uid == plexapp.ACCOUNT.ID:
                        return True
                    user = plexapp.ACCOUNT.getHomeUser(uid)
                    if not user or user.isProtected:
                        self.doUserOption(force_option="switch")
                        return True
                    self.doUserOption(force_option={"fast_switch": user.id})
                    return True
                elif action == xbmcgui.ACTION_MOUSE_LEFT_CLICK:
                    self.showUserMenu(mouse=True)
                    self.setBoolProperty('show.options', True)
                    return True
            elif controlID == self.SERVER_LIST_ID:
                if action == xbmcgui.ACTION_SELECT_ITEM:
                    self.setFocusId(self.SERVER_BUTTON_ID)
                    return True

            # The showing view's own controls, when it's one of this window's own views
            # (kodigui.MultiWindowView): the grid's or Recommended's handler. A hosted screen
            # handles its own once this method hands the action back.
            if isinstance(self._current, kodigui.MultiWindowView) and self._current.viewAction(action):
                return True

        except:
            util.ERROR()

        return self._dispatchNativeAction(action)

    def routeClick(self, controlID):
        """The sidebar's clicks, for this window's own views (onClick() below) and for hosted
        screens (kodigui.BaseWindow.routeClickToHost()): written once here instead of in every
        screen (I3 in the navigation review). Control writes go to _sidebarTarget(), the hosted
        screen while one is showing."""
        if controlID == self.SECTION_LIST_ID:
            # Ported from HomeWindow's identical guard (home.py's onClick()) - while
            # self.movingSection is set, sectionMover() owns ACTION_SELECT_ITEM itself (via
            # routeAction() above) to finalize the move; an ordinary click-dispatch here on the same
            # press would otherwise also try to open whatever's now selected. Hosted screens
            # lacked this guard. The screen's own sectionClicked() runs: its Search entry searches
            # its own item's section, and a section click reaches this window through its goHome().
            if not self.movingSection:
                self._sidebarTarget().sectionClicked()
            return True

        if controlID == self.USER_LIST_ID:
            # Stage 3: shared across every content mode and hosted screen, checked before the
            # contentMode=='recommended' bypass in onClick(). Ported from HomeWindow's identical
            # USER_LIST_ID handling (home.py's onClick()) - minus self._skipNextAction,
            # input-suppression state LibraryWindow doesn't have and only matters for the
            # refresh_users/local_users options staying "open".
            target = self._sidebarTarget()
            self.doUserOption(target=target)
            target.setBoolProperty('show.options', False)
            target.setFocusId(self.USER_BUTTON_ID)
            return True

        if controlID == self.SERVER_RETRY_BUTTON_ID:
            # the "isn't responding" panel, on the grid and Recommended views
            self.retryServerNow()
            return True

        if controlID == self.SERVER_LIST_ID:
            # Stage 3: same as USER_LIST_ID above. Deferred, not called inline - see the
            # SERVER_BUTTON_ID routeAction() branch's own comment for why selectServer() can't run
            # synchronously from a native callback.
            self._sidebarTarget().setBoolProperty('show.servers', False)
            self.postNav('selectServer', self.selectServer)
            return True

        return False

    def tabListClicked(self):
        """A click on the tabs row (TAB_LIST_ID), from the grid's and Recommended's own click
        handlers: both templates have the row. It isn't one of routeClick()'s shared controls,
        because Pre-play and Episodes use the same ID for their video-resolution group, and Genres
        handles its own tabs row."""
        mli = self.tabList.getSelectedItem()
        if not mli:
            return

        if self._tabListIsPlaylists:
            # Music/Video: _applyItemTypeChoice() is an in-place refill (reset()/fill()), never a
            # doClose()-based window reconstruction - none of the deferral below applies, same as
            # itemTypeButtonClicked()'s own dropdown-result call to it.
            self._applyItemTypeChoice(mli.getProperty('item.type'))
            return

        # Posted (MultiWindow.postNav()), not a direct switchTab() call: confirmed as
        # xbmc/xbmc#27552/#27239, an upstream Kodi core bug - CGUIWindow::OnAction()'s
        # focused-control parent walk crashes if the window/skin gets reloaded nested underneath
        # the very OnAction()/onClick() call that triggered it. switchTab()'s doClose() is exactly
        # that kind of reload, so it must never run synchronously, inline, from this callback - see
        # the #27239 note in windowutils.py for the full diagnosis.
        mode = mli.getProperty('content.mode')
        if mode == 'categories':
            self.postNav('browseGenres', self.browseGenres)
        elif mode == 'collections':
            self.postNav('switchToCollections', self.switchToCollections)
        else:
            item_type = self._libraryTabItemType() if mode == 'library' else None
            self.postNav('switchTab', self.switchTab, args=(mode,), kwargs={'item_type': item_type})

    def searchButtonClicked(self):
        # Watchlist's own server is plex.tv's, which isn't searched here
        server = None if self.section == home.watchlist_section else self.section.server
        self.processCommand(search.dialog(self, section_id=self.section.key, server=server))

    def buildSectionList(self):
        """The shared sidebar build (windowutils.SidebarMixin), with Watchlist made afresh first:
        this is the only window that makes it (sidebar_model.refreshWatchlistSection())."""
        sidebar_model.refreshWatchlistSection()
        windowutils.SidebarMixin.buildSectionList(self)

    def sidebarNavSettings(self):
        # Real state the section menu edits (loadNavSettings()/saveNavSettings()), so its changes
        # show on the next rebuild without reading the setting back. onFirstInit()/serverRefresh()
        # load it; this only covers a build before either.
        if self.navSettings is None:
            self.loadNavSettings()
        return self.navSettings

    def sidebarActiveSection(self, entries):
        """Home for Home; otherwise the entry for this section, or for the real library it belongs
        to. self.section.key alone only matches when the section IS a sidebar entry: a collection
        or folder carries its own key, so fall back to getLibrarySectionId() (live-confirmed
        regression: a collection opened in a nested LibraryWindow highlighted nothing). An
        entrySectionId threaded down a drill chain wins over that fallback: a collection opened
        from a cross-section filmography can live in a different section from the one to keep
        highlighted. Watchlist when entered from it with no section to follow."""
        if self.section.key == home.home_section.key:
            return home.home_section
        if self.entrySectionId is not None:
            activeLibraryId = self.entrySectionId
        else:
            getActiveLibraryId = getattr(self.section, 'getLibrarySectionId', None)
            activeLibraryId = getActiveLibraryId() if getActiveLibraryId else None
        for section in entries:
            if section.key == self.section.key or (activeLibraryId and section.key == activeLibraryId):
                return section
        if self.entrySectionId is None and self.entryFromWatchlist:
            return home.watchlist_section
        return None

    def _sidebarPlaylistsChanged(self):
        self.postUI('sidebar playlists', self._rebuildSidebar)

    def _rebuildSidebar(self):
        """Rebuild the sidebar as it stands, on the main thread (postUI())."""
        if self.closing or self._shuttingDown or self.sectionList is None:
            return
        try:
            windowutils.SidebarMixin.buildSectionList(self)
        except kodigui.ScreenClosed:
            pass

    def sectionMenu(self):
        """Context menu (ACTION_CONTEXT_MENU) for the sidebar's currently-focused section item -
        ported from HomeWindow.sectionMenu() (home.py), adapted to this window's own state:
        self.librarySettings (home.py's per-section show/hide/pin/order dict) -> self.navSettings
        (see __init__'s comment for the name-collision reason), self.saveLibrarySettings() ->
        self.saveNavSettings(). Triggered from routeAction()'s SECTION_LIST_ID/ACTION_CONTEXT_MENU
        branch, which also owns the return-value -> serverRefresh() handoff.
        """
        item = self.sectionList.getSelectedItem()
        if not item or not item.getProperty('item') or item.getProperty('is.search'):
            return

        section = item.dataSource
        choice = None
        if not section.key:
            # home section
            sections = [home.playlists_section] + plexapp.SERVERMANAGER.selectedServer.library.sections()
            options = []

            use_sep = False
            if "order" in self.navSettings and self.navSettings["order"]:
                options.append({'key': 'reset_order', 'display': T(33040, "Reset library order")})
                use_sep = True

            if util.getSetting('cache_requests'):
                options.append({'key': 'cache_reset', 'display': T(33720, "Clear all caches")})
                use_sep = True

            if use_sep:
                options.append(dropdown.SEPARATOR)

            for s in sections:
                section_settings = self.navSettings.get(section_ids.sectionId(s))
                if section_settings and not section_settings.get("show", True):
                    options.append({'key': 'show',
                                    'section_id': section_ids.sectionId(s),
                                    'display': T(33029, "Show library: {}").format(s.title)
                                    }
                                   )

            # hack for an inexistant watchlist due to it being hidden
            if util.getUserSetting("use_watchlist", True) and not self.navSettings.get(
                    section_ids.WATCHLIST_ID, {}).get("show", True):
                options.append({'key': 'show',
                                'section_id': section_ids.WATCHLIST_ID,
                                'display': T(33029, "Show library: {}").format(T(34000, 'Watchlist'))
                                })

            # Add Manage Hubs and Refresh Hubs options
            if options:
                options.append(dropdown.SEPARATOR)
            options.append({'key': 'manage_hubs', 'display': T(34080, "Manage Hubs")})
            options.append({'key': 'refresh_hubs', 'display': T(34096, "Refresh Hubs")})

            if options:
                choice = dropdown.showDropdown(
                    options,
                    pos=(660, 441),
                    close_direction='none',
                    set_dropdown_prop=False,
                    header=T(33034, "Library settings"),
                    select_index=0,
                    align_items="left",
                    dialog_props=getattr(self, 'carriedProps', None)
                )

        else:
            options = []

            # the server's own admin only: a shared server refuses these
            if (plexapp.ACCOUNT.isAdmin and section not in (home.watchlist_section, home.playlists_section)
                    and section.server.owned):
                options = [{'key': 'refresh', 'display': T(33082, "Scan Library Files")},
                           {'key': 'emptyTrash', 'display': T(33083, "Empty Trash")},
                           {'key': 'analyze', 'display': T(33084, "Analyze")},
                           dropdown.SEPARATOR]

            if section.locations and util.getSetting('path_mapping'):
                for loc in section.locations:
                    source, target = section.getMappedPath(loc)
                    loc_is_mapped = source and target
                    options.append(
                        {'key': 'map', 'mapped': loc_is_mapped, 'path': loc, 'display': T(33026,
                                                                                          "Map path: {}").format(loc)
                            if not loc_is_mapped else T(33027, "Remove mapping: {}").format(target)
                         }
                    )

                options.append(dropdown.SEPARATOR)

            options.append({'key': 'hide', 'display': T(33028, "Hide library")})
            options.append({'key': 'move', 'display': T(33039, "Move")})
            options.append(dropdown.SEPARATOR)

            if 'libraries' in util.getSetting('cache_requests') and section != home.watchlist_section:
                options.append({'key': 'section_cache_reset', 'display': T(33721, "Clear library cache (not items)")})
                options.append(dropdown.SEPARATOR)

            # Add Manage Hubs and Refresh Hubs options (not applicable to watchlist)
            if section != home.watchlist_section:
                options.append(dropdown.SEPARATOR)
                options.append({'key': 'manage_hubs', 'display': T(34080, "Manage Hubs")})
                options.append({'key': 'refresh_hubs', 'display': T(34096, "Refresh Hubs")})

            choice = dropdown.showDropdown(
                options,
                pos=(660, 441),
                close_direction='none',
                set_dropdown_prop=False,
                header=T(33030, 'Choose action for: {}').format(section.title),
                select_index=0,
                align_items="left",
                dialog_props=getattr(self, 'carriedProps', None)
            )

        if not choice:
            return

        if choice["key"] == "map":
            is_mapped = choice.get("mapped")
            if is_mapped:
                # show deletion
                source, target = section.getMappedPath(choice["path"])
                section.deleteMapping(target)
                return self.section

            else:
                # show fb - select loc to map
                d = xbmcgui.Dialog().browse(0, T(33031, "Select Kodi source for {}").format(choice["path"]), "files")
                if not d:
                    return
                pmm.addPathMapping(d, choice["path"], server=section.server)
                return self.section
        elif choice["key"] == "hide":
            self.navSettings.setdefault(section_ids.sectionId(section), {})['show'] = False
            self.saveNavSettings()
            return self.sectionList[self.sectionList.prev()].dataSource
        elif choice["key"] == "show":
            if "section_id" in choice:
                if choice["section_id"] in self.navSettings:
                    self.navSettings[choice["section_id"]]['show'] = True
                    self.saveNavSettings()
                    return self.section
        elif choice["key"] == "move":
            self.sectionMover(item, "init")
        elif choice["key"] == "reset_order":
            if "order" in self.navSettings:
                del self.navSettings["order"]
                self.saveNavSettings()
                return self.section
        elif choice["key"] == "refresh":
            with busy.BusyContext(delay=True, delay_time=0.2):
                section.refresh()
            return self.section
        elif choice["key"] == "emptyTrash":
            button = optionsdialog.show(
                T(33083, 'Empty Trash'),
                section.title,
                T(32328, 'Yes'),
                T(32329, 'No'),
                dialog_props=getattr(self, 'carriedProps', None)
            )
            if button == 0:
                with busy.BusyContext(delay=True, delay_time=0.2):
                    section.emptyTrash()
                return self.section
        elif choice["key"] == "analyze":
            with busy.BusyContext(delay=True, delay_time=0.2):
                section.analyze()
            return

        elif choice["key"] == "cache_reset":
            try:
                plexapp.util.INTERFACE.clearRequestsCache()
            except Exception as e:
                util.DEBUG_LOG("Couldn't clear requests cache: {}", e)

        elif choice["key"] == "section_cache_reset":
            try:
                util.DEBUG_LOG('Clearing requests cache for section {}...', section.title)
                section.clearCache()
            except Exception as e:
                util.DEBUG_LOG("Couldn't clear library cache: {}", e)

        elif choice["key"] == "manage_hubs":
            self.showHubSettingsDialog(section)
            # showHubSettingsDialog() has no HomeWindow-style showHubs() call to fall back on here
            # (no equivalent exists on this window) - reopening the section below, via the caller's
            # serverRefresh(section=...) handoff, is this window's own refresh mechanism, so only
            # ask for it when something actually changed.
            if self._hubsSettingsChanged:
                return self.section
            return

        elif choice["key"] == "refresh_hubs":
            return self.section

    def sectionMover(self, item, action):
        """Sidebar section-reorder ("Move") mode - ported verbatim from HomeWindow.sectionMover()
        (home.py). Entered via sectionMenu()'s 'move' choice; routeAction()/onClick() route input here
        instead of their normal handling while self.movingSection is set - see those methods' own
        comments.
        """
        def stop_moving(reset=False):
            # set everything to non-moving and re-insert search + home items
            self.movingSection = False
            self.setBoolProperty("moving", False)
            item.setBoolProperty("moving", False)
            searchmli = kodigui.ManagedListItem(T(32431, 'Search'), iconImage='script.plex/buttons/search.png')
            searchmli.setProperty('is.search', '1')
            searchmli.setProperty('item', '1')
            homemli = kodigui.ManagedListItem(T(32332, 'Home'), iconImage='script.plex/home/type/home.png',
                                              data_source=home.home_section)
            homemli.setProperty('is.home', '1')
            homemli.setProperty('item', '1')
            if home.home_section.key == self.section.key:
                homemli.setProperty('is.active', '1')
            if reset:
                if self._initialMovingSectionPos is not None:
                    self.sectionList.moveItem(item, self._initialMovingSectionPos)
                self._initialMovingSectionPos = None
            self.sectionList.insertItem(0, homemli)
            self.sectionList.insertItem(0, searchmli)
            # Finishing or cancelling a move navigates nowhere - put the selection back on the
            # section actually showing.
            self._selectActiveSection()

        if action == "init":
            self.movingSection = item
            self.setBoolProperty("moving", True)
            self._initialMovingSectionPos = self.sectionList.getSelectedPos() - 2  # account for search + home

            # remove search + home items
            self.sectionList.removeItem(0)  # search
            self.sectionList.removeItem(0)  # home (shifted to 0)
            self.sectionList.setSelectedItem(item)

            item.setBoolProperty("moving", True)

        elif action in (xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_PREVIOUS_MENU):
            stop_moving(reset=True)

        elif action in (xbmcgui.ACTION_MOVE_UP, xbmcgui.ACTION_MOVE_DOWN):
            direction = "left" if action == xbmcgui.ACTION_MOVE_UP else "right"
            index = self.sectionList.getManagedItemPosition(item)
            last_index = len(self.sectionList) - 1
            next_index = min(max(0, index - 1 if direction == "left" else index + 1), last_index)
            if index == 0 and direction == "left":
                next_index = last_index
                self.sectionList.selectItem(last_index)
            elif index == last_index and direction == "right":
                next_index = 0
                self.sectionList.selectItem(0)

            self.sectionList.moveItem(item, next_index)
            self.sectionList.selectItem(next_index)

        elif action == xbmcgui.ACTION_SELECT_ITEM:
            stop_moving()
            # store section order
            order = [section_ids.sectionId(i.dataSource) for i in self.sectionList.items if i.dataSource]
            # other servers' libraries keep their places after these
            self.navSettings["order"] = order + [k for k in self.navSettings.get("order", []) if k not in order]
            self.saveNavSettings()

    def _tabListNeedsRebuild(self, section):
        """True (and updates self._tabListIsPlaylists/self._tabListHasCategories/
        self._tabListHasCollections to match `section`) if buildTabList() needs to fully rebuild
        the tab-list's item set for it, not just rebind (newControl()) - three independent
        boundaries: the playlists/non-playlists one (Music/Video vs. Recommended/Library), the
        movie-or-show/other one (whether the Categories tab belongs there), and whether the
        Collections tab belongs there (movie/show/artist AND an actual existence probe -
        _sectionHasCollections(), cached in a module-level dict, so this is cheap on every call
        after the first for a given section). Live-confirmed bug this guards against: before this
        existed, onFirstInit() only ever compared the playlists boundary, so a swap between two
        non-playlists sections that differed only in Categories-eligibility (e.g. Show -> Artist,
        or worse, whichever section this LibraryWindow instance happened to build its tab list for
        first -> Movie) silently kept showing/hiding Categories based on stale state instead of
        the section actually on screen.
        """
        is_playlists = section.TYPE == 'playlists'
        playlist_types = self._playlistTypes() if is_playlists else ()
        if playlist_types and self.itemType not in playlist_types:
            # Open on a tab that has playlists: the remembered one - or Music, on a first visit
            # (reset()) - may have none.
            self.librarySettings.setItemType(playlist_types[0])
        has_categories = section.TYPE in ('movie', 'show')
        has_collections = section.TYPE in ('movie', 'show', 'artist') and _sectionHasCollections(section)
        # Guards against the Collections tab vanishing out from under a still-'collection'
        # ITEM_TYPE: LibrarySettings persists ITEM_TYPE per-section, so returning to a section
        # that was left on Collections restores ITEM_TYPE='collection' (openSection() ->
        # LibrarySettings.__init__() -> _loadSettings()) before this probe ever runs - if every
        # collection has since been removed, has_collections above is correctly False, but nothing
        # else would ever reset ITEM_TYPE back. Without this, the tab row falls back to
        # highlighting Library as active (updateActiveTabMarker()'s has_collections check), while
        # doRefill() keeps querying type=collection underneath it - an empty grid masquerading as
        # the section having no content at all. Same reset _libraryTabItemType() already does for
        # an explicit Library-tab click, just triggered here by the probe instead of a click.
        if not has_collections and self.itemType == 'collection':
            self.librarySettings.setItemType(section.TYPE)
        needsRebuild = (is_playlists != self._tabListIsPlaylists
                         or playlist_types != self._tabListPlaylistTypes
                         or has_categories != self._tabListHasCategories
                         or has_collections != self._tabListHasCollections)
        self._tabListIsPlaylists = is_playlists
        self._tabListPlaylistTypes = playlist_types
        self._tabListHasCategories = has_categories
        self._tabListHasCollections = has_collections
        return needsRebuild

    # The Playlists section's tabs, in order
    PLAYLIST_TYPES = ('audio', 'video')

    def _sectionPlaylists(self):
        """The server's playlists, fetched once per view: the Playlists section's tabs
        (_tabListNeedsRebuild()) and its grid (fillPlaylists()) both need them."""
        playlists = self.__dict__.get('_viewPlaylists')
        if playlists is None:
            server = plexapp.SERVERMANAGER.selectedServer
            playlists = self._viewPlaylists = list(server.playlists() or [])
            sidebar_model.notePlaylists(server, playlists)
        return playlists

    def _playlistTypes(self):
        """The playlist types the server has, in tab order."""
        present = set(pl.playlistType for pl in self._sectionPlaylists())
        return tuple(t for t in self.PLAYLIST_TYPES if t in present)

    def _hideSectionTabs(self):
        """Whether the tabs row has nothing to offer: Home (TYPE 'mixed') has no grid to switch
        to, Playlists with one type of playlist (or none) has nothing to choose between, and an
        empty library (_noteSectionEmpty()) nothing to show in any tab."""
        if self.section.TYPE == 'mixed':
            return True
        if self._tabListIsPlaylists:
            return len(self._tabListPlaylistTypes) < 2
        return (self.section.server.uuid, self.section.key) in _emptySections

    def _noteSectionEmpty(self, empty):
        """A fill or bind found this section empty, or not: remembered (_emptySections), and the
        tabs row follows straight away."""
        key = (self.section.server.uuid, self.section.key)
        if empty:
            _emptySections.add(key)
        else:
            _emptySections.discard(key)
        self.setBoolProperty('hide.section_tabs', self._hideSectionTabs())

    def buildTabList(self):
        """Populate the section-tabs row: Recommended/Library normally (plan item 0,
        quiet-orbiting-heron.md), or Music/Video for the Playlists section instead - per the
        user's own request, Playlists has no real hub content for a Recommended tab (no numeric
        section key for SectionHubsTask to fetch against) and no separate Library-tab concept
        either (always grid), so this reuses the same 2-tab row for the Audio/Video item-type
        choice instead - the same choice the old floating item-type button (312,
        ITEM_TYPE_BUTTON_ID) used to offer via a dropdown for this section, before it became
        playlists-hidden (see itemTypeButtonClicked()'s own comment). self._tabListIsPlaylists/
        self._tabListHasCategories (both kept in sync by _tabListNeedsRebuild(), called from
        onFirstInit() immediately before this) pick which flavor gets built - called once per
        LibraryWindow lifetime for a given flavor, then only rebound (newControl()) on further
        same-flavor swaps, and rebuilt again if a swap crosses either boundary - see
        _tabListNeedsRebuild()'s own comment. Recommended/Library's
        labels are plain hardcoded English, not T()-translated - no existing translation string
        to reuse there, and adding new ones was a separate concern from that original pass;
        Music/Video reuse existing strings since this is porting an already-translated dropdown's
        own option labels, not introducing new copy.
        """
        items = []
        if self._tabListIsPlaylists:
            labels = {'audio': T(32394, 'Music'), 'video': T(32053, 'Video')}
            for item_type in self._tabListPlaylistTypes:
                label = labels[item_type]
                mli = kodigui.ManagedListItem(label)
                mli.setProperty('item', '1')
                mli.setProperty('item.type', item_type)
                items.append(mli)
        else:
            for mode, label in (('recommended', 'Recommended'), ('library', 'Library')):
                mli = kodigui.ManagedListItem(label)
                mli.setProperty('item', '1')
                mli.setProperty('content.mode', mode)
                items.append(mli)
            if self._tabListHasCollections:
                # Collections - not a real contentMode (same shape as Categories below), just
                # another tab entry pointing at switchToCollections() instead of switchTab() - see
                # tabListClicked(). Reuses the exact label the item-type dropdown
                # used to show for this choice (T(32490, 'Collections')), now removed from that
                # dropdown (itemTypeButtonClicked()) since this tab replaces it.
                mli = kodigui.ManagedListItem(T(32490, 'Collections'))
                mli.setProperty('item', '1')
                mli.setProperty('content.mode', 'collections')
                items.append(mli)
            if self.section.TYPE in ('movie', 'show'):
                # Categories (genres.py's GenreBrowserWindow) - not a real contentMode (see
                # switchTab()'s own comment), just another tab entry pointing at browseGenres()
                # instead of switchTab() - see tabListClicked().
                mli = kodigui.ManagedListItem(T(34102, 'Categories'))
                mli.setProperty('item', '1')
                mli.setProperty('content.mode', 'categories')
                items.append(mli)

        self.tabList.reset()
        self.tabList.addItems(items)
        self.updateActiveTabMarker()

    def updateActiveTabMarker(self, active_override=None):
        """Update 'current' on the tab list items to highlight the active tab - self.contentMode
        normally (Recommended/Library), or the active ITEM_TYPE for the Playlists section's
        Music/Video tabs instead (self._tabListIsPlaylists). Same key-matched-property pattern
        updateActiveSectionMarker() uses for the sidebar, called both right after buildTabList()
        and whenever the active tab changes (switchTab() for contentMode,
        _applyItemTypeChoice() for ITEM_TYPE).

        active_override: genres.py's GenreBrowserWindow passes 'categories' here once hosted -
        self.contentMode is deliberately never mutated to 'categories' (switchTab()'s own
        comment), so there'd otherwise be nothing to mark that tab active while it's showing.
        Collections doesn't need an override - unlike Categories, it never leaves contentMode
        'library' at all, so ITEM_TYPE itself (checked below) is enough to tell it apart from an
        ordinary Library-tab view.
        """
        if not self.tabList:
            return

        if self._tabListIsPlaylists:
            key, active = 'item.type', self.itemType
        else:
            key = 'content.mode'
            if active_override:
                active = active_override
            elif self._tabListHasCollections and self.contentMode == 'library' and self.itemType == 'collection':
                active = 'collections'
            else:
                active = self.contentMode

        for i in range(self.tabList.size()):
            mli = self.tabList[i]
            if not mli:
                continue
            if mli.getProperty(key) == active:
                mli.setProperty('current', '1')
                # Pre-positions the list's own native cursor on the active tab, independently of
                # the 'current' property above (which only drives the underline visual) - without
                # this, Kodi's internal focus position for control 320 stays wherever it last was
                # (item 0, the first time it's ever focused) regardless of which tab is actually
                # active, so navigating up into the tab row from the grid below landed on the
                # first tab rather than the selected one (live-confirmed).
                self.tabList.selectItem(i)
            elif mli.getProperty('current'):
                mli.setProperty('current', '')

    # sectionClicked() now provided by SidebarMixin - its default _dispatchSectionOpen() covers
    # this window's needs exactly: home_section is just another section value here (LibraryWindow
    # has openSection(), so is.home no longer gets any special treatment - see that method's own
    # is.home-equivalent TYPE == 'mixed' check for how it lands on the right tab).

    def routeFocus(self, controlID):
        """Every focus event on the grid and Recommended views comes here first
        (kodigui.MultiWindowView.onFocus()); True drops it before the view's own handler sees it.

        After an in-place go_root reset (onReInit()), this window's reactivation re-focuses
        whichever control had focus before the Home press. Live-confirmed 2026-09-24: that event
        is always delivered before the reset's own setFocusId() event (0-1ms vs ~100-135ms after
        the reset), so focus still ends on the target - but handled as real focus, it records the
        old control as lastFocusID. From the sidebar (9001) or the audio widget (204) that makes
        the target's own event look like a native arrival from outside the hub range
        (_hubJustEnteredFromOutside, HubsMixin.hubFocus()), which then swallows the next real
        press. So ignore every focus event until the target's own arrives; the deadline is only a
        safety net."""
        if self._goRootAwaitFocus is not None:
            if controlID == self._goRootAwaitFocus:
                self._goRootAwaitFocus = None
                kodigui.markStep(self.__dict__.get('_homeResetTiming'), 'focus')
                logHomeReset(self)
            elif time.time() < self._goRootAwaitUntil:
                return True
            else:
                self._goRootAwaitFocus = None
                logHomeReset(self, 'focus event not seen within the wait')
        return False

    def recordFocus(self, controlID):
        """The sidebar's section marker (reselectActiveSection()) and lastFocusID follow focus.
        Called by each view's own focus handler once it has read lastFocusID for itself."""
        self.reselectActiveSection(controlID, self.lastFocusID)
        self.lastFocusID = controlID


class PostersWindow(kodigui.MultiWindowView, kodigui.ControlledWindow, windowutils.UtilMixin):
    xmlFile = 'script-plex-posters.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    POSTERS_PANEL_ID = 101
    KEY_LIST_ID = 151
    SCROLLBAR_ID = 152

    OPTIONS_GROUP_ID = 200

    PLAYER_STATUS_BUTTON_ID = 204

    SORT_BUTTON_ID = 210
    FILTER1_BUTTON_ID = 211
    FILTER2_BUTTON_ID = 212
    ITEM_TYPE_BUTTON_ID = 312

    PLAY_BUTTON_ID = 301
    SHUFFLE_BUTTON_ID = 302
    OPTIONS_BUTTON_ID = 303
    VIEWTYPE_BUTTON_ID = 304

    VIEWTYPE = 'panel'
    MULTI_WINDOW_ID = 0

    ROW_SIZE = 6
    CHUNK_OVERCOMMIT = 6

    # This view's own input, after the host's shared routing (kodigui.MultiWindowView): the
    # grid's handlers (library_grid.py).
    def viewAction(self, action):
        return self.hostedBy().gridAction(action)

    def viewClick(self, controlID):
        self.hostedBy().gridClick(controlID)

    def viewFocus(self, controlID):
        self.hostedBy().gridFocus(controlID)

    def handleBack(self):
        return self.hostedBy().gridBack()


class PostersSmallWindow(PostersWindow):
    xmlFile = 'script-plex-posters-small.xml'
    VIEWTYPE = 'panel2'
    MULTI_WINDOW_ID = 1
    ROW_SIZE = 10
    CHUNK_OVERCOMMIT = 30


class SquaresWindow(PostersWindow):
    xmlFile = 'script-plex-squares.xml'
    VIEWTYPE = 'panel'
    MULTI_WINDOW_ID = 0


class ListViewSquareWindow(PostersWindow):
    xmlFile = 'script-plex-listview-square.xml'
    VIEWTYPE = 'list'
    ROW_SIZE = 0
    MULTI_WINDOW_ID = 1


# 'panel3'/'panel4' (PostersCompactWindow/PostersSmallCompactWindow) were dropped here. A stored
# viewtype.<uuid>.<section> setting naming either one needs no migration: .get() returns None for
# an unknown key and MultiWindow.setDefault() (kodigui.py) is `self._next = default or
# self._windows[0]`, so anyone parked on a compact view lands on the plain poster grid and
# overwrites the stale string on their next view-cycle. The same goes for 'list', the 16:9 list
# view (ListView16x9Window), removed in step 12 of the navigation review: video sections are
# posters only.
VIEWS_POSTER = {
    'panel': PostersWindow,
    'panel2': PostersSmallWindow,
    'all': (PostersWindow, PostersSmallWindow)
}

class TrackListWindow(ListViewSquareWindow):
    # The music section's own list view. Only ever shows Tracks (MUSIC_VIEWTYPE_BY_ITEM_TYPE pins
    # every other music item type to the grid), so its template drops the parent's left-hand detail
    # pane entirely and styles each row as a track: title, artist, duration, on the Artist screen's
    # own Popular Tracks pill. Photos and Playlists keep the parent window/template unchanged.
    xmlFile = 'script-plex-listview-tracks.xml'


VIEWS_SQUARE = {
    'panel': SquaresWindow,
    'list': ListViewSquareWindow,
    'all': (SquaresWindow, ListViewSquareWindow)
}

# Music sections swap the list half for TrackListWindow - same keys, so everything that reads a
# view map (reset(), forcedViewWindow()) works against either without caring which it got.
VIEWS_SQUARE_MUSIC = {
    'panel': SquaresWindow,
    'list': TrackListWindow,
    'all': (SquaresWindow, TrackListWindow)
}


class RecommendedWindow(kodigui.MultiWindowView, kodigui.ControlledWindow, windowutils.UtilMixin):
    # The Recommended view: every section's hub rows and hero, Home's included. Its template began
    # as a copy of the old Home window's hub row stack and hero overlay (quiet-orbiting-heron.md,
    # Recommended-tab sharing); the hub engine (HubsMixin, library_hubs.py) fills it.
    xmlFile = 'script-plex-recommended.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    # The now-playing widget (shown while music plays) and the first hub row.
    PLAYER_STATUS_BUTTON_ID = 204
    HUB_CONTROL_ID = 400

    MULTI_WINDOW_ID = 0

    # This view's own input, after the host's shared routing (kodigui.MultiWindowView): the hub
    # engine's handlers (library_hubs.py). Its Back steps are in hubAction(), which runs after
    # the chain pops, so it keeps the default handleBack().
    def viewAction(self, action):
        return self.hostedBy().hubAction(action)

    def viewClick(self, controlID):
        self.hostedBy().hubClick(controlID)

    def viewFocus(self, controlID):
        self.hostedBy().hubFocus(controlID)


VIEWS_RECOMMENDED = {
    'panel': RecommendedWindow,
    'all': (RecommendedWindow,)
}
