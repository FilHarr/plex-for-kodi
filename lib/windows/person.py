# coding=utf-8
from __future__ import absolute_import

import datetime
import threading
import time

from kodi_six import xbmc
from kodi_six import xbmcgui

from lib import backgroundthread
from lib import util
from lib.util import T
from plexnet import util as plexnetUtil, plexapp
from . import busy
from . import dropdown
from . import kodigui
from . import opener
from . import windowutils
from . import sidebar_model

DISCOVER_HUB_SLOTS = 6
NOT_IN_LIBRARY_BATCH_SIZE = 10


class PersonDetailsTask(backgroundthread.Task):
    def __init__(self, role, callback):
        super(PersonDetailsTask, self).__init__()
        self.role = role
        self.callback = callback

    def run(self):
        if self.isCanceled():
            return
        details = self.role.getDetails()
        if not self.isCanceled():
            self.callback(details)


# How long the person screen waits for a server's answer (filmography, library presence) before
# going on without it, as search does (search.SEARCH_TIMEOUT).
SERVER_TIMEOUT = 10.0


def personServers(role):
    """The servers whose libraries a person's films are looked for in: the sidebar's, in its order,
    those answering - and the one the role came from, if it isn't among them (a library opened
    from the picker, say). Not Discover's server, which has no library."""
    servers = [server for server in sidebar_model.sidebarServers() if not server.offline and not server.gone]
    own = role.server
    known = plexapp.SERVERMANAGER.serversByUuid
    if own is not None and own.uuid in known and own.uuid not in [server.uuid for server in servers]:
        servers.append(own)
    return servers


def personKey(role):
    """The person's plex.tv key (tagKey): the same on every server, so it's what asks each one for
    them (checked live: Alan Rickman's on Animal and Oscar). A role without one has it looked up on
    its own server; None if that doesn't know either."""
    key = role.get('tagKey')
    if key:
        return key
    try:
        data = role.server.query('/library/people/{0}'.format(role.id))
        for directory in data.findall('Directory') if data is not None else ():
            if directory.get('tagKey'):
                return directory.get('tagKey')
    except Exception as e:
        util.DEBUG_LOG('Person: no tagKey for {0}: {1}', role.tag, e)
    return None


def libraryFilmography(server, key):
    """A person's movies and shows in server's libraries: /library/people/{key}/media, whole - it
    only pages when asked (checked live, PMS 1.43.4). One in two libraries comes twice."""
    from plexnet import video
    data = server.query('/library/people/{0}/media'.format(key))
    items = []
    if data is None:
        return items
    for elem in list(data.findall('Video')) + list(data.findall('Metadata')) + list(data.findall('Directory')):
        kind = elem.get('type', '')
        if kind == 'movie':
            items.append(video.Movie(elem, '/library/people', server))
        elif kind == 'show':
            items.append(video.Show(elem, '/library/people', server))
    return items


def _askServers(servers, fn):
    """fn(server) on each server together, a thread each, for up to SERVER_TIMEOUT: {uuid: answer}
    for those that answered. One that fails or is too slow is left out."""
    answers = {}

    def ask(server):
        try:
            answers[server.uuid] = fn(server)
        except Exception as e:
            util.DEBUG_LOG('Person: no answer from {0}: {1}', server.name, e)

    threads = []
    for server in servers:
        thread = threading.Thread(target=ask, args=(server,), name='person.' + server.name)
        thread.daemon = True
        thread.start()
        threads.append(thread)
    started = time.time()
    for thread in threads:
        thread.join(max(0, SERVER_TIMEOUT - (time.time() - started)))
    return answers


class PersonFilmographyTask(backgroundthread.Task):
    """A person's movies and shows in every server's libraries (personServers()), in the servers'
    order - the person screen's filmography (the user, 2026-10-06: it showed only the library
    the person was opened from, and another server's films under "Not in Library")."""

    def __init__(self, role, servers, callback):
        super(PersonFilmographyTask, self).__init__()
        self.role = role
        self.servers = servers
        self.callback = callback

    def run(self):
        if self.isCanceled():
            return
        key = personKey(self.role)
        # without a plex.tv key, only the role's own server can be asked, by its own id
        servers = self.servers if key else [self.role.server]
        answers = _askServers(servers, lambda server: libraryFilmography(server, key or self.role.id))
        items = [item for server in servers for item in answers.get(server.uuid, ())]
        if not self.isCanceled():
            self.callback(items)


def libraryPresence(servers, guids):
    """Which of guids are in a library on any of servers: {guid: the first server, in order, that
    has it} - asked together (Role.checkLibraryPresence() on each)."""
    from plexnet import media as plexmedia
    servers = servers or []
    found = _askServers(servers, lambda server: plexmedia.Role.checkLibraryPresence(server, guids))
    present = {}
    for server in servers:
        for guid in found.get(server.uuid, ()):
            present.setdefault(guid, server)
    return present


class DiscoverItem(object):
    def __init__(self, credit_data):
        meta = credit_data.get('Metadata', {})
        self.title = meta.get('title', '')
        self.year = str(meta.get('year', ''))
        self.type = meta.get('type', 'movie')
        self.ratingKey = meta.get('ratingKey', '')
        self.guid = 'plex://{0}/{1}'.format(self.type, self.ratingKey)
        self.thumb = meta.get('thumb', '')
        self.art = meta.get('art', '')
        self.role = credit_data.get('role', '')
        self.order = credit_data.get('order', 999)
        self.is_discover = True


class DiscoverCreditsTask(backgroundthread.Task):
    def __init__(self, role, servers, callback, credit_type=None):
        super(DiscoverCreditsTask, self).__init__()
        self.role = role
        self.servers = servers
        self.callback = callback
        self.credit_type = credit_type

    def run(self):
        if self.isCanceled():
            return

        credit_groups = self.role.getDiscoverCredits(credit_type=self.credit_type)
        if self.isCanceled() or not credit_groups:
            self.callback([], {})
            return
        if self.credit_type is not None:
            # One type asked for (DirectorWindow): getDiscoverCredits() returns that group's
            # credits as a flat list, not (type, credits) pairs.
            credit_groups = [(self.credit_type, credit_groups)]

        discover_hubs = []
        all_guids = []

        for group_type, credits in credit_groups:
            group_items = []
            for credit in credits:
                item = DiscoverItem(credit)
                if item.ratingKey:
                    group_items.append(item)
                    all_guids.append(item.guid)
            if group_items:
                discover_hubs.append((group_type, group_items))

        if self.isCanceled():
            self.callback([], {})
            return

        # {guid: a server that has it}: in a library on any server isn't "Not in Library"
        library_guids = libraryPresence(self.servers, list(set(all_guids)))

        if not self.isCanceled():
            self.callback(discover_hubs, library_guids)


class PersonWindow(kodigui.ControlledWindow, windowutils.UtilMixin, windowutils.SidebarMixin):
    xmlFile = 'script-plex-person.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    THUMB_DIM = util.scaleResolution(300, 300)
    POSTER_DIM = util.scaleResolution(244, 361)

    FILMOGRAPHY_LIST_ID = 400
    DISCOVER_LIST_BASE_ID = 401
    DISCOVER_GROUP_BASE_ID = 501
    PLAYER_STATUS_BUTTON_ID = 204
    FILTER_BUTTON_ID = 300

    # Override in subclasses
    CREDIT_TYPE = None      # passed to getDiscoverCredits — None fetches all types
    PRIMARY_TYPE = 'actor'  # which credit group to use for filmography filtering
    TYPE_LABEL_ID = 32473   # strings.po ID for the role type label shown on screen

    def __init__(self, *args, **kwargs):
        kodigui.ControlledWindow.__init__(self, *args, **kwargs)
        self.setProperty('loading', '1')
        self.role = kwargs.get('role')
        self.sectionId = kwargs.get('section_id')
        self.cameFromWatchlist = kwargs.get('from_watchlist', False)
        self.personDetails = None
        self.filmographyItems = []
        self.filmographyAllItems = []
        self.filmographyByGuid = {}
        self.filmographyFilter = None
        self.discoverListControls = []
        # {guid: a server it's in a library on} for the Discover credits (libraryPresence())
        self.libraryGuids = {}
        # the servers asked for the person's films (personServers())
        self.servers = []
        self.tasks = backgroundthread.Tasks()
        self.exitCommand = None
        self.initialized = False
        self.lastFocusID = None
        # hashed-orbiting-pizza.md Phase 2: None here means "build my own sectionList" (a
        # standalone/un-hosted open) - a hosted open (LibraryWindow._setupCurrent(), library.py)
        # overwrites this with the host's own sectionList object before onFirstInit() runs.
        self.sectionList = None

    def paintInitialBackground(self):
        """No art, and no colours of a person's own: the neutral colour panel from the first
        frame (kodigui's setNeutralPanel())."""
        super(PersonWindow, self).paintInitialBackground()
        self.setNeutralPanel()

    def onFirstInit(self):
        self.setProperty('loading', '1')
        self.filmographyListControl = kodigui.ManagedControlList(self, self.FILMOGRAPHY_LIST_ID, 5)

        self.discoverListControls = []
        for i in range(DISCOVER_HUB_SLOTS):
            list_id = self.DISCOVER_LIST_BASE_ID + i
            try:
                control = kodigui.ManagedControlList(self, list_id, 5)
                self.discoverListControls.append(control)
            except Exception:
                break

        if self.sectionList is None:
            self.sectionList = kodigui.ManagedControlList(self, self.SECTION_LIST_ID, 15)
            self.buildSectionList()
        else:
            self.sectionList.newControl(self)
        self._selectActiveSection()
        self.displayServerAndUser()

        # Credits are looked up in the library of the server the role came from. A Discover
        # role's server is plex.tv's, which has no library: the first sidebar server answering
        # stands in.
        local_server = next((s for s in sidebar_model.sidebarServers() if not s.offline), None)
        role_server = self.role.server
        if local_server and not (role_server and role_server.uuid in plexapp.SERVERMANAGER.serversByUuid):
            self.role.server = local_server
        self.servers = personServers(self.role)

        self.setProperty('person.name', self.role.tag or '')
        self.setProperty('person.type_label', T(self.TYPE_LABEL_ID, self.PRIMARY_TYPE.title()))
        self.setProperty('filmography.filter', T(32345, 'All'))
        if self.role.thumb:
            self.setProperty('person.thumb', self.role.thumb.asTranscodedImageURL(*self.THUMB_DIM))

        self.fetchPersonDetails()
        self.fetchFilmography()
        self.fetchDiscoverCredits()

        self.initialized = True

    def onReInit(self):
        pass

    def onAction(self, action):
        # Hosted: the host sees the action first (kodigui.BaseWindow.routeActionToHost()).
        if self.routeActionToHost(action):
            return
        try:
            if action in (xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_PREVIOUS_MENU):
                self.doClose()
                return

        except Exception:
            util.ERROR()

        kodigui.ControlledWindow.onAction(self, action)

    def onClick(self, controlID):
        # Not live on its host yet, or any more (kodigui.BaseWindow.ignoresInput()).
        # Hosted: the host handles the sidebar's clicks (kodigui.BaseWindow.routeClickToHost()).
        if self.routeClickToHost(controlID):
            return
        if controlID == self.SECTION_LIST_ID:
            self.sectionClicked()
        elif controlID == self.FILTER_BUTTON_ID:
            self.filterButtonClicked()
        elif controlID == self.FILMOGRAPHY_LIST_ID:
            self.filmographyItemClicked()
        elif controlID == self.PLAYER_STATUS_BUTTON_ID:
            self.showAudioPlayer()
        elif self.DISCOVER_LIST_BASE_ID <= controlID < self.DISCOVER_LIST_BASE_ID + DISCOVER_HUB_SLOTS:
            self.openDiscoverItem(controlID)

    def onFocus(self, controlID):
        # Not live on its host yet, or any more (kodigui.BaseWindow.ignoresInput()).
        if self.ignoresInput():
            return
        self.reselectActiveSection(controlID, self.lastFocusID)
        self.lastFocusID = controlID

        if self.FILMOGRAPHY_LIST_ID <= controlID <= self.DISCOVER_LIST_BASE_ID + DISCOVER_HUB_SLOTS:
            self.setProperty('hub.focus', str(controlID - self.FILMOGRAPHY_LIST_ID))

        if controlID > self.FILMOGRAPHY_LIST_ID and xbmc.getCondVisibility('ControlGroup(50).HasFocus(0)'):
            self.setProperty('on.extras', '1')
        else:
            self.setProperty('on.extras', '')

    def doClose(self, **kw):
        self.tasks.kill()
        kodigui.ControlledWindow.doClose(self)

    def fetchPersonDetails(self):
        task = PersonDetailsTask(self.role, self.onPersonDetails)
        self.tasks.add(task)
        backgroundthread.BGThreader.addTask(task)

    def fetchFilmography(self):
        self.setProperty('loading', '1')
        task = PersonFilmographyTask(self.role, self.servers, self.onFilmography)
        self.tasks.add(task)
        backgroundthread.BGThreader.addTask(task)

    def onPersonDetails(self, details):
        if not details:
            util.DEBUG_LOG('PersonWindow: No details returned')
            return

        self.personDetails = details
        self.setProperty('person.name', details.get('name', ''))
        self.setProperty('person.summary', util.widenParagraphBreaks(details.get('summary', '')))
        self.setProperty('person.birthPlace', details.get('birthPlace', ''))

        birthDate = details.get('birthDate', '')
        deathDate = details.get('deathDate', '')

        if birthDate:
            self.setProperty('person.birthDate', self.formatDate(birthDate))
            age = self.calculateAge(birthDate, deathDate)
            if age:
                self.setProperty('person.age', str(age))

        if deathDate:
            self.setProperty('person.deathDate', self.formatDate(deathDate))
            self.setProperty('person.deceased', '1')

        thumb = details.get('thumb', '')
        if thumb:
            self.setProperty('person.thumb', self.role.server.getImageTranscodeURL(thumb, *self.THUMB_DIM))

        tag_key = details.get('tagKey', '')
        if tag_key and not getattr(self.role, 'tagKey', None):
            self.role.tagKey = tag_key
            self.fetchDiscoverCredits()

    def fetchDiscoverCredits(self):
        if not hasattr(self.role, 'tagKey') or not self.role.tagKey:
            util.DEBUG_LOG('PersonWindow: No tagKey, skipping discover credits')
            return

        task = DiscoverCreditsTask(
            self.role, self.servers, self.onDiscoverCredits,
            credit_type=self.CREDIT_TYPE
        )
        self.tasks.add(task)
        backgroundthread.BGThreader.addTask(task)

    def onDiscoverCredits(self, discover_hubs, library_guids):
        self.libraryGuids = library_guids

        slot = 0
        for group_type, items in discover_hubs:
            if slot >= DISCOVER_HUB_SLOTS:
                break
            not_in_library = [item for item in items if item.guid not in library_guids]
            if not_in_library:
                label = '{0} - {1}'.format(T(32479, 'Not in Library'), group_type.title())
                self.fillDiscoverHub(slot, not_in_library, label)
                slot += 1

        util.DEBUG_LOG('PersonWindow: Discover credits: {0} groups, {1} in library, {2} hubs populated',
                       len(discover_hubs), len(library_guids), slot)

        # Avoid focus trap: if filmography is empty but Discover hubs filled, move focus there
        if slot > 0 and self.filmographyListControl.size() == 0:
            self.setFocusId(self.DISCOVER_LIST_BASE_ID)

    def fillDiscoverHub(self, slot, items, label):
        if slot >= len(self.discoverListControls):
            return

        listControl = self.discoverListControls[slot]
        listItems = [self.createNotInLibraryListItem(item) for item in items]
        listControl.reset()
        listControl.addItems(listItems)
        self.setProperty('discover.hub.{0}.label'.format(slot), label)

    def createNotInLibraryListItem(self, item):
        mli = kodigui.ManagedListItem(
            item.title, item.year, thumbnailImage=item.thumb, data_source=item
        )
        mli.setProperty('media.type', item.type)
        mli.setProperty('thumb.fallback', 'script.plex/thumb_fallbacks/{0}.png'.format(
            'show' if item.type == 'show' else 'movie'))
        if item.role:
            mli.setProperty('role', item.role)
        return mli

    def openDiscoverItem(self, controlID):
        slot = controlID - self.DISCOVER_LIST_BASE_ID
        if slot < 0 or slot >= len(self.discoverListControls):
            return

        mli = self.discoverListControls[slot].getSelectedItem()
        if not mli or not mli.dataSource:
            return

        item = mli.dataSource
        if not item.ratingKey:
            return

        from plexnet import util as pnUtil
        from plexnet.compat import quote_plus
        # in a library on one of the servers: opened from there
        local_server = self.libraryGuids.get(item.guid)
        if local_server:
            try:
                # Resolve plex:// guid against the local PMS — getObject builds a proper PlexObject
                self.processCommand(opener.open(
                    '/library/metadata/{0}'.format(quote_plus(item.guid)), context=self, server=local_server,
                    entry_section_id=self.sectionId, entry_from_watchlist=self.cameFromWatchlist))
                return
            except Exception as e:
                util.DEBUG_LOG('PersonWindow: Local open failed for {0}: {1}', item.guid, e)

        if pnUtil.LOCAL_MODE:
            util.DEBUG_LOG('PersonWindow: Not opening discover item in local mode')
            return

        discover_server = pnUtil.SERVERMANAGER.getDiscoverServer()
        if not discover_server:
            util.DEBUG_LOG('PersonWindow: No discover server available')
            return

        self.processCommand(opener.open(
            item.ratingKey,
            context=self,
            server=discover_server,
            from_watchlist=True,
            external_item=True,
            entry_section_id=self.sectionId,
            entry_from_watchlist=self.cameFromWatchlist
        ))

    def onFilmography(self, items):
        """Every server's movies and shows for the person (PersonFilmographyTask)."""
        self.setProperty('loading', '')
        self.filmographyAllItems = items
        self.applyFilmographyFilter()

    def createFilmographyListItem(self, item):
        title = item.title if hasattr(item, 'title') else item.get('title', '')
        year = ''
        if hasattr(item, 'year'):
            year = str(item.year) if item.year else ''

        thumb = ''
        if hasattr(item, 'thumb') and item.thumb:
            thumb = item.thumb.asTranscodedImageURL(*self.POSTER_DIM)
        elif hasattr(item, 'defaultThumb') and item.defaultThumb:
            thumb = item.defaultThumb.asTranscodedImageURL(*self.POSTER_DIM)

        mli = kodigui.ManagedListItem(title, year, thumbnailImage=thumb, data_source=item)

        item_type = item.type if hasattr(item, 'type') else item.TYPE if hasattr(item, 'TYPE') else ''
        mli.setProperty('media.type', item_type)

        if hasattr(item, 'isPlayed') and item.isPlayed:
            mli.setProperty('watched', '1')

        mli.setProperty('thumb.fallback', 'script.plex/thumb_fallbacks/{0}.png'.format(
            item_type in ('show', 'season', 'episode') and 'show' or 'movie'))

        return mli

    def fillFilmography(self):
        listItems = []
        for item in self.filmographyItems:
            mli = self.createFilmographyListItem(item)
            listItems.append(mli)

        self.filmographyListControl.reset()
        self.filmographyListControl.addItems(listItems)
        self.setProperty('filmography.count', str(len(self.filmographyItems)))

    def filterButtonClicked(self):
        options = [
            {'key': None,    'display': T(32345, 'All')},
            {'key': 'movie', 'display': T(32348, 'Movies')},
            {'key': 'show',  'display': T(32350, 'Shows')},
        ]
        choice = dropdown.showDropdown(
            options=options,
            pos=(560, 515),
            close_direction='none',
            set_dropdown_prop=False,
            align_items='left'
        )
        if choice is None:
            return
        self.filmographyFilter = choice['key']
        self.setProperty('filmography.filter', choice['display'])
        self.applyFilmographyFilter()

    def applyFilmographyFilter(self):
        """The filmography as the filter has it (All, Movies, Shows): from what's loaded, one entry
        for copies of a film on several servers or in several libraries (groupFilmographyByGuid()),
        by title."""
        items = self.filmographyAllItems
        if self.filmographyFilter:
            items = [item for item in items if getattr(item, 'type', None) == self.filmographyFilter]
        self.filmographyItems, self.filmographyByGuid = self.groupFilmographyByGuid(items)
        self.filmographyItems.sort(key=lambda item: u'{0}'.format(item.get('titleSort') or item.get('title')).lower())
        self.fillFilmography()

    def filmographyItemClicked(self):
        mli = self.filmographyListControl.getSelectedItem()
        if not mli or not mli.dataSource:
            return

        item = mli.dataSource
        guid = self.getItemGuid(item)
        versions = self.filmographyByGuid.get(guid, [item]) if guid else [item]

        if len(versions) > 1:
            selectedItem = self.showVersionPicker(versions, item.type if hasattr(item, 'type') else 'movie')
            if selectedItem:
                self.processCommand(opener.open(selectedItem, context=self,
                                                entry_section_id=self.sectionId,
                                                entry_from_watchlist=self.cameFromWatchlist))
        else:
            self.processCommand(opener.open(item, context=self,
                                            entry_section_id=self.sectionId,
                                            entry_from_watchlist=self.cameFromWatchlist))

    def sidebarActiveSection(self, entries):
        # A person isn't tied to one library section (their filmography can span several), but
        # the screen the role was clicked from is: self.sectionId carries it through
        # (RolesMixin.roleSectionId()). None (nothing highlighted) when reached some other way,
        # e.g. Search.
        return sidebar_model.matchSection(entries, self.sectionId, self.cameFromWatchlist, server=self.role.server)

    def formatDate(self, dateStr):
        if not dateStr:
            return ''
        try:
            parts = dateStr.split('-')
            if len(parts) == 3:
                year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
                return datetime.date(year, month, day).strftime('%B %d, %Y')
        except (ValueError, IndexError):
            pass
        return dateStr

    def calculateAge(self, birthDateStr, deathDateStr=None):
        if not birthDateStr:
            return None
        try:
            parts = birthDateStr.split('-')
            if len(parts) != 3:
                return None
            birthDate = datetime.date(int(parts[0]), int(parts[1]), int(parts[2]))

            if deathDateStr:
                parts = deathDateStr.split('-')
                endDate = datetime.date(int(parts[0]), int(parts[1]), int(parts[2])) if len(parts) == 3 else datetime.date.today()
            else:
                endDate = datetime.date.today()

            age = endDate.year - birthDate.year
            if (endDate.month, endDate.day) < (birthDate.month, birthDate.day):
                age -= 1
            return age
        except (ValueError, IndexError):
            return None

    def getItemGuid(self, item):
        if hasattr(item, 'guid') and item.guid:
            return str(item.guid)
        return None

    def groupFilmographyByGuid(self, items, existingByGuid=None):
        byGuid = existingByGuid if existingByGuid is not None else {}
        uniqueItems = []
        seenGuids = set(byGuid.keys()) if existingByGuid else set()

        for item in items:
            guid = self.getItemGuid(item)
            if guid:
                if guid not in byGuid:
                    byGuid[guid] = []
                byGuid[guid].append(item)
                if guid not in seenGuids:
                    seenGuids.add(guid)
                    uniqueItems.append(item)
            else:
                uniqueItems.append(item)

        for guid, versions in byGuid.items():
            if len(versions) > 1:
                versions.sort(key=lambda v: self.getItemBitrate(v), reverse=True)
                for i, uitem in enumerate(uniqueItems):
                    if self.getItemGuid(uitem) == guid:
                        uniqueItems[i] = versions[0]
                        break

        return uniqueItems, byGuid

    def getItemBitrate(self, item):
        try:
            if hasattr(item, 'media') and item.media:
                for media in item.media:
                    if hasattr(media, 'bitrate'):
                        return int(media.bitrate) if media.bitrate else 0
        except (ValueError, TypeError, AttributeError):
            pass
        return 0

    def getItemResolution(self, item):
        try:
            if hasattr(item, 'media') and item.media:
                for media in item.media:
                    if hasattr(media, 'videoResolution') and media.videoResolution:
                        return str(media.videoResolution)
        except (AttributeError, TypeError):
            pass
        return ''

    def getItemLibraryTitle(self, item):
        if hasattr(item, 'getLibrarySectionTitle'):
            return item.getLibrarySectionTitle()
        elif hasattr(item, 'librarySectionTitle'):
            return str(item.librarySectionTitle)
        return ''

    def formatVersionLabel(self, item, media_type='movie'):
        library = self.getItemLibraryTitle(item) or T(34108, 'Unknown')
        server = getattr(item, 'server', None)
        if server is not None and len(plexapp.SERVERMANAGER.getServers()) > 1:
            # which server, on a multi-server account (the person screen asks them all)
            library = u'{0}, {1}'.format(library, server.name)
        if media_type == 'movie':
            resolution = self.getItemResolution(item)
            bitrate = self.getItemBitrate(item)
            res_str = '{}p'.format(resolution) if resolution and 'k' not in str(resolution).lower() else (resolution.upper() if resolution else T(34108, 'Unknown'))
            if bitrate:
                return '{}, {} ({})'.format(library, res_str, plexnetUtil.bitrateToString(bitrate * 1000))
            return '{}, {}'.format(library, res_str)
        return library

    def showVersionPicker(self, versions, media_type='movie'):
        options = [{'key': idx, 'display': self.formatVersionLabel(item, media_type)}
                   for idx, item in enumerate(versions)]
        choice = dropdown.showDropdown(
            options=options,
            pos=(660, 441),
            close_direction='none',
            set_dropdown_prop=False,
            header=T(34109, 'Choose Version'),
            align_items='left'
        )
        if choice is not None:
            return versions[choice['key']]
        return None


class ActorWindow(PersonWindow):
    CREDIT_TYPE = None
    PRIMARY_TYPE = 'actor'
    TYPE_LABEL_ID = 32473  # "Actor"


class DirectorWindow(PersonWindow):
    CREDIT_TYPE = 'director'
    PRIMARY_TYPE = 'director'
    TYPE_LABEL_ID = 32474  # "Director"
