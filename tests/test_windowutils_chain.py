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

NavIntent (navintent.py, I5 in the navigation review) replaced the 'HOME' exit command and the
section/go_root values stashed on Home: a hosted screen hands the intent to its host, anything
else hands it to Home at once (returnHere()) and closes with it as its exitCommand, and each
blocking window it passes through (processCommand()) closes too. LibraryWindow, which points its
own _chainHost at itself, acts on it as Home or leaves like any other window - LibraryNavigateTest
below runs its real navigate()/returnHere()/processCommand(), which check `self is HOME` rather than
delegating to _liveChainHost() (that would resolve back to self and recurse forever).

Importing lib.windows.windowutils starts lib.player's monitor thread unless abort_requested is set
first - same guard the other lib.windows.* tests use for the same reason.
"""

from __future__ import absolute_import

from kodienv import ENV

ENV.abort_requested = True
from lib.windows import library, navintent, windowutils  # noqa: E402

from .base import KodiTestCase  # noqa: E402

# A section OBJECT stand-in. Not a bare string: goHome() treats a str (plexobjects.PlexValue is
# one) as a section key to be resolved through HOME.sectionByKey() - see the resolution test
# below - so a string here would exercise that path, not the pass-through this file is about.
SECTION = type("FakeSection", (), {"key": "42"})()


class FakeChainHost(object):
    def __init__(self, all_closed=False):
        self._allClosed = all_closed
        self.navigateCalls = []
        self.processCommandCalls = []
        self.swapToCalls = []
        self.postNavCalls = []

    def navigate(self, intent):
        self.navigateCalls.append(intent)

    def processCommand(self, command):
        self.processCommandCalls.append(command)

    def swapTo(self, window_class, **kwargs):
        self.swapToCalls.append((window_class, kwargs))

    def postNav(self, name, fn, args=(), kwargs=None, stack=False):
        # Run at once: the queue itself is covered by tests/test_nav_queue.py.
        self.postNavCalls.append(name)
        fn(*args, **(kwargs or {}))


class FakeHome(object):
    def __init__(self):
        self.returned = []

    def returnHere(self, intent):
        self.returned.append(intent)


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


def intentFields(intent):
    return (intent.kind, intent.section, intent.root, intent.force)


class HomeTestCase(KodiTestCase):
    def setUp(self):
        super(HomeTestCase, self).setUp()
        self.home = FakeHome()
        windowutils.HOME = self.home
        self.addCleanup(setattr, windowutils, 'HOME', None)


class ChainAwareGoHomeTest(HomeTestCase):
    def test_goHome_hands_the_intent_to_the_chain_host(self):
        host = FakeChainHost()
        shell = FakeChainedShell(host)

        shell.goHome(section=SECTION, with_root=True)

        self.assertEqual([('home', SECTION, True, False)], [intentFields(i) for i in host.navigateCalls])
        # Not the shell's own dismiss/close - operating on self here would only ever close the
        # shell, leaving the host's poll loop to reconstruct and reopen it.
        self.assertFalse(shell.forceDismissCalled)
        self.assertFalse(shell.doCloseCalled)
        self.assertEqual([], self.home.returned)

    def test_goHomeRoot_asks_the_chain_host_for_the_root(self):
        host = FakeChainHost()
        shell = FakeChainedShell(host)

        shell.goHomeRoot()

        self.assertEqual([('home', None, True, False)], [intentFields(i) for i in host.navigateCalls])
        self.assertFalse(shell.forceDismissCalled)

    def test_outside_the_chain_home_takes_it_and_the_window_closes_with_it(self):
        shell = FakeChainedShell(chain_host=None)

        shell.goHome(section=SECTION, force=True)

        self.assertTrue(shell.forceDismissCalled)
        self.assertTrue(shell.doCloseCalled)
        self.assertEqual([('home', SECTION, False, True)], [intentFields(i) for i in self.home.returned])
        # The same intent, so each blocking window beneath closes too.
        self.assertIs(self.home.returned[0], shell.exitCommand)


class ChainAwareProcessCommandTest(HomeTestCase):
    def test_an_intent_passing_a_hosted_screen_goes_to_its_host(self):
        host = FakeChainHost()
        shell = FakeChainedShell(host)
        intent = navintent.home()

        shell.processCommand(intent)

        self.assertEqual([intent], host.processCommandCalls)
        self.assertFalse(shell.doCloseCalled)
        self.assertIsNone(shell.exitCommand)

    def test_an_intent_passing_a_window_outside_the_chain_closes_it_too(self):
        shell = FakeChainedShell(chain_host=None)
        intent = navintent.home()

        shell.processCommand(intent)

        self.assertTrue(shell.doCloseCalled)
        self.assertIs(intent, shell.exitCommand)
        # Home already has it, from where it was issued.
        self.assertEqual([], self.home.returned)

    def test_no_data_still_raises(self):
        shell = FakeChainedShell(chain_host=None)
        with self.assertRaises(windowutils.util.NoDataException):
            shell.processCommand("NODATA")


class ChainAwareOpenWindowTest(KodiTestCase):
    def test_open_window_swaps_in_place_when_already_chained(self):
        host = FakeChainHost()
        shell = FakeChainedShell(host)

        shell.openWindow(FakeChainedShell, media_item="the-show")

        self.assertEqual(["open FakeChainedShell"], host.postNavCalls)
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


class ChainAwareStaleHostTest(HomeTestCase):
    """The bug this session's live testing actually caught: a shell's own settled-focus debounce
    thread firing after its host already fully closed. See the module docstring."""

    def test_goHome_leaves_for_home_itself_once_the_host_has_closed(self):
        host = FakeChainHost(all_closed=True)
        shell = FakeChainedShell(host)

        shell.goHome(section=SECTION)

        # Not handed to the dead host - that's the crash this guards against.
        self.assertEqual([], host.navigateCalls)
        self.assertTrue(shell.forceDismissCalled)
        self.assertTrue(shell.doCloseCalled)
        self.assertEqual(1, len(self.home.returned))

    def test_process_command_closes_once_the_host_has_closed(self):
        host = FakeChainHost(all_closed=True)
        shell = FakeChainedShell(host)
        intent = navintent.home()

        shell.processCommand(intent)

        self.assertEqual([], host.processCommandCalls)
        self.assertTrue(shell.doCloseCalled)
        self.assertIs(intent, shell.exitCommand)

    def test_a_live_host_is_still_used_normally(self):
        """Plain sanity check that all_closed=False (the default) doesn't itself break the
        already-covered delegating path above - the guard must be precise, not a blanket bypass."""
        host = FakeChainHost(all_closed=False)
        shell = FakeChainedShell(host)

        shell.goHome(section=SECTION)

        self.assertEqual([('home', SECTION, False, False)], [intentFields(i) for i in host.navigateCalls])
        self.assertFalse(shell.forceDismissCalled)


class FakeLibrary(windowutils.UtilMixin):
    """LibraryWindow's real navigate()/returnHere()/resolveSection()/processCommand(), on a stand-in
    that points its own _chainHost at itself as LibraryWindow does."""
    navigate = library.LibraryWindow.navigate
    returnHere = library.LibraryWindow.returnHere
    resolveSection = library.LibraryWindow.resolveSection
    processCommand = library.LibraryWindow.processCommand

    def __init__(self, section=None):
        windowutils.UtilMixin.__init__(self)
        self._chainHost = self
        self._allClosed = False
        self.section = section
        self.closeOption = None
        self.go_root = False
        self.calls = []

    def _deferOpenSection(self, section, force=False):
        self.calls.append(('openSection', section, force))

    def _goRootNow(self):
        self.calls.append(('root',))

    def openSection(self, section, force=False):
        self.calls.append(('openSection', section, force))

    def postNav(self, name, fn, args=(), kwargs=None, stack=False):
        fn(*args, **(kwargs or {}))

    def show(self, **kwargs):
        self.calls.append(('show', self.go_root))

    def sectionByKey(self, key):
        return SECTION if key == '42' else None

    def forceDismiss(self):
        self.calls.append(('forceDismiss',))

    def doClose(self, **kw):
        self.calls.append(('doClose',))


class LibraryNavigateTest(KodiTestCase):
    def setUp(self):
        super(LibraryNavigateTest, self).setUp()
        self.addCleanup(setattr, windowutils, 'HOME', None)

    def _home(self, section=None):
        home = FakeLibrary(section)
        windowutils.HOME = home
        return home

    def test_home_opens_a_section_it_is_not_showing(self):
        home = self._home()
        home.navigate(navintent.home(section=SECTION))
        self.assertEqual([('openSection', SECTION, False)], home.calls)

    def test_home_ignores_the_section_it_is_showing_unless_forced(self):
        home = self._home(SECTION)
        home.navigate(navintent.home(section=SECTION))
        self.assertEqual([], home.calls)
        home.navigate(navintent.home(section=SECTION, force=True))
        self.assertEqual([('openSection', SECTION, True)], home.calls)

    def test_home_goes_to_its_root(self):
        home = self._home()
        home.navigate(navintent.home(root=True))
        self.assertEqual([('root',)], home.calls)

    def test_a_section_key_is_resolved_through_the_sidebar(self):
        """getLibrarySectionId() callers (the music player's / Album screen's / photo directory's
        "Go to <section>") hand over a key, not a section - a str (PlexValue). It has to reach
        openSection() as the sidebar's section object; passing the key through raw blew up there
        on `section.server` (live, 2026-09-18)."""
        home = self._home()
        home.navigate(navintent.home(section='42'))
        self.assertEqual([('openSection', SECTION, False)], home.calls)

    def test_returning_home_shows_it_then_opens_the_section(self):
        home = self._home()
        home.returnHere(navintent.home(section='42'))
        self.assertEqual([('show', False), ('openSection', SECTION, True)], home.calls)

    def test_returning_home_to_the_root_shows_it_with_go_root(self):
        home = self._home()
        home.returnHere(navintent.home(root=True))
        self.assertEqual([('show', True)], home.calls)

    def test_a_nested_library_window_leaves_for_home_without_recursing(self):
        home = self._home()
        nested = FakeLibrary()

        nested.navigate(navintent.home(section=SECTION))

        self.assertEqual([('forceDismiss',), ('doClose',)], nested.calls)
        self.assertTrue(navintent.isNavIntent(nested.exitCommand))
        self.assertEqual([('show', False), ('openSection', SECTION, True)], home.calls)

    def test_an_intent_arriving_at_home_leaves_it_open(self):
        home = self._home()
        home.processCommand(navintent.home())
        self.assertEqual([], home.calls)

    def test_an_intent_arriving_at_home_with_a_session_end_closes_it(self):
        home = self._home()
        home.closeOption = 'exit'
        home.processCommand(navintent.home())
        self.assertEqual([('doClose',)], home.calls)

    def test_an_intent_passing_a_nested_library_window_closes_it(self):
        self._home()
        nested = FakeLibrary()
        intent = navintent.home()
        nested.processCommand(intent)
        self.assertEqual([('doClose',)], nested.calls)
        self.assertIs(intent, nested.exitCommand)
