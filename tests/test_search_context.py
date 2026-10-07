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
from unittest import mock

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

    def setText(self, text):
        self.text = text


def searchWindow(control=None, text='alien'):
    """A SearchWindow with only what the methods under test touch."""
    win = search.SearchWindow.__new__(search.SearchWindow)
    win.resultsList = control or FakeManagedControlList(2100)
    win.edit = FakeEdit(text)
    win.exitCommand = None
    win._closing = False
    win.processedCommands = []
    win.historyAdded = []
    win.addToHistory = win.historyAdded.append
    win.processCommand = win.processedCommands.append
    return win


class ResultClickedTest(KodiTestCase):
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
            win.resultClicked()
        finally:
            search.opener.open = originalOpen

        return win, control, mli, calls

    def test_opens_the_result_with_itself_as_the_context(self):
        for type_ in ('movie', 'show', 'episode', 'Director', 'Role', 'photo', 'track', 'clip'):
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

    def test_a_result_gone_meanwhile_leaves_the_grid(self):
        win, control, mli, _ = self._click(FakeHubItem('movie', exists=False))
        self.assertEqual([mli], control.removedItems)


class RestoreStateTest(KodiTestCase):
    def window(self, focus, selected_pos=0):
        win = searchWindow(FakeManagedControlList(2100, selected_pos=selected_pos), text='alien')
        win.getFocusId = lambda: focus
        win.getProperty = lambda key: {'search.section': 'movie'}.get(key, '')
        return win

    def test_on_a_result_it_keeps_the_query_type_and_result(self):
        self.assertEqual({'query': 'alien', 'searchSection': 'movie', 'focus': 4},
                         self.window(2100, selected_pos=4).restoreState())

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


class TypeButtonsTest(KodiTestCase):
    """The type buttons narrow the results (showHubs()); People shows the actors and directors."""

    class Hub(object):
        def __init__(self, type_):
            self.type = type_
            self.size = type('Size', (), {'asInt': lambda s: 1})()
            self.items = [type_]

    def shown(self, section):
        win = searchWindow()
        win.props = {'search.section': section}
        win.getProperty = lambda key: win.props.get(key, '')
        win.setProperty = win.props.__setitem__
        win.clearHubs = lambda: None
        added = []
        win.resultsList = type('Grid', (), {'addItems': lambda grid, items: added.extend(items)})()
        win.createListItem = lambda item, artType: (item, artType)
        win.showHubs([self.Hub(t) for t in ('movie', 'actor', 'show', 'director', 'genre', 'track')])
        return added, win.props['no.results']

    def test_people_shows_actors_and_directors(self):
        self.assertEqual(([('actor', 'circle'), ('director', 'circle')], ''), self.shown('people'))

    def test_all_shows_everything_in_the_rows_order(self):
        items, _ = self.shown('all')
        self.assertEqual(['movie', 'actor', 'show', 'director', 'track'], [i[0] for i in items])

    def test_each_item_is_drawn_as_its_rows_art(self):
        items, _ = self.shown('all')
        self.assertEqual(['poster', 'circle', 'poster', 'circle', 'square'], [i[1] for i in items])

    def test_genres_arent_shown(self):
        items, _ = self.shown('all')
        self.assertNotIn('genre', [i[0] for i in items])

    def test_nothing_of_a_type_says_so(self):
        self.assertEqual(([], '1'), self.shown('photo'))

    def test_people_has_its_button(self):
        self.assertEqual('people', search.SearchWindow.SECTION_BUTTONS[916])


class TypeLineTest(KodiTestCase):
    """The line under a result's title: its type, and what tells it apart (typeLine())."""

    class Item(object):
        def __init__(self, type_, reasonTitle='', **fields):
            self.TYPE = type_
            self.reasonTitle = reasonTitle
            self.fields = fields

        def get(self, key, default=None):
            return self.fields.get(key, default)

    def line(self, *args, **kwargs):
        return searchWindow().typeLine(self.Item(*args, **kwargs))

    def test_a_film_has_its_year(self):
        self.assertEqual(u'1979 · Movie', self.line('movie', year='1979'))

    def test_an_episode_its_number(self):
        self.assertEqual(u'S2 E4 · Episode',
                         self.line('episode', parentIndex='2', index='4', grandparentTitle='Reacher'))

    def test_an_episodes_show_has_its_own_line(self):
        win = searchWindow()
        self.assertEqual('Reacher', win.subtitle(self.Item('episode', grandparentTitle='Reacher')))
        self.assertEqual('', win.subtitle(self.Item('season', parentTitle='Reacher')))

    def test_an_album_its_artist(self):
        self.assertEqual(u'Bowie · Album', self.line('album', parentTitle='Bowie'))

    def test_a_person_just_their_type(self):
        # what Plex says they were found through is the library, which the line below has
        self.assertEqual(u'Actor', self.line('Role', reasonTitle='Films'))
        self.assertEqual(u'Director', self.line('Director', reasonTitle='Films'))

    def test_nothing_to_add_just_the_type(self):
        self.assertEqual(u'Movie', self.line('movie'))
        self.assertEqual(u'Photo', self.line('photo'))


class TypeButtonsShowTest(KodiTestCase):
    """The type buttons show once a search has found something it can show (has.results), whatever
    the type chosen, and go with the history."""

    def window(self, section='all'):
        win = searchWindow()
        win.props = {'search.section': section}
        win.getProperty = lambda key: win.props.get(key, '')
        win.setProperty = win.props.__setitem__
        win.showHubs = lambda rows: None
        win._restoreFocus = lambda: None
        return win

    def test_results_show_them(self):
        win = self.window()
        win.showResults('alien', [TypeButtonsTest.Hub('movie')], [])
        self.assertEqual('1', win.props['has.results'])

    def test_even_when_the_type_chosen_has_none(self):
        win = self.window('people')
        win.showResults('alien', [TypeButtonsTest.Hub('movie')], [])
        self.assertEqual('1', win.props['has.results'])

    def test_no_results_none(self):
        win = self.window()
        win.showResults('zzz', [], [])
        self.assertEqual('', win.props['has.results'])

    def test_the_history_hides_them(self):
        win = self.window()
        win.props['has.results'] = '1'
        win.clearHubs = lambda: None
        win.loadSearchHistory = lambda: []
        win.showSearchHistory()
        self.assertEqual('', win.props['has.results'])


class TypingTest(KodiTestCase):
    """A key typed off the entry box types into it only from the left-hand column (typesHere(),
    SafeControlEdit's grab_focus): anywhere else it's what Kodi maps it to - 'c' the context menu
    on a result (the user, 2026-10-07)."""

    C_KEY = 61507  # 'c', as Kodi's button code

    class Action(object):
        def __init__(self, action_id, button_code):
            self._id, self._code = action_id, button_code

        def getId(self):
            return self._id

        def getButtonCode(self):
            return self._code

    class Label(object):
        def setLabel(self, label):
            pass

    def typed(self, focus):
        win = searchWindow()
        win.focus = focus
        win.getFocusId = lambda: win.focus
        win.setFocusId = lambda controlID: setattr(win, 'focus', controlID)
        passed = []
        edit = kodigui.SafeControlEdit.__new__(kodigui.SafeControlEdit)
        edit.controlID, edit._win, edit._keyCallback = search.SearchWindow.EDIT_CONTROL_ID, win, None
        edit.grabFocus, edit._text, edit._compatibleMode = win.typesHere, '', True
        edit._labelControl = self.Label()
        edit._winOnAction = passed.append
        edit.onAction(self.Action(117, self.C_KEY))
        return edit.getText(), win.focus, passed

    def test_from_the_keyboard_it_types(self):
        text, focus, passed = self.typed(1001)
        self.assertEqual(('c', search.SearchWindow.EDIT_CONTROL_ID, []), (text, focus, passed))

    def test_from_the_left_hand_column_it_types(self):
        for controlID in (998, 1036, 951, 953, search.SearchWindow.HISTORY_LIST_ID):
            self.assertEqual('c', self.typed(controlID)[0], controlID)

    def test_from_a_result_it_is_the_context_menu(self):
        text, focus, passed = self.typed(search.SearchWindow.RESULTS_ID)
        self.assertEqual(('', search.SearchWindow.RESULTS_ID), (text, focus))
        self.assertEqual([117], [action.getId() for action in passed])

    def test_from_a_type_button_or_the_sidebar_it_does_not_type(self):
        for controlID in (911, 916, search.SearchWindow.SECTION_LIST_ID):
            self.assertEqual('', self.typed(controlID)[0], controlID)


class CaretTest(KodiTestCase):
    """The entry box's caret shows only where typing goes into it (SafeControlEdit._showsCursor(),
    typesHere()), in the sidebar's orange."""

    def label(self, focus):
        win = searchWindow()
        win.getFocusId = lambda: focus
        shown = []
        label = TypingTest.Label()
        label.setLabel = shown.append
        edit = kodigui.SafeControlEdit.__new__(kodigui.SafeControlEdit)
        edit.controlID, edit._win, edit._labelControl = search.SearchWindow.EDIT_CONTROL_ID, win, label
        edit.grabFocus, edit._text, edit._compatibleMode = win.typesHere, 'alien', True
        edit.updateLabel()
        return shown[-1]

    def test_on_the_keyboard_the_caret(self):
        self.assertEqual(u'alien[COLOR FFE5A00D]|[/COLOR]', self.label(1001))

    def test_in_the_field_the_caret(self):
        self.assertTrue(self.label(search.SearchWindow.EDIT_CONTROL_ID).endswith('|[/COLOR]'))

    def test_on_a_result_or_the_sidebar_none(self):
        self.assertEqual(u'alien', self.label(search.SearchWindow.RESULTS_ID))
        self.assertEqual(u'alien', self.label(911))
        self.assertEqual(u'alien', self.label(search.SearchWindow.SECTION_LIST_ID))


class ArtSizeTest(KodiTestCase):
    """Each result's art is asked for at its size on the card, through the poster resolution
    setting (util.scaleResolution()) - it was 256x256 covered for every shape, so an episode's still
    came at about 455x256 for a 133x75 card, shrunk 3.4x on a 1080p interface (the user,
    2026-10-07)."""

    class Thumb(object):
        def __init__(self, asked):
            self.asked = asked

        def asTranscodedImageURL(self, w, h):
            self.asked.append((w, h))
            return 'http://art/{0}x{1}'.format(w, h)

    class Item(object):
        def __init__(self, type_, asked):
            self.TYPE = type_
            self.title = 'Thing'
            self.thumb = ArtSizeTest.Thumb(asked)

        def get(self, key, default=''):
            return self.thumb if key == 'thumb' else default

    def asked(self, type_, artType, perc):
        win = searchWindow()
        asked = []
        win.subtitle = win.typeLine = lambda item: ''
        with mock.patch.object(search.util.addonSettings, 'posterResolutionScalePerc', perc), \
                mock.patch.object(search, 'placesLine', lambda item: ''):
            win.createListItem(self.Item(type_, asked), artType)
        return asked[0]

    def test_at_100_the_cards_own_size(self):
        self.assertEqual((133, 75), self.asked('episode', 'ar16x9', 100))
        self.assertEqual((133, 200), self.asked('movie', 'poster', 100))
        self.assertEqual((133, 133), self.asked('album', 'square', 100))

    def test_at_400_twice_it(self):
        self.assertEqual((266, 150), self.asked('episode', 'ar16x9', 400))


class SupersededTest(KodiTestCase):
    """A search the text has moved on from by the time it's answered isn't shown, and skips its
    copies' lookup (the user, 2026-10-07): with a remote, typing "the" searched "th" on the way."""

    def window(self, query):
        import threading
        win = searchWindow()
        win._hostRef = None
        win._resultsLock = threading.Lock()
        win._query = query
        win.posted = []
        win._post = lambda name, fn, args: win.posted.append(name)
        return win

    def test_typed_on_meanwhile_not_shown(self):
        win = self.window('th')

        def searchServers(query, servers, positions, superseded):
            win._query = 'the'  # a key pressed while the servers answered
            return [], []
        with mock.patch.object(search, 'searchServers', searchServers), \
                mock.patch.object(search, 'searchedServers', lambda: []), \
                mock.patch.object(search.sidebar_model, 'loadNavSettings', lambda: None), \
                mock.patch.object(search.sidebar_model, 'entryPositions', lambda nav: {}):
            win._search('th')
        self.assertEqual(['searching'], win.posted)

    def test_still_wanted_shown(self):
        win = self.window('the')
        with mock.patch.object(search, 'searchServers', lambda q, s, p, superseded: ([], [])), \
                mock.patch.object(search, 'searchedServers', lambda: []), \
                mock.patch.object(search.sidebar_model, 'loadNavSettings', lambda: None), \
                mock.patch.object(search.sidebar_model, 'entryPositions', lambda nav: {}):
            win._search('the')
        self.assertEqual(['searching', 'search results'], win.posted)


class TypeButtonNarrowsTest(KodiTestCase):
    """A type button narrows the results already shown, at once, rather than searching the servers
    again a second later (the user, 2026-10-07)."""

    def window(self, text, shown):
        win = searchWindow(text=text)
        win.props = {'search.section': 'all'}
        win.getProperty = lambda key: win.props.get(key, '')
        win.setProperty = win.props.__setitem__
        win.drawn, win.searched = [], []
        win.showHubs = win.drawn.append
        win.updateResults = lambda delay=1: win.searched.append(delay)
        win._shownRows = shown
        return win

    def test_the_rows_shown_narrowed_without_a_search(self):
        rows = ['movie row']
        win = self.window('alien', ('alien', rows))
        win.typeClicked(912)
        self.assertEqual(('movie', [rows], []), (win.props['search.section'], win.drawn, win.searched))

    def test_typed_on_since_a_search_now(self):
        win = self.window('aliens', ('alien', ['movie row']))
        win.typeClicked(912)
        self.assertEqual(([], [0]), (win.drawn, win.searched))

    def test_the_same_button_nothing(self):
        win = self.window('alien', ('alien', ['movie row']))
        win.typeClicked(911)
        self.assertEqual(([], []), (win.drawn, win.searched))


class HistoryPickTest(KodiTestCase):
    def test_a_history_entry_is_searched_at_once(self):
        win = searchWindow(text='')
        win.historyList = FakeManagedControlList(2050, FakeManagedListItem(search.HistoryItem('alien')))
        searched = []
        win.updateResults = lambda delay=1: searched.append(delay)
        win.historyItemClicked()
        self.assertEqual([0], searched)


class HoldSearchTest(KodiTestCase):
    """Moving on the keyboard while a search waits out the typing waits it out again; moving off it
    runs it now; with nothing waiting, moving does nothing (_holdSearch(), the user, 2026-10-07)."""

    def window(self, waiting):
        import threading
        import time
        win = searchWindow()
        win._resultsLock = threading.Lock()
        win.resultsThread = 'running' if waiting is not None else None
        win.updateResultsTimeout = time.time() + waiting if waiting is not None else 0
        return win

    def test_moving_between_keys_waits_again(self):
        import time
        win = self.window(0.2)
        win._holdSearch(1005)
        self.assertGreater(win.updateResultsTimeout, time.time() + 0.8)

    def test_delete_and_the_entry_box_count_as_the_keyboard(self):
        import time
        for controlID in (951, 953, search.SearchWindow.EDIT_CONTROL_ID):
            win = self.window(0.2)
            win._holdSearch(controlID)
            self.assertGreater(win.updateResultsTimeout, time.time() + 0.8, controlID)

    def test_moving_off_it_runs_it_now(self):
        import time
        for controlID in (search.SearchWindow.RESULTS_ID, 911, search.SearchWindow.HISTORY_LIST_ID, 998):
            win = self.window(0.8)
            win._holdSearch(controlID)
            self.assertLessEqual(win.updateResultsTimeout, time.time(), controlID)

    def test_nothing_waiting_nothing_done(self):
        win = self.window(None)
        win._holdSearch(1005)
        self.assertEqual(0, win.updateResultsTimeout)

    def test_a_search_already_out_isnt_touched(self):
        import time
        win = self.window(-0.5)  # its wait is over: the servers are being asked
        before = win.updateResultsTimeout
        win._holdSearch(1005)
        self.assertEqual(before, win.updateResultsTimeout)


class BackDeletesTest(KodiTestCase):
    """Back on the left-hand column takes a letter off what's typed, until there's none; then it's
    Back (the user, 2026-10-07)."""

    class Action(object):
        def __init__(self, action_id):
            self._id = action_id

        def getId(self):
            return self._id

        def __eq__(self, other):
            return self._id == other

        def __hash__(self):
            return hash(self._id)

    def window(self, text, focus):
        win = searchWindow(text=text)
        win.getFocusId = lambda: focus
        win.ignoresInput = lambda: False
        win.deleted, win.routed = [], []
        win.deleteClicked = lambda: win.deleted.append(True)
        win.routeActionToHost = lambda action: win.routed.append(action) or True
        return win

    def back(self, text, focus):
        win = self.window(text, focus)
        win.onAction(self.Action(search.xbmcgui.ACTION_NAV_BACK))
        return len(win.deleted), len(win.routed)

    def test_on_the_keyboard_it_deletes(self):
        for controlID in (1001, 1036, 951, 953, 998, search.SearchWindow.HISTORY_LIST_ID):
            self.assertEqual((1, 0), self.back('alien', controlID), controlID)

    def test_with_nothing_typed_its_back(self):
        self.assertEqual((0, 1), self.back('', 1001))

    def test_off_the_left_hand_column_its_back(self):
        self.assertEqual((0, 1), self.back('alien', search.SearchWindow.SECTION_LIST_ID))

    def test_on_a_type_button_to_the_keyboards_a(self):
        for controlID in (911, 916):
            win = self.window('alien', controlID)
            win.useKodiKbd = False
            focused = []
            win.setFocusId = focused.append
            win.onAction(self.Action(search.xbmcgui.ACTION_NAV_BACK))
            self.assertEqual(([search.SearchWindow.BUTTON_A_ID], 0, 0), (focused, len(win.deleted), len(win.routed)))

    def onResults(self, pos, kodiKbd=False):
        win = self.window('alien', search.SearchWindow.RESULTS_ID)
        win.useKodiKbd = kodiKbd
        selected, focused = [], []
        win.resultsList = FakeManagedControlList(search.SearchWindow.RESULTS_ID, selected_pos=pos)
        win.resultsList.setSelectedItemByPos = selected.append
        win.setFocusId = focused.append
        win.onAction(self.Action(search.xbmcgui.ACTION_NAV_BACK))
        return selected, focused, len(win.deleted), len(win.routed)

    def test_on_a_result_past_the_first_to_the_first(self):
        self.assertEqual(([0], [], 0, 0), self.onResults(7))

    def test_on_the_first_to_the_keyboards_a(self):
        self.assertEqual(([], [search.SearchWindow.BUTTON_A_ID], 0, 0), self.onResults(0))

    def test_with_kodis_keyboard_to_the_entry_box(self):
        self.assertEqual(([], [search.SearchWindow.EDIT_CONTROL_ID], 0, 0), self.onResults(0, kodiKbd=True))

    def test_in_the_entry_box_too(self):
        win = self.window('alien', search.SearchWindow.EDIT_CONTROL_ID)
        win.updateFromEdit(search.xbmcgui.ACTION_NAV_BACK, 'alien', 'alien')
        self.assertEqual((1, 0), (len(win.deleted), len(win.routed)))
        win = self.window('', search.SearchWindow.EDIT_CONTROL_ID)
        win.updateFromEdit(search.xbmcgui.ACTION_NAV_BACK, '', '')
        self.assertEqual((0, 1), (len(win.deleted), len(win.routed)))
