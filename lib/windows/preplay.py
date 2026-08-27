from __future__ import absolute_import

import json
import os

from kodi_six import xbmc
from kodi_six import xbmcgui
from plexnet import plexplayer, media, plexobjects, util as pnUtil, plexapp, plexlibrary, playlist, playqueue

from lib import metadata
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
from . import playersettings
from . import search
from . import videoplayer
from . import windowutils
from .mixins.ratings import RatingsMixin
from .mixins.media_info_pills import MediaInfoPillsMixin
from .mixins.playbackbtn import PlaybackBtnMixin
from .mixins.thememusic import ThemeMusicMixin
from .mixins.watchlist import WatchlistUtilsMixin, removeFromWatchlistBlind
from .mixins.roles import RolesMixin
from .mixins.common import CommonMixin
from .mixins.tasks import TasksMixin

VIDEO_RELOAD_KW = dict(includeExtras=1, includeExtrasCount=10, includeChapters=1, includeReviews=1)


class RelatedPaginator(pagination.BaseRelatedPaginator):
    def getData(self, offset, amount):
        return self.parentWindow.video.getRelated(offset=offset, limit=amount)

    def createListItem(self, rel):
        return kodigui.ManagedListItem(
            rel.title or '',
            str(rel.year) if rel.year else '',
            thumbnailImage=rel.defaultThumb.asTranscodedImageURL(*self.parentWindow.RELATED_DIM),
            data_source=rel
        )


class CollectionPaginator(pagination.BaseRelatedPaginator):
    initialPageSize = 10
    pageSize = 8
    orphans = 4
    thumbFallback = 'script.plex/thumb_fallbacks/movie.png'

    def setup(self, server, path):
        self._server = server
        self._path = path
        return self

    @property
    def initialPage(self):
        data = self.getData(self.offset, self.initialPageSize)
        if data:
            self._lastAmount = self._currentAmount
            self._currentAmount = len(data)
            return data

    def getData(self, offset, amount):
        items = plexobjects.listItems(self._server, self._path, offset=offset, limit=amount)
        if not self.leafCount:
            self.leafCount = int(items.totalSize or 0) or len(items)
        return items

    def createListItem(self, item):
        return kodigui.ManagedListItem(
            item.title or '',
            str(item.year) if item.year else '',
            thumbnailImage=item.defaultThumb.asTranscodedImageURL(*self.parentWindow.RELATED_DIM),
            data_source=item
        )

    def prepareListItem(self, item, mli):
        mli.setProperty('unwatched', not item.isWatched and '1' or '')
        mli.setBoolProperty('watched', item.isFullyWatched)
        mli.setProperty('progress', util.getProgressImage(item))


class PrePlayWindow(kodigui.ControlledWindow, windowutils.UtilMixin, windowutils.SidebarMixin, RatingsMixin,
                    MediaInfoPillsMixin, PlaybackBtnMixin, ThemeMusicMixin, RolesMixin, CommonMixin,
                    WatchlistUtilsMixin, TasksMixin):
    xmlFile = 'script-plex-pre_play.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    supportsAutoPlay = True
    # back-out of preplay can leave the window lingering on the stack until a parent
    # re-activate; actively dismiss it on NAV_BACK (see ControlledWindow.onAction)
    dismissOnClose = True

    RELATED_DIM = util.scaleResolution(268, 402)
    EXTRA_DIM = util.scaleResolution(329, 185)
    ROLES_DIM = util.scaleResolution(334, 334)
    CLEAR_LOGO_DIM = util.scaleResolution(616, 109)

    ROLES_LIST_ID = 400
    REVIEWS_LIST_ID = 401
    EXTRA_LIST_ID = 402
    RELATED_LIST_ID = 403
    COLLECTION_LIST_IDS = [404, 405, 406]

    OPTIONS_GROUP_ID = 200

    MAIN_BUTTON_GROUP_ID = 300
    INFO_BUTTON_ID = 304
    PLAY_BUTTON_ID = 302
    TRAILER_BUTTON_ID = 303
    SETTINGS_BUTTON_ID = 305
    OPTIONS_BUTTON_ID = 306
    MEDIA_BUTTON_ID = 307

    POSSIBLE_PLAY_BUTTON_IDS = [302, 2302, 2303, 2304, 2305]

    PLAYER_STATUS_BUTTON_ID = 204

    def __init__(self, *args, **kwargs):
        kodigui.ControlledWindow.__init__(self, *args, **kwargs)
        PlaybackBtnMixin.__init__(self)
        WatchlistUtilsMixin.__init__(self)
        TasksMixin.__init__(self)
        self.video = kwargs.get('video')
        self.parentList = kwargs.get('parent_list')
        self.fromWatchlist = kwargs.get('from_watchlist', False)
        self.isExternal = kwargs.get('external_item', False)
        self.directlyFromWatchlist = kwargs.get('directly_from_watchlist')
        self.is_watchlisted = kwargs.get('is_watchlisted', False)
        self.startOver = kwargs.get('start_over')

        # Sidebar entry-section persistence (ported from Sidebar-Tab-Unification's
        # mellow-pondering-magpie.md, 2026-08-18): which sidebar row should stay highlighted while
        # drilling through content, regardless of which section the item actually on screen
        # belongs to - set once here (not recomputed per buildSectionList() call) so every window
        # this one goes on to open can inherit it unchanged. None/False here means "nobody passed
        # one down" - this window is itself a genesis point (opened from the sidebar/Home/Search/
        # Watchlist), so it falls back to the same real-section-of-the-item computation
        # buildSectionList() always used before this.
        self.entrySectionId = kwargs.get('entry_section_id')
        self.entryFromWatchlist = kwargs.get('entry_from_watchlist', False)
        if self.entrySectionId is None and not self.entryFromWatchlist:
            self.entrySectionId = self.video.getLibrarySectionId()
            self.entryFromWatchlist = self.fromWatchlist or self.directlyFromWatchlist

        self.videos = None
        self.exitCommand = None
        self.trailer = None
        self.lastFocusID = None
        self.lastNonOptionsFocusID = None
        self.initialized = False
        self.relatedPaginator = None
        self.collectionPaginators = [None, None, None]
        self.openedWithAutoPlay = False
        self.fromPlayback = False
        self.useBGM = False
        # hashed-orbiting-pizza.md Phase 2: None here means "build my own sectionList" (a
        # standalone/un-hosted open) - a hosted open (LibraryWindow._setupCurrent(), library.py)
        # overwrites this with the host's own sectionList object before onFirstInit() runs.
        self.sectionList = None

    def doClose(self, **kw):
        self.relatedPaginator = None
        TasksMixin.doClose(self)
        kodigui.ControlledWindow.doClose(self)

    def onFirstInit(self):
        if not self.fromWatchlist:
            # pre_play-wl.xml replaces this whole block with wl_availability.xml.tpl's own controls -
            # these ids only exist on the non-watchlist streams block
            self.initMediaInfoPillControls()

        self.extraListControl = kodigui.ManagedControlList(self, self.EXTRA_LIST_ID, 5)
        self.relatedListControl = kodigui.ManagedControlList(self, self.RELATED_LIST_ID, 5)
        self.rolesListControl = kodigui.ManagedControlList(self, self.ROLES_LIST_ID, 5)
        self.reviewsListControl = kodigui.ManagedControlList(self, self.REVIEWS_LIST_ID, 5)
        self.collectionListControls = [kodigui.ManagedControlList(self, lid, 5) for lid in self.COLLECTION_LIST_IDS]
        self.setBoolProperty("is_watchlisted", self.is_watchlisted)

        if self.sectionList is None:
            self.sectionList = kodigui.ManagedControlList(self, self.SECTION_LIST_ID, 15)
            self.buildSectionList()
        else:
            self.sectionList.newControl(self)
        self.displayServerAndUser()

        self.setup()
        self.initialized = True

        if not util.getSetting("slow_connection") and not self.openedWithAutoPlay:
            self.themeMusicInit(self.video, locations=[os.path.dirname(s.part.file) for s in self.video.videoStreams])

    def doAutoPlay(self, blind=False):
        # First reload the video to get all the other info
        self.video.reload(checkFiles=1, **VIDEO_RELOAD_KW)
        self.openedWithAutoPlay = True
        return self.playVideo(from_auto_play=True)

    @busy.dialog()
    def onReInit(self):
        PlaybackBtnMixin.onReInit(self)
        self.themeMusicReinit(self.video)
        self.initialized = False
        if util.getSetting("slow_connection"):
            self.setProperty('remainingTime', T(32914, "Loading"))
        self.video.reload(checkFiles=1, fromMediaChoice=self.video.mediaChoice is not None, skip_cache=True, **VIDEO_RELOAD_KW)
        removed_from_wl = False
        if self.fromPlayback:
            removed_from_wl = self.wl_auto_remove(self.video)
        self.fromPlayback = False
        self.refreshInfo(from_reinit=True)

        if not removed_from_wl:
            self.checkIsWatchlisted(self.video)
        self.initialized = True

    def onBlindClose(self):
        if self.fromPlayback and self.openedWithAutoPlay and not self.started:
            self.video.reload(checkFiles=1, fromMediaChoice=self.video.mediaChoice is not None, **VIDEO_RELOAD_KW)
            if self.video.isFullyWatched:
                removeFromWatchlistBlind(self.video.guid, self.video)

    def refreshInfo(self, from_reinit=False):
        oldFocusId = self.getFocusId()

        util.setGlobalProperty('hide.resume', '' if self.video.viewOffset.asInt() else '1')
        # skip setting background when coming from reinit (other window) if we've focused something other than main
        self.setInfo(skip_bg=from_reinit and not (self.PLAY_BUTTON_ID <= oldFocusId <= self.MEDIA_BUTTON_ID))

        if not from_reinit:
            show_reviews = util.getSetting('show_reviews1')
            if show_reviews:
                if "watched" in show_reviews and "unwatched" not in show_reviews:
                    self.fillReviews()

            self.fillRelated()
        xbmc.sleep(100)

        if oldFocusId == self.PLAY_BUTTON_ID:
            self.focusPlayButton()

    def onAction(self, action):
        try:
            controlID = self.getFocusId()

            if controlID == self.SECTION_LIST_ID:
                self.checkSectionItem(action=action)

            if not controlID and self.lastFocusID and not action == xbmcgui.ACTION_MOUSE_MOVE:
                self.setFocusId(self.lastFocusID)

            if action == xbmcgui.ACTION_CONTEXT_MENU:
                if controlID == self.PLAY_BUTTON_ID:
                    self.playVideo(force_resume_menu=True)
                    return

                if not xbmc.getCondVisibility('ControlGroup({0}).HasFocus(0)'.format(self.OPTIONS_GROUP_ID)):
                    self.lastNonOptionsFocusID = self.lastFocusID
                    self.setFocusId(self.OPTIONS_GROUP_ID)
                    return
                else:
                    if self.lastNonOptionsFocusID:
                        self.setFocusId(self.lastNonOptionsFocusID)
                        self.lastNonOptionsFocusID = None
                        return

            elif action == xbmcgui.ACTION_NAV_BACK:
                if (not xbmc.getCondVisibility('ControlGroup({0}).HasFocus(0)'.format(
                        self.OPTIONS_GROUP_ID)) or not controlID) and \
                        not util.addonSettings.fastBack:
                    if self.getProperty('on.extras'):
                        self.setFocusId(self.OPTIONS_GROUP_ID)
                        return

            elif self.isWatchedAction(action) and xbmc.getCondVisibility('ControlGroup({}).HasFocus(0)'.format(self.MAIN_BUTTON_GROUP_ID)):
                self.toggleWatched(self.video)
                return

            elif action == xbmcgui.ACTION_LAST_PAGE and xbmc.getCondVisibility('ControlGroup({}).HasFocus(0)'.format(self.MAIN_BUTTON_GROUP_ID)):
                next(self)
            elif action == xbmcgui.ACTION_NEXT_ITEM:
                self.setFocusId(300)
                next(self)
            elif action == xbmcgui.ACTION_FIRST_PAGE and xbmc.getCondVisibility('ControlGroup({}).HasFocus(0)'.format(self.MAIN_BUTTON_GROUP_ID)):
                self.prev()
            elif action == xbmcgui.ACTION_PREV_ITEM:
                self.setFocusId(300)
                self.prev()

            elif action == xbmcgui.ACTION_MOVE_UP and controlID in (self.REVIEWS_LIST_ID,
                                                                    self.ROLES_LIST_ID,
                                                                    self.EXTRA_LIST_ID):
                self.updateBackgroundFrom(self.video)

            if controlID == self.RELATED_LIST_ID:
                if self.relatedPaginator.boundaryHit:
                    self.relatedPaginator.paginate()
                    return
                elif action in (xbmcgui.ACTION_MOVE_LEFT, xbmcgui.ACTION_MOVE_RIGHT):
                    self.updateBackgroundFrom(self.relatedListControl.getSelectedItem().dataSource)

            if controlID in self.COLLECTION_LIST_IDS:
                idx = self.COLLECTION_LIST_IDS.index(controlID)
                paginator = self.collectionPaginators[idx]
                if paginator and paginator.boundaryHit:
                    paginator.paginate()
                    return
        except:
            util.ERROR()

        kodigui.ControlledWindow.onAction(self, action)

    def onClick(self, controlID):
        if controlID == self.SECTION_LIST_ID:
            self.sectionClicked()
        elif controlID == self.EXTRA_LIST_ID:
            self.openItem(self.extraListControl)
        elif controlID == self.RELATED_LIST_ID:
            self.openItem(self.relatedListControl)
        elif controlID in self.COLLECTION_LIST_IDS:
            self.openItem(self.collectionListControls[self.COLLECTION_LIST_IDS.index(controlID)])
        elif controlID == self.ROLES_LIST_ID:
            if not self.roleClicked():
                return
        elif controlID == self.PLAY_BUTTON_ID:
            self.playVideo()
        elif controlID in self.WL_RELEVANT_BTNS and self.fromWatchlist and self.wl_availability:
            self.wl_item_opener(self.video, self.openItem)
        elif controlID in self.WL_BTN_STATE_BTNS:
            is_watchlisted = self.toggleWatchlist(self.video)
            self.waitAndSetFocus(self.WL_BTN_STATE_WATCHLISTED if is_watchlisted else self.WL_BTN_STATE_NOT_WATCHLISTED)
        elif controlID == self.PLAYER_STATUS_BUTTON_ID:
            self.showAudioPlayer()
        elif controlID == self.INFO_BUTTON_ID:
            self.infoButtonClicked()
        elif controlID == self.SETTINGS_BUTTON_ID:
            self.settingsButtonClicked()
        elif controlID == self.TRAILER_BUTTON_ID:
            self.openItem(item=self.trailer)
        elif controlID == self.OPTIONS_BUTTON_ID:
            self.optionsButtonClicked()
        elif controlID == self.MEDIA_BUTTON_ID:
            self.mediaButtonClicked()

    def onFocus(self, controlID):
        self.reselectActiveSection(controlID, self.lastFocusID)
        self.lastFocusID = controlID

        if controlID == self.SECTION_LIST_ID:
            self.checkSectionItem()

        if 399 < controlID < 500:
            self.setProperty('hub.focus', str(controlID - 400))

            if controlID == self.RELATED_LIST_ID:
                self.updateBackgroundFrom(self.relatedListControl.getSelectedItem().dataSource)

        if xbmc.getCondVisibility('ControlGroup(50).HasFocus(0) + ControlGroup(300).HasFocus(0)'):
            self.setProperty('on.extras', '')
        elif xbmc.getCondVisibility('ControlGroup(50).HasFocus(0) + !ControlGroup(300).HasFocus(0)'):
            self.setProperty('on.extras', '1')

    def toggleWatched(self, item, state=None, **kw):
        watched = super(PrePlayWindow, self).toggleWatched(item, state=state, **kw)
        if watched is None:
            return

        if watched:
            self.wl_auto_remove(self.video)
            self.checkIsWatchlisted(self.video)
        self.refreshInfo()
        util.MONITOR.watchStatusChanged()

    def searchButtonClicked(self):
        self.processCommand(search.dialog(self, section_id=self.video.getLibrarySectionId() or None))

    def roleSectionId(self):
        return self.entrySectionId

    def roleFromWatchlist(self):
        return self.entryFromWatchlist

    def buildSectionList(self):
        """Populate the sidebar's section list. Mirrors library.py's buildSectionList()/
        home.py's showSections() - see library.py:675 for why this isn't shared code yet.
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

        # self.entrySectionId (Sidebar entry-section persistence) - resolved once in __init__,
        # either inherited from whatever this window was drilled in from or, when this is itself a
        # genesis point, this exact same real-section-of-the-item computation. A real section match
        # always wins; only fall back to Watchlist when nothing matched - activeSectionId can be a
        # real section's key, empty, or the literal string "watchlist" (what discover/watchlist
        # items report), which never matches a real section's key, so it naturally falls through to
        # the watchlist fallback below.
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
        """Sidebar avatar/username and server icon/name. Mirrors library.py's
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

    def settingsButtonClicked(self):
        if not self.video.mediaChoice:
            playerObject = plexplayer.PlexPlayer(self.video)
            playerObject.build()
        playersettings.showDialog(video=self.video, non_playback=True)
        self.setAudioAndSubtitleInfo()

    def infoButtonClicked(self):
        opener.handleOpen(
            info.InfoWindow,
            title=self.video.defaultTitle,
            sub_title=self.getProperty('info'),
            thumb=self.video.type == 'episode' and self.video.thumb or self.video.defaultThumb,
            thumb_fallback='script.plex/thumb_fallbacks/{0}.png'.format(self.video.type == 'episode' and 'show' or 'movie'),
            info=self.video.summary,
            background=self.getProperty('background'),
            is_16x9=self.video.type == 'episode',
            video=self.video
        )

    def optionsButtonClicked(self):
        options = []

        inProgress = self.video.viewOffset.asInt()
        if not self.video.isWatched or inProgress:
            options.append({'key': 'mark_watched', 'display': T(32319, 'Mark Played')})
        if self.video.isWatched or inProgress:
            options.append({'key': 'mark_unwatched', 'display': T(32318, 'Mark Unplayed')})

        options.append(dropdown.SEPARATOR)

        if self.video.type == 'episode':
            options.append({'key': 'to_season', 'display': T(32400, 'Go to Season')})
            options.append({'key': 'to_show', 'display': T(32323, 'Go to Show')})

        if self.video.type in ('episode', 'movie'):
            options.append({'key': 'to_section', 'display': T(32324, u'Go to {0}').format(self.video.getLibrarySectionTitle())})

        if plexapp.ACCOUNT.isAdmin:
            options.append(dropdown.SEPARATOR)
            options.append({'key': 'refresh', 'display': T(33719, 'Refresh metadata')})

            if self.video.server.allowsMediaDeletion:
                options.append({'key': 'delete', 'display': T(32322, 'Delete')})

        if 'items' in util.getSetting('cache_requests'):
            options.append({'key': 'cache_reset', 'display': T(33728, "Clear cache for item")})
        # if xbmc.getCondVisibility('Player.HasAudio') and self.section.TYPE == 'artist':
        #     options.append({'key': 'add_to_queue', 'display': 'Add To Queue'})

        # if False:
        #     options.append({'key': 'add_to_playlist', 'display': 'Add To Playlist'})
        posy = 880
        if not util.getGlobalProperty('hide.resume'):
            posy += 106
        if self.getProperty('trailer.button'):
            posy += 106
        choice = dropdown.showDropdown(options, (posy, 618), close_direction='left')
        if not choice:
            return

        if choice['key'] == 'play_next':
            xbmc.executebuiltin('PlayerControl(Next)')
        elif choice['key'] == 'mark_watched':
            self.toggleWatched(self.video, state=True, **VIDEO_RELOAD_KW)
        elif choice['key'] == 'mark_unwatched':
            self.toggleWatched(self.video, state=False, **VIDEO_RELOAD_KW)
        elif choice['key'] == 'to_season':
            self.processCommand(opener.open(self.video.parentRatingKey,
                                            entry_section_id=self.entrySectionId,
                                            entry_from_watchlist=self.entryFromWatchlist))
        elif choice['key'] == 'to_show':
            self.processCommand(opener.open(self.video.grandparentRatingKey,
                                            entry_section_id=self.entrySectionId,
                                            entry_from_watchlist=self.entryFromWatchlist))
        elif choice['key'] == 'to_section':
            self.cameFrom = "library"
            section = plexlibrary.LibrarySection.fromFilter(self.video)
            self.processCommand(opener.sectionClicked(section,
                                                      came_from=self.video.ratingKey)
                                )
        elif choice['key'] == 'delete':
            self.delete()
        elif choice['key'] == 'refresh':
            self.video.refresh()
            self.video.reload(checkFiles=1, **VIDEO_RELOAD_KW)
            self.refreshInfo()
        elif choice["key"] == "cache_reset":
            try:
                util.DEBUG_LOG('Clearing requests cache for {}...', self.video)
                self.video.clearCache()
                self.video.reload(checkFiles=1, **VIDEO_RELOAD_KW)
                self.refreshInfo()
            except Exception as e:
                util.DEBUG_LOG("Couldn't clear cache: {}", e)

    def mediaButtonClicked(self):
        options = []
        for media in self.video.media:
            ind = ''
            if self.video.mediaChoice and media.id == self.video.mediaChoice.media.id:
                ind = 'script.plex/home/device/check.png'
            options.append({'key': media, 'display': media.versionString(), 'indicator': ind})
        choice = dropdown.showDropdown(options, header=T(32450, 'Choose Version'), with_indicator=True)
        if not choice:
            return False

        for media in self.video.media:
            media.set('selected', '')

        self.video.setMediaChoice(choice['key'])
        choice['key'].set('selected', 1)
        pnUtil.INTERFACE.playbackManager(self.video, key="media_version", value=choice['key'].id)
        self.setInfo()

    def delete(self):
        button = optionsdialog.show(
            T(32326, 'Really delete?'),
            T(33035, "Delete {}: {}?").format(type(self.video).__name__, self.video.defaultTitle),
            T(32328, 'Yes'),
            T(32329, 'No')
        )

        if button != 0:
            return

        if self._delete():
            self.doClose()
        else:
            util.messageDialog(T(32330, 'Message'), T(32331, 'There was a problem while attempting to delete the media.'))

    @busy.dialog()
    def _delete(self):
        success = self.video.delete()
        util.LOG('Media DELETE: {0} - {1}', self.video, success and 'SUCCESS' or 'FAILED')
        return success

    def getVideos(self):
        if not self.videos:
            if self.video.TYPE == 'episode':
                self.videos = self.video.show().episodes()

        if not self.videos:
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
            mli = self.parentList.getListItemByDataSource(self.video)
            if not mli:
                return False

            pos = mli.pos() + 1
            if not self.parentList.positionIsValid(pos):
                pos = 0

            self.video = self.parentList.getListItem(pos).dataSource
        else:
            if not self.getVideos():
                return False

            if self.video not in self.videos:
                return False

            pos = self.videos.index(self.video)
            pos += 1
            if pos >= len(self.videos):
                pos = 0

            self.video = self.videos[pos]

        return True

    def prev(self):
        if not self._prev():
            return
        self.setup()

    @busy.dialog()
    def _prev(self):
        if self.parentList:
            mli = self.parentList.getListItemByDataSource(self.video)
            if not mli:
                return False

            pos = mli.pos() - 1
            if pos < 0:
                pos = self.parentList.size() - 1

            self.video = self.parentList.getListItem(pos).dataSource
        else:
            if not self.getVideos():
                return False

            if self.video not in self.videos:
                return False

            pos = self.videos.index(self.video)
            pos -= 1
            if pos < 0:
                pos = len(self.videos) - 1

            self.video = self.videos[pos]

        return True

    def playVideo(self, from_auto_play=False, force_resume_menu=False):
        if self.playBtnClicked:
            return

        if not self.video.available():
            util.messageDialog(T(32312, 'Unavailable'), T(32313, 'This item is currently unavailable.'))
            return

        resume = False
        if self.video.viewOffset.asInt() and not self.startOver:
            if not util.getSetting('assume_resume') or force_resume_menu:
                choice = dropdown.showDropdown(
                    options=[
                        {'key': 'resume', 'display': T(32429, 'Resume from {0}').format(util.timeDisplay(self.video.viewOffset.asInt()).lstrip('0').lstrip(':'))},
                        {'key': 'play', 'display': T(32317, 'Play from beginning')}
                    ],
                    pos=(660, 441),
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

        self.fromPlayback = True

        preRoll = util.getUserSetting('preplay_preroll', False)
        preRollFirst = util.getUserSetting('preplay_preroll_first', True)
        trailers = 5 - util.getUserSetting('preplay_trailers', 5)
        # play playqueue if necessary (trailer preplay or plex told us to preplay something)
        if not resume:
            if preRoll or trailers:
                pq = playqueue.createPlayQueueForItem(self.video, use_async=False, method="POST",
                                                          extrasPrefixCount=trailers)

                _items = [item for item in pq.items if item.get('type') == 'clip']
                for item in _items:
                    item.isExtra = True

                if preRoll and preRollFirst and trailers:
                    items = []
                    # move prerolls to the front
                    for item in reversed(_items):
                        if not item.get('subtype'):
                            # pre-roll detected
                            items.insert(0, item)
                    for item in _items:
                        if item.get('subtype') == 'trailer':
                            items.append(item)
                else:
                    # use server pq as is, but filter out prerolls if not wanted
                    items = list(filter(lambda x: x.get('subtype') == "trailer", _items)) if not preRoll else _items

                items.append(self.video)

                pl = playlist.LocalPlaylist(items, self.video.getServer())
                self.processCommand(
                    videoplayer.play(play_queue=pl, bgm=self.useBGM))
                return True

        self.processCommand(videoplayer.play(video=self.video, resume=resume, bgm=self.useBGM))
        return True

    def openItem(self, control=None, item=None, inherit_from_watchlist=True, server=None, is_watchlisted=False, **kw):
        if not item:
            mli = control.getSelectedItem()
            if not mli:
                return
            item = mli.dataSource

        self.processCommand(opener.open(item, from_watchlist=self.fromWatchlist if inherit_from_watchlist else False,
                                        server=server, is_watchlisted=is_watchlisted,
                                        entry_section_id=self.entrySectionId,
                                        entry_from_watchlist=self.entryFromWatchlist, **kw))

    def focusPlayButton(self, extended=False):
        if extended:
            self.setFocusId(self.wl_play_button_id)
            return
        try:
            if not self.getFocusId() == self.PLAY_BUTTON_ID:
                # id 302's own <visible> (unavailable/disable_playback) is keyed off properties
                # we just set, but the GUI thread hasn't necessarily recalculated visibility yet -
                # SetFocus on a still-invisible control fails silently and focus falls through
                # elsewhere (e.g. a hub row, which then triggers its slide-into-view animation).
                # Wait for it to actually be visible first.
                self.waitForVisibility(self.PLAY_BUTTON_ID)
                self.setFocusId(self.PLAY_BUTTON_ID)
        except (SystemError, RuntimeError):
            util.ERROR()
            self.setFocusId(self.PLAY_BUTTON_ID)

    @busy.dialog()
    def setup(self):
        self.watchlist_setup(self.video)

        util.DEBUG_LOG('PrePlay: Showing video info: {0}', self.video)

        if self.isExternal:
            # fixme, multiple? choice?
            self.video.related_source = "more-from-credits"
        self.video.reload(checkFiles=1, **VIDEO_RELOAD_KW)
        try:
            self.relatedPaginator = RelatedPaginator(self.relatedListControl, leaf_count=int(self.video.relatedCount),
                                                     parent_window=self)
        except ValueError:
            raise util.NoDataException

        if self.fromWatchlist:
            self.watchlistItemAvailable(self.video, shortcut_watchlisted=self.directlyFromWatchlist)
        if not self.directlyFromWatchlist:
            self.checkIsWatchlisted(self.video)

        self.setInfo()
        self.setBoolProperty("initialized", True)
        # For watchlist items, PLAY_BUTTON_ID (302) is permanently hidden behind disable_playback
        # - watchlistItemAvailable() above already owns focusing the dynamic wl button (2302-2305)
        # once its availability check resolves, so waiting on 302 here would just block on a
        # control that's never going to show up.
        if not self.fromWatchlist:
            self.focusPlayButton()
        self.batch_simple([(self.fillRoles, None, None),
                           (self.fillReviews, None, None),
                           (self.fillExtras, None, None),
                           (self.fillRelated, None, None),
                           (self.fillCollections, None, None)])

    def setInfo(self, skip_bg=False):
        if not skip_bg:
            self.updateBackgroundFrom(self.video)
        self.setProperty('title', self.video.title)
        logo = util.clearLogoFrom(self.video, *self.CLEAR_LOGO_DIM)
        self.setProperty('clear.logo', logo)
        self.setProperty('duration', self.video.duration and util.durationToText(self.video.duration.asInt()))
        self.setProperty('summary', self.video.summary.strip().replace('\t', ' '))
        self.setProperty('unwatched', not self.video.isWatched and '1' or '')
        self.setBoolProperty('watched', self.video.isFullyWatched)
        self.setBoolProperty('disable_playback', self.fromWatchlist)

        directors = u' / '.join([d.tag for d in self.video.directors()][:3])
        directorsLabel = len(self.video.directors) > 1 and T(32401, u'DIRECTORS').upper() or T(32383, u'DIRECTOR').upper()
        self.setProperty('directors', directors and u'{0}    {1}'.format(directorsLabel, directors) or '')
        writers = u' / '.join([r.tag for r in self.video.writers()][:3])
        writersLabel = len(self.video.writers) > 1 and T(32403, u'WRITERS').upper() or T(32402, u'WRITER').upper()
        self.setProperty('writers',
                         writers and u'{0}{1}    {2}'.format(directors and '    ' or '', writersLabel, writers) or '')

        self.setProperty('title', self.video.defaultTitle)
        genres = u' / '.join([g.tag for g in self.video.genres()][:3])
        self.setProperty('info', genres)
        self.setProperty('date', self.video.year)
        if self.fromWatchlist and not self.wl_availability:
            self.setProperty('wl_server_availability_verbose', util.cleanLeadingZeros(self.video.originallyAvailableAt.asDatetime('%B %d, %Y')))
        self.setProperty('content.rating', self.video.contentRating.split('/', 1)[-1])

        cast = u' / '.join([r.tag for r in self.video.roles()][:5])
        castLabel = 'CAST'
        self.setProperty('cast', cast and u'{0}    {1}'.format(castLabel, cast) or '')
        self.setProperty('related.header', T(32404, 'Related Movies') if not self.fromWatchlist else T(34018, 'Related Media'))

        if self.fromWatchlist:
            self.setProperty('studios', u' / '.join([r.tag for r in self.video.studios()][:2]))

        else:
            # single studio attribute here, vs. the joined tag list above, but both feed the same 'studios' property
            self.setProperty('studios', self.video.studio)
            self.setProperty('video.res', self.video.resolutionString())
            self.setProperty('audio.codec', self.video.audioCodecString())
            self.setProperty('video.codec', self.video.videoCodecString())
            self.setProperty('video.rendering', self.video.videoCodecRendering)
            self.setProperty('audio.channels', self.video.audioChannelsString(metadata.apiTranslate))
            self.setBoolProperty('media.multiple', len(list(filter(lambda x: x.isAccessible(), self.video.media()))) > 1)

            video_text = self.video.resolutionString()
            if self.video.videoCodecRendering:
                video_text = u'{0} {1}'.format(video_text, self.video.videoCodecRendering)
            self.resizeInfoPill(self.videoInfoImage, self.videoInfoLabel, video_text, self.VIDEO_PILL_MAX_WIDTH)

        self.populateRatings(self.video, self)

        if not self.fromWatchlist:
            self.setAudioAndSubtitleInfo()

            self.setProperty('unavailable', all(not v.isAccessible() for v in self.video.media()) and '1' or '')

            if self.video.viewOffset.asInt():
                self.setProperty('remainingTime', T(33615, "{time} left").format(time=self.video.remainingTimeString))
            else:
                self.setProperty('remainingTime', '')

    def setAudioAndSubtitleInfo(self):
        # discover external audio files for mapped direct play
        if util.getSetting('use_external_audio', False) and hasattr(type(self.video), 'discoverExternalAudioStreams'):
            self.video.discoverExternalAudioStreams()

        sas = self.video.selectedAudioStream()

        audio_text = ''
        if sas:
            if len(self.video.audioStreams) > 1:
                audio_text = sas and u'{0} +{1}'.format(sas.getTitle(metadata.apiTranslate),
                                                         len(self.video.audioStreams) - 1) \
                    or T(32309, 'None')
            else:
                audio_text = sas and sas.getTitle(metadata.apiTranslate) or T(32309, 'None')
            self.setProperty('audio', audio_text)

        sss = self.video.selectedSubtitleStream(
            forced_subtitles_override=util.getSetting("forced_subtitles_override") and pnUtil.ACCOUNT.subtitlesForced == 0,
            deselect_subtitles=getNativeLanguages(util.getSetting("disable_subtitle_languages") or []))
        if sss:
            if len(self.video.subtitleStreams) > 1:
                subtitles_text = u'{0} +{1}'.format(sss.getTitle(metadata.apiTranslate), len(self.video.subtitleStreams) - 1)
            else:
                subtitles_text = sss.getTitle(metadata.apiTranslate)
        else:
            if self.video.subtitleStreams:
                subtitles_text = u'{0} +{1}'.format(T(32309, 'None'), len(self.video.subtitleStreams))
            else:
                subtitles_text = T(32309, u'None')
        self.setProperty('subtitles', subtitles_text)

        self.resizeInfoPill(self.audioInfoImage, self.audioInfoLabel, audio_text, self.AUDIO_PILL_MAX_WIDTH)
        self.resizeInfoPill(self.subtitleInfoImage, self.subtitleInfoLabel, subtitles_text, self.SUBTITLE_PILL_MAX_WIDTH)

    def createListItem(self, obj):
        mli = kodigui.ManagedListItem(obj.title or '', thumbnailImage=obj.thumb.asTranscodedImageURL(*self.EXTRA_DIM), data_source=obj)
        return mli

    def fillExtras(self):
        items = []
        idx = 0

        if not self.video.extras:
            if self.fromWatchlist:
                self.video.fetchExternalExtras()

            if not self.video.extras:
                self.extraListControl.reset()
                return False

        for extra in self.video.extras:
            if not self.trailer and extra.extraType.asInt() == media.METADATA_RELATED_TRAILER:
                self.trailer = extra
                self.setProperty('trailer.button', '1')
                continue

            mli = self.createListItem(extra)
            if mli:
                mli.setProperty('index', str(idx))
                mli.setProperty(
                    'thumb.fallback', 'script.plex/thumb_fallbacks/{0}.png'.format(extra.type in ('show', 'season', 'episode') and 'show' or 'movie')
                )
                mli.setProperty('extra.duration', extra.duration and util.simplifiedTimeDisplay(extra.duration.asInt()))
                items.append(mli)
                idx += 1

        if not items:
            return False

        self.extraListControl.reset()
        self.extraListControl.addItems(items)

        return True

    def fillRelated(self):
        if not self.relatedPaginator.leafCount:
            self.relatedListControl.reset()
            return False

        items = self.relatedPaginator.paginate()

        if not items:
            return False

        return True

    def fillCollections(self):
        collections = self.video.collections() if self.video.type == 'movie' and self.video.collections else []
        section_id = self.video.getLibrarySectionId()

        # Fetch the section's collection metadata items to get their proper keys,
        # which respect the sort order set in Plex (Custom / Alphabetical / Release Date).
        # The id on a movie's <Collection> tag is a tag ID, not a metadata ratingKey,
        # so we can't use it directly — match by title instead.
        col_key_map = {}  # title → key (e.g. "/library/metadata/12345/children")
        try:
            col_items = plexobjects.listItems(
                self.video.server,
                '/library/sections/{0}/collections'.format(section_id)
            )
            for col_item in col_items:
                title = str(col_item.title)
                key = str(col_item.key)
                if title and key:
                    col_key_map[title] = key
        except Exception:
            util.ERROR()

        for i, list_control in enumerate(self.collectionListControls):
            if i >= len(collections):
                list_control.reset()
                self.setProperty('collection.header.{0}'.format(i), '')
                self.collectionPaginators[i] = None
                continue

            collection = collections[i]
            tag = str(collection.tag)
            if tag in col_key_map:
                path = col_key_map[tag]
            else:
                # Fallback: filter-based path. Works but ignores custom sort order.
                path = '/library/sections/{0}/all?type=1&{1}'.format(section_id, collection.filter)

            paginator = CollectionPaginator(list_control, parent_window=self, leaf_count=0)
            paginator.setup(self.video.server, path)
            try:
                paginator.paginate()
            except Exception:
                util.ERROR()
                list_control.reset()
                self.setProperty('collection.header.{0}'.format(i), '')
                self.collectionPaginators[i] = None
                continue

            self.collectionPaginators[i] = paginator
            self.setProperty('collection.header.{0}'.format(i), collection.tag)

    def fillRoles(self):
        items = []
        idx = 0

        if not self.video.roles:
            self.rolesListControl.reset()
            return False

        roles = self.video.combined_roles if util.getUserSetting('show_directors', True) else self.video.roles

        for role in roles:
            mli = kodigui.ManagedListItem(role.tag, role.role or util.TRANSLATED_ROLES[role.translated_role],
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

    def fillReviews(self):
        items = []
        idx = 0

        show_reviews = util.getSetting('show_reviews1')
        fully_watched = self.video.isFullyWatched

        if (not show_reviews or not self.video.reviews or
                ("unwatched" not in show_reviews and not fully_watched) or
                ("watched" not in show_reviews and fully_watched)):
            self.reviewsListControl.reset()
            return False

        for review in self.video.reviews():
            mli = kodigui.ManagedListItem(review.source, review.tag, thumbnailImage=review.ratingImage())
            mli.setProperty('index', str(idx))
            mli.setProperty('text', review.text)
            items.append(mli)
            idx += 1

        if not items:
            return False

        self.reviewsListControl.reset()
        self.reviewsListControl.addItems(items)
        return True

class PrePlayWindowWL(PrePlayWindow):
    xmlFile = 'script-plex-pre_play-wl.xml'
