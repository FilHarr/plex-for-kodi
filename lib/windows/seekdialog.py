from __future__ import absolute_import

import re
import threading
import time
import weakref
from collections import OrderedDict

from kodi_six import xbmc
from kodi_six import xbmcgui

from plexnet import plexapp
from plexnet.util import AttributeDict
from plexnet.exceptions import ServerNotOwned, NotFound
from plexnet.videosession import VideoSessionInfo, ATTRIBUTE_TYPES as SESSION_ATTRIBUTE_TYPES
from six.moves import range

import lib.cache
from lib import util
from lib.kodijsonrpc import builtin
from lib.util import T
from lib.language_util import getNativeLanguages
from . import busy
from . import dropdown
from . import kodigui
from . import windowutils
from . import playersettings
from . import optionsdialog
from . import previews
from . import seek_scan
from .mixins.spoilers import SpoilersMixin
from .mixins.subtitledl import PlexSubtitleDownloadMixin

KEY_MOVE_SET = frozenset(
    (
        xbmcgui.ACTION_MOVE_LEFT,
        xbmcgui.ACTION_MOVE_RIGHT,
        xbmcgui.ACTION_MOVE_UP,
        xbmcgui.ACTION_MOVE_DOWN
    )
)

KEY_STEP_SEEK_SET = frozenset(
    (
        xbmcgui.ACTION_MOVE_LEFT,
        xbmcgui.ACTION_MOVE_RIGHT,
        xbmcgui.ACTION_STEP_FORWARD,
        xbmcgui.ACTION_STEP_BACK
    )
)

MARKERS = OrderedDict([
    ("intro", {
        "marker": None,
        "name": T(32495, 'Skip intro'),
        "autoSkipName": T(32800, 'Skipping intro'),
        "overrideStartOff": None,
        "countdown": None,
        "countdown_initial": None,
        "skipped": False,
        "hidden": False,

        # attrs
        "markerAutoSkip": "autoSkipIntro",
        "markerAutoSkipped": False,
        "markerAutoSkipShownTimer": "_introSkipShownStarted",
        "markerSkipBtnTimeout": "skipIntroButtonTimeout",
    }),
    ("credits", {
        "marker": None,
        "name": T(32496, 'Skip credits'),
        "autoSkipName": T(32801, 'Skipping credits'),
        "overrideStartOff": None,
        "countdown": None,
        "countdown_initial": None,
        "skipped": False,
        "hidden": False,

        "markerAutoSkip": "autoSkipCredits",
        "markerAutoSkipped": False,
        "markerAutoSkipShownTimer": "_creditsSkipShownStarted",
        "markerSkipBtnTimeout": "skipCreditsButtonTimeout"
    })
])


class Marker(AttributeDict):
    pass


FINAL_MARKER_NEGOFF = 3000
MARKER_SHOW_NEGOFF = 3000
MARKER_OFF = 500
MARKER_CHAPTER_OVERLAP_THRES = 30000  # 30 seconds
MARKER_END_JUMP_OFF = 1000


class SeekDialog(kodigui.BaseDialog, windowutils.GoHomeMixin, PlexSubtitleDownloadMixin, SpoilersMixin):
    """
    fixme: This is a convoluted mess.
    """

    xmlFile = 'script-plex-seek_dialog.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    MAIN_BUTTON_ID = 100
    SEEK_IMAGE_ID = 200
    POSITION_IMAGE_ID = 201
    SELECTION_INDICATOR = 202  # the seek marker
    CACHE_IMAGE_ID = 206
    BIF_IMAGE_ID = 300
    BIF_WIDTH = 304  # the preview thumbnail's frame (the template's group 300): the card rows' 300 art, 2 each side
    # The seekbar is the music player's: 80% of the screen, centred - see the SEEKBAR comment in
    # script-plex-seek_dialog.xml.tpl, whose 232/1496 these and BAR_X/BAR_RIGHT must match.
    SEEK_IMAGE_WIDTH = 1496
    # the played and buffer fills' rounded end caps, 4 wide (the template's SEEKBAR)
    POSITION_CAP_ID = 208
    CACHE_CAP_ID = 210
    BAR_CAP = 4
    # the size of the file chapters' pictures from the server (300x168 cards in the template's chapter row)
    CHAPTER_THUMB_DIM = util.scaleResolution(300, 168)
    # the card rows' 200ms fade (includes/osd_card_row.xml.tpl), plus a margin
    ROW_FADE_OUT = 0.3

    SETTINGS_BUTTON_ID = 403
    OPTIONS_BUTTON_ID = 411
    SUBTITLE_BUTTON_ID = 412
    VS10_BUTTON_ID = 413

    BIG_SEEK_GROUP_ID = 500
    BIG_SEEK_LIST_ID = 501
    # the play queue's card row, below the chapters' (includes/osd_card_row.xml.tpl)
    QUEUE_GROUP_ID = 510
    QUEUE_LIST_ID = 511
    ROW_LIST_IDS = (BIG_SEEK_LIST_ID, QUEUE_LIST_ID)

    SKIP_MARKER_BUTTON_ID = 791
    # the top of the OSD: up from these closes it (onAction())
    OSD_TOP_IDS = (SETTINGS_BUTTON_ID, SUBTITLE_BUTTON_ID, VS10_BUTTON_ID, SKIP_MARKER_BUTTON_ID)
    NO_OSD_BUTTON_ID = 800

    BAR_X = 232
    # the bar's mouse area, the template's timeline hitrect: 980-1024 round the 995-1003 bar, short of the buttons
    BAR_Y = 980
    BAR_RIGHT = 1728
    BAR_BOTTOM = 1024

    NAVBAR_BTN_SIZE = 60
    # The buttons' dropdowns (dropdown.CardDropdownDialog, its list 600 wide with the backdrop 20 past it each
    # side): right-aligned with the button row's last pill (1840), so the list starts at 1840 - 20 - 600; the
    # list's foot at 892, its backdrop's 17 lower at 909, 10 above the button pills (919).
    DROPDOWN_X = 1220
    DROPDOWN_BOTTOM = 892

    HIDE_DELAY = 4  # This uses the Cron tick so is +/- 1 second accurate
    OSD_HIDE_ANIMATION_DURATION = 0.2
    OSD_HIDE_ACTION_THRESHOLD = 0.5
    FIRST_SEEK_STEP_DELAY = 1.0  # the least a seek's first step waits to be applied, auto-seek on (delayedSeek())
    # The least auto-seek delay, as the setting's slider has it. 0 made a seek on every press, a jerky mess; it and anything
    # else under this saved before count as this.
    MIN_AUTO_SEEK_DELAY = 0.5
    # Hold left/right to scan (startScan()): how often a scan moves the seek point; and, while its thumbnails come
    # from the server (previewImage()), one per SCAN_BIF_STEP of video, changed at most every SCAN_BIF_INTERVAL - each
    # new one's a fetch. Local ones change on every move.
    SCAN_TICK = 0.1
    SCAN_BIF_STEP = 2000
    SCAN_BIF_INTERVAL = 0.4
    SCAN_KEYS = {
        xbmcgui.ACTION_MOVE_RIGHT: seek_scan.FORWARD,
        xbmcgui.ACTION_STEP_FORWARD: seek_scan.FORWARD,
        xbmcgui.ACTION_MOVE_LEFT: seek_scan.BACK,
        xbmcgui.ACTION_STEP_BACK: seek_scan.BACK,
    }
    # a remote's FF/RW start a scan, or step its speed, in place of Kodi's own fast-forward (scanAction())
    SCAN_MEDIA_KEYS = {
        xbmcgui.ACTION_PLAYER_FORWARD: seek_scan.FORWARD,
        xbmcgui.ACTION_PLAYER_REWIND: seek_scan.BACK,
    }
    SKIP_STEPS = {"negative": [-10000], "positive": [30000]}

    def __init__(self, *args, **kwargs):
        super(SeekDialog, self).__init__(*args, **kwargs)
        PlexSubtitleDownloadMixin.__init__(self, *args, **kwargs)
        SpoilersMixin.__init__(self, *args, **kwargs)

        # fixme: heyo, there's a lot of disorder in here.
        self.handler = kwargs.get('handler')
        self.initialVideoSettings = {}
        self.initialAudioStream = None
        self.initialSubtitleStream = None
        self.bifURL = None
        self.baseURL = None
        self.hasBif = bool(self.bifURL)
        self.baseOffset = 0
        self._duration = 0
        self.offset = 0
        self.playbackTime = 0
        self.selectedOffset = 0
        self.bigSeekChanged = False  # attention, with chapters this can become an integer for the True state
        self._rowPos = {}  # card row list id -> the position syncRows() last selected
        self._rowLeftAt = {}  # card row list id -> when focus last left it (syncRows() waits out its fade)
        self._queueRowStale = True  # the play queue row needs (re)building - refreshQueueRow()
        self._queuePlayingPos = 0  # the play queue row's position of the playing item
        self._rowHint = None  # the rows.hint text last set (updateRowHint())
        self._barCaps = {}  # SEEKBAR fill -> its rounded end cap (setBarPercent())
        self._playPauseInputAt = None  # when play/pause was last pressed (onPlayBackResumed() closes the OSD on it)
        self._focusArrived = None  # the control onFocus() last moved to, until the next action (onAction())
        # Playback paused for seeking (seekByOffset()): None, or 'seeking' (in seek mode), 'trickplay' (as 'seeking',
        # but Kodi's FF/RW speed being undone first - its resume to 1x isn't one, endTrickPlay()), 'applying' (the
        # seek's been made; the handler resumes once it lands) or 'resuming' (abandoned, play sent) - with when it got
        # there
        self._seekPaused = None
        self._seekPausedAt = 0
        # Hold left/right to scan (video_hold_to_scan, docs/hold-to-fast-forward.md): the hold detector (also telling
        # a scan's taps from a held key's repeats), and the scan while one runs (startScan()), which its thread moves on
        # (_scanLoop()) until it's applied or cancelled
        self._holdDetector = seek_scan.HoldDetector()
        self._scan = None
        self._scanLock = threading.Lock()
        self._scanBifUrl = None
        self._scanBifAt = 0
        # this item's preview index download has been started (startPreviews(); previews.store has it)
        self._previewsStarted = False
        # spoilers, for the item playing (spoilerHiding()): no moving preview and a placeholder on every chapter card;
        # the episode's title, and file chapters' names as "Chapter N"
        self.hidePreviews = False
        self.hideTitles = False
        self.title = ''
        self.title2 = ''
        self.fromSeek = 0
        self.initialized = False
        self.timeout = None
        self.autoSeekTimeout = None
        self.hasDialog = False
        self.lastFocusID = None
        self.previousFocusID = None
        self.showChapters = False
        self._seeking = False
        self._applyingSeek = False
        self._seekingWithoutOSD = False
        self._delayedSeekThread = None
        self._delayedSeekTimeout = 0
        self._osdHideAnimationTimeout = 0
        self._hideDelay = util.addonSettings.osdHideDelay if util.SKIN_PLEXTUARY else 4
        self._autoSeekDelay = util.addonSettings.autoSeek and             max(util.addonSettings.autoSeekDelay, self.MIN_AUTO_SEEK_DELAY) or 0
        self._atSkipStep = -1
        self._lastSkipDirection = None
        self._forcedLastSkipAmount = None
        self._navigatedViaMarkerOrChapter = False
        self.lastTimelineResponse = None
        self._terminated = False
        self._ignoreInput = False
        self._ignoreTick = False
        self._abortBufferWait = False
        self._playerDebugActive = False
        self._playerNativePPIActive = False
        self.no_spoilers = util.getSetting('no_episode_spoilers4')
        self.no_time_no_osd_spoilers = util.getSetting('no_osd_time_spoilers')
        self.clientLikePlex = util.getSetting('player_official')
        self.fastPauseResume = self.clientLikePlex and util.getUserSetting('fast_pause_resume', []) or []

        self.waitingForBuffer = False
        self.lastSubtitleNavAction = "forward"
        self._vs10Shown = False  # the VS10 button's in the row, right of Subtitles (onFirstInit())
        self.ldTimer = True #util.advancedSettings.lowDriftTimer
        self.timeKeeper = None
        self.timeKeeperTime = None
        self.idleTime = None
        self.stopPlaybackOnIdle = util.getSetting('player_stop_on_idle')
        self.resumeSeekBehind = util.getSetting('resume_seek_behind')
        self.resumeSeekBehindPause = util.getSetting('resume_seek_behind_pause')
        self.resumeSeekBehindAfter = util.getSetting('resume_seek_behind_after') / 1000.0
        self.resumeSeekBehindOnlyDP = util.getSetting('resume_seek_behind_onlydp')
        self.useAlternateSeek = util.getSetting('use_alternate_seek2')
        self.holdToScan = util.getSetting('video_hold_to_scan')
        self.pausedAt = None
        self.isDirectPlay = True
        self.isTranscoded = False

        # optimize
        self._enableMarkerSkip = plexapp.ACCOUNT.hasPlexPass()
        self.markers = None
        self.chapters = None
        self._introSkipShownStarted = None
        self._creditsSkipShownStarted = None
        self._currentMarker = None
        self.skipSteps = self.SKIP_STEPS
        self.useAutoSeek = util.addonSettings.autoSeek

        # this is duplicated in onFirstInit; we need to do this to get the early player skip right, as we might be
        # an initialized instance already, but not yet a window, but the player needs to access these values
        button_settings = util.getUserSetting('player_show_buttons',
                                              ['subtitle_downloads', 'skip_intro', 'skip_credits'])
        self.showSkipIntro = 'skip_intro' in button_settings
        self.showSkipCredits = 'skip_credits' in button_settings
        self.bingeMode = False
        self.autoSkipIntro = False
        self.autoSkipCredits = False
        self.showIntroSkipEarly = False
        self.skipPostPlay = False
        self.videoPausedForAudioStreamChange = False

        self.skipIntroButtonTimeout = util.addonSettings.skipIntroButtonTimeout
        self.skipCreditsButtonTimeout = util.addonSettings.skipCreditsButtonTimeout
        self.showItemEndsInfo = util.addonSettings.showMediaEndsInfo
        self.showItemEndsLabel = util.addonSettings.showMediaEndsLabel

        # Kept so doClose() can disconnect from the same server: the server outlives this dialog,
        # and without that every closed seek dialog stayed alive and kept answering its signals,
        # each one stopping playback again on a later stream's termination.
        self._npServer = self.player.video.server
        self._npServer.on("np:timelineResponse", self.timelineResponseCallback)
        self._npServer.on("np:streamTerminated", self.streamTerminatedCallback)

        if util.kodiSkipSteps and util.addonSettings.kodiSkipStepping and not self.handler.useAlternateSeek:
            self.skipSteps = {"negative": [], "positive": []}
            for step in util.kodiSkipSteps:
                key = "negative" if step < 0 else "positive"
                self.skipSteps[key].append(step * 1000)

            self.skipSteps["negative"].reverse()

        try:
            seconds = int(xbmc.getInfoLabel("Skin.String(SkinHelper.AutoCloseVideoOSD)"))
            if seconds > 0:
                self._hideDelay = seconds
        except ValueError:
            pass

    @property
    def player(self):
        return self.handler.player

    def timelineResponseCallback(self, **kwargs):
        response = kwargs.get("response")
        self.lastTimelineResponse = response.getBodyXml()

    def streamTerminatedCallback(self, **kwargs):
        # Server killed the stream (admin stop, plan/concurrent limit, server
        # shutdown, ...). Capture progress, suppress next-episode/post-play, stop
        # playback immediately instead of waiting for the buffer to drain, and tell
        # the user why.
        if self._terminated:
            return
        self._terminated = True

        code = kwargs.get("code")
        reason = kwargs.get("reason") or util.T(32330, "Message")
        util.LOG("SeekDialog: stream terminated by server (code={0}, reason={1})",
                 code, reason)

        offset = None
        try:
            if self.handler and self.handler.player:
                pt = self.handler.player.getTime()
                if pt is not None:
                    offset = int(pt * 1000)
        except Exception:
            offset = None
        if offset is None:
            try:
                offset = self.trueOffset()
            except Exception:
                offset = 0

        # Final timeline event with current playhead so PMS records progress.
        try:
            self.sendTimeline(state=self.player.STATE_STOPPED, t=offset)
        except Exception:
            util.ERROR()

        # Suppress next-up / post-play.
        if self.handler:
            self.handler.terminated = True
            self.handler.skipPostPlay = True
            self.handler.stoppedManually = True

        self._ignoreTick = True
        self._ignoreInput = True

        # Stop the Kodi player; we don't wait for the buffer to drain.
        try:
            if self.handler and self.handler.player:
                self.handler.player.stop()
        except Exception:
            util.ERROR()

        try:
            util.showNotification(reason, time_ms=8000,
                                  header=util.T(35003, 'Stream Stopped by Server'))
        except Exception:
            util.ERROR()

    def resetTimeout(self, fast=False):
        self.timeout = time.time() + (fast and min(0.5, self._hideDelay) or self._hideDelay)

    def resetAutoSeekTimer(self, value="not_set"):
        self.autoSeekTimeout = value if value != "not_set" else time.time() + self._autoSeekDelay

    def setSeekPaused(self, state):
        self._seekPaused = state
        self._seekPausedAt = time.time()

    def resetSeeking(self):
        self._endScan()
        if self._seekPaused in ('seeking', 'trickplay'):
            # the seek was abandoned (doSeek() moves it on first): play on from where it was - now, or once the
            # pause has happened if it hasn't yet (onPlayBackPaused())
            self.setSeekPaused('resuming')
            if self.player.playState == self.player.STATE_PAUSED:
                self.player.control('play')

        self._seeking = False
        self._seekingWithoutOSD = False
        self._delayedSeekTimeout = None
        self._applyingSeek = False
        self.bigSeekChanged = False
        self.selectedOffset = None
        self._navigatedViaMarkerOrChapter = False
        self.setProperty('button.seek', '')
        self.setProperty('marker.countdown', '')
        self.resetAutoSeekTimer(None)
        self.resetSkipSteps()

    def resetMarkerStates(self):
        self.setProperty('show.markerSkip', '')
        self.setProperty('show.markerSkip_OSDOnly', '')
        self.setProperty('marker.autoSkip', '')
        self.setProperty('skipMarkerName', '')

        self._introSkipShownStarted = None
        self._introAutoSkipped = False
        self._creditsSkipShownStarted = None
        self._currentMarker = None
        self._creditsAutoSkipped = False
        self.markers = None

    @property
    def DPPlayerOffset(self):
        if self.isDirectPlay and self.handler.player and self.handler.player.playerObject:
            return self.handler.player.playerObject.startOffset * 1000
        return 0

    def trueOffset(self):
        if self.isDirectPlay:
            return self.DPPlayerOffset + (self.offset if self.offset is not None else 0)
        else:
            return self.baseOffset + (self.offset if self.offset is not None else 0)

    @property
    def markers(self):
        if not self._enableMarkerSkip:
            return []

        if self._markers is None:
            if hasattr(self.handler.player.video, "markers"):
                markers = []

                for m in self.handler.player.video.markers:
                    if m.type in MARKERS:
                        # normalize markers and properties as we modify them later on
                        final = m.final.asBool()
                        sto = m.startTimeOffset.asInt()
                        marker = Marker({
                            "id": m.id.asInt(),
                            "final": final,
                            "type": str(m.type),
                            "title": "{}@{}{}".format(m.type, m.startTimeOffset.asInt(), final and ",final" or ""),
                            "startTimeOffset": sto,
                            "endTimeOffset": m.endTimeOffset.asInt()
                        })

                        # skip completely bad markers
                        if marker.startTimeOffset > self.duration:
                            continue

                        # skip intro markers that are too late
                        if (marker.type == "intro"
                                and marker.startTimeOffset > util.addonSettings.introMarkerMaxOffset * 1000):
                            util.DEBUG_LOG("Throwing away intro marker {}, as its start time offset is bigger than the"
                                           " configured maximum", marker)
                            continue

                        m = MARKERS[marker.type].copy()
                        m["marker"] = marker
                        m["marker_type"] = marker.type
                        markers.append(m)

                self._markers = markers
                util.DEBUG_LOG("Got markers: {}", lambda: list(_m["marker"] for _m in markers))
            else:
                self._markers = []

        return self._markers

    @markers.setter
    def markers(self, val):
        self._markers = val

    def getCurrentMarkerDef(self, offset=None):
        """
        Show intro/credits skip button at current time
        """

        if not self.markers:
            return

        off = offset if offset is not None else self.trueOffset()

        for markerDef in self.markers:
            marker = markerDef["marker"]
            if marker:
                startTimeOffset = marker.startTimeOffset

                # marker display wanted?
                if (not self.showSkipIntro and markerDef["marker_type"] == "intro") or \
                        (not self.showSkipCredits and markerDef["marker_type"] == "credits"):
                    continue

                # show intro skip early? (only if intro is during the first X minutes)
                if self.showIntroSkipEarly and markerDef["marker_type"] == "intro" and \
                        startTimeOffset <= util.addonSettings.skipIntroButtonShowEarlyThreshold2 * 1000:
                    startTimeOffset = 0
                    markerDef["overrideStartOff"] = 0

                # fix markers with a bad endTimeOffset
                if marker.endTimeOffset > self.duration:
                    marker.endTimeOffset = self.duration
                    util.DEBUG_LOG("Fixing marker endTimeOffset for: {}", marker)

                markerEndNegoff = FINAL_MARKER_NEGOFF if getattr(markerDef["marker"], "final", False) else 0

                if startTimeOffset - MARKER_SHOW_NEGOFF <= off < marker.endTimeOffset - markerEndNegoff:

                    return markerDef

    def onFirstInit(self):
        try:
            self._onFirstInit()
        except RuntimeError:
            util.ERROR(hide_tb=True)
            self.started = False
        except AttributeError:
            self.started = False
            # early exit probably during dialog setup
            self.handler.player._ignorePlaybackFailure = True
            self.stop()

    def _onFirstInit(self):
        util.DEBUG_LOG("SeekDialog: onFirstInit")
        self.resetTimeout()
        self.setProperty('skipMarkerName', T(32495, 'Skip intro'))

        # Re-syncs a card row once it has faded out after focus leaves it (onFocus()), rather than leaving that to
        # the next once-a-second tick. Weakly held, so a pending timer can't keep a closed dialog alive.
        selfRef = weakref.ref(self)

        def syncRowsLater():
            dialog = selfRef()
            if dialog:
                dialog.syncRows()

        self._rowSyncTimer = kodigui.PropertyTimer(self._winID, self.ROW_FADE_OUT, 'rows.syncing', '',
                                                   init_value=False, callback=syncRowsLater)
        self.setProperty('queue.label', T(35079, 'Play queue'))

        if self.handler.playlist:
            self.handler.playlist.on('change', self.updateProperties)
            self.handler.playlist.on('current.changed', self.updateProperties)

        self.seekbarControl = self.getControl(self.SEEK_IMAGE_ID)
        self.positionControl = self.getControl(self.POSITION_IMAGE_ID)
        self.cacheControl = self.getControl(self.CACHE_IMAGE_ID)
        # last width (px along the bar) set on the played fills / scrubber / buffer, so unchanged
        # values cost no GUI call (setBarPercent())
        self._barWidths = {}
        self._barCaps = {self.positionControl: self.getControl(self.POSITION_CAP_ID),
                         self.cacheControl: self.getControl(self.CACHE_CAP_ID)}
        self.bifImageControl = self.getControl(self.BIF_IMAGE_ID)
        self.selectionIndicator = self.getControl(self.SELECTION_INDICATOR)
        # updateProgress() moves the seek marker and the thumbnail along the bar, keeping the template's y
        self._markerY = self.selectionIndicator.getY()
        self._bifY = self.bifImageControl.getY()
        self.bigSeekControl = kodigui.ManagedControlList(self, self.BIG_SEEK_LIST_ID, 12)
        self.queueControl = kodigui.ManagedControlList(self, self.QUEUE_LIST_ID, 12)
        self.initialized = True

        button_defaults = ['subtitle_downloads', 'skip_intro', 'skip_credits'] + \
            (['video_show_vs10'] if util.CE_VS10 else [])
        button_settings = util.getUserSetting('player_show_buttons', button_defaults)
        self.holdToScan = util.getSetting('video_hold_to_scan')
        showQuickSubs = 'subtitle_downloads' in button_settings
        self.showSkipIntro = 'skip_intro' in button_settings
        self.showSkipCredits = 'skip_credits' in button_settings
        self.setBoolProperty('nav.quick_subtitles', showQuickSubs)
        # VS10 mode switcher: show on CoreELEC Amlogic builds (U3k, avdvplus, p3i, CPM) if not hidden by user
        showVS10 = 'video_show_vs10' in button_settings
        self._vs10Shown = bool(util.CE_VS10 and showVS10)
        self.setBoolProperty('nav.vs10', self._vs10Shown)

        self.updateProperties()
        self.updateChapters()
        self.videoSettingsHaveChanged()
        self.update()

        self.setBoolProperty("initialized", True)

    def onReInit(self):
        util.DEBUG_LOG("SeekDialog: onReInit")
        self.lastTimelineResponse = None
        self._terminated = False
        self._ignoreTick = False
        self.waitingForBuffer = False
        self._abortBufferWait = False

        self.resetTimeout()
        self.resetSeeking()
        self.updateProperties()
        self.updateChapters()
        self.videoSettingsHaveChanged()
        self.updateProgress()
        self.setBoolProperty("initialized", True)

    def reuseDialog(self):
        # in case of a reused handler/dialog (consecutive playback), onFirstInit and onReInit won't be called;
        # setup() will reset certain assumptions, set them here
        self.setBoolProperty("initialized", True)

    def setup(self, duration, meta, offset=0, bif_url=None, title='', title2='', chapters=None, keepMarkerDef=False,
              reused=False):
        """
        this is called by our handler and occurs earlier than onFirstInit.
        """
        util.DEBUG_LOG("SeekDialog: setup, keepMarkerDef={}, offset={}", keepMarkerDef, offset)
        self._duration = duration
        self.title = title
        self.title2 = title2
        self.chapters = chapters or []
        if not keepMarkerDef:
            # a new item, not a transcode's seek restarting this one; before the title lines below use it
            self.hidePreviews, self.hideTitles = self.spoilerHiding(self.player.video)
        self.isDirectPlay = not meta.isTranscoded
        self.isTranscoded = not self.isDirectPlay
        self.setProperty('video.title', title)
        self.setProperty('is.show', (self.player.video.type == 'episode') and '1' or '')
        # set spoiler-relevant properties immediately; updateProperties() only runs after the window has rendered
        # (fresh dialog) or possibly never (reused dialog without a playlist), which would briefly - or permanently -
        # leak the episode title/times with the previous or empty property state (#279)
        self.setBoolProperty('hide.title', self.hideTitles)
        self.setBoolProperty('no.osd.hide_info', self.no_time_no_osd_spoilers)
        self.setProperty('ep.year', (self.player.video.type == 'episode') and self.player.video.year or '')
        self.setTitleLines()
        self.setProperty('has.playlist', self.handler.playlist and '1' or '')
        self.setProperty('shuffled', (self.handler.playlist and self.handler.playlist.isShuffled) and '1' or '')
        self.setProperty('show.buffer', (util.addonSettings.playerShowBuffer and self.isDirectPlay) and '1' or '')
        self.setProperty('theme', 'modern')
        self.setBoolProperty("initialized", False)

        self.killTimeKeeper()

        self.playbackTime = 0
        # a new video: its playing item moved, so the play queue row is rebuilt on the next button focus
        self._queueRowStale = True

        try:
            if self.player.video.type == 'episode':
                pbs = self.player.video.playbackSettings
                util.DEBUG_LOG("Playback settings for {}: {}", self.player.video.ratingKey, pbs)

                self.bingeMode = pbs.binge_mode
                self.handler.inBingeMode = self.bingeMode

                # don't auto skip intro when on binge mode on the first episode of a season
                firstEp = self.player.video.index == '1'

                if self.isDirectPlay or util.getUserSetting('auto_skip_in_transcode', True):
                    self.autoSkipIntro = (self.bingeMode and not firstEp) or pbs.auto_skip_intro
                    self.autoSkipCredits = self.bingeMode or pbs.auto_skip_credits

                self.showIntroSkipEarly = self.bingeMode or pbs.show_intro_skip_early
                self.handler.skipPostPlay = self.skipPostPlay = (self.bingeMode or pbs.skip_post_play_tv)

            # in transcoded scenarios, when seeking, keep previous marker states, as the video restarts
            if not keepMarkerDef:
                self.resetMarkerStates()
        except IndexError:
            self.doClose(delete=True)
            raise util.NoDataException

        self.showChapters = util.getUserSetting('show_chapters', True) and (
                bool(chapters) or (util.getUserSetting('virtual_chapters', True) and bool(self.markers)))
        self.setProperty('has.chapters', self.showChapters and '1' or '')

        self.baseOffset = offset
        self.offset = 0
        self.idleTime = None
        self.setSeekPaused(None)
        self.lastSubtitleNavAction = "forward"
        self._ignoreTick = False
        self._ignoreInput = False
        self.bifURL = bif_url
        self.hasBif = bool(self.bifURL)
        if not keepMarkerDef:
            # a new item, not a transcode's seek restarting this one: the last one's previews go, its own are
            # downloaded once it's playing (tick())
            previews.store.clear()
            self._previewsStarted = False

        if self.hasBif:
            self.baseURL = re.sub(r'/\d+\?', '/{0}?', self.bifURL)

        if reused:
            self.reuseDialog()
        self.update()

    def update(self, offset=None, from_seek=False):
        if from_seek:
            self.fromSeek = time.time()
        else:
            if time.time() - self.fromSeek > 0.5:
                self.fromSeek = 0

        if offset is not None:
            self.offset = offset
            self.selectedOffset = self.trueOffset()

        self.updateProgress()

    def closeWithCommand(self, command):
        self.exitCommand = command
        self.stop()

    def onAction(self, action):
        if xbmc.getCondVisibility('Window.IsActive(selectdialog)'):
            if self.doKodiSelectDialogHack(action):
                return

        try:
            self.resetTimeout()

            controlID = self.getFocusId()
            # Kodi's moved focus for this action before it gets here: whether it just did, onto this control
            justArrived = self._focusArrived == controlID
            self._focusArrived = None
            self.idleTime = None
            # user input means someone's actually watching
            util.MONITOR.tv_standby = False

            cancelActions = (xbmcgui.ACTION_PREVIOUS_MENU, xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_STOP)


            if not self._ignoreInput:
                if self.scanAction(action, controlID):
                    return

                if action.getId() in KEY_MOVE_SET:
                    self.setProperty('mouse.mode', '')
                    if not controlID:
                        self.beginSeeking()
                        self.setFocusId(self.SETTINGS_BUTTON_ID)  # the button row's first, never its last-focused
                        return
                elif action == xbmcgui.ACTION_MOUSE_MOVE:
                    self.setProperty('mouse.mode', '1')

                if controlID in (self.MAIN_BUTTON_ID, self.NO_OSD_BUTTON_ID):
                    if action == xbmcgui.ACTION_MOUSE_LEFT_CLICK:
                        if self.getProperty('mouse.mode') != '1':
                            self.setProperty('mouse.mode', '1')

                        self.seekMouse(action, without_osd=controlID == self.NO_OSD_BUTTON_ID)
                        return
                    elif action == xbmcgui.ACTION_MOUSE_MOVE:
                        self.seekMouse(action, without_osd=controlID == self.NO_OSD_BUTTON_ID, preview=True)
                        return

                if action in (xbmcgui.ACTION_PAUSE, xbmcgui.ACTION_PLAYER_PLAY, xbmcgui.ACTION_PLAYER_PLAYPAUSE):
                    self._playPauseInputAt = time.time()

                if action == xbmcgui.ACTION_CONTEXT_MENU or (self.getProperty('show.PPI') and action in (xbmcgui.ACTION_MOVE_LEFT, xbmcgui.ACTION_MOVE_RIGHT)):
                    if self.getProperty('show.PPI') and not self._playerDebugActive and not self._playerNativePPIActive:
                        if action == xbmcgui.ACTION_MOVE_LEFT:
                            self.showPPIDialog(real_ppi=True, debug=True)
                        else:
                            self.showPPIDialog(real_ppi=True)
                        return
                if self._playerNativePPIActive and action in (xbmcgui.ACTION_MOVE_UP, xbmcgui.ACTION_MOVE_DOWN):
                    self._playerNativePPIActive = False

                # Up off the top of the OSD closes it: from the buttons when there's no skip button above them
                # (focus stays put), or from the skip button. Not the up that's just brought focus here.
                if action == xbmcgui.ACTION_MOVE_UP and not justArrived and controlID in self.OSD_TOP_IDS                         and self.osdVisible():
                    self.hideOSD()
                    return

                passThroughMain = False
                if controlID == self.SKIP_MARKER_BUTTON_ID:
                    if action == xbmcgui.ACTION_SELECT_ITEM:
                        if self._applyingSeek:
                            return

                        markerDef = self._currentMarker
                        if markerDef["marker"]:
                            marker = markerDef["marker"]
                            final = getattr(marker, "final", False)

                            if final:
                                return self.handleFinalMarker(markerDef, immediate=False, context="MarkerSkip")

                            util.DEBUG_LOG('MarkerSkip: Skipping marker'
                                           ' {} (final: {}, to: {}, offset: {})'.format(markerDef["marker"],
                                                                            final, marker.endTimeOffset, MARKER_END_JUMP_OFF))
                            self.setProperty('show.markerSkip', '')
                            self.setProperty('show.markerSkip_OSDOnly', '')
                            markerDef["skipped"] = True
                            self.doSeek(marker.endTimeOffset + MARKER_END_JUMP_OFF)
                            self.hideOSD(skipMarkerFocus=True)

                            if marker.type == "credits":
                                # non-final marker
                                setattr(self, markerDef["markerAutoSkipShownTimer"], None)
                                self.resetAutoSeekTimer(None)

                        return
                    elif action == xbmcgui.ACTION_MOVE_DOWN:
                        # Only reached with the OSD hidden: with it shown, the template's ondown has already moved
                        # focus to the buttons. Opens the OSD and leaves the button as it was - it comes back on
                        # its own when the OSD closes (hideOSD() refocuses it); Back is what dismisses it.
                        self.showOSD()
                    elif action in (xbmcgui.ACTION_MOVE_RIGHT, xbmcgui.ACTION_STEP_FORWARD, xbmcgui.ACTION_MOVE_LEFT,
                                    xbmcgui.ACTION_STEP_BACK):
                        # allow no-OSD-seeking with intro skip button shown
                        passThroughMain = True
                    elif action in (xbmcgui.ACTION_PREVIOUS_MENU, xbmcgui.ACTION_NAV_BACK):
                        if self.getProperty('show.markerSkip') and not self.getProperty('show.markerSkip_OSDOnly'):
                            self.setProperty('show.markerSkip', '')
                            self.setProperty('show.markerSkip_OSDOnly', '1')
                            markerDef = self._currentMarker
                            if markerDef:
                                markerDef["hidden"] = True
                            return

                if controlID == self.MAIN_BUTTON_ID:
                    # we're seeking from the timeline with the OSD open - do an actual timeline seek

                    # ignore seek actions for a split second when the OSD is hiding or was hiding
                    if (action.getId() in KEY_MOVE_SET and self._osdHideAnimationTimeout and
                            self._osdHideAnimationTimeout + self.OSD_HIDE_ACTION_THRESHOLD >= time.time()):
                        return

                    if action in (xbmcgui.ACTION_MOVE_RIGHT, xbmcgui.ACTION_STEP_FORWARD,
                                  xbmcgui.ACTION_MOVE_LEFT, xbmcgui.ACTION_STEP_BACK):
                        if self.handler.waitingForSOS:
                            util.DEBUG_LOG("SeekDialog: Ignoring seek action as we're waiting for SOS")
                            return
                        # seek mode starts here, from where playback is now - focusing the timeline doesn't start it
                        if not self._seeking:
                            self.selectedOffset = self.trueOffset()
                        # The OSD-hidden seek's steps (skipSteps: +30/-10, or Kodi's own with kodi_skip_stepping),
                        # through skipByOffset() - auto-seek on, the seek's made the delay after the last press
                        if action in (xbmcgui.ACTION_MOVE_RIGHT, xbmcgui.ACTION_STEP_FORWARD):
                            return self.skipForward()
                        return self.skipBack()

                    # Up/down are plain template navigation: up to the buttons (and on to the skip button), down
                    # to the chapter row.

                # don't auto-apply the currently selected seek when moving off the timeline (up to the buttons,
                # down to a card row): it's abandoned
                elif action in (xbmcgui.ACTION_MOVE_UP, xbmcgui.ACTION_MOVE_DOWN) \
                        and self.previousFocusID == self.MAIN_BUTTON_ID and self._seeking:
                    self.resetSeeking()

                elif controlID == self.NO_OSD_BUTTON_ID or passThroughMain:
                    # ignore seek actions for a split second when the OSD is hiding or was hiding
                    if (action.getId() in KEY_MOVE_SET and self._osdHideAnimationTimeout and
                            self._osdHideAnimationTimeout + self.OSD_HIDE_ACTION_THRESHOLD >= time.time()):
                        return

                    if action in (xbmcgui.ACTION_MOVE_RIGHT, xbmcgui.ACTION_MOVE_LEFT):
                        if self.handler.waitingForSOS:
                            util.DEBUG_LOG("SeekDialog: Ignoring seek action as we're waiting for SOS")
                            return
                        # we're seeking from the timeline, with the OSD closed; act as we're skipping
                        if not self._seeking:
                            self.selectedOffset = self.trueOffset()

                        if action == xbmcgui.ACTION_MOVE_RIGHT:
                            self.skipForward(without_osd=True)

                        else:
                            self.skipBack(without_osd=True)
                    elif action in (xbmcgui.ACTION_MOVE_UP,
                                    xbmcgui.ACTION_MOVE_DOWN,
                                    xbmcgui.ACTION_PAGE_UP,
                                    xbmcgui.ACTION_PAGE_DOWN):
                        if self.clientLikePlex:
                            self.showOSD()
                            return

                        if action in (xbmcgui.ACTION_MOVE_UP, xbmcgui.ACTION_MOVE_DOWN):
                            # we're seeking from the timeline, with the OSD closed; act as we're skipping
                            if not self._seeking:
                                self.selectedOffset = self.trueOffset()

                            if self.skipChapter(forward=(action == xbmcgui.ACTION_MOVE_UP), without_osd=True):
                                return

                    if action in (
                            xbmcgui.ACTION_MOVE_UP,
                            xbmcgui.ACTION_MOVE_DOWN,
                            xbmcgui.ACTION_BIG_STEP_FORWARD,
                            xbmcgui.ACTION_BIG_STEP_BACK
                    ) and not self._seekingWithoutOSD:
                        self.selectedOffset = self.trueOffset()
                        self.beginSeeking()
                        self.updateProgress()
                        self.showOSD()

                    elif action.getButtonCode() == 61519:
                        if self.getProperty('show.PPI'):
                            self.hidePPIDialog()
                        else:
                            self.showPPIDialog()
                        return

                if action.getButtonCode() == 61516:
                    self.cycleSubtitles()
                elif action.getButtonCode() == 61524:
                    self.toggleSubtitles()
                elif action.getButtonCode() == 323714:
                    # Alt-left
                    builtin.PlayerControl('tempodown')
                elif action.getButtonCode() == 323715:
                    # Alt-right
                    builtin.PlayerControl('tempoup')
                elif action == xbmcgui.ACTION_NEXT_ITEM:
                    self.prepareNewPlayback(queuing_next=True, ignore_tick=True)
                    self.player.trigger("action", action="next")
                elif action == xbmcgui.ACTION_PREV_ITEM:
                    self.prepareNewPlayback(ignore_tick=True)
                    self.player.trigger("action", action="prev")

                if action in cancelActions + (xbmcgui.ACTION_SELECT_ITEM,):
                    if action in cancelActions:
                        if self.getProperty('show.PPI'):
                            self.hidePPIDialog()
                            self.hideOSD()
                            return
                        if self._playerDebugActive:
                            xbmc.executebuiltin('Action(playerdebug)')
                            self._playerDebugActive = False
                            return
                        if self._playerNativePPIActive:
                            self._playerNativePPIActive = False

                    # immediate marker timer actions
                    if self.countingDownMarker:
                        if controlID != self.BIG_SEEK_LIST_ID and \
                                (util.addonSettings.skipMarkerTimerCancel
                                 or util.addonSettings.skipMarkerTimerImmediate):
                            if util.addonSettings.skipMarkerTimerCancel and \
                                    action in (xbmcgui.ACTION_PREVIOUS_MENU, xbmcgui.ACTION_NAV_BACK):
                                self.displayMarkers(cancelTimer=True)
                                return

                            # skip the first second of a marker shown with countdown to avoid unexpected OK/SELECT
                            # behaviour
                            elif util.addonSettings.skipMarkerTimerImmediate \
                                    and action == xbmcgui.ACTION_SELECT_ITEM and \
                                    self._currentMarker["countdown"] is not None:
                                    #self._currentMarker["countdown_initial"] is not None and \
                                    #self._currentMarker["countdown"] < self._currentMarker["countdown_initial"]:
                                self.displayMarkers(immediate=True)
                                self.hideOSD(skipMarkerFocus=True)
                                return

                    if action in cancelActions:
                        if self.waitingForBuffer:
                            self._abortBufferWait = True
                            self.waitingForBuffer = False
                            return

                        if self._seeking and not self._ignoreInput:
                            self.resetSeeking()
                            self.updateCurrent()
                            self.updateProgress()
                            if self.osdVisible():
                                self.hideOSD()
                            return

                        if action in (xbmcgui.ACTION_PREVIOUS_MENU, xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_STOP):
                            if action != xbmcgui.ACTION_STOP and self._osdHideAnimationTimeout:
                                if self._osdHideAnimationTimeout >= time.time():
                                    return
                                else:
                                    self._osdHideAnimationTimeout = None

                            if action != xbmcgui.ACTION_STOP and self.osdVisible():
                                self.hideOSD()
                            else:
                                # The real position, even inside credits: whether that counts as watched is the
                                # server's call (its played threshold and completion behaviour - by default the
                                # earlier of 90% and the first credits marker). This used to report a dismissed
                                # credits marker's end instead (b4be6be9), overriding servers set otherwise.
                                self.sendTimeline(state=self.player.STATE_STOPPED, ensureFinalTimelineEvent=True)
                                self.stop()
                            return
        except:
            util.ERROR()

        kodigui.BaseDialog.onAction(self, action)

    def doKodiSelectDialogHack(self, action):
        command = {
            xbmcgui.ACTION_MOVE_UP: "Up",
            xbmcgui.ACTION_MOVE_DOWN: "Down",
            xbmcgui.ACTION_MOVE_LEFT: "Right",  # Not sure if these are actually reversed or something else is up here
            xbmcgui.ACTION_MOVE_RIGHT: "Left",
            xbmcgui.ACTION_SELECT_ITEM: "Select",
            xbmcgui.ACTION_PREVIOUS_MENU: "Back",
            xbmcgui.ACTION_NAV_BACK: "Back"
        }.get(action.getId())

        if command is not None:
            xbmc.executebuiltin('Action({0},selectdialog)'.format(command))
            return True

        return False

    def onFocus(self, controlID):
        self._focusArrived = controlID
        lastFocusID = self.lastFocusID
        self.previousFocusID = self.lastFocusID
        self.lastFocusID = controlID
        if lastFocusID in self.ROW_LIST_IDS and controlID != lastFocusID:
            self._rowLeftAt[lastFocusID] = time.time()
            self._rowSyncTimer.reset(init=False)

        if self._scan:
            # A scan keeps the timeline: up/down (Kodi's moved focus before onAction() sees them) come straight back,
            # and arriving there doesn't end seek mode as it otherwise does.
            if controlID != self.MAIN_BUTTON_ID:
                self.setFocusId(self.MAIN_BUTTON_ID)
            return

        if controlID == self.MAIN_BUTTON_ID:
            if lastFocusID == self.BIG_SEEK_LIST_ID and self.bigSeekChanged:
                # OK on a chapter (bigSeekSelected()) sent focus here; bigSeekChanged holds the chapter's offset
                offset = self.bigSeekChanged
                self.updateProgress(set_to_current=False, offset=offset)

                # immediately seek bigSeek after click
                self._performSeek(offset=offset)
                self.hideOSD(skipMarkerFocus=True)

            else:
                # Not seek mode: left/right start that (onAction). Until then the time bubble follows playback
                # (updateCurrent()) and OK plays/pauses (onClick).
                if self._seeking:
                    self.resetSeeking()
                self.selectedOffset = None
                self.updateProgress()
                # the only way into the card rows is down from here: have them built and on the playing chapter/item
                self.refreshQueueRow()
                self.syncRows()

        elif controlID in self.ROW_LIST_IDS:
            # whatever the user browses to from here, the next syncRows() puts back
            self._rowPos.pop(controlID, None)

        elif xbmc.getCondVisibility('ControlGroup(400).HasFocus(0)'):
            self.selectedOffset = self.trueOffset()
            self.updateProgress()

        self.updateRowHint(controlID)

    def onClick(self, controlID):
        if self._ignoreInput:
            return

        if controlID in (self.MAIN_BUTTON_ID, self.NO_OSD_BUTTON_ID):
            # only react to click events on our main areas if we're not in mouse mode, otherwise mouse seeking is
            # handled by onAction
            if self.getProperty('mouse.mode') != '1':
                if controlID == self.MAIN_BUTTON_ID:
                    if self._seeking:
                        self.resetAutoSeekTimer(None)
                        self.doSeek()
                        self.hideOSD()
                    else:
                        # not seeking (only left/right start that): play/pause
                        self._playPauseInputAt = time.time()
                        xbmc.executebuiltin('PlayerControl(Play)')
                elif controlID == self.NO_OSD_BUTTON_ID:
                    if not self._seeking:
                        # we might be reacting to an immediate marker skip while showing a marker with timeout;
                        # in that case, don't show the OSD
                        if not self._currentMarker or not util.addonSettings.skipMarkerTimerImmediate or \
                                self._currentMarker["countdown"] is None:
                            # check if fast pause or resume are enabled and act accordingly instead of showing OSD
                            if "paused" in self.fastPauseResume and self.player.playState == self.player.STATE_PAUSED:
                                self.player.pause()
                                return
                            elif "playing" in self.fastPauseResume and self.player.playState == self.player.STATE_PLAYING:
                                self.player.pause()
                                return
                            else:
                                self.showOSD()
                    else:
                        # currently seeking without the OSD, apply the seek
                        self.doSeek()
        elif controlID == self.SETTINGS_BUTTON_ID:
            self.handleDialog(self.showSettings)
        elif controlID == self.OPTIONS_BUTTON_ID:
            self.handleDialog(self.optionsButtonClicked)
        elif controlID == self.SUBTITLE_BUTTON_ID:
            self.handleDialog(self.subtitleButtonClicked)
        elif controlID == self.VS10_BUTTON_ID:
            self.handleDialog(self.vs10ButtonClicked)
        elif controlID == self.BIG_SEEK_LIST_ID:
            self.bigSeekSelected()
        elif controlID == self.QUEUE_LIST_ID:
            self.queueItemSelected()

    def stop(self):
        self._ignoreTick = True
        self.doClose()
        # self.handler.onSeekAborted()
        self.handler.stoppedManually = True
        self.handler.player.stop()

    def prepareNewPlayback(self, queuing_next=False, queuing_specific=False, ignore_tick=False, ignore_input=False,
                           with_timeline=True):
        if with_timeline:
            self.sendTimeline(state=self.player.STATE_STOPPED)
        self._ignoreTick = ignore_tick
        self._ignoreInput = ignore_input
        self.handler.queuingNext = queuing_next
        self.handler.queuingSpecific = queuing_specific
        self.killTimeKeeper()

    def doClose(self, delete=False, **kw):
        util.DEBUG_LOG("SeekDialog: Closing")
        self._endScan()
        previews.store.clear()
        server = getattr(self, '_npServer', None)
        if server is not None:
            server.off("np:timelineResponse", self.timelineResponseCallback)
            server.off("np:streamTerminated", self.streamTerminatedCallback)
        if self.handler.playlist:
            self.handler.playlist.off('change', self.updateProperties)
            self.handler.playlist.off('current.changed', self.updateProperties)

        try:
            self.killTimeKeeper()
            # stop(), not close(): the dialog can be shown again (onReInit())
            timer = getattr(self, '_rowSyncTimer', None)
            if timer:
                timer.stop()
        finally:
            kodigui.BaseDialog.doClose(self)

    def showPPIDialog(self, real_ppi=False, debug=False):
        from lib.cache import kcm
        if self.getProperty('show.PPI'):
            if real_ppi:
                self.setProperty('show.PPI', '')
                if debug:
                    xbmc.executebuiltin('Action(playerdebug)')
                    self._playerDebugActive = True
                else:
                    xbmc.executebuiltin('Action(playerprocessinfo)')
                    self._playerNativePPIActive = True
            return

        for attrib in SESSION_ATTRIBUTE_TYPES.values():
            self.setProperty('ppi.%s' % attrib.label, "")

        self.setProperty('show.PPI', '1')
        self.setProperty('ppi.Status', 'Loading ...')

        def getVideoSession(currentVideo):
            return currentVideo.server.findVideoSession(self.handler.sessionID, currentVideo.ratingKey)

        if util.KODI_BUILD_NUMBER < 2090821:
            try:
                cache = int(xbmc.getInfoLabel('Player.ProgressCache')) - int(xbmc.getInfoLabel('Player.Progress'))
                self.setProperty('ppi.Buffered', str(cache))
            except:
                pass

        self.setProperty('ppi.BufferMB', str(kcm.memorySize))
        if kcm.readFactor > 0:
            self.setProperty('ppi.ReadFactor', str(kcm.readFactor))
        else:
            self.setProperty('ppi.AReadFactor', 'Adaptive')

        tries = 0
        while not self.player.started and tries < 50:
            util.MONITOR.waitForAbort(0.1)
            tries += 1

        if tries >= 50:
            self.hidePPIDialog()
            return

        info = None
        currentVideo = self.player.video
        try:
            videoSession = None
            elapsed = 0
            while not videoSession:
                if elapsed >= 2:
                    raise NotFound

                videoSession = getVideoSession(currentVideo)
                if videoSession:
                    break

                util.MONITOR.waitForAbort(0.5)
                elapsed += 0.5

            # fill attributes
            info = VideoSessionInfo(videoSession, currentVideo, currentVideo.server.anyLANConnection)

        except ServerNotOwned:
            # timeline response data fallback
            elapsed = 0
            try:
                while not self.lastTimelineResponse:
                    if elapsed > 10:
                        raise NotFound

                    util.MONITOR.waitForAbort(0.1)
                    elapsed += 0.1

                info = VideoSessionInfo(None, currentVideo,
                                        currentVideo.server.anyLANConnection,
                                        incompleteSessionData=self.lastTimelineResponse)
            except NotFound:
                self.setProperty('ppi.Status', 'Info not available (data not found)')

            except:
                util.ERROR()

        except NotFound:
            util.DEBUG_LOG("PPI: Couldn't find session: {}", self.handler.sessionID)
            try:
                for s in currentVideo.server.sessions:
                    util.DEBUG_LOG(
                        "PPI: candidate session: id={} ratingKey={} sessionKey={} playbackId={}, "
                        "wanted: id={} ratingKey={}",
                        s.session and s.session.id, s.ratingKey, getattr(s, "sessionKey", None),
                        getattr(getattr(s, "player", None), "playbackId", None),
                        self.handler.sessionID, currentVideo.ratingKey)
            except:
                util.ERROR()
            self.setProperty('ppi.Status', 'Info not available (session not found)')

        except:
            util.ERROR()

        if info:
            self.setProperty('ppi.Status', '')
            for attrib in info.attributes.values():
                self.setProperty('ppi.%s' % attrib.label, attrib.value)

    def hidePPIDialog(self):
        self.setProperty('show.PPI', '')

    def resetSkipSteps(self):
        self._forcedLastSkipAmount = None
        self._atSkipStep = -1
        self._lastSkipDirection = None

    def determineSkipStep(self, direction):
        stepCount = len(self.skipSteps[direction])

        # shortcut for simple skipping
        if stepCount == 1:
            return self.skipSteps[direction][0]

        use_direction = direction

        # kodi-style skip steps

        # when the direction changes, we either use the skip steps of the other direction, or walk backwards in the
        # current skip step list
        if self._lastSkipDirection != direction:
            if self._atSkipStep == -1 or self._lastSkipDirection is None:
                self._atSkipStep = 0
                self._lastSkipDirection = direction
                self._forcedLastSkipAmount = None
                step = self.skipSteps[use_direction][0]

            else:
                # we're reversing the current direction
                use_direction = self._lastSkipDirection

                # use the inverse value of the current skip step
                step = self.skipSteps[use_direction][min(self._atSkipStep, len(self.skipSteps[use_direction]) - 1)] * -1

                # we've hit a boundary, reverse the difference of the last skip step in relation to the boundary
                if self._forcedLastSkipAmount is not None:
                    step = self._forcedLastSkipAmount * -1
                    self._forcedLastSkipAmount = None

                # walk back one step
                self._atSkipStep -= 1
        else:
            # no reversal of any kind was requested and we've not hit any boundary, use the next skip step
            if self._forcedLastSkipAmount is None:
                self._atSkipStep += 1
                step = self.skipSteps[use_direction][min(self._atSkipStep, stepCount - 1)]

            else:
                # we've hit a timeline boundary and haven't reversed yet. Don't do any further skipping
                return

        return step

    def skipChapter(self, forward=True, without_osd=False):
        lastSelectedOffset = self.selectedOffset
        util.DEBUG_LOG('chapter skipping from {0} with forward {1}', lastSelectedOffset, forward)
        if forward:
            nextChapters = [c for c in self.chapters if c.startTime() > lastSelectedOffset]
            util.DEBUG_LOG('Found {0} chapters among {1}', lambda: len(nextChapters),
                           lambda: len(self.chapters))
            if len(nextChapters) == 0:
                return False
            chapter = nextChapters[0]
        else:
            startTimeLimit = lastSelectedOffset - 2000
            if startTimeLimit < 0:
                startTimeLimit = 0
            lastChapters = [c for c in self.chapters if c.startTime() <= startTimeLimit]
            util.DEBUG_LOG('Found {0} chapters among {1}', lambda: len(lastChapters),
                           lambda: len(self.chapters))
            if len(lastChapters) == 0:
                return False
            chapter = lastChapters[-1]

        if chapter.tag:
            util.DEBUG_LOG('Skipping to chapter: {}', chapter.tag)

        util.DEBUG_LOG('New start time is {0}', lambda: chapter.startTime())
        self.skipByOffset(chapter.startTime() - lastSelectedOffset, without_osd=without_osd)
        return True

    def skipForward(self, without_osd=False, immediate=False):
        self.skipByStep("positive", without_osd, immediate=immediate)

    def skipBack(self, without_osd=False, immediate=False):
        self.skipByStep("negative", without_osd, immediate=immediate)

    def skipByStep(self, direction="positive", without_osd=False, immediate=False):
        step = self.determineSkipStep(direction)
        self.skipByOffset(step, without_osd, immediate=immediate)

    def skipByOffset(self, offset, without_osd=False, immediate=False):
        if self.countingDownMarker:
            self.displayMarkers(cancelTimer=True)

        if offset is not None:
            if not self.seekByOffset(offset, without_osd=without_osd):
                return

        if self.useAutoSeek:
            self.delayedSeek()
        elif immediate:
            self._performSeek()
            self.resetSeeking()
        else:
            self.setProperty('button.seek', '1')

    def delayedSeek(self):
        self.setProperty('button.seek', '1')
        delay = self._autoSeekDelay

        if delay > 0:
            timeout = time.time() + delay
            if not self._delayedSeekTimeout:
                # A seek's first step waits at least FIRST_SEEK_STEP_DELAY: a held key only starts repeating some time
                # after it goes down (half a second on a default Windows keyboard, about the same on most remotes),
                # and a shorter auto-seek delay applied the step first - on a transcode, restarting the stream and
                # losing the rest of the hold.
                timeout = time.time() + max(delay, self.FIRST_SEEK_STEP_DELAY)
            # never brought forward by a later press: a quick tap and then a hold keeps the first step's wait
            self._delayedSeekTimeout = max(timeout, self._delayedSeekTimeout or 0)

            if not self._delayedSeekThread or not self._delayedSeekThread.is_alive():
                self._delayedSeekThread = threading.Thread(target=self._delayedSeek)
                self._delayedSeekThread.start()
        else:
            # Do seek now
            self._performSeek()
            self.resetSeeking()

    def _delayedSeek(self):
        try:
            while not util.MONITOR.waitForAbort(0.1):
                if not self._delayedSeekTimeout or time.time() > self._delayedSeekTimeout:
                    break

            if not util.MONITOR.abortRequested() and self._delayedSeekTimeout is not None:
                self._performSeek()
        except:
            util.ERROR()

    def _performSeek(self, offset=None):
        self._lastSkipDirection = None
        self._forcedLastSkipAmount = None
        self.doSeek(offset=offset)

    def scanAction(self, action, controlID):
        """
        Scanning the timeline (docs/hold-to-fast-forward.md): onAction()'s first look at an action. True when it's
        dealt with it. A remote's FF/RW start a scan anywhere in the player, always. With video_hold_to_scan on, so
        does a hold (seek_scan.HoldDetector) where left/right skip - the timeline, the OSD-hidden button, the skip
        button. While a scan runs, every key's handled here.
        """
        actionID = action.getId()
        now = time.time()

        media = self.SCAN_MEDIA_KEYS.get(actionID)
        if media:
            # A tap as left/right's are: starts a scan, or steps its speed. Kodi's own FF/RW have already sped up
            # a playing video (startScan() puts that right); a paused one, as during a scan, they leave alone.
            if self._scan:
                if self.holdAnswer(media, now, 'ff/rw') == 'press':
                    self.stepScan(media, now)
                return True
            if self.canScan():
                self.holdAnswer(media, now, 'ff/rw')
                self.startScan(media, trick_play=True)
                return True
            return False

        if not self.holdToScan and not self._scan:
            return False

        direction = self.SCAN_KEYS.get(actionID)
        if not self._scan:
            if not direction or not (controlID == self.MAIN_BUTTON_ID or (
                    controlID in (self.NO_OSD_BUTTON_ID, self.SKIP_MARKER_BUTTON_ID)
                    and actionID in (xbmcgui.ACTION_MOVE_RIGHT, xbmcgui.ACTION_MOVE_LEFT))):
                self._holdDetector.reset()
                return False
            answer = self.holdAnswer(direction, now)
            # Taps - a held key's press and first repeat among them - skip as ever. Its fast repeats don't: they're
            # the hold, seen at the third of them (before the first skip applies). Where there can't be a scan,
            # everything skips.
            if answer == 'press' or not self.canScan():
                return False
            if answer == 'hold':
                self.startScan(direction)
            return True

        if direction:
            # a tap steps the speed along -16x..0x..16x; a held key's repeats do nothing
            if self.holdAnswer(direction, now) == 'press':
                self.stepScan(direction, now)
            return True

        self._holdDetector.reset()
        if actionID == xbmcgui.ACTION_SELECT_ITEM:
            # stopped where it's shown; the timeline's onClick() applies it as it does a skip, anywhere else here
            self._endScan()
            if controlID != self.MAIN_BUTTON_ID:
                self.applyScan()
        elif actionID in (xbmcgui.ACTION_PAUSE, xbmcgui.ACTION_PLAYER_PLAY, xbmcgui.ACTION_PLAYER_PLAYPAUSE):
            self.applyScan(play=True)
        elif actionID in (xbmcgui.ACTION_PREVIOUS_MENU, xbmcgui.ACTION_NAV_BACK):
            self.cancelScan()
        elif actionID == xbmcgui.ACTION_STOP:
            self._endScan()
            return False
        elif actionID in (xbmcgui.ACTION_MOVE_UP, xbmcgui.ACTION_MOVE_DOWN):
            # Kodi's already moved focus off the timeline (onFocus() sends it back too)
            self.setFocusId(self.MAIN_BUTTON_ID)
        return True

    def holdAnswer(self, direction, now, key=None):
        answer = self._holdDetector.press(direction, now)
        gap = self._holdDetector.gap
        util.DEBUG_LOG("SeekDialog: Hold detector: {}{} {} -> {}{}", direction > 0 and 'right' or 'left',
                       key and ' ({})'.format(key) or '', gap is None and 'new' or '{:.3f}s'.format(gap), answer,
                       self._scan and ' (scanning)' or '')
        return answer

    def stepScan(self, direction, now):
        """A tap during a scan: a step along -16x..0x..16x."""
        with self._scanLock:
            scan = self._scan
            if scan:
                scan.press(direction, now)
                self.selectedOffset = scan.offset
        if scan:
            self.showScanSpeed(scan)
            self.updateProgress(set_to_current=False)

    def canScan(self):
        return (self.initialized and not self._applyingSeek and not self.handler.waitingForSOS
                and not self.handler.player.isExternal and self.duration > seek_scan.END_MARGIN)

    def startScan(self, direction, trick_play=False):
        """
        Pauses the video (as a seek does, seekByOffset() - usually the hold's first press already has) and moves the
        seek point on its own from where the marker is - after the hold's press and first repeat, or earlier taps -
        with the OSD up on the timeline, until applyScan() or cancelScan(). trick_play: started by FF/RW, which Kodi
        has already acted on, speeding up a playing video.
        """
        # the hold's press and repeats were skips: dropped, and neither auto-seek may apply anything during the scan
        self._delayedSeekTimeout = None
        self.resetAutoSeekTimer(None)
        self.resetSkipSteps()

        now = time.time()
        scan = seek_scan.Scan(self.duration)
        start = self.selectedOffset if self._seeking and self.selectedOffset is not None else self.trueOffset()
        scan.start(start, direction, now)
        self._holdDetector.held(direction, now)
        with self._scanLock:
            self._scan = scan
        self._scanBifUrl = None
        self._scanBifAt = 0
        self.selectedOffset = scan.offset
        self._seekingWithoutOSD = False
        self.beginSeeking()

        if trick_play:
            self.endTrickPlay()
        elif not self._seekPaused and self.player.playState == self.player.STATE_PLAYING:
            self.setSeekPaused('seeking')
            self.player.control('pause')

        self.setProperty('button.seek', '1')
        self.showScanSpeed(scan)
        self.setProperty('scan.active', '1')
        if not self.osdVisible():
            self.showOSD()
        elif self.getFocusId() != self.MAIN_BUTTON_ID:
            self.setFocusId(self.MAIN_BUTTON_ID)
        self.updateProgress(set_to_current=False)

        util.DEBUG_LOG("SeekDialog: Scan from {} ({} {})", scan.offset, scan.direction > 0 and 'forward' or 'back',
                       scan.label)
        threading.Thread(target=self._scanLoop, args=(scan,), name='SeekDialog.scan').start()

    def endTrickPlay(self):
        """
        Pauses a video Kodi's own FF/RW have sped up, for a scan. Kodi's Player.Playing is false at any speed but 1x,
        so playState() reads such a video as stopped; and PlayerControl(Play), which pausing sends, only brings it
        back to 1x. So that first, then the pause (queued in order). True if it did.
        """
        if not xbmc.getCondVisibility('Player.Forwarding | Player.Rewinding'):
            if not self._seekPaused and self.player.playState == self.player.STATE_PLAYING:
                self.setSeekPaused('seeking')
                self.player.control('pause')
            return False
        util.DEBUG_LOG("SeekDialog: Scan: ending Kodi's trick-play, then pausing")
        # Kodi reports the return to 1x as a resume, ahead of the pause (onPlayBackResumed() passes over it)
        self.setSeekPaused('trickplay')
        xbmc.executebuiltin('PlayerControl(Play)')
        xbmc.executebuiltin('PlayerControl(Play)')
        return True

    def _scanLoop(self, scan):
        try:
            while not util.MONITOR.waitForAbort(self.SCAN_TICK):
                # a scan's video stays paused: should Kodi's FF/RW have sped it up after all (its speed change not
                # yet in when startScan() looked), put that right
                if xbmc.getCondVisibility('Player.Forwarding | Player.Rewinding'):
                    self.endTrickPlay()
                with self._scanLock:
                    if self._scan is not scan:
                        break
                    self.selectedOffset = scan.advance(time.time())
                self.updateProgress(set_to_current=False)
                self.showScanSpeed(scan)
                self.resetTimeout()
        except Exception:
            util.ERROR()

    def _endScan(self):
        """Stops a scan, if one runs, where it's got to: no seek and no resume (doSeek()/resetSeeking() do those)."""
        with self._scanLock:
            if not self._scan:
                return
            self._scan = None
        self._holdDetector.reset()
        self.setProperty('scan.active', '')
        self.setProperty('scan.label', '')
        self.setProperty('scan.direction', '')

    def showScanSpeed(self, scan):
        """The OSD's scan speed: scan.label ("4x") and scan.direction, for its icon - none at 0x."""
        self.setProperty('scan.label', scan.label)
        self.setProperty('scan.direction', {seek_scan.FORWARD: 'forward', seek_scan.BACK: 'back'}.get(scan.direction, ''))

    def applyScan(self, play=False):
        """
        Seeks to where the scan's shown. OK plays on from there if the scan paused the video, or leaves it paused;
        Play/Pause always plays - Kodi's resuming the video itself (onPlayBackResumed()), and the seek plays wherever
        that's got to.
        """
        self._endScan()
        util.DEBUG_LOG("SeekDialog: Scan applied at {} (play: {})", self.selectedOffset, play)
        if play:
            self._playPauseInputAt = time.time()
            self.handler.unPauseAfterSeek = True
        self.resetAutoSeekTimer(None)
        self.doSeek()
        self.hideOSD()

    def cancelScan(self):
        """Back: no seek, the bar back on the video and, if the scan paused it, the video playing on."""
        util.DEBUG_LOG("SeekDialog: Scan cancelled")
        self.resetSeeking()
        self.updateProgress()
        # the OSD stays up on the timeline, where focus arrived during the scan without onFocus() setting it up
        self.refreshQueueRow()
        self.syncRows()
        self.updateRowHint(self.MAIN_BUTTON_ID)

    def handleDialog(self, func):
        self.hasDialog = True
        hideFast = False
        try:
            hideFast = func()
        finally:
            self.resetTimeout(fast=hideFast)
            self.hasDialog = False

    def videoSettingsHaveChanged(self):
        changed = AttributeDict(video=False, audio=False, subtitle=False, reload=False)
        if self.player.video.settings.prefOverrides != self.initialVideoSettings:
            changed.video = True
            changed.reload = True
        if self.player.video.selectedAudioStream() != self.initialAudioStream:
            changed.audio = True
            if not self.isDirectPlay:
                changed.reload = True

        if changed.video or changed.audio:
            self.initialVideoSettings = dict(self.player.video.settings.prefOverrides)
            self.initialAudioStream = self.player.video.selectedAudioStream()

        sss = self.currentSubtitleStream()
        if sss != self.initialSubtitleStream:
            util.DEBUG_LOG("Subtitle changed from {} to {} (deselect: {})", self.initialSubtitleStream, sss,
                           util.getSetting("disable_subtitle_languages"))
            self.initialSubtitleStream = sss
            changed.subtitle = True
            if self.isTranscoded:
                changed.reload = True

        return changed

    # Repeat and shuffle, for the Settings dialog's rows (playersettings.py) - once the OSD's own buttons.

    def repeatMode(self):
        """'off', 'all' or 'one': the play queue's, or Kodi's own without one."""
        pl = self.handler.playlist
        if pl:
            return pl.isRepeatOne and 'one' or pl.isRepeat and 'all' or 'off'
        if xbmc.getCondVisibility('Playlist.IsRepeatOne'):
            return 'one'
        if xbmc.getCondVisibility('Playlist.IsRepeat'):
            return 'all'
        return 'off'

    def setRepeatMode(self, mode):
        pl = self.handler.playlist
        if pl:
            # repeat one is isRepeatOne alone, not with isRepeat
            pl.setRepeat(mode == 'all', one=mode == 'one')
            if mode == 'off':
                self.updateProperties()
            else:
                pl.refresh(force=True)
        else:
            xbmc.executebuiltin('PlayerControl({0})'.format(
                {'off': 'RepeatOff', 'all': 'RepeatAll', 'one': 'RepeatOne'}[mode]))

    def canShuffle(self):
        return bool(self.handler.playlist)

    def isShuffled(self):
        return bool(self.handler.playlist and self.handler.playlist.isShuffled)

    def toggleShuffle(self):
        """Shuffles or unshuffles the play queue; returns the state asked for (a server play queue only takes it
        on the server's answer)."""
        shuffle = not self.isShuffled()
        self.handler.playlist.setShuffle(shuffle)
        return shuffle

    def optionsButtonClicked(self):  # Button currently commented out.
        pass
        # options = []

        # options.append({'key': 'kodi_video', 'display': 'Video Options'})
        # options.append({'key': 'kodi_audio', 'display': 'Audio Options'})

        # choice = dropdown.showDropdown(options, (1360, 1060), close_direction='down', pos_is_bottom=True, close_on_playback_ended=True)

        # if not choice:
        #     return

        # if choice['key'] == 'kodi_video':
        #     xbmc.executebuiltin('ActivateWindow(OSDVideoSettings)')
        # elif choice['key'] == 'kodi_audio':
        #     xbmc.executebuiltin('ActivateWindow(OSDAudioSettings)')

    def subtitleButtonClicked(self):
        """
        The Subtitles button: the Settings dialog's Subtitles picker (playersettings.showSubtitlesDialog), tall at
        the right - Off, the streams, Download subtitles, and Subtitle Delay and auto-sync where they apply. A stream
        is applied as the Settings dialog's are (applyVideoSettingsChanges()); Download runs downloadSubtitles(),
        which asks Plex or Kodi as the setting says, over the picker and back to it.
        It was a menu of its own: Download, Subtitle Delay, Previous/Next, auto-sync and Enable/Disable.
        """
        choice = playersettings.showSubtitlesDialog(self.player.video, session_id=self.handler.sessionID, side=True,
                                                    download=self.downloadSubtitles, player=self)
        if choice is playersettings.SUBTITLE_DELAY:
            self.subtitleDelay()
            return
        if choice is playersettings.SUBTITLE_AUTO_SYNC:
            self.toggleSubtitleAutoSync()
            return
        return self.applyVideoSettingsChanges()

    def subtitleDelay(self):
        """Kodi's subtitle delay slider, the OSD out of its way."""
        self.hideOSD()
        self.lastSubtitleNavAction = "delay"
        builtin.Action('SubtitleDelay')

    def toggleSubtitleAutoSync(self, hide_osd=True):
        """The playing subtitle's auto-sync on or off, for this session."""
        sss = self.player.video.selectedSubtitleStream()
        if not sss:
            return
        should_auto_sync = not sss.should_auto_sync_unforced

        # force auto sync for session
        if sss.force_auto_sync is not None:
            sss.force_auto_sync = not sss.force_auto_sync
        else:
            sss.force_auto_sync = should_auto_sync
        sss.should_auto_sync = should_auto_sync
        util.DEBUG_LOG("Setting subtitle auto-sync for session to: {}".format(sss.should_auto_sync))

        # self.player.video isn't the same as the mediachoice representation
        if self.player.playerObject.choice.subtitleStream:
            self.player.playerObject.choice.subtitleStream.should_auto_sync = sss.should_auto_sync
            self.player.playerObject.choice.subtitleStream.force_auto_sync = sss.force_auto_sync
        if hide_osd and self.player.playState == self.player.STATE_PLAYING:
            self.hideOSD()
        if self.isDirectPlay:
            self.setSubtitles(honor_forced_subtitles_override=False, honor_deselect_subtitles=False)
        else:
            self.doSeek(self.trueOffset(), settings_changed=True)
        self.lastSubtitleNavAction = "auto_sync"

    def downloadSubtitles(self):
        """
        Subtitles from Plex or Kodi's own search, as the subtitle_download_from setting says (or asking). Run from
        the Subtitles picker, left open beneath: the OSD stays as it is (Kodi's search window hides it).
        """
        subs_dl_source = util.getSetting('subtitle_download_from')
        if subs_dl_source == 'ask':
            button = optionsdialog.show(
                T(33693, 'Download subtitles using'),
                T(33704, 'Using which service?'),
                'Plex',
                'Kodi'
            )

            subs_dl_source = button == 0 and 'plex' or 'kodi'


        if subs_dl_source == 'plex':
            was_playing = False
            if self.player.playState == self.player.STATE_PLAYING:
                was_playing = True
                self.player.pause()
            downloaded = self.downloadPlexSubtitles(self.player.video, side=True)
            if downloaded:
                self.setSubtitles(honor_forced_subtitles_override=False,
                                  honor_deselect_subtitles=False, ref=None)
            elif downloaded is None:
                if util.getSetting('subtitle_download_fallback'):
                    subs_dl_source = 'kodi'
            if was_playing and self.player.playState == self.player.STATE_PAUSED:
                self.player.pause()

        if subs_dl_source == 'kodi':
            if self.handler and self.handler.player and self.handler.player.playerObject \
                    and util.getSetting('calculate_oshash'):
                meta = self.handler.player.playerObject.metadata
                if not meta.size:
                    util.LOG("Can't calculate OpenSubtitles hash because we're transcoding")

                else:
                    oss_hash = util.getOpenSubtitlesHash(meta.size, meta.streamUrls[0])
                    if oss_hash:
                        util.DEBUG_LOG("OpenSubtitles hash: {}", oss_hash)
                        util.setGlobalProperty("current_oshash", oss_hash, base='videoinfo.{0}')
            else:
                util.setGlobalProperty("current_oshash", '', base='videoinfo.{0}')
            self.lastSubtitleNavAction = "download"

            # remove the Year info from the current video info tag for better OSS search results
            t = self.player.getVideoInfoTag()
            changed_info_tag = False
            item = xbmcgui.ListItem()
            item.setPath(self.player.getPlayingFile())
            if t:
                year = t.getYear()
                if year:
                    if util.KODI_VERSION_MAJOR >= 20:
                        vi = item.getVideoInfoTag()
                        vi.setYear(0)
                    else:
                        item.setInfo("video", {"year": 0})
                    util.DEBUG_LOG("Removing videoInfo year for subtitle search")
                    self.player.updateInfoTag(item)
                    changed_info_tag = year

            builtin.ActivateWindow('SubtitleSearch')
            # wait for the window to activate
            while not xbmc.getCondVisibility('Window.IsActive(SubtitleSearch)'):
                util.MONITOR.waitForAbort(0.1)
            # wait for the window to close
            while xbmc.getCondVisibility('Window.IsActive(SubtitleSearch)'):
                util.MONITOR.waitForAbort(0.1)

            if changed_info_tag:
                if util.KODI_VERSION_MAJOR >= 20:
                    vi = item.getVideoInfoTag()
                    vi.setYear(changed_info_tag)
                else:
                    item.setInfo("video", {"year": changed_info_tag})
                self.player.updateInfoTag(item)

    def vs10ButtonClicked(self):
        # amlogic.vs10.mode.raw values: 0/1 = Dolby Vision, 2 = HDR10, 3 = SDR, 5 = Original
        current_mode = xbmc.getInfoLabel('Player.Process(amlogic.vs10.mode.raw)')
        check = 'script.plex/indicators/tick.png'  # the option pickers' tick

        options = [
            {'key': 'dv',           'display': 'Dolby Vision',  'indicator': current_mode in ('0', '1') and check or ''},
            {'key': 'hdr10',        'display': 'HDR10',          'indicator': current_mode == '2' and check or ''},
            {'key': 'sdr',          'display': 'SDR',            'indicator': current_mode == '3' and check or ''},
            {'key': 'original',     'display': 'Original',       'indicator': current_mode == '5' and check or ''},
            {'key': 'process_info', 'display': 'Player Info',    'indicator': '', 'separator': True},
        ]

        choice = dropdown.showDropdown(
            options,
            (self.DROPDOWN_X, self.DROPDOWN_BOTTOM),
            pos_is_bottom=True,
            close_on_playback_ended=True,
            with_indicator=True,
            header=T(34090, 'VS10 Mode'),
            dialog_class=dropdown.CardDropdownDialog
        )

        if not choice:
            return

        if choice['key'] == 'process_info':
            xbmc.executebuiltin('ActivateWindow(playerprocessinfo)')
        else:
            xbmc.executebuiltin('Action(vs10.{})'.format(choice['key']))

    def toggleSubtitles(self):
        """
        Used for subtitle toggling from button press or subtitle toggle menu
        """
        if xbmc.getCondVisibility('VideoPlayer.SubtitlesEnabled') and self.player.video.hasSubtitle:
            self.disableSubtitles()
            return False
        else:
            self.enableSubtitles()
            return True

    def disableSubtitles(self):
        self.player.video.disableSubtitles(sync_to_server=False)
        self.setSubtitles()
        if self.isTranscoded:
            self.doSeek(self.trueOffset(), settings_changed=True)

    def enableSubtitles(self):
        stream = self.player.video.enableSubtitles(sync_to_server=False)
        self.setSubtitles()
        util.showNotification(str(stream), time_ms=1500, header=util.T(32396, "Subtitles"))
        if self.isTranscoded:
            self.doSeek(self.trueOffset(), settings_changed=True)

    def cycleSubtitles(self, forward=True):
        """
        Selects the first subtitle or the next one
        """
        stream = self.player.video.cycleSubtitles(forward=forward, sync_to_server=False)
        self.setSubtitles(honor_forced_subtitles_override=False, honor_deselect_subtitles=False)
        util.showNotification(str(stream), time_ms=1500, header=util.T(32396, "Subtitles"))
        if self.isTranscoded:
            self.doSeek(self.trueOffset(), settings_changed=True)

    def currentSubtitleStream(self):
        """The selected subtitle stream as videoSettingsHaveChanged() compares it."""
        return self.player.video.selectedSubtitleStream(
            deselect_subtitles=getNativeLanguages(util.getSetting("disable_subtitle_languages") or []))

    def setSubtitles(self, do_sleep=False, honor_forced_subtitles_override=False, honor_deselect_subtitles=False,
                     ref="_current_subtitle_idx"):
        self.handler.setSubtitles(do_sleep=do_sleep, honor_forced_subtitles_override=honor_forced_subtitles_override,
                                  honor_deselect_subtitles=honor_deselect_subtitles, ref=ref)
        # What's on screen now is the baseline videoSettingsHaveChanged() compares with: set from anywhere but a
        # settings change (a download, the subtitle keys, auto-sync), it was left behind - then choosing what it had
        # been (Off, after a download into a video that had none) looked like no change, and nothing turned it off.
        self.initialSubtitleStream = self.currentSubtitleStream()
        if self.player.video.current_subtitle_is_embedded and util.CE_NEEDS_EMBEDDED_SEEKBACK:
            # this is an embedded stream, seek back a second after setting the subtitle due to long standing kodi
            # issue: https://github.com/xbmc/xbmc/issues/21086
            util.DEBUG_LOG("Switching embedded subtitle stream, seeking due to Kodi issue #21086")

            # true offset can be 0, which might lead to an infinite loop, seek to 100ms at least.
            if self.handler.seekOnStart is not None:
                util.DEBUG_LOG("Waiting for seekOnStart to apply: {}", self.handler.seekOnStart)

            waited = 0
            while self.handler.seekOnStart is not None and waited < 100 and not util.MONITOR.abortRequested():
                util.MONITOR.waitForAbort(0.1)
                waited += 1

            if waited < 100:
                seekBack = 1500 if self.useAlternateSeek else 100
                self.doSeek(max(self.trueOffset() - seekBack, seekBack, 0))
                return
            util.LOG("Tried switching embedded subtitle stream to the correct one, but we've waited too long for "
                      "seekOnStart.")

    def showSettings(self):
        with self.propertyContext('settings.visible'):
            playersettings.showDialog(self.player.video, via_osd=True, parent=self)

        return self.applyVideoSettingsChanges()

    def applyVideoSettingsChanges(self):
        """
        Whatever the Settings dialog or a picker changed - video, audio, subtitles - applied to playback,
        restarting it when that's the only way. Returns whether the OSD should hide fast (handleDialog()).
        """
        changed = self.videoSettingsHaveChanged()
        any_changes = any(changed.values())

        if any_changes:
            if not changed.reload:
                if changed.subtitle:
                    self.setSubtitles(do_sleep=False)
                    self.lastSubtitleNavAction = "forward"

                if changed.audio:
                    self.handler.setAudioTrack()

                oldTranscoded = self.player.playerObject.metadata.isTranscoded

                # check if we need to restart
                self.player.playerObject.rebuild(self.player.video)

                # ping server to update activity/session
                self.player.playerObject.getServerDecision()

                if oldTranscoded == self.player.playerObject.metadata.isTranscoded:
                    # On CoreELEC changing the audio stream causes the audio to stutter or delay
                    # so this small seek helps sync things back up.  But we also need to pause the
                    # video for a short time if it's playing or the seek doesn't work
                    if self.useAlternateSeek and changed.audio:
                        if not xbmc.getCondVisibility('Player.Paused'):
                            self.videoPausedForAudioStreamChange = True
                            self.handler.player.control('pause')
                        self.doSeek(offset=max(self.handler.player.getTime() * 1000 - 1500, 1500))
                    return True

            util.LOG("Media settings have changed and are not directly applicable, restarting video: {}", changed)
            self.doSeek(self.trueOffset(), settings_changed=True)
            return False
        return True

    def beginSeeking(self):
        # Enters seek mode at selectedOffset. This used to be setBigSeekShift(), which also slid the 12-dot big-seek
        # row along the bar and only set _seeking when a dot matched - always, as the first dot sat at 0.
        if self.selectedOffset is None:
            return
        self._seeking = True

    def syncRows(self):
        """
        Keeps the card rows on what's playing - the chapters on the last chapter starting at or before the current
        position, the play queue on its playing item - while they're out of sight. A row is drawn but faded to nothing
        while it doesn't have focus (includes/osd_card_row.xml.tpl), so a selection made now scrolls into place unseen;
        made as the row took focus, the scroll played out during its fade-in. Kodi only runs a list's scroll while it's
        drawn, which is why a row can't simply be hidden. Leaves alone the row that has focus, and one still fading out
        after focus left it (_rowSyncTimer calls this again as that fade ends). Calls Kodi only when a position changes.
        """
        # (a button's first onFocus can arrive before onFirstInit has made the rows)
        if not self.initialized:
            return

        now = time.time()
        for listID, control in ((self.BIG_SEEK_LIST_ID, self.bigSeekControl),
                                (self.QUEUE_LIST_ID, self.queueControl)):
            if self.lastFocusID == listID or not control.items:
                continue
            if now - self._rowLeftAt.get(listID, 0) < self.ROW_FADE_OUT:
                continue

            if listID == self.BIG_SEEK_LIST_ID:
                offset = self.trueOffset()
                pos = 0
                for i, mli in enumerate(control.items):
                    if mli.dataSource > offset:
                        break
                    pos = i
            else:
                pos = self._queuePlayingPos

            if pos != self._rowPos.get(listID):
                self._rowPos[listID] = pos
                control.selectItem(pos)

    def refreshQueueRow(self):
        """
        (Re)builds the play queue row, if anything has changed since it was last built: a new video, or the queue
        itself (updateProperties(), on the queue's change events). Built here - on a button's focus, the only way down
        into it - rather than with each video: list items cost a GUI call or several apiece, and most playback never
        opens it. Only for a queue of more than one item; otherwise the row stays empty, and so unfocusable.
        """
        if not self.initialized or not self._queueRowStale:
            return
        self._queueRowStale = False

        items = []
        playingPos = 0
        pq = self.handler.playlist
        if pq:
            entries = list(pq.items())
            if len(entries) > 1:
                playing = self.player.video.ratingKey
                for index, pi in enumerate(entries):
                    mli = self.createQueueItem(index, pi)
                    if not mli:
                        continue
                    if pi.ratingKey == playing:
                        mli.setProperty('playing', '1')
                        playingPos = len(items)
                    items.append(mli)

        self.queueControl.reset()
        self.queueControl.addItems(items)
        self._queuePlayingPos = playingPos
        self._rowPos.pop(self.QUEUE_LIST_ID, None)
        self.setBoolProperty('has.queue', bool(items))

    def createQueueItem(self, index, pi):
        """
        A play queue row item: the art, the title, and under it (the 'sub' property) an episode's S/E, show and length
        or a film's year and length, bullet-separated, any that's missing left out. Episodes follow the no-spoilers
        settings, as the play queue popup this row replaced did - unwatched ones can have their title hidden and their
        art blurred. data_source is the item's position in the queue, which is what queueItemSelected() hands to
        playAt.
        """
        durationMs = pi.duration.asInt()
        duration = durationMs and util.durationToShortText(durationMs, noSpaces=True) or ''
        if pi.type == 'episode':
            title = pi.title
            sub = (u'{0} \u2022 {1}'.format(T(32310, 'S{}').format(pi.parentIndex), T(32311, 'E{}').format(pi.index)),
                   u'{0}'.format(pi.grandparentTitle or ''), duration)
            thumbnailOpts = {}
            if self.getNoSpoilers(pi) != "off":
                hideSpoilers = self.hideSpoilers(pi)
                if hideSpoilers:
                    if self.noTitles:
                        title = T(33008, '')
                    thumbnailOpts = self.getThumbnailOpts(pi, hide_spoilers=hideSpoilers)
            thumb = pi.thumb.asTranscodedImageURL(*self.CHAPTER_THUMB_DIM, **thumbnailOpts)
        elif pi.type in ('movie', 'clip'):
            title = pi.title
            sub = (pi.year and u'{0}'.format(pi.year) or '', duration)
            thumb = pi.art.asTranscodedImageURL(*self.CHAPTER_THUMB_DIM)
        else:
            return None

        return kodigui.ManagedListItem(title, thumbnailImage=thumb, data_source=index,
                                       properties={'sub': u' • '.join(part for part in sub if part)})

    def updateRowHint(self, controlID):
        """
        The text of the OSD's bottom line naming what's below (the template's ROW HINT): from anywhere above the rows,
        both rows' names or whichever exists; from the chapters, the play queue's. Focus moving into the queue row, or
        to 800 as the OSD closes, leaves the text as it was: the hint fades out there, and changing the text would
        make it vanish while the chevron beside it was still fading.
        """
        if not self.initialized or controlID in (self.QUEUE_LIST_ID, self.NO_OSD_BUTTON_ID):
            return

        hasQueue = bool(self.queueControl.items)
        if controlID == self.BIG_SEEK_LIST_ID:
            if not hasQueue:
                return
            text = T(35079, 'Play queue')
        else:
            text = u'/'.join(name for name, has in ((T(33611, 'Chapters'), bool(self.bigSeekControl.items)),
                                                     (T(35079, 'Play queue'), hasQueue)) if has)

        if text and text != self._rowHint:
            self._rowHint = text
            self.setProperty('rows.hint', text)

    def queueItemSelected(self):
        # OK on a play queue item plays it from the start, as the popup this row replaced did (resume=False)
        mli = self.queueControl.getSelectedItem()
        if not mli:
            return
        self.hideOSD()
        self.player.trigger("action", action="playAt", pos=mli.dataSource)

    def bigSeekSelected(self):
        # this gets called when a click action happened on the bigSeek, defer the actual action to onFocus
        # by setFocusId(MAIN)

        self.bigSeekChanged = True
        if self.showChapters:
            self.resetAutoSeekTimer(None)
            self._navigatedViaMarkerOrChapter = True

            sel = self.bigSeekControl.getSelectedItem()
            if self.bigSeekControl.isLastItem(sel):
                self.selectedOffset = sel.dataSource - FINAL_MARKER_NEGOFF
            else:
                self.selectedOffset = sel.dataSource + MARKER_OFF

            # the onFocus action might take a couple of ms and might be overridden by onAction, store separately
            self.bigSeekChanged = self.selectedOffset

        self.setFocusId(self.MAIN_BUTTON_ID)

    def setTitleLines(self):
        """
        The OSD's title, two lines (the template's osd.title and osd.subtitle): a film's title over its year and
        runtime; an episode's title over its S/E, show and runtime - the play queue row's second line
        (createQueueItem()). With the episode title hidden for spoilers (hide.title), the show's name on the first
        line instead, and not again on the second.
        """
        v = self.player.video
        durationMs = v.duration.asInt() or self._duration
        runtime = durationMs and util.durationToShortText(durationMs, noSpaces=True) or ''
        if v.type == 'episode':
            hideTitle = self.hideTitles
            show = u'{0}'.format(v.grandparentTitle or '')
            title = show if hideTitle else u'{0}'.format(v.title or '')
            sub = (u'{0} \u2022 {1}'.format(T(32310, 'S{}').format(v.parentIndex), T(32311, 'E{}').format(v.index)),
                   '' if hideTitle else show, runtime)
        else:
            title = u'{0}'.format(v.title or '')
            sub = (v.year and u'{0}'.format(v.year) or '', runtime)
        self.setProperty('osd.title', title)
        self.setProperty('osd.subtitle', u' \u2022 '.join(part for part in sub if part))

    def updateProperties(self, **kwargs):
        if not self.started:
            return

        if self.fromSeek:
            self.setFocusId(self.MAIN_BUTTON_ID)
            self.fromSeek = 0

        v = self.player.video
        is_show = v.type == 'episode'

        self.setProperty('has.bif', self.bifURL and '1' or '')
        self.setProperty('video.title', self.title)
        self.setProperty('video.title2', self.title2)
        self.setProperty('is.show', is_show and '1' or '')
        self.setProperty('media.show_ends', self.showItemEndsInfo and '1' or '')
        self.setProperty('time.ends_label', self.showItemEndsLabel and (util.T(32543, 'Ends at')) or '')
        self.setBoolProperty('no.osd.hide_info', self.no_time_no_osd_spoilers)

        self.setBoolProperty('hide.title', self.hideTitles)
        self.setTitleLines()

        if self.isDirectPlay:
            self.setProperty('time.fmt.ends', util.timeFormatKN.replace(":ss", ""))
            # in directPlay we use the timeLeft display directly from Kodi, which only knows about the current part
            # add the remaining parts' time
            timeAdd = ''
            if self.hasMoreParts:
                plength = 0
                part = self.player.playerObject.metadata.nextPart

                while part:
                    plength += part.partDuration
                    part = part.nextPart

                if plength:
                    timeAdd = " (+{})".format(util.durationToShortText(plength, shortHourMins=True))

            self.setProperty('time.add', timeAdd)

        self.setBoolProperty('direct.play', self.isDirectPlay)

        # the play queue (or which of its items plays) may have changed: rebuild its row on the next button focus
        self._queueRowStale = True

        pq = self.handler.playlist
        if pq:
            self.setProperty('has.playlist', '1')
            self.setProperty('pq.isRemote', pq.isRemote and '1' or '')
            self.setProperty('pq.repeat', pq.isRepeat and '1' or '')
            self.setProperty('pq.repeat.one', pq.isRepeatOne and '1' or '')
            self.setProperty('pq.shuffled', pq.isShuffled and '1' or '')
        else:
            self.setProperties(('pq.isRemote', 'pq.repeat', 'pq.shuffled', 'has.playlist'),
                               '')

        self.updateCurrent()

    def updateChapters(self):
        items = []

        # replace bigSeek with chapters or markers if possible
        if self.showChapters:
            # one header whatever the chapters' source (file, markers or both) - it used to name the source, in
            # capitals, and claimed "combined" even when every marker was dropped as overlapping a chapter
            self.setProperty('chapters.label', T(33611, 'Chapters'))
            chaps = []
            chapOffsets = []
            markerOffsets = set()
            if self.chapters:
                for index, chapter in enumerate(self.chapters):
                    thumb = (not self.hidePreviews and chapter.thumb
                             and chapter.thumb.asTranscodedImageURL(*self.CHAPTER_THUMB_DIM) or None)
                    st = chapter.startTime()
                    chapOffsets.append(st)
                    # a file's chapter names can tell the story ("The Betrayal"): hidden with episode titles
                    name = not self.hideTitles and chapter.tag or T(33607, 'Chapter {}').format(index + 1)
                    chaps.append((st, thumb, name))

            # fake chapters by using markers
            if util.getUserSetting('virtual_chapters', True) and self.markers and (not self.chapters or util.getUserSetting('combined_chapters', True)):
                creditsCounter = 0
                preparedMarkers = []
                for markerDef in self.markers:
                    marker = markerDef["marker"]
                    if marker:
                        if markerDef["marker_type"] == "intro":
                            preparedMarkers.append((marker.startTimeOffset, T(33608, "Intro"), False))
                            preparedMarkers.append((marker.endTimeOffset, T(33610, "Main"), False))

                        elif markerDef["marker_type"] == "credits":
                            creditsCounter += 1
                            if creditsCounter > 1 and getattr(marker, "final", False):
                                label = T(33635, "Final Credits")
                            else:
                                label = T(33609, "Credits") + "{}"
                            preparedMarkers.append((marker.startTimeOffset, label, True))

                # add staggered virtual markers
                #preparedMarkers.append((int(self.duration * 0.25), "25 %", False))
                #preparedMarkers.append((int(self.duration * 0.50), "50 %", False))
                #preparedMarkers.append((int(self.duration * 0.75), "75 %", False))

                credCnt = 1
                for offset, label, credits in sorted(preparedMarkers):
                    # filter intersections
                    skipMarker = False
                    for cOffset in chapOffsets:
                        if offset - MARKER_CHAPTER_OVERLAP_THRES <= cOffset <= offset + MARKER_CHAPTER_OVERLAP_THRES:
                            skipMarker = True
                            break

                    # skip marker if we're overlapping with any chapter
                    if skipMarker:
                        continue

                    bifUrl = not self.hidePreviews and self.previewImage(offset)[0] or None
                    markerOffsets.add(offset)
                    chaps.append((offset, bifUrl,
                                  label.format(" #{}".format(credCnt) if credits and creditsCounter > 1 else "")))

                    if credits:
                        credCnt += 1

            for offset, thumb, label in sorted(chaps):
                # time: the chapter's start, under its name - the row's stand-in for the seekbar's time bubble.
                # A marker's card has a preview picture: the server's until the index is in (onPreviewsReady()).
                # spoiler: the card's "hidden" placeholder (includes/osd_card_row.xml.tpl), pictures hidden.
                mli = kodigui.ManagedListItem(data_source=offset, thumbnailImage=thumb, label=label,
                                              properties={'sub': util.simplifiedTimeDisplay(offset),
                                                          'marker_preview': offset in markerOffsets and '1' or '',
                                                          'spoiler': self.hidePreviews and '1' or ''})
                items.append(mli)

        # Without chapters the row stays empty, which also leaves it unfocusable: down from the buttons goes nowhere.
        # (It used to hold 12 evenly spaced big-seek dots.)
        self.bigSeekControl.reset()
        self.bigSeekControl.addItems(items)
        self._rowPos.pop(self.BIG_SEEK_LIST_ID, None)

    def updateCurrent(self, update_position_control=True, atOffset=None):
        ratio = self.trueOffset() / float(self.duration)

        w = None
        if update_position_control:
            w = int(ratio * self.SEEK_IMAGE_WIDTH)
            self.setPlayed(w)

        # update cache/buffer bar
        if util.addonSettings.playerShowBuffer and self.isDirectPlay and util.KODI_VERSION_MAJOR > 18:
            cache_w = int(xbmc.getInfoLabel("Player.ProgressCache")) * self.SEEK_IMAGE_WIDTH // 100
            w = w or self._barWidths.get(self.positionControl, 0)
            self.setBarPercent(self.cacheControl, max(cache_w, w+5))

        if self.isTranscoded:
            to = atOffset if atOffset is not None else self.trueOffset()
            # the direct play times' format (the template's TIMES): no leading zero, the hour only when there is one
            self.setProperty('time.current', util.simplifiedTimeDisplay(to))
            self.setProperty('time.left', util.simplifiedTimeDisplay(self.duration - to))
            self.setProperty('time.end', self.endTimeDisplay(self.duration - to))

        # the timeline focused but not seeking: the time bubble follows playback
        if update_position_control and self.lastFocusID == self.MAIN_BUTTON_ID:
            self.updateProgress(offset=atOffset if atOffset is not None else self.trueOffset(),
                                onlyTimeIndicator=True)

    def endTimeDisplay(self, remaining):
        # the clock time playback ends at, remaining ms from now ("Ends at")
        _fmt = util.timeFormat.replace(":%S", "")

        val = time.strftime(_fmt, time.localtime(time.time() + remaining / 1000))
        if not util.padHour and val[0] == "0" and val[1] != ":":
            val = val[1:]
        return val

    def setBarPercent(self, control, w):
        """
        Fills a SEEKBAR progress control to w px along the bar. They're <reveal> progress controls
        (see the template's SEEKBAR comment) so the rounded mask clips rather than stretches:
        set a percentage, not a width. Info-less, so the value sticks.
        """
        w = max(0, min(w, self.SEEK_IMAGE_WIDTH))
        if self._barWidths.get(control) == w:
            return
        self._barWidths[control] = w

        cap = self._barCaps.get(control)
        if cap:
            # a rounded end: the fill stops BAR_CAP short and its cap's half circle ends at w
            if w >= self.BAR_CAP:
                w -= self.BAR_CAP
                cap.setPosition(w, 0)
            else:
                # within the bar's own rounded left end: that rounds it, no cap (off the bar, below the screen)
                cap.setPosition(0, 2000)
        control.setPercent(w * 100.0 / self.SEEK_IMAGE_WIDTH)

    def setPlayed(self, w):
        self.setBarPercent(self.positionControl, w)


    @property
    def hasMoreParts(self):
        return self.player and self.player.playerObject and self.player.playerObject.hasMoreParts()

    def doSeek(self, offset=None, settings_changed=False, skip_alt_seek_fix=False):
        self._applyingSeek = True
        self._ignoreInput = settings_changed
        offset = self.selectedOffset if offset is None else offset

        if self.countingDownMarker:
            self.displayMarkers(cancelTimer=True)

        self.resetSkipSteps()
        self.updateProgress(offset=offset)

        if self._seekPaused in ('seeking', 'trickplay'):
            # paused for this seek: the handler resumes once it lands (onPlayBackSeek), as after its own alternate
            # seek's pause - or, restarting a transcode, has it start playing (seek())
            self.setSeekPaused('applying')
            self.handler.unPauseAfterSeek = True

        try:
            self.handler.seek(offset, settings_changed=settings_changed, skip_alt_seek_fix=skip_alt_seek_fix)
        finally:
            self.resetSeeking()

    def seekByOffset(self, offset, auto_seek=False, without_osd=False):
        """
        Sets the selected offset and updates the progress bar to visually represent the current seek
        :param offset: offset to seek to
        :param auto_seek: whether to automatically seek to :offset: after a certain amount of time
        :param without_osd: indicates whether this seek was done with or without OSD
        :return:
        """
        if self.selectedOffset is None:
            self.selectedOffset = self.offset
        lastSelectedOffset = self.selectedOffset
        # If we are seeking forward and already past 5 seconds from end, don't seek at all
        if lastSelectedOffset > self.duration - 5000 and offset > 0:
            return False

        # Seeking pauses playback, resumed when the seek lands (doSeek()) or is abandoned (resetSeeking()); already
        # paused, it stays paused.
        if not self._seekPaused and self.player.playState == self.player.STATE_PLAYING:
            self.setSeekPaused('seeking')
            self.player.control('pause')

        self._seeking = True
        self._seekingWithoutOSD = without_osd
        sign = offset > 0 and 1 or -1
        self.selectedOffset += max(abs(offset), self.useAlternateSeek and util.addonSettings.altseekValidSeekWindow or 0) * sign
        # Don't skip past 5 seconds from end
        if self.selectedOffset > self.duration - 5000:
            # offset = +100, at = 80000, duration = 80007, realoffset = 2
            self._forcedLastSkipAmount = self.duration - 5000 - lastSelectedOffset
            self.selectedOffset = self.duration - 5000
        # Don't skip back past 1 (0 is handled specially so seeking to 0 will not do a seek)
        elif self.selectedOffset < 1:
            # offset = -100, at = 5, realat = -95, realoffset = 1 - 5 = -4
            self._forcedLastSkipAmount = 1 - lastSelectedOffset
            self.selectedOffset = 1

        self.updateProgress(set_to_current=False, no_osd=without_osd)
        # after updateProgress(): the seek look and the seek point's times show with this step's values
        self.setProperty('button.seek', '1')
        self.beginSeeking()
        # the skip button follows the seek point straight away, not on the next tick (about a second)
        if self.initialized and not (self.handler.seekOnStart or self.handler.waitingForSOS or self.handler.seekBackTo):
            try:
                self.displayMarkers(offset=self.selectedOffset)
            except Exception:
                util.ERROR()
        if auto_seek:
            self.resetAutoSeekTimer()
        return True

    def seekMouse(self, action, without_osd=False, preview=False):
        x = self.mouseXTrans(action.getAmount1())
        y = self.mouseYTrans(action.getAmount2())
        if not (self.BAR_Y <= y <= self.BAR_BOTTOM):
            return

        if not (self.BAR_X <= x <= self.BAR_RIGHT):
            return

        self._seeking = True
        self._seekingWithoutOSD = without_osd

        self.selectedOffset = int((x - self.BAR_X) / float(self.SEEK_IMAGE_WIDTH) * self.duration)
        if not preview:
            self.doSeek()
            if not xbmc.getCondVisibility('Window.IsActive(videoosd) | Player.Rewinding | Player.Forwarding'):
                self.hideOSD()
        else:
            self.updateProgress(set_to_current=False)
            self.setProperty('button.seek', '1')


    @property
    def duration(self):
        try:
            return self._duration or self.handler.currentDuration()
        except RuntimeError:  # Not playing
            return 1

    def startPreviews(self):
        """
        Starts this item's preview index downloads (previews.store) once it's playing - after any resume seek, so
        they stay out of start-up buffering - one per part. Called from tick(), so a second or so in; once an item.
        """
        if self._previewsStarted or not self.hasBif or self.hidePreviews or self.handler.waitingForSOS:
            return
        player = self.handler.player
        playerObject = player.playerObject
        if not playerObject or player.isExternal or not xbmc.getCondVisibility('Player.HasVideo'):
            return
        self._previewsStarted = True
        parts = []
        for part in playerObject.media.parts:
            path = part.getIndexPath("hd") or part.getIndexPath("sd")
            if path:
                parts.append((part.id, path))
        if parts:
            util.DEBUG_LOG("SeekDialog: downloading the preview index of {} part(s)", len(parts))
            previews.store.start(parts, playerObject.item.getServer(), on_ready=self.onPreviewsReady)

    def localPreview(self, offset):
        """The downloaded preview at offset (ms into the item, across its parts), or None while there isn't one."""
        playerObject = self.handler.player.playerObject
        if not playerObject:
            return None
        found = previews.part_at([(part.id, part.duration.asInt()) for part in playerObject.media.parts], offset)
        return found and previews.store.picture(*found) or None

    def previewImage(self, offset, scanning=False):
        """
        The preview picture at offset, and whether it's local: the downloaded index's (localPreview()), else one
        from the server (PlexPlayer.getBifUrl()) - a scan's at one per SCAN_BIF_STEP, so passing over the same
        stretch reuses what Kodi has fetched.
        """
        local = self.localPreview(offset)
        if local:
            return local, True
        if scanning:
            offset -= offset % self.SCAN_BIF_STEP
        return self.handler.player.playerObject.getBifUrl(offset), False

    def spoilerHiding(self, video):
        """
        (hide previews, hide titles) for video (docs/spoiler-previews.md): the "No TV spoilers" options
        "Hide preview thumbnails and chapter images" (stored as blur_chapters, its name when it blurred them) and
        "No unplayed episode titles" (the OSD's episode title, and file chapters' names), for an episode they cover -
        unwatched, or not fully watched with "in progress", outside the allowed genres (SpoilersMixin.hideSpoilers()).
        Decided once an item, in setup(), so passing the watched mark mid-play reveals nothing.
        """
        previewsOpt = 'blur_chapters' in self.no_spoilers
        titlesOpt = 'no_unwatched_episode_titles' in self.no_spoilers
        if not (previewsOpt or titlesOpt):
            return False, False
        try:
            hide = self.hideSpoilers(video, use_cache=False)
        except Exception:
            # the genres can need a request; hiding is the safe way to be wrong
            util.ERROR()
            hide = video.type == 'episode'
        return previewsOpt and hide, titlesOpt and hide

    def onPreviewsReady(self):
        """A part's index is in (on its download's thread): the chapter row's marker cards, built from the server's
        pictures, switch to the downloaded ones."""
        if not self.initialized or self.hidePreviews:
            return
        for mli in self.bigSeekControl:
            if mli.getProperty('marker_preview'):
                local = self.localPreview(mli.dataSource)
                if local and mli.thumbnailImage != local:
                    mli.setThumbnailImage(local)

    def updateProgress(self, set_to_current=True, offset=None, onlyTimeIndicator=False, no_osd=False):
        """
        Updates the progress bars (seek and position) and the currently-selected-time-label for the current position or
        seek state on the timeline.
        :param set_to_current: if True, sets both the position bar and the seek bar to the currently selected position,
                               otherwise we're in seek mode, whereas one of both bars move relatively to the currently
                               selected position depending on the direction of the seek
        :return: None
        """
        if not all((self.initialized, self.handler.player, self.handler.player.playerObject)):
            return

        offset = offset if offset is not None else \
            self.selectedOffset if self.selectedOffset is not None else self.trueOffset()
        ratio = offset / float(self.duration)
        w = int(ratio * self.SEEK_IMAGE_WIDTH)

        current_w = int(self.offset / float(self.duration) * self.SEEK_IMAGE_WIDTH)

        # the thumbnail's left edge runs from the bar's left end to its width short of its right end
        bifx = (w - int(ratio * self.BIF_WIDTH)) + self.BAR_X
        # the seek marker, centred on the bar at the point
        self.selectionIndicator.setPosition(self.BAR_X + w, self._markerY)

        # a scan keeps its thumbnail until it changes, rather than blanking it ten times a second
        scanning = self._scan is not None
        if not scanning:
            self.setProperty('bif.image', "")
        if onlyTimeIndicator:
            return

        if not no_osd or (no_osd and not self.no_time_no_osd_spoilers):
            if self.hasBif and not self.hidePreviews:
                bifUrl, local = self.previewImage(offset, scanning=scanning)
                setBif = True
                if scanning:
                    now = time.time()
                    setBif = bifUrl != self._scanBifUrl and (local or now - self._scanBifAt >= self.SCAN_BIF_INTERVAL)
                    if setBif:
                        self._scanBifUrl, self._scanBifAt = bifUrl, now
                if setBif:
                    self.setProperty('bif.image', bifUrl or '')
                self.bifImageControl.setPosition(bifx, self._bifY)

        if set_to_current:
            self.setBarPercent(self.seekbarControl, w)
            self.setPlayed(w)
        else:
            # we're seeking
            if not self.selectedOffset:
                return

            # the times either side of the bar show the seek point's while seeking (the template's TIMES)
            remaining = max(0, self.duration - offset)
            self.setProperty('time.seek.current', util.simplifiedTimeDisplay(offset))
            self.setProperty('time.seek.left', util.simplifiedTimeDisplay(remaining))
            self.setProperty('time.seek.end', self.endTimeDisplay(remaining))

            # the played fill (hidden while seeking, by the template) stays at the video's position for after; the
            # gold scrubber in its place runs to the seek point
            self.setPlayed(current_w)
            self.setBarPercent(self.seekbarControl, w)

    def waitForBuffer(self):
        # current filesize in bytes
        size = float(self.handler.player.video.mediaChoice.part.size)

        # current buffer fill percentage
        currentBufferPerc = int(xbmc.getInfoLabel("Player.ProgressCache")) - int(xbmc.getInfoLabel("Player.Progress"))

        # configured buffer size
        bufferBytes = lib.cache.kcm.memorySize * 1024 * 1024

        # wait for the full buffer or for 10% of the file at max
        # a full buffer is typically 30% of the configured cache value
        sensibleBufferPerc = min(bufferBytes / size * 100.0 / 2.8, 10)

        # can wait for buffer?
        # we're relying on integer based percentages coming from kodi's internal ProgressCache.
        # with a typical device buffer of 20-160 MB, this might be less than 1% of available buffer based on the playing
        # media item. If we're below that value, wait for a defined amount of time instead of being smart.
        if sensibleBufferPerc >= 1.0:
            if currentBufferPerc < sensibleBufferPerc:
                # pause
                wasPlaying = False
                if self.player.playState == self.player.STATE_PLAYING:
                    util.DEBUG_LOG("SeekDialog.buffer: Waiting for buffer to reach {} (is: {}), pausing"
                                   .format(sensibleBufferPerc, currentBufferPerc))
                    self.player.pause()
                    wasPlaying = True

                waitedFor = 0
                waitMax = util.addonSettings.bufferWaitMax
                waitExceeded = False
                self.waitingForBuffer = True
                self.showOSD(focusButton=False)
                with busy.BusyClosableMsgContext() as bc:
                    # check for the buffer fill-state every 200ms
                    # this may be canceled by the usual actions;
                    # depending on who receives the cancel action, _abortBufferWait might be set by our onAction
                    # or by the busy window via the context manager
                    try:
                        while not self._abortBufferWait and not bc.shouldClose and waitedFor < waitMax and \
                                (int(xbmc.getInfoLabel("Player.ProgressCache")) -
                                 int(xbmc.getInfoLabel("Player.Progress"))) < sensibleBufferPerc:
                            curBuf = int(xbmc.getInfoLabel("Player.ProgressCache")) - \
                                     int(xbmc.getInfoLabel("Player.Progress"))

                            bc.setMessage("Buffer: {} %".format(int(curBuf / sensibleBufferPerc * 100)))

                            xbmc.sleep(200)
                            waitedFor += 0.2

                            # report buffer state every 10 seconds
                            if int(waitedFor) > 0 and int(waitedFor) % 10 == 0:
                                util.DEBUG_LOG("SeekDialog.buffer: "
                                               "Buffer filled {}/{}".format(curBuf, sensibleBufferPerc))
                    except Exception:
                        # Caught here, not let out: what follows resumes playback, which a failed
                        # wait (an empty progress label, say) would otherwise leave paused.
                        util.ERROR('SeekDialog.buffer: waiting for the buffer failed')

                    # buffer wait canceled via busy window
                    if bc.shouldClose:
                        self._abortBufferWait = True

                    # buffer timed out
                    if waitedFor >= waitMax:
                        waitExceeded = True

                self.waitingForBuffer = False

                if waitExceeded or self._abortBufferWait:
                    if not self._abortBufferWait:
                        util.showNotification(util.T(32917, "Couldn't fill buffer in time ({}s)").format(waitMax),
                                              header="Buffer")
                    self.stop()
                    return True

                if self.player.playState == self.player.STATE_PAUSED and wasPlaying:
                    # resume
                    util.DEBUG_LOG("SeekDialog.buffer: Buffer filled, resuming")
                    self.player.pause()
                    return True
            else:
                util.DEBUG_LOG("SeekDialog.buffer: Buffer already filled, not waiting for buffer")

        else:
            wait = util.addonSettings.bufferInsufficientWait
            util.DEBUG_LOG("SeekDialog.buffer: Buffer is too small for us to see, waiting {} seconds", wait)
            self.waitingForBuffer = True

            wasPlaying = False
            if self.player.playState == self.player.STATE_PLAYING:
                self.player.pause()
                wasPlaying = True

            with busy.BusyClosableMsgContext() as bc:
                try:
                    bc.setMessage("Buffering")
                    util.MONITOR.waitForAbort(wait)
                except Exception:
                    # Caught, as above: this runs from the player's tick.
                    util.ERROR('SeekDialog.buffer: waiting failed')
                finally:
                    # Resume however the wait ended, or playback stays paused.
                    self.waitingForBuffer = False
                    if self.player.playState == self.player.STATE_PAUSED and wasPlaying:
                        self.player.pause()
                return True

    def seekBehind(self):
        to = self.trueOffset()
        # make sure we're at least seeking behind 1500ms when we're using alternate seek
        amount = max(self.resumeSeekBehind, 1500) if self.useAlternateSeek else self.resumeSeekBehind
        if ((not self.resumeSeekBehindOnlyDP or self.isDirectPlay)
                and self.resumeSeekBehind and to > amount):
            util.DEBUG_LOG("SeekDialog: Seeking back from {} to {}", to, to - amount)
            self.doSeek(max(to - amount, 0), skip_alt_seek_fix=True)

    def onPlayBackResumed(self):
        util.DEBUG_LOG("SeekDialog: OnPlaybackResumed")
        if self._ignoreInput:
            self._ignoreInput = False

        # A resume from OK on the timeline or a play/pause key goes back to the video; a pause leaves the OSD up. Decided here, not where the input arrives: Kodi has usually already paused/resumed by
        # the time our onAction/onClick runs, so the player state there can't tell which it was.
        if self._playPauseInputAt and time.time() - self._playPauseInputAt < 3:
            self._playPauseInputAt = None
            if self.osdVisible():
                self.hideOSD()

        if self._seekPaused == 'trickplay':
            # Kodi's speed back to 1x on the way to a scan's pause (endTrickPlay()): not a resume, and the pause
            # that follows is the scan's
            self.setSeekPaused('seeking')
            return

        if self._seekPaused:
            # the end of a pause for seeking - no resume seek-behind for it
            self.setSeekPaused(None)
            self.idleTime = None
            self.ldTimer and self.syncTimeKeeper()
            return

        # the alt seek fix will pause during a seek and resume afterwards if necessary; in that case, don't try any
        # normal shenanigans
        if self.handler and self.handler.pausedForSeek:
            self.handler.pausedForSeek = False
            return

        self.idleTime = None
        self.ldTimer and self.syncTimeKeeper()

        if self.resumeSeekBehind and not self.resumeSeekBehindPause and (
                not self.resumeSeekBehindAfter or
                self.pausedAt and time.time() - self.pausedAt >= self.resumeSeekBehindAfter):
            self.seekBehind()

        self.pausedAt = None

    def onAVChange(self):
        util.DEBUG_LOG("SeekDialog: OnAVChange: DPO: {0}, offset: {1}", self.DPPlayerOffset, self.offset)

        # wait for buffer if we're not expecting a seek
        if not self.handler.seekOnStart and util.getSetting("slow_connection") and not self.waitingForBuffer:
            # fixme: not sure why this is necessary, but something breaks when playing back a next item from playback
            #        that doesn't have a seek value. Adding a slight delay here fixes that. Timing issue?
            xbmc.sleep(100)
            self.tick(waitForBuffer=True)
            return

    def onAVStarted(self):
        util.DEBUG_LOG("SeekDialog: OnAVStarted: DPO: {0}, offset: {1}", self.DPPlayerOffset, self.offset)
        if self._ignoreInput:
            self._ignoreInput = False

        self.ldTimer and self.syncTimeKeeper()

    def onPlayBackStarted(self):
        util.DEBUG_LOG("SeekDialog: OnPlaybackStarted")
        if self._ignoreInput:
            self._ignoreInput = False

        self.ldTimer and self.syncTimeKeeper()

    def onPlayBackPaused(self):
        util.DEBUG_LOG("SeekDialog: OnPlaybackPaused")
        # that play/pause press was a pause (onPlayBackResumed())
        self._playPauseInputAt = None

        if self._seekPaused:
            # paused for seeking: not a pause for the idle stop or the resume seek-behind
            if self._seekPaused == 'resuming':
                # the seek was abandoned before this pause came through
                self.player.control('play')
            return

        if self.handler and self.handler.seekBackTo and not self.handler.seekBackToDone:
            return

        # Need to resume the video when changing streams on CoreELEC
        if self.useAlternateSeek and self.videoPausedForAudioStreamChange:
            self.videoPausedForAudioStreamChange = False
            self.handler.player.control('play')
            return

        self.idleTime = time.time()
        if self.resumeSeekBehindPause and not self.resumeSeekBehindAfter:
            self.seekBehind()
            return

        self.pausedAt = time.time()

    def onPlayBackSeek(self, stime, offset):
        util.DEBUG_LOG("SeekDialog: OnPlaybackSeek: {0}, {1}", stime, offset)
        self.idleTime = None
        self.ldTimer and self.syncTimeKeeper()

    def onPlayBackStopped(self):
        util.DEBUG_LOG("SeekDialog: OnPlayBackStopped")
        self._endScan()
        self.killTimeKeeper()

    def onPlayBackEnded(self):
        util.DEBUG_LOG("SeekDialog: OnPlayBackEnded")
        self._endScan()
        self.killTimeKeeper()

    def onPlayBackFailed(self):
        util.DEBUG_LOG("SeekDialog: OnPlayBackFailed")
        self._endScan()
        self.killTimeKeeper()

    def syncTimeKeeper(self):
        if not self.handler.player.playerObject:
            return

        if not self.handler.player.isExternal:
            self.timeKeeperTime = self.trueOffset()#int(self.handler.player.getTime() * 1000)
        else:
            # special case for external players - we don't know the actual progress, but we can make an educated guess
            # for the start point
            if not self.timeKeeperTime:
                self.timeKeeperTime = self.baseOffset or self.handler.seekOnStart
                if self.timeKeeperTime is None:
                    self.timeKeeperTime = 0

        if not self.timeKeeper:
            self.timeKeeper = plexapp.util.RepeatingCounterTimer(1.0, self.onTimeKeeperCallback)
        self.onTimeKeeperCallback(tick=False)
        self.timeKeeper.reset()

    def killTimeKeeper(self):
        if self.timeKeeper:
            try:
                self.timeKeeper.stop()
                self.timeKeeper = None
            except:
                util.ERROR("Couldn't stop timeKeeper")

    def onTimeKeeperCallback(self, tick=True):
        """
        called by playbackTimer periodically, sets playback time/ends in UI
        """
        force_tick = self.handler.player.isExternal

        # we might be a little early on slower systems
        if not force_tick:
            if not self.started or not self.handler.player.playerObject:
                return

            if self.stopPlaybackOnIdle:
                if self.idleTime and time.time() - self.idleTime >= self.stopPlaybackOnIdle:
                    util.LOG("Player has been idle for {}s, stopping.", int(time.time() - self.idleTime))
                    self.handler.stoppedManually = True
                    self.sendTimeline(state=self.player.STATE_STOPPED)
                    self.handler.player.stopAndWait()
                    return

                # not paused for a seek or a scan: a scan can run a while with no key pressed
                if not self.idleTime and not (self._seekPaused or self._scan) \
                        and xbmc.getCondVisibility('Player.Paused'):
                    self.idleTime = time.time()

        # force_tick is enabled when we're using an external player. In this case we simply count the time spent while
        # the external player is open and report that to the PMS
        if tick and (xbmc.getCondVisibility('Player.HasVideo + Player.Playing') or force_tick):
            self.timeKeeperTime += 1000
            self.playbackTime += 1000

        if force_tick:
            return

        # Update buffer state in PPI if open and old Kodi version
        if util.KODI_BUILD_NUMBER < 2090821 and self.getProperty('show.PPI'):
            try:
                cache = int(xbmc.getInfoLabel('Player.ProgressCache')) - int(xbmc.getInfoLabel('Player.Progress'))
                self.setProperty('ppi.Buffered', str(cache))
            except:
                pass

        # Only updateCurrent when not in DirectPlay mode. Otherwise the Kodi time functions will be used by the skin.
        if self.isDirectPlay:
            return

        self.updateCurrent(
            update_position_control=not self._seeking and not self._applyingSeek, atOffset=self.timeKeeperTime)

    @property
    def countingDownMarker(self):
        return self._currentMarker and \
               self._currentMarker["countdown"] is not None and \
               self._currentMarker["countdown"] > 0 and \
               self.getProperty('show.markerSkip')

    @countingDownMarker.setter
    def countingDownMarker(self, val):
        if not val and self._currentMarker:
            self._currentMarker["countdown"] = None
            self.setProperty('marker.countdown', '')

    def handleFinalMarker(self, marker_def, immediate=False, context="MarkerAutoSkip"):
        # final marker is _not_ at the end of video, seek and do nothing
        if marker_def["marker"].endTimeOffset < self.duration - FINAL_MARKER_NEGOFF:
            target = marker_def["marker"].endTimeOffset
            util.DEBUG_LOG(
                "{}: Skipping final marker, its endTime is too early, "
                "though, seeking and playing back", context)
            self.doSeek(target)
            return False

        # tell plex we've arrived at the end of the video
        self.sendTimeline(state=self.player.STATE_STOPPED, t=self.duration - 1000)

        # go to next video immediately (post play or next episode on bingeMode)
        if self.handler.playlist and self.handler.playlist.hasNext():
            if util.MONITOR.tv_standby:
                util.DEBUG_LOG("{}: TV in standby, stopping instead of auto-advancing", context)
                self.handler.endedManually = True
                self.player.stop()
                return True
            if self.bingeMode or self.skipPostPlay:
                if not self.handler.queuingNext:
                    # skip final marker
                    util.DEBUG_LOG("{}: {} final marker, going to next video", context,
                        immediate and "Immediately skipping" or "Skipping")
                    self.prepareNewPlayback(queuing_next=True, ignore_tick=True, ignore_input=True, with_timeline=False)
                    self.player.stop()
                return True
            else:
                util.DEBUG_LOG("{}: Skipping final marker in episode, stopping", context)
                self.handler.endedManually = True
                self.handler.creditsSkipped = True
                self.player.stop()
                return True
        else:
            # the last item: the video's end all the same - post-play, as for one played out. A
            # plain stop here, since a stop stopped meaning post-play (bb4fbdfc), went back to
            # where playback started (the user, 2026-10-13: a credits skip isn't a stop).
            util.DEBUG_LOG("{}: Skipping final marker, stopping", context)
            # stop() but for its stoppedManually
            self._ignoreTick = True
            self.doClose()
            self.handler.endedManually = True
            self.handler.creditsSkipped = True
            self.handler.player.stop()
        return False

    def sendTimeline(self, state=None, t=None, ensureFinalTimelineEvent=True):
        self.handler.updateNowPlaying(state=state, t=t, overrideChecks=True)
        if ensureFinalTimelineEvent:
            self.handler.ignoreTimelines = True
            # kill previous timeline data
            plexapp.util.APP.nowplayingmanager.reset()

    def displayMarkers(self, cancelTimer=False, immediate=False, onlyReturnIntroMD=False, setSkipped=False,
                       offset=None, setMarkersSkipped=False):

        if setMarkersSkipped:
            cnt = 0
            for markerDef in self.markers:
                if markerDef["marker"].startTimeOffset < offset:
                    markerDef["markerAutoSkipped"] = True
                    cnt += 1
            util.DEBUG_LOG("Markers: Skipping {}/{} markers that are before offset {}", cnt,
                           len(self.markers), offset)
            return

        # intro/credits marker display logic
        markerDef = self.getCurrentMarkerDef(offset=offset)

        if not markerDef:
            # no marker to display, hide it
            self.setProperty('show.markerSkip', '')
            self.setProperty('show.markerSkip_OSDOnly', '')
            if not self.getBoolProperty('show.OSD'):
                util.setGlobalProperty('osd_active', '')

            # this might be counter intuitive, but self._currentMarker is a reference to a dict
            if self._currentMarker:
                self._currentMarker["countdown"] = None
                setattr(self, self._currentMarker["markerAutoSkipShownTimer"], None)
            self._currentMarker = None

            # Out of every marker's window: each starts afresh next time, shown on its own again, whether its
            # button timed out, was dismissed (Back) or was used. Not markerAutoSkipped: seeking back into a marker
            # that's been auto-skipped (or was before a resume point) mustn't auto-skip it again.
            for md in self.markers or ():
                md["hidden"] = False
                md["skipped"] = False
            return False

        # getCurrentMarkerDef might have overridden the startTimeOffset, use that
        startTimeOff = markerDef["overrideStartOff"] if markerDef["overrideStartOff"] is not None else \
            markerDef["marker"].startTimeOffset

        markerAutoSkip = getattr(self, markerDef["markerAutoSkip"])

        # don't skip the credits marker on the last available episode
        if markerDef["marker_type"] == "credits" and self.bingeMode and self.handler.playlist and \
                not self.handler.playlist.hasNext():
            markerAutoSkip = False

        markerAutoSkipped = markerDef["markerAutoSkipped"]

        sTOffWThres = startTimeOff + util.addonSettings.autoSkipOffset * 1000

        # we just want to return an early marker if we want to autoSkip it, so we can tell the handler to seekOnStart
        if onlyReturnIntroMD and markerDef["marker_type"] == "intro" and markerAutoSkip:
            if startTimeOff <= 2000 and not markerDef["markerAutoSkipped"]:
                if setSkipped:
                    markerDef["markerAutoSkipped"] = True
                return markerDef["marker"].endTimeOffset + MARKER_END_JUMP_OFF
            return False

        if cancelTimer and self.countingDownMarker:
            self.countingDownMarker = False
            markerDef["markerAutoSkipped"] = True
            markerDef["hidden"] = True
            setattr(self, markerDef["markerAutoSkipShownTimer"], None)
            self.setProperty('show.markerSkip', '')
            if not self.getBoolProperty('show.OSD'):
                util.setGlobalProperty('osd_active', '')
            return False

        # never on its own while paused or choosing a seek (displayMarkers() runs then too)
        autoSkippingNow = markerDef \
            and markerAutoSkip \
            and not markerAutoSkipped \
            and not self._navigatedViaMarkerOrChapter \
            and (immediate or (not self._seeking and self.player.playState == self.player.STATE_PLAYING)) \
            and (markerDef["countdown"] == 0 or startTimeOff == 0 or immediate)
        # and (startTimeOff == 0 or sTOffWThres <= self.offset) \

        # auto skip marker
        # delay marker autoskip by autoSkipOffset to avoid cutting off content at the expense of being
        # slightly too late
        if autoSkippingNow:
            markerDef["markerAutoSkipped"] = True
            setattr(self, markerDef["markerAutoSkipShownTimer"], None)
            self.setProperty('show.markerSkip', '')
            self.setProperty('show.markerSkip_OSDOnly', '')
            if not self.getBoolProperty('show.OSD'):
                util.setGlobalProperty('osd_active', '')
            self.resetAutoSeekTimer(None)
            self.countingDownMarker = False

            if getattr(markerDef["marker"], "final", False):
                return self.handleFinalMarker(markerDef, immediate=immediate)

            util.DEBUG_LOG('MarkerAutoSkip: Skipping marker {}', markerDef["marker"])
            self.doSeek(markerDef["marker"].endTimeOffset + MARKER_END_JUMP_OFF)
            return True

        # got a marker, display logic
        # hide marker into OSD after a timeout
        # fixme: "markerAutoSkipShownTimer" should be "markerSkipShownTimer"
        timer = getattr(self, markerDef["markerAutoSkipShownTimer"])

        # restarted while paused or with the OSD open, so the button gets its full time on screen after either
        if timer is None or self.player.playState == self.player.STATE_PAUSED or self.osdVisible():
            setattr(self, markerDef["markerAutoSkipShownTimer"], time.time())

        else:
            # if we've not already OSD-hidden the marker manually, check its timeout
            if not self.getProperty('show.markerSkip_OSDOnly'):
                if timer + getattr(self, markerDef["markerSkipBtnTimeout"]) <= time.time():
                    self.setProperty('show.markerSkip_OSDOnly', '1')
                    markerDef["hidden"] = True
                else:
                    self.setProperty('show.markerSkip_OSDOnly', '')

        # no marker auto skip and not yet skipped or not yet auto skipped, normal display
        if (markerAutoSkip and not markerAutoSkipped) or (not markerAutoSkip and not markerDef["skipped"]):
            self.setProperty('show.markerSkip', '1')
            if not markerDef["hidden"]:
                self.setProperty('show.markerSkip_OSDOnly', '')
                util.setGlobalProperty('osd_active', '1')
        # marker auto skip and already skipped, or no autoskip and manually skipped - hide in OSD
        else:
            self.setProperty('show.markerSkip_OSDOnly', '1')

        # set marker name, count down
        if markerAutoSkip and not markerAutoSkipped:
            isNew = False
            if markerDef["countdown"] is None:
                # reset countdown on new marker
                if not self._currentMarker or self._currentMarker != markerDef or markerDef["countdown"] is None:
                    # fixme: round might not be right here, but who cares
                    to = self.trueOffset()
                    # set the countdown to either the auto skip offset, or, if we're already "inside" the marker time
                    # area through seeking, at max the difference between the current offset and the end of the
                    # video
                    markerDef["countdown"] = int(
                        max(
                            round((sTOffWThres - to) / 1000.0) + 1,
                            min(util.addonSettings.autoSkipOffset, int((self.duration - to) / 1000.0))
                        )
                    )
                    isNew = True

            # a second of playback per tick - not while seeking, which calls this per step too (seekByOffset())
            if self.player.playState == self.player.STATE_PLAYING and not self.osdVisible() and not self._seeking:
                markerDef["countdown"] -= 1
            if isNew:
                markerDef["countdown_initial"] = markerDef["countdown"]

            self.setProperty('marker.countdown', '1')

            if markerDef["countdown"] > 0:
                markerName = "{} ({})".format(markerDef["autoSkipName"], markerDef["countdown"])
            else:
                markerName = "  {}   ".format(markerDef["autoSkipName"])
        else:
            markerName = markerDef["name"]
        self.setProperty('skipMarkerName', markerName)

        # store current marker
        self._currentMarker = markerDef

        # focus marker if OSD is hidden, last focus wasn't the marker button and we're not auto skipping this marker -
        # nor seeking: OK applies the seek then, and would skip instead (it takes focus once the seek's landed)
        if not self.osdVisible() and not self._seeking and self.lastFocusID != self.SKIP_MARKER_BUTTON_ID and \
                not self.getProperty('show.markerSkip_OSDOnly') and self.getProperty('show.markerSkip') \
                and not markerAutoSkip:
            self.setFocusId(self.SKIP_MARKER_BUTTON_ID)

    def tick(self, offset=None, waitForBuffer=False):
        """
        Called ~1/s; can be wildly inaccurate.
        """
        if self.handler and self.handler.player and self.handler.player.isExternal:
            return

        # we might be called with an offset for seekOnStart even before we're initialized (onFirstInit)
        # in that case, skip all functionality and just seekOnStart
        if (not offset and not self.initialized) or self._ignoreTick:
            return

        if self.initialized:
            self.startPreviews()
            if waitForBuffer:
                cont = self.waitForBuffer()
                if not cont:
                    return

            if (self.pausedAt and self.resumeSeekBehindPause and
                    time.time() - self.pausedAt >= self.resumeSeekBehindAfter):
                self.seekBehind()
                self.pausedAt = None
                return

            # Where playback is, before the markers are chosen from it below: a seek reports where it
            # was asked to go, and playback can land earlier, on a keyframe. From pannal/plex-for-kodi.
            try:
                self.offset = offset or int(self.handler.player.getTime() * 1000)
            except RuntimeError:  # Playback has stopped
                self.resetSeeking()
                return

            if self.player.playState == self.player.STATE_PLAYING:
                self.idleTime = None

            if self._seekPaused in ('applying', 'resuming') and time.time() - self._seekPausedAt > 5:
                # a pause for seeking that never ended - a seek too small to make (alternate seek) doesn't report
                # landing, so the handler never resumed: resume here
                util.DEBUG_LOG("SeekDialog: Seek pause never ended ({}), resuming", self._seekPaused)
                self.setSeekPaused(None)
                if self.handler.unPauseAfterSeek:
                    self.handler.unPauseAfterSeek = False
                    if self.player.playState == self.player.STATE_PAUSED:
                        self.setSeekPaused('resuming')
                        self.player.control('play')

            # invisibly sync low-drift timer to current playback every X seconds, as Player.getTime() can be wildly off
            if self.ldTimer and not self.osdVisible() and self.timeKeeper and self.timeKeeper.ticks >= 60:
                self.syncTimeKeeper()

            cancelTick = False
            # don't auto skip while we're initializing and waiting for the handler to seek on start. Paused too -
            # which seeking is, choosing where to - and while seeking, the seek point's marker: the skip button
            # follows where you're going.
            if (offset is None and not self.handler.seekOnStart and not self.handler.waitingForSOS
                    and not self.handler.seekBackTo
                    and self.player.playState in (self.player.STATE_PLAYING, self.player.STATE_PAUSED)):
                cancelTick = self.displayMarkers(
                    offset=self.selectedOffset if self._seeking and self.selectedOffset else None)

            if cancelTick:
                return

            if xbmc.getCondVisibility('Window.IsActive(busydialog) + !Player.Caching'):
                util.DEBUG_LOG('SeekDialog: Possible stuck busy dialog - closing')
                xbmc.executebuiltin('Dialog.Close(busydialog,1)')

            if not self.hasDialog and self.osdVisible():
                # follow playback into the next chapter while the rows are out of sight
                self.syncRows()

                t = time.time()
                # with a customizable OSD hide timeout, OSD hide timeout might happen before a pending auto-seek
                # (delayedSeek()'s, or this tick's own autoSeekTimeout); in case we're still waiting for a seek,
                # postpone OSD hiding
                pendingSeek = self._delayedSeekTimeout or self.autoSeekTimeout
                if t > self.timeout and (not pendingSeek or pendingSeek < self.timeout < t) and not self._scan:
                    xbmc.executebuiltin('Dialog.Close(videoosd,true)')
                    xbmc.executebuiltin('Dialog.Close(seekbar,true)')
                    if not xbmc.getCondVisibility('Window.IsActive(videoosd) | Player.Rewinding | Player.Forwarding'):
                        self.hideOSD()

        if offset or self.initialized:
            if not self.initialized:
                # not initialized yet (seekOnStart, onFirstInit()): read above when it is
                self.offset = offset

            if offset or (self.autoSeekTimeout and time.time() >= self.autoSeekTimeout and
                          self.offset != self.selectedOffset):
                #off = offset is not None and offset or None
                #self.doSeek(off)
                if (not self.useAlternateSeek or
                        (((self.selectedOffset and abs(self.selectedOffset - self.offset) >= util.addonSettings.altseekValidSeekWindow)
                          or not self.selectedOffset) and not self.handler.waitingForSOS and not self.handler.seekBackTo)):
                    util.DEBUG_LOG("SeekDialog: Tick: Seek: {}, {}, {}", self.offset, self.selectedOffset, util.addonSettings.altseekValidSeekWindow)
                    self.resetAutoSeekTimer(None)
                    self.doSeek()
                    return True

            if self.isDirectPlay or not self.ldTimer:
                self.updateCurrent(update_position_control=not self._seeking and not self._applyingSeek)

    def osdVisible(self):
        return xbmc.getCondVisibility('Control.IsVisible(801)')

    def showOSD(self, focusButton=True):
        self.setProperty('show.OSD', '1')
        util.setGlobalProperty('osd_active', '1')
        xbmc.executebuiltin('Dialog.Close(videoosd,true)')
        if xbmc.getCondVisibility('Player.showinfo'):
            xbmc.executebuiltin('Action(Info)')

        if focusButton:
            # the timeline: OK there plays/pauses, left/right seek, down reaches the buttons
            self.setFocusId(self.MAIN_BUTTON_ID)

    def hideOSD(self, skipMarkerFocus=False, closing=False):
        util.DEBUG_LOG("SeekDialog: HideOSD: {}, {}", skipMarkerFocus, closing)
        self.setProperty('show.OSD', '')
        util.setGlobalProperty('osd_active', '')
        if closing:
            return

        self.setFocusId(self.NO_OSD_BUTTON_ID)
        if not skipMarkerFocus and not self.getProperty('show.markerSkip_OSDOnly') \
                and self.getProperty('show.markerSkip'):
            self.setFocusId(self.SKIP_MARKER_BUTTON_ID)

        self.resetSeeking()
        self._osdHideAnimationTimeout = time.time() + self.OSD_HIDE_ANIMATION_DURATION
