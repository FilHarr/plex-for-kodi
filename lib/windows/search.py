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
from . import sidebar_model
from . import windowutils


class HistoryItem(object):
    TYPE = 'history'

    def __init__(self, query, is_clear=False):
        self.query = query
        self.title = query
        self.is_clear = is_clear


class SearchDialog(kodigui.BaseDialog, windowutils.UtilMixin):
    xmlFile = 'script-plex-search.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    LETTERS = 'abcdefghijklmnopqrstuvwxyz0123456789 '
    SECTION_BUTTONS = {
        901: 'all',
        902: 'movie',
        903: 'show',
        904: 'artist',
        905: 'photo'
    }

    # results opener.open() opens itself, blocking, rather than through the window's queue
    OPENED_HERE = ('photo', 'track', 'clip')

    EDIT_CONTROL_ID = 650
    BUTTON_A_ID = 1001
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
        kodigui.BaseDialog.__init__(self, *args, **kwargs)
        windowutils.UtilMixin.__init__(self)
        self.parentWindow = kwargs.get('parent_window')
        # Back from a result opened from here: the search again, and the result (searchReturn())
        self.initialQuery = kwargs.get('query')
        self.initialFocus = kwargs.get('focus')
        self.resultsThread = None
        self.updateResultsTimeout = 0
        self.isActive = True
        self.useKodiKbd = util.getSetting('search_use_kodi_kbd')

    def onFirstInit(self):
        self.hubControls = [
            kodigui.ManagedControlList(self, 2100 + i, 5)
            for i in range(self.SEARCH_HUB_COUNT)
        ]
        self.historyList = kodigui.ManagedControlList(self, self.HISTORY_LIST_ID, self.MAX_HISTORY_ITEMS + 1)

        self.edit = kodigui.SafeControlEdit(self.EDIT_CONTROL_ID, 651, self, key_callback=self.updateFromEdit,
                                            grab_focus=True)
        self.edit.setCompatibleMode(rpc.Application.GetProperties(properties=["version"])["version"]["major"] < 17)
        if self.useKodiKbd:
            self.setProperty('hide.kbd', '1')
            self.setFocusId(self.EDIT_CONTROL_ID)
            xbmc.executebuiltin('Action(Select,{0})'.format(self._winID))
        else:
            self.setFocusId(self.BUTTON_A_ID)
        self.setProperty('search.section', 'all')
        # the servers button (chooseServers())
        self.setProperty('search.multi', len(plexapp.SERVERMANAGER.getServers()) > 1 and '1' or '')
        if self.initialQuery:
            self.edit.setText(self.initialQuery)
            self.updateResults(delay=0)
        else:
            self.showSearchHistory()

    def onReInit(self):
        # Re-displayed (e.g. returning from an opened result): re-evaluate the view.
        # onFirstInit only runs on the first init, so without this the history view
        # never re-renders after the dialog is shown again.
        if self.edit.getText():
            self.updateResults()
        else:
            self.showSearchHistory()

    def onAction(self, action):
        try:
            if action in (xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_PREVIOUS_MENU):
                self.isActive = False
            elif action in (xbmcgui.ACTION_MOVE_DOWN, xbmcgui.ACTION_MOVE_UP):
                if self._skipEmptyRow(action):
                    return
        except:
            util.ERROR()

        kodigui.BaseDialog.onAction(self, action)

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
        if controlID == self.SERVERS_BUTTON_ID:
            self.chooseServers()
        elif 1000 < controlID < 1037:
            self.letterClicked(controlID)
        elif controlID in self.SECTION_BUTTONS:
            self.sectionClicked(controlID)
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
        if 2099 < controlID < 2200:
            self.setProperty('hub.focus', str(controlID - 2100))

    def updateFromEdit(self, actionID, oldVal, newVal):
        if actionID == xbmcgui.ACTION_PREVIOUS_MENU:
            self.isActive = False
            self.doClose()
            return

        self.updateQuery()

    def updateQuery(self):
        self.updateResults()

    def updateResults(self, delay=1):
        self.updateResultsTimeout = time.time() + delay
        if not self.resultsThread or not self.resultsThread.is_alive():
            self.resultsThread = threading.Thread(target=self._updateResults, name='search.update')
            self.resultsThread.start()

    def _updateResults(self):
        while time.time() < self.updateResultsTimeout and not util.MONITOR.waitForAbort(0.1):
            pass

        self._reallyUpdateResults()

    def _reallyUpdateResults(self):
        query = self.edit.getText()
        if query:
            with self.propertyContext('searching'):
                rows, missing = searchServers(query, searchedServers())
                self.showHubs(rows)
            self._restoreFocus()
            # the results are short of a server's: say whose
            self.setProperty('search.note', missing and T(35129, "{0} isn't responding").format(', '.join(missing)) or '')
        else:
            self.setProperty('search.note', '')
            self.showSearchHistory()

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

    def sectionClicked(self, controlID):
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
        server = plexapp.SERVERMANAGER.selectedServer
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
        if hubItem.TYPE not in self.OPENED_HERE:
            # Back from it comes back here (LibraryWindow.swapTo()/popBack())
            host = self.parentWindow._liveChainHost() if hasattr(self.parentWindow, '_liveChainHost') else None
            if host is not None and hasattr(host, 'searchReturn'):
                host.searchReturn({'query': self.edit.getText(),
                                   'focus': (self.hubControls.index(control), control.getSelectedPos())})
        self.doClose()
        try:
            # context=self.parentWindow (hashed-orbiting-pizza.md Phase 5 follow-up): every
            # search.dialog() caller passes the window that was current when Search opened as
            # parent_window - by the time this runs, self.doClose() above has already closed this
            # dialog, so parentWindow is back to being the sole active window, same as any other
            # context-menu-driven open elsewhere in this codebase. Without this, every one of the
            # seven hosted shell types opened from a search result opened as a second real nested
            # window instead of swapping into a live chain, and everything drilled into further
            # from there kept nesting too, since a standalone (non-hosted) shell's own
            # _chainHost is always None - defeating the whole point of hosting for that entire
            # sub-tree. context is a no-op for object types no dispatch branch is wired for
            # (photo/track) - opener.open() already ignores it there.
            command = opener.open(hubItem, context=self.parentWindow)

            if not hubItem.exists():
                control.removeManagedItem(mli)

            self.processCommand(command)
        finally:
            if not self.exitCommand and hubItem.TYPE in self.OPENED_HERE:
                # a photo, track or clip opens here and now (opener.handleOpen()): back to the
                # results after
                self.show()
            else:
                # Anything else is opened by the window behind, from its queue (MultiWindow.
                # postNav(), since 43f176ae) - which only runs once this dialog has finished.
                # Shown again, as it was, the dialog sat in front of the open it had asked for, for
                # good (live 2026-10-05: no search result opened).
                self.isActive = False

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
        self.opaqueBackground(on=False)

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
                self.opaqueBackground()
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
        self.opaqueBackground(on=False)
        self.setProperty('no.results', '')
        for i, control in enumerate(self.hubControls):
            control.reset()
            hub_id = 2100 + i
            self.setProperty('hub.{0}'.format(hub_id), '')
            self.setProperty('hub.display.{0}'.format(hub_id), '')
        self.setProperty('hub.focus', '')
        self.historyList.reset()
        self.setProperty('show.history', '')

    def opaqueBackground(self, on=True):
        self.parentWindow.setProperty('search.dialog.hasresults', on and '1' or '')

    def wait(self):
        # short slices: Kodi only runs this dialog's queued callbacks (each key typed) between them
        # - see kodigui.WAIT_SLICE_SECONDS
        while self.isActive and not util.MONITOR.waitForAbort(kodigui.WAIT_SLICE_SECONDS):
            pass


def sidebarServers():
    """The servers the sidebar has entries from, in sidebar order."""
    manager = plexapp.SERVERMANAGER
    servers, seen = [], set()
    for sid in sidebar_model.loadNavSettings().get('entries', ()):
        uuid, sep, _ = sid.partition(':')
        server = manager.serversByUuid.get(uuid) if sep else None
        if server is not None and uuid not in seen:
            seen.add(uuid)
            servers.append(server)
    return servers


def accountServers():
    """Every server on the account: the sidebar's first, in its order, then the rest (owned first,
    by name) - the search's server chooser lists them all."""
    servers = sidebarServers()
    rest = sorted((s for s in plexapp.SERVERMANAGER.getServers() if s not in servers),
                  key=lambda s: (not getattr(s, 'owned', False), (s.name or '').lower()))
    return servers + rest


def _searchedServersKey():
    return 'search.servers.{0}'.format(plexapp.ACCOUNT.ID)


def saveSearchedServers(uuids):
    util.setSetting(_searchedServersKey(), json.dumps(list(uuids)))


def searchedServers():
    """The servers a search asks: the ones chosen for the account (SearchDialog.chooseServers()), or
    until there's a choice, every one the sidebar has libraries from - or the selected one if it
    has none (the user, 2026-10-05: one search, everything on each server, wherever it's opened
    from)."""
    try:
        chosen = json.loads(util.getSetting(_searchedServersKey(), '') or 'null')
    except ValueError:
        chosen = None
    if chosen:
        servers = [s for s in accountServers() if s.uuid in chosen]
        if servers:
            return servers
    servers = sidebarServers()
    manager = plexapp.SERVERMANAGER
    if not servers and manager.selectedServer:
        servers.append(manager.selectedServer)
    return servers


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


def dialog(parent_window, query=None, focus=None):
    """The search dialog over parent_window. query/focus: a search to run straight away and the
    result to focus in it (Back to a search, LibraryWindow.popBack())."""
    parent_window.setProperty('search.dialog.hasresults', '')
    with parent_window.propertyContext('search.dialog'):
        try:
            w = SearchDialog.open(parent_window=parent_window, query=query, focus=focus)
            w.wait()
            command = w.exitCommand or ''
            del w
            return command
        finally:
            parent_window.setProperty('search.dialog.hasresults', '')
