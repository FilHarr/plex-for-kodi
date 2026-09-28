from __future__ import absolute_import

import os
import random
import time

import plexnet
import six
import six.moves.urllib.parse
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
from lib import util
from lib import shuffle
from lib.util import T
from . import busy
from . import collection
from . import dropdown
from . import kodigui
from . import opener
from . import videoplayer
from . import optionsdialog
from . import preplay
from . import subitems
from .mixins.watchlist import removeFromWatchlistBlind


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


def getQueryItemType(section, item_type, fallback_to_section_type=False, force_include_collections=False):
    base_type = item_type

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


# Roughly a screenful of grid items: the first chunk's timing line says when this many were written.
CHUNK_SCREENFUL = 30


class ChunkRequestTask(backgroundthread.Task):
    def setup(self, section, start, size, callback, filter_=None, sort=None, subDir=False, bool_filters=None,
              item_type=None):
        self.section = section
        # Passed in, not read from the window: this runs on a worker (3e in the navigation review).
        self.itemType = item_type
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
            type_ = getQueryItemType(self.section, self.itemType)

            if self.itemType == 'folder':
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


class GridMixin(object):
    """LibraryWindow's library grid: filling it in chunks, the key list, the sort, filter, view and
    item-type buttons, item options and shuffle. A mixin rather than an object of its own because it
    reads the host's state throughout (L6 in the navigation review). LibraryWindow lists it first in
    its bases, so its methods still come before its other bases' (CommonMixin.toggleWatched)."""

    # ------------------------------------------------------------------------------------------
    # Input: the grid views' own handlers (PostersWindow's viewAction(), viewClick(), viewFocus()
    # and handleBack()), each called after the host's shared routing (kodigui.MultiWindowView).

    def gridAction(self, action):
        """The grid view's own actions, from the host's routeAction() after its shared steps:
        chunk requests, the background and the key list as the cursor moves, the context menu,
        the watched toggle, and Back to the first row. True when the action was used; False lets
        the host's Back and Home handling and then Kodi's own have it."""
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
        elif action == xbmcgui.ACTION_CONTEXT_MENU:
            # item action possible?
            had_action = self.itemOptions()
            if not had_action:
                if not xbmc.getCondVisibility('ControlGroup({0}).HasFocus(0)'.format(self.OPTIONS_GROUP_ID)):
                    self.lastNonOptionsFocusID = self.lastFocusID
                    self.setFocusId(self.OPTIONS_GROUP_ID)
                    return True
                else:
                    if self.lastNonOptionsFocusID:
                        self.setFocusId(self.lastNonOptionsFocusID)
                        self.lastNonOptionsFocusID = None
                        return True
            else:
                return True
        elif self.isWatchedAction(action):
            mli = self.showPanelControl.getSelectedItem()
            if not mli or not mli.dataSource:
                return True
            self.toggleWatched(mli)
            return True

        elif action in (xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_CONTEXT_MENU):
            if not xbmc.getCondVisibility('ControlGroup({0}).HasFocus(0)'.format(self.OPTIONS_GROUP_ID)) and \
                    (not util.addonSettings.fastBack or action == xbmcgui.ACTION_CONTEXT_MENU):
                if xbmc.getCondVisibility('Integer.IsGreater(Container(101).ListItem.Property(index),5)'):
                    self.showPanelControl.selectItem(0)
                    return True

        self.updateItem()
        return False

    def gridClick(self, controlID):
        """The grid view's own clicks: every click the host's routeClick() didn't use."""
        if controlID == self.TAB_LIST_ID:
            self.tabListClicked()
        elif controlID == self.POSTERS_PANEL_ID:
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

    def gridFocus(self, controlID):
        """The grid view's own focus handling: every focus event the host's routeFocus() didn't
        drop."""
        self.recordFocus(controlID)
        if controlID == self.KEY_LIST_ID:
            self.selectKey()

    def gridBack(self):
        """The grid view's own Back step (its handleBack()), which the host runs before it pops
        the chain: Back while scrolled down the grid snaps to item 0 first, and only once already
        on item 0 does Back mean leaving. Before the chain pops, so it applies mid-chain too, e.g.
        in a collection's grid reached via swapToSection() with a non-empty _backStack."""
        if self.getFocusId() != self.POSTERS_PANEL_ID:
            return False
        mli = self.showPanelControl.getSelectedItem() if self.showPanelControl else None
        if mli and mli.pos():
            self.showPanelControl.selectItem(0)
            return True
        return False

    def onItemChanged(self, mli):
        if not mli:
            return

        if not mli.dataSource or not mli.dataSource.TYPE == 'photo':
            return

        self.showPhotoItemProperties(mli.dataSource)

    def toggleWatched(self, mli, state=None, **kw):
        item = mli.dataSource
        wl_ref = item.show() if item.TYPE in ('episode', 'season') else item
        watched = super(GridMixin, self).toggleWatched(item)
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
        self.processCommand(videoplayer.play(play_queue=pl, context=self))

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
        self.processCommand(videoplayer.play(play_queue=pl, context=self))

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
            # force: the section's start, as a sidebar click - it's usually the section showing.
            self.goHome(self.section.getLibrarySectionId(), force=True)

    def itemTypeButtonClicked(self):
        # Button stays visible on the Collections tab (its own visibility only checks
        # section.TYPE, not ITEM_TYPE), but none of the branches below ever offer a
        # 'collection' option to select - same no-op-click treatment 'playlists' already
        # gets further down for a type with no dropdown options at all.
        if self.itemType == 'collection':
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
        if choice == self.itemType:
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
            self.setProperty('media.type', TYPE_PLURAL.get(self.itemType or self.section.TYPE, self.section.TYPE))
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
            if self.itemType == 'collection':
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
            if self.itemType == 'episode':
                searchTypes = ['titleSort', 'show.titleSort', 'addedAt', 'originallyAvailableAt', 'lastViewedAt',
                               'rating', 'audienceRating', 'userRating', 'mediaBitrate', 'random']
            elif self.itemType == 'collection':
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
            if self.itemType == 'album':
                searchTypes = ['titleSort', 'artist.titleSort', 'addedAt', 'lastViewedAt', 'viewCount',
                               'originallyAvailableAt', 'rating', 'random']
            elif self.itemType == 'collection':
                searchTypes = ['titleSort', 'addedAt']
            elif self.itemType == 'track':
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

        # Remember the panel generation before the photo viewer (still a blocking, standalone
        # open) runs. If the panel gets rebuilt while it's up, `mli` below is backed by a freed
        # ListItem and must not be touched - doing so hard-crashes Kodi (SIGSEGV in
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
            if self.itemType == 'episode' or mli.dataSource.TYPE == 'episode' or mli.dataSource.TYPE == 'season':
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
        elif self.section.TYPE == 'artist' or mli.dataSource.TYPE == 'artist' or mli.dataSource.TYPE == 'album' or mli.dataSource.TYPE == 'track':
            if self.itemType == 'album' or mli.dataSource.TYPE == 'album' or mli.dataSource.TYPE == 'track':
                self.openItem(mli.dataSource, entry_section_id=self.entrySectionId)
            else:
                # hashed-orbiting-pizza.md Phase 4 item 3: self.openWindow(), not
                # opener.handleOpen() directly - same reasoning as the PrePlayWindow branch above.
                self.openWindow(subitems.ArtistWindow, media_item=mli.dataSource, parent_list=self.showPanelControl,
                                 entry_section_id=self.entrySectionId, entry_from_watchlist=self.entryFromWatchlist)
        elif self.section.TYPE in ('photo', 'photodirectory'):
            self.showPhoto(mli.dataSource)
            # Every other branch only posts a swap (openWindow()), so there's nothing to refresh
            # after them: the watched/progress refresh and existence check that used to follow
            # were for opens that blocked until the child closed, and held up each open by two
            # server round trips (I2 in the navigation review). Back rebuilds the grid anyway.
            # A photo still opens the blocking viewer.
            if self._closeSignalled or self._listGeneration != listGeneration:
                return
            if mli.dataSource and not mli.dataSource.exists():
                self.showPanelControl.removeItem(mli.pos())
        elif self.section.TYPE == 'playlists':
            # Mirrors the 'collection' branch above - opener.open()'s playlist-TYPE branch now
            # swaps in place via context=self, same as every other migrated shell.
            self.processCommand(opener.open(mli.dataSource, context=self))

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


    def _placeholderItems(self, start, count, key=None):
        """Empty grid items for positions start..start+count-1, which the chunk fetches fill in.
        Three GUI calls each (the thumb fallback, index and, for a title sort, the letter key):
        every Python ListItem call takes Kodi's GUI lock."""
        fallback = self.thumb_fallback
        items = []
        for x in range(start, start + count):
            mli = kodigui.ManagedListItem('')
            mli.setProperty('thumb.fallback', fallback)
            mli.setProperty('index', str(x))
            if key:
                mli.setProperty('key', key)
            items.append(mli)
        return items

    @property
    def thumb_fallback(self):
        return 'script.plex/thumb_fallbacks/{0}.png'.format(TYPE_KEYS.get(self.section.type, TYPE_KEYS['movie'])['fallback'])

    @busy.dialog()
    def fillShows(self, keep_focus=False):
        if self.__dict__.get('_gridTiming') is not None:
            # part of a grid open's own timing line (onFirstInit())
            self._fillShows(keep_focus)
            return
        # A sort, filter or item-type change refilling the grid in place gets a line of its own.
        timing = self._gridTiming = kodigui.StepTiming('Grid refill')
        try:
            self._fillShows(keep_focus)
        finally:
            self._gridTiming = None
        timing.log()

    def _fillShows(self, keep_focus=False):
        # A sort, filter or item-type change refills the grid in place without a swap, so chunks
        # still in flight from the previous fill have to be marked stale here too.
        self._retireListItems()
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

        type_ = getQueryItemType(self.section, self.itemType)
        # supplying this type kills all results (bug: 2025/10/21)
        if type_ == plexobjects.SEARCHTYPES["photo"]:
            type_ = None

        # Built here, on this thread, in one go. They used to be built on workers while this
        # thread waited, polling: the GUI lock serialised the workers anyway, and each poll handed
        # queued clicks to Python, so a sort-menu click ran inside the refill it was about to
        # replace (live-caught on the AM6B, 2026-09-26: a refill stuck for 52 s behind the menu).
        placeholders = []

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
        if isAlphaSort(self.sort) and self.itemType != 'folder' \
                and (self.itemType != 'episode' or self.sort == 'show.titleSort') \
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
            # Not for episodes either: a collection holds shows, never episodes, and with "4,18"
            # the server counted shows instead - 159 index entries against 7000+ episodes on the
            # AM6B, so the grid got 159 placeholders and the first chunk ran off the end.
            if self.section.TYPE != 'artist' and collection_mode == 2 and self.itemType != 'episode' \
                    and not (self.filter or self.boolFilters.get('unwatched')):
                jl_type = getQueryItemType(self.section, self.itemType, fallback_to_section_type=True,
                                           force_include_collections=True)

            jumpList = self.section.jumpList(filter_=self.getFilterOpts(), sort=self.getSortOpts(),
                                             type_=jl_type, bool_filters=bool_filters)
            kodigui.markStep(self.__dict__.get('_gridTiming'), 'jump list')
            if jumpList is None:
                # Endpoint doesn't support this sort/type combo (or errored) - fall back to
                # a regular fetch below rather than reporting the section as empty.
                util.DEBUG_LOG('jumpList() unavailable for sort {0}/type {1}, falling back to all()',
                               self.sort, self.itemType)

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

                keyed = self._placeholderItems(idx, ji_size, key=ji.key)
                if keyed:
                    self.firstOfKeyItems[ji.key] = keyed[0]
                placeholders += keyed
                idx += ji_size

            util.DEBUG_LOG('JumpList item size: {}', totalSize)

            util.setGlobalProperty('key', jumpList[0].key)
        else:
            if self.itemType == 'folder':
                sectionAll = self.section.folder(0, 0, self.subDir)
            else:
                sectionAll = self.section.all(0, 0, filter_=self.getFilterOpts(), sort=self.getSortOpts(),
                                              type_=type_, bool_filters=bool_filters)

            totalSize = sectionAll.totalSize.asInt()
            kodigui.markStep(self.__dict__.get('_gridTiming'), 'count')

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
                placeholders = self._placeholderItems(0, totalSize)

        self.setProperty("items.count", str(totalSize))

        self.showPanelControl.reset()
        self.keyListControl.reset()
        self.showPanelControl.addItems(placeholders)
        timing = self.__dict__.get('_gridTiming')
        if timing is not None:
            timing.mark('placeholders')
            timing.add('items', totalSize)
            timing.add('keys', len(jitems))
            # for the first chunk's own timing line (_chunkCallbackFor()): a grid open counts from
            # the navigation request, a refill from its own start
            requested = self.__dict__.get('_lastSwapStarted') if timing.name == 'Grid open' else timing.started
            self._firstChunkTiming = (self._listGeneration, time.time(), requested)

        if jitems:
            self.keyListControl.addItems(jitems)
        kodigui.markStep(timing, 'key list')

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
                    filter_=self.getFilterOpts(), sort=self.getSortOpts(), subDir=self.subDir, bool_filters=bool_filters,
                    item_type=self.itemType
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
        kodigui.markStep(timing, 'select + queue chunks')

        if restorePos:
            # Real art/metadata only exists for whichever chunk(s) have actually been fetched -
            # by default (retrieveAllMediaUpFront off) only chunk 0 is requested up front, above;
            # real chunks are otherwise only ever requested by MOVE_SET arrow-key navigation
            # (routeAction()) or keyClicked()'s identical jump-and-request pattern, which this
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
        fillPlaylists() so the same per-item treatment can also run on focus-move (gridAction()'s
        MOVE_SET handling above), not just once at fill time. Needed at all because playlists
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
                    if pl.playlistType == self.itemType]

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
            firstChunk = self.__dict__.get('_firstChunkTiming')
            if not firstChunk or firstChunk[0] != generation:
                self._chunkCallback(items, start, generation)
                return
            self._firstChunkTiming = None
            marks = self._firstChunkMarks = {}
            started = time.time()
            try:
                self._chunkCallback(items, start, generation)
            finally:
                self._firstChunkMarks = None
            requested = firstChunk[2]

            def since(key):
                return int((marks[key] - started) * 1000) if key in marks else '-'
            util.DEBUG_LOG("Library: first chunk ({0} items) bound in {1} ms (background {2}, first {3} items {4}),"
                           " {5} ms after the placeholders, {6} ms after the request", len(items),
                           int((time.time() - started) * 1000), since('background'), CHUNK_SCREENFUL,
                           since('screenful'), int((started - firstChunk[1]) * 1000),
                           int((time.time() - requested) * 1000) if requested else '?')
        return callback

    def _chunkCallback(self, items, start, generation=None):
        if not self.showPanelControl or not items or self.closing:
            return

        with self.lock:
            # Checked here and before every item, under the lock (see _retireListItems()).
            if generation is not None and generation != self._listGeneration:
                util.DEBUG_LOG("Library: _chunkCallback() declined - stale generation ({0} != {1})",
                               generation, self._listGeneration)
                return

            pos = start
            self.setBackground(items, pos, randomize=not util.addonSettings.dynamicBackgrounds)
            # the first chunk's timing line (_chunkCallbackFor())
            marks = self.__dict__.get('_firstChunkMarks')
            if marks is not None:
                marks['background'] = time.time()

            thumbDim = TYPE_KEYS.get(self.section.type, TYPE_KEYS['movie'])['thumb_dim']
            artDim = TYPE_KEYS.get(self.section.type, TYPE_KEYS['movie']).get('art_dim', (256, 256))

            if not self.showPanelControl:
                return

            if self.itemType == 'episode':
                for offset, obj in enumerate(items):
                    if generation is not None and generation != self._listGeneration:
                        util.DEBUG_LOG("Library: _chunkCallback() stopped - the list moved on")
                        return
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
                    if marks is not None and pos - start == CHUNK_SCREENFUL:
                        marks['screenful'] = time.time()

            elif self.itemType == 'album':
                for offset, obj in enumerate(items):
                    if generation is not None and generation != self._listGeneration:
                        util.DEBUG_LOG("Library: _chunkCallback() stopped - the list moved on")
                        return
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
                    if marks is not None and pos - start == CHUNK_SCREENFUL:
                        marks['screenful'] = time.time()
            else:
                for offset, obj in enumerate(items):
                    if generation is not None and generation != self._listGeneration:
                        util.DEBUG_LOG("Library: _chunkCallback() stopped - the list moved on")
                        return

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
                    if marks is not None and pos - start == CHUNK_SCREENFUL:
                        marks['screenful'] = time.time()

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
                                            sort=self.getSortOpts(), subDir=self.subDir, bool_filters=self.boolFilters,
                                            item_type=self.itemType)

            self.tasks.add(task)
            backgroundthread.BGThreader.addTasksToFront([task])
