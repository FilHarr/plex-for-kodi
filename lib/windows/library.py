from __future__ import absolute_import

import json
import os
import random
import threading
import time

import plexnet
import six
import six.moves.urllib.error
import six.moves.urllib.parse
import six.moves.urllib.request
from kodi_six import xbmc
from kodi_six import xbmcgui
from plexnet import playqueue
from plexnet import playlist
from plexnet import plexapp
from plexnet import plexobjects
from plexnet import util as pnUtil
from six.moves import range

from lib import backgroundthread
from lib import player
from lib import util
from lib import shuffle
from lib.path_mapping import pmm
from lib.util import T
from . import background
from . import busy
from . import collection
from . import dropdown
from . import home
from . import kodigui
from . import opener
from . import videoplayer
from . import optionsdialog
from . import preplay
from . import search
from . import subitems
from . import windowutils
from .mixins.playbackbtn import PlaybackBtnMixin
from .mixins.watchlist import removeFromWatchlistBlind
from .mixins.common import CommonMixin

KEYS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

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

THUMB_POSTER_DIM = util.scaleResolution(268, 402)
THUMB_AR16X9_DIM = util.scaleResolution(619, 348)
THUMB_SQUARE_DIM = util.scaleResolution(355, 355)
ART_AR16X9_DIM = util.scaleResolution(630, 355)

TYPE_KEYS = {
    'episode': {
        'fallback': 'show',
        'thumb_dim': THUMB_POSTER_DIM,
    },
    'season': {
        'fallback': 'show',
        'thumb_dim': THUMB_POSTER_DIM
    },
    'movie': {
        'fallback': 'movie',
        'thumb_dim': THUMB_POSTER_DIM,
        'art_dim': ART_AR16X9_DIM
    },
    'show': {
        'fallback': 'show',
        'thumb_dim': THUMB_POSTER_DIM,
        'art_dim': ART_AR16X9_DIM
    },
    'collection': {
        'fallback': 'movie',
        'thumb_dim': THUMB_POSTER_DIM,
        'art_dim': ART_AR16X9_DIM
    },
    'album': {
        'fallback': 'music',
        'thumb_dim': THUMB_SQUARE_DIM
    },
    'artist': {
        'fallback': 'music',
        'thumb_dim': THUMB_SQUARE_DIM
    },
    'track': {
        'fallback': 'music',
        'thumb_dim': THUMB_SQUARE_DIM
    },
    'photo': {
        'fallback': 'photo',
        'thumb_dim': THUMB_SQUARE_DIM
    },
    'clip': {
        'fallback': 'movie16x9',
        'thumb_dim': THUMB_POSTER_DIM
    },
}

TYPE_PLURAL = {
    'artist': T(32347, 'artists'),
    'album': T(32461, 'albums'),
    'movie': T(32348, 'Movies'),
    'photo': T(32349, 'photos'),
    'show': T(32350, 'Shows'),
    'episode': T(32458, 'Episodes'),
    'collection': T(32490, 'Collections'),
    'folder': T(32491, 'Folders'),
    'track': T(33644, 'Tracks'),
    # watchlist
    'movies_shows': T(34002, "Movies & Shows"),
}

SORT_KEYS = {
    'movie': {
        'titleSort': {'title': T(32357, 'By Title'), 'display': T(32358, 'Title'), 'defSortDesc': False},
        'addedAt': {'title': T(32351, 'By Date Added'), 'display': T(32352, 'Date Added'), 'defSortDesc': True},
        'originallyAvailableAt': {'title': T(32353, 'By Release Date'), 'display': T(32354, 'Release Date'),
                                  'defSortDesc': True, 'subDisplay': 'originallyAvailableAt', 'subDisplayExclusive': True},
        'lastViewedAt': {'title': T(32355, 'By Date Viewed'), 'display': T(32356, 'Date Viewed'), 'defSortDesc': True, 'subDisplay': 'lastViewedAt'},
        'rating': {'title': T(33107, 'By Critic Rating'), 'display': T(33108, ' Critic Rating'), 'defSortDesc': True},
        'audienceRating': {'title': T(33101, 'By Audience Rating'), 'display': T(33102, 'Audience Rating'),
                           'defSortDesc': True},
        # called "Rating" in PlexWeb, using more obvious "This is this user's rating" here
        'userRating': {'title': T(33103, 'By my Rating'), 'display': T(33104, 'My Rating'), 'defSortDesc': True},
        'contentRating': {'title': T(33105, 'By Content Rating'), 'display': T(33106, 'Content Rating'),
                          'defSortDesc': False, 'subDisplay': 'contentRating'},
        'resolution': {'title': T(32361, 'By Resolution'), 'display': T(32362, 'Resolution'), 'defSortDesc': True, 'subDisplay': 'resolutionString'},
        'duration': {'title': T(32363, 'By Duration'), 'display': T(32364, 'Duration'), 'defSortDesc': True, 'subDisplay': 'duration'},
        'unwatched': {'title': T(32367, 'By Unplayed'), 'display': T(32368, 'Unplayed'), 'defSortDesc': False},
        'year': {'title': T(32377, 'Year'), 'display': T(32377, 'Year'), 'defSortDesc': True},
        'viewOffset': {'title': T(34040, 'By Progress'), 'display': T(34041, 'Progress'), 'defSortDesc': True},
        'viewCount': {'title': T(32371, 'By Play Count'), 'display': T(32372, 'Play Count'), 'defSortDesc': True, 'subDisplay': 'viewCount'},
        'mediaBitrate': {'title': T(33731, 'By Bitrate'), 'display': T(33732, 'Bitrate'), 'defSortDesc': True, 'subDisplay': 'mediaBitrate'},
        'random': {'title': T(33730, 'Randomly'), 'display': T(33730, 'Randomly'), 'defSortDesc': True},
    },
    'show': {
        'titleSort': {'title': T(32357, 'By Title'), 'display': T(32358, 'Title'), 'defSortDesc': False},
        'year': {'title': T(32377, "Year"), 'display': T(32377, "Year"), 'defSortDesc': True},
        'show.titleSort': {'title': T(32457, 'By Show'), 'display': T(32456, 'Show'), 'defSortDesc': False},
        'originallyAvailableAt': {'title': T(32353, 'By Release Date'), 'display': T(32354, 'Release Date'),
                                  'defSortDesc': True, 'subDisplay': 'originallyAvailableAt', 'subDisplayExclusive': True},
        'rating': {'title': T(33107, 'By Critic Rating'), 'display': T(33108, ' Critic Rating'), 'defSortDesc': True},
        'audienceRating': {'title': T(33101, 'By Audience Rating'), 'display': T(33102, 'Audience Rating'),
                           'defSortDesc': True},
        # called "Rating" in PlexWeb, using more obvious "This is this user's rating" here
        'userRating': {'title': T(33103, 'By my Rating'), 'display': T(33104, 'My Rating'), 'defSortDesc': True},
        'contentRating': {'title': T(33105, 'By Content Rating'), 'display': T(33106, 'Content Rating'),
                          'defSortDesc': True, 'subDisplay': 'contentRating'},
        'unviewedLeafCount': {'title': T(32367, 'By Unplayed'), 'display': T(32368, 'Unplayed'), 'defSortDesc': True},
        'episode.addedAt': {'title': T(33042, 'Episode Date Added'), 'display': T(33042, 'Episode Date Added'), 'defSortDesc': True},
        'addedAt': {'title': T(32351, 'By Date Added'), 'display': T(32352, 'Date Added'), 'defSortDesc': True, 'subDisplay': 'addedAt'},
        'lastViewedAt': {'title': T(32355, 'By Date Added'), 'display': T(32356, 'Date Added'), 'defSortDesc': True, 'subDisplay': 'lastViewedAt'},
        'random': {'title': T(33730, 'Randomly'), 'display': T(33730, 'Randomly'), 'defSortDesc': True},
    },
    'artist': {
        'titleSort': {'title': T(32357, 'By Title'), 'display': T(32358, 'Title'), 'defSortDesc': False},
        'artist.titleSort': {'title': T(32463, 'By Artist'), 'display': T(32462, 'Artist'), 'defSortDesc': False},
        'userRating': {'title': T(33103, 'By my Rating'), 'display': T(33104, 'My Rating'), 'defSortDesc': True},
        'addedAt': {'title': T(32351, 'By Date Added'), 'display': T(32352, 'Date Added'), 'defSortDesc': True, 'subDisplay': 'addedAt'},
        'lastViewedAt': {'title': T(32369, 'By Date Played'), 'display': T(32370, 'Date Played'), 'defSortDesc': False},
        'viewCount': {'title': T(32371, 'By Play Count'), 'display': T(32372, 'Play Count'), 'defSortDesc': True, 'subDisplay': 'viewCount'},
        'random': {'title': T(33730, 'Randomly'), 'display': T(33730, 'Randomly'), 'defSortDesc': True},
    },
    'track': {
        'titleSort': {'title': T(32357, 'By Title'), 'display': T(32358, 'Title'), 'defSortDesc': False},
        'userRating': {'title': T(33103, 'By my Rating'), 'display': T(33104, 'My Rating'), 'defSortDesc': True},
        'artist.titleSort': {'title': T(32463, 'By Artist'), 'display': T(32462, 'Artist'), 'defSortDesc': False},
        'lastViewedAt': {'title': T(32369, 'By Date Played'), 'display': T(32370, 'Date Played'), 'defSortDesc': True},
        'viewCount': {'title': T(32371, 'By Play Count'), 'display': T(32372, 'Play Count'), 'defSortDesc': True}
    },
    'photo': {
        'addedAt': {'title': T(32351, 'By Date Added'), 'display': T(32352, 'Date Added'), 'defSortDesc': True, 'subDisplay': 'addedAt'},
        'originallyAvailableAt': {'title': T(32373, 'By Date Taken'), 'display': T(32374, 'Date Taken'),
                                  'defSortDesc': True, 'subDisplay': 'originallyAvailableAt', 'subDisplayExclusive': True},
        'photos.titleSort': {'title': T(32357, 'By Title'), 'display': T(32358, 'Title'), 'defSortDesc': False},
        'mediaCount': {'title': T(34042, 'By Album'), 'display': T(34043, 'Album'), 'defSortDesc': False},
    },
    'photodirectory': {},
    'collection': {},
    'mixed': {},  # home_section (home.py) - always an empty grid, so no sort options needed
    # playlists_section (Playlists port) - same "no real sort options" shape; hideFilterOptions
    # (doRefill()) hides the sort button entirely, but SORT_KEYS[self.section.TYPE] is indexed
    # unconditionally in a few places regardless, so this still needs to resolve. DEFAULT_SORT
    # ('titleSort', PlaylistsSection) falls back cleanly to SORT_KEYS['movie']['titleSort'].
    'playlists': {},
    # watchlist
    'movies_shows': {
        'watchlistedAt': {'title': T(32351, 'By Date Added'), 'display': T(32352, 'Date Added'), 'defSortDesc': True},
        'titleSort': {'title': T(32357, 'By Title'), 'display': T(32358, 'Title'), 'defSortDesc': False},
        'firstAvailableAt': {'title': T(32353, 'By Release Date'), 'display': T(32354, 'Release Date'),
                                          'defSortDesc': True},
        'rating': {'title': T(33107, 'By Critic Rating'), 'display': T(33108, ' Critic Rating'), 'defSortDesc': True},
        'audienceRating': {'title': T(33101, 'By Audience Rating'), 'display': T(33102, 'Audience Rating'),
                           'defSortDesc': True},
    }
}


def isAlphaSort(sortKey):
    """Whether sorting by this key orders items alphabetically by (some) title -
    ie. it's a 'titleSort' field, possibly namespaced (show.titleSort, artist.titleSort, ...).
    Used to decide between showing the A-Z key scrubber vs. a plain scrollbar; the scrubber
    itself only ends up with real letters when the underlying fetch actually builds one (see
    fillShows()/fillPhotos()), so this is necessary but not sufficient for that - the
    'sort.alpha' window property tracks the actual outcome per-fill.
    """
    return sortKey == 'titleSort' or bool(sortKey) and sortKey.endswith('.titleSort')


ITEM_TYPE = None

# Maps a server filter key -> (string id, fallback) for localized labels. Unknown filter
# keys fall back to the server-provided title (hybrid labels).
FILTER_LABELS = {
    'year': (32377, 'Year'),
    'decade': (32378, 'Decade'),
    'genre': (32379, 'Genre'),
    'contentRating': (32380, 'Content Rating'),
    'network': (32381, 'Network'),
    'collection': (32382, 'Collection'),
    'director': (32383, 'Director'),
    'actor': (32384, 'Actor'),
    'writer': (32402, 'Writer'),
    'producer': (34031, 'Producer'),
    'country': (32385, 'Country'),
    'studio': (32386, 'Studio'),
    'resolution': (32362, 'Resolution'),
    'audioLanguage': (34032, 'Audio Language'),
    'subtitleLanguage': (34033, 'Subtitle Language'),
    'editionTitle': (34035, 'Editions'),
    'label': (32387, 'Labels'),
    'released': (34001, 'Released'),
    'make': (32388, 'Camera Make'),
    'model': (32389, 'Camera Model'),
    'aperture': (32390, 'Aperture'),
    'exposure': (32391, 'Shutter Speed'),
    'iso': (None, 'ISO'),  # no dedicated string id; 'ISO' is universal
    'lens': (32392, 'Lens'),
    'location': (34034, 'Folder Location'),
    'unwatched': (32368, 'Unplayed'),
    'hdr': (34037, 'HDR'),
    'dovi': (34036, 'DOVI'),
}


def setItemType(type_=None):
    assert type_ is not None, "Invalid type: None"
    global ITEM_TYPE
    ITEM_TYPE = type_
    util.setGlobalProperty('item.type', str(ITEM_TYPE))

def getQueryItemType(section, fallback_to_section_type=False, force_include_collections=False):
    base_type = ITEM_TYPE

    if fallback_to_section_type and not base_type:
        base_type = section.TYPE

    if not base_type:
        return

    type_ = plexobjects.SEARCHTYPES.get(base_type)

    # combine collections into types, otherwise jumpList/firstCharacter returns different results with
    # includeCollections=1
    if force_include_collections and type_ is not None and type_ != 18:
        type_ = "{},{}".format(type_, 18)
    return type_

class CreateDefaultItemsTask(backgroundthread.Task):
    def setup(self, startPos, count, totalSize, fallback, callback, key=None):
        self.startPos = startPos
        self.count = count
        self.totalSize = totalSize
        self.endPos = self.startPos + self.count
        if self.endPos > self.totalSize:
            self.endPos = self.totalSize
        self.fallback = fallback
        self.callback = callback
        self.key = key
        return self

    def contains(self, pos):
        return self.startPos <= pos < self.endPos

    def run(self):
        if self.isCanceled():
            return

        items = []
        firstMli = None
        for x in range(self.startPos, self.endPos):
            mli = kodigui.ManagedListItem('')
            mli.setProperty('thumb.fallback', self.fallback)
            mli.setProperty('index', str(x))
            if self.key:
                mli.setProperty('key', self.key)
                if x == self.startPos:  # i.e. first item
                    firstMli = mli
            items.append(mli)
        self.callback(items, self.key, firstMli)

class ChunkRequestTask(backgroundthread.Task):
    def setup(self, section, start, size, callback, filter_=None, sort=None, subDir=False, bool_filters=None):
        self.section = section
        self.start = start
        self.size = size
        self.callback = callback
        self.filter = filter_
        self.sort = sort
        self.bool_filters = bool_filters or {}
        self.subDir = subDir
        return self

    def contains(self, pos):
        return self.start <= pos <= (self.start + self.size)

    def run(self):
        if self.isCanceled():
            return

        try:
            type_ = getQueryItemType(self.section)

            if ITEM_TYPE == 'folder':
                items = self.section.folder(self.start, self.size, self.subDir)
            else:
                # supplying this type kills all results (bug: 2025/10/21)
                if type_ == plexobjects.SEARCHTYPES["photo"]:
                    type_ = None
                items = self.section.all(self.start, self.size, self.filter, self.sort, type_=type_,
                                         bool_filters=self.bool_filters)

            if self.isCanceled():
                return
            self.callback(items, self.start)
        except plexnet.exceptions.BadRequest:
            util.DEBUG_LOG('404 on section: {0}', repr(self.section.title))


class PhotoPropertiesTask(backgroundthread.Task):
    def setup(self, photo, callback):
        self.photo = photo
        self.callback = callback
        return self

    def run(self):
        if self.isCanceled():
            return

        try:
            self.photo.reload()
            self.callback(self.photo)
        except plexnet.exceptions.BadRequest:
            util.DEBUG_LOG('404 on photo reload: {0}', self.photo)


class LibrarySettings(object):
    def __init__(self, section_or_server_id, ignoreLibrarySettings=False):
        self.ignoreLibrarySettings = ignoreLibrarySettings
        self.sectionType = None
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
        if self.ignoreLibrarySettings:
            self._settings = {}
            return

        if not self.sectionID:
            self._settings = {}
            return

        jsonString = util.getSetting('library.settings.{0}'.format(self.serverID), '')
        self._settings = {}
        try:
            self._settings = json.loads(jsonString)
        except ValueError:
            pass
        except:
            util.ERROR()

        # Live-confirmed bug without the sectionType fallback: a section that's never had its
        # own ITEM_TYPE saved (getItemType() returns None) fell all the way through to the bare
        # ITEM_TYPE module global - whatever a completely different, previously-open section
        # left it at (e.g. Music's 'album'), not anything valid for *this* section - silently
        # sending the wrong type= filter to the server and rendering as "No content available"
        # even though the library genuinely has content. sectionType (this section's own native
        # type, set in __init__) is the correct fallback for a never-configured section; the
        # bare ITEM_TYPE global is now only reached for the string-serverID construction (no real
        # section to derive a type from at all).
        setItemType(self.getItemType() or self.sectionType or ITEM_TYPE)

    def getItemType(self):
        if not self._settings or self.sectionID not in self._settings:
            return None

        return self._settings[self.sectionID].get('ITEM_TYPE')

    def setItemType(self, item_type):
        setItemType(item_type)

        if self.sectionID not in self._settings:
            self._settings[self.sectionID] = {}

        self._settings[self.sectionID]['ITEM_TYPE'] = item_type

        self._saveSettings()

    def getContentMode(self):
        """Persisted per-section tab choice ('library'/'recommended', quiet-orbiting-heron.md plan
        item 0/"Same reasoning applies one level down" - tab selection sticky per-section, the same
        way sort/filter/item-type already are). Unlike ITEM_TYPE, there's no module-level global to
        keep in sync - contentMode only ever lives as a plain instance attribute
        (LibraryWindow.contentMode) - so this is a straight read, no free-function call needed."""
        if not self._settings or self.sectionID not in self._settings:
            return None

        return self._settings[self.sectionID].get('CONTENT_MODE')

    def setContentMode(self, content_mode):
        if self.sectionID not in self._settings:
            self._settings[self.sectionID] = {}

        self._settings[self.sectionID]['CONTENT_MODE'] = content_mode

        self._saveSettings()

    def _saveSettings(self):
        jsonString = json.dumps(self._settings)
        util.setSetting('library.settings.{0}'.format(self.serverID), jsonString)

    def setSection(self, section_id):
        self.sectionID = section_id

    def getSetting(self, setting, default=None):
        if not self._settings or self.sectionID not in self._settings:
            return default

        if ITEM_TYPE not in self._settings[self.sectionID]:
            return default

        return self._settings[self.sectionID][ITEM_TYPE].get(setting, default)

    def setSetting(self, setting, value):
        if self.sectionID not in self._settings:
            self._settings[self.sectionID] = {}

        if ITEM_TYPE not in self._settings[self.sectionID]:
            self._settings[self.sectionID][ITEM_TYPE] = {}

        self._settings[self.sectionID][ITEM_TYPE][setting] = value

        self._saveSettings()


class LibraryWindow(PlaybackBtnMixin, kodigui.MultiWindow, windowutils.UtilMixin, windowutils.SidebarMixin, CommonMixin):
    bgXML = 'script-plex-blank.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'

    # Needs to be an even multiple of 6(posters) and 10(small posters) and 12(list)
    # so that we fill an entire row
    CHUNK_SIZE = 240
    CHUNK_OVERCOMMIT = 6
    DEFAULT_ITEMS_CHUNK_SIZE = 250
    DEFAULT_ITEMS_CHUNK_SIZE_BIG = 500

    # Plan item 0 (quiet-orbiting-heron.md): section-tabs row control id (includes/
    # section_tabs.xml.tpl). Defined directly on LibraryWindow (the outer, persisting object),
    # not on a specific inner shell class - unlike e.g. POSTERS_PANEL_ID, this control exists
    # identically in every content-mode's template, so it doesn't need per-shell delegation.
    TAB_LIST_ID = 320

    def __init__(self, *args, **kwargs):
        PlaybackBtnMixin.__init__(self)
        kodigui.MultiWindow.__init__(self, *args, **kwargs)
        windowutils.UtilMixin.__init__(self)
        # Only ever read/written once this instance is windowutils.HOME - see processCommand()'s own
        # comment (Home-ControlledWindow plan, item 4). Defined unconditionally here anyway, same as
        # exitCommand above, so every instance (including nested ones that never become HOME) has it.
        self._pendingSection = None
        self.section = kwargs.get('section')

        # Sidebar entry-section persistence (ported from Sidebar-Tab-Unification's
        # mellow-pondering-magpie.md, 2026-08-18) - see preplay.py's PrePlayWindow.__init__ for the
        # full reasoning. Only ever set when this instance was opened as a drilled-in child (a
        # collection/subDir view) of an ancestor tracking its own inherited entry section - a real
        # top-level section reached directly via the sidebar never passes this, so it stays None
        # here and buildSectionList() falls back to exactly its pre-existing self.section-based
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
        # Resolve to self as chain host, unconditionally - windowutils.UtilMixin.openWindow()
        # checks self._liveChainHost() to decide whether a click should swapTo() in place or
        # fall back to opener.handleOpen(); pointing this at self lets LibraryWindow's own
        # click-handlers reuse that exact generic path, same as every hosted shell. See
        # goHome()/goHomeRoot()/processCommand() below for the self-referential-delegation
        # hazard this creates and how it's avoided (windowutils.py's _goHomeDirect() etc.).
        self._chainHost = self
        # Live-confirmed reentrancy hazard (kodi.log: 7 concurrent openSection() calls, on 7
        # different threads, all racing to tear down/reconstruct self._current at the same
        # instant) - see _deferOpenSection()'s own comment below.
        self._pendingSectionTimer = None
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

        self.dragging = False

        self.cleared = True
        self.librarySettings = LibrarySettings(self.section,
                                               ignoreLibrarySettings=kwargs.get("ignoreLibrarySettings", False))

        # Sections with no library-grid content at all (home_section, so far the only one - see
        # its own TYPE comment, home.py) unconditionally force 'recommended' - 'library' is
        # permanently empty there regardless of anything persisted (see openSection()'s identical
        # check for the in-place-swap case, and its own longer comment for why this can't just be
        # left to whatever was last saved). An explicit content_mode kwarg (no current caller
        # passes one, but the parameter's existed since before this) wins next - a caller with a
        # specific reason to land on a particular tab should get it, not the user's last choice.
        # Otherwise, restore this section's own persisted choice (item 0's own "sticky per-section,
        # same as sort/filter/item-type" design point, not built until now) - falling back to the
        # 'library' default set above if this section has never had a tab choice saved yet.
        if self.section and self.section.TYPE == 'mixed':
            self.contentMode = 'recommended'
        elif kwargs.get('content_mode'):
            self.contentMode = kwargs['content_mode']
        else:
            self.contentMode = self.librarySettings.getContentMode() or self.contentMode

        # Session-lifecycle surface (quiet-orbiting-heron.md's Cold Start + windowutils.HOME
        # migration plan) - ported from HomeWindow, which owns all of this today. closeOption is
        # read by main.py's outer loop once this window's session ends (quit/exit/restart/update/
        # recompile/sign-out/switch/etc. - see shutdown()/closeWRecompileTpls() below for the
        # methods that set it). _shuttingDown is read directly, unguarded, by player.py's
        # playQueueCallback() and checked by SidebarMixin's own sectionChanged()/_sectionChanged()
        # - must exist before anything else can run, not just before shutdown() is ever called.
        # go_root/_goRootHoldUntil are consumed by onReInit()/onAction()/onFocus() below - see
        # those for the full mechanism, ported from HomeWindow's own go_root handling.
        self.closeOption = None
        self._shuttingDown = False
        self.go_root = False
        self._goRootHoldUntil = 0
        # One-shot: onFirstInit() below clears the cold-start busy spinner (background.setBusy())
        # the moment the first real content is confirmed showing, same timing main.py's old
        # create()+waitForOpen() two-step gave HomeWindow - but only once, not on every later
        # section/tab swap's own onFirstInit() re-entry (self._openBaseWinID stays set for this
        # instance's whole life, this flag doesn't).
        self._coldStartSignaled = False
        # Reentrancy guard for the exit-confirmation dialog (onAction()'s NAV_BACK handling,
        # confirmExit() below) - ported from HomeWindow's identical guard (home.py).
        self._checkingForExit = False

        self.reset()

        self.lock = threading.Lock()

        # Stage C (quiet-orbiting-heron.md, Recommended-tab sharing): minimal state so the ported
        # isHubHidden()/sortHubsByUserOrder()/getEnabledHubsForSection() below don't AttributeError
        # if ever called - values match HomeWindow.__init__'s own initial values exactly (self.hubSettings
        # = None, self.sectionHubs = {}). Nothing populates these from a live fetch yet - that's Stage D.
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
        # Set while sectionMenu()'s modal dropdown is up - guards SidebarMixin._sectionChanged()
        # (windowutils.py) against its debounce thread settling on a section change while the menu
        # is still open, same race HomeWindow's identical flag (home.py) guards against there.
        self.block_section_change = False

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
        self._hubSlideGen = 0
        self._hubSlideMovers = []
        self._hubSliding = False
        self._hubSlideThread = None
        # Hero art (plan item 11) - ported verbatim from HomeWindow.__init__'s own initial value
        # (home.py). None, not False - _setNoHeroArt()'s own no-op guard checks identity against
        # "never set yet", not just "currently False", so the very first real call (True or False)
        # always actually applies rather than being wrongly treated as a no-op.
        self._lastNoHeroArt = None
        # One-shot, ported from HomeWindow's identical flag (home.py) - consumed by
        # onFirstInit()'s 'recommended' branch below. Without this, cold start left focus on the
        # sidebar's Search entry (buildSectionList()'s default native list position) instead of
        # the first hub - live-confirmed regression, HomeWindow avoided it via this exact
        # mechanism (applyInitialHubFocus()) that never got ported when Recommended-tab sharing
        # (Stage C/D) was built.
        self._initialHubFocusApplied = False
        # Built once per LibraryWindow lifetime, then rebound via newControl() on every later
        # 'recommended' entry - see onFirstInit()'s own comment for why (a fresh discard-and-
        # recreate every entry, the original shape here, is the one remaining structural
        # difference from self.tabList/self.sectionList's proven-safe repeated-newControl()
        # pattern - live-confirmed 20+ plain section-to-section swaps clean, only 'recommended'
        # entries ever crash).
        self.hubControls = None

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

    def reset(self):
        PlaybackBtnMixin.reset(self)
        util.setGlobalProperty('sort', '')
        util.setGlobalProperty('sort.alpha', '')

        if self.section.TYPE == 'playlists' and ITEM_TYPE not in ('audio', 'video'):
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
            self.setWindows(VIEWS_SQUARE.get('all'))
            self.setDefault(VIEWS_SQUARE.get(viewtype))
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
        # TEMPORARY diagnostic logging (hashed-orbiting-pizza.md live-crash investigation) -
        # remove once the native-crash-on-second-hosting-cycle bug is understood/fixed.
        util.DEBUG_LOG("Library: _setupCurrent({0}) real_shell_count={1} isHostedShell(before)={2}",
                        cls, getattr(self, '_realShellHostCount', 0), self._isHostedShell)

        # EXPERIMENTAL fix, being tested live (hashed-orbiting-pizza.md crash investigation):
        # self._current._chainHost = self (below) creates a reference cycle between the host
        # and every hosted shell (shell -> host via _chainHost/onAction/onFirstInit's closure;
        # host -> shell via self._current, while it's current) - refcounting alone can't free a
        # genuine cycle, so the outgoing shell can survive past reassignment below until
        # Python's cyclic GC happens to run, which nothing here ever forces between swaps (the
        # only gc.collect() in this whole session is MultiWindow.open()'s, once, at session
        # end). Hypothesis: Kodi's native side needs the outgoing window's Python object torn
        # down promptly to safely reuse its window ID for the next one, and a shell kept alive
        # by an uncollected cycle is what corrupts the next window built on that reused ID -
        # live-confirmed as a 100%-deterministic native crash (identical faulting instruction
        # and address - a classic "used a not-found sentinel as a pointer" read at
        # 0xFFFFFFFFFFFFFFFF - across 5 independent captures) that only manifests after a real
        # shell has been hosted more than once before a section switch. Not proven; explicitly
        # breaking the cycle and forcing collection here is the direct test of that hypothesis.
        #
        # Breaking the cycle (clearing the outgoing shell's own back-references) has to happen
        # here, before self._current is reassigned below - but gc.collect() itself must NOT run
        # until after that reassignment, since self._current is still the only remaining
        # reference to the outgoing shell until then; collecting too early would find it still
        # referenced and do nothing. See _forceCollectOutgoing() below, called at the tail of
        # both branches once self._current genuinely points at the new object instead.
        outgoingShell = self._current
        outgoingWasRealShell = outgoingShell is not None and getattr(outgoingShell, '_chainHost', None) is not None
        if outgoingWasRealShell:
            outgoingShell._chainHost = None
            outgoingShell.onAction = None
            outgoingShell.onFirstInit = None
        del outgoingShell

        if not self._isRealShell(cls):
            self._isHostedShell = False
            kodigui.MultiWindow._setupCurrent(self, cls)
            if outgoingWasRealShell:
                self._forceCollectOutgoing(cls)
            util.DEBUG_LOG("Library: _setupCurrent({0}) thin-proxy branch complete", cls)
            return

        self._realShellHostCount = getattr(self, '_realShellHostCount', 0) + 1
        self._isHostedShell = True
        self._current = cls(cls.xmlFile, cls.path, cls.theme, cls.res, **self._nextKwargs)
        self._currentKwargs = self._nextKwargs
        self._current._chainHost = self
        # Phase 2 (hashed-orbiting-pizza.md): hand the host's own sectionList object to the
        # shell - its onFirstInit() sees a non-None sectionList and rebinds via newControl()
        # instead of rebuilding, so is.active (and everything else about which section is
        # highlighted) carries over untouched for the whole chain. self is always the host here
        # (never a shell), and the host's own sectionList is never rebuilt across its own swaps,
        # so this is the same single object handed to every shell in the chain, forward or
        # backward (popBack() reconstructs via this same method).
        self._current.sectionList = self.sectionList

        # Wraps (not replaces) the shell's own real onFirstInit - deliberately does NOT call
        # self._onFirstInit()/self.onFirstInit() the way base MultiWindow._setupCurrent() would:
        # LibraryWindow.onFirstInit() is real logic keyed to LibraryWindow's own templates
        # (sectionList/tabList/userList/serverList, POSTERS_PANEL_ID focus) and would run broken
        # against a real shell's native window (e.g. PrePlayWindow's XML has none of those
        # controls). Only registers the close.windows signal (the other host-generic line base
        # MultiWindow._onFirstInit() does, kodigui.py) - deliberately does NOT also replay
        # self._properties onto the shell the way that base method does for LibraryWindow's own
        # thin proxies. Live-confirmed bug without this exclusion: self._properties accumulates
        # whatever LibraryWindow's own 'recommended'-mode hero display last set via
        # updateHeroFrom()/setHeroInfo() (clear.logo/summary/etc. for the focused hub item) and
        # nothing overwrites those specific keys again once the user is just browsing an
        # ordinary grid - so they sit frozen at whatever hub item was focused when Home's hubs
        # first drew this session (Continue Watching's first item, in practice) for the rest of
        # the session. A real shell like PrePlayWindow happens to use the same property names
        # for its own, unrelated metadata panel, so blindly replaying the host's entire cache
        # briefly shows that frozen, unrelated content until the shell's own setInfo() overwrites
        # it a moment later - visible specifically when opening straight from a library grid
        # (nothing there ever refreshes those keys), not when opening from a hub (navigating the
        # hub row to reach the click target keeps refreshing them to something closer to
        # correct). A real shell has its own independent metadata logic; it was never meant to
        # inherit the host's display-state cache the way a thin proxy is.
        shellOnFirstInit = self._current.onFirstInit

        def _onFirstInit():
            plexapp.util.APP.on('close.windows', self.onCloseSignal)
            shellOnFirstInit()

        self._current.onFirstInit = _onFirstInit

        # Same capture-and-forward shape base MultiWindow.onAction() already uses - this
        # window's own onAction() (below) handles NAV_BACK/PREVIOUS_MENU/hosted-shell dispatch
        # itself before falling through to the shell's real onAction() for everything else.
        self._currentOnAction = self._current.onAction
        self._current.onAction = self.onAction
        # onClick/onFocus/onReInit deliberately left untouched on the shell instance - unlike
        # LibraryWindow's own thin view-type children, these seven carry real business logic.
        if outgoingWasRealShell:
            self._forceCollectOutgoing(cls)
        # TEMPORARY diagnostic logging - see this method's own top.
        util.DEBUG_LOG("Library: _setupCurrent({0}) real-shell branch complete, real_shell_count={1}",
                        cls, self._realShellHostCount)

    def _forceCollectOutgoing(self, cls):
        """EXPERIMENTAL, see _setupCurrent()'s own comment on the hypothesis this tests. Called
        only once self._current/self._currentOnAction have both already been reassigned away
        from the outgoing shell (whose own back-references to self were already cleared) - at
        this point nothing in this object graph should still reference it, so a forced
        collection should free it (and its native window resources) immediately rather than
        waiting on Python's own GC scheduling.

        Live-confirmed cosmetic cost of this being synchronous/inline: whatever's beneath the
        addon's window stack (Kodi's own base skin) can flash through for the ~50-150ms this
        blocks the next window's .modal() call - see plexobjects.py's PlexItemList/container
        objects (item<->container is a genuine cycle only the collector, not refcounting, can
        free) and this method's own git history for the investigation. Live-confirmed NOT
        rescuable by moving this call to a background thread instead (tried and reverted): it
        deadlocked Kodi outright, almost certainly because freeing the outgoing shell here
        triggers native Kodi GUI-subsystem teardown, and doing that off-thread while the main
        thread is simultaneously inside .modal()'s own native GUI code is a cross-thread
        lock-order hazard. Must stay synchronous, before self._current's caller proceeds to the
        next .modal() call - the flicker is the accepted tradeoff for not deadlocking."""
        import gc
        collected = gc.collect()
        util.DEBUG_LOG("Library: _setupCurrent({0}) forced gc.collect() after real-shell teardown, "
                        "collected={1}", cls, collected)

    def swapTo(self, cls, push=True, **kwargs):
        """Swap this already-open, already-hosting LibraryWindow to one of the seven real
        descendant shell types in place - same construct-fresh-via-_open()'s-loop pattern
        openSection()/switchTab() already use, just targeting a real shell class instead of one
        of LibraryWindow's own thin view-type proxies. See _backStack's own comment (__init__)
        for the two entry shapes pushed here."""
        if push and self._current is not None:
            if self._isHostedShell:
                self._backStack.append((self._current.__class__, self._currentKwargs))
            else:
                # Genesis swap out of LibraryWindow's own grid: push root-restore state so the
                # *last* pop of this chain reveals the grid again instead of running off the
                # stack - this is what makes _backStack empty mean "never started a chain"
                # unambiguously, every time.
                self._backStack.append((None, {'section': self.section, 'filter_': self.filter}))
        self._next = cls
        self._nextKwargs = kwargs
        self._current.doClose()

    def popBack(self):
        cls, kwargs = self._backStack.pop()
        if cls is None:
            # force=True: section == self.section will be true here (root state is never
            # mutated while a shell is hosted), which openSection()'s own no-op guard would
            # otherwise decline.
            self.openSection(force=True, **kwargs)
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
        """
        if self._isHostedShell:
            entry = (self._current.__class__, self._currentKwargs)
        else:
            entry = (None, {'section': self.section, 'filter_': self.filter})
        self.openSection(section, filter_=filter_, force=True)
        self._backStack.append(entry)

    def switchTab(self, mode):
        """Swap this already-open window between content modes ('library' grid vs.
        'recommended' hubs) in place, the same construct-fresh-via-_open()'s-loop pattern
        openSection() already uses for section swaps - see that method's own docstring for why
        in-place mutation, not a fresh object, is the safe shape here.
        """
        try:
            isCurrent = self.is_current_window
        except AttributeError:
            isCurrent = False

        if not isCurrent:
            util.DEBUG_LOG("Library: switchTab() declined - {0} not current window (descendant open, or closing)", self)
            return False

        if mode == self.contentMode:
            return False

        self.tasks.kill()
        # Settle any in-flight hub-slide animation (its own background thread, see
        # _startHubSlide()) before doClose() below tears the native window down for real -
        # otherwise that thread can still be mid-setPosition() on a control that's about to stop
        # existing. Live-confirmed as a native invalid-pointer-read crash otherwise. Harmless
        # no-op when contentMode isn't 'recommended' (self._hubSliding is only ever True there).
        self._settleHubSlide()
        self._listGeneration += 1
        self.contentMode = mode
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

    def openSection(self, section, filter_=None, force=False):
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
        """
        try:
            isCurrent = self.is_current_window
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
        # Bumped here, not just inside doRefill(), so a suspended call elsewhere that captured
        # showPanelControl/mli.dataSource before this swap can detect the invalidation the moment
        # it actually happens, not only once _open()'s loop gets back around to rebuilding.
        self._listGeneration += 1

        self.section = section
        # Keep SidebarMixin's own change-tracking in sync too (windowutils.py's
        # _dispatchSectionOpen()/_sectionChanged() gate every sidebar click/settled-focus on
        # `section == self.lastSection`) - not just whichever caller happened to reach this
        # in-place swap through that path. Live-confirmed regression without this: back-navigating
        # to Home (onReInit()'s go_root branch, which calls openSection() directly, not through
        # the sidebar dispatch) updated self.section correctly but left self.lastSection stale at
        # whatever section was showing before - so re-clicking that same section in the sidebar
        # afterward hit `section == self.lastSection` and silently no-opped, until a genuinely
        # different section was clicked first (which finally advanced lastSection for real).
        self.lastSection = section
        # hashed-orbiting-pizza.md Phase 4: a sidebar section click reaches here even while a
        # descendant chain is hosted (bubbled via PrePlayWindow etc.'s own goHome(section=...),
        # windowutils.py's GoHomeMixin/_dispatchSectionOpen(), landing on this deferred call) -
        # an explicit sidebar click is exactly the case that should abandon any chain in
        # progress, not just leave it dangling. Without this, _backStack keeps whatever
        # root-restore entry the chain pushed on its way in, live-confirmed to cause real
        # breakage on the *next* unrelated NAV_BACK/chain: onAction()'s NAV_BACK intercept below
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
        self.lastFocusID = None
        self.lastNonOptionsFocusID = None

        # Rebuilt before contentMode is decided below, not after - the new section's own
        # persisted tab choice (getContentMode()) has to come from *this* section's settings, not
        # the outgoing one's.
        self.librarySettings = LibrarySettings(
            self.section, ignoreLibrarySettings=self.librarySettings.ignoreLibrarySettings)

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
            # and a black background (that shell doesn't read 'background' the way
            # _setPlaylistBackground() sets it). Arriving from an ordinary library section never
            # hit this, since none of them force contentMode to 'recommended' in the first place.
            self.contentMode = 'library'
        else:
            # Ordinary sections (real library-grid content): restore this section's own last tab
            # choice, the same "sticky per-section" treatment sort/filter/item-type already get
            # (LibrarySettings.getItemType() and friends) - falling back to whatever contentMode
            # currently is (the previous section's tab) if this one's never had a choice saved,
            # matching this method's original carry-over behavior for that specific case.
            persisted = self.librarySettings.getContentMode()
            if persisted:
                self.contentMode = persisted

        self.reset()
        self.refill = True
        self.updateActiveSectionMarker(section)

        # TEMPORARY diagnostic logging (hashed-orbiting-pizza.md live-crash investigation) -
        # remove once the native-crash-on-second-hosting-cycle bug is understood/fixed.
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

    def processCommand(self, command):
        """UtilMixin.processCommand() (windowutils.py) - live-confirmed regression, fixed here.
        Every real descendant a 'HOME' command bubbles through (ShowWindow, EpisodesWindow,
        PrePlayWindow, a nested LibraryWindow instance, ... via openItem()/openWindow()) is meant to
        close itself on the way back - that's the base class's own, still-correct behavior,
        unchanged below. But once the bubble reaches back up to whichever ancestor opened the chain,
        and that ancestor is US (the cold-start root, windowutils.HOME), the command has arrived,
        not "left home too" - goHome()/goHomeRoot() (windowutils.py's GoHomeMixin/SidebarMixin)
        already reset us via go_root/show() before the bubble even started. Falling into the base
        class's self.doClose() here would tear down the whole session, since nothing sits underneath
        this window anymore the way HomeWindow used to. Live-confirmed: pressing the Home button
        from a descendant briefly flashed this window back up, then closed the whole addon, before
        this.

        One exception: _closeSessionWithOption() (below) primes self.closeOption directly before
        starting this same bubble, for a nested LibraryWindow instance (e.g. a movie collection)
        whose own user-options-menu close action needs to end the real session, not just itself -
        live-confirmed regression, choosing Exit from within a collection only closed the
        collection. closeOption already being set (still None on an ordinary "just go home"
        bubble) is the signal this arrived HOME to actually close, not merely to reset root.

        A second exception, live-tested: an ordinary sidebar section click/settle from any
        descendant (windowutils.py's _dispatchSectionOpen()) goes through this exact same 'HOME'
        bubble now too (Home-ControlledWindow plan, item 4), carrying the target section via
        self._pendingSection (stashed directly on this object by GoHomeMixin.goHome() before the
        bubble started, not embedded in the command string - HOME is a persistent singleton, so a
        live object reference survives however many ancestors unwind before this runs). Once
        closeOption rules out the "actually closing" case above, a pending section that differs
        from what's already showing gets swapped in the same deferred way every other openSection()
        caller already uses.
        """
        if command and command.startswith('HOME') and self is windowutils.HOME:
            pending = self._pendingSection
            self._pendingSection = None
            if self.closeOption is not None:
                self.doClose()
            elif pending is not None and pending != self.section:
                threading.Timer(windowutils.SKIN_RELOAD_DEFER_SECONDS, self.openSection, args=(pending,)).start()
            return
        if command and command.startswith('HOME'):
            # self is guaranteed not to be windowutils.HOME here (ruled out above) - go straight
            # to _processHomeCommandDirect(), not the chain-checking UtilMixin.processCommand():
            # this LibraryWindow instance always points its own _chainHost at itself (__init__),
            # so calling the wrapper would resolve _liveChainHost() back to self and call
            # host.processCommand(command) = self.processCommand(command) - which Python resolves
            # right back to this very override, recursing forever. There's no other object to
            # delegate to once "I'm not windowutils.HOME" has already been decided here; just
            # close and let the bubble continue upward, matching a plain (non-chain-hosting)
            # window's behavior exactly (the pre-Phase-1 UtilMixin.processCommand() behavior).
            windowutils.UtilMixin._processHomeCommandDirect(self, command)
            return
        # Any other command (e.g. "NODATA") - safe to hand to the generic UtilMixin.processCommand()
        # unchanged, since its 'HOME'-prefixed branch (the only one that touches _liveChainHost())
        # can't fire for a command that isn't 'HOME'-prefixed.
        windowutils.UtilMixin.processCommand(self, command)

    def confirmExit(self):
        """Ported verbatim from HomeWindow.confirmExit() (home.py) - self-contained, no
        Home-specific state. See onAction()'s NAV_BACK handling below for the caller."""
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

        self.userList.reset()
        self.userList.addItems(items)
        itemHeight = util.vscale(66, r=0)

        self.userList.setHeight((len(items) * itemHeight))
        self.getControl(self.USER_MENU_GROUP_ID).setHeight((len(items) * itemHeight))
        self.getControl(self.USER_MENU_BG_ID).setHeight((len(items) * itemHeight) + 80)

        if not mouse:
            self.setFocusId(self.USER_LIST_ID)

    def _closeSessionWithOption(self, option, shutting_down=False):
        """Every doUserOption() branch that ends a session (go_online while local, signout, exit,
        the switch/signin/go_local catch-all) needs to act on the TRUE top-level session
        (windowutils.HOME), not necessarily self. Live-confirmed regression, fixed here: self is a
        fresh, non-cold-start LibraryWindow instance whenever it was opened for a movie collection
        or similar (opener.collectionClicked()/sectionClicked() always construct a new instance,
        never an in-place swap onto the real session - home_section is the one exception, folded
        into openSection() already). Choosing Exit from within a collection just closed that
        nested instance, revealing the library grid underneath instead of actually exiting.
        """
        target = windowutils.HOME
        if shutting_down:
            target._shuttingDown = True
            util.DEBUG_LOG("Library: Initiating shutdown, setting background")
            background.setShutdown()
        else:
            util.DEBUG_LOG("Killing last background image")
            kodigui.LAST_BG_URL = None
            target.windowSetBackground(None)

        target.closeOption = option

        if self is target:
            self.doClose()
            return

        # Bubble via the same forceDismiss()+closeWithCommand('HOME') chain goHome() already uses
        # to unwind every ancestor back to the real session (proven safe/correct - this is exactly
        # how pressing Home from a descendant already works, and 'HOME' is the one bubble command
        # every window class's processCommand() already knows to propagate, unlike a bespoke
        # command string that only LibraryWindow's own override would understand). processCommand()
        # below sees closeOption already set once the bubble reaches windowutils.HOME, and actually
        # closes instead of the ordinary swallow-and-stay-open behavior a plain "go home" HOME
        # bubble gets.
        self.goHome()

    def doUserOption(self, force_option=None):
        """Ported from HomeWindow.doUserOption() (home.py) - see quiet-orbiting-heron.md's Cold
        Start plan, Stage 3. Adaptations: dialog_props reads carriedProps defensively (getattr,
        CommonMixin's own pattern) since LibraryWindow doesn't define it; storeLastBG() stays
        unported (see shutdown()'s own comment) - HomeWindow's version isn't called from here
        anyway, only from confirmExit()'s minimize branch and shutdown() itself, neither of which
        call it here either; every session-ending branch routes through _closeSessionWithOption()
        above instead of closing self directly - see that method's own comment for why.
        """
        if not force_option:
            mli = self.userList.getSelectedItem()
            if not mli:
                return

            option = mli.dataSource
        else:
            option = force_option

        self.setFocusId(self.USER_BUTTON_ID)

        if option == 'settings':
            from . import settings
            settings.openWindow()
        elif option == 'update':
            self.setBoolProperty('show.options', False)
            self.setProperty('busy', '1')
            self.setFocusId(self.SECTION_LIST_ID)
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
        """
        plexapp.SERVERMANAGER.on('new:server', self.onNewServer)
        plexapp.SERVERMANAGER.on('remove:server', self.onRemoveServer)
        plexapp.SERVERMANAGER.on('reachable:server', self.onReachableServer)
        plexapp.SERVERMANAGER.on('reachable:server', self.displayServerAndUser)
        plexapp.util.APP.on('change:selectedServer', self.onSelectedServerChange)

    def unhookSignals(self):
        plexapp.SERVERMANAGER.off('new:server', self.onNewServer)
        plexapp.SERVERMANAGER.off('remove:server', self.onRemoveServer)
        plexapp.SERVERMANAGER.off('reachable:server', self.onReachableServer)
        plexapp.SERVERMANAGER.off('reachable:server', self.displayServerAndUser)
        plexapp.util.APP.off('change:selectedServer', self.onSelectedServerChange)

    def showServers(self, from_refresh=False, mouse=False):
        """Ported from HomeWindow.showServers() (home.py) - see quiet-orbiting-heron.md's Cold
        Start plan, Stage 3. Builds/shows the shared server-switch dropdown (control 260,
        includes/sidebar_dropdowns.xml.tpl) - same include showUserMenu() above already uses."""
        with self.lock:
            selection = None
            if from_refresh:
                mli = self.serverList.getSelectedItem()
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

            self.serverList.replaceItems(items)
            itemHeight = util.vscale(100, r=0)

            listHeight = min(len(items), 9) * itemHeight
            self.getControl(self.SERVER_MENU_BG_ID).setHeight(listHeight + 80)

            # Position dropdown so it grows upward from the server button area
            buttonY = util.vscale(990, r=0)
            dropdownY = buttonY - listHeight
            self.getControl(self.SERVER_MENU_GROUP_ID).setPosition(80, dropdownY)

            for item in items:
                if item.dataSource != kodigui.DUMMY_DATA_SOURCE:
                    item.hookSignals()

            if selection:
                for mli in self.serverList:
                    if mli.uuid == selection:
                        self.serverList.selectItem(mli.pos())

            if not from_refresh and items and not mouse:
                self.setFocusId(self.SERVER_LIST_ID)

            if not from_refresh:
                plexapp.refreshResources()

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
        self.setFocusId(self.SECTION_LIST_ID)

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
        with busy.BusySignalContext(plexapp.util.APP, "change:selectedServer") as bc:
            changed = plexapp.SERVERMANAGER.setSelectedServer(server, force=True)
            if not changed:
                bc.ignoreSignal = True
                self.changingServer = False
            else:
                util.setSetting('previous_server.{}'.format(plexapp.ACCOUNT.ID), prevUUID)

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
        if self._openBaseWinID is not None and not self._coldStartSignaled:
            # Cold start (main.py) - the first real content is now confirmed showing (this native
            # onInit() callback only fires once Kodi has actually activated the window), so this is
            # the equivalent moment main.py's old create()+waitForOpen() two-step used to clear the
            # busy spinner at, just driven by the real event instead of a separate poll.
            self._coldStartSignaled = True
            background.setBusy(False)

        pnUtil.APP.on("watchlist:modified", self.setWatchlistDirty)
        util.MONITOR.on("library.back_home", self.goHomeRoot)

        # Sections with no library-grid content at all (TYPE == 'mixed' - home_section, so far the
        # only one) have nothing to switch to - hiding the row entirely rather than showing a lone
        # "Recommended" tab with nothing to switch between. Set unconditionally, every fresh
        # onFirstInit() (i.e. every content-mode/section swap, not just once) - section_tabs.xml.tpl
        # gates control 320's own <visible> on this; onAction()'s hub-row MOVE_UP interception below
        # also checks it directly before redirecting focus there, since a hidden control can't
        # usefully receive focus.
        self.setBoolProperty('hide.section_tabs', self.section.TYPE == 'mixed')

        if self.sectionList is None:
            self.loadNavSettings()
            self.sectionList = kodigui.ManagedControlList(self, self.SECTION_LIST_ID, 15)
            self.buildSectionList()
            self.displayServerAndUser()
        else:
            self.sectionList.newControl(self)

        if self.tabList is None:
            self.tabList = kodigui.ManagedControlList(self, self.TAB_LIST_ID, 5)
            self._tabListIsPlaylists = self.section.TYPE == 'playlists'
            self.buildTabList()
        else:
            self.tabList.newControl(self)
            is_playlists = self.section.TYPE == 'playlists'
            if is_playlists != self._tabListIsPlaylists:
                # Crossed the playlists/non-playlists boundary since the tabList's 2 items were
                # last built - newControl()'s usual rebind-in-place isn't enough here, the items
                # themselves (Recommended/Library vs. Music/Video) need swapping out too.
                self._tabListIsPlaylists = is_playlists
                self.buildTabList()
            else:
                self.updateActiveTabMarker()

        if self.userList is None:
            self.userList = kodigui.ManagedControlList(self, self.USER_LIST_ID, 5)
        else:
            self.userList.newControl(self)

        if self.serverList is None:
            self.serverList = kodigui.ManagedControlList(self, self.SERVER_LIST_ID, 10)
            if self is windowutils.HOME:
                # Only the true root reacts to server-list-relevant signals - see hookSignals()'s
                # own comment for why a nested instance's dropdown still works without them.
                self.hookSignals()
        else:
            self.serverList.newControl(self)

        if self.contentMode == 'recommended':
            # quiet-orbiting-heron.md Stage B: RecommendedWindow has none of the poster-grid
            # controls (POSTERS_PANEL_ID/KEY_LIST_ID) doRefill() below binds against - real
            # Recommended-tab rendering (Stage C/D) replaces this branch entirely, it doesn't
            # call doRefill() at all.
            self.refill = False

            # Stage D (quiet-orbiting-heron.md): fires every swap into 'recommended' -
            # onFirstInit() only runs when _setupCurrent() constructs a fresh _current, which for
            # this content mode only happens on a switchTab()/openSection() swap (VIEWS_RECOMMENDED
            # has a single view type, so nothing else re-triggers it). Index i always holds control
            # id HUB_CONTROL_ID+i (400-404), same fixed mapping HomeWindow.hubControls uses - no
            # rotation here (deliberately out of scope), so this mapping is also the final one for
            # this swap's whole lifetime.

            # Populates self.hubSettings from the user's already-saved hub visibility/order
            # preferences (Stage C's ported loadHubSettings(), never called until now) so
            # _recommendedHubsCallback()'s isHubHidden() filter below has real data to check
            # against, instead of always seeing "nothing hidden" (self.hubSettings starts None).
            # Synchronous (a single setting read), fine on the main thread here alongside the
            # rest of this one-time setup.
            self.loadHubSettings()

            # Reset every fresh entry, not just at __init__ - _setNoHeroArt()'s own no-op guard
            # (self._lastNoHeroArt) exists for HomeWindow, a persistent window whose control 51
            # never gets destroyed - there, "state unchanged since last time" really does mean
            # "already positioned correctly, skip redundant work". This shell's control 51 is
            # brand new every 'recommended' entry (RecommendedWindow gets torn down and
            # reconstructed by switchTab()/openSection() like any other view-type swap), so
            # self._lastNoHeroArt surviving from whatever the *previous* section's Recommended tab
            # last had is stale, not a real "nothing to do" signal - live-confirmed: if the new
            # hub's hero-art state happened to match the stale value, the guard skipped
            # _setNoHeroArt()'s real setPosition() call entirely, leaving this fresh control 51
            # wherever it defaulted to (visibly wrong row position) until a hub-to-hub move
            # produced a genuinely different value and finally forced the real positioning to run.
            self._lastNoHeroArt = None

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
                    kodigui.ManagedControlList(self, self.HUB_CONTROL_ID + 4, 3),
                )
            else:
                # newControlEmpty(), not newControl(): this section's hub content is about to
                # be replaced wholesale by hubsTask.run() below anyway, so repainting whatever
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
            # once hubsTask.run() below actually lands, so without this, whatever the *previous*
            # section's Recommended tab last set title/clear.logo/summary/background/etc. to just
            # sits there, fully visible, for that same gap. _setNoHeroArt(True) is the existing
            # single choke point for this: script-plex-recommended.xml.tpl's hero-art box is gated
            # purely on no_hero_art, and its info panel is gated on title-non-empty OR no_hero_art -
            # forcing it true here hides both regardless of whatever stale property values are
            # still sitting underneath, until the real callback below reveals (or keeps hidden)
            # the anchor hub's actual state. self._lastNoHeroArt was already reset to None just
            # above, so this isn't a no-op even when the previous section also had no hero art.
            self._setNoHeroArt(True)

            # Snapshot now (main thread, same moment the task is scheduled) so the callback can
            # tell a stale fetch (a swap landed before it ran) from a current one - same idiom as
            # _chunkCallbackFor()'s _listGeneration snapshot.
            generation = self._listGeneration

            # SectionHubsTask's 3rd arg (section_keys, passed to the server as section_ids)
            # restricts which sections' hubs get included in a home_section fetch -
            # HomeWindow.wantedSections's whole purpose (home.py), built from the same
            # navSettings-based hidden-section check buildSectionList() above already applies
            # for its own sidebar list. Leaving this unset (server default: no restriction)
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
            hubsTask = home.SectionHubsTask().setup(self.section, self._recommendedHubsCallbackFor(generation),
                                                     section_keys)
            # Run inline (main thread), not dispatched to BGThreader: _recommendedHubsCallback()
            # (below) does real Control geometry mutation (getControl().setPosition()/setHeight()
            # via _setRoleGeometry()), not just ListItem property updates like _chunkCallback()'s
            # own background-thread work elsewhere in this file - live-confirmed as a native
            # access violation (heap/vtable corruption - EXCEPTION_ACCESS_VIOLATION with a DEP/
            # execute-noncanonical-address signature, not a simple bad read) after a small handful
            # of switchTab() round trips into and back out of 'recommended', with the deferred-
            # close fix (onClick(), TAB_LIST_ID) already in place and no hub-to-hub navigation
            # involved at all - narrowing it to this one-time bind, the only remaining background-
            # thread Control mutation Stage D2 added. HomeWindow's own _bindAllHubSlots() (home.py)
            # does the identical thing from its own SectionHubsTask callback and has apparently
            # gotten away with it, but HomeWindow is a persistent window that's realistically never
            # rebound this many times in a short span the way switchTab() cycling does - if this is
            # a rare, cumulative heap-corruption bug rather than an immediate one, infrequent reuse
            # would explain why it's never surfaced there. Blocking here costs whatever the fetch
            # itself takes (~100-200ms observed) before the window finishes initializing - the
            # hubs were never rendered before this returned anyway (this is still the *first* bind,
            # not a background refresh), so nothing that used to be visible earlier is lost, just
            # shifted before the window shows instead of popping in after.
            hubsTask.run()

            if not self._initialHubFocusApplied:
                # Ported from HomeWindow.applyInitialHubFocus() (home.py) - one-time, on the very
                # first hubs draw of this LibraryWindow instance's session: land in the first
                # hub's first item instead of leaving focus on the sidebar's Search entry.
                # hubsTask.run() above is synchronous/inline, so self.visibleHubs is already
                # populated by the time this runs (or empty, if the fetch found nothing) - no
                # callback timing to race, unlike HomeWindow's own background-thread version.
                # Only acts if focus is still on the sidebar list (the native default this window
                # construction starts with) - if the user already moved focus elsewhere by the
                # time this fires, leave it alone.
                self._initialHubFocusApplied = True
                if self.getFocusId() == self.SECTION_LIST_ID and self.visibleHubs:
                    self.setFocusId(self._anchorControlId())

            self.setBoolProperty("initialized", True)
        elif self.showPanelControl and not self.refill:
            self.showPanelControl.newControl(self)
            self.keyListControl.newControl(self)
            self.showPanelControl.selectItem(0)
            self.setFocusId(self.VIEWTYPE_BUTTON_ID)
            self.setBoolProperty("initialized", True)
        else:
            self.doRefill()

    def doRefill(self):
        # The previous panel's ListItems are about to be freed and replaced; bump the
        # generation so any caller holding a stale ListItem reference can detect it.
        self._listGeneration += 1
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
        try:
            self.setProperty('sort.display',
                             SORT_KEYS[self.section.TYPE].get(self.sort, SORT_KEYS['movie'].get(self.sort))['display'])
        except TypeError:
            self.resetSort()
            self.setProperty('sort.display',
                             SORT_KEYS[self.section.TYPE].get(self.sort, SORT_KEYS['movie'].get(self.sort))['display'])
        self.setProperty('media.itemType', ITEM_TYPE or self.section.TYPE)
        self.setProperty('media.type', TYPE_PLURAL.get(ITEM_TYPE or self.section.TYPE, self.section.TYPE))
        self.setProperty('media', self.section.TYPE)
        self.setProperty('hide.filteroptions', hideFilterOptions and '1' or '')
        # Library grid screens never want the sharp top-right hero-art box
        # (default_background.xml.tpl) - only Recommended's hub-focused item does. no_hero_art is
        # otherwise only ever written by the Recommended-tab hero-art code (updateHeroFrom()/
        # _setNoHeroArt(), only reachable from contentMode == 'recommended'), so without this,
        # whatever a previous visit to Recommended last left the property at just persists
        # unchanged into library mode - not reliably hidden, just whatever it happened to be.
        # Plain setBoolProperty(), not _setNoHeroArt() - that method also repositions control 51,
        # which doesn't exist in any library-grid template (RuntimeError: Non-Existent Control).
        self.setBoolProperty('no_hero_art', True)
        # ...but _setNoHeroArt()'s own no-op guard (self._lastNoHeroArt) still needs to know about
        # this write, or it goes stale: onFirstInit()'s 'recommended' branch already resets it to
        # None unconditionally before its own _setNoHeroArt(True) call, so this doesn't change that
        # path's correctness - but _setNoHeroArt() can also be reached later via
        # updateHeroFrom()/_recommendedHubsCallback() without onFirstInit() running again in
        # between (e.g. hub-to-hub focus moves within the same 'recommended' entry), where a stale
        # guard could wrongly no-op a real property change.
        self._lastNoHeroArt = True

        self.setTitle()
        self.setBoolProperty("initialized", True)
        self.fill()
        self.refill = False
        if self.getProperty('no.content') or self.getProperty('no.content.filtered'):
            self.setFocusId(self.SECTION_LIST_ID)
        else:
            self.setFocusId(self.POSTERS_PANEL_ID)

    def _deferOpenSection(self, section):
        """Single-flight defer for the "self is HOME, safe in-place swap" case both this class's
        own goHome() and windowutils.py's SidebarMixin._dispatchSectionOpen() use (both only ever
        call this when self is windowutils.HOME). Both used to construct their own bare
        threading.Timer(SKIN_RELOAD_DEFER_SECONDS, self.openSection, ...) independently, with no
        coordination between repeated calls.

        Live-confirmed reentrancy hazard without this: kodi.log showed 7 concurrent
        openSection() calls, on 7 different threads, all racing to mutate
        self.section/self._current/self._backStack/etc. at the same instant - triggered by
        something firing goHome()/_dispatchSectionOpen() repeatedly in quick succession (a
        Home-button remote auto-repeating while held is the prime suspect, now reachable from a
        hosted shell too via onAction()'s _isHostedShell branch -> _dispatchNativeAction() ->
        base MultiWindow.onAction()'s goHomeAction() check; the immediate-click and settled-
        focus-debounce paths both firing for the same section-list navigation is a second,
        independent way to get two overlapping triggers). This is exactly the "openSection()/
        switchTab() triggered a second time before _open()'s loop caught up and reassigned
        self._current" native-crash shape ControlledWindow.doClose()'s own _closing guard
        (kodigui.py) already documents - that guard stops a second doClose() call on the same
        already-closing shell, but does nothing about N-way-concurrent openSection() calls each
        independently mutating this object's other state before/after it.

        A fresh call cancels whatever's already pending and replaces it - only the most recent
        target matters, and there is never more than one Timer in flight. cancel() only prevents
        a Timer that hasn't fired yet; it can't un-fire one already mid-run - this reduces the
        race to a much narrower window rather than proving it impossible, the same "cheap,
        low-risk mitigation, not a proven fix" status every other SKIN_RELOAD_DEFER_SECONDS use
        in this codebase already carries.
        """
        if self._pendingSectionTimer is not None:
            self._pendingSectionTimer.cancel()

        def _fire():
            self._pendingSectionTimer = None
            if self.openSection(section):
                self.lastSection = section

        self._pendingSectionTimer = threading.Timer(windowutils.SKIN_RELOAD_DEFER_SECONDS, _fire)
        self._pendingSectionTimer.start()

    def goHome(self, section=None, with_root=False):
        """GoHomeMixin.goHome() (windowutils.py) assumes self is some OTHER (descendant) window
        handing off to a separate Home singleton elsewhere: force-dismiss self, bubble a close
        command, then HOME.show(). Live-confirmed broken once self already IS that singleton
        (windowutils.HOME) - self.forceDismiss() there ALSO force-dismisses self._background (the
        _MWBackground hosting this whole session's outer blocking .modal() call,
        MultiWindow.open(), kodigui.py), and closeWithCommand() unconditionally self.doClose()s -
        both prematurely kill the entire session instead of just resetting to the root. Reached
        via MultiWindow.goHomeAction() (Home-button remote mapping, kodigui.py) and the
        "library.back_home" monitor event (onFirstInit() below) firing goHomeRoot() directly on
        this window, not a descendant - both hit this exact bug before this fix. Just reset root
        state and reactivate in that case instead of falling into the base class's
        descendant-oriented dance; fall through to it unchanged for genuine descendants.
        """
        if self is windowutils.HOME:
            if section and section != self.section:
                self._deferOpenSection(section)
            if with_root:
                self.go_root = True
                self.show()
            return
        # _goHomeDirect(), not the chain-checking goHome() wrapper: this LibraryWindow instance
        # always points its own _chainHost at itself (__init__), so the wrapper would resolve
        # _liveChainHost() back to self and recurse forever. Once this override has already
        # decided "I'm not windowutils.HOME," self-referential delegation is meaningless - see
        # windowutils.py's GoHomeMixin._goHomeDirect() for the full reasoning.
        windowutils.GoHomeMixin._goHomeDirect(self, section=section, with_root=with_root)

    def goHomeRoot(self, *args, **kwargs):
        if self is windowutils.HOME:
            self.go_root = True
            self.show()
            return
        windowutils.GoHomeMixin._goHomeRootDirect(self)

    def show(self, **kwargs):
        """MultiWindow has no native show() of its own (kodigui.py) - unlike HomeWindow's own
        show() override (home.py), which just calls super().show() then checks go_root inline.
        Delegate to whichever concrete shell is currently active (the closest equivalent to
        "reactivate this window"), then run the same go_root check - monitor.py's actionHome() and
        windowutils.py's GoHomeMixin/SidebarMixin.goHomeRoot() all just set self.go_root and call
        self.show(), expecting exactly this contract. Guarded on self._current existing: show()
        can be reached (windowutils.HOME.show()) after real teardown has already del'd it.
        """
        if self._current:
            self._current.show(**kwargs)
        if self.go_root:
            self.onReInit()

    def onReInit(self):
        if self.go_root:
            # Ported from HomeWindow's onReInit() go_root handling (home.py) - see
            # quiet-orbiting-heron.md's Cold Start plan. Consumed by the Home-button action
            # (MultiWindow.goHomeAction(), kodigui.py) and goHome()/goHomeRoot()
            # (windowutils.py's GoHomeMixin/SidebarMixin) - all three just set self.go_root and
            # call self.show(), same contract HomeWindow's version already has.
            self.go_root = False
            if self.section != home.home_section:
                # Deferred, not called inline: openSection()'s doClose()-based swap, nested
                # synchronously under this native onReInit() callback, is the same shape as the
                # confirmed Kodi core OnAction() reentrancy crash this plan's "Known Kodi core bug"
                # section documents (SKIN_RELOAD_DEFER_SECONDS, windowutils.py) - untested whether
                # onReInit() is actually exposed to it the same way OnAction() is, so deferring
                # here too rather than assuming it's safe.
                threading.Timer(windowutils.SKIN_RELOAD_DEFER_SECONDS, self.openSection,
                                 args=(home.home_section,)).start()
            else:
                self.setFocusId(self.SECTION_LIST_ID)
            # Set at the end, same as HomeWindow's own version - openSection() above is deferred
            # and can itself take a while (hub fetch/render) once it fires, so measuring the 150ms
            # hold from here (not from go_root's entry) is what keeps it long enough to actually
            # catch the stray reactivation focus event once the swap lands.
            self._goRootHoldUntil = time.time() + 0.15
            return

        if self.refill and self.contentMode != 'recommended':
            self.doRefill()
        if player.PLAYER.bgmPlaying:
            player.PLAYER.stopAndWait(fade=util.addonSettings.themeMusicFade, deferred=True)

    def _dispatchNativeAction(self, action):
        """onAction() below funnels both its branches through here instead of calling
        kodigui.MultiWindow.onAction() directly, to intercept NAV_BACK/PREVIOUS_MENU before that
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
                return

            if self.section != home.home_section:
                # Not at the true root yet - treat back as "go home" (same contract goHome()
                # itself uses), not "exit anything".
                self.go_root = True
                self.show()
                return

            if self._checkingForExit or util.getSetting('disable_exit_on_back', False):
                return

            try:
                self._checkingForExit = True
                ex = self.confirmExit()
                # 0 = exit; 1 = minimize; 2/None = cancel
                if ex.button in (2, None):
                    return
                elif ex.button == 1:
                    util.setGlobalProperty('is_active', '')
                    xbmc.executebuiltin('ActivateWindow(10000)')
                    return
                elif ex.button == 0:
                    self._shuttingDown = True
                    background.setShutdown()
                    self.closeOption = "quit" if ex.modifier == "quit" else "exit"
                    self.doClose()
                    return
            finally:
                self._checkingForExit = False
            return

        kodigui.MultiWindow.onAction(self, action)

    def onAction(self, action):
        if self._shuttingDown:
            return

        # belt: any real user input ends the post-go_root hold window early - ported from
        # HomeWindow's identical onAction() guard (home.py). See onReInit()'s go_root handling.
        if self._goRootHoldUntil:
            self._goRootHoldUntil = 0

        # Descendant-chain back-stack (hashed-orbiting-pizza.md Phase 1) - swapTo() always
        # pushes a root-restore entry on the genesis swap out of this window's own grid, so
        # _backStack is guaranteed non-empty whenever a real shell is hosted; an empty stack
        # therefore unambiguously means "never started a chain," falling through to every branch
        # below exactly as before. Must return immediately, never fall through to the outgoing
        # shell's own onAction() - every real shell sets dismissOnClose = True, so a fallthrough
        # would double-process the same NAV_BACK.
        #
        # Deferred via SKIN_RELOAD_DEFER_SECONDS, not called inline: popBack()/swapTo() end in the
        # exact same doClose()-based reconstruct openSection()/switchTab() use, and this is that
        # reload triggered synchronously from inside onAction() itself - precisely the shape
        # hashed-orbiting-pizza.md's Phase 3 flagged as a live open risk (the documented Kodi core
        # OnAction() reentrancy bug this constant exists for). Live-confirmed crash during Phase 4
        # testing on a related path (a stale _backStack entry left behind by a sidebar section
        # switch mid-chain, since fixed in openSection() - see its own comment); deferring this
        # call is the same cheap, low-risk mitigation every other onAction()-triggered reload in
        # this class already uses, not a proven fix for that specific bug.
        if action in (xbmcgui.ACTION_PREVIOUS_MENU, xbmcgui.ACTION_NAV_BACK) and self._backStack:
            threading.Timer(windowutils.SKIN_RELOAD_DEFER_SECONDS, self.popBack).start()
            return

        try:
            controlID = self.getFocusId()
            if controlID == self.SECTION_LIST_ID:
                if self.movingSection:
                    # Section-reorder ("Move") mode - ported from HomeWindow's identical routing
                    # (home.py's onAction()). sectionMover() owns every action while active; nothing
                    # below in this method (checkSectionItem()/context menu) should also react.
                    self.sectionMover(self.movingSection, action)
                    return
                if action == xbmcgui.ACTION_CONTEXT_MENU:
                    # Section-item context menu - ported from HomeWindow's identical routing
                    # (home.py's onAction()). block_section_change (see __init__'s/
                    # SidebarMixin._sectionChanged()'s own comments) guards against a debounce
                    # thread already in flight from focus movement just before this settling on a
                    # section change while the modal dropdown is up.
                    try:
                        self.block_section_change = True
                        show_section = self.sectionMenu()
                    finally:
                        self.block_section_change = False
                    if not show_section:
                        return
                    self.serverRefresh(section=show_section)
                    return
                self.checkSectionItem(action=action)
            elif controlID == self.SERVER_BUTTON_ID:
                # Stage 3 (quiet-orbiting-heron.md's Cold Start plan) - ported from HomeWindow's
                # identical SERVER_BUTTON_ID handling (home.py's onAction()). selectServer() below
                # is deferred, not called inline: it can end in an openSection()/doClose()-based
                # swap once the resulting change:selectedServer signal reaches serverRefresh() -
                # same reentrancy reasoning as switchTab()'s own deferred dispatch (see
                # windowutils.SKIN_RELOAD_DEFER_SECONDS).
                if action == xbmcgui.ACTION_SELECT_ITEM:
                    self.showServers()
                    return
                elif action == xbmcgui.ACTION_CONTEXT_MENU and util.getUserSetting('previous_server', None):
                    uuid = util.getUserSetting('previous_server', None)
                    if uuid != plexapp.SERVERMANAGER.selectedServer.uuid:
                        threading.Timer(windowutils.SKIN_RELOAD_DEFER_SECONDS, self.selectServer, args=(uuid,)).start()
                    return
                elif action == xbmcgui.ACTION_MOUSE_LEFT_CLICK:
                    self.showServers(mouse=True)
                    self.setBoolProperty('show.servers', True)
                    return
            elif controlID == self.USER_BUTTON_ID:
                # Stage 3 (quiet-orbiting-heron.md's Cold Start plan) - ported from HomeWindow's
                # identical USER_BUTTON_ID handling (home.py's onAction()).
                if action == xbmcgui.ACTION_SELECT_ITEM:
                    self.showUserMenu()
                    return
                elif action == xbmcgui.ACTION_CONTEXT_MENU and util.getSetting('previous_user'):
                    # fast-switch to the previous user, if not protected
                    uid = util.getSetting('previous_user')
                    if uid == plexapp.ACCOUNT.ID:
                        return
                    user = plexapp.ACCOUNT.getHomeUser(uid)
                    if not user or user.isProtected:
                        self.doUserOption(force_option="switch")
                        return
                    self.doUserOption(force_option={"fast_switch": user.id})
                    return
                elif action == xbmcgui.ACTION_MOUSE_LEFT_CLICK:
                    self.showUserMenu(mouse=True)
                    self.setBoolProperty('show.options', True)
                    return
            elif controlID == self.SERVER_LIST_ID:
                if action == xbmcgui.ACTION_SELECT_ITEM:
                    self.setFocusId(self.SERVER_BUTTON_ID)
                    return

            if self._isHostedShell:
                # Everything below here (grid MOVE_SET, drag, hub-rotation-ring) is specific to
                # LibraryWindow's own content area and reads state (self.contentMode,
                # self.getFocusId() delegating through __getattr__ to the hosted shell's real
                # focused control) that has nothing to do with whatever the real shell is
                # actually showing. Confirmed concretely: PrePlayWindow's own
                # ROLES_LIST_ID/REVIEWS_LIST_ID/EXTRA_LIST_ID/RELATED_LIST_ID/COLLECTION_LIST_IDS
                # (400-406) all fall inside the 399 < controlID < 500 hub-rotation check below -
                # without this early return, ordinary up/down navigation on a hosted
                # PrePlayWindow whose host was last on the 'recommended' tab would wrongly
                # trigger _startHubSlide()/hub-menu logic against host-side state. The shared
                # sidebar/server/user controls above (SidebarMixin) stay reachable either way.
                self._dispatchNativeAction(action)
                return

            if self.dragging:
                if not action == xbmcgui.ACTION_MOUSE_DRAG:
                    self.dragging = False
                    self.setBoolProperty('dragging', self.dragging)

            if self.contentMode == 'recommended':
                # Stage D2 (quiet-orbiting-heron.md): up/down on a hub-row control switches
                # which hub is logically focused (rotation-ring slide) instead of falling
                # through to the blanket return below - same interception HomeWindow's own
                # onAction() does (home.py, `elif 399 < controlID < 500:`). Explicitly re-checks
                # contentMode == 'recommended' here too (redundant with the outer if, but this
                # whole branch is exactly the kind of contentMode-independent-handler risk the
                # plan's "Known interim gaps"/item 9 flagged - control ids 400-404 only exist in
                # RecommendedWindow's template, so this is defensive, not reachable any other way
                # today, but cheap insurance against a future control-id collision).
                controlID = self.getFocusId()
                if 399 < controlID < 500 and self.contentMode == 'recommended':
                    action_id = action.getId()
                    if action_id in (xbmcgui.ACTION_MOVE_UP, xbmcgui.ACTION_MOVE_DOWN):
                        # Topmost hub, pressing up: exit the rotation ring entirely into the
                        # section-tabs row (plan item 0) instead of the silent no-op
                        # _startHubSlide() falls into at focusedHubIndex 0 - same role XML onup
                        # plays for grid content (library_posters.xml.tpl etc.), just done here in
                        # Python since hub-to-hub vertical nav is already fully Python-owned (see
                        # this branch's own docstring reference to home.py's onAction()).
                        if (action_id == xbmcgui.ACTION_MOVE_UP and self.focusedHubIndex == 0
                                and self.tabList and self.section.TYPE != 'mixed'):
                            self.setFocusId(self.TAB_LIST_ID)
                            return
                        self._startHubSlide(-1 if action_id == xbmcgui.ACTION_MOVE_UP else 1)
                        return
                    elif action_id in (xbmcgui.ACTION_MOVE_LEFT, xbmcgui.ACTION_MOVE_RIGHT):
                        # Plan item 11: sync hero art/info to the item this move is landing on.
                        # Reads getSelectedItem() directly, same as MOVE_SET's own dynamic-
                        # background update below does for the grid - Kodi's native container
                        # cursor is already at the new position by the time onAction() runs (that
                        # existing, proven pattern is what this one's modeled on), not the old one,
                        # so no special before/after ordering is needed here. Deliberately doesn't
                        # return - the actual cursor movement is Kodi's own native list behavior,
                        # not something this method does; falls through to
                        # kodigui.MultiWindow.onAction() below like anything else unhandled here.
                        self._updateHeroFromFocusedHubItem(controlID)
                    elif action == xbmcgui.ACTION_CONTEXT_MENU:
                        # Hub-item context menu - ported from HomeWindow's identical routing
                        # (home.py's onAction(), `elif action == xbmcgui.ACTION_CONTEXT_MENU:`
                        # inside its own `elif 399 < controlID < 500:` branch). Same return-value
                        # -> serverRefresh() handoff sectionMenu()'s own trigger uses above.
                        show_section = self.hubMenu(controlID)
                        if not show_section:
                            return
                        self.serverRefresh(section=show_section)
                        return

                # quiet-orbiting-heron.md Stage B: everything below this point (MOVE_SET,
                # mouse-drag, context-menu handling) reaches into grid-specific state
                # (self.showPanelControl, a ManagedControlList still bound to the old library
                # window's control 101) unconditionally - RecommendedWindow's template has no
                # such control at all, and self.showPanelControl is stale (switchTab() doesn't
                # clear it, just leaves it unused). Live-confirmed as a native use-after-free
                # crash navigating within the hub lists (MOVE_SET fires on every arrow key) -
                # unlike onFocus()/onClick()/onReInit()'s equivalent guards, this one was missed
                # the first time since it's not gated behind a single top-level if/elif. So this
                # branch still can't just fall into that code the way the non-recommended path
                # does at the bottom of this method.
                #
                # A bare `return` here (the original D2 shape) went further than that guard
                # needed, though - it's inside this method's own try: block, so it also skipped
                # _dispatchNativeAction(action) entirely (the base-class/NAV_BACK dispatch at the
                # very bottom of this method, which forwards ordinary actions to
                # self._currentOnAction(action)) - the real native WindowXML.onAction() Kodi needs
                # to actually move focus within a list. Horizontal in-hub navigation (left/right
                # between items in the same hub row) was never actually reaching Kodi at all as a
                # result - live-confirmed, not just "out of scope" the way checkHubItem()'s richer
                # per-item behavior (hero-art updates, pagination, round-robin) genuinely still is.
                # Calling the dispatch directly - skipping only this method's own grid-specific
                # body in between - fixes that without reopening the crash the blanket return was
                # protecting against.
                self._dispatchNativeAction(action)
                return

            if action.getId() in MOVE_SET:
                mli = self.showPanelControl.getSelectedItem()
                if mli:
                    self.requestChunk(mli.pos())

                if util.addonSettings.dynamicBackgrounds:
                    # `mli and mli.dataSource`, not `is not None`, used to gate this - a real
                    # footgun for Playlist dataSources specifically: BasePlaylist defines
                    # __len__() (playlist.py) returning its *member* count, which is always 0
                    # for the summary objects this grid fetches (real items are never loaded
                    # just to browse the grid) - Python falls back to __len__ for truthiness
                    # when __bool__ isn't defined, so a perfectly valid Playlist object silently
                    # evaluated as falsy here, skipping the background update on every single
                    # scroll. Live-confirmed via diagnostic logging: MOVE_SET fired correctly
                    # every time with a valid mli.dataSource, but this check still failed.
                    # Explicit `is not None` sidesteps __len__ entirely.
                    if mli is not None and mli.dataSource is not None:
                        if self.section.TYPE == 'playlists':
                            # updateBackgroundFrom() keys off ds.get('art', ...), which
                            # playlists don't have (see _setPlaylistBackground()'s own
                            # docstring) - without this, scrolling through the playlists grid
                            # silently did nothing (no art, so no background write at all),
                            # leaving whichever playlist fillPlaylists() randomly picked at fill
                            # time showing until the next full refill (e.g. a Music/Video tab
                            # swap) happened to pick a different one.
                            self._setPlaylistBackground(mli.dataSource)
                        else:
                            self.updateBackgroundFrom(mli.dataSource)

                controlID = self.getFocusId()
                if controlID == self.POSTERS_PANEL_ID or controlID == self.SCROLLBAR_ID:
                    self.updateKey()
            elif action == xbmcgui.ACTION_MOUSE_DRAG:
                self.onMouseDrag(action)
            elif action == xbmcgui.ACTION_CONTEXT_MENU:
                # item action possible?
                had_action = self.itemOptions()
                if not had_action:
                    if not xbmc.getCondVisibility('ControlGroup({0}).HasFocus(0)'.format(self.OPTIONS_GROUP_ID)):
                        self.lastNonOptionsFocusID = self.lastFocusID
                        self.setFocusId(self.OPTIONS_GROUP_ID)
                        return
                    else:
                        if self.lastNonOptionsFocusID:
                            self.setFocusId(self.lastNonOptionsFocusID)
                            self.lastNonOptionsFocusID = None
                            return
                else:
                    return
            elif self.isWatchedAction(action):
                mli = self.showPanelControl.getSelectedItem()
                if not mli or not mli.dataSource:
                    return
                self.toggleWatched(mli)
                return

            elif action in (xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_CONTEXT_MENU):
                if not xbmc.getCondVisibility('ControlGroup({0}).HasFocus(0)'.format(self.OPTIONS_GROUP_ID)) and \
                        (not util.addonSettings.fastBack or action == xbmcgui.ACTION_CONTEXT_MENU):
                    if xbmc.getCondVisibility('Integer.IsGreater(Container(101).ListItem.Property(index),5)'):
                        self.showPanelControl.selectItem(0)
                        return

            self.updateItem()

        except:
            util.ERROR()

        self._dispatchNativeAction(action)

    def onClick(self, controlID):
        if controlID == self.SECTION_LIST_ID:
            # Ported from HomeWindow's identical guard (home.py's onClick()) - while
            # self.movingSection is set, sectionMover() owns ACTION_SELECT_ITEM itself (via
            # onAction() above) to finalize the move; an ordinary click-dispatch here on the same
            # press would otherwise also try to open whatever's now selected.
            if not self.movingSection:
                self.sectionClicked()
            return

        if controlID == self.TAB_LIST_ID:
            # Plan item 0 (quiet-orbiting-heron.md): TAB_LIST_ID exists identically in every
            # content-mode's template, so this is checked before the contentMode=='recommended'
            # bypass below, same as SECTION_LIST_ID above.
            mli = self.tabList.getSelectedItem()
            if mli:
                if self._tabListIsPlaylists:
                    # Music/Video: _applyItemTypeChoice() is an in-place refill (reset()/fill()),
                    # never a doClose()-based window reconstruction - none of the deferral below
                    # applies, same as itemTypeButtonClicked()'s own dropdown-result call to it.
                    self._applyItemTypeChoice(mli.getProperty('item.type'))
                    return

                # Not a direct switchTab() call: confirmed as xbmc/xbmc#27552/#27239, an upstream
                # Kodi core bug, not anything specific to this control - CGUIWindow::OnAction()'s
                # focused-control parent walk crashes if the window/skin gets reloaded nested
                # underneath the very OnAction()/onClick() call that triggered it. switchTab()'s
                # doClose() is exactly that kind of reload, so it must never run synchronously,
                # inline, from this callback - see windowutils.SKIN_RELOAD_DEFER_SECONDS' own
                # comment for the full diagnosis and why a real time delay (not just a different
                # thread with no delay - live-confirmed as insufficient on its own) is what
                # actually avoids it.
                mode = mli.getProperty('content.mode')
                threading.Timer(windowutils.SKIN_RELOAD_DEFER_SECONDS, self.switchTab, args=(mode,)).start()
            return

        if controlID == self.USER_LIST_ID:
            # Stage 3: shared across every content mode, same reasoning as SECTION_LIST_ID/
            # TAB_LIST_ID above - checked before the contentMode=='recommended' bypass below.
            # Ported from HomeWindow's identical USER_LIST_ID handling (home.py's onClick()) -
            # minus self._skipNextAction, input-suppression state LibraryWindow doesn't have and
            # only matters for the refresh_users/local_users options staying "open".
            self.doUserOption()
            self.setBoolProperty('show.options', False)
            self.setFocusId(self.USER_BUTTON_ID)
            return

        if controlID == self.SERVER_LIST_ID:
            # Stage 3: same shared-across-content-modes reasoning as USER_LIST_ID above. Deferred,
            # not called inline - see the SERVER_BUTTON_ID onAction() branch's own comment for why
            # selectServer() can't run synchronously from a native callback.
            self.setBoolProperty('show.servers', False)
            threading.Timer(windowutils.SKIN_RELOAD_DEFER_SECONDS, self.selectServer).start()
            return

        if self.contentMode == 'recommended':
            # RecommendedWindow has none of the grid controls (POSTERS_PANEL_ID/KEY_LIST_ID/etc.)
            # the elif chain below unconditionally checks against - live-confirmed as an
            # AttributeError otherwise, so hub-row clicks need their own branch here rather than
            # falling into that chain.
            if 399 < controlID < 500:
                self.hubItemClicked(controlID)
            return

        if controlID == self.POSTERS_PANEL_ID:
            self.showPanelClicked()
        elif controlID == self.KEY_LIST_ID:
            self.keyClicked()
        elif controlID == self.PLAYER_STATUS_BUTTON_ID:
            self.showAudioPlayer()
        elif controlID == self.PLAY_BUTTON_ID:
            self.playButtonClicked()
        elif controlID == self.SHUFFLE_BUTTON_ID:
            self.shuffleButtonClicked()
        elif controlID == self.OPTIONS_BUTTON_ID:
            self.optionsButtonClicked()
        elif controlID == self.VIEWTYPE_BUTTON_ID:
            self.viewTypeButtonClicked()
        elif controlID == self.SORT_BUTTON_ID:
            self.sortButtonClicked()
        elif controlID == self.FILTER1_BUTTON_ID:
            self.filter1ButtonClicked()
        elif controlID == self.ITEM_TYPE_BUTTON_ID:
            self.itemTypeButtonClicked()

    def buildSectionList(self):
        """Populate the sidebar's section list. Mirrors home.py's showSections(), minus
        the hub-fetching side effects Home needs and this window doesn't - see the Sidebar
        rollout plan (Phase B) for why this isn't shared code yet: the two consumers'
        needs (in-place hub reload vs. plain nav) diverge enough that extracting a shared
        helper before a third consumer exists risked locking in the wrong shape.
        """
        items = []
        # Native list-control cursor position of whichever item ends up marked is.active below -
        # set once, after addItems(), so the sidebar's own selected position already reflects the
        # active section the very first time focus ever lands there (Kodi otherwise defaults an
        # unset list control's position to 0/Search). Live-confirmed regression without this: at
        # cold start (self.section is home_section), moving focus into the sidebar for the first
        # time landed on Search, not Home - is.active was never set on homemli either, in the
        # cold-start case, since it was only ever set inside the sections-only loop below (which
        # never includes home_section itself).
        active_pos = None

        searchmli = kodigui.ManagedListItem(T(32431, 'Search'), iconImage='script.plex/buttons/search.png')
        searchmli.setProperty('is.search', '1')
        searchmli.setProperty('item', '1')
        items.append(searchmli)

        homemli = kodigui.ManagedListItem(T(32332, 'Home'), iconImage='script.plex/home/type/home.png',
                                          data_source=home.home_section)
        homemli.setProperty('is.home', '1')
        homemli.setProperty('item', '1')
        if home.home_section.key == self.section.key:
            homemli.setProperty('is.active', '1')
            active_pos = len(items)
        items.append(homemli)

        # self.navSettings is real, mutable state (loadNavSettings()/saveNavSettings()) rather than
        # a fresh read here, so sectionMenu()'s hide/show/pin/order changes are picked up on the
        # very next rebuild without a redundant settings round-trip. Defensive load if somehow not
        # populated yet - onFirstInit()/serverRefresh() are the normal call sites.
        if self.navSettings is None:
            self.loadNavSettings()
        navSettings = self.navSettings

        sections = []

        # home.watchlist_section only ever got constructed by HomeWindow.showSections() (home.py) -
        # dead code on this branch, since HomeWindow is never instantiated once main.py boots
        # straight into LibraryWindow (Stage 2). Left unfixed, home.watchlist_section stays None
        # forever, and the check below always short-circuits there regardless of whether the
        # account's watchlist actually has data - live-confirmed: watchlist never appeared in the
        # sidebar at all. Constructed fresh here instead, same construction HomeWindow's own
        # (dead) version used, gated by the same offline/setting checks to avoid a needless network
        # call when the feature's disabled - this is the only place in the live codebase that reads
        # home.watchlist_section, so it's also the only place that needs to populate it.
        if not plexapp.ACCOUNT.isOffline and util.getUserSetting("use_watchlist", True):
            from plexnet import plexlibrary
            home.watchlist_section = plexlibrary.WatchlistSection(
                None, server=plexapp.SERVERMANAGER.getDiscoverServer())
            home.watchlist_section.title = T(34000, 'Watchlist')

        if (not plexapp.ACCOUNT.isOffline and util.getUserSetting("use_watchlist", True) and home.watchlist_section
                and home.watchlist_section.has_data()
                and ("/library/sections/watchlist" not in navSettings
                     or navSettings["/library/sections/watchlist"].get("show", True))):
            sections.append(home.watchlist_section)

        if "playlists" not in navSettings or navSettings["playlists"].get("show", True):
            if plexapp.SERVERMANAGER.selectedServer.playlists():
                sections.append(home.playlists_section)

        for section in plexapp.SERVERMANAGER.selectedServer.library.sections():
            if section.key in navSettings and not navSettings[section.key].get("show", True):
                continue
            sections.append(section)

        if "order" in navSettings:
            order = navSettings["order"]

            def orderPos(s):
                if s.key in order:
                    return order.index(s.key), 0
                return -1, 0

            sections = sorted(sections, key=orderPos)

        # self.section.key alone only matches a sidebar entry when self.section IS one - a
        # collection or a folder drilled into via sectionClicked() carries its own key (the
        # collection's, or the folder's parent's already-collection-shaped key), never a real
        # section's - live-confirmed regression: opening a collection from a nested LibraryWindow
        # left nothing highlighted in its own sidebar at all. getLibrarySectionId() (present on
        # every section-shaped object this window's self.section can be, per its own existing use
        # a few lines above for viewtype lookups) still resolves back to the real owning library's
        # key in that case, so fall back to it rather than leaving nothing highlighted. Ported from
        # the Sidebar-Tab-Unification branch's identical fix (commit f0e6340f), which found the
        # same bug independently - that branch's own pooled-window architecture isn't ported here,
        # just this small, self-contained highlight fix.
        # self.entrySectionId (Sidebar entry-section persistence, ported from Sidebar-Tab-
        # Unification's mellow-pondering-magpie.md) overrides the fallback above when present: an
        # ancestor further up the drill chain (PrePlayWindow/ShowWindow/etc - see their own
        # buildSectionList()) explicitly threaded its own entrySectionId through - a collection
        # opened from e.g. a cross-section PersonWindow filmography click can genuinely live in a
        # different real section than the one that should stay highlighted, so that always wins
        # when present.
        if self.entrySectionId is not None:
            activeLibraryId = self.entrySectionId
        else:
            getActiveLibraryId = getattr(self.section, 'getLibrarySectionId', None)
            activeLibraryId = getActiveLibraryId() if getActiveLibraryId else None

        for section in sections:
            mli = kodigui.ManagedListItem(section.title,
                                          iconImage='script.plex/home/type/{0}.png'.format(section.type),
                                          data_source=section)
            mli.setProperty('item', '1')
            if section == home.playlists_section:
                mli.setProperty('is.playlists', '1')
                mli.setIconImage('script.plex/home/type/playlists.png')
            elif section == home.watchlist_section:
                mli.setIconImage('script.plex/home/type/watchlist.png')
            if section.key == self.section.key or (activeLibraryId and section.key == activeLibraryId) or \
                    (self.entrySectionId is None and self.entryFromWatchlist and section == home.watchlist_section):
                mli.setProperty('is.active', '1')
                active_pos = len(items)
            items.append(mli)

        self.sectionList.reset()
        self.sectionList.addItems(items)
        if active_pos is not None:
            self.sectionList.selectItem(active_pos)

    def sectionMenu(self):
        """Context menu (ACTION_CONTEXT_MENU) for the sidebar's currently-focused section item -
        ported from HomeWindow.sectionMenu() (home.py), adapted to this window's own state:
        self.librarySettings (home.py's per-section show/hide/pin/order dict) -> self.navSettings
        (see __init__'s comment for the name-collision reason), self.saveLibrarySettings() ->
        self.saveNavSettings(). Triggered from onAction()'s SECTION_LIST_ID/ACTION_CONTEXT_MENU
        branch, which also owns the block_section_change guard and the return-value ->
        serverRefresh() handoff - see that branch's own comment for why.
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
                section_settings = self.navSettings.get(s.key)
                if section_settings and not section_settings.get("show", True):
                    options.append({'key': 'show',
                                    'section_id': s.key,
                                    'display': T(33029, "Show library: {}").format(s.title)
                                    }
                                   )

            # hack for an inexistant watchlist due to it being hidden
            if util.getUserSetting("use_watchlist", True) and not self.navSettings.get(
                    "/library/sections/watchlist", {}).get("show", True):
                options.append({'key': 'show',
                                'section_id': "/library/sections/watchlist",
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

            if plexapp.ACCOUNT.isAdmin and section not in (home.watchlist_section, home.playlists_section):
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
                return self.lastSection

            else:
                # show fb - select loc to map
                d = xbmcgui.Dialog().browse(0, T(33031, "Select Kodi source for {}").format(choice["path"]), "files")
                if not d:
                    return
                pmm.addPathMapping(d, choice["path"])
                return self.lastSection
        elif choice["key"] == "hide":
            if section.key not in self.navSettings:
                self.navSettings[section.key] = {}
            self.navSettings[section.key]['show'] = False
            self.saveNavSettings()
            return self.sectionList[self.sectionList.prev()].dataSource
        elif choice["key"] == "show":
            if "section_id" in choice:
                if choice["section_id"] in self.navSettings:
                    self.navSettings[choice["section_id"]]['show'] = True
                    self.saveNavSettings()
                    return self.lastSection
        elif choice["key"] == "move":
            self.sectionMover(item, "init")
        elif choice["key"] == "reset_order":
            if "order" in self.navSettings:
                del self.navSettings["order"]
                self.saveNavSettings()
                return self.lastSection
        elif choice["key"] == "refresh":
            with busy.BusyContext(delay=True, delay_time=0.2):
                section.refresh()
            return self.lastSection
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
                return self.lastSection
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
                return self.lastSection
            return

        elif choice["key"] == "refresh_hubs":
            return self.lastSection

    def sectionMover(self, item, action):
        """Sidebar section-reorder ("Move") mode - ported verbatim from HomeWindow.sectionMover()
        (home.py). Entered via sectionMenu()'s 'move' choice; onAction()/onClick() route input here
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
            if reset:
                if self._initialMovingSectionPos is not None:
                    self.sectionList.moveItem(item, self._initialMovingSectionPos)
                self._initialMovingSectionPos = None
            self.sectionList.insertItem(0, homemli)
            self.sectionList.insertItem(0, searchmli)
            if reset:
                self.sectionList.selectItem(1)  # Home
            self.sectionChanged()

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
            self.navSettings["order"] = [i.dataSource.key for i in self.sectionList.items if i.dataSource]
            self.saveNavSettings()

    def buildTabList(self):
        """Populate the section-tabs row: Recommended/Library normally (plan item 0,
        quiet-orbiting-heron.md), or Music/Video for the Playlists section instead - per the
        user's own request, Playlists has no real hub content for a Recommended tab (no numeric
        section key for SectionHubsTask to fetch against) and no separate Library-tab concept
        either (always grid), so this reuses the same 2-tab row for the Audio/Video item-type
        choice instead - the same choice the old floating item-type button (312,
        ITEM_TYPE_BUTTON_ID) used to offer via a dropdown for this section, before it became
        playlists-hidden (see itemTypeButtonClicked()'s own comment). self._tabListIsPlaylists
        (set by onFirstInit() immediately before calling this) picks which flavor gets built -
        called once per LibraryWindow lifetime for a given flavor, then only rebound
        (newControl()) on further same-flavor swaps, and rebuilt again if a swap crosses the
        playlists/non-playlists boundary - see onFirstInit()'s own comment. Recommended/Library's
        labels are plain hardcoded English, not T()-translated - no existing translation string
        to reuse there, and adding new ones was a separate concern from that original pass;
        Music/Video reuse existing strings since this is porting an already-translated dropdown's
        own option labels, not introducing new copy.
        """
        items = []
        if self._tabListIsPlaylists:
            for item_type, label in (('audio', T(32394, 'Music')), ('video', T(32053, 'Video'))):
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

        self.tabList.reset()
        self.tabList.addItems(items)
        self.updateActiveTabMarker()

    def updateActiveTabMarker(self):
        """Update 'current' on the tab list items to highlight the active tab - self.contentMode
        normally (Recommended/Library), or the active ITEM_TYPE for the Playlists section's
        Music/Video tabs instead (self._tabListIsPlaylists). Same key-matched-property pattern
        updateActiveSectionMarker() uses for the sidebar, called both right after buildTabList()
        and whenever the active tab changes (switchTab() for contentMode,
        _applyItemTypeChoice() for ITEM_TYPE).
        """
        if not self.tabList:
            return

        if self._tabListIsPlaylists:
            key, active = 'item.type', ITEM_TYPE
        else:
            key, active = 'content.mode', self.contentMode

        for i in range(self.tabList.size()):
            mli = self.tabList[i]
            if not mli:
                continue
            if mli.getProperty(key) == active:
                mli.setProperty('current', '1')
            elif mli.getProperty('current'):
                mli.setProperty('current', '')

    # sectionClicked() now provided by SidebarMixin - its default _dispatchSectionOpen() covers
    # this window's needs exactly: home_section is just another section value here (LibraryWindow
    # has openSection(), so is.home no longer gets any special treatment - see that method's own
    # is.home-equivalent TYPE == 'mixed' check for how it lands on the right tab), skip re-opening
    # the already-shown section via lastSection tracking, playlists -> PlaylistsWindow, else ->
    # opener.sectionClicked().

    def displayServerAndUser(self, **kwargs):
        """Sidebar avatar/username and server icon/name. Window properties are
        per-window, so home.py's own displayServerAndUser() (which this mirrors)
        never reaches this window - see home.py:3622.
        """
        title = plexapp.ACCOUNT.title or plexapp.ACCOUNT.username or ' '
        self.setProperty('user.name', title)
        self.setProperty('user.avatar', plexapp.ACCOUNT.safeUserThumb(plexapp.ACCOUNT.ID,
                                                                       thumb=plexapp.ACCOUNT.thumb))
        self.setProperty('user.avatar.letter', title[0].upper())

        if plexapp.SERVERMANAGER.selectedServer:
            self.setProperty('server.name', plexapp.SERVERMANAGER.selectedServer.name)
            self.setProperty('server.icon', 'script.plex/home/device/plex.png')
            self.setProperty('server.iconmod',
                             plexapp.SERVERMANAGER.selectedServer.isSecure and 'script.plex/home/device/lock.png' or '')
            self.setProperty('server.iconmod2',
                             plexapp.SERVERMANAGER.selectedServer.isLocal and 'script.plex/home/device/home_small.png'
                             or '')
        else:
            self.setProperty('server.name', T(32338, 'No Servers Found'))
            self.setProperty('server.icon', 'script.plex/home/device/error.png')
            self.setProperty('server.iconmod', '')
            self.setProperty('server.iconmod2', '')

    def onFocus(self, controlID):
        # Within the 150ms hold window after go_root, any non-section-list focus event is the
        # stray Kodi fires when this window reactivates with its previously-focused control still
        # recorded. Snap it back and consume the deadline so real user input (which arrives well
        # after the window closes) passes through unblipped. Ported from HomeWindow's identical
        # onFocus() guard (home.py) - see onReInit()'s go_root handling.
        if (time.time() < self._goRootHoldUntil
                and 100 < controlID < 500 and controlID != self.SECTION_LIST_ID):
            self._goRootHoldUntil = 0
            self.setFocusId(self.SECTION_LIST_ID)
            return

        self.reselectActiveSection(controlID, self.lastFocusID)
        self.lastFocusID = controlID

        if controlID == self.SECTION_LIST_ID and not self.changingServer and not self.movingSection:
            # changingServer guard: ported from HomeWindow's identical onFocus() check (home.py) -
            # selectServer() below sets focus to SECTION_LIST_ID itself as its very first step,
            # well before the switch actually completes - without this, that focus event would
            # fire checkSectionItem() immediately and re-trigger a section reload mid-switch.
            # movingSection guard: same reasoning, also ported from HomeWindow (home.py) - focus
            # moves within the list constantly during a reorder (moveItem()/selectItem() calls in
            # sectionMover() itself), none of which should be treated as "settle on this section".
            self.checkSectionItem()

        if self.contentMode == 'recommended':
            # quiet-orbiting-heron.md Stage B: RecommendedWindow has no KEY_LIST_ID (or any
            # other grid control) - live-confirmed as an AttributeError otherwise, since this
            # runs on every focus change, not just KEY_LIST_ID's own. Real Recommended-tab focus
            # handling (Stage C/D) replaces this branch.
            return

        if controlID == self.KEY_LIST_ID:
            self.selectKey()

    def onItemChanged(self, mli):
        if not mli:
            return

        if not mli.dataSource or not mli.dataSource.TYPE == 'photo':
            return

        self.showPhotoItemProperties(mli.dataSource)

    def toggleWatched(self, mli, state=None, **kw):
        item = mli.dataSource
        wl_ref = item.show() if item.TYPE in ('episode', 'season') else item
        watched = super(LibraryWindow, self).toggleWatched(item)
        if watched is None:
            return

        if watched:
            removeFromWatchlistBlind(wl_ref.guid, wl_ref)
        self.updateUnwatchedAndProgress(mli)
        util.MONITOR.watchStatusChanged()

    def itemOptions(self):
        mli = self.showPanelControl.getSelectedItem()
        if not mli:
            return True

        if mli.dataSource is None:
            return True

        if mli.dataSource.TYPE in ('episode', 'season', 'movie', 'show'):
            options = []
            ds = mli.dataSource
            wl_ref = ds.show() if ds.TYPE in ('episode', 'season') else ds

            if self.section.TYPE != "movies_shows":
                # we don't want mark watched for watchlist items
                if not mli.getProperty('watched'):
                    options.append({'key': 'mark_watched', 'display': T(32319, "Mark Played")})

                if (ds.isFullyWatched or ds.isWatched or
                        (ds.TYPE in ("show", "season") and 0 < ds.unViewedLeafCount < ds.leafCount)):
                    options.append({'key': 'mark_unwatched', 'display': T(32318, "Mark Unplayed")})
            else:
                options.append({'key': 'remove_from_watchlist', 'display': T(34011, "Remove from watchlist")})

            title = mli.label
            secondary = mli.label2
            if ds.TYPE in ("movie", "show"):
                secondary = mli.getProperty('year')
            elif ds.TYPE == "episode":
                title = ds.defaultTitle
                secondary = mli.getProperty('subtitle')

            label = u"{} ({})".format(six.ensure_str(title), six.ensure_str(secondary))

            choice = dropdown.showDropdown(
                options,
                pos=(660, 441),
                close_direction='none',
                set_dropdown_prop=False,
                header=T(33030, 'Choose action for: {}').format(label),
                align_items="left",
            )

            if choice and choice["key"] in ("mark_watched", "mark_unwatched", "remove_from_watchlist"):
                if util.getSetting('home_confirm_actions'):
                    button = optionsdialog.show(
                        T(32319, "Mark Played") if choice["key"] == "mark_watched"
                        else T(34011,"Remove from watchlist")
                        if choice["key"] == "remove_from_watchlist" else T(32318, "Mark Unplayed"),
                        label,
                        T(32328, 'Yes'),
                        T(32329, 'No'),
                    )

                    if button != 0:
                        return True

                if choice["key"] == "mark_watched":
                    self.toggleWatched(mli, state=True)

                elif choice["key"] == "mark_unwatched":
                    self.toggleWatched(mli, state=False)

                elif choice["key"] == "remove_from_watchlist":
                    removeFromWatchlistBlind(wl_ref.guid, wl_ref)
                    self.doRefill()
            return True


    def updateKey(self, mli=None):
        mli = mli or self.showPanelControl.getSelectedItem()
        if not mli:
            return

        if self.lastItem != mli:
            self.lastItem = mli
            self.onItemChanged(mli)

        util.setGlobalProperty('key', mli.getProperty('key'))

        self.selectKey(mli)

    def selectKey(self, mli=None):
        if not mli:
            mli = self.showPanelControl.getSelectedItem()
            if not mli:
                return

        li = self.keyItems.get(mli.getProperty('key'))
        if not li or not li.pos():
            return
        self.keyListControl.selectItem(li.pos())

    def searchButtonClicked(self):
        self.processCommand(search.dialog(self, section_id=self.section.key))

    def browseGenres(self):
        from . import genres as genres_window
        self.processCommand(opener.handleOpen(genres_window.GenreBrowserWindow,
                                              section=self.section))

    def keyClicked(self):
        li = self.keyListControl.getSelectedItem()
        if not li:
            return

        mli = self.firstOfKeyItems.get(li.dataSource)
        if not mli:
            return
        pos = mli.pos()

        # This code is a little goofy but what it's trying to do is move the selected item from the
        # jumplist up to the top of the panel and then it requests the chunk for the current position
        # and the chunk for the current position + CHUNK_OVERCOMMIT.  The reason we need to potentially
        # request a different chunk is if the items on the panel are in two different chunks this code
        # will request both chunks so that we don't have blank items.  The requestChunk will only request
        # chunks that haven't already been fetched so if the current position and current position
        # plus the CHUNK_OVERCOMMIT are in the same chunk then the second requestChunk call doesn't
        # do anything.
        chunkOC = getattr(self._current, "CHUNK_OVERCOMMIT", self.CHUNK_OVERCOMMIT)
        self.showPanelControl.selectItem(pos+chunkOC)
        self.showPanelControl.selectItem(pos)
        self.requestChunk(pos)
        self.requestChunk(pos+chunkOC)

        self.setFocusId(self.POSTERS_PANEL_ID)
        util.setGlobalProperty('key', li.dataSource)

    def playButtonClicked(self, shuffle=False):
        if self.playBtnClicked:
            return

        self.subOptionCache = {}

        self.playBtnClicked = True
        filter_ = self.getFilterOpts()
        sort = self.getSortOpts()
        args = {}
        if filter_:
            args[filter_[0]] = filter_[1]

        if sort:
            args['sort'] = '{0}:{1}'.format(*sort)

        if self.section.TYPE == 'movie':
            args['sourceType'] = '1'
        elif self.section.TYPE == 'show':
            args['sourceType'] = '2'
        elif self.section.TYPE != 'collection':
            args['sourceType'] = '8'

        # When the list is filtered by unwatched, play and shuffle button should only play unwatched videos
        if self.boolFilters.get('unwatched'):
            args['unwatched'] = '1'

        pq = playqueue.createPlayQueueForItem(self.section, options={'shuffle': shuffle}, args=args)
        opener.open(pq, auto_play=True, auto_play_open=True)

    def shuffleButtonClicked(self):
        # TV and movie libraries open the Shuffle Mode menu; other section types
        # keep the classic server-side random shuffle.
        if self.section.TYPE == 'show':
            self.shuffleModeSelected()
        elif self.section.TYPE == 'movie':
            self.movieShuffleSelected()
        else:
            self.playButtonClicked(shuffle=True)

    def movieShuffleSelected(self):
        options = [
            {'key': shuffle.MODE_UNWATCHED, 'display': T(35010, "Unwatched")},
            {'key': shuffle.MODE_REWATCH, 'display': T(35011, "Rewatch")},
            {'key': 'classic', 'display': T(35018, "Shuffle All")},
        ]
        choice = dropdown.showDropdown(
            options,
            pos=(660, 441),
            close_direction='none',
            set_dropdown_prop=False,
            header=T(35009, "Shuffle Mode"),
            select_index=0,
            align_items="left",
        )
        if not choice:
            return
        if choice['key'] == 'classic':
            self.playButtonClicked(shuffle=True)
            return
        self.startMovieShuffle(choice['key'])

    def startMovieShuffle(self, mode):
        with busy.BusyContext(delay=True, delay_time=0.2):
            movies = self.section.all(type_=1)
            pool = shuffle.eligible_movies(movies, mode)
            if not pool:
                util.messageDialog(T(35009, "Shuffle Mode"),
                                   T(35013, "No matching items are available for this shuffle mode."))
                return
            ordered = shuffle.pick(pool, len(pool))

        pl = playlist.LocalPlaylist(ordered, self.section.getServer())
        self.processCommand(videoplayer.play(play_queue=pl))

    def shuffleModeSelected(self):
        options = [
            {'key': shuffle.MODE_UNWATCHED, 'display': T(35010, "Unwatched")},
            {'key': shuffle.MODE_REWATCH, 'display': T(35011, "Rewatch")},
            {'key': shuffle.MODE_CATCHUP, 'display': T(35012, "Catchup")},
            {'key': 'classic', 'display': T(35018, "Shuffle All")},
        ]
        choice = dropdown.showDropdown(
            options,
            pos=(660, 441),
            close_direction='none',
            set_dropdown_prop=False,
            header=T(35009, "Shuffle Mode"),
            select_index=0,
            align_items="left",
        )
        if not choice:
            return
        if choice['key'] == 'classic':
            self.playButtonClicked(shuffle=True)
            return
        self.startShuffleMode(choice['key'])

    def startShuffleMode(self, mode):
        section = self.section
        threshold = util.getSetting('shuffle_catchup_episode_threshold', 3)
        series_count = util.getSetting('shuffle_catchup_series_count', 5)
        specials_mode = util.getSetting('tv_specials_order', 'default')

        items = []
        with busy.BusyContext(delay=True, delay_time=0.2):
            shows = section.all(type_=2)
            pool = shuffle.eligible_shows(shows, mode, threshold=threshold)
            if not pool:
                util.messageDialog(T(35009, "Shuffle Mode"),
                                   T(35013, "No shows are available for this shuffle mode."))
                return

            pick_count = series_count if mode == shuffle.MODE_CATCHUP else 1
            start_index = 0
            for show in shuffle.pick(pool, pick_count):
                episodes = show.all()
                if mode == shuffle.MODE_CATCHUP:
                    # Eligibility counts PMS viewedLeafCount (fully-watched leaves only),
                    # so in-progress episodes are dropped here and a show may contribute
                    # fewer episodes than its unwatched count implied. The empty-queue
                    # guard below handles the case where nothing is left to play.
                    episodes = shuffle.unwatched_episodes(episodes)
                episodes = playlist.reorder_with_specials(episodes, mode=specials_mode)
                for ep in episodes:
                    # let the player reach show metadata, mirroring episodes.py
                    ep._show = show
                if not items:
                    # first show that actually contributes: start on its own first real
                    # episode (skip a leading special), not somewhere later in the queue
                    start_index = shuffle.first_regular_index(episodes)
                items.extend(episodes)

        if not items:
            util.messageDialog(T(35009, "Shuffle Mode"),
                               T(35013, "No shows are available for this shuffle mode."))
            return

        pl = playlist.LocalPlaylist(items, section.getServer())
        pl.setCurrent(items[start_index])
        self.processCommand(videoplayer.play(play_queue=pl))

    def optionsButtonClicked(self):
        options = []
        if xbmc.getCondVisibility('Player.HasAudio + MusicPlayer.HasNext'):
            options.append({'key': 'play_next', 'display': T(32325, 'Play Next')})

        if self.section.TYPE == 'photodirectory':
            if options:
                options.append(dropdown.SEPARATOR)
            options.append({'key': 'to_section', 'display': T(32324, u'Go to {0}').format(self.section.getLibrarySectionTitle())})

        choice = dropdown.showDropdown(options, (255, 205))
        if not choice:
            return

        if choice['key'] == 'play_next':
            xbmc.executebuiltin('PlayerControl(Next)')
        elif choice['key'] == 'to_section':
            self.goHome(self.section.getLibrarySectionId())

    def itemTypeButtonClicked(self):
        options = []

        if self.section.TYPE == 'show':
            for t in ('show', 'episode', 'collection'):
                options.append({'type': t, 'display': TYPE_PLURAL.get(t, t)})
            options.append({'type': 'browse_genres', 'display': T(34102, 'Categories')})
        elif self.section.TYPE == 'movie':
            for t in ('movie', 'collection'):
                options.append({'type': t, 'display': TYPE_PLURAL.get(t, t)})
            options.append({'type': 'browse_genres', 'display': T(34102, 'Categories')})
            options.append({'type': 'folder', 'display': TYPE_PLURAL.get('folder', 'folder')})
        elif self.section.TYPE == 'artist':
            for t in ('artist', 'album', 'collection', 'track'):
                options.append({'type': t, 'display': TYPE_PLURAL.get(t, t)})
        elif self.section.TYPE == 'movies_shows':
            for t in ('movies_shows', 'movie', 'show'):
                options.append({'type': t, 'display': TYPE_PLURAL.get(t, t)})
        else:
            # 'playlists' used to be here too (Audio/Video options) - control 312
            # (ITEM_TYPE_BUTTON_ID, this method's only caller) is playlists-specific-hidden now,
            # per the user's own request: Playlists gets Music/Video as real tabList tabs
            # instead of a floating dropdown button, same _applyItemTypeChoice() effect either
            # way - see onClick()'s TAB_LIST_ID branch.
            return

        selectItem = None
        curType = self.librarySettings.getItemType()
        try:
            selectItem = list(filter(lambda o: o["type"] == curType, options))[0]
        except:
            pass

        result = dropdown.showDropdown(options, (380, 106), with_indicator=True,
                                       select_item=not self.getBoolProperty('no.content.filtered') and selectItem or None)
        if not result:
            return

        choice = result['type']

        if choice == 'browse_genres':
            self.browseGenres()
            return

        self._applyItemTypeChoice(choice)

    def _applyItemTypeChoice(self, choice):
        """Switch ITEM_TYPE in place (no window reconstruction) - shared by
        itemTypeButtonClicked()'s dropdown result above and the Playlists tabList's Music/Video
        click (onClick()'s TAB_LIST_ID branch), which needs the exact same effect without a
        dropdown at all."""
        if choice == ITEM_TYPE:
            return

        with self.lock:
            if self.tasks and any(list(filter(lambda x: not x.finished, self.tasks))):
                util.DEBUG_LOG("Waiting for tasks to finish")
                with busy.BusyContext(delay=True, delay_time=0.2):
                    while self.tasks and not util.MONITOR.abortRequested():
                        task = self.tasks.pop()
                        if task.isValid():
                            task.cancel()
                            ct = 0
                            while not task.finished and not util.MONITOR.abortRequested() and ct < 40:
                                xbmc.sleep(100)
                                ct += 1
                        del task

            try:
                self.showPanelControl.reset()
            except:
                util.DEBUG_LOG("Couldn't reset showPanelControl on view change")
            # Not self.showPanelControl = None (as this used to do, "TODO: Need to do some check
            # here I think"): nothing rebuilds it before fill() below runs except a real window
            # reconstruction (nextWindow(False) below, kodigui.py) - and that path had its own
            # bug (fixed separately) that made it fire unconditionally on every item-type change,
            # which is what covered for this: the reconstruction's own onFirstInit()/doRefill()
            # rebuilt showPanelControl fresh every time, whether or not one was actually needed.
            # With that now fixed, the common no-real-window-change case reaches fill() with
            # showPanelControl still None otherwise - live-confirmed as a crash for Playlists
            # (fillPlaylists() calling .addItems() on None) and, for every other section type, a
            # silent no-op (_chunkCallback()'s own `if not self.showPanelControl: return` guard,
            # so the grid would've just stayed empty instead). reset() above already clears its
            # contents/native state in place; the object itself stays perfectly valid to reuse
            # for the fill() that's about to happen on the very same still-open window.

        self.librarySettings.setItemType(choice)

        # LibrarySettings keys sort and filters by item type, so reset() below restores
        # whatever this type was left in. Only the outgoing type's in-memory filter has to
        # go, otherwise reset() would carry it over ("self.filter or <stored>").
        self.filter = None
        self.reset()
        self.updateFilterDisplay()
        util.setGlobalProperty('sort', self.sort)

        if not self.nextWindow(False):
            self.setProperty('media.type', TYPE_PLURAL.get(ITEM_TYPE or self.section.TYPE, self.section.TYPE))
            try:
                self.setProperty('sort.display', SORT_KEYS[self.section.TYPE].get(self.sort, SORT_KEYS['movie'].get(self.sort))['display'])
            except TypeError:
                # stored sort isn't valid for this item type
                self.resetSort()
            self.fill(keep_focus=True)

        # No-op for the Recommended/Library tabList flavor (updateActiveTabMarker() keys off
        # self.contentMode there, unaffected by an ITEM_TYPE change) - only meaningfully updates
        # anything when self._tabListIsPlaylists, but cheap enough not to bother gating.
        self.updateActiveTabMarker()

    def sortButtonClicked(self):
        desc = 'script.plex/indicators/arrow-down.png'
        asc = 'script.plex/indicators/arrow-up.png'
        ind = self.sortDesc and desc or asc

        options = []
        defSortByOption = {}

        if self.section.TYPE == 'movie':
            searchTypes = ['titleSort', 'year', 'originallyAvailableAt', 'rating', 'audienceRating', 'userRating',
                           'contentRating', 'duration', 'viewOffset', 'viewCount', 'addedAt', 'lastViewedAt',
                           'resolution', 'mediaBitrate', 'random']
            if ITEM_TYPE == 'collection':
                searchTypes = ['titleSort', 'addedAt', 'contentRating']

            for stype in searchTypes:
                option = SORT_KEYS['movie'].get(stype).copy()
                option['type'] = stype
                option['indicator'] = self.sort == stype and ind or ''
                defSortByOption[stype] = option.get('defSortDesc')
                options.append(option)
        elif self.section.TYPE == 'show':
            searchTypes = ['titleSort', 'year', 'originallyAvailableAt', 'rating', 'audienceRating', 'userRating',
                           'contentRating', 'unviewedLeafCount', 'episode.addedAt',
                           'addedAt', 'lastViewedAt', 'random']
            if ITEM_TYPE == 'episode':
                searchTypes = ['titleSort', 'show.titleSort', 'addedAt', 'originallyAvailableAt', 'lastViewedAt',
                               'rating', 'audienceRating', 'userRating', 'mediaBitrate', 'random']
            elif ITEM_TYPE == 'collection':
                searchTypes = ['titleSort', 'addedAt']

            for stype in searchTypes:
                option = SORT_KEYS['show'].get(stype, SORT_KEYS['movie'].get(stype, {})).copy()
                if not option:
                    continue
                option['type'] = stype
                option['indicator'] = self.sort == stype and ind or ''
                defSortByOption[stype] = option.get('defSortDesc')
                options.append(option)
        elif self.section.TYPE == 'artist':
            searchTypes = ['titleSort', 'userRating', 'addedAt', 'lastViewedAt', 'viewCount', 'random']
            if ITEM_TYPE == 'album':
                searchTypes = ['titleSort', 'artist.titleSort', 'addedAt', 'lastViewedAt', 'viewCount',
                               'originallyAvailableAt', 'rating', 'random']
            elif ITEM_TYPE == 'collection':
                searchTypes = ['titleSort', 'addedAt']
            elif ITEM_TYPE == 'track':
                searchTypes = ['titleSort', 'addedAt', 'lastViewedAt', 'viewCount']

            for stype in searchTypes:
                option = SORT_KEYS['artist'].get(stype, SORT_KEYS['movie'].get(stype)).copy()
                option['type'] = stype
                option['indicator'] = self.sort == stype and ind or ''
                defSortByOption[stype] = option.get('defSortDesc')
                options.append(option)
        elif self.section.TYPE == 'photo':
            searchTypes = ['addedAt', 'originallyAvailableAt', 'photos.titleSort', 'mediaCount']
            for stype in searchTypes:
                option = SORT_KEYS['photo'].get(stype, SORT_KEYS['movie'].get(stype)).copy()
                option['type'] = stype
                option['indicator'] = self.sort == stype and ind or ''
                defSortByOption[stype] = option.get('defSortDesc')
                options.append(option)
        elif self.section.TYPE == 'movies_shows':
            searchTypes = self.section.ALLOWED_SORT
            for stype in searchTypes:
                option = SORT_KEYS['movies_shows'].get(stype, SORT_KEYS['movie'].get(stype)).copy()
                option['type'] = stype
                option['indicator'] = self.sort == stype and ind or ''
                defSortByOption[stype] = option.get('defSortDesc')
                options.append(option)
        else:
            return

        selectItem = None
        try:
            selectItem = list(filter(lambda o: o["type"] == self.sort, options))[0]
        except:
            pass

        result = dropdown.showDropdown(options, (560, 106), with_indicator=True,
                                       select_item=not self.getBoolProperty('no.content.filtered') and selectItem or None)
        if not result:
            return

        choice = result['type']

        if choice == self.sort:
            self.sortDesc = not self.sortDesc
        else:
            self.sortDesc = defSortByOption.get(choice, False)

        if choice == "random":
            self.section.clearCache()
        self.sort = choice

        self.librarySettings.setSetting('sort', self.sort)
        self.librarySettings.setSetting('sort.desc', self.sortDesc)

        util.setGlobalProperty('sort', choice)
        self.setProperty('sort.display', result['display'])

        self.sortShowPanel(choice, True, keep_focus=True)

    def viewTypeButtonClicked(self):
        for task in self.tasks:
            if task.isValid():
                task.cancel()
                self.refill = True

        with self.lock:
            self.showPanelControl.invalidate()
            win = self.nextWindow()

        key = self.section.key
        if not key or not key.isdigit():
            key = self.section.getLibrarySectionId()
        util.setSetting('viewtype.{0}.{1}'.format(self.section.server.uuid, key), win.VIEWTYPE)

    def sortShowPanel(self, choice, force_refresh=False, keep_focus=False):
        if force_refresh or self.showPanelControl.size() == 0:
            self.fillShows(keep_focus=keep_focus)
            return

        # inline sorting is disabled; this code will never be reached

        if choice == 'addedAt':
            self.showPanelControl.sort(lambda i: i.dataSource.addedAt, reverse=self.sortDesc)
        elif choice == 'originallyAvailableAt':
            self.showPanelControl.sort(lambda i: i.dataSource.get('originallyAvailableAt'), reverse=self.sortDesc)
        elif choice == 'lastViewedAt':
            self.showPanelControl.sort(lambda i: i.dataSource.get('lastViewedAt'), reverse=self.sortDesc)
        elif choice == 'viewCount':
            self.showPanelControl.sort(lambda i: i.dataSource.get('titleSort') or i.dataSource.title)
            self.showPanelControl.sort(lambda i: i.dataSource.get('viewCount').asInt(), reverse=self.sortDesc)
        elif choice == 'titleSort':
            self.showPanelControl.sort(lambda i: i.dataSource.get('titleSort') or i.dataSource.title, reverse=self.sortDesc)
            self.keyListControl.sort(lambda i: i.getProperty('original'), reverse=self.sortDesc)
        elif choice == 'show.titleSort':
            self.showPanelControl.sort(lambda i: i.label, reverse=self.sortDesc)
            self.keyListControl.sort(lambda i: i.getProperty('original'), reverse=self.sortDesc)
        elif choice == 'artist.titleSort':
            self.showPanelControl.sort(lambda i: i.label, reverse=self.sortDesc)
            self.keyListControl.sort(lambda i: i.getProperty('original'), reverse=self.sortDesc)
        elif choice == 'rating':
            self.showPanelControl.sort(lambda i: i.dataSource.get('titleSort') or i.dataSource.title)
            self.showPanelControl.sort(lambda i: i.dataSource.get('rating').asFloat(), reverse=self.sortDesc)
        elif choice == 'audienceRating':
            self.showPanelControl.sort(lambda i: i.dataSource.get('titleSort') or i.dataSource.title)
            self.showPanelControl.sort(lambda i: i.dataSource.get('audienceRating').asFloat(), reverse=self.sortDesc)
        elif choice == 'userRating':
            self.showPanelControl.sort(lambda i: i.dataSource.get('titleSort') or i.dataSource.title)
            self.showPanelControl.sort(lambda i: i.dataSource.get('userRating').asFloat(), reverse=self.sortDesc)
        elif choice == 'contentRating':
            self.showPanelControl.sort(lambda i: i.dataSource.get('titleSort') or i.dataSource.title)
            self.showPanelControl.sort(lambda i: i.dataSource.get('contentRating'), reverse=self.sortDesc)
        elif choice == 'resolution':
            self.showPanelControl.sort(lambda i: i.dataSource.maxHeight, reverse=self.sortDesc)
        elif choice == 'duration':
            self.showPanelControl.sort(lambda i: i.dataSource.duration.asInt(), reverse=self.sortDesc)
        elif choice == 'unviewedLeafCount':
            self.showPanelControl.sort(lambda i: i.dataSource.unViewedLeafCount, reverse=self.sortDesc)

        self.showPanelControl.selectItem(0)
        self.setFocusId(self.POSTERS_PANEL_ID)
        self.backgroundSet = False
        self.setBackground([item.dataSource for item in self.showPanelControl], 0,
                           randomize=not util.addonSettings.dynamicBackgrounds)

    def subOptionCallback(self, option):
        check = 'script.plex/home/device/check.png'
        options = None
        subKey = None
        if self.filter and self.filter.get('sub'):
            subKey = self.filter['sub']['val']

        ftype = self._filterTypeByKey.get(option['type'])
        if ftype and ftype != 'boolean':
            # cache suboptions
            ck = (self.librarySettings.getItemType() or self.section.TYPE, option['type'])
            if ck in self.subOptionCache:
                options = self.subOptionCache[ck]
            else:
                options = [{'val': o.key, 'display': o.title, 'indicator': o.key == subKey and check or ''} for o in
                            self.section.listChoices(option['type'],
                                                     libtype=self.librarySettings.getItemType() or self.section.TYPE)]
                self.subOptionCache[ck] = options

            if not options:
                options = [{'val': None, 'display': T(32375, 'No filters available'), 'ignore': True}]

        return options

    def _filterLabel(self, fkey, server_title):
        # Hybrid labels: use pm4k's localized strings for filters we have ids for
        # (keeps wording/translations consistent), and fall back to the server's
        # own title for any filter we don't recognise (e.g. atmos, codec filters).
        known = FILTER_LABELS.get(fkey)
        if known:
            sid, fallback = known
            return T(sid, fallback) if sid else fallback
        return server_title or fkey

    def filter1ButtonClicked(self):
        check = 'script.plex/home/device/check.png'

        libtype = self.librarySettings.getItemType()
        try:
            filters = self.section.listFilters(libtype=libtype)
        except Exception:
            util.ERROR('filter1ButtonClicked: listFilters failed')
            filters = None

        self._filterTypeByKey = {}

        if not filters:
            util.DEBUG_LOG('No filters available for section {0}', self.section.key)
            dropdown.showDropdown(
                [{'val': None, 'display': T(32375, 'No filters available'), 'ignore': True}],
                (200, 106))
            return

        # Group boolean toggles (HDR/DOVI/Atmos/Unwatched/...) at the top, separated from
        # the value filters (genre/year/...). Server order is preserved within each group.
        boolOptions = []
        valueOptions = []

        for f in filters:
            fkey = f.filter
            ftype = f.filterType
            if not fkey:
                continue
            # Folder location filtering is admin-oriented; only surface it for admins.
            if fkey == 'location' and not pnUtil.ACCOUNT.isAdmin:
                continue

            self._filterTypeByKey[fkey] = ftype
            label = self._filterLabel(fkey, f.title)

            if ftype == 'boolean':
                # Caps signals these are combinable toggles, distinct from the
                # single-select (title-case) value categories.
                boolOptions.append({'type': fkey, 'display': label.upper(),
                                    'indicator': self.boolFilters.get(fkey) and check or '',
                                    'is_bool': True})
            else:
                active = self.filter and self.filter.get('type') == fkey
                valueOptions.append({'type': fkey, 'display': label, 'is_sub_list': True,
                                     'indicator': active and check or ''})

        options = []
        if self.filter or any(self.boolFilters.values()):
            options.append({'type': 'clear_filter', 'display': T(32376, 'CLEAR FILTER').upper(),
                            'indicator': 'script.plex/indicators/remove.png'})
            options.append(None)  # Separator

        options.extend(boolOptions)
        if boolOptions and valueOptions:
            options.append(None)  # Separator between toggles and value filters
        options.extend(valueOptions)

        result = dropdown.showDropdown(options, (200, 106), with_indicator=True,
                                       suboption_callback=self.subOptionCallback,
                                       select_item=not self.getBoolProperty('no.content.filtered') and self.filter or None,
                                       open_sublists=not self.getBoolProperty('no.content.filtered'))
        if not result:
            return

        choice = result['type']

        if choice == 'clear_filter':
            self.clearFilters(skip_display=True)
        elif result.get('is_bool') or self._filterTypeByKey.get(choice) == 'boolean':
            if self.boolFilters.get(choice):
                del self.boolFilters[choice]
            else:
                self.boolFilters[choice] = True
            self.librarySettings.setSetting('filter.bools', self.boolFilters)
        else:
            self.filter = result
            self.librarySettings.setSetting('filter', self.filter)

        self.updateFilterDisplay()

        if self.filter or choice == 'clear_filter' or result.get('is_bool') or self._filterTypeByKey.get(choice) == 'boolean':
            self.fill(keep_focus=True)

    def clearFilters(self, skip_display=False):
        self.filter = None
        self.boolFilters = {}
        self.librarySettings.setSetting('filter.bools', self.boolFilters)
        self.librarySettings.setSetting('filter', None)
        if not skip_display:
            self.updateFilterDisplay()

    def resetSort(self):
        self.sort = 'titleSort'
        self.sortDesc = False

        self.librarySettings.setSetting('sort', self.sort)
        self.librarySettings.setSetting('sort.desc', self.sortDesc)

        util.setGlobalProperty('sort', self.sort)
        self.setProperty('sort.display', SORT_KEYS[self.section.TYPE].get(self.sort, SORT_KEYS['movie'].get(self.sort))['display'])

    def updateFilterDisplay(self):
        boolLabels = [self._filterLabel(k, k) for k, on in self.boolFilters.items() if on]
        if self.filter:
            disp = self.filter['display']
            if self.filter.get('sub'):
                disp = u'{0}: {1}'.format(disp, self.filter['sub']['display'])
            self.setProperty('filter1.display', disp)
            self.setProperty('filter2.display', ", ".join(boolLabels))
        else:
            self.setProperty('filter2.display', '')
            if not boolLabels:
                boolLabels = [T(32345, 'All')]
            self.setProperty('filter1.display', ", ".join(boolLabels))

    def showPanelClicked(self):
        mli = self.showPanelControl.getSelectedItem()
        # dataSource truthiness can't be used here: BasePlaylist.__len__() returns
        # len(self._items), which is empty until a playlist's contents are actually loaded, so a
        # freshly-listed (unopened) Playlist object is falsy even though it's a real dataSource - an
        # explicit None-check is required or every playlist click no-ops. Ported from the
        # Sidebar-Tab-Unification branch's identical fix (commit f0e6340f), found live-testing that
        # branch's own Playlists port.
        if not mli or mli.dataSource is None:
            return

        sectionType = self.section.TYPE

        updateUnwatchedAndProgress = False
        # Remember the panel generation before we open any (modal) child window. If the
        # panel gets rebuilt while we're away (e.g. a watchlist item auto-removed on full
        # watch triggers doRefill via onReInit), `mli` below is backed by a freed ListItem
        # and must not be touched - doing so hard-crashes Kodi (SIGSEGV in
        # CGUIListItem::SetProperty).
        listGeneration = self._listGeneration

        self.subOptionCache = {}

        extra_kwargs = {}

        # watchlist
        if sectionType == 'movies_shows':
            extra_kwargs['from_watchlist'] = True
            extra_kwargs['directly_from_watchlist'] = True
            extra_kwargs['external_item'] = True

        # Sidebar entry-section persistence (ported from Sidebar-Tab-Unification's
        # mellow-pondering-magpie.md, 2026-08-18): None/False here for a genuine top-level section
        # (the common case) is exactly equivalent to not passing these at all - only meaningfully
        # differs when this LibraryWindow instance was itself opened as a drilled-in child (a
        # collection/subDir view) inheriting an ancestor's entrySectionId, in which case that keeps
        # propagating instead of being lost - see this window's own buildSectionList(). Folded into
        # extra_kwargs (not a separate dict) since every branch below already either uses
        # extra_kwargs or wants these two keys the same way.
        extra_kwargs['entry_section_id'] = self.entrySectionId
        extra_kwargs['entry_from_watchlist'] = self.entryFromWatchlist

        if mli.dataSource.TYPE == 'collection':
            # collection.CollectionWindow (not a nested LibraryWindow) - a plain bounded grid, no
            # LibrarySettings/ITEM_TYPE involved at all, so none of the old restore-after-a-
            # blocking-nested-window dance is needed any more. See hashed-orbiting-pizza.md's
            # Phase 4.
            self.openWindow(collection.CollectionWindow, collection=mli.dataSource, **extra_kwargs)
        elif self.section.TYPE == 'show' or mli.dataSource.TYPE == 'show' or mli.dataSource.TYPE == 'season' or mli.dataSource.TYPE == 'episode':
            if ITEM_TYPE == 'episode' or mli.dataSource.TYPE == 'episode' or mli.dataSource.TYPE == 'season':
                self.openItem(mli.dataSource, **extra_kwargs)
            else:
                # hashed-orbiting-pizza.md Phase 4 item 3: self.openWindow(), not
                # opener.handleOpen() directly - same reasoning as the PrePlayWindow branch below.
                self.openWindow(subitems.ShowWindow, media_item=mli.dataSource, parent_list=self.showPanelControl, **extra_kwargs)
            if mli.dataSource.TYPE != 'season': # NOTE: A collection with Seasons doesn't have the leafCount/viewedLeafCount until you actually go into the season so we can't update the unwatched count here
                updateUnwatchedAndProgress = True
        elif self.section.TYPE == 'movie' or mli.dataSource.TYPE == 'movie':
            datasource = mli.dataSource
            if datasource.isDirectory():
                # collection.SubDirWindow (not a nested LibraryWindow) - a plain bounded grid, same
                # shape as the collection branch above, no LibrarySettings/ITEM_TYPE involved at
                # all any more. This structurally eliminates the class of bug ignoreLibrarySettings
                # (below, in the now-superseded nested-LibraryWindow path this replaced) fixed - the
                # new shell never touches LibrarySettings/ITEM_TYPE, so it has nothing left to
                # clobber. See hashed-orbiting-pizza.md's Phase 4.
                self.openWindow(collection.SubDirWindow, section=collection.buildSubDirSection(self.section, datasource),
                                **extra_kwargs)
            else:
                # hashed-orbiting-pizza.md Phase 4 item 1: self.openWindow(), not
                # opener.handleOpen() directly - swaps PrePlayWindow in place via this window's
                # own swapTo() (self._chainHost always points at self, __init__) instead of
                # opening a second real nested window. parent_list=self.showPanelControl is safe
                # to keep passing through unchanged - PrePlayWindow only ever reads it for
                # next/prev-in-grid lookups (preplay.py's _next()/_prev()), pure Python-side
                # ManagedControlList data reads, not native-control reads, and self.showPanelControl
                # lives on this outer, persistent LibraryWindow instance (never torn down when
                # hosting a shell - only self._current, the native window, is).
                self.openWindow(preplay.PrePlayWindow if not sectionType == 'movies_shows' else preplay.PrePlayWindowWL,
                                 video=datasource, parent_list=self.showPanelControl, **extra_kwargs)
                updateUnwatchedAndProgress = True
        elif self.section.TYPE == 'artist' or mli.dataSource.TYPE == 'artist' or mli.dataSource.TYPE == 'album' or mli.dataSource.TYPE == 'track':
            if ITEM_TYPE == 'album' or mli.dataSource.TYPE == 'album' or mli.dataSource.TYPE == 'track':
                self.openItem(mli.dataSource, entry_section_id=self.entrySectionId)
            else:
                # hashed-orbiting-pizza.md Phase 4 item 3: self.openWindow(), not
                # opener.handleOpen() directly - same reasoning as the PrePlayWindow branch above.
                self.openWindow(subitems.ArtistWindow, media_item=mli.dataSource, parent_list=self.showPanelControl,
                                 entry_section_id=self.entrySectionId, entry_from_watchlist=self.entryFromWatchlist)
        elif self.section.TYPE in ('photo', 'photodirectory'):
            self.showPhoto(mli.dataSource)
        elif self.section.TYPE == 'playlists':
            # Mirrors the 'collection' branch above - opener.open()'s existing playlist-TYPE
            # branch (opener.py) already routes to playlist.PlaylistWindow correctly.
            self.processCommand(opener.open(mli.dataSource))

        if self._closeSignalled:
            return

        if not mli:
            return

        if self._listGeneration != listGeneration:
            # Panel was rebuilt while the child window was open; `mli` is stale. The fresh
            # panel already reflects current watched/progress state, so nothing to do.
            return

        if mli.dataSource and not mli.dataSource.exists():
            self.showPanelControl.removeItem(mli.pos())
            return

        if updateUnwatchedAndProgress:
            self.updateUnwatchedAndProgress(mli)

    def showPhoto(self, photo):
        self.subOptionCache = {}
        if isinstance(photo, plexnet.photo.Photo) or photo.TYPE == 'clip':
            self.processCommand(opener.open(photo))
        else:
            self.processCommand(opener.sectionClicked(photo, context=self))

    def updateUnwatchedAndProgress(self, mli):
        mli.dataSource.reload()
        if mli.dataSource.isWatched:
            mli.setProperty('unwatched', '')
            mli.setProperty('unwatched.count', '')
        else:
            if self.section.TYPE == 'show' or mli.dataSource.TYPE == 'show' or mli.dataSource.TYPE == 'season':
                mli.setProperty('unwatched.count', str(mli.dataSource.unViewedLeafCount))
                mli.setBoolProperty('unwatched.count.large', mli.dataSource.unViewedLeafCount > 999)
            else:
                mli.setProperty('unwatched', '1')
        mli.setBoolProperty('watched', mli.dataSource.isFullyWatched)
        mli.setProperty('progress', util.getProgressImage(mli.dataSource))

    def setTitle(self):
        self.setProperty('screen.title', self.section.title)

        self.updateFilterDisplay()

    def updateItem(self, mli=None):
        mli = mli or self.showPanelControl.getSelectedItem()
        if not mli or mli.dataSource:
            return

        for task in self.tasks:
            if task.contains(mli.pos()):
                util.DEBUG_LOG('Moving task to front: {0}', task)
                backgroundthread.BGThreader.moveToFront(task)
                break

    def setBackground(self, items, position, randomize=True):
        if self.backgroundSet:
            return

        if randomize:
            item = random.choice(items)
            self.updateBackgroundFrom(item)
        else:
            # we want the first item of the first chunk
            if position != 0:
                return

            self.updateBackgroundFrom(items[0])
        self.backgroundSet = True

    def fill(self, keep_focus=False):
        self.backgroundSet = False

        if self.section.TYPE in ('photo', 'photodirectory'):
            self.fillPhotos()
        elif self.section.TYPE == 'playlists':
            self.fillPlaylists(keep_focus=keep_focus)
        else:
            self.fillShows(keep_focus=keep_focus)

    def getFilterOpts(self):
        if not self.filter:
            return None

        if not self.filter.get('sub'):
            #util.DEBUG_LOG('Filter missing sub-filter data')
            return self.filter['type'], "1"

        if isinstance(self.filter['sub']['val'], six.string_types) and self.filter['sub']['val'].startswith("/"):
            return self.filter['type'], self.filter['sub']['val']
        return self.filter['type'], six.moves.urllib.parse.unquote_plus(self.filter['sub']['val'])

    def getSortOpts(self):
        if not self.sort:
            return None

        return (self.sort, self.sortDesc and 'desc' or 'asc')


    def getDefChunkSize(self, size):
        return self.DEFAULT_ITEMS_CHUNK_SIZE if size < 1000 else self.DEFAULT_ITEMS_CHUNK_SIZE_BIG

    @property
    def thumb_fallback(self):
        return 'script.plex/thumb_fallbacks/{0}.png'.format(TYPE_KEYS.get(self.section.type, TYPE_KEYS['movie'])['fallback'])

    @busy.dialog()
    def fillShows(self, keep_focus=False):
        self.setBoolProperty('no.content', False)
        self.setBoolProperty('no.content.filtered', False)
        self.setBoolProperty('content.filling', True)
        items = []
        jitems = []
        self.keyItems = {}
        self.firstOfKeyItems = {}
        totalSize = 0
        self.alreadyFetchedChunkList = set()
        self.finalChunkPosition = 0

        type_ = getQueryItemType(self.section)
        # supplying this type kills all results (bug: 2025/10/21)
        if type_ == plexobjects.SEARCHTYPES["photo"]:
            type_ = None

        tasks = []

        # boolean filters (hdr/dovi/unwatched/inProgress/...) flow through as a dict
        bool_filters = self.boolFilters

        jumpList = None
        # The server's firstCharacter/jumpList endpoint only makes sense for alphabetical
        # sorts, and only for the item types/sections it's known to support: episode titles
        # are excluded since browsing episodes by their own title isn't a sensible A-Z
        # anchor, but show.titleSort groups by the parent show's title, so episodes are let
        # through specifically for that one. artist.titleSort is excluded outright - the
        # server 500s on it (confirmed against a real PMS), so it always falls through to
        # the plain scrollbar below instead.
        if isAlphaSort(self.sort) and self.sort != 'artist.titleSort' and ITEM_TYPE != 'folder' \
                and (ITEM_TYPE != 'episode' or self.sort == 'show.titleSort') \
                and not self.subDir and self.section.TYPE not in ("collection", "movies_shows"):
            # find library collection mode setting, as we need to force-feed the collection type to the jumpList,
            # if collection_mode is 2, otherwise the returned item count differs from /all with the same parameters
            collection_mode = self.section.settings.get("collectionMode",
                                                       {"value": plexobjects.PlexValue(2)})["value"].asInt()

            jl_type = type_
            if collection_mode == 2 and not (self.filter or self.boolFilters.get('unwatched')):
                jl_type = getQueryItemType(self.section, fallback_to_section_type=True, force_include_collections=True)

            jumpList = self.section.jumpList(filter_=self.getFilterOpts(), sort=self.getSortOpts(),
                                             type_=jl_type, bool_filters=bool_filters)
            if jumpList is None:
                # Endpoint doesn't support this sort/type combo (or errored) - fall back to
                # a regular fetch below rather than reporting the section as empty.
                util.DEBUG_LOG('jumpList() unavailable for sort {0}/type {1}, falling back to all()',
                               self.sort, ITEM_TYPE)

        if jumpList:
            idx = 0
            for kidx, ji in enumerate(jumpList):
                ji_size = ji.size.asInt()
                mli = kodigui.ManagedListItem(ji.title, data_source=ji.key)
                mli.setProperty('key', ji.key)
                mli.setProperty('index', str(kidx))
                mli.setProperty('original', '{0:02d}'.format(kidx))
                self.keyItems[ji.key] = mli
                jitems.append(mli)
                totalSize += ji_size

                tasks.append(CreateDefaultItemsTask().setup(idx, ji.size.asInt(), totalSize, self.thumb_fallback, self._defaultItemsCallback, key=ji.key))
                idx += ji_size

            util.DEBUG_LOG('JumpList item size: {}', totalSize)

            util.setGlobalProperty('key', jumpList[0].key)
        else:
            if ITEM_TYPE == 'folder':
                sectionAll = self.section.folder(0, 0, self.subDir)
            else:
                sectionAll = self.section.all(0, 0, filter_=self.getFilterOpts(), sort=self.getSortOpts(),
                                              type_=type_, bool_filters=bool_filters)

            totalSize = sectionAll.totalSize.asInt()

            if not totalSize:
                self.showPanelControl.reset()
                self.keyListControl.reset()

                if (self.filter or any(self.boolFilters.values())
                        or self.librarySettings.getItemType()):
                    self.setBoolProperty('no.content.filtered', True)
                else:
                    self.setBoolProperty('no.content', True)

                return
            else:
                for startPosition in range(0, totalSize, self.getDefChunkSize(totalSize)):
                    tasks.append(CreateDefaultItemsTask().setup(startPosition, self.getDefChunkSize(totalSize), totalSize, self.thumb_fallback, self._defaultItemsCallback))

        self.setProperty("items.count", str(totalSize))

        self.showPanelControl.reset()
        self.keyListControl.reset()

        # Start the background tasks to create the default items
        self.tasks.add(tasks)
        backgroundthread.BGThreader.addTasksToFront(tasks)

        # Wait for the default items to be created
        while backgroundthread.BGThreader.working() and not util.MONITOR.abortRequested():
            util.MONITOR.waitFor()

        if jitems:
            self.keyListControl.addItems(jitems)

        util.setGlobalProperty('sort.alpha', jitems and '1' or '')

        self.showPanelControl.selectItem(0)
        if not keep_focus:
            self.setFocusId(self.POSTERS_PANEL_ID)

        generation = self._listGeneration
        tasks = []
        for startChunkPosition in range(0, totalSize, self.CHUNK_SIZE):
            tasks.append(
                ChunkRequestTask().setup(
                    self.section, startChunkPosition, self.CHUNK_SIZE, self._chunkCallbackFor(generation),
                    filter_=self.getFilterOpts(), sort=self.getSortOpts(), subDir=self.subDir, bool_filters=bool_filters
                )
            )

            # If we're retrieving media as we navigate then we just want to request the first
            # chunk of media and stop.  We'll fetch the rest as the user navigates to those items
            if not util.addonSettings.retrieveAllMediaUpFront:
                # Calculate the end chunk's starting position based on the totalSize of items
                self.finalChunkPosition = (totalSize // self.CHUNK_SIZE) * self.CHUNK_SIZE
                # Keep track of the chunks we've already fetched by storing the chunk's starting position
                self.alreadyFetchedChunkList.add(startChunkPosition)
                break

        self.tasks.add(tasks)
        backgroundthread.BGThreader.addTasksToFront(tasks)

    def showPhotoItemProperties(self, photo):
        if photo.isFullObject():
            return

        task = PhotoPropertiesTask().setup(photo, self._showPhotoItemProperties)
        self.tasks.add(task)
        backgroundthread.BGThreader.addTasksToFront([task])

    def _showPhotoItemProperties(self, photo):
        mli = self.showPanelControl.getSelectedItem()
        if not mli or not mli.dataSource.TYPE == 'photo':
            for mli in self.showPanelControl:
                if mli.dataSource == photo:
                    break
            else:
                return

        mli.setProperty('camera.model', photo.media[0].model)
        mli.setProperty('camera.lens', photo.media[0].lens)

        attrib = []
        if photo.media[0].height:
            attrib.append(u'{0} x {1}'.format(photo.media[0].width, photo.media[0].height))

        orientation = photo.media[0].parts[0].orientation
        if orientation:
            attrib.append(u'{0} Mo'.format(orientation))

        container = photo.media[0].container_ or os.path.splitext(photo.media[0].parts[0].file)[-1][1:].lower()
        if container == 'jpg':
            container = 'jpeg'
        attrib.append(container.upper())
        if attrib:
            mli.setProperty('photo.dims', u' \u2022 '.join(attrib))

        settings = []
        if photo.media[0].iso:
            settings.append('ISO {0}'.format(photo.media[0].iso))
        if photo.media[0].aperture:
            settings.append('{0}'.format(photo.media[0].aperture))
        if photo.media[0].exposure:
            settings.append('{0}'.format(photo.media[0].exposure))
        mli.setProperty('camera.settings', u' \u2022 '.join(settings))
        mli.setProperty('photo.summary', photo.get('summary'))

    def createPlaylistGridListItem(self, obj):
        # Square tiles for both audio/video, 'thumb' composite (matches what the playlist detail
        # screen shows, not the old 'art' backdrop-style video rendering), item count instead of
        # duration. Ported from the Sidebar-Tab-Unification branch's identical method (commit
        # f0e6340f), which itself mirrors HomeWindow.createPlaylistListItem() (home.py, f69b1e7e).
        # Named distinctly from the pre-existing createPlaylistListItem() (below,
        # CREATE_LI_MAP/createListItem()'s hub-tile dispatch, a different rendering context - hub
        # rows use self.THUMB_SQUARE_DIM at 220x220, this grid view uses the module-level
        # THUMB_SQUARE_DIM at 355x355, same dimension every other grid-view create*ListItem() uses)
        # - same method name on the same class would have silently shadowed one or the other.
        w, h = THUMB_SQUARE_DIM
        thumb = obj.buildComposite(width=w, height=h, media='thumb')

        itemCount = T(35055, '{0} items').format(obj.leafCount.asInt())
        mli = kodigui.ManagedListItem(
            obj.title or '',
            itemCount,
            thumbnailImage=thumb,
            data_source=obj
        )
        mli.setProperty('thumb.fallback', 'script.plex/thumb_fallbacks/{0}.png'.format(
            obj.playlistType == 'audio' and 'music' or 'movie'))
        # script-plex-squares.xml.tpl's own item template reads the tile's second line from the
        # album.artist property (not ListItem.Label2, unlike the listview-square template, which
        # does use Label2 - set above too, for that view). Reusing the same property/mechanism the
        # Artist grid already renders rather than touching the shared squares template's layout.
        mli.setProperty('album.artist', itemCount)
        return mli

    def _setPlaylistBackground(self, pl):
        """Background art + corner-panel colors for a single playlist - factored out of
        fillPlaylists() so the same per-item treatment can also run on focus-move (onAction()'s
        MOVE_SET handling below), not just once at fill time. Needed at all because playlists
        never go through the generic updateBackgroundFrom()/setBackground() path: that keys off
        ds.get('art', ...), which playlists don't have - mirrors the old playlists.py's own
        fill(), which set 'background' directly from .composite instead for the same reason.

        windowSetBackground(), not a bare setProperty(): a bare setProperty() skips the
        background_static/LAST_BG_URL bookkeeping windowSetBackground() (kodigui.py) does for
        every other background-setting path in the app - live-confirmed as a stale-art flash
        without it (a bare setProperty() here left 'background' pointing at a playlist's
        composite while background_static/LAST_BG_URL still held whatever the *previous*
        Recommended-tab visit last set, so the next Recommended entry whose anchor happened to
        match LAST_BG_URL again silently kept showing this playlist's art instead of the real
        new value).

        Panel corners: playlists have no ultraBlurColors of their own (not a Video/Photo/Audio
        media item at all), so backgroundPanelCorners() is called directly with seed= instead of
        through updateBackgroundFrom() - real ultraBlurColors is never an option here, only the
        seeded fake-color fallback, seeded from this same playlist so art and panel stay paired.
        """
        self.windowSetBackground(util.backgroundFromArt(
            pl.composite, width=self.width, height=self.height))
        self._setPanelCorners(util.backgroundPanelCorners(
            None, seed=pl.get('ratingKey') or pl.title))

    @busy.dialog()
    def fillPlaylists(self, keep_focus=False):
        # Playlists were never a paginated library query (see the old playlists.py's own fill()) -
        # a single small synchronous fetch, filtered client-side by the current tab (ITEM_TYPE:
        # 'audio'/'video'), populating showPanelControl directly rather than going through
        # fillShows()'s section.all()/jumpList()/ChunkRequestTask machinery, none of which applies.
        # Ported from the Sidebar-Tab-Unification branch's identical method (commit f0e6340f).
        self.setBoolProperty('no.content', False)
        self.setBoolProperty('no.content.filtered', False)
        self.setBoolProperty('content.filling', True)

        playlists = [pl for pl in plexapp.SERVERMANAGER.selectedServer.playlists()
                    if pl.playlistType == ITEM_TYPE]

        self.showPanelControl.reset()
        self.keyListControl.reset()
        util.setGlobalProperty('sort.alpha', '')
        self.setProperty("items.count", str(len(playlists)))

        if not playlists:
            self.setBoolProperty('no.content', True)
            self.setBoolProperty('content.filling', False)
            return

        items = []
        for idx, pl in enumerate(playlists):
            mli = self.createPlaylistGridListItem(pl)
            mli.setProperty('index', str(idx))
            items.append(mli)

        if not self.backgroundSet:
            self._setPlaylistBackground(random.choice(playlists))
            self.backgroundSet = True

        self.showPanelControl.addItems(items)
        self.showPanelControl.selectItem(0)
        if not keep_focus:
            self.setFocusId(self.POSTERS_PANEL_ID)

        self.setBoolProperty('content.filling', False)

    @busy.dialog()
    def fillPhotos(self):
        self.setBoolProperty('no.content', False)
        self.setBoolProperty('no.content.filtered', False)
        items = []
        keys = []
        self.firstOfKeyItems = {}
        idx = 0

        if self.section.TYPE == 'photodirectory':
            photos = self.section.all()
        else:
            photos = self.section.all(filter_=self.getFilterOpts(), sort=self.getSortOpts(), bool_filters=self.boolFilters)

        if not photos:
            return

        photo = random.choice(photos)
        self.updateBackgroundFrom(photo)
        thumbDim = TYPE_KEYS.get(self.section.type, TYPE_KEYS['movie'])['thumb_dim']
        fallback = 'script.plex/thumb_fallbacks/{0}.png'.format(TYPE_KEYS.get(self.section.type, TYPE_KEYS['movie'])['fallback'])

        if not photos:
            if self.filter or any(self.boolFilters.values()):
                self.setBoolProperty('no.content.filtered', True)
            else:
                self.setBoolProperty('no.content', True)
            return

        self.setProperty("items.count", photos.totalSize)

        for photo in photos:
            title = photo.title
            if photo.TYPE == 'photodirectory':
                thumb = photo.composite.asTranscodedImageURL(*thumbDim)
                mli = kodigui.ManagedListItem(title, thumbnailImage=thumb, data_source=photo)
                mli.setProperty('is.folder', '1')
            else:
                thumb = photo.defaultThumb.asTranscodedImageURL(*thumbDim)
                label2 = util.cleanLeadingZeros(photo.originallyAvailableAt.asDatetime('%d %B %Y'))
                mli = kodigui.ManagedListItem(title, label2, thumbnailImage=thumb, data_source=photo)

            mli.setProperty('thumb.fallback', fallback)
            mli.setProperty('index', str(idx))

            key = title[0].upper()
            if key not in KEYS:
                key = '#'
            if key not in keys:
                self.firstOfKeyItems[key] = mli
                keys.append(key)
            mli.setProperty('key', str(key))
            items.append(mli)
            idx += 1

        litems = []
        self.keyItems = {}
        # Keys are collected above in whatever order items were fetched in, which is only
        # alphabetical when the fetch itself was sorted by title - otherwise the letters
        # would show up in a meaningless, jumbled order, so skip building the scrubber list.
        if isAlphaSort(self.sort):
            for i, key in enumerate(keys):
                mli = kodigui.ManagedListItem(key, data_source=key)
                mli.setProperty('key', key)
                mli.setProperty('original', '{0:02d}'.format(i))
                self.keyItems[key] = mli
                litems.append(mli)

        self.showPanelControl.reset()
        self.keyListControl.reset()

        self.showPanelControl.addItems(items)
        self.keyListControl.addItems(litems)

        util.setGlobalProperty('sort.alpha', litems and '1' or '')

        if keys:
            util.setGlobalProperty('key', keys[0])

    def _defaultItemsCallback(self, items, key, firstMli):
        if not items:
            return

        while True:
            self.lock.acquire()
            # When creating the default items for the title sort we need to add them to the list
            # in order.  So we look at the first index of the incoming items to see if it's the
            # next batch of items to add.  If not then it releases the lock and adds a small delay
            # so that other threads can grab the lock.
            if key and firstMli:
                if int(firstMli.getProperty('index')) != self.showPanelControl.size():
                    self.lock.release()
                    xbmc.sleep(1)
                    continue

                self.firstOfKeyItems[key] = firstMli

            self.showPanelControl.addItems(items)
            self.lock.release()
            break

    def _chunkCallbackFor(self, generation):
        """Wraps _chunkCallback() with the _listGeneration snapshot taken when the chunk fetch
        was scheduled, so a chunk that finishes after an openSection()/switchTab() in-place swap
        (bumps _listGeneration immediately, but self.tasks.kill() can't preempt a fetch that's
        already past its own isCanceled() check and mid-callback) gets recognized as stale and
        discarded, instead of writing into/setting background properties on a window that's
        moved on - live-confirmed as "Window id does not exist" errors otherwise (the swap's
        new/closing window not having a valid native id at that exact moment). self.closing
        (checked below) only covers the whole LibraryWindow session ending, not an in-place
        swap - this is the missing check for that case specifically.
        """
        def callback(items, start):
            self._chunkCallback(items, start, generation)
        return callback

    def _chunkCallback(self, items, start, generation=None):
        if generation is not None and generation != self._listGeneration:
            util.DEBUG_LOG("Library: _chunkCallback() declined - stale generation ({0} != {1})",
                           generation, self._listGeneration)
            return

        if not self.showPanelControl or not items or self.closing:
            return

        with self.lock:
            pos = start
            self.setBackground(items, pos, randomize=not util.addonSettings.dynamicBackgrounds)

            thumbDim = TYPE_KEYS.get(self.section.type, TYPE_KEYS['movie'])['thumb_dim']
            artDim = TYPE_KEYS.get(self.section.type, TYPE_KEYS['movie']).get('art_dim', (256, 256))

            if not self.showPanelControl:
                return

            if ITEM_TYPE == 'episode':
                for offset, obj in enumerate(items):
                    mli = self.showPanelControl[pos]
                    if obj:
                        mli.dataSource = obj
                        mli.setProperty('index', str(pos))
                        if obj.index:
                            subtitle = u'{0} \u2022 {1}'.format(T(32310, 'S').format(obj.parentIndex),
                                                                T(32311, 'E').format(obj.index))
                            mli.setProperty('subtitle', subtitle)
                            subtitle = "\n" + subtitle
                        else:
                            subtitle = ' - ' + obj.originallyAvailableAt.asDatetime('%m/%d/%y')
                        mli.setLabel((obj.defaultTitle or ''))# + subtitle)

                        mli.setThumbnailImage(obj.defaultThumb.asTranscodedImageURL(*thumbDim))

                        mli.setProperty('summary', obj.summary)

                        #mli.setLabel2(util.durationToText(obj.fixedDuration()))
                        mli.setLabel2(subtitle)
                        mli.setProperty('art', obj.defaultArt.asTranscodedImageURL(*artDim))
                        if not obj.isWatched:
                            mli.setProperty('unwatched', '1')
                        mli.setBoolProperty('watched', obj.isFullyWatched)
                        mli.setProperty('initialized', '1')
                    else:
                        mli.clear()
                        if obj is False:
                            mli.setProperty('index', str(pos))
                        else:
                            mli.setProperty('index', '')

                    pos += 1

            elif ITEM_TYPE == 'album':
                for offset, obj in enumerate(items):
                    mli = self.showPanelControl[pos]
                    if obj:
                        mli.dataSource = obj
                        mli.setProperty('index', str(pos))
                        mli.setLabel(obj.title)
                        mli.setProperty('album.artist', obj.parentTitle)

                        mli.setThumbnailImage(obj.defaultThumb.asTranscodedImageURL(*thumbDim))

                        mli.setProperty('summary', obj.summary)

                        mli.setLabel2(obj.year)
                    else:
                        mli.clear()
                        if obj is False:
                            mli.setProperty('index', str(pos))
                        else:
                            mli.setProperty('index', '')

                    pos += 1
            else:
                for offset, obj in enumerate(items):

                    try:
                        mli = self.showPanelControl[pos]
                    except RuntimeError:
                        util.LOG("Library/ChunkCallback: {} not found", pos)
                        pos += 1
                        continue

                    if obj:
                        mli.setProperty('index', str(pos))

                        if obj.TYPE == 'track':
                            mli.setLabel("{} - {}: {}".format(obj.grandparentTitle, obj.parentTitle, obj.title))
                        else:
                            mli.setLabel(obj.defaultTitle or '')

                        if obj.TYPE == 'collection':
                            colArtDim = TYPE_KEYS.get('collection').get('art_dim', (256, 256))
                            mli.setProperty('art', obj.artCompositeURL(*colArtDim))
                            mli.setThumbnailImage(obj.server.getImageTranscodeURL(
                                obj.artCompositeURL(*tuple(2*dim for dim in thumbDim)), *thumbDim)
                            )
                        else:
                            if obj.TYPE == 'photodirectory' and obj.composite:
                                mli.setThumbnailImage(obj.composite.asTranscodedImageURL(*thumbDim))
                            else:
                                mli.setThumbnailImage(obj.defaultThumb.asTranscodedImageURL(*thumbDim))
                        mli.dataSource = obj
                        mli.setProperty('summary', obj.get('summary'))

                        # get secondary sort based info
                        sk_data = SORT_KEYS[self.section.TYPE].get(self.sort, {'subDisplay': None})
                        sub_display = sk_data.get('subDisplay', None)
                        sub_title = obj.get('year')
                        if sub_display:
                            if hasattr(obj, "meta_{}".format(sub_display)):
                                res = getattr(obj, "meta_{}".format(sub_display))('')
                                if res:
                                    exclusive = sk_data.get('subDisplayExclusive', False)
                                    sub_title = res
                                    if not exclusive:
                                        sub_title = "{} ({})".format(res, obj.get('year'))
                        mli.setProperty('year', sub_title)

                        if obj.TYPE != 'collection':
                            if not obj.isDirectory() and obj.get('duration').asInt():
                                mli.setLabel2(util.durationToText(obj.fixedDuration()))
                            mli.setProperty('art', obj.defaultArt.asTranscodedImageURL(*artDim))
                            if not obj.isWatched and obj.TYPE != "Directory":
                                if self.section.TYPE == 'show' or obj.TYPE == 'show' or obj.TYPE == 'season':
                                    mli.setProperty('unwatched.count', str(obj.unViewedLeafCount))
                                    mli.setBoolProperty('unwatched.count.large', obj.unViewedLeafCount > 999)
                                else:
                                    mli.setProperty('unwatched', '1')
                            elif obj.isFullyWatched and obj.TYPE != "Directory":
                                mli.setBoolProperty('watched', '1')
                            mli.setProperty('initialized', '1')

                        mli.setProperty('progress', util.getProgressImage(obj))
                    else:
                        mli.clear()
                        if obj is False:
                            mli.setProperty('index', str(pos))
                        else:
                            mli.setProperty('index', '')

                    pos += 1

        self.setBoolProperty('content.filling', False)

    def requestChunk(self, start):
        if util.addonSettings.retrieveAllMediaUpFront or self.section.TYPE == 'playlists':
            # fillPlaylists() always fetches the whole (small, unpaginated) list synchronously up
            # front - there's never a further chunk to request, and PlaylistsSection has no all()
            # for ChunkRequestTask to call (confirmed by the Sidebar-Tab-Unification branch's own
            # live test: AttributeError otherwise, triggered by ordinary focus movement in the
            # panel).
            return

        # Calculate the correct starting chunk position for the item they passed in
        startChunkPosition = (start // self.CHUNK_SIZE) * self.CHUNK_SIZE
        # If we calculated a chunk position that's beyond the end chunk then just return
        if startChunkPosition > self.finalChunkPosition:
            return

        # Check if the chunk has already been requested, if not then go fetch the data
        if startChunkPosition not in self.alreadyFetchedChunkList:
            util.DEBUG_LOG('Position {0} so requesting chunk {1}', start, startChunkPosition)
            # Keep track of the chunks we've already fetched by storing the chunk's starting position
            self.alreadyFetchedChunkList.add(startChunkPosition)
            task = ChunkRequestTask().setup(self.section, startChunkPosition, self.CHUNK_SIZE,
                                            self._chunkCallbackFor(self._listGeneration), filter_=self.getFilterOpts(),
                                            sort=self.getSortOpts(), subDir=self.subDir, bool_filters=self.boolFilters)

            self.tasks.add(task)
            backgroundthread.BGThreader.addTasksToFront([task])

    # ------------------------------------------------------------------------------------------
    # Stage C: ported from home.py's HomeWindow, Recommended-tab sharing (quiet-orbiting-heron.md)
    # -- not yet wired into any call path (Stage D). Mechanical, verbatim-where-possible port of
    # the display-type inference, hub-settings persistence, hub visibility/ordering, and per-item-
    # type ListItem builder logic that's already section-generic in HomeWindow. Nothing below is
    # called by anything yet outside this group of methods calling each other (e.g. createListItem()
    # dispatching to the per-type builders). home.py itself is untouched - HomeWindow keeps its own
    # copies, still the live Home experience today.
    # ------------------------------------------------------------------------------------------

    # Hub identifier prefixes that indicate 16x9 display format
    HUB_PREFIXES_16X9 = ('video.', 'music.videos.')

    # Hub identifiers that have mixed content (movies + episodes) - always use poster format
    HUBS_MIXED_CONTENT = {
        'continueWatching',  # Combined continue watching hub (modern Plex clients) - mixed movies/episodes
        'home.ondeck',  # Old-style On Deck hub - uses show posters
        'tv.inprogress', 'tv.ondeck', 'movie.inprogress',
    }
    # Note: home.continue (old Continue Watching) is NOT in HUBS_MIXED_CONTENT
    # because it shows episodes only and should use 16x9 thumbnails

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

    def getHubRenderFlags(self, hub, identifier):
        """Get rendering flags for a hub based on identifier patterns and content.

        Returns dict with: with_progress, do_updates, text2lines, ar16x9, with_art
        All hubs get sensible defaults - no fixed index mapping.
        """
        # Default flags - most hubs want these
        flags = {
            'with_progress': True,
            'do_updates': True,
            'text2lines': True,
            'ar16x9': False,
            'with_art': False,
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

    @staticmethod
    def inferDisplayType(hub):
        """Infer display type from the first item in the hub."""
        if not hub.items:
            return "poster"  # Default fallback

        item_type = hub.items[0].type
        return LibraryWindow.TYPE_TO_DISPLAY.get(item_type, "poster")

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
        # Old-style split Continue Watching hub (episodes only)
        'home.continue': 'ar16x9',
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

        enabled = {h.get('catalog_id', h.get('identifier')) for h in section_config.get('hubs', [])}

        # When CW mode changes, the hub identifiers change but saved config may have old ones.
        # Map between them so hubs stay enabled after switching modes.
        if section_key is None:  # Home section only
            use_new_continue_watching = util.getSetting('hubs_use_new_continue_watching', False)
            if use_new_continue_watching:
                if 'home.continue' in enabled or 'home.ondeck' in enabled:
                    enabled.add('continueWatching')
            else:
                if 'continueWatching' in enabled:
                    enabled.add('home.continue')
                    enabled.add('home.ondeck')

        return enabled

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

        # Use getEnabledHubsForSection so CW mode mapping is applied consistently.
        # (e.g. config has 'continueWatching' but old mode expects 'home.continue'/'home.ondeck')
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

        # When CW mode changes, map order between old/new identifiers so user ordering is preserved.
        if section_key is None:  # Home section only
            use_new_continue_watching = util.getSetting('hubs_use_new_continue_watching', False)
            if use_new_continue_watching:
                if 'home.continue' in user_order and 'continueWatching' not in user_order:
                    user_order['continueWatching'] = user_order['home.continue']
                elif 'home.ondeck' in user_order and 'continueWatching' not in user_order:
                    user_order['continueWatching'] = user_order['home.ondeck']
            else:
                if 'continueWatching' in user_order:
                    cw_order = user_order['continueWatching']
                    if 'home.continue' not in user_order:
                        user_order['home.continue'] = cw_order
                    if 'home.ondeck' not in user_order:
                        user_order['home.ondeck'] = cw_order + 0.5

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

        config_key = str(section_key) if section_key is not None else None

        section_config = self.hubSettings.get(config_key, {}) if self.hubSettings else {}
        has_custom_config = section_config.get('custom', False)
        configured_hubs = section_config.get('hubs', []) if has_custom_config else []

        if section_key is None and has_custom_config and configured_hubs:
            use_new_continue_watching = util.getSetting('hubs_use_new_continue_watching', False)
            configured_ids = {h.get('catalog_id', h.get('identifier')) for h in configured_hubs}
            if use_new_continue_watching and ('home.continue' in configured_ids or 'home.ondeck' in configured_ids) \
                    and 'continueWatching' not in configured_ids:
                old_entries = [h for h in configured_hubs
                               if h.get('catalog_id') in ('home.continue', 'home.ondeck')]
                min_order = min(h.get('order', 999) for h in old_entries)
                new_hubs = [h for h in configured_hubs
                            if h.get('catalog_id') not in ('home.continue', 'home.ondeck')]
                new_hubs.append({'catalog_id': 'continueWatching', 'order': min_order})
                new_hubs.sort(key=lambda h: h.get('order', 999))
                for i, h in enumerate(new_hubs):
                    h['order'] = i
                section_config['hubs'] = new_hubs
                self.saveHubSettings()
            elif not use_new_continue_watching and 'continueWatching' in configured_ids \
                    and 'home.continue' not in configured_ids and 'home.ondeck' not in configured_ids:
                cw_entry = next(h for h in configured_hubs if h.get('catalog_id') == 'continueWatching')
                cw_order = cw_entry.get('order', 0)
                new_hubs = [h for h in configured_hubs if h.get('catalog_id') != 'continueWatching']
                new_hubs.append({'catalog_id': 'home.continue', 'order': cw_order})
                new_hubs.append({'catalog_id': 'home.ondeck', 'order': cw_order + 0.5})
                new_hubs.sort(key=lambda h: h.get('order', 999))
                for i, h in enumerate(new_hubs):
                    h['order'] = i
                section_config['hubs'] = new_hubs
                self.saveHubSettings()

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
            section_key = getattr(self, '_managingHubsForSection', self.lastSection.key)
            section_title = getattr(self, '_managingHubsForSectionTitle', '')
            self._discoverHubsSync()
            options = self._buildHubSettingsOptions(section_key, section_title)
            return ('rebuild', options, 0)

        if choice.get('key') == 'reset_hubs':
            section_key = getattr(self, '_managingHubsForSection', self.lastSection.key)
            section_title = getattr(self, '_managingHubsForSectionTitle', '')
            self.resetSectionHubs(section_key)
            self._hubsSettingsChanged = True
            options = self._buildHubSettingsOptions(section_key, section_title)
            return ('rebuild', options, 0)

        if choice.get('key') != 'toggle_hub':
            return

        catalog_id = choice.get('catalog_id', choice.get('identifier'))
        section_key = getattr(self, '_managingHubsForSection', self.lastSection.key)
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
    THUMB_AR16X9_DIM = util.scaleResolution(352, 198)
    THUMB_SQUARE_DIM = util.scaleResolution(220, 220)

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

        mli = kodigui.ManagedListItem(
            obj.title or '',
            T(35055, '{0} items').format(obj.leafCount.asInt()),
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
    # _prepareHubSlideHero()/_setNoHeroArt()/_typeHasHeroArt()/updateHeroFrom() (hero-art
    # background sync - LibraryWindow has no hero-art concept yet at all). See this plan file's
    # "Next step: Recommended-tab sharing" section (Stage D2) for the full scoping rationale.
    # ------------------------------------------------------------------------------------------

    # Permanent geometric order of the 5 physical controls (see
    # docs/notes/home-hub-fixed-focus-position-status.md for the full history behind this design
    # - ported verbatim from HomeWindow.HUB_ROTATION_RING, home.py). Which ROLE (-2 two-above /
    # -1 peek-above / 0 anchor / +1 peek-below / +2 two-below) a given control id currently plays
    # rotates as focus moves - tracked by self._anchorRingPos (index into this tuple) - rather
    # than roles being permanently glued to one control id with content rebound to match every
    # move. A control that already has correct, already-rendered content for a hub keeps it and
    # just repositions; only the one control "wrapping around" per move (see _startHubSlide())
    # ever needs a fresh content bind, and since that control's role is always the extreme (±2),
    # which is never inside grouplist 50's own clip range regardless of which two controls
    # currently hold it, that rebind is always safely off-screen, never visible.
    HUB_ROTATION_RING = (403, 401, 400, 402, 404)
    # Each ring control's own wrapper control id (script-plex-recommended.xml.tpl groups
    # 500-504) - fixed, structural, so "moving" a control between roles means repositioning
    # *its* wrapper, not re-parenting the list control itself. Ported verbatim from
    # HomeWindow.HUB_WRAPPER_FOR_CONTROL.
    HUB_WRAPPER_FOR_CONTROL = {400: 500, 401: 501, 402: 502, 403: 503, 404: 504}

    # A row's own real rendered height (template-declared, pre-vscale units), keyed by the same
    # (display_type, text2lines) values getHubDisplayType()/getHubRenderFlags() already report.
    # Ported verbatim from HomeWindow.ROW_CONTENT_HEIGHT - see that constant's own comment
    # (home.py) for the underlying arithmetic.
    ROW_CONTENT_HEIGHT = {
        ('poster', False): 429, ('poster', True): 429,
        ('square', False): 371, ('square', True): 398,
        ('ar16x9', False): 349, ('ar16x9', True): 376,
    }
    # Fixed gap between any two adjacent rows, either direction - used by _roleLocalY()'s
    # stacking recurrence. Ported verbatim from HomeWindow.ROW_GAP.
    ROW_GAP = 25
    # The anchor's own absolute resting position (script-plex-recommended.xml.tpl's group 51,
    # local y-offset GROUP51_BASELINE_OFFSET below, sitting inside grouplist 50 at its base
    # posy=135 - 135 + 289 = 424). Ported verbatim from HomeWindow.ANCHOR_ABS_Y; used by
    # _setRoleGeometry() to size peek-below's clip height to reach exactly to the screen bottom.
    ANCHOR_ABS_Y = 424
    # The local y-offset group 51 must always be explicitly set to via setPosition() to sit at
    # its correct resting position - ported verbatim from HomeWindow.GROUP51_BASELINE_OFFSET.
    # Used as the "no hero art" case of _group51RestOffset() below (the other case, has-hero-art,
    # subtracts HUB_SLIDE_CLIP_SHIFT_HERO - real again as of the hero-art port, plan item 11; D2
    # itself never reached this case, always forcing no_hero_art=True). Set unconditionally, once
    # per fresh bind, in _recommendedHubsCallback() below - group 51 has no correct position at
    # all until Python explicitly sets it (see that control's own comment in the template for why
    # grouplist 50's auto-stacking can't be relied on for this).
    GROUP51_BASELINE_OFFSET = 289
    # Hub-switch slide animation step count/total time - ported verbatim from
    # HomeWindow.HUB_SLIDE_STEPS/HUB_SLIDE_TIME.
    HUB_SLIDE_STEPS = 24
    HUB_SLIDE_TIME = 0.15
    # Hero art/info overlay (plan item 11) - ported verbatim from HomeWindow's own constants
    # (home.py). HUB_SLIDE_CLIP_SHIFT_HERO: how far grouplist 50 shifts down (script-plex-
    # recommended.xml.tpl's own Conditional animation, keyed on no_hero_art) to make room for the
    # hero overlay when it's showing - _group51RestOffset() below counter-shifts group 51 by the
    # same amount so the anchor's own absolute position (ANCHOR_ABS_Y) never moves regardless of
    # hero-art state. HERO_ART_TYPES: which item types are eligible at all (see
    # _typeHasHeroArt()'s own docstring for why type-based, not art-field-presence-based).
    # CLEAR_LOGO_DIM: the clearlogo image's own render bounds.
    HUB_SLIDE_CLIP_SHIFT_HERO = 321
    HERO_ART_TYPES = {'movie', 'show', 'season', 'episode'}
    CLEAR_LOGO_DIM = util.scaleResolution(616, 109)

    def _hubRowHeight(self, hub):
        """A row's own real rendered height (pre-vscale template units) for whichever hub it's
        currently showing - used by _roleLocalY()'s stacking recurrence. hub=None (nothing bound
        at some intermediate offset, e.g. the empty-hubs case) falls back to the tallest real
        case (poster). Ported from HomeWindow._hubRowHeight() (home.py) - is_home adapted per
        this file's own convention (self.section.key is None; LibraryWindow has no
        self.lastSection concept, self.section already is "whatever's currently shown")."""
        if hub is None:
            return self.ROW_CONTENT_HEIGHT[('poster', False)]
        is_home = self.section.key is None
        identifier = hub.getCleanHubIdentifier(is_home=is_home)
        display_type = self.getHubDisplayType(hub, identifier)
        text2lines = self.getHubRenderFlags(hub, identifier)['text2lines']
        return self.ROW_CONTENT_HEIGHT.get(
            (display_type, text2lines), self.ROW_CONTENT_HEIGHT[('poster', False)]
        )

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
        bind (_recommendedHubsCallback()) and _startHubSlide(). Ported verbatim from
        HomeWindow._setRoleGeometry() (home.py)."""
        y = self._roleLocalY(role_offset, focused_index)
        wrapper.setPosition(0, util.vscale(y, r=0))
        if role_offset == 1:
            wrapper.setHeight(util.vscale(self.height - self.ANCHOR_ABS_Y - y, r=0))
        return y

    # ------------------------------------------------------------------------------------------
    # Plan item 11 (quiet-orbiting-heron.md): hero art/info overlay (title/clearlogo/meta-row/
    # summary for the focused hub item), ported from HomeWindow's own _typeHasHeroArt()/
    # updateHeroFrom()/setHeroInfo()/_group51RestOffset()/_setNoHeroArt() (home.py). Sequenced
    # after item 10 (hub interactivity) deliberately - hero art has to update as the focused
    # *item* changes, not just the focused hub, which needs item 10's horizontal-move handling to
    # exist first. The background art box itself (default_background.xml.tpl) is shared
    # infrastructure every window already includes via default.xml.tpl - only the text overlay
    # (title/logo/summary) needed porting into script-plex-recommended.xml.tpl; nothing here
    # needed template changes beyond that one block.
    # ------------------------------------------------------------------------------------------

    def _typeHasHeroArt(self, ds, hub=None):
        """Whether ds's item type is allowed to show the hero art/info treatment - movies/TV shows
        only (self.HERO_ART_TYPES). Type-based rather than art-field-presence-based - see
        HomeWindow._typeHasHeroArt()'s own docstring (home.py) for the full reasoning, ported
        verbatim including the hub-based exclusions (Other Videos library items report as
        type='movie', the same type real Movie libraries use).

        is_home adapted per this file's own convention throughout (self.section.key is None;
        LibraryWindow has no self.lastSection concept, self.section already is "whatever's
        currently shown") - same substitution _hubRowHeight()/_bindHubToControl() already use."""
        if not ds or getattr(ds, 'type', None) not in self.HERO_ART_TYPES:
            return False
        if hub is not None:
            is_home = self.section.key is None
            identifier = hub.getCleanHubIdentifier(is_home=is_home)
            if identifier and any(kw in identifier.lower() for kw in ('clip', 'video')):
                return False
            if getattr(hub, 'type', None) in ('clip', 'video'):
                return False
            if hub.items and getattr(hub.items[0], 'type', None) in ('clip', 'video'):
                return False
        return True

    def updateHeroFrom(self, ds, hub=None):
        """Like updateBackgroundFrom, but also drives the hero info overlay (clearlogo/title, meta
        row, summary) from the same item, and sets no_hero_art via _typeHasHeroArt(). Ported
        verbatim from HomeWindow.updateHeroFrom() (home.py) - see that method's own docstring for
        why this wraps updateBackgroundFrom rather than folding into it."""
        self._setNoHeroArt(not self._typeHasHeroArt(ds, hub=hub))
        result = self.updateBackgroundFrom(ds)
        self.setHeroInfo(ds)
        return result

    def setHeroInfo(self, ds):
        """Populates the Window properties script-plex-recommended.xml.tpl's own hero-overlay
        block reads. Ported verbatim from HomeWindow.setHeroInfo() (home.py) - see that method's
        own docstring for why every field is read defensively (hub items aren't always Video
        subclasses)."""
        if not ds:
            return

        self.setProperty('title', getattr(ds, 'title', '') or '')
        self.setProperty('clear.logo', util.clearLogoFrom(ds, *self.CLEAR_LOGO_DIM))

        duration = getattr(ds, 'duration', None)
        self.setProperty('duration', duration and util.durationToText(duration.asInt()) or '')

        summary = getattr(ds, 'summary', None)
        self.setProperty('summary', summary and str(summary).strip().replace('\t', ' ') or '')

        year = getattr(ds, 'year', None)
        self.setProperty('date', year and str(year) or '')

        content_rating = getattr(ds, 'contentRating', None)
        self.setProperty('content.rating', content_rating and str(content_rating).split('/', 1)[-1] or '')

        genres_attr = getattr(ds, 'genres', None)
        genres = ''
        try:
            if genres_attr is not None and not isinstance(genres_attr, plexobjects.PlexValue):
                genre_list = genres_attr()
                if genre_list:
                    genres = u' / '.join([g.tag for g in genre_list][:3])
        except Exception:
            util.DEBUG_LOG('setHeroInfo: genres failed for {}', ds)
        self.setProperty('info', genres)

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

    def _group51RestOffset(self, no_hero_art):
        """The local y-offset group 51 must be explicitly set to (via setPosition()) so the
        anchor's absolute position stays at ANCHOR_ABS_Y, given whether the currently/about-to-be-
        focused hub has hero art. Ported verbatim from HomeWindow._group51RestOffset() (home.py)."""
        if no_hero_art:
            return self.GROUP51_BASELINE_OFFSET
        return self.GROUP51_BASELINE_OFFSET - self.HUB_SLIDE_CLIP_SHIFT_HERO

    def _setNoHeroArt(self, no_hero_art):
        """Single choke point for every no_hero_art write - keeps group 51's own local y-offset
        (_group51RestOffset()) in sync with the property, snapped instantly (time="0", not eased -
        see HomeWindow._setNoHeroArt()'s own docstring, home.py, for the live-visible sync bug an
        earlier eased version caused: this Python setPosition() call and the native Conditional
        animation the property write triggers on grouplist 50 must land in the same rendered
        frame, or the whole row stack visibly swings through the full HUB_SLIDE_CLIP_SHIFT_HERO-px
        difference before settling). Ported verbatim, including the self._lastNoHeroArt no-op
        guard (not the window property itself, which reads empty/False before this has ever run -
        checking that would wrongly no-op, skipping group 51's position entirely, the very first
        time a hero-art-eligible hub loads)."""
        if no_hero_art == self._lastNoHeroArt:
            return
        self._lastNoHeroArt = no_hero_art
        self.setBoolProperty('no_hero_art', no_hero_art)
        g51 = self.getControl(51)
        g51.setPosition(g51.getPosition()[0], util.vscale(self._group51RestOffset(no_hero_art), r=0))

    def _prepareHubSlideHero(self):
        """Sync the hero art/info overlay to the hub about to become the anchor
        (self.visibleHubs[self.focusedHubIndex] - the caller already advanced focusedHubIndex to
        it), immediately, before the slide's own row movement starts - see
        HomeWindow._prepareHubSlideHero()'s own docstring (home.py) for why (both directions need
        to update at the same moment the scroll begins, not just the losing-hero-art one).

        Simplified from the original: uses new_hub.items[0] directly rather than
        _previewSelectedItem()/self._hubReselectPositions - D2 never ported reselect-position
        memory (_startHubSlide()'s own docstring), so every hub row always starts at item 0 here,
        there's no remembered scroll position to guess at."""
        new_hub = self.visibleHubs[self.focusedHubIndex]
        new_ds = new_hub.items[0] if new_hub.items else None
        self._setNoHeroArt(not self._typeHasHeroArt(new_ds, hub=new_hub))
        self.setHeroInfo(new_ds)
        self.updateBackgroundFrom(new_ds)

    def _updateHeroFromFocusedHubItem(self, control_id):
        """Sync the hero art/info overlay to whichever item is currently selected in hub-row
        control_id - called on horizontal (left/right) movement within a hub row. Minimal port of
        the hero-art-relevant slice of HomeWindow.checkHubItem() (home.py) - that method also
        handles pagination (ExtendHubTask), round-robin wraparound, and reselect-position memory,
        none of which are built here (see plan item 10's own scope notes) - just the hero-info
        replica update, mirroring updateHeroFrom() rather than calling it directly for the same
        reason checkHubItem() does (own docstring, home.py): updateHeroFrom() always calls
        updateBackgroundFrom() unconditionally, ignoring the dynamicBackgrounds setting - hero
        info (title/summary) should still update regardless of that setting, only the background
        art panel itself is gated on it."""
        control = self.hubControls[control_id - self.HUB_CONTROL_ID]
        mli = control.getSelectedItem()
        if not mli or not mli.dataSource:
            return
        ds = mli.dataSource
        self._setNoHeroArt(not self._typeHasHeroArt(ds, hub=control.dataSource))
        self.setHeroInfo(ds)
        self.updateBackgroundFrom(ds)

    def _anchorControlId(self):
        """Whichever physical control (400-404) is currently serving the anchor role. Ported
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

    def _ringRoleOffset(self, control_id, ring_pos=None):
        """control_id's current role-offset (-2 two-above / -1 peek-above / 0 anchor / +1
        peek-below / +2 two-below) relative to ring_pos (an index into HUB_ROTATION_RING -
        defaults to the current anchor's own position, self._anchorRingPos, when not given).
        Ported verbatim from HomeWindow._ringRoleOffset() (home.py)."""
        if ring_pos is None:
            ring_pos = self._anchorRingPos
        ring = self.HUB_ROTATION_RING
        half = len(ring) // 2
        return ((ring.index(control_id) - ring_pos + half) % len(ring)) - half

    def hubItemClicked(self, hub_control_id):
        """Open whatever's focused in a hub row (controls 400-404). Minimal port of
        HomeWindow.hubItemClicked() (home.py): generic opener.open() dispatch, since hub items
        span many different types across different hubs, unlike the grid's own section-TYPE-
        scoped showPanelClicked(). Deliberately narrower than the original for now - no
        in-progress auto-resume, no season/episode-to-show redirection for discover hubs, no
        hub-becomes-empty cleanup after the click (an item removed/deleted, a watchlist item
        dropped on open, etc. leaving this row with fewer items than before) - real gaps, not yet
        decided whether/when to close, see quiet-orbiting-heron.md.

        watchlist-specific extra_kwargs (live-confirmed gap, fixed here): this window's own
        contentMode can be 'recommended' for a section whose TYPE is 'movies_shows' (Watchlist,
        e.g. if that's the last tab persisted for it - see reset()'s own contentMode comment), in
        which case clicks land here, not showPanelClicked() - which never gets a chance to set
        from_watchlist/directly_from_watchlist at all. Without it, the opened window's own
        getLibrarySectionId() legitimately finds nothing real to match (discover items report the
        literal string "watchlist"), so its sidebar has nothing to highlight. Same detection
        showPanelClicked() uses (self.section.TYPE, not per-hub cross-section sourcing -
        hubMenu()'s own _crossSectionSource - which would be a separate, currently unhandled case
        even there).
        """
        control = self.hubControls[hub_control_id - self.HUB_CONTROL_ID]
        mli = control.getSelectedItem()
        if not mli or not mli.dataSource:
            return

        extra_kwargs = {
            'entry_section_id': self.entrySectionId,
            'entry_from_watchlist': self.entryFromWatchlist,
        }
        if self.section.TYPE == 'movies_shows':
            extra_kwargs['from_watchlist'] = True
            extra_kwargs['directly_from_watchlist'] = True
            extra_kwargs['external_item'] = True

        # context=self (hashed-orbiting-pizza.md Phase 4 item 1): hub items span many object
        # types (unlike the grid's own type-scoped showPanelClicked()), so this keeps using
        # opener.open()'s shared dispatch rather than duplicating it locally - context=self lets
        # whichever branch has been made chain-aware so far (currently just movies) call
        # self.openWindow(...) instead of unconditionally opening a real nested window. Inert for
        # every other object type until its own Phase 4 item wires that branch too.
        self.processCommand(opener.open(mli.dataSource, context=self, **extra_kwargs))

    def hubMenu(self, hubControlID):
        """Context menu (ACTION_CONTEXT_MENU) for whichever item is focused in a hub row - ported
        from HomeWindow.hubMenu() (home.py), adapted to this window's own state. Triggered from
        onAction()'s hub-row branch (399 < controlID < 500), which owns the return-value ->
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

        # Determine the hub's source section and catalog_id. (The original also computed a
        # `self.lastSection`-is-home flag here for the 'add_to_home' option's own visibility check
        # - not ported, see this method's own docstring, so only hub_is_home below is needed.)
        cross_source = hub.__dict__.get('_crossSectionSource')
        hub_source_key = cross_source if cross_source is not None else self.lastSection.key
        hub_is_home = hub_source_key is None
        clean_identifier = hub.getCleanHubIdentifier(is_home=hub_is_home)

        # Build catalog_id for Manage Hubs integration
        if hub_is_home:
            catalog_id = clean_identifier
        else:
            catalog_id = '{}:{}'.format(hub_source_key, clean_identifier)

        hub_title = hub.__dict__.get('_displayTitle') or hub.title or clean_identifier

        select_base = 0

        options = []
        has_prev = False
        is_watchlist = self.lastSection == home.watchlist_section
        # Don't allow disabling hubs for watchlist or main CW/On Deck hubs
        if not is_watchlist and hub.hubIdentifier not in ("continueWatching", "home.continue", "home.ondeck"):
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
                if (hub.hubIdentifier in ("continueWatching", "home.continue", "home.ondeck") or
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
                if ds.TYPE == 'episode':
                    options.append({'key': 'to_season', 'display': T(32400, "Go To Season")})

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
            # self.lastSection hands off to onAction()'s serverRefresh() call, same pattern
            # sectionMenu()'s own 'manage_hubs'/'refresh_hubs' choices use - forces the section
            # to reopen, which re-triggers hub fetching/isHubHidden() filtering and so drops the
            # now-disabled hub from view.
            section_key = self.lastSection.key
            self._ensureCustomConfigExists(section_key)
            self._disableHub(catalog_id, section_key)
            return self.lastSection

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
            return self.lastSection

        elif choice["key"] in ("to_season", "to_show"):
            target = ds.show() if choice["key"] == "to_show" else ds.season()
            try:
                command = opener.open(target, dialog_props=getattr(self, 'carriedProps', None))
                if command == "NODATA":
                    raise util.NoDataException
            except util.NoDataException:
                util.ERROR("No data - deleted or server disconnected?", notify=True, time_ms=5000)
                return

        elif choice["key"] == "to_item":
            try:
                command = opener.open(ds, dialog_props=getattr(self, 'carriedProps', None))
                if command == "NODATA":
                    raise util.NoDataException
            except util.NoDataException:
                util.ERROR("No data - deleted or server disconnected?", notify=True, time_ms=5000)
                return

        elif choice["key"] == "start_over":
            try:
                command = opener.open(ds, auto_play=True, start_over=True, dialog_props=getattr(self, 'carriedProps', None))
                if command == "NODATA":
                    raise util.NoDataException
            except util.NoDataException:
                util.ERROR("No data - deleted or server disconnected?", notify=True, time_ms=5000)
                return
            return

        elif choice["key"] == "resume":
            try:
                command = opener.open(ds, auto_play=True, dialog_props=getattr(self, 'carriedProps', None))
                if command == "NODATA":
                    raise util.NoDataException
            except util.NoDataException:
                util.ERROR("No data - deleted or server disconnected?", notify=True, time_ms=5000)
                return
            return

        elif choice["key"] == "cache_reset":
            try:
                util.DEBUG_LOG('Clearing requests cache for {}...', ds)
                ds.clearCache()
            except Exception as e:
                util.DEBUG_LOG("Couldn't clear cache: {}", e)

    def _bindHubToControl(self, hub, control_index):
        """Populate physical hub-row control HUB_CONTROL_ID + control_index with hub's content -
        the properties/dataSource/items population D1's flat _recommendedHubsCallback() did
        inline for every control unconditionally, factored out here since both the initial full
        bind and _startHubSlide()'s wrap-control rebind need to do exactly this for one control
        at a time. Deliberately NOT HomeWindow.showHub()/_showHub() - those also handle
        reselect-position restoration and hero-art/spoiler/cache-clearing, all out of scope for
        D2 (see this block's own header comment)."""
        is_home = self.section.key is None
        identifier = hub.getCleanHubIdentifier(is_home=is_home)
        display_type = self.getHubDisplayType(hub, identifier)
        flags = self.getHubRenderFlags(hub, identifier)
        title = hub.__dict__.get('_displayTitle') or hub.title or ''

        # Row title label reads $INFO[Window.Property(hub.{{ id - 100 }})] (id 500-504, so
        # property name is hub.400 .. hub.404) - same property name/format
        # HomeWindow._showHub() sets (home.py). hub.display.4NN drives which of
        # hub_itemlayout_{poster,square,ar16x9}.xml.tpl actually renders each item - without it
        # every itemlayout's <itemlayout condition="..."> is false and the list shows no visible
        # content even with items bound.
        self.setProperty('hub.display.4{0:02d}'.format(control_index), display_type)
        self.setProperty('hub.4{0:02d}'.format(control_index), title)
        self.setProperty('hub.text2lines.4{0:02d}'.format(control_index), flags['text2lines'] and '1' or '')

        control = self.hubControls[control_index]
        control.dataSource = hub
        items = [mli for mli in
                (self.createListItem(obj, wide=flags['with_art']) for obj in hub.items) if mli]

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

        control.replaceItems(items)

    def _recommendedHubsCallbackFor(self, generation):
        """Wraps _recommendedHubsCallback() with the _listGeneration snapshot taken when the
        hub fetch was scheduled (onFirstInit(), 'recommended' branch), so a fetch that finishes
        after a swap away (switchTab()/openSection() bump _listGeneration immediately, but
        self.tasks.kill() can't preempt a fetch already past its own isCanceled() check) gets
        recognized as stale and discarded instead of writing into a window that's moved on -
        same idiom as _chunkCallbackFor() above.
        """
        def callback(section, hubs, reselect_pos_dict=None):
            self._recommendedHubsCallback(section, hubs, generation)
        return callback

    def _recommendedHubsCallback(self, section, hubs, generation):
        """SectionHubsTask's callback. Called synchronously, inline, on the main thread -
        onFirstInit()'s 'recommended' branch calls hubsTask.run() directly rather than dispatching
        it to BGThreader. This was tried as a fix for a native crash entering/leaving
        'recommended' (heap/vtable corruption, not a simple bad read), on the theory that the
        Control geometry mutation below (getControl(), _setRoleGeometry()'s setPosition()/
        setHeight() calls) running off the main thread was the cause - live-tested and ruled out
        (the crash persisted, at the exact same faulting address, even with all of this loop's
        geometry mutation skipped entirely in a separate diagnostic pass). The real cause turned
        out to be upstream: xbmc/xbmc#27552/#27239, a confirmed Kodi core bug where
        CGUIWindow::OnAction() crashes if a skin/window reload happens nested underneath the same
        OnAction() call that triggered it - see windowutils.SKIN_RELOAD_DEFER_SECONDS for the full
        diagnosis and the actual fix (deferring switchTab()/openSection() itself, not anything in
        here). Left running inline on the main thread anyway now that it's already this shape -
        no reason to revert a harmless simplification just because it wasn't the fix, and it still
        avoids background-thread Control mutation as a matter of general caution.

        Historical note: this used to run on a genuine background thread (BGThreader), same shape
        HomeWindow's own SectionHubsTask callback (_bindAllHubSlots(), home.py) still uses safely -
        that always was fine, since it was never the actual bug. The self.lock/double-stale-check
        shape below predates this change and is no longer strictly load-bearing (nothing else can
        run between scheduling and this call any more, since it's synchronous) but is kept as
        cheap, harmless defensiveness rather than removed.

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
            self.focusedHubIndex = 0
            self._anchorRingPos = self.HUB_ROTATION_RING.index(self.HUB_CONTROL_ID)

            # Group 51 has no correct position at all until this is set explicitly - see
            # GROUP51_BASELINE_OFFSET's own comment above. _setNoHeroArt() below now handles this
            # (it's the single choke point for group 51's position, keyed on hero-art state) -
            # previously done unconditionally here, forcing no_hero_art=True, back when D2 had no
            # hero-art concept at all (see that block's own former comment, still relevant
            # context: a property that's never been written at all reads as empty in Kodi, same
            # as explicitly set to '' - which matches has-hero-art's *empty* state, not no-hero-
            # art's '1' - so no_hero_art must always be written explicitly, never left implicit,
            # in every branch below, not just this one).

            if not sorted_hubs:
                for index in range(len(self.hubControls)):
                    self.hubControls[index].reset()
                    self.setProperty('hub.display.4{0:02d}'.format(index), '')
                self.setBoolProperty('hub.has_prev', False)
                self.setBoolProperty('hub.has_next', False)
                self._setNoHeroArt(True)
                self.setProperty('hub.anchor_id', str(self._anchorControlId()))
                for control_id in self.HUB_ROTATION_RING:
                    role = self._ringRoleOffset(control_id)
                    wrapper = self.getControl(self.HUB_WRAPPER_FOR_CONTROL[control_id])
                    self._setRoleGeometry(wrapper, role, self.focusedHubIndex)
                util.DEBUG_LOG("Library: _recommendedHubsCallback() bound 0 hubs for {0}", section.key)
                return

            self.setProperty('hub.anchor_id', str(self._anchorControlId()))

            # Seed hero art/info from the anchor hub's first item before binding any controls -
            # same ordering HomeWindow._bindAllHubSlots() uses and for the same reason (own
            # comment there): binding the anchor first means the hero state is already settled by
            # the time the other slots populate, so nothing else can race it. Real now (plan item
            # 11) - previously this comment said "no hero-art background to seed here", back when
            # D2 forced no_hero_art=True unconditionally instead.
            anchor_hub = sorted_hubs[self.focusedHubIndex]
            anchor_ds = anchor_hub.items[0] if anchor_hub.items else None
            self.updateHeroFrom(anchor_ds, hub=anchor_hub)

            for control_id in sorted(self.HUB_ROTATION_RING, key=lambda cid: abs(self._ringRoleOffset(cid))):
                role = self._ringRoleOffset(control_id)
                index = control_id - self.HUB_CONTROL_ID
                wrapper = self.getControl(self.HUB_WRAPPER_FOR_CONTROL[control_id])
                self._setRoleGeometry(wrapper, role, self.focusedHubIndex)

                hub_index = self.focusedHubIndex + role
                if not (0 <= hub_index < len(sorted_hubs)):
                    self.hubControls[index].reset()
                    self.setProperty('hub.display.4{0:02d}'.format(index), '')
                    if role == -1:
                        self.setBoolProperty('hub.has_prev', False)
                    elif role == 1:
                        self.setBoolProperty('hub.has_next', False)
                    continue

                self._bindHubToControl(sorted_hubs[hub_index], index)
                if role == -1:
                    self.setBoolProperty('hub.has_prev', True)
                elif role == 1:
                    self.setBoolProperty('hub.has_next', True)

            util.DEBUG_LOG("Library: _recommendedHubsCallback() bound {0} hub(s) for {1}, anchor={2}",
                           min(len(sorted_hubs), len(self.hubControls)), section.key,
                           self._anchorControlId())

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

        Staleness guard (Stage D2 addition, no HomeWindow equivalent needed - HomeWindow is a
        single persistent window, never swapped out from under its own background thread): snap-
        shots self._listGeneration (list_gen) here, at the moment this move is still definitely
        valid, alongside the usual self._hubSlideGen repeat-press-cancellation snapshot. The
        background animation loop below checks both, plus self.closing (the whole session
        ending), before every setPosition() call - NOT self._closing (no leading underscore vs.
        with - self.closing is LibraryWindow's own instance attribute for "session ending";
        self._closing doesn't exist on LibraryWindow itself and resolves, via
        MultiWindow.__getattr__, to whichever concrete window self._current currently *is* at
        the moment it's read - after a mid-slide swap away from 'recommended', that's a fresh,
        just-opened window with _closing=False, not the 'recommended' window this slide actually
        belongs to. This is exactly the same delegation trap the plan's "Known interim gaps" bug
        (3) already found and fixed for _scheduleBackgroundStaticSync() (kodigui.py - that method
        and the self._bgSyncGen counter it needed are since removed entirely, no longer relevant
        beyond this lesson - see windowSetBackground()'s own current comment for why) -
        self._listGeneration
        (bumped synchronously by switchTab()/openSection() before they close anything) is the
        correct, non-delegated signal for "a swap happened out from under this", same idiom
        _chunkCallbackFor()/_recommendedHubsCallbackFor() already use.
        """
        if not self.visibleHubs:
            return
        new_index = self.focusedHubIndex + delta
        if not (0 <= new_index < len(self.visibleHubs)):
            return

        list_gen = self._listGeneration

        # Finish any still-running slide from a fast preceding press first, so this transition
        # always starts from a settled, consistent state instead of fighting or compounding with
        # one already in flight.
        self._settleHubSlide()

        old_focused_index = self.focusedHubIndex
        self.focusedHubIndex = new_index

        old_ring_pos = self._anchorRingPos
        new_ring_pos = (old_ring_pos + delta) % len(self.HUB_ROTATION_RING)
        self._anchorRingPos = new_ring_pos
        self.setProperty('hub.anchor_id', str(self._anchorControlId()))

        self._prepareHubSlideHero()

        # The one control wrapping around: currently at the extreme role opposite the direction
        # of travel - its data isn't valid for any role in the new arrangement, so it needs a
        # fresh content bind and a position snap to its new role. Done synchronously,
        # immediately - see this method's own docstring for why its old and new roles (both
        # ±half, the ring's own extremes) are never inside grouplist 50's clip regardless of
        # which controls currently hold them, so there's nothing to collide with.
        half = len(self.HUB_ROTATION_RING) // 2
        wrap_role = -half if delta > 0 else half
        wrap_control_id = next(cid for cid in self.HUB_ROTATION_RING
                                if self._ringRoleOffset(cid, ring_pos=old_ring_pos) == wrap_role)
        wrap_new_role = -wrap_role
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
        # No hub.has_prev/has_next update here - the wrap control's new role is always ±half (±2
        # for this 5-ring), never ±1, so it never owns that state; whichever mover below lands on
        # ±1 does.

        # The other 4 controls: reposition smoothly over the animation loop below, content
        # untouched (already correct for their new role - see this method's own docstring).
        movers = []
        for cid in self.HUB_ROTATION_RING:
            if cid == wrap_control_id:
                continue
            old_role = self._ringRoleOffset(cid, ring_pos=old_ring_pos)
            new_role = self._ringRoleOffset(cid, ring_pos=new_ring_pos)
            start_y = self._roleLocalY(old_role, old_focused_index)
            end_y = self._roleLocalY(new_role, new_index)
            wrapper = self.getControl(self.HUB_WRAPPER_FOR_CONTROL[cid])
            if new_role == 1:
                wrapper.setHeight(util.vscale(self.height - self.ANCHOR_ABS_Y - end_y, r=0))
                self.setBoolProperty('hub.has_next', True)
            elif new_role == -1:
                self.setBoolProperty('hub.has_prev', True)
            movers.append((wrapper, start_y, end_y))

        self._hubSlideMovers = movers

        if self.closing or self._listGeneration != list_gen:
            # No animation thread will run to land these at end_y - snap directly, matching what
            # the loop's own tail does, so nothing is left mid-transition. self.closing (not
            # self._closing - see this method's own docstring) is the real "tearing down for
            # real" signal here; self._listGeneration != list_gen would mean a swap already
            # landed between the checks above and here, on the same synchronous call - not
            # expected (nothing yields control in between), but cheap to also cover.
            for wrapper, start_y, end_y in movers:
                wrapper.setPosition(0, util.vscale(end_y, r=0))
            self._hubSlideMovers = []
            self._finishHubSlide()
            return

        self.setBoolProperty('hub.sliding', True)
        self._hubSliding = True
        self._hubSlideGen += 1
        gen = self._hubSlideGen
        steps = self.HUB_SLIDE_STEPS
        step_time = self.HUB_SLIDE_TIME / float(steps)

        def run():
            for i in range(1, steps + 1):
                if self.closing or self._hubSlideGen != gen or self._listGeneration != list_gen:
                    return
                t = i / float(steps)
                eased = t * t * (3 - 2 * t)  # smoothstep - approximates the old sine inout tween
                for wrapper, start_y, end_y in movers:
                    raw = int(round(start_y + (end_y - start_y) * eased))
                    wrapper.setPosition(0, util.vscale(raw, r=0))
                if util.MONITOR.waitFor(step_time):
                    return
            if self.closing or self._hubSlideGen != gen or self._listGeneration != list_gen:
                return
            for wrapper, start_y, end_y in movers:
                wrapper.setPosition(0, util.vscale(end_y, r=0))
            self._hubSlideMovers = []
            self._finishHubSlide()

        t = threading.Thread(target=run, name='hubslide')
        self._hubSlideThread = t
        t.start()

    def _finishHubSlide(self):
        """Slide-completion - deliberately NOT a full _recommendedHubsCallback() rebuild (that
        would rebind all 5 controls' content unconditionally, defeating the ring design's whole
        point). Both the wrap control and the movers' content/position are already fully
        handled, synchronously, by _startHubSlide() itself - this just clears hub.sliding
        (re-showing the anchor's own title label) and moves native Kodi focus to whichever
        control the ring now says is the anchor. Ported from HomeWindow._finishHubSlide()
        (home.py), minus its checkHubItem(anchor_id) call - horizontal in-hub navigation/
        reselect-preview is out of scope for D2."""
        self.setBoolProperty('hub.sliding', False)
        self._hubSliding = False
        anchor_id = self._anchorControlId()
        if self.getFocusId() != anchor_id:
            self.setFocusId(anchor_id)

    def _settleHubSlide(self):
        """If a hub-slide animation is currently in flight, snap it straight to completion
        instead of leaving it to finish on its own background thread. Bumps _hubSlideGen first
        so that thread's own next gen-check (whether mid-sleep or mid-loop) sees the mismatch and
        exits without touching state itself - not ported verbatim from HomeWindow._settleHubSlide()
        (home.py) any more, though: HomeWindow is a single persistent window that's never
        destroyed out from under this thread (see _startHubSlide()'s own docstring), but
        LibraryWindow's is - switchTab()/openSection() call this right before doClose() tears the
        native window down for real. Bumping the gen alone only stops the thread from touching
        controls on its *next* loop check; a call already past that check (mid-setPosition(), or
        about to make one for the current step) can still land after the native window is gone -
        a real, theoretically-possible race, tried as a fix for a native crash switching back out
        of Recommended (this was in place before that crash's actual cause - xbmc/xbmc#27552/
        #27239, see windowutils.SKIN_RELOAD_DEFER_SECONDS - was diagnosed; the crash persisted
        after this fix alone, at the same faulting address, so this specific race was likely never
        what was actually firing). join()ing it here, before this method's own final setPosition()
        snap, still closes a real (if apparently unobserved) window: once join() returns, no other
        thread can still be calling into these controls, so the snap below is provably the last
        write. HUB_SLIDE_TIME is 0.15s total, so a bounded wait is cheap insurance either way, not
        a real stall - left in place as legitimate defensiveness, not reverted just because it
        wasn't the actual fix.
        """
        if not self._hubSliding:
            return
        self._hubSlideGen += 1
        thread = self._hubSlideThread
        if thread and thread.is_alive():
            thread.join(1.0)
        self._hubSlideThread = None
        for wrapper, start_y, end_y in self._hubSlideMovers:
            wrapper.setPosition(0, util.vscale(end_y, r=0))
        self._hubSlideMovers = []
        self._finishHubSlide()


class PostersWindow(kodigui.ControlledWindow, windowutils.UtilMixin):
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


class PostersCompactWindow(PostersWindow):
    xmlFile = 'script-plex-posters-compact.xml'
    VIEWTYPE = 'panel3'
    MULTI_WINDOW_ID = 3
    ROW_SIZE = 10
    CHUNK_OVERCOMMIT = 30


class PostersSmallWindow(PostersWindow):
    xmlFile = 'script-plex-posters-small.xml'
    VIEWTYPE = 'panel2'
    MULTI_WINDOW_ID = 1
    ROW_SIZE = 10
    CHUNK_OVERCOMMIT = 30


class PostersSmallCompactWindow(PostersWindow):
    xmlFile = 'script-plex-posters-small-compact.xml'
    VIEWTYPE = 'panel4'
    MULTI_WINDOW_ID = 4
    ROW_SIZE = 10
    CHUNK_OVERCOMMIT = 30


class ListView16x9Window(PostersWindow):
    xmlFile = 'script-plex-listview-16x9.xml'
    VIEWTYPE = 'list'
    MULTI_WINDOW_ID = 2
    ROW_SIZE = 0
    CHUNK_OVERCOMMIT = 12


class SquaresWindow(PostersWindow):
    xmlFile = 'script-plex-squares.xml'
    VIEWTYPE = 'panel'
    MULTI_WINDOW_ID = 0


class ListViewSquareWindow(PostersWindow):
    xmlFile = 'script-plex-listview-square.xml'
    VIEWTYPE = 'list'
    ROW_SIZE = 0
    MULTI_WINDOW_ID = 1


VIEWS_POSTER = {
    'panel': PostersWindow,
    'panel2': PostersSmallWindow,
    'panel3': PostersCompactWindow,
    'panel4': PostersSmallCompactWindow,
    'list': ListView16x9Window,
    'all': (PostersWindow, PostersCompactWindow, PostersSmallWindow, PostersSmallCompactWindow, ListView16x9Window)
}

VIEWS_SQUARE = {
    'panel': SquaresWindow,
    'list': ListViewSquareWindow,
    'all': (SquaresWindow, ListViewSquareWindow)
}


class RecommendedWindow(kodigui.ControlledWindow, windowutils.UtilMixin):
    # Stage B (quiet-orbiting-heron.md, Recommended-tab sharing) - real template (near-verbatim
    # copy of script-plex-home.xml.tpl's hub row stack + hero-info overlay), no Python-side
    # hub-fetch/rendering logic wired to it yet (Stage C/D). Renders as an empty hub area until
    # then - every Container(...)/Window.Property(...) reference in the template evaluates
    # empty/false with nothing populating them.
    xmlFile = 'script-plex-recommended.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    # Matches script-plex-home.xml.tpl's own control ids - not yet read by any Python logic
    # here (Stage C/D's job), declared now so Stage C/D wiring has them ready.
    PLAYER_STATUS_BUTTON_ID = 204
    HUB_CONTROL_ID = 400

    MULTI_WINDOW_ID = 0


VIEWS_RECOMMENDED = {
    'panel': RecommendedWindow,
    'all': (RecommendedWindow,)
}
