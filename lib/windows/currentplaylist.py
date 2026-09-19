from __future__ import absolute_import

from kodi_six import xbmc
from kodi_six import xbmcgui

from lib import kodijsonrpc
from lib import player
from lib import util
from lib.util import T
from . import busy
from . import dropdown
from . import kodigui
from . import opener
from . import windowutils


def require_duration(f):
    def wrapper(self, *args, **kwargs):
        if not self.duration:
            self.setDuration()
        return f(self, *args, **kwargs)
    return wrapper


class CurrentPlaylistWindow(kodigui.ControlledWindow, windowutils.UtilMixin):
    xmlFile = 'script-plex-music_current_playlist.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    LI_THUMB_DIM = (64, 64)
    ALBUM_THUMB_DIM = util.scaleResolution(639, 639)

    PLAYLIST_LIST_ID = 101

    SEEK_BUTTON_ID = 500
    SEEK_IMAGE_ID = 510

    POSITION_IMAGE_ID = 201
    SELECTION_INDICATOR = 202
    SELECTION_BOX = 203

    REPEAT_BUTTON_ID = 401
    SHUFFLE_BUTTON_ID = 402
    SHUFFLE_REMOTE_BUTTON_ID = 422
    SKIP_PREV_BUTTON_ID = 404
    SKIP_NEXT_BUTTON_ID = 409
    PLAYLIST_BUTTON_ID = 410
    OPTIONS_BUTTON_ID = 411
    STOP_BUTTON_ID = 407

    # The seekbar is the player screen's bar at 80% of a 1440-wide now-playing column, shifted
    # 20px left with the rest of that column - see the SEEKBAR comment in
    # script-plex-music_current_playlist.xml.tpl, whose 124/1152 these must match.
    # MusicPlayerWindow overrides the three widths for its full-screen column.
    SEEK_IMAGE_WIDTH = 1152
    SELECTION_BOX_WIDTH = 101
    SELECTION_INDICATOR_Y = 896

    BAR_X = 124
    BAR_Y = 921
    BAR_RIGHT = 1276
    BAR_BOTTOM = 969

    # Class level, not just assigned in __init__: MusicPlayerWindow subclasses this but calls
    # kodigui.ControlledWindow.__init__ directly, so this class's __init__ never runs for it and
    # anything set only there is missing on the player. Found the hard way - updateFromTrack()
    # died on _panelAlbum every time the player opened, which left it with no background panel
    # (the cover survived, since that is set earlier in the same method).
    #
    # (parentRatingKey, Album) of the last album fetched for the background panel - see
    # _albumForPanel().
    _panelAlbum = None
    # What fillPlaylist() last put in the rows - see playlistSignature().
    _playlistSig = None

    def __init__(self, *args, **kwargs):
        kodigui.ControlledWindow.__init__(self, *args, **kwargs)
        self.selectedOffset = 0
        self.duration = None
        self.track = None
        self.setDuration()
        self.exitCommand = None
        self.musicPlayerWinID = kwargs.get('winID')

    def doClose(self, **kwargs):
        player.PLAYER.off('av.started', self.onPlayBackStarted)
        player.PLAYER.off('playlist.changed', self.playQueueCallback)
        if player.PLAYER.handler.playQueue and player.PLAYER.handler.playQueue.isRemote:
            player.PLAYER.handler.playQueue.off('change', self.updateProperties)
        self.commonDeinit()
        kodigui.ControlledWindow.doClose(self)

    def commonInit(self):
        player.PLAYER.on('starting.audio', self.onAudioStarting)
        player.PLAYER.on('started.audio', self.onAudioStarted)
        player.PLAYER.on('changed.audio', self.onAudioChanged)

    def commonDeinit(self):
        player.PLAYER.off('starting.audio', self.onAudioStarting)
        player.PLAYER.off('started.audio', self.onAudioStarted)
        player.PLAYER.off('changed.audio', self.onAudioChanged)

    def onFirstInit(self):
        self.playlistListControl = kodigui.ManagedControlList(self, self.PLAYLIST_LIST_ID, 9)
        self.setupSeekbar()

        self.fillPlaylist()
        self.selectPlayingItem()
        self.setFocusId(self.PLAYLIST_LIST_ID)
        self.commonInit()
        self.updateProperties()
        self.updateFromTrack()
        if player.PLAYER.handler.playQueue and player.PLAYER.handler.playQueue.isRemote:
            player.PLAYER.handler.playQueue.on('change', self.updateProperties)
        player.PLAYER.on('playlist.changed', self.playQueueCallback)

    def onAction(self, action):
        try:
            controlID = self.getFocusId()
            if action in (xbmcgui.ACTION_PREVIOUS_MENU, xbmcgui.ACTION_NAV_BACK):
                self.doClose()
                return
            if self.checkSeekActions(action, controlID):
                return
        except:
            util.ERROR()

        kodigui.ControlledWindow.onAction(self, action)

    def onClick(self, controlID):
        if controlID == self.PLAYLIST_LIST_ID:
            self.playlistListClicked()
        elif controlID == self.SEEK_BUTTON_ID:
            self.seekButtonClicked()
        elif controlID == self.SHUFFLE_BUTTON_ID:
            self.fillPlaylist()
            self.selectPlayingItem()
        elif controlID == self.SHUFFLE_REMOTE_BUTTON_ID:
            player.PLAYER.handler.playQueue.setShuffle()
        elif controlID == self.REPEAT_BUTTON_ID:
            self.repeatButtonClicked()
        elif controlID == self.SKIP_PREV_BUTTON_ID:
            self.skipPrevButtonClicked()
            self.selectPlayingItem()
        elif controlID == self.SKIP_NEXT_BUTTON_ID:
            self.skipNextButtonClicked()
            self.selectPlayingItem()
        elif controlID == self.OPTIONS_BUTTON_ID:
            self.optionsButtonClicked()
        elif controlID == self.STOP_BUTTON_ID:
            self.stopButtonClicked()

    def onFocus(self, controlID):
        if controlID == self.SEEK_BUTTON_ID:
            try:
                if player.PLAYER.isPlaying():
                    self.selectedOffset = player.PLAYER.getTime() * 1000
                else:
                    self.selectedOffset = 0
            except RuntimeError:
                self.selectedOffset = 0

            self.updateSelectedProgress()

    def onPlayBackStarted(self, **kwargs):
        self.setDuration()

    def onAudioStarting(self, *args, **kwargs):
        util.setGlobalProperty('ignore_spinner', '1')
        self.ignoreStopCommands = True

    def onAudioStarted(self, *args, **kwargs):
        util.setGlobalProperty('ignore_spinner', '')
        self.ignoreStopCommands = False
        self.selectedOffset = 0
        self.duration = None
        self.setDuration()
        self.updateFromTrack()
        # Next/previous depend on where the playing track sits, so they have to be worked out
        # again here. Waiting for the queue's own 'change' signal would leave them a refresh
        # behind (updatePlayQueue delays that by 5s), showing Next as live on the last track for
        # several seconds. The queue's selectedId is already current by now -
        # AudioPlayerHandler.extractTrackInfo() sets it as soon as it identifies the track.
        self.updateProperties()

    def onAudioChanged(self, *args, **kwargs):
        util.setGlobalProperty('ignore_spinner', '')
        self.ignoreStopCommands = False
        self.setDuration()
        self.updateFromTrack()

    COVER_FALLBACK = 'script.plex/thumb_fallbacks/music.png'

    # The 4 background corner tints, ids as declared in both windows' templates - see the
    # BACKGROUND comment in either for why these are driven from here rather than from window
    # properties like every other screen's panel.
    PANEL_CORNER_CONTROLS = ((301, 'topLeft'), (302, 'topRight'), (303, 'bottomLeft'), (304, 'bottomRight'))

    def updateFromTrack(self, track=None):
        """The cover and the background panel, from the track. Called with the track about to
        play from MusicPlayerWindow.onFirstInit(); otherwise with the one the handler extracted
        from the playing item (player.PLAYER.currentTrack()), which
        AudioPlayerHandler.onPlayBackStarted() has refreshed by the time started.audio fires.

        Cover: a window property rather than $INFO[Player.Art(thumb)] in the template. Prev/next
        (unlike a track ending) stop the player for the ~10ms before the next item starts
        (kodi.log: "Player - STOPPED" then "STARTED"), and for that gap plus the reload
        Player.Art(thumb) is empty, so the image control dropped its texture and the light-grey
        fallback plate under it flashed through. This property is only ever set on a track
        start, never cleared, so the control keeps the old texture until the new one is ready
        and crossfades (its <fadetime> - CGUIImage::Process holds the last texture while the
        next is loading). Same URL as the player's list item (player.py, 640x640), so the two
        share Kodi's texture cache, and consecutive tracks of one album don't even reload. The
        fallback for a track with no art is chosen here for the same reason - a fallback layer
        in the template would flash on during the gap.

        Panel: the 4-corner panel (includes/default_background.xml.tpl) from the track's album -
        its ultraBlurColors, the same source the Album screen's panel uses, so the two agree -
        falling back to the track's own when it has no album (or the album carries none), and
        then to the seeded stand-in every other screen ends up with (util.backgroundPanelCorners),
        seeded on the album so a whole album shares it. updateBackgroundFrom() (kodigui.py) isn't
        used because these windows show the cover itself and never want the hero-art box that
        also drives; crossfade=False because on these two screens the panel is the whole
        background and its crossfade flickered - see _setPanelCorners()."""
        track = track or player.PLAYER.currentTrack()
        if not track:
            return
        thumb = track.defaultThumb
        self.setProperty('cover.url', (thumb and thumb.asTranscodedImageURL(640, 640)) or self.COVER_FALLBACK)

        if not util.addonSettings.dynamicBackgrounds:
            return
        album = self._albumForPanel(track)
        colors = album is not None and getattr(album, 'ultraBlurColors', None) or None
        if not colors:
            colors = getattr(track, 'ultraBlurColors', None)
        seed = track.get('parentRatingKey') or track.get('ratingKey') or track.get('title')
        self.setPanelCorners(util.backgroundPanelCorners(colors, seed=seed))

    def setPanelCorners(self, corners):
        """The 4 corner tints, straight onto the controls. A corner with no color is set fully
        transparent rather than hidden - a <visible> condition is one more thing that can flap."""
        for cid, corner in self.PANEL_CORNER_CONTROLS:
            try:
                self.getControl(cid).setColorDiffuse(corners.get(corner) or '00000000')
            except (RuntimeError, AttributeError):
                util.DEBUG_LOG('{}: no background corner control {}', self.__class__.__name__, cid)

    def _albumForPanel(self, track):
        """The track's album, fetched once and reused for the tracks that follow on it - a
        failed or empty fetch is remembered too, so a track that has none isn't retried on
        every callback. MusicPlayerWindow pre-seeds this with the album it was opened from."""
        key = track.get('parentRatingKey')
        if not key:
            return None
        if self._panelAlbum and self._panelAlbum[0] == key:
            return self._panelAlbum[1]
        album = None
        if track.get('parentKey'):
            try:
                album = track.album()
            except Exception:
                util.ERROR()
        self._panelAlbum = (key, album)
        return album

    def repeatButtonClicked(self):
        if player.PLAYER.handler.playQueue and player.PLAYER.handler.playQueue.isRemote:
            if xbmc.getCondVisibility('Playlist.IsRepeatOne'):
                xbmc.executebuiltin('PlayerControl(RepeatOff)')
            elif player.PLAYER.handler.playQueue.isRepeat:
                player.PLAYER.handler.playQueue.setRepeat(False)
                player.PLAYER.handler.playQueue.refresh(force=True)
                xbmc.executebuiltin('PlayerControl(RepeatOne)')
            else:
                player.PLAYER.handler.playQueue.setRepeat(True)
                player.PLAYER.handler.playQueue.refresh(force=True)
                # Kodi has to be told as well. setRepeat() only sets flags on the queue object
                # (the value rides along on the next request), and PMS's own repeat governs what
                # it hands back when windowing - neither makes Kodi loop the playlist it is
                # actually playing, so repeat-all did nothing audible and playback just stopped at
                # the end (live, 2026-09-19).
                xbmc.executebuiltin('PlayerControl(RepeatAll)')
        else:
            xbmc.executebuiltin('PlayerControl(Repeat)')

    def skipPrevButtonClicked(self):
        if not xbmc.getCondVisibility('MusicPlayer.HasPrevious') and player.PLAYER.handler.playQueue and player.PLAYER.handler.playQueue.isRemote:
            util.DEBUG_LOG('MusicPlayer: No previous in Kodi playlist - refreshing remote PQ')
            if not player.PLAYER.handler.playQueue.refresh(force=True, wait=True):
                return

        # Sets script.plex.ignore_spinner, which is what stops Kodi's own DialogBusy fading in
        # over the file swap that PlayerControl() is about to start (skin.plextuary/xml/
        # DialogBusy.xml gates every one of its animations on that property being empty).
        # playlistListClicked() already does this before playselected(), and MusicPlayerWindow's
        # own copies of these two methods always have - without it the spinner blinked over the
        # middle of this window on every next/previous click, and nowhere else (live, 2026-09-19).
        self.onAudioStarting()
        xbmc.executebuiltin('PlayerControl(Previous)')

    def skipNextButtonClicked(self):
        if not xbmc.getCondVisibility('MusicPlayer.HasNext') and player.PLAYER.handler.playQueue and player.PLAYER.handler.playQueue.isRemote:
            util.DEBUG_LOG('MusicPlayer: No next in Kodi playlist - refreshing remote PQ')
            if not player.PLAYER.handler.playQueue.refresh(force=True, wait=True):
                return

        self.onAudioStarting()
        xbmc.executebuiltin('PlayerControl(Next)')

    def optionsButtonClicked(self, pos=(670, 1060)):
        track = player.PLAYER.currentTrack()
        if not track:
            return

        options = []

        options.append({'key': 'to_album', 'display': T(32300, 'Go to Album')})
        options.append({'key': 'to_artist', 'display': T(32301, 'Go to Artist')})
        options.append({'key': 'to_section', 'display': T(32302, u'Go to {0}').format(track.getLibrarySectionTitle())})

        choice = dropdown.showDropdown(options, pos, pos_is_bottom=True, close_on_playback_ended=True)
        if not choice:
            return

        if choice['key'] == 'to_album':
            self.processCommand(opener.open(track.parentRatingKey))
        elif choice['key'] == 'to_artist':
            self.processCommand(opener.open(track.grandparentRatingKey))
        elif choice['key'] == 'to_section':
            self.goHome(track.getLibrarySectionId())

    def stopButtonClicked(self):
        xbmc.executebuiltin('Action(Back, {})'.format(self.musicPlayerWinID))
        util.MONITOR.waitForAbort(0.5)
        player.PLAYER.stopAndWait()
        self.exitCommand = "STOP"
        self.doClose()

    def selectPlayingItem(self):
        for mli in reversed(self.playlistListControl):
            if xbmc.getCondVisibility('String.StartsWith(MusicPlayer.Comment,{0})'.format(mli.dataSource['comment'].split(':', 1)[0])):
                self.playlistListControl.selectItem(mli.pos())
                break

    def playQueueCallback(self, **kwargs):
        self.setProperty('pq.isshuffled', player.PLAYER.handler.playQueue.isShuffled and '1' or '')

        items = self.playlistItems()
        if self.playlistSignature(items) == self._playlistSig:
            # Same tracks in the same order - only which one is playing has moved, so re-select and
            # leave the rows alone. Worth the check because this fires a lot: the handler rebuilds
            # Kodi's playlist whenever a windowed play queue slides
            # (AudioPlayerHandler.playQueueCallback, player.py), and a full reset()/addItems() here
            # blinks every row out and back.
            self.selectPlayingItem()
            return

        mli = self.playlistListControl.getSelectedItem()
        # No selection to preserve (an empty list, or focus never landed on it) - just refill and
        # let selectPlayingItem() put the highlight back.
        if not mli:
            self.fillPlaylist(items)
            self.selectPlayingItem()
            return

        plexID = mli.dataSource['comment'].split(':', 1)[0]
        viewPos = self.playlistListControl.getViewPosition()

        self.fillPlaylist(items)

        # due to Kodi playlist limitations and necessary swappery, we might've got the current item twice in the list;
        # select the latest one
        for ni in reversed(self.playlistListControl):
            if ni.dataSource['comment'].split(':', 1)[0] == plexID:
                self.playlistListControl.selectItem(ni.pos())
                break

        util.MONITOR.waitForAbort(0.25)

        newViewPos = self.playlistListControl.getViewPosition()
        if viewPos != newViewPos:
            diff = newViewPos - viewPos
            self.playlistListControl.shiftView(diff, True)

    def seekButtonClicked(self):
        player.PLAYER.seekTime(self.selectedOffset / 1000.0)

    def playlistListClicked(self):
        mli = self.playlistListControl.getSelectedItem()
        if not mli:
            return
        self.onAudioStarting()
        player.PLAYER.playselected(mli.pos())

    def createListItem(self, pi, idx):
        label2 = u'{0} • {1}'.format(pi['artist'][0], pi['album'])
        plexInfo = pi['comment']
        mli = kodigui.ManagedListItem(pi['title'], label2, thumbnailImage=pi['thumbnail'], data_source=pi)
        # The row is includes/track_row.xml.tpl (the music section's list view), which reads these
        # three rather than Label/Label2 - see its own comment on why. The second line here is
        # "Artist <bullet> Album", the same pairing and separator as the now-playing meta line
        # beside it, where that view's is the artist alone.
        mli.setProperty('track.title', pi['title'])
        mli.setProperty('track.artist', label2)
        mli.setProperty('thumb.fallback', 'script.plex/thumb_fallbacks/music.png')
        mli.setProperty('track.duration', util.simplifiedTimeDisplay(pi['duration'] * 1000))
        if plexInfo.startswith('PLEX-'):
            mli.setProperty('track.ID', plexInfo.split('-', 1)[-1].split(':', 1)[0])
            mli.setProperty('track.number', str(pi['playcount']))
        else:
            mli.setProperty('track.ID', '!NONE!')
            mli.setProperty('track.number', str(pi['track']))
            mli.setProperty('playlist.position', str(idx))

        mli.setProperty('file', pi['file'])
        return mli

    @staticmethod
    def playlistItems():
        """Kodi's music playlist, as the JSON-RPC hands it over."""
        return kodijsonrpc.rpc.PlayList.GetItems(
            playlistid=xbmc.PLAYLIST_MUSIC,
            properties=['title', 'artist', 'album', 'track', 'thumbnail', 'duration', 'playcount', 'comment', 'file']
        )['items']

    @staticmethod
    def playlistSignature(items):
        """What the rows are showing, for telling a real queue change from a track change. The
        PLEX-<ratingKey> half of each comment, in order - the rest of that tag is the serialised
        track, which is bulky and doesn't identify anything the ratingKey doesn't."""
        return tuple(pi['comment'].split(':', 1)[0] for pi in items)

    @busy.dialog()
    def fillPlaylist(self, pl_items=None):
        pl_items = self.playlistItems() if pl_items is None else pl_items
        items = []
        idx = 1
        for pi in pl_items:
            mli = self.createListItem(pi, idx)
            if mli:
                mli.setProperty('index', str(idx))
                items.append(mli)
                idx += 1

        self.playlistListControl.reset()
        self.playlistListControl.addItems(items)
        self._playlistSig = self.playlistSignature(pl_items)

    def setupSeekbar(self):
        self.seekbarControl = self.getControl(self.SEEK_IMAGE_ID)
        self.selectionIndicator = self.getControl(self.SELECTION_INDICATOR)
        self.selectionBox = self.getControl(self.SELECTION_BOX)
        self.selectionBoxHalf = self.SELECTION_BOX_WIDTH // 2
        # Where the seek-time bubble stops tracking the scrub point and clamps to the bar's right
        # end instead (updateSelectedProgress()), so it never overhangs the bar.
        self.selectionBoxMax = self.SEEK_IMAGE_WIDTH - (self.selectionBoxHalf - 3)
        player.PLAYER.on('av.started', self.onPlayBackStarted)

    def checkSeekActions(self, action, controlID):
        if controlID == self.SEEK_BUTTON_ID:
            if action == xbmcgui.ACTION_MOUSE_MOVE:
                self.seekMouse(action)
                return True
            elif action in (xbmcgui.ACTION_MOVE_RIGHT, xbmcgui.ACTION_NEXT_ITEM):
                self.seekForward(3000)
                return True
            elif action in (xbmcgui.ACTION_MOVE_LEFT, xbmcgui.ACTION_PREV_ITEM):
                self.seekBack(3000)
                return True
            # elif action == xbmcgui.ACTION_MOVE_UP:
            #     self.seekForward(60000)
            # elif action == xbmcgui.ACTION_MOVE_DOWN:
            #     self.seekBack(60000)
        elif action == xbmcgui.ACTION_STOP:
            self.stopButtonClicked()
            return True

    def setDuration(self):
        try:
            #duration = None
            #if self.track:
            #    duration = self.track.duration.asInt()
            #if not duration:
            #    duration = player.PLAYER.getTotalTime() * 1000
            #if not duration:
            duration = player.PLAYER.getMusicInfoTag().getDuration() * 1000
            self.duration = duration if duration > 0 else self.duration
        except (RuntimeError, AttributeError):  # Not playing
            pass

    @require_duration
    def seekForward(self, offset):
        self.selectedOffset += offset
        if self.selectedOffset > self.duration:
            self.selectedOffset = self.duration

        self.updateSelectedProgress()

    @require_duration
    def seekBack(self, offset):
        self.selectedOffset -= offset
        if self.selectedOffset < 0:
            self.selectedOffset = 0

        self.updateSelectedProgress()

    @require_duration
    def seekMouse(self, action):
        x = self.mouseXTrans(action.getAmount1())
        y = self.mouseYTrans(action.getAmount2())
        if not (self.BAR_Y <= y <= self.BAR_BOTTOM):
            return

        if not (self.BAR_X <= x <= self.BAR_RIGHT):
            return

        self.selectedOffset = int((x - self.BAR_X) / float(self.SEEK_IMAGE_WIDTH) * self.duration)
        self.updateSelectedProgress()

    def setSeekbarProgress(self, w):
        # The scrubber (SEEK_IMAGE_ID) is a <reveal> progress control in both windows' templates
        # (see the SEEKBAR comment in either) so the pill mask clips rather than stretches with
        # it: set its percentage, not its width. Info-less, so the value sticks.
        self.seekbarControl.setPercent(w * 100.0 / self.SEEK_IMAGE_WIDTH)

    @require_duration
    def updateSelectedProgress(self):
        if not self.duration:
            return

        ratio = self.selectedOffset / float(self.duration)
        w = int(ratio * self.SEEK_IMAGE_WIDTH)
        self.setSeekbarProgress(w)

        self.selectionIndicator.setPosition(w, self.SELECTION_INDICATOR_Y)
        if w < self.selectionBoxHalf - 3:
            self.selectionBox.setPosition((-self.selectionBoxHalf + (self.selectionBoxHalf - w)) - 3, 0)
        elif w > self.selectionBoxMax:
            self.selectionBox.setPosition((-self.SELECTION_BOX_WIDTH + (self.SEEK_IMAGE_WIDTH - w)) + 3, 0)
        else:
            self.selectionBox.setPosition(-self.selectionBoxHalf, 0)
        self.setProperty('time.selection', util.simplifiedTimeDisplay(int(self.selectedOffset)))

    def updateProperties(self, **kwargs):
        pq = player.PLAYER.handler.playQueue
        if pq:
            if pq.isRemote:
                self.setProperty('pq.isRemote', '1')
                # hasNext()/hasPrev(), not allowSkipNext/allowSkipPrev: those two are
                # position-independent (totalSize > 1 and a container flag), so the buttons stayed
                # lit at both ends of the queue. These two ask where the playing track actually
                # sits. Same pair the video OSD uses (seekdialog.py).
                self.setProperty('pq.hasnext', pq.hasNext() and '1' or '')
                self.setProperty('pq.hasprev', pq.hasPrev() and '1' or '')
                self.setProperty('pq.repeat', pq.isRepeat and '1' or '')
                self.setProperty('pq.shuffled', pq.isShuffled and '1' or '')
            else:
                self.setProperties(('pq.isRemote', 'pq.hasnext', 'pq.hasprev', 'pq.repeat', 'pq.shuffled'), '')
