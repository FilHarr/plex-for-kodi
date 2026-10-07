from __future__ import absolute_import

import threading

import plexnet
from kodi_six import xbmcgui
from six.moves import range

from plexnet import plexapp, signalsmixin
from lib import backgroundthread
from lib import player
from lib import util
from lib.util import T
from . import busy
from . import dropdown
from . import home
from . import info
from . import kodigui
from . import opener
from . import videoplayer
from . import windowutils
from .mixins.row_restore import RowRestoreMixin

PLAYLIST_PAGE_SIZE = 500

class ChunkRequestTask(backgroundthread.Task):
    WINDOW = None

    @classmethod
    def reset(cls):
        del cls.WINDOW
        cls.WINDOW = None

    def setup(self, start, size):
        self.start = start
        self.size = size
        return self

    def contains(self, pos):
        return self.start <= pos <= (self.start + self.size)

    def run(self):
        if self.isCanceled():
            return

        try:
            items = self.WINDOW.playlist.extend(self.start, self.size)
            if self.isCanceled():
                return

            if not self.WINDOW:  # Window is closed
                return

            self.WINDOW.chunkCallback(items, self.start)
        except AttributeError:
            util.DEBUG_LOG('Playlist window closed, ignoring chunk at index {0}', self.start)
        except plexnet.exceptions.BadRequest:
            util.DEBUG_LOG('404 on playlist: {0}', lambda: repr(self.WINDOW.playlist.title))


class PlaylistWindow(kodigui.ControlledWindow, windowutils.UtilMixin, windowutils.SidebarMixin, signalsmixin.SignalsMixin,
                     RowRestoreMixin):
    xmlFile = 'script-plex-playlist.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    OPTIONS_GROUP_ID = 200
    PLAYER_STATUS_BUTTON_ID = 204

    PLAY_BUTTON_ID = 301
    SHUFFLE_BUTTON_ID = 302

    # The invisible click target over the header's summary textbox (script-plex-playlist.xml.tpl),
    # the same 305 the Album screen uses.
    SUMMARY_BUTTON_ID = 305

    # Each row's art box (includes/playlist_row.xml.tpl).
    LI_AR16X9_THUMB_DIM = util.scaleResolution(142, 80)
    LI_SQUARE_THUMB_DIM = util.scaleResolution(80, 80)
    LI_POSTER_THUMB_DIM = util.scaleResolution(53, 80)

    # The Album screen's cover request (tracks.py's THUMB_SQUARE_DIM), for the same 370 box.
    ALBUM_THUMB_DIM = util.scaleResolution(630, 630)

    PLAYLIST_LIST_ID = 101

    def __init__(self, *args, **kwargs):
        kodigui.ControlledWindow.__init__(self, *args, **kwargs)
        signalsmixin.SignalsMixin.__init__(self)
        self.playlist = kwargs.get('playlist')
        self.exitCommand = None
        self.tasks = backgroundthread.Tasks()
        self.isPlaying = False
        self.video_progress = {}
        self.lastFocusID = None
        # Whether rows so far have shown a poster, and 16:9 art - see noteArtShape().
        self.seenPoster = False
        self.seenWide = False
        # hashed-orbiting-pizza.md Phase 4 follow-up: None here means "build my own sectionList"
        # (a standalone/un-hosted open) - a hosted open (LibraryWindow._setupCurrent(), library.py)
        # overwrites this with the host's own sectionList object before onFirstInit() runs.
        self.sectionList = None
        # (PLAYLIST_LIST_ID, position): Back from an item visited from here ("Visit media item")
        # lands on it again, not on the playlist's current item (RowRestoreMixin; on request,
        # 2026-10-07)
        self.restoreFocus = kwargs.get('restore_focus')
        # Set once a Back restore has chosen the row, so a later chunk's onPlaylistFilled() doesn't
        # move the selection back to the playlist's current item.
        self.restoredSelection = False
        ChunkRequestTask.WINDOW = self

    def restoreRows(self):
        return {self.PLAYLIST_LIST_ID: self.playlistListControl}

    def initialBackgroundURL(self):
        # No hero art from the first frame (kodigui's paintInitialBackground()) - see
        # setProperties().
        return None

    def onFirstInit(self):
        self.playlistListControl = kodigui.ManagedControlList(self, self.PLAYLIST_LIST_ID, 5)
        self.setProperties()
        player.PLAYER.on('new.video', self.onNewVideo)
        player.PLAYER.on('video.progress', self.onVideoProgress)
        self.on('playlist.filled', self.onPlaylistFilled)

        if self.sectionList is None:
            self.sectionList = kodigui.ManagedControlList(self, self.SECTION_LIST_ID, 15)
            self.buildSectionList()
        else:
            self.sectionList.newControl(self)
        self._selectActiveSection()
        self.displayServerAndUser()

        self.fillPlaylist()
        # An empty playlist leaves nothing on the screen to focus - no rows, and no Play/Shuffle
        # (hidden, script-plex-playlist.xml.tpl) - so the sidebar, as an empty library section
        # does (LibraryWindow).
        if self.playlistListControl.size():
            # Every row exists by now - the first chunk's, and placeholders for the rest - so a
            # Back restore can select its row straight away.
            if self.restoreFocus and self._restoreRowFocus():
                self.restoredSelection = True
            else:
                self.setFocusId(self.PLAYLIST_LIST_ID)
        else:
            self.setFocusId(self.SECTION_LIST_ID)

    def onReInit(self):
        if self.playlistListControl.size():
            self.playlistListControl.setSelectedItemByDataSource(self.playlist.current())

    def onFocus(self, controlID):
        # Not live on its host yet, or any more (kodigui.BaseWindow.ignoresInput()).
        if self.ignoresInput():
            return
        self.reselectActiveSection(controlID, self.lastFocusID)
        self.lastFocusID = controlID

    # def onAction(self, action):
    #     try:
    #         if action in(xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_CONTEXT_MENU):
    #             if not xbmc.getCondVisibility('ControlGroup({0}).HasFocus(0)'.format(self.OPTIONS_GROUP_ID)):
    #                 self.setFocusId(self.OPTIONS_GROUP_ID)
    #                 return
    #     except:
    #         util.ERROR()

    #     self.defOnAction(action)

    def onNewVideo(self, *args, **kwargs):
        video = kwargs.get("video")
        self.playlist.setCurrent(self.playlist.getPosFromItem(video))

    def onVideoProgress(self, data=None, **kwargs):
        if not data:
            return

        util.DEBUG_LOG("Storing video progress data: {}", data)
        gprk, prk, rk, state = data
        self.video_progress[rk] = state

    def onAction(self, action):
        # Hosted: the host sees the action first (kodigui.BaseWindow.routeActionToHost()).
        if self.routeActionToHost(action):
            return
        try:
            if action in (xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_PREVIOUS_MENU):
                self.doClose()
            elif self.playlist.playlistType == 'video' and action == xbmcgui.ACTION_CONTEXT_MENU:
                return self.plItemPlaybackMenu()
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
        elif controlID == self.PLAYLIST_LIST_ID:
            self.playlistListClicked()
        elif controlID == self.PLAYER_STATUS_BUTTON_ID:
            self.showAudioPlayer()
        elif controlID == self.PLAY_BUTTON_ID:
            self.playlistListClicked(no_item=True, shuffle=False, play=True)
        elif controlID == self.SHUFFLE_BUTTON_ID:
            self.playlistListClicked(no_item=True, shuffle=True, play=True)
        elif controlID == self.SUMMARY_BUTTON_ID:
            info.showSummary(self.playlist.title, self.playlist.get('summary'))

    def doClose(self, **kw):
        player.PLAYER.off('new.video', self.onNewVideo)
        player.PLAYER.off('video.progress', self.onVideoProgress)
        self.off('playlist.filled', self.onPlaylistFilled)
        kodigui.ControlledWindow.doClose(self)
        self.tasks.cancel()
        ChunkRequestTask.reset()

    def plItemPlaybackMenu(self, select_choice='visit'):
        mli = self.playlistListControl.getSelectedItem()
        if not mli or not mli.dataSource:
            return

        can_resume = mli.dataSource.viewOffset.asInt()

        options = [
            {'key': 'visit', 'display': T(33019, 'Visit Media Item')},
            {'key': 'play', 'display': T(33020, 'Play') if not can_resume else T(32317, 'Play from beginning')},
        ]
        if can_resume:
            options.append({'key': 'resume', 'display': T(32429, 'Resume from {0}').format(
                    util.timeDisplay(mli.dataSource.viewOffset.asInt()).lstrip('0').lstrip(':'))})

        choice = dropdown.showDropdown(
            options,
            pos=(660, 441),
            close_direction='none',
            set_dropdown_prop=False,
            header=T(33021, 'Choose action'),
            select_index=2 if select_choice == 'resume' else 1 if util.addonSettings.playlistVisitMedia else 0
        )

        if not choice:
            return

        if choice['key'] == 'visit':
            self.openItem(mli.dataSource)
        elif choice['key'] == 'play':
            self.playlistListClicked(resume=False, play=True)
        elif choice['key'] == 'resume':
            self.playlistListClicked(resume=True, play=True)

    def sidebarActiveSection(self, entries):
        # A playlist isn't tied to one library section (its items can span several): its server's
        # Playlists is where this screen was reached from.
        server = getattr(getattr(self, 'playlist', None), 'server', None)
        return home.playlistsSection(server) if server is not None else None

    def playlistListClicked(self, no_item=False, shuffle=False, resume=None, play=False):
        if no_item:
            mli = None
        else:
            mli = self.playlistListControl.getSelectedItem()
            if not mli or not mli.dataSource:
                return

        # The track already playing: just the player again, as the header's now-playing button
        # opens it - the Album and Artist screens' clicks end the same way (MusicPlayerWindow.play()
        # leaves a playing track alone). Must come before the stop below, which is what made this
        # restart it.
        if mli and self.playlist.playlistType == 'audio' and util.trackIsPlaying(mli.dataSource):
            self.showAudioPlayer()
            return

        try:
            self.isPlaying = True
            self.tasks.cancel()
            player.PLAYER.stop()  # Necessary because if audio is already playing, it will close the window when that is stopped
            if self.playlist.playlistType == 'audio':
                if self.playlist.leafCount.asInt() <= util.addonSettings.playlistMaxSize:
                    self.playlist.setShuffle(shuffle)
                    self.playlist.setCurrent(mli and mli.pos() or 0)
                    self.showAudioPlayer(track=mli and mli.dataSource or self.playlist.current(), playlist=self.playlist)
                else:
                    args = {'sourceType': '8', 'shuffle': shuffle}
                    if mli:
                        args['key'] = mli.dataSource.key
                    pq = plexnet.playqueue.createPlayQueueForItem(self.playlist, options=args)
                    opener.open(pq)
            elif self.playlist.playlistType == 'video':
                if not util.addonSettings.playlistVisitMedia or play:
                    if resume is None and mli and bool(mli.dataSource.viewOffset.asInt()):
                        if not util.getSetting('assume_resume'):
                            return self.plItemPlaybackMenu(select_choice='resume')
                        resume = True

                    if self.playlist.leafCount.asInt() <= util.addonSettings.playlistMaxSize:
                        self.playlist.setShuffle(shuffle)
                        self.playlist.setCurrent(mli and mli.pos() or 0)
                        videoplayer.play(play_queue=self.playlist, resume=resume, context=self)
                    else:
                        args = {'shuffle': shuffle}
                        if mli:
                            args['key'] = mli.dataSource.key
                        pq = plexnet.playqueue.createPlayQueueForItem(self.playlist, options=args)
                        opener.open(pq, resume=resume)
                else:
                    if not mli:
                        firstItem = 0
                        if shuffle:
                            import random
                            firstItem = random.randint(0, self.playlistListControl.size()-1)
                        mli = self.playlistListControl.getListItem(firstItem)
                    self.openItem(mli.dataSource)

        finally:
            self.isPlaying = False
            self.restartFill()
            self.video_progress = {}

    def restartFill(self):
        threading.Thread(target=self._restartFill).start()

    def _restartFill(self):
        util.DEBUG_LOG('Checking if playlist list is full...')
        for idx, mli in enumerate(self.playlistListControl):
            if self.isPlaying or not self.isOpen or util.MONITOR.abortRequested():
                break

            if not mli.dataSource:
                if self.playlist[idx]:
                    self.updateListItem(idx, self.playlist[idx])
                else:
                    break
            # Update the progress for videos
            elif mli.dataSource.type in ('episode', 'movie', 'clip') and mli.dataSource.ratingKey in self.video_progress:
                mli.dataSource.clearCache()
                mli.dataSource.reload()
                self.updateListItem(idx, mli.dataSource)
        else:
            util.DEBUG_LOG('Playlist list is full - nothing to do')
            return

        util.DEBUG_LOG('Playlist list is not full - finishing')
        total = self.playlist.leafCount.asInt()
        for start in range(idx, total, PLAYLIST_PAGE_SIZE):
            if util.MONITOR.abortRequested():
                break
            self.tasks.add(ChunkRequestTask().setup(start, PLAYLIST_PAGE_SIZE))

        backgroundthread.BGThreader.addTasksToFront(self.tasks)

    def setProperties(self):
        # The colour panel alone, no hero art (on request, 2026-10-07 - was the composite): the
        # Playlists grid's own background (updatePanelFrom(), library_grid.py). A playlist has no
        # ultraBlurColors, so its panel is seeded from its ratingKey - the grid's seed, so the
        # colours carry over from the tile that opened it.
        self.updatePanelFrom(self.playlist)
        self.windowSetBackground('')
        fallback = self.thumbFallback()
        self.setProperty('playlist.thumb.fallback', fallback)
        # An empty playlist has no composite: its stand-in by another path than the fallback's, or
        # the cover stays blank (util.standInThumb(), as createPlaylistListItem() does for its tile).
        if self.playlist.composite:
            thumb = self.playlist.composite.asTranscodedImageURL(*self.ALBUM_THUMB_DIM)
        else:
            thumb = util.standInThumb(fallback)
        self.setProperty('playlist.thumb', thumb)
        self.setProperty('playlist.title', util.colorizeEmoji(self.playlist.title))
        # Cleared, not left unset: Kodi can hand a new window a reused id's old properties
        # (PrePlayWindow.doClose()), and a mixed playlist's would misplace this one's poster rows'
        # text. noteArtShape() sets it as rows fill.
        self.setProperty('playlist.mixed', '')
        self.setProperty('playlist.meta', T(35159, 'Smart playlist') if self.playlist.smart.asBool() else '')
        self.setProperty('summary', util.summaryForBox(self.playlist.get('summary')))

    def thumbFallback(self, name=None):
        """A stand-in image's skin path: name is the art's shape's own (music for square, movie for a
        poster, movie16x9 for 16:9); by default, the cover's - by the playlist's type."""
        if name is None:
            name = 'music' if self.playlist.playlistType == 'audio' else 'movie16x9'
        return 'script.plex/thumb_fallbacks/{0}.png'.format(name)


    def updateListItem(self, idx, pi, mli=None):
        mli = mli or self.playlistListControl.getListItem(idx)
        mli.setLabel(pi.title)
        mli.setProperty('track.ID', pi.ratingKey)
        mli.dataSource = pi
        # By the art's shape (includes/playlist_row.xml.tpl): square for a track, a film's poster,
        # 16:9 for the rest.
        mli.setProperty('thumb.fallback', self.thumbFallback(
            {'track': 'music', 'movie': 'movie'}.get(pi.type, 'movie16x9')))

        if pi.type == 'track':
            self.createTrackListItem(mli, pi)
        elif pi.type == 'episode':
            self.createEpisodeListItem(mli, pi)
        elif pi.type in ('movie', 'clip'):
            self.createMovieListItem(mli, pi)

        if pi.type in ('episode', 'movie', 'clip'):
            mli.setProperty('progress', util.getProgressImage(mli.dataSource))
            self.noteArtShape(poster=pi.type == 'movie')

        return mli

    def noteArtShape(self, poster):
        """Sets playlist.mixed once a video playlist's rows have shown both a film's poster and 16:9
        art, which moves the poster rows' text across to the 16:9 rows' column
        (includes/playlist_row.xml.tpl) so the list's text lines up. Known before the list is drawn
        for a playlist the first chunk holds (fillPlaylist()); a bigger one can turn out mixed in a
        later chunk, and its poster rows' text then moves across once (accepted, on request
        2026-10-07)."""
        if poster:
            if self.seenPoster:
                return
            self.seenPoster = True
        else:
            if self.seenWide:
                return
            self.seenWide = True
        if self.seenPoster and self.seenWide:
            self.setProperty('playlist.mixed', '1')

    def createTrackListItem(self, mli, track):
        mli.setLabel2(u'{0} / {1}'.format(track.grandparentTitle, track.parentTitle))
        mli.setThumbnailImage(track.defaultThumb.asTranscodedImageURL(*self.LI_SQUARE_THUMB_DIM))
        mli.setProperty('track.duration', util.simplifiedTimeDisplay(track.duration.asInt()))

    def createEpisodeListItem(self, mli, episode):
        label2 = u'{0} \u2022 {1}'.format(
            episode.grandparentTitle, u'{0} \u2022 {1}'.format(T(32310, 'S').format(episode.parentIndex),
                                                               T(32311, 'E').format(episode.index))
        )
        mli.setLabel2(label2)
        mli.setThumbnailImage(episode.thumb.asTranscodedImageURL(*self.LI_AR16X9_THUMB_DIM))
        mli.setProperty('track.duration', util.durationToShortText(episode.duration.asInt()))
        mli.setProperty('video', '1')
        mli.setProperty('watched', episode.isPlayed and '1' or '')
        mli.setProperty('unwatched', episode.isFullyWatched and '' or '1')

    def createMovieListItem(self, mli, movie):
        mli.setLabel(movie.defaultTitle)
        mli.setLabel2(movie.year)
        if movie.type == 'movie':
            # The poster (on request, 2026-10-07 - was the 16:9 background art), in the row's poster
            # shape; clips keep their 16:9 art.
            mli.setThumbnailImage(movie.thumb.asTranscodedImageURL(*self.LI_POSTER_THUMB_DIM))
            mli.setProperty('poster', '1')
        else:
            mli.setThumbnailImage(movie.art.asTranscodedImageURL(*self.LI_AR16X9_THUMB_DIM))
        mli.setProperty('track.duration', util.durationToShortText(movie.duration.asInt()))
        mli.setProperty('video', '1')
        mli.setProperty('watched', movie.isPlayed and '1' or '')
        mli.setProperty('unwatched', movie.isWatched and '' or '1')


    def onPlaylistFilled(self, *args, **kwargs):
        if self.restoredSelection:
            # Back put the selection on the row it left from (onFirstInit()) - keep it there
            return
        start = kwargs.get("start", None)
        item_count = kwargs.get("item_count", None)
        uc = self.playlist.userCurrent()
        item_pos = self.playlist.getPosFromItem(uc)

        if item_pos > -1 and start is not None and item_count is not None and start <= item_pos < start + item_count:
            util.DEBUG_LOG("Playlist: Relevant task finished, selecting "
                           "user-relevant current item: {} (pos: {}, range: {}-{})", uc, item_pos, start, start + item_count)
            self.playlist.setCurrent(item_pos)
            success = self.playlistListControl.setSelectedItemByDataSource(self.playlist.current())
            if not success:
                util.LOG("Playlist: Couldn't find item in playlist (current: {}, user-current: {})",
                         self.playlist.current(), self.playlist.userCurrent())


    @busy.dialog()
    def fillPlaylist(self):
        total = self.playlist.leafCount.asInt()

        # leafCount is clamped to 6 when coming from Home/PlaylistsHub
        actualPlaylistLength = len(self.playlist.items())

        if total < len(self.playlist):
            total = actualPlaylistLength

        # Here rather than with the other hero properties: total is the real count, not leafCount.
        self.setProperty('playlist.subtitle', util.playlistSubtitle(self.playlist.playlistType, total,
                                                                    self.playlist.duration.asInt()))

        if not total:
            # An empty playlist (Recently Added with nothing new): nothing to fetch or select.
            # 'playlist.filled' would have onPlaylistFilled() ask it for its current item, which
            # raises IndexError on an empty one.
            self.playlistListControl.reset()
            return

        endoffirst = min(util.addonSettings.playlistMaxSize, PLAYLIST_PAGE_SIZE, total)
        items = [self.updateListItem(i, pi, kodigui.ManagedListItem()) for i, pi in enumerate(self.playlist.extend(0, endoffirst))]

        items += [kodigui.ManagedListItem() for i in range(total - endoffirst)]

        self.playlistListControl.reset()
        self.playlistListControl.addItems(items)

        if total <= min(util.addonSettings.playlistMaxSize, PLAYLIST_PAGE_SIZE):
            self.trigger('playlist.filled', start=0, item_count=total)
            return

        batchSize = min(util.addonSettings.playlistMaxSize, PLAYLIST_PAGE_SIZE)
        self.trigger('playlist.filled', start=0, item_count=batchSize)

        for start in range(endoffirst, total, batchSize):
            if util.MONITOR.abortRequested():
                break
            self.tasks.add(ChunkRequestTask().setup(start, batchSize))

        backgroundthread.BGThreader.addTasksToFront(self.tasks)

    def chunkCallback(self, items, start):
        for i, pi in enumerate(items):
            if self.isPlaying or not self.isOpen or util.MONITOR.abortRequested():
                break

            idx = start + i
            self.updateListItem(idx, pi)

        self.trigger('playlist.filled', start=start, item_count=len(items))
