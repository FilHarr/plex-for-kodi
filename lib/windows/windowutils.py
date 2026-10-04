from __future__ import absolute_import

import weakref

from lib import util
from lib.util import T
from . import dropdown
from . import home
from . import kodigui
from . import navintent
from . import opener
from . import sidebar_model

HOME = None
_restartingForSkinReload = False


def restartAfterSkinReload(reason):
    """
    Closes Home with its closeOption at "restart": _main() returns, and main.realExit() runs the
    addon again from a clean state. For a skin reload with us open, noticed either by the monitor
    (GUI.OnSkinLoaded: Kodi 22, and the p3i CoreELEC builds) or by a window finding its controls
    rebuilt (kodigui.XMLBase.onInit(), stock Kodi 21). Only the first one to notice restarts.
    """
    global _restartingForSkinReload
    if _restartingForSkinReload or HOME is None:
        return
    _restartingForSkinReload = True
    util.LOG("Skin reload: restarting the addon ({0})", reason)
    HOME.closeOption = "restart"
    HOME.doClose()

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
# Used by the click dispatch paths (sectionClicked(), library.py's tab-list onClick()) that had no
# delay at all before this was diagnosed. Short enough to feel instant to a user, long enough (many
# frames at any realistic refresh rate) to be a real safety margin, not a token gesture.
#
# Since S1 (navigation review), swaps no longer start their own timers: they're posted to the host
# (kodigui.MultiWindow.postNav()) and run on the main thread from the current view's wait loop,
# after the callback that asked has returned. Without any delay (I2, settled 2026-09-25): tab,
# sidebar, Back and item-open stress tests at 0 and 150 ms on the PC and the AM6B found no crash
# tied to the delay - the ones they did find were races the delay neither caused nor prevented.
# The swap was already only a close flag when this went in (74b775cb), and that commit changed
# the hub bind and the hub-slide thread too, so the delay may never have been what fixed the
# crash. The last user, opener.py's standalone season open, opens directly since 3f stage E, and
# the constant (SKIN_RELOAD_DEFER_SECONDS = 0.15) is gone. The comments that name it point here,
# to this note on the #27239 reentrancy crash.


class GoHomeMixin():
    # _chainHost is None for every window except a shell hosted inside a LibraryWindow-hosted
    # descendant chain (set by LibraryWindow._setupCurrent(), library.py), or LibraryWindow itself
    # (which points this at self - see LibraryWindow.__init__'s own comment for why). See
    # hashed-orbiting-pizza.md's Phase 1. A chained shell's own forceDismiss()/closeWithCommand()
    # only ever touch itself, not the host - the host's _open() poll loop would just reconstruct and
    # reopen the same shell again, since neither its _allClosed flag nor _next/_nextKwargs changed -
    # goHome()/goHomeRoot() below must operate on the host itself once one exists, not on the
    # chained shell that happened to receive the call.
    #
    # Held weakly, so a shell (and LibraryWindow's own self-reference) makes no reference cycle
    # with the host - see LibraryWindow._setupCurrent(). The host outlives its shells.
    _chainHostRef = None

    @property
    def _chainHost(self):
        ref = self._chainHostRef
        return ref() if ref is not None else None

    @_chainHost.setter
    def _chainHost(self, host):
        self._chainHostRef = weakref.ref(host) if host is not None else None

    def _liveChainHost(self):
        """None if this window was never chained, OR if its host has already fully closed
        (_allClosed - a real, never-del'd attribute, unlike _current, which MultiWindow._open()'s
        teardown does del - kodigui.py) - live-confirmed crash otherwise: a call already in flight
        on another thread from *before* a swapTo() swapped this shell out (or the whole chain
        closed) can land here well after self._chainHost's own _current is gone. A stale
        reference here, not a bug in the caller, so treating it as "nothing left to act on" is
        correct, not a workaround."""
        host = self._chainHost
        if host is not None and host._allClosed:
            return None
        return host

    def goHome(self, section=None, with_root=False, force=False):
        self.navigate(navintent.home(section=section, root=with_root, force=force))

    def goHomeRoot(self, *args, **kwargs):
        self.navigate(navintent.home(root=True))

    def navigate(self, intent):
        """Act on a NavIntent (navintent.py, I5 in the navigation review). A hosted screen hands it
        to its host, which acts on it through its navigation queue; any other window leaves for
        Home with it (leaveFor()). LibraryWindow overrides this as the host that acts.

        A section may be a bare key (a str, or plexobjects.PlexValue, from getLibrarySectionId():
        the music player's / Album screen's / photo directory's "Go to <section>"): Home resolves
        it to the sidebar's own section object (LibraryWindow.resolveSection())."""
        host = self._liveChainHost()
        if host is not None and host is not self:
            util.DEBUG_LOG('Navigate: {0} from hosted {1}, to its host', intent, type(self).__name__)
            host.navigate(intent)
            return
        self.leaveFor(intent)

    def leaveFor(self, intent):
        """Outside the chain, and not Home: Home takes the intent at once (returnHere()), and this
        window closes with it as its exitCommand, so each blocking window beneath it closes in turn
        as it passes through their processCommand().

        Home takes it now rather than when the bubble reaches it: its navigation queue only runs
        from its own view's wait loop, once the closing windows are gone, and a caller that drops
        the result (the hub menu's "Go to show", say) can't lose it. It used to be stashed on Home
        (_pendingSection, go_root) until a 'HOME' exit command arrived, and a dropped one left a
        section there for the next Home command to open.

        forceDismiss() first: closeWithCommand()'s doClose() only flips a flag on windows using the
        doModal()-emulation pattern (ControlledWindow/MultiWindow), so Home's show() lands on a
        clean stack instead of pushing on top of this one. No-op on window classes that don't need
        it (see BaseFunctions.forceDismiss())."""
        util.DEBUG_LOG('Navigate: {0} from {1}, outside the chain: to Home, closing', intent,
                       type(self).__name__)
        self.forceDismiss()
        self.closeWithCommand(intent)
        HOME.returnHere(intent)


class SidebarMixin():
    """Control ids for the persistent vertical nav rail (includes/sidebar.xml.tpl)
    and its user dropdown (includes/sidebar_dropdowns.xml.tpl) and Libraries button. Any window
    that includes header_sidebar (see default.xml.tpl) can mix this in to reuse the
    same ids instead of redeclaring them.
    """
    SIDEBAR_GROUP_ID = 9000
    SECTION_LIST_ID = 9001

    SERVER_BUTTON_ID = 201
    USER_BUTTON_ID = 202

    USER_LIST_ID = 250

    USER_MENU_BG_ID = 801
    USER_MENU_GROUP_ID = 901

    def dismissSidebarPopupOnBack(self, target=None):
        """Call first, before any other NAV_BACK/PREVIOUS_MENU handling, in every SidebarMixin
        window's own onAction() - not just LibraryWindow's (a real hosted shell's onAction goes
        through the host first, kodigui.BaseWindow.routeActionToHost(), but an *unhosted* real
        shell still runs its own onAction, so this has to be reachable from both). The user dropdown
        (includes/sidebar_dropdowns.xml.tpl) is visible off Control.HasFocus(250) - remote/keyboard
        navigation onto the list - OR the show.options Window property (the mouse-click path, which
        doesn't move focus). Live-confirmed bug otherwise: pressing back while it was open fell through to
        this window's normal back-handling instead - popping the descendant chain a step
        (library.py's own _backStack check) or closing the window outright (doClose(), in every
        real shell's own onAction) - rather than just dismissing the popup, like every other
        "back closes the topmost overlay first" control in this addon already does (e.g.
        EpisodesWindow.onAction()'s own OPTIONS_GROUP_ID redirect). Returns True if it dismissed a
        popup (caller should return immediately, doing no further back-handling), False otherwise.

        target: LibraryWindow._sidebarTarget() from a LibraryWindow caller - setFocusId() (unlike
        the show.options property write just below, and unlike getFocusId() itself)
        is a real control write, and must never land on self while self is a LibraryWindow
        currently hosting a real shell (see _sidebarTarget()'s own comment for the native crash
        that's confirmed to cause). Omitted (defaults to self) from a real shell's own onAction(),
        which - per the note above - only ever runs this while genuinely unhosted, where self's
        own native window is always the live one."""
        if target is None:
            target = self
        controlID = self.getFocusId()
        if controlID == self.USER_LIST_ID or self.getProperty('show.options'):
            self.setBoolProperty('show.options', False)
            target.setFocusId(self.USER_BUTTON_ID)
            return True
        return False

    def buildSectionList(self):
        """Fill self.sectionList with the sidebar's entries (sidebar_model.sections()), marking the
        one sidebarActiveSection() picks as is.active and selecting it, so the list's cursor is on
        it the first time focus lands there rather than on Search. Writes go through the list's own
        guard (LibraryWindow's _sidebarListGuard() for its lists)."""
        entries = sidebar_model.sections(self.sidebarNavSettings(), onChange=self._sidebarEntriesChanged)
        active = self.sidebarActiveSection([home.home_section] + entries)
        active_pos = None

        searchmli = kodigui.ManagedListItem(T(32431, 'Search'), iconImage='script.plex/buttons/search.png')
        searchmli.setProperty('is.search', '1')
        searchmli.setProperty('item', '1')
        items = [searchmli]

        for section in [home.home_section] + entries:
            if section is home.home_section:
                mli = kodigui.ManagedListItem(T(32332, 'Home'), iconImage='script.plex/home/type/home.png',
                                              data_source=section)
                mli.setProperty('is.home', '1')
            else:
                mli = kodigui.ManagedListItem(section.title,
                                              iconImage='script.plex/home/type/{0}.png'.format(section.type),
                                              data_source=section)
                server = sidebar_model.serverName(section)
                if server:
                    mli.setProperty('server.name', server)
                if section == home.playlists_section:
                    mli.setProperty('is.playlists', '1')
                    mli.setIconImage('script.plex/home/type/playlists.png')
                elif section == home.watchlist_section:
                    mli.setIconImage('script.plex/home/type/watchlist.png')
            mli.setProperty('item', '1')
            if active is not None and section == active:
                mli.setProperty('is.active', '1')
                active_pos = len(items)
            items.append(mli)

        self.sectionList.reset()
        self.sectionList.addItems(items)
        if active_pos is not None:
            self.sectionList.selectItem(active_pos)

    def sidebarNavSettings(self):
        """The sidebar's stored list (sidebar_model.loadNavSettings()). LibraryWindow keeps it as
        state its section menu and the Libraries picker edit."""
        return sidebar_model.loadNavSettings()

    # What a screen shows, by the attribute screens keep it under: its server picks between two
    # servers' libraries with the same key (sidebarServer()).
    SIDEBAR_ITEM_ATTRS = ('video', 'mediaItem', 'show_', 'season', 'album', 'collection', 'playlist', 'section')

    def sidebarServer(self):
        """The server of what this screen shows, if it shows something with one."""
        for name in self.SIDEBAR_ITEM_ATTRS:
            server = getattr(getattr(self, name, None), 'server', None)
            if server is not None and getattr(server, 'uuid', None):
                return server
        return None

    def sidebarActiveSection(self, entries):
        """Which of entries (Home first, then sidebar_model.sections()) is highlighted as the
        section on screen. By default the section this screen was entered from (entrySectionId,
        inherited down a drill chain or the item's own library), on this screen's server, else
        Watchlist when it came from there. Screens with their own idea override this."""
        return sidebar_model.matchSection(entries, getattr(self, 'entrySectionId', None),
                                          getattr(self, 'entryFromWatchlist', False), server=self.sidebarServer())

    def _sidebarEntriesChanged(self):
        """A background check (a server's libraries, sidebar_model.serverSections(); or whether it
        has playlists, hasPlaylists()) found a different answer from the one this sidebar was built
        with. On a worker thread; LibraryWindow rebuilds."""
        pass

    def displayServerAndUser(self, **kwargs):
        """The sidebar's avatar, user name and server icon and name. Window properties are
        per-window, so each window sets its own."""
        for key, value in sidebar_model.serverAndUserProperties():
            self.setProperty(key, value)

    def _selectActiveSection(self):
        """Select the sidebar entry marked is.active - the section actually on screen. The rule this
        maintains: whenever the section list doesn't have focus, its selection is the active
        section, so the collapsed rail never shows a section the user only scrolled past. Walks the
        Python-side items rather than sectionList[i], which makes a native getListItem() call per
        entry."""
        sectionList = getattr(self, 'sectionList', None)
        if not sectionList:
            return

        for i, mli in enumerate(sectionList.items):
            if mli.getProperty('is.active'):
                sectionList.setSelectedItemByPos(i)
                return

    def reselectActiveSection(self, controlID, previousFocusID):
        """Call from onFocus(controlID), passing the control that had focus immediately before
        (self.lastFocusID, captured before it gets overwritten with controlID). Sections only open
        on a click, so browsing the list moves nothing but the highlight - this snaps it back to the
        active section when focus leaves the list, and when focus enters it from outside the
        sidebar's own controls (on a window's first focus event the list would otherwise sit on
        index 0, which is always Search). Skipped while sectionMover() owns the selection."""
        if getattr(self, 'movingSection', False):
            return

        if controlID == self.SECTION_LIST_ID:
            if previousFocusID in (self.SIDEBAR_GROUP_ID, self.SECTION_LIST_ID,
                                   self.SERVER_BUTTON_ID, self.USER_BUTTON_ID):
                return
        elif previousFocusID != self.SECTION_LIST_ID:
            return

        self._selectActiveSection()

    def _dispatchSectionOpen(self, item):
        """Open the clicked sidebar section fresh. A click always acts, even on the section already
        showing: that resets it to its root (from a descendant, unwinds the chain back to it).

        Two cases, split on whether self is the true root (windowutils.HOME):

        - self IS HOME: in-place swap (library.py's LibraryWindow.openSection()),
          posted through the navigation queue by _deferOpenSection().

        - self is a descendant - a real hosted shell lands here (ShowWindow, PrePlayWindow,
          EpisodesWindow...): the host's routeClick() runs the shell's own sectionClicked(), so
          its Search entry stays scoped to its own item. goHome() bubbles the section up to the
          host, carrying force so library.py's goHome() override doesn't no-op on the
          already-active section.
        """
        section = item.dataSource
        if self is HOME:
            self._deferOpenSection(section, force=True)
        else:
            self.goHome(section=section, force=True)

    def sectionClicked(self):
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
        # context=self (hashed-orbiting-pizza.md Phase 4): lets opener.open()'s dispatch call
        # self.openWindow(...) instead of unconditionally handleOpen()-ing, for whichever object
        # types its dispatch has been made chain-aware for (see opener.py's own docstring on
        # open() for the current list - everything except photo/track/clip, which deliberately
        # stay standalone). Inert (ignored) for those few types - safe for every existing caller.
        self.processCommand(opener.open(obj, context=self, **kwargs))

    def openWindow(self, window_class, **kwargs):
        # A prior attempt hosted chains via a separate DescendantContainer class
        # (descendant_container.py, since deleted) - genesis-open of that class was reverted
        # after a real, session-breaking native window-stack desync was found live
        # (hashed-orbiting-pizza-history.md). hashed-orbiting-pizza.md's Phase 1 replaces that
        # design: LibraryWindow now hosts chains directly on itself (library.py), pointing
        # _chainHost at self unconditionally, and at itself on each real shell it swaps in
        # (LibraryWindow._setupCurrent()) - so this swapTo() branch is live again, targeting a
        # LibraryWindow host rather than a second MultiWindow.
        host = self._liveChainHost()
        if host is not None:
            # Posted like every other swap (MultiWindow.postNav()), not run inside the click (I2 in
            # the navigation review). Also coalesces a double click into one open: inline, the
            # second click's swapTo() pushed the still-showing screen onto the back stack twice.
            host.postNav('open ' + window_class.__name__, host.swapTo, args=(window_class,),
                         kwargs=kwargs)
            return
        # only a chain host has a back stack to root (LibraryWindow.swapTo())
        kwargs.pop('chain_root', None)
        self.processCommand(opener.handleOpen(window_class, **kwargs))

    def processCommand(self, command):
        """The result of a blocking open (opener.handleOpen()). A NavIntent passing through
        (navintent.py) has already reached Home, which acts on it; this window closes too, passing
        it on to whatever opened it - unless it's hosted, when its host decides (Home stays; a
        nested library window hosting it closes). A window that couldn't open (navintent.noData())
        raises NoDataException here, for the caller's own handling."""
        if navintent.isNoData(command):
            raise util.NoDataException
        if navintent.isNavIntent(command):
            host = self._liveChainHost()
            if host is not None and host is not self:
                host.processCommand(command)
                return
            util.DEBUG_LOG('Navigate: {0} passing through {1}, closing', command, type(self).__name__)
            # A real close, as leaveFor() does for the window the intent started from: doClose()
            # only flags a ControlledWindow (the music player, say) closed, and its Kodi window
            # stayed open and active under the next screen (live on the AM6B, 2026-09-27).
            self.forceDismiss()
            self.exitCommand = command
            self.doClose()

    def closeWithCommand(self, command):
        self.exitCommand = command
        self.doClose()

    def showAudioPlayer(self, **kwargs):
        from . import musicplayer
        self.processCommand(opener.handleOpen(musicplayer.MusicPlayerWindow, **kwargs))

    def getNextShowEp(self, pl, items, title, on_deck=None, specials_mode='default'):
        """Pick which episode `pl` should start on, and return whether to resume it.

        True/False = start on the item just set as current, resuming or not; None = the user backed
        out of the resume prompt and nothing should play at all.

        `on_deck` is the show's own OnDeck list (Show.onDeck, populated by the includeOnDeck=1
        reload its window already does). Plex's on-deck pick is a whole-show "continue watching"
        heuristic, which is exactly the question a show-level Play button asks - unlike
        EpisodesWindow._defaultEpisode() (episodes.py), which needs one specific season's own next
        episode and deliberately doesn't use it. An entry in it is authoritative, specials included;
        the only pick that gets ignored is one that isn't in `items` at all. Optional - without it,
        this falls back to the local scan it always did.

        `specials_mode` must be the tv_specials_order value `items` was built with
        (reorder_with_specials(), plexnet/playlist.py) - passed in rather than read here so the queue
        order and this pick can't disagree about it. Under 'interleave' that ordering has already
        decided where each special belongs by air date, so the scan below stops skipping them.

        The pick itself is pickShowEp() below - this only adds the playlist and the prompt.
        """
        n = self.pickShowEp(items, on_deck=on_deck, specials_mode=specials_mode)
        if n is None:
            return False

        pl.setCurrent(n)

        # Nothing to resume - an on-deck pick is usually just the next unwatched episode, and
        # there's no question to ask about starting one of those from the beginning.
        if not n.get('viewOffset').asInt():
            return False

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

    def pickShowEp(self, items, on_deck=None, specials_mode='default'):
        """Which episode a show-level Play would start on, or None for an empty queue.

        Split out of getNextShowEp() above so the same answer can be had without touching a
        playlist or putting a dialog on screen - the Seasons screen's own Play button labels
        itself with it (setPlayButtonState(), subitems.py), off a background thread. Keep it free
        of side effects for that reason.
        """
        if not items:
            return None

        revitems = list(reversed(items))

        n = None
        for v in (on_deck or []):
            # __eq__ on these is ratingKey-based (media.MediaItem), so this both tests membership
            # and lets setCurrent() below find the position. Membership matters: the playlist is
            # built from unwatched episodes only, so an on-deck pick the server considers watched
            # (or one from a season that got filtered out) has no slot to start from.
            if v in items:
                n = v
                break

        # Specials included, deliberately: an on-deck entry is taken as authoritative, whatever
        # season it's in. This branch briefly refused an unstarted season-0 pick, on the theory that
        # the local scan's own skip-past-specials rule (further down, and the one
        # reorder_with_specials() documents for 'default' mode) shouldn't be quietly overruled by
        # the server. Live data killed that: Battlestar's on-deck is the miniseries, which really is
        # its first episode, and refusing it started the show on S01E01 instead. The skip below is
        # for choosing blind - it's a heuristic about where specials usually sit, not a rule the
        # server's own answer should lose to.
        if n is None:
            in_progress = [i for i in revitems if i.get('viewOffset').asInt()]
            n = in_progress[0] if in_progress else None
        if n is not None:
            return n

        # Nothing on deck and nothing in progress, so pick blind. Note `items` is normally the
        # unwatched-only queue (Show.all(unwatched=True), video.py), which means the watched-episode
        # walk just below is only ever reachable for a show with nothing left unwatched at all -
        # i.e. a rewatch, where all() fell back to handing over every episode.

        # Where they left off: revitems is newest-first, so the first watched episode walking it is
        # the latest watched one in queue order, and the next episode after it is where to resume
        # the show. Was `revitems[k-2]` inside the loop, which expressed the same idea by accident
        # of negative indexing and wrapped around to items[0] when every episode was watched -
        # live-caught on a fully-watched Battlestar, which started on a making-of special because
        # that happened to be first in the queue. It also never fired at all when only the very
        # first episode was watched, having run out of loop iterations to notice.
        latest_watched = None
        for (k, i) in enumerate(revitems):
            if i.get('viewCount').asInt() > 0:
                latest_watched = len(items) - 1 - k
                break

        if latest_watched is not None and latest_watched + 1 < len(items):
            return items[latest_watched + 1]

        # Otherwise the first unwatched episode in queue order. Specials are skipped for this -
        # they sit at the front of PMS's own order regardless of when they aired, so starting on one
        # is almost never what's wanted - unless the queue was built by air date, where that
        # reasoning doesn't hold and skipping them would contradict the ordering the user asked for.
        # Falling back to the first candidate covers a rewatch, where nothing is unwatched at all.
        if specials_mode == 'interleave':
            pool = items
        else:
            pool = [i for i in items if i.get('parentIndex').asInt()]
        use = next((i for i in pool if i.get('viewCount').asInt() == 0), None)
        if use is None:
            use = pool[0] if pool else items[0]
        return use



def shutdownHome():
    global HOME
    if HOME:
        HOME.shutdown()
    del HOME
    HOME = None
