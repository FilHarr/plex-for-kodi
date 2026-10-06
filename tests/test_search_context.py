# coding=utf-8
"""
lib/windows/search.py's SearchWindow, a hosted screen since Search became a sidebar destination
(the user, 2026-10-06): a result opens as from any hosted screen (opener.open(context=self)), what
Back to it needs is its restoreState(), and the results thread's answers reach the screen through
the host's UI queue, only while it's still the screen showing.

Constructing a real SearchWindow here would pull in the native WindowXML machinery (pointless for
a pure-Python test) - the real methods are called on an instance made with __new__, its few
attributes set by hand, the style test_library_chain.py uses.

Importing lib.windows.search starts lib.player's monitor thread unless abort_requested is set
first - same guard the other lib.windows.* tests use for the same reason.
"""

from __future__ import absolute_import

import weakref

from kodienv import ENV

ENV.abort_requested = True
from lib.windows import kodigui, search  # noqa: E402

from .base import KodiTestCase  # noqa: E402


class FakeHubItem(object):
    def __init__(self, type_, exists=True):
        self.TYPE = type_
        self._exists = exists

    def exists(self):
        return self._exists


class FakeManagedControlList(object):
    def __init__(self, control_id, selected_item=None, selected_pos=0):
        self.controlID = control_id
        self._selected = selected_item
        self._selectedPos = selected_pos
        self.removedItems = []

    def getSelectedItem(self):
        return self._selected

    def getSelectedPos(self):
        return self._selectedPos

    def removeManagedItem(self, mli):
        self.removedItems.append(mli)


class FakeManagedListItem(object):
    def __init__(self, data_source):
        self.dataSource = data_source


class FakeEdit(object):
    def __init__(self, text=''):
        self.text = text

    def getText(self):
        return self.text


def searchWindow(control=None, text='alien'):
    """A SearchWindow with only what the methods under test touch."""
    win = search.SearchWindow.__new__(search.SearchWindow)
    win.hubControls = [control or FakeManagedControlList(2100)]
    win.edit = FakeEdit(text)
    win.exitCommand = None
    win._closing = False
    win.processedCommands = []
    win.historyAdded = []
    win.addToHistory = win.historyAdded.append
    win.processCommand = win.processedCommands.append
    return win


class HubItemClickedTest(KodiTestCase):
    def _click(self, hubItem):
        mli = FakeManagedListItem(hubItem)
        control = FakeManagedControlList(2100, selected_item=mli)
        win = searchWindow(control)

        calls = []
        originalOpen = search.opener.open

        def fakeOpen(obj, context=None, **kwargs):
            calls.append((obj, context))
            return 'the-command'

        search.opener.open = fakeOpen
        try:
            win.hubItemClicked(2100)
        finally:
            search.opener.open = originalOpen

        return win, control, mli, calls

    def test_opens_the_result_with_itself_as_the_context(self):
        for type_ in ('movie', 'show', 'episode', 'Genre', 'Director', 'Role', 'photo', 'track', 'clip'):
            hubItem = FakeHubItem(type_)
            win, _, _, calls = self._click(hubItem)
            self.assertEqual([(hubItem, win)], calls, type_)
            self.assertEqual(['the-command'], win.processedCommands, type_)

    def test_the_query_goes_into_the_history_first(self):
        win, _, _, _ = self._click(FakeHubItem('movie'))
        self.assertEqual(['alien'], win.historyAdded)

    def test_it_stays_open(self):
        """The host swaps the result's screen in (opener -> openWindow() -> swapTo()); a photo,
        track or clip opens over it. Either way it doesn't close itself."""
        win, _, _, _ = self._click(FakeHubItem('movie'))
        self.assertFalse(win._closing)

    def test_a_result_gone_meanwhile_leaves_the_row(self):
        win, control, mli, _ = self._click(FakeHubItem('movie', exists=False))
        self.assertEqual([mli], control.removedItems)


class RestoreStateTest(KodiTestCase):
    def window(self, focus, selected_pos=0):
        rows = [FakeManagedControlList(2100 + i, selected_pos=selected_pos) for i in range(search.SearchWindow.SEARCH_HUB_COUNT)]
        win = searchWindow(text='alien')
        win.hubControls = rows
        win.getFocusId = lambda: focus
        win.getProperty = lambda key: {'search.section': 'movie'}.get(key, '')
        return win

    def test_on_a_result_it_keeps_the_query_type_and_result(self):
        self.assertEqual({'query': 'alien', 'searchSection': 'movie', 'focus': (2, 4)},
                         self.window(2102, selected_pos=4).restoreState())

    def test_away_from_the_results_no_focus(self):
        for focus in (search.SearchWindow.BUTTON_A_ID, search.SearchWindow.HISTORY_LIST_ID, 911):
            self.assertIsNone(self.window(focus).restoreState()['focus'], focus)

    def test_its_keys_are_the_constructors(self):
        """popBack() rebuilds it with the entry as its kwargs (LibraryWindow.swapTo())."""
        state = self.window(2100).restoreState()
        self.assertEqual({'query', 'searchSection', 'focus'}, set(state))


class FakeHost(object):
    """The host's real UI queue (kodigui.MultiWindow.postUI()/_runPendingUI())."""
    postUI = kodigui.MultiWindow.postUI
    _runPendingUI = kodigui.MultiWindow._runPendingUI
    NAV_INIT_HOLD_MAX_SECONDS = kodigui.MultiWindow.NAV_INIT_HOLD_MAX_SECONDS

    def __init__(self):
        import threading
        self._navLock = threading.Lock()
        self._uiPending = []
        self._current = None

    def runUI(self):
        view = type('Ready', (), {'finishedInit': True})()
        self._runPendingUI(view, 0)


class PostedResultsTest(KodiTestCase):
    """The results thread doesn't write the screen: it posts to the host, and what it posted only
    runs while this screen is still the one showing (_post())."""

    def hosted(self):
        host = FakeHost()
        win = searchWindow()
        win._hostRef = weakref.ref(host)
        host._current = win
        win.shown = []
        return host, win

    def test_runs_on_the_hosts_queue(self):
        host, win = self.hosted()
        win._post('search results', win.shown.append, ('rows',))
        self.assertEqual([], win.shown)
        host.runUI()
        self.assertEqual(['rows'], win.shown)

    def test_dropped_once_swapped_out(self):
        host, win = self.hosted()
        win._post('search results', win.shown.append, ('rows',))
        host._current = object()
        host.runUI()
        self.assertEqual([], win.shown)

    def test_not_posted_once_swapped_out(self):
        host, win = self.hosted()
        host._current = object()
        win._post('search results', win.shown.append, ('rows',))
        self.assertEqual([], host._uiPending)

    def test_dropped_once_closed(self):
        host, win = self.hosted()
        win._post('search results', win.shown.append, ('rows',))
        win._closing = True
        host.runUI()
        self.assertEqual([], win.shown)


class ResultsThreadTest(KodiTestCase):
    """A key pressed while a search is under way is searched for once it's done (it used to wait
    for the next key)."""

    def test_a_query_changed_during_a_search_is_searched_next(self):
        win = searchWindow()
        win._hostRef = None
        import threading
        win._resultsLock = threading.Lock()
        win.resultsThread = 'running'
        win.updateResultsTimeout = 0
        win._query = 'ali'
        searched = []

        def fakeSearch(query):
            searched.append(query)
            if query == 'ali':
                # typed meanwhile (updateResults() on the main thread)
                win._query = 'alien'
        win._search = fakeSearch
        win._updateResults()
        self.assertEqual(['ali', 'alien'], searched)
        self.assertIsNone(win.resultsThread)
