from __future__ import absolute_import

import math
import threading
import time
import traceback
import uuid

from kodi_six import xbmc
from kodi_six import xbmcgui

from lib import colors
from lib import kodijsonrpc
from lib import player
from lib import util
from lib.util import T
from plexnet import plexapp
from plexnet.serverdecision import DecisionFailure
from . import busy
from . import kodigui
from . import opener
from . import pagination
from . import windowutils
from .mixins.spoilers import SpoilersMixin

PASSOUT_PROTECTION_DURATION_SECONDS = 7200
PASSOUT_LAST_VIDEO_DURATION_MILLIS = 1200000


class RelatedPaginator(pagination.BaseRelatedPaginator):
    def readyForPaging(self):
        return self.parentWindow.postPlayInitialized

    def getData(self, offset, amount):
        return (self.parentWindow.prev or self.parentWindow.next).getRelated(offset=offset, limit=amount)

    def prepareListItem(self, data, mli):
        super(RelatedPaginator, self).prepareListItem(data, mli)
        # the poster grid's second caption line: the year, plus the runtime for movies in
        # pre-play/episodes' short form, bullet-separated
        parts = [data.get('year', '')]
        if data.type == 'movie' and data.duration:
            parts.append(util.durationToShortText(data.duration.asInt(), noSpaces=True))
        mli.setProperty('subtitle', u' \u2022 '.join(part for part in parts if part))


class OnDeckPaginator(pagination.MCLPaginator):
    initialPageSize = 8

    def readyForPaging(self):
        return self.parentWindow.postPlayInitialized

    thumbFallback = lambda self, rel: 'script.plex/thumb_fallbacks/{0}.png'.format(
                    rel.type in ('show', 'season', 'episode') and 'show' or 'movie')

    def prepareListItem(self, data, mli):
        mli.setProperty('progress', util.getProgressImage(mli.dataSource))
        mli.setProperty('unwatched', not mli.dataSource.isWatched and '1' or '')
        mli.setProperty('watched', mli.dataSource.isFullyWatched and '1' or '')

        # episodes get both caption lines in createListItem(), which knows whether the title is hidden
        if data.type != 'episode':
            mli.setLabel2(data.year)

    def createListItem(self, ondeck):
        title = ondeck.grandparentTitle or ondeck.title
        label2 = ''
        if ondeck.type == 'episode':
            hide_spoilers = self.parentWindow.hideSpoilers(ondeck, use_cache=False)
            thumb_opts = self.parentWindow.getThumbnailOpts(ondeck, hide_spoilers=hide_spoilers)
            thumb = ondeck.thumb.asTranscodedImageURL(*self.parentWindow.ONDECK_DIM, **thumb_opts)
            # second line: show, S/E code, runtime (pre-play/episodes' short form), bullet-separated
            parts = [self.parentWindow.episodeCode(ondeck),
                     ondeck.duration and util.durationToShortText(ondeck.duration.asInt(), noSpaces=True)]
            # when spoiler settings hide the episode title, the show's name stands in for it on the
            # first line instead, so it isn't repeated on the second
            if not (hide_spoilers and self.parentWindow.noTitles):
                title = ondeck.title
                parts.insert(0, ondeck.grandparentTitle)
            label2 = u' \u2022 '.join(part for part in parts if part)
        else:
            thumb = ondeck.defaultArt.asTranscodedImageURL(*self.parentWindow.ONDECK_DIM)

        mli = kodigui.ManagedListItem(title or '', label2, thumbnailImage=thumb, data_source=ondeck)
        if mli:
            return mli

    def getData(self, offset, amount):
        data = (self.parentWindow.prev or self.parentWindow.next).sectionOnDeck(offset=offset, limit=amount)
        skipRKs = []
        if self.parentWindow.next:
            skipRKs.append(self.parentWindow.next.ratingKey)
        if self.parentWindow.prev:
            skipRKs.append(self.parentWindow.prev.ratingKey)
        if skipRKs:
            return list(filter(lambda x: x.ratingKey not in skipRKs, data))
        return data


class VideoPlayerWindow(kodigui.ControlledWindow, windowutils.UtilMixin, SpoilersMixin):
    xmlFile = 'script-plex-video_player.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    NEXT_DIM = util.scaleResolution(619, 348)
    PREV_DIM = util.scaleResolution(619, 348)
    ONDECK_DIM = util.scaleResolution(619, 348)
    RELATED_DIM = util.scaleResolution(268, 402)

    PREV_BUTTON_ID = 101
    NEXT_BUTTON_ID = 102

    ONDECK_LIST_ID = 400
    RELATED_LIST_ID = 401

    PLAYER_STATUS_BUTTON_ID = 204

    def __init__(self, *args, **kwargs):
        kodigui.ControlledWindow.__init__(self, *args, **kwargs)
        windowutils.UtilMixin.__init__(self)
        SpoilersMixin.__init__(self, *args, **kwargs)
        self.playQueue = kwargs.get('play_queue')
        self.video = kwargs.get('video')
        self.resume = bool(kwargs.get('resume'))

        if util.platformFlavor == "CoreELEC":
            self.defer_init = True

        self.postPlayMode = False
        self.prev = None
        self.playlist = None
        self.handler = None
        self.next = None
        self.videos = None
        self.trailer = None
        self.aborted = True
        self.timeout = None
        self.passoutProtection = 0
        self.postPlayInitialized = False
        self.relatedPaginator = None
        self.onDeckPaginator = None
        self.lastFocusID = None
        self.playBackStarted = False
        self.handleBGM = kwargs.get('bgm')
        self.lastItem = None
        self.earlyAbortRequested = False
        self.sessionID = None
        self.playbackFailed = False
        self.openAfterClose = None

    def doClose(self, force=False):
        util.DEBUG_LOG('VideoPlayerWindow: Closing')
        self.timeout = None
        self.relatedPaginator = None
        self.onDeckPaginator = None
        self.lastItem = None
        if self.earlyAbortRequested:
            player.PLAYER._ignorePlaybackFailure = True
            if player.PLAYER.isPlayingVideo():
                player.PLAYER.close()
                if player.PLAYER.handler:
                    player.PLAYER.handler.stoppedManually = True
                player.PLAYER.stop()

        kodigui.ControlledWindow.doClose(self)

        if player.PLAYER.handler:
            player.PLAYER.handler.sessionEnded()

    def onFirstInit(self):
        player.PLAYER.on('session.ended', self.sessionEnded)
        player.PLAYER.on('videowindow.closed', self.videoWindowClosed)
        player.PLAYER.on('av.started', self.playerPlaybackStarted)
        player.PLAYER.on('starting.video', self.onVideoStarting)
        player.PLAYER.on('started.video', self.onVideoStarted)
        player.PLAYER.on('changed.video', self.onVideoChanged)
        player.PLAYER.on('post.play', self.postPlay)
        player.PLAYER.on('change.background', self.changeBackground)
        player.PLAYER.on('playback.failed', self.setPlaybackFailed)

        self.sessionID = str(uuid.uuid4())

        self.onDeckListControl = kodigui.ManagedControlList(self, self.ONDECK_LIST_ID, 5)
        self.relatedListControl = kodigui.ManagedControlList(self, self.RELATED_LIST_ID, 5)

        util.DEBUG_LOG('VideoPlayerWindow: Starting session (ID: {0})', self.sessionID)
        self.resetPassoutProtection()
        self.play(resume=self.resume)

    def onVideoStarting(self, *args, **kwargs):
        util.setGlobalProperty('ignore_spinner', '1')

    def onVideoStarted(self, *args, **kwargs):
        util.setGlobalProperty('ignore_spinner', '')

    def onVideoChanged(self, *args, **kwargs):
        #util.setGlobalProperty('ignore_spinner', '')
        pass

    def onReInit(self):
        util.DEBUG_LOG('VideoPlayerWindow: Reinitializing')
        if not self.earlyAbortRequested:
            self.setBackground()

    def onAction(self, action):
        try:
            if self.postPlayMode:
                controlID = self.getFocusId()

                self.cancelTimer()
                self.resetPassoutProtection()
                # user input means someone's actually watching
                util.MONITOR.tv_standby = False
                # Back always closes: the header has no buttons to step back to (Home/Search are
                # gone, and the audio widget is hidden - play() stopped any audio)
                if action in(xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_PREVIOUS_MENU):
                    self.doClose()
                    return

                if action in (xbmcgui.ACTION_NEXT_ITEM, xbmcgui.ACTION_PLAYER_PLAY):
                    self.playVideo()
                elif action == xbmcgui.ACTION_PREV_ITEM:
                    self.playVideo(prev=True)
                elif action == xbmcgui.ACTION_STOP:
                    self.doClose()

                if controlID == self.RELATED_LIST_ID:
                    if self.relatedPaginator.boundaryHit:
                        self.relatedPaginator.paginate()
                        return

                elif controlID == self.ONDECK_LIST_ID:
                    if self.onDeckPaginator.boundaryHit:
                        self.onDeckPaginator.paginate()
                        return

                    mli = self.onDeckListControl.getSelectedItem()
                    if not mli or mli.getProperty("is.boundary"):
                        return

                    lastItem = self.lastItem

                    if action in (xbmcgui.ACTION_MOVE_RIGHT, xbmcgui.ACTION_MOVE_LEFT) and lastItem:
                        items = self.onDeckPaginator.wrap(mli, lastItem, action)
                        xbmc.sleep(100)
                        if items:
                            # wrapped with new data
                            return True

                    if mli != self.lastItem and not mli.getProperty("is.boundary"):
                        self.lastItem = mli
            else:
                if action in(xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_PREVIOUS_MENU, xbmcgui.ACTION_STOP):
                    util.DEBUG_LOG('VideoPlayerWindow: Abort requested, setting flag')
                    self.earlyAbortRequested = True
        except:
            util.ERROR()

        kodigui.ControlledWindow.onAction(self, action)

    def playerPlaybackStarted(self, *args, **kwargs):
        self.playBackStarted = True

        if self.earlyAbortRequested:
            util.DEBUG_LOG('VideoPlayerWindow: Abort flag set, closing')
            self.doClose()

    def setPlaybackFailed(self, *args, **kwargs):
        self.playbackFailed = True

    def onClick(self, controlID):
        if not self.postPlayMode:
            return

        # stop the countdown before anything a click opens: onAction(), which would otherwise stop
        # it, only runs after this returns, and the timer's SendClick() lands on the top window
        self.cancelTimer()

        if controlID == self.ONDECK_LIST_ID:
            self.openItem(self.onDeckListControl)
        elif controlID == self.RELATED_LIST_ID:
            self.openItem(self.relatedListControl)
        elif controlID == self.PREV_BUTTON_ID:
            self.playVideo(prev=True)
        elif controlID == self.NEXT_BUTTON_ID:
            self.playVideo()
        elif controlID == self.PLAYER_STATUS_BUTTON_ID:
            self.showAudioPlayer()

    def onFocus(self, controlID):
        if not self.postPlayMode:
            return

        self.lastFocusID = controlID

        if 399 < controlID < 500:
            self.setProperty('hub.focus', str(controlID - 400))
        else:
            self.setProperty('hub.focus', '')

        if xbmc.getCondVisibility('Control.HasFocus(101) | Control.HasFocus(102) | ControlGroup(200).HasFocus(0)'):
            self.setProperty('on.extras', '')
        elif xbmc.getCondVisibility('ControlGroup(60).HasFocus(0)'):
            # only On Deck + Related need the screen to scroll; a lone Related row (movies) fits
            # below the top band as it is
            self.setProperty('on.extras', xbmc.getCondVisibility('Control.IsVisible(500)') and '1' or '')

    def setBackground(self):
        video = self.video if self.video else self.playQueue.current()
        self.windowSetBackground(video.defaultArt.asTranscodedImageURL(1920, 1080, opacity=60,
                                                                       background=colors.noAlpha.Background))

    def changeBackground(self, url, **kwargs):
        self.windowSetBackground(url)

    def sessionEnded(self, session_id=None, **kwargs):
        if session_id != self.sessionID:
            util.DEBUG_LOG('VideoPlayerWindow: Ignoring session end (ID: {0} - SessionID: {1})', self.sessionID, session_id)
            return

        util.DEBUG_LOG('VideoPlayerWindow: Session ended - closing (ID: {0})', self.sessionID)
        self.doClose()

    def videoWindowClosed(self, session_id=None, video=None, **kwargs):
        if session_id != self.sessionID:
            return

        video.clearCache()

    def play(self, resume=False, handler=None):
        util.DEBUG_LOG("VideoPlayerWindow: play() called")
        self.hidePostPlay()

        player.PLAYER.dontRequeueBGM = True
        player.PLAYER.startingVideoPlayback = True

        def anyOtherVPlayer():
            return any(list(filter(lambda x: x['playerid'] > 0, kodijsonrpc.rpc.Player.GetActivePlayers())))

        if player.PLAYER.isPlayingVideo():
            activePlayers = anyOtherVPlayer()
            if activePlayers:
                util.DEBUG_LOG("Stopping other active players: {}", activePlayers)
                xbmc.executebuiltin('PlayerControl(Stop)')
                ct = 0
                while player.PLAYER.isPlayingVideo() or anyOtherVPlayer():
                    if ct >= 50:
                        util.showNotification("Other player active", header=util.T(32448, 'Playback Failed!'))
                        break
                    util.MONITOR.waitForAbort(0.1)
                    ct += 1

                if ct >= 50:
                    self.doClose()
                    return
                util.MONITOR.waitForAbort(0.5)

        # wait for BGM to end if it's playing or queued
        if self.handleBGM or player.PLAYER.isPlayingAudio():
            util.DEBUG_LOG("Checking BGM")
            if player.PLAYER.BGMTask:
                player.PLAYER.BGMTask.cancel()
            ct = 0
            while not player.PLAYER.bgmPlaying and player.PLAYER.bgmStarting and ct < 20:
                util.DEBUG_LOG("Waiting for BGM to start as it has been queued")
                util.MONITOR.waitForAbort(0.1)
                ct += 1

            if player.PLAYER.bgmPlaying:
                util.DEBUG_LOG("Stopping BGM before starting playback")
                player.PLAYER.stopAndWait()

            if player.PLAYER.isPlayingAudio():
                player.PLAYER.stopAndWait()

            ct = 0
            while (player.PLAYER.bgmPlaying or player.PLAYER.isPlayingAudio()) and ct < 20:
                util.MONITOR.waitForAbort(0.1)
                ct += 1
            util.DEBUG_LOG("BGM check done")

        self.setBackground()

        self.sessionID = self.sessionID or str(uuid.uuid4())

        try:
            if self.playQueue:
                player.PLAYER.playVideoPlaylist(self.playQueue, resume=resume or self.resume, session_id=self.sessionID,
                                                handler=handler)
            elif self.video:
                player.PLAYER.playVideo(self.video, resume=resume or self.resume, force_update=True, session_id=self.sessionID,
                                        handler=handler)
        except DecisionFailure:
            util.LOG("Can't play this media.")
            self.doClose()

        except Exception as e:
            util.LOG("Playback failed: {}", traceback.format_exc())
            self.doClose()
        finally:
            player.PLAYER.startingVideoPlayback = False

        util.DEBUG_LOG("VideoPlayerWindow: Playback initialized; returning from play()")


    def openItem(self, control=None, item=None):
        if not item:
            mli = control.getSelectedItem()
            if not mli:
                return
            item = mli.dataSource

        # not opened on top of post-play: it closes, and play() has the screen that started playback
        # open the item, so Back from it goes there rather than back here
        self.openAfterClose = item
        # keep that screen's content hidden for the moment it shows before the item replaces it
        kodigui.setNavHidden(True)
        self.doClose()

    def showPostPlay(self):
        self.postPlayMode = True
        self.setProperty('post.play', '1')

    def hidePostPlay(self):
        self.postPlayMode = False
        self.setProperty('post.play', '')
        self.setProperty('no_hero_art', '')
        self._setPanelCorners({})
        self.setProperties((
            'info.title',
            'info.duration',
            'info.summary',
            'info.date',
            'next.thumb',
            'next.title',
            'next.subtitle',
            'prev.thumb',
            'prev.title',
            'prev.subtitle',
            'related.header',
            'has.next'
        ), '')

        self.onDeckListControl.reset()
        self.relatedListControl.reset()

    @busy.dialog()
    def postPlay(self, video=None, playlist=None, handler=None, stoppedManually=False, **kwargs):
        util.DEBUG_LOG('VideoPlayer: Starting post-play')
        self.showPostPlay()
        self.prev = video
        self.playlist = playlist
        self.handler = handler
        self.setPostPlayBackground()

        self.getHubs()

        self.setProperty(
            'thumb.fallback', 'script.plex/thumb_fallbacks/{0}.png'.format(self.prev.type in ('show', 'season', 'episode') and 'show' or 'movie')
        )

        util.DEBUG_LOG('PostPlay: Showing video info')
        if self.next:
            self.next.reload(includeChapters=1, includeExtras=1, includeExtrasCount=10)

        self.relatedPaginator = RelatedPaginator(self.relatedListControl,
                                                 leaf_count=int((self.prev or self.next).relatedCount),
                                                 parent_window=self)

        # movies only get Related
        self.onDeckPaginator = None
        vid = self.prev or self.next
        if self.prev.type != 'movie' and vid.sectionOnDeckCount:
            self.onDeckPaginator = OnDeckPaginator(self.onDeckListControl,
                                                   leaf_count=int(vid.sectionOnDeckCount) - (1 if self.next else 0),
                                                   parent_window=self)

        self.setInfo()
        self.fillOnDeck()
        self.fillRelated()

        if not stoppedManually:
            self.startTimer()

        if self.next:
            self.setFocusId(self.NEXT_BUTTON_ID)
        else:
            self.setFocusId(self.PREV_BUTTON_ID)
        self.postPlayInitialized = True

    def setPostPlayBackground(self):
        # Post-play's background is only the shared 4-corner colour panel
        # (includes/default_background.xml.tpl), tinted from the item that just played; the
        # hero-art box stays hidden while post-play is up. hidePostPlay() restores both for the
        # next item's start-up.
        self.setProperty('no_hero_art', '1')
        if util.addonSettings.dynamicBackgrounds:
            self._setPanelCorners(util.backgroundPanelCorners(
                getattr(self.prev, 'ultraBlurColors', None),
                seed=self.prev.get('ratingKey') or self.prev.get('title')))

    def resetPassoutProtection(self):
        self.passoutProtection = time.time() + PASSOUT_PROTECTION_DURATION_SECONDS

    def startTimer(self):
        if not util.getUserSetting('post_play_auto', True):
            util.DEBUG_LOG('Post play auto-play disabled')
            return

        if util.MONITOR.tv_standby:
            util.DEBUG_LOG('Post play auto-play skipped: TV in standby')
            return

        if not self.next:
            return

        if time.time() > self.passoutProtection and self.prev.duration.asInt() > PASSOUT_LAST_VIDEO_DURATION_MILLIS:
            util.DEBUG_LOG('Post play auto-play skipped: Passout protection')
            return
        else:
            millis = (self.passoutProtection - time.time()) * 1000
            util.DEBUG_LOG('Post play auto-play: Passout protection in {0}',
                           lambda: util.durationToShortText(millis))

        self.timeout = time.time() + abs(util.getSetting('postplay_timeout', 10))
        util.DEBUG_LOG('Starting post-play timer until: %i' % self.timeout)
        threading.Thread(target=self.countdown).start()

    def cancelTimer(self):
        if self.timeout is not None:
            util.DEBUG_LOG('Canceling post-play timer')

        self.timeout = None
        self.setProperty('countdown', '')

    def countdown(self):
        shown = None
        while self.timeout and not util.MONITOR.waitForAbort(0.1):
            if util.MONITOR.tv_standby:
                util.DEBUG_LOG('Post-play timer canceled: TV in standby')
                self.cancelTimer()
                break
            now = time.time()
            if self.timeout and now > self.timeout:
                self.timeout = None
                self.setProperty('countdown', '')
                util.DEBUG_LOG('Post-play timer finished')
                # This works. The direct method caused the OSD to be broken, possibly because it was triggered from another thread?
                # That was the only real difference I could see between the direct method and the user actually clicking the button.
                xbmc.executebuiltin('SendClick(,{0})'.format(self.NEXT_BUTTON_ID))
                # Direct method, causes issues with OSD
                # self.playVideo()
                break
            elif self.timeout is not None:
                # whole seconds left, only written when it changes
                text = T(35095, 'in {0}s').format(int(math.ceil(self.timeout - now)))
                if text != shown:
                    self.setProperty('countdown', text)
                    shown = text

    def getHubs(self):
        try:
            self.hubs = self.prev.postPlay()
        except:
            util.ERROR("No data - deleted or server disconnected?", notify=True, time_ms=5000)
            self.doClose()
            return

        self.next = None

        if self.playlist:
            if self.prev != self.playlist.current():
                self.next = self.playlist.current()
            else:
                if self.prev.type == 'episode' and 'tv.upnext' in self.hubs:
                    self.next = self.hubs['tv.upnext'].items[-1]

        if self.next:
            self.setProperty('has.next', '1')

    def setInfo(self):
        hide_spoilers = False
        if self.next and self.next.type == "episode":
            hide_spoilers = self.hideSpoilers(self.next, fully_watched=False, watched=False, use_cache=False)
        if self.next:
            if self.next.type == "episode" and hide_spoilers:
                if self.noTitles:
                    self.setProperty('info.title',
                                     u'{0} \u2022 {1}'.format(T(32310, 'S').format(self.next.parentIndex),
                                                              T(32311, 'E').format(self.next.index)))
                else:
                    self.setProperty('info.title', self.next.title)
                self.setProperty('info.summary', T(33008, ''))
            else:
                self.setProperty('info.title', self.next.title)
                self.setProperty('info.summary', util.widenParagraphBreaks(self.next.summary))
            self.setProperty('info.duration', util.durationToText(self.next.duration.asInt()))

        if self.prev.type == 'episode':
            self.setProperty('related.header', T(32306, 'Related Shows'))
            if self.next:
                thumb_opts = {}
                if hide_spoilers:
                    thumb_opts = self.getThumbnailOpts(self.next, hide_spoilers=hide_spoilers)
                self.setProperty('next.thumb', self.next.thumb.asTranscodedImageURL(*self.NEXT_DIM, **thumb_opts))
                self.setProperty('info.date',
                                 util.cleanLeadingZeros(self.next.originallyAvailableAt.asDatetime('%B %d, %Y')))

                # the show's name stands in when spoiler settings hide unwatched episode titles
                self.setProperty('next.title', self.next.grandparentTitle if hide_spoilers and self.noTitles
                                 else self.next.title)
                self.setProperty('next.subtitle', self.episodeCode(self.next))
            if self.prev:
                self.setProperty('prev.thumb', self.prev.thumb.asTranscodedImageURL(*self.PREV_DIM))
                self.setProperty('prev.title', self.prev.title)
                self.setProperty('prev.subtitle', self.episodeCode(self.prev))
        elif self.prev.type == 'movie':
            self.setProperty('related.header', T(32404, 'Related Movies'))
            if self.next:
                self.setProperty('next.thumb', self.next.defaultArt.asTranscodedImageURL(*self.NEXT_DIM))
                self.setProperty('info.date', self.next.year)

                self.setProperty('next.title', self.next.title)
                self.setProperty('next.subtitle', self.next.year)
            if self.prev:
                self.setProperty('prev.thumb', self.prev.defaultArt.asTranscodedImageURL(*self.PREV_DIM))
                self.setProperty('prev.title', self.prev.title)

    @staticmethod
    def episodeCode(ep):
        # e.g. "S1 - E2" with a bullet, as the On Deck row's second caption line
        return u'{0} \u2022 {1}'.format(T(32310, 'S').format(ep.parentIndex), T(32311, 'E').format(ep.index))

    def fillOnDeck(self):
        if not self.onDeckPaginator:
            return False

        if not self.onDeckPaginator.leafCount:
            self.onDeckPaginator.reset()
            return False

        items = self.onDeckPaginator.paginate()

        if not items:
            return False

        return True

    def fillRelated(self, has_prev=False):
        if not self.relatedPaginator.leafCount:
            self.relatedListControl.reset()
            return False

        items = self.relatedPaginator.paginate()

        if not items:
            return False
        return True

    def playVideo(self, prev=False):
        self.cancelTimer()
        # the resume request the window opened with was for its first video only; everything played
        # from post-play starts at the beginning - including an in-progress Playing next, as fits
        # watching through a series
        self.resume = False
        try:
            if not self.next and self.playlist:
                if prev:
                    self.playlist.prev()
                self.aborted = False
                self.playQueue = self.playlist
                self.video = None
            else:
                video = self.next
                if prev:
                    video = self.prev
                    # when playing the previous video, move the playlist back as well
                    self.playlist.prev()

                if not video:
                    util.DEBUG_LOG('Trying to play next video with no next video available')
                    self.video = None
                    return

                self.playQueue = None
                self.video = video

            self.play(handler=self.handler)
        except:
            util.ERROR()


def librarySectionOf(item):
    section_id = str(item.getLibrarySectionId())
    for section in plexapp.SERVERMANAGER.selectedServer.library.sections():
        if str(section.key) == section_id:
            return section
    return None


def play(video=None, play_queue=None, resume=False, bgm=False, context=None, **kwargs):
    """context: the calling window, which opens anything picked from post-play's rows once the
    player has closed (see opener.open()'s own context)."""
    w = None
    try:
        w = VideoPlayerWindow.open(video=video, play_queue=play_queue, resume=resume, bgm=bgm, aggressive=True)
    except util.NoDataException:
        raise
    finally:
        # codec teardown might show a spinner, wait a short while - not when post-play is closing
        # to open an item: playback ended long before, and the wait only kept the screen that
        # started playback on show before the item replaced it
        if not (w and w.openAfterClose is not None):
            util.MONITOR.waitFor(0.5)
        util.DEBUG_LOG("VideoPlayer Window exit")
        if w.playbackFailed:
            util.DEBUG_LOG("VideoPlayer: Playback failed, checking and waiting for open dialogs to close")
            ct = 0
            if xbmcgui.getCurrentWindowDialogId() > 9999:
                util.LOG("VideoPlayer: Unexpected dialog open, waiting for it to close until closing window: {}",
                         xbmcgui.getCurrentWindowDialogId())
                while xbmcgui.getCurrentWindowDialogId() > 9999 and ct < util.MONITOR.waitAmount(10):
                    util.MONITOR.waitFor()
                    ct += 1
        player.PLAYER.off('session.ended', w.sessionEnded)
        player.PLAYER.off('videowindow.closed', w.videoWindowClosed)
        player.PLAYER.off('post.play', w.postPlay)
        player.PLAYER.off('av.started', w.playerPlaybackStarted)
        player.PLAYER.off('starting.video', w.onVideoStarting)
        player.PLAYER.off('started.video', w.onVideoStarted)
        player.PLAYER.off('changed.video', w.onVideoChanged)
        player.PLAYER.off('change.background', w.changeBackground)
        player.PLAYER.off('playback.failed', w.setPlaybackFailed)
        player.PLAYER.reset()

    if w:
        command = w.exitCommand
        item = w.openAfterClose
        del w
        util.garbageCollect()
        if item is not None:
            # In a chain, Back from what opens goes to the item's own library section rather than
            # the screen that started playback (chain_root, LibraryWindow.swapTo()); outside one
            # it opens on top of that screen. came_from="postplay" keeps an opened show's theme
            # music off, as before.
            openKwargs = {}
            host = context._liveChainHost() if context is not None and hasattr(context, '_liveChainHost') else None
            section = host is not None and librarySectionOf(item)
            if section:
                openKwargs['chain_root'] = section
            try:
                result = opener.open(item, context=context, came_from="postplay", **openKwargs)
            except Exception:
                kodigui.setNavHidden(False)
                raise
            if host is not None:
                # the swap completes on the host's own loop, where the new screen's first init
                # clears nav_hidden; this only covers it never getting there
                threading.Timer(5, kodigui.setNavHidden, args=(False,)).start()
            else:
                kodigui.setNavHidden(False)
            return result
        return command
    return
