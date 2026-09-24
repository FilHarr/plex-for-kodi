from __future__ import absolute_import

import json
import threading

import plexnet
from kodi_six import xbmcgui
from six.moves import range

from plexnet import signalsmixin, plexapp
from lib import backgroundthread
from lib import player
from lib import util
from lib.util import T
from . import busy
from . import dropdown
from . import home
from . import kodigui
from . import opener
from . import search
from . import videoplayer
from . import windowutils

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


class PlaylistWindow(kodigui.ControlledWindow, windowutils.UtilMixin, windowutils.SidebarMixin, signalsmixin.SignalsMixin):
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

    LI_AR16X9_THUMB_DIM = util.scaleResolution(178, 100)
    LI_SQUARE_THUMB_DIM = util.scaleResolution(100, 100)

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
        # hashed-orbiting-pizza.md Phase 4 follow-up: None here means "build my own sectionList"
        # (a standalone/un-hosted open) - a hosted open (LibraryWindow._setupCurrent(), library.py)
        # overwrites this with the host's own sectionList object before onFirstInit() runs.
        self.sectionList = None
        ChunkRequestTask.WINDOW = self

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
        self.setFocusId(self.PLAYLIST_LIST_ID)

    def onReInit(self):
        self.playlistListControl.setSelectedItemByDataSource(self.playlist.current())

    def onFocus(self, controlID):
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
        if self.handleSidebarDropdownClick(controlID):
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

    def searchButtonClicked(self):
        self.processCommand(search.dialog(self))

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

        for section in sections:
            mli = kodigui.ManagedListItem(section.title,
                                          iconImage='script.plex/home/type/{0}.png'.format(section.type),
                                          data_source=section)
            mli.setProperty('item', '1')
            if section == home.playlists_section:
                mli.setProperty('is.playlists', '1')
                mli.setIconImage('script.plex/home/type/playlists.png')
                # A single playlist isn't tied to one library section (its items can span several),
                # so unlike every other ported screen there's no getLibrarySectionId() to compare
                # against - just mark the Playlists entry active directly, since that's where this
                # screen was reached from.
                mli.setProperty('is.active', '1')
            elif section == home.watchlist_section:
                mli.setIconImage('script.plex/home/type/watchlist.png')
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

    def playlistListClicked(self, no_item=False, shuffle=False, resume=None, play=False):
        if no_item:
            mli = None
        else:
            mli = self.playlistListControl.getSelectedItem()
            if not mli or not mli.dataSource:
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
                        videoplayer.play(play_queue=self.playlist, resume=resume)
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
        self.setProperty(
            'background',
            util.backgroundFromArt(self.playlist.composite, width=self.width, height=self.height)
        )
        self.setProperty('playlist.thumb', self.playlist.composite.asTranscodedImageURL(*self.ALBUM_THUMB_DIM))
        self.setProperty('playlist.title', util.colorizeEmoji(self.playlist.title))
        self.setProperty('playlist.duration', util.durationToText(self.playlist.duration.asInt()))

    def updateListItem(self, idx, pi, mli=None):
        mli = mli or self.playlistListControl.getListItem(idx)
        mli.setLabel(pi.title)
        mli.setProperty('track.ID', pi.ratingKey)
        mli.setProperty('track.number', str(idx + 1))
        mli.dataSource = pi

        if pi.type == 'track':
            self.createTrackListItem(mli, pi)
        elif pi.type == 'episode':
            self.createEpisodeListItem(mli, pi)
        elif pi.type in ('movie', 'clip'):
            self.createMovieListItem(mli, pi)

        if pi.type in ('episode', 'movie', 'clip'):
            mli.setProperty('progress', util.getProgressImage(mli.dataSource))

        return mli

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
        mli.setProperty('watched', episode.isFullyWatched and '1' or '')
        mli.setProperty('unwatched', episode.isFullyWatched and '' or '1')

    def createMovieListItem(self, mli, movie):
        mli.setLabel(movie.defaultTitle)
        mli.setLabel2(movie.year)
        mli.setThumbnailImage(movie.art.asTranscodedImageURL(*self.LI_AR16X9_THUMB_DIM))
        mli.setProperty('track.duration', util.durationToShortText(movie.duration.asInt()))
        mli.setProperty('video', '1')
        mli.setProperty('watched', movie.isWatched and '1' or '')
        mli.setProperty('unwatched', movie.isWatched and '' or '1')


    def onPlaylistFilled(self, *args, **kwargs):
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
