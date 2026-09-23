from __future__ import absolute_import

import datetime
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
from plexnet import plexlibrary
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
        'mediaHeight': {'title': T(32361, 'By Resolution'), 'display': T(32362, 'Resolution'), 'defSortDesc': True, 'subDisplay': 'resolutionString'},
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
        # The server's compound artist.titleSort,album.titleSort,... sort; "Album Artist" is its
        # own name for it, and for tracks it sits next to the plain track-artist sort below.
        'artist.titleSort': {'title': T(35091, 'By Album Artist'), 'display': T(35092, 'Album Artist'), 'defSortDesc': False},
        'originalTitle': {'title': T(32463, 'By Artist'), 'display': T(32462, 'Artist'), 'defSortDesc': False},
        'album.titleSort': {'title': T(34042, 'By Album'), 'display': T(34043, 'Album'), 'defSortDesc': False},
        'userRating': {'title': T(33103, 'By my Rating'), 'display': T(33104, 'My Rating'), 'defSortDesc': True},
        'addedAt': {'title': T(32351, 'By Date Added'), 'display': T(32352, 'Date Added'), 'defSortDesc': True, 'subDisplay': 'addedAt'},
        'lastViewedAt': {'title': T(32369, 'By Date Played'), 'display': T(32370, 'Date Played'), 'defSortDesc': True},
        'viewCount': {'title': T(32371, 'By Play Count'), 'display': T(32372, 'Play Count'), 'defSortDesc': True, 'subDisplay': 'viewCount'},
        'random': {'title': T(33730, 'Randomly'), 'display': T(33730, 'Randomly'), 'defSortDesc': True},
        # Track-only on the server side (like originalTitle/album.titleSort above); here because
        # sortButtonClicked()/sortDisplay() look labels up by section type, and a music section's
        # TYPE is 'artist' whatever ITEM_TYPE is.
        'lastRatedAt': {'title': T(35087, 'By Date Rated'), 'display': T(35088, 'Date Rated'), 'defSortDesc': True},
        'ratingCount': {'title': T(35089, 'By Popularity'), 'display': T(35090, 'Popularity'), 'defSortDesc': True},
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
        'photo.titleSort': {'title': T(32357, 'By Title'), 'display': T(32358, 'Title'), 'defSortDesc': False},
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


# Sort keys the addon used to persist under its own spelling, mapped to the server's (as
# /sorts advertises them, and as SORT_KEYS/serverSortOptions() now key them). Applied when a
# stored 'sort' setting is read back; both spellings sort identically server-side, this just
# keeps an old setting matching its menu entry.
LEGACY_SORT_KEYS = {
    'resolution': 'mediaHeight',
    'photos.titleSort': 'photo.titleSort',
}


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


# Music sections pin their view type to the item type rather than honouring the per-section
# viewtype.<uuid>.<key> setting every other section type toggles: Artists, Albums and the
# Collections tab are always the grid, Tracks is always the list (a track is a row, not a card).
# Keyed by ITEM_TYPE; a type absent from here - or any section that isn't music - keeps the
# ordinary stored-setting behaviour. Values are VIEWS_SQUARE keys, not window classes, because
# those classes are defined far below this point in the module.
MUSIC_VIEWTYPE_BY_ITEM_TYPE = {
    'artist': 'panel',
    'album': 'panel',
    'collection': 'panel',
    'track': 'list',
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

_sectionHasCollectionsCache = {}

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
    def __init__(self, section_or_server_id):
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
        setItemType(self.getItemType() or self.sectionType or ITEM_TYPE)

    def getItemType(self):
        if not self._settings or self.sectionID not in self._settings:
            return None

        return self._settings[self.sectionID].get('ITEM_TYPE')

    def setItemType(self, item_type):
        setItemType(item_type)
        self._mutate(lambda entry: entry.update({'ITEM_TYPE': item_type}))

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

        if ITEM_TYPE not in self._settings[self.sectionID]:
            return default

        return self._settings[self.sectionID][ITEM_TYPE].get(setting, default)

    def setSetting(self, setting, value):
        def apply_(entry):
            entry.setdefault(ITEM_TYPE, {})[setting] = value

        self._mutate(apply_)


class _CatalogHub(object):
    """Just enough of a hub (title + hubIdentifier) for LibraryWindow.homeHubDisplayTitle() to
    re-label a Manage Hubs catalog entry, which stores those as plain fields."""
    def __init__(self, title, hub_identifier):
        self.title = title
        self.hubIdentifier = hub_identifier


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

    # onFocus()'s own "just crossed into the hub range from outside it" flag, consumed by
    # onAction()'s hub-branch - see onFocus()'s own comment for the double-delivery bug this
    # guards against. Class-level default so it's never missing before the first onFocus() call.
    _hubJustEnteredFromOutside = False

    def __init__(self, *args, **kwargs):
        PlaybackBtnMixin.__init__(self)
        kodigui.MultiWindow.__init__(self, *args, **kwargs)
        windowutils.UtilMixin.__init__(self)
        # Only ever read/written once this instance is windowutils.HOME - see processCommand()'s own
        # comment (Home-ControlledWindow plan, item 4). Defined unconditionally here anyway, same as
        # exitCommand above, so every instance (including nested ones that never become HOME) has it.
        self._pendingSection = None
        self._pendingSectionForce = False
        self.section = kwargs.get('section')
        # openSection() keeps this mirroring self.section on every real section swap (a handful of
        # methods - hubMenu() among them - read self.lastSection directly) - but openSection() itself is
        # never called for the very first section a LibraryWindow is constructed with (cold start,
        # main.py, constructs directly with section=home_section and never calls openSection()).
        # Left unset, self.lastSection would raise AttributeError the first time anything read it
        # before the first real section switch - live-confirmed: hubMenu() (the hub-item context
        # menu) silently did nothing on a hub item click on cold start, working normally only
        # after switching to a different section for the first time. Seeded here so it's never in
        # an undefined state.
        self.lastSection = self.section

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
        self.librarySettings = LibrarySettings(self.section)

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
        # playQueueCallback() - must exist before anything else can run, not just before
        # shutdown() is ever called.
        # go_root/_goRootHoldUntil are consumed by onReInit()/onAction()/onFocus() below - see
        # those for the full mechanism, ported from HomeWindow's own go_root handling.
        self.closeOption = None
        self._shuttingDown = False
        self.go_root = False
        self._goRootHoldUntil = 0
        self._goRootFocusTarget = None
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
        # Pending threading.Timer for _bindPeekHubsDeferred() (see _bindAllHubSlots()'s own
        # defer_peek param) - a fresh 'recommended' entry defers binding the ring's two always-
        # off-screen extreme controls instead of doing it inline. Cancelled by _startHubSlide()/
        # _settleHubSlide() so it can never fire concurrently with a slide's own Control mutation.
        self._hubPeekBindTimer = None
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

    def forcedViewWindow(self):
        """The window class this section/item-type combination is pinned to, or None to honour
        the stored viewtype setting.

        Only music sections pin anything (MUSIC_VIEWTYPE_BY_ITEM_TYPE) - Photos and Playlists
        keep their grid/list toggle. ITEM_TYPE can still be unset the first time a section is
        opened, hence the section-type fallback, which resolves to 'artist' (the grid) for music.
        """
        if self.section.TYPE != 'artist':
            return None

        viewtype = MUSIC_VIEWTYPE_BY_ITEM_TYPE.get(ITEM_TYPE or self.section.TYPE)
        return self.squareViews().get(viewtype) if viewtype else None

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
        next .modal() call - the flicker is the accepted tradeoff for not deadlocking.

        EXPERIMENTAL mitigation, unproven (not the same standing as SKIN_RELOAD_DEFER_SECONDS's
        confirmed-upstream-bug fix, windowutils.py - this is a hypothesis, not a diagnosed root
        cause): the short sleep after gc.collect() below targets a live-reported, intermittent
        unresponsive-black-screen freeze on Back, WinDbg-confirmed as the language-invoker thread
        blocked inside a native call (SleepConditionVariableSRW) from deep within .modal() - i.e.
        genuinely waiting on Kodi's own native side, not a Python-level bug, and not reproducible
        with Kodi's own debug logging on (which slows native processing down, the same effect a
        real sleep has). gc.collect() returning doesn't guarantee Kodi's own native teardown of
        the outgoing shell's window - triggered by freeing it, per this method's own docstring
        above - has actually finished settling before the next .modal() call starts; giving it a
        little real wall-clock time here, same shape as every other SKIN_RELOAD_DEFER_SECONDS use
        in this file, is a cheap, low-risk thing to try. Same accepted-flicker tradeoff as the
        gc.collect() call itself, just a bit more of it."""
        import gc
        collected = gc.collect()
        util.MONITOR.waitFor(windowutils.SKIN_RELOAD_DEFER_SECONDS)
        util.DEBUG_LOG("Library: _setupCurrent({0}) forced gc.collect() after real-shell teardown, "
                        "collected={1}", cls, collected)

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
            if self.visibleHubs and 0 <= self.focusedHubIndex < len(self.visibleHubs):
                hub = self.visibleHubs[self.focusedHubIndex]
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

    def swapTo(self, cls, push=True, **kwargs):
        """Swap this already-open, already-hosting LibraryWindow to one of the seven real
        descendant shell types in place - same construct-fresh-via-_open()'s-loop pattern
        openSection()/switchTab() already use, just targeting a real shell class instead of one
        of LibraryWindow's own thin view-type proxies. See _backStack's own comment (__init__)
        for the two entry shapes pushed here."""
        if push and self._current is not None:
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

    def popBack(self):
        cls, kwargs = self._backStack.pop()
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
            self.openSection(force=True, fresh=False, **kwargs)
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
        self.openSection(section, filter_=filter_, force=True, fresh=False)
        self._backStack = precedingBackStack + [entry]

    def switchTab(self, mode, item_type=None):
        """Swap this already-open window between content modes ('library' grid vs.
        'recommended' hubs) in place, the same construct-fresh-via-_open()'s-loop pattern
        openSection() already uses for section swaps - see that method's own docstring for why
        in-place mutation, not a fresh object, is the safe shape here.

        Also reached (mode always 'library'/'recommended', never 'categories') when leaving the
        Categories tab (genres.py's GenreBrowserWindow, hosted via browseGenres()'s swapTo()) back
        to an ordinary tab - self.contentMode is deliberately never mutated to 'categories' (see
        browseGenres()/onClick()'s TAB_LIST_ID branch), so it still holds whatever content mode
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

        itemTypeChanging = item_type is not None and item_type != ITEM_TYPE

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
        # Settle any in-flight hub-slide animation (its own background thread, see
        # _startHubSlide()) before doClose() below tears the native window down for real -
        # otherwise that thread can still be mid-setPosition() on a control that's about to stop
        # existing. Live-confirmed as a native invalid-pointer-read crash otherwise. Harmless
        # no-op when contentMode isn't 'recommended' (self._hubSliding is only ever True there).
        self._settleHubSlide()
        self._listGeneration += 1
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
        return self.section.TYPE if ITEM_TYPE == 'collection' else None

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

    def openSection(self, section, filter_=None, force=False, fresh=True):
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
        if fresh:
            self._hubReselectPositions = {}
        # Bumped here, not just inside doRefill(), so a suspended call elsewhere that captured
        # showPanelControl/mli.dataSource before this swap can detect the invalidation the moment
        # it actually happens, not only once _open()'s loop gets back around to rebuilding.
        self._listGeneration += 1

        self.section = section
        # Force a fresh live Collections probe for the section we're now entering, rather than
        # trusting whatever was cached from a previous visit - see _sectionHasCollections()'s own
        # docstring. Harmless no-op for section types that were never eligible for the probe in
        # the first place (nothing to evict).
        _invalidateSectionHasCollectionsCache(section)
        # Kept mirroring self.section for the menus that still read self.lastSection.
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
        self.librarySettings = LibrarySettings(self.section)

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

    def sectionByKey(self, key):
        """The sidebar's section object for a library section key, or None. For callers that only
        hold a key (getLibrarySectionId()) - GoHomeMixin._goHomeDirect() (windowutils.py) resolves
        those through here, the way HomeWindow's old 'HOME:<key>' handler matched the same list."""
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
            pendingForce = self._pendingSectionForce
            self._pendingSection = None
            self._pendingSectionForce = False
            if self.closeOption is not None:
                self.doClose()
            elif pending is not None and (pending != self.section or pendingForce):
                # force=True unconditionally here (not just pendingForce) - matches every other
                # openSection() caller in this bubble/dispatch family (popBack(), _deferOpenSection())
                # that already skips its own no-op guard once it's decided a real reconstruction is
                # needed; pendingForce is what decided that above when pending == self.section.
                threading.Timer(windowutils.SKIN_RELOAD_DEFER_SECONDS, self.openSection, args=(pending,),
                                 kwargs={'force': True}).start()
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

    def _sidebarTarget(self):
        """Whichever window object the sidebar's server/user dropdown UI must actually read/write
        controls on right now: self._current (the live, currently-modal real shell) while one is
        hosted, self otherwise. Needed because onAction() runs as this bound method even when a
        real shell owns the screen (_setupCurrent()'s self._current.onAction = self.onAction
        monkeypatch, so shared chrome like the sidebar is handled centrally) - but self's own
        native window has already been closed (doClose()) in favor of the shell's by then (see
        MultiWindow._open()'s .modal() loop). getFocusId() reads still resolve against whatever's
        genuinely on screen (that's how onAction()'s SERVER_BUTTON_ID/USER_BUTTON_ID branches get
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
        self.userList.newControlEmpty(target)
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

    def doUserOption(self, force_option=None, target=None):
        """Ported from HomeWindow.doUserOption() (home.py) - see quiet-orbiting-heron.md's Cold
        Start plan, Stage 3. Adaptations: dialog_props reads carriedProps defensively (getattr,
        CommonMixin's own pattern) since LibraryWindow doesn't define it; storeLastBG() stays
        unported (see shutdown()'s own comment) - HomeWindow's version isn't called from here
        anyway, only from confirmExit()'s minimize branch and shutdown() itself, neither of which
        call it here either; every session-ending branch routes through _closeSessionWithOption()
        above instead of closing self directly - see that method's own comment for why.

        target: explicit override for _sidebarTarget() - onClick()'s own USER_LIST_ID branch below
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
        target = self._sidebarTarget()
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

            # Rebind first, not after - see showUserMenu()'s own comment on this same pattern.
            # newControl(), not newControlEmpty(): from_refresh can reach here with the list
            # already showing (a live server/reachability update, not a fresh open), and unlike
            # showUserMenu()'s unconditional reset()+addItems(), replaceItems() above only
            # repaints when the item count actually changed - newControlEmpty()'s own repaint-skip
            # would leave a stale/empty list on screen in the common case where it doesn't.
            self.serverList.newControl(target)
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
        # newControl() re-adds the items to a fresh native control whose selection starts at index
        # 0 (Search) - reselect the active section so the collapsed rail shows it from the first
        # frame (SidebarMixin._selectActiveSection()'s rule).
        self._selectActiveSection()

        if self.tabList is None:
            self.tabList = kodigui.ManagedControlList(self, self.TAB_LIST_ID, 5)
            self._tabListNeedsRebuild(self.section)  # just to set the tracked flags - always builds below regardless
            self.buildTabList()
        else:
            self.tabList.newControl(self)
            if self._tabListNeedsRebuild(self.section):
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

            # Group 51 has no correct position at all until Python sets it explicitly - grouplist
            # 50 auto-stacks its only child flush to 0, ignoring the declared posy (see that
            # control's own comment in script-plex-recommended.xml.tpl). This shell's control 51
            # is brand new every 'recommended' entry (RecommendedWindow gets torn down and
            # reconstructed by switchTab()/openSection() like any other view-type swap), so it's
            # positioned here, once per entry, at its single fixed offset - nothing else ever
            # moves it (the slides move the per-role wrappers inside it, see _setRoleGeometry()).
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

            # Explicitly (re-)assert focus on the anchor hub row - ported from
            # HomeWindow.applyInitialHubFocus() (home.py), which only ever did this once, the very
            # first hubs draw of a whole session (self._initialHubFocusApplied, guarded on
            # self.getFocusId() == self.SECTION_LIST_ID, the native default this window
            # construction starts with) - broadened 2026-09-04 (live-reported) to run
            # unconditionally, every fresh 'recommended' entry, not just the first ever: this whole
            # branch only ever runs once per freshly-constructed RecommendedWindow shell (see this
            # method's own docstring), so there's no live user interaction between hubsTask.run()
            # returning and here for a later entry to have raced past the way HomeWindow's own
            # background-thread version could. A restored hub/item position
            # (_captureHostedShellRestoreState()'s chain, or _bindHubToControl()'s own
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
                # move, and onFocus()'s own _hubJustEnteredFromOutside detector (see its own
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
                # on a window that has never painted - makes onFocus()'s own was_outside_hub read
                # False regardless of exactly when its callback actually runs relative to this
                # line, rather than trying to race a reset against it afterward.
                self.lastFocusID = self._anchorControlId()
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
        display = self.sortDisplay()
        if display is None:
            self.resetSort()
        else:
            self.setProperty('sort.display', display)
            self.updateSortIcon()
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
        self.fill()
        self.refill = False
        if self.getProperty('no.content') or self.getProperty('no.content.filtered'):
            self.setFocusId(self.SECTION_LIST_ID)
        else:
            self.setFocusId(self.POSTERS_PANEL_ID)

    def _deferOpenSection(self, section, force=False):
        """Single-flight defer for the "self is HOME, safe in-place swap" case both this class's
        own goHome() and windowutils.py's SidebarMixin._dispatchSectionOpen() use (both only ever
        call this when self is windowutils.HOME). Both used to construct their own bare
        threading.Timer(SKIN_RELOAD_DEFER_SECONDS, self.openSection, ...) independently, with no
        coordination between repeated calls.

        force=True (threaded through from an explicit sidebar click on the already-active section,
        SidebarMixin.sectionClicked()) is passed straight through to openSection() - otherwise its
        own `section == self.section` no-op would swallow a click that's meant to reset the section
        in place, the same case serverRefresh() already carries force=True through for.

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
            if self.openSection(section, force=force):
                self.lastSection = section

        self._pendingSectionTimer = threading.Timer(windowutils.SKIN_RELOAD_DEFER_SECONDS, _fire)
        self._pendingSectionTimer.start()

    def goHome(self, section=None, with_root=False, force=False):
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

        force=True (threaded from a sidebar click - windowutils.py's SidebarMixin.sectionClicked()/
        _dispatchSectionOpen()) skips the "already on this section" no-op below, the same way
        openSection()'s own force param does - needed here specifically because a real hosted
        shell's own onClick() (EpisodesWindow etc.) always reaches this method through this exact
        call, never library.py's other sidebar-click path (_deferOpenSection() directly), since a
        real shell's onClick is never monkeypatched to the host's (see
        SidebarMixin.handleSidebarDropdownClick()'s own comment).
        """
        if self is windowutils.HOME:
            if section and (section != self.section or force):
                self._deferOpenSection(section, force=force)
            if with_root:
                self.go_root = True
                self.show()
            return
        # _goHomeDirect(), not the chain-checking goHome() wrapper: this LibraryWindow instance
        # always points its own _chainHost at itself (__init__), so the wrapper would resolve
        # _liveChainHost() back to self and recurse forever. Once this override has already
        # decided "I'm not windowutils.HOME," self-referential delegation is meaningless - see
        # windowutils.py's GoHomeMixin._goHomeDirect() for the full reasoning.
        windowutils.GoHomeMixin._goHomeDirect(self, section=section, with_root=with_root, force=force)

    def goHomeRoot(self, *args, **kwargs):
        if self is windowutils.HOME:
            self.go_root = True
            self.show()
            return
        windowutils.GoHomeMixin._goHomeRootDirect(self)

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
                threading.Timer(windowutils.SKIN_RELOAD_DEFER_SECONDS, self.openSection,
                                 args=(home.home_section,), kwargs={'force': True}).start()
            else:
                # Already showing Home: reset it in place to the first row, item 0 (the Home
                # rule), then hold that focus for 150ms against the stray focus event Kodi fires
                # when this window reactivates with its previously-focused control still recorded
                # (see onFocus()). No hold on the rebuild branch above - it can't outlast the
                # deferred rebuild, and the new window sets its own focus.
                self._goRootFocusTarget = self._resetHubsToTop()
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

        # Dismiss the sidebar user/server popup first, before it can ever reach the back-stack
        # pop below - see dismissSidebarPopupOnBack()'s own comment (windowutils.py) for the bug
        # this fixes: back while the popup was open used to pop the descendant chain a step
        # instead of just closing the popup.
        if action in (xbmcgui.ACTION_PREVIOUS_MENU, xbmcgui.ACTION_NAV_BACK) and \
                self.dismissSidebarPopupOnBack(target=self._sidebarTarget()):
            return

        # Grid "home" on Back, requested directly: Back while scrolled down the poster/list grid
        # snaps to item 0 first, rather than immediately leaving the section/chain - only once
        # already on item 0 does Back fall through to its normal meaning (below). Checked ahead of
        # the chain-pop branch immediately below so this applies even mid-chain (e.g. browsing a
        # Collection's own grid, reached via swapToSection() with a non-empty _backStack) - a
        # scrolled-down position there should also snap home before that chain pops a level.
        #
        # not self._isHostedShell first, and short-circuiting before anything else: self.
        # POSTERS_PANEL_ID/self.getFocusId() aren't real attributes of this outer host object,
        # they resolve via MultiWindow.__getattr__ delegation to self._current - fine whenever
        # self._current is one of LibraryWindow's own thin view-type proxies (PostersWindow etc.,
        # which do define POSTERS_PANEL_ID), but once a real shell is hosted (e.g. PrePlayWindow,
        # after clicking an item from this exact grid) self._current has no such attribute at all.
        # Live-confirmed regression without this guard: raised a bare AttributeError from inside
        # onAction() on every single Back press while any shell was hosted, silently swallowed
        # somewhere above this call - Back appeared to simply stop doing anything at all after
        # opening an item from a grid. contentMode == 'library' (not 'recommended') and focus on
        # POSTERS_PANEL_ID specifically - hub-row Back has its own separate semantics, untouched
        # here.
        if action in (xbmcgui.ACTION_PREVIOUS_MENU, xbmcgui.ACTION_NAV_BACK) and \
                not self._isHostedShell and self.contentMode == 'library' \
                and self.getFocusId() == self.POSTERS_PANEL_ID:
            mli = self.showPanelControl.getSelectedItem() if self.showPanelControl else None
            if mli and mli.pos():
                self.showPanelControl.selectItem(0)
                return

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
            def _popBack():
                try:
                    self.popBack()
                except:
                    # threading.Timer callbacks aren't covered by this addon's normal onAction()-level
                    # error handling - an uncaught exception here (e.g. popBack()'s own _backStack.pop()
                    # live-suspected as a contributor to an intermittent unresponsive-black-screen hang
                    # after Back) would otherwise vanish completely: no traceback anywhere, the outgoing
                    # window already closed, the next one never opens. Purely diagnostic - doesn't change
                    # behavior on the success path.
                    util.ERROR()
            threading.Timer(windowutils.SKIN_RELOAD_DEFER_SECONDS, _popBack).start()
            return

        try:
            controlID = self.getFocusId()
            if controlID == self.SECTION_LIST_ID:
                if self.movingSection:
                    # Section-reorder ("Move") mode - ported from HomeWindow's identical routing
                    # (home.py's onAction()). sectionMover() owns every action while active; nothing
                    # below in this method (the context menu) should also react.
                    self.sectionMover(self.movingSection, action)
                    return
                if action == xbmcgui.ACTION_CONTEXT_MENU:
                    # Section-item context menu - ported from HomeWindow's identical routing
                    # (home.py's onAction()).
                    show_section = self.sectionMenu()
                    if not show_section:
                        return
                    self.serverRefresh(section=show_section)
                    return
            elif controlID == self.SERVER_BUTTON_ID:
                # Stage 3 (quiet-orbiting-heron.md's Cold Start plan) - ported from HomeWindow's
                # identical SERVER_BUTTON_ID handling (home.py's onAction()). selectServer() below
                # is deferred, not called inline: it can end in an openSection()/doClose()-based
                # swap once the resulting change:selectedServer signal reaches serverRefresh() -
                # same reentrancy reasoning as switchTab()'s own deferred dispatch (see
                # windowutils.SKIN_RELOAD_DEFER_SECONDS).
                #
                # This whole onAction() runs against a real hosted shell too (self._current.onAction
                # is monkeypatched to this bound method - _setupCurrent()'s own comment above), but
                # self here is still the *host* - and the host's own native window has already been
                # closed (doClose()) in favor of the shell's, once a real shell is showing (see
                # MultiWindow._open()'s .modal() loop). showServers()/selectServer()/doUserOption()
                # below are all _sidebarTarget()-aware (see that method's own comment) precisely
                # because of this - every control write they do lands on self._current, the
                # genuinely live window, not self.
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
                # identical USER_BUTTON_ID handling (home.py's onAction()). See SERVER_BUTTON_ID's
                # own comment just above on why this is safe against a real hosted shell too.
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
                    if self._hubJustEnteredFromOutside:
                        # Live-confirmed double-delivery (HUBDBG investigation): this same action
                        # already carried focus into the hub range natively (via a control outside
                        # it - the tabs row 320, the audio widget 204, or the sidebar rail 9001 -
                        # all landing here through 50's <defaultcontrol> chain, via <ondown> or, for
                        # the sidebar, <onright>) - Kodi delivers it to onAction() a second time
                        # *after* that navigation has already happened, which onFocus() flagged for
                        # us (see its own comment; onAction() itself can't tell "just arrived" apart
                        # from "already settled here" - by the time it runs, the native move, if
                        # any, is already done either way).
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
                        return
                    action_id = action.getId()
                    if action_id in (xbmcgui.ACTION_MOVE_UP, xbmcgui.ACTION_MOVE_DOWN):
                        # Topmost hub, pressing up: exit the rotation ring entirely instead of the
                        # silent no-op _startHubSlide() falls into at focusedHubIndex 0 - same role
                        # XML onup plays for grid content (library_posters.xml.tpl etc.), just done
                        # here in Python since hub-to-hub vertical nav is already fully Python-owned
                        # (see this branch's own docstring reference to home.py's onAction()).
                        # Prefers the section-tabs row (plan item 0) when it's actually on screen;
                        # falls back to the audio widget (204) when the tabs are hidden (a 'mixed'
                        # section has none) so pressing up still lands somewhere reachable rather
                        # than nowhere - the same condition every XML onup/onright path into 204
                        # already gates on (e.g. section_tabs.xml.tpl's own onright).
                        if action_id == xbmcgui.ACTION_MOVE_UP and self.focusedHubIndex == 0:
                            if self.tabList and self.section.TYPE != 'mixed':
                                self.setFocusId(self.TAB_LIST_ID)
                                return
                            elif xbmc.getCondVisibility(
                                    'Player.HasAudio + String.IsEmpty(Window(10000).Property(script.plex.theme_playing))'):
                                self.setFocusId(self.PLAYER_STATUS_BUTTON_ID)
                                return
                        self._startHubSlide(-1 if action_id == xbmcgui.ACTION_MOVE_UP else 1)
                        return
                    elif action_id in (xbmcgui.ACTION_MOVE_LEFT, xbmcgui.ACTION_MOVE_RIGHT):
                        # Plan items 10 (Group A)/11: sync hero art/info to the item this move is
                        # landing on, plus pagination/reselect-position memory (checkHubItem(),
                        # all hooked into this same call site). Reads
                        # getSelectedItem() directly, same as MOVE_SET's own dynamic-background
                        # update below does for the grid - Kodi's native container cursor is
                        # already at the new position by the time onAction() runs (that existing,
                        # proven pattern is what this one's modeled on), not the old one, so no
                        # special before/after ordering is needed here. Deliberately doesn't
                        # return (checkHubItem()'s return value only matters for the NAV_BACK
                        # case below) - the actual cursor movement is Kodi's own native list
                        # behavior, not something this method does; falls through to
                        # kodigui.MultiWindow.onAction() below like anything else unhandled here.
                        self.checkHubItem(controlID, action=action)
                    elif action in (xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_PREVIOUS_MENU):
                        # Only reached when self._backStack is empty (onAction()'s own top-of-
                        # method check already intercepts NAV_BACK/PREVIOUS_MENU otherwise) - i.e.
                        # a hub row focused on the root 'recommended' tab, no chain in progress.
                        # checkHubItem() resets to item 0 first if not already there (returns
                        # False, swallowed here); only lets the action propagate to whatever
                        # default NAV_BACK handling exists below once already at item 0 - same
                        # shape as HomeWindow's own onAction() routing (home.py).
                        if not self.checkHubItem(controlID, action=action):
                            return
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
                # per-item behavior (hero-art updates, pagination) genuinely still is.
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
                if mode == 'categories':
                    threading.Timer(windowutils.SKIN_RELOAD_DEFER_SECONDS, self.browseGenres).start()
                elif mode == 'collections':
                    threading.Timer(windowutils.SKIN_RELOAD_DEFER_SECONDS, self.switchToCollections).start()
                else:
                    item_type = self._libraryTabItemType() if mode == 'library' else None
                    threading.Timer(windowutils.SKIN_RELOAD_DEFER_SECONDS, self.switchTab,
                                    args=(mode,), kwargs={'item_type': item_type}).start()
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
            # falling into that chain. PLAYER_STATUS_BUTTON_ID (204, the header audio widget) is
            # checked explicitly too, for the same reason - it's the one control from that chain
            # this window's own template actually has (script-plex-recommended.xml.tpl), and
            # without this the unconditional `return` below swallowed clicks on it entirely
            # (live-confirmed: no music-player window opened, unlike every other window that
            # reaches the elif chain's own PLAYER_STATUS_BUTTON_ID case further down).
            if 399 < controlID < 500:
                self.hubItemClicked(controlID)
            elif controlID == self.PLAYER_STATUS_BUTTON_ID:
                self.showAudioPlayer()
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
            try:
                home.watchlist_section = plexlibrary.WatchlistSection(
                    None, server=plexapp.SERVERMANAGER.getDiscoverServer())
                home.watchlist_section.title = T(34000, 'Watchlist')
            except plexnet.exceptions.BadRequest as e:
                # WatchlistSection.__init__ (plexlibrary.py) queries discover.provider.plex.tv
                # synchronously, uninsured - live-confirmed: a transient 503 there raised
                # uncaught all the way out of onFirstInit(), leaving the whole window (sidebar
                # partially built, no Home content) stuck instead of just missing Watchlist for
                # this session. Same catch/skip idiom this file already uses elsewhere for
                # optional, best-effort fetches (see e.g. SectionTask.run() above). Leaving
                # home.watchlist_section as whatever it already was (usually None) is enough -
                # the check below already treats a falsy value as "don't show it".
                util.DEBUG_LOG('Watchlist section unavailable ({0}), skipping for this session', e)
                home.watchlist_section = None

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
            self.navSettings["order"] = [i.dataSource.key for i in self.sectionList.items if i.dataSource]
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
        if not has_collections and ITEM_TYPE == 'collection':
            self.librarySettings.setItemType(section.TYPE)
        needsRebuild = (is_playlists != self._tabListIsPlaylists
                         or has_categories != self._tabListHasCategories
                         or has_collections != self._tabListHasCollections)
        self._tabListIsPlaylists = is_playlists
        self._tabListHasCategories = has_categories
        self._tabListHasCollections = has_collections
        return needsRebuild

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
            if self._tabListHasCollections:
                # Collections - not a real contentMode (same shape as Categories below), just
                # another tab entry pointing at switchToCollections() instead of switchTab() - see
                # onClick()'s TAB_LIST_ID branch. Reuses the exact label the item-type dropdown
                # used to show for this choice (T(32490, 'Collections')), now removed from that
                # dropdown (itemTypeButtonClicked()) since this tab replaces it.
                mli = kodigui.ManagedListItem(T(32490, 'Collections'))
                mli.setProperty('item', '1')
                mli.setProperty('content.mode', 'collections')
                items.append(mli)
            if self.section.TYPE in ('movie', 'show'):
                # Categories (genres.py's GenreBrowserWindow) - not a real contentMode (see
                # switchTab()'s own comment), just another tab entry pointing at browseGenres()
                # instead of switchTab() - see onClick()'s TAB_LIST_ID branch.
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
            key, active = 'item.type', ITEM_TYPE
        else:
            key = 'content.mode'
            if active_override:
                active = active_override
            elif self._tabListHasCollections and self.contentMode == 'library' and ITEM_TYPE == 'collection':
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
        # Flags "just crossed into the hub-row range (399-500) from a control outside it" for
        # onAction()'s own hub-branch to consume - live-confirmed Kodi behavior: a directional
        # action that exits a native container via its own <onup>/<ondown>/<onright> (the tabs
        # row 320, the audio widget 204, or the sidebar rail 9001, all landing on a hub control
        # via 50's <defaultcontrol> chain) gets delivered to onAction() a SECOND time *after*
        # native navigation has already moved focus - onFocus(<hub control>) fires before
        # onAction()'s own getFocusId() for that same press, i.e. the move already happened once
        # by the time our Python code runs at all. Without this guard, onAction()'s hub-branch
        # treated that replay as a second, independent move and acted on it again (silently
        # continuing on to the next row on entry, or swallowing the next real press after a
        # sidebar interaction, depending on which action the replay carried).
        #
        # Computed here, not in onAction(): this is the only place that reliably knows what
        # controlID had focus *immediately before* this one (self.lastFocusID, not yet
        # overwritten below) - onAction()'s own getFocusId() can't tell "just arrived from
        # outside" apart from "already settled here", since by the time it runs the native move,
        # if any, has already completed either way. Consumed (reset to False) the first time
        # onAction()'s hub-branch checks it, before branching on the action's own direction -
        # the replay carries whatever direction caused the entry, not necessarily UP/DOWN - so
        # it never survives to affect a later, unrelated real press; those never re-fire onFocus
        # for the same control anyway, since in-hub vertical nav is entirely Python-owned
        # (_startHubSlide()), not native.
        if self.contentMode == 'recommended':
            was_outside_hub = not (399 < (self.lastFocusID or -1) < 500)
            self._hubJustEnteredFromOutside = (399 < controlID < 500) and was_outside_hub

        # Within the 150ms hold window after an in-place go_root reset, a focus event anywhere
        # but the reset's own target is the stray Kodi fires when this window reactivates with its
        # previously-focused control still recorded. Snap it back and consume the deadline so real
        # user input (which arrives well after the window closes) passes through unblipped. See
        # onReInit()'s go_root handling.
        if time.time() < self._goRootHoldUntil and controlID != self._goRootFocusTarget:
            self._goRootHoldUntil = 0
            self.lastFocusID = self._goRootFocusTarget
            self.setFocusId(self._goRootFocusTarget)
            return

        self.reselectActiveSection(controlID, self.lastFocusID)
        self.lastFocusID = controlID

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
        self.swapTo(genres_window.GenreBrowserWindow, section=self.section)

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
            args['sort'] = plexlibrary.sortArg(sort)

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
        # Only ever "Go to <section>" now, and the button (303) is only shown for photodirectory
        # sections, where no.options is empty. It used to also offer "Play Next" whenever music
        # was playing, which is what made it appear on Movies/TV grids; dropped.
        options = []
        if self.section.TYPE == 'photodirectory':
            options.append({'key': 'to_section', 'display': T(32324, u'Go to {0}').format(self.section.getLibrarySectionTitle())})

        choice = dropdown.showDropdown(options, (255, 205))
        if not choice:
            return

        if choice['key'] == 'to_section':
            self.goHome(self.section.getLibrarySectionId())

    def itemTypeButtonClicked(self):
        # Button stays visible on the Collections tab (its own visibility only checks
        # section.TYPE, not ITEM_TYPE), but none of the branches below ever offer a
        # 'collection' option to select - same no-op-click treatment 'playlists' already
        # gets further down for a type with no dropdown options at all.
        if ITEM_TYPE == 'collection':
            return

        options = []

        # 'collection' deliberately excluded from every branch below - promoted to a real tab
        # (Collections, buildTabList()/switchToCollections()), same precedent as Categories'
        # 'browse_genres' choice before it (see this method's own git history) - control 312
        # (ITEM_TYPE_BUTTON_ID)'s dropdown no longer offers either.
        if self.section.TYPE == 'show':
            for t in ('show', 'episode'):
                options.append({'type': t, 'display': TYPE_PLURAL.get(t, t)})
        elif self.section.TYPE == 'movie':
            options.append({'type': 'movie', 'display': TYPE_PLURAL.get('movie', 'movie')})
            options.append({'type': 'folder', 'display': TYPE_PLURAL.get('folder', 'folder')})
        elif self.section.TYPE == 'artist':
            for t in ('artist', 'album', 'track'):
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

        self._applyItemTypeChoice(choice)

    def _applyItemTypeChoice(self, choice, keep_focus=True):
        """Switch ITEM_TYPE in place (no window reconstruction) - shared by
        itemTypeButtonClicked()'s dropdown result above and the Playlists tabList's Music/Video
        click (onClick()'s TAB_LIST_ID branch), which needs the exact same effect without a
        dropdown at all.

        keep_focus: forwarded to fill() - True (default) leaves native focus wherever it already
        was (right for the dropdown-result case above: closing the dropdown already returns focus
        to the item-type button, and yanking it into the grid instead would undo that). Passed
        False by switchToCollections() for its own in-place-refill path, since a tab click - unlike
        a dropdown result - should move focus onto the grid the same way every other tab-switch
        path here does (live-confirmed otherwise: Library -> Collections left focus sitting on the
        tab row, with no poster showing as focused at all, unlike every other tab-swap direction,
        which all go through switchTab()'s full reconstruction and land on the grid naturally)."""
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

        # The pinned window, not nextWindow(False): False resolves to whichever class is already
        # showing (kodigui.py), so it can never return anything but None here - fine while every
        # item type shared one view, but a music section now changes view class with the item type
        # (Tracks is the list, Artists/Albums the grid), and that needs a real reconstruction.
        # Passing a class still short-circuits to None when it's the one already showing, so the
        # ordinary in-place refill below is unaffected for every other section type.
        if not self.nextWindow(self.forcedViewWindow() or False):
            self.setProperty('media.type', TYPE_PLURAL.get(ITEM_TYPE or self.section.TYPE, self.section.TYPE))
            display = self.sortDisplay()
            if display is None:
                # stored sort isn't valid for this item type
                self.resetSort()
            else:
                self.setProperty('sort.display', display)
                self.updateSortIcon()
            self.fill(keep_focus=keep_focus)

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

        # The static lists below are the fallback for when the server has no /sorts answer
        # (old PMS, request failed) and for the section types usesServerSorts() excludes.
        serverOptions = self.usesServerSorts() and self.serverSortOptions() or []

        if serverOptions:
            for opt in serverOptions:
                option = dict(opt, indicator=self.sort == opt['type'] and ind or '')
                defSortByOption[opt['type']] = opt['defSortDesc']
                options.append(option)
        elif self.section.TYPE == 'movie':
            searchTypes = ['titleSort', 'year', 'originallyAvailableAt', 'rating', 'audienceRating', 'userRating',
                           'contentRating', 'duration', 'viewOffset', 'viewCount', 'addedAt', 'lastViewedAt',
                           'mediaHeight', 'mediaBitrate', 'random']
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
            searchTypes = ['addedAt', 'originallyAvailableAt', 'photo.titleSort', 'mediaCount']
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
        self.updateSortIcon()

        self.sortShowPanel(choice, True, keep_focus=True)

    def viewTypeButtonClicked(self):
        # Button 304 is hidden for music sections (script-plex-squares.xml.tpl/
        # script-plex-listview-square.xml.tpl), so this is unreachable there by click - the guard
        # is for any other route in, and to make sure nothing writes a viewtype setting that
        # reset() would then ignore.
        if self.forcedViewWindow():
            return

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
        elif choice == 'mediaHeight':
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
        self.setProperty('sort.display', self.sortDisplay())
        self.updateSortIcon()

    def updateSortIcon(self):
        # A plain token, not a texture path: $INFO[Window.Property(...)] isn't evaluated inside
        # a button's <texturenofocus> the way it is inside an image control's <texture> (that
        # only resolved to a broken path, rendering an empty box) - so the skin instead flips
        # between two static-texture placeholder buttons on this property, same as it already
        # does for the media-type button's artist/non-artist variants (310/312).
        self.setProperty('sort.icon', self.sortDesc and 'desc' or 'asc')

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
                # self.openItem() (opener.open() -> opener.showClicked(), context=self), not a
                # direct self.openWindow(subitems.ShowWindow, ...) any more - showClicked() is where
                # skipChildren shows (single-season, "Seasons" library option set to Hide) get
                # redirected straight to EpisodesWindow instead of ShowWindow; a direct openWindow()
                # call here bypassed that dispatch entirely, live-confirmed (this was still landing
                # on the Seasons page for skipChildren shows after that fix). Identical outcome to
                # before for every other show - showClicked()'s own non-skipChildren branch does the
                # same context.openWindow(subitems.ShowWindow, media_item=show, **kwargs) this used
                # to do directly.
                self.openItem(mli.dataSource, parent_list=self.showPanelControl, **extra_kwargs)
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
            # Mirrors the 'collection' branch above - opener.open()'s playlist-TYPE branch now
            # swaps in place via context=self, same as every other migrated shell.
            self.processCommand(opener.open(mli.dataSource, context=self))

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

        key = self.sort
        if self.usesServerSorts():
            # Send the server's canonical key rather than the short one self.sort holds: for
            # Album Artist that's the compound 'artist.titleSort,album.titleSort,album.index,...',
            # which pins the secondary order (and what :desc flips, see plexlibrary.sortArg())
            # to the server's own definition instead of whatever it defaults to for a bare key.
            for opt in self.serverSortOptions():
                if opt['type'] == key:
                    key = opt['serverKey']
                    break

        return (key, self.sortDesc and 'desc' or 'asc')

    def usesServerSorts(self):
        """Whether this section's sort menu comes from the server (/sorts?includeAdvanced=1)
        rather than the static lists in sortButtonClicked().

        Every real PMS section type. Checked against PMS 1.43.4 (2026-09-20): with includeAdvanced
        the server's list is a superset of the static one for every item type - identical for
        movies/shows/artists, and adding the sorts the static lists lacked for episodes (Year,
        Duration, Progress, Plays, Resolution), albums (Year, Rating) and especially tracks (Album
        Artist, Artist, Album, Rating, Duration, Date Rated, Popularity, Bitrate, Randomly).

        Not for: the watchlist (not a PMS section), synthetic folder sections (subDir - their key
        is a path, and the static list is the right answer there anyway), and collections, where
        the server only advertises Title but the addon has always offered Date Added (and Content
        Rating for movie collections) too, and the server does honour them.
        """
        return self.section.TYPE in ('movie', 'show', 'artist', 'photo') \
            and bool(self.section.key) and self.section.key.isdigit() \
            and self.librarySettings.getItemType() != 'collection'

    def serverSortOptions(self):
        """The sorts the server advertises for the current section + item type, as dropdown
        option dicts in server order, or [] when it has nothing usable (old server, request
        failed, unknown item type) so callers fall back to the static lists.

        'type' is the *leading component* of the server key - 'artist.titleSort' for the compound
        Album Artist sort - and is what self.sort holds and LibrarySettings persists. That keeps
        every existing consumer of self.sort working unchanged (isAlphaSort(), the SORT_KEYS
        label/subDisplay lookups, the jumpList guards in fillShows(), previously stored settings);
        only getSortOpts() expands it to the full 'serverKey' at request time. Labels come from
        SORT_KEYS where pm4k has localized ones, else the server's own title - the same hybrid as
        FILTER_LABELS/_filterLabel().
        """
        libtype = self.librarySettings.getItemType() or self.section.TYPE
        try:
            sorts = self.section.listSorts(libtype=libtype)
        except Exception:
            util.ERROR('serverSortOptions: listSorts failed')
            return []

        options = []
        seen = set()
        for srt in sorts:
            serverKey = srt.key
            if not serverKey:
                continue
            key = serverKey.split(',')[0]
            if key in seen:
                continue
            seen.add(key)
            known = SORT_KEYS[self.section.TYPE].get(key) or SORT_KEYS['movie'].get(key) or {}
            title = srt.title or key
            options.append({
                'type': key,
                'serverKey': serverKey,
                'title': known.get('title', title),
                'display': known.get('display', title),
                'defSortDesc': srt.defaultDirection == 'desc',
            })
        return options

    def sortDisplay(self):
        """Sort-button label for self.sort: pm4k's localized SORT_KEYS text where it has one,
        else the server's title for that sort, else None - the key is unknown to both, so the
        caller should resetSort()."""
        known = SORT_KEYS[self.section.TYPE].get(self.sort) or SORT_KEYS['movie'].get(self.sort)
        if known:
            return known['display']
        if self.usesServerSorts():
            for opt in self.serverSortOptions():
                if opt['type'] == self.sort:
                    return opt['display']
        return None


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
        # through specifically for that one. artist.titleSort (Album Artist, for albums and
        # tracks) used to be excluded here over a server 500 - that was the merged 'type=9,18'
        # below (collections have no artist to join on), not the sort itself; with the plain
        # type PMS 1.43.4 answers it correctly for both (buckets checked against the sorted
        # list) and flags the sort with firstCharacterKey itself. A server that still can't
        # just fails the request, which jumpList() turns into None and the plain scrollbar.
        if isAlphaSort(self.sort) and ITEM_TYPE != 'folder' \
                and (ITEM_TYPE != 'episode' or self.sort == 'show.titleSort') \
                and not self.subDir and self.section.TYPE not in ("collection", "movies_shows"):
            # find library collection mode setting, as we need to force-feed the collection type to the jumpList,
            # if collection_mode is 2, otherwise the returned item count differs from /all with the same parameters
            collection_mode = self.section.settings.get("collectionMode",
                                                       {"value": plexobjects.PlexValue(2)})["value"].asInt()

            jl_type = type_
            # collectionMode ("hide items which are in collections") is a movie/show library pref;
            # music and photo sections have no such entry in /prefs (live-checked), so the default
            # of 2 above would fabricate one for them - and the merged type it leads to is exactly
            # what makes the server 500 on the artist-joined Album Artist sort.
            if self.section.TYPE != 'artist' and collection_mode == 2 \
                    and not (self.filter or self.boolFilters.get('unwatched')):
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

        restorePos = self._consumeRestoreItemPos(totalSize)
        self.showPanelControl.selectItem(restorePos)
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

        if restorePos:
            # Real art/metadata only exists for whichever chunk(s) have actually been fetched -
            # by default (retrieveAllMediaUpFront off) only chunk 0 is requested up front, above;
            # real chunks are otherwise only ever requested by MOVE_SET arrow-key navigation
            # (onAction()) or keyClicked()'s identical jump-and-request pattern, which this
            # mirrors. selectItem() above is a plain Python-side position set - it never generates
            # that arrow-key navigation, so a restored position past chunk 0 would otherwise sit on
            # fallback-thumb placeholders until the user nudges focus. Deliberately placed after
            # the loop above, not alongside selectItem() - requestChunk() reads
            # self.finalChunkPosition/self.alreadyFetchedChunkList, both only just set to their
            # real values by that loop (still 0/empty, their __init__/top-of-method reset, before
            # it runs). Requests the position's own chunk plus CHUNK_OVERCOMMIT ahead of it, same
            # as keyClicked(), so the row(s) around it don't show blank/fallback art either.
            chunkOC = getattr(self._current, "CHUNK_OVERCOMMIT", self.CHUNK_OVERCOMMIT)
            self.requestChunk(restorePos)
            self.requestChunk(restorePos + chunkOC)

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
        mli.setProperty('photo.summary', util.widenParagraphBreaks(photo.get('summary')))

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
            util.colorizeEmoji(obj.title) or '',
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
        self.showPanelControl.selectItem(self._consumeRestoreItemPos(len(items)))
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
        self.showPanelControl.selectItem(self._consumeRestoreItemPos(len(items)))

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

                        mli.setProperty('summary', util.widenParagraphBreaks(obj.summary))

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

                        mli.setProperty('summary', util.widenParagraphBreaks(obj.summary))

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
                            # The music section's list view renders a track as three separate
                            # fields rather than that one composite label (which stays as it is,
                            # for every other consumer of a track row) - see
                            # includes/track_row_text.xml.tpl. Label/Label2 are deliberately left
                            # alone: Label2 below is set to the duration for every type, in
                            # durationToText()'s "2m 23s" form, where a track wants "2:23".
                            mli.setProperty('track.title', obj.title or '')
                            mli.setProperty('track.artist', obj.grandparentTitle or '')
                            mli.setProperty('track.duration',
                                            util.simplifiedTimeDisplay(obj.duration.asInt()))
                            # Keyed off the same window property ArtistWindow's Popular Tracks row
                            # uses for its now-playing tint (subitems.py).
                            mli.setProperty('track.ID', obj.ratingKey)
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
                        mli.setProperty('summary', util.widenParagraphBreaks(obj.get('summary')))

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
    # can't be relied on for this). Set once per fresh 'recommended' entry, in onFirstInit().
    # -32, not the 381 it once was: the hero overlay used to be conditional, with grouplist 50
    # shifting down 413px (its old Conditional animation) whenever it showed and this offset
    # counter-shifting by the same amount to keep the anchor at ANCHOR_ABS_Y. The overlay is
    # unconditional now, so both halves are baked in: 50 sits at 518 permanently and this is the
    # old 381 - 413. Negative is fine - it was already this value live whenever hero art showed.
    GROUP51_BASELINE_OFFSET = -32
    # Hub-switch slide animation step count/total time - ported verbatim from
    # HomeWindow.HUB_SLIDE_STEPS/HUB_SLIDE_TIME.
    HUB_SLIDE_STEPS = 12
    HUB_SLIDE_TIME = 0.25
    # How long after a fresh 'recommended' entry _bindPeekHubsDeferred() waits before binding the
    # ring's two extreme (role +-half) controls - always outside grouplist 50's clip region (see
    # _startHubSlide()'s own docstring), so never visible at the moment they'd otherwise be bound
    # inline. Long enough that the window has definitely painted with its immediately-visible rows
    # (anchor + peek +-1) before this fires; short enough to almost always land before a user could
    # plausibly slide that far. Not tied to HUB_SLIDE_TIME/SKIN_RELOAD_DEFER_SECONDS - a distinct
    # concern (background content bind, not animation or click-debounce), sized on its own.
    HUB_PEEK_BIND_DEFER_SECONDS = 0.2
    # Hero art/info overlay (plan item 11) - ported from HomeWindow's own constants (home.py).
    # The overlay is unconditional - shown for every focused hub item, whatever its type (the old
    # HERO_ART_TYPES / _typeHasHeroArt() movie-and-TV-only gate is gone, and with it the
    # two-position row layout it drove - see GROUP51_BASELINE_OFFSET above) - so no_hero_art is
    # only ever True while nothing is bound at all: a fresh 'recommended' entry before hubsTask
    # lands (onFirstInit(), hiding the previous section's stale overlay) and a section with no
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
        this file's own convention (self.section.key is None; LibraryWindow has no
        self.lastSection concept, self.section already is "whatever's currently shown")."""
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
        it."""
        self._setNoHeroArt(False)
        result = self.updateBackgroundFrom(ds)
        self.setHeroInfo(ds)
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
        from hub 0 (which also puts the hero on hub 0's first item), selects item 0 in every row,
        and focuses the anchor row. Returns the control id it focused, for onFocus()'s hold - the
        sidebar when there are no hubs, the same exception a section with no content gets."""
        self._settleHubSlide()
        self._hubReselectPositions = {}
        if not self.visibleHubs or not self.hubControls:
            self.setFocusId(self.SECTION_LIST_ID)
            return self.SECTION_LIST_ID

        self.focusedHubIndex = 0
        self._anchorRingPos = self.HUB_ROTATION_RING.index(self.HUB_CONTROL_ID)
        self._bindAllHubSlots()
        # _bindHubToControl() only selects when there's a remembered position, and these are the
        # same native controls, so they keep whatever they last had selected.
        for hc in self.hubControls:
            if hc.size():
                hc.selectItem(0)

        target = self._anchorControlId()
        # Pre-seeded for the same reason onFirstInit() does it: the programmatic focus below must
        # not look like a native arrival from outside the hub range to onFocus().
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
        self._setNoHeroArt(False)
        self.setHeroInfo(new_ds)
        self.updateBackgroundFrom(new_ds)

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
        self._setNoHeroArt(False)
        self.setHeroInfo(ds)
        self.updateBackgroundFrom(ds)

    def checkHubItem(self, control_id, action=None):
        """Horizontal (left/right) in-row hub navigation - hero-art sync (delegated to
        _updateHeroFromFocusedHubItem() above) and reselect-position memory, both hooked into
        this one call site (onAction()'s hub-row branch). Port of HomeWindow.checkHubItem()
        (home.py), plan item 10 Group A (quiet-orbiting-heron.md). In-row pagination (the old
        "load more" placeholder this also used to trigger) is gone - a row is capped at
        home.HUB_ROW_MAX_ITEMS, see _bindHubToControl().

        Round-robin wraparound (the old hubs_round_robin setting) was deliberately dropped after
        this landed, not ported: pressing Left at a row's first item already exits to the sidebar
        (native template onleft neighbor, nothing Python-side to override), and NAV_BACK already
        jumps back to item 0 - between the two, a mid-row "wrap past the end" gesture wasn't worth
        the extra state/complexity (self._lastSelectedItem, the old double-press detector, is gone
        too - nothing else in this file ever needed it).

        self.section.key is None replaces self.lastSection's is-home check (this file's own
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
        """Open whatever's focused in a hub row (controls 400-404). Port of
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
        if hub_is_home:
            hub_title = self.homeHubDisplayTitle(hub, self.ambiguousHubTitles(self.visibleHubs))

        select_base = 0

        options = []
        has_prev = False
        is_watchlist = self.lastSection == home.watchlist_section
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

        elif choice["key"] == "to_show":
            try:
                command = opener.open(ds.show(), context=self, dialog_props=getattr(self, 'carriedProps', None))
                if command == "NODATA":
                    raise util.NoDataException
            except util.NoDataException:
                util.ERROR("No data - deleted or server disconnected?", notify=True, time_ms=5000)
                return

        elif choice["key"] == "to_item":
            try:
                command = opener.open(ds, context=self, dialog_props=getattr(self, 'carriedProps', None))
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

        # Row title label reads $INFO[Window.Property(hub.{{ id - 100 }})] (id 500-504, so
        # property name is hub.400 .. hub.404) - same property name/format
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

        reselect = self._hubReselectPositions.get(identifier)
        if reselect and items:
            rk, pos = reselect
            resolved = next((i for i, mli in enumerate(items)
                              if mli.dataSource and str(mli.dataSource.ratingKey) == rk), pos)
            if resolved is not None and 0 <= resolved < len(items):
                control.selectItem(resolved)

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

            self._bindAllHubSlots(defer_peek=True)
            util.DEBUG_LOG("Library: _recommendedHubsCallback() bound {0} hub(s) for {1}, anchor={2}",
                           min(len(sorted_hubs), len(self.hubControls)), section.key,
                           self._anchorControlId())

    def _bindAllHubSlots(self, defer_peek=False):
        """Bind all 5 physical hub-row controls to their current roles, from
        self.visibleHubs/self.focusedHubIndex (already set by the caller) - factored out of
        _recommendedHubsCallback()'s own per-control loop (Stage D2) since it's also needed
        outside a fresh section bind: plan item 10's Group B (hubItemClicked()'s empty-hub
        cleanup, after visibleHubs shrinks) and Group A (returning to a hub row whose reselect
        position should be restored - handled by _bindHubToControl() itself, called from here).
        Ported in spirit from HomeWindow._bindAllHubSlots() (home.py) - "visibleHubs by
        construction only ever contains non-empty hubs, so any in-range index is automatically
        valid" (focusFirstValidHub()'s own comment there) still applies verbatim here.

        defer_peek: True only from _recommendedHubsCallback()'s own fresh-entry call. Skips
        binding (just resets) the ring's two extreme (role +-half) controls here and schedules
        _bindPeekHubsDeferred() to do it ~HUB_PEEK_BIND_DEFER_SECONDS later instead - both are
        always fully outside grouplist 50's clip region (see _startHubSlide()'s own docstring),
        so this never leaves anything visible unbound, it just moves 2 of the 5 initial
        createListItem() passes off the synchronous tab-entry path. False (the reset()-then-
        continue "out of range" branch below already covers a real gap) for every other caller -
        those run mid-session, off the hot tab-entry path, where the eager behavior's own
        correctness (e.g. not leaving stale content from a just-deleted hub) matters more than
        shaving a few controls' worth of bind time."""
        if not self.visibleHubs:
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

        half = len(self.HUB_ROTATION_RING) // 2
        for control_id in sorted(self.HUB_ROTATION_RING, key=lambda cid: abs(self._ringRoleOffset(cid))):
            role = self._ringRoleOffset(control_id)
            index = control_id - self.HUB_CONTROL_ID
            wrapper = self.getControl(self.HUB_WRAPPER_FOR_CONTROL[control_id])
            self._setRoleGeometry(wrapper, role, self.focusedHubIndex)

            if defer_peek and abs(role) == half:
                self.hubControls[index].reset()
                self.setProperty('hub.display.4{0:02d}'.format(index), '')
                continue

            hub_index = self.focusedHubIndex + role
            if not (0 <= hub_index < len(self.visibleHubs)):
                self.hubControls[index].reset()
                self.setProperty('hub.display.4{0:02d}'.format(index), '')
                if role == -1:
                    self.setBoolProperty('hub.has_prev', False)
                elif role == 1:
                    self.setBoolProperty('hub.has_next', False)
                continue

            self._bindHubToControl(self.visibleHubs[hub_index], index)
            if role == -1:
                self.setBoolProperty('hub.has_prev', True)
            elif role == 1:
                self.setBoolProperty('hub.has_next', True)

        if defer_peek:
            generation = self._listGeneration
            timer = threading.Timer(self.HUB_PEEK_BIND_DEFER_SECONDS,
                                    self._bindPeekHubsDeferred, args=[generation])
            timer.name = 'hubpeekbind'
            self._hubPeekBindTimer = timer
            timer.start()

    def _bindPeekHubsDeferred(self, generation):
        """threading.Timer target scheduled by _bindAllHubSlots(defer_peek=True) - binds the
        ring's two extreme (role +-half) controls that call left skipped (reset only),
        ~HUB_PEEK_BIND_DEFER_SECONDS after a fresh 'recommended' entry. Re-derives which physical
        control currently holds each extreme role, and which hub belongs there, from live state
        (self.focusedHubIndex/self._anchorRingPos) rather than anything captured at schedule time,
        so this is still correct even if the user has already slid once or more by the time it
        fires - same as every other role/content lookup in this file.

        Declines under self.lock if stale (same generation/closing/contentMode guard
        _recommendedHubsCallback() itself uses) or if a slide is actively mid-animation
        (self._hubSliding): _startHubSlide()'s own wrap-control rebind already touches these same
        two roles as part of every slide, so racing it from this second thread for content that's
        about to be superseded anyway buys nothing and risks a genuine concurrent-Control-mutation
        collision - the one thing this whole mechanism has stayed deliberately cautious about (see
        _recommendedHubsCallback()'s own docstring). _settleHubSlide() - called by _startHubSlide()
        before every new slide, and directly by switchTab()/openSection() before tearing this
        window down - cancel()s and join()s this timer outright first, so this decline branch is
        normally only reached in the narrow window where the timer had already started running
        (past cancel()'s reach) just as _settleHubSlide() ran. Worst case either way: the role
        stays unbound - still never visible - until the user's own next slide binds it for real
        via the normal wrap path, never a wrong-content or missing-content-while-visible bug."""
        with self.lock:
            if (generation != self._listGeneration or self.closing
                    or self.contentMode != 'recommended' or self._hubSliding):
                return

            half = len(self.HUB_ROTATION_RING) // 2
            for control_id in self.HUB_ROTATION_RING:
                role = self._ringRoleOffset(control_id)
                if abs(role) != half:
                    continue
                index = control_id - self.HUB_CONTROL_ID
                hub_index = self.focusedHubIndex + role
                if 0 <= hub_index < len(self.visibleHubs):
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
        write. HUB_SLIDE_TIME is 0.25s total, so a bounded wait is cheap insurance either way, not
        a real stall - left in place as legitimate defensiveness, not reverted just because it
        wasn't the actual fix.

        Also unconditionally cancels/joins any pending _bindPeekHubsDeferred() timer (see
        _bindAllHubSlots()'s defer_peek param) before the _hubSliding check below - that check is
        specific to the slide-animation thread, but this method is also every caller's (including
        switchTab()/openSection()) one chokepoint for "about to touch or tear down these controls
        from another thread, make sure nothing else still can" - the peek-bind timer is exactly
        such a thing, whether or not a slide happens to be in flight at the same moment.
        """
        timer = self._hubPeekBindTimer
        if timer is not None:
            timer.cancel()
            self._hubPeekBindTimer = None
            timer.join(1.0)

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


class PostersSmallWindow(PostersWindow):
    xmlFile = 'script-plex-posters-small.xml'
    VIEWTYPE = 'panel2'
    MULTI_WINDOW_ID = 1
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


# 'panel3'/'panel4' (PostersCompactWindow/PostersSmallCompactWindow) were dropped here. A stored
# viewtype.<uuid>.<section> setting naming either one needs no migration: .get() returns None for
# an unknown key and MultiWindow.setDefault() (kodigui.py) is `self._next = default or
# self._windows[0]`, so anyone parked on a compact view lands on the plain poster grid and
# overwrites the stale string on their next view-cycle.
VIEWS_POSTER = {
    'panel': PostersWindow,
    'panel2': PostersSmallWindow,
    'list': ListView16x9Window,
    'all': (PostersWindow, PostersSmallWindow, ListView16x9Window)
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
