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
from lib.util import T
from . import background
from . import busy
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


def realSection(section):
    """The library a section belongs to. Pinned top bar item-type views proxy one."""
    return section.__dict__.get('librarySection') or section


class LibrarySettings(object):
    def __init__(self, section_or_server_id, ignoreLibrarySettings=False):
        self.ignoreLibrarySettings = ignoreLibrarySettings
        self.forcedItemType = None
        if isinstance(section_or_server_id, six.string_types):
            self.serverID = section_or_server_id
            self.sectionID = None
        else:
            self.serverID = section_or_server_id.getServer().uuid
            self.sectionID = section_or_server_id.key
            # a pinned item-type view always opens in its own type, no matter which type was
            # last selected while inside it
            self.forcedItemType = section_or_server_id.__dict__.get('itemType')

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

        setItemType(self.forcedItemType or self.getItemType() or ITEM_TYPE)

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
        self.section = kwargs.get('section')
        self.filter = kwargs.get('filter_')
        self.subDir = kwargs.get('subDir')
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
        elif self.section.TYPE in ('artist', 'photo', 'photodirectory'):
            self.setWindows(VIEWS_SQUARE.get('all'))
            self.setDefault(VIEWS_SQUARE.get(viewtype))
        else:
            self.setWindows(VIEWS_POSTER.get('all'))
            self.setDefault(VIEWS_POSTER.get(viewtype))

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

    def openSection(self, section, filter_=None):
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
        sidebar-driven section switch is the generalized dispatch/bubble mechanism goHome()
        already does for itself (closeWithCommand()'s exitCommand propagating through each
        ancestor's processCommand() as their own .modal() calls return) - not yet generalized to
        ordinary section switches, so this just declines rather than corrupting state in the
        meantime.
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

        if section == self.section:
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

        util.DEBUG_LOG("Library: openSection() swapping in place to {0}", section)
        self._current.doClose()
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
        plan. HomeWindow's own version also resets its serverList control and calls storeLastBG()
        (persists the focused hub's background art for next cold start) here - both depend on
        sidebar/hub-rendering state that doesn't exist on LibraryWindow yet (the user-options-menu/
        server-popup UI, Stage 3, and a LibraryWindow-shaped equivalent of Home's visibleHubs-based
        background persistence). Deliberately not ported until that state exists to port it onto.
        """
        util.DEBUG_LOG("Library: shutdown called")
        self._shuttingDown = True
        self.stopRetryingRequests()

    def processCommand(self, command):
        """UtilMixin.processCommand() (windowutils.py) - live-confirmed regression, fixed here.
        Every real descendant a 'HOME'/'HOME:<section>' command bubbles through (ShowWindow,
        EpisodesWindow, PrePlayWindow, ... via openItem()/openWindow()) is meant to close itself
        on the way back - that's the base class's own, still-correct behavior, unchanged below.
        But once the bubble reaches back up to whichever ancestor opened the chain, and that
        ancestor is US (the cold-start root, windowutils.HOME), the command has arrived, not "left
        home too" - goHome()/goHomeRoot() (windowutils.py's GoHomeMixin/SidebarMixin) already reset
        us via go_root/show() before the bubble even started. Falling into the base class's
        self.doClose() here would tear down the whole session, since nothing sits underneath this
        window anymore the way HomeWindow used to. Live-confirmed: pressing the Home button from a
        descendant briefly flashed this window back up, then closed the whole addon, before this.
        """
        if command and command.startswith('HOME') and self is windowutils.HOME:
            return
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
            self.sectionList = kodigui.ManagedControlList(self, self.SECTION_LIST_ID, 15)
            self.buildSectionList()
            self.displayServerAndUser()
        else:
            self.sectionList.newControl(self)

        if self.tabList is None:
            self.tabList = kodigui.ManagedControlList(self, self.TAB_LIST_ID, 5)
            self.buildTabList()
        else:
            self.tabList.newControl(self)
            self.updateActiveTabMarker()

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
                for hc in self.hubControls:
                    hc.newControl(self)

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
            # Playlists/pinned-type entries also in this list.
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

        hideFilterOptions = self.section.TYPE == 'photodirectory' or self.section.TYPE == 'collection'

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

        self.setTitle()
        self.setBoolProperty("initialized", True)
        self.fill()
        self.refill = False
        if self.getProperty('no.content') or self.getProperty('no.content.filtered'):
            self.setFocusId(self.SECTION_LIST_ID)
        else:
            self.setFocusId(self.POSTERS_PANEL_ID)

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
                threading.Timer(windowutils.SKIN_RELOAD_DEFER_SECONDS, self.openSection, args=(section,)).start()
            if with_root:
                self.go_root = True
                self.show()
            return
        windowutils.GoHomeMixin.goHome(self, section=section, with_root=with_root)

    def goHomeRoot(self, *args, **kwargs):
        if self is windowutils.HOME:
            self.go_root = True
            self.show()
            return
        windowutils.GoHomeMixin.goHomeRoot(self, *args, **kwargs)

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

        try:
            if self.getFocusId() == self.SECTION_LIST_ID:
                self.checkSectionItem(action=action)

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
                    if mli and mli.dataSource:
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
            self.sectionClicked()
            return

        if controlID == self.TAB_LIST_ID:
            # Plan item 0 (quiet-orbiting-heron.md): TAB_LIST_ID exists identically in every
            # content-mode's template, so this is checked before the contentMode=='recommended'
            # bypass below, same as SECTION_LIST_ID above.
            mli = self.tabList.getSelectedItem()
            if mli:
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

        searchmli = kodigui.ManagedListItem(T(32431, 'Search'), iconImage='script.plex/buttons/search.png')
        searchmli.setProperty('is.search', '1')
        searchmli.setProperty('item', '1')
        items.append(searchmli)

        homemli = kodigui.ManagedListItem(T(32332, 'Home'), iconImage='script.plex/home/type/home.png',
                                          data_source=home.home_section)
        homemli.setProperty('is.home', '1')
        homemli.setProperty('item', '1')
        items.append(homemli)

        setting_key = 'home.settings.{}.{}'.format(plexapp.SERVERMANAGER.selectedServer.uuid[-8:], plexapp.ACCOUNT.ID)
        try:
            navSettings = json.loads(util.getSetting(setting_key, '')) or {}
        except ValueError:
            navSettings = {}

        sections = []

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
            if navSettings:
                pinnable = home.PINNABLE_TYPES.get(str(getattr(section, 'TYPE', None)), ())
                stored = navSettings.get(section.key, {}).get('pinned_types') or []
                for item_type in stored:
                    if item_type in pinnable:
                        sections.append(home.PinnedTypeSection(section, item_type))

        if "order" in navSettings:
            order = navSettings["order"]

            def orderPos(s):
                if s.key in order:
                    return order.index(s.key), 0
                if isinstance(s, home.PinnedTypeSection) and s.librarySection.key in order:
                    return order.index(s.librarySection.key), 1
                return -1, 0

            sections = sorted(sections, key=orderPos)

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
            elif isinstance(section, home.PinnedTypeSection):
                mli.setProperty('is.pinned.type', section.itemType)
            if section.key == self.section.key:
                mli.setProperty('is.active', '1')
            items.append(mli)

        self.sectionList.reset()
        self.sectionList.addItems(items)

    def buildTabList(self):
        """Populate the section-tabs row (Recommended/Library) - plan item 0
        (quiet-orbiting-heron.md). Built once per LibraryWindow lifetime (see onFirstInit()),
        not rebuilt on every content-mode swap - only which item is marked 'current' changes
        (updateActiveTabMarker()), same relationship buildSectionList()/is.active has to the
        sidebar. Plain hardcoded English labels for now, not T()-translated - no existing
        translation string to reuse, and adding new ones is a separate concern from this pass.
        """
        items = []
        for mode, label in (('recommended', 'Recommended'), ('library', 'Library')):
            mli = kodigui.ManagedListItem(label)
            mli.setProperty('item', '1')
            mli.setProperty('content.mode', mode)
            items.append(mli)

        self.tabList.reset()
        self.tabList.addItems(items)
        self.updateActiveTabMarker()

    def updateActiveTabMarker(self):
        """Update 'current' on the tab list items to highlight self.contentMode's active tab -
        same key-matched-property pattern updateActiveSectionMarker() uses for the sidebar,
        called both right after buildTabList() and whenever switchTab() changes contentMode.
        """
        if not self.tabList:
            return

        for i in range(self.tabList.size()):
            mli = self.tabList[i]
            if not mli:
                continue
            if mli.getProperty('content.mode') == self.contentMode:
                mli.setProperty('current', '1')
            elif mli.getProperty('current'):
                mli.setProperty('current', '')

    # sectionClicked() now provided by SidebarMixin - its default _dispatchSectionOpen() covers
    # this window's needs exactly: home_section is just another section value here (LibraryWindow
    # has openSection(), so is.home no longer gets any special treatment - see that method's own
    # is.home-equivalent TYPE == 'mixed' check for how it lands on the right tab), skip re-opening
    # the already-shown section via lastSection tracking, playlists -> PlaylistsWindow, else ->
    # opener.sectionClicked().

    def displayServerAndUser(self):
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

        if controlID == self.SECTION_LIST_ID:
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
        # a pinned item-type view searches the library it belongs to
        self.processCommand(search.dialog(self, section_id=realSection(self.section).key))

    def browseGenres(self):
        from . import genres as genres_window
        self.processCommand(opener.handleOpen(genres_window.GenreBrowserWindow,
                                              section=realSection(self.section)))

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
            self.showPanelControl = None  # TODO: Need to do some check here I think

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
        if not mli or not mli.dataSource:
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

        if mli.dataSource.TYPE == 'collection':
            prevItemType = self.librarySettings.getItemType() or ITEM_TYPE
            self.processCommand(opener.open(mli.dataSource))
            self.librarySettings.setItemType(prevItemType)
        elif self.section.TYPE == 'show' or mli.dataSource.TYPE == 'show' or mli.dataSource.TYPE == 'season' or mli.dataSource.TYPE == 'episode':
            if ITEM_TYPE == 'episode' or mli.dataSource.TYPE == 'episode' or mli.dataSource.TYPE == 'season':
                self.openItem(mli.dataSource, **extra_kwargs)
            else:
                self.processCommand(opener.handleOpen(subitems.ShowWindow, media_item=mli.dataSource, parent_list=self.showPanelControl, **extra_kwargs))
            if mli.dataSource.TYPE != 'season': # NOTE: A collection with Seasons doesn't have the leafCount/viewedLeafCount until you actually go into the season so we can't update the unwatched count here
                updateUnwatchedAndProgress = True
        elif self.section.TYPE == 'movie' or mli.dataSource.TYPE == 'movie':
            datasource = mli.dataSource
            if datasource.isDirectory():
                cls = self.section.__class__
                section = cls(self.section.data, self.section.initpath, self.section.server, self.section.container)
                sectionId = section.key
                if not sectionId.isdigit():
                    sectionId = section.getLibrarySectionId()

                section.set('librarySectionID', sectionId)
                section.key = datasource.key
                section.title = datasource.title

                self.processCommand(opener.handleOpen(LibraryWindow, windows=self._windows, default_window=self._next, section=section, filter_=self.filter, subDir=True))
                self.librarySettings.setItemType(self.librarySettings.getItemType() or ITEM_TYPE)
            else:
                self.processCommand(opener.handleOpen(preplay.PrePlayWindow if not sectionType == 'movies_shows' else preplay.PrePlayWindowWL, video=datasource, parent_list=self.showPanelControl, **extra_kwargs))
                updateUnwatchedAndProgress = True
        elif self.section.TYPE == 'artist' or mli.dataSource.TYPE == 'artist' or mli.dataSource.TYPE == 'album' or mli.dataSource.TYPE == 'track':
            if ITEM_TYPE == 'album' or mli.dataSource.TYPE == 'album' or mli.dataSource.TYPE == 'track':
                self.openItem(mli.dataSource)
            else:
                self.processCommand(opener.handleOpen(subitems.ArtistWindow, media_item=mli.dataSource, parent_list=self.showPanelControl))
        elif self.section.TYPE in ('photo', 'photodirectory'):
            self.showPhoto(mli.dataSource)

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
            self.processCommand(opener.sectionClicked(photo))

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
        if util.addonSettings.retrieveAllMediaUpFront:
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
        watchlist-specific extra_kwargs, no in-progress auto-resume, no season/episode-to-show
        redirection for discover hubs, no hub-becomes-empty cleanup after the click (an item
        removed/deleted, a watchlist item dropped on open, etc. leaving this row with fewer items
        than before) - real gaps, not yet decided whether/when to close, see
        quiet-orbiting-heron.md."""
        control = self.hubControls[hub_control_id - self.HUB_CONTROL_ID]
        mli = control.getSelectedItem()
        if not mli or not mli.dataSource:
            return

        self.processCommand(opener.open(mli.dataSource))

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
            # dynamic hub with nothing to show right now) - same filter PinnedTypeHubsTask.run()
            # (home.py) already applies for the same reason. Left in, such a hub would still
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
