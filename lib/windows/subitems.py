from __future__ import absolute_import

import json

from kodi_six import xbmc
from kodi_six import xbmcgui
from plexnet import playlist, playqueue, util as pnUtil, plexapp, plexlibrary

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
from .mixins.text_metrics import FONT10_POINT_SIZE, measureTextWidth


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
    # ArtistWindow-only (base stays None/empty so the onClick branches below are simply unreachable
    # for every other ShowWindow-based screen, same idiom as EXTRA_LIST_ID/ROLES_LIST_ID above).
    POPULAR_TRACKS_LIST_ID = None
    ALBUM_TYPE_LIST_IDS = ()
    # Explicit "399 < controlID < 500" -> hub.focus tier override (see onFocus() below) - None means
    # "use the plain controlID-399 arithmetic", true everywhere except ArtistWindow, whose row-list
    # ids aren't allocated in top-to-bottom visual order (see its own override for why).
    HUB_FOCUS_TIERS = None

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
    # Play and Resume are the same action - the show-level pick resumes by itself when it lands on
    # an in-progress episode (getNextShowEp(), windowutils.py) - but a button can't swap its own
    # textures on a condition, so the row carries two mutually-exclusive ones and
    # setPlayButtonState() below decides which is showing. 301 was INFO_BUTTON_ID, a constant left
    # over from the Info button both this screen and Artist dropped; nothing rendered there and its
    # only remaining use was as the lower bound of the button row's own range check in onAction().
    PLAY_BUTTON_ID = 302
    RESUME_BUTTON_ID = 301
    # The two Play/Resume focus-pill overlays (includes/episode_button_label.xml.tpl). Their label
    # text isn't fixed at build time - the episode number's digit count moves it by ~45px - so
    # setPlayButtonState() measures the real string and resizes all three controls of whichever
    # one is live. Seasons-only ids: Artist inherits this class but has its own button row.
    PLAY_LABEL_GROUP_ID = 391
    PLAY_LABEL_PILL_ID = 396
    PLAY_LABEL_TEXT_ID = 397
    RESUME_LABEL_GROUP_ID = 398
    RESUME_LABEL_PILL_ID = 399
    RESUME_LABEL_TEXT_ID = 307
    SHUFFLE_BUTTON_ID = 303
    OPTIONS_BUTTON_ID = 304
    # Click/focus target laid over this screen's own summary textbox (script-plex-seasons.xml.tpl/
    # script-plex-artist.xml.tpl both use id 305 for it) - wired to summaryButtonClicked() below.
    # 305, not the old INFO_BUTTON_ID (301): neither screen has a real rendered control at 301 any
    # more (Seasons dropped its Info button first; Artist's own copy was dropped once this became
    # the only way to reach the same popup) - INFO_BUTTON_ID above is now just OPTIONS_BUTTON_ID's
    # own range-check boundary (see onAction()).
    SUMMARY_BUTTON_ID = 305

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
        # ratingKey the Play button's episode label has already been resolved for, so the one-off
        # allLeaves request in setPlayButtonState() isn't repeated on every property refresh
        self.playLabelResolvedFor = None
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

    def backgroundItem(self):
        return self.mediaItem

    def onFirstInit(self):
        timing = kodigui.StepTiming('Show open')
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
        self._selectActiveSection()
        self.displayServerAndUser()
        timing.mark('controls')

        self.setup(timing)
        self.initialized = True
        # Now that setup() has decided Play or Resume and made the button row visible (the
        # initialized property), focus the one that's showing. setPlayButtonState() can't during
        # setup(): the row is still hidden then, so Kodi refused focus on Resume, then hid Play,
        # which had it - leaving nothing focused, only Back working (live-caught 2026-09-25 on
        # part-watched shows on the AM6B, where the queued focus request beat the property).
        if not self.fromWatchlist and self.getFocusId() in (0, self.PLAY_BUTTON_ID, self.RESUME_BUTTON_ID):
            self.focusPlayButton(wait_visible=True)
        timing.mark('focus')
        self.themeMusicInit(self.mediaItem)
        timing.mark('theme music')
        timing.log()

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

    def setup(self, timing=None):
        if self.isExternal:
            # fixme, multiple? choice?
            self.mediaItem.related_source = "more-from-credits"
        self.mediaItem.reload(includeExtras=1, includeExtrasCount=10, includeOnDeck=1)
        kodigui.markStep(timing, 'reload')
        # Sized by fillRelated() on its worker, as on Pre-play (P4): the count is a server query
        # that held up Show opens by 40-345 ms on the AM6B.
        self.relatedPaginator = None

        self.watchlist_setup(self.mediaItem)
        if self.fromWatchlist:
            self.watchlistItemAvailable(self.mediaItem, shortcut_watchlisted=self.directlyFromWatchlist)
        if not self.directlyFromWatchlist:
            self.checkIsWatchlisted(self.mediaItem)
        else:
            self.setBoolProperty("is_watchlisted", self.is_watchlisted)
        kodigui.markStep(timing, 'watchlist')

        self.updateProperties()
        self.setBoolProperty("initialized", True)
        kodigui.markStep(timing, 'properties')
        # fill() (the season row) runs synchronously, unlike the rest below - it's this screen's primary
        # content (same treatment episodes.py's _setup() gives fillEpisodes()), and onFirstInit() needs it
        # populated before it can focus the season row as the screen's default control. The rest are
        # secondary content, postponed to background threads same as before.
        self.fill(timing=timing)
        self.batch_simple([(self.fillExtras, None, None),
                           (self.fillRelated, None, None),
                           (self.fillRoles, None, None)])


    def onDeckPick(self):
        """The show's own OnDeck episode, or None.

        No viewCount filter: an episode can be on deck *and* already carry a viewCount - a rewatch
        left part-way through is the obvious case (American Dad's own on-deck is 86% through an
        episode watched twice before). Those are exactly the ones Show.all(unwatched=True) drops,
        so queueWithOnDeck() below puts it back rather than this quietly ignoring the server.
        """
        for v in (self.mediaItem.onDeck or []):
            return v
        return None

    def queueWithOnDeck(self, items, pick):
        """`items` with the on-deck episode guaranteed present, inserted in queue order.

        The play queue is built from unwatched episodes only (Show.all(unwatched=True), video.py),
        which silently excludes an on-deck episode the user has seen before - and an episode that
        isn't in the queue can't be started from it (getNextShowEp() has to be able to setCurrent()
        it). Inserting it keeps the rest of the queue as "what's left to watch" while still starting
        where the server says.

        Position is by (season, episode), which is the order PMS's own allLeaves uses for the
        regulars and the order 'interleave' sorts them into as well - only its placement relative to
        specials differs between the two modes, and an on-deck special is rare enough not to chase.
        """
        if pick is None or pick in items:
            return items

        key = (pick.parentIndex.asInt(), pick.index.asInt())
        for i, ep in enumerate(items):
            if (ep.parentIndex.asInt(), ep.index.asInt()) > key:
                return items[:i] + [pick] + items[i:]
        return items + [pick]

    def setPlayButtonState(self):
        """Decide whether the button row shows Play or Resume, and what its label spells out.

        Both come from the show's own OnDeck entry (Show.onDeck, already loaded by setup()'s
        includeOnDeck=1 reload), because that is what getNextShowEp() (windowutils.py) will pick
        when the button is actually pressed - an on-deck entry is authoritative there, and
        playButtonClicked() makes sure it's in the queue to be picked. Deliberately no allLeaves
        request just to label a button.

        When there's no on-deck entry the episode isn't known yet: the label starts as a plain
        "Play" and resolvePlayButtonEpisode() fills it in from a background thread.
        """
        if self.mediaItem.type != 'show':
            return

        pick = self.onDeckPick()
        if pick is None:
            # No on-deck means the server has no opinion, which in practice means a show with
            # nothing left unwatched. The answer is then whatever the blind scan in pickShowEp()
            # lands on, and that needs the actual episode list - one allLeaves request, 65kB on a
            # 26-episode show and 1MB on a 399-episode one. Backgrounded rather than paid in
            # setup(): the button shows a plain "Play" until it resolves, the same way the roles/
            # extras/related rows fill in behind the screen. Only ~15% of a typical library reaches
            # this at all, and the request is skipped entirely once one has already answered for
            # this item.
            self.setProperty('play.episode', '')
            self.setBoolProperty('play.in.progress', False)
            self.setProperty('resume.timeleft', '')
            if self.playLabelResolvedFor != self.mediaItem.ratingKey:
                self.playLabelResolvedFor = self.mediaItem.ratingKey
                self.postpone_simple(self.resolvePlayButtonEpisode)
            self.sizePlayButtonLabel()
            # onFirstInit() focuses Play before any of this is known, so the button it focused may
            # be the one that just went invisible.
            if self.initialized and self.getFocusId() in (self.PLAY_BUTTON_ID, self.RESUME_BUTTON_ID):
                self.focusPlayButton(wait_visible=True)
        else:
            self.applyPlayButtonEpisode(pick)

    def resolvePlayButtonEpisode(self):
        """Fill in the Play button's episode for a show the server has no on-deck entry for.

        Background thread (see setPlayButtonState()). Runs the same pickShowEp() the button itself
        will run, over the same queue playButtonClicked() would build, so the label can't promise an
        episode other than the one that then plays - the blind scan's answer depends on both the
        specials mode and on stray view offsets left behind on an otherwise finished show, neither
        of which can be inferred without the list.
        """
        try:
            items = self.mediaItem.all(unwatched=True)
            if not items:
                return
            specials_mode = util.getSetting('tv_specials_order', 'default')
            items = playlist.reorder_with_specials(items, mode=specials_mode)
            pick = self.pickShowEp(items, specials_mode=specials_mode)
        except:
            util.ERROR()
            return

        if pick is None or self.mediaItem.ratingKey != self.playLabelResolvedFor:
            # the window moved on to another show while this was in flight
            return

        self.applyPlayButtonEpisode(pick)

    def applyPlayButtonEpisode(self, pick):
        """The three properties the button row's Play/Resume pair keys off, for `pick`."""
        # "S5E14": the screen's own two localized fragments concatenated, not the bulleted
        # "S5 - E14" form used elsewhere (library.py, playlist.py) - the Resume label already ends
        # in a bullet before its time-left, and two of them read as a list.
        self.setProperty('play.episode', u'{0}{1}'.format(
            T(32310, 'S').format(pick.parentIndex), T(32311, 'E').format(pick.index)))
        view_offset = pick.viewOffset.asInt()
        duration = pick.duration.asInt()
        in_progress = bool(view_offset and duration)
        self.setBoolProperty('play.in.progress', in_progress)
        # remainingTimeToShortText's own no-space style, matching Episodes'/Pre-play's own Resume
        # buttons ("1h31m left", not "1h 31m left")
        self.setProperty('resume.timeleft', in_progress and T(33615, "{time} left").format(
            time=util.remainingTimeToShortText(duration - view_offset)) or '')
        self.sizePlayButtonLabel()
        # Not during onFirstInit()'s setup(), which focuses once it's done (see there).
        if self.initialized and self.getFocusId() in (self.PLAY_BUTTON_ID, self.RESUME_BUTTON_ID):
            self.focusPlayButton(wait_visible=True)

    def sizePlayButtonLabel(self):
        """Shrink whichever focus-pill overlay is live to fit the label it's actually showing.

        The overlay include can't do this itself - its widths are literals passed at build time
        (see includes/episode_button_label.xml.tpl), and the episode number moves the string by
        ~45px between "S1E1" and "S12E345". Same formula that file documents: label_width is the
        measured text + 4, the pill is label + 62 and the group label + 18.
        """
        episode = self.getProperty('play.episode')
        if self.getProperty('play.in.progress'):
            text = u'{0} {1}'.format(T(32316, 'Resume'), episode)
            timeleft = self.getProperty('resume.timeleft')
            if timeleft:
                text = u'{0} \u2022 {1}'.format(text, timeleft)
            ids = (self.RESUME_LABEL_GROUP_ID, self.RESUME_LABEL_PILL_ID, self.RESUME_LABEL_TEXT_ID)
        else:
            text = u'{0} {1}'.format(T(33020, 'Play'), episode).rstrip()
            ids = (self.PLAY_LABEL_GROUP_ID, self.PLAY_LABEL_PILL_ID, self.PLAY_LABEL_TEXT_ID)

        label_width = int(round(measureTextWidth(text, FONT10_POINT_SIZE))) + 4
        group_id, pill_id, text_id = ids
        try:
            self.getControl(text_id).setWidth(label_width)
            self.getControl(pill_id).setWidth(label_width + 62)
            self.getControl(group_id).setWidth(label_width + 18)
        except (SystemError, RuntimeError):
            # Artist inherits this class and has no controls at these ids; so does any state where
            # the row hasn't rendered yet. The build-time widths are the worst case either way, so
            # a miss here just leaves a slightly roomy pill rather than a broken one.
            util.DEBUG_LOG('ShowWindow: no Play/Resume label controls to resize')

    def updateProperties(self):
        self.setProperty('title', self.mediaItem.title)
        logo = util.clearLogoFrom(self.mediaItem, *self.CLEAR_LOGO_DIM)
        self.setProperty('clear.logo', logo)
        self.setProperty('summary', util.summaryForBox(self.mediaItem.summary))
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
        self.setPlayButtonState()
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
        # The rest of the shared meta row (CommonMixin.META_ROW_PROPERTIES) this screen has no
        # value for.
        self.blankMetaRow('episode.code', 'remainingTime', 'unavailable')

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

    def focusPlayButton(self, extended=False, wait_visible=False):
        if extended:
            self.setFocusId(self.wl_play_button_id)
            return
        # Whichever of the pair is actually rendered - the other one's <visible> is false, and
        # focusing a hidden control drops focus somewhere unrelated. onFirstInit() calls this before
        # setup() has decided, so it lands on Play, and again once setup() has decided.
        if self.getProperty('play.in.progress'):
            button_id = self.RESUME_BUTTON_ID
        else:
            button_id = self.PLAY_BUTTON_ID
        if wait_visible:
            # After play.in.progress changed, the button it names only becomes visible once Kodi
            # next evaluates the pair's <visible>, and setFocusId() is only queued - a focus request
            # that gets there first is refused. Capped, as waitForVisibility() is.
            kodigui.waitForVisibility(button_id, amount=1)
        try:
            if not self.getFocusId() == button_id:
                self.setFocusId(button_id)
        except (SystemError, RuntimeError):
            self.setFocusId(button_id)

    def handleBack(self):
        return self.backToRowStartOrRetract()

    def backResetRows(self):
        # SUB_ITEM_LIST_ID (the season posters) is deliberately not included, unlike the
        # peripheral Roles/Extras/Related rows below it - it's this screen's own primary content,
        # not one of several hub rows sharing space, so Back from it should leave the screen
        # immediately, on request.
        return {self.ROLES_LIST_ID: self.rolesListControl,
                self.EXTRA_LIST_ID: self.extraListControl,
                self.RELATED_LIST_ID: self.relatedListControl}

    def onAction(self, action):
        # Hosted: the host sees the action first (kodigui.BaseWindow.routeActionToHost()).
        if self.routeActionToHost(action):
            return
        try:
            controlID = self.getFocusId()

            if not controlID and self.lastFocusID and not action == xbmcgui.ACTION_MOUSE_MOVE:
                self.setFocusId(self.lastFocusID)

            if controlID == self.SUB_ITEM_LIST_ID and action in (xbmcgui.ACTION_MOVE_LEFT, xbmcgui.ACTION_MOVE_RIGHT):
                self.manuallySelectedSeason = True

            elif action == xbmcgui.ACTION_CONTEXT_MENU:
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
                if controlID == self.SUB_ITEM_LIST_ID and not self.isExternal:
                    self.optionsButtonClicked(from_item=True)
                return

            elif controlID == self.SUB_ITEM_LIST_ID and self.isWatchedAction(action):
                item = self.subItemListControl.getSelectedItem()
                if not item.dataSource:
                    return

                self.toggleWatched(item.dataSource)
                return

            elif action == xbmcgui.ACTION_NAV_BACK:
                # Was `in (NAV_BACK, CONTEXT_MENU)`, but menu already returns from its own branch
                # above and never reached here.
                if self.dismissSidebarPopupOnBack():
                    return
                if self.handleBack():
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
                    self.RESUME_BUTTON_ID <= controlID <= self.OPTIONS_BUTTON_ID):
                self.updateBackgroundFrom(self.mediaItem)

            if controlID == self.RELATED_LIST_ID:
                if self.relatedPaginator and self.relatedPaginator.boundaryHit:
                    self.relatedPaginator.paginate()
                    return

        except:
            util.ERROR()

        kodigui.ControlledWindow.onAction(self, action)

    def onClick(self, controlID):
        # Not live on its host yet, or any more (kodigui.BaseWindow.ignoresInput()).
        # Hosted: the host handles the sidebar's clicks (kodigui.BaseWindow.routeClickToHost()).
        if self.routeClickToHost(controlID):
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
        elif controlID == self.POPULAR_TRACKS_LIST_ID:
            self.popularTrackClicked()
        elif controlID in self.ALBUM_TYPE_LIST_IDS:
            self.albumListClicked(self.albumTypeListControls[controlID])
        elif controlID == self.ROLES_LIST_ID:
            if not self.roleClicked():
                return
        elif controlID == self.SUMMARY_BUTTON_ID:
            self.summaryButtonClicked()
        elif controlID in (self.PLAY_BUTTON_ID, self.RESUME_BUTTON_ID):
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
        # Not live on its host yet, or any more (kodigui.BaseWindow.ignoresInput()).
        if self.ignoresInput():
            return
        self.reselectActiveSection(controlID, self.lastFocusID)
        self.lastFocusID = controlID

        if 399 < controlID < 500:
            # controlID - 399, not - 400: gives the season row its own tier (1) instead of colliding
            # with the button row's own reset-to-'0' below, so group 50's slide animations (see the
            # template) can treat "focus is somewhere in the season row and beyond" as one properly
            # ordered depth scale - 1=season row, 2=roles, 3=extras, 4=related - instead of needing a
            # separate one-off condition just for the season row. HUB_FOCUS_TIERS overrides this
            # arithmetic explicitly for screens (ArtistWindow) whose row-list ids don't already
            # ascend in visual/stacking order the way every other ShowWindow-based screen's do.
            tier = self.HUB_FOCUS_TIERS.get(controlID, controlID - 399) if self.HUB_FOCUS_TIERS \
                else controlID - 399
            self.setProperty('hub.focus', str(tier))
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
        # stack an unwanted extra -300 on top of it. SUMMARY_BUTTON_ID needs the same exclusion: it's
        # a header control (script-plex-seasons.xml.tpl/script-plex-artist.xml.tpl) that happens to
        # live inside group 50 but outside group 300, so without this the elif below misread focusing
        # it as "focus moved into deeper content" and slid the whole header up (live-reported on
        # Artist as "moving navigation up to focus the textbox button causes all the content to move
        # up" - fixed there first, applies identically here now that Seasons shares the same button).
        if (controlID == self.SUB_ITEM_LIST_ID or controlID == self.SUMMARY_BUTTON_ID or
                xbmc.getCondVisibility('ControlGroup(50).HasFocus(0) + ControlGroup(300).HasFocus(0)')):
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
            # this class's own openItem() below (item=, not EpisodesWindow.open() directly): it
            # threads context=self through opener.py's chain-aware dispatch, so when this Seasons
            # screen is itself a chained shell (reached via a hub/library click, not a raw nested
            # open), the season tab continues that same chain (host.swapTo()) instead of opening
            # EpisodesWindow as an unhosted standalone window - a real bug otherwise, live-
            # confirmed: the sidebar's user-menu popup silently does nothing inside an unhosted
            # EpisodesWindow, since the dropdowns are only handled by a live host
            # (kodigui.BaseWindow.routeClickToHost()). entry_section_id/entry_from_watchlist/from_watchlist aren't
            # passed - openItem() below already fills those in from self.entrySectionId/
            # self.entryFromWatchlist/self.fromWatchlist itself; passing them here too would
            # collide as duplicate kwargs once it forwards to opener.open().
            self.openItem(item=mli.dataSource, show=self.mediaItem,
                         parent_list=self.subItemListControl,
                         directly_from_watchlist=self.directlyFromWatchlist,
                         is_watchlisted=self.is_watchlisted)
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
            # this class's own openItem() below (item=) when this Seasons screen is itself a
            # chained shell, so a season poster click continues the same chain instead of opening
            # EpisodesWindow unhosted - see seasonTabClicked()'s identical fix, above, for the full
            # reasoning (sidebar user-menu popup silently breaking otherwise) and for why
            # entry_section_id/entry_from_watchlist/from_watchlist aren't passed here. openItem()
            # doesn't block/return a window instance the way EpisodesWindow.open() does though, so
            # the empty-list cleanup below (which needs w.exitCommand) only applies to the
            # non-chained, still-blocking fallback path.
            if self._liveChainHost() is not None:
                self.openItem(item=mli.dataSource, show=self.mediaItem,
                             parent_list=self.subItemListControl,
                             directly_from_watchlist=self.directlyFromWatchlist,
                             is_watchlisted=self.is_watchlisted)
                # The open is only queued, and runs once this returns. Back rebuilds this screen,
                # and its setup() reloads the show, so the refresh below would only hold the open
                # up (137-244 ms on the AM6B).
                return
            else:
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
            if w is not None:
                self.closeWithCommand(w.exitCommand)
                ref = util.windowRef(w)
                del w
                util.collectIfAlive(ref)
            return

        if update:
            if mli and mli.dataSource:
                mli.setProperty('unwatched.count', not mli.dataSource.isWatched and str(mli.dataSource.unViewedLeafCount) or '')
            self.mediaItem.reload(includeRelated=1, includeRelatedCount=10, includeExtras=1, includeExtrasCount=10)
            self.updateProperties()

        if w is not None:
            # Only set on the non-chained, still-blocking EpisodesWindow.open()/AlbumWindow.open()
            # fallback path (see this method's own comment above) - the chained openItem() path
            # already ran its own processCommand() internally and left w as None, nothing further
            # to bubble here.
            ref = util.windowRef(w)
            try:
                self.processCommand(w.exitCommand)
            finally:
                del w
                util.collectIfAlive(ref)

    def summaryButtonClicked(self):
        # Popup, not opener.handleOpen(info.InfoWindow, ...) any more - same change episodes.py's/
        # preplay.py's own Info buttons already got (infoButtonClicked() there): everything
        # InfoWindow showed here duplicated what's already visible on this screen itself except the
        # title/summary, so a dialog like Settings'/More's own popups is enough (no cameFrom
        # bookkeeping needed either, that existed only for InfoWindow's own close-and-return flow).
        # Shared by Seasons (this class directly) and Artist (ArtistWindow below) - both just need
        # their own title/summary, nothing type-specific.
        info.showSummary(self.mediaItem.title, self.mediaItem.summary)

    def playButtonClicked(self, shuffle=False):
        if self.playBtnClicked:
            return

        items = self.mediaItem.all(unwatched=True)
        # Read once and handed to both reorder_with_specials() and getNextShowEp() below: the two
        # have to agree about specials or the queue ends up ordered by air date while the starting
        # episode is still chosen as though they were all bunched at the front.
        specials_mode = util.getSetting('tv_specials_order', 'default')
        on_deck_pick = None
        if not shuffle and self.mediaItem.type == 'show':
            items = playlist.reorder_with_specials(items, mode=specials_mode)
            # Before the playlist is built, not after: an episode that isn't in it can't be started
            # from it, and the on-deck one is missing whenever the user has seen it before.
            on_deck_pick = self.onDeckPick()
            items = self.queueWithOnDeck(items, on_deck_pick)
        pl = playlist.LocalPlaylist(items, self.mediaItem.getServer())
        resume = False
        if not shuffle and self.mediaItem.type == 'show':
            # on_deck: setup() already reloads this show with includeOnDeck=1 (originally for the
            # season posters' own progress bars, since removed - it's this button and the
            # rewatch-detection in fillSeasons() that need it now), so handing the list to
            # getNextShowEp() costs nothing and lets the server's own whole-show "continue watching"
            # pick choose the starting episode instead of the local scan. This screen is about the
            # whole show, which is exactly the question that heuristic answers, and its answer is
            # taken as authoritative when there is one - see that method's own docstring, and
            # EpisodesWindow._defaultEpisode() (episodes.py) for why the season-level screen
            # deliberately does the opposite.
            resume = self.getNextShowEp(pl, items, self.mediaItem.title,
                                        on_deck=[on_deck_pick] if on_deck_pick else None,
                                        specials_mode=specials_mode)
            if resume is None:
                return

        self.playBtnClicked = True
        pl.shuffle(shuffle, first=True)
        videoplayer.play(play_queue=pl, resume=resume, bgm=self.useBGM, context=self)

    def shuffleButtonClicked(self):
        self.playButtonClicked(shuffle=True)

    def optionsButtonClicked(self, from_item=None):
        options = []

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

        # 518, not the old 880: stale after this session's Seasons button row rework
        # (script-plex-seasons.xml.tpl) - same class of bug as episodes.py's own copy of this static
        # fallback (from_item=False, opened via the More button itself, so there's no per-focus
        # position to compute from the way the from_item branch below does). Old row was posx=22,
        # 152-wide boxes, -20 itemgap (132px/button); new is posx=63, 70-wide, 0 itemgap (70px/
        # button) - scaled the old value's offset from its own row start by that same 70/132 ratio
        # (858 old offset * 70/132 = ~455) rather than recomputing a fixed button index, since the
        # watchlist button cluster ahead of More (wl_dynamic_buttons.xml.tpl/
        # wl_add_remove_buttons.xml.tpl) can show a different number of buttons depending on
        # availability/watchlist state, same ambiguity the old value already carried. Y (618) left
        # alone - same reasoning as episodes.py's own fix attempt: the button row's own absolute
        # glyph position was deliberately preserved through the resize (posy 0 -> vscale(25), see
        # that control's own comment), so it shouldn't have moved vertically either - unconfirmed
        # live though.
        pos = (518, 618)
        if from_item:
            viewPos = self.subItemListControl.getViewPosition()
            optsLen = len(list(filter(None, options)))
            # dropDown handles any overlap with the right window boundary so we don't need to care here
            pos = ((((viewPos + 1) * 218) - 100), 460 if optsLen < 7 else 460 - 66 * (optsLen - 6))

        choice = dropdown.showDropdown(options, pos, close_direction='left')
        if not choice:
            return

        if choice['key'] == 'mark_watched':
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
                self.focusPlayButton(wait_visible=True)
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
    def fill(self, update=False, timing=None):
        # One fetch for both rows: each used to call seasons() itself, a server request apiece.
        try:
            seasons = self.mediaItem.seasons()
        except:
            raise util.NoDataException
        kodigui.markStep(timing, 'fetch seasons')
        self.fillSeasons(self.mediaItem, update=update, do_focus=not self.manuallySelectedSeason, seasons=seasons)
        kodigui.markStep(timing, 'seasons')
        self.fillSeasonTabs(update=update, seasons=seasons)
        kodigui.markStep(timing, 'season tabs')

    def fillSeasonTabs(self, update=False, seasons=None):
        # Header season-tab row (script-plex-seasons.xml.tpl, header_middle_add block) - a separate,
        # simpler list from the season row above (id=400): plain title only, no thumb/episode-count,
        # plus a pinned "Show" entry at the front (no dataSource, always 'current') representing this
        # screen itself, matching Episodes' own season-tab row's current-season underline treatment.
        if seasons is None:
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
        if self.tasks is None:
            # closed before this task ran
            return False
        if self.relatedPaginator is None:
            try:
                count = int(self.mediaItem.relatedCount)
            except ValueError:
                count = 0
            self.relatedPaginator = RelatedPaginator(self.relatedListControl, leaf_count=count,
                                                     parent_window=self)
        paginator = self.relatedPaginator
        if not paginator.leafCount:
            self.relatedListControl.reset()
            return

        items = paginator.paginate()

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

    # Square, not the base class's 268x402 poster dims: this screen's Similar Artists row draws
    # square 240x240 tiles (script-plex-artist.xml.tpl's list 401, same recipe as the album rows'
    # includes/artist_album_row.xml.tpl), so a 2:3 poster fetch was pulling art taller than the
    # tile could ever use. 240 matches the drawn size exactly.
    RELATED_DIM = util.scaleResolution(240, 240)

    SUB_ITEM_LIST_ID = 400
    EXTRA_LIST_ID = None
    ROLES_LIST_ID = None
    RELATED_LIST_ID = 401
    POPULAR_TRACKS_LIST_ID = 402

    # One row per otherAlbums hub (Artist.OTHER_ALBUM_HUBS, plexnet/audio.py), each its own list
    # control (on request: separate lists per album type, not everything dumped into one row sorted
    # by year) - (mediaItem attr, control id, header Window.Property name, string id, default text).
    # Control ids/order match script-plex-artist.xml.tpl's grouplist 600 album-row includes.
    ALBUM_TYPE_ROWS = (
        ('liveAlbums', 404, 'live_albums.header', 35066, 'Live Albums'),
        ('compilationAlbums', 405, 'compilation_albums.header', 35067, 'Compilations'),
        ('singleAlbums', 406, 'single_albums.header', 35068, 'Singles & EPs'),
        ('soundtrackAlbums', 407, 'soundtrack_albums.header', 35069, 'Soundtracks'),
        ('demoAlbums', 408, 'demo_albums.header', 35070, 'Demos'),
        ('remixAlbums', 409, 'remix_albums.header', 35071, 'Remixes'),
    )
    ALBUM_TYPE_LIST_IDS = tuple(cid for _attr, cid, _hp, _sid, _default in ALBUM_TYPE_ROWS)

    # Explicit hub.focus tier per row-list id, in visual/grouplist-stacking order - Popular Tracks
    # (402) is drawn first despite Albums (400) having the lower numeric id (SUB_ITEM_LIST_ID can't
    # move off 400, the shared base class's own convention), so the plain controlID-399 arithmetic
    # onFocus() normally uses would give tiers wildly out of visual order (402->3, 400->1, 404->5...).
    # script-plex-artist.xml.tpl's own per-tier reveal animations (group 50) key off these same
    # numbers 1-9 paired with each row's own group id (501-508, Related's existing 500) - the two
    # must be kept in sync by hand.
    HUB_FOCUS_TIERS = {
        402: 1,  # Popular Tracks (group id 501)
        400: 2,  # Albums (group id 502)
        404: 3,  # Live Albums (group id 503)
        405: 4,  # Compilations (group id 504)
        406: 5,  # Singles & EPs (group id 505)
        407: 6,  # Soundtracks (group id 506)
        408: 7,  # Demos (group id 507)
        409: 8,  # Remixes (group id 508)
        401: 9,  # Related Artists (group id 500)
    }

    def onFirstInit(self):
        self.subItemListControl = kodigui.ManagedControlList(self, self.SUB_ITEM_LIST_ID, 5)
        self.relatedListControl = kodigui.ManagedControlList(self, self.RELATED_LIST_ID, 5)
        self.popularTracksListControl = kodigui.ManagedControlList(self, self.POPULAR_TRACKS_LIST_ID, 5)
        self.albumTypeListControls = {}
        for _attr, cid, _header_prop, _sid, _default in self.ALBUM_TYPE_ROWS:
            self.albumTypeListControls[cid] = kodigui.ManagedControlList(self, cid, 5)

        # This fully overrides ShowWindow.onFirstInit() rather than calling super(), so unlike
        # every other ShowWindow-based screen the sidebar's section list is never populated for
        # free via inheritance - needs its own copy of the same build-or-reuse branch.
        if self.sectionList is None:
            self.sectionList = kodigui.ManagedControlList(self, self.SECTION_LIST_ID, 15)
            self.buildSectionList()
        else:
            self.sectionList.newControl(self)
        self._selectActiveSection()
        self.displayServerAndUser()

        self.setup()
        self.initialized = True

        self.setFocusId(self.PLAY_BUTTON_ID)

    def backResetRows(self):
        # Own list, not ShowWindow's: this screen has no Roles/Extras controls (ShowWindow's version
        # raised AttributeError here, so Back never reset a row on Artist), and Albums (400) is one
        # row among several here, not the screen's main selection the way Seasons' 400 is.
        rows = {self.SUB_ITEM_LIST_ID: self.subItemListControl,
                self.RELATED_LIST_ID: self.relatedListControl,
                self.POPULAR_TRACKS_LIST_ID: self.popularTracksListControl}
        rows.update(self.albumTypeListControls)
        return rows

    def onFocus(self, controlID):
        # Not live on its host yet, or any more (kodigui.BaseWindow.ignoresInput()).
        if self.ignoresInput():
            return
        # Full override, not ShowWindow.onFocus()'s shared version - that one exempts
        # SUB_ITEM_LIST_ID (400) from on.extras on the theory it's "the season row", which already
        # gets its own dedicated tier-1 slide separate from the general -300 (true for Seasons, whose
        # season row really is first). On Artist, 400 is Albums, not the first row (Popular Tracks,
        # 402, is) - inheriting that exemption cleared on.extras right at the Popular Tracks->Albums
        # boundary while the animation's own tier2 condition was simultaneously switching on, so the
        # -300 retracting and the new tier's -500 extending fought each other for one frame (live-
        # reported as "content moves up before dropping back down slightly"). This screen's reveal
        # animations are all uniform stacked tiers (script-plex-artist.xml.tpl's group 50), the same
        # scheme script-plex-pre_play.xml.tpl uses - so this is a straight port of PrePlayWindow's own
        # onFocus() (preplay.py), not ShowWindow's: only SUMMARY_BUTTON_ID is exempted, and hub.focus
        # is never reset back to 0 (same as Pre-play - other controls key off it staying "seen at
        # least once", not off returning to exactly 0).
        self.reselectActiveSection(controlID, self.lastFocusID)
        self.lastFocusID = controlID

        if 399 < controlID < 500:
            tier = self.HUB_FOCUS_TIERS.get(controlID, controlID - 399)
            self.setProperty('hub.focus', str(tier))
            self.setProperty('row.focused', '1')
        else:
            self.setProperty('row.focused', '')

        if (controlID == self.SUMMARY_BUTTON_ID or
                xbmc.getCondVisibility('ControlGroup(50).HasFocus(0) + ControlGroup(300).HasFocus(0)')):
            self.setProperty('on.extras', '')
        elif xbmc.getCondVisibility('ControlGroup(50).HasFocus(0) + !ControlGroup(300).HasFocus(0)'):
            self.setProperty('on.extras', '1')

    def setup(self):
        self.relatedPaginator = RelatedPaginator(self.relatedListControl, leaf_count=int(self.mediaItem.relatedCount),
                                                 parent_window=self)
        self.updateProperties()
        self.fill()
        self.fillRelated()
        self.fillPopularTracks()
        self.fillAlbumTypeRows()

    def playButtonClicked(self, shuffle=False):
        # The artist itself - a server play queue of their material, the way a Plex client plays an
        # artist. Was a LocalPlaylist of self.mediaItem.all() pushed straight into Kodi's playlist,
        # which the server never heard about. Artist is the one type plexnet insists on a remote
        # queue for (PlayQueueFactory.itemRequiresRemotePlayQueue).
        pq = playqueue.createPlayQueueForItem(self.mediaItem, options={'shuffle': shuffle})
        if not pq:
            util.DEBUG_LOG('ArtistWindow: no play queue for {}', self.mediaItem)
            return
        self.processCommand(opener.open(pq))

    def popularTrackClicked(self):
        mli = self.popularTracksListControl.getSelectedItem()
        if not mli:
            return
        # Queue the popular-tracks *query*, not the handful of rows on screen. <PopularLeaves>
        # carries its own key (Artist._setData, plexnet/audio.py) - a real listable
        # /library/sections/<id>/all?artist.id=...&sort=ratingCount:desc&type=10 - and it returns
        # considerably more than the row shows (5 visible, 24 behind the key for The Beautiful
        # South, checked against the live server). That larger popularity-ranked list is what a
        # real client plays, and Next/Previous still walks it in rank order rather than dropping
        # into album-order playback. Without the key we fall back to the track's album, same as
        # any other track click.
        self.processCommand(opener.trackClicked(mli.dataSource,
                                                container_path=self.mediaItem.popularTracksKey))

    def albumListClicked(self, listControl):
        # The 'artist' branch of subItemListClicked() above, generalized to any of the 6 otherAlbums
        # rows - those never need that method's 'show' branch (seasons) or its empty-list
        # close-the-screen cleanup (this is a secondary row, not the screen's own primary content).
        mli = listControl.getSelectedItem()
        if not mli:
            return
        tracks.AlbumWindow.open(album=mli.dataSource, parent_list=listControl,
                                entry_section_id=self.entrySectionId)
        if not mli.dataSource.exists():
            listControl.removeItem(mli.pos())

    def updateProperties(self):
        self.setProperty('summary', util.summaryForBox(self.mediaItem.summary))
        self.setProperty('related.header', T(32960, 'Similar Artists'))
        self.setProperty('popular_tracks.header', T(35065, 'Popular Tracks'))
        # 'Albums' (35072), not the album-type rows' own headers below - the primary/studio row
        # (Artist.albums(), the /children listing) never had a header of its own before these other
        # rows existed alongside it, sorted-and-merged into a single unlabeled row.
        self.setProperty('albums.header', T(35072, 'Albums'))
        for _attr, _cid, header_prop, string_id, default in self.ALBUM_TYPE_ROWS:
            self.setProperty(header_prop, T(string_id, default))
        self.updateBackgroundFrom(self.mediaItem)

    @busy.dialog()
    def fill(self):
        self.mediaItem.reload(includeRelated=1, includeRelatedCount=20, includePopularLeaves=1)
        self.setProperty('artist.title', self.mediaItem.title)
        genres = u' / '.join([g.tag for g in util.removeDups(self.mediaItem.genres())][:6])
        self.setProperty('artist.genre', genres)
        # Primary/studio row only now - the otherAlbums hub types (Live/Compilation/Singles &
        # EPs/Soundtracks/Demos/Remixes) get their own separate rows below (fillAlbumTypeRows()),
        # rather than being merged in here alongside these (on request).
        #
        # Server order, no local sort: PMS has a per-library preference for exactly this decision -
        # albumSort, "How to sort the albums for artists", offering Newest first / Oldest first / By
        # name - and /children already comes back honouring it (verified against a live server:
        # newest-first at the default setting, and the endpoint re-orders when the preference or an
        # explicit sort= says otherwise). Sorting here by year overrode that choice unconditionally,
        # and reversing it would only have overridden it in the other direction. Same reasoning
        # fillPopularTracks() below already documents for its own server-ranked row.
        items = []
        idx = 0
        for album in self.mediaItem.albums():
            mli = self.createListItem(album)
            if mli:
                mli.setProperty('index', str(idx))
                mli.setProperty('year', album.year)
                mli.setProperty('thumb.fallback', 'script.plex/thumb_fallbacks/music.png')
                items.append(mli)
                idx += 1

        self.subItemListControl.reset()
        self.subItemListControl.addItems(items)

    def fillAlbumTypeRows(self):
        for attr, cid, _header_prop, _string_id, _default in self.ALBUM_TYPE_ROWS:
            listControl = self.albumTypeListControls[cid]
            items = []
            idx = 0
            # Server order here too - and these hubs arrive embedded in the artist's own metadata
            # (Artist._setData(), plexnet/audio.py), so there's no sort parameter to send even if we
            # wanted one: whatever order PMS puts them in is the only order available. See fill()
            # above for the albumSort preference this defers to.
            for album in getattr(self.mediaItem, attr):
                mli = self.createListItem(album)
                if mli:
                    mli.setProperty('index', str(idx))
                    mli.setProperty('year', album.year)
                    mli.setProperty('thumb.fallback', 'script.plex/thumb_fallbacks/music.png')
                    items.append(mli)
                    idx += 1

            listControl.reset()
            listControl.addItems(items)

    def fillPopularTracks(self):
        items = []
        idx = 0
        # A real track row (title over its album, duration to the right - loosely
        # script-plex-album.xml.tpl's own recipe, minus the number column that one carries), not
        # another square-art carousel like Albums/Related above it - this is a list of tracks you
        # click to play (popularTrackClicked() below), not another set of things you open (on
        # request, after the first pass wrongly copied the card-carousel treatment).
        # PopularLeaves entries arrive already sorted by ratingCount (server-side, see the request's
        # own &sort= in fill()'s reload()) - no local re-sort, unlike the album loop above.
        for track in self.mediaItem.popularTracks:
            mli = kodigui.ManagedListItem(track.title or '', data_source=track)
            mli.setProperty('index', str(idx))
            mli.setProperty('track.ID', track.ratingKey)
            # parentTitle = the track's own album (playlist.py's own track rows use the same
            # field for their album line) - the row's second, dimmed caption line.
            mli.setProperty('track.album', track.parentTitle or '')
            mli.setProperty('track.duration', util.simplifiedTimeDisplay(track.duration.asInt()))
            items.append(mli)
            idx += 1

        self.popularTracksListControl.reset()
        self.popularTracksListControl.addItems(items)
