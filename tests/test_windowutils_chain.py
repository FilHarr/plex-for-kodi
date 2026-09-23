# coding=utf-8
"""
lib/windows/windowutils.py's chain-awareness additions from hashed-orbiting-pizza.md's Phase 1:
GoHomeMixin.goHome()/goHomeRoot() and UtilMixin.processCommand()/openWindow() all need to operate
on a shell's host (self._chainHost - the hosting LibraryWindow instance, library.py) rather than
the shell instance itself, once one exists - a chained shell's own forceDismiss()/doClose() only
ever touch itself, and the host's _open() poll loop would otherwise just reconstruct and reopen the
same shell again (neither its _allClosed flag nor _next/_nextKwargs would have changed).

Deliberately doesn't exercise the *not* chained branches beyond a plain regression check - those
are pre-existing, already-live code paths (real HOME/_MWBackground/opener.handleOpen()
interactions), not what this session's Phase 1 work changed.

GoHomeMixin._liveChainHost() exists because of a real, live-caught crash: a shell's own
settled-focus debounce thread (since removed - the sidebar is click-only now) could still be in
flight from *before* a swapTo() swapped that shell out (or the whole chain closed), and land here calling
self.goHome() well after self._chainHost's own _current/_currentOnAction were already del'd by
MultiWindow._open()'s teardown (kodigui.py) - AttributeError, live-confirmed via kodi.log, not a
hypothetical. _allClosed is a real, never-del'd flag (unlike _current), so checking it first is what
tells a live host from a stale reference to an already-fully-closed one. ChainAwareStaleHostTest
below locks in the fix.

ChainAwareSelfHostingTest covers a second, distinct hazard: LibraryWindow points its own _chainHost
at itself (unconditionally, so openWindow() can resolve a genesis click into swapTo() without a
LibraryWindow-specific override) - which means the chain-checking goHome()/goHomeRoot()/
processCommand() wrappers below would resolve _liveChainHost() back to the caller itself and
recurse forever if a self-hosting caller ever invoked them directly. _goHomeDirect()/
_goHomeRootDirect()/_processHomeCommandDirect() exist so a self-hosting override (LibraryWindow's
own goHome()/goHomeRoot()/processCommand(), library.py) can bypass the wrapper and call straight
through once it's already decided "I'm not delegating anywhere else."

Importing lib.windows.windowutils starts lib.player's monitor thread unless abort_requested is set
first - same guard the other lib.windows.* tests use for the same reason.
"""

from __future__ import absolute_import

from kodienv import ENV

ENV.abort_requested = True
from lib.windows import windowutils  # noqa: E402

from .base import KodiTestCase  # noqa: E402

# A section OBJECT stand-in. Not a bare string: goHome() treats a str (plexobjects.PlexValue is
# one) as a section key to be resolved through HOME.sectionByKey() - see the resolution test
# below - so a string here would exercise that path, not the pass-through this file is about.
SECTION = type("FakeSection", (), {"key": "42"})()


class FakeChainHost(object):
    def __init__(self, all_closed=False):
        self._allClosed = all_closed
        self.goHomeCalls = []
        self.processCommandCalls = []
        self.swapToCalls = []

    def goHome(self, section=None, with_root=False, force=False):
        self.goHomeCalls.append((section, with_root, force))

    def processCommand(self, command):
        self.processCommandCalls.append(command)

    def swapTo(self, window_class, **kwargs):
        self.swapToCalls.append((window_class, kwargs))


class FakeChainedShell(windowutils.UtilMixin):
    """A UtilMixin user standing in for any chain-eligible shell (CollectionWindow, PrePlayWindow,
    ...) - only the bits goHome()/processCommand()/openWindow() actually touch are faked."""

    def __init__(self, chain_host):
        windowutils.UtilMixin.__init__(self)
        self._chainHost = chain_host
        self.forceDismissCalled = False
        self.doCloseCalled = False

    def forceDismiss(self):
        self.forceDismissCalled = True

    def doClose(self, **kw):
        self.doCloseCalled = True


class ChainAwareGoHomeTest(KodiTestCase):
    def test_goHome_delegates_to_the_chain_host_instead_of_dismissing_itself(self):
        host = FakeChainHost()
        shell = FakeChainedShell(host)

        shell.goHome(section=SECTION, with_root=True)

        self.assertEqual([(SECTION, True, False)], host.goHomeCalls)
        # Not the shell's own dismiss/close - operating on self here would only ever close the
        # shell, leaving the host's poll loop to reconstruct and reopen it.
        self.assertFalse(shell.forceDismissCalled)
        self.assertFalse(shell.doCloseCalled)

    def test_goHomeRoot_delegates_to_the_chain_host_with_root_forced(self):
        host = FakeChainHost()
        shell = FakeChainedShell(host)

        shell.goHomeRoot()

        self.assertEqual([(None, True, False)], host.goHomeCalls)
        self.assertFalse(shell.forceDismissCalled)

    def test_unchained_goHome_still_dismisses_itself_directly(self):
        """Plain regression check on the pre-existing (unchanged) branch - _chainHost's class-
        level default is None, so a window that was never inside a chain must behave exactly as
        before."""
        fakeHome = type("FakeHome", (), {"go_root": None, "_pendingSection": None, "show": lambda self: None})()
        windowutils.HOME = fakeHome
        try:
            shell = FakeChainedShell(chain_host=None)
            shell.goHome(section=SECTION)
            self.assertTrue(shell.forceDismissCalled)
            self.assertTrue(shell.doCloseCalled)
            self.assertEqual(SECTION, fakeHome._pendingSection)
        finally:
            windowutils.HOME = None

    def test_a_bare_section_key_is_resolved_through_home(self):
        """getLibrarySectionId() callers (the music player's / Album screen's / photo directory's
        "Go to <section>") hand goHome() a key, not a section - a str (PlexValue). It has to reach
        openSection() as the sidebar's section object, via HOME.sectionByKey(); passing the key
        through raw blew up there on `section.server` (live, 2026-09-18)."""
        looked_up = []
        fakeHome = type("FakeHome", (), {
            "go_root": None, "_pendingSection": None, "show": lambda self: None,
            "sectionByKey": lambda self, key: looked_up.append(key) or SECTION,
        })()
        windowutils.HOME = fakeHome
        try:
            shell = FakeChainedShell(chain_host=None)
            shell.goHome(section="42")
            self.assertEqual(["42"], looked_up)
            self.assertIs(SECTION, fakeHome._pendingSection)
        finally:
            windowutils.HOME = None


class ChainAwareProcessCommandTest(KodiTestCase):
    def test_a_home_command_bubbles_to_the_chain_host(self):
        host = FakeChainHost()
        shell = FakeChainedShell(host)

        shell.processCommand("HOME")

        self.assertEqual(["HOME"], host.processCommandCalls)
        self.assertFalse(shell.doCloseCalled)
        self.assertIsNone(shell.exitCommand)

    def test_unchained_home_command_still_closes_itself_directly(self):
        shell = FakeChainedShell(chain_host=None)

        shell.processCommand("HOME")

        self.assertTrue(shell.doCloseCalled)
        self.assertEqual("HOME", shell.exitCommand)


class ChainAwareOpenWindowTest(KodiTestCase):
    def test_open_window_swaps_in_place_when_already_chained(self):
        host = FakeChainHost()
        shell = FakeChainedShell(host)

        shell.openWindow(FakeChainedShell, media_item="the-show")

        self.assertEqual([(FakeChainedShell, {"media_item": "the-show"})], host.swapToCalls)


class OpenItemPassesContextTest(KodiTestCase):
    """hashed-orbiting-pizza.md Phase 4 item 1: openItem() passes context=self to opener.open()
    so its dispatch can call self.openWindow(...) for whichever object types have been made
    chain-aware so far (currently just movies, opener.py's own docstring on open()) - inert for
    everything else. Doesn't exercise opener.open()'s own dispatch logic (that's
    tests/test_opener_context.py) - just that openItem() forwards context correctly."""

    def test_openItem_forwards_context_equal_to_self(self):
        shell = FakeChainedShell(chain_host=None)
        openCalls = []

        def fakeOpen(obj, context=None, **kwargs):
            openCalls.append((obj, context, kwargs))
            return ''

        originalOpen = windowutils.opener.open
        windowutils.opener.open = fakeOpen
        try:
            shell.openItem("the-object", extra="kwarg")
        finally:
            windowutils.opener.open = originalOpen

        self.assertEqual([("the-object", shell, {"extra": "kwarg"})], openCalls)


class ChainAwareStaleHostTest(KodiTestCase):
    """The bug this session's live testing actually caught: a shell's own settled-focus debounce
    thread firing after its host already fully closed. See the module docstring."""

    def test_goHome_falls_back_to_dismissing_itself_once_the_host_has_closed(self):
        host = FakeChainHost(all_closed=True)
        fakeHome = type("FakeHome", (), {"go_root": None, "_pendingSection": None, "show": lambda self: None})()
        windowutils.HOME = fakeHome
        try:
            shell = FakeChainedShell(host)
            shell.goHome(section=SECTION)

            # Not delegated to the dead host - that's the crash this guards against.
            self.assertEqual([], host.goHomeCalls)
            self.assertTrue(shell.forceDismissCalled)
            self.assertTrue(shell.doCloseCalled)
        finally:
            windowutils.HOME = None

    def test_goHomeRoot_falls_back_once_the_host_has_closed(self):
        host = FakeChainHost(all_closed=True)
        fakeHome = type("FakeHome", (), {"go_root": None, "_pendingSection": None, "show": lambda self: None})()
        windowutils.HOME = fakeHome
        try:
            shell = FakeChainedShell(host)
            shell.goHomeRoot()

            self.assertEqual([], host.goHomeCalls)
            self.assertTrue(shell.forceDismissCalled)
        finally:
            windowutils.HOME = None

    def test_process_command_falls_back_once_the_host_has_closed(self):
        host = FakeChainHost(all_closed=True)
        shell = FakeChainedShell(host)

        shell.processCommand("HOME")

        self.assertEqual([], host.processCommandCalls)
        self.assertTrue(shell.doCloseCalled)
        self.assertEqual("HOME", shell.exitCommand)

    def test_a_live_host_is_still_used_normally(self):
        """Plain sanity check that all_closed=False (the default) doesn't itself break the
        already-covered delegating path above - the guard must be precise, not a blanket bypass."""
        host = FakeChainHost(all_closed=False)
        shell = FakeChainedShell(host)

        shell.goHome(section=SECTION)

        self.assertEqual([(SECTION, False, False)], host.goHomeCalls)
        self.assertFalse(shell.forceDismissCalled)


class FakeSelfHostingWindow(windowutils.UtilMixin):
    """Stands in for LibraryWindow: points its own _chainHost at itself (library.py's __init__),
    and mirrors LibraryWindow's own goHome()/goHomeRoot()/processCommand() overrides - each of
    which falls through, once it's decided "I'm not the true root," to the mixin's _...Direct()
    variant rather than the chain-checking wrapper. See the module docstring."""

    def __init__(self):
        windowutils.UtilMixin.__init__(self)
        self._chainHost = self
        self.forceDismissCalled = False
        self.doCloseCalled = False
        self.isRoot = False

    def forceDismiss(self):
        self.forceDismissCalled = True

    def doClose(self, **kw):
        self.doCloseCalled = True

    def goHome(self, section=None, with_root=False, force=False):
        if self.isRoot:
            return
        windowutils.GoHomeMixin._goHomeDirect(self, section=section, with_root=with_root, force=force)

    def goHomeRoot(self, *args, **kwargs):
        if self.isRoot:
            return
        windowutils.GoHomeMixin._goHomeRootDirect(self)

    def processCommand(self, command):
        if command and command.startswith('HOME') and self.isRoot:
            return
        if command and command.startswith('HOME'):
            windowutils.UtilMixin._processHomeCommandDirect(self, command)
            return
        windowutils.UtilMixin.processCommand(self, command)


class ChainAwareSelfHostingTest(KodiTestCase):
    """LibraryWindow's _chainHost points at itself unconditionally (needed so openWindow() can
    resolve its own genesis clicks into swapTo() without a LibraryWindow-specific override) - which
    means goHome()/goHomeRoot()/processCommand() must NOT go through the chain-checking wrapper
    once a self-hosting override has already run: _liveChainHost() would resolve back to self,
    and calling self.goHome()/self.processCommand() again would recurse forever, since Python
    resolves that call straight back to the same override. Locks in the _...Direct() fix."""

    def test_goHome_does_not_recurse_when_self_hosting(self):
        fakeHome = type("FakeHome", (), {"go_root": None, "_pendingSection": None, "show": lambda self: None})()
        windowutils.HOME = fakeHome
        try:
            window = FakeSelfHostingWindow()
            window.goHome(section=SECTION)

            self.assertTrue(window.forceDismissCalled)
            self.assertTrue(window.doCloseCalled)
            self.assertEqual(SECTION, fakeHome._pendingSection)
        finally:
            windowutils.HOME = None

    def test_goHomeRoot_does_not_recurse_when_self_hosting(self):
        fakeHome = type("FakeHome", (), {"go_root": None, "_pendingSection": None, "show": lambda self: None})()
        windowutils.HOME = fakeHome
        try:
            window = FakeSelfHostingWindow()
            window.goHomeRoot()

            self.assertTrue(window.forceDismissCalled)
        finally:
            windowutils.HOME = None

    def test_process_command_does_not_recurse_when_self_hosting(self):
        window = FakeSelfHostingWindow()

        window.processCommand("HOME")

        self.assertTrue(window.doCloseCalled)
        self.assertEqual("HOME", window.exitCommand)

    def test_root_instance_still_short_circuits_before_reaching_the_mixin(self):
        """Sanity check that this fake's own "am I the true root" branch (mirroring LibraryWindow's
        `self is windowutils.HOME` check) still wins over self-hosting delegation - the recursion
        risk only exists for the non-root fallback path exercised above."""
        window = FakeSelfHostingWindow()
        window.isRoot = True

        window.goHome(section=SECTION)
        window.processCommand("HOME")

        self.assertFalse(window.forceDismissCalled)
        self.assertFalse(window.doCloseCalled)
