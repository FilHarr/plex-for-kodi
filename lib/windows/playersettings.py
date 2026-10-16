from __future__ import absolute_import

import plexnet
from kodi_six import xbmc
from kodi_six import xbmcgui

from lib import metadata
from lib import util
from lib.util import T
from lib.language_util import getNativeLanguages
from . import kodigui
from .dialog import showOptionsDialog
from .mixins.subtitledl import PlexSubtitleDownloadMixin


class VideoSettingsDialog(kodigui.BaseDialog, util.CronReceiver, PlexSubtitleDownloadMixin):
    xmlFile = 'script-plex-video_settings_dialog.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    SETTINGS_LIST_ID = 100
    FRAME_GROUP_ID = 200
    FRAME_BACKDROP_ID = 201
    FRAME_SHADOW_ID = 202
    FRAME_X = 660  # centres the 600-wide list
    ROW_HEIGHT = util.vscalei(64)  # the template's row pitch (58 cards, 6 apart)
    MAX_ROWS = 10

    def __init__(self, *args, **kwargs):
        kodigui.BaseDialog.__init__(self, *args, **kwargs)
        PlexSubtitleDownloadMixin.__init__(self, *args, **kwargs)
        self.video = kwargs.get('video')
        self.viaOSD = kwargs.get('via_osd')
        self.nonPlayback = kwargs.get('non_playback')
        self.parent = kwargs.get('parent')
        self.sessionID = None
        if self.parent and self.parent.player:
            self.sessionID = self.parent.player.handler.sessionID
        self.roundRobin = kwargs.get('round_robin', True)
        self.lastSelectedItem = 0
        self.shuffleAsked = None  # the shuffle state last asked for, until the play queue has it

        if not self.video.mediaChoice:
            playerObject = plexnet.plexplayer.PlexPlayer(self.video)
            playerObject.build()

    def onFirstInit(self):
        self.settingsList = kodigui.ManagedControlList(self, self.SETTINGS_LIST_ID, 6)
        self.setProperty('heading', T(32343, 'Settings'))
        if self.viaOSD:
            self.setProperty('via.OSD', '1')
        self.showSettings(True)
        util.CRON.registerReceiver(self)

    def onAction(self, action):
        try:
            if not xbmc.getCondVisibility('Player.HasMedia') and not self.nonPlayback:
                self.doClose()
                return
        except:
            util.ERROR()

        if self.roundRobin and action in (xbmcgui.ACTION_MOVE_UP, xbmcgui.ACTION_MOVE_DOWN) and \
                self.getFocusId() == self.SETTINGS_LIST_ID:
            to_pos = None
            last_index = self.settingsList.size() - 1
            if action == xbmcgui.ACTION_MOVE_UP and self.lastSelectedItem == 0 and self.settingsList.topHasFocus():
                to_pos = last_index

            elif action == xbmcgui.ACTION_MOVE_DOWN and self.lastSelectedItem == last_index \
                    and self.settingsList.bottomHasFocus():
                to_pos = 0

            if to_pos is not None:
                self.settingsList.setSelectedItemByPos(to_pos)
                self.lastSelectedItem = to_pos
                return

            self.lastSelectedItem = self.settingsList.control.getSelectedPosition()

        kodigui.BaseDialog.onAction(self, action)

    def onClick(self, controlID):
        if controlID == self.SETTINGS_LIST_ID:
            self.editSetting()

    def onClosed(self):
        util.CRON.cancelReceiver(self)

    def tick(self):
        if self.nonPlayback:
            return

        if not xbmc.getCondVisibility('Player.HasMedia'):
            self.doClose()
            return

    @property
    def qualityOverride(self):
        quality_type = self.video.getQualityType()
        return self.video.settings.getPrefOverride(quality_type, self.video.settings.getQualityIndex(quality_type))

    def showSettings(self, init=False):
        video = self.video
        override = self.qualityOverride
        if override is not None and override < 16:
            current = T((32001, 32017, 32002, 32016, 32003, 32004, 32005, 32015, 32006, 32007, 32008, 32009, 32010,
                         32011)[16 - override])
        else:
            current = u'{0} {1} ({2})'.format(
                plexnet.util.bitrateToString(video.mediaChoice.media.bitrate.asInt() * 1000),
                video.mediaChoice.media.getVideoResolutionString(),
                video.mediaChoice.media.title or T(32001, 'Original')
            )

        audio, subtitle = self.getAudioAndSubtitleInfo()

        options = []
        # Video entry, above Audio - only when there's an actual choice to make, same gating the
        # episode button row's own "media" button used to have before it was replaced by this
        # entry (episodes.py, now removed) - not always offering a single-item picker.
        accessibleMedia = [m for m in video.media() if m.isAccessible()]
        if len(accessibleMedia) > 1:
            options.append(('video', T(32053, 'Video'),
                            video.mediaChoice and video.mediaChoice.media.versionString() or ''))

        options += [
            ('audio', T(32395, 'Audio'), audio),
            ('subs', T(32396, 'Subtitles'), subtitle),
            ('quality', T(32397, 'Quality'), u'{0}'.format(current)),
        ]

        # Repeat and Shuffle, the video player's (the OSD's buttons until they moved here): only from its OSD
        if self.viaOSD and self.parent:
            options.append(('repeat', T(32934, 'Repeat'), self.REPEAT_LABELS()[self.parent.repeatMode()]))
            if self.parent.canShuffle():
                shuffled = self.parent.isShuffled()
                if self.shuffleAsked is not None and self.shuffleAsked != shuffled:
                    shuffled = self.shuffleAsked
                else:
                    self.shuffleAsked = None
                options.append(('shuffle', T(32935, 'Shuffle'), shuffled and T(35181, 'On') or T(32481, 'Off')))

        # Kodi's own settings windows, one row: its picker lists them (kodiSettingsOptions())
        if not self.nonPlayback:
            options.append(('kodi', T(35182, 'Kodi settings'), ''))

        if self.viaOSD:
            if self.parent.getProperty("show.PPI") or self.parent._playerDebugActive or self.parent._playerNativePPIActive:
                options += [
                    ('stream_info', T(32483, 'Hide Stream Info'), ''),
                ]
            else:
                options += [
                    ('stream_info', T(32484, 'Show Stream Info'), ''),
                ]

        items = []
        for o in options:
            item = kodigui.ManagedListItem(o[1], o[2], data_source=o[0])
            items.append(item)
        if init:
            self.settingsList.reset()
            self.settingsList.addItems(items)
        else:
            self.settingsList.replaceItems(items)

        self.fitFrame(len(items))
        self.setFocusId(self.SETTINGS_LIST_ID)

    def fitFrame(self, rows):
        """
        The card frame (the template's group 200) fitted to the settings: the list as many rows high as there are, up
        to 10 (then it scrolls); the backdrop the list plus its heading's 66 and 17 below
        (the last card's 3 and these: 20 under it, as at the sides); the shadow 40
        past that each way; all centred on the screen.
        """
        listHeight = min(rows, self.MAX_ROWS) * self.ROW_HEIGHT
        header = util.vscalei(66)
        self.settingsList.setHeight(listHeight)
        self.getControl(self.FRAME_BACKDROP_ID).setHeight(listHeight + header + util.vscalei(17))
        self.getControl(self.FRAME_SHADOW_ID).setHeight(listHeight + header + util.vscalei(97))
        top = max(0, (self.height - listHeight - header - util.vscalei(17)) // 2)
        self.getControl(self.FRAME_GROUP_ID).setPosition(self.FRAME_X, top + header)

    @staticmethod
    def kodiSettingsOptions():
        """The Kodi settings row's picker: (what to run, its name) for each of Kodi's settings windows there is."""
        options = [
            ('ActivateWindow(OSDVideoSettings)', T(35183, 'Video settings')),
            ('ActivateWindow(OSDAudioSettings)', T(35184, 'Audio settings')),
        ]
        if util.KODI_VERSION_MAJOR >= 18:
            options.append(('ActivateWindow(OSDSubtitleSettings)', T(35185, 'Subtitle settings')))
            if xbmc.getCondVisibility('Player.HasResolutions'):
                options.append(('Action(PlayerResolutionSelect)', T(35186, 'Resolution settings')))
        if util.KODI_VERSION_MAJOR >= 20 and xbmc.getCondVisibility('System.HasCMS'):
            options.append(('ActivateWindow(osdcmssettings)', T(35187, 'Colour settings')))
        return options

    @staticmethod
    def REPEAT_LABELS():
        return {'off': T(32481, 'Off'), 'all': T(32345, 'All'), 'one': T(35180, 'One')}

    def getAudioAndSubtitleInfo(self):
        sas = self.video.selectedAudioStream()
        if sas:
            if len(self.video.audioStreams) > 1:
                audio = sas and u'{0} \u2022 {1} {2}'.format(sas.getTitle(metadata.apiTranslate),
                                                             len(self.video.audioStreams) - 1, T(32307, 'More')) \
                        or T(32309, 'None')
            else:
                audio = sas and sas.getTitle(metadata.apiTranslate) or T(32309, 'None')
        else:
            audio = T(32309, 'None')

        sss = self.video.selectedSubtitleStream(
            forced_subtitles_override=util.getSetting("forced_subtitles_override") and plexnet.util.ACCOUNT.subtitlesForced == 0,
            deselect_subtitles=util.getSetting("disable_subtitle_languages")
        )

        if sss:
            if len(self.video.subtitleStreams) > 1:
                subtitle = u'{0} \u2022 {1} {2}'.format(sss.getTitle(metadata.apiTranslate), len(self.video.subtitleStreams) - 1, T(32307, 'More'))
            else:
                subtitle = sss.getTitle(metadata.apiTranslate)
        elif self.video.subtitleStreams:
            subtitle = u'{0} \u2022 {1} {2}'.format(T(32481, 'Off'), len(self.video.subtitleStreams), T(32308, 'Available'))
        else:
            subtitle = T(32309, 'None')

        return audio, subtitle

    def editSetting(self):
        mli = self.settingsList.getSelectedItem()
        if not mli:
            return

        result = mli.dataSource
        # every picker from here: the video player's (Settings from its OSD) tall at the right
        # (dialog.SideSelectDialog), pre-play's centred
        side = bool(self.viaOSD)

        if result == 'video':
            showVideoDialog(self.video, non_playback=self.nonPlayback, side=side)
        elif result == 'audio':
            showAudioDialog(self.video, non_playback=self.nonPlayback, session_id=self.sessionID, side=side)
        elif result == 'subs':
            def download():
                # pre-play's: Plex's search (Kodi's needs a video playing)
                downloaded = self.downloadPlexSubtitles(self.video, non_playback=self.nonPlayback, side=side)
                if downloaded:
                    self.video.selectStream(downloaded, from_session=not self.nonPlayback, sync_to_server=False)
                    self.video.manually_selected_sub_stream = downloaded.id

            # The video player's (self.parent, its dialog): its own download, the Subtitles button's - Plex or
            # Kodi as subtitle_download_from says, with its fallback - and Subtitle Delay and auto-sync.
            player = self.viaOSD and self.parent or None
            if player:
                download = player.downloadSubtitles
            choice = showSubtitlesDialog(self.video, non_playback=self.nonPlayback, session_id=self.sessionID,
                                         side=side, download=download, player=player)
            if choice is SUBTITLE_DELAY:
                # Kodi's slider, over this (which hides while it's up)
                xbmc.executebuiltin('Action(SubtitleDelay)')
            elif choice is SUBTITLE_AUTO_SYNC:
                player.toggleSubtitleAutoSync(hide_osd=False)
        elif result == 'quality':
            # the current one, as showSettings() labels it: a cap below 16, else Original (16)
            override = self.qualityOverride
            current = override if override is not None and override < 16 else 16
            showQualityDialog(self.video, non_playback=self.nonPlayback, current=current, side=side)
        elif result == 'repeat':
            labels = self.REPEAT_LABELS()
            modes = ('off', 'all', 'one')
            choice = showOptionsDialog(T(32934, 'Repeat'), [(m, labels[m]) for m in modes],
                                       selected_idx=modes.index(self.parent.repeatMode()), side=side)
            if choice is not None:
                self.parent.setRepeatMode(choice)
                if not self.parent.handler.playlist:
                    # Kodi's own repeat: let the builtin land before the row reads it back
                    xbmc.sleep(100)
        elif result == 'shuffle':
            self.shuffleAsked = self.parent.toggleShuffle()
        elif result == 'kodi':
            choice = showOptionsDialog(T(35182, 'Kodi settings'), self.kodiSettingsOptions(), side=side)
            if choice is not None:
                xbmc.executebuiltin(choice)
        elif result == "stream_info":
            if self.parent:
                if self.parent.getProperty("show.PPI"):
                    self.parent.hidePPIDialog()
                else:
                    #xbmc.executebuiltin('Action(PlayerProcessInfo)')
                    if self.parent._playerDebugActive:
                        xbmc.executebuiltin('Action(playerdebug)')
                        self.parent._playerDebugActive = False
                    elif self.parent._playerNativePPIActive:
                        xbmc.executebuiltin('Action(playerprocessinfo)')
                        self.parent._playerNativePPIActive = False
                    else:
                        self.parent.showPPIDialog()
            self.doClose()
            return

        self.showSettings()


def showVideoDialog(video, non_playback=False, side=False):
    """
    Same version-choosing logic the episode button row's own "media" button used to have
    (mediaButtonClicked() - episodes.py, now removed in favor of this entry).
    showOptionsDialog, not dropdown.showDropdown, for the same reason: it's the mechanism Audio/
    Subtitles/Quality below already use successfully from within this same dialog - dropdown's own
    dialog-over-dialog behavior isn't (every existing dropdown.showDropdown() caller opens it from
    a full window, not from on top of another dialog like this one).
    """
    options = []
    idx = None
    for i, media in enumerate(video.media()):
        if video.mediaChoice and media.id == video.mediaChoice.media.id:
            idx = i
        options.append((media, media.versionString()))

    # non_playback must be threaded through: SelectDialog.onAction() (dialog.py) closes itself on
    # every action - including plain navigation - whenever Player.HasMedia is false and
    # non_playback wasn't passed (live-confirmed - the episode screen isn't actually playing
    # anything, so this closed spontaneously without it). Same param Audio/Subtitles above already
    # forward from self.nonPlayback - this one was missing it.
    choice = showOptionsDialog(T(32053, 'Video'), options, non_playback=non_playback, selected_idx=idx, side=side)
    if choice is None:
        return

    for media in video.media():
        media.set('selected', '')

    video.setMediaChoice(choice)
    choice.set('selected', 1)
    # Same persisted media_version preference the button row's own version picker used to set
    # directly (mediaButtonClicked() - episodes.py and preplay.py, both now removed in favor of
    # this single Settings entry, 2026-09-04 for preplay.py's own copy) - missing this wouldn't
    # break the immediate switch, just the choice being remembered/synced the same way.
    plexnet.util.INTERFACE.playbackManager(video, key="media_version", value=choice.id)
    video.clearCache()


def showAudioDialog(video, non_playback=False, session_id=None, side=False):
    options = []
    idx = None
    for i, s in enumerate(video.audioStreams):
        if s.isSelected():
            idx = i
        options.append((s, (s.getTitle(metadata.apiTranslate), s.title)))
    choice = showOptionsDialog(T(32395, 'Audio'), options, non_playback=non_playback, selected_idx=idx,
                               trim=False, side=side)
    if choice is None:
        return

    video.selectStream(choice, from_session=not non_playback, session_id=session_id)
    video.clearCache()


# showSubtitlesDialog()'s answers for its own options: Download subtitles, and the video player's Subtitle Delay and
# auto-sync
DOWNLOAD_SUBTITLES = object()
SUBTITLE_DELAY = object()
SUBTITLE_AUTO_SYNC = object()
SUBTITLE_ACTIONS = (DOWNLOAD_SUBTITLES, SUBTITLE_DELAY, SUBTITLE_AUTO_SYNC)


def subtitleOptions(video, with_download=False, player=None):
    """
    The Subtitles picker's options and the current one's index: Off, the streams, Download subtitles (with_download),
    and with the video player's dialog (player) Subtitle Delay when a subtitle's on and auto-sync when that one can.
    """
    none_label = T(32481, 'Off') if video.subtitleStreams else T(32309, 'None')
    options = [(plexnet.plexstream.NoneStream(), none_label)]
    idx = 0
    sss = video.selectedSubtitleStream(
        forced_subtitles_override=util.getSetting("forced_subtitles_override") and plexnet.util.ACCOUNT.subtitlesForced == 0,
        deselect_subtitles=getNativeLanguages(util.getSetting("disable_subtitle_languages") or [])
    )
    for i, s in enumerate(video.subtitleStreams):
        if s == sss:
            idx = i + 1
        options.append((s, s.getTitle(metadata.apiTranslate)))

    if with_download:
        options.append((DOWNLOAD_SUBTITLES, T(33703, "Download subtitles")))

    if player is not None and video.hasSubtitles and video.hasSubtitle:
        options.append((SUBTITLE_DELAY, T(32406, 'Subtitle Delay')))
        playing = video.selectedSubtitleStream()
        if xbmc.getCondVisibility('VideoPlayer.SubtitlesEnabled') and playing and playing.canAutoSync.asBool():
            if playing.force_auto_sync is None:
                playing.should_auto_sync = video.playbackSettings.auto_sync
            options.append((SUBTITLE_AUTO_SYNC, playing.should_auto_sync and T(33658, 'Disable Auto-Sync') or
                            T(33657, 'Enable Auto-Sync')))

    return options, idx


def showSubtitlesDialog(video, non_playback=False, session_id=None, with_download=False, side=False, download=None,
                        player=None):
    """
    The subtitle streams to choose from (subtitleOptions()), the current one ticked; choosing one selects it. side:
    the video player's tall picker at the right (dialog.SideSelectDialog).
    Download subtitles: with download (a callable), runs it with the picker left open beneath whatever it opens,
    and comes back to the picker, a downloaded subtitle among its streams; with_download alone returns
    DOWNLOAD_SUBTITLES for the caller to run instead. player (the video player's dialog) adds Subtitle Delay and
    auto-sync where they apply, returning SUBTITLE_DELAY or SUBTITLE_AUTO_SYNC when chosen.
    """
    withDownload = with_download or download is not None

    def onChoice(choice):
        if choice is DOWNLOAD_SUBTITLES and download is not None:
            download()
            return subtitleOptions(video, withDownload, player)
        return None

    options, idx = subtitleOptions(video, withDownload, player)
    choice = showOptionsDialog(T(32396, 'Subtitle'), options, non_playback=non_playback, selected_idx=idx, side=side,
                               on_choice=onChoice)
    if choice is None:
        return
    if any(choice is action for action in SUBTITLE_ACTIONS):
        return choice

    video.selectStream(choice, from_session=not non_playback, session_id=session_id)
    video.clearCache()
    video.manually_selected_sub_stream = choice.id


def showQualityDialog(video, non_playback=False, current=None, side=False):
    """current: the quality in force (16 Original, else a cap's 15-3), focused and ticked when it's offered."""
    options = []
    video_bitrate = video.mediaChoice.media.bitrate.asInt()

    if video.settings.getPreference('clamp_video_bitrates', True):
        bitrates = list(reversed(video.settings.getGlobal("transcodeVideoBitrates")))[1:]
        for (i, l) in enumerate((32017, 32002, 32016, 32003, 32004, 32005, 32015, 32006, 32007, 32008, 32009, 32010,
                                 32011)):
            br_in_list = int(bitrates[i])
            if br_in_list > video_bitrate:
                continue

            options.append((15 - i, T(l)))
    else:
        options = [(15 - i, T(l)) for (i, l) in enumerate((32017, 32002, 32016, 32003, 32004, 32005, 32015, 32006,
                                                           32007, 32008, 32009, 32010, 32011))]


    options.insert(0, (16, u'{0} {1} ({2})'.format(
                plexnet.util.bitrateToString(video_bitrate * 1000),
                video.mediaChoice.media.getVideoResolutionString(),
                T(32001, 'Original')
            )))

    # found by value: a cap above the file's bitrate isn't offered (clamp_video_bitrates), so positions don't line up
    values = [value for value, _ in options]
    selected_idx = values.index(current) if current in values else None
    choice = showOptionsDialog('Quality', options, non_playback=non_playback, selected_idx=selected_idx, side=side)
    if choice is None:
        return

    video.settings.setPrefOverride('local_quality2', choice)
    video.settings.setPrefOverride('remote_quality2', choice)
    video.settings.setPrefOverride('online_quality2', choice)


class SideVideoSettingsDialog(VideoSettingsDialog):
    """
    The video player's Settings dialog (script-plex-video_settings_dialog_side.xml.tpl): in the option pickers'
    tall frame at the right (dialog.SideSelectDialog's) - 876 high from 103, its right edge 10 from the screen's,
    13 rows of 61 (the template's 793, then it scrolls) - so each of its pickers opens exactly over it.
    """
    xmlFile = 'script-plex-video_settings_dialog_side.xml'
    ROW_HEIGHT = util.vscalei(61)  # the template's row pitch (55 cards, 6 apart)
    FRAME_X = 1290
    FRAME_TOP = 103
    FRAME_HEIGHT = 876
    LIST_HEIGHT = 793

    def fitFrame(self, rows):
        header = util.vscalei(66)
        height = util.vscalei(self.FRAME_HEIGHT)
        self.settingsList.setHeight(min(rows * self.ROW_HEIGHT, util.vscalei(self.LIST_HEIGHT)))
        self.getControl(self.FRAME_BACKDROP_ID).setHeight(height)
        self.getControl(self.FRAME_SHADOW_ID).setHeight(height + util.vscalei(80))
        self.getControl(self.FRAME_GROUP_ID).setPosition(self.FRAME_X, util.vscalei(self.FRAME_TOP) + header)


def showDialog(video, non_playback=False, via_osd=False, parent=None):
    # the video player's (from its OSD) tall at the right, with its pickers; pre-play's centred
    w = (via_osd and SideVideoSettingsDialog or VideoSettingsDialog).open(
        video=video, non_playback=non_playback, via_osd=via_osd, parent=parent)
    ref = util.windowRef(w)
    del w
    util.collectIfAlive(ref)
