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

    # Defaults for everything the shared playback callbacks touch. MusicPlayerWindow subclasses
    # this and runs those callbacks too, so each of these has to mean something on both screens.
    # They are class level rather than __init__ assignments as a belt and braces measure: the
    # player used to skip this class's __init__ outright - it called
    # kodigui.ControlledWindow.__init__ directly - and every attribute set only there was missing
    # on it, which is how updateFromTrack() came to die on _panelAlbum and leave the player with
    # no background panel. That __init__ chains properly now, but a callback can still arrive
    # before onFirstInit() has built anything, which is what these cover.

    # (parentRatingKey, Album) of the last album fetched for the background panel - see
    # _albumForPanel().
    _panelAlbum = None
    # What fillPlaylist() last put in the rows - see playlistSignature().
    _playlistSig = None
    # Only this window builds the queue rows; the player screen has no list to select in.
    playlistListControl = None
    # The remote play queue we hooked 'change' on, remembered so doClose() unhooks the queue it
    # actually hooked rather than whatever happens to be playing by then.
    _boundPlayQueue = None
    # Raised around a track change by onAudioStarting/onAudioStarted. MusicPlayerWindow.onAction
    # reads it to tell a stop the user asked for from one the file swap caused.
    ignoreStopCommands = False

    def __init__(self, *args, **kwargs):
        kodigui.ControlledWindow.__init__(self, *args, **kwargs)
        self.selectedOffset = 0
        self.duration = None
        self.track = None
        self.setDuration()
        self.exitCommand = None
        self.musicPlayerWinID = kwargs.get('winID')

    @property
    def playQueue(self):
        """The queue the transport acts on - whatever is playing right now.

        One accessor for both screens. MusicPlayerWindow used to read its own self.playlist (the
        queue it was handed when it opened) in its own copies of repeatButtonClicked, both skip
        handlers and updateProperties, while this class read the handler's: four near-identical
        pairs that had to be kept in step by hand, and were not - repeat-all shipped working on
        the queue screen and broken on the player because the fix landed on one copy only.

        The handler's is the better of the two anyway. playAudioPlaylist() installs the very
        object self.playlist holds, so the two agree once playback has started, and this one is
        still right when the player is reopened with no arguments at all
        (windowutils.showAudioPlayer), where self.playlist is None and the remote half of the
        transport row went dark.
        """
        return getattr(player.PLAYER.handler, 'playQueue', None)

    def bindPlayQueue(self):
        """Follow the queue's own change notifications, to keep the transport row current.

        Called once playback has started, never before: playAudioPlaylist() is what puts the queue
        on the handler, so binding any earlier hooks the previous session's queue instead.
        """
        pq = self.playQueue
        if pq is not None and pq.isRemote:
            pq.on('change', self.updateProperties)
            self._boundPlayQueue = pq

    def unbindPlayQueue(self):
        if self._boundPlayQueue is not None:
            self._boundPlayQueue.off('change', self.updateProperties)
            self._boundPlayQueue = None

    def doClose(self, **kwargs):
        player.PLAYER.off('av.started', self.onPlayBackStarted)
        # A no-op on the player screen, which never hooks this - SignalsMixin.off() checks the
        # callback is connected before disconnecting it.
        player.PLAYER.off('playlist.changed', self.playQueueCallback)
        self.unbindPlayQueue()
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
        self.bindPlayQueue()
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
            self.playQueue.setShuffle()
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
        # Move the rows onto the track that just started. Doing this only from onClick (where it
        # still is, for the shuffle rebuild) ran it before the skip had happened - PlayerControl
        # is queued, not immediate - so the rows stayed on the outgoing track and only caught up
        # on the click after. Nothing followed a track that changed on its own at all, so
        # wrapping from the last track to the first left the list sitting at the far end.
        self.selectPlayingItem()
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
        self.selectPlayingItem()

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

    @staticmethod
    def setKodiRepeat(mode):
        """Kodi's own repeat mode - 'off', 'one' or 'all'.

        Player.SetRepeat rather than PlayerControl(Repeat*): the builtin applies the change to
        PlaylistPlayer::GetCurrentPlaylist(), and Kodi sets that to TYPE_NONE whenever a skip runs
        off the end of a playlist (CPlayListPlayer::PlayNext's failure path calls Reset()). A
        repeat change made while it sits there is dropped without a word, so the queue could
        record repeat-all while Kodi had none - the button lit up and hasNext() promised a wrap,
        but nothing wrapped. Live, that showed as repeat-all working on the first album and not
        on later ones, with kodi all=False against pq repeat=True in the same log line.

        The JSON-RPC call resolves the playlist from the player id instead
        (PlayerOperations.cpp: GetPlaylist(GetPlayer(playerid))), so it always lands on the music
        playlist whatever Kodi currently considers current.
        """
        try:
            kodijsonrpc.rpc.Player.SetRepeat(playerid=0, repeat=mode)
        except Exception as e:
            util.DEBUG_LOG('Could not set Kodi repeat to {}: {}', mode, e)

    # off -> all -> one -> off, as the REPEAT comment in includes/music_player_buttons.xml.tpl
    # describes it and as the focused button's own caption promises.
    REPEAT_CYCLE = {'off': 'all', 'all': 'one', 'one': 'off'}

    def currentRepeatMode(self):
        """Which repeat mode the button is currently showing - 'one', 'all' or 'off'.

        Read from exactly the places the button's own visibility conditions read
        (includes/music_player_buttons.xml.tpl): Kodi's Playlist.IsRepeatOne first, then Kodi's
        Playlist.IsRepeat *or* the queue's own flag. Deciding this any other way is how the
        button came to lie about itself.

        Repeat lives in two places, and they can disagree. Kodi's belongs to its music playlist
        and outlives a playback session; the queue's flag is created False with every new play
        queue. Start an album, turn repeat-all on, then click a track somewhere else: Kodi still
        repeats, so the button still reads as repeat-all and its caption offers "Repeat one" -
        but the new queue's isRepeat is False. This used to branch on that flag alone, so the
        first click landed in the "turn repeat-all on" arm and set the state the screen was
        already showing. The click did nothing, visibly or audibly, and only the second one moved
        (live, 2026-09-21).
        """
        if xbmc.getCondVisibility('Playlist.IsRepeatOne'):
            return 'one'
        pq = self.playQueue
        if xbmc.getCondVisibility('Playlist.IsRepeat') or (pq is not None and pq.isRepeat):
            return 'all'
        return 'off'

    def repeatButtonClicked(self):
        mode = self.REPEAT_CYCLE[self.currentRepeatMode()]

        pq = self.playQueue
        if pq is not None and pq.isRemote:
            # Only repeat-all maps onto the queue's flag. Repeat-one stays Kodi's alone, because
            # PlayQueue.hasNext() short-circuits to True on isRepeatOne, and playerSkip() lifts
            # repeat-one for a deliberate skip precisely so it does not pin the queue.
            pq.setRepeat(mode == 'all')
            pq.refresh(force=True)

        # Kodi is told in every case, including the local one this used to hand a bare 'cycle'.
        # setRepeat() above only sets flags on the queue object (the value rides along on the
        # next request), and PMS's own repeat governs what it hands back when windowing - neither
        # makes Kodi loop the playlist it is actually playing, so repeat-all did nothing audible
        # and playback just stopped at the end (live, 2026-09-19). Naming the mode rather than
        # cycling also keeps Kodi on the mode the caption just promised, whatever it was on
        # before.
        self.setKodiRepeat(mode)

        # Next/previous depend on the repeat mode now (hasNext/hasPrev wrap when it is
        # repeat-all), and nothing else recomputes them until the next track change or queue
        # refresh - so the buttons sat on their old state after a toggle.
        self.updateProperties()

    def playerSkip(self, command):
        """PlayerControl(Next) / PlayerControl(Previous), stepping over repeat-one if it is on.

        Repeat-one is meant to loop a track that reaches its own end, not to pin the queue - but
        Kodi applies it to deliberate skips too. CPlayListPlayer::GetNextItemIdx() returns the
        current index unchanged in both directions while it is set (PlayListPlayer.cpp), so next
        and previous just restarted the playing track. Dropping the mode for the duration of the
        skip and restoring it straight after gets the queue movement people expect while leaving
        the loop-at-the-end behaviour alone.

        No wait flags: builtins are queued and run in the order they are posted, so the skip
        lands between the two repeat changes.
        """
        repeatOne = xbmc.getCondVisibility('Playlist.IsRepeatOne')
        if repeatOne:
            self.setKodiRepeat('off')

        xbmc.executebuiltin('PlayerControl({0})'.format(command))

        if repeatOne:
            self.setKodiRepeat('one')

    def skipPrevButtonClicked(self):
        pq = self.playQueue
        if not xbmc.getCondVisibility('MusicPlayer.HasPrevious') and pq and pq.isRemote:
            util.DEBUG_LOG('MusicPlayer: No previous in Kodi playlist - refreshing remote PQ')
            if not pq.refresh(force=True, wait=True):
                return

        # Sets script.plex.ignore_spinner, which is what stops Kodi's own DialogBusy fading in
        # over the file swap that PlayerControl() is about to start (skin.plextuary/xml/
        # DialogBusy.xml gates every one of its animations on that property being empty).
        # playlistListClicked() already does this before playselected(), and MusicPlayerWindow's
        # own copies of these two methods always have - without it the spinner blinked over the
        # middle of this window on every next/previous click, and nowhere else (live, 2026-09-19).
        self.onAudioStarting()
        self.playerSkip('Previous')

    def skipNextButtonClicked(self):
        pq = self.playQueue
        if not xbmc.getCondVisibility('MusicPlayer.HasNext') and pq and pq.isRemote:
            util.DEBUG_LOG('MusicPlayer: No next in Kodi playlist - refreshing remote PQ')
            if not pq.refresh(force=True, wait=True):
                return

        self.onAudioStarting()
        self.playerSkip('Next')

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
            # force: the section's start, even when it's the one showing under the player - Home
            # otherwise counted Music as already showing and left the Artist screen up.
            self.goHome(track.getLibrarySectionId(), force=True)

    def stopButtonClicked(self):
        xbmc.executebuiltin('Action(Back, {})'.format(self.musicPlayerWinID))
        util.MONITOR.waitForAbort(0.5)
        player.PLAYER.stopAndWait()
        self.exitCommand = "STOP"
        self.doClose()

    def selectPlayingItem(self):
        # "is None", not a truth test: ManagedControlList defines __len__ and no __bool__, so an
        # empty one is falsy. What we are asking is whether this window built a list at all.
        if self.playlistListControl is None:
            return

        for mli in reversed(self.playlistListControl):
            if xbmc.getCondVisibility('String.StartsWith(MusicPlayer.Comment,{0})'.format(mli.dataSource['comment'].split(':', 1)[0])):
                self.playlistListControl.selectItem(mli.pos())
                break

    def playQueueCallback(self, **kwargs):
        self.setProperty('pq.isshuffled', self.playQueue.isShuffled and '1' or '')

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
        # Nothing to fill on the player screen, which shares onClick's shuffle branch but has no
        # row list - the same guard selectPlayingItem() carries, for the same reason. "is None"
        # matters here: ManagedControlList is falsy while it is empty, which is precisely the
        # state the first fill starts from, so a truth test emptied the queue screen instead.
        if self.playlistListControl is None:
            return
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

    @staticmethod
    def skipAvailability(pq):
        """(previous, next) - whether each skip button has anywhere to go.

        Worked out from Kodi's playlist, not the play queue's own view of itself. Kodi is what
        performs the skip, on the playlist it holds, so it is the only thing that can say whether
        one is possible. PlayQueue.hasNext()/hasPrev() answer from selectedId against a windowed
        item list, and the two drift: logged live against a 20-track album, they reported
        False/False at position 1 and True/True at position 0, neither matching the playlist
        underneath. False/False is their tell for a selectedId matching nothing in the window, at
        which point both buttons go dark wherever the track actually sits.

        A windowed queue is the one thing Kodi cannot know about - its playlist holds only the
        window, and PMS has more on either side - so the queue is still asked about that.
        """
        pl = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)
        size = pl.size()
        pos = pl.getposition()
        if size <= 0 or pos < 0:
            return False, False

        wraps = xbmc.getCondVisibility('Playlist.IsRepeat') or bool(pq and pq.isWindowed())
        return (pos > 0 or wraps), (pos < size - 1 or wraps)

    def updateProperties(self, **kwargs):
        pq = self.playQueue
        if pq:
            if pq.isRemote:
                self.setProperty('pq.isRemote', '1')
                hasPrev, hasNext = self.skipAvailability(pq)
                self.setProperty('pq.hasnext', hasNext and '1' or '')
                self.setProperty('pq.hasprev', hasPrev and '1' or '')
                self.setProperty('pq.repeat', pq.isRepeat and '1' or '')
                self.setProperty('pq.shuffled', pq.isShuffled and '1' or '')
            else:
                self.setProperties(('pq.isRemote', 'pq.hasnext', 'pq.hasprev', 'pq.repeat', 'pq.shuffled'), '')
