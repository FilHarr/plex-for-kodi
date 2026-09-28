# coding=utf-8
"""
lib/windows/library.py's LibraryWindow chain-hosting additions from hashed-orbiting-pizza.md's
Phase 1: swapTo()/_backStack/popBack() and the _setupCurrent() bifurcation that lets this same
LibraryWindow instance host any of the seven real descendant shell types (PrePlayWindow,
EpisodesWindow, ...) in place, instead of opening each as a real nested window. Ported from the
now-deleted lib/windows/descendant_container.py's DescendantContainer prototype and its own tests
(tests/test_descendant_container.py, since deleted) - the back-stack/wrap logic is the same, now
living directly on LibraryWindow instead of a separate MultiWindow subclass.

Constructing a real LibraryWindow here would pull in LibrarySettings, backgroundthread.Tasks(),
sidebar/hub state, and more - impractical for a pure-Python test. Instead, the real bound methods
under test (swapTo/popBack/_setupCurrent/_isRealShell, and the early returns in routeAction())
are called directly against a lightweight FakeHostWindow double that carries only the attributes
those methods actually touch - same style the other lib.windows.* chain tests use.

Two routeAction() regressions get their own narrow tests (OnActionTest) rather than a full
routeAction() walkthrough: routeAction() itself is a large method with many unrelated branches (section-list/server/user-button handling),
and both new early-returns fire (and must return) before any of that runs - so FakeHostWindow
deliberately does NOT define attributes those later branches would need (self.dragging,
self.contentMode, self.movingSection, ...). If a regression ever made either early-return fall
through instead of returning, the test fails with a plain AttributeError, not a silent pass.

Importing lib.windows.library starts lib.player's monitor thread unless abort_requested is set
first - same guard the other lib.windows.* tests use for the same reason.
"""

from __future__ import absolute_import

from kodi_six import xbmcgui
from kodienv import ENV

ENV.abort_requested = True
from lib.windows import collection, library, library_hubs  # noqa: E402

from .base import KodiTestCase  # noqa: E402


class FakeAction(object):
    """xbmcgui.Action compares equal to its id - same stand-in test_dropdown.py uses."""

    def __init__(self, action_id):
        self.action_id = action_id

    def __eq__(self, other):
        return self.action_id == other

    def getId(self):
        return self.action_id


class FakeShell(object):
    xmlFile = 'script-plex-fake.xml'
    BACK_ACTIONS = library.kodigui.BaseWindow.BACK_ACTIONS
    path = '/fake/path'
    theme = 'Main'
    res = '1080i'

    def __init__(self, xmlFile, path, theme, res, **kwargs):
        self.xmlFile = xmlFile
        self.path = path
        self.theme = theme
        self.res = res
        self.kwargs = kwargs
        self.closed = False
        self.onFirstInitCalled = False
        self.setPropertyCalls = []
        self.handleBackResult = False
        self.handleBackCalls = 0

    def onFirstInit(self):
        self.onFirstInitCalled = True

    def handleBack(self):
        self.handleBackCalls += 1
        return self.handleBackResult

    def setProperty(self, key, value):
        self.setPropertyCalls.append((key, value))

    def onAction(self, action):
        pass

    def doClose(self, **kw):
        self.closed = True

    def forceDismiss(self):
        self.nativelyClosed = True


class OtherFakeShell(FakeShell):
    """A second, unrelated real-shell class - swapTo() must accept a genuinely different class."""
    xmlFile = 'script-plex-fake-other.xml'


class FakeThinProxy(object):
    """Stands in for LibraryWindow's own thin view-type children (PostersWindow etc.) - carries
    MULTI_WINDOW_ID, the marker _isRealShell()/_setupCurrent() use to tell it apart from the seven
    real shells. No constructor kwargs (base MultiWindow._setupCurrent() never passes any)."""
    MULTI_WINDOW_ID = 0
    xmlFile = 'script-plex-fake-proxy.xml'
    path = '/fake/path'
    theme = 'Main'
    res = '1080i'

    def __init__(self, xmlFile, path, theme, res):
        self.closed = False

    def onAction(self, action):
        pass

    def doClose(self, **kw):
        self.closed = True


class ReadyView(object):
    """A view that has finished initialising, for running queued navigation."""
    finishedInit = True


class FakeSection(object):
    """Just the library key swapTo()'s chain_root matching compares."""
    def __init__(self, key):
        self.key = key


class FakeHostWindow(object):
    """A hand-built double carrying only the attributes LibraryWindow's real, bound
    swapTo/popBack/_setupCurrent/onAction methods (imported directly off library.LibraryWindow
    below) actually touch - not a real LibraryWindow instance. See module docstring."""

    # _setupCurrent()'s real-shell branch calls self._isRealShell(cls)/self.swapTo() indirectly
    # (via popBack()), and its thin-proxy branch delegates to unmodified base
    # kodigui.MultiWindow._setupCurrent() (redirects onFirstInit/onReInit/onClick/onFocus/onAction
    # to the host) - bind all of the real methods those paths touch here too, so they resolve
    # without needing a full LibraryWindow instance.
    _isRealShell = staticmethod(library.LibraryWindow._isRealShell)
    _setupCurrent = library.LibraryWindow._setupCurrent
    _retireListItems = library.LibraryWindow._retireListItems
    swapTo = library.LibraryWindow.swapTo
    popBack = library.LibraryWindow.popBack
    swapToSection = library.LibraryWindow.swapToSection
    _deferOpenSection = library.LibraryWindow._deferOpenSection
    _popBackIfChained = library.LibraryWindow._popBackIfChained
    _chainRootEntry = library.LibraryWindow._chainRootEntry
    # The real navigation queue (kodigui.MultiWindow), with no delay so requests are due at once.
    postNav = library.kodigui.MultiWindow.postNav
    runPendingNav = library.kodigui.MultiWindow.runPendingNav
    navWaitInterval = library.kodigui.MultiWindow.navWaitInterval
    postUI = library.kodigui.MultiWindow.postUI
    _runPendingUI = library.kodigui.MultiWindow._runPendingUI
    NAV_DEFER_SECONDS = 0.0
    NAV_INIT_HOLD_MAX_SECONDS = library.kodigui.MultiWindow.NAV_INIT_HOLD_MAX_SECONDS

    def _captureRootRestoreState(self):
        # Real LibraryWindow._captureRootRestoreState() reads contentMode/showPanelControl/
        # visibleHubs, none of which this minimal double carries - stubbed to the "nothing
        # identifiable" no-op result every real caller already treats as safe. Restore-position
        # behavior itself is covered directly against the real LibraryWindow method elsewhere.
        return {}

    def _captureHostedShellRestoreState(self):
        # Real LibraryWindow._captureHostedShellRestoreState() does an isinstance() check against
        # collection.BoundedGridWindow that FakeShell/OtherFakeShell (this double's own stand-ins
        # for "some real shell") deliberately aren't - stubbed to the same no-op result the real
        # method already returns for every non-BoundedGridWindow shell.
        return {}

    def __init__(self):
        self._current = None
        self._next = None
        self._nextKwargs = {}
        self._currentKwargs = {}
        self._backStack = []
        self._isHostedShell = False
        self._properties = {}
        self.section = 'the-section'
        self.filter = 'the-filter'
        # Phase 2 (hashed-orbiting-pizza.md): the host's own sectionList - _setupCurrent() must
        # hand this exact object to the hosted shell so its onFirstInit() reuses (newControl())
        # rather than rebuilds it. A plain sentinel is enough here; no real ManagedControlList
        # behavior is exercised by _setupCurrent() itself.
        self.sectionList = object()
        self.openSectionCalls = []
        self.onCloseSignalCalls = []
        self.onActionCalls = []
        self.lock = library.threading.Lock()
        self._listGeneration = 0
        self._navLock = library.threading.Lock()
        self._navPending = []
        self._uiPending = []
        self._allClosed = False
        # A real LibraryWindow.openSection() returns True/False; configurable here per-test.
        self.openSectionReturnValue = False

    def openSection(self, *args, **kwargs):
        self.openSectionCalls.append((args, kwargs))
        return self.openSectionReturnValue

    # The section the sidebar marks active; None until something moves the marker.
    activeMarker = None

    def updateActiveSectionMarker(self, section):
        self.activeMarker = section

    def navNames(self):
        return [r[0] for r in self._navPending]

    def runNav(self):
        """Run every queued request, as the current view's wait loop would once it's ready."""
        view = ReadyView()
        while self._navPending:
            self.runPendingNav(view)

    def doClose(self, **kw):
        pass

    def onCloseSignal(self, *args, **kwargs):
        self.onCloseSignalCalls.append((args, kwargs))

    def dismissSidebarPopupOnBack(self, target=None):
        # Real windowutils.SidebarMixin.dismissSidebarPopupOnBack() - stubbed to "no popup showing"
        # (its own real no-op return), the OnActionTest tests below aren't exercising this.
        return False

    def _sidebarTarget(self):
        return None

    def routeAction(self, action):
        # Never exercised as real dispatch logic here. OnActionTest below calls the real
        # library.LibraryWindow.routeAction directly instead of through this stub.
        self.onActionCalls.append(action)
        return False

    # kodigui.MultiWindowView forwards these two straight to the host - no-op stand-ins.
    def _onFirstInit(self):
        pass

    def onReInit(self):
        pass


# Bind the real, unbound methods under test directly - no LibraryWindow instance is ever
# constructed.
_isRealShell = library.LibraryWindow._isRealShell
_setupCurrent = library.LibraryWindow._setupCurrent
swapTo = library.LibraryWindow.swapTo
popBack = library.LibraryWindow.popBack
swapToSection = library.LibraryWindow.swapToSection
switchTab = library.LibraryWindow.switchTab
switchToCollections = library.LibraryWindow.switchToCollections
routeAction = library.LibraryWindow.routeAction
_captureRootRestoreState = library.LibraryWindow._captureRootRestoreState
_consumeRestoreItemPos = library.LibraryWindow._consumeRestoreItemPos
_captureHostedShellRestoreState = library.LibraryWindow._captureHostedShellRestoreState
gridBack = library.LibraryWindow.gridBack


def onFocus(host, controlID):
    """What kodigui.MultiWindowView.onFocus() does for the Recommended view: the host's
    routeFocus() first, then the view's own handler, HubsMixin.hubFocus()."""
    if not library.LibraryWindow.routeFocus(host, controlID):
        library.LibraryWindow.hubFocus(host, controlID)


class IsRealShellTest(KodiTestCase):
    def test_a_thin_view_type_proxy_is_not_a_real_shell(self):
        self.assertFalse(_isRealShell(FakeThinProxy))

    def test_a_real_descendant_shell_class_is_a_real_shell(self):
        self.assertTrue(_isRealShell(FakeShell))
        self.assertTrue(_isRealShell(OtherFakeShell))

    def test_none_of_the_seven_real_shells_define_multi_window_id(self):
        """Regression guard for the assumption _isRealShell()/_setupCurrent() are built on:
        confirmed via grep against the live classes when this was written - if any of these ever
        grow a MULTI_WINDOW_ID, the bifurcation below silently starts treating it as a thin proxy
        instead of a real shell."""
        from lib.windows import preplay, episodes, subitems, person, tracks, collection, playlist, genres

        realShellClasses = [
            preplay.PrePlayWindow, preplay.PrePlayWindowWL,
            episodes.EpisodesWindow,
            subitems.ShowWindow, subitems.ArtistWindow,
            person.PersonWindow,
            tracks.AlbumWindow,
            collection.CollectionWindow, collection.SubDirWindow,
            playlist.PlaylistWindow,
            genres.GenreBrowserWindow,
        ]
        for cls in realShellClasses:
            self.assertTrue(_isRealShell(cls), "{0} unexpectedly carries MULTI_WINDOW_ID".format(cls))


class SetupCurrentTest(KodiTestCase):
    def test_real_shell_branch_constructs_with_stored_kwargs(self):
        host = FakeHostWindow()
        host._nextKwargs = {'collection': 'the-collection'}

        _setupCurrent(host, FakeShell)

        shell = host._current
        self.assertIsInstance(shell, FakeShell)
        self.assertEqual({'collection': 'the-collection'}, shell.kwargs)
        self.assertEqual({'collection': 'the-collection'}, host._currentKwargs)
        self.assertTrue(host._isHostedShell)

    def test_real_shell_branch_hands_the_hosts_own_sectionList_to_the_shell(self):
        """Phase 2 (hashed-orbiting-pizza.md): the sidebar-highlight-reuse fix depends entirely
        on this one assignment - the shell's own onFirstInit() branch (each of the seven shells,
        not exercised here) only reuses via newControl() if it sees a non-None sectionList, and
        it must be the SAME object the host has, not a copy, so is.active carries over."""
        host = FakeHostWindow()

        _setupCurrent(host, FakeShell)

        self.assertIs(host.sectionList, host._current.sectionList)

    def test_real_shell_branch_marks_the_shell_as_chained_to_this_host(self):
        host = FakeHostWindow()

        _setupCurrent(host, FakeShell)

        self.assertIs(host, host._current._chainHost)

    def test_real_shell_branch_patches_no_callbacks_and_holds_the_host_weakly(self):
        """I8: the shell's own class methods are what Kodi calls - its onAction() routes through
        the host by name (routeActionToHost()) - and nothing bound to the host is stored on it."""
        host = FakeHostWindow()

        _setupCurrent(host, FakeShell)
        shell = host._current

        for name in ('onAction', 'onFirstInit', 'onClick', 'onFocus', 'onReInit'):
            self.assertNotIn(name, vars(shell), name)
        self.assertIs(host, shell._hostRef())
        self.assertFalse(hasattr(host, '_currentOnAction'))

    def test_swapping_to_a_real_shell_makes_in_flight_list_work_stale(self):
        """swapTo() changes neither section nor tab, so the grid a hosted screen replaces relied on
        nothing to tell its in-flight chunks they're stale - live-caught 2026-09-25 as a segfault in
        CGUIListItem::SetProperty when a chunk wrote into the freed grid (AM6B crash log)."""
        host = FakeHostWindow()
        before = host._listGeneration
        _setupCurrent(host, FakeShell)
        self.assertEqual(before + 1, host._listGeneration)

    def test_swapping_between_thin_views_keeps_the_generation(self):
        """A view-type swap reuses the grid's list; its chunks must still land."""
        host = FakeHostWindow()
        before = host._listGeneration
        _setupCurrent(host, FakeThinProxy)
        self.assertEqual(before, host._listGeneration)

    def test_swapping_out_a_real_shell_closes_its_native_window(self):
        """doClose() only flags a hosted shell; closing it natively was left to the forced gc
        disposing it, which a task still running for it prevents - Kodi then re-activated it over
        the next view (live-caught 2026-09-24)."""
        host = FakeHostWindow()
        _setupCurrent(host, FakeShell)
        outgoing = host._current
        _setupCurrent(host, OtherFakeShell)
        self.assertTrue(getattr(outgoing, 'nativelyClosed', False))
        self.assertFalse(getattr(host._current, 'nativelyClosed', False))

    def test_real_shell_branch_leaves_onClick_and_onFocus_and_onReInit_untouched(self):
        host = FakeHostWindow()

        _setupCurrent(host, FakeShell)
        shell = host._current

        self.assertNotIn('onClick', vars(shell))
        self.assertNotIn('onFocus', vars(shell))
        self.assertNotIn('onReInit', vars(shell))

    def test_real_shell_branch_registers_the_hosts_close_signal_only(self):
        """The one host-generic line of base MultiWindow._onFirstInit() a real shell needs: the
        host's close.windows handler. Not the host's own onFirstInit()/_onFirstInit() - that's
        LibraryWindow's template-specific setup, which would run broken against a real shell's
        native window (FakeHostWindow defines no onFirstInit(), so reaching it would raise)."""
        from plexnet import plexapp

        host = FakeHostWindow()
        try:
            _setupCurrent(host, FakeShell)
            self.assertTrue(plexapp.util.APP.has_signal('close.windows', host.onCloseSignal))
            host._current.onFirstInit()
        finally:
            plexapp.util.APP.off('close.windows', host.onCloseSignal)

        self.assertTrue(host._current.onFirstInitCalled)

    def test_real_shell_branch_does_not_replay_the_hosts_own_properties_onto_the_shell(self):
        """Live-confirmed bug this guards against: self._properties accumulates whatever
        LibraryWindow's own 'recommended'-mode hero display last set (clear.logo/summary/etc.
        for the focused hub item) and nothing overwrites those specific keys again once the user
        is just browsing an ordinary grid, so they sit frozen for the rest of the session. A real
        shell like PrePlayWindow happens to use the same property names for its own, unrelated
        metadata panel - replaying the host's entire cache onto it briefly showed that frozen,
        unrelated content (Home's Continue Watching's first item, in practice) until the shell's
        own setInfo() overwrote it a moment later. A real shell has its own independent metadata
        logic; it must not inherit the host's display-state cache the way a thin proxy does."""
        from plexnet import plexapp

        host = FakeHostWindow()
        host._properties = {'clear.logo': 'stale-continue-watching-logo.png', 'summary': 'stale summary'}

        try:
            _setupCurrent(host, FakeShell)
            shell = host._current
            shell.onFirstInit()
        finally:
            plexapp.util.APP.off('close.windows', host.onCloseSignal)

        self.assertEqual([], shell.setPropertyCalls)

    def test_thin_proxy_branch_marks_not_hosted_and_passes_no_kwargs(self):
        host = FakeHostWindow()
        host._nextKwargs = {'collection': 'the-collection'}  # must be ignored for a thin proxy

        _setupCurrent(host, FakeThinProxy)

        self.assertFalse(host._isHostedShell)
        self.assertIsInstance(host._current, FakeThinProxy)


class SwapToAndBackStackTest(KodiTestCase):
    def test_genesis_swap_out_of_the_grid_pushes_a_root_restore_entry(self):
        """The outgoing _current here is a thin proxy (host._isHostedShell is False, the state
        right after LibraryWindow's own __init__/reset()) - swapTo() must push root-restore state
        (section/filter), not try to reconstruct the proxy as if it were a real shell class."""
        host = FakeHostWindow()
        host._current = FakeThinProxy(FakeThinProxy.xmlFile, FakeThinProxy.path, FakeThinProxy.theme, FakeThinProxy.res)
        host._isHostedShell = False

        swapTo(host, FakeShell, video='the-movie')

        self.assertEqual([(None, {'section': 'the-section', 'filter_': 'the-filter'})], host._backStack)
        self.assertEqual(FakeShell, host._next)
        self.assertEqual({'video': 'the-movie'}, host._nextKwargs)
        self.assertTrue(host._current.closed)

    def test_swap_between_two_real_shells_pushes_the_outgoing_shells_class_and_kwargs(self):
        host = FakeHostWindow()
        _setupCurrent(host, FakeShell)  # host._current is now a real, hosted FakeShell
        firstShell = host._current

        swapTo(host, OtherFakeShell, video='the-movie')

        self.assertEqual([(FakeShell, {})], host._backStack)
        self.assertEqual(OtherFakeShell, host._next)
        self.assertEqual({'video': 'the-movie'}, host._nextKwargs)
        self.assertTrue(firstShell.closed)
        # doClose() is a flag-flip only - _open()'s loop reconstructs on its own frame, so
        # host._current itself must not have been swapped out synchronously.
        self.assertIs(firstShell, host._current)

    def test_swap_with_push_false_does_not_push(self):
        host = FakeHostWindow()
        _setupCurrent(host, FakeShell)

        swapTo(host, OtherFakeShell, push=False, video='the-movie')

        self.assertEqual([], host._backStack)

    # chain_root: post-play's opens (videoplayer.play()) - Back from what opens goes to the item's
    # own section, never back through the chain that started playback.

    def test_a_chain_root_in_another_section_replaces_the_chain_with_that_section_fresh(self):
        movies, shows = FakeSection('1'), FakeSection('2')
        host = FakeHostWindow()
        host._backStack = [(None, {'section': movies, 'filter_': None, '_restoreHubId': 'movie.ondeck'}),
                           (FakeShell, {'video': 'earlier'})]
        host._hubReselectPositions = {'hub': ('1', 3)}
        _setupCurrent(host, FakeShell)
        currentShell = host._current

        swapTo(host, OtherFakeShell, chain_root=shows, video='the-show')

        self.assertEqual([(None, {'section': shows, 'filter_': None})], host._backStack)
        self.assertEqual({}, host._hubReselectPositions)
        self.assertEqual(OtherFakeShell, host._next)
        self.assertEqual({'video': 'the-show'}, host._nextKwargs)
        self.assertTrue(currentShell.closed)
        self.assertIs(shows, host.activeMarker, 'the sidebar marks the section Back now goes to')

    def test_a_chain_root_in_the_starting_section_collapses_to_that_section_as_it_was_left(self):
        """Same section, unfiltered: keep the chain's own root entry (its row/grid position) and
        the per-row positions, rather than opening the section fresh. Matched by key - post-play
        finds its section object separately from the one the chain started with."""
        root = (None, {'section': FakeSection('2'), 'filter_': None, '_restoreHubId': 'tv.ondeck'})
        host = FakeHostWindow()
        host._backStack = [root, (FakeShell, {'video': 'earlier'})]
        host._hubReselectPositions = {'tv.ondeck': ('1', 3)}
        _setupCurrent(host, FakeShell)

        swapTo(host, OtherFakeShell, chain_root=FakeSection('2'), video='the-episode')

        self.assertEqual([root], host._backStack)
        self.assertEqual({'tv.ondeck': ('1', 3)}, host._hubReselectPositions)
        self.assertIsNone(host.activeMarker, 'already the marked section')

    def test_a_chain_root_from_the_hosts_own_section_view_roots_at_it_as_it_is(self):
        """No chain yet (e.g. Play All from the section's grid): the root is what a genesis swap
        would push now - the host's current section and its restore state."""
        shows = FakeSection('2')
        host = FakeHostWindow()
        host.section, host.filter = shows, None
        host._current = FakeThinProxy(FakeThinProxy.xmlFile, FakeThinProxy.path, FakeThinProxy.theme, FakeThinProxy.res)
        host._isHostedShell = False
        host._hubReselectPositions = {'tv.ondeck': ('1', 3)}

        swapTo(host, OtherFakeShell, chain_root=FakeSection('2'), video='the-episode')

        self.assertEqual([(None, {'section': shows, 'filter_': None})], host._backStack)
        self.assertEqual({'tv.ondeck': ('1', 3)}, host._hubReselectPositions)

    def test_a_chain_root_in_the_starting_section_but_filtered_opens_it_fresh(self):
        shows = FakeSection('2')
        host = FakeHostWindow()
        host._backStack = [(None, {'section': FakeSection('2'), 'filter_': 'genre=drama'})]
        host._hubReselectPositions = {'hub': ('1', 3)}
        _setupCurrent(host, FakeShell)

        swapTo(host, OtherFakeShell, chain_root=shows, video='the-show')

        self.assertEqual([(None, {'section': shows, 'filter_': None})], host._backStack)
        self.assertEqual({}, host._hubReselectPositions)

    def test_pop_back_on_a_shell_reconstruction_entry_swaps_without_pushing_again(self):
        host = FakeHostWindow()
        host._backStack = [(FakeShell, {'collection': 'the-collection'})]
        _setupCurrent(host, OtherFakeShell)
        currentShell = host._current

        popBack(host)

        self.assertEqual(FakeShell, host._next)
        self.assertEqual({'collection': 'the-collection'}, host._nextKwargs)
        self.assertEqual([], host._backStack)
        self.assertTrue(currentShell.closed)

    def test_pop_back_on_a_root_restore_entry_calls_openSection_not_swapTo(self):
        host = FakeHostWindow()
        host._backStack = [(None, {'section': 'the-section', 'filter_': 'the-filter'})]
        _setupCurrent(host, FakeShell)

        popBack(host)

        # fresh=False: Back restores the hub rows' remembered positions instead of clearing them.
        self.assertEqual([((), {'force': True, 'fresh': False, 'section': 'the-section',
                                'filter_': 'the-filter'})],
                          host.openSectionCalls)
        # openSection(), not swapTo() - _next/_nextKwargs must be untouched by this pop.
        self.assertIsNone(host._next)

    def test_a_three_level_chain_unwinds_in_order_ending_on_root_restore(self):
        host = FakeHostWindow()
        host._current = FakeThinProxy(FakeThinProxy.xmlFile, FakeThinProxy.path, FakeThinProxy.theme, FakeThinProxy.res)
        host._isHostedShell = False

        # grid -> shell A -> shell B
        swapTo(host, FakeShell, video='a')
        _setupCurrent(host, host._next)
        swapTo(host, OtherFakeShell, video='b')
        _setupCurrent(host, host._next)

        self.assertEqual(2, len(host._backStack))

        # pop: shell B -> shell A
        popBack(host)
        self.assertEqual(FakeShell, host._next)
        self.assertEqual({'video': 'a'}, host._nextKwargs)
        _setupCurrent(host, host._next)

        # pop: shell A -> root grid. The real openSection() clears _backStack when it swaps; the
        # fake only reports that it did.
        host.openSectionReturnValue = True
        popBack(host)
        self.assertEqual([], host._backStack)
        self.assertEqual(1, len(host.openSectionCalls))

    def test_pop_back_on_a_root_restore_entry_strips_restore_kwargs_into_pending_state(self):
        """_restoreItemPos/_restoreHubId (_captureRootRestoreState()) aren't real openSection()
        kwargs - popBack() must peel them off into self._pendingRestore*/hand openSection() only
        section/filter_, so a stale/unexpected kwarg doesn't reach it directly."""
        host = FakeHostWindow()
        host.openSectionReturnValue = True
        host._backStack = [(None, {'section': 'the-section', 'filter_': 'the-filter',
                                    '_restoreItemPos': 5, '_restoreHubId': 'hub-x'})]
        _setupCurrent(host, FakeShell)

        popBack(host)

        self.assertEqual(5, host._pendingRestoreItemPos)
        self.assertEqual('hub-x', host._pendingRestoreHubId)
        # fresh=False: Back restores the hub rows' remembered positions instead of clearing them.
        self.assertEqual([((), {'force': True, 'fresh': False, 'section': 'the-section',
                                'filter_': 'the-filter'})],
                          host.openSectionCalls)

    def test_a_declined_pop_back_keeps_its_entry_for_the_next_back(self):
        """openSection() declines while the current view isn't Kodi's current window yet (Back
        pressed as a screen was still opening). Live-caught 2026-09-24: the popped entry was lost,
        leaving an empty chain, and the next Back offered to exit the addon."""
        entry = (None, {'section': 'the-section', 'filter_': 'the-filter',
                        '_restoreItemPos': 5, '_restoreHubId': 'hub-x'})
        host = FakeHostWindow()
        host.openSectionReturnValue = False
        host._backStack = [entry]
        _setupCurrent(host, FakeShell)

        popBack(host)

        self.assertEqual([entry], host._backStack)
        self.assertIsNone(host._pendingRestoreItemPos)
        self.assertIsNone(host._pendingRestoreHubId)

    def test_pop_back_on_a_root_restore_entry_without_restore_kwargs_clears_pending_state(self):
        host = FakeHostWindow()
        host._backStack = [(None, {'section': 'the-section', 'filter_': 'the-filter'})]
        _setupCurrent(host, FakeShell)

        popBack(host)

        self.assertIsNone(host._pendingRestoreItemPos)
        self.assertIsNone(host._pendingRestoreHubId)


class CaptureRootRestoreStateTest(KodiTestCase):
    """LibraryWindow._captureRootRestoreState() - what swapTo()/swapToSection() merge into a
    fresh (None, {...}) root-restore _backStack entry so popBack() can land back on whichever
    grid item or hub row was actually focused, instead of always resetting to item 0 / hub 0."""

    class _Bag(object):
        """Plain attribute holder - _captureRootRestoreState() only ever reads attributes off
        self, no methods, so this is enough of a double without a full LibraryWindow."""

    class _FakePanelItem(object):
        def __init__(self, pos):
            self._pos = pos

        def pos(self):
            return self._pos

    class _FakeShowPanelControl(object):
        def __init__(self, selected=None):
            self.selected = selected

        def getSelectedItem(self):
            return self.selected

    class _FakeHub(object):
        def __init__(self, identifier):
            self.identifier = identifier

        def getCleanHubIdentifier(self, is_home=False):
            return self.identifier

    class _FakeSection(object):
        def __init__(self, key=None):
            self.key = key

    def test_library_mode_captures_the_selected_grid_item_position(self):
        host = self._Bag()
        host.contentMode = 'library'
        host.showPanelControl = self._FakeShowPanelControl(self._FakePanelItem(17))

        self.assertEqual({'_restoreItemPos': 17}, _captureRootRestoreState(host))

    def test_library_mode_with_no_selected_item_is_a_no_op(self):
        host = self._Bag()
        host.contentMode = 'library'
        host.showPanelControl = self._FakeShowPanelControl(None)

        self.assertEqual({}, _captureRootRestoreState(host))

    def test_library_mode_with_no_panel_control_yet_is_a_no_op(self):
        host = self._Bag()
        host.contentMode = 'library'
        host.showPanelControl = None

        self.assertEqual({}, _captureRootRestoreState(host))

    def test_recommended_mode_captures_the_focused_hubs_identifier(self):
        host = self._Bag()
        host.contentMode = 'recommended'
        host.visibleHubs = [self._FakeHub('hub-a'), self._FakeHub('hub-b')]
        host.focusedHubIndex = 1
        host.section = self._FakeSection(key='1')

        self.assertEqual({'_restoreHubId': 'hub-b'}, _captureRootRestoreState(host))

    def test_recommended_mode_with_no_visible_hubs_is_a_no_op(self):
        host = self._Bag()
        host.contentMode = 'recommended'
        host.visibleHubs = []
        host.focusedHubIndex = 0
        host.section = self._FakeSection(key='1')

        self.assertEqual({}, _captureRootRestoreState(host))


class ConsumeRestoreItemPosTest(KodiTestCase):
    """LibraryWindow._consumeRestoreItemPos() - the fillShows()/fillPlaylists()/fillPhotos() end
    of the same mechanism: one-shot read-and-clear of self._pendingRestoreItemPos, clamped to the
    freshly loaded item count."""

    class _Bag(object):
        pass

    def test_returns_the_pending_position_when_in_range(self):
        host = self._Bag()
        host._pendingRestoreItemPos = 3

        self.assertEqual(3, _consumeRestoreItemPos(host, 10))
        self.assertIsNone(host._pendingRestoreItemPos)

    def test_falls_back_to_zero_when_out_of_range(self):
        host = self._Bag()
        host._pendingRestoreItemPos = 99

        self.assertEqual(0, _consumeRestoreItemPos(host, 10))
        self.assertIsNone(host._pendingRestoreItemPos)

    def test_falls_back_to_zero_when_nothing_pending(self):
        host = self._Bag()
        host._pendingRestoreItemPos = None

        self.assertEqual(0, _consumeRestoreItemPos(host, 10))


class CaptureHostedShellRestoreStateTest(KodiTestCase):
    """LibraryWindow._captureHostedShellRestoreState() - the counterpart to
    _captureRootRestoreState() for a hosted real shell with its own grid concept
    (collection.py's CollectionWindow/SubDirWindow specifically - live-reported (2026-09-03) as
    never restoring focus at all before this existed, then live-reported again the same day: a
    position only reached by scrolling the paginator past its initial page still fell back to item
    0, because this method used to no-op entirely once offset != 0). Captures an *absolute* list
    position now, regardless of paginator offset - see the real method's own docstring for the
    offset-shift math, and collection.py's BoundedGridPaginator.jumpToPosition()/
    _selectInitialItem() for the consuming side."""

    class _Bag(object):
        pass

    class _FakePanelItem(object):
        def __init__(self, pos, is_boundary=False):
            self._pos = pos
            self._is_boundary = is_boundary

        def pos(self):
            return self._pos

        def getProperty(self, key):
            if key == 'is.boundary':
                return '1' if self._is_boundary else ''
            return ''

    class _FakeGridControl(object):
        def __init__(self, selected=None):
            self.selected = selected

        def getSelectedItem(self):
            return self.selected

    @staticmethod
    def _fakeBoundedGridWindow(offset, selected=None):
        # object.__new__(), not CollectionWindow(...) - a real construction needs a genuine
        # xbmcgui.WindowXML underneath (xmlFile/path/theme/res, native control binding), well
        # beyond what this unit deliberately touches. This is enough for the isinstance() check
        # _captureHostedShellRestoreState() does, with only the two attributes it actually reads
        # set directly.
        inst = object.__new__(collection.CollectionWindow)
        inst.paginator = CaptureHostedShellRestoreStateTest._Bag()
        inst.paginator.offset = offset
        inst.gridControl = CaptureHostedShellRestoreStateTest._FakeGridControl(selected)
        return inst

    def test_captures_the_selected_items_position_on_the_initial_page(self):
        host = self._Bag()
        host._current = self._fakeBoundedGridWindow(offset=0, selected=self._FakePanelItem(9))

        self.assertEqual({'_restoreItemPos': 9}, _captureHostedShellRestoreState(host))

    def test_captures_an_absolute_position_once_scrolled_past_the_initial_page(self):
        """offset=60, control-relative index 5 - index 0 on this page is the left-boundary
        sentinel (any page that doesn't start at the real beginning of the list has one), so the
        5th control slot is the page's 4th real item: absolute position 60 + (5 - 1) = 64, not the
        raw control-relative 5."""
        host = self._Bag()
        host._current = self._fakeBoundedGridWindow(offset=60, selected=self._FakePanelItem(5))

        self.assertEqual({'_restoreItemPos': 64}, _captureHostedShellRestoreState(host))

    def test_shifts_for_the_left_boundary_sentinel_once_past_the_initial_page(self):
        """offset=60, control-relative index 1 (index 0 is the left-boundary sentinel on any page
        that doesn't start at the real beginning of the list) - real position is 60 + (1-1) = 60,
        the page's own first real item."""
        host = self._Bag()
        host._current = self._fakeBoundedGridWindow(offset=60, selected=self._FakePanelItem(1))

        self.assertEqual({'_restoreItemPos': 60}, _captureHostedShellRestoreState(host))

    def test_no_op_when_the_selected_item_is_the_boundary_sentinel_itself(self):
        host = self._Bag()
        host._current = self._fakeBoundedGridWindow(
            offset=60, selected=self._FakePanelItem(0, is_boundary=True))

        self.assertEqual({}, _captureHostedShellRestoreState(host))

    def test_no_op_with_no_selected_item(self):
        host = self._Bag()
        host._current = self._fakeBoundedGridWindow(offset=0, selected=None)

        self.assertEqual({}, _captureHostedShellRestoreState(host))

    def test_no_op_for_a_shell_thats_not_a_bounded_grid_window(self):
        """PrePlayWindow/EpisodesWindow/ShowWindow/... - every other real shell - deliberately
        out of scope (see the real method's own docstring)."""
        host = self._Bag()
        host._current = FakeShell(FakeShell.xmlFile, FakeShell.path, FakeShell.theme, FakeShell.res)

        self.assertEqual({}, _captureHostedShellRestoreState(host))


class SwapToSectionTest(KodiTestCase):
    """hashed-orbiting-pizza.md Phase 4 item 8: genre/director/actor-tag "go to section" clicks
    reuse this LibraryWindow's own section-rendering in place (openSection()) rather than
    swapping to a different shell class - but openSection() unconditionally clears _backStack
    before returning (correct for its own ordinary sidebar-click callers, wrong here). Both fakes
    below mimic that real clearing side effect, since a fake that silently kept _backStack intact
    would pass even if swapToSection() forgot to re-append its own entry afterward."""

    def _openSectionClearingBackStack(self, host):
        def _fake(section, filter_=None, force=False, fresh=True):
            host.openSectionCalls.append((section, filter_, force, fresh))
            host._backStack = []
            return True
        return _fake

    def test_a_declined_open_section_adds_no_entry(self):
        """Appending anyway would make Back 'return' to the screen still showing."""
        host = FakeHostWindow()
        _setupCurrent(host, FakeShell)
        host._backStack = [(None, {'section': 'root', 'filter_': None})]
        host.openSectionReturnValue = False

        swapToSection(host, 'new-section')

        self.assertEqual([(None, {'section': 'root', 'filter_': None})], host._backStack)

    def test_from_a_hosted_shell_pushes_the_shells_own_reconstruction_entry(self):
        host = FakeHostWindow()
        _setupCurrent(host, FakeShell)  # host._current is now a real, hosted FakeShell
        host._currentKwargs = {'video': 'the-movie'}
        host.openSection = self._openSectionClearingBackStack(host)

        swapToSection(host, 'new-section', filter_='new-filter')

        # fresh=False: the chain is kept, so the hub rows' remembered positions are too.
        self.assertEqual([('new-section', 'new-filter', True, False)], host.openSectionCalls)
        self.assertEqual([(FakeShell, {'video': 'the-movie'})], host._backStack)

    def test_from_the_grid_pushes_a_root_restore_entry(self):
        host = FakeHostWindow()
        host._current = FakeThinProxy(FakeThinProxy.xmlFile, FakeThinProxy.path, FakeThinProxy.theme, FakeThinProxy.res)
        host._isHostedShell = False
        host.section = 'old-section'
        host.filter = 'old-filter'
        host.openSection = self._openSectionClearingBackStack(host)

        swapToSection(host, 'new-section', filter_='new-filter')

        self.assertEqual([(None, {'section': 'old-section', 'filter_': 'old-filter'})], host._backStack)

    def test_entry_is_captured_before_open_section_mutates_section_and_filter(self):
        """Regression guard: swapToSection() must read self.section/self.filter for the pushed
        entry BEFORE calling openSection() (which reassigns both to the new section/filter) - not
        after, which would push the new section as if it were the old one, making Back a no-op."""
        host = FakeHostWindow()
        host._current = FakeThinProxy(FakeThinProxy.xmlFile, FakeThinProxy.path, FakeThinProxy.theme, FakeThinProxy.res)
        host._isHostedShell = False
        host.section = 'old-section'
        host.filter = 'old-filter'

        def _fakeMutatingOpenSection(section, filter_=None, force=False, fresh=True):
            host.openSectionCalls.append((section, filter_, force, fresh))
            host.section = section
            host.filter = filter_
            host._backStack = []
            return True
        host.openSection = _fakeMutatingOpenSection

        swapToSection(host, 'new-section', filter_='new-filter')

        self.assertEqual([(None, {'section': 'old-section', 'filter_': 'old-filter'})], host._backStack)

    def test_preserves_whatever_was_already_on_the_backstack(self):
        """Regression guard: a real bug found while building Categories - a second
        swapToSection() deeper in the same chain (e.g. enter Categories, then click a genre) must
        not lose the entry that got it into the hosted shell in the first place. openSection()
        clears _backStack unconditionally; swapToSection() must restore whatever preceded its own
        entry, not just append to a blank stack - otherwise a second Back only ever unwinds one
        hop instead of the whole chain."""
        host = FakeHostWindow()
        host._backStack = [(None, {'section': 'root-section', 'filter_': None})]
        _setupCurrent(host, FakeShell)  # host._current is now a real, hosted FakeShell
        host._currentKwargs = {'video': 'the-movie'}
        host.openSection = self._openSectionClearingBackStack(host)

        swapToSection(host, 'new-section', filter_='new-filter')

        self.assertEqual(
            [(None, {'section': 'root-section', 'filter_': None}), (FakeShell, {'video': 'the-movie'})],
            host._backStack)


class FakeTasks(object):
    def __init__(self):
        self.killed = False

    def kill(self):
        self.killed = True


class FakeLibrarySettings(object):
    itemType = None

    def __init__(self):
        self.contentModeCalls = []
        self.itemTypeCalls = []

    def setContentMode(self, mode):
        self.contentModeCalls.append(mode)

    def setItemType(self, item_type):
        self.itemTypeCalls.append(item_type)
        self.itemType = item_type


class FakeSwitchTabHost(object):
    """A hand-built double carrying only the attributes the real, bound switchTab() (imported
    directly off library.LibraryWindow above) actually touches - not a real LibraryWindow
    instance. See module docstring."""

    _retireListItems = library.LibraryWindow._retireListItems
    itemType = library.LibraryWindow.itemType

    def __init__(self):
        self.is_current_window = True
        self._isHostedShell = False
        self.contentMode = 'library'
        self.tasks = FakeTasks()
        self.hubSlideSettled = False
        self._listGeneration = 0
        self.lock = library.threading.RLock()
        self._backStack = []
        self.librarySettings = FakeLibrarySettings()
        self.resetCalled = False
        self.refill = False
        self._current = FakeShell(FakeShell.xmlFile, FakeShell.path, FakeShell.theme, FakeShell.res)

    def _settleHubSlide(self):
        self.hubSlideSettled = True

    def reset(self):
        self.resetCalled = True


class SwitchTabTest(KodiTestCase):
    """hashed-orbiting-pizza.md Categories follow-up: two correctness fixes to switchTab(),
    needed because a real shell (genres.py's GenreBrowserWindow, hosted via browseGenres()) can be
    showing while self.contentMode still holds whatever it was before Categories was entered -
    switchTab() is never itself called with mode='categories' (see its own docstring), only
    'library'/'recommended', to leave Categories."""

    def test_same_mode_is_a_genuine_noop_when_not_hosting_a_real_shell(self):
        """Regression guard for the ordinary, pre-Categories case: clicking the tab you're already
        on must stay a no-op."""
        host = FakeSwitchTabHost()
        host.contentMode = 'library'

        result = switchTab(host, 'library')

        self.assertFalse(result)
        self.assertFalse(host.resetCalled)

    def test_same_mode_proceeds_when_a_real_shell_is_fronting_it(self):
        """The bug this guards against: leaving Categories via the Library tab when contentMode
        was already 'library' before Categories was entered - the naive `mode == self.contentMode`
        check would wrongly no-op and leave Categories showing."""
        host = FakeSwitchTabHost()
        host.contentMode = 'library'
        host._isHostedShell = True

        result = switchTab(host, 'library')

        self.assertTrue(result)
        self.assertTrue(host.resetCalled)
        self.assertTrue(host._current.closed)

    def test_clears_the_backstack_when_a_switch_actually_proceeds(self):
        """An explicit tab click abandons any chain in progress - same reasoning openSection()
        already applies to sidebar clicks. Without this, leaving Categories via a direct tab click
        (not Back) would leave its root-restore entry stale on the stack."""
        host = FakeSwitchTabHost()
        host._isHostedShell = True
        host._backStack = [(None, {'section': 'the-section', 'filter_': None})]

        switchTab(host, 'recommended')

        self.assertEqual([], host._backStack)

    def test_declines_when_not_the_current_window(self):
        host = FakeSwitchTabHost()
        del host.is_current_window

        result = switchTab(host, 'recommended')

        self.assertFalse(result)
        self.assertFalse(host.resetCalled)

    def test_item_type_none_never_persists_anything(self):
        """Regression guard - every pre-Collections caller passes no item_type at all; that path
        must stay exactly as cheap/inert as before."""
        host = FakeSwitchTabHost()

        switchTab(host, 'recommended')

        self.assertEqual([], host.librarySettings.itemTypeCalls)

    def test_item_type_persists_when_provided(self):
        host = FakeSwitchTabHost()
        host.librarySettings.itemType = 'movie'

        switchTab(host, 'library', item_type='collection')

        self.assertEqual(['collection'], host.librarySettings.itemTypeCalls)

    def test_item_type_change_bypasses_the_no_op_guard_even_when_mode_matches(self):
        """The Collections-follow-up bug this guards against: Library-tab-from-Collections never
        changes contentMode (it was 'library' throughout), so the ordinary mode-comparison no-op
        guard alone would wrongly swallow the click and leave ITEM_TYPE stuck on 'collection'."""
        host = FakeSwitchTabHost()
        host.librarySettings.itemType = 'collection'
        host.contentMode = 'library'

        result = switchTab(host, 'library', item_type='movie')

        self.assertTrue(result)
        self.assertTrue(host.resetCalled)
        self.assertEqual(['movie'], host.librarySettings.itemTypeCalls)

    def test_item_type_equal_to_current_does_not_bypass_the_no_op_guard(self):
        """item_type matching the already-active ITEM_TYPE isn't a real change - must not
        artificially defeat the no-op guard."""
        host = FakeSwitchTabHost()
        host.librarySettings.itemType = 'movie'
        host.contentMode = 'library'

        result = switchTab(host, 'library', item_type='movie')

        self.assertFalse(result)
        self.assertFalse(host.resetCalled)


class SwitchToCollectionsTest(KodiTestCase):
    """switchToCollections() (buildTabList()'s Collections tab): an in-place ITEM_TYPE refill when
    already on the ordinary library grid, otherwise a real contentMode swap via switchTab() (e.g.
    starting from Recommended, or from a hosted shell like Categories fronting 'library') - see the
    method's own docstring for why persisting item_type through switchTab() is enough, no separate
    post-reconstruction hook needed."""

    class FakeCollectionsHost(object):
        def __init__(self, content_mode, is_hosted_shell=False):
            self.contentMode = content_mode
            self._isHostedShell = is_hosted_shell
            self.appliedItemTypeChoices = []
            self.switchTabCalls = []

        def _applyItemTypeChoice(self, choice, keep_focus=True):
            # keep_focus is recorded, not just accepted: switchToCollections() passes False
            # deliberately (see its own docstring - a tab click should land focus on the grid, the
            # opposite of what _applyItemTypeChoice()'s dropdown-result caller wants), and this
            # fake silently not taking the kwarg at all is what let that call go untested.
            self.appliedItemTypeChoices.append((choice, keep_focus))

        def switchTab(self, mode, item_type=None):
            self.switchTabCalls.append((mode, item_type))

    def test_in_place_refill_when_already_on_the_ordinary_library_grid(self):
        host = self.FakeCollectionsHost('library')

        switchToCollections(host)

        self.assertEqual([('collection', False)], host.appliedItemTypeChoices)
        self.assertEqual([], host.switchTabCalls)

    def test_real_switch_from_recommended(self):
        host = self.FakeCollectionsHost('recommended')

        switchToCollections(host)

        self.assertEqual([], host.appliedItemTypeChoices)
        self.assertEqual([('library', 'collection')], host.switchTabCalls)

    def test_real_switch_when_a_hosted_shell_is_fronting_library(self):
        """Categories can front contentMode == 'library' without switchTab() itself having been
        the thing that got there - _isHostedShell, not contentMode alone, is what actually means
        "the ordinary grid is on screen right now."""
        host = self.FakeCollectionsHost('library', is_hosted_shell=True)

        switchToCollections(host)

        self.assertEqual([], host.appliedItemTypeChoices)
        self.assertEqual([('library', 'collection')], host.switchTabCalls)


class LibrarySettingsPersistenceTest(KodiTestCase):
    """LibrarySettings writes, which all share ONE blob per server (library.settings.<uuid>,
    every section in it).

    Live-confirmed bug these pin: each instance held a whole-blob snapshot taken at construction
    and rewrote all of it on any change, so a write from an instance built before someone else's
    write silently reverted it. Symptom was the music section reopening on Tracks after the user
    had switched to Albums - ITEM_TYPE persisted, then reverted by an unrelated later write - and
    it was only visible at all once the view type started following ITEM_TYPE (forcedViewWindow()).
    """

    class FakeSection(object):
        def __init__(self, key, type_, uuid='the-server'):
            self.key = key
            self.TYPE = type_
            self._uuid = uuid

        def getServer(self):
            return self

        @property
        def uuid(self):
            return self._uuid

    def music(self):
        return library.LibrarySettings(self.FakeSection('10', 'artist'))

    def test_a_stale_instance_does_not_revert_another_instances_item_type(self):
        stale = self.music()          # snapshot taken before the change below
        self.music().setItemType('track')

        current = self.music()
        self.assertEqual('track', current.getItemType())

        current.setItemType('album')
        # The stale instance writes something entirely unrelated afterwards - as a cancelled
        # background task or an outgoing window's sort/filter save does.
        stale.setSetting('sort', 'titleSort')

        self.assertEqual('album', self.music().getItemType())

    def test_a_sectionless_instance_never_wipes_the_blob(self):
        """HomeSection's key is None, so _loadSettings() leaves it an empty snapshot - writing
        that out replaced every real section's settings with a single "null" entry."""
        self.music().setItemType('album')

        home = library.LibrarySettings(self.FakeSection(None, 'mixed'))
        home.setItemType('mixed')
        home.setContentMode('recommended')

        self.assertEqual('album', self.music().getItemType())

    def test_writes_from_different_sections_do_not_evict_each_other(self):
        self.music().setItemType('album')
        movies = library.LibrarySettings(self.FakeSection('22', 'movie'))
        movies.setItemType('movie')
        movies.setContentMode('library')

        self.assertEqual('album', self.music().getItemType())
        self.assertEqual('movie', movies.getItemType())


class DeferOpenSectionTest(KodiTestCase):
    """_deferOpenSection() posts openSection() to the navigation queue (S1). It used to start a
    single-flight threading.Timer, after kodi.log showed 7 concurrent openSection() calls on 7
    threads; a newer request now replaces a pending one, and all run on the main thread."""

    def test_posts_open_section_instead_of_calling_it(self):
        host = FakeHostWindow()
        host._deferOpenSection('the-section', force=True)

        self.assertEqual([], host.openSectionCalls)
        self.assertEqual(['openSection'], host.navNames())
        host.runNav()
        self.assertEqual([(('the-section',), {'force': True})], host.openSectionCalls)

    def test_a_second_call_replaces_the_first(self):
        host = FakeHostWindow()
        host._deferOpenSection('the-section')
        host._deferOpenSection('a-different-section')

        host.runNav()
        self.assertEqual([(('a-different-section',), {'force': False})], host.openSectionCalls)


class OnActionTest(KodiTestCase):
    """Deliberately narrow - see module docstring. FakeHostWindow defines no self.dragging/
    self.contentMode/self.movingSection etc., so if either early-return below fell through instead
    of returning, the real routeAction() body would raise AttributeError trying to reach them."""

    def test_navback_posts_popBack_instead_of_calling_it_inline(self):
        """hashed-orbiting-pizza.md Phase 3's still-open OnAction()-reentrancy risk: popBack()
        must not run synchronously from inside routeAction() - the same shape the documented Kodi
        core OnAction() reentrancy bug (SKIN_RELOAD_DEFER_SECONDS's own comment) is suspected
        unsafe for. Posted to the navigation queue like every other swap (MultiWindow.postNav()),
        then run through the real queue here."""
        host = FakeHostWindow()
        host._shuttingDown = False
        host._goRootAwaitFocus = None
        host._backStack = [(FakeShell, {})]
        popCalls = []
        host.popBack = lambda: popCalls.append(True)

        self.assertTrue(routeAction(host, FakeAction(xbmcgui.ACTION_NAV_BACK)))

        self.assertEqual([], popCalls, "popBack() must not run inline, only from the queue")
        self.assertEqual(['popBack'], host.navNames())
        host.runNav()
        self.assertEqual([True], popCalls)

    def test_two_quick_backs_stack_rather_than_replace(self):
        host = FakeHostWindow()
        host._shuttingDown = False
        host._goRootAwaitFocus = None
        host._backStack = [(FakeShell, {}), (FakeShell, {})]
        popCalls = []

        def popBack():
            popCalls.append(True)
            host._backStack.pop()
        host.popBack = popBack

        routeAction(host, FakeAction(xbmcgui.ACTION_NAV_BACK))
        routeAction(host, FakeAction(xbmcgui.ACTION_NAV_BACK))
        self.assertEqual(['popBack', 'popBack'], host.navNames())
        host.runNav()
        self.assertEqual([True, True], popCalls)

    def test_a_posted_back_with_no_chain_left_does_nothing(self):
        """E.g. a section switch ran first and cleared the chain."""
        host = FakeHostWindow()
        host._backStack = []
        popCalls = []
        host.popBack = lambda: popCalls.append(True)

        host.postNav('popBack', host._popBackIfChained, stack=True)
        host.runNav()
        self.assertEqual([], popCalls)

    def test_navback_with_a_hosted_shell_does_not_touch_grid_specific_attributes(self):
        """Regression guard for a real live bug (2026-09-03): the grid's "snap to item 0 first"
        Back step must never run for a hosted screen - it reads self.getFocusId()/
        self.POSTERS_PANEL_ID/self.showPanelControl, and a real shell like PrePlayWindow doesn't
        define POSTERS_PANEL_ID at all. It raised a bare AttributeError on every Back press while
        any shell was hosted - Back appeared to just stop doing anything after opening an item
        from a grid. Since I4 the step is the grid view's own handleBack() (GridMixin.gridBack()),
        so the host only ever asks the view that's showing. FakeHostWindow deliberately doesn't
        define contentMode/POSTERS_PANEL_ID (see module docstring), so a regression fails this
        test with that same AttributeError instead of silently passing."""
        host = FakeHostWindow()
        host._shuttingDown = False
        host._goRootAwaitFocus = None
        host._isHostedShell = True
        host._current = FakeShell(FakeShell.xmlFile, FakeShell.path, FakeShell.theme, FakeShell.res)
        host._backStack = [(FakeShell, {})]
        popCalls = []
        host.popBack = lambda: popCalls.append(True)

        routeAction(host, FakeAction(xbmcgui.ACTION_NAV_BACK))

        # Same expected outcome as the test above (posts popBack()) - what this test actually
        # guards is that the grid check above it didn't raise first.
        self.assertEqual([], popCalls)
        self.assertEqual(['popBack'], host.navNames())


class OnActionHandleBackTest(KodiTestCase):
    """I1: a hosted screen's own Back steps (handleBack()) run before the host pops the chain."""

    def _host(self, handleBackResult=False):
        host = FakeHostWindow()
        host._shuttingDown = False
        host._goRootAwaitFocus = None
        host._isHostedShell = True
        host._current = FakeShell(FakeShell.xmlFile, FakeShell.path, FakeShell.theme, FakeShell.res)
        host._current.handleBackResult = handleBackResult
        host._backStack = [(FakeShell, {})]
        return host

    def _press(self, host, action_id):
        routeAction(host, FakeAction(action_id))
        return host.navNames()

    def test_screen_that_uses_back_keeps_the_chain(self):
        host = self._host(handleBackResult=True)
        posted = self._press(host, xbmcgui.ACTION_NAV_BACK)
        self.assertEqual(1, host._current.handleBackCalls)
        self.assertEqual([], posted, "the chain must not pop when the screen used the press")

    def test_screen_that_declines_back_pops_the_chain(self):
        host = self._host(handleBackResult=False)
        posted = self._press(host, xbmcgui.ACTION_NAV_BACK)
        self.assertEqual(1, host._current.handleBackCalls)
        self.assertEqual(1, len(posted))

    def test_previous_menu_skips_the_screen_and_pops(self):
        """The screens' standalone onAction() only runs these steps for NAV_BACK."""
        host = self._host(handleBackResult=True)
        posted = self._press(host, xbmcgui.ACTION_PREVIOUS_MENU)
        self.assertEqual(0, host._current.handleBackCalls)
        self.assertEqual(1, len(posted))

    def test_an_error_in_the_screen_still_pops(self):
        host = self._host()

        def boom():
            raise RuntimeError('control gone')
        host._current.handleBack = boom
        originalError = library.util.ERROR
        library.util.ERROR = lambda *a, **k: None
        try:
            posted = self._press(host, xbmcgui.ACTION_NAV_BACK)
        finally:
            library.util.ERROR = originalError
        self.assertEqual(1, len(posted))

    def test_the_hosts_own_views_take_previous_menu_too(self):
        """The grid view's Back step (gridBack()) runs for PREVIOUS_MENU as well as Back, as the
        grid's snap to item 0 always did (kodigui.MultiWindowView.BACK_ACTIONS)."""
        host = self._host(handleBackResult=True)
        host._isHostedShell = False
        host._current.BACK_ACTIONS = library.kodigui.MultiWindowView.BACK_ACTIONS
        posted = self._press(host, xbmcgui.ACTION_PREVIOUS_MENU)
        self.assertEqual(1, host._current.handleBackCalls)
        self.assertEqual([], posted)

    def test_a_view_without_back_steps_is_not_asked(self):
        """Not every view has BACK_ACTIONS (the chain tests' plain doubles): nothing to ask."""
        host = self._host(handleBackResult=True)
        host._current = ReadyView()
        posted = self._press(host, xbmcgui.ACTION_NAV_BACK)
        self.assertEqual(1, len(posted))

    def test_navback_with_an_empty_backstack_falls_through_unmodified(self):
        """Regression guard for the "empty stack means never chained" contract: swapTo() always
        pushes before hosting a real shell, so an empty stack must behave exactly as it did before
        this session's change - i.e. NOT call popBack(), and fall into the method's pre-existing
        body. Confirmed by the AttributeError this raises (self.getFocusId is undefined on the
        fake) - proving control reached past the new early-return, not that it was skipped."""
        host = FakeHostWindow()
        host._shuttingDown = False
        host._goRootAwaitFocus = None
        host._backStack = []
        popCalls = []
        host.popBack = lambda: popCalls.append(True)

        with self.assertRaises(AttributeError):
            routeAction(host, FakeAction(xbmcgui.ACTION_NAV_BACK))

        self.assertEqual([], popCalls)

    def test_hosted_shell_skips_the_grid_body_and_dispatches_natively(self):
        """A hosted screen's action goes from the shared steps straight to the Back and Home
        handling: the grid's and Recommended's handlers are for their own views only."""
        host = FakeHostWindow()
        host._shuttingDown = False
        host._goRootAwaitFocus = None
        host._backStack = [(FakeShell, {})]  # non-empty, but this action isn't NAV_BACK
        host._isHostedShell = True
        host._current = FakeShell(FakeShell.xmlFile, FakeShell.path, FakeShell.theme, FakeShell.res)
        host.SECTION_LIST_ID = 1
        host.SERVER_BUTTON_ID = 2
        host.USER_BUTTON_ID = 3
        host.SERVER_LIST_ID = 4
        host.getFocusId = lambda: 999  # matches none of the above
        dispatchCalls = []
        host._dispatchNativeAction = lambda action: dispatchCalls.append(action)

        action = FakeAction(xbmcgui.ACTION_MOVE_DOWN)
        routeAction(host, action)

        self.assertEqual([action], dispatchCalls)


class ViewActionTest(KodiTestCase):
    """I4: routeAction() reads only the controls every view shares. The grid's and Recommended's
    own controls are read by their own handlers (viewAction()), which the host calls only when one
    of its own views (kodigui.MultiWindowView) is showing - so a hosted screen's control IDs never
    reach them."""

    class FakeView(library.kodigui.MultiWindowView):
        def __init__(self, used=False):
            self.used = used
            self.actions = []

        def viewAction(self, action):
            self.actions.append(action)
            return self.used

    def _host(self, current, focus_id=999):
        host = FakeHostWindow()
        host._shuttingDown = False
        host._goRootAwaitFocus = None
        host._backStack = []
        host.SECTION_LIST_ID = 1
        host.SERVER_BUTTON_ID = 2
        host.USER_BUTTON_ID = 3
        host.SERVER_LIST_ID = 4
        host.getFocusId = lambda: focus_id
        host._current = current
        host.dispatched = []
        host._dispatchNativeAction = lambda action: host.dispatched.append(action) or False
        host.hubAction = lambda action: self.fail('hub code reached for {0}'.format(current))
        return host

    def test_the_views_own_handler_runs_after_the_shared_steps(self):
        view = self.FakeView(used=True)
        host = self._host(view)
        action = FakeAction(xbmcgui.ACTION_MOVE_DOWN)

        self.assertTrue(routeAction(host, action))

        self.assertEqual([action], view.actions)
        self.assertEqual([], host.dispatched, "an action the view used goes no further")

    def test_an_action_the_view_passes_on_reaches_back_and_home_handling(self):
        view = self.FakeView(used=False)
        host = self._host(view)
        action = FakeAction(xbmcgui.ACTION_MOVE_DOWN)

        routeAction(host, action)

        self.assertEqual([action], view.actions)
        self.assertEqual([action], host.dispatched)

    def test_a_shared_control_never_reaches_the_view(self):
        view = self.FakeView(used=True)
        host = self._host(view, focus_id=4)  # the server list
        host.setFocusId = lambda control_id: None

        self.assertTrue(routeAction(host, FakeAction(xbmcgui.ACTION_SELECT_ITEM)))

        self.assertEqual([], view.actions)

    def test_a_hosted_pre_plays_lists_never_reach_hub_code(self):
        """Pre-play's ROLES/REVIEWS/EXTRA/RELATED/collection lists are 400-406, inside the hub
        rows' range: up and down on them used to reach the hub slide when the host was last on
        the Recommended tab, until a guard was added after a live crash."""
        shell = FakeShell(FakeShell.xmlFile, FakeShell.path, FakeShell.theme, FakeShell.res)
        for control_id in range(400, 407):
            host = self._host(shell, focus_id=control_id)
            host._isHostedShell = True
            host.contentMode = 'recommended'
            for action_id in (xbmcgui.ACTION_MOVE_UP, xbmcgui.ACTION_MOVE_DOWN, xbmcgui.ACTION_CONTEXT_MENU):
                action = FakeAction(action_id)
                routeAction(host, action)
                self.assertEqual(action, host.dispatched[-1])


class GridBackTest(KodiTestCase):
    """GridMixin.gridBack(), the grid view's handleBack(): Back on a scrolled grid snaps to item 0
    before the host pops the chain."""

    POSTERS_PANEL_ID = 101

    class Item(object):
        def __init__(self, pos):
            self._pos = pos

        def pos(self):
            return self._pos

    class Panel(object):
        def __init__(self, pos):
            self.item = GridBackTest.Item(pos) if pos is not None else None
            self.selected = []

        def getSelectedItem(self):
            return self.item

        def selectItem(self, pos):
            self.selected.append(pos)

    class Host(object):
        POSTERS_PANEL_ID = 101

        def __init__(self, focus_id, panel):
            self.focus_id = focus_id
            self.showPanelControl = panel

        def getFocusId(self):
            return self.focus_id

    def test_a_scrolled_grid_snaps_to_the_first_item(self):
        panel = self.Panel(37)
        self.assertTrue(gridBack(self.Host(self.POSTERS_PANEL_ID, panel)))
        self.assertEqual([0], panel.selected)

    def test_on_the_first_item_back_goes_on(self):
        panel = self.Panel(0)
        self.assertFalse(gridBack(self.Host(self.POSTERS_PANEL_ID, panel)))
        self.assertEqual([], panel.selected)

    def test_only_with_the_grid_focused(self):
        panel = self.Panel(37)
        self.assertFalse(gridBack(self.Host(151, panel)))  # the key list
        self.assertEqual([], panel.selected)

    def test_no_panel_yet_or_nothing_selected(self):
        self.assertFalse(gridBack(self.Host(self.POSTERS_PANEL_ID, None)))
        self.assertFalse(gridBack(self.Host(self.POSTERS_PANEL_ID, self.Panel(None))))


class OnReInitPlayGuardTest(KodiTestCase):
    """The grid's Play and "Shuffle All" (playButtonClicked()) ignore a second press while the
    first is starting (playBtnClicked). Coming back to the view, e.g. from the player, clears it
    (PlaybackBtnMixin.onReInit()) - LibraryWindow's own onReInit() used to skip that, so after one
    Play both did nothing until a section or tab switch (live-caught 2026-09-28)."""

    class Host(object):
        refill = False
        contentMode = 'library'

        def __init__(self, go_root=False):
            self.go_root = go_root
            self.playBtnClicked = True
            self.posted = []

        def _needsRootReconstruct(self):
            return True

        def openSection(self, *args, **kwargs):
            pass

        def postNav(self, name, fn, args=(), kwargs=None, stack=False):
            self.posted.append(name)

    def test_the_guard_clears_when_the_view_shows_again(self):
        host = self.Host()
        library.LibraryWindow.onReInit(host)
        self.assertFalse(host.playBtnClicked)

    def test_and_on_the_way_back_to_homes_root(self):
        host = self.Host(go_root=True)
        library.LibraryWindow.onReInit(host)
        self.assertFalse(host.playBtnClicked)
        self.assertEqual(['openSection'], host.posted)


class _FakeOnFocusHost(object):
    """A hand-built double carrying only what the Recommended view's focus path (onFocus() above:
    LibraryWindow.routeFocus(), then HubsMixin.hubFocus()) actually touches."""

    SECTION_LIST_ID = 900  # any value distinct from the hub control ids used below

    def __init__(self, last_focus_id):
        self.contentMode = 'recommended'
        self.lastFocusID = last_focus_id
        self._hubJustEnteredFromOutside = False
        self._goRootAwaitFocus = None
        self._goRootAwaitUntil = 0
        self.reselectActiveSectionCalls = []
        # No hubs by default, so the entry redirect stays out of the way of the flag-only tests.
        self.visibleHubs = []
        self._anchorRingPos = self.HUB_ROTATION_RING.index(400)
        self.focusCalls = []
        self._hubEntryRedirect = None

    HUB_ROTATION_RING = library.LibraryWindow.HUB_ROTATION_RING
    _anchorControlId = library.LibraryWindow._anchorControlId
    recordFocus = library.LibraryWindow.recordFocus

    def setFocusId(self, control_id):
        self.focusCalls.append(control_id)

    def reselectActiveSection(self, control_id, last_focus_id):
        self.reselectActiveSectionCalls.append((control_id, last_focus_id))


class OnFocusHubEntryFlagTest(KodiTestCase):
    """HubsMixin.hubFocus()'s _hubJustEnteredFromOutside detector - live-
    reported regression (2026-09-04) from onFirstInit()'s 'recommended' branch forcing focus onto
    the anchor hub control on every fresh entry (the focus-ring fix from earlier the same day):
    that setFocusId() call fires a real onFocus() the same as any other focus move, and this
    detector couldn't tell it apart from a genuine native cross-container arrow move (sidebar/tabs
    -> hub row) - it read self.lastFocusID as still outside the hub range and set the flag as if a
    duplicate native replay were coming to swallow, which then never arrived, silently eating the
    user's next real press instead. Fixed by pre-seeding self.lastFocusID to the anchor control
    itself right before that setFocusId() call - these tests pin the mechanism that relies on."""

    ANCHOR_CONTROL_ID = 400

    def test_flag_stays_false_when_last_focus_id_was_pre_seeded_to_the_anchor_itself(self):
        """The actual fix: onFirstInit()'s 'recommended' branch sets self.lastFocusID to the
        anchor control id immediately before calling setFocusId(anchor) - by the time onFocus()
        for that call runs (now or later, timing doesn't matter), was_outside_hub reads False."""
        host = _FakeOnFocusHost(last_focus_id=self.ANCHOR_CONTROL_ID)

        onFocus(host, self.ANCHOR_CONTROL_ID)

        self.assertFalse(host._hubJustEnteredFromOutside)

    def test_flag_would_have_been_set_without_the_pre_seed(self):
        """Contrast case, proving the fix actually matters: without pre-seeding lastFocusID (the
        pre-fix shape - whatever native default control focus/None left it at), the exact same
        onFocus(<hub control>) call sets the flag, which then goes on to wrongly swallow the
        user's next real press (HubsMixin.hubAction())."""
        host = _FakeOnFocusHost(last_focus_id=None)

        onFocus(host, self.ANCHOR_CONTROL_ID)

        self.assertTrue(host._hubJustEnteredFromOutside)

    def test_flag_stays_false_for_an_ordinary_in_hub_move(self):
        """Not just the initial-entry case - moving between two hub controls (both already inside
        399-500) must never set this either, the same as before any of this session's changes."""
        host = _FakeOnFocusHost(last_focus_id=401)

        onFocus(host, self.ANCHOR_CONTROL_ID)

        self.assertFalse(host._hubJustEnteredFromOutside)


class OnFocusGoRootWaitTest(KodiTestCase):
    """LibraryWindow.routeFocus()'s go_root wait. After an in-place go_root reset (onReInit(),
    _resetHubsToTop()), the window's reactivation re-focuses whichever control had focus before the
    Home press, and that event arrives before the reset's own focus event (live-confirmed
    2026-09-24). Handled as real focus it recorded the old control as lastFocusID, so a stray from
    the sidebar (9001) set _hubJustEnteredFromOutside on the target's own event and swallowed the
    next real press. routeFocus() now ignores everything until the target's own event arrives."""

    ANCHOR_CONTROL_ID = 400
    SIDEBAR_ID = 9001

    def _awaiting(self, deadline_in=1.0):
        # lastFocusID pre-seeded to the target, as _resetHubsToTop() does.
        host = _FakeOnFocusHost(last_focus_id=self.ANCHOR_CONTROL_ID)
        host._goRootAwaitFocus = self.ANCHOR_CONTROL_ID
        host._goRootAwaitUntil = library.time.time() + deadline_in
        return host

    def test_the_stray_is_ignored_entirely(self):
        host = self._awaiting()

        onFocus(host, self.SIDEBAR_ID)

        self.assertEqual(self.ANCHOR_CONTROL_ID, host.lastFocusID)
        self.assertEqual([], host.reselectActiveSectionCalls)
        self.assertEqual(self.ANCHOR_CONTROL_ID, host._goRootAwaitFocus)

    def test_stray_then_target_leaves_the_hub_entry_flag_unset(self):
        host = self._awaiting()

        onFocus(host, self.SIDEBAR_ID)
        onFocus(host, self.ANCHOR_CONTROL_ID)

        self.assertFalse(host._hubJustEnteredFromOutside)
        self.assertIsNone(host._goRootAwaitFocus)
        self.assertEqual(self.ANCHOR_CONTROL_ID, host.lastFocusID)

    def test_the_old_behaviour_set_the_flag(self):
        """Contrast case: the same two events with nothing waiting (what the stray did before this
        change, with the timed hold switched off) set the flag."""
        host = _FakeOnFocusHost(last_focus_id=self.ANCHOR_CONTROL_ID)

        onFocus(host, self.SIDEBAR_ID)
        onFocus(host, self.ANCHOR_CONTROL_ID)

        self.assertTrue(host._hubJustEnteredFromOutside)

    def test_focus_already_on_the_target_clears_the_wait_on_the_first_event(self):
        host = self._awaiting()

        onFocus(host, self.ANCHOR_CONTROL_ID)
        onFocus(host, self.ANCHOR_CONTROL_ID)

        self.assertIsNone(host._goRootAwaitFocus)
        self.assertFalse(host._hubJustEnteredFromOutside)

    def test_past_the_deadline_focus_is_handled_normally(self):
        host = self._awaiting(deadline_in=-1.0)

        onFocus(host, self.SIDEBAR_ID)

        self.assertIsNone(host._goRootAwaitFocus)
        self.assertEqual(self.SIDEBAR_ID, host.lastFocusID)


class MigrateOldContinueWatchingTest(KodiTestCase):
    """LibraryWindow._migrateOldContinueWatching() - the one-time rewrite loadHubSettings() runs
    on a saved hub config: the server's old separate home.continue/home.ondeck home hubs no longer
    exist (plexserver.hubs() always substitutes the combined continueWatching hub), so a custom
    config still listing them must list continueWatching instead or the row vanishes."""

    migrate = library.LibraryWindow._migrateOldContinueWatching

    def test_old_pair_becomes_one_continue_watching_entry_at_the_earliest_position(self):
        settings = {None: {'custom': True, 'hubs': [
            {'catalog_id': 'home.movies.recent', 'order': 0},
            {'catalog_id': 'home.continue', 'order': 1},
            {'catalog_id': 'home.ondeck', 'order': 2},
            {'catalog_id': 'home.music.recent', 'order': 3},
        ]}}
        self.assertTrue(self.migrate(settings))
        self.assertEqual(
            [('home.movies.recent', 0), ('continueWatching', 1), ('home.music.recent', 2)],
            [(h['catalog_id'], h['order']) for h in settings[None]['hubs']])

    def test_old_entries_just_drop_when_continue_watching_is_already_listed(self):
        settings = {None: {'custom': True, 'hubs': [
            {'catalog_id': 'continueWatching', 'order': 0},
            {'catalog_id': 'home.ondeck', 'order': 1},
        ]}}
        self.assertTrue(self.migrate(settings))
        self.assertEqual(['continueWatching'], [h['catalog_id'] for h in settings[None]['hubs']])

    def test_every_section_is_rewritten_not_just_home(self):
        settings = {'3': {'custom': True, 'hubs': [
            {'catalog_id': 'home.continue', 'order': 0},
            {'catalog_id': '3:movie.recentlyadded', 'order': 1},
        ]}}
        self.assertTrue(self.migrate(settings))
        self.assertEqual(['continueWatching', '3:movie.recentlyadded'],
                         [h['catalog_id'] for h in settings['3']['hubs']])

    def test_a_config_without_the_old_ids_is_left_alone(self):
        hubs = [{'catalog_id': 'home.movies.recent', 'order': 0}]
        settings = {None: {'custom': True, 'hubs': hubs}, '3': {'custom': False}}
        self.assertFalse(self.migrate(settings))
        self.assertIs(hubs, settings[None]['hubs'])

    def test_empty_or_missing_settings_are_fine(self):
        self.assertFalse(self.migrate({}))
        self.assertFalse(self.migrate(None))


class _TitledHub(object):
    def __init__(self, title, hub_identifier):
        self.title = title
        self.hubIdentifier = hub_identifier


class _TitledSection(object):
    def __init__(self, title):
        self.title = title


class HomeHubDisplayTitleTest(KodiTestCase):
    """LibraryWindow.homeHubDisplayTitle()/promotedHubSourceKey() - a library hub the server
    promotes onto Home (trailing section-id suffix on its hubIdentifier) is shown with its library
    named, Home's own hubs stay bare."""

    sections = {'32': _TitledSection('Other Videos'), '22': _TitledSection('Movies')}

    def title(self, hub_title, hub_identifier, ambiguous=None):
        host = library.LibraryWindow.__new__(library.LibraryWindow)
        if ambiguous is None:
            ambiguous = {hub_title.lower()}
        return library.LibraryWindow.homeHubDisplayTitle(
            host, _TitledHub(hub_title, hub_identifier), ambiguous, self.sections.get)

    def test_ambiguous_titles_are_the_ones_shared_between_hubs(self):
        hubs = [_TitledHub('Continue Watching', 'continueWatching'),
                _TitledHub('Continue Watching', 'video.inprogress.32'),
                _TitledHub('Recently Released Movies', 'movie.recentlyreleased.22'),
                _TitledHub('', 'x'), _TitledHub(None, 'y')]
        self.assertEqual({'continue watching'}, library.LibraryWindow.ambiguousHubTitles(hubs))

    def test_a_promoted_hub_with_an_unshared_title_stays_bare(self):
        self.assertEqual('Recently Released Movies',
                         self.title('Recently Released Movies', 'movie.recentlyreleased.22', ambiguous=set()))

    def test_source_key_is_the_single_trailing_suffix_on_home(self):
        self.assertEqual('32', library.LibraryWindow.promotedHubSourceKey('video.inprogress.32'))
        self.assertEqual('10', library.LibraryWindow.promotedHubSourceKey('music.recent.played.10'))

    def test_source_key_is_the_section_not_the_instance_for_a_two_suffix_identifier(self):
        self.assertEqual('22', library.LibraryWindow.promotedHubSourceKey('movie.recentlyadded.22.1'))

    def test_homes_own_hubs_have_no_source_key(self):
        for ident in ('home.movies.recent', 'continueWatching', 'home.playlists', '', None):
            self.assertIsNone(library.LibraryWindow.promotedHubSourceKey(ident), ident)

    def test_a_promoted_library_hub_names_its_library(self):
        self.assertEqual(u'Continue Watching \u2013 Other Videos',
                         self.title('Continue Watching', 'video.inprogress.32'))

    def test_homes_own_hub_stays_bare(self):
        self.assertEqual('Continue Watching', self.title('Continue Watching', 'continueWatching'))

    def test_an_unresolvable_library_stays_bare(self):
        self.assertEqual('Recently Played Music', self.title('Recently Played Music', 'music.recent.played.10'))

    def test_a_title_identical_to_the_library_name_stays_bare(self):
        self.assertEqual('Movies', self.title('Movies', 'movie.something.22'))


class HubStackTest(KodiTestCase):
    """Step 11 stage B: each row wrapper sits at its hub's place in one tall stack (_stackY()), and
    group 51's offset (_group51Y()) brings the focused row to the anchor line, so a slide moves
    group 51 alone. Relative to the anchor, every row must land exactly where the old per-row
    recurrence (_roleLocalY()) put it, missing hubs above the first and past the last included."""

    class Host(object):
        ROW_GAP = library.LibraryWindow.ROW_GAP
        GROUP51_BASELINE_OFFSET = library.LibraryWindow.GROUP51_BASELINE_OFFSET
        _stackY = library.LibraryWindow._stackY
        _group51Y = library.LibraryWindow._group51Y
        _roleLocalY = library.LibraryWindow._roleLocalY

        def __init__(self, heights):
            self.visibleHubs = list(heights)  # each "hub" is just its row height here

        def _hubRowHeight(self, hub):
            return 446 if hub is None else hub

    HEIGHTS = (446, 371, 326, 374, 398, 446)

    def test_rows_land_where_the_old_recurrence_put_them(self):
        host = self.Host(self.HEIGHTS)
        for focused in range(len(self.HEIGHTS)):
            for role in (-1, 0, 1, 2):
                self.assertEqual(host._roleLocalY(role, focused),
                                 host._stackY(focused + role) - host._stackY(focused),
                                 'focused {0}, role {1}'.format(focused, role))

    def test_the_stack_starts_at_the_first_hub(self):
        host = self.Host(self.HEIGHTS)
        self.assertEqual(0, host._stackY(0))
        self.assertEqual(446 + 25, host._stackY(1))
        self.assertEqual(-(446 + 25), host._stackY(-1))

    def test_the_focused_row_sits_on_the_baseline(self):
        host = self.Host(self.HEIGHTS)
        base = library.util.vscale(host.GROUP51_BASELINE_OFFSET, r=0)
        for focused in range(len(self.HEIGHTS)):
            anchor = host._group51Y(focused) + library.util.vscale(host._stackY(focused), r=0)
            self.assertEqual(base, anchor, 'focused {0}'.format(focused))

    def test_a_slide_moves_the_group_by_the_rows_between(self):
        host = self.Host(self.HEIGHTS)
        self.assertEqual(-(371 + 25), host._group51Y(2) - host._group51Y(1))
        self.assertEqual(371 + 25, host._group51Y(1) - host._group51Y(2))


class HubRingRolesTest(KodiTestCase):
    """The four-control ring: roles -1..+2 around the anchor, and a slide in either direction wraps
    exactly one control between the two off-screen roles (-1 <-> +2) while the rest shift by one."""

    class host(object):
        HUB_ROTATION_RING = library.LibraryWindow.HUB_ROTATION_RING
        HUB_MIN_ROLE = library.LibraryWindow.HUB_MIN_ROLE

    def _roles(self, ring_pos):
        h = self.host()
        return {cid: library.LibraryWindow._ringRoleOffset(h, cid, ring_pos=ring_pos)
                for cid in h.HUB_ROTATION_RING}

    def test_roles_at_rest(self):
        start = library.LibraryWindow.HUB_ROTATION_RING.index(400)
        self.assertEqual({401: -1, 400: 0, 402: 1, 403: 2}, self._roles(start))

    def test_every_ring_position_covers_minus_one_to_plus_two(self):
        for pos in range(4):
            self.assertEqual([-1, 0, 1, 2], sorted(self._roles(pos).values()))

    def test_sliding_down_wraps_only_minus_one_to_plus_two(self):
        for pos in range(4):
            before, after = self._roles(pos), self._roles((pos + 1) % 4)
            for cid in before:
                if before[cid] == -1:
                    self.assertEqual(2, after[cid])
                else:
                    self.assertEqual(before[cid] - 1, after[cid])

    def test_sliding_up_wraps_only_plus_two_to_minus_one(self):
        for pos in range(4):
            before, after = self._roles(pos), self._roles((pos - 1) % 4)
            for cid in before:
                if before[cid] == 2:
                    self.assertEqual(-1, after[cid])
                else:
                    self.assertEqual(before[cid] + 1, after[cid])


class FakeClock(object):
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now


class FakeGroup(object):
    def __init__(self):
        self.moves = []

    def setPosition(self, x, y):
        self.moves.append((x, y))


class HubSlideTest(KodiTestCase):
    """Step 11 stage C: HubSlide moves group 51 by the clock - each step goes where the elapsed time
    says - so a late step shortens the slide instead of stretching it (stage A measured the old
    12 fixed steps at about twice their 250 ms)."""

    def _slide(self, start_y=0, end_y=-400):
        clock = FakeClock()
        group = FakeGroup()
        timing = library.kodigui.StepTiming('test')
        slide = library_hubs.HubSlide(group, 7, start_y, end_y, 0.25, 'view', 1, timing, clock=clock)
        slide.start()
        return slide, clock, group

    def test_each_step_goes_where_the_clock_says(self):
        slide, clock, group = self._slide()
        clock.now += 0.125  # half way: smoothstep(0.5) = 0.5
        self.assertTrue(slide.step())
        self.assertEqual([(7, -200)], group.moves)

    def test_a_late_step_jumps_ahead_rather_than_stretching(self):
        slide, clock, group = self._slide()
        clock.now += 0.02
        slide.step()
        clock.now += 0.2  # one long stall
        slide.step()
        self.assertEqual(2, len(group.moves))
        self.assertLess(group.moves[-1][1], -380)  # nearly there: eased past 0.88

    def test_it_lands_on_time_and_stops(self):
        slide, clock, group = self._slide()
        clock.now += 0.3
        self.assertFalse(slide.step())
        self.assertEqual((7, -400), group.moves[-1])
        self.assertFalse(slide.step())
        self.assertEqual(1, len(group.moves))

    def test_no_call_when_the_position_has_not_changed(self):
        slide, clock, group = self._slide()
        clock.now += 0.001  # smoothstep(0.004) * 400 rounds to 0
        slide.step()
        self.assertEqual([], group.moves)

    def test_landing_early_snaps_to_the_end_once(self):
        slide, clock, group = self._slide()
        clock.now += 0.05
        slide.step()
        slide.land()
        slide.land()
        self.assertEqual((7, -400), group.moves[-1])
        self.assertEqual(2, len(group.moves))


class HubSlideTickerTest(KodiTestCase):
    """The host's side (_tickHubSlide(), _settleHubSlide()): the slide steps from the view's wait
    loop on the main thread, finishes once, and is dropped without touching its control once the
    view it belongs to has gone."""

    class Host(object):
        _tickHubSlide = library.LibraryWindow._tickHubSlide
        _settleHubSlide = library.LibraryWindow._settleHubSlide
        _hubSlideLive = library.LibraryWindow._hubSlideLive

        def __init__(self, slide):
            self._hubSlide = slide
            self._current = 'view'
            self._listGeneration = 1
            self.closing = False
            self.finished = 0

        def _finishHubSlide(self):
            self.finished += 1

    def _slide(self):
        clock = FakeClock()
        group = FakeGroup()
        slide = library_hubs.HubSlide(group, 0, 0, -400, 0.25, 'view', 1,
                                      library.kodigui.StepTiming('test'), clock=clock)
        slide.start()
        return slide, clock, group

    def test_steps_until_it_lands_then_finishes_once(self):
        slide, clock, group = self._slide()
        host = self.Host(slide)
        clock.now += 0.1
        self.assertTrue(host._tickHubSlide(clock.now))
        clock.now += 0.2
        self.assertFalse(host._tickHubSlide(clock.now))
        self.assertEqual(1, host.finished)
        self.assertIsNone(host._hubSlide)
        self.assertFalse(host._tickHubSlide(clock.now))
        self.assertEqual(1, host.finished)

    def test_settling_lands_it_and_finishes_once(self):
        slide, clock, group = self._slide()
        host = self.Host(slide)
        host._settleHubSlide()
        host._settleHubSlide()
        self.assertEqual((0, -400), group.moves[-1])
        self.assertEqual(1, host.finished)
        self.assertFalse(host._tickHubSlide(clock.now))

    def test_a_slide_whose_view_has_gone_is_dropped_untouched(self):
        for change in ('view', 'swap', 'closing'):
            slide, clock, group = self._slide()
            host = self.Host(slide)
            if change == 'view':
                host._current = 'a hosted screen'
            elif change == 'swap':
                host._listGeneration = 2
            else:
                host.closing = True
            clock.now += 0.1
            self.assertFalse(host._tickHubSlide(clock.now), change)
            host._settleHubSlide()
            self.assertEqual([], group.moves, change)
            self.assertEqual(0, host.finished, change)


class TickerTest(KodiTestCase):
    """MultiWindow.addTicker(): called from the view's wait loop every slice until it returns
    False, added once however often it's asked for."""

    class Host(object):
        addTicker = library.kodigui.MultiWindow.addTicker
        _runTickers = library.kodigui.MultiWindow._runTickers

        def __init__(self):
            self._tickers = []

    def test_runs_until_false_and_is_added_once(self):
        host = self.Host()
        calls = []

        def ticker(now):
            calls.append(now)
            return len(calls) < 3

        host.addTicker(ticker)
        host.addTicker(ticker)
        for now in range(5):
            host._runTickers(host._tickers, now)
        self.assertEqual([0, 1, 2], calls)
        self.assertEqual([], host._tickers)

    def test_a_ticker_that_raises_is_dropped(self):
        host = self.Host()

        def ticker(now):
            raise RuntimeError('boom')

        host.addTicker(ticker)
        originalError = library.util.ERROR
        library.util.ERROR = lambda *a, **k: None
        try:
            host._runTickers(host._tickers, 0)
        finally:
            library.util.ERROR = originalError
        self.assertEqual([], host._tickers)


class _FakeFinishSlideHost(object):
    HUB_ROTATION_RING = library.LibraryWindow.HUB_ROTATION_RING
    _anchorControlId = library.LibraryWindow._anchorControlId

    def __init__(self, focus_id, anchor_id):
        self._anchorRingPos = self.HUB_ROTATION_RING.index(anchor_id)
        self.focus_id = focus_id
        self.focusCalls = []
        self.props = {}

    def setBoolProperty(self, key, value):
        self.props[key] = value

    def getFocusId(self):
        return self.focus_id

    def setFocusId(self, control_id):
        self.focusCalls.append(control_id)


class FinishHubSlideFocusTest(KodiTestCase):
    """_finishHubSlide() moves native focus onto the new anchor only while focus is still in the hub
    rows. Live-caught 2026-09-24: Up pressed during a slide onto the first row sends focus to the
    tab bar, and the slide landing afterwards pulled it back to the row."""

    def test_moves_focus_from_the_old_anchor_to_the_new_one(self):
        host = _FakeFinishSlideHost(focus_id=402, anchor_id=400)

        library.LibraryWindow._finishHubSlide(host)

        self.assertEqual([400], host.focusCalls)
        self.assertFalse(host.props['hub.sliding'])

    def test_leaves_focus_on_the_tab_bar(self):
        host = _FakeFinishSlideHost(focus_id=320, anchor_id=400)

        library.LibraryWindow._finishHubSlide(host)

        self.assertEqual([], host.focusCalls)
        self.assertFalse(host.props['hub.sliding'])

    def test_leaves_focus_on_the_sidebar(self):
        host = _FakeFinishSlideHost(focus_id=9001, anchor_id=400)

        library.LibraryWindow._finishHubSlide(host)

        self.assertEqual([], host.focusCalls)

    def test_nothing_to_do_when_already_on_the_anchor(self):
        host = _FakeFinishSlideHost(focus_id=400, anchor_id=400)

        library.LibraryWindow._finishHubSlide(host)

        self.assertEqual([], host.focusCalls)


class OnFocusHubEntryRedirectTest(KodiTestCase):
    """Entering the hub rows from outside lands on whichever row control Kodi's group focus memory
    holds. After a slide that finished while focus was on the tabs or sidebar (_finishHubSlide()
    leaves focus alone then) that's the previous row, not the anchor - live-caught 2026-09-24.
    onFocus() redirects it to the anchor, keeping the entry flag for Kodi's replayed action."""

    TAB_LIST_ID = 320

    def _host(self, last_focus_id, anchor=400):
        host = _FakeOnFocusHost(last_focus_id=last_focus_id)
        host.visibleHubs = ['hub0', 'hub1', 'hub2']
        host._anchorRingPos = host.HUB_ROTATION_RING.index(anchor)
        return host

    def test_arrival_on_a_stale_row_is_redirected_to_the_anchor(self):
        host = self._host(last_focus_id=self.TAB_LIST_ID, anchor=402)

        onFocus(host, 400)

        self.assertEqual([402], host.focusCalls)
        self.assertTrue(host._hubJustEnteredFromOutside)
        self.assertEqual(402, host.lastFocusID)

    def test_the_redirects_own_event_keeps_the_entry_flag(self):
        host = self._host(last_focus_id=self.TAB_LIST_ID, anchor=402)

        onFocus(host, 400)
        onFocus(host, 402)

        self.assertTrue(host._hubJustEnteredFromOutside)
        self.assertEqual([402], host.focusCalls)

    def test_after_the_replay_consumed_the_flag_the_redirect_does_not_set_it_again(self):
        host = self._host(last_focus_id=self.TAB_LIST_ID, anchor=402)

        onFocus(host, 400)
        host._hubJustEnteredFromOutside = False  # routeAction()'s hub branch consumed the replay
        onFocus(host, 402)

        self.assertFalse(host._hubJustEnteredFromOutside)

    def test_arrival_on_the_anchor_is_left_alone(self):
        host = self._host(last_focus_id=self.TAB_LIST_ID, anchor=400)

        onFocus(host, 400)

        self.assertEqual([], host.focusCalls)
        self.assertTrue(host._hubJustEnteredFromOutside)

    def test_moves_within_the_rows_are_never_redirected(self):
        host = self._host(last_focus_id=401, anchor=400)

        onFocus(host, 402)

        self.assertEqual([], host.focusCalls)


class ChunkCallbackStopsMidChunkTest(KodiTestCase):
    """_retireListItems() only waits for the item being written: _chunkCallback() checks the list
    generation before every item, so a swap during a chunk stops the rest of it."""

    class Thumb(object):
        def asTranscodedImageURL(self, *dim):
            return 'thumb'

    class Album(object):
        title = parentTitle = summary = year = 'x'

        def __init__(self):
            self.defaultThumb = ChunkCallbackStopsMidChunkTest.Thumb()

    class Item(object):
        def __init__(self, onWrite=None):
            self.written = False
            self.onWrite = onWrite

        def setProperty(self, *a):
            pass

        def setLabel(self, label):
            self.written = True
            if self.onWrite:
                self.onWrite()

        setThumbnailImage = setLabel2 = setProperty

    class Host(object):
        _chunkCallback = library.LibraryWindow._chunkCallback
        _retireListItems = library.LibraryWindow._retireListItems
        closing = False

        def __init__(self):
            self.lock = library.threading.RLock()
            self._listGeneration = 1
            self.section = type('S', (), {'type': 'artist'})()

        def setBackground(self, *a, **k):
            pass

        def setBoolProperty(self, *a):
            pass

    def test_a_swap_during_a_chunk_stops_the_rest(self):
        host = self.Host()
        first = self.Item(onWrite=lambda: host._retireListItems())
        second = self.Item()
        host.showPanelControl = [first, second]
        host.itemType = 'album'
        host._chunkCallback([self.Album(), self.Album()], 0, generation=1)
        self.assertTrue(first.written)
        self.assertFalse(second.written, 'written after the list was retired')
