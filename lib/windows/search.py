from __future__ import absolute_import

import json
import re
import threading
import time
import unicodedata

from kodi_six import xbmcgui, xbmc
from plexnet import plexapp, plexobjects, util as plexnetUtil

from lib import util
from lib.util import T
from lib.kodijsonrpc import rpc
from . import dropdown
from . import kodigui
from . import opener
from . import optionsdialog
from . import section_ids
from . import sidebar_model
from . import windowutils


class HistoryItem(object):
    TYPE = 'history'

    def __init__(self, query, is_clear=False):
        self.query = query
        self.title = query
        self.is_clear = is_clear


class SearchWindow(kodigui.ControlledWindow, windowutils.UtilMixin, windowutils.SidebarMixin):
    """Search, a sidebar destination like a library or Watchlist (the user, 2026-10-06), shown by
    the host (LibraryWindow._openSearch()) with the sidebar, its Search entry the active one.
    Opened from the sidebar, it starts fresh: an empty query, with the history. Back goes to Home's
    root, as from any section; Back from a result opened here rebuilds it from the back stack -
    the query, the type button and the result focused (restoreState())."""
    xmlFile = 'script-plex-search.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    LETTERS = 'abcdefghijklmnopqrstuvwxyz0123456789 '
    # The type buttons: 911-916, clear of the sidebar's user menu group (901, SidebarMixin.
    # USER_MENU_GROUP_ID), which the user menu resizes by id
    SECTION_BUTTONS = {
        911: 'all',
        912: 'movie',
        913: 'show',
        914: 'artist',
        915: 'photo',
        916: 'people',
    }

    EDIT_CONTROL_ID = 650
    EDIT_LABEL_ID = 651
    # the entry box's tile; with one server it, the field and its text run the keyboard's width
    ENTRY_BOX_ID = 652
    ENTRY_FULL_WIDTH = 414
    BUTTON_A_ID = 1001
    PLAYER_STATUS_BUTTON_ID = 204
    # The results: one grid, three across (script-plex-search.xml.tpl)
    RESULTS_ID = 2100
    HISTORY_LIST_ID = 2050
    MAX_HISTORY_ITEMS = 10
    # The history's group, below Delete/Space/Clear. With Kodi's keyboard there's no keyboard or
    # row above it: it starts where the keyboard would, and runs to 60 above the screen's bottom.
    HISTORY_GROUP_ID = 2040
    HISTORY_KODI_KBD_Y = 144
    HISTORY_KODI_KBD_HEIGHT = 876

    HUBMAP = {
        'track': {'type': 'square'},
        'episode': {'type': 'ar16x9'},
        'movie': {'type': 'poster'},
        'show': {'type': 'poster'},
        'artist': {'type': 'square'},
        'album': {'type': 'square'},
        'photoalbum': {'type': 'square'},
        'photo': {'type': 'square'},
        'actor': {'type': 'circle'},
        'director': {'type': 'circle'},
        # no 'genre': a genre is a library's, reached from it (the user, 2026-10-06)
        'playlist': {'type': 'square'},
        # the collections the search's tags are (resolveCollections()) - the user, 2026-10-07
        'collection': {'type': 'poster'},
    }

    def __init__(self, *args, **kwargs):
        kodigui.ControlledWindow.__init__(self, *args, **kwargs)
        windowutils.UtilMixin.__init__(self)
        # A search to run straight away, its type button and the result to focus in it: Back to a
        # search from a result opened from it (restoreState())
        self.initialQuery = kwargs.get('query')
        self.initialSection = kwargs.get('searchSection') or 'all'
        self.initialFocus = kwargs.get('focus')
        # The results thread (updateResults()): the query it searches next, and when
        self._resultsLock = threading.Lock()
        self.resultsThread = None
        self.updateResultsTimeout = 0
        self._query = ''
        self.useKodiKbd = util.getSetting('search_use_kodi_kbd')
        self.lastFocusID = None
        # The host's sidebar list, handed over by LibraryWindow._setupCurrent() before
        # onFirstInit(); None builds one of its own (as PersonWindow)
        self.sectionList = None

    def paintInitialBackground(self):
        """No art: the neutral colour panel (kodigui's setNeutralPanel()), as the person screen."""
        super(SearchWindow, self).paintInitialBackground()
        self.setNeutralPanel()

    def onFirstInit(self):
        self.resultsList = kodigui.ManagedControlList(self, self.RESULTS_ID, 12)
        self.historyList = kodigui.ManagedControlList(self, self.HISTORY_LIST_ID, self.MAX_HISTORY_ITEMS + 1)

        if self.sectionList is None:
            self.sectionList = kodigui.ManagedControlList(self, self.SECTION_LIST_ID, 15)
            self.buildSectionList()
        else:
            self.sectionList.newControl(self)
            host = self.hostedBy()
            if host is not None:
                # Search's entry is the active one whenever it shows: Back to it through a
                # library's grid too (a genre clicked on a result's screen,
                # LibraryWindow.swapToSection()), which moved the marker
                host.updateActiveSectionMarker(windowutils.SEARCH_ENTRY)
        self._selectActiveSection()
        self.displayServerAndUser()

        self.edit = kodigui.SafeControlEdit(self.EDIT_CONTROL_ID, self.EDIT_LABEL_ID, self,
                                            key_callback=self.updateFromEdit, grab_focus=self.typesHere)
        self.edit.setCompatibleMode(rpc.Application.GetProperties(properties=["version"])["version"]["major"] < 17)
        if self.useKodiKbd:
            self.setProperty('hide.kbd', '1')
            history = self.getControl(self.HISTORY_GROUP_ID)
            history.setPosition(history.getPosition()[0], util.vscale(self.HISTORY_KODI_KBD_Y, r=0))
            self.getControl(self.HISTORY_LIST_ID).setHeight(util.vscale(self.HISTORY_KODI_KBD_HEIGHT, r=0))
        self.setProperty('search.section', self.initialSection)
        # the servers button (chooseServers()), right of the entry box
        multi = len(plexapp.SERVERMANAGER.getServers()) > 1
        self.setProperty('search.multi', multi and '1' or '')
        if not multi:
            # no servers button: the entry box takes its place, the keyboard's full width
            self.getControl(self.ENTRY_BOX_ID).setWidth(self.ENTRY_FULL_WIDTH)
            self.getControl(self.EDIT_CONTROL_ID).setWidth(self.ENTRY_FULL_WIDTH)
            self.getControl(self.EDIT_LABEL_ID).setWidth(self.ENTRY_FULL_WIDTH - 60)
        if self.initialQuery:
            # Back to the results: focus moves on to the result once they're in (_restoreFocus())
            self.setFocusId(self.EDIT_CONTROL_ID if self.useKodiKbd else self.BUTTON_A_ID)
            self.edit.setText(self.initialQuery)
            self.updateResults(delay=0)
        else:
            if self.useKodiKbd:
                self.setFocusId(self.EDIT_CONTROL_ID)
                xbmc.executebuiltin('Action(Select,{0})'.format(self._winID))
            else:
                self.setFocusId(self.BUTTON_A_ID)
            self.showSearchHistory()

    def onReInit(self):
        # Shown again after a photo, track or clip opened from here (opener.handleOpen() blocks):
        # the results again, or the history.
        if self.edit.getText():
            self.updateResults()
        else:
            self.showSearchHistory()

    def restoreState(self):
        """What a back-stack entry keeps of this screen (LibraryWindow.
        _captureHostedShellRestoreState()), as the constructor's kwargs: the query, the type button,
        and the result focused - its place in the grid, or None away from the results."""
        focus = None
        if self.getFocusId() == self.RESULTS_ID:
            focus = self.resultsList.getSelectedPos()
        return {'query': self.edit.getText(), 'searchSection': self.getProperty('search.section') or 'all',
                'focus': focus}

    def onAction(self, action):
        # Back on the left-hand column takes a letter off what's typed (_backDeletes()); on the
        # results it goes to the first, then to the keyboard (_backFromResults()); on a type button
        # straight to the keyboard
        if action == xbmcgui.ACTION_NAV_BACK and not self.ignoresInput():
            focus = self.getFocusId()
            if self._backDeletes(focus):
                self.deleteClicked()
                return
            if focus == self.RESULTS_ID:
                self._backFromResults()
                return
            if focus in self.SECTION_BUTTONS:
                self._toKeyboard()
                return
        # Hosted: the host sees the action first (kodigui.BaseWindow.routeActionToHost()), Back
        # included - it goes through the chain, to Home's root from here.
        if self.routeActionToHost(action):
            return
        try:
            if action == xbmcgui.ACTION_CONTEXT_MENU and self.getFocusId() == self.RESULTS_ID:
                if self.openFrom():
                    return
        except Exception:
            util.ERROR()
        kodigui.ControlledWindow.onAction(self, action)

    SERVERS_BUTTON_ID = 998

    def onClick(self, controlID):
        # Not live on its host yet, or any more (kodigui.BaseWindow.ignoresInput()).
        # Hosted: the host handles the sidebar's clicks (kodigui.BaseWindow.routeClickToHost()).
        if self.routeClickToHost(controlID):
            return
        if controlID == self.SECTION_LIST_ID:
            self.sectionClicked()
        elif controlID == self.PLAYER_STATUS_BUTTON_ID:
            self.showAudioPlayer()
        elif controlID == self.SERVERS_BUTTON_ID:
            self.chooseServers()
        elif 1000 < controlID < 1037:
            self.letterClicked(controlID)
        elif controlID in self.SECTION_BUTTONS:
            self.typeClicked(controlID)
        elif controlID == 951:
            self.deleteClicked()
        elif controlID == 952:
            self.letterClicked(1037)
        elif controlID == 953:
            self.clearClicked()
        elif controlID == self.RESULTS_ID:
            self.resultClicked()
        elif controlID == self.HISTORY_LIST_ID:
            self.historyItemClicked()

    def onFocus(self, controlID):
        # Not live on its host yet, or any more (kodigui.BaseWindow.ignoresInput()).
        if self.ignoresInput():
            return
        self.reselectActiveSection(controlID, self.lastFocusID)
        self.lastFocusID = controlID
        # the caret only where typing goes into the entry box (typesHere())
        edit = getattr(self, 'edit', None)
        if edit is not None:
            edit.updateLabel()
        self._holdSearch(controlID)

    def _holdSearch(self, controlID):
        """While a search waits out the typing (updateResults()), moving on the keyboard - to the
        next letter, most likely - waits it out again, and moving off it runs it now: done typing
        (the user, 2026-10-07). With a remote it used to search each part-word on the way ("t",
        "th", "the"). The entry box counts as the keyboard: a key typed off it moves the focus
        there. Moving with no search waiting does nothing."""
        lock = getattr(self, '_resultsLock', None)
        if lock is None:
            return
        with lock:
            now = time.time()
            if self.resultsThread is None or self.updateResultsTimeout <= now:
                return
            onKeyboard = 1000 < controlID < 1037 or controlID in (951, 952, 953, self.EDIT_CONTROL_ID)
            self.updateResultsTimeout = now + self.typingDelay() if onKeyboard else now

    def sidebarActiveSection(self, entries):
        """The Search entry (windowutils.SEARCH_ENTRY), for a sidebar this screen builds itself."""
        return windowutils.SEARCH_ENTRY

    def typesHere(self, controlID):
        """Whether a key typed with controlID focused goes into the entry box (SafeControlEdit's
        grab_focus): from the left-hand column only - the servers button, the keyboard, Delete/
        Space/Clear and the history. Anywhere else a key is what Kodi maps it to, 'c' the context
        menu on a result (the user, 2026-10-07): it used to type from anywhere."""
        return (controlID == self.SERVERS_BUTTON_ID or 1000 < controlID < 1037
                or controlID in (951, 952, 953, self.HISTORY_LIST_ID))

    def _backFromResults(self):
        """Back on the results: to the first, or from the first to the keyboard's A - the entry box
        with Kodi's keyboard - where Back then takes letters off (the user, 2026-10-07)."""
        if self.resultsList.getSelectedPos():
            self.resultsList.setSelectedItemByPos(0)
        else:
            self._toKeyboard()

    def _toKeyboard(self):
        self.setFocusId(self.EDIT_CONTROL_ID if self.useKodiKbd else self.BUTTON_A_ID)

    def _backDeletes(self, controlID):
        """Whether Back with controlID focused takes a letter off what's typed, as Delete does: on
        the left-hand column - the entry box, the keyboard, Delete/Space/Clear, the servers button
        and the history - while there's any (the user, 2026-10-07). Once it's empty, Back is Back."""
        edit = getattr(self, 'edit', None)
        return (edit is not None and bool(edit.getText())
                and (controlID == self.EDIT_CONTROL_ID or self.typesHere(controlID)))

    def updateFromEdit(self, actionID, oldVal, newVal):
        # The entry box focused: every action comes here (SafeControlEdit.processAction()), not to
        # onAction(). A keyboard's Backspace is the field's own, deleting already; this is a
        # remote's Back.
        if actionID == xbmcgui.ACTION_NAV_BACK and self._backDeletes(self.EDIT_CONTROL_ID):
            self.deleteClicked()
            return
        if actionID in (xbmcgui.ACTION_PREVIOUS_MENU, xbmcgui.ACTION_NAV_BACK):
            # leaving, as Back does anywhere else on this screen: through the host
            self.routeActionToHost(actionID)
            return

        self.updateQuery()

    def updateQuery(self):
        self.updateResults()

    def _gone(self):
        """Closed, or swapped out by its host: nothing more is shown here."""
        return self._closing or (self._hostRef is not None and self.hostedBy() is None)

    # How long typing has to stop before what's typed is searched for (updateResults()), unless
    # the search_typing_delay setting says otherwise (Settings > Main, the user, 2026-10-07)
    TYPING_DELAY = 1.0

    def typingDelay(self):
        """The search_typing_delay setting, in seconds, read once for this screen."""
        delay = getattr(self, '_typingDelay', None)
        if delay is None:
            try:
                delay = float(util.getSetting('search_typing_delay', self.TYPING_DELAY) or self.TYPING_DELAY)
            except (TypeError, ValueError):
                delay = self.TYPING_DELAY
            self._typingDelay = delay
        return delay

    def updateResults(self, delay=None):
        """Search for what's typed, delay seconds after the last key - the setting's
        (typingDelay()) when not given - on the results thread (_updateResults()). The query is
        read here, on the main thread."""
        if delay is None:
            delay = self.typingDelay()
        query = self.edit.getText()
        with self._resultsLock:
            self._query = query
            self.updateResultsTimeout = time.time() + delay
            if self.resultsThread is None:
                self.resultsThread = threading.Thread(target=self._updateResults, name='search.update')
                self.resultsThread.daemon = True
                self.resultsThread.start()

    def _updateResults(self):
        """The results thread: waits out the typing, searches, and goes again if the query changed
        meanwhile. It used to end after one search, and a key pressed during it went unsearched
        until the next."""
        while True:
            while time.time() < self.updateResultsTimeout:
                if util.MONITOR.waitForAbort(0.1) or self._gone():
                    with self._resultsLock:
                        self.resultsThread = None
                    return
            with self._resultsLock:
                query = self._query
                timeout = self.updateResultsTimeout
            try:
                self._search(query)
            except Exception:
                util.ERROR()
            with self._resultsLock:
                if self._gone() or (self._query == query and self.updateResultsTimeout == timeout):
                    self.resultsThread = None
                    return

    def _search(self, query):
        if self._gone():
            return
        if not query:
            self._post('search history', self.showResults, (query, None, None))
            return
        self._post('searching', self.setProperty, ('searching', '1'))
        positions = sidebar_model.entryPositions(sidebar_model.loadNavSettings())
        superseded = lambda: self._superseded(query)  # noqa: E731
        rows, missing = searchServers(query, searchedServers(), positions, superseded)
        if rows is None or superseded():
            # typed on meanwhile - a key pressed while the remote moved to the next: not shown,
            # _updateResults() searches the new text next (the user, 2026-10-07)
            return
        self._post('search results', self.showResults, (query, rows, missing))

    def _superseded(self, query):
        """Whether the text has changed since query was searched for."""
        with self._resultsLock:
            return self._query != query

    def _post(self, name, fn, args):
        """Run fn(*args) on the main thread, through the host's UI queue (MultiWindow.postUI()), if
        this screen is still the one showing by then. The results thread used to write the lists
        itself, which a screen swapped out meanwhile would have had freed. Not hosted: at once."""
        if self._hostRef is None:
            if not self._closing:
                fn(*args)
            return
        host = self.hostedBy()
        if host is None:
            return

        def run():
            if not self._gone():
                fn(*args)
        host.postUI(name, run)

    def showResults(self, query, rows, missing):
        """The results thread's answer for query (_search()): its rows, or the history for an empty
        query (rows None)."""
        self.setProperty('searching', '')
        # kept for the type buttons, which narrow these without searching again (typeClicked())
        self._shownRows = (query, rows)
        if rows is None:
            self.setProperty('search.note', '')
            self.showSearchHistory()
            return
        self.showHubs(rows)
        # the type buttons show once the search has found anything it can show, whichever type is
        # chosen - a type with nothing for this query can still be changed
        self.setProperty('has.results', any(h.size.asInt() > 0 and h.type in self.HUBMAP for h in rows) and '1' or '')
        self._restoreFocus()
        # the results are short of a server's: say whose
        self.setProperty('search.note', missing and T(35129, "{0} isn't responding").format(', '.join(missing)) or '')

    def _restoreFocus(self):
        """Back at the results from a result opened from them: focus on that result again, if the
        search still has it there."""
        pos, self.initialFocus = self.initialFocus, None
        if pos is None or not isinstance(pos, int):
            return
        if 0 <= pos < self.resultsList.size():
            self.setFocusId(self.RESULTS_ID)
            self.resultsList.selectItem(pos)

    # a server's row in chooseServers(): searched, or not
    SERVER_ON = 'script.plex/indicators/visible.png'
    SERVER_OFF = 'script.plex/indicators/hidden.png'

    def chooseServers(self):
        """Which of the account's servers a search asks (the user, 2026-10-05): a card per server,
        its toggle on the right. At least one stays on. Saved for the account; the search runs
        again with the new choice."""
        self._serversChanged = False
        dropdown.showDropdown(
            self._serverOptions(),
            pos=(660, 200),
            close_direction='none',
            set_dropdown_prop=False,
            with_indicator=True,
            header=T(35140, 'Servers to search'),
            align_items='left',
            close_only_with_back=True,
            options_callback=self._onServerToggle,
            dialog_class=dropdown.CardListDialog,
            columns=(dropdown.CardListDialog.PIN,),
        )
        if self._serversChanged and self.edit.getText():
            self.updateResults(delay=0)

    def _serverOptions(self):
        chosen = set(s.uuid for s in searchedServers())
        options = []
        for server in accountServers():
            on = server.uuid in chosen
            note = (server.offline or server.gone) and T(35129, "{0} isn't responding").format(server.name) or ''
            options.append({'key': 'server', 'uuid': server.uuid, 'display': server.name,
                            'indicator': self.SERVER_ON if on else self.SERVER_OFF, 'indicator_dim': not on,
                            'properties': {'buttons': '1', 'single': '1', 'subtitle': note}})
        return options

    def _onServerToggle(self, optionsList, mli):
        choice = mli.dataSource
        if not choice or choice.get('key') != 'server':
            return
        chosen = [s.uuid for s in searchedServers()]
        if choice['uuid'] in chosen:
            if len(chosen) == 1:
                return  # one at least
            chosen.remove(choice['uuid'])
        else:
            chosen.append(choice['uuid'])
        saveSearchedServers(chosen)
        self._serversChanged = True
        return ('rebuild', self._serverOptions(), optionsList.getSelectedPos())

    def typeClicked(self, controlID):
        """A type button (All, Movies, Shows, Music, Photos). Not sectionClicked(), which is the
        sidebar's (windowutils.SidebarMixin)."""
        section = self.SECTION_BUTTONS[controlID]
        old = self.getProperty('search.section')
        self.setProperty('search.section', section)
        if old == section:
            return
        # the results shown are the whole search's, every type: narrowed again at once (showHubs()),
        # where it used to search the servers again a second later (the user, 2026-10-07). Only if
        # they're for what's typed now - otherwise a search for it is due, and takes the new type.
        query, rows = getattr(self, '_shownRows', (None, None))
        if rows is not None and query == self.edit.getText():
            self.showHubs(rows)
        else:
            self.updateResults(delay=0)

    def letterClicked(self, controlID):
        letter = self.LETTERS[controlID - 1001]
        self.edit.append(letter)
        self.updateQuery()

    def deleteClicked(self):
        self.edit.delete()
        self.updateQuery()

    def clearClicked(self):
        self.edit.setText('')
        self.updateQuery()

    def _historyKey(self):
        """The account's search history - a search covers every server now (it was the selected
        server's, 'search.history.<uuid[-8:]>.<account>', loadSearchHistory() takes it over)."""
        return 'search.history.{0}'.format(plexapp.ACCOUNT.ID)

    def _oldHistoryKey(self):
        server = section_ids.legacyServer()
        return server and 'search.history.{0}.{1}'.format(server.uuid[-8:], plexapp.ACCOUNT.ID)

    def loadSearchHistory(self):
        key = self._historyKey()
        try:
            stored = util.getSetting(key, '')
            if not stored and self._oldHistoryKey():
                # the selected server's history becomes the account's
                stored = util.getSetting(self._oldHistoryKey(), '') or '[]'
                util.setSetting(key, stored)
            return json.loads(stored or '[]')[:self.MAX_HISTORY_ITEMS]
        except Exception:
            util.ERROR()
            return []

    def saveSearchHistory(self, history):
        key = self._historyKey()
        if not key:
            return
        try:
            util.setSetting(key, json.dumps(history[:self.MAX_HISTORY_ITEMS]))
        except Exception:
            util.ERROR()

    def addToHistory(self, title):
        if not title or not title.strip():
            return
        title = title.strip()
        history = self.loadSearchHistory()
        if title in history:
            history.remove(title)
        history.insert(0, title)
        self.saveSearchHistory(history)

    def clearSearchHistory(self):
        key = self._historyKey()
        if key:
            try:
                util.setSetting(key, '[]')
            except Exception:
                util.ERROR()

    def showSearchHistory(self):
        self.clearHubs()
        # no results, so no type buttons
        self.setProperty('has.results', '')
        history = self.loadSearchHistory()
        if not history:
            self.setProperty('show.history', '')
            return
        items = []
        for query in history:
            mli = kodigui.ManagedListItem(query, data_source=HistoryItem(query))
            mli.setProperty('icon', 'script.plex/buttons/search.png')
            items.append(mli)
        clear_label = T(35005, 'Clear search history')
        clear_mli = kodigui.ManagedListItem(clear_label, data_source=HistoryItem(clear_label, is_clear=True))
        clear_mli.setProperty('icon', 'script.plex/indicators/remove.png')
        items.append(clear_mli)
        self.historyList.reset()
        self.historyList.addItems(items)
        self.setProperty('show.history', '1')

    def historyItemClicked(self):
        mli = self.historyList.getSelectedItem()
        if not mli:
            return
        item = mli.dataSource
        if getattr(item, 'is_clear', False):
            button = optionsdialog.show(
                T(35005, 'Clear search history'),
                T(35006, 'Clear all search history?'),
                T(32328, 'Yes'),
                T(32329, 'No'),
            )
            if button == 0:
                self.clearSearchHistory()
                self.showSearchHistory()
            return
        self.edit.setText(item.query)
        # all of it at once: nothing more is coming to wait for (the user, 2026-10-07)
        self.updateResults(delay=0)

    def resultClicked(self, hubItem=None):
        """Open the focused result - the copy dedupeResults() picked, or hubItem (openFrom())."""
        mli = self.resultsList.getSelectedItem()
        if not mli:
            return

        hubItem = hubItem or mli.dataSource
        if hubItem.TYPE == 'playlist' and not hubItem.exists():  # Workaround for server bug
            util.messageDialog('No Access', 'Playlist not accessible by this user.')
            util.DEBUG_LOG('Search: Playlist does not exist - probably wrong user')
            return

        self.addToHistory(self.edit.getText())
        # As from any hosted screen: the host swaps the result's screen in, pushing this one, and
        # Back rebuilds this from the back stack (restoreState()). A photo, track or clip opens
        # over this screen and comes back to it (onReInit()).
        command = opener.open(hubItem, context=self)

        if not hubItem.exists():
            self.resultsList.removeManagedItem(mli)

        self.processCommand(command)

    def openFrom(self):
        """The context menu on a result with more than one copy (dedupeResults()) or version: which
        to open - a row for each version of each copy (the user, 2026-10-07), its library, its
        server on a multi-server account and its quality, the copy then opened with that version
        chosen (chooseVersion()). True if it was one."""
        mli = self.resultsList.getSelectedItem()
        # not for a person: their screen has every server's films whichever copy opens it
        if not mli or mli.dataSource.TYPE in ('Role', 'Director'):
            return False
        entries = openFromEntries(mli.dataSource)
        if len(entries) < 2:
            return False
        multiServer = len(plexapp.SERVERMANAGER.getServers()) > 1
        options = [{'key': i, 'display': copyLabel(copy, multiServer, media)} for i, (copy, media) in enumerate(entries)]
        choice = dropdown.showDropdown(
            options=options,
            pos=(660, 441),
            close_direction='none',
            set_dropdown_prop=False,
            header=T(35151, 'Open from'),
            align_items='left'
        )
        if choice is not None:
            copy, media = entries[choice['key']]
            if media is not None:
                chooseVersion(copy, media)
            self.resultClicked(copy)
        return True

    # A result's type, first on the line under its title (typeLine())
    TYPE_NAMES = {
        'movie': (35144, 'Movie'),
        'show': (32456, 'Show'),
        'season': (35146, 'Season'),
        'episode': (35145, 'Episode'),
        'artist': (32462, 'Artist'),
        'album': (34043, 'Album'),
        'track': (35147, 'Track'),
        'photo': (35148, 'Photo'),
        'photodirectory': (35149, 'Photo album'),
        'playlist': (35150, 'Playlist'),
        'Role': (32473, 'Actor'),
        'Director': (32474, 'Director'),
        'collection': (32382, 'Collection'),
    }

    def typeLine(self, hubItem):
        """The line under a result's title: what tells it apart - a film's or show's year, a
        season's show, an episode's number (its show has its own line, subtitle()), an album's or
        track's artist - then its type. A person just their type: what Plex says they were found
        through (reasonTitle) is only the library, which the line below says (placesLine())."""
        kind = hubItem.TYPE
        name = self.TYPE_NAMES.get(kind)
        parts = []
        if kind in ('movie', 'show'):
            parts.append(hubItem.get('year', ''))
        elif kind == 'season':
            parts.append(hubItem.get('parentTitle', ''))
        elif kind == 'episode':
            season, episode = hubItem.get('parentIndex', ''), hubItem.get('index', '')
            if season and episode:
                parts.append(u'{0} {1}'.format(T(32310, 'S{}').format(season), T(32311, 'E{}').format(episode)))
        elif kind == 'album':
            parts.append(hubItem.get('parentTitle', ''))
        elif kind == 'track':
            parts.append(hubItem.get('grandparentTitle', ''))
        elif kind == 'collection':
            # its library: copies of a collection in two libraries can be different collections
            # (Star Trek's guid on 26 films in Films and on 3 in Movies, live), so never merged
            parts.append(hubItem.get('librarySectionTitle', ''))
        if name:
            parts.append(T(*name))
        return u' \u00b7 '.join(u'{0}'.format(part) for part in parts if part)

    def subtitle(self, hubItem):
        """The line under an episode's title: its show. Nothing for anything else."""
        return hubItem.get('grandparentTitle', '') if hubItem.TYPE == 'episode' else ''

    def createListItem(self, hubItem, artType):
        """A result's grid item: its art drawn as artType (HUBMAP), its title, an episode's show,
        the type line and, on a multi-server account, its server."""
        mli = self._listItem(hubItem, *util.scaleResolution(*self.ART_SIZES.get(artType, self.ART_SIZES['square'])))
        if mli is not None:
            mli.setProperty('art.type', artType)
            mli.setProperty('subtitle', self.subtitle(hubItem))
            mli.setLabel2(self.typeLine(hubItem))
            # the line under the type: where it is - its server on a multi-server account, or for
            # one with copies, the server it opens on and how many others (placesLine())
            mli.setProperty('server.name', placesLine(hubItem))
        return mli

    # Each art shape's size on its card (script-plex-search.xml.tpl, by art.type), asked for at that
    # size through the poster resolution setting (util.scaleResolution()), as the other screens ask.
    # It was 256x256 for every shape, covered (minSize), so an episode's 16:9 still came at about
    # 455x256 for a 133x75 card: shrunk 3.4x by Kodi on a 1080p interface (the AM6B), which left it
    # jagged (the user, 2026-10-07).
    ART_SIZES = {'poster': (133, 200), 'square': (133, 133), 'circle': (133, 133), 'ar16x9': (133, 75)}

    def _listItem(self, hubItem, width, height):
        if hubItem.TYPE in ('Director', 'Role'):
            mli = kodigui.ManagedListItem(
                hubItem.tag, thumbnailImage=hubItem.get('thumb').asTranscodedImageURL(width, height), data_source=hubItem
            )
            mli.setProperty('thumb.fallback', 'script.plex/thumb_fallbacks/role.png')
        else:
            if hubItem.TYPE == 'playlist':
                mli = kodigui.ManagedListItem(hubItem.tag, thumbnailImage=hubItem.get('composite').asTranscodedImageURL(width, height), data_source=hubItem)
                mli.setProperty('thumb.fallback', 'script.plex/thumb_fallbacks/{0}.png'.format(hubItem.playlistType == 'audio' and 'music' or 'movie'))
            elif hubItem.TYPE == 'photodirectory':
                mli = kodigui.ManagedListItem(hubItem.title, thumbnailImage=hubItem.get('composite').asTranscodedImageURL(width, height), data_source=hubItem)
                mli.setProperty('thumb.fallback', 'script.plex/thumb_fallbacks/photo.png')
            else:
                mli = kodigui.ManagedListItem(hubItem.title, thumbnailImage=hubItem.get('thumb').asTranscodedImageURL(width, height), data_source=hubItem)
                if hubItem.TYPE in ('movie', 'clip'):
                    mli.setProperty('thumb.fallback', 'script.plex/thumb_fallbacks/movie.png')
                elif hubItem.TYPE in ('artist', 'album', 'track'):
                    mli.setProperty('thumb.fallback', 'script.plex/thumb_fallbacks/music.png')
                elif hubItem.TYPE in ('show', 'season', 'episode'):
                    mli.setProperty('thumb.fallback', 'script.plex/thumb_fallbacks/show.png')
                elif hubItem.TYPE == 'photo':
                    mli.setProperty('thumb.fallback', 'script.plex/thumb_fallbacks/photo.png')
                elif hubItem.TYPE == 'collection':
                    mli.setProperty('thumb.fallback', 'script.plex/thumb_fallbacks/{0}.png'.format(
                        self.COLLECTION_FALLBACKS.get(u'{0}'.format(hubItem.get('librarySectionType')), 'movie')))

        return mli

    # The rows each type button shows (all of them for All)
    SECTION_TYPES = {
        'movie': ('movie', 'collection'),
        'show': ('show', 'season', 'episode', 'collection'),
        'artist': ('artist', 'album', 'track', 'collection'),
        'photo': ('photo', 'photodirectory'),
        'people': ('actor', 'director'),
    }
    # The library type (librarySectionType) whose collections each type button shows, and a
    # collection's stand-in art by it
    COLLECTION_LIBRARY_TYPES = {'movie': '1', 'show': '2', 'artist': '8'}
    COLLECTION_FALLBACKS = {'1': 'movie', '2': 'show', '8': 'music'}

    def showHubs(self, hubs):
        """The search's rows as one grid, three across: each type's items in the order the types
        come (the rows' order, mergeResults()), the ones the type button allows."""
        self.clearHubs()
        section = self.getProperty('search.section')
        allowed = self.SECTION_TYPES.get(section)
        collections = self.COLLECTION_LIBRARY_TYPES.get(section)
        items = []
        for hub in hubs:
            if allowed and hub.type not in allowed or hub.size.asInt() <= 0:
                continue
            info = self.HUBMAP.get(hub.type)
            if not info:
                util.DEBUG_LOG('Unhandled hub type: {0}', hub.type)
                continue
            util.DEBUG_LOG('Showing search hub: {0}, {1} items', hub.type, len(hub.items))
            for hubItem in hub.items:
                # a type button's collections: those of its kind of library
                if hub.type == 'collection' and collections and \
                        u'{0}'.format(hubItem.get('librarySectionType')) != collections:
                    continue
                mli = self.createListItem(hubItem, info['type'])
                if mli:
                    items.append(mli)
        self.resultsList.addItems(items)
        self.setProperty('no.results', '' if items else '1')

    def clearHubs(self):
        self.setProperty('no.results', '')
        self.resultsList.reset()
        self.historyList.reset()
        self.setProperty('show.history', '')


def accountServers():
    """Every server on the account: the sidebar's first, in its order, then the rest (owned first,
    by name) - the search's server chooser lists them all."""
    servers = sidebar_model.sidebarServers()
    rest = sorted((s for s in plexapp.SERVERMANAGER.getServers() if s not in servers),
                  key=lambda s: (not getattr(s, 'owned', False), (s.name or '').lower()))
    return servers + rest


def _searchedServersKey():
    return 'search.servers.{0}'.format(plexapp.ACCOUNT.ID)


def saveSearchedServers(uuids):
    util.setSetting(_searchedServersKey(), json.dumps(list(uuids)))


def searchedServers():
    """The servers a search asks: the ones chosen for the account (SearchWindow.chooseServers()), or
    until there's a choice, every one the sidebar has libraries from - or every one on the account
    if it has none (the user, 2026-10-05: one search, everything on each server, wherever it's
    opened from)."""
    try:
        chosen = json.loads(util.getSetting(_searchedServersKey(), '') or 'null')
    except ValueError:
        chosen = None
    if chosen:
        servers = [s for s in accountServers() if s.uuid in chosen]
        if servers:
            return servers
    return sidebar_model.sidebarServers() or accountServers()


# One search answers in about 0.15 s on the LAN; a server slower than this is left out of this
# result (the next keystroke asks again).
SEARCH_TIMEOUT = 10.0

# How many results of each type a server sends (/hubs/search's limit; 3 without one) - all it
# has, though it says no more (more="0" whatever it cut, checked live 2026-10-06). Each library's
# copy takes a place, so with a film in two libraries this is half as many films; 10 (the
# original's, from 2016) was 5 films on Animal, best scores first. 30: about twice the answer of
# 10 (240 KB for "star" on Animal), and Plex barely slower (172 ms against 112). Now the
# search_limit setting (Settings > Main), 50 by default (the user, 2026-10-07): 50 gives the fuller
# film lists ("star" 28 films against 19 at 30); 100 also reaches episodes whose title matches past
# ones only there for their show's name (dropShowNameEpisodes()) - "frasier" keeps 5 at 100, 2 at
# 30 or 50 - but "the" is 2.5 MB across both servers against 1.1 MB at 30.
SEARCH_LIMIT = 50


def searchServers(query, servers, positions=None, superseded=None):
    """/hubs/search on each server together (a thread each), one row per type: the servers' rows of
    a type merged, its items by their score (Plex's relevance), in the order the types first come,
    and copies of one thing one result (dedupeResults(); positions: the sidebar's libraries'
    places). A server known to be offline isn't asked. Returns (rows, the names of the servers whose results
    aren't in them - offline, failed or too slow); rows None if superseded() says the search has been
    overtaken by then, before the copies are looked up."""
    answers = {}
    limit = util.getSetting('search_limit', SEARCH_LIMIT) or SEARCH_LIMIT

    def ask(server):
        try:
            answers[server.uuid] = server.hubs(count=limit, search_query=query)
        except Exception:
            util.ERROR()

    threads = []
    for server in servers:
        if server.offline or server.gone:
            continue
        thread = threading.Thread(target=ask, args=(server,), name='search.' + server.name)
        thread.daemon = True
        thread.start()
        threads.append(thread)
    started = time.time()
    for thread in threads:
        thread.join(max(0, SEARCH_TIMEOUT - (time.time() - started)))
    answered = [s for s in servers if s.uuid in answers]
    missing = [s.name for s in servers if s.uuid not in answers]
    if superseded is not None and superseded():
        return None, missing
    rows = resolveCollections(dropShowNameEpisodes(mergeResults([answers[s.uuid] for s in answered]), query))
    return dedupeResults(rows, answered, positions, lookupCopies(rows, answered)), missing


def _words(text):
    """text as lower-case words, accents dropped, for matching a query against a title."""
    text = unicodedata.normalize('NFKD', u'{0}'.format(text or ''))
    text = u''.join(c for c in text if not unicodedata.combining(c)).lower()
    return re.sub(r'[\W_]+', ' ', text, flags=re.UNICODE).split()


def _matches(words, text):
    """Whether every word typed is in text, as a word or the start of one ("star" in "Starling"),
    or anywhere in it ("star" in "Superstar")."""
    text = u' '.join(_words(text))
    return bool(words) and all(word in text for word in words)


def dropShowNameEpisodes(rows, query):
    """The episodes Plex sends only because their show's name matches (the user, 2026-10-07): the
    show has its own result, and they filled the episode row - all 30 of "arrow"'s, 28 of
    "frasier"'s, checked live. Plex doesn't mark them (no reason=); they're the episodes whose show's
    name has every word typed and whose own title hasn't. One matched some other way - a spelling
    Plex corrected, say - stays."""
    words = _words(query)
    if not words:
        return rows
    for hub in rows:
        if hub.type != 'episode':
            continue
        kept = [item for item in hub.items
                if _matches(words, item.get('title')) or not _matches(words, item.get('grandparentTitle'))]
        if len(kept) != len(hub.items):
            hub.items = kept
            hub.size = plexobjects.PlexValue(str(len(kept)), hub)
    return rows


def resolveCollections(rows):
    """The search's collections as the collections themselves (the user, 2026-10-07). Plex sends
    each as its tag (plexnet media.Collection): the tag's id, a filter key and TMDB's art - not
    something to open, and the tag's id isn't the collection's ratingKey (84090 is an episode on
    Animal). A library's collections whose index is the tags' ids are them, all in one request
    (/library/sections/<id>/collections?index=a,b - about 20 ms, checked live), every library's
    together: with the server's own poster, and opened as the Collections tab opens one. Each
    keeps its tag's library, for its card and the type buttons. One not found - gone, or its
    server too slow - is dropped: there'd be nothing to open."""
    hub = next((h for h in rows if h.type == 'collection'), None)
    if hub is None or not hub.items:
        return rows
    groups = {}
    for tag in hub.items:
        server = getattr(tag, 'server', None)
        library = u'{0}'.format(tag.get('librarySectionID') or '')
        groups.setdefault((getattr(server, 'uuid', None), library), (server, library, []))[2].append(tag)
    found = {}
    lock = threading.Lock()

    def ask(server, library, tags):
        try:
            collections = plexobjects.listItems(server, '/library/sections/{0}/collections'.format(library), params={
                'index': ','.join(u'{0}'.format(tag.get('id')) for tag in tags)})
            with lock:
                for collection in collections:
                    found[(server.uuid, library, u'{0}'.format(collection.get('index')))] = collection
        except Exception:
            util.ERROR()

    threads = []
    for server, library, tags in groups.values():
        if server is None or not library:
            continue
        thread = threading.Thread(target=ask, args=(server, library, tags), name='search.collections.' + server.name)
        thread.daemon = True
        thread.start()
        threads.append(thread)
    started = time.time()
    for thread in threads:
        thread.join(max(0, LOOKUP_TIMEOUT - (time.time() - started)))
    items = []
    with lock:
        for tag in hub.items:
            key = (getattr(getattr(tag, 'server', None), 'uuid', None),
                   u'{0}'.format(tag.get('librarySectionID') or ''), u'{0}'.format(tag.get('id')))
            collection = found.get(key)
            if collection is None:
                continue
            collection.set('librarySectionTitle', tag.get('librarySectionTitle'))
            collection.set('librarySectionType', tag.get('librarySectionType'))
            items.append(collection)
    hub.items = items
    hub.size = plexobjects.PlexValue(str(len(items)), hub)
    return rows


# /library/all's type for each merged type: a copy's versions (its Media, for pickCopy()'s quality)
# only come with one (checked live 2026-10-07)
LOOKUP_TYPES = {'movie': 1, 'show': 2, 'season': 3, 'episode': 4, 'artist': 8, 'album': 9, 'track': 10}

# The copies' lookup comes after the search: a server slower than this adds none this time.
LOOKUP_TIMEOUT = 5.0


def lookupCopies(rows, servers):
    """Every copy of the results, on every server searched: {guid key: [items]}, for
    dedupeResults(). The search can't be relied on for them: past its limit Plex sometimes sends one
    library's copies and leaves the other's out, by a rule of its own (checked live 2026-10-07:
    shows for "the" at 30 all from TV, none from TV shows), and a server whose search didn't send a
    title sends nothing to say it has it. So each server is asked for the results' guids - one
    request per type, together (/library/all?guid=..., as plezy finds a title's copies) - about
    0.15 s after the search on the LAN; without summaries, which halve it and aren't shown."""
    keys = {}
    for hub in rows:
        if hub.type not in MERGED_TYPES:
            continue
        for item in hub.items:
            key = _sameKey(item)
            type_ = u'{0}'.format(item.get('type') or hub.type)
            if key and type_ in LOOKUP_TYPES:
                keys.setdefault(type_, set()).add(key)
    found = []
    lock = threading.Lock()

    def ask(server, type_, guids):
        try:
            items = plexobjects.listItems(server, '/library/all', params={
                'guid': ','.join(sorted(guids)), 'type': LOOKUP_TYPES[type_], 'excludeFields': 'summary'})
            with lock:
                found.extend(items)
        except Exception:
            util.ERROR()

    threads = []
    for server in servers:
        for type_, guids in keys.items():
            thread = threading.Thread(target=ask, args=(server, type_, guids), name='search.copies.' + server.name)
            thread.daemon = True
            thread.start()
            threads.append(thread)
    started = time.time()
    for thread in threads:
        thread.join(max(0, LOOKUP_TIMEOUT - (time.time() - started)))
    copies = {}
    with lock:
        for item in found:
            key = _sameKey(item)
            if key:
                copies.setdefault(key, []).append(item)
    return copies


def _score(item):
    try:
        return float(item.get('score') or 0)
    except (TypeError, ValueError):
        return 0.0


def mergeResults(answers):
    """Each server's search hubs ([[Hub]], servers in order) as one row per type: the first hub of a
    type keeps its title and takes the others' items, all sorted by score, best first (a stable
    sort, so ties keep server order)."""
    merged, order = {}, []
    for hubs in answers:
        for hub in hubs:
            key = hub.type
            if key not in merged:
                merged[key] = hub
                order.append(key)
                hub.items = list(hub.items)
            else:
                merged[key].items.extend(hub.items)
    rows = []
    for key in order:
        hub = merged[key]
        hub.items = sorted(hub.items, key=_score, reverse=True)
        hub.size = plexobjects.PlexValue(str(len(hub.items)), hub)
        rows.append(hub)
    return rows


# The types whose copies are one result (dedupeResults()): the things an agent matched, by its
# guid; and people, who have none, by their plex.tv person's key (tagKey - the same on every
# server and in every library, checked live). Not playlists: two of one name hold different things.
MERGED_TYPES = ('movie', 'show', 'season', 'episode', 'artist', 'album', 'track')
PEOPLE_TYPES = ('actor', 'director')


def _sameKey(item):
    """What makes two results copies of one thing: the agent's guid, less any language suffix.
    None for one no agent matched (local://, which only means something on its own server) or
    with no guid."""
    guid = u'{0}'.format(item.get('guid') or '')
    if not guid or guid.startswith('local://'):
        return None
    return guid.split('?', 1)[0]


def _personKey(item):
    """What makes two people results one person: their plex.tv key. None without one."""
    return u'{0}'.format(item.get('tagKey') or '') or None


def copiesOf(item):
    """A merged result's copies, the one shown first (dedupeResults()); [] for one with none.
    Read from __dict__: a plexnet object answers any missing attribute with an empty value."""
    return item.__dict__.get('searchCopies') or []


def _versions(item):
    """An item's versions (its Media), [] for one with none (a show, a person)."""
    try:
        return list(item.media or [])
    except Exception:
        return []


def _int(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _quality(item):
    """A copy's best version's (width, bitrate), for pickCopy(); (0, 0) if it has none. The best,
    not the first: Plex's order is its own, and a copy with a 4K version second was judged by its
    1080p (the user, 2026-10-07). Read with _int(): a video's versions (plexmedia.PlexMedia)
    answer get() with plain strings."""
    return max([(_int(media.get('width')), _int(media.get('bitrate'))) for media in _versions(item)] or [(0, 0)])


# The types whose versions Open from offers one by one, the one picked opened chosen
# (chooseVersion()): the ones with a version to play
VERSIONED_TYPES = ('movie', 'episode')


def openFromEntries(item):
    """Open from's rows for a result (SearchWindow.openFrom()): (copy, version) for each version of
    each copy that has more than one - a film's 4K and 1080p in one library are two rows - else
    (copy, None)."""
    entries = []
    for copy in copiesOf(item) or [item]:
        versions = _versions(copy) if copy.TYPE in VERSIONED_TYPES else []
        if len(versions) > 1:
            entries.extend((copy, media) for media in versions)
        else:
            entries.append((copy, None))
    return entries


def chooseVersion(copy, media):
    """copy opened with media its chosen version, as pre-play's Choose Version does
    (preplayutils.chooseVersion()): pre-play keeps it through its first load, and the episode
    screen gives it to its own copy of the episode (EpisodesPaginator.createListItem())."""
    for version in _versions(copy):
        version.set('selected', '')
    media.set('selected', 1)
    copy.setMediaChoice(media)


def pickCopy(copies, serverOrder, positions=None):
    """Which copy a merged result opens (the user, 2026-10-06): one part-watched - of several, the
    one watched last (as Continue Watching keeps, home.mergeContinueWatching()); then the one in the
    library highest in the sidebar - pinned beats unpinned whatever the quality: a library pinned,
    and pinned high, is the one watched from (positions: {(server uuid, library key): place},
    sidebar_model.entryPositions()); then the best quality; then the one on the server first in the
    sidebar (serverOrder: uuid -> place); then the best scored. The others are on its context menu
    (SearchWindow.openFrom())."""
    positions = positions or {}
    # past every pinned library: a place is the entry's index in the whole sidebar, Watchlist and
    # Playlists included, so it can be higher than the number of libraries
    unpinned = max(positions.values()) + 1 if positions else 0

    def rank(indexed):
        i, item = indexed
        partWatched = bool(item.get('viewOffset').asInt())
        viewed = item.get('lastViewedAt').asInt() if partWatched else 0
        width, bitrate = _quality(item)
        uuid = getattr(getattr(item, 'server', None), 'uuid', None)
        place = positions.get((uuid, u'{0}'.format(item.get('librarySectionID') or '')), unpinned)
        return (not partWatched, -viewed, place, -width, -bitrate,
                serverOrder.get(uuid, len(serverOrder)), i)
    return min(enumerate(copies), key=rank)[1]


def _copyID(item):
    return getattr(getattr(item, 'server', None), 'uuid', None), u'{0}'.format(item.get('ratingKey') or '')


def dedupeResults(rows, servers, positions=None, found=None):
    """Each row's copies of one thing - in two libraries of a server, or on two servers - as one
    result (the user, 2026-10-06): the copy pickCopy() chooses, in the place the first copy had
    (the best scored, mergeResults()), the others kept with it (copiesOf()). Plex lists a film in
    two libraries twice (Alien in Films and Movies, checked live), and a person once per library
    (Alan Rickman in Films and Movies on Animal, and in Films on Oscar). servers: the ones searched,
    in the sidebar's order; positions: the sidebar's libraries' places (pickCopy()); found: the
    copies lookupCopies() found, joining the results they're copies of (never results of their
    own)."""
    found = found or {}
    order = dict((server.uuid, i) for i, server in enumerate(servers))
    for hub in rows:
        if hub.type in MERGED_TYPES:
            keyOf = _sameKey
        elif hub.type in PEOPLE_TYPES:
            keyOf = _personKey
        else:
            continue
        groups, slots = {}, []
        for item in hub.items:
            key = keyOf(item)
            if key is None:
                slots.append([item])
            elif key in groups:
                groups[key].append(item)
            else:
                groups[key] = [item]
                slots.append(groups[key])
        if keyOf is _sameKey:
            for key, copies in groups.items():
                have = set(_copyID(copy) for copy in copies)
                for copy in found.get(key, ()):
                    if _copyID(copy) not in have:
                        have.add(_copyID(copy))
                        copies.append(copy)
        if all(len(copies) == 1 for copies in slots):
            continue
        items = []
        for copies in slots:
            best = pickCopy(copies, order, positions)
            if len(copies) > 1:
                best.searchCopies = [best] + [copy for copy in copies if copy is not best]
            items.append(best)
        hub.items = items
        hub.size = plexobjects.PlexValue(str(len(items)), hub)
    return rows


def placesLine(item):
    """Where a result is, the line under its type: for one with copies (dedupeResults()), the
    server of the one it opens (pickCopy()), whatever the account, and how many others there are
    on any server - "Animal + 2" (the user, 2026-10-06); otherwise its server, on a multi-server
    account (resultServerName()). Nothing for a person: their page gathers every server's films
    (person.PersonFilmographyTask), so which one they were found on says nothing, and there's no
    other page to choose (the user, 2026-10-06)."""
    if item.TYPE in ('Role', 'Director'):
        return ''
    copies = copiesOf(item)
    if not copies:
        return resultServerName(item)
    return u'{0} + {1}'.format(getattr(getattr(item, 'server', None), 'name', '') or '', len(copies) - 1)


def copyLabel(copy, multiServer, media=None):
    """A row in the Open from list (SearchWindow.openFrom()): the copy's library, its server on a
    multi-server account, then the quality of media - a version of it, else its first - "Films
    \u00b7 Animal \u00b7 1080p (12.5 Mbps)", the dot the cards' lines use (the user, 2026-10-07)."""
    parts = [u'{0}'.format(copy.get('librarySectionTitle') or '')]
    server = getattr(copy, 'server', None)
    if multiServer and server is not None:
        parts.append(server.name)
    if media is None:
        versions = _versions(copy)
        media = versions[0] if versions else None
    if media is not None:
        resolution = u'{0}'.format(media.get('videoResolution') or '')
        resolution = resolution + 'p' if resolution.isdigit() else resolution.upper()
        bitrate = _int(media.get('bitrate'))
        rate = plexnetUtil.bitrateToString(bitrate * 1000) if bitrate else ''
        if resolution and rate:
            parts.append(u'{0} ({1})'.format(resolution, rate))
        else:
            parts.append(resolution or rate)
    return u' \u00b7 '.join(part for part in parts if part)


def resultServerName(item):
    """A result's server, for the line under it on a multi-server account (the sidebar's rule)."""
    manager = plexapp.SERVERMANAGER
    server = getattr(item, 'server', None)
    if server is None or len(manager.getServers()) < 2:
        return ''
    return server.name
