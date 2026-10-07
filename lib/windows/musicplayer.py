from __future__ import absolute_import

from kodi_six import xbmcgui

from lib import player
from lib import util
from . import currentplaylist
from . import opener


class MusicPlayerWindow(currentplaylist.CurrentPlaylistWindow):
    xmlFile = 'script-plex-music_player.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    # Only the ids and measurements that actually differ from the queue screen's. The rest
    # (the transport buttons, the selection box, BAR_Y/BAR_BOTTOM) are inherited - they were
    # spelled out here as well, identically, which is the sort of copy that quietly goes stale.
    SEEK_IMAGE_ID = 200

    # The seekbar is 80% of the screen width, centred - see the SEEKBAR comment in
    # script-plex-music_player.xml.tpl, whose 192/1536 these must match.
    SEEK_IMAGE_WIDTH = 1536

    BAR_X = 192
    BAR_RIGHT = 1728

    def __init__(self, *args, **kwargs):
        # Chain, rather than jumping straight to kodigui.ControlledWindow as this used to. Going
        # round the base meant every attribute it sets was simply absent here, and the shared
        # callbacks below walked into them one at a time - see the class attribute block in
        # currentplaylist.py.
        currentplaylist.CurrentPlaylistWindow.__init__(self, *args, **kwargs)
        # The queue this window was opened with. Only play() and the initial bind need it; the
        # transport reads self.playQueue, which is whatever is playing.
        self.playlist = kwargs.get('playlist')
        self.track = kwargs.get('track')
        if self.track:
            # The base has already asked Kodi, which is still on the outgoing track (or nothing)
            # until play() runs - the track we were handed knows better.
            self.duration = self.track.duration.asInt()

    def onFirstInit(self):
        self.setupSeekbar()
        self.commonInit()
        self.play()
        # Both of these want playback already under way: play() is what hands self.playlist to
        # the handler, and until it has, self.playQueue is still the previous session's queue -
        # so binding or reading the transport state any earlier used the wrong one.
        self.bindPlayQueue()
        self.updateProperties()
        # self.track, not whatever is current: play() has only just started it, and
        # currentTrack() is still the one before until the handler catches up.
        self.updateFromTrack(self.track)
        self.setFocusId(406)

    def processCommand(self, command):
        if command == "STOP":
            self.doClose()
            return
        super(MusicPlayerWindow, self).processCommand(command)

    def onAction(self, action):
        if self.ignoreStopCommands and action in (xbmcgui.ACTION_PREVIOUS_MENU,
                                                  xbmcgui.ACTION_NAV_BACK):
            if not self.is_current_window:
                return
        elif not self.ignoreStopCommands:
            if not self.is_current_window and action != xbmcgui.ACTION_STOP:
                return
        try:
            if action == xbmcgui.ACTION_STOP:
                self.stopButtonClicked()
                return
        except:
            util.ERROR()

        super(MusicPlayerWindow, self).onAction(action)

    def onClick(self, controlID):
        if controlID == self.PLAYLIST_BUTTON_ID:
            self.showPlaylist()
        elif controlID == self.SEEK_BUTTON_ID:
            self.seekButtonClicked()
        elif controlID == self.SHUFFLE_REMOTE_BUTTON_ID:
            self.playQueue.setShuffle()
        elif controlID == self.REPEAT_BUTTON_ID:
            self.repeatButtonClicked()
        elif controlID == self.SKIP_PREV_BUTTON_ID:
            self.skipPrevButtonClicked()
        elif controlID == self.SKIP_NEXT_BUTTON_ID:
            self.skipNextButtonClicked()
        elif controlID == self.OPTIONS_BUTTON_ID:
            self.optionsButtonClicked((1240, 1060))
        elif controlID == self.STOP_BUTTON_ID:
            self.stopButtonClicked()

    def showPlaylist(self):
        self.processCommand(opener.handleOpen(currentplaylist.CurrentPlaylistWindow, winID=self._winID))

    def stopButtonClicked(self):
        player.PLAYER.stopAndWait(fade=True)
        self.doClose()

    def play(self):
        if not self.track:
            return

        # Left alone only when it's playing from the very queue this window was handed. Every
        # caller passing a track has just built a fresh queue (opener.open(), the album/artist
        # Play buttons, a track click that isn't from the playing container -
        # opener.trackClicked()), and that one restarts it: skipping it whenever the track was
        # playing at all kept Kodi on the old queue (Popular Tracks, say) with the album never
        # queued, while the new queue had already replaced it on the server.
        if util.trackIsPlaying(self.track) and self.playlist is player.PLAYER.playingAudioQueue():
            return

        self.onAudioStarting()

        fanart = None
        if self.playlist:
            fanart = self.playlist.get('composite') or self.playlist.defaultArt
        # There used to be an album= branch here (player.playAlbum()) for a track clicked on the
        # Album screen or in the library. Every one of those callers now arrives with a server play
        # queue as self.playlist, so the album is just another queue and this is the only path
        # left. The bare playAudio() below still covers a track with no queue at all - see
        # opener.trackClicked()'s fallback when the server won't give us one.
        if self.playlist:
            player.PLAYER.playAudioPlaylist(self.playlist, startpos=list(self.playlist.items()).index(self.track), fanart=fanart)
        else:
            player.PLAYER.playAudio(self.track)
