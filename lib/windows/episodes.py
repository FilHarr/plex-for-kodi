from __future__ import absolute_import

import requests.exceptions
import copy
import json
import threading
import time
from kodi_six import xbmc
from kodi_six import xbmcgui
from collections import OrderedDict

from plexnet import plexapp, playlist, plexplayer, util as pnUtil, plexobjects

from lib import backgroundthread
from lib import metadata
from lib import player
from lib import util
from lib.util import T
from lib.language_util import getNativeLanguages
from . import busy
from . import dropdown
from . import home
from . import info
from . import kodigui
from . import opener
from . import optionsdialog
from . import pagination
from . import playbacksettings
from . import playersettings
from . import search
from . import videoplayer
from . import windowutils
from .mixins.seasons import SeasonsMixin
from .mixins.spoilers import SpoilersMixin
from .mixins.media_info_pills import MediaInfoPillsMixin
from .mixins.playbackbtn import PlaybackBtnMixin
from .mixins.thememusic import ThemeMusicMixin
from .mixins.watchlist import WatchlistUtilsMixin, removeFromWatchlistBlind
from .mixins.ratings import RatingsMixin
from .mixins.roles import RolesMixin
from .mixins.common import CommonMixin
from .mixins.tasks import TasksMixin
from .mixins.text_metrics import FONT10_POINT_SIZE, measureTextWidth

VIDEO_RELOAD_KW = dict(includeExtras=1, includeExtrasCount=10, includeChapters=1)


class EpisodesReloadTask(backgroundthread.Task):
    def setup(self, episodes, callback, set_item_info=False):
        self.episodes = episodes
        self.callback = callback
        self.setItemInfo = set_item_info
        return self

    def run(self):
        if self.isCanceled():
            return

        if not plexapp.SERVERMANAGER.selectedServer:
            # Could happen during sign-out for instance
            return

        epLen = len(self.episodes)
        if not epLen:
            return

        try:
            if epLen == 1:
                ep, prog = self.episodes[0]
                ep.reload(checkFiles=1, includeChapters=1, fromMediaChoice=ep.mediaChoice is not None)
            elif epLen > 1:
                # fetch data for all episodes in one go
                epMap = {str(ep.ratingKey): ep for ep, _ in self.episodes}
                data = plexobjects.listItems(self.episodes[0][0].server, '/library/metadata/{0}'.format(",".join(list(e.ratingKey for e, _ in self.episodes))), return_data=True,
                                             checkFiles=1, includeChapters=1, includeMarkers=1)
                rl_cnt = 0
                for d in data:
                    ep = epMap.get(d.attrib.get("ratingKey"), None)
                    if ep:
                        ep.reload(checkFiles=1, includeChapters=1, fromMediaChoice=ep.mediaChoice is not None, data=d)
                        rl_cnt += 1
                util.DEBUG_LOG("EpisodesReloadTask: Reloaded data for {}/{} items", rl_cnt, len(self.episodes))
            else:
                return

            if self.isCanceled():
                return
            self.callback(self, self.episodes, set_item_info=self.setItemInfo)
        except (requests.exceptions.RequestException, IndexError):
            raise util.NoDataException
        except:
            util.ERROR()


class EpisodesPaginator(pagination.MCLPaginator):
    """
    Append-only in both directions, matching how Related/Collection Hub rows (BaseRelatedPaginator)
    never discard or re-fetch anything already loaded - but unlike those rows, Episodes' initial page
    starts mid-season (centered on the current episode via initialPage below), not always at offset
    0, so growth has to be able to happen at either end of the loaded window rather than only the
    right. self.offset tracks the left edge (index of the first loaded episode, same meaning it
    always had), self._rightOffset is the new addition tracking the index one-past the last loaded
    episode. Neither edge is ever rewound or re-sliced once fetched - only ever extended further out.
    """
    thumbFallback = 'script.plex/thumb_fallbacks/show.png'
    _currentEpisode = None
    _rightOffset = 0
    _seasonCardInserted = False
    # Time spent in getData() and setItemInfo(), for fillEpisodes()'s Screen timing line.
    fetchMs = 0
    itemInfoMs = 0
    # the same, in this thread's own CPU time: the gap to the wall time above is waiting (for
    # Kodi's GUI lock, mostly), not work
    itemInfoCpuMs = 0

    def reset(self):
        super(EpisodesPaginator, self).reset()
        self._currentEpisode = None
        self._rightOffset = 0
        self._seasonCardInserted = False

    def wrap(self, mli, last_mli, action):
        # Episodes don't round-robin: the sidebar rail now occupies the left edge, so looping
        # back to the last episode when pressing left past the first (or vice versa) would fight
        # with escaping into the rail. The skin's onleft/onright on control 400 already provide a
        # hard stop on the right and hand off to the sidebar (id 9000) once truly at the first
        # episode - see that control's own onleft comment in script-plex-episodes.xml.tpl.
        return None

    def getData(self, offset, amount):
        started = time.time()
        try:
            return (self.parentWindow.season or self.parentWindow.show_).episodes(offset=offset, limit=amount)
        finally:
            self.fetchMs += (time.time() - started) * 1000

    def createListItem(self, data):
        mli = super(EpisodesPaginator, self).createListItem(data)
        started, cpuStarted = time.time(), time.thread_time()
        self.parentWindow.setItemInfo(data, mli)
        self.itemInfoMs += (time.time() - started) * 1000
        self.itemInfoCpuMs += (time.thread_time() - cpuStarted) * 1000
        return mli

    def prepareListItem(self, data, mli):
        mli.setBoolProperty('watched', mli.dataSource.isPlayed)
        if not mli.dataSource.isWatched:
            mli.setProperty('unwatched.count', str(mli.dataSource.unViewedLeafCount))
            mli.setBoolProperty('unwatched.count.large', mli.dataSource.unViewedLeafCount.asInt() > 999)
            mli.setProperty('unwatched', '1')
        mli.setProperty('progress', util.getProgressImage(mli.dataSource))

    def setEpisode(self, ep):
        self._currentEpisode = ep

    @property
    def initialPage(self):
        episode = self.parentWindow.episode
        offset = 0
        amount = self.initialPageSize
        if episode:
            self.setEpisode(episode)
            # try cutting the query short while not querying all episodes, to find the slice with the currently
            # selected episode in it
            episodes = []
            _amount = self.initialPageSize + self.orphans
            epSeasonIndex = int(episode.index or 1) - 1  # .index is 1-based
            if _amount < self.leafCount:
                _amount = self.initialPageSize * 2
                notFound = False
                while episode not in episodes:
                    offset = int(max(0, epSeasonIndex - _amount / 2))
                    episodes = self.getData(offset, int(_amount))

                    if _amount >= self.leafCount:
                        # ep not found?
                        notFound = True
                        break

                    # in case the episode wasn't found inside the slice, increase the slice's size
                    _amount *= 2

                if notFound:
                    # search conservatively
                    util.DEBUG_LOG("Episode not found with intelligent index-based search, re-trying conservatively")
                    _amount = self.initialPageSize * 2
                    offset = 0
                    episodes = self.getData(offset, int(_amount))
                    while episode not in episodes:
                        offset = _amount
                        episodes = self.getData(offset, int(_amount))

                        if _amount >= self.leafCount:
                            break

                        _amount *= 2
            else:
                # shortcut for short seasons
                episodes = self.getData(offset, int(_amount))

        else:
            episodes = super(EpisodesPaginator, self).initialPage
            # base class already set self.offset/self._currentAmount for this fallback (no current
            # episode to center on) - mirror the right edge from those.
            self._rightOffset = self.offset + self._currentAmount
            return episodes

        episodeFound = episode and episode in episodes
        if episodeFound:
            if self.initialPageSize + self.orphans < self.leafCount:
                # slice around the episode
                # Clamp the left side dynamically based on the item index and how many items are left in the season.
                # The episodes list might be longer than our limit, because the season doesn't necessarily have all the
                # episodes in it and we're basing the initial load on the current episode's index, which is the actual
                # index of the episode in the season, not what's physically there. To find the episode, we're
                # dynamically increasing the window size above. Re-clamp to :amount:, adding slack to both sides if
                # the remaining episodes would fit inside half of :amount:.
                tmpEpIdx = episodes.index(episode)
                leftBoundary = self.initialPageSize - len(episodes[tmpEpIdx:tmpEpIdx + self.orphans])

                left = max(tmpEpIdx - leftBoundary, 0)
                offset += left
                epsLeft = self.leafCount - offset
                # avoid short pages on the right end
                if epsLeft <= self.initialPageSize + self.orphans:
                    amount = epsLeft

                # avoid short pages on the left end
                if offset < self.orphans and amount + offset < self.initialPageSize + self.orphans:
                    amount += offset
                    left = 0
                    offset = 0

                episodes = episodes[left:left + amount]

        self.offset = offset
        self._currentAmount = len(episodes)
        self._rightOffset = offset + len(episodes)

        return episodes

    def selectItem(self, amount, more_left=False, more_right=False, items=None):
        # Only ever reached for the initial page (self._direction is None there) - boundary-triggered
        # pages handle their own selection directly in populate() below, without going through this.
        if not super(EpisodesPaginator, self).selectItem(amount, more_left):
            if (self._currentEpisode and items) and self._currentEpisode in items:
                self.control.selectItem(items.index(self._currentEpisode) + (1 if more_left else 0))

    @property
    def boundaryHit(self):
        # Same trigger condition as the base class (currently-selected item is an unclaimed boundary
        # marker), but doesn't reuse its self.offset = orig.index assignment: that would clobber
        # self.offset's meaning here (the left edge) whenever a RIGHT marker is hit, since the base
        # class only has one offset variable for both directions. This paginator already tracks both
        # edges itself (self.offset/self._rightOffset, kept live and accurate as items load), so
        # there's nothing to recover from the marker at all - it only needs a direction.
        self._boundaryHit = False

        if not self._readyForPaging:
            return self._boundaryHit

        mli = self.control.getSelectedItem()
        if mli and mli.getProperty("is.boundary") and not mli.getProperty("is.updating") and \
                not mli.getProperty("is.season.card"):
            mli.setBoolProperty("is.updating", True)
            self._direction = "left" if mli.getProperty("left.boundary") else "right"
            self._boundaryHit = True

        return self._boundaryHit

    @property
    def nextPage(self):
        # Append-only in both directions - see this class's own docstring. Whichever edge the
        # boundary marker that triggered this sits on is the one that grows; the other edge, and
        # everything already loaded, is untouched.
        if self._direction == "left":
            newOffset = max(0, self.offset - self.pageSize)
            amount = self.offset - newOffset
            data = self.getData(newOffset, amount)
            self.offset = newOffset
        else:
            amount = self.pageSize
            itemsLeft = self.leafCount - self._rightOffset
            if itemsLeft <= self.pageSize + self.orphans:
                amount = itemsLeft
            data = self.getData(self._rightOffset, amount)
            self._rightOffset += len(data)

        self._lastAmount = self._currentAmount
        self._currentAmount += len(data)
        return data

    def populate(self, items):
        if self._direction is None:
            # Initial page: identical shape to the base class's own population (both markers as
            # needed, selection handled by selectItem() above via self._currentEpisode) - nothing to
            # append/prepend around yet since this is the first thing loaded.
            finalItems = super(EpisodesPaginator, self).populate(items)
            # Short seasons (or landing near the very start) can already have self.offset == 0 on
            # this very first load, with no "left" pagination step ever happening to reach the
            # season-card insertion point below - same prependItems() re-selection guarantee applies
            # here as there (see that branch's own comment).
            if self.offset == 0 and not self._seasonCardInserted:
                self._seasonCardInserted = True
                self.control.prependItems([self.parentWindow.createSeasonCardItem()])
                if not self._currentEpisode:
                    # No specific episode was ever selected above (self._currentEpisode only gets
                    # set when parentWindow.episode was truthy going in - see initialPage/setEpisode)
                    # - EpisodesWindow._defaultEpisode() found nothing in-progress and nothing
                    # watched at all in this season, on request: land on the season card itself
                    # rather than letting prependItems()'s own "preserve whatever was already
                    # selected" carry the list's own default (position 0 before this prepend, i.e.
                    # episode 1) forward to position 1.
                    self.control.setSelectedItemByPos(0)
                    # setSelectedItemByPos() -> the native control's own selectItem() doesn't
                    # necessarily take effect by the time this call returns (same lag
                    # selectEpisode()'s own identical poll below works around) - postSetup()'s
                    # checkForHeaderFocus(initial=True) call and _setup()'s postponed
                    # fillExtras()/fillRoles() both read getSelectedItem() moments after this
                    # returns, on the very same call stack with no yield in between, so without
                    # settling here first they were live-confirmed to still see episode 1 (the
                    # list's pre-prepend default) and fill Roles/Extras for that instead of the
                    # season card - only correcting once the user moved off and back and gave the
                    # control a chance to catch up on its own.
                    tries = 0
                    while self.control.getSelectedPos() != 0 and tries < util.MONITOR.waitAmount(4, interval=0.05):
                        kodigui.sleepForGui(0.05)
                        self.control.setSelectedItemByPos(0)
                        tries += 1
            return finalItems

        if not items:
            return []

        thumbFallback = self.thumbFallback
        finalItems = []
        for item in items:
            mli = self.createListItem(item)
            if not mli:
                continue

            self.prepareListItem(item, mli)
            if thumbFallback:
                if callable(thumbFallback):
                    mli.setProperty('thumb.fallback', thumbFallback(item))
                else:
                    mli.setProperty('thumb.fallback', thumbFallback)

            finalItems.append(mli)

        if self._direction == "left":
            # Drop the marker that triggered this before prepending the new items in its place -
            # nothing already shown is ever removed, only the marker itself.
            self.control.removeItem(0)

            moreLeft = self.offset > 0
            if moreLeft:
                start = kodigui.ManagedListItem('')
                start.setBoolProperty('is.boundary', True)
                start.setBoolProperty('left.boundary', True)
                start.setProperty('orig.index', str(self.offset))
                finalItems.insert(0, start)
            elif not self._seasonCardInserted:
                # True start of the season finally reached (no more marker needed) - pin the season
                # card ahead of episode 1, permanently: nothing ever triggers another "left" pass
                # after this (moreLeft stays False forever once self.offset hits 0), so this is the
                # only place this ever needs to run.
                self._seasonCardInserted = True
                finalItems.insert(0, self.parentWindow.createSeasonCardItem())

            self.control.prependItems(finalItems)
            # Land on the newly-revealed item closest to where the marker was (the last of the
            # newly-prepended batch), continuing in the same direction the user was already moving.
            self.control.setSelectedItemByPos(len(finalItems) - 1)
        else:
            self.control.removeItem(self.control.size() - 1)

            moreRight = self._rightOffset < self.leafCount
            selectPos = self.control.size()
            # addItems (unlike prependItems) doesn't renumber anything via _updateItems, so this
            # batch's own 'index' has to be set explicitly - selectPos is exactly the first real
            # item's own absolute position, since it's read right after removing the old marker and
            # before adding anything new.
            idx = selectPos
            for mli in finalItems:
                mli.setProperty('index', str(idx))
                idx += 1

            if moreRight:
                end = kodigui.ManagedListItem('')
                end.setBoolProperty('is.boundary', True)
                end.setBoolProperty('right.boundary', True)
                end.setProperty('orig.index', str(self._rightOffset))
                finalItems.append(end)

            self.control.addItems(finalItems)
            self.control.setSelectedItemByPos(selectPos)

        return finalItems


class RedirectToEpisode(Exception):
    episode = None
    season = None
    select_episode = True

    def __init__(self, episode, season=None, select_episode=True):
        self.episode = episode
        self.season = season
        self.select_episode = select_episode


def close_safe(func):
    def inner(obj, *args, **kwargs):
        try:
            return func(obj, *args, **kwargs)
        except:
            if obj.closing:
                return
            raise
    return inner


# selectItem() only queues the change for Kodi's GUI thread, so selectEpisode() polls until it has
# landed: this often, not every 50 ms, so it's seen within about a frame (step 4 in the navigation
# review - the 50 ms steps and a fixed 50 ms wait after them were most of the ~165 ms selectEpisode()
# took per Episodes open on the AM6B). They sleep (kodigui.sleepForGui()) rather than wait, so a click
# queued meanwhile can't run in the middle of the selection (F6).
SELECT_POLL_SECONDS = 0.01

VIDEO_PROGRESS = OrderedDict()

class EpisodesWindow(kodigui.ControlledWindow, windowutils.UtilMixin, windowutils.SidebarMixin, SeasonsMixin,
                     RatingsMixin, SpoilersMixin, MediaInfoPillsMixin, RolesMixin, PlaybackBtnMixin,
                     ThemeMusicMixin, WatchlistUtilsMixin, CommonMixin, TasksMixin,
                     playbacksettings.PlaybackSettingsMixin):
    xmlFile = 'script-plex-episodes.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    supportsAutoPlay = True
    dismissOnClose = True

    THUMB_AR16X9_DIM = util.scaleResolution(657, 393)
    POSTER_DIM = util.scaleResolution(420, 630)
    # 533x300 = 512x288 display size (script-plex-episodes.xml.tpl's extras row) * 104%, the row's own
    # focus-zoom end value - matches ShowWindow's/PrePlayWindow's own EXTRA_DIM exactly (subitems.py,
    # preplay.py), now that this row's art was resized to match theirs. The old 329x185 matched the old
    # 299x168 art this row used before that resize.
    EXTRA_DIM = util.scaleResolution(533, 300)
    ROLES_DIM = util.scaleResolution(334, 334)
    # 660x98, not the old 784x106: matches Recommended's own episode-variant clearlogo box exactly
    # (CLEAR_LOGO_DIM_EPISODE, library.py), now that the header was resized to match it
    # (script-plex-episodes.xml.tpl).
    CLEAR_LOGO_DIM = util.scaleResolution(660, 98)

    EPISODE_LIST_ID = 400
    SEASONS_LIST_ID = 205
    ROLES_LIST_ID = 402
    EXTRA_LIST_ID = 403

    OPTIONS_GROUP_ID = 200
    PLAYER_STATUS_BUTTON_ID = 204

    MAIN_BUTTON_GROUP_ID = 300
    PLAY_BUTTON_ID = 301
    PLAY_BUTTON_DISABLED_ID = 306
    SHUFFLE_BUTTON_ID = 302
    OPTIONS_BUTTON_ID = 303
    INFO_BUTTON_ID = 304
    SETTINGS_BUTTON_ID = 305
    RESUME_BUTTON_ID = 308
    RESTART_BUTTON_ID = 309
    # The season card's own Play/Resume focus-pill overlays (script-plex-episodes.xml.tpl) and the
    # pill/label inside each - the only two overlays on this screen whose text isn't fixed at build
    # time, since they name the episode the card is about. sizeSeasonCardPlayLabel() resizes all
    # three ids of whichever one is live. 384-387, not the 390s the other overlays use: those are
    # full, and 398/399 were the only ids left there.
    SEASON_CARD_PLAY_LABEL_GROUP_ID = 398
    SEASON_CARD_PLAY_LABEL_PILL_ID = 384
    SEASON_CARD_PLAY_LABEL_TEXT_ID = 385
    SEASON_CARD_RESUME_LABEL_GROUP_ID = 399
    SEASON_CARD_RESUME_LABEL_PILL_ID = 386
    SEASON_CARD_RESUME_LABEL_TEXT_ID = 387
    # Click/focus target laid over the summary textbox (script-plex-episodes.xml.tpl) - 350, not
    # something in the 300-309 button cluster (all already taken here, unlike Seasons'/Artist's own
    # copy of this control, which reuses 305 since neither of them has a button at that id any
    # more) or 310-322 (includes/media_info_pills.xml.tpl's own ids, also live in this window -
    # 310 specifically collided with that include's video-pill background image, live-reported as
    # "the background does not extend the full length of the label": Control.setWidth() calls
    # meant for that pill (MediaInfoPillsMixin.resizeMediaInfoPills()) were hitting this button
    # instead, since Kodi doesn't guarantee which same-id control a getControl() call resolves to).
    # Wired to summaryButtonClicked() below.
    SUMMARY_BUTTON_ID = 350

    SEASONS_CONTROL_ATTR = "seasonsListControl"

    # (season ratingKey, episode) - see _cacheSeasonCardPick(). Class-level default so the accessors
    # below don't depend on reset() having run first.
    _seasonCardPick = None

    def __init__(self, *args, **kwargs):
        kodigui.ControlledWindow.__init__(self, *args, **kwargs)
        windowutils.UtilMixin.__init__(self)
        SpoilersMixin.__init__(self, *args, **kwargs)
        PlaybackBtnMixin.__init__(self, *args, **kwargs)
        WatchlistUtilsMixin.__init__(self)
        TasksMixin.__init__(self)
        self.episode = None
        self.reset(kwargs.get('episode'), kwargs.get('season'), kwargs.get('show'))
        self.parentList = kwargs.get('parentList')
        self.cameFrom = kwargs.get('came_from')
        self.fromWatchlist = kwargs.get('from_watchlist')
        self.directlyFromWatchlist = kwargs.get('directly_from_watchlist')
        self.is_watchlisted = kwargs.get('is_watchlisted', False)
        self.startOver = kwargs.get('start_over')
        self.debouncing = False
        # Settled-focus debounce for the Roles/Extras rows (checkForHeaderFocus()/
        # scheduleRowDataUpdate()/_updateRowData() below). Extras aren't part of an episode's own
        # listing data (unlike Roles, already present on every episode from the season listing
        # fetch) - filling it requires a dedicated network fetch per episode (fillExtras() below),
        # so without this holding a direction key to scroll through the row would fire one request
        # per episode flown past instead of one for wherever focus actually settles.
        self.rowDataChangeTimeout = 0
        self.rowDataChangeThread = None
        # fillExtras() below can't trust ds.extras' own truthiness + PlexObject.__getattr__'s .NA
        # marker to mean "never fetched" - reloadItems()/EpisodesReloadTask (this file) reload
        # every paginated-in episode's dataSource for progress/media-choice/chapters without
        # includeExtras, which resets .extras to a real (non-NA) empty PlexVideoItemList almost
        # immediately, well before the debounce here ever gets a chance to fetch it. Tracking our
        # own fetch attempts by ratingKey here survives that clobbering.
        self._extrasFetched = set()

        # Sidebar entry-section persistence (ported from Sidebar-Tab-Unification's
        # mellow-pondering-magpie.md, 2026-08-18) - see preplay.py's PrePlayWindow.__init__ for the
        # full reasoning; identical shape here. Set once here, not in reset() - navigating between
        # episodes within this same window (reset() is called again for that) must not change
        # which sidebar section stays lit.
        self.entrySectionId = kwargs.get('entry_section_id')
        self.entryFromWatchlist = kwargs.get('entry_from_watchlist', False)
        if self.entrySectionId is None and not self.entryFromWatchlist:
            self.entrySectionId = self.show_.getLibrarySectionId()
            self.entryFromWatchlist = self.fromWatchlist or self.directlyFromWatchlist

        # hashed-orbiting-pizza.md Phase 2: None here means "build my own sectionList" (a
        # standalone/un-hosted open) - a hosted open (LibraryWindow._setupCurrent(), library.py)
        # overwrites this with the host's own sectionList object before onFirstInit() runs. Set
        # in __init__, not reset() below - reset() re-runs on every episode navigation within
        # this same window and must not force a rebuild each time.
        self.sectionList = None

    def reset(self, episode, season=None, show=None):
        timing = kodigui.StepTiming('Episodes reset')
        self.episode = episode
        self.initialEpisode = episode
        self.season = season if season is not None else self.episode.season()
        timing.mark('season')
        try:
            self.show_ = show or (self.episode or self.season).show().reload(includeExtras=1, includeExtrasCount=10,
                                                                             includeOnDeck=1)
        except IndexError:
            raise util.NoDataException
        timing.mark('show')

        # skipChildren (set on the Show, not the Season - the "Seasons" library option set to Hide for
        # single-season shows) is Plex's own signal that this show's single season shouldn't be treated
        # as a distinct level at all. A real Season object fetched via show.seasons() (subitems.py's
        # ShowWindow path) carries none of this - it looks like an ordinary season - so without this
        # override self.season ends up showing "Season 1"/no extras there, while the Continue Watching
        # path (which resolves self.season via Episode.season(), and that method already redirects to
        # the show itself when the episode's own skipParent is set) shows the show's own title/extras
        # instead. Forcing self.season to the show here makes both entry paths land on the same, correct
        # result: every self.season read throughout this window (title, extras, thumb, etc.) reflects
        # the show, since there's no meaningful season to show separately.
        if self.show_.get('skipChildren').asBool():
            self.season = self.show_

        # Cleared before _defaultEpisode() below, which seeds it (_cacheSeasonCardPick()) - a
        # navigation that passes an explicit episode skips that call entirely and would otherwise
        # keep whatever the previous subject left here.
        self._seasonCardPick = None

        if not self.episode:
            # Opened from a season tile (subitems.py) with no specific episode - EpisodesPaginator.
            # initialPage only knows how to center its window on self.episode; with nothing set it
            # just loads from the very start of the season (episode 1), stranding any unwatched/
            # in-progress episode further in outside that initial window entirely. See
            # _defaultEpisode()'s own comment for how the fallback episode is picked.
            # initialEpisode above deliberately keeps the real original value (None) - doAutoPlay()
            # treats it as "the episode we were explicitly asked to open with", which this auto-pick
            # isn't.
            self.episode = self._defaultEpisode()
        timing.mark('default episode')
        timing.log()

        self.initialized = False
        self.closing = False
        self.parentList = None
        self.episodesPaginator = None
        self.seasons = None
        self.manuallySelected = False
        self.manuallySelectedSeason = False
        self.hadUserInteraction = False
        self.currentItemLoaded = False
        self.lastItem = None
        self.lastFocusID = None
        self.openedWithAutoPlay = False
        self.useBGM = False
        self.debouncing = False
        self.rowDataChangeTimeout = 0
        PlaybackBtnMixin.reset(self)

    def _seasonPick(self):
        """This season's own "where were we" episode: (episode, in_progress, first episode).

        Best-effort only - both callers just want a nicer starting point than episode 1, neither is
        required for the screen to function, so any failure here falls back silently rather than
        surfacing an error.

        Not sourced from self.show_.onDeck - Plex's own on-deck pick is a whole-show "continue
        watching" heuristic, not necessarily this season's own first unwatched/in-progress episode,
        and live testing showed it doesn't reliably match what's expected here. (The Seasons screen
        does treat on-deck as authoritative - ShowWindow.onDeckPick(), subitems.py - precisely
        because that screen IS about the whole show. Same distinction, one level up.) Scans this
        season's own episodes directly instead. One full-season listing call (Season.episodes() with
        no offset/limit fetches everything), shared between both callers via _cacheSeasonCardPick()
        below rather than paid twice.

        An in-progress episode always wins, even one later in the season than the first plain
        unwatched one - someone mid-episode is more clearly "where they were" than an earlier
        episode they just haven't started yet, so the loop returns on the first in-progress hit
        immediately rather than waiting to see if an earlier unwatched one exists. isWatched and
        not isFullyWatched means "has real progress but hasn't crossed the watched threshold" -
        exactly viewOffset>0 (video.py's own isWatched/isFullyWatched checks viewCount OR
        viewOffset vs viewCount AND not viewOffset). Only once the whole season has been scanned
        with no in-progress episode found does the first plain-unwatched one (remembered along the
        way, not re-searched for) get returned instead.

        `first` is returned alongside for the season card's own Play button, which has to start
        somewhere even when the scan comes up empty - see seasonCardEpisode().
        """
        try:
            first = None
            firstUnwatched = None
            for ep in self.season.episodes():
                if first is None:
                    first = ep
                if ep.isWatched and not ep.isFullyWatched:
                    return ep, True, first
                if firstUnwatched is None and not ep.isWatched:
                    firstUnwatched = ep

            return firstUnwatched, False, first
        except:
            util.ERROR('EpisodesWindow._seasonPick: failed, falling back to episode 1')

        return None, False, None

    def _defaultEpisode(self):
        pick, in_progress, first = self._seasonPick()
        # The scan above is the same one the season card's own Play button needs, and this runs on
        # both paths that land on a new season (reset() and switchSeason()) - so hand it over rather
        # than making updateSeasonCardPlayState() repeat the listing call on every cold start.
        self._cacheSeasonCardPick(pick, first)

        # Nothing in-progress and nothing fully watched either (viewedLeafCount==0, the season's own
        # aggregate, not just "the first episode happens to be unwatched" - pick could just as easily
        # be an early episode in a season with real progress further in) - i.e. a genuinely untouched
        # season, on request: land on the season card itself (EpisodesPaginator.populate()'s own
        # self._currentEpisode check, driven by this returning None) instead of defaulting to
        # episode 1 the way pick otherwise would here.
        try:
            if not in_progress and self.season.viewedLeafCount.asInt() == 0:
                return None
        except:
            util.ERROR('EpisodesWindow._defaultEpisode: failed, falling back to episode 1')
            return None

        return pick

    def _cacheSeasonCardPick(self, pick, first):
        """Remember _seasonPick()'s answer for the season card, keyed by the season it's about."""
        if pick is None and first is None:
            # The listing failed (or the season is genuinely empty, which no navigable season is) -
            # deliberately not cached, so a transient failure gets another go the next time the card
            # is focused rather than leaving its Play button dead for the life of this window.
            self._seasonCardPick = None
            return

        # Keyed rather than just stored: switchSeason() reuses this window in place, and the
        # paginator/card are rebuilt around a different season each time.
        self._seasonCardPick = ((self.season or self.show_).ratingKey,
                                pick if pick is not None else first)

    def seasonCardEpisode(self):
        """The episode the season card's own Play/Resume button starts, or None.

        _seasonPick()'s answer, except where that comes up empty: nothing unwatched and nothing
        part-way through means a fully watched season, where _defaultEpisode() answers None (land on
        the card rather than episode 1). Play has to start somewhere, so it rewatches from the top.

        Cached per season - the click path and the button's own label must agree on the episode, and
        neither should pay for a second listing call to find that out.
        """
        key = (self.season or self.show_).ratingKey
        cached = self._seasonCardPick
        if cached and cached[0] == key:
            return cached[1]

        pick, in_progress, first = self._seasonPick()
        self._cacheSeasonCardPick(pick, first)
        return pick if pick is not None else first

    def updateSeasonCardPlayState(self, mli):
        """Point the button row's Play/Resume pair at the season card's own episode.

        Cheap when the pick is already known (the usual case - _defaultEpisode() seeded it on the way
        in); otherwise the listing call it needs goes to a background thread rather than blocking the
        focus change that got us here. The button shows a plain "Play" until it lands, same way the
        Roles/Extras rows fill in behind the screen.
        """
        key = (self.season or self.show_).ratingKey
        cached = self._seasonCardPick
        if cached and cached[0] == key:
            self.applySeasonCardPlayState(mli, cached[1])
        else:
            self.postpone_simple(self.resolveSeasonCardPlayState, mli)

    def resolveSeasonCardPlayState(self, mli):
        key = (self.season or self.show_).ratingKey
        episode = self.seasonCardEpisode()
        if (self.season or self.show_).ratingKey != key:
            # the tab row moved to another season while the listing was in flight
            return

        self.applySeasonCardPlayState(mli, episode)

    def applySeasonCardPlayState(self, mli, episode):
        """The two ListItem properties the button row keys off, for the season card.

        in.progress/resume.timeleft, exactly as setProgress() sets them for a real episode card -
        the buttons' own visibility conditions (script-plex-episodes.xml.tpl) read them off
        Container(400)'s selected item either way, so the card gets Resume+Restart instead of Play
        for free. setProgress() itself can't be reused: it reads mli.dataSource, which this card
        deliberately doesn't have (createSeasonCardItem()).
        """
        if episode is None:
            mli.setBoolProperty('in.progress', False)
            mli.setProperty('resume.timeleft', '')
            self.setProperty('play.episode', '')
            # a plain "Play", so the pill shouldn't keep the width of whatever named an episode last
            self.sizeSeasonCardPlayLabel(False)
            return

        view_offset = episode.viewOffset.asInt()
        duration = episode.duration.asInt()
        in_progress = bool(view_offset and duration)
        mli.setBoolProperty('in.progress', in_progress)
        # remainingTimeToShortText's own 90-minute-cutoff, no-space style, matching setProgress()
        mli.setProperty('resume.timeleft', in_progress and T(33615, "{time} left").format(
            time=util.remainingTimeToShortText(duration - view_offset)) or '')
        # "S1E4": the same two localized fragments ShowWindow.applyPlayButtonEpisode() concatenates
        # (subitems.py), for the same reason - the Resume label already ends in a bullet before its
        # time-left, and two of them read as a list.
        self.setProperty('play.episode', u'{0}{1}'.format(
            T(32310, 'S').format(episode.parentIndex), T(32311, 'E').format(episode.index)))
        self.sizeSeasonCardPlayLabel(in_progress, mli.getProperty('resume.timeleft'))

        # This can land while the button row already has focus (the background resolve above), and
        # flipping in.progress swaps which of Play/Resume is the visible control - Kodi drops focus
        # entirely when the focused one goes invisible. selectPlayButton() can't do this: it bails
        # out on hadUserInteraction, which getting here by focusing the card implies.
        # No RESTART_BUTTON_ID: that one is hidden on this card entirely (its own comment in
        # script-plex-episodes.xml.tpl), so it can't be what has focus here.
        focused = self.getFocusId()
        if focused in (self.PLAY_BUTTON_ID, self.PLAY_BUTTON_DISABLED_ID, self.RESUME_BUTTON_ID):
            target = self.getPlayButtonID(mli)
            if target != focused:
                kodigui.waitForVisibility(target, amount=2)
                if xbmc.getCondVisibility('Control.IsVisible({0})'.format(target)):
                    self.setCondFocusId(target)

    def sizeSeasonCardPlayLabel(self, in_progress, timeleft=''):
        """Shrink the season card's own Play/Resume overlay to the label it's actually showing.

        Same formula and the same reason as ShowWindow.sizePlayButtonLabel() (subitems.py): the
        episode number in these two labels isn't known at build time, so the widths passed in the
        skin are only the worst case - "S1E1" to "S12E345" is ~45px of difference. label_width is
        the measured text + 4, the pill is label + 62 and the group label + 18
        (includes/episode_button_label.xml.tpl documents the formula). The episode cards' own
        overlays are separate controls with fixed text and aren't touched here.
        """
        episode = self.getProperty('play.episode')
        if in_progress:
            text = u'{0} {1}'.format(T(32316, 'Resume'), episode).rstrip()
            if timeleft:
                text = u'{0} • {1}'.format(text, timeleft)
            ids = (self.SEASON_CARD_RESUME_LABEL_GROUP_ID, self.SEASON_CARD_RESUME_LABEL_PILL_ID,
                   self.SEASON_CARD_RESUME_LABEL_TEXT_ID)
        else:
            text = u'{0} {1}'.format(T(33020, 'Play'), episode).rstrip()
            ids = (self.SEASON_CARD_PLAY_LABEL_GROUP_ID, self.SEASON_CARD_PLAY_LABEL_PILL_ID,
                   self.SEASON_CARD_PLAY_LABEL_TEXT_ID)

        label_width = int(round(measureTextWidth(text, FONT10_POINT_SIZE))) + 4
        group_id, pill_id, text_id = ids
        try:
            self.getControl(text_id).setWidth(label_width)
            self.getControl(pill_id).setWidth(label_width + 62)
            self.getControl(group_id).setWidth(label_width + 18)
        except (SystemError, RuntimeError):
            # Any state where the row hasn't rendered yet. The build-time widths are the worst case
            # anyway, so a miss here leaves a slightly roomy pill rather than a broken one.
            util.DEBUG_LOG('Episodes: no season card Play/Resume label controls to resize')

    @busy.dialog(delay_time=1.0)
    def doClose(self, **kw):
        if self.closing:
            util.LOG("Episodes: Already closing")
            return
        self.closing = True
        self.episodesPaginator = None
        TasksMixin.doClose(self)
        try:
            player.PLAYER.off('new.video', self.onNewVideo)
            player.PLAYER.off('video.progress', self.onVideoProgress)
        except KeyError:
            pass
        kodigui.ControlledWindow.doClose(self)
        #super(EpisodesWindow, self).doClose(**kw)

    def onBlindClose(self):
        if self.openedWithAutoPlay and not self.started:
            vp = None
            if self.show_.ratingKey in VIDEO_PROGRESS:
                # access progress data for current show only
                vp = copy.deepcopy(VIDEO_PROGRESS[self.show_.ratingKey]).get(self.season.ratingKey, {})

            if vp:
                self.show_.reload(checkFiles=1, **VIDEO_RELOAD_KW)
                if self.show_.isFullyWatched:
                    removeFromWatchlistBlind(self.show_.guid, self.show_)

    @busy.dialog(delay_time=2.5)
    def _onFirstInit(self):
        timing = kodigui.StepTiming('Episodes open')
        self.episodeListControl = kodigui.ManagedControlList(self, self.EPISODE_LIST_ID, 5)
        self.initMediaInfoPillControls()

        self.seasonsListControl = kodigui.ManagedControlList(self, self.SEASONS_LIST_ID, 5)
        self.rolesListControl = kodigui.ManagedControlList(self, self.ROLES_LIST_ID, 5)
        self.extraListControl = kodigui.ManagedControlList(self, self.EXTRA_LIST_ID, 5)

        if self.sectionList is None:
            self.sectionList = kodigui.ManagedControlList(self, self.SECTION_LIST_ID, 15)
            self.buildSectionList()
        else:
            self.sectionList.newControl(self)
        self._selectActiveSection()
        self.displayServerAndUser()

        VIDEO_PROGRESS.clear()

        if not self.openedWithAutoPlay:
            # we may have set up the hooks before
            self._setup_hooks()

        if self.show_ and not util.getSetting("slow_connection") and \
                (not self.cameFrom or self.cameFrom not in (self.show_.ratingKey, "postplay")) and \
                not self.openedWithAutoPlay:
            self.themeMusicInit(self.show_)
        timing.mark('controls')

        self._setup(timing=timing)
        self.postSetup(select_play_button=False)
        timing.mark('post setup')
        timing.log()

    def doAutoPlay(self, blind=False):
        # First reload the video to get all the other info
        self.initialEpisode.reload(checkFiles=1, **VIDEO_RELOAD_KW)

        # We're not hitting onFirstInit when autoplaying from home, setup hooks here, so we can grab video progress
        self._setup_hooks()
        self.openedWithAutoPlay = True
        return self.playButtonClicked(force_episode=self.initialEpisode, from_auto_play=True, start_over=self.startOver)

    def backgroundItem(self):
        # what updateProperties() paints once it runs - see kodigui's paintInitialBackground()
        return self.season or self.show_

    def onFirstInit(self):
        self._onFirstInit()

        self.openedWithAutoPlay = False

    @busy.dialog()
    def onRestored(self):
        """Back from minimised (kodigui.BaseFunctions.onRestored()): keep the focused episode.
        onReInit() re-picks one, for a return from playback or another screen where watch state
        may have moved, and without an episode it picks the next to watch - a restore moved the
        focus to that (live on the AM6B, 2026-09-27)."""
        self.playBtnClicked = False

    def onReInit(self):
        self.playBtnClicked = False

        # Watch state may have moved while we were away - playback being the obvious case, but also
        # a Mark Played from any screen opened on top of this one - so the season card's own pick
        # has to be worked out again. Dropped rather than recomputed here: the next focus onto the
        # card picks it up (checkForHeaderFocus()), and there's no reason to pay for the listing
        # call on every return to this window. The exception is the card already being the selected
        # item, where that focus change isn't coming.
        self._seasonCardPick = None
        selected = self.episodeListControl.getSelectedItem()
        if selected is not None and selected.getProperty("is.season.card"):
            self.updateSeasonCardPlayState(selected)

        self.themeMusicReinit(self.show_)
        if not self.tasks:
            self.tasks = backgroundthread.Tasks()

        vp = None
        if self.show_.ratingKey in VIDEO_PROGRESS:
            # access progress data for current show only
            vp = copy.deepcopy(VIDEO_PROGRESS[self.show_.ratingKey]).get(self.season.ratingKey, {})

        if (self.manuallySelected and not VIDEO_PROGRESS) or self.cameFrom in ("info", "show", "library"):
            if self.cameFrom in ("info", "show", "library"):
                self.cameFrom = None
                return
            util.DEBUG_LOG("Episodes: ReInit: Not doing anything, as we've previously manually selected "
                           "this item and don't have progress")
            return

        self.manuallySelected = False
        util.DEBUG_LOG("Episodes: {}: Got progress info: {}, came from: {}".format(
            self.episode and self.episode.ratingKey or None, VIDEO_PROGRESS, self.cameFrom))
        try:
            self.selectEpisode(from_reinit=True)
        except RedirectToEpisode as redirect:
            if redirect.select_episode:
                util.DEBUG_LOG("Got episode progress for a different season, redirecting")
            self.episodeListControl.reset()
            self.reset(episode=redirect.episode if redirect.select_episode else None, season=redirect.season)
            self.hadUserInteraction = True
            self._setup(from_redirect=True)
            self.postSetup()
            return
        except AttributeError:
            raise util.NoDataException

        if self.cameFrom == "info":
            self.cameFrom = None

        # keep progress data if we've been opened from another view, as parent views might need the updates as well
        if not self.cameFrom:
            VIDEO_PROGRESS.clear()

        mli = self.episodeListControl.getSelectedItem()
        if not mli or not self.episodesPaginator:
            return

        self.checkIsWatchlisted(self.show_)

        if vp:
            self.show_.reload(checkFiles=1, **VIDEO_RELOAD_KW)
            self.wl_auto_remove(self.show_)

        reload_items = [mli]
        skip_progress_for = None
        if vp:
            skip_progress_for = []
            break_next = False
            for m in self.episodeListControl:
                # pagination boundary
                if not m.dataSource:
                    continue

                if m.dataSource.ratingKey in vp or break_next:
                    reload_items.append(m)
                    if not break_next:
                        skip_progress_for.append(m.dataSource.ratingKey)
                        del vp[m.dataSource.ratingKey]
                    else:
                        break
                if not vp:
                    # for multi-episode videos reload the next one after this progress event as well
                    break_next = True

        reload_items = list(set(reload_items))
        #select_episode = reload_items and reload_items[-1] or mli

        #self.episodesPaginator.setEpisode(select_episode.dataSource)
        if not reload_items:
            self.selectPlayButton()
        self.reloadItems(items=reload_items, with_progress=True, skip_progress_for=skip_progress_for,
                         set_item_info=True)
        self.postpone_simple(self.fillSeasons, self.show_, seasonsFilter=lambda x: len(x) > 1,
                             selectSeason=self.season, update=True, do_focus=not self.manuallySelectedSeason,
                             extraFirstItem=self._showTabItem())

    def postSetup(self, select_play_button=True):
        self.checkForHeaderFocus(xbmcgui.ACTION_MOVE_DOWN, initial=True)
        if not self.hadUserInteraction and select_play_button:
            self.selectPlayButton()
        self.initialized = True

    def selectPlayButton(self):
        if self.closing:
            return

        if not self.fromWatchlist:
            selected = self.episodeListControl.getSelectedItem()
            if selected:
                set_focus = self.getPlayButtonID(selected, base=not self.currentItemLoaded
                                                 and self.PLAY_BUTTON_DISABLED_ID or None)
                if self.getFocusId() == set_focus or self.hadUserInteraction:
                    return

                kodigui.waitForVisibility(set_focus, amount=2)
                if xbmc.getCondVisibility('Control.IsVisible({0})'.format(set_focus)):
                    self.setCondFocusId(set_focus)
                else:
                    # the target button never became visible in time (eg. slow reload under network
                    # load) - forcing focus onto it anyway makes Kodi silently reject the request and
                    # leaves the window with no focused control at all, so fall back to the episode list
                    util.DEBUG_LOG("Episodes: Play button {} never became visible, focusing episode list "
                                   "instead", set_focus)
                    self.setCondFocusId(self.EPISODE_LIST_ID)

    @busy.dialog()
    def setup(self):
        self._setup()

    def _setup_hooks(self):
        player.PLAYER.on('new.video', self.onNewVideo)
        player.PLAYER.on('video.progress', self.onVideoProgress)

    def _setup(self, from_redirect=False, timing=None):
        (self.season or self.show_).reload(checkFiles=1, **VIDEO_RELOAD_KW)
        kodigui.markStep(timing, 'reload')

        if not self.episodesPaginator:
            self.episodesPaginator = EpisodesPaginator(self.episodeListControl,
                                                       leaf_count=int(self.season.leafCount) if self.season else 0,
                                                       parent_window=self)

        self.watchlist_setup(self.show_)
        kodigui.markStep(timing, 'watchlist')
        self.updateProperties()
        self.setBoolProperty("initialized", True)
        kodigui.markStep(timing, 'properties')
        self.fillEpisodes(from_redirect=from_redirect, timing=timing)

        # postpone less important tasks
        self.batch_simple([
            (self.fillSeasons, (self.show_,), dict(seasonsFilter=lambda x: len(x) > 1, selectSeason=self.season,
                                                    extraFirstItem=self._showTabItem())),
            (self.fillExtras, None, None),
            (self.fillRoles, None, None),
        ])

        if not self.directlyFromWatchlist:
            self.checkIsWatchlisted(self.show_)

    @close_safe
    def selectEpisode(self, from_reinit=False):
        util.DEBUG_LOG("SelectEpisode called: {}, {}, {}, {}, {}, {}", from_reinit, self.episode, self.season,
                       self.show_, VIDEO_PROGRESS, self.cameFrom)
        if not self.episodesPaginator:
            return

        if not self.episode and not from_reinit and self.season.viewedLeafCount.asInt() == 0:
            # Nothing in the season has ever been watched - same condition EpisodesWindow.
            # _defaultEpisode() already used to return None instead of episode 1 (see that method's
            # own comment) - reused here since this method has its own, separate "no self.episode ->
            # select the first unwatched episode" fallback below (the third condition a few lines
            # down) that would otherwise land right back on episode 1 regardless, live-confirmed:
            # EpisodesPaginator.populate()'s own season-card selection (driven by the exact same
            # self.episode is None signal) already ran by the time fillEpisodes() calls this method,
            # only for this fallback to immediately override it back to episode 1. Land on the
            # season card (position 0, that same populate() insertion) instead, and skip the rest of
            # this method entirely - none of its progress-data-syncing logic below applies to a
            # season nothing has ever touched.
            #
            # Deliberately NOT setting self.lastItem here (unlike every other branch that selects
            # something in this method) - checkForHeaderFocus()'s own season-card branch uses
            # `mli != self.lastItem` to decide whether it still needs to run fillSeasonCardExtras()
            # for the very first time; pre-seeding lastItem with this same season-card item here,
            # before that ever gets a chance to run, made that check see "no change" and skip the
            # fill entirely on real first load - live-confirmed, Extras stayed on whatever the
            # postponed batch_simple() fillExtras() call had raced in beforehand (see fillExtras()'s
            # own routing comment) until the user moved off the card and back.
            self.episodeListControl.selectItem(0)
            return

        had_progress_data = False
        progress_data_left = None
        progress_data = None
        if self.show_.ratingKey in VIDEO_PROGRESS:
            # access progress data for current show only
            progress_data = copy.deepcopy(VIDEO_PROGRESS[self.show_.ratingKey])

        set_main_progress_to = None
        selected_new = False

        last_mli_seen = None
        progress_for_last_mli = False

        mli = self.episodeListControl[0]

        if progress_data or not self.season.isFullyWatched:
            if progress_data:
                # check for progress data in current season
                progress_data_left = progress_data.pop(self.season.ratingKey, None)
                had_progress_data = bool(progress_data_left)

            for mli in self.episodeListControl:
                # pagination boundary
                if not mli.dataSource:
                    continue

                is_last_mli = self.episodeListControl.isLastItem(mli)

                just_fully_watched = False

                if progress_data_left and mli.dataSource:
                    progress = progress_data_left.pop(mli.dataSource.ratingKey, False)
                    progress_for_last_mli = progress and is_last_mli

                    # progress can be False (no entry), a number (progress), or True (fully watched just now)
                    # select it if it's not watched or in progress
                    if progress:
                        if progress is True:
                            # ep was just watched
                            just_fully_watched = True
                            mli.setProperty('unwatched', '')
                            mli.setProperty('watched', '1')
                            mli.setProperty('progress', '')
                            mli.setProperty('unwatched.count', '')
                            mli.setProperty('unwatched.count.large', '')
                            mli.dataSource.set('viewCount', mli.dataSource.get('viewCount', 0).asInt() + 1)
                            mli.dataSource.set('viewOffset', 0)
                            mli.dataSource.markWatched()
                            self.setUserItemInfo(mli, fully_watched=True)

                        elif progress > 60000:
                            # ep has progress - the tick stays if it was played before (a re-watch)
                            mli.setProperty('watched', mli.dataSource.isPlayed and '1' or '')
                            mli.setProperty('progress', util.getProgressImage(mli.dataSource, view_offset=progress))
                            mli.dataSource.set('viewOffset', progress)
                            self.setUserItemInfo(mli, watched=True)
                            set_main_progress_to = progress

                        elif progress <= 60000:
                            # reset progress as we might've had progress before
                            mli.setProperty('progress', '')
                            mli.dataSource.set('viewOffset', '')
                            self.setUserItemInfo(mli)
                            set_main_progress_to = 0

                        mli.dataSource.clearCache()

                        if self.noRatings:
                            self.populateRatings(mli.dataSource, mli, hide_ratings=self.hideSpoilers(mli.dataSource))

                    # after immediately updating the watched state, if we still have data left, continue
                    if progress is True and progress_data_left:
                        continue

                last_mli_seen = mli

                # first condition: we select self.episode if we've got no progress data, or we haven't watched it just now.
                # second condition: we've just come from playback with progress upon reinit. select the next available
                # episode that's either unwatched or in progress. if we're at the last item in the list, select it as well.
                # third condition: select the next unwatched episode if we don't have self.episode and didn't have any
                # player progress, which happens when being called without an episode (season view, show view).
                if (mli.dataSource == self.episode and not just_fully_watched and not progress_data_left) or \
                   (had_progress_data and not progress_data_left and ((not just_fully_watched
                    and not mli.dataSource.isFullyWatched) or (just_fully_watched and is_last_mli))) or \
                   ((not had_progress_data or not from_reinit) and not self.episode and not mli.dataSource.isFullyWatched):
                    #if self.episodeListControl.getSelectedPosition() < mli.pos():
                    self.episodeListControl.selectItem(mli.pos())

                    tries = 0
                    while self.episodeListControl.getSelectedPos() != mli.pos() and tries < util.MONITOR.waitAmount(4, interval=SELECT_POLL_SECONDS):
                        kodigui.sleepForGui(SELECT_POLL_SECONDS)
                        self.episodeListControl.selectItem(mli.pos())
                        tries += 1

                    self.episodesPaginator.setEpisode(self.episode or mli.dataSource)
                    self.lastItem = mli
                    selected_new = mli
                    if just_fully_watched:
                        set_main_progress_to = 0

                    # this is a little counter-intuitive - None is actually valid here, and if set to None, setProgress will
                    # use the actual item progress, not ours
                    self.setProgress(mli, view_offset=set_main_progress_to)
                    break
            else:
                # no matching episode found
                mli = self.episodeListControl.getSelectedItem()
                self.setProgress(mli, view_offset=0)
        elif self.season.isFullyWatched:
            # A fully watched season: self.episode when there is one, else the first episode. Used to
            # be "and not self.episode" with item 0 picked blind - two gaps, live-reported 2026-10-02:
            # with self.episode set (re-watching an episode of a season that's otherwise all watched -
            # Plex still counts the season fully watched) neither branch selected anything, so the
            # row kept its default, episode 1, and the selected episode never got set up (its media
            # pills stayed at their build-time size); and item 0 is the season card now
            # (createSeasonCardItem(), dataSource None), so the no-episode case landed on the card
            # instead of episode 1. The paginator's own early pick of self.episode (selectItem())
            # doesn't survive the season card's prepend reliably, the native select being queued.
            target = None
            for item in self.episodeListControl:
                if item.dataSource and (not self.episode or item.dataSource == self.episode):
                    target = item
                    break

            if target:
                mli = target
                self.episodeListControl.selectItem(mli.pos())

                tries = 0
                while self.episodeListControl.getSelectedPos() != mli.pos() and tries < util.MONITOR.waitAmount(4, interval=SELECT_POLL_SECONDS):
                    kodigui.sleepForGui(SELECT_POLL_SECONDS)
                    self.episodeListControl.selectItem(mli.pos())
                    tries += 1

                self.episodesPaginator.setEpisode(mli.dataSource)
                self.lastItem = mli
                # None: the item's own progress, as the branch above does - a part-watched
                # re-watch shows its resume state.
                self.setProgress(mli, view_offset=None)

        if from_reinit and had_progress_data:
            # we had progress data for our current season and still have progress data for the current TV show
            if progress_data:
                # we've probably watched something in the next season
                ns = progress_data[list(progress_data.keys())[-1]]
                key = '/library/metadata/{0}'.format(list(ns.keys())[-1])
                ep = plexapp.SERVERMANAGER.selectedServer.getObject(key)
                if ep.parentIndex != self.season.index and ep.grandparentRatingKey == self.show_.ratingKey:
                    util.LOG("Progress data left for TV show, going to season of "
                             "remaining episode with progress data: {}", ep)
                    raise RedirectToEpisode(ep)
            elif progress_for_last_mli and last_mli_seen.dataSource.isFullyWatched and self.getSeasons():
                # check if we need to go to the next season
                remaining_seasons = self.seasons[self.seasons.index(self.season)+1:]
                if remaining_seasons:
                    season = remaining_seasons[0]
                    VIDEO_PROGRESS.clear()
                    util.LOG("Season watched, going to next season: {}", season)
                    raise RedirectToEpisode(season.episodes()[0], season=season, select_episode=False)

        if selected_new:
            #self.setProperty('hub.focus', "0")
            #self.setProperty('on.extras', '')
            self.lastFocusID = None
            if not from_reinit:
                self.currentItemLoaded = False
            # No fixed wait here any more: it stood in for "until the new selection has landed",
            # which the poll above already waits for (step 4 in the navigation review - it cost
            # 50 ms of every Episodes open on the AM6B).

        self.episode = None

    # Back from Roles/Extras retracts to the episode row, not the button row below it (on request);
    # a further Back from there leaves the screen.
    BACK_RETRACT_ID = EPISODE_LIST_ID

    def handleBack(self):
        return self.backToRowStartOrRetract()

    def backResetRows(self):
        # EPISODE_LIST_ID is left out: the selected episode is what this screen is showing.
        return {self.ROLES_LIST_ID: self.rolesListControl,
                self.EXTRA_LIST_ID: self.extraListControl}

    def onAction(self, action):
        # Hosted: the host sees the action first (kodigui.BaseWindow.routeActionToHost()).
        if self.routeActionToHost(action):
            return
        try:
            if self.debouncing:
                util.DEBUG_LOG("Already waiting to work on previous input, debouncing.")
                return

            controlID = self.getFocusId()

            if not self.initialized and not self.currentItemLoaded:
                tries = 0
                self.debouncing = True
                while not self.initialized and not self.currentItemLoaded and tries < util.MONITOR.waitAmount(4):
                    util.MONITOR.waitFor()
                    tries += 1
                self.debouncing = False

            if not controlID and self.lastFocusID and not action == xbmcgui.ACTION_MOUSE_MOVE:
                self.setCondFocusId(self.lastFocusID)

            if action == xbmcgui.ACTION_LAST_PAGE and xbmc.getCondVisibility('ControlGroup(300).HasFocus(0)'):
                next(self)
            elif action == xbmcgui.ACTION_NEXT_ITEM:
                next(self)
            elif action == xbmcgui.ACTION_FIRST_PAGE and xbmc.getCondVisibility('ControlGroup(300).HasFocus(0)'):
                self.prev()
            elif action == xbmcgui.ACTION_PREV_ITEM:
                self.prev()

            if action in (xbmcgui.ACTION_MOVE_DOWN, xbmcgui.ACTION_MOVE_LEFT, xbmcgui.ACTION_MOVE_RIGHT):
                self.hadUserInteraction = True

            if action == xbmcgui.ACTION_MOVE_UP and controlID in (self.EPISODE_LIST_ID, self.SEASONS_LIST_ID):
                self.updateBackgroundFrom((self.season or self.show_ or self.season.show()))

            if controlID == self.SEASONS_LIST_ID and \
                    action in (xbmcgui.ACTION_MOVE_LEFT, xbmcgui.ACTION_MOVE_RIGHT):
                self.manuallySelectedSeason = True

            elif controlID == self.EPISODE_LIST_ID:
                if self.checkForHeaderFocus(action):
                    return
                elif self.isWatchedAction(action):
                    mli = self.episodeListControl.getSelectedItem()
                    if not mli or mli.getProperty("is.boundary"):
                        return
                    self.toggleWatched(mli)
                    self.selectEpisode()
                    return
                elif action == xbmcgui.ACTION_CONTEXT_MENU:
                    self.optionsButtonClicked(from_item=True)
                    return

            elif self.isWatchedAction(action) and xbmc.getCondVisibility('ControlGroup({}).HasFocus(0)'.format(self.MAIN_BUTTON_GROUP_ID)):
                mli = self.episodeListControl.getSelectedItem()
                if not mli or mli.getProperty("is.boundary"):
                    return

                self.toggleWatched(mli)
                self.selectEpisode()
                return

            if action == xbmcgui.ACTION_CONTEXT_MENU:
                # Swallowed on anything without a context menu of its own, rather than shoving focus
                # into OPTIONS_GROUP_ID (the header, group 200) the way this used to. That jump was
                # written when the header still carried the home/search buttons; every screen here now
                # blanks header_topleft in favour of the sidebar, so group 200's own
                # <defaultcontrol always="true">201</defaultcontrol> (default.xml.tpl) points at a
                # control that no longer exists. What's left inside it is the audio widget (204, only
                # focusable while Player.HasAudio) and, on Seasons/Episodes, the season tabs (205,
                # only when they have items) - so with nothing playing and no tabs the group has no
                # focusable child at all, Kodi drops focus entirely and the screen goes dead to
                # everything but Back (live-reported on Artist, Pre-play and skipChildren Seasons;
                # where tabs did exist the same jump landed focus on the tab bar instead).
                # Nothing is exempt here any more: in-progress items get their own Resume/Restart
                # buttons instead of a single Play, so the old "menu on Play forces the
                # resume-or-restart dropdown" shortcut (force_resume_menu, gated on assume_resume)
                # had nothing left to offer and is gone - Play is inert under menu, on request.
                return

            elif action == xbmcgui.ACTION_NAV_BACK:
                if self.handleBack():
                    return

            if action in (xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_PREVIOUS_MENU):
                if self.dismissSidebarPopupOnBack():
                    return
                self.doClose()
                return
        except:
            util.ERROR()

        kodigui.ControlledWindow.onAction(self, action)

    def onNewVideo(self, video=None, **kwargs):
        if not video:
            return

        if not video.type == 'episode':
            return

        util.DEBUG_LOG('Updating selected episode: {0}', video)
        self.episode = video

        return True

    def onVideoProgress(self, data=None, **kwargs):
        if not data:
            return

        util.DEBUG_LOG("Storing video progress data: {}", data)
        gprk, prk, rk, state = data
        if gprk not in VIDEO_PROGRESS:
            VIDEO_PROGRESS[gprk] = OrderedDict()

        if prk not in VIDEO_PROGRESS[gprk]:
            VIDEO_PROGRESS[gprk][prk] = OrderedDict()

        VIDEO_PROGRESS[gprk][prk][rk] = state

    def onBGMStarted(self, **kwargs):
        #self.playBtnClicked = True
        pass

    def onClick(self, controlID):
        # Not live on its host yet, or any more (kodigui.BaseWindow.ignoresInput()).
        # Hosted: the host handles the sidebar's clicks (kodigui.BaseWindow.routeClickToHost()).
        if self.routeClickToHost(controlID):
            return
        if controlID == self.SECTION_LIST_ID:
            self.sectionClicked()
        elif controlID == self.EPISODE_LIST_ID:
            self.episodeListClicked()
        elif controlID == self.PLAYER_STATUS_BUTTON_ID:
            self.showAudioPlayer()
        elif controlID == self.PLAY_BUTTON_ID:
            self.playButtonClicked()
        elif controlID == self.RESUME_BUTTON_ID:
            self.episodeListClicked(force_resume=True)
        elif controlID == self.RESTART_BUTTON_ID:
            self.episodeListClicked(start_over=True)
        elif controlID == self.SHUFFLE_BUTTON_ID:
            self.shuffleButtonClicked()
        elif controlID == self.OPTIONS_BUTTON_ID:
            self.optionsButtonClicked()
        elif controlID == self.SETTINGS_BUTTON_ID:
            self.settingsButtonClicked()
        elif controlID == self.INFO_BUTTON_ID:
            self.infoButtonClicked()
        elif controlID == self.SUMMARY_BUTTON_ID:
            self.summaryButtonClicked()
        elif controlID == self.SEASONS_LIST_ID:
            if self.fromWatchlist:
                return
            mli = self.seasonsListControl.getSelectedItem()
            if not mli:
                return
            item = mli.dataSource
            if item is None:
                # "Show" tab - see _goToShow()'s own comment (shared with the options menu's
                # "Go To Show" entry, optionsButtonClicked()).
                self._goToShow(parent_list=self.seasonsListControl)
            elif item != self.season:
                self.switchSeason(item)
            else:
                self.setCondFocusId(self.EPISODE_LIST_ID)
        elif controlID == self.ROLES_LIST_ID:
            if not self.roleClicked():
                return
        elif controlID == self.EXTRA_LIST_ID:
            self.openItem(self.extraListControl)

    def onFocus(self, controlID):
        # Not live on its host yet, or any more (kodigui.BaseWindow.ignoresInput()).
        if self.ignoresInput():
            return
        self.reselectActiveSection(controlID, self.lastFocusID)
        self.lastFocusID = controlID

        if 399 < controlID < 500:
            self.setProperty('hub.focus', str(controlID - 400))

        # row.focused (not hub.focus, which is never cleared once set - other controls key off it
        # staying "seen at least once") drives default_background.xml.tpl's shared full-canvas dim
        # scrim, same as PrePlayWindow.onFocus()/ShowWindow.onFocus() (preplay.py/subitems.py) - this
        # screen just never opted in before now. 401, not 399: unlike those two screens, this one's
        # own 400 is the episode row itself, this screen's primary content and the default focus
        # target on open, not "extra" content the way Roles (402)/Extras (403) are - so the dim
        # should only kick in once focus moves down past the button row into Roles/Extras, not for
        # the episode row too.
        if 401 < controlID < 500:
            self.setProperty('row.focused', '1')
        else:
            self.setProperty('row.focused', '')

        # the episode row counts as "not on extras" too, now that it's the screen's default focus target -
        # otherwise this fires the very moment the window opens instead of only once focus goes deeper,
        # into roles/extras. SUMMARY_BUTTON_ID needs the same exclusion: it's a header control that
        # happens to live inside group 50 but outside group 300, so without this the elif below misread
        # focusing it as "focus moved into deeper content" and slid the whole header up - same bug/fix
        # as ShowWindow.onFocus()'s own copy of this (subitems.py), which this was ported from.
        if (controlID == self.EPISODE_LIST_ID or controlID == self.SUMMARY_BUTTON_ID or
                xbmc.getCondVisibility('ControlGroup(50).HasFocus(0) + ControlGroup(300).HasFocus(0)')):
            self.setProperty('on.extras', '')
            # hub.focus (set above, only for controlIDs 400-499) is otherwise never reset once focus
            # leaves the roles/extras row stack for the button row - it's not in that range, so
            # it'd keep whatever value the last-focused row left it at. The row-collapse slide
            # animations on group 50 (script-plex-episodes.xml.tpl) key off hub.focus, not on.extras, so
            # without this they'd stay collapsed even after on.extras clears and the header reappears -
            # the header (and the now-fully-visible episode row) would show while the logo/title/summary
            # block above it stays scrolled out of view until focus reaches the episode row and resets
            # hub.focus itself.
            self.setProperty('hub.focus', '0')
        elif xbmc.getCondVisibility('ControlGroup(50).HasFocus(0) + !ControlGroup(300).HasFocus(0)'):
            self.setProperty('on.extras', '1')

    def toggleWatched(self, mli=None, item=None, state=None, **kw):
        if not mli and not item:
            return

        item = item or mli.dataSource
        watched = super(EpisodesWindow, self).toggleWatched(item, state=state, **VIDEO_RELOAD_KW)
        if watched is None:
            return

        self.show_ = self.show_.reload(includeExtras=1, includeExtrasCount=10, includeOnDeck=1)
        if watched:
            self.wl_auto_remove(self.show_)
            self.checkIsWatchlisted(self.show_)
        self.updateItems(mli)
        util.MONITOR.watchStatusChanged()

    def openItem(self, control=None, item=None, came_from=None):
        if not item:
            mli = control.getSelectedItem()
            if not mli:
                return
            item = mli.dataSource

        self.processCommand(opener.open(item, context=self, came_from=came_from,
                                        entry_section_id=self.entrySectionId,
                                        entry_from_watchlist=self.entryFromWatchlist))

    def roleSectionId(self):
        return self.entrySectionId

    def roleFromWatchlist(self):
        return self.entryFromWatchlist

    def getRoleItemDDPosition(self, *args, **kwargs):
        y = 900
        if xbmc.getCondVisibility('Control.IsVisible(500)'):
            y += 380
        if xbmc.getCondVisibility('!String.IsEmpty(Window.Property(on.extras))'):
            y -= 80
        if xbmc.getCondVisibility('Integer.IsGreater(Window.Property(hub.focus),0) + Control.IsVisible(500)'):
            # Mirrors the tier-1 hub.focus slide amount in script-plex-episodes.xml.tpl (group 50) -
            # grown from 500 to 540 along with the episode row's own thumbnail resize, see that
            # animation's own comment.
            y -= 540

        return super(EpisodesWindow, self).getRoleItemDDPosition(y=y, container_id="402")

    def getSeasons(self):
        if not self.seasons:
            self.seasons = self.show_.seasons()

        if not self.seasons:
            return False

        return True

    def next(self):
        if not self._next():
            return
        self.setup()

    __next__ = next

    @busy.dialog()
    def _next(self):
        if self.parentList:
            mli = self.parentList.getListItemByDataSource(self.season)
            if not mli:
                return False

            pos = mli.pos() + 1
            if not self.parentList.positionIsValid(pos):
                pos = 0

            self.season = self.parentList.getListItem(pos).dataSource
        else:
            if not self.getSeasons():
                return False

            if self.season not in self.seasons:
                return False

            pos = self.seasons.index(self.season)
            pos += 1
            if pos >= len(self.seasons):
                pos = 0

            self.season = self.seasons[pos]

        return True

    def prev(self):
        if not self._prev():
            return
        self.setup()

    @busy.dialog()
    def _prev(self):
        if self.parentList:
            mli = self.parentList.getListItemByDataSource(self.season)
            if not mli:
                return False

            pos = mli.pos() - 1
            if pos < 0:
                pos = self.parentList.size() - 1

            self.season = self.parentList.getListItem(pos).dataSource
        else:
            if not self.getSeasons():
                return False

            if self.season not in self.seasons:
                return False

            pos = self.seasons.index(self.season)
            pos -= 1
            if pos < 0:
                pos = len(self.seasons) - 1

            self.season = self.seasons[pos]

        return True

    def _goToShow(self, parent_list=None):
        """Shared by the season-tab row's "Show" tab (onClick(), SEASONS_LIST_ID handling) and the
        options menu's "Go To Show" entry (optionsButtonClicked()) - both want identical treatment.
        initialEpisode (reset(), untouched by in-page switchSeason()) is None only when this window
        was opened with season= rather than episode= - i.e. from a season click on the Seasons page
        itself (opener.py's seasonClicked()) - meaning that exact Seasons page is still sitting
        right underneath us. In that case just do what Back does (onAction(), not doClose()
        directly, since a hosted shell's onAction goes through the host first - see
        kodigui.BaseWindow.routeActionToHost() - so this correctly pops the
        descendant chain when hosted, or closes outright when not) instead of opening a second copy
        of Seasons on top: switchSeason() never pushes a nav step per season-tab switch (see its own
        comment), so however many seasons were browsed this way before landing here, there's still
        only this one screen to unwind.

        Otherwise (Search, On Deck, Recommended, Continue Watching, the options menu from any of
        those, ...) there's no Seasons page underneath to fall back to - open one fresh, but as a
        *replacement* for this Episodes page on the descendant chain (push=False - see swapTo()'s
        own param, library.py) rather than an addition to it, so a subsequent Back from Seasons goes
        straight to wherever this screen was really opened from instead of back through it.
        push=False only means something while genuinely chained (_liveChainHost() live) - passing it
        while unhosted would reach ShowWindow's own constructor as a stray, unexpected kwarg."""
        if self.initialEpisode is None:
            self.onAction(xbmcgui.ACTION_NAV_BACK)
            return

        self.cameFrom = "show"
        openKwargs = dict(parent_list=parent_list, came_from=self.cameFrom,
                          from_watchlist=self.fromWatchlist,
                          directly_from_watchlist=self.directlyFromWatchlist,
                          is_watchlisted=self.is_watchlisted,
                          entry_section_id=self.entrySectionId,
                          entry_from_watchlist=self.entryFromWatchlist)
        if self._liveChainHost() is not None:
            openKwargs['push'] = False
        self.processCommand(opener.open(self.show_, context=self, **openKwargs))

    def switchSeason(self, season):
        # reload this window in place rather than opening a new one on top of it - the season tab bar makes
        # switching seasons frequent, and stacking a window per swap would take that many Back presses to undo
        self.season = season

        if self.episodesPaginator:
            # _setup() below only builds a fresh paginator "if not self.episodesPaginator" - since
            # this window (and its paginator) is reused in place rather than reopened, the old
            # season's own navigation state (offset/rightOffset/direction/currentEpisode) and
            # leafCount would otherwise carry straight over into the new season, which fillEpisodes()
            # -> paginate() reads before anything else here gets a chance to touch it.
            self.episodesPaginator.reset()
            self.episodesPaginator.leafCount = int(self.season.leafCount) if self.season else 0

        # Same "no specific episode" default as reset() (see that method's own comment and
        # _defaultEpisode() itself) - switching seasons via this in-page tab row bypasses reset()
        # entirely, so without this it always landed back on episode 1 regardless of the new
        # season's own watched state.
        self.episode = self._defaultEpisode()
        self.manuallySelectedSeason = True
        self.setup()

    def _showTabItem(self):
        # Pinned "Show" entry at the front of the season-tab row (fillSeasons()'s extraFirstItem,
        # mixins/seasons.py) - no dataSource, so onClick()'s SEASONS_LIST_ID handler recognizes it and
        # opens the show/season page instead of trying to switch to it as a season.
        return kodigui.ManagedListItem(T(35058, 'Show'))

    def searchButtonClicked(self):
        section_id = self.show_.getLibrarySectionId()
        self.processCommand(search.dialog(self, section_id=section_id or None))

    def buildSectionList(self):
        """Populate the sidebar's section list. Mirrors library.py's buildSectionList()/
        home.py's showSections() and preplay.py's own copy - see library.py:675 for why this
        isn't shared code yet.
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

        if "order" in navSettings:
            order = navSettings["order"]

            def orderPos(s):
                if s.key in order:
                    return order.index(s.key), 0
                return -1, 0

            sections = sorted(sections, key=orderPos)

        # self.entrySectionId (Sidebar entry-section persistence) - see preplay.py's
        # buildSectionList() for the full reasoning; identical shape here.
        activeSectionId = self.entrySectionId
        activeSection = None
        if activeSectionId:
            for section in sections:
                if section.key == activeSectionId:
                    activeSection = section
                    break
        if activeSection is None and self.entryFromWatchlist:
            activeSection = home.watchlist_section

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
            if section == activeSection:
                mli.setProperty('is.active', '1')
            items.append(mli)

        self.sectionList.reset()
        self.sectionList.addItems(items)

    # sectionClicked() now provided by SidebarMixin - its default _dispatchSectionOpen() covers
    # this window's needs exactly.

    def displayServerAndUser(self):
        """Sidebar avatar/username and server icon/name. Mirrors library.py's/preplay.py's
        displayServerAndUser() (see library.py:777 for why home.py's own version doesn't
        reach this window - window properties are per-window).
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

    def playButtonClicked(self, force_episode=None, from_auto_play=False, start_over=False,
                          force_resume=False):
        return self.episodeListClicked(force_episode=force_episode, from_auto_play=from_auto_play,
                                       start_over=start_over, force_resume=force_resume)

    def shuffleButtonClicked(self):
        # Season-card-only now (button row's own visible condition) - shuffles the whole
        # season/show, not a single episode, so it never made sense as a per-episode-card action
        # the way Play/Resume/Restart do.
        seasonOrShow = self.season or self.show_
        items = seasonOrShow.all()
        pl = playlist.LocalPlaylist(items, seasonOrShow.getServer())

        pl.shuffle(True, first=True)
        videoplayer.play(play_queue=pl, context=self)
        return True

    def settingsButtonClicked(self):
        mli = self.episodeListControl.getSelectedItem()
        if not mli or mli.getProperty("is.boundary"):
            return

        episode = mli.dataSource

        if not episode.mediaChoice:
            playerObject = plexplayer.PlexPlayer(episode)
            playerObject.build()
        playersettings.showDialog(video=episode, non_playback=True)
        # setPostReloadItemInfo(), not just setItemAudioAndSubtitleInfo(): the Settings popup can
        # now also change the media choice itself (its new Video entry - playersettings.py), which
        # setItemAudioAndSubtitleInfo() alone never refreshed (video.res/video.codec/
        # video.rendering only live in setPostReloadItemInfo(), which also covers audio/subtitle -
        # it already calls setItemAudioAndSubtitleInfo() itself). Confirmed live: the video pill
        # was staying stale after a Video-entry change even though the underlying file had
        # actually switched (worked correctly through the old dedicated media button, which called
        # this same method - removed along with that button, on request).
        self.setPostReloadItemInfo(episode, mli)
        # Text alone updating without the pill's own width following it (audio/subtitle case, not
        # new this session) is setItemAudioAndSubtitleInfo() only ever touching the raw property
        # text - updateMediaInfoPills() is the actual resize step (resizeMediaInfoPills()), never
        # called after this dialog closes before now.
        self.updateMediaInfoPills(mli)

    def infoButtonClicked(self):
        mli = self.episodeListControl.getSelectedItem()
        if not mli or mli.getProperty("is.boundary"):
            return

        episode = mli.dataSource

        # Popup, not opener.handleOpen(info.InfoWindow, ...) any more: title/subtitle/thumb/summary
        # there all duplicated what's already visible on the episode screen itself - only the
        # media/file/stream detail block (formatMediaDetails() - info.py, shared with InfoWindow's
        # own getVideoInfo()) was actually new information, on request. A dialog like Settings'/
        # More's own popups, not a full window transition, so no cameFrom bookkeeping needed either
        # (that existed only for InfoWindow's own close-and-return-to-this-window flow).
        info.showMediaDetails(episode)

    def summaryButtonClicked(self):
        mli = self.episodeListControl.getSelectedItem()
        if not mli:
            return

        if mli.getProperty("is.season.card"):
            # The season card has no dataSource at all (createSeasonCardItem()'s own docstring -
            # giving it one crashes the window elsewhere), so unlike a real episode its title/summary
            # come straight from the window's own self.season/self.show_, same as the card's own
            # on-screen title/summary properties (createSeasonCardItem() itself). Show name as the
            # main title (live-reported: "Season X" alone read wrong there, should be a subtitle
            # under the show name) - same title/subtitle split as a real episode's own popup, just
            # season instead of episode. self.season is self.show_ for a skipChildren show (no real
            # season layer - see this window's own setup() where that flag is checked), so no
            # subtitle then.
            seasonOrShow = self.season or self.show_
            if not seasonOrShow:
                return
            showTitle = self.show_.title if self.show_ else seasonOrShow.title
            subtitle = self.season.title if self.season and self.season is not self.show_ else None
            info.showSummary(showTitle, seasonOrShow.summary.strip().replace('\t', ' '), subtitle=subtitle)
            return

        if mli.getProperty("is.boundary"):
            # A plain pagination boundary marker (left/right chevron/spinner) - no title/summary of
            # its own to show, unlike the season card above.
            return

        episode = mli.dataSource
        # grandparentTitle, not self.show_.title directly: same fallback setItemInfo() already uses
        # for the 'show.title' ListItem property this same row reads elsewhere (mli.setProperty
        # above in this file).
        showTitle = episode.grandparentTitle or (self.show_.title if self.show_ else '')
        info.showSummary(showTitle, episode.summary, subtitle=episode.title)

    def episodeListClicked(self, force_episode=None, from_auto_play=False, start_over=False,
                           force_resume=False):

        if self.playBtnClicked and not from_auto_play:
            util.DEBUG_LOG("Not honoring play action: currentItemLoaded: {0}, "
                           "playBtnClicked: {1}, from_auto_play: {2}",
                           self.currentItemLoaded, self.playBtnClicked, from_auto_play)
            return

        # wait for current item to be loaded
        if not from_auto_play:
            amount = 0
            while not self.currentItemLoaded and amount < util.MONITOR.waitAmount(5):
                util.MONITOR.waitFor()
                amount += 1

            amount = 0
            while any(not t.finished for t in self.tasks) and amount < util.MONITOR.waitAmount(5):
                util.MONITOR.waitFor()
                amount += 1

            if not self.currentItemLoaded:
                util.DEBUG_LOG("Not honoring play action: currentItemLoaded: False")
                return

        if not force_episode:
            mli = self.episodeListControl.getSelectedItem()
            if not mli:
                return

            if mli.getProperty("is.season.card"):
                # The season card has no dataSource of its own (createSeasonCardItem()), so the
                # episode comes from the season's own scan instead - the same one the button's own
                # label is spelling out. Ahead of the is.boundary guard below, which this card also
                # carries: before this branch existed, Play on the card fell into that guard and
                # silently did nothing at all.
                episode = self.seasonCardEpisode()
                if not episode:
                    util.DEBUG_LOG("Episodes: season card has no episode to play")
                    return
            elif mli.getProperty("is.boundary"):
                return
            else:
                episode = mli.dataSource
        else:
            episode = force_episode

        if not episode.available():
            util.messageDialog(T(32312, 'unavailable'), T(32332, 'This item is currently unavailable.'))
            return

        resume = False
        if episode.viewOffset.asInt() and not start_over:
            if force_resume:
                # Dedicated Resume button (button row) - skip the dialog/assume_resume check below
                # entirely, the button itself already made the choice explicit.
                resume = True
            elif not util.getSetting('assume_resume'):
                choice = dropdown.showDropdown(
                    options=[
                        {'key': 'resume', 'display': T(32429, 'Resume from {0}').format(util.timeDisplay(episode.viewOffset.asInt()).lstrip('0').lstrip(':'))},
                        {'key': 'play', 'display': T(32317, 'Play from beginning')}
                    ],
                    pos=(660, "middle"),
                    close_direction='none',
                    set_dropdown_prop=False,
                    header=T(32314, 'In Progress'),
                    dialog_props=from_auto_play and self.dialogProps or None
                )

                if not choice:
                    return

                if choice['key'] == 'resume':
                    resume = True
            else:
                resume = True

        if not from_auto_play:
            self.playBtnClicked = True

        items = playlist.reorder_with_specials(
            self.show_.all(),
            mode=util.getSetting('tv_specials_order', 'default')
        )
        pl = playlist.LocalPlaylist(items, self.show_.getServer())
        try:
            # inject our show in case we need to access show metadata from the player
            episode._show = self.show_
            if len(pl) > 1:  # Don't use playlist if it's only this video
                for ep in pl:
                    ep._show = self.show_

                pl.setCurrent(episode)
                self.processCommand(videoplayer.play(play_queue=pl, resume=resume, bgm=self.useBGM, context=self))
                self.playBtnClicked = False
                return True

            self.processCommand(videoplayer.play(video=episode, resume=resume, bgm=self.useBGM, context=self))
            self.playBtnClicked = False
            return True
        except util.NoDataException:
            util.ERROR("No data - deleted or server disconnected?", notify=True, time_ms=5000)
            self.doClose()

    def optionsButtonClicked(self, from_item=False):
        options = []

        mli = self.episodeListControl.getSelectedItem()
        # is.boundary is also true for the paginator's own loading-spinner markers, but those never
        # carry is.season.card, so this only matches the season pseudo-card itself.
        isSeasonCard = bool(mli and mli.getProperty("is.boundary") and mli.getProperty("is.season.card"))
        # self.season is the season card's usual target, but the same pseudo-card doubles as a
        # show-level card (createSeasonCardItem()'s own seasonOrShow fallback) when there's no
        # specific season - self.show_ then, for refresh/cache_reset below.
        seasonCardItem = self.season or self.show_

        if mli and not mli.getProperty("is.boundary"):
            # "Play from beginning" used to live here (assume_resume users only, since the plain
            # Play button already asks otherwise) - dropped now that the button row itself splits
            # into dedicated Resume/Restart buttons for a part-watched episode, on request.
            inProgress = mli.dataSource.viewOffset.asInt()

            if not mli.dataSource.isWatched or inProgress:
                options.append({'key': 'mark_watched', 'display': T(32319, 'Mark Played')})
            if mli.dataSource.isWatched or inProgress:
                options.append({'key': 'mark_unwatched', 'display': T(32318, 'Mark Unplayed')})

            # if True:
            #     options.append({'key': 'add_to_playlist', 'display': '[COLOR FF808080]Add To Playlist[/COLOR]'})

        # Season-card-only now, not shown on every episode card's own menu (its watched state is a
        # season-level action, not something that made sense mixed in with a specific episode's own
        # Mark Played/Unplayed above - on request).
        if isSeasonCard and self.season:
            if self.season.isWatched:
                options.append({'key': 'mark_season_unwatched', 'display': T(32320, 'Mark Season Unplayed')})
            else:
                options.append({'key': 'mark_season_watched', 'display': T(32321, 'Mark Season Played')})

        if self.show_:
            if options:
                options.append(dropdown.SEPARATOR)

            options.append({'key': 'playback_settings', 'display': T(32925, 'Playback Settings')})
            options.append(dropdown.SEPARATOR)

        if plexapp.ACCOUNT.isAdmin:
            options.append({'key': 'refresh', 'display': T(33719, 'Refresh metadata')})

            # Delete stays episode-only: the confirmation dialog below (delete()) is worded for a
            # single episode's own S/E numbers (item.parentIndex/item.index), which doesn't carry
            # over to a Season object, and deleting a season's media is a much bigger, more
            # destructive action than deleting one episode - not something to wire up to the same
            # confirmation text by accident.
            if not isSeasonCard and mli.dataSource.server.allowsMediaDeletion:
                options.append({'key': 'delete', 'display': T(32322, 'Delete')})

        # if xbmc.getCondVisibility('Player.HasAudio') and self.section.TYPE == 'artist':
        #     options.append({'key': 'add_to_queue', 'display': 'Add To Queue'})

        if options:
            options.append(dropdown.SEPARATOR)

        options.append({'key': 'to_show', 'display': T(32323, 'Go To Show')})

        if 'items' in util.getSetting('cache_requests'):
            options.append({'key': 'cache_reset', 'display': T(33728, "Clear cache for item")})

        pos = (500, util.vscalei(620))
        bottom = False
        if from_item:
            viewPos = self.episodeListControl.getViewPosition()
            optsLen = len(list(filter(None, options)))
            # dropDown handles any overlap with the right window boundary, so we don't need to care here
            pos = (
                (((viewPos + 1) * 359) - 100),
                util.vscalei(649) if optsLen < 7 else 649 - util.vscalei(66) * (optsLen - 6))

        choice = dropdown.showDropdown(options, pos, pos_is_bottom=bottom, close_direction='left',
                                       set_dropdown_prop=False)
        if not choice:
            return

        if choice['key'] == 'mark_watched':
            self.toggleWatched(mli, state=True)
        elif choice['key'] == 'mark_unwatched':
            self.toggleWatched(mli, state=False)
        elif choice['key'] == 'mark_season_watched':
            self.toggleWatched(item=self.season, state=True)
        elif choice['key'] == 'mark_season_unwatched':
            self.toggleWatched(item=self.season, state=False)
        elif choice['key'] == 'to_show':
            self._goToShow()
        elif choice['key'] == 'delete':
            self.delete(mli.dataSource)
            self.episodesPaginator.leafCount = int(self.season.leafCount) if self.season else 0
            self.fillEpisodes()
        elif choice['key'] == 'playback_settings':
            self.playbackSettings(self.show_, pos, bottom)
        elif choice['key'] == 'refresh':
            # updateItems() with no item, not updateItems(mli): the per-item branch reads
            # item.dataSource, which is None for the season card - the no-arg branch just
            # re-fills the whole episode list instead, which covers this card too.
            if isSeasonCard:
                seasonCardItem.refresh()
                self.updateItems()
            else:
                mli.dataSource.refresh()
                self.updateItems(mli)
        elif choice["key"] == "cache_reset":
            try:
                target = seasonCardItem if isSeasonCard else mli.dataSource
                util.DEBUG_LOG('Clearing requests cache for {}...', target)
                target.clearCache()
                target.reload()
                if isSeasonCard:
                    self.updateItems()
                else:
                    self.updateItems(mli)
            except Exception as e:
                util.DEBUG_LOG("Couldn't clear cache: {}", e)

    def delete(self, item):
        button = optionsdialog.show(
            T(32326, 'Really delete?'),
            T(33036, "Delete episode S{0:02d}E{1:02d} from {2}?").format(item.parentIndex.asInt(),
                                                                         item.index.asInt(), item.defaultTitle),
            T(32328, 'Yes'),
            T(32329, 'No')
        )

        if button != 0:
            return

        if not self._delete():
            util.messageDialog(T(32330, 'Message'), T(32331, 'There was a problem while attempting to delete the media.'))
        else:
            return True

    @busy.dialog()
    def _delete(self):
        mli = self.episodeListControl.getSelectedItem()
        if not mli or mli.getProperty("is.boundary"):
            return

        video = mli.dataSource
        success = video.delete()
        util.LOG('Media DELETE: {0} - {1}', video, success and 'SUCCESS' or 'FAILED')
        if success:
            self.episodeListControl.removeItem(mli.pos())
            if not self.episodeListControl.size():
                self.doClose()
            else:
                (self.season or self.show_).reload()
        return success

    def checkForHeaderFocus(self, action, initial=False):
        if not self.episodesPaginator:
            return

        mli = self.episodeListControl.getSelectedItem()
        if mli and mli.getProperty("is.boundary") and mli.getProperty("is.season.card"):
            # Extras only, from the season itself (not the show) - see fillSeasonCardExtras()'s own
            # comment. Roles/progress/media pills don't apply to the season card, so this skips the
            # rest of the method entirely, same as any other boundary marker - but deliberately
            # ahead of the self.tasks throttle below: fillSeasonCardExtras() has no network/
            # paginator cost of its own (self.season.extras is already loaded), so it shouldn't be
            # held up by a guard meant for the heavier pagination-fetch logic further down. Without
            # this ordering, landing on the season card while a background episode reload is still
            # in flight - near-certain right after window open, reloadItems() just queued one -
            # would leave Extras showing stale/wrong data from whatever was focused before, until
            # the user moved off and back once that reload task cleared.
            if mli != self.lastItem:
                self.lastItem = mli
                self.updateExtrasHeader(mli)
                # Play/Resume for this card, same place a real episode card gets setProgress() -
                # further down this method, on the branch this one returns ahead of.
                self.updateSeasonCardPlayState(mli)
                self.fillSeasonCardExtras()
                # fillRoles() already blanks itself on any boundary item (including this one) via
                # its own is.boundary guard - just never got called at all on this branch before,
                # so whatever the last real episode's Roles were stayed on screen untouched.
                self.fillRoles()
            return

        # don't continue if we're still waiting for tasks
        if self.tasks:
            if not initial:
                util.DEBUG_LOG("Episodes: Moving too fast through paginator, throttling.")
            return

        if self.episodesPaginator.boundaryHit:
            items = self.episodesPaginator.paginate()
            self.reloadItems(items)
            return True

        if not mli:
            return

        if mli.getProperty("is.boundary"):
            return

        lastItem = self.lastItem

        if action in (xbmcgui.ACTION_MOVE_RIGHT, xbmcgui.ACTION_MOVE_LEFT) and lastItem:
            items = self.episodesPaginator.wrap(mli, lastItem, action)
            #xbmc.sleep(100)
            mli = self.episodeListControl.getSelectedItem()
            if items:
                self.reloadItems(items)
                return True

        if mli != self.lastItem and not mli.getProperty("is.boundary"):
            self.lastItem = mli
            self.setProgress(mli)
            self.updateMediaInfoPills(mli)
            # Clear immediately, right when the move is detected - not just once the debounce
            # settles and fillRoles()/fillExtras() reset+refill in one step (scheduleRowDataUpdate()
            # below). Without this, a quick move that lands on a new episode still shows the
            # previous episode's Roles/Extras for the whole 0.35s settle window - close enough to
            # instant that it reads as "wrong data for this episode" rather than "still loading".
            self.rolesListControl.reset()
            self.extraListControl.reset()
            # updateExtrasHeader() itself moved to _fillRowData() below, alongside fillExtras() -
            # live-confirmed bug calling it immediately here instead: the header text (an
            # Window property, always visible) updated the instant focus moved, but whether this
            # episode actually HAS extras isn't known yet - fillExtras() below still has to fetch
            # that per-episode (ds.fetchExternalExtras()), debounced same as fillRoles(). The
            # section's own visibility is correctly gated on Container(403).NumItems>0, not on this
            # text, so an extras-less episode still ended up hidden once the debounce settled - but
            # not before the label itself briefly flashed "Extras • Episode N" first, since nothing
            # else about updating this particular property is gated on the list actually having
            # anything in it. Deferring the text to update alongside the real fill instead costs
            # nothing: while the section is hidden (NumItems==0, true immediately thanks to the
            # reset above) a stale label underneath it is invisible regardless of its timing.
            self.scheduleRowDataUpdate(immediate=initial)

        if action in (xbmcgui.ACTION_MOVE_UP, xbmcgui.ACTION_PAGE_UP):
            if mli.getProperty('is.header'):
                xbmc.executebuiltin('Action(up)')
        if action in (xbmcgui.ACTION_MOVE_DOWN, xbmcgui.ACTION_PAGE_DOWN, xbmcgui.ACTION_MOVE_LEFT,
                      xbmcgui.ACTION_MOVE_RIGHT):
            if not initial and action in (xbmcgui.ACTION_MOVE_LEFT, xbmcgui.ACTION_MOVE_RIGHT):
                self.manuallySelected = True
            if mli.getProperty('is.header'):
                xbmc.executebuiltin('Action(down)')

    def scheduleRowDataUpdate(self, immediate=False):
        """Settled-focus debounce for fillRoles()/fillExtras(). Roles data is already present on
        every episode from the season listing fetch (no network involved), but Extras isn't -
        fillExtras() below has to fetch it per-episode, so without debouncing, holding a
        direction key to fly through the row would fire one request per episode passed over
        instead of one for wherever focus actually settles. Both rows are refilled together
        (not just Extras) so they never show data for two different episodes at once.

        immediate=True (the initial-focus call from postSetup()/checkForHeaderFocus()) skips the
        wait entirely - there's nothing to debounce against on first load, and delaying the very
        first fill would just add a visible pause before the rows populate.
        """
        if immediate:
            self.rowDataChangeTimeout = 0
            self._fillRowData()
            return

        self.rowDataChangeTimeout = time.time() + 0.35
        if not self.rowDataChangeThread or not self.rowDataChangeThread.is_alive():
            self.rowDataChangeThread = threading.Thread(target=self._updateRowData, name="episoderowdata")
            self.rowDataChangeThread.start()

    def _updateRowData(self):
        if self.closing:
            return

        while not util.MONITOR.waitFor():
            # timing issue
            if not self.rowDataChangeTimeout:
                return
            if time.time() >= self.rowDataChangeTimeout:
                break

        if self.closing:
            return

        try:
            if self.getFocusId() != self.EPISODE_LIST_ID:
                # focus moved off the episode row entirely before we settled - eg. down onto the
                # button row - don't act on a selection the user isn't browsing anymore
                return
        except AttributeError:
            return

        try:
            self._fillRowData()
        except kodigui.ScreenClosed:
            # the screen closed while this ran (kodigui.WriteGuard) - this is a plain thread, not a
            # SimpleTask, so nothing else would catch it
            return

    def _fillRowData(self):
        mli = self.episodeListControl.getSelectedItem()
        if not mli or mli.getProperty("is.boundary") or mli != self.lastItem:
            # stale by the time we got here - a newer scheduleRowDataUpdate() call (or the window
            # closing) has already moved lastItem on
            return

        self.updateExtrasHeader(mli)
        self.fillRoles()
        self.fillExtras()

    def updateProperties(self):
        showTitle = self.show_ and self.show_.title or ''
        self.setBoolProperty('disable_playback', self.fromWatchlist)
        self.setBoolProperty('current_item.loaded', False)
        self.postpone_simple(self.updateBackgroundFrom, self.season or self.show_)

        self.setProperty('season.thumb', (self.season or self.show_).thumb.asTranscodedImageURL(*self.POSTER_DIM))
        self.setProperty('show.title', showTitle)
        # the heading here is the show's, and the server points an episode's clearLogo at the show anyway
        self.setProperty('clear.logo', util.clearLogoFrom(self.show_ or self.season, *self.CLEAR_LOGO_DIM))
        self.setProperty('season.title', (self.season or self.show_).title)

        # Placeholder only - checkForHeaderFocus()'s initial=True call (postSetup(), right after
        # this) replaces it immediately with whichever of updateExtrasHeader()'s two forms actually
        # matches what's focused, before the window is ever shown. Was a static "Extras \u2022 Season N"
        # here, which stayed wrong (season-only wording) for the common case of a specific episode
        # being focused, now that Extras is per-episode, not per-season (fillExtras() above).
        self.setProperty('extras.header', T(32305, 'Extras'))

        # First 2 genres, comma-joined - matches Pre-play's/Seasons' own genres.short exactly
        # (PrePlayWindow.updateProperties(), preplay.py; ShowWindow.setup(), subitems.py). Episodes
        # always inherit the show's own genres (Episode.genres property, video.py), same as the show
        # logo above, so this is computed once here rather than per-episode.
        show_genres = self.show_.genres() or []
        self.genres_short = u', '.join([g.tag for g in show_genres][:2])

    @busy.dialog()
    def updateItems(self, item=None):
        if item:
            item.setProperty('unwatched', not item.dataSource.isWatched and '1' or '')
            item.setProperty('watched', item.dataSource.isPlayed and '1' or '')
            self.setProgress(item)
            item.setProperty('progress', util.getProgressImage(item.dataSource))
            # **VIDEO_RELOAD_KW (includeExtras among them), not a bare reload() - pre-existing bug,
            # unrelated to tonight's skipChildren work: fillSeasonCardExtras()'s own comment states
            # self.season/self.show_ is "never independently re-reloaded afterward without
            # [includeExtras]" as its whole reason for not needing its own fetch - this call broke
            # that assumption, live-confirmed as the season card's Extras row going blank after
            # toggling any episode's watched state (any show, not just skipChildren ones).
            (self.season or self.show_).reload(**VIDEO_RELOAD_KW)

            if self.noRatings:
                self.populateRatings(item.dataSource, item, hide_ratings=self.hideSpoilers(item.dataSource))
            self.setUserItemInfo(item)
        else:
            self.fillEpisodes(update=True)
            if not self.cameFrom:
                VIDEO_PROGRESS.clear()

        if self.episode:
            self.episode.reload()

    def setUserItemInfo(self, mli, video=None, types=("title", "thumbnail", "summary"), watched=None,
                        fully_watched=None, hide_spoilers=None):
        video = video or mli.dataSource

        properties = {}
        methods = []
        if self.noSpoilers == "off" and not hide_spoilers:
            # no special handling
            if "title" in types:
                properties["title"] = video.title
                methods.append(("setLabel", video.title))
            if "summary" in types:
                properties["summary"] = util.summaryForBox(video.summary)

            if "thumbnail" in types:
                methods.append(("setThumbnailImage", video.thumb.asTranscodedImageURL(*self.THUMB_AR16X9_DIM)))

        else:
            hide_spoilers = hide_spoilers if hide_spoilers is not None else \
                self.hideSpoilers(video, fully_watched=fully_watched, watched=watched)
            hide_title = hide_spoilers and self.noTitles
            if "title" in types:
                tit = hide_title and T(33008, '') or video.title
                properties["title"] = tit
                methods.append(("setLabel", tit))

            if "summary" in types:
                properties["summary"] = ((hide_spoilers and self.noSummaries and T(33008, '')) or
                                         util.summaryForBox(video.summary))

            if "thumbnail" in types:
                methods.append(("setThumbnailImage",
                                video.thumb.asTranscodedImageURL(
                                    *self.THUMB_AR16X9_DIM,
                                    **self.getThumbnailOpts(video, fully_watched=fully_watched, watched=watched,
                                                            hide_spoilers=hide_spoilers)
                                )
                                ))

        for property, value in properties.items():
            mli.setProperty(property, value)

        for method, value in methods:
            getattr(mli, method)(value)

    def setItemInfo(self, video, mli):
        # video.reload(checkFiles=1)
        # Only what the template or this file reads: every ListItem call takes Kodi's GUI lock, and
        # this runs while the window is being drawn, when each one waits (step 4 in the navigation
        # review). 'background', 'season', 'episode' and 'episode.duration' were written here and
        # in createListItem() but read nowhere.
        mli.setProperty('show.title', video.grandparentTitle or (self.show_.title if self.show_ else ''))
        # noSpaces short form ("1h30m"), not durationToText's long form ("1 hr 30 mins") - matches
        # Seasons/PrePlay/Recommended's own header meta row duration format (setHeroInfo() -
        # library.py, util.durationToShortText(..., noSpaces=True)); this is the only template
        # consumer of this property (script-plex-episodes.xml.tpl's header meta row).
        mli.setProperty('duration', util.durationToShortText(video.duration.asInt(), noSpaces=True))
        mli.setProperty('video.rendering', video.videoCodecRendering)
        self.setUserItemInfo(mli, video, types=("title", "summary"))

        # "1 Sep 2026", not the old "September 1, 2026" - day/month order matches Recommended's own
        # hub-row air date format (HomeWindow.setHeroInfo(), library.py, '%d %b %Y'), but with the
        # day's leading zero dropped on request - util.cleanLeadingZeros can't do that here since its
        # regex requires a preceding space (built for stripping a zero appearing mid-string, after
        # the month name in the old format); asDatetime() with no format string returns the raw
        # datetime instead of a pre-formatted one, so dt.day (a plain int) is used directly instead.
        air_date = video.originallyAvailableAt.asDatetime()
        mli.setProperty('date', air_date and u'{0} {1}'.format(air_date.day, air_date.strftime('%b %Y')) or '')

        mli.setProperty('content.rating', video.contentRating.split('/', 1)[-1])
        mli.setProperty('genres.short', self.genres_short)
        self.populateRatings(video, mli, hide_ratings=self.hideSpoilers(video) and self.noRatings)

    def setPostReloadItemInfo(self, video, mli):
        if not self.fromWatchlist:
            self.setItemAudioAndSubtitleInfo(video, mli)
            mli.setProperty('unwatched', not video.isWatched and '1' or '')
            mli.setProperty('watched', video.isPlayed and '1' or '')
            mli.setProperty('video.res', video.resolutionString())
            mli.setProperty('video.codec', video.videoCodecString())
            mli.setProperty('video.rendering', video.videoCodecRendering)
            mli.setBoolProperty('unavailable', not video.available())

    def setItemAudioAndSubtitleInfo(self, video, mli):
        if util.getSetting('use_external_audio', False) and hasattr(type(video), 'discoverExternalAudioStreams'):
            video.discoverExternalAudioStreams()

        sas = video.selectedAudioStream()

        if sas:
            mli.setProperty('audio', sas.getTitle(metadata.apiTranslate))

        sss = video.selectedSubtitleStream(forced_subtitles_override=
                                           util.getSetting("forced_subtitles_override") and pnUtil.ACCOUNT.subtitlesForced == 0,
                                           deselect_subtitles=getNativeLanguages(util.getSetting("disable_subtitle_languages") or []))
        if sss:
            mli.setProperty('subtitles', sss.getTitle(metadata.apiTranslate))
        elif video.subtitleStreams:
            mli.setProperty('subtitles', T(32481, 'Off'))
        else:
            mli.setProperty('subtitles', T(32309, 'None'))

    def updateMediaInfoPills(self, mli):
        if self.fromWatchlist:
            return

        video_text = mli.getProperty('video.res')
        rendering = mli.getProperty('video.rendering')
        if rendering:
            video_text = u'{0} {1}'.format(video_text, rendering)

        self.resizeMediaInfoPills(video_text, mli.getProperty('audio'), mli.getProperty('subtitles'))

    def setProgress(self, mli, view_offset=None):
        video = mli.dataSource
        view_offset = view_offset if view_offset is not None else video.viewOffset.asInt()

        if view_offset:
            mli.setProperty('remainingTime', T(33615,
                                               "{time} left").format(time=video._remainingTimeString(view_offset)))
            # Drives the button row's Resume/Restart split (in place of a single Play) for a
            # part-watched episode - separate property/format from remainingTime above (which
            # feeds the header meta row's own pill, unrelated to the button row) since the Resume
            # button's label wants remainingTimeToShortText's own 90-minute-cutoff, no-space style
            # ("1h31m left"), not remainingTime's ("1h 31m left").
            mli.setBoolProperty('in.progress', True)
            mli.setProperty('resume.timeleft', T(33615, "{time} left").format(
                time=util.remainingTimeToShortText(video.duration.asInt() - view_offset)))
        else:
            mli.setProperty('remainingTime', '')
            mli.setBoolProperty('in.progress', False)
            mli.setProperty('resume.timeleft', '')

    def createListItem(self, episode):
        mli = kodigui.ManagedListItem(
            '',
            data_source=episode
        )
        self.setUserItemInfo(mli, types=("title", "thumbnail"))
        mli.setProperty('episode.number', episode.index and T(32311, 'E').format(episode.index) or '')
        mli.setProperty('unwatched', not episode.isWatched and '1' or '')
        mli.setProperty('watched', episode.isPlayed and '1' or '')
        # mli.setProperty('progress', util.getProgressImage(obj))
        return mli

    def createSeasonCardItem(self):
        """A permanent pseudo-item pinned ahead of episode 1 (EpisodesPaginator.populate()'s "left"
        branch, and the initial-page path) - renders through the exact same landscape ar16x9 art
        control every real episode card already uses (script-plex-episodes.xml.tpl), just fed the
        season's/show's own background art instead of an episode thumb (a poster-shaped card was
        tried and dropped on request - didn't read well in a landscape cell). is.boundary=True
        piggybacks on every existing "not a real, actionable episode" guard already scattered
        through this file (watched-toggle, options menu, delete, setProgress/fillRoles/
        updateMediaInfoPills, ...) for free, since none of them are meaningful for this item either
        - is.season.card=True is the narrower flag actually needed on top of that: it carves this
        item back out of the two places is.boundary normally means something MORE than "not real" -
        the boundary overlay (grey card + chevron/spinner, itemlayout/focusedlayout) and
        EpisodesPaginator.boundaryHit (which would otherwise read this as a marker to paginate on).

        data_source=None, matching every real boundary marker (kodigui.ManagedListItem('') with no
        data_source at all) - not self.season: live-confirmed crash otherwise. reloadItems() checks
        mli.dataSource truthiness on its own, with no is.boundary guard first (unlike every other
        guard in this file, which all check is.boundary before ever touching dataSource) - if this
        item is the currently-selected one when that runs, a real dataSource here made it reload
        this like a genuine episode (Episode-only methods like media()), which crashed and closed
        the whole window. Nothing else needs mli.dataSource for this item - the thumbnail/title/
        summary below all read self.season/self.show_ directly, not through the mli.

        title/summary: the header's own title label and summary textbox (script-plex-episodes.xml.tpl)
        read Container(400).ListItem.Property(title)/(summary) directly off whichever item currently
        has focus, with no is.boundary-based visibility gating - so without these, focusing the
        season card left them showing whatever the previously-focused episode had (title/summary
        are otherwise only ever set on real episode items - setUserItemInfo()/setItemInfo()). title
        also doubles as this card's own top-right season-name panel's label (same template). Starting
        point only: just these two, not the full episode metadata row (date/genre/rating/etc. -
        setItemInfo()) which doesn't have a season-level equivalent for most of its fields."""
        seasonOrShow = self.season or self.show_
        # Prefer the season's own background art over the show's, but only when the season
        # genuinely has one of its own - Plex commonly backfills a season's `art` with the show's
        # anyway, but only ever omits the attribute entirely (not just leaves it empty) when the
        # season has no distinct art of its own; see plexobjects.py's own PlexObject.get() docstring
        # for the same "attribute genuinely absent vs. present-but-empty" distinction this leans on.
        artSource = self.season if self.season and self.season.__dict__.get('art') else self.show_ or seasonOrShow
        mli = kodigui.ManagedListItem(
            '',
            thumbnailImage=artSource.art.asTranscodedImageURL(*self.THUMB_AR16X9_DIM)
        )
        mli.setBoolProperty('is.boundary', True)
        mli.setBoolProperty('is.season.card', True)
        # self.season is self.show_ for a skipChildren show (no real season layer - see this
        # window's own setup() where that flag is checked) - the header (script-plex-episodes.xml.tpl)
        # uses this to swap in Seasons' own full-size clearlogo/no-title-line treatment instead of
        # the normal reduced-clearlogo-plus-title-line one, on request: "Season X" read as a
        # redundant, wrong title line under a skipChildren show's own clearlogo, which already
        # names the show and has no real season identity to caption separately.
        mli.setBoolProperty('is.skip.children.card', self.season is self.show_)
        # show.title, not left unset like every other property on this item: the header's own
        # no-clearlogo big-title label reads this (same property a real episode's own
        # setUserItemInfo()/setItemInfo() sets), so without it that label just showed nothing for
        # this item (live-reported: "season cards for shows without clearlogos only show a
        # subtitle") - the "title" property below covers the smaller subtitle line underneath it,
        # not the title itself.
        mli.setProperty('show.title', self.show_.title if self.show_ else '')
        mli.setProperty('title', seasonOrShow.title)
        mli.setProperty('summary', util.summaryForBox(seasonOrShow.summary))

        # watched/unwatched: same properties, same meaning, as a real episode's own
        # (EpisodesPaginator.prepareListItem()) - Season has the same isFullyWatched/isWatched
        # aggregate properties a Show does (already used elsewhere in this file, e.g.
        # optionsButtonClicked()'s Mark Season Played/Unplayed entries), so the shared
        # includes/watched_indicator.xml.tpl include (already unconditionally rendered by this
        # template for every item) picks this up and shows a real watched/unwatched indicator for
        # this card too, with no template changes of its own needed beyond the season-card-specific
        # xoff it's now given (see the two watched_indicator.xml.tpl include calls below).
        #
        # unwatched.count/unwatched.count.large deliberately NOT set, unlike prepareListItem()'s own
        # copy of these two lines - this card's own watched_indicator.xml.tpl include never passes
        # with_count, so the number itself never renders anywhere; but the season-name panel's own
        # paired/standalone mask <visible> conditions (mirroring the episode-number badge's own,
        # script-plex-episodes.xml.tpl) also treat a non-empty unwatched.count as "an indicator is
        # showing" - live-confirmed bug otherwise: an episode's own unwatched.count is always empty
        # (str() on that class's unset PlexValue attribute, not "0"), so it never actually affects
        # that condition for episodes, but Season/Show's unViewedLeafCount is a real, always-nonzero-
        # when-unwatched int, so setting it here forced the paired (single-corner) mask any time the
        # season had unwatched episodes - even in indicator configs where nothing was actually
        # showing (e.g. checkmark-only style on an unwatched season).
        mli.setBoolProperty('watched', seasonOrShow.isPlayed)
        if not seasonOrShow.isWatched:
            mli.setProperty('unwatched', '1')
        return mli

    def fillEpisodes(self, update=False, from_redirect=False, timing=None):
        paginator = self.episodesPaginator
        paginator.fetchMs = paginator.itemInfoMs = paginator.itemInfoCpuMs = 0
        cpuStarted = time.thread_time()
        items = paginator.paginate()
        kodigui.markStep(timing, 'episode list')
        if timing is not None:
            timing.add('of which fetch', paginator.fetchMs)
            timing.add('setItemInfo', paginator.itemInfoMs)
            timing.add('of which CPU', paginator.itemInfoCpuMs)
            timing.add('episode list CPU', (time.thread_time() - cpuStarted) * 1000)
            timing.add('items', len(items or ()))
        if from_redirect:
            self.episodeListControl.setSelectedItemByPos(0)
        if not update:
            self.selectEpisode()
        kodigui.markStep(timing, 'select episode')
        self.reloadItems(items, with_progress=True)
        kodigui.markStep(timing, 'queue reloads')

    @close_safe
    def reloadItems(self, items, with_progress=False, skip_progress_for=None, set_item_info=False):
        if self.closing:
            return

        tasks = []
        cur_mli = self.episodeListControl.getSelectedItem()

        if cur_mli and cur_mli.dataSource:
            # handle our currently selected episode first, synchronously, then use background tasks to load the remaining
            # episode's details
            item_progress = with_progress
            if skip_progress_for:
                item_progress = False if cur_mli.dataSource.ratingKey in skip_progress_for else with_progress

            try:
                cur_mli.dataSource.reload(checkFiles=1, includeChapters=1, fromMediaChoice=cur_mli.dataSource.mediaChoice is not None)
                util.DEBUG_LOG("Episodes: Sync-loading currently selected item: {}", cur_mli.dataSource)
                self._reloadItem(cur_mli, with_progress=item_progress, set_item_info=set_item_info)
            except kodigui.ScreenClosed:
                # the screen closed while this ran (kodigui.WriteGuard) - not missing data
                return
            except:
                util.ERROR("No data - deleted or server disconnected?", notify=True, time_ms=5000)
                self.doClose()
                return
            util.DEBUG_LOG("Episodes: Currently selected item loaded")
            self.currentItemLoaded = True
            self.lastItem = cur_mli
            self.updateMediaInfoPills(cur_mli)
            self.setBoolProperty('current_item.loaded', True)
        elif cur_mli and cur_mli.getProperty("is.boundary"):
            # Season card (createSeasonCardItem() - has no dataSource, deliberately) selected
            # initially - e.g. entering a completely unwatched season from Seasons, where
            # _defaultEpisode() deliberately lands on the season card rather than episode 1. There's
            # no per-item data to sync-load here, but currentItemLoaded/current_item.loaded is the
            # only signal episodeListClicked()'s own load-wait and the button row's Play/Resume/
            # Restart visibility have for "is this window ready" - leaving it permanently False
            # (the pre-existing behaviour, this branch didn't exist before) silently broke both:
            # live-confirmed clicking to play timed out and never honored the action, and Play
            # never left its 306/loading state, for as long as the season card stayed selected.
            self.currentItemLoaded = True
            self.lastItem = cur_mli
            self.setBoolProperty('current_item.loaded', True)
            # Live-confirmed follow-up bug from setting self.lastItem here: checkForHeaderFocus()'s
            # own season-card branch only calls updateExtrasHeader() when mli != self.lastItem -
            # already true by the time its own initial=True call runs (postSetup(), right after
            # _setup() which is what calls reloadItems(), this method), so that branch always found
            # them equal and skipped on a genuine cold start landing on the season card, leaving
            # updateProperties()'s raw "Extras" placeholder in place instead of a real computed
            # value - correct-looking by coincidence for a skipChildren show (no season to name),
            # wrong for a real one (missing "• Season N" until the user moved off and back, at
            # which point self.lastItem no longer matched and it finally computed a real value).
            # fillSeasonCardExtras()/fillRoles() don't have the same gap - _setup()'s own
            # batch_simple() call already fills those independently of this branch.
            self.updateExtrasHeader(cur_mli)
            # Same gap, same fix, for the button row's Play/Resume state - checkForHeaderFocus()'s
            # own call to this is behind that same mli != self.lastItem check.
            self.updateSeasonCardPlayState(cur_mli)
        else:
            util.LOG("Episodes: There's no current item to be loaded, something's wrong.")

        if not self.hadUserInteraction:
            self.setCondFocusId(self.EPISODE_LIST_ID)

        fetch = []
        for mli in items:
            if not mli.dataSource:
                continue

            if mli == cur_mli:
                continue

            item_progress = with_progress
            if skip_progress_for:
                item_progress = False if mli.dataSource.ratingKey in skip_progress_for else with_progress

            fetch.append((mli.dataSource, item_progress))

        task = EpisodesReloadTask().setup(fetch, self.reloadItemsCallback, set_item_info=set_item_info)
        self.tasks.add(task)
        tasks.append(task)

        backgroundthread.BGThreader.addTasks(tasks)

    def getPlayButtonID(self, mli, base=None):
        # Resume, not Play, is the button row's actual default target for a part-watched episode
        # now (base itself, PLAY_BUTTON_DISABLED_ID during a still-loading state, takes priority
        # over this either way - in.progress isn't known yet at that point). No more +1000 variant
        # (single button row now, on request - the multi-version group is gone, its own version
        # picker replaced by Settings' new Video entry - playersettings.py).
        if not base and mli.getProperty('in.progress'):
            base = self.RESUME_BUTTON_ID
        return base or self.PLAY_BUTTON_ID

    @close_safe
    def _reloadItem(self, mli, with_progress=False, set_item_info=False):
        if self.closing:
            return

        episode = mli.dataSource
        if not episode.mediaChoice:
            episode.setMediaChoice()

        try:
            self.setPostReloadItemInfo(episode, mli)
            if set_item_info:
                self.setUserItemInfo(mli)
        except kodigui.ScreenClosed:
            # the screen closed while this ran (kodigui.WriteGuard) - not missing data
            return
        except:
            util.ERROR("No data - deleted or server disconnected?", notify=True, time_ms=5000)
            self.doClose()
            return

        if with_progress:
            self.episodesPaginator.prepareListItem(None, mli)

    @close_safe
    def reloadItemsCallback(self, task, episodes, set_item_info=False):
        if self.closing:
            return

        for ep, with_progress in episodes:
            # todo: implement hashmap over datasource:mli?
            mli = self.episodeListControl.getListItemByDataSource(ep)
            self._reloadItem(mli, with_progress=with_progress, set_item_info=set_item_info)
        try:
            task.episodes = None
            self.tasks.remove(task)
            del task
        except:
            pass

    def updateExtrasHeader(self, mli):
        # Was a static "Extras • Season N" set once in updateProperties() - stayed wrong (season-
        # only wording) for the common case of a specific episode being focused, now that Extras is
        # per-episode, not per-season (fillExtras() below). Season.index/Episode.index (via T()'s
        # own .format() convention - see the T(32304, 'Episode')/T(32303, 'Season') call sites
        # elsewhere in this file) are already known synchronously off mli/self.season, no fetch
        # needed, so this updates right alongside the immediate clear in checkForHeaderFocus() -
        # same timing as that clear, not gated behind the Roles/Extras debounce.
        if mli.getProperty("is.season.card"):
            if self.season is self.show_:
                # skipChildren show (reset()'s own comment) - self.season is the show itself, not a
                # real season, so there's no season number to name here - just "Extras", matching
                # the show-flavored title/extras the season card already displays for these.
                self.setProperty('extras.header', T(32305, 'Extras'))
            else:
                self.setProperty('extras.header', u'{0} • {1}'.format(
                    T(32305, 'Extras'), T(32303, 'Season').format(self.season.index)))
        else:
            self.setProperty('extras.header', u'{0} • {1}'.format(
                T(32305, 'Extras'), T(32304, 'Episode').format(mli.dataSource.index)))

    def fillExtras(self):
        mli = self.episodeListControl.getSelectedItem()
        if not mli:
            self.extraListControl.reset()
            return False

        if mli.getProperty("is.boundary"):
            if mli.getProperty("is.season.card"):
                # _setup()'s postponed batch_simple() call to this method (not the season-card
                # branch in checkForHeaderFocus()) is what actually performs the first fill in
                # practice, on a background thread with no ordering guarantee against
                # postSetup()'s own initial checkForHeaderFocus() call (which checkForHeaderFocus()
                # itself may skip anyway - see its own self.tasks guard comment). Routing here too,
                # not just there, means whichever one actually wins the race still lands on the
                # right data instead of stale/wrong episode extras.
                return self.fillSeasonCardExtras()
            self.extraListControl.reset()
            return False

        ds = mli.dataSource

        if not ds.extras and ds.ratingKey not in self._extrasFetched:
            # Unlike Roles, an episode's own listing fetch (EpisodesPaginator.getData()) never
            # includes Extras - only a dedicated per-episode fetch does. Can't rely on ds.extras'
            # own emptiness + PlexObject.__getattr__'s .NA marker (plexobjects.py) to mean "never
            # attempted" here, the way preplay.py's fillExtras() does - reloadItems()/
            # EpisodesReloadTask (this file) reload every paginated-in episode's dataSource for
            # progress/media-choice/chapters without includeExtras, which resets .extras to a real
            # (non-NA) empty PlexVideoItemList almost immediately, well before this ever runs.
            # self._extrasFetched (set in __init__) is our own record instead, keyed by ratingKey
            # (a PlexValue - a str subclass, so value-hashed and stable across reloads) - immune to
            # that clobbering.
            ds.fetchExternalExtras()
            self._extrasFetched.add(ds.ratingKey)

        if not ds.extras:
            self.extraListControl.reset()
            return False

        return self._fillExtrasList(ds.extras)

    def fillSeasonCardExtras(self):
        # Season only, deliberately no show fallback (unlike createSeasonCardItem()'s art source) -
        # an explicit ask: the season card's Extras row should go blank rather than show the show's
        # extras when the season itself has none. self.season is already reloaded with
        # includeExtras (_setup()'s VIDEO_RELOAD_KW reload of self.season or self.show_) and, unlike
        # episode dataSources, is never independently re-reloaded afterward without it - so no fetch
        # (or the fillExtras() memoization above) is needed here at all.
        if not self.season or not self.season.extras:
            self.extraListControl.reset()
            return False

        return self._fillExtrasList(self.season.extras)

    def _fillExtrasList(self, extras):
        items = []
        idx = 0

        for extra in extras:
            mli = kodigui.ManagedListItem(
                extra.title or '',
                metadata.EXTRA_MAP.get(extra.extraType.asInt(), ''),
                thumbnailImage=extra.thumb.asTranscodedImageURL(*self.EXTRA_DIM),
                data_source=extra
            )

            if mli:
                mli.setProperty('index', str(idx))
                mli.setProperty(
                    'thumb.fallback', 'script.plex/thumb_fallbacks/{0}.png'.format(extra.type in ('show', 'season', 'episode') and 'show' or 'movie')
                )
                items.append(mli)
                idx += 1

        if not items:
            self.extraListControl.reset()
            return False

        self.extraListControl.reset()
        self.extraListControl.addItems(items)
        return True

    def fillRoles(self):
        items = []
        idx = 0

        mli = self.episodeListControl.getSelectedItem()
        if not mli or mli.getProperty("is.boundary"):
            # The season card (also a boundary marker, see createSeasonCardItem()'s own comment)
            # has no dataSource - can be the selected item here if it was given initial focus
            # (EpisodesPaginator.populate()'s "nothing watched" case) and this runs before the
            # user has moved off it, eg. via _setup()'s postponed batch_simple() call.
            self.rolesListControl.reset()
            return False

        ds = mli.dataSource

        if not ds.roles:
            self.rolesListControl.reset()
            return False

        roles = ds.combined_roles if util.getUserSetting('show_directors', True) else ds.roles

        for role in roles:
            mli = kodigui.ManagedListItem(role.tag, role.role or
                                          util.TRANSLATED_ROLES[role.translated_role],
                                          thumbnailImage=role.thumb.asTranscodedImageURL(*self.ROLES_DIM),
                                          data_source=role)
            mli.setProperty('index', str(idx))
            items.append(mli)
            idx += 1

        if not items:
            return False

        self.rolesListControl.reset()
        self.rolesListControl.addItems(items)
        return True
