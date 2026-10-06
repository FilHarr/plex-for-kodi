from __future__ import absolute_import

import json
import threading
import time

from kodi_six import xbmcgui, xbmc
from plexnet import plexapp, plexobjects

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
    # The type buttons: 911-915, clear of the sidebar's user menu group (901, SidebarMixin.
    # USER_MENU_GROUP_ID), which the user menu resizes by id
    SECTION_BUTTONS = {
        911: 'all',
        912: 'movie',
        913: 'show',
        914: 'artist',
        915: 'photo'
    }

    EDIT_CONTROL_ID = 650
    BUTTON_A_ID = 1001
    PLAYER_STATUS_BUTTON_ID = 204
    SEARCH_HUB_COUNT = 12  # must match core.search_hub_count in lib/templating/context.py
    HISTORY_LIST_ID = 2050
    MAX_HISTORY_ITEMS = 10

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
        'genre': {'type': 'circle'},
        'playlist': {'type': 'square'},
    }

    SECTION_TYPE_MAP = {
        '1': {'thumb': 'script.plex/section_type/movie.png'},  # Movie
        '2': {'thumb': 'script.plex/section_type/show.png'},  # Show
        '3': {'thumb': 'script.plex/section_type/show.png'},  # Season
        '4': {'thumb': 'script.plex/section_type/show.png'},  # Episode
        '8': {'thumb': 'script.plex/section_type/music.png'},  # Artist
        '9': {'thumb': 'script.plex/section_type/music.png'},  # Album
        '10': {'thumb': 'script.plex/section_type/music.png'},  # Track
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
        self.hubControls = [
            kodigui.ManagedControlList(self, 2100 + i, 5)
            for i in range(self.SEARCH_HUB_COUNT)
        ]
        self.historyList = kodigui.ManagedControlList(self, self.HISTORY_LIST_ID, self.MAX_HISTORY_ITEMS + 1)

        if self.sectionList is None:
            self.sectionList = kodigui.ManagedControlList(self, self.SECTION_LIST_ID, 15)
            self.buildSectionList()
        else:
            self.sectionList.newControl(self)
            host = self.hostedBy()
            if host is not None:
                # Search's entry is the active one whenever it shows: Back to it from a genre
                # result too, whose library's grid moved the marker (LibraryWindow.swapToSection())
                host.updateActiveSectionMarker(windowutils.SEARCH_ENTRY)
        self._selectActiveSection()
        self.displayServerAndUser()

        self.edit = kodigui.SafeControlEdit(self.EDIT_CONTROL_ID, 651, self, key_callback=self.updateFromEdit,
                                            grab_focus=True)
        self.edit.setCompatibleMode(rpc.Application.GetProperties(properties=["version"])["version"]["major"] < 17)
        if self.useKodiKbd:
            self.setProperty('hide.kbd', '1')
        self.setProperty('search.section', self.initialSection)
        # the servers button (chooseServers())
        self.setProperty('search.multi', len(plexapp.SERVERMANAGER.getServers()) > 1 and '1' or '')
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
        and the result focused - (row, item), or None away from the results."""
        controlID = self.getFocusId()
        focus = None
        if 2100 <= controlID < 2100 + self.SEARCH_HUB_COUNT:
            focus = (controlID - 2100, self.hubControls[controlID - 2100].getSelectedPos())
        return {'query': self.edit.getText(), 'searchSection': self.getProperty('search.section') or 'all',
                'focus': focus}

    def onAction(self, action):
        # Hosted: the host sees the action first (kodigui.BaseWindow.routeActionToHost()), Back
        # included - it goes through the chain, to Home's root from here.
        if self.routeActionToHost(action):
            return
        try:
            if action in (xbmcgui.ACTION_MOVE_DOWN, xbmcgui.ACTION_MOVE_UP):
                if self._skipEmptyRow(action):
                    return
        except Exception:
            util.ERROR()

        kodigui.ControlledWindow.onAction(self, action)

    def _skipEmptyRow(self, action):
        controlID = self.getFocusId()
        if not (2100 <= controlID < 2100 + self.SEARCH_HUB_COUNT):
            return False
        idx = controlID - 2100
        step = 1 if action == xbmcgui.ACTION_MOVE_DOWN else -1
        nxt = idx + step
        while 0 <= nxt < self.SEARCH_HUB_COUNT:
            control = self.hubControls[nxt]
            if control and control.size() > 0:
                self.setFocusId(2100 + nxt)
                return True
            nxt += step
        return False

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
        elif 2099 < controlID < 2200:
            self.hubItemClicked(controlID)
        elif controlID == self.HISTORY_LIST_ID:
            self.historyItemClicked()

    def onFocus(self, controlID):
        # Not live on its host yet, or any more (kodigui.BaseWindow.ignoresInput()).
        if self.ignoresInput():
            return
        self.reselectActiveSection(controlID, self.lastFocusID)
        self.lastFocusID = controlID

        if 2099 < controlID < 2200:
            self.setProperty('hub.focus', str(controlID - 2100))

    def sidebarActiveSection(self, entries):
        """The Search entry (windowutils.SEARCH_ENTRY), for a sidebar this screen builds itself."""
        return windowutils.SEARCH_ENTRY

    def updateFromEdit(self, actionID, oldVal, newVal):
        if actionID == xbmcgui.ACTION_PREVIOUS_MENU:
            # leaving, as Back does anywhere else on this screen: through the host
            self.routeActionToHost(actionID)
            return

        self.updateQuery()

    def updateQuery(self):
        self.updateResults()

    def _gone(self):
        """Closed, or swapped out by its host: nothing more is shown here."""
        return self._closing or (self._hostRef is not None and self.hostedBy() is None)

    def updateResults(self, delay=1):
        """Search for what's typed, delay seconds after the last key, on the results thread
        (_updateResults()). The query is read here, on the main thread."""
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
        rows, missing = searchServers(query, searchedServers())
        self._post('search results', self.showResults, (query, rows, missing))

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
        if rows is None:
            self.setProperty('search.note', '')
            self.showSearchHistory()
            return
        self.showHubs(rows)
        self._restoreFocus()
        # the results are short of a server's: say whose
        self.setProperty('search.note', missing and T(35129, "{0} isn't responding").format(', '.join(missing)) or '')

    def _restoreFocus(self):
        """Back at the results from a result opened from them: focus on that result again, if the
        search still has it there."""
        focus, self.initialFocus = self.initialFocus, None
        if not focus:
            return
        index, pos = focus
        if 0 <= index < len(self.hubControls) and pos < self.hubControls[index].size():
            self.setFocusId(2100 + index)
            self.hubControls[index].selectItem(pos)

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
        if old != section:
            self.updateResults()

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
        self.updateQuery()

    def hubItemClicked(self, hubControlID):
        for control in self.hubControls:
            if control.controlID == hubControlID:
                break
        else:
            return

        mli = control.getSelectedItem()
        if not mli:
            return

        hubItem = mli.dataSource
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
            control.removeManagedItem(mli)

        self.processCommand(command)

    def createListItem(self, hubItem):
        mli = self._listItem(hubItem)
        if mli is not None:
            mli.setProperty('server.name', resultServerName(hubItem))
        return mli

    def _listItem(self, hubItem):
        if hubItem.TYPE in ('Genre', 'Director', 'Role'):
            if hubItem.TYPE == 'Genre':
                thumb = (self.SECTION_TYPE_MAP.get(hubItem.librarySectionType) or {}).get('thumb', '')
                mli = kodigui.ManagedListItem(hubItem.tag, hubItem.reasonTitle, thumbnailImage=thumb, data_source=hubItem)
                mli.setProperty('thumb.fallback', thumb)
            else:
                mli = kodigui.ManagedListItem(
                    hubItem.tag, hubItem.reasonTitle, thumbnailImage=hubItem.get('thumb').asTranscodedImageURL(256, 256), data_source=hubItem
                )
                mli.setProperty('thumb.fallback', 'script.plex/thumb_fallbacks/role.png')
        else:
            if hubItem.TYPE == 'playlist':
                mli = kodigui.ManagedListItem(hubItem.tag, thumbnailImage=hubItem.get('composite').asTranscodedImageURL(256, 256), data_source=hubItem)
                mli.setProperty('thumb.fallback', 'script.plex/thumb_fallbacks/{0}.png'.format(hubItem.playlistType == 'audio' and 'music' or 'movie'))
            elif hubItem.TYPE == 'photodirectory':
                mli = kodigui.ManagedListItem(hubItem.title, thumbnailImage=hubItem.get('composite').asTranscodedImageURL(256, 256), data_source=hubItem)
                mli.setProperty('thumb.fallback', 'script.plex/thumb_fallbacks/photo.png')
            else:
                mli = kodigui.ManagedListItem(hubItem.title, thumbnailImage=hubItem.get('thumb').asTranscodedImageURL(256, 256), data_source=hubItem)
                if hubItem.TYPE in ('movie', 'clip'):
                    mli.setProperty('thumb.fallback', 'script.plex/thumb_fallbacks/movie.png')
                elif hubItem.TYPE in ('artist', 'album', 'track'):
                    mli.setProperty('thumb.fallback', 'script.plex/thumb_fallbacks/music.png')
                elif hubItem.TYPE in ('show', 'season', 'episode'):
                    mli.setProperty('thumb.fallback', 'script.plex/thumb_fallbacks/show.png')
                elif hubItem.TYPE == 'photo':
                    mli.setProperty('thumb.fallback', 'script.plex/thumb_fallbacks/photo.png')

        return mli

    def showHubs(self, hubs):
        self.clearHubs()

        allowed = None
        if self.getProperty('search.section') == 'movie':
            allowed = ('movie',)
        elif self.getProperty('search.section') == 'show':
            allowed = ('show', 'season', 'episode')
        elif self.getProperty('search.section') == 'artist':
            allowed = ('artist', 'album', 'track')
        elif self.getProperty('search.section') == 'photo':
            allowed = ('photo', 'photodirectory')

        controlID = None
        i = 0
        for h in hubs:
            if allowed and h.type not in allowed:
                continue

            if h.size.asInt() > 0:
                if i >= self.SEARCH_HUB_COUNT:
                    break
                cid = self.showHub(h, i)
                controlID = controlID or cid
                i += 1

        if controlID:
            self.setProperty('no.results', '')
        else:
            self.setProperty('no.results', '1')

    def showHub(self, hub, idx):
        util.DEBUG_LOG('Showing search hub: {0} at {1}', hub.type, idx)
        info = self.HUBMAP.get(hub.type)
        if not info:
            util.DEBUG_LOG('Unhandled hub type: {0}', hub.type)
            return

        hub_id = 2100 + idx
        control = self.hubControls[idx]

        self.setProperty('hub.display.{0}'.format(hub_id), info['type'])
        self.setProperty('hub.{0}'.format(hub_id), hub.title)

        items = []
        for hubItem in hub.items:
            mli = self.createListItem(hubItem)
            if mli:
                items.append(mli)

        control.reset()
        control.addItems(items)

        return control.controlID

    def clearHubs(self):
        self.setProperty('no.results', '')
        for i, control in enumerate(self.hubControls):
            control.reset()
            hub_id = 2100 + i
            self.setProperty('hub.{0}'.format(hub_id), '')
            self.setProperty('hub.display.{0}'.format(hub_id), '')
        self.setProperty('hub.focus', '')
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


def searchServers(query, servers):
    """/hubs/search on each server together (a thread each), one row per type: the servers' rows of
    a type merged, its items by their score (Plex's relevance), in the order the types first come.
    A server known to be offline isn't asked. Returns (rows, the names of the servers whose results
    aren't in them - offline, failed or too slow)."""
    answers = {}

    def ask(server):
        try:
            answers[server.uuid] = server.hubs(count=10, search_query=query)
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
    return mergeResults([answers[s.uuid] for s in answered]), missing


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


def resultServerName(item):
    """A result's server, for the line under it on a multi-server account (the sidebar's rule)."""
    manager = plexapp.SERVERMANAGER
    server = getattr(item, 'server', None)
    if server is None or len(manager.getServers()) < 2:
        return ''
    return server.name
