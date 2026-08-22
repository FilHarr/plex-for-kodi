from __future__ import absolute_import

import threading
import time

from lib import util
from lib.util import T
from . import dropdown
from . import opener

HOME = None

# Confirmed upstream Kodi core bug (xbmc/xbmc#27552, consolidated into #27239, fix proposed in
# xbmc/xbmc#28928, not yet merged/released as of this writing): CGUIWindow::OnAction() walks the
# focused control's parent chain, and if a skin/window reload (our doClose()-then-reconstruct
# in-place-swap pattern - openSection()/switchTab(), library.py) happens *nested underneath that
# same OnAction() call* - i.e. triggered synchronously, inline, from a native onClick()/onAction()
# callback - the control can be freed mid-walk, and the next dereference is a native access
# violation. A Kodi maintainer's ASAN trace confirmed this is single-threaded reentrancy (all on
# the main thread, T0), not a cross-thread data race: the reload gets processed from inside the
# very OnAction() call it then crashes underneath, once the loop unwinds back into it.
#
# This can't be fixed from the addon side - it's inside Kodi's own CGUIWindow::OnAction(), not
# anything we control - but it CAN be avoided: never trigger a swap synchronously, inline, from a
# native callback. Deferring the actual call via threading.Timer (a real, if small, time delay -
# not just a different Python thread with no delay, which doesn't reliably guarantee Kodi's own
# call stack has unwound by the time it runs) lets Kodi's engine fully return to idle first. Live-
# confirmed as the fix for a native crash that otherwise recurred at the exact same faulting
# address across independent crash dumps - i.e. one deterministic bug, not generic corruption.
#
# The addon's existing sidebar focus-settle debounce (sectionChanged()/_sectionChanged() below,
# 0.5s) already provides this delay incidentally, which is almost certainly why swapping sections
# via arrow-key/settled-focus navigation has always been reliable - this constant is for direct-
# click dispatch paths (sectionClicked(), library.py's tab-list onClick()) that had no delay at
# all before this was diagnosed. Short enough to feel instant to a user, long enough (many frames
# at any realistic refresh rate) to be a real safety margin, not a token gesture.
SKIN_RELOAD_DEFER_SECONDS = 0.15


class GoHomeMixin():
    def goHome(self, section=None, with_root=False):
        HOME.go_root = with_root
        # closeWithCommand()/doClose() below only flips a flag on windows using the doModal()-emulation
        # pattern (ControlledWindow/MultiWindow) - forceDismiss() is the real Kodi-native dismiss, so
        # HOME.show() below always lands on a clean stack instead of pushing on top of self. No-op on
        # window classes that don't need it (see BaseFunctions.forceDismiss()).
        self.forceDismiss()

        if section:
            self.closeWithCommand('HOME:{0}'.format(section))
        else:
            self.closeWithCommand('HOME')

        HOME.show()

    def goHomeRoot(self, *args, **kwargs):
        HOME.go_root = True
        self.forceDismiss()
        self.closeWithCommand('HOME')
        HOME.show()


class SidebarMixin():
    """Control ids for the persistent vertical nav rail (includes/sidebar.xml.tpl)
    and its server/user dropdowns (includes/sidebar_dropdowns.xml.tpl). Any window
    that includes header_sidebar (see default.xml.tpl) can mix this in to reuse the
    same ids instead of redeclaring them.
    """
    SIDEBAR_GROUP_ID = 9000
    SECTION_LIST_ID = 9001

    SERVER_BUTTON_ID = 201
    USER_BUTTON_ID = 202

    USER_LIST_ID = 250
    SERVER_LIST_ID = 260
    SERVER_LIST_SCROLLBAR_ID = 261

    SERVER_MENU_GROUP_ID = 802
    SERVER_MENU_BG_ID = 800
    USER_MENU_BG_ID = 801
    USER_MENU_GROUP_ID = 901

    def reselectActiveSection(self, controlID, previousFocusID):
        """Call from onFocus(controlID), passing the control that had focus immediately before
        (self.lastFocusID, captured before it gets overwritten with controlID). If focus just moved
        onto the section list from outside the sidebar's own controls, snap the highlight to
        whichever item carries is.active - the section actually on screen - instead of leaving it on
        the list's last internally-browsed position, or, on a window's first focus event, index 0,
        which is always Search.
        """
        if controlID != self.SECTION_LIST_ID:
            return

        if previousFocusID in (self.SIDEBAR_GROUP_ID, self.SECTION_LIST_ID,
                                self.SERVER_BUTTON_ID, self.USER_BUTTON_ID):
            return

        sectionList = getattr(self, 'sectionList', None)
        if not sectionList:
            return

        for i in range(sectionList.size()):
            mli = sectionList[i]
            if mli and mli.getProperty('is.active'):
                sectionList.setSelectedItemByPos(i)
                return

    def openSidebarTarget(self, open_fn, *args, **kwargs):
        """Open a sidebar-reached window (call `open_fn(*args, **kwargs)`, e.g.
        opener.sectionClicked(section)) the way every sidebar-driven hop should: force-dismiss
        self's real Kodi window first, so the new window replaces it on Kodi's native stack instead
        of pushing on top of it - see forceDismiss() on ControlledWindow/MultiWindow.
        self.doClose()'s own flag-only close still happens afterwards via processCommand(), same as
        before, for the (possibly bubbled-up) exit command handling.
        """
        self.forceDismiss()
        self.processCommand(open_fn(*args, **kwargs))

    # --- Focus-driven section navigation ---------------------------------------------------
    #
    # checkSectionItem()/sectionChanged()/_sectionChanged() debounce sidebar focus movement
    # (originally home.py-only) so settling on a section - not just clicking it - opens it.
    # _dispatchSectionOpen(item) is what actually happens once the debounce settles on a genuinely
    # different section; sectionClicked() is the immediate, non-debounced click path, sharing the
    # same dispatch. HomeWindow overrides _dispatchSectionOpen() to keep its existing in-place hub
    # preview instead (it never leaves itself via this path) and keeps its own separate
    # sectionClicked(), since click and settled-focus intentionally do different things there.

    def _ensureSidebarNavState(self):
        """Lazy-init for windows other than HomeWindow, which already sets these in __init__.
        lastSection seeds from whichever sidebar entry is already marked is.active (the section
        this window itself belongs to/is displaying, per buildSectionList()) so simply re-focusing
        or re-clicking your own current section doesn't look like a change and doesn't reopen it -
        this is what let library.py's old explicit `section.key == self.section.key` guard go away
        in favor of the same lastSection tracking HomeWindow already used.
        """
        if not hasattr(self, 'sectionChangeTimeout'):
            self.sectionChangeTimeout = 0
            self.sectionChangeThread = None
        if not hasattr(self, 'lastSection'):
            self.lastSection = None
            sectionList = getattr(self, 'sectionList', None)
            if sectionList:
                for i in range(sectionList.size()):
                    mli = sectionList[i]
                    if mli and mli.getProperty('is.active'):
                        self.lastSection = mli.dataSource
                        break

    def checkSectionItem(self, force=False, action=None):
        self._ensureSidebarNavState()

        item = self.sectionList.getSelectedItem()
        if not item or item.getProperty('is.search'):
            return

        self._onSectionItemFocused(item)

        if item.dataSource != self.lastSection or force:
            self.sectionChanged(force=force)

    def _onSectionItemFocused(self, item):
        """Hook: runs on every settled focus, even when the section hasn't changed. HomeWindow
        overrides this to storeLastBG() on its own entry; nothing to do for everyone else."""
        pass

    def sectionChanged(self, force=False):
        if getattr(self, '_shuttingDown', False):
            return

        self.sectionChangeTimeout = time.time() + 0.5

        self._waitForPendingFetches()

        if force:
            self.sectionChangeTimeout = None
            self._sectionChanged(immediate=True)
            return

        if not self.sectionChangeThread or (self.sectionChangeThread and not self.sectionChangeThread.is_alive()):
            self.sectionChangeThread = threading.Thread(target=self._sectionChanged, name="sectionchanged")
            self.sectionChangeThread.start()

    def _waitForPendingFetches(self):
        """Hook: block briefly if a fetch relevant to currently-displayed content is still in
        flight, so a settling debounce doesn't act against stale state. HomeWindow overrides this
        with its own busy-spinner + task-list wait; nothing worth waiting on here otherwise yet."""
        pass

    def _sectionChanged(self, immediate=False):
        if getattr(self, '_shuttingDown', False):
            return

        # Set by LibraryWindow while sectionMenu()'s modal dropdown is up (home.py's HomeWindow has
        # an identical guard for the same reason) - without it, a debounce thread already in flight
        # from focus movement just before the context menu opened could settle on a section change
        # mid-menu, racing sectionMenu()'s own return-value handling. Default False via getattr so
        # windows that never set this attribute (anything but LibraryWindow) are unaffected.
        if getattr(self, 'block_section_change', False):
            return

        if not immediate:
            if not self.sectionChangeTimeout:
                return
            while not util.MONITOR.waitFor():
                # timing issue
                if not self.sectionChangeTimeout:
                    return
                if time.time() >= self.sectionChangeTimeout:
                    break

            # by the time the debounce settled, focus may have moved past the section list
            # entirely (e.g. down onto the server/user button) - the selection it's about to
            # read is stale in that case, so don't act on a section the user isn't even browsing
            # anymore
            if self.getFocusId() != self.SECTION_LIST_ID:
                return

        item = self.sectionList.getSelectedItem()
        if not item or item.getProperty('is.search') or item.dataSource is None:
            # checkSectionItem() applies this same filter when it starts the debounce timer, but
            # focus can still move onto Search (or anything else with no real section behind it)
            # inside the section list before the timer fires - the "focus left the list entirely"
            # check above doesn't catch that, since it never leaves SECTION_LIST_ID. Re-checking
            # here against this settled-on item, not just the one that started the timer, is what
            # was missing - live-confirmed crash otherwise (opener.sectionClicked() dereferencing
            # a None section).
            return

        if self.lastSection == item.dataSource:
            return

        self._dispatchSectionOpen(item)

    def _dispatchSectionOpen(self, item):
        """What happens once the debounce settles on a genuinely different section (also reused by
        sectionClicked() below for the immediate click path). is.home is no longer special-cased
        up front (Home-ControlledWindow plan, item 1 - "fold home_section into openSection()"):
        home_section is just another section value now, indistinguishable from a real one, to any
        window with in-place swap support (openSection() - LibraryWindow). Skips if it's the
        section this window already shows (see _ensureSidebarNavState()'s lastSection seeding -
        this replaces library.py's old explicit `section.key == self.section.key` check), else ->
        opener.sectionClicked(). HomeWindow overrides this entirely (preview only, never opens a
        window).

        playlists_section is likewise no longer special-cased here (Playlists port, ported from the
        Sidebar-Tab-Unification branch's identical change): it used to always push a standalone
        PlaylistsWindow, the one sidebar target that couldn't do an in-place swap and so had to stay
        parked underneath other windows - a structural bug where Exit could silently fail and land
        back on Playlists instead of quitting. PlaylistsSection now carries enough of a real-section
        surface (TYPE='playlists', getLibrarySectionId(), see home.py) for
        opener.sectionClicked() to route it through library.LibraryWindow like any other section
        (opener.py's own VIEWS_SQUARE check), so it falls through to the same branches below as
        everything else - the in-place swap for windows with openSection(), the generic
        openSidebarTarget(opener.sectionClicked, section) push otherwise.

        The one remaining is.home special case (final elif below) is for windows *without*
        openSection() - ShowWindow/PrePlayWindow's own independent sidebar (see the plan's "Known
        interim gaps"/"Descendant windows" note - untouched by this work). Home has no equivalent
        "open a fresh window for this section" the way ordinary sections do via
        opener.sectionClicked() (there is no standalone HomeWindow-equivalent to open freshly), so
        it still needs goHome()'s real, separate-window navigation there. Still click-only (main-
        thread-gated): goHome() itself still makes a new blocking .modal() call (HOME.show()) - the
        exact reentrancy-unsafe shape this whole plan exists to eliminate - unrelated to this
        fold-in and not yet solved for these descendant-sidebar windows specifically.
        """
        section = item.dataSource
        if section == self.lastSection:
            return

        if hasattr(self, 'openSection'):
            # In-place swap (library.py's LibraryWindow.openSection()) - safe to call from any
            # thread, no new blocking .modal() call, home_section included (openSection() forces
            # contentMode to 'recommended' when the target section has no library-grid content at
            # all - see that method's own comment). Declines (returns False) rather than acting
            # if a descendant window is currently open on top of self - see that method's own
            # docstring. lastSection only advances on an actual swap, so a declined attempt gets
            # retried on the next settled focus/click instead of being silently forgotten.
            #
            # Deferred, not called inline: this method is reached directly from onClick()
            # (sectionClicked() above) on a genuine click, unlike the settled-focus debounce path
            # (sectionChanged()/_sectionChanged() below) that already runs this same call off a
            # background thread with a real delay. Calling openSection() (and its doClose()) here
            # inline would nest the resulting skin/window reload underneath the very onClick()/
            # OnAction() call handling this click - see SKIN_RELOAD_DEFER_SECONDS' own comment
            # above for why that's a confirmed Kodi core crash, not a theoretical one.
            def _deferredOpenSection():
                if self.openSection(section):
                    self.lastSection = section
            threading.Timer(SKIN_RELOAD_DEFER_SECONDS, _deferredOpenSection).start()
        elif item.getProperty('is.home'):
            if threading.current_thread() is not threading.main_thread():
                return
            self.goHome()
        else:
            self.lastSection = section
            self.openSidebarTarget(opener.sectionClicked, section)

    def sectionClicked(self):
        self._ensureSidebarNavState()

        item = self.sectionList.getSelectedItem()
        if not item:
            return

        if item.getProperty('is.search'):
            self.searchButtonClicked()
            return

        self._dispatchSectionOpen(item)


class UtilMixin(GoHomeMixin):
    def __init__(self):
        self.exitCommand = None

    def openItem(self, obj, **kwargs):
        self.processCommand(opener.open(obj, **kwargs))

    def openWindow(self, window_class, **kwargs):
        self.processCommand(opener.handleOpen(window_class, **kwargs))

    def processCommand(self, command):
        if command and command.startswith('HOME'):
            self.exitCommand = command
            self.doClose()
        elif command and command == "NODATA":
            raise util.NoDataException

    def closeWithCommand(self, command):
        self.exitCommand = command
        self.doClose()

    def showAudioPlayer(self, **kwargs):
        from . import musicplayer
        self.processCommand(opener.handleOpen(musicplayer.MusicPlayerWindow, **kwargs))

    def getNextShowEp(self, pl, items, title):
        revitems = list(reversed(items))
        in_progress = [i for i in revitems if i.get('viewOffset').asInt()]
        if in_progress:
            n = in_progress[0]
            pl.setCurrent(n)

            if not util.getSetting('assume_resume'):
                choice = dropdown.showDropdown(
                    options=[
                        {'key': 'resume', 'display': T(32429, 'Resume from {0}').format(
                            util.timeDisplay(n.viewOffset.asInt()).lstrip('0').lstrip(':'))},
                        {'key': 'play', 'display': T(32317, 'Play from beginning')}
                    ],
                    pos=(660, 441),
                    set_dropdown_prop=False,
                    header=u'{0} - {1} \u2022 {2}'.format(title,
                                                          T(32310, 'S').format(n.parentIndex),
                                                          T(32311, 'E').format(n.index))
                )

                if not choice:
                    return None

                if choice['key'] == 'resume':
                    return True
            else:
                return True
            return False

        watched = False
        for (k, i) in enumerate(revitems):
            if watched:
                try:
                    pl.setCurrent(revitems[k-2])
                    return False
                except IndexError:
                    break
            if i.get('viewCount').asInt() > 0:
                watched = True

        non_special = [i for i in revitems if i.get('parentIndex').asInt() and i.get('viewCount').asInt() == 0]
        use = items[0]
        if non_special:
            use = non_special[-1]
        pl.setCurrent(use)
        return False



def shutdownHome():
    global HOME
    if HOME:
        HOME.shutdown()
    del HOME
    HOME = None
