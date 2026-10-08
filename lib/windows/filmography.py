# coding=utf-8
from __future__ import absolute_import

from kodi_six import xbmcgui

from lib import backgroundthread
from lib import util
from lib.util import T
from . import kodigui
from . import person
from . import sidebar_model
from . import windowutils
from .mixins.row_restore import RowRestoreMixin


class FilmographyTask(backgroundthread.Task):
    """Every credit Discover has for a person, by type: on_credits([(type, title, [DiscoverItem])]),
    in Discover's order (newest first within a type). Then which of them are in a library on any
    of servers: on_presence({guid: the first server that has it}) - person.libraryPresence(), a
    batch of requests per server, so the rows show without waiting for it."""

    def __init__(self, role, servers, on_credits, on_presence):
        super(FilmographyTask, self).__init__()
        self.role = role
        self.servers = servers
        self.onCredits = on_credits
        self.onPresence = on_presence

    def run(self):
        if self.isCanceled():
            return
        if not getattr(self.role, 'tagKey', None):
            key = person.personKey(self.role)
            if key:
                self.role.tagKey = key

        groups = []
        for group_type, title, credits in self.role.getDiscoverCredits(titled=True):
            items = [item for item in (person.DiscoverItem(credit) for credit in credits) if item.ratingKey]
            if items:
                groups.append((group_type, title, items))
        if self.isCanceled():
            return
        self.onCredits(groups)

        guids = list(set(item.guid for _, _, items in groups for item in items))
        if not guids or self.isCanceled():
            return
        present = person.libraryPresence(self.servers, guids)
        if not self.isCanceled():
            self.onPresence(present)


class FilmographyWindow(kodigui.ControlledWindow, windowutils.UtilMixin, windowutils.SidebarMixin, RowRestoreMixin):
    """A person's whole filmography as Discover has it (Role.getDiscoverCredits()): a button per
    credit type - Producer, Actor, Appearances, Writer... with its count - over a list of that
    type's credits, newest first, each marked with the server it's on if it's in a library there.
    Opened from the person screen's Filmography button (person.PersonWindow.openFilmography());
    modelled on Plex's own filmography screen (on request, 2026-10-08)."""
    xmlFile = 'script-plex-filmography.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    # The type buttons, one per credit type Discover has for the person (Stan Lee has six);
    # 911-918, clear of the sidebar's user menu group (901), as Search's are
    TYPE_BUTTON_IDS = tuple(range(911, 919))
    CREDIT_LIST_ID = 101
    PLAYER_STATUS_BUTTON_ID = 204

    def __init__(self, *args, **kwargs):
        kodigui.ControlledWindow.__init__(self, *args, **kwargs)
        windowutils.UtilMixin.__init__(self)
        self.role = kwargs.get('role')
        self.sectionId = kwargs.get('section_id')
        self.cameFromWatchlist = kwargs.get('from_watchlist', False)
        # The credit type shown ('producer', 'actor'...) - kept through Back (restoreState());
        # None shows the first
        self.creditType = kwargs.get('credit_type')
        # (CREDIT_LIST_ID, position) to focus once the list is filled: Back from what was opened
        # from it (RowRestoreMixin)
        self.restoreFocus = kwargs.get('restore_focus')
        # [(type, title, [DiscoverItem])] (FilmographyTask)
        self.groups = []
        # {guid: a server it's in a library on} (FilmographyTask)
        self.present = {}
        self.servers = []
        self.tasks = backgroundthread.Tasks()
        self.lastFocusID = None
        self.creditList = None
        # None: build my own sectionList (a standalone open) - a hosted open
        # (LibraryWindow._setupCurrent()) hands over the host's before onFirstInit() runs
        self.sectionList = None

    def restoreRows(self):
        return {self.CREDIT_LIST_ID: self.creditList}

    def asyncRestoreRows(self):
        return (self.CREDIT_LIST_ID,)

    def restoreDefaultFocusIds(self):
        return (0, self.CREDIT_LIST_ID)

    def restoreState(self):
        """RowRestoreMixin's list item, plus the credit type it's in."""
        state = RowRestoreMixin.restoreState(self)
        state['credit_type'] = self.creditType
        return state

    def paintInitialBackground(self):
        """The person screen's: the neutral colour panel from the first frame."""
        super(FilmographyWindow, self).paintInitialBackground()
        self.setNeutralPanel()

    def onFirstInit(self):
        self.creditList = kodigui.ManagedControlList(self, self.CREDIT_LIST_ID, 8)

        if self.sectionList is None:
            self.sectionList = kodigui.ManagedControlList(self, self.SECTION_LIST_ID, 15)
            self.buildSectionList()
        else:
            self.sectionList.newControl(self)
        self._selectActiveSection()
        self.displayServerAndUser()

        # the person screen has already put a library server in place of a Discover role's
        # (PersonWindow.onFirstInit()) - the same role object comes here
        self.servers = person.personServers(self.role)
        self.setProperty('person.name', self.role.tag or '')
        self.setProperty('loading', '1')

        task = FilmographyTask(self.role, self.servers, self.onCredits, self.onPresence)
        self.tasks.add(task)
        backgroundthread.BGThreader.addTask(task)

    def onReInit(self):
        pass

    def onAction(self, action):
        # Hosted: the host sees the action first (kodigui.BaseWindow.routeActionToHost()).
        if self.routeActionToHost(action):
            return
        try:
            if action in (xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_PREVIOUS_MENU):
                if not self.handleBack():
                    self.doClose()
                return
        except Exception:
            util.ERROR()

        kodigui.ControlledWindow.onAction(self, action)

    def handleBack(self):
        """Back down the list goes to its first credit before it leaves the screen (on request,
        2026-10-08). The host asks this before popping the chain (kodigui.BaseWindow.handleBack())."""
        if self.creditList is None or self.getFocusId() != self.CREDIT_LIST_ID:
            return False
        if not self.creditList.getSelectedPos():
            return False
        self.creditList.setSelectedItemByPos(0)
        return True

    def onClick(self, controlID):
        # Hosted: the host handles the sidebar's clicks (kodigui.BaseWindow.routeClickToHost()).
        if self.routeClickToHost(controlID):
            return
        if controlID == self.SECTION_LIST_ID:
            self.sectionClicked()
        elif controlID == self.PLAYER_STATUS_BUTTON_ID:
            self.showAudioPlayer()
        elif controlID in self.TYPE_BUTTON_IDS:
            self.typeClicked(self.TYPE_BUTTON_IDS.index(controlID))
        elif controlID == self.CREDIT_LIST_ID:
            self.creditClicked()

    def onFocus(self, controlID):
        # Not live on its host yet, or any more (kodigui.BaseWindow.ignoresInput()).
        if self.ignoresInput():
            return
        self.reselectActiveSection(controlID, self.lastFocusID)
        self.lastFocusID = controlID

    def doClose(self, **kw):
        self.tasks.kill()
        kodigui.ControlledWindow.doClose(self)

    def sidebarActiveSection(self, entries):
        # the person screen's (PersonWindow.sidebarActiveSection())
        return sidebar_model.matchSection(entries, self.sectionId, self.cameFromWatchlist, server=self.role.server)

    def onCredits(self, groups):
        """The credit types and their credits (FilmographyTask): a type button each, labelled with
        Discover's name for it and its count, and the list of the type Back left, or the first."""
        self.groups = groups[:len(self.TYPE_BUTTON_IDS)]
        types = [group[0] for group in self.groups]
        if self.creditType not in types:
            self.creditType = types[0] if types else None
        self.setProperty('loading', '')
        self.setBoolProperty('no.credits', not self.groups)
        if not self.groups:
            return
        self.showType(types.index(self.creditType))

        # a Back restore to the credit opened, if there is one (RowRestoreMixin)
        self._restoreRowFocus(filled=self.CREDIT_LIST_ID)

    def onPresence(self, present):
        """Which credits are in a library (FilmographyTask): marked on the list shown, and on the
        others as they're shown (createListItem())."""
        self.present = present
        for mli in self.creditList:
            self.markServer(mli)

    def typeClicked(self, index):
        if index < len(self.groups) and self.groups[index][0] != self.creditType:
            self.showType(index)

    def showType(self, index):
        group_type, title, items = self.groups[index]
        self.creditType = group_type
        self.labelTypeButtons(index)
        self.creditList.reset()
        self.creditList.addItems([self.createListItem(item) for item in items])

    def labelTypeButtons(self, current):
        """Each type button's label, "Producer (126)", the type shown (current, an index) in the
        sidebar's active orange as Search's selected type is; '' hides a button with no type."""
        for i in range(len(self.TYPE_BUTTON_IDS)):
            label = ''
            if i < len(self.groups):
                label = u'{0} ({1})'.format(self.groups[i][1], len(self.groups[i][2]))
                if i == current:
                    label = u'[COLOR FFE5A00D]{0}[/COLOR]'.format(label)
            self.setProperty('type.{0}.label'.format(i), label)

    def createListItem(self, item):
        """A credit's row: the year, then the title, then "as" its role (a character, or Executive
        Producer, Characters...) where it has one - and the server it's on (markServer())."""
        label = item.title
        if item.role:
            label = u'{0}  [COLOR AAFFFFFF]{1}[/COLOR]'.format(label, T(35161, 'as {0}').format(item.role))
        mli = kodigui.ManagedListItem(label, data_source=item)
        mli.setProperty('year', item.year if item.year not in ('', '0', 'None') else '')
        self.markServer(mli)
        return mli

    def markServer(self, mli):
        server = self.present.get(mli.dataSource.guid)
        if server is not None:
            mli.setProperty('server', T(35162, 'On {0}').format(server.name))

    def creditClicked(self):
        """Open the credit: from the library it's in, if it is in one, otherwise from Discover
        (person.openCredit())."""
        mli = self.creditList.getSelectedItem()
        if not mli or not mli.dataSource:
            return
        person.openCredit(self, mli.dataSource, self.present.get(mli.dataSource.guid))
