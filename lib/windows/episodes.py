from __future__ import absolute_import

import requests.exceptions
import copy
import json
from kodi_six import xbmc
from kodi_six import xbmcgui
from collections import OrderedDict

from plexnet import plexapp, playlist, plexplayer, plexlibrary, util as pnUtil, plexobjects

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
    thumbFallback = 'script.plex/thumb_fallbacks/show.png'
    _currentEpisode = None

    def reset(self):
        super(EpisodesPaginator, self).reset()
        self._currentEpisode = None

    def wrap(self, mli, last_mli, action):
        # Episodes don't round-robin: the sidebar rail now occupies the left edge, so looping
        # back to the last episode when pressing left past the first (or vice versa) would fight
        # with escaping into the rail. The skin's onleft/onright on control 400 already provide a
        # hard stop on the right and hand off to the sidebar (id 9000) once truly at the first
        # episode - see that control's own onleft comment in script-plex-episodes.xml.tpl.
        return None

    def getData(self, offset, amount):
        return (self.parentWindow.season or self.parentWindow.show_).episodes(offset=offset, limit=amount)

    def createListItem(self, data):
        mli = super(EpisodesPaginator, self).createListItem(data)
        self.parentWindow.setItemInfo(data, mli)
        return mli

    def prepareListItem(self, data, mli):
        mli.setBoolProperty('watched', mli.dataSource.isFullyWatched)
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
            return super(EpisodesPaginator, self).initialPage

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

        return episodes

    def selectItem(self, amount, more_left=False, more_right=False, items=None):
        if not super(EpisodesPaginator, self).selectItem(amount, more_left):
            if (self._currentEpisode and items) and self._currentEpisode in items:
                self.control.selectItem(items.index(self._currentEpisode) + (1 if more_left else 0))


class RelatedPaginator(pagination.BaseRelatedPaginator):
    def getData(self, offset, amount):
        return self.parentWindow.show_.getRelated(offset=offset, limit=amount)


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
    RELATED_DIM = util.scaleResolution(268, 402)
    EXTRA_DIM = util.scaleResolution(329, 185)
    ROLES_DIM = util.scaleResolution(334, 334)
    CLEAR_LOGO_DIM = util.scaleResolution(784, 106)

    LIST_OPTIONS_BUTTON_ID = 111

    EPISODE_LIST_ID = 400
    SEASONS_LIST_ID = 205
    ROLES_LIST_ID = 402
    EXTRA_LIST_ID = 403
    RELATED_LIST_ID = 404

    OPTIONS_GROUP_ID = 200
    PLAYER_STATUS_BUTTON_ID = 204

    MAIN_BUTTON_GROUP_ID = 300
    PLAY_BUTTON_ID = 301
    PLAY_BUTTON_DISABLED_ID = 306
    SHUFFLE_BUTTON_ID = 302
    OPTIONS_BUTTON_ID = 303
    INFO_BUTTON_ID = 304
    SETTINGS_BUTTON_ID = 305
    MEDIA_BUTTON_ID = 307

    SEASONS_CONTROL_ATTR = "seasonsListControl"

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

    def reset(self, episode, season=None, show=None):
        self.episode = episode
        self.initialEpisode = episode
        self.season = season if season is not None else self.episode.season()
        try:
            self.show_ = show or (self.episode or self.season).show().reload(includeExtras=1, includeExtrasCount=10,
                                                                             includeOnDeck=1)
        except IndexError:
            raise util.NoDataException

        self.initialized = False
        self.closing = False
        self.parentList = None
        self.episodesPaginator = None
        self.relatedPaginator = None
        self.seasons = None
        self.manuallySelected = False
        self.manuallySelectedSeason = False
        self.hadUserInteraction = False
        self.currentItemLoaded = False
        self.lastItem = None
        self.lastFocusID = None
        self.lastNonOptionsFocusID = None
        self.openedWithAutoPlay = False
        self.useBGM = False
        self.debouncing = False
        PlaybackBtnMixin.reset(self)

    @busy.dialog(delay_time=1.0)
    def doClose(self, **kw):
        if self.closing:
            util.LOG("Episodes: Already closing")
            return
        self.closing = True
        self.episodesPaginator = None
        self.relatedPaginator = None
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
        self.episodeListControl = kodigui.ManagedControlList(self, self.EPISODE_LIST_ID, 5)
        self.initMediaInfoPillControls()

        self.seasonsListControl = kodigui.ManagedControlList(self, self.SEASONS_LIST_ID, 5)
        self.rolesListControl = kodigui.ManagedControlList(self, self.ROLES_LIST_ID, 5)
        self.extraListControl = kodigui.ManagedControlList(self, self.EXTRA_LIST_ID, 5)
        self.relatedListControl = kodigui.ManagedControlList(self, self.RELATED_LIST_ID, 5)

        self.sectionList = kodigui.ManagedControlList(self, self.SECTION_LIST_ID, 15)
        self.buildSectionList()
        self.displayServerAndUser()

        VIDEO_PROGRESS.clear()

        if not self.openedWithAutoPlay:
            # we may have set up the hooks before
            self._setup_hooks()

        if self.show_ and not util.getSetting("slow_connection") and \
                (not self.cameFrom or self.cameFrom not in (self.show_.ratingKey, "postplay")) and \
                not self.openedWithAutoPlay:
            self.themeMusicInit(self.show_)

        self._setup()
        self.postSetup(select_play_button=False)

    def doAutoPlay(self, blind=False):
        # First reload the video to get all the other info
        self.initialEpisode.reload(checkFiles=1, **VIDEO_RELOAD_KW)

        # We're not hitting onFirstInit when autoplaying from home, setup hooks here, so we can grab video progress
        self._setup_hooks()
        self.openedWithAutoPlay = True
        return self.playButtonClicked(force_episode=self.initialEpisode, from_auto_play=True, start_over=self.startOver)

    def onFirstInit(self):
        self._onFirstInit()

        self.openedWithAutoPlay = False

    @busy.dialog()
    def onReInit(self):
        self.playBtnClicked = False
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
            self.relatedListControl.reset()
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
                             selectSeason=self.season, update=True, do_focus=not self.manuallySelectedSeason)

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

    def _setup(self, from_redirect=False):
        (self.season or self.show_).reload(checkFiles=1, **VIDEO_RELOAD_KW)

        if not self.episodesPaginator:
            self.episodesPaginator = EpisodesPaginator(self.episodeListControl,
                                                       leaf_count=int(self.season.leafCount) if self.season else 0,
                                                       parent_window=self)

        if not self.relatedPaginator:
            self.relatedPaginator = RelatedPaginator(self.relatedListControl, leaf_count=int(self.show_.relatedCount),
                                                     parent_window=self)

        self.watchlist_setup(self.show_)
        self.updateProperties()
        self.setBoolProperty("initialized", True)
        self.fillEpisodes(from_redirect=from_redirect)

        # postpone less important tasks
        self.batch_simple([
            (self.fillSeasons, (self.show_,), dict(seasonsFilter=lambda x: len(x) > 1, selectSeason=self.season)),
            (self.fillExtras, None, None),
            (self.fillRelated, None, None),
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
                            # ep has progress
                            mli.setProperty('watched', '')
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
                    while self.episodeListControl.getSelectedPos() != mli.pos() and tries < util.MONITOR.waitAmount(4, interval=0.05):
                        util.MONITOR.waitFor(0.05)
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
        elif self.season.isFullyWatched and not self.episode:
            self.episodeListControl.selectItem(mli.pos())

            tries = 0
            while self.episodeListControl.getSelectedPos() != mli.pos() and tries < util.MONITOR.waitAmount(4, interval=0.05):
                util.MONITOR.waitFor(0.05)
                self.episodeListControl.selectItem(mli.pos())
                tries += 1

            self.episodesPaginator.setEpisode(mli.dataSource)
            self.lastItem = mli

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
            util.MONITOR.waitFor(0.05)

        self.episode = None

    def onAction(self, action):
        try:
            if self.debouncing:
                util.DEBUG_LOG("Already waiting to work on previous input, debouncing.")
                return

            controlID = self.getFocusId()

            if controlID == self.SECTION_LIST_ID:
                self.checkSectionItem(action=action)

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

            if controlID == self.SEASONS_LIST_ID and action in (xbmcgui.ACTION_MOVE_LEFT, xbmcgui.ACTION_MOVE_RIGHT):
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

            elif controlID == self.RELATED_LIST_ID:
                if self.relatedPaginator and self.relatedPaginator.boundaryHit:
                    self.relatedPaginator.paginate()
                    return
                elif action in (xbmcgui.ACTION_MOVE_LEFT, xbmcgui.ACTION_MOVE_RIGHT):
                    self.updateBackgroundFrom(self.relatedListControl.getSelectedItem().dataSource)

            elif self.isWatchedAction(action) and xbmc.getCondVisibility('ControlGroup({}).HasFocus(0)'.format(self.MAIN_BUTTON_GROUP_ID)):
                mli = self.episodeListControl.getSelectedItem()
                if not mli or mli.getProperty("is.boundary"):
                    return

                self.toggleWatched(mli)
                self.selectEpisode()
                return

            if controlID == self.LIST_OPTIONS_BUTTON_ID and self.checkOptionsAction(action):
                return
            elif action == xbmcgui.ACTION_CONTEXT_MENU:
                if controlID in (self.PLAY_BUTTON_ID, self.PLAY_BUTTON_ID + 1000) and util.getSetting('assume_resume'):
                    self.playButtonClicked(force_resume_menu=True)
                    return

                if not xbmc.getCondVisibility('ControlGroup({0}).HasFocus(0)'.format(self.OPTIONS_GROUP_ID)):
                    self.lastNonOptionsFocusID = self.lastFocusID
                    self.setFocusId(self.OPTIONS_GROUP_ID)
                    return
                else:
                    if self.lastNonOptionsFocusID:
                        self.setCondFocusId(self.lastNonOptionsFocusID)
                        self.lastNonOptionsFocusID = None
                        return

            elif action == xbmcgui.ACTION_NAV_BACK:
                if (not xbmc.getCondVisibility('ControlGroup({0}).HasFocus(0)'.format(
                        self.OPTIONS_GROUP_ID)) or not controlID) and \
                        not util.addonSettings.fastBack:
                    if self.getProperty('on.extras'):
                        self.setCondFocusId(self.OPTIONS_GROUP_ID)
                        return

            if action in (xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_PREVIOUS_MENU):
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

    def checkOptionsAction(self, action):
        if action == xbmcgui.ACTION_MOVE_UP:
            mli = self.episodeListControl.getSelectedItem()
            if not mli or mli.getProperty("is.boundary"):
                return False
            pos = mli.pos() - 1
            if self.episodeListControl.positionIsValid(pos):
                self.setCondFocusId(self.EPISODE_LIST_ID)
                self.episodeListControl.selectItem(pos)
            return True
        elif action == xbmcgui.ACTION_MOVE_DOWN:
            mli = self.episodeListControl.getSelectedItem()
            if not mli or mli.getProperty("is.boundary"):
                return False
            pos = mli.pos() + 1
            if self.episodeListControl.positionIsValid(pos):
                self.setCondFocusId(self.EPISODE_LIST_ID)
                self.episodeListControl.selectItem(pos)
            return True

        return False

    def onClick(self, controlID):
        if controlID == self.SECTION_LIST_ID:
            self.sectionClicked()
        elif controlID == self.EPISODE_LIST_ID:
            self.episodeListClicked()
        elif controlID == self.PLAYER_STATUS_BUTTON_ID:
            self.showAudioPlayer()
        elif controlID in (self.PLAY_BUTTON_ID, self.PLAY_BUTTON_ID+1000):
            self.playButtonClicked()
        elif controlID in (self.SHUFFLE_BUTTON_ID, self.SHUFFLE_BUTTON_ID+1000):
            self.shuffleButtonClicked()
        elif controlID in (self.OPTIONS_BUTTON_ID, self.OPTIONS_BUTTON_ID+1000):
            self.optionsButtonClicked()
        elif controlID in (self.SETTINGS_BUTTON_ID, self.SETTINGS_BUTTON_ID+1000):
            self.settingsButtonClicked()
        elif controlID == self.MEDIA_BUTTON_ID+1000:
            self.mediaButtonClicked()
        elif controlID in (self.INFO_BUTTON_ID, self.INFO_BUTTON_ID+1000):
            self.infoButtonClicked()
        elif controlID == self.SEASONS_LIST_ID:
            if self.fromWatchlist:
                return
            mli = self.seasonsListControl.getSelectedItem()
            if not mli:
                return
            item = mli.dataSource
            if item != self.season:
                self.switchSeason(item)
            else:
                self.setCondFocusId(self.EPISODE_LIST_ID)
        elif controlID == self.ROLES_LIST_ID:
            if not self.roleClicked():
                return
        elif controlID == self.EXTRA_LIST_ID:
            self.openItem(self.extraListControl)
        elif controlID == self.RELATED_LIST_ID:
            self.openItem(self.relatedListControl)

    def onFocus(self, controlID):
        self.reselectActiveSection(controlID, self.lastFocusID)
        self.lastFocusID = controlID

        if controlID == self.SECTION_LIST_ID:
            self.checkSectionItem()

        # we allow hidden focus on the play button when we're in multiple video files mode. in that case focus the
        # correct play button after the hidden one has been focused
        if controlID == self.PLAY_BUTTON_ID and xbmc.getCondVisibility(
                '!String.IsEmpty(Container(400).ListItem.Property(media.multiple))'):
            self.setCondFocusId(self.PLAY_BUTTON_ID + 1000)
            return

        if 399 < controlID < 500:
            self.setProperty('hub.focus', str(controlID - 400))
            if controlID == self.RELATED_LIST_ID:
                self.updateBackgroundFrom(self.relatedListControl.getSelectedItem().dataSource)
        # the episode row counts as "not on extras" too, now that it's the screen's default focus target -
        # otherwise this fires the very moment the window opens instead of only once focus goes deeper,
        # into roles/extras/related
        if controlID == self.EPISODE_LIST_ID or xbmc.getCondVisibility(
                'ControlGroup(50).HasFocus(0) + [ControlGroup(300).HasFocus(0) | ControlGroup(1300).HasFocus(0)]'):
            self.setProperty('on.extras', '')
            # hub.focus (set above, only for controlIDs 400-499) is otherwise never reset once focus
            # leaves the roles/extras/related row stack for the button row - it's not in that range, so
            # it'd keep whatever value the last-focused row left it at. The row-collapse slide
            # animations on group 50 (script-plex-episodes.xml.tpl) key off hub.focus, not on.extras, so
            # without this they'd stay collapsed even after on.extras clears and the header reappears -
            # the header (and the now-fully-visible episode row) would show while the logo/title/summary
            # block above it stays scrolled out of view until focus reaches the episode row and resets
            # hub.focus itself.
            self.setProperty('hub.focus', '0')
        elif xbmc.getCondVisibility('ControlGroup(50).HasFocus(0) + !ControlGroup(300).HasFocus(0) + !ControlGroup(1300).HasFocus(0)'):
            self.setProperty('on.extras', '1')

    def toggleWatched(self, mli=None, item=None, state=None, **kw):
        if not mli and not item:
            return

        item = item or mli.dataSource
        watched = super(EpisodesWindow, self).toggleWatched(item, state=state, **VIDEO_RELOAD_KW)
        if watched is None:
            return

        self.show_ = (self.episode or self.season).show().reload(includeExtras=1, includeExtrasCount=10,
                                                                 includeOnDeck=1)
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

        self.processCommand(opener.open(item, came_from=came_from,
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
            y -= 500

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

    def switchSeason(self, season):
        # reload this window in place rather than opening a new one on top of it - the season tab bar makes
        # switching seasons frequent, and stacking a window per swap would take that many Back presses to undo
        self.episode = None
        self.season = season
        self.manuallySelectedSeason = True
        self.setup()

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

    def playButtonClicked(self, shuffle=False, force_episode=None, from_auto_play=False, force_resume_menu=False,
                          start_over=False):
        if shuffle:
            seasonOrShow = self.season or self.show_
            items = seasonOrShow.all()
            pl = playlist.LocalPlaylist(items, seasonOrShow.getServer())

            pl.shuffle(shuffle, first=True)
            videoplayer.play(play_queue=pl)
            return True

        else:
            return self.episodeListClicked(force_episode=force_episode, from_auto_play=from_auto_play,
                                           force_resume_menu=force_resume_menu, start_over=start_over)

    def shuffleButtonClicked(self):
        self.playButtonClicked(shuffle=True)

    def settingsButtonClicked(self):
        mli = self.episodeListControl.getSelectedItem()
        if not mli or mli.getProperty("is.boundary"):
            return

        episode = mli.dataSource

        if not episode.mediaChoice:
            playerObject = plexplayer.PlexPlayer(episode)
            playerObject.build()
        playersettings.showDialog(video=episode, non_playback=True)
        self.setItemAudioAndSubtitleInfo(episode, mli)

    def infoButtonClicked(self):
        mli = self.episodeListControl.getSelectedItem()
        if not mli or mli.getProperty("is.boundary"):
            return

        episode = mli.dataSource

        if episode.index:
            subtitle = u'{0} {1}'.format(T(32303, 'Season').format(episode.parentIndex),
                                         T(32304, 'Episode').format(episode.index))
        else:
            subtitle = episode.originallyAvailableAt.asDatetime('%B %d, %Y')

        hide_spoilers = self.hideSpoilers(episode)

        opener.handleOpen(
            info.InfoWindow,
            title=hide_spoilers and self.noTitles and T(33008, '') or episode.title,
            sub_title=subtitle,
            thumb=episode.thumb,
            thumb_opts=self.getThumbnailOpts(episode, hide_spoilers=hide_spoilers),
            thumb_fallback='script.plex/thumb_fallbacks/show.png',
            info=(hide_spoilers and self.noSummaries and T(33008, '')) or episode.summary,
            background=self.getProperty('background'),
            is_16x9=True,
            video=episode
        )
        self.cameFrom = "info"

    def episodeListClicked(self, force_episode=None, from_auto_play=False, force_resume_menu=False,
                           start_over=False):

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
            if not mli or mli.getProperty("is.boundary"):
                return

            episode = mli.dataSource
        else:
            episode = force_episode

        if not episode.available():
            util.messageDialog(T(32312, 'unavailable'), T(32332, 'This item is currently unavailable.'))
            return

        resume = False
        if episode.viewOffset.asInt() and not start_over:
            if not util.getSetting('assume_resume') or force_resume_menu:
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
                self.processCommand(videoplayer.play(play_queue=pl, resume=resume, bgm=self.useBGM))
                self.playBtnClicked = False
                return True

            self.processCommand(videoplayer.play(video=episode, resume=resume, bgm=self.useBGM))
            self.playBtnClicked = False
            return True
        except util.NoDataException:
            util.ERROR("No data - deleted or server disconnected?", notify=True, time_ms=5000)
            self.doClose()

    def optionsButtonClicked(self, from_item=False):
        options = []

        mli = self.episodeListControl.getSelectedItem()

        if mli and not mli.getProperty("is.boundary"):
            inProgress = mli.dataSource.viewOffset.asInt()
            if inProgress and util.getSetting('assume_resume'):
                options.append({'key': 'play_startover', 'display': T(32317, 'Play from beginning')})
                options.append(dropdown.SEPARATOR)

            if not mli.dataSource.isWatched or inProgress:
                options.append({'key': 'mark_watched', 'display': T(32319, 'Mark Played')})
            if mli.dataSource.isWatched or inProgress:
                options.append({'key': 'mark_unwatched', 'display': T(32318, 'Mark Unplayed')})

            # if True:
            #     options.append({'key': 'add_to_playlist', 'display': '[COLOR FF808080]Add To Playlist[/COLOR]'})

        if xbmc.getCondVisibility('Player.HasAudio + MusicPlayer.HasNext'):
            options.append({'key': 'play_next', 'display': T(32325, 'Play Next')})

        if self.season:
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

            if mli.dataSource.server.allowsMediaDeletion:
                options.append({'key': 'delete', 'display': T(32322, 'Delete')})

        # if xbmc.getCondVisibility('Player.HasAudio') and self.section.TYPE == 'artist':
        #     options.append({'key': 'add_to_queue', 'display': 'Add To Queue'})

        if options:
            options.append(dropdown.SEPARATOR)

        options.append({'key': 'to_show', 'display': T(32323, 'Go To Show')})
        options.append({'key': 'to_section', 'display': T(32324, u'Go to {0}').format(
            self.show_.getLibrarySectionTitle())})

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

        if choice['key'] == 'play_next':
            xbmc.executebuiltin('PlayerControl(Next)')
        elif choice['key'] == 'mark_watched':
            self.toggleWatched(mli, state=True)
        elif choice['key'] == 'mark_unwatched':
            self.toggleWatched(mli, state=False)
        elif choice['key'] == 'mark_season_watched':
            self.toggleWatched(item=self.season, state=True)
        elif choice['key'] == 'mark_season_unwatched':
            self.toggleWatched(item=self.season, state=False)
        elif choice['key'] == 'to_show':
            self.cameFrom = "show"
            self.processCommand(opener.open(
                mli.dataSource.show().ratingKey,
                came_from=mli.dataSource.season().ratingKey,
                server=mli.dataSource.server,
                entry_section_id=self.entrySectionId,
                entry_from_watchlist=self.entryFromWatchlist)
            )
        elif choice['key'] == 'to_section':
            self.cameFrom = "library"
            section = plexlibrary.LibrarySection.fromFilter(mli.dataSource.show())
            self.processCommand(opener.sectionClicked(section,
                came_from=mli.dataSource.show().ratingKey)
            )
        elif choice['key'] == 'delete':
            self.delete(mli.dataSource)
            self.episodesPaginator.leafCount = int(self.season.leafCount) if self.season else 0
            self.fillEpisodes()
        elif choice['key'] == 'playback_settings':
            self.playbackSettings(self.show_, pos, bottom)
        elif choice['key'] == 'refresh':
            mli.dataSource.refresh()
            self.updateItems(mli)
        elif choice['key'] == 'play_startover':
            self.episodeListClicked(start_over=True)
        elif choice["key"] == "cache_reset":
            try:
                util.DEBUG_LOG('Clearing requests cache for {}...', mli.dataSource)
                mli.dataSource.clearCache()
                mli.dataSource.reload()
                self.updateItems(mli)
            except Exception as e:
                util.DEBUG_LOG("Couldn't clear cache: {}", e)

    def mediaButtonClicked(self):
        options = []
        mli = self.episodeListControl.getSelectedItem()
        ds = mli.dataSource
        for media in ds.media:
            ind = ''
            if ds.mediaChoice and media.id == ds.mediaChoice.media.id:
                ind = 'script.plex/home/device/check.png'
            options.append({'key': media, 'display': media.versionString(), 'indicator': ind})
        choice = dropdown.showDropdown(options, header=T(32450, 'Choose Version'), with_indicator=True)
        if not choice:
            return False

        for media in ds.media:
            media.set('selected', '')

        ds.setMediaChoice(choice['key'])
        choice['key'].set('selected', 1)
        pnUtil.INTERFACE.playbackManager(mli.dataSource, key="media_version", value=choice['key'].id)
        self.setPostReloadItemInfo(ds, mli)

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
        # don't continue if we're still waiting for tasks
        if self.tasks or not self.episodesPaginator:
            if self.tasks and not initial:
                util.DEBUG_LOG("Episodes: Moving too fast through paginator, throttling.")
            return

        if self.episodesPaginator.boundaryHit:
            items = self.episodesPaginator.paginate()
            self.reloadItems(items)
            return True

        mli = self.episodeListControl.getSelectedItem()
        if not mli or mli.getProperty("is.boundary"):
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
            self.fillRoles()
            self.updateMediaInfoPills(mli)

        if action in (xbmcgui.ACTION_MOVE_UP, xbmcgui.ACTION_PAGE_UP):
            if mli.getProperty('is.header'):
                xbmc.executebuiltin('Action(up)')
        if action in (xbmcgui.ACTION_MOVE_DOWN, xbmcgui.ACTION_PAGE_DOWN, xbmcgui.ACTION_MOVE_LEFT,
                      xbmcgui.ACTION_MOVE_RIGHT):
            if not initial and action in (xbmcgui.ACTION_MOVE_LEFT, xbmcgui.ACTION_MOVE_RIGHT):
                self.manuallySelected = True
            if mli.getProperty('is.header'):
                xbmc.executebuiltin('Action(down)')

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

        if self.season:
            self.setProperty('extras.header', u'{0} \u2022 {1}'.format(T(32305, 'Extras'),
                                                                       T(32303, 'Season').format(self.season.index)))
        else:
            self.setProperty('extras.header', u'Extras')

        self.setProperty('related.header', T(32306, 'Related Shows'))
        self.genre = self.show_.genres() and self.show_.genres()[0].tag or ''

    @busy.dialog()
    def updateItems(self, item=None):
        if item:
            item.setProperty('unwatched', not item.dataSource.isWatched and '1' or '')
            item.setProperty('watched', item.dataSource.isFullyWatched and '1' or '')
            self.setProgress(item)
            item.setProperty('progress', util.getProgressImage(item.dataSource))
            (self.season or self.show_).reload()

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
                properties["summary"] = video.summary.strip().replace('\t', ' ')

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
                                         video.summary.strip().replace('\t', ' '))

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
        mli.setProperty('background', util.backgroundFromArt(video.art, width=self.width, height=self.height))
        mli.setProperty('show.title', video.grandparentTitle or (self.show_.title if self.show_ else ''))
        mli.setProperty('duration', util.durationToText(video.duration.asInt()))
        mli.setProperty('video.rendering', video.videoCodecRendering)
        self.setUserItemInfo(mli, video, types=("title", "summary"))

        if video.index:
            mli.setProperty('season', T(32303, 'Season').format(video.parentIndex))
            mli.setProperty('episode', T(32304, 'Episode').format(video.index))
        else:
            mli.setProperty('season', '')
            mli.setProperty('episode', '')

        mli.setProperty('date', util.cleanLeadingZeros(video.originallyAvailableAt.asDatetime('%B %d, %Y')))

        # mli.setProperty('related.header', 'Related Shows')
        mli.setProperty('content.rating', video.contentRating.split('/', 1)[-1])
        mli.setProperty('genre', self.genre)
        self.populateRatings(video, mli, hide_ratings=self.hideSpoilers(video) and self.noRatings)

    def setPostReloadItemInfo(self, video, mli):
        if not self.fromWatchlist:
            self.setItemAudioAndSubtitleInfo(video, mli)
            mli.setProperty('unwatched', not video.isWatched and '1' or '')
            mli.setProperty('watched', video.isFullyWatched and '1' or '')
            mli.setProperty('video.res', video.resolutionString())
            mli.setProperty('video.codec', video.videoCodecString())
            mli.setProperty('video.rendering', video.videoCodecRendering)
            mli.setBoolProperty('unavailable', not video.available())
            mli.setBoolProperty('media.multiple', len(list(filter(lambda x: x.isAccessible(), video.media()))) > 1)

    def setItemAudioAndSubtitleInfo(self, video, mli):
        if util.getSetting('use_external_audio', False) and hasattr(type(video), 'discoverExternalAudioStreams'):
            video.discoverExternalAudioStreams()

        sas = video.selectedAudioStream()

        if sas:
            if len(video.audioStreams) > 1:
                mli.setProperty(
                    'audio', sas and u'{0} +{1}'.format(sas.getTitle(metadata.apiTranslate),
                                                        len(video.audioStreams) - 1)
                    or T(32309, 'None')
                )
            else:
                mli.setProperty('audio', sas and sas.getTitle(metadata.apiTranslate) or T(32309, 'None'))

        sss = video.selectedSubtitleStream(forced_subtitles_override=
                                           util.getSetting("forced_subtitles_override") and pnUtil.ACCOUNT.subtitlesForced == 0,
                                           deselect_subtitles=getNativeLanguages(util.getSetting("disable_subtitle_languages") or []))
        if sss:
            if len(video.subtitleStreams) > 1:
                mli.setProperty(
                    'subtitles', u'{0} +{1}'.format(sss.getTitle(metadata.apiTranslate), len(video.subtitleStreams) - 1)
                )
            else:
                mli.setProperty('subtitles', sss.getTitle(metadata.apiTranslate))
        else:
            if video.subtitleStreams:
                mli.setProperty('subtitles', u'{0} +{1}'.format(T(32309, 'None'), len(video.subtitleStreams)))
            else:
                mli.setProperty('subtitles', T(32309, 'None'))

    def updateMediaInfoPills(self, mli):
        if self.fromWatchlist:
            return

        video_text = mli.getProperty('video.res')
        rendering = mli.getProperty('video.rendering')
        if rendering:
            video_text = u'{0} {1}'.format(video_text, rendering)

        self.resizeInfoPill(self.videoInfoImage, self.videoInfoLabel, video_text, self.VIDEO_PILL_MAX_WIDTH)
        self.resizeInfoPill(self.audioInfoImage, self.audioInfoLabel, mli.getProperty('audio'), self.AUDIO_PILL_MAX_WIDTH)
        self.resizeInfoPill(self.subtitleInfoImage, self.subtitleInfoLabel, mli.getProperty('subtitles'),
                            self.SUBTITLE_PILL_MAX_WIDTH)

    def setProgress(self, mli, view_offset=None):
        video = mli.dataSource
        view_offset = view_offset if view_offset is not None else video.viewOffset.asInt()

        if view_offset:
            mli.setProperty('remainingTime', T(33615,
                                               "{time} left").format(time=video._remainingTimeString(view_offset)))
        else:
            mli.setProperty('remainingTime', '')

    def createListItem(self, episode):
        mli = kodigui.ManagedListItem(
            '',
            data_source=episode
        )
        self.setUserItemInfo(mli, types=("title", "thumbnail"))
        mli.setProperty('episode.number', episode.index and T(32311, 'E').format(episode.index) or '')
        mli.setProperty('episode.duration', util.durationToText(episode.duration.asInt()))
        mli.setProperty('unwatched', not episode.isWatched and '1' or '')
        mli.setProperty('watched', episode.isFullyWatched and '1' or '')
        # mli.setProperty('progress', util.getProgressImage(obj))
        return mli

    def fillEpisodes(self, update=False, from_redirect=False):
        items = self.episodesPaginator.paginate()
        if from_redirect:
            self.episodeListControl.setSelectedItemByPos(0)
        if not update:
            self.selectEpisode()
        self.reloadItems(items, with_progress=True)

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
            except:
                util.ERROR("No data - deleted or server disconnected?", notify=True, time_ms=5000)
                self.doClose()
                return
            util.DEBUG_LOG("Episodes: Currently selected item loaded")
            self.currentItemLoaded = True
            self.lastItem = cur_mli
            self.updateMediaInfoPills(cur_mli)
            self.setBoolProperty('current_item.loaded', True)
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
        return (base and base or self.PLAY_BUTTON_ID) + (mli.getProperty('media.multiple') and 1000 or 0)

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

    def fillExtras(self):
        items = []
        idx = 0

        seasonOrShow = self.season or self.show_

        if not seasonOrShow.extras:
            self.extraListControl.reset()
            return False

        for extra in seasonOrShow.extras():
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
            return False

        self.extraListControl.reset()
        self.extraListControl.addItems(items)
        return True

    def fillRelated(self):
        if not self.relatedPaginator or not self.relatedPaginator.leafCount:
            self.relatedListControl.reset()
            return

        items = self.relatedPaginator.paginate()
        if not items:
            return False

        return True

    def fillRoles(self):
        items = []
        idx = 0

        ds = self.episodeListControl.getSelectedItem().dataSource

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
