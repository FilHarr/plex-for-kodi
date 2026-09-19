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

    def onAudioChanged(self, *args, **kwargs):
        util.setGlobalProperty('ignore_spinner', '')
        self.ignoreStopCommands = False
        self.setDuration()

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
        mli = self.playlistListControl.getSelectedItem()
        pi = mli.dataSource
        plexID = pi['comment'].split(':', 1)[0]
        viewPos = self.playlistListControl.getViewPosition()

        self.fillPlaylist()

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

    @busy.dialog()
    def fillPlaylist(self):
        items = []
        idx = 1
        for pi in kodijsonrpc.rpc.PlayList.GetItems(
            playlistid=xbmc.PLAYLIST_MUSIC, properties=['title', 'artist', 'album', 'track', 'thumbnail', 'duration', 'playcount', 'comment', 'file']
        )['items']:
            mli = self.createListItem(pi, idx)
            if mli:
                mli.setProperty('index', str(idx))
                items.append(mli)
                idx += 1

        self.playlistListControl.reset()
        self.playlistListControl.addItems(items)

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
                self.setProperty('pq.hasnext', pq.allowSkipNext and '1' or '')
                self.setProperty('pq.hasprev', pq.allowSkipPrev and '1' or '')
                self.setProperty('pq.repeat', pq.isRepeat and '1' or '')
                self.setProperty('pq.shuffled', pq.isShuffled and '1' or '')
            else:
                self.setProperties(('pq.isRemote', 'pq.hasnext', 'pq.hasprev', 'pq.repeat', 'pq.shuffled'), '')
