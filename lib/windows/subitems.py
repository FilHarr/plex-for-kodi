from __future__ import absolute_import

import gc
import json

from kodi_six import xbmc
from kodi_six import xbmcgui
from plexnet import playlist, util as pnUtil, plexapp, plexlibrary

from lib import metadata
from lib import util
from lib.util import T
from lib.language_util import getNativeLanguages
from . import busy
from . import dropdown
from . import episodes
from . import home
from . import info
from . import kodigui
from . import musicplayer
from . import opener
from . import pagination
from . import playbacksettings
from . import search
from . import tracks
from . import videoplayer
from . import windowutils
from .mixins.seasons import SeasonsMixin
from .mixins.delete_media import DeleteMediaMixin
from .mixins.ratings import RatingsMixin
from .mixins.playbackbtn import PlaybackBtnMixin
from .mixins.watchlist import WatchlistUtilsMixin
from .mixins.thememusic import ThemeMusicMixin
from .mixins.roles import RolesMixin
from .mixins.common import CommonMixin
from .mixins.tasks import TasksMixin


class RelatedPaginator(pagination.BaseRelatedPaginator):
    def getData(self, offset, amount):
        return self.parentWindow.mediaItem.getRelated(offset=offset, limit=amount)


class ShowWindow(kodigui.ControlledWindow, windowutils.UtilMixin, windowutils.SidebarMixin, SeasonsMixin,
                 DeleteMediaMixin, RatingsMixin, RolesMixin, PlaybackBtnMixin, WatchlistUtilsMixin,
                 ThemeMusicMixin, CommonMixin, TasksMixin, playbacksettings.PlaybackSettingsMixin):
    xmlFile = 'script-plex-seasons.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    # 533x300 = 512x288 display size (script-plex-seasons.xml.tpl's extras row) * 104%, the row's own
    # focus-zoom end value - same "fetch at the zoomed-in size, not the at-rest one" pattern the old
    # 299x168 art used (329x185 was that at 110%, its own zoom end value at the time). Shared with
    # PrePlayWindow's own EXTRA_DIM (preplay.py) - both rows use the same art recipe.
    EXTRA_DIM = util.scaleResolution(533, 300)
    RELATED_DIM = util.scaleResolution(268, 402)
    ROLES_DIM = util.scaleResolution(334, 334)
    # 722x162, matching PrePlayWindow's own CLEAR_LOGO_DIM (preplay.py) - the corner poster this used
    # to size around (CLEAR_LOGO_DIM_NO_POSTER, THUMB_POSTER_DIM) is gone, this screen now mirrors
    # pre_play's single-column hero layout exactly.
    CLEAR_LOGO_DIM = util.scaleResolution(722, 162)

    SUB_ITEM_LIST_ID = 400

    ROLES_LIST_ID = 401
    EXTRA_LIST_ID = 402
    RELATED_LIST_ID = 403

    # Header season-tab row, same id Episodes' own equivalent uses (script-plex-episodes.xml.tpl) -
    # unrelated to (and doesn't collide with) the ids above, since it lives in the shared header
    # (group 200, header_middle_add block) rather than this screen's own content group 50.
    SEASON_TABS_LIST_ID = 205
    # Plain-list twin of the row above, used instead once there are 6 seasons or fewer - see that
    # control's own comment in the template for why a type="fixedlist" misbehaves at low item counts.
    # fillSeasonTabs() below decides which of the two actually gets the items.
    SEASON_TABS_LIST_ID_ALT = 206

    OPTIONS_GROUP_ID = 200

    PLAYER_STATUS_BUTTON_ID = 204

    MAIN_BUTTON_GROUP_ID = 300
    INFO_BUTTON_ID = 301
    PLAY_BUTTON_ID = 302
    SHUFFLE_BUTTON_ID = 303
    OPTIONS_BUTTON_ID = 304

    def __init__(self, *args, **kwargs):
        kodigui.ControlledWindow.__init__(self, *args, **kwargs)
        SeasonsMixin.__init__(*args, **kwargs)
        DeleteMediaMixin.__init__(*args, **kwargs)
        PlaybackBtnMixin.__init__(self, *args, **kwargs)
        WatchlistUtilsMixin.__init__(self)
        ThemeMusicMixin.__init__(self)
        TasksMixin.__init__(self)
        self.mediaItem = kwargs.get('media_item')
        self.parentList = kwargs.get('parent_list')
        self.cameFrom = kwargs.get('came_from')
        self.fromWatchlist = kwargs.get('from_watchlist', False)
        self.isExternal = kwargs.get('external_item', False)
        self.directlyFromWatchlist = kwargs.get('directly_from_watchlist')
        self.is_watchlisted = kwargs.get('is_watchlisted')

        # Sidebar entry-section persistence (ported from Sidebar-Tab-Unification's
        # mellow-pondering-magpie.md, 2026-08-18) - see preplay.py's PrePlayWindow.__init__ for the
        # full reasoning; identical shape here.
        self.entrySectionId = kwargs.get('entry_section_id')
        self.entryFromWatchlist = kwargs.get('entry_from_watchlist', False)
        if self.entrySectionId is None and not self.entryFromWatchlist:
            self.entrySectionId = self.mediaItem.getLibrarySectionId()
            self.entryFromWatchlist = self.fromWatchlist or self.directlyFromWatchlist

        self.mediaItems = None
        self.exitCommand = None
        self.lastFocusID = None
        self.lastNonOptionsFocusID = None
        self.manuallySelectedSeason = False
        self.initialized = False
        self.relatedPaginator = None
        self.useBGM = False
        # hashed-orbiting-pizza.md Phase 2: None here means "build my own sectionList" (a
        # standalone/un-hosted open) - a hosted open (LibraryWindow._setupCurrent(), library.py)
        # overwrites this with the host's own sectionList object before onFirstInit() runs.
        self.sectionList = None

    def doClose(self, **kw):
        self.relatedPaginator = None
        kodigui.ControlledWindow.doClose(self)
        TasksMixin.doClose(self)

    def onFirstInit(self):
        self.focusPlayButton()
        self.subItemListControl = kodigui.ManagedControlList(self, self.SUB_ITEM_LIST_ID, 5)
        self.rolesListControl = kodigui.ManagedControlList(self, self.ROLES_LIST_ID, 5)
        self.extraListControl = kodigui.ManagedControlList(self, self.EXTRA_LIST_ID, 5)
        self.relatedListControl = kodigui.ManagedControlList(self, self.RELATED_LIST_ID, 5)
        self.seasonTabsControl = kodigui.ManagedControlList(self, self.SEASON_TABS_LIST_ID, 5)
        self.seasonTabsListControl = kodigui.ManagedControlList(self, self.SEASON_TABS_LIST_ID_ALT, 5)

        if self.sectionList is None:
            self.sectionList = kodigui.ManagedControlList(self, self.SECTION_LIST_ID, 15)
            self.buildSectionList()
        else:
            self.sectionList.newControl(self)
        self.displayServerAndUser()

        self.setup()
        self.initialized = True
        self.themeMusicInit(self.mediaItem)

        # focusPlayButton() above gives the window something focused immediately, before setup() has
        # populated the season row - the screen now opens on the play button instead of jumping focus
        # to the season row once it's filled (as it used to). Watchlist screens already drive focus onto
        # whichever watchlist button reflects this item's availability (setup() -> watchlistItemAvailable(),
        # see mixins/watchlist.py's wl_set_btn()), independently of this.

    def onReInit(self):
        PlaybackBtnMixin.onReInit(self)
        self.wl_auto_remove(self.mediaItem)
        self.checkIsWatchlisted(self.mediaItem)
        self.themeMusicReinit(self.mediaItem)

    def setup(self):
        if self.isExternal:
            # fixme, multiple? choice?
            self.mediaItem.related_source = "more-from-credits"
        self.mediaItem.reload(includeExtras=1, includeExtrasCount=10, includeOnDeck=1)
        self.relatedPaginator = RelatedPaginator(self.relatedListControl, leaf_count=int(self.mediaItem.relatedCount),
                                                 parent_window=self)

        self.watchlist_setup(self.mediaItem)
        if self.fromWatchlist:
            self.watchlistItemAvailable(self.mediaItem, shortcut_watchlisted=self.directlyFromWatchlist)
        if not self.directlyFromWatchlist:
            self.checkIsWatchlisted(self.mediaItem)
        else:
            self.setBoolProperty("is_watchlisted", self.is_watchlisted)

        self.updateProperties()
        self.setBoolProperty("initialized", True)
        # fill() (the season row) runs synchronously, unlike the rest below - it's this screen's primary
        # content (same treatment episodes.py's _setup() gives fillEpisodes()), and onFirstInit() needs it
        # populated before it can focus the season row as the screen's default control. The rest are
        # secondary content, postponed to background threads same as before.
        self.fill()
        self.batch_simple([(self.fillExtras, None, None),
                           (self.fillRelated, None, None),
                           (self.fillRoles, None, None)])

    def updateProperties(self):
        self.setProperty('title', self.mediaItem.title)
        logo = util.clearLogoFrom(self.mediaItem, *self.CLEAR_LOGO_DIM)
        self.setProperty('clear.logo', logo)
        self.setProperty('summary', self.mediaItem.summary)
        self.updateBackgroundFrom(self.mediaItem)
        self.setProperty('duration', util.durationToShortText(self.mediaItem.fixedDuration(), noSpaces=True))
        self.setProperty('info', '')
        self.setProperty('date', self.mediaItem.year)
        self.setProperty('content.rating', self.mediaItem.contentRating.split('/', 1)[-1])
        season_count = self.mediaItem.childCount
        season_str = T(34006, '{} season') if int(season_count or 0) == 1 else T(34003, '{} seasons')
        season_text = season_str.format(season_count)
        words = season_text.split(' ')
        words[-1] = words[-1].capitalize()
        self.setProperty('season.count', ' '.join(words))
        self.setBoolProperty('disable_playback', self.fromWatchlist)
        if not self.mediaItem.isWatched:
            self.setProperty('unwatched.count', str(self.mediaItem.unViewedLeafCount) or '')
            self.setBoolProperty('unwatched.count.large', self.mediaItem.unViewedLeafCount > 999)
        else:
            self.setBoolProperty('watched', self.mediaItem.isWatched)

        self.setProperty('extras.header', T(32305, 'Extras'))
        self.setProperty('related.header', T(32306, 'Related Shows') if not self.fromWatchlist else T(34018, 'Related Media'))

        if self.mediaItem.creator:
            self.setProperty('studio', self.mediaItem.creator)
        elif self.mediaItem.studio:
            self.setProperty('studio', self.mediaItem.studio)

        genres = self.mediaItem.genres()
        self.setProperty('info', genres and (u' / '.join([g.tag for g in genres][:3])) or '')
        # Separate from 'info' above (used by the info/options dialogs elsewhere, 3 genres joined by
        # ' / ') - the metadata row (pp_meta_row.xml.tpl, shared with pre_play) wants its own shorter,
        # comma-separated form.
        self.setProperty('genres.short', genres and u', '.join([g.tag for g in genres][:2]) or '')

        if self.fromWatchlist and not self.wl_availability:
            self.setProperty('wl_server_availability_verbose',
                             util.cleanLeadingZeros(self.mediaItem.originallyAvailableAt.asDatetime('%B %d, %Y')))

        self.populateRatings(self.mediaItem, self)

        sas = self.mediaItem.selectedAudioStream()
        self.setProperty('audio', sas and sas.getTitle() or 'None')

        sss = self.mediaItem.selectedSubtitleStream(
            forced_subtitles_override=util.getSetting("forced_subtitles_override") and pnUtil.ACCOUNT.subtitlesForced == 0,
            deselect_subtitles=getNativeLanguages(util.getSetting("disable_subtitle_languages") or []))
        self.setProperty('subtitles', sss and sss.getTitle() or 'None')

    def focusPlayButton(self, extended=False):
        if extended:
            self.setFocusId(self.wl_play_button_id)
            return
        try:
            if not self.getFocusId() == self.PLAY_BUTTON_ID:
                self.setFocusId(self.PLAY_BUTTON_ID)
        except (SystemError, RuntimeError):
            self.setFocusId(self.PLAY_BUTTON_ID)

    def onAction(self, action):
        try:
            controlID = self.getFocusId()

            if controlID == self.SECTION_LIST_ID:
                self.checkSectionItem(action=action)

            if not controlID and self.lastFocusID and not action == xbmcgui.ACTION_MOUSE_MOVE:
                self.setFocusId(self.lastFocusID)

            if controlID == self.SUB_ITEM_LIST_ID and action in (xbmcgui.ACTION_MOVE_LEFT, xbmcgui.ACTION_MOVE_RIGHT):
                self.manuallySelectedSeason = True

            elif action == xbmcgui.ACTION_CONTEXT_MENU:
                if controlID == self.SUB_ITEM_LIST_ID and not self.isExternal:
                    self.optionsButtonClicked(from_item=True)
                    return
                elif not xbmc.getCondVisibility('ControlGroup({0}).HasFocus(0)'.format(self.OPTIONS_GROUP_ID)):
                    self.lastNonOptionsFocusID = self.lastFocusID
                    self.setFocusId(self.OPTIONS_GROUP_ID)
                    return
                else:
                    if self.lastNonOptionsFocusID:
                        self.setFocusId(self.lastNonOptionsFocusID)
                        self.lastNonOptionsFocusID = None
                        return

            elif controlID == self.SUB_ITEM_LIST_ID and self.isWatchedAction(action):
                item = self.subItemListControl.getSelectedItem()
                if not item.dataSource:
                    return

                self.toggleWatched(item.dataSource)
                return

            elif action in (xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_CONTEXT_MENU):
                # Matches Recommended's own hub rows (LibraryWindow.checkHubItem(), library.py): Back on
                # a row scrolled away from its first item resets to item 0 and stops there (swallowed),
                # rather than immediately leaving the screen - a second Back, now already at item 0,
                # falls through to the normal handling below.
                if action == xbmcgui.ACTION_NAV_BACK:
                    rowControl = {self.SUB_ITEM_LIST_ID: self.subItemListControl,
                                 self.ROLES_LIST_ID: self.rolesListControl,
                                 self.EXTRA_LIST_ID: self.extraListControl,
                                 self.RELATED_LIST_ID: self.relatedListControl}.get(controlID)
                    if rowControl:
                        pos = rowControl.getSelectedPos()
                        if pos is not None and pos > 0:
                            rowControl.selectItem(0)
                            return

                if not xbmc.getCondVisibility('ControlGroup({0}).HasFocus(0)'.format(
                        self.OPTIONS_GROUP_ID)) and \
                        (not util.addonSettings.fastBack or action == xbmcgui.ACTION_CONTEXT_MENU):
                    if self.getProperty('on.extras'):
                        self.setFocusId(self.OPTIONS_GROUP_ID)
                        return

            if action == xbmcgui.ACTION_LAST_PAGE and xbmc.getCondVisibility('ControlGroup(300).HasFocus(0)'):
                next(self)
            elif action == xbmcgui.ACTION_NEXT_ITEM:
                self.setFocusId(300)
                next(self)
            elif action == xbmcgui.ACTION_FIRST_PAGE and xbmc.getCondVisibility('ControlGroup(300).HasFocus(0)'):
                self.prev()
            elif action == xbmcgui.ACTION_PREV_ITEM:
                self.setFocusId(300)
                self.prev()
            elif self.isWatchedAction(action) and xbmc.getCondVisibility('ControlGroup({}).HasFocus(0)'.format(self.MAIN_BUTTON_GROUP_ID)):
                self.toggleWatched(self.mediaItem)
                return

            if action == xbmcgui.ACTION_MOVE_UP and (controlID == self.SUB_ITEM_LIST_ID or
                    self.INFO_BUTTON_ID <= controlID <= self.OPTIONS_BUTTON_ID):
                self.updateBackgroundFrom(self.mediaItem)

            if controlID == self.RELATED_LIST_ID:
                if self.relatedPaginator and self.relatedPaginator.boundaryHit:
                    self.relatedPaginator.paginate()
                    return

        except:
            util.ERROR()

        kodigui.ControlledWindow.onAction(self, action)

    def onClick(self, controlID):
        if self.handleSidebarDropdownClick(controlID):
            return
        if controlID == self.SECTION_LIST_ID:
            self.sectionClicked()
        elif controlID == self.SUB_ITEM_LIST_ID:
            if not self.fromWatchlist:
                self.subItemListClicked()
            else:
                mli = self.subItemListControl.getSelectedItem()
                if not mli:
                    return
                if self.wl_availability:
                    self.wl_item_opener(mli.dataSource, self.openItem)
                else:
                    # Not available anywhere - inherit_from_watchlist=False keeps the opened
                    # season/episode from being (wrongly) treated as playable, but it also drops
                    # from_watchlist entirely, which the sidebar relies on to highlight Watchlist.
                    # directly_from_watchlist carries that context separately; is_watchlisted is
                    # already known from this show (self.is_watchlisted) so there's no need to
                    # make the destination window re-check it.
                    self.openItem(item=mli.dataSource, inherit_from_watchlist=False,
                                 is_watchlisted=self.is_watchlisted, directly_from_watchlist=True)
        elif controlID in (self.SEASON_TABS_LIST_ID, self.SEASON_TABS_LIST_ID_ALT):
            self.seasonTabClicked(controlID)
        elif controlID == self.PLAYER_STATUS_BUTTON_ID:
            self.showAudioPlayer()
        elif controlID == self.EXTRA_LIST_ID:
            self.openItem(self.extraListControl)
        elif controlID == self.RELATED_LIST_ID:
            self.openItem(self.relatedListControl)
        elif controlID == self.ROLES_LIST_ID:
            if not self.roleClicked():
                return
        elif controlID == self.INFO_BUTTON_ID:
            self.infoButtonClicked()
        elif controlID == self.PLAY_BUTTON_ID:
            self.playButtonClicked()
        elif controlID in self.WL_RELEVANT_BTNS and self.fromWatchlist and self.wl_availability:
            self.wl_item_opener(self.mediaItem, self.openItem)
        elif controlID in self.WL_BTN_STATE_BTNS:
            is_watchlisted = self.toggleWatchlist(self.mediaItem)
            self.waitAndSetFocus(self.WL_BTN_STATE_WATCHLISTED if is_watchlisted else self.WL_BTN_STATE_NOT_WATCHLISTED)
        elif controlID == self.SHUFFLE_BUTTON_ID:
            self.shuffleButtonClicked()
        elif controlID == self.OPTIONS_BUTTON_ID:
            self.optionsButtonClicked()

    def onFocus(self, controlID):
        self.reselectActiveSection(controlID, self.lastFocusID)
        self.lastFocusID = controlID

        if controlID == self.SECTION_LIST_ID:
            self.checkSectionItem()

        if 399 < controlID < 500:
            # controlID - 399, not - 400: gives the season row its own tier (1) instead of colliding
            # with the button row's own reset-to-'0' below, so group 50's slide animations (see the
            # template) can treat "focus is somewhere in the season row and beyond" as one properly
            # ordered depth scale - 1=season row, 2=roles, 3=extras, 4=related - instead of needing a
            # separate one-off condition just for the season row.
            self.setProperty('hub.focus', str(controlID - 399))
            self.setProperty('row.focused', '1')
        else:
            # row.focused (not hub.focus, which is never cleared once set - the row-collapse slide
            # animations above key off it staying "seen at least once") drives default_background.xml.tpl's
            # scroll-dim scrim - same mechanism as Pre-play (preplay.py's own onFocus) - which needs to
            # toggle back off when focus returns to the season row/button row above.
            self.setProperty('row.focused', '')

        # controlID == SUB_ITEM_LIST_ID counts as "not on extras" too: on.extras drives its own -300
        # slide (group 50, template) that's meant for Roles/Extras/Related only - the season row already
        # gets its own, correctly-sized tier-1 slide (-415) above, so on.extras firing there too would
        # stack an unwanted extra -300 on top of it.
        if controlID == self.SUB_ITEM_LIST_ID or xbmc.getCondVisibility('ControlGroup(50).HasFocus(0) + ControlGroup(300).HasFocus(0)'):
            self.setProperty('on.extras', '')
            if controlID != self.SUB_ITEM_LIST_ID:
                # hub.focus (set above, only for controlIDs 400-499) is otherwise never reset once focus
                # leaves the seasons/roles/extras/related row stack for the button row - it's not in that
                # range, so it'd keep whatever value the last-focused row left it at. The row-collapse slide
                # animations on group 50 key off hub.focus, not on.extras, so without this they'd stay
                # collapsed even after on.extras clears and the header reappears - see episodes.py's onFocus
                # for the identical fix and rationale. Guarded to the button row specifically: the season
                # row must keep its own tier-1 value (1) rather than being stomped back to '0' here too.
                self.setProperty('hub.focus', '0')
        elif xbmc.getCondVisibility('ControlGroup(50).HasFocus(0) + !ControlGroup(300).HasFocus(0)'):
            self.setProperty('on.extras', '1')

    def buildSectionList(self):
        """Populate the sidebar's section list. Mirrors library.py's buildSectionList()/
        home.py's showSections() and episodes.py's/preplay.py's own copies - see library.py:675 for why
        this isn't shared code yet.
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
        """Sidebar avatar/username and server icon/name. Mirrors library.py's/episodes.py's/preplay.py's
        displayServerAndUser() (see library.py:777 for why home.py's own version doesn't reach this
        window - window properties are per-window).
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

    def toggleWatched(self, item, state=None, **kw):
        watched = super(ShowWindow, self).toggleWatched(item, state=state, **kw)
        if watched is None:
            return

        if watched:
            self.wl_auto_remove(self.mediaItem)
            self.checkIsWatchlisted(self.mediaItem)
        self.updateItems()
        self.updateProperties()
        util.MONITOR.watchStatusChanged()

    def getMediaItems(self):
        return False

    def next(self):
        if not self._next():
            return
        self.setup()

    __next__ = next

    @busy.dialog()
    def _next(self):
        if self.parentList:
            mli = self.parentList.getListItemByDataSource(self.mediaItem)
            if not mli:
                return False

            pos = mli.pos() + 1
            if not self.parentList.positionIsValid(pos):
                pos = 0

            self.mediaItem = self.parentList.getListItem(pos).dataSource
        else:
            if not self.getMediaItems():
                return False

            if self.mediaItem not in self.mediaItems:
                return False

            pos = self.mediaItems.index(self.mediaItem)
            pos += 1
            if pos >= len(self.mediaItems):
                pos = 0

            self.mediaItem = self.mediaItems[pos]

        return True

    def prev(self):
        if not self._prev():
            return
        self.setup()

    @busy.dialog()
    def _prev(self):
        if self.parentList:
            mli = self.parentList.getListItemByDataSource(self.mediaItem)
            if not mli:
                return False

            pos = mli.pos() - 1
            if pos < 0:
                pos = self.parentList.size() - 1

            self.mediaItem = self.parentList.getListItem(pos).dataSource
        else:
            if not self.getMediaItems():
                return False

            if self.mediaItem not in self.mediaItems:
                return False

            pos = self.mediaItems.index(self.mediaItem)
            pos -= 1
            if pos < 0:
                pos = len(self.mediaItems) - 1

            self.mediaItem = self.mediaItems[pos]

        return True

    def searchButtonClicked(self):
        self.processCommand(search.dialog(self, section_id=self.mediaItem.getLibrarySectionId() or None))

    def roleSectionId(self):
        return self.entrySectionId

    def roleFromWatchlist(self):
        return self.entryFromWatchlist

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

    def seasonTabClicked(self, controlID=None):
        control = self.seasonTabsListControl if controlID == self.SEASON_TABS_LIST_ID_ALT else self.seasonTabsControl
        mli = control.getSelectedItem()
        # No dataSource means the pinned "Show" tab - already this screen, nothing to do.
        if not mli or not mli.dataSource:
            return

        if not self.fromWatchlist:
            episodes.EpisodesWindow.open(season=mli.dataSource, show=self.mediaItem,
                                         parent_list=self.subItemListControl, from_watchlist=self.fromWatchlist,
                                         directly_from_watchlist=self.directlyFromWatchlist,
                                         is_watchlisted=self.is_watchlisted,
                                         entry_section_id=self.entrySectionId,
                                         entry_from_watchlist=self.entryFromWatchlist)
        elif self.wl_availability:
            self.wl_item_opener(mli.dataSource, self.openItem)
        else:
            self.openItem(item=mli.dataSource, inherit_from_watchlist=False,
                         is_watchlisted=self.is_watchlisted, directly_from_watchlist=True)

    def subItemListClicked(self):
        mli = self.subItemListControl.getSelectedItem()
        if not mli:
            return

        update = False

        w = None
        if self.mediaItem.type == 'show':
            w = episodes.EpisodesWindow.open(season=mli.dataSource, show=self.mediaItem,
                                             parent_list=self.subItemListControl, from_watchlist=self.fromWatchlist,
                                             directly_from_watchlist=self.directlyFromWatchlist,
                                             is_watchlisted=self.is_watchlisted,
                                             entry_section_id=self.entrySectionId,
                                             entry_from_watchlist=self.entryFromWatchlist)
            update = True
        elif self.mediaItem.type == 'artist':
            w = tracks.AlbumWindow.open(album=mli.dataSource, parent_list=self.subItemListControl,
                                        entry_section_id=self.entrySectionId)

        if not mli:
            return

        if not mli.dataSource.exists():
            self.subItemListControl.removeItem(mli.pos())

        if not self.subItemListControl.size():
            self.closeWithCommand(w.exitCommand)
            del w
            gc.collect(2)
            return

        if update:
            if mli and mli.dataSource:
                mli.setProperty('unwatched.count', not mli.dataSource.isWatched and str(mli.dataSource.unViewedLeafCount) or '')
            self.mediaItem.reload(includeRelated=1, includeRelatedCount=10, includeExtras=1, includeExtrasCount=10)
            self.updateProperties()

        try:
            self.processCommand(w.exitCommand)
        finally:
            del w
            gc.collect(2)

    def infoButtonClicked(self):
        fallback = 'script.plex/thumb_fallbacks/{0}.png'.format(self.mediaItem.type == 'show' and 'show' or 'music')
        genres = u' / '.join([g.tag for g in util.removeDups(self.mediaItem.genres())][:6])

        w = info.InfoWindow.open(
            title=self.mediaItem.title,
            sub_title=genres,
            thumb=self.mediaItem.defaultThumb,
            thumb_fallback=fallback,
            info=self.mediaItem.summary,
            background=self.getProperty('background'),
            is_square=bool(isinstance(self, ArtistWindow)),
            video=self.mediaItem
        )
        del w
        util.garbageCollect()

    def playButtonClicked(self, shuffle=False):
        if self.playBtnClicked:
            return

        items = self.mediaItem.all(unwatched=True)
        if not shuffle and self.mediaItem.type == 'show':
            items = playlist.reorder_with_specials(
                items, mode=util.getSetting('tv_specials_order', 'default')
            )
        pl = playlist.LocalPlaylist(items, self.mediaItem.getServer())
        resume = False
        if not shuffle and self.mediaItem.type == 'show':
            resume = self.getNextShowEp(pl, items, self.mediaItem.title)
            if resume is None:
                return

        self.playBtnClicked = True
        pl.shuffle(shuffle, first=True)
        videoplayer.play(play_queue=pl, resume=resume, bgm=self.useBGM)

    def shuffleButtonClicked(self):
        self.playButtonClicked(shuffle=True)

    def optionsButtonClicked(self, from_item=None):
        options = []
        if xbmc.getCondVisibility('Player.HasAudio + MusicPlayer.HasNext'):
            options.append({'key': 'play_next', 'display': 'Play Next'})

        item = self.mediaItem
        if from_item:
            sel = self.subItemListControl.getSelectedItem()
            if sel.dataSource:
                item = sel.dataSource

        if not item:
            return

        if item.type != 'artist':
            if item.isWatched:
                options.append({'key': 'mark_unwatched', 'display': T(32318, 'Mark Unplayed')})
            else:
                options.append({'key': 'mark_watched', 'display': T(32319, 'Mark Played')})

            if item.type == "show":
                if options:
                    options.append(dropdown.SEPARATOR)

                options.append({'key': 'playback_settings', 'display': T(32925, 'Playback Settings')})
                if plexapp.ACCOUNT.isAdmin and item.server.allowsMediaDeletion:
                    options.append(dropdown.SEPARATOR)
                    if plexapp.ACCOUNT.isAdmin:
                        options.append({'key': 'refresh', 'display': T(33719, 'Refresh metadata')})
                    options.append({'key': 'delete', 'display': T(32322, 'Delete')})
            elif item.type == "season":
                if plexapp.ACCOUNT.isAdmin and item.server.allowsMediaDeletion:
                    options.append(dropdown.SEPARATOR)
                    if plexapp.ACCOUNT.isAdmin:
                        options.append({'key': 'refresh', 'display': T(33719, 'Refresh metadata')})
                    options.append({'key': 'delete', 'display': T(32975, 'Delete Season')})

        # if xbmc.getCondVisibility('Player.HasAudio') and self.section.TYPE == 'artist':
        #     options.append({'key': 'add_to_queue', 'display': 'Add To Queue'})

        # if False:
        #     options.append({'key': 'add_to_playlist', 'display': 'Add To Playlist'})

        options.append(dropdown.SEPARATOR)

        options.append({'key': 'to_section', 'display': u'Go to {0}'.format(self.mediaItem.getLibrarySectionTitle())})

        if 'items' in util.getSetting('cache_requests'):
            options.append({'key': 'cache_reset', 'display': T(33728, "Clear cache for item")})

        pos = (880, 618)
        if from_item:
            viewPos = self.subItemListControl.getViewPosition()
            optsLen = len(list(filter(None, options)))
            # dropDown handles any overlap with the right window boundary so we don't need to care here
            pos = ((((viewPos + 1) * 218) - 100), 460 if optsLen < 7 else 460 - 66 * (optsLen - 6))

        choice = dropdown.showDropdown(options, pos, close_direction='left')
        if not choice:
            return

        if choice['key'] == 'play_next':
            xbmc.executebuiltin('PlayerControl(Next)')
        elif choice['key'] == 'mark_watched':
            self.toggleWatched(item, state=True)
        elif choice['key'] == 'mark_unwatched':
            self.toggleWatched(item, state=False)
        elif choice['key'] == 'to_section':
            self.cameFrom = "library"
            section = plexlibrary.LibrarySection.fromFilter(self.mediaItem)
            self.processCommand(opener.sectionClicked(section, context=self,
                                                      came_from=self.mediaItem.ratingKey)
                                )
        elif choice['key'] == 'playback_settings':
            self.playbackSettings(self.mediaItem, pos, False)
        elif choice['key'] == 'delete':
            if self.delete(item):
                # cheap way of requesting a home hub refresh because of major deletion
                util.MONITOR.watchStatusChanged()
                self.initialized = False
                self.setBoolProperty("initialized", False)
                self.setup()
                self.initialized = True
                self.setFocusId(self.PLAY_BUTTON_ID)
        elif choice['key'] == 'refresh':
            item.refresh()
            self.updateItems()
            self.updateProperties()

        elif choice["key"] == "cache_reset":
            try:
                util.DEBUG_LOG('Clearing requests cache for {}...', item)
                item.clearCache()
                self.updateItems()
                self.updateProperties()
            except Exception as e:
                util.DEBUG_LOG("Couldn't clear cache: {}", e)

    def getRoleItemDDPosition(self, *args, **kwargs):
        y = 980
        if xbmc.getCondVisibility('Control.IsVisible(500)'):
            y += 380
        if xbmc.getCondVisibility('!String.IsEmpty(Window.Property(on.extras))'):
            y -= 200
        if xbmc.getCondVisibility('Integer.IsGreater(Window.Property(hub.focus),0) + Control.IsVisible(500)'):
            y -= 650

        return super(ShowWindow, self).getRoleItemDDPosition(y=y, container_id="401")

    def updateItems(self):
        self.fill(update=True)

    def createListItem(self, obj):
        mli = kodigui.ManagedListItem(
            obj.title or '',
            thumbnailImage=obj.defaultThumb.asTranscodedImageURL(*self.THUMB_DIMS[self.mediaItem.type]['item.thumb']),
            data_source=obj
        )
        return mli

    @busy.dialog()
    def fill(self, update=False):
        self.fillSeasons(self.mediaItem, update=update, do_focus=not self.manuallySelectedSeason)
        self.fillSeasonTabs(update=update)

    def fillSeasonTabs(self, update=False):
        # Header season-tab row (script-plex-seasons.xml.tpl, header_middle_add block) - a separate,
        # simpler list from the season row above (id=400): plain title only, no thumb/episode-count,
        # plus a pinned "Show" entry at the front (no dataSource, always 'current') representing this
        # screen itself, matching Episodes' own season-tab row's current-season underline treatment.
        try:
            seasons = self.mediaItem.seasons()
        except:
            seasons = []

        items = [kodigui.ManagedListItem(T(35058, 'Show'))]
        items[0].setBoolProperty('current', True)
        for season in seasons:
            items.append(kodigui.ManagedListItem(season.title or '', data_source=season))

        # 6 seasons or fewer (7 tabs, Show included): the plain-list control (206) - past that: the
        # fixedlist (205), which needs enough items to fill the row before its focusposition/movement
        # scrolling makes sense. See that control's own comment in the template for the fixedlist's
        # short-list quirk this split avoids. The other control is always emptied so its own <visible>
        # keeps it hidden.
        target, other = (self.seasonTabsListControl, self.seasonTabsControl) if len(seasons) <= 6 \
            else (self.seasonTabsControl, self.seasonTabsListControl)

        other.reset()
        if update:
            target.replaceItems(items)
        else:
            target.reset()
            target.addItems(items)

    def fillExtras(self):
        items = []
        idx = 0

        if not self.mediaItem.extras:
            self.extraListControl.reset()
            return False

        for extra in self.mediaItem.extras():
            mli = kodigui.ManagedListItem(
                extra.title or '',
                metadata.EXTRA_MAP.get(extra.extraType.asInt(), ''),
                thumbnailImage=extra.thumb.asTranscodedImageURL(*self.EXTRA_DIM),
                data_source=extra
            )

            if mli:
                mli.setProperty('index', str(idx))
                mli.setProperty('extra.duration', extra.duration and util.simplifiedTimeDisplay(extra.duration.asInt()))
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
        if not self.relatedPaginator.leafCount:
            self.relatedListControl.reset()
            return

        items = self.relatedPaginator.paginate()

        if not items:
            return False

        return True

    def fillRoles(self):
        items = []
        idx = 0
        if not self.mediaItem.roles:
            self.rolesListControl.reset()
            return

        roles = self.mediaItem.combined_roles if util.getUserSetting('show_directors', True) else self.mediaItem.roles

        for role in roles:
            mli = kodigui.ManagedListItem(role.tag, role.role or util.TRANSLATED_ROLES[role.translated_role],
                                          thumbnailImage=role.thumb.asTranscodedImageURL(*self.ROLES_DIM),
                                          data_source=role)
            mli.setProperty('index', str(idx))
            items.append(mli)
            idx += 1

        self.rolesListControl.reset()
        self.rolesListControl.addItems(items)
        return True


class ArtistWindow(ShowWindow):
    xmlFile = 'script-plex-artist.xml'

    SUB_ITEM_LIST_ID = 400
    EXTRA_LIST_ID = None
    ROLES_LIST_ID = None
    RELATED_LIST_ID = 401

    def onFirstInit(self):
        self.subItemListControl = kodigui.ManagedControlList(self, self.SUB_ITEM_LIST_ID, 5)
        self.relatedListControl = kodigui.ManagedControlList(self, self.RELATED_LIST_ID, 5)

        # This fully overrides ShowWindow.onFirstInit() rather than calling super(), so unlike
        # every other ShowWindow-based screen the sidebar's section list is never populated for
        # free via inheritance - needs its own copy of the same build-or-reuse branch.
        if self.sectionList is None:
            self.sectionList = kodigui.ManagedControlList(self, self.SECTION_LIST_ID, 15)
            self.buildSectionList()
        else:
            self.sectionList.newControl(self)
        self.displayServerAndUser()

        self.setup()
        self.initialized = True

        self.setFocusId(self.PLAY_BUTTON_ID)

    def setup(self):
        self.relatedPaginator = RelatedPaginator(self.relatedListControl, leaf_count=int(self.mediaItem.relatedCount),
                                                 parent_window=self)
        self.updateProperties()
        self.fill()
        self.fillRelated()

    def playButtonClicked(self, shuffle=False):
        pl = playlist.LocalPlaylist(self.mediaItem.all(), self.mediaItem.getServer(), self.mediaItem)
        pl.startShuffled = shuffle
        self.processCommand(opener.handleOpen(musicplayer.MusicPlayerWindow, track=pl.current(), playlist=pl))

    def updateProperties(self):
        self.setProperty('summary', self.mediaItem.summary)
        self.setProperty('thumb', self.mediaItem.defaultThumb.asTranscodedImageURL(*self.THUMB_DIMS[self.mediaItem.type]['main.thumb']))
        self.setProperty('related.header', T(32960, 'Similar Artists'))
        self.updateBackgroundFrom(self.mediaItem)

    @busy.dialog()
    def fill(self):
        self.mediaItem.reload(includeRelated=1, includeRelatedCount=20)
        self.setProperty('artist.title', self.mediaItem.title)
        genres = u' / '.join([g.tag for g in util.removeDups(self.mediaItem.genres())][:6])
        self.setProperty('artist.genre', genres)
        items = []
        idx = 0
        for album in sorted(self.mediaItem.albums() + list(self.mediaItem.otherAlbums), key=lambda x: x.year):
            mli = self.createListItem(album)
            if mli:
                mli.setProperty('index', str(idx))
                mli.setProperty('year', album.year)
                mli.setProperty('thumb.fallback', 'script.plex/thumb_fallbacks/music.png')
                items.append(mli)
                idx += 1

        self.subItemListControl.reset()
        self.subItemListControl.addItems(items)
