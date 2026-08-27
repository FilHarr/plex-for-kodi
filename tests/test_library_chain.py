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
under test (swapTo/popBack/_setupCurrent/_isRealShell, and the two new onAction() early-returns)
are called directly against a lightweight FakeHostWindow double that carries only the attributes
those methods actually touch - same style the other lib.windows.* chain tests use.

Two onAction() regressions get their own narrow tests (test_onAction_navback_pops_the_backstack /
test_onAction_hosted_shell_skips_the_grid_body) rather than a full onAction() walkthrough: onAction()
itself is a large method with many unrelated branches (section-list/server/user-button handling),
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
from lib.windows import library  # noqa: E402

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

    def onFirstInit(self):
        self.onFirstInitCalled = True

    def onAction(self, action):
        pass

    def doClose(self, **kw):
        self.closed = True


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
    swapTo = library.LibraryWindow.swapTo
    popBack = library.LibraryWindow.popBack

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
        self.openSectionCalls = []
        self.onCloseSignalCalls = []
        self.onActionCalls = []

    def openSection(self, *args, **kwargs):
        self.openSectionCalls.append((args, kwargs))

    def doClose(self, **kw):
        pass

    def onCloseSignal(self, *args, **kwargs):
        self.onCloseSignalCalls.append((args, kwargs))

    def onAction(self, action):
        # Never exercised as real dispatch logic here - _setupCurrent() only needs *some* bound
        # callable on the host to capture-and-forward onto the hosted shell. OnActionTest below
        # calls the real library.LibraryWindow.onAction directly instead of through this stub.
        self.onActionCalls.append(action)

    # base kodigui.MultiWindow._setupCurrent() (the thin-proxy branch) redirects these four
    # straight onto the host - no-op stand-ins, only exercised for "was it reassigned" checks.
    def _onFirstInit(self):
        pass

    def onReInit(self):
        pass

    def onClick(self, controlID):
        pass

    def onFocus(self, controlID):
        pass


# Bind the real, unbound methods under test directly - no LibraryWindow instance is ever
# constructed.
_isRealShell = library.LibraryWindow._isRealShell
_setupCurrent = library.LibraryWindow._setupCurrent
swapTo = library.LibraryWindow.swapTo
popBack = library.LibraryWindow.popBack
onAction = library.LibraryWindow.onAction


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
        from lib.windows import preplay, episodes, subitems, person, tracks, collection

        realShellClasses = [
            preplay.PrePlayWindow, preplay.PrePlayWindowWL,
            episodes.EpisodesWindow,
            subitems.ShowWindow, subitems.ArtistWindow,
            person.PersonWindow,
            tracks.AlbumWindow,
            collection.CollectionWindow, collection.SubDirWindow,
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

    def test_real_shell_branch_marks_the_shell_as_chained_to_this_host(self):
        host = FakeHostWindow()

        _setupCurrent(host, FakeShell)

        self.assertIs(host, host._current._chainHost)

    def test_real_shell_branch_wraps_rather_than_replaces_onFirstInit_and_onAction(self):
        host = FakeHostWindow()

        _setupCurrent(host, FakeShell)
        shell = host._current

        originalOnFirstInit = FakeShell.onFirstInit
        originalOnAction = FakeShell.onAction

        self.assertIsNot(originalOnFirstInit, shell.onFirstInit)
        self.assertIsNot(originalOnAction, shell.onAction)
        self.assertEqual(host.onAction, shell.onAction)
        self.assertEqual(originalOnAction, host._currentOnAction.__func__)

    def test_real_shell_branch_leaves_onClick_and_onFocus_and_onReInit_untouched(self):
        host = FakeHostWindow()

        _setupCurrent(host, FakeShell)
        shell = host._current

        self.assertNotIn('onClick', vars(shell))
        self.assertNotIn('onFocus', vars(shell))
        self.assertNotIn('onReInit', vars(shell))

    def test_real_shell_branch_does_not_invoke_LibraryWindows_own_onFirstInit(self):
        """Regression test for the wrap's own deviation from the naive port (see _setupCurrent()'s
        comment in library.py): the wrap must NOT call the host's onFirstInit()/_onFirstInit() -
        that's LibraryWindow's own real, template-specific setup, which would run broken against a
        real shell's native window. FakeHostWindow defines no onFirstInit() at all, so calling the
        wrapped closure would raise AttributeError if it ever tried to reach it - proving the wrap
        only touches the two host-generic lines (queued setProperty() replay + close.windows
        registration) before running the shell's own real onFirstInit()."""
        from plexnet import plexapp

        host = FakeHostWindow()
        _setupCurrent(host, FakeShell)
        shell = host._current

        try:
            shell.onFirstInit()  # must not raise, and must not need host.onFirstInit at all
            # The two host-generic lines did run: close.windows got registered...
            self.assertTrue(plexapp.util.APP.has_signal('close.windows', host.onCloseSignal))
        finally:
            plexapp.util.APP.off('close.windows', host.onCloseSignal)

        # ...and the shell's own real onFirstInit still ran (wrapped, not replaced/discarded).
        self.assertTrue(shell.onFirstInitCalled)

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

        self.assertEqual([((), {'force': True, 'section': 'the-section', 'filter_': 'the-filter'})],
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

        # pop: shell A -> root grid
        popBack(host)
        self.assertEqual([], host._backStack)
        self.assertEqual(1, len(host.openSectionCalls))


class OnActionTest(KodiTestCase):
    """Deliberately narrow - see module docstring. FakeHostWindow defines no self.dragging/
    self.contentMode/self.movingSection etc., so if either early-return below fell through instead
    of returning, the real onAction() body would raise AttributeError trying to reach them."""

    def test_navback_pops_the_backstack_and_returns_immediately(self):
        host = FakeHostWindow()
        host._shuttingDown = False
        host._goRootHoldUntil = 0
        host._backStack = [(FakeShell, {})]
        popCalls = []
        host.popBack = lambda: popCalls.append(True)

        onAction(host, FakeAction(xbmcgui.ACTION_NAV_BACK))

        self.assertEqual([True], popCalls)

    def test_navback_with_an_empty_backstack_falls_through_unmodified(self):
        """Regression guard for the "empty stack means never chained" contract: swapTo() always
        pushes before hosting a real shell, so an empty stack must behave exactly as it did before
        this session's change - i.e. NOT call popBack(), and fall into the method's pre-existing
        body. Confirmed by the AttributeError this raises (self.getFocusId is undefined on the
        fake) - proving control reached past the new early-return, not that it was skipped."""
        host = FakeHostWindow()
        host._shuttingDown = False
        host._goRootHoldUntil = 0
        host._backStack = []
        popCalls = []
        host.popBack = lambda: popCalls.append(True)

        with self.assertRaises(AttributeError):
            onAction(host, FakeAction(xbmcgui.ACTION_NAV_BACK))

        self.assertEqual([], popCalls)

    def test_hosted_shell_skips_the_grid_body_and_dispatches_natively(self):
        host = FakeHostWindow()
        host._shuttingDown = False
        host._goRootHoldUntil = 0
        host._backStack = [(FakeShell, {})]  # non-empty, but this action isn't NAV_BACK
        host._isHostedShell = True
        host.SECTION_LIST_ID = 1
        host.SERVER_BUTTON_ID = 2
        host.USER_BUTTON_ID = 3
        host.SERVER_LIST_ID = 4
        host.getFocusId = lambda: 999  # matches none of the above
        dispatchCalls = []
        host._dispatchNativeAction = lambda action: dispatchCalls.append(action)

        action = FakeAction(xbmcgui.ACTION_MOVE_DOWN)
        onAction(host, action)

        self.assertEqual([action], dispatchCalls)
