# -*- coding: utf-8 -*-
from __future__ import absolute_import

import gc
import threading
import time
import traceback
import os
import weakref

from kodi_six import xbmc
from kodi_six import xbmcgui
from six.moves import range
from six.moves import zip

from .. import util
from . import navintent

from plexnet import plexapp
from plexnet import exceptions as plexExceptions

# A screen that can't load its item: deleted on the server, or the server answering with an error
# (plexserver.query() raises BadRequest for anything but 200/201). It closes with
# navintent.noData(), and the host goes back (LibraryWindow.viewClosed()/viewFailed()).
NO_DATA_ERRORS = (util.NoDataException, plexExceptions.BadRequest, plexExceptions.NotFound)

MONITOR = None


class BaseFunctions(object):
    xmlFile = ''
    path = ''
    theme = ''
    res = '720p'
    width = 1280
    height = 720

    usesGenerate = False
    lastWinID = None
    lastDialogID = None
    # Set by a restore from minimised (monitor.py) for the screen it reactivates; see onRestored().
    restoring = False

    def __init__(self):
        self.isOpen = True

    def onWindowFocus(self):
        # Not automatically called. Can be used by an external window manager
        pass

    def onClosed(self):
        pass

    def onRestored(self):
        """The screen a restore from minimised reactivated (monitor.py). Nothing has happened to it
        meanwhile; by default it re-inits as on any return (onReInit()). A screen whose re-init
        reacts to where it's returning from (EpisodesWindow re-picks its episode) overrides this."""
        if hasattr(self, "onReInit"):
            self.onReInit()

    @classmethod
    def open(cls, **kwargs):
        path = cls.path
        aggressive = kwargs.pop('aggressive', False)
        if os.getenv("INSTALLATION_DIR_AVOID_WRITE"):
            path = util.PROFILE
        window = cls(cls.xmlFile, path, cls.theme, cls.res, **kwargs)
        window.modal(aggressive=aggressive)
        return window

    @classmethod
    def create(cls, show=True, **kwargs):
        # Use the user addon data directory in installations where the extension installation directory is not writable
        path = cls.path
        if os.getenv("INSTALLATION_DIR_AVOID_WRITE"):
            path = util.PROFILE
        window = cls(cls.xmlFile, path, cls.theme, cls.res, **kwargs)

        if show:
            window.show()
            if xbmcgui.getCurrentWindowId() < 13000:
                window.isOpen = False
                return window

        window.isOpen = xbmcgui.getCurrentWindowId() >= 13000
        return window

    def modal(self, aggressive=False):
        self.isOpen = True
        try:
            self.doModal(aggressive=aggressive)
        except SystemExit:
            pass
        self.onClosed()
        self.isOpen = False

    def activate(self):
        if not self._winID:
            self._winID = xbmcgui.getCurrentWindowId()
        xbmc.executebuiltin('ReplaceWindow({0})'.format(self._winID))

    def forceDismiss(self):
        # Default no-op: BaseWindow-only subclasses (e.g. SettingsWindow) and dialogs never override
        # close() to be flag-only in the first place, so their own doClose() already does a real
        # dismiss - nothing extra needed. ControlledWindow/MultiWindow (whose close() only flips
        # self._closing, see ControlledBase.close()) override this with a real dismiss.
        pass

    def mouseXTrans(self, val):
        return int((val / self.getWidth()) * self.width)

    def mouseYTrans(self, val):
        return int((val / self.getHeight()) * self.height)

    def closing(self):
        return self._closing

    @classmethod
    def generate(self):
        return None

    def setProperties(self, prop_list, val_list_or_val):
        if isinstance(val_list_or_val, list) or isinstance(val_list_or_val, tuple):
            val_list = val_list_or_val
        else:
            val_list = [val_list_or_val] * len(prop_list)

        for prop, val in zip(prop_list, val_list):
            self.setProperty(prop, val)

    def propertyContext(self, prop, val='1'):
        return WindowProperty(self, prop, val)

    def setBoolProperty(self, key, boolean):
        self.setProperty(key, boolean and '1' or '')

    def getBoolProperty(self, key):
        return self.getProperty(key) == '1'

    def waitForVisibility(self, control):
        return waitForVisibility(control)

    def waitAndSetFocus(self, control):
        self.waitForVisibility(control)
        self.setFocusId(control)


BG_NA = "script.plex/home/background-fallback_black.png"
# The size background art is requested at: the hero art box's, which is the only place any screen
# draws it (the full-screen copies behind search results and Person are going). The box
# (includes/default_background.xml.tpl) is 1229 wide plus its 61-pixel zoom pad, and a 16:9 image
# covers that at 1290x726; the window's 1920x1080 was about 2.2 times the pixels (step 12 in the
# navigation review). tests/test_move_lookups.py checks it against the template.
HERO_ART_SIZE = (1290, 726)
NAV_HIDDEN = False


def setNavHidden(hidden):
    """Hide every default.xml.tpl screen's content (nav_hidden) - post-play's hand-over to an item
    it opens. Tracked here too, so the next window's first init clears it without a GUI call on
    every other window open."""
    global NAV_HIDDEN
    NAV_HIDDEN = hidden
    util.setGlobalProperty('nav_hidden', hidden and '1' or '')


class XMLBase(object):
    defer_init = False
    defer_init_time = 0.25

    def onInit(self, count=0):
        if not self.started:
            if self.defer_init:
                util.DEBUG_LOG("Kodigui: Deferring init of {} for {}s", self, self.defer_init_time)
                util.MONITOR.waitForAbort(self.defer_init_time)
            try:
                self.getControl(666)
            except RuntimeError as e:
                if e.args and "Non-Existent Control" in e.args[0]:
                    if getattr(self, '_closing', False):
                        # Closed while we were waiting for it to finish loading, so its controls
                        # are going away rather than missing. Retrying costs 2s of xbmc.sleep on
                        # a dead window and ends in a template recompilation that nothing was
                        # wrong with - see the comment in busy.dialog(), whose delayed spinner is
                        # how this gets hit.
                        util.DEBUG_LOG('Kodigui: {} closed while initialising, not waiting for '
                                       'its controls', self.xmlFile)
                        return
                    if count < 8:
                        # retry
                        xbmc.sleep(250)
                        return self.onInit(count=count+1)

                    util.ERROR("Possibly broken XML file: {}, triggering recompilation.".format(self.xmlFile))
                    util.showNotification("Recompiling templates", time_ms=1000,
                                          header="Possibly broken XML file(s)")

                    try:
                        if xbmc.Player().isPlaying():
                            try:
                                xbmc.Player().stop()
                            except:
                                pass

                        tries = 0
                        while xbmc.Player().isPlaying() and tries < util.MONITOR.waitAmount(5):
                            util.MONITOR.waitFor()
                            tries += 1
                    except:
                        pass

                    xbmc.sleep(1000)

                    from . import windowutils
                    if self is windowutils.HOME:
                        try:
                            self._errored = True
                            self.closeWRecompileTpls()
                        except Exception:
                            pass
                    elif self.__class__.__name__ == "BackgroundWindow":
                        try:
                            self._errored = True
                            self.doClose()
                        except Exception:
                            pass
                    else:
                        try:
                            self._errored = True
                            self.doClose()
                        finally:
                            windowutils.HOME.closeWRecompileTpls()
                    return
                raise
        self._onInit()

    def goHomeAction(self, action):
        """The mapped Home button: Home's root, as a NavIntent (goHome() -> navigate()). Shared by
        every window and MultiWindow. goHome(), not navigate() directly, so a window's own goHome()
        (the photo viewer's) still decides how it leaves."""
        if (util.HOME_BUTTON_MAPPED is not None
                and action.getButtonCode() == int(util.HOME_BUTTON_MAPPED) and hasattr(self, "goHome")):
            util.DEBUG_LOG("Home button: going Home from {0}", type(self).__name__)
            self.goHome(with_root=True)
            return True
        return


class BaseWindow(XMLBase, xbmcgui.WindowXML, BaseFunctions):
    __slots__ = ("_closing", "_winID", "started", "finishedInit", "dialogProps", "isOpen", "_errored",
                 "_closeSignalled", "_bgURL", "_panelLayer", "_panelColors")
    supportsAutoPlay = False

    def __init__(self, *args, **kwargs):
        BaseFunctions.__init__(self)
        self._closing = False
        self._errored = False
        self._closeSignalled = False
        self._winID = None
        self.started = False
        self.finishedInit = False
        # The art URL windowSetBackground() last wrote to this window, None before the first.
        self._bgURL = None
        self._panelLayer = 'a'
        self._panelColors = ('', '', '', '')
        self.dialogProps = kwargs.get("dialog_props", None)
        # opener.py's handleOpen() reads w.exitCommand unconditionally on every window it opens
        # this way (win.open(**kwargs) then `return w.exitCommand or ''`) - a BaseWindow subclass
        # that never mixes in UtilMixin/MultiWindow (both of which already set this in their own
        # __init__) and never sets it itself (e.g. PhotoWindow) hit this as a bare AttributeError
        # instead of the intended empty-command default. Same default those two already use.
        self.exitCommand = None

        carryProps = kwargs.get("window_props", None)
        if carryProps:
            applyCarriedProps(self, carryProps)
        self.setBoolProperty('is_plextuary', util.SKIN_PLEXTUARY)

    # Weak reference to the MultiWindow (LibraryWindow) showing this window as its current view,
    # set by the host's _setupCurrent(). None for a window opened on its own. See hostedBy().
    _hostRef = None

    def hostedBy(self):
        """The host showing this window as its current view, or None. None too once the host has
        swapped this window out (or closed): Kodi can still deliver a late callback to it then, and
        that must not reach the host's routing, which only ever acts on its current view."""
        ref = self._hostRef
        host = ref() if ref is not None else None
        if host is not None and host.__dict__.get('_current') is self:
            return host
        return None

    def ignoresInput(self):
        """True for a hosted window that isn't live on its host: swapped out, or not started its
        first init yet. Called first thing in onClick()/onFocus() by every window a host can show
        (routeActionToHost() does the same for onAction()).

        Swapped out: the host closes the outgoing window natively, which frees its controls, but
        Kodi still delivers callbacks it had queued for it - live-caught 2026-09-25 as a crash on
        the PC: fast mouse tab clicks left Categories with queued onFocus calls, delivered during
        the host's wait after the close, and the handler read the freed sidebar list.

        Not started: Kodi queues a new window's first onFocus before its onInit, and input can
        arrive before it too. Until onFirstInit() rebinds them, the lists the host shares with each
        view (the sidebar, the grid) still wrap the previous view's controls, freed with it -
        live-caught 2026-09-25 as a use-after-free crash on the PC during fast sidebar switching.
        started (set just before onFirstInit()) rather than finishedInit, so a view whose
        onFirstInit() raised doesn't ignore input for good."""
        if self._hostRef is None:
            return False
        return self.hostedBy() is None or not self.started

    def routeActionToHost(self, action):
        """Called first thing in onAction() by every window a host can show. A hosted window's
        actions go through the host's routeAction() first (sidebar popups, the server and user
        buttons, Back through the chain, the Home button); True means it used the action and
        onAction() should stop there. A window that was hosted but no longer is its host's current
        view drops the action (True). False: not hosted, handle it here as usual.

        Replaces the host overwriting onAction on each hosted instance, so the method Kodi calls
        is the one you read in the class, and nothing bound to the host is stored on the view."""
        if self._hostRef is None:
            return False
        host = self.hostedBy()
        if host is None:
            return True
        if not self.started:
            # Too early to handle (ignoresInput()). Back isn't lost: it's delivered again once the
            # view is ready - the navigation queue holds it until then (runPendingNav()).
            if action in (xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_PREVIOUS_MENU):
                host.postNav('Back (pressed as the screen opened)', self.onAction, args=(action,),
                             stack=True)
            return True
        return host.routeAction(action)

    def routeClickToHost(self, controlID):
        """Called first thing in onClick() by every window a host can show, beside
        routeActionToHost(). The host's routeClick() handles the sidebar's own clicks - the section
        list and the user and server dropdowns - for whichever screen is showing, so they're written
        once instead of in every screen (I3 in the navigation review). True means onClick() should
        stop there: the host used the click, or this window isn't live (ignoresInput()). False: not
        hosted, or not a sidebar click - handle it here as usual."""
        if self.ignoresInput():
            return True
        if self._hostRef is None:
            return False
        return self.hostedBy().routeClick(controlID)

    # The actions that run handleBack() while this screen is hosted: NAV_BACK only, as on the
    # screens' own standalone path. The host's own views take PREVIOUS_MENU too (MultiWindowView).
    BACK_ACTIONS = (xbmcgui.ACTION_NAV_BACK,)

    def handleBack(self):
        """This screen's own Back steps, the ones that keep it open (a scrolled row back to its
        first item, the extras rows back to the button row). Returns True when one of them used
        the press. Called from the screen's own onAction() when it runs standalone, and by
        LibraryWindow.routeAction() before it pops the chain when the screen is hosted - the host
        sees a hosted screen's actions first, so without this a hosted screen never saw Back."""
        return False

    def onCloseSignal(self, *args, **kwargs):
        self._closeSignalled = True
        self.doClose(force=True)

    def _onInit(self):
        # 'show' ends as Kodi hands over onInit, before this window's own first GUI calls.
        host = self.hostedBy() if not self.started else None
        timing = host.__dict__.get('_swapTiming') if host is not None else None
        if timing is not None:
            timing.mark('show')
        self._winID = xbmcgui.getCurrentWindowId()
        if not getattr(self, 'isBaseWindow', False):
            # The screen a restore from minimised reactivates (monitor.py). Not the base window
            # (BackgroundWindow), which re-inits whenever it's reactivated - ensureBaseWindow(), or
            # Kodi falling back to it - and is blank: a restore then left a black screen (live on
            # the AM6B, 2026-09-27).
            BaseFunctions.lastWinID = self._winID
        self.setProperty('use_solid_background', util.useSolidBackground and '1' or '')
        if util.useSolidBackground:
            bgColour = util.addonSettings.backgroundColour if util.addonSettings.backgroundColour != "-" \
                else "ff000000"

            if util.addonSettings.customBackgroundColour:
                try:
                    cbgColour = util.addonSettings.customBackgroundColour.strip("#").strip().lower()
                    cbgclen = len(cbgColour)
                    if cbgclen < 6 or cbgclen > 8:
                        # invalid color
                        util.LOG("Invalid custom background colour: {}".format(util.addonSettings.customBackgroundColour))
                    else:
                        if cbgclen == 6:
                            cbgColour = "ff{}".format(cbgColour)
                        bgColour = cbgColour
                except:
                    pass

            self.setProperty('background_colour', "0x%s" % bgColour.lower())
            self.setProperty('background_colour_opaque', "0x%s" % bgColour.lower())
        else:
            # set background color to 0 to avoid kodi UI BG clearing, improves performance
            if util.addonSettings.dbgCrossfade:
                self.setProperty('background_colour', "0x00000000")
            else:
                self.setProperty('background_colour', "0xff111111")
            self.setProperty('background_colour_opaque', "0xff111111")

        self.setBoolProperty('use_bg_fallback', util.addonSettings.useBgFallback)
        self.setBoolProperty('dynamic_backgrounds', util.addonSettings.dynamicBackgrounds)

        try:
            if self.started:
                if BaseFunctions.restoring and not getattr(self, 'isBaseWindow', False):
                    # Reactivated by a restore from minimised (monitor.py), not a return from
                    # another screen: see onRestored().
                    BaseFunctions.restoring = False
                    self.onRestored()
                elif hasattr(self, "onReInit"):
                    self.onReInit()
            else:
                self.started = True
                self.paintInitialBackground()

                from . import windowutils
                if self is not windowutils.HOME and self.__class__.__name__ != "BackgroundWindow":
                    plexapp.util.APP.on('close.windows', self.onCloseSignal)

                # the screen replacing post-play's starting screen is showing: see setNavHidden()
                if NAV_HIDDEN:
                    setNavHidden(False)

                if hasattr(self, "onFirstInit"):
                    self.onFirstInit()
                self.finishedInit = True
                if timing is not None and host.__dict__.get('_swapTiming') is timing:
                    timing.report(self)
                    host._swapTiming = None
            util.setGlobalProperty('active_window', self.__class__.__name__)

        except NO_DATA_ERRORS as e:
            util.LOG('{0}: its item could not be loaded ({1!r}), closing', type(self).__name__, e)
            self.exitCommand = navintent.noData()
            self.doClose()

    def onAction(self, action):
        if XMLBase.goHomeAction(self, action):
            return
        xbmcgui.WindowXML.onAction(self, action)

    def onReInit(self):
        pass

    def doAutoPlay(self, blind=False):
        pass

    def onBlindClose(self):
        pass

    def waitForOpen(self, base_win_id=None):
        def not_open():
            return (not base_win_id and not self.isOpen) or (base_win_id and xbmcgui.getCurrentWindowId() < base_win_id)

        if not not_open():
            util.DEBUG_LOG("Window {} opened: {}", self, self.isOpen)
            return True

        tries = 0
        while not_open() and tries < util.MONITOR.waitAmount(120, interval=1.0):
            if tries == 0:
                util.LOG("Couldn't open window {}, other dialog open? Retrying for 120s. ({}, {}, {})", self, base_win_id, xbmcgui.getCurrentWindowId(), self.isOpen)
            if util.MONITOR.abortRequested():
                util.LOG("Couldn't open window {}, abort requested ({}, {}, {})", self, base_win_id, xbmcgui.getCurrentWindowId(), self.isOpen)
                break
            self.show()
            if not not_open():
                break
            if not self.isOpen:
                tries += 1
                util.MONITOR.waitFor(1.0)
            else:
                break

        util.DEBUG_LOG("Window {} opened: {}", self, self.isOpen)

        return self.isOpen

    def setProperty(self, key, value):
        if self._closing:
            return

        # Written to this window only. It used to be written a second time through
        # xbmcgui.Window(self._winID): the same window once it's open, so three GUI-locked calls
        # (that constructor takes the lock too) for one property. Before it's open, _winID fell
        # back to whichever window was on screen, so the write went there instead (F2 in the
        # navigation review). getProperty() already reads from this window.
        try:
            xbmcgui.WindowXML.setProperty(self, key, value)
        except RuntimeError:
            util.DEBUG_LOG('kodigui.BaseWindow.setProperty: Missing window ({}) ({})', self._winID, key)

    def setCondFocusId(self, focus):
        if self.getFocusId() != focus:
            self.setFocusId(focus)

    def backgroundItem(self):
        """The item whose art this window's hero shows, if it knows it before onFirstInit()."""
        return None

    def initialBackgroundURL(self):
        """The art a new window's first frame shows: its own item's (backgroundItem()), or None for
        no art. A screen whose art isn't an item's own art (a playlist's composite) overrides this."""
        ds = self.backgroundItem()
        return self.backgroundURLFor(ds) if ds is not None else None

    def paintInitialBackground(self):
        """A new window's first hero-art paint: its own art, the same URL its own
        updateBackgroundFrom() paints later, so that's a no-op (and Show -> Episodes keeps the
        show's art up throughout). Or no art. Never the previous screen's: that used to be the
        fallback, a global of the last art shown anywhere, so a screen opened from a library grid
        showed the right art only because the grid wrote art it never shows on every press (step
        12 stage C in the navigation review).

        No art is written as empty properties, not left alone: Kodi can hand a new window a
        reused id's old ones (PrePlayWindow.doClose())."""
        url = self.initialBackgroundURL() if util.addonSettings.dynamicBackgrounds else None
        if url:
            self.windowSetBackground(url)
        else:
            self.setProperty('background_static', '')
            self.setProperty('background', '')

    def backgroundURLFor(self, ds):
        """The hero-art URL updateBackgroundFrom() paints for ds, or None if it has no art."""
        # First non-empty of the three, checked one at a time. The old nested
        # ds.get('art', ds.get('parentArt', ds.get('grandparentArt', None))) form was wrong at
        # the end of the chain: PlexObject.get() wraps a missing key's default in a PlexValue,
        # and PlexValue(None) is the *string* "None" - truthy - so an item with no art at all
        # (live: the artist "Scott Bond" in the Recently Played row) produced a transcode URL
        # ending in "...127.0.0.1:32400None" that Kodi's texture loader then failed on
        # (CCurlFile::Open errors in kodi.log) every time the item was focused, instead of the
        # no-art path below.
        art = None
        for key in ('art', 'parentArt', 'grandparentArt'):
            candidate = ds.get(key)
            if candidate:
                art = candidate
                break
        # opacity=100: this art is now a focal, vivid box next to its own color panel, not a
        # full-bleed wash with text floating on top anywhere - backgroundArtOpacityAmount2's
        # server-side dimming was designed for that older look and just reads as muddy here.
        # Always a plain 16:9 transcode. The zoom inside the hero-art box is done entirely in
        # the skin (default_background.xml.tpl, hero_zoom_pad): PMS's minSize=1 does NOT crop to
        # the requested aspect, it returns the whole image scaled until both dimensions are
        # >= what was asked (verified live: 1920x1440 requested -> 2560x1440 returned), so asking
        # for a non-16:9 size here only wastes bandwidth and texture memory.
        return util.backgroundFromArt(art, width=HERO_ART_SIZE[0], height=HERO_ART_SIZE[1], opacity=100)

    def updateBackgroundFrom(self, ds):
        # `ds is not None`, not truthiness: an unopened Playlist is falsy (BasePlaylist.__len__()
        # is its item count, empty until opened) - see LibraryWindow.setHeroInfo(). Playlists
        # then resolve to no art here (they carry `composite`, deliberately not treated as
        # background art - the hero art box is hidden for them via hero.no_art) but still get
        # their seeded panel corners (updatePanelFrom()).
        if util.addonSettings.dynamicBackgrounds and ds is not None:
            self.updatePanelFrom(ds)
            return self.windowSetBackground(self.backgroundURLFor(ds))

    def updateArtFrom(self, ds):
        """The hero art half of updateBackgroundFrom(), on its own: for a write that waits for the
        cursor to rest while the colour panel follows every press (MultiWindow.settleLater())."""
        if util.addonSettings.dynamicBackgrounds and ds is not None:
            return self.windowSetBackground(self.backgroundURLFor(ds))

    def updatePanelFrom(self, ds):
        """The colour panel half of updateBackgroundFrom(), on its own for a screen that shows no
        art: the library grids."""
        if util.addonSettings.dynamicBackgrounds and ds is not None:
            # 4-corner tinted-panel colors, Phase 1 approximation of official Plex's native
            # per-corner art color extraction - see docs/notes/hero-art-background-status.md.
            # getattr, not ds.get(): ultraBlurColors is a plain instance attribute only present on
            # Video subclasses (Movie/Show/Season/Episode/Clip), absent entirely on e.g. Photo, and
            # PlexObject.get() would wrap a missing key in a truthy PlexValue instead of None.
            # seed=ratingKey (falling back to title): when ultraBlurColors is genuinely absent
            # (Photo/most Music items, or any item the server just didn't return it for),
            # backgroundPanelCorners() hashes this into a deterministic, neutral-but-colorful
            # stand-in instead of leaving the panel flat black - see its own docstring (util.py).
            corners = util.backgroundPanelCorners(getattr(ds, 'ultraBlurColors', None),
                                                  seed=ds.get('ratingKey') or ds.get('title'))
            self._setPanelCorners(corners)

    PANEL_CORNER_PROPS = (('background_panel_tl', 'topLeft'), ('background_panel_tr', 'topRight'),
                           ('background_panel_bl', 'bottomLeft'), ('background_panel_br', 'bottomRight'))

    def _setPanelCorners(self, corners):
        """Cross-fades the 4-corner background color panel (default_background.xml.tpl) between
        items instead of popping instantly. A control's <colordiffuse> has no fade of its own in
        Kodi - unlike the hero art layers windowSetBackground drives, which crossfade because their
        *texture* changes, only a control's own <visible> transition can be animated (via an
        explicit <animation effect="fade">VisibleChange</animation>). So default_background.xml.tpl
        duplicates the 4 corners into two layers (_a/_b, each a group gated on
        background_panel_layer); this writes the new colors into whichever layer is currently
        hidden, then flips background_panel_layer so the now-hidden old layer fades out while the
        newly-shown one fades in.
        """
        values = tuple(corners.get(corner, '') for _, corner in self.PANEL_CORNER_PROPS)
        if values == self._panelColors:
            return
        self._panelColors = values

        if not util.addonSettings.dbgCrossfade:
            for prop, corner in self.PANEL_CORNER_PROPS:
                # always set, even to '' - established hide-via-empty-property idiom this skin
                # already uses, needed so a title with no ultraBlurColors clears colors left by a
                # prior title.
                self.setProperty('{}_a'.format(prop), corners.get(corner, ''))
            self.setProperty('background_panel_layer', 'a')
            return

        target = 'b' if self._panelLayer == 'a' else 'a'
        for prop, corner in self.PANEL_CORNER_PROPS:
            self.setProperty('{}_{}'.format(prop, target), corners.get(corner, ''))
        self.setProperty('background_panel_layer', target)
        self._panelLayer = target

    def windowSetBackground(self, value):
        """Writes the hero art, or the no-art image when value is empty (an item with no art shows
        none, not the previous item's). Skips a URL this window already shows: compared with this
        window's own last write (_bgURL), not a global of the last art shown anywhere, which could
        match while this window showed something else and skip a write it needed (step 12 stage C
        in the navigation review)."""
        if not util.addonSettings.dbgCrossfade:
            self.setProperty("background_static", value or BG_NA)
            return value

        if not value:
            if self._bgURL != BG_NA:
                self.setProperty("background_static", BG_NA)
                self.setProperty("background", BG_NA)
                self._bgURL = BG_NA
            return BG_NA

        if self._bgURL != value:
            # Both layers move together now, on request: the previous item's art should be gone
            # the instant focus moves off it, not held solid as a backdrop for the crossfading
            # layer above to blend against (the original reason for staggering these - see git
            # history for the old two-stage version and its now-removed _scheduleBackgroundStaticSync()
            # catch-up timer). What's actually behind default_background.xml.tpl's hero-art box
            # isn't black, it's the already-crossfading 4-corner tinted color panel (same file,
            # above this box) - so setting background_static here loses its own held-old-art
            # backdrop and the two layers' <fadetime> crossfades now run in lockstep, but neither
            # exposes a blank/black gap; the tinted panel shows through the shared transparent
            # moments instead.
            self.setProperty("background_static", value)
            self.setProperty("background", value)
            self._bgURL = value

        return value

    def doClose(self, **kw):
        force = kw.get('force', True)
        plexapp.util.APP.off('close.windows', self.onCloseSignal)
        util.DEBUG_LOG("{}: doClose called, force: {}", self.__class__.__name__, force)
        if self._closing:
            # Already told to close - self.close() (native) is not safe to call twice on the
            # same window; the old `if not self.isOpen and not force` guard below only protected
            # non-force callers, but force=True is the default every caller actually uses, so it
            # never applied in practice. Found live: openSection()/switchTab() (library.py) can
            # both be triggered a second time before _open()'s loop (kodigui.py) has caught up
            # and reassigned self._current to a new object - a native crash with no Python
            # exception to show for it, since self.close() failing isn't Python-catchable.
            return
        if not self.isOpen and not force:
            return
        self._closing = True
        self.isOpen = False
        self.close()

    def show(self, aggressive=False):
        self._closing = False
        # can we activate?
        ct = 0
        while xbmcgui.getCurrentWindowDialogId() > 9999 and ct < util.MONITOR.waitAmount(2):
            util.MONITOR.waitFor()
            ct += 1

        lastWinID = BaseFunctions.lastWinID

        #self.isOpen = True
        xbmcgui.WindowXML.show(self)

        if aggressive:
            cid = xbmcgui.getCurrentWindowId()
            util.DEBUG_LOG("{}: checking window state (ID: {}, last: {}, current: {})", self, self._winID, lastWinID, cid)
            if(self._winID and cid != self._winID) or not self._winID or xbmcgui.getCurrentWindowId() == lastWinID:
                # our current window ID _has_ to be different to the last one, if it isn't, handle.
                # kodi doesn't throw an exception in case of a still active modal dialog, but instead just logs:
                # Activate of window 'xxxxxx' refused because there are active modal dialogs
                if xbmcgui.getCurrentWindowId() == lastWinID:
                    util.DEBUG_LOG('{}: not yet active, retrying', self.__class__.__name__)
                    util.MONITOR.waitFor()

                ct = 0
                while xbmcgui.getCurrentWindowId() == lastWinID and ct < util.MONITOR.waitAmount(2, interval=0.5) and not util.MONITOR.abortRequested():
                    ct += 1
                    # we might have run into an active dialog, which happens sometimes, so we didn't really activate the window
                    # retry
                    xbmcgui.WindowXML.show(self)
                    util.MONITOR.waitFor(0.5)

                util.DEBUG_LOG("{}: activation state (ID: {}, last: {}, current: {})", self, self._winID, lastWinID, xbmcgui.getCurrentWindowId())

        self.isOpen = xbmcgui.getCurrentWindowId() >= 13000

    @property
    def is_active(self):
        return self._winID and BaseFunctions.lastWinID == self._winID

    @property
    def is_current_window(self):
        return self._winID and xbmcgui.getCurrentWindowId() == self._winID

    def onClosed(self):
        pass


class BaseDialog(XMLBase, xbmcgui.WindowXMLDialog, BaseFunctions):
    __slots__ = ("_closing", "_winID", "started", "isOpen", "_errored", "_closeSignalled", "dialogProps")

    def __init__(self, *args, **kwargs):
        BaseFunctions.__init__(self)
        self._closing = False
        self._errored = False
        self._closeSignalled = False
        self._winID = ''
        self.started = False

        carryProps = kwargs.get("dialog_props", None)
        self.dialogProps = carryProps
        if carryProps:
            applyCarriedProps(self, carryProps)
        self.setBoolProperty('is_plextuary', util.SKIN_PLEXTUARY)

    def onCloseSignal(self, *args, **kwargs):
        self._closeSignalled = True
        self.doClose()

    def modal(self, aggressive=False):
        try:
            BaseFunctions.modal(self, aggressive=aggressive)
        finally:
            # doClose() disconnects this too, but Back closes a dialog through Kodi's own
            # onAction(), which never calls it: the signal then kept every such dialog alive for
            # the rest of the session (E4 in the navigation review).
            plexapp.util.APP.off('close.dialogs', self.onCloseSignal)

    def _onInit(self):
        self._winID = xbmcgui.getCurrentWindowDialogId()
        BaseFunctions.lastDialogID = self._winID
        if self.started:
            self.onReInit()
        else:
            self.started = True
            plexapp.util.APP.on('close.dialogs', self.onCloseSignal)
            self.onFirstInit()

    def onAction(self, action):
        if XMLBase.goHomeAction(self, action):
            return
        xbmcgui.WindowXMLDialog.onAction(self, action)

    def onFirstInit(self):
        pass

    def onReInit(self):
        pass

    def setProperty(self, key, value):
        if self._closing:
            return

        # This dialog only - see BaseWindow.setProperty().
        try:
            xbmcgui.WindowXMLDialog.setProperty(self, key, value)
        except RuntimeError:
            xbmc.log('kodigui.BaseDialog.setProperty: Missing window', xbmc.LOGDEBUG)

    def doClose(self, **kw):
        plexapp.util.APP.off('close.dialogs', self.onCloseSignal)
        self._closing = True
        self.close()
        self.isOpen = False

    def show(self):
        self._closing = False
        xbmcgui.WindowXMLDialog.show(self)
        self.isOpen = True

    def onClosed(self):
        pass


# How long a window's wait loop waits at a time. Kodi runs a script's queued callbacks - onInit,
# onAction, onClick, onFocus - only between these waits: Monitor.waitForAbort() waits out its whole
# slice on the abort event and calls MakePendingCalls() after it (Omega's Monitor.cpp), unlike
# Kodi's own doModal(), which wakes on each action. At 0.1 s every remote press waited up to 100 ms
# (50 on average) before the addon saw it, and every screen's onInit a full 100 ms after Kodi had
# built the window (step 4 in the navigation review: a posters window took 45 ms to build in a
# plain Kodi window on the AM6B, 139 ms to reach onInit in the addon).
WAIT_SLICE_SECONDS = 0.02


class ControlledBase:
    def doModal(self, aggressive=False):
        self.show(aggressive=aggressive)
        self.wait()

    def wait(self):
        # A hosted view's wait loop is also where its host runs queued navigation (S1 in the
        # navigation review, MultiWindow.postNav()): between waits, on this - the main - thread,
        # which is the only thread Kodi hands this view's callbacks to, and only while it's inside
        # waitFor(). So a swap run here can never interleave with this view's input handling.
        while not self._closing:
            host = self.hostedBy() if isinstance(self, BaseWindow) else None
            interval = host.navWaitInterval() if host is not None else None
            if MONITOR.waitFor(min(interval, WAIT_SLICE_SECONDS) if interval else WAIT_SLICE_SECONDS):
                break
            if host is not None and not self._closing:
                host.runPendingNav(self)

    def close(self):
        self._closing = True


class ControlledWindow(ControlledBase, BaseWindow):
    # opt-in: actively dismiss the Kodi window on a genuine back-out (see onAction). Off by
    # default; ControlledBase.close() only flips a flag, so non-opted windows keep relying on
    # GC/parent re-activate and windows with their own teardown (video player) stay untouched.
    dismissOnClose = False

    def onAction(self, action):
        try:
            if action in (xbmcgui.ACTION_PREVIOUS_MENU, xbmcgui.ACTION_NAV_BACK):
                self.doClose()
                if self.dismissOnClose:
                    # genuine NAV_BACK on an opted-in window: the wait()-loop close only sets a
                    # flag, so the window can linger on the stack and swallow input. Force the
                    # real Kodi dismiss. Scoped to back-out, so go-home/playback teardown paths
                    # (different actions / non-opted windows) are never force-closed.
                    self.forceDismiss()
                return
        except:
            traceback.print_exc()

        BaseWindow.onAction(self, action)

    def forceDismiss(self):
        # Real dismiss, callable directly (not just from the dismissOnClose-gated NAV_BACK branch
        # above) - needed by sidebar-focus-driven navigation, which must leave a window's real Kodi
        # window closed *before* opening the next one instead of pushing on top of it.
        try:
            xbmcgui.WindowXML.close(self)
        except Exception:
            pass


class ControlledDialog(ControlledBase, BaseDialog):
    def onAction(self, action):
        try:
            if action in (xbmcgui.ACTION_PREVIOUS_MENU, xbmcgui.ACTION_NAV_BACK):
                self.doClose()
                return
        except:
            traceback.print_exc()

        BaseDialog.onAction(self, action)


DUMMY_LIST_ITEM = xbmcgui.ListItem()


class DummyDataSource(object):
    def __nonzero__(self):
        return False

    __bool__ = __nonzero__

    def exists(self, *args, **kwargs):
        return False


class EmptyDataSource(DummyDataSource):
    def __getattr__(self, item):
        return None

    def __setattr__(self, key, value):
        raise NotImplementedError


DUMMY_DATA_SOURCE = DummyDataSource()


class ScreenClosed(Exception):
    """Raised by a guarded control or list item call once its screen has closed (WriteGuard)."""


class WriteGuard(object):
    """Lets a screen stop background work touching its controls once it has closed, without
    waiting for that work (F5 in the navigation review). A screen that runs background fills
    (mixins/tasks.py's TasksMixin) has one; every ManagedControlList it creates, and the items in
    it, route their Kodi calls through the guard's lock and raise ScreenClosed once close() has
    run. close() takes the lock, so it waits for the one call in progress - milliseconds - rather
    than for a fill's server request; the host then closes the screen natively, freeing the
    controls, with nothing still able to reach them."""

    def __init__(self):
        self.lock = threading.RLock()
        self.closed = False

    def close(self):
        with self.lock:
            self.closed = True


class _Guarded(object):
    """A Kodi control or ListItem whose method calls go through a WriteGuard."""
    __slots__ = ('_target', '_guard')

    def __init__(self, target, guard):
        self._target = target
        self._guard = guard

    def __getattr__(self, name):
        attr = getattr(self._target, name)
        if not callable(attr):
            return attr
        guard = self._guard

        def call(*args, **kwargs):
            with guard.lock:
                if guard.closed:
                    raise ScreenClosed(name)
                return attr(*args, **kwargs)
        return call

    def __bool__(self):
        return bool(self._target)

    __nonzero__ = __bool__


class ManagedListItem(object):
    __slots__ = ("_listItem", "dataSource", "properties", "label", "label2", "iconImage", "thumbnailImage", "path",
                 "_ID", "_manager", "_valid")

    def __init__(self, label='', label2='', iconImage='', thumbnailImage='', path='', data_source=None,
                 properties=None):
        self._listItem = xbmcgui.ListItem(label, label2, path=path)
        # Every ListItem call takes Kodi's GUI lock, so skip the one that would set nothing: a
        # grid's placeholder items have neither (library.py's _placeholderItems()).
        if thumbnailImage or iconImage:
            self._listItem.setArt({"thumb": thumbnailImage, "icon": iconImage})
        self.dataSource = data_source
        self.properties = {}
        self.label = label
        self.label2 = label2
        self.iconImage = iconImage
        self.thumbnailImage = thumbnailImage
        self.path = path
        self._ID = None
        self._manager = None
        self._valid = True

        if properties:
            for k, v in properties.items():
                self.setProperty(k, v)

    def __nonzero__(self):
        return self._valid

    @property
    def listItem(self):
        if not self._listItem:
            if not self._manager:
                return None

            try:
                self._listItem = self._manager.getListItemFromManagedItem(self)
            except RuntimeError:
                return None

        guard = getattr(self._manager, '_guard', None) if self._manager else None
        if guard is not None:
            return _Guarded(self._listItem, guard)
        return self._listItem

    def invalidate(self):
        self._valid = False
        self._listItem = DUMMY_LIST_ITEM
        self.dataSource = DUMMY_DATA_SOURCE

    def _takeListItem(self, manager, lid):
        self._manager = manager
        self._ID = lid
        li = self._listItem
        self._listItem = None
        self._manager._properties.update(self.properties)
        return li

    def _updateListItem(self):
        self.listItem.setLabel(self.label)
        self.listItem.setLabel2(self.label2)
        self.listItem.setArt({"thumb": self.thumbnailImage, "icon": self.iconImage})
        self.listItem.setPath(self.path)
        for k in self._manager._properties.keys():
            self.listItem.setProperty(k, self.properties.get(k) or '')

    def clear(self):
        self.label = ''
        self.label2 = ''
        self.iconImage = ''
        self.thumbnailImage = ''
        self.path = ''
        for k in self.properties:
            self.properties[k] = ''
        self._updateListItem()

    def pos(self):
        if not self._manager:
            return None
        return self._manager.getManagedItemPosition(self)

    def addContextMenuItems(self, items, replaceItems=False):
        self.listItem.addContextMenuItems(items, replaceItems)

    def addStreamInfo(self, stype, values):
        self.listItem.addStreamInfo(stype, values)

    def getLabel(self):
        return self.label

    def getLabel2(self):
        return self.label2

    def getProperty(self, key):
        return self.properties.get(key, '')

    def getdescription(self):
        return self.listItem.getdescription()

    def getduration(self):
        return self.listItem.getduration()

    def getfilename(self):
        return self.listItem.getfilename()

    def isSelected(self):
        return self.listItem.isSelected()

    def select(self, selected):
        return self.listItem.select(selected)

    def setArt(self, values):
        return self.listItem.setArt(values)

    def setIconImage(self, icon):
        self.iconImage = icon
        return self.listItem.setArt({"icon": self.iconImage})

    def setInfo(self, itype, infoLabels):
        return self.listItem.setInfo(itype, infoLabels)

    def setLabel(self, label):
        self.label = label
        return self.listItem.setLabel(label)

    def setLabel2(self, label):
        self.label2 = label
        return self.listItem.setLabel2(label)

    def setMimeType(self, mimetype):
        return self.listItem.setMimeType(mimetype)

    def setPath(self, path):
        self.path = path
        return self.listItem.setPath(path)

    def setProperty(self, key, value):
        if self._manager:
            self._manager._properties[key] = 1
        # Every ListItem call takes Kodi's GUI lock, so skip a write that changes nothing: the
        # value it already has, or '' for a property it never had. self.properties mirrors the
        # list item - every other path that writes one (_updateListItem(), clear()) goes from it.
        # A grid chunk rewrote 'index' and wrote empty 'progress'/'year' on every placeholder.
        unchanged = self.properties.get(key, '') == value
        self.properties[key] = value
        if not unchanged:
            self.listItem.setProperty(key, value)
        return self

    def setProperties(self, prop_list, val_list_or_val):
        if isinstance(val_list_or_val, list) or isinstance(val_list_or_val, tuple):
            val_list = val_list_or_val
        else:
            val_list = [val_list_or_val] * len(prop_list)

        for prop, val in zip(prop_list, val_list):
            self.setProperty(prop, val)

    def setBoolProperty(self, key, boolean):
        return self.setProperty(key, boolean and '1' or '')

    def setSubtitles(self, subtitles):
        return self.listItem.setSubtitles(subtitles)  # List of strings - HELIX

    def setThumbnailImage(self, thumb):
        self.thumbnailImage = thumb
        return self.listItem.setArt({"thumb": self.thumbnailImage})

    def onDestroy(self):
        pass


class ManagedControlList(object):
    __slots__ = ("controlID", "control", "items", "_sortKey", "_idCounter", "_maxViewIndex", "_properties",
                 "dataSource", "_guard")

    def __init__(self, window, control_id, max_view_index, data_source=None):
        self.controlID = control_id
        # The creating screen's WriteGuard, if it has one. Not applied by newControl(): the host's
        # shared lists (the sidebar) are rebound to each screen that way, and outlive it.
        self._guard = getattr(window, '_writeGuard', None)
        self.control = self._guardedControl(window.getControl(control_id))
        self.items = []
        self._sortKey = None
        self._idCounter = 0
        self._maxViewIndex = max_view_index
        self._properties = {}
        self.dataSource = data_source

    def __getattr__(self, name):
        return getattr(self.control, name)

    def __getitem__(self, idx):
        if isinstance(idx, slice):
            return self.items[idx]
        else:
            return self.getListItem(idx)

    def __iter__(self):
        for i in self.items:
            yield i

    def __len__(self):
        return self.size()

    def prev(self):
        pos = self.getSelectedPos()-1
        if self.positionIsValid(pos):
            return pos
        return 0

    def _updateItems(self, bottom=None, top=None):
        if bottom is None:
            bottom = 0
            top = self.size()

        try:
            for idx in range(bottom, top):
                try:
                    li = self.control.getListItem(idx)
                except RuntimeError:
                    continue

                mli = self.items[idx]
                self._properties.update(mli.properties)
                mli._manager = self
                mli._listItem = li
                mli._updateListItem()
                mli.setProperty('index', str(idx))
        except RuntimeError:
            #xbmc.log('kodigui.ManagedControlList._updateItems: Runtime error', xbmc.LOGINFO)
            util.ERROR('kodigui.ManagedControlList._updateItems: Runtime error')
            return False

        return True

    def _nextID(self):
        self._idCounter += 1
        return str(self._idCounter)

    def _guardedControl(self, control):
        return _Guarded(control, self._guard) if self._guard is not None else control

    def reInit(self, window, control_id):
        self.controlID = control_id
        self.control = self._guardedControl(window.getControl(control_id))
        self.control.addItems([i._takeListItem(self, self._nextID()) for i in self.items])

    def setSort(self, sort):
        self._sortKey = sort

    def addItem(self, managed_item):
        self.items.append(managed_item)
        self.control.addItem(managed_item._takeListItem(self, self._nextID()))

    def addItems(self, managed_items):
        self.items += managed_items
        self.control.addItems([i._takeListItem(self, self._nextID()) for i in managed_items])

    def prependItems(self, managed_items):
        """
        Inserts managed_items at the front of the list, keeping every already-loaded item (nothing
        is destroyed/invalidated the way replaceItems does) - for append-only-in-both-directions
        pagination (e.g. Episodes), where growth can happen at either end, not just the end addItems
        already covers.

        Kodi's own ControlList has no native "insert at position" for multiple items, so this grows
        the control by len(managed_items) blank slots (same technique replaceItems already uses for
        a size increase) and then re-pushes every item's content into its correct slot via
        _updateItems - which also renumbers every item's own 'index' property to match its new
        position, so nothing needs manual reindexing here.
        """
        if not managed_items:
            return

        n = len(managed_items)
        selectedPos = self.getSelectedPos()

        self.items[0:0] = managed_items

        for _ in range(n):
            self.control.addItem(xbmcgui.ListItem())

        self._updateItems(0, self.size())

        if selectedPos is not None:
            self.control.selectItem(selectedPos + n)

    def replaceItem(self, pos, mli):
        self[pos].onDestroy()
        self[pos].invalidate()
        self.items[pos] = mli
        li = self.control.getListItem(pos)
        mli._manager = self
        mli._listItem = li
        mli._updateListItem()

    def replaceItems(self, managed_items):
        if not self.items:
            self.addItems(managed_items)
            return True

        oldSize = self.size()

        for i in self.items:
            i.onDestroy()
            i.invalidate()

        self.items = managed_items
        size = self.size()
        if size != oldSize:
            pos = self.getSelectedPosition()

            if size > oldSize:
                for i in range(0, size - oldSize):
                    self.control.addItem(xbmcgui.ListItem())
            elif size < oldSize:
                diff = oldSize - size
                idx = oldSize - 1
                while diff:
                    self.control.removeItem(idx)
                    idx -= 1
                    diff -= 1

            if self.positionIsValid(pos):
                self.selectItem(pos)
            elif pos >= size:
                self.selectItem(size - 1)

        return self._updateItems(0, self.size())

    def getListItem(self, pos):
        li = self.control.getListItem(pos)
        mli = self.items[pos]
        mli._listItem = li
        return mli

    def getListItemByDataSource(self, data_source):
        for mli in self:
            if data_source == mli.dataSource:
                return mli
        return None

    def getSelectedItem(self):
        return self.getSelectedItemAndPos()[0]

    def getSelectedItemAndPos(self):
        """The selected item and its position, from the one lookup: for a caller that needs both,
        where the item's pos() would scan the list for a position this already read."""
        pos = self.getSelectedPos()
        if pos is None:
            return None, None
        return self.getListItem(pos), pos

    def getSelectedPos(self):
        pos = self.control.getSelectedPosition()
        if not self.positionIsValid(pos):
            pos = self.size() - 1

        if pos < 0:
            return None
        return pos

    def getItemByPos(self, pos):
        if self.positionIsValid(pos):
            return self.getListItem(pos)

    def setSelectedItemByPos(self, pos):
        if self.positionIsValid(pos):
            self.control.selectItem(pos)

    def setSelectedItem(self, item):
        pos = self.getManagedItemPosition(item)
        if self.positionIsValid(pos):
            self.control.selectItem(pos)

    def setSelectedItemByDataSource(self, data_source):
        mli = self.getListItemByDataSource(data_source)
        if mli:
            self.setSelectedItem(mli)
            return True
        return False

    def removeItem(self, index):
        old = self.items.pop(index)
        old.onDestroy()
        old.invalidate()

        self.control.removeItem(index)
        top = self.control.size() - 1
        if top < 0:
            return
        if top < index:
            index = top
        self.control.selectItem(index)

    def removeManagedItem(self, mli):
        self.removeItem(mli.pos())

    def insertItem(self, index, managed_item):
        pos = self.getSelectedPosition() + 1

        if index >= self.size() or index < 0:
            self.addItem(managed_item)
        else:
            self.items.insert(index, managed_item)
            self.control.addItem(managed_item._takeListItem(self, self._nextID()))
            self._updateItems(index, self.size())

        if self.positionIsValid(pos):
            self.selectItem(pos)

    def moveItem(self, mli, dest_idx):
        source_idx = mli.pos()
        if source_idx < dest_idx:
            rstart = source_idx
            rend = dest_idx + 1
            # dest_idx-=1
        else:
            rstart = dest_idx
            rend = source_idx + 1
        mli = self.items.pop(source_idx)
        self.items.insert(dest_idx, mli)

        self._updateItems(rstart, rend)

    def swapItems(self, pos1, pos2):
        if not self.positionIsValid(pos1) or not self.positionIsValid(pos2):
            return False

        item1 = self.items[pos1]
        item2 = self.items[pos2]
        li1 = item1._listItem
        li2 = item2._listItem
        item1._listItem = li2
        item2._listItem = li1

        item1._updateListItem()
        item2._updateListItem()
        self.items[pos1] = item2
        self.items[pos2] = item1

        return True

    def shiftView(self, shift, hold_selected=False):
        if not self._maxViewIndex:
            return
        selected = self.getSelectedItem()
        selectedPos = selected.pos()
        viewPos = self.getViewPosition()

        if shift > 0:
            pushPos = selectedPos + (self._maxViewIndex - viewPos) + shift
            if pushPos >= self.size():
                pushPos = self.size() - 1
            self.selectItem(pushPos)
            newViewPos = self._maxViewIndex
        elif shift < 0:
            pushPos = (selectedPos - viewPos) + shift
            if pushPos < 0:
                pushPos = 0
            self.selectItem(pushPos)
            newViewPos = 0

        if hold_selected:
            self.selectItem(selected.pos())
        else:
            diff = newViewPos - viewPos
            fix = pushPos - diff
            # print '{0} {1} {2}'.format(newViewPos, viewPos, fix)
            if self.positionIsValid(fix):
                self.selectItem(fix)

    def reset(self):
        self.dataSource = None
        for i in self.items:
            i.onDestroy()
            i.invalidate()
        self.items = []
        self.control.reset()

    def size(self):
        return len(self.items)

    def getViewPosition(self):
        try:
            return int(xbmc.getInfoLabel('Container({0}).Position'.format(self.controlID)))
        except:
            return 0

    def getViewRange(self):
        viewPosition = self.getViewPosition()
        selected = self.getSelectedPosition()
        return list(range(max(selected - viewPosition, 0), min(selected + (self._maxViewIndex - viewPosition) + 1, self.size() - 1)))

    def positionIsValid(self, pos):
        return 0 <= pos < self.size()

    def sort(self, sort=None, reverse=False):
        sort = sort or self._sortKey

        self.items.sort(key=sort, reverse=reverse)

        self._updateItems(0, self.size())

    def reverse(self):
        self.items.reverse()
        self._updateItems(0, self.size())

    def getManagedItemPosition(self, mli):
        return self.items.index(mli)

    def isLastItem(self, mli=None):
        return self.getManagedItemPosition(mli or self.getSelectedItem()) + 1 == len(self)

    def getListItemFromManagedItem(self, mli):
        pos = self.items.index(mli)
        return self.control.getListItem(pos)

    def topHasFocus(self):
        return self.getSelectedPosition() == 0

    def bottomHasFocus(self):
        return self.getSelectedPosition() == self.size() - 1

    def invalidate(self):
        for item in self.items:
            item._listItem = DUMMY_LIST_ITEM

    def newControl(self, window=None, control_id=None):
        self.controlID = control_id or self.controlID
        self.control = window.getControl(self.controlID)
        self.control.addItems([xbmcgui.ListItem() for i in range(self.size())])
        self._updateItems()

    def newControlEmpty(self, window=None, control_id=None):
        """Like newControl(), but rebinds to the fresh native control without repainting
        whatever ManagedListItems this list was still holding - for a caller whose items are
        about to be replaced wholesale anyway (replaceItems()/reset()), where newControl()'s
        repaint would otherwise put stale content on screen for the gap between window
        construction and the real replacement landing.
        """
        self.controlID = control_id or self.controlID
        self.control = window.getControl(self.controlID)
        for i in self.items:
            i.onDestroy()
            i.invalidate()
        self.items = []


class _MWBackground(ControlledWindow):
    __slots__ = ("_multiWindow", "started")

    def __init__(self, *args, **kwargs):
        self._multiWindow = kwargs.get('multi_window')
        self.started = False
        BaseWindow.__init__(self, *args, **kwargs)

    def onInit(self):
        if self.started:
            return
        self.started = True
        # Real native close, not just close() (ControlledBase.close() only flips self._closing,
        # see its own docstring) - and done now, before _open() (below), not after. _open() blocks
        # for the entire session (this onInit() call is itself the "outer blocking .modal() call"
        # library.py's goHome() docstring describes), so a close() placed after it - the previous
        # order - would only ever run at genuine session end. Until then this window's native
        # handle stayed alive, shown-but-hidden, at the bottom of Kodi's window stack for the
        # whole session: harmless as long as nothing ever routes an action to it, but if one ever
        # does (a stray/misrouted input reaching the wrong native window - the shell-swap path
        # below this class also only flag-closes the outgoing shell, e.g. openSection()'s
        # self._current.doClose(), library.py), this class's blank bgXML template (script-plex-
        # blank.xml) is what's left on screen, and ControlledWindow.onAction() only reacts to
        # NAV_BACK, so nothing else in the UI responds either - live-observed as a "blank,
        # unresponsive" freeze, force-dismissing here removes it as a possible landing spot.
        self.close()
        self.forceDismiss()
        self._multiWindow._open()


class MultiWindowView(object):
    """A view that only ever exists as a MultiWindow's current window (LibraryWindow's grid and
    Recommended views). Its input takes the same route as a hosted screen's: the host's shared
    routing first (routeActionToHost(), routeClickToHost(), the host's routeFocus()), then the
    view's own handlers, which each view class supplies: viewAction(), viewClick(), viewFocus() and
    handleBack(). The host calls viewAction() and handleBack() itself, from routeAction(), at the
    points in its order where a view's own handling belongs. So the host reads only the controls
    every view shares, and one view's control IDs never reach another's handlers (I4 in the
    navigation review).

    List it before ControlledWindow in the bases. Input on a view the host has swapped out, or
    that hasn't started its first init, is dropped (see BaseWindow.ignoresInput())."""

    # Back, and PREVIOUS_MENU (Escape on a keyboard), both run the view's own Back steps.
    BACK_ACTIONS = (xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_PREVIOUS_MENU)

    def onFirstInit(self):
        host = self.hostedBy()
        if host is not None:
            host._onFirstInit()

    def onReInit(self):
        host = self.hostedBy()
        if host is not None:
            host.onReInit()

    def onClick(self, controlID):
        if not self.routeClickToHost(controlID):
            self.viewClick(controlID)

    def onFocus(self, controlID):
        if self.ignoresInput():
            return
        if not self.hostedBy().routeFocus(controlID):
            self.viewFocus(controlID)

    def onAction(self, action):
        if self.routeActionToHost(action):
            return
        super(MultiWindowView, self).onAction(action)

    def viewAction(self, action):
        """This view's own handling of an action, called by the host's routeAction() after the
        shared steps. True when it used the action; False lets the host's Back and Home handling
        and then Kodi's own have it."""
        return False

    def viewClick(self, controlID):
        """This view's own clicks: every click the host's routeClick() didn't use."""

    def viewFocus(self, controlID):
        """This view's own focus handling: every focus event the host's routeFocus() didn't use."""


class StepTiming(object):
    """How long something took, step by step, logged as one DEBUG line (step 4 in the navigation
    review). mark() records the time since the previous mark, add() a duration measured inside a
    step."""

    def __init__(self, name):
        self.name = name
        self.started = self._last = time.time()
        self.steps = []

    def mark(self, label):
        now = time.time()
        self.steps.append((label, (now - self._last) * 1000))
        self._last = now

    def add(self, label, ms):
        self.steps.append((label, ms))

    def elapsedMs(self):
        return (time.time() - self.started) * 1000

    def stepsText(self):
        return ', '.join('{0} {1}'.format(label, int(ms)) for label, ms in self.steps)

    def log(self):
        """A screen's own setup steps, which the Swap timing line only shows as one onFirstInit."""
        util.DEBUG_LOG("Screen timing: {0}: {1} ms ({2})", self.name, int(self.elapsedMs()), self.stepsText())


def markStep(timing, label):
    if timing is not None:
        timing.mark(label)


def logMoveTiming(window, timing):
    """The "Grid move timing" and "Row move timing" lines (step 12 stage A in the navigation
    review): one arrow press's work, step by step, and the time since the previous press started,
    which shows whether a held key outruns the handler."""
    last = window.__dict__.get('_lastMoveStarted')
    window._lastMoveStarted = timing.started
    util.DEBUG_LOG("{0} timing: {1} ms ({2}), {3}", timing.name, int(timing.elapsedMs()), timing.stepsText(),
                   '{0} ms after the previous press'.format(int((timing.started - last) * 1000))
                   if last is not None else 'first press')


# Python's own collections, now that none are forced after a screen is torn down (63037c16) and
# a closed dialog is only collected when it outlives its caller (util.collectIfAlive()): each one
# stops every Python thread, so one landing mid-build shows up as a stall in the timing lines.
GC_PAUSE_LOG_MS = 10
_gcStarted = {}


def _logGcPause(phase, info):
    if phase == 'start':
        _gcStarted['at'] = time.time()
        return
    started = _gcStarted.pop('at', None)
    if started is None:
        return
    ms = (time.time() - started) * 1000
    if ms >= GC_PAUSE_LOG_MS:
        util.DEBUG_LOG("GC pause: generation {0}, {1} ms, {2} collected", info.get('generation'), int(ms),
                       info.get('collected'))


if _logGcPause not in gc.callbacks:
    gc.callbacks.append(_logGcPause)


# F3 in the navigation review: plexnet signals run their handlers on whichever thread triggers
# them, and a window's handler that touches controls off the main thread can crash Kodi during a
# swap (both 3b crashes). A handler still connected after its window closed keeps the window alive
# and acts on a dead screen. Each case is logged once per handler, signal and reason.
_signalAuditSeen = set()
# The script's own thread, which imports this module. Python sees it as a dummy thread, not
# threading.main_thread().
_MAIN_THREAD_IDENT = threading.get_ident()


def _threadName():
    # HTTP threads are named after their request URL, token included.
    return threading.current_thread().name.split(':http', 1)[0]


def _auditSignal(emitter, signalName, slots):
    offMain = threading.get_ident() != _MAIN_THREAD_IDENT
    for slot in slots:
        owner = getattr(slot, '__self__', None)
        if isinstance(owner, MultiWindow):
            closed = getattr(owner, '_allClosed', False)
        elif isinstance(owner, (BaseWindow, BaseDialog)):
            closed = getattr(owner, '_closing', False)
        else:
            continue
        reasons = []
        if offMain:
            reasons.append('on thread ' + _threadName())
        if closed:
            reasons.append('after its window closed')
        for reason in reasons:
            key = (type(owner).__name__, slot.__func__.__name__, signalName, reason)
            if key in _signalAuditSeen:
                continue
            _signalAuditSeen.add(key)
            util.DEBUG_LOG("Signal audit: {0} from {1} reaches {2}.{3} {4}", signalName, type(emitter).__name__,
                           type(owner).__name__, slot.__func__.__name__, reason)


def _installSignalAudit():
    from plexnet import signalsmixin
    signalsmixin.AUDIT = _auditSignal


_installSignalAudit()


def applyCarriedProps(window, props):
    """Properties carried into a new window or dialog (window_props/dialog_props) go to it and to
    the window on screen underneath. That second write used to happen as a side effect of
    setProperty() before a window was open (see BaseWindow.setProperty()), and the carried props
    rely on it: LibraryWindow.carriedProps restores a hub row's labels on the window beneath a
    dialog, and the dropdown re-applies them there after a sub-menu for the same reason."""
    under = xbmcgui.Window(xbmcgui.getCurrentWindowId())
    for key, value in props.items():
        under.setProperty(key, value)
        window.setProperty(key, value)


class SwapTiming(StepTiming):
    """One screen change on a MultiWindow, logged once the new view has finished its first init.
    Started when a navigation request runs (runPendingNav())."""

    def report(self, view):
        self.mark('onFirstInit')
        util.DEBUG_LOG("Swap timing: {0} -> {1}: {2} ms ({3})", self.name, view.__class__.__name__,
                       int(self.elapsedMs()), self.stepsText())


class MultiWindow(object):
    def __init__(self, windows=None, default_window=None, **kwargs):
        self._windows = windows
        self._next = default_window or self._windows[0]
        self._properties = {}
        self._current = None
        self._background = None
        self._allClosed = False
        self._closeSignalled = False
        self.exitCommand = None
        # Set by open() when a caller (main.py's cold start) needs the same "did it actually
        # become the current window" guarantee BaseWindow.waitForOpen() gives non-MultiWindow
        # callers - see open()/_open() below. None means no caller asked for the check.
        self._openBaseWinID = None
        self._openFailed = False
        # Navigation requests (postNav()), oldest first, run by runPendingNav() from the current
        # view's wait loop. Guarded by _navLock: requests arrive from any thread.
        self._navLock = threading.Lock()
        self._navPending = []
        # UI updates from other threads (postUI()), oldest first, run before navigation.
        self._uiPending = []
        # Per-slice callbacks (addTicker()). Main thread only, so no lock.
        self._tickers = []
        # The write waiting for the cursor to rest (settleLater()): (due, fn, view), or None.
        self._settle = None

    def __getattr__(self, name):
        # dict lookup, not bare self._current - once _open()'s real teardown del's _current,
        # a bare reference has nothing in __dict__, so Python re-enters __getattr__ to resolve
        # it, recursing forever instead of raising. Also reached by openSection() (library.py)
        # checking is_current_window from the debounce thread, possibly after teardown began -
        # see the Home-ControlledWindow plan's "Uncommitted diagnostic-branch fixes" notes.
        current = self.__dict__.get('_current')
        if current:
            return getattr(current, name)
        raise AttributeError(name)

    def forceDismiss(self):
        # _MWBackground never receives routed onAction (the currently-showing concrete window routes
        # its input to this object - routeActionToHost()/MultiWindowView - not to _MWBackground -
        # confirmed live, it never fires), so it can't rely on the dismissOnClose/
        # onAction mechanism ControlledWindow.forceDismiss() otherwise uses; force-dismiss it directly
        # here alongside whichever concrete window is currently showing.
        if self._current:
            self._current.forceDismiss()
        if self._background:
            self._background.forceDismiss()

    def onCloseSignal(self, *args, **kwargs):
        self._closeSignalled = True
        self.doClose()

    def setWindows(self, windows):
        self._windows = windows

    def setDefault(self, default):
        self._next = default or self._windows[0]

    def windowIndex(self, window):
        if hasattr(window, 'MULTI_WINDOW_ID'):
            for i, w in enumerate(self._windows):
                if window.MULTI_WINDOW_ID == w.MULTI_WINDOW_ID:
                    return i
            return 0
        else:
            return self._windows.index(window.__class__)

    def nextWindow(self, window=None):
        if window is False:
            window = self._windows[self.windowIndex(self._current)]

        if window:
            # window is a class here (from self._windows, or an explicit caller-supplied class -
            # every real caller passes one, never an instance), so this must compare directly
            # against self._current's own class, not against window.__class__ (that's the
            # metaclass, e.g. `type` - comparing a metaclass to a real window class can never
            # match). The window=False path above always resolves to self._current's own class
            # (windowIndex(self._current) finds self._current's own position in self._windows),
            # so this bug made this branch permanently unreachable for that caller
            # (_applyItemTypeChoice(), library.py) - every item-type change forced a full,
            # unintended window reconstruction (doClose()+rebuild) instead of the lightweight
            # in-place refill this was supposed to allow, since "no window class exists other
            # than the one already showing" could never be detected. Live-confirmed as a crash
            # for Playlists specifically: a MOVE_SET action arriving while that reconstruction
            # was still in flight hit self.showPanelControl before doRefill() had rebuilt it
            # (AttributeError: 'NoneType' object has no attribute 'getSelectedItem').
            if window == self._current.__class__:
                return None
        else:
            idx = self.windowIndex(self._current)
            idx += 1
            if idx >= len(self._windows):
                idx = 0
            window = self._windows[idx]

        self._next = window
        self._current.doClose()
        return self._next

    # Delay before a posted navigation request runs. None needed (I2 in the navigation review, see
    # the #27239 note in windowutils.py, once SKIN_RELOAD_DEFER_SECONDS); kept so a delay can be
    # tried again in one place.
    NAV_DEFER_SECONDS = 0.0
    # How long a due request waits for the current view to finish initialising (finishedInit)
    # before running anyway - a view whose onFirstInit() raised never sets it.
    NAV_INIT_HOLD_MAX_SECONDS = 3.0

    def postNav(self, name, fn, args=(), kwargs=None, stack=False):
        """Queue a navigation step (a section open, tab switch, Back, server change, go Home) to
        run on the main thread from the current view's wait loop (ControlledBase.wait()), once
        it's NAV_DEFER_SECONDS old and the current view has finished initialising - never on the
        thread that asked. Safe to call from any thread.

        Replaces the threading.Timer each of these used to start, which ran the swap on its own
        thread, mutating this window's state while the main thread went on handling input, and
        let different swaps interleave (S1 in the navigation review).

        A new request replaces everything still pending (the user changed their mind; also
        coalesces a held-down Home button), unless stack=True: Back requests queue behind each
        other so two quick presses go up two levels, each after the previous swap's new view is
        ready."""
        request = (name, fn, tuple(args), dict(kwargs or {}), time.time() + self.NAV_DEFER_SECONDS)
        with self._navLock:
            if not stack and self._navPending:
                util.DEBUG_LOG("MultiWindow: nav request {0} replaces pending {1}", name,
                               [r[0] for r in self._navPending])
                del self._navPending[:]
            self._navPending.append(request)
        util.DEBUG_LOG("MultiWindow: nav request {0} posted", name)

    def postUI(self, name, fn, args=(), kwargs=None):
        """Queue a UI update to run on the main thread from the current view's wait loop, once the
        view has finished initialising - for code reached on some other thread (plexnet signal
        handlers, timers) that touches controls. Unlike postNav() nothing is delayed, replaced or
        dropped: every update runs, in order, ahead of any navigation due on the same tick.

        Live-caught 2026-09-24 (crash dump): plexnet's deferred reachability update fired
        'reachable:server' on its own timer thread just as a server switch showed the new Home
        view, and LibraryWindow's handler updated the server list from that thread - a null read
        inside Kodi while the main thread was in show()."""
        with self._navLock:
            self._uiPending.append((name, fn, tuple(args), dict(kwargs or {}), time.time()))

    def addTicker(self, fn):
        """Call fn(now) from the current view's wait loop, on the main thread, every slice (about
        WAIT_SLICE_SECONDS) until it returns False: for work that advances with the clock on the
        thread that also handles input, such as the hub slide (step 11 in the navigation review),
        so a step and a key press never interleave. Main thread only; adding one that's already
        running does nothing."""
        if fn not in self._tickers:
            self._tickers.append(fn)

    # How long the cursor has to rest before a settleLater() write runs.
    SETTLE_SECONDS = 0.2

    def settleLater(self, fn):
        """Run fn once the cursor has rested SETTLE_SECONDS: each call replaces the write waiting
        and restarts the wait, so a held key runs none until it's let go (step 12 stage D in the
        navigation review). On the main thread, from the ticker. Dropped if the view changes
        first; cancelSettle() drops it when something else writes what it would have."""
        self._settle = (time.time() + self.SETTLE_SECONDS, fn, self.__dict__.get('_current'))
        self.addTicker(self._tickSettle)

    def cancelSettle(self):
        self._settle = None

    def _tickSettle(self, now):
        settle = self.__dict__.get('_settle')
        if settle is None:
            return False
        due, fn, view = settle
        if self.__dict__.get('_current') is not view or getattr(view, '_closing', False):
            self._settle = None
            return False
        if now < due:
            return True
        self._settle = None
        fn()
        return False

    def _runTickers(self, tickers, now):
        for fn in tickers[:]:
            try:
                keep = fn(now)
            except Exception:
                util.ERROR()
                keep = False
            if not keep:
                tickers.remove(fn)

    def navRequestPending(self):
        """Whether a navigation request is waiting to run (postNav())."""
        with self._navLock:
            return bool(self._navPending)

    def navWaitInterval(self):
        """How long the current view's wait loop should wait next: until the oldest request is
        due, if that's sooner than the usual interval, so the delay stays NAV_DEFER_SECONDS. A
        pending UI update is due at once."""
        with self._navLock:
            if self._uiPending:
                return 0.02
            if not self._navPending:
                return None
            remaining = self._navPending[0][4] - time.time()
        return min(getattr(MONITOR, 'wait_interval', 0.1), max(0.02, remaining))

    def _runPendingUI(self, view, now):
        """Run every queued UI update (postUI()), if the view is ready for them."""
        with self._navLock:
            if not self._uiPending:
                return
            posted = self._uiPending[0][4]
            if not getattr(view, 'finishedInit', False) and now - posted < self.NAV_INIT_HOLD_MAX_SECONDS:
                return
            updates = self._uiPending[:]
            del self._uiPending[:]
        for name, fn, args, kwargs, _posted in updates:
            util.DEBUG_LOG("MultiWindow: running UI update {0}", name)
            try:
                fn(*args, **kwargs)
            except Exception:
                util.ERROR()

    def runPendingNav(self, view):
        """Run the tickers (addTicker()), queued UI updates (postUI()), then the oldest due
        navigation request (postNav()). Called from view's wait loop, between waits."""
        now = time.time()
        if self._allClosed:
            return
        tickers = self.__dict__.get('_tickers')
        if tickers:
            self._runTickers(tickers, now)
        self._runPendingUI(view, now)
        if getattr(view, '_closing', False):
            # An update started a swap (e.g. serverRefresh()'s openSection()); navigation waits
            # for the new view.
            return
        with self._navLock:
            if not self._navPending or self._allClosed:
                return
            name, fn, args, kwargs, due = self._navPending[0]
            if due > now:
                return
            if not getattr(view, 'finishedInit', False) and now - due < self.NAV_INIT_HOLD_MAX_SECONDS:
                # Still opening: e.g. Back pressed as a screen appears, before its onInit() has
                # made it Kodi's current window - run it once that's done instead of letting it be
                # declined (live-caught 2026-09-24 as a lost Back).
                return
            self._navPending.pop(0)
        util.DEBUG_LOG("MultiWindow: running nav request {0}, {1:.0f} ms after posting{2}", name,
                       (now - due + self.NAV_DEFER_SECONDS) * 1000,
                       '' if getattr(view, 'finishedInit', False) else ' (view never finished init)')
        # Reported by the next view to finish its first init (SwapTiming); a request that swaps
        # nothing is simply replaced by the next one.
        self._swapTiming = SwapTiming(name)
        self._lastSwapStarted = self._swapTiming.started
        self._swapTiming.add('queued', (now - due + self.NAV_DEFER_SECONDS) * 1000)
        try:
            fn(*args, **kwargs)
        except Exception:
            util.ERROR()

    def _setupCurrent(self, cls):
        # cls is a MultiWindowView: its own class methods forward every callback here.
        self._current = cls(cls.xmlFile, cls.path, cls.theme, cls.res)
        self._current._hostRef = weakref.ref(self)

    @classmethod
    def open(cls, base_win_id=None, **kwargs):
        """base_win_id: same contract as BaseWindow.waitForOpen()'s own kwarg - pass the winID a
        caller needs this MultiWindow to reach or exceed before treating it as genuinely open (main
        .py's cold start, replacing HomeWindow's old create()+waitForOpen()+modal() three-step).
        Checked once, on the very first inner shell _open() constructs - see _open() below. Omit
        for the ordinary sidebar-navigation case (opener.handleOpen()), which never needed this -
        that swap is always into an already-running session.
        """
        mw = cls(**kwargs)
        mw._openBaseWinID = base_win_id
        if base_win_id is not None:
            # base_win_id is only ever passed by the one caller opening this as the app's
            # top-level, session-owning window (main.py's cold start) - never by ordinary
            # sidebar-navigation opens (opener.handleOpen(), which construct/discard many
            # short-lived instances per session). onColdStart() is a no-op here; LibraryWindow
            # overrides it to self-register as windowutils.HOME - doing that unconditionally in
            # __init__ instead would have every incidental in-session LibraryWindow construction
            # stomp the real singleton.
            mw.onColdStart()
        b = _MWBackground(mw.bgXML, mw.path, mw.theme, mw.res, multi_window=mw)
        # kept on mw (not just local) so forceDismiss() can still reach it later, including from
        # within a nested call while b.modal() below is still on the stack (sidebar-focus-driven
        # navigation force-dismisses mw before opening the next window) - see MultiWindow.forceDismiss().
        mw._background = b
        b.modal()
        ref = util.windowRef(b)
        del b
        mw._background = None
        util.collectIfAlive(ref)
        return mw

    def _open(self):
        firstOpen = True
        while not MONITOR.abortRequested() and not self._allClosed:
            try:
                self._setupCurrent(self._next)
            except NO_DATA_ERRORS as e:
                # A screen can load its item as it's constructed (Episodes loads its show): an
                # error here escaped this loop and ended the session (live on the AM6B,
                # 2026-09-27, a show deleted in Plex Web).
                util.LOG('MultiWindow: {0} could not load its item ({1!r})', self._next, e)
                if self.viewFailed(e):
                    continue
                raise

            if firstOpen:
                firstOpen = False
                if self._openBaseWinID is not None:
                    # Mirrors BaseWindow.waitForOpen()'s own retry loop, reused directly since each
                    # concrete shell already IS a BaseWindow subclass - no need to reimplement the
                    # polling here. On failure, break without calling .modal(): the loop-exit cleanup
                    # below still runs (doClose() on whatever _current is), same as a normal close.
                    self._current.show()
                    if not self._current.waitForOpen(base_win_id=self._openBaseWinID):
                        util.LOG("MultiWindow: {} never became the current window, aborting open()", self._current)
                        self._openFailed = True
                        break

            # Swap logging, kept from the hosted-screen crash investigation - see
            # LibraryWindow._setupCurrent()'s first log line.
            util.DEBUG_LOG("MultiWindow: _open() about to call .modal() on {0}", self._current)
            ensureBaseWindow(type(self._current).__name__)
            timing = self.__dict__.get('_swapTiming')
            if timing is not None:
                timing.mark('setup')
            self._current.modal()
            util.DEBUG_LOG("MultiWindow: _open() .modal() on {0} returned", self._current)
            timing = self.__dict__.get('_swapTiming')
            if timing is not None:
                timing.mark('request+close')
            self.viewClosed(self._current)

        self._current.doClose()
        del self._current
        del self._next

    def setProperty(self, key, value):
        self._properties[key] = value
        self._current.setProperty(key, value)

    def _onFirstInit(self):
        for k, v in self._properties.items():
            self._current.setProperty(k, v)

        plexapp.util.APP.on('close.windows', self.onCloseSignal)
        self.onFirstInit()

    def doClose(self, **kw):
        plexapp.util.APP.off('close.windows', self.onCloseSignal)
        self._allClosed = True
        self._current.doClose()

    goHomeAction = XMLBase.goHomeAction

    def viewClosed(self, view):
        """Called in _open()'s loop each time a view's modal() returns, before the next view (_next)
        is set up. Nothing by default."""
        pass

    def viewFailed(self, error):
        """Called in _open()'s loop when setting up the next view (_next) raised one of
        NO_DATA_ERRORS. True if the host has picked another _next to set up instead; False (the
        default) raises the error."""
        return False

    def onColdStart(self):
        """Called once from open(), only when base_win_id was passed - i.e. only for the one
        construction meant to be the app's top-level, session-owning window. No-op here; override
        for whatever singleton-registration/session-lifecycle setup that owner needs (see
        LibraryWindow's override, quiet-orbiting-heron.md's Cold Start plan)."""
        pass

    def onFirstInit(self):
        pass

    def onReInit(self):
        pass

    def routeAction(self, action):
        """The current view's actions come here first (BaseWindow.routeActionToHost()). Returns True
        when the action was used; False hands it back to the view's own onAction()."""
        if action == xbmcgui.ACTION_PREVIOUS_MENU or action == xbmcgui.ACTION_NAV_BACK:
            self.doClose()
        elif self.goHomeAction(action):
            return True
        return False

    def routeClick(self, controlID):
        """A hosted screen's clicks come here first (BaseWindow.routeClickToHost()). Returns True
        when the click was used; False hands it back to the screen's own onClick()."""
        return False

    def routeFocus(self, controlID):
        """A MultiWindowView's focus events come here first. Returns True when the host used the
        event and the view's own viewFocus() should not see it."""
        return False


class SafeControlEdit(object):
    CHARS_LOWER = 'abcdefghijklmnopqrstuvwxyz'
    CHARS_UPPER = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    CHARS_NUMBERS = '0123456789'
    CURSOR = '[COLOR FFCC7B19]|[/COLOR]'

    def __init__(self, control_id, label_id, window, key_callback=None, grab_focus=False):
        self.controlID = control_id
        self.labelID = label_id
        self._win = window
        self._keyCallback = key_callback
        self.grabFocus = grab_focus
        self._text = ''
        self._compatibleMode = False
        self.setup()

    def setup(self):
        self._labelControl = self._win.getControl(self.labelID)
        self._winOnAction = self._win.onAction
        self._win.onAction = self.onAction
        self.updateLabel()

    def setCompatibleMode(self, on):
        self._compatibleMode = on

    def onAction(self, action):
        try:
            controlID = self._win.getFocusId()
            if controlID == self.controlID:
                if self.processAction(action.getId()):
                    return
            elif self.grabFocus:
                if self.processOffControlAction(action.getButtonCode()):
                    self._win.setFocusId(self.controlID)
                    return
        except:
            traceback.print_exc()

        self._winOnAction(action)

    def processAction(self, action_id):
        if not self._compatibleMode:
            oldVal = self._text
            self._text = self._win.getControl(self.controlID).getText()

            if self._keyCallback:
                self._keyCallback(action_id, oldVal, self._text)

            self.updateLabel()

            return True
        oldVal = self.getText()

        if 61793 <= action_id <= 61818:  # Lowercase
            self.processChar(self.CHARS_LOWER[action_id - 61793])
        elif 61761 <= action_id <= 61786:  # Uppercase
            self.processChar(self.CHARS_UPPER[action_id - 61761])
        elif 61744 <= action_id <= 61753:
            self.processChar(self.CHARS_NUMBERS[action_id - 61744])
        elif action_id == 61728:  # Space
            self.processChar(' ')
        elif action_id == 61448:
            self.delete()
        else:
            return False

        if self._keyCallback:
            self._keyCallback(action_id, oldVal, self.getText())

        return True

    def processOffControlAction(self, action_id):
        oldVal = self.getText() if self._compatibleMode else self._text
        if 61505 <= action_id <= 61530:  # Lowercase
            self.processChar(self.CHARS_LOWER[action_id - 61505])
        elif 192577 <= action_id <= 192602:  # Uppercase
            self.processChar(self.CHARS_UPPER[action_id - 192577])
        elif 61488 <= action_id <= 61497:
            self.processChar(self.CHARS_NUMBERS[action_id - 61488])
        elif 61552 <= action_id <= 61561:
            self.processChar(self.CHARS_NUMBERS[action_id - 61552])
        elif action_id == 61472:  # Space
            self.processChar(' ')
        else:
            return False

        if self._keyCallback:
            self._keyCallback(action_id, oldVal, self.getText())

        return True

    def _setText(self, text):
        self._text = text

        if not self._compatibleMode:
            self._win.getControl(self.controlID).setText(text)
        self.updateLabel()

    def _getText(self):
        if not self._compatibleMode and self._win.getFocusId() == self.controlID:
            return self._win.getControl(self.controlID).getText()
        else:
            return self._text

    def updateLabel(self):
        self._labelControl.setLabel(self._getText() + self.CURSOR)

    def processChar(self, char):
        self._setText(self.getText() + char)

    def setText(self, text):
        self._setText(text)

    def getText(self):
        return self._getText()

    def append(self, text):
        self._setText(self.getText() + text)

    def delete(self):
        self._setText(self.getText()[:-1])


class PropertyTimer():
    def __init__(self, window_id, timeout, property_, value='', init_value='1', addon_id=None, callback=None):
        self._winID = window_id
        self._timeout = timeout
        self._property = property_
        self._value = value
        self._initValue = init_value
        self._endTime = 0
        self._thread = None
        self._addonID = addon_id
        self._closeWin = None
        self._closed = False
        self._callback = callback
        self._generation = 0

    def _onTimeout(self):
        self._endTime = 0
        xbmcgui.Window(self._winID).setProperty(self._property, self._value)
        if self._addonID:
            xbmcgui.Window(10000).setProperty('{0}.{1}'.format(self._addonID, self._property), self._value)
        if self._closeWin:
            self._closeWin.doClose()
        if self._callback:
            self._callback()

    def _wait(self, generation):
        while not MONITOR.abortRequested() and time.time() < self._endTime and generation == self._generation:
            xbmc.sleep(100)
        if MONITOR.abortRequested():
            return
        if self._endTime == 0 or generation != self._generation:
            return
        self._onTimeout()

    def _stopped(self):
        return not self._thread or not self._thread.is_alive()

    def _reset(self):
        self._endTime = time.time() + self._timeout

    def _start(self):
        self.init(self._initValue)
        self._generation += 1
        self._thread = threading.Thread(target=self._wait, args=(self._generation,))
        self._thread.start()

    def stop(self, trigger=False):
        self._endTime = trigger and 1 or 0
        if not self._stopped():
            self._thread.join()

    def close(self):
        self._closed = True
        self.stop()
        # The callback is the owning window's: kept, it kept a closed photo screen alive.
        self._callback = None
        self._closeWin = None

    def init(self, val):
        if val is False:
            return
        elif val is None:
            val = self._initValue

        xbmcgui.Window(self._winID).setProperty(self._property, val)
        if self._addonID:
            xbmcgui.Window(10000).setProperty('{0}.{1}'.format(self._addonID, self._property), val)

    def reset(self, close_win=None, init=None):
        self.init(init)

        if self._closed:
            return

        if not self._timeout:
            return

        self._closeWin = close_win
        self._reset()

        # Every reset starts a thread, as it always has (this tested the method itself, always
        # true), but only the newest may fire: the others used to fire too, once each. Reusing a
        # running thread instead would lose a reset landing while it times out.
        self._start()


class WindowProperty():
    __slots__ = ("win", "prop", "val", "end", "old")

    def __init__(self, win, prop, val='1', end=''):
        self.win = win
        self.prop = prop
        self.val = val
        self.end = end
        self.old = self.win.getProperty(self.prop)

    def __enter__(self):
        self.win.setProperty(self.prop, self.val)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.win.setProperty(self.prop, self.end or self.old)


class GlobalProperty():
    __slots__ = ("_addonID", "prop", "val", "end", "old")

    def __init__(self, prop, val='1', end=''):
        self.prop = prop
        self.val = val
        self.end = end
        self.old = xbmc.getInfoLabel('Window(10000).Property(script.plex.{})'.format(prop))

    def __enter__(self):
        xbmcgui.Window(10000).setProperty('script.plex.{}'.format(self.prop), self.val)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        xbmcgui.Window(10000).setProperty('script.plex.{}'.format(self.prop), self.end or self.old)


# BackgroundWindow's (background.py): the window the whole session runs in, and what Kodi should
# show for the moment between one screen closing and the next showing.
BASE_WINDOW_ID = None


def ensureBaseWindow(showing):
    """Called just before a screen shows (MultiWindow._open()). A Kodi window remembers the window
    that was active when it was shown, and goes back to it when it closes. Normally that's the base
    window. But one screen shown while something else was active - Kodi's own home after a window
    that no longer exists closed, or a window that was only flagged closed - remembers that
    instead, and every screen after it did the same: Kodi showed through on each screen change for
    the rest of the session (live on the AM6B, 2026-09-27, after Home from the music player and
    then the photo viewer; seen now and then long before). Reactivating the base window here puts
    it back: Kodi trims its history to it, and the screen about to show remembers it again.
    Skipped while the addon is minimised, when Kodi's home is meant to be showing."""
    if not BASE_WINDOW_ID or util.getGlobalProperty('is_active') != '1':
        return
    current = xbmcgui.getCurrentWindowId()
    if current == BASE_WINDOW_ID:
        return
    util.LOG("Window stack: Kodi shows window {0} before {1}, not the base window {2}: reactivating it",
             current, showing, BASE_WINDOW_ID)
    xbmc.executebuiltin('ActivateWindow({0})'.format(BASE_WINDOW_ID), True)


def sleepForGui(seconds):
    """Wait for something Kodi's GUI thread applies - a list selection, a control becoming
    visible - without handing this thread its queued callbacks. MONITOR.waitFor() runs them inside
    the wait, so a click queued meanwhile ran in the middle of the caller's own setup (F6 in the
    navigation review, the mechanism behind the 52 s grid refill). Kodi applies these on its own
    thread whatever this one is doing, so a plain sleep sees them just as soon."""
    time.sleep(seconds)


VISIBILITY_POLL_SECONDS = 0.02


def waitForVisibility(control, amount=5):
    # Polled every 20 ms, about a frame, against a deadline of amount seconds; it used to be
    # 100 ms, so a button could get focus up to 100 ms after it appeared.
    deadline = time.time() + amount
    while not xbmc.getCondVisibility('Control.IsVisible({0})'.format(control)) and time.time() < deadline \
            and not util.MONITOR.abortRequested():
        sleepForGui(VISIBILITY_POLL_SECONDS)
