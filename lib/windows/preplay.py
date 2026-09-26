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
    # 533x300 = 512x288 display size (script-plex-pre_play.xml.tpl's extras row) * 104%, the row's own
    # focus-zoom end value - same "fetch at the zoomed-in size, not the at-rest one" pattern the old
    # 299x168 art used (329x185 was that at 110%, its own zoom end value at the time). Shared with
    # ShowWindow's own EXTRA_DIM (subitems.py) - both rows use the same art recipe.
    EXTRA_DIM = util.scaleResolution(533, 300)
    ROLES_DIM = util.scaleResolution(334, 334)
    CLEAR_LOGO_DIM = util.scaleResolution(722, 162)

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
    # Play splits into these two once the video has a view offset (in.progress - setInfo() below),
    # matching Episodes' own button row. 301/307, the only ids left free in this screen's 300-block,
    # so they don't read in row order the way Episodes' 308/309 do - see the button row's own
    # comment (script-plex-pre_play.xml.tpl).
    RESUME_BUTTON_ID = 301
    RESTART_BUTTON_ID = 307
    # Click/focus target laid over the summary textbox (script-plex-pre_play.xml.tpl) - 350, not
    # something in the 300-306 button cluster (all already taken here) or 310-322
    # (includes/media_info_pills.xml.tpl's own ids, also live in this window - 310 specifically
    # collided with that include's video-pill background image, live-reported as "the background
    # does not extend the full length of the label": Control.setWidth() calls meant for that pill
    # (MediaInfoPillsMixin.resizeMediaInfoPills()) were hitting this button instead, since Kodi
    # doesn't guarantee which same-id control a getControl() call resolves to). Wired to
    # summaryButtonClicked() below.
    SUMMARY_BUTTON_ID = 350

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
        # Kodi reuses native window IDs (kodigui.py's windowSetBackground() has its own,
        # longer-standing comment on this - "window ids get reused... may just be leftover from
        # whatever window last held this id"), and hashed-orbiting-pizza.md's Phase 4 host
        # mechanism reconstructs a fresh PrePlayWindow far more often/tightly than the old
        # real-nested-window-per-click design did. Live-confirmed: without this, the *next*
        # PrePlayWindow to reuse this window ID briefly shows this movie's hero art (the
        # window-level background/background_static properties, which persist independently of
        # this Python object) until its own onFirstInit() gets far enough to overwrite them.
        # Clearing them here, on the way out - while self._winID is still correctly this
        # instance's own (must run before kodigui.ControlledWindow.doClose() below sets
        # self._closing, which makes setProperty() a no-op) - can't fully eliminate the gap (the
        # next instance still needs to load its own art), but replaces "briefly shows the wrong
        # movie" with "briefly shows nothing," which is what actually needs verifying live.
        self.setProperty('background', '')
        self.setProperty('background_static', '')
        TasksMixin.doClose(self)
        kodigui.ControlledWindow.doClose(self)

    def backgroundItem(self):
        return self.video

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
        self._selectActiveSection()
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

        # skip setting background when coming from reinit (other window) if we've focused something other than main
        # 301-307, not the old 302-306: Resume/Restart (301/307) bracket the rest of the button
        # row's ids, so the range has to widen with them rather than leave those two reading as
        # "focus is somewhere else entirely".
        self.setInfo(skip_bg=from_reinit and not (self.RESUME_BUTTON_ID <= oldFocusId <= self.RESTART_BUTTON_ID))

        if not from_reinit:
            show_reviews = util.getSetting('show_reviews1')
            if show_reviews:
                if "watched" in show_reviews and "unwatched" not in show_reviews:
                    self.fillReviews()

            self.fillRelated()
        xbmc.sleep(100)

        # Any of the three play states, not just 302: which one was focused before the reload isn't
        # necessarily the one that should be focused after it (a resumed-then-finished video flips
        # from Resume/Restart back to Play), so focusPlayButton() re-picks by the current state.
        if oldFocusId in (self.PLAY_BUTTON_ID, self.RESUME_BUTTON_ID, self.RESTART_BUTTON_ID):
            self.focusPlayButton()

    def handleBack(self):
        return self.backToRowStartOrRetract()

    def backResetRows(self):
        rows = {self.ROLES_LIST_ID: self.rolesListControl,
                self.REVIEWS_LIST_ID: self.reviewsListControl,
                self.EXTRA_LIST_ID: self.extraListControl,
                self.RELATED_LIST_ID: self.relatedListControl}
        rows.update(zip(self.COLLECTION_LIST_IDS, self.collectionListControls))
        return rows

    def onAction(self, action):
        # Hosted: the host sees the action first (kodigui.BaseWindow.routeActionToHost()).
        if self.routeActionToHost(action):
            return
        try:
            controlID = self.getFocusId()

            if not controlID and self.lastFocusID and not action == xbmcgui.ACTION_MOUSE_MOVE:
                self.setFocusId(self.lastFocusID)

            if action == xbmcgui.ACTION_CONTEXT_MENU:
                # Swallowed on anything without a context menu of its own, rather than shoving focus
                # into OPTIONS_GROUP_ID (the header, group 200) the way this used to. That jump was
                # written when the header still carried the home/search buttons; every screen here now
                # blanks header_topleft in favour of the sidebar, so group 200's own
                # <defaultcontrol always="true">201</defaultcontrol> (default.xml.tpl) points at a
                # control that no longer exists. What's left inside it is the audio widget (204, only
                # focusable while Player.HasAudio) and, on Seasons/Episodes, the season tabs (205/206,
                # only when they have items) - so with nothing playing and no tabs the group has no
                # focusable child at all, Kodi drops focus entirely and the screen goes dead to
                # everything but Back (live-reported on Artist, Pre-play and skipChildren Seasons;
                # where tabs did exist the same jump landed focus on the tab bar instead).
                # Nothing is exempt here any more: in-progress items get their own Resume/Restart
                # buttons instead of a single Play, so the old "menu on Play forces the
                # resume-or-restart dropdown" shortcut (force_resume_menu) had nothing left to offer
                # and is gone - Play is inert under menu, on request.
                return

            elif action == xbmcgui.ACTION_NAV_BACK:
                if self.dismissSidebarPopupOnBack():
                    return
                if self.handleBack():
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
        # Not live on its host yet, or any more (kodigui.BaseWindow.ignoresInput()).
        if self.ignoresInput():
            return
        if self.handleSidebarDropdownClick(controlID):
            return
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
        elif controlID == self.RESUME_BUTTON_ID:
            self.playVideo(force_resume=True)
        elif controlID == self.RESTART_BUTTON_ID:
            self.playVideo(start_over=True)
        elif controlID in self.WL_RELEVANT_BTNS and self.fromWatchlist and self.wl_availability:
            self.wl_item_opener(self.video, self.openItem)
        elif controlID in self.WL_BTN_STATE_BTNS:
            is_watchlisted = self.toggleWatchlist(self.video)
            self.waitAndSetFocus(self.WL_BTN_STATE_WATCHLISTED if is_watchlisted else self.WL_BTN_STATE_NOT_WATCHLISTED)
        elif controlID == self.PLAYER_STATUS_BUTTON_ID:
            self.showAudioPlayer()
        elif controlID == self.INFO_BUTTON_ID:
            self.infoButtonClicked()
        elif controlID == self.SUMMARY_BUTTON_ID:
            self.summaryButtonClicked()
        elif controlID == self.SETTINGS_BUTTON_ID:
            self.settingsButtonClicked()
        elif controlID == self.TRAILER_BUTTON_ID:
            self.openItem(item=self.trailer)
        elif controlID == self.OPTIONS_BUTTON_ID:
            self.optionsButtonClicked()

    def onFocus(self, controlID):
        # Not live on its host yet, or any more (kodigui.BaseWindow.ignoresInput()).
        if self.ignoresInput():
            return
        self.reselectActiveSection(controlID, self.lastFocusID)
        self.lastFocusID = controlID

        if 399 < controlID < 500:
            self.setProperty('hub.focus', str(controlID - 400))
            self.setProperty('row.focused', '1')
        else:
            # row.focused (not hub.focus, which is never cleared once set - other controls key off
            # it staying "seen at least once") drives default_background.xml.tpl's scroll-dim scrim,
            # which needs to toggle back off when focus returns to the details/button area above the
            # row list.
            self.setProperty('row.focused', '')

        # SUMMARY_BUTTON_ID needs the same exclusion as ControlGroup(300)'s own focus below: it's a
        # header control that happens to live inside group 50 but outside group 300, so without this
        # the elif below misread focusing it as "focus moved into deeper content" and slid the whole
        # header up - same bug/fix as ShowWindow.onFocus()'s own copy of this (subitems.py), which
        # this was ported from.
        if (controlID == self.SUMMARY_BUTTON_ID or
                xbmc.getCondVisibility('ControlGroup(50).HasFocus(0) + ControlGroup(300).HasFocus(0)')):
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
        # The dialog's own Video entry (playersettings.showVideoDialog()) can change mediaChoice
        # itself - the video pill's own visible text is driven by the video.res/video.rendering
        # *properties* (media_info_pills.xml.tpl's label markup), separate from video_text below
        # (only ever used for the pill's width, via setAudioAndSubtitleInfo() ->
        # resizeMediaInfoPills()). Without refreshing these two properties here too, the pill kept
        # showing the previous version's resolution/codec even though the underlying media had
        # actually switched (live-reported) - setInfo() sets them the same way on a full refresh,
        # this is just that same pair repeated for this narrower post-dialog case.
        res = self.video.resolutionString()
        rendering = self.video.videoCodecRendering
        self.setProperty('video.res', res)
        self.setProperty('video.rendering', rendering)
        video_text = u'{0} {1}'.format(res, rendering) if rendering else res
        self.setAudioAndSubtitleInfo(video_text)

    def infoButtonClicked(self):
        # Popup, not opener.handleOpen(info.InfoWindow, ...) any more - same change episodes.py's
        # own Info button already got (infoButtonClicked() there):
        # title/subtitle/thumb/summary all duplicate what's already visible on this screen itself,
        # only the media/file/stream detail block (formatMediaDetails() - info.py, shared with
        # InfoWindow's own getVideoInfo()) was actually new information. A dialog like Settings'/
        # More's own popups, not a full window transition, so no cameFrom bookkeeping needed either
        # (that existed only for InfoWindow's own close-and-return-to-this-window flow).
        info.showMediaDetails(self.video)

    def summaryButtonClicked(self):
        info.showSummary(self.video.title, self.video.summary)

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
        # x (misnamed here for a long time), not y: showDropdown takes (x, y), and with
        # close_direction='left' this anchor is what keeps the dropdown under the More button as the
        # row ahead of it grows.
        # 518, not the old 880: stale since the button row resize, exactly as Seasons' own copy of
        # this static fallback was - see optionsButtonClicked() (subitems.py) for the derivation,
        # which applies verbatim here since this row went through the same 22->63 / 152->70 /
        # itemgap -20->0 change: (880 - 22) * 70/132 + 63 = 518.
        # 70 per extra button, not the old 106: that never matched a pitch in either layout (the old
        # one was 132), and the current row is 70-wide boxes at itemgap 0, so one more visible button
        # is exactly 70px of the row.
        # in.progress (setInfo()), not the old global hide.resume property: that global was only ever
        # written by refreshInfo(), which onFirstInit()/setup() don't call, so on a freshly opened
        # window it still held the *previous* item's state - an unwatched movie opened right after an
        # in-progress one shifted this anchor as though a resume button were there. in.progress is
        # set by setInfo() on both paths and is the very property the row's Play/Resume+Restart split
        # keys off, so it can't disagree with what's on screen. It costs one button, not two: Resume
        # and Restart replace Play rather than joining it.
        pos_x = 518
        if self.getProperty('in.progress'):
            pos_x += 70
        if self.getProperty('trailer.button'):
            pos_x += 70
        choice = dropdown.showDropdown(options, (pos_x, 618), close_direction='left')
        if not choice:
            return

        if choice['key'] == 'mark_watched':
            self.toggleWatched(self.video, state=True, **VIDEO_RELOAD_KW)
        elif choice['key'] == 'mark_unwatched':
            self.toggleWatched(self.video, state=False, **VIDEO_RELOAD_KW)
        elif choice['key'] == 'to_season':
            self.processCommand(opener.open(self.video.parentRatingKey, context=self,
                                            entry_section_id=self.entrySectionId,
                                            entry_from_watchlist=self.entryFromWatchlist))
        elif choice['key'] == 'to_show':
            self.processCommand(opener.open(self.video.grandparentRatingKey, context=self,
                                            entry_section_id=self.entrySectionId,
                                            entry_from_watchlist=self.entryFromWatchlist))
        elif choice['key'] == 'to_section':
            self.cameFrom = "library"
            section = plexlibrary.LibrarySection.fromFilter(self.video)
            self.processCommand(opener.sectionClicked(section, context=self,
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

    def playVideo(self, from_auto_play=False, force_resume=False, start_over=False):
        if self.playBtnClicked:
            return

        if not self.video.available():
            util.messageDialog(T(32312, 'Unavailable'), T(32313, 'This item is currently unavailable.'))
            return

        resume = False
        # start_over is the Restart button's own request, self.startOver the same thing carried in
        # from whoever opened this window (kwargs) - either one skips the resume question entirely
        # and leaves resume False, i.e. plays from the beginning.
        if self.video.viewOffset.asInt() and not self.startOver and not start_over:
            if force_resume:
                # Dedicated Resume button - the button itself already made the choice explicit, so
                # neither the dropdown nor the assume_resume check below applies.
                resume = True
            elif not util.getSetting('assume_resume'):
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
                    videoplayer.play(play_queue=pl, bgm=self.useBGM, context=self))
                return True

        self.processCommand(videoplayer.play(video=self.video, resume=resume, bgm=self.useBGM, context=self))
        return True

    def openItem(self, control=None, item=None, inherit_from_watchlist=True, server=None, is_watchlisted=False, **kw):
        if not item:
            mli = control.getSelectedItem()
            if not mli:
                return
            item = mli.dataSource

        self.processCommand(opener.open(item, context=self,
                                        from_watchlist=self.fromWatchlist if inherit_from_watchlist else False,
                                        server=server, is_watchlisted=is_watchlisted,
                                        entry_section_id=self.entrySectionId,
                                        entry_from_watchlist=self.entryFromWatchlist, **kw))

    def focusPlayButton(self, extended=False):
        if extended:
            self.setFocusId(self.wl_play_button_id)
            return
        # Resume, not Play, for a part-watched video: 302 is hidden in that state (in.progress -
        # setInfo()), and focusing a hidden control would just fall through to whatever Kodi picks
        # next, exactly what the wait below exists to prevent.
        button_id = self.RESUME_BUTTON_ID if self.getProperty('in.progress') else self.PLAY_BUTTON_ID
        try:
            if not self.getFocusId() == button_id:
                # the button's own <visible> (unavailable/disable_playback/in.progress) is keyed off
                # properties we just set, but the GUI thread hasn't necessarily recalculated
                # visibility yet - SetFocus on a still-invisible control fails silently and focus
                # falls through elsewhere (e.g. a hub row, which then triggers its slide-into-view
                # animation). Wait for it to actually be visible first.
                self.waitForVisibility(button_id)
                self.setFocusId(button_id)
        except (SystemError, RuntimeError):
            util.ERROR()
            self.setFocusId(button_id)

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
        self.setProperty('duration', self.video.duration and util.durationToShortText(self.video.duration.asInt(), noSpaces=True))
        self.setProperty('summary', util.summaryForBox(self.video.summary))
        self.setProperty('unwatched', not self.video.isWatched and '1' or '')
        self.setBoolProperty('watched', self.video.isFullyWatched)
        self.setBoolProperty('disable_playback', self.fromWatchlist)

        # Drives the button row's Play -> Resume+Restart split (script-plex-pre_play.xml.tpl).
        # Unconditional, unlike the remainingTime property further down: that one lives in the
        # non-watchlist branch, but these two have to be actively cleared for a watchlist item too,
        # or a stale in.progress from a previous video would leave this row showing Resume/Restart
        # over a play button that disable_playback has already hidden.
        # Duration is required, not just the offset: the Resume label carries a time-left suffix
        # computed from it (resume.timeleft), and without one there'd be nothing to put after the
        # bullet. An item with an offset but no duration falls back to plain Play, which still
        # offers resume through the usual assume_resume dropdown (playVideo()).
        view_offset = self.video.viewOffset.asInt()
        duration = self.video.duration.asInt()
        in_progress = bool(view_offset and duration) and not self.fromWatchlist
        self.setBoolProperty('in.progress', in_progress)
        # remainingTimeToShortText's own no-space, 90-minute-cutoff style ("1h31m left"), matching
        # Episodes' own Resume button - not remainingTime's spaced "1h 31m left" below.
        self.setProperty('resume.timeleft', in_progress and T(33615, "{time} left").format(
            time=util.remainingTimeToShortText(duration - view_offset)) or '')

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
        # Separate from 'info' above (used by the info/options dialogs elsewhere, 3 genres joined by
        # ' / ') - the metadata row (pp_meta_row.xml.tpl) wants its own shorter, comma-separated form.
        self.setProperty('genres.short', u', '.join([g.tag for g in self.video.genres()][:2]))
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

            video_text = self.video.resolutionString()
            if self.video.videoCodecRendering:
                video_text = u'{0} {1}'.format(video_text, self.video.videoCodecRendering)

        self.populateRatings(self.video, self)

        # The rest of the shared meta row (CommonMixin.META_ROW_PROPERTIES) this screen has no
        # value for; a Watchlist item has none for the two below either.
        self.blankMetaRow('episode.code')
        if not self.fromWatchlist:
            self.setAudioAndSubtitleInfo(video_text)

            self.setProperty('unavailable', all(not v.isAccessible() for v in self.video.media()) and '1' or '')

            if self.video.viewOffset.asInt():
                self.setProperty('remainingTime', T(33615, "{time} left").format(time=self.video.remainingTimeString))
            else:
                self.setProperty('remainingTime', '')
        else:
            self.blankMetaRow('unavailable', 'remainingTime')

    def setAudioAndSubtitleInfo(self, video_text):
        # discover external audio files for mapped direct play
        if util.getSetting('use_external_audio', False) and hasattr(type(self.video), 'discoverExternalAudioStreams'):
            self.video.discoverExternalAudioStreams()

        sas = self.video.selectedAudioStream()

        audio_text = ''
        if sas:
            audio_text = sas.getTitle(metadata.apiTranslate)
            self.setProperty('audio', audio_text)

        sss = self.video.selectedSubtitleStream(
            forced_subtitles_override=util.getSetting("forced_subtitles_override") and pnUtil.ACCOUNT.subtitlesForced == 0,
            deselect_subtitles=getNativeLanguages(util.getSetting("disable_subtitle_languages") or []))
        if sss:
            subtitles_text = sss.getTitle(metadata.apiTranslate)
        elif self.video.subtitleStreams:
            subtitles_text = T(32481, 'Off')
        else:
            subtitles_text = T(32309, u'None')
        self.setProperty('subtitles', subtitles_text)

        self.resizeMediaInfoPills(video_text, audio_text, subtitles_text)

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
        if self.relatedPaginator is None:
            # closed (doClose() drops it) before this task ran
            return False
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
