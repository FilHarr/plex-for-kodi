from __future__ import absolute_import

import json

from plexnet import plexapp, plexobjects

from lib import util
from lib.util import T
from . import home
from . import kodigui
from . import opener
from . import playlists
from . import search
from . import windowutils


class GenreBrowserWindow(kodigui.ControlledWindow, windowutils.UtilMixin, windowutils.SidebarMixin):
    xmlFile = 'script-plex-genres.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    GENRE_PANEL_ID = 101

    PLAYER_STATUS_BUTTON_ID = 204

    def __init__(self, *args, **kwargs):
        kodigui.ControlledWindow.__init__(self, *args, **kwargs)
        windowutils.UtilMixin.__init__(self)
        self.section = kwargs.get('section')
        self.exitCommand = None

    def onFirstInit(self):
        self.genreListControl = kodigui.ManagedControlList(self, self.GENRE_PANEL_ID, 5)
        self.setProperty('screen.title', u'{0} \u00b7 {1}'.format(
            self.section.title.upper(), T(34102, 'Categories').upper()
        ))
        self.fillGenres()

        self.sectionList = kodigui.ManagedControlList(self, self.SECTION_LIST_ID, 15)
        self.buildSectionList()
        self.displayServerAndUser()

        self.setBoolProperty('initialized', True)
        self.setFocusId(self.GENRE_PANEL_ID)

    def fillGenres(self):
        if self.section.key.startswith('/'):
            path = '{0}/categories'.format(self.section.key)
        else:
            path = '/library/sections/{0}/categories'.format(self.section.key)

        categories = plexobjects.listItems(self.section.server, path, bytag=True)
        if not categories:
            return

        items = []
        for cat in categories:
            mli = kodigui.ManagedListItem(str(cat.title))
            mli.dataSource = cat
            if cat.__dict__.get('thumb'):
                mli.setThumbnailImage(cat.thumb.asURL(includeToken=True))
            items.append(mli)

        self.genreListControl.addItems(items)
        self.setProperty('items.count', str(len(items)))

    def doClose(self, **kw):
        kodigui.ControlledWindow.doClose(self)

    def onClick(self, controlID):
        if controlID == self.SECTION_LIST_ID:
            self.sectionClicked()
        elif controlID == self.PLAYER_STATUS_BUTTON_ID:
            self.showAudioPlayer()
        elif controlID == self.GENRE_PANEL_ID:
            self.genreClicked()

    def searchButtonClicked(self):
        self.processCommand(search.dialog(self, section_id=self.section.key))

    def buildSectionList(self):
        """Populate the sidebar's section list. Mirrors library.py's buildSectionList()/
        home.py's showSections() and episodes.py's/preplay.py's/subitems.py's own copies -
        see library.py:675 for why this isn't shared code yet.
        """
        items = []

        searchmli = kodigui.ManagedListItem(T(32431, 'Search'), iconImage='script.plex/buttons/search.png')
        searchmli.setProperty('is.search', '1')
        searchmli.setProperty('item', '1')
        items.append(searchmli)

        homemli = kodigui.ManagedListItem(T(32332, 'Home'), iconImage='script.plex/home/type/home.png',
                                          data_source=home.home_section)
        homemli.setProperty('is.home', '1')
        homemli.setProperty('item', '1')
        items.append(homemli)

        setting_key = 'home.settings.{}.{}'.format(plexapp.SERVERMANAGER.selectedServer.uuid[-8:], plexapp.ACCOUNT.ID)
        try:
            navSettings = json.loads(util.getSetting(setting_key, '')) or {}
        except ValueError:
            navSettings = {}

        sections = []

        if (not plexapp.ACCOUNT.isOffline and util.getUserSetting("use_watchlist", True) and home.watchlist_section
                and home.watchlist_section.has_data()
                and ("/library/sections/watchlist" not in navSettings
                     or navSettings["/library/sections/watchlist"].get("show", True))):
            sections.append(home.watchlist_section)

        if "playlists" not in navSettings or navSettings["playlists"].get("show", True):
            if plexapp.SERVERMANAGER.selectedServer.playlists():
                sections.append(home.playlists_section)

        for section in plexapp.SERVERMANAGER.selectedServer.library.sections():
            if section.key in navSettings and not navSettings[section.key].get("show", True):
                continue
            sections.append(section)
            if navSettings:
                pinnable = home.PINNABLE_TYPES.get(str(getattr(section, 'TYPE', None)), ())
                stored = navSettings.get(section.key, {}).get('pinned_types') or []
                for item_type in stored:
                    if item_type in pinnable:
                        sections.append(home.PinnedTypeSection(section, item_type))

        if "order" in navSettings:
            order = navSettings["order"]

            def orderPos(s):
                if s.key in order:
                    return order.index(s.key), 0
                if isinstance(s, home.PinnedTypeSection) and s.librarySection.key in order:
                    return order.index(s.librarySection.key), 1
                return -1, 0

            sections = sorted(sections, key=orderPos)

        activeSectionId = self.section.key

        for section in sections:
            mli = kodigui.ManagedListItem(section.title,
                                          iconImage='script.plex/home/type/{0}.png'.format(section.type),
                                          data_source=section)
            mli.setProperty('item', '1')
            if section == home.playlists_section:
                mli.setProperty('is.playlists', '1')
                mli.setIconImage('script.plex/home/type/playlists.png')
            elif section == home.watchlist_section:
                mli.setIconImage('script.plex/home/type/watchlist.png')
            elif isinstance(section, home.PinnedTypeSection):
                mli.setProperty('is.pinned.type', section.itemType)
            if activeSectionId and section.key == activeSectionId:
                mli.setProperty('is.active', '1')
            items.append(mli)

        self.sectionList.reset()
        self.sectionList.addItems(items)

    def sectionClicked(self):
        mli = self.sectionList.getSelectedItem()
        if not mli:
            return

        if mli.getProperty('is.search'):
            self.searchButtonClicked()
            return

        if mli.getProperty('is.home'):
            self.goHome()
            return

        section = mli.dataSource
        if section.type == 'playlists':
            self.processCommand(opener.handleOpen(playlists.PlaylistsWindow))
        else:
            self.processCommand(opener.sectionClicked(section))

    def displayServerAndUser(self):
        """Sidebar avatar/username and server icon/name. Mirrors library.py's/episodes.py's/
        preplay.py's/subitems.py's displayServerAndUser() (see library.py:777 for why home.py's
        own version doesn't reach this window - window properties are per-window).
        """
        title = plexapp.ACCOUNT.title or plexapp.ACCOUNT.username or ' '
        self.setProperty('user.name', title)
        self.setProperty('user.avatar', plexapp.ACCOUNT.safeUserThumb(plexapp.ACCOUNT.ID,
                                                                       thumb=plexapp.ACCOUNT.thumb))
        self.setProperty('user.avatar.letter', title[0].upper())

        if plexapp.SERVERMANAGER.selectedServer:
            self.setProperty('server.name', plexapp.SERVERMANAGER.selectedServer.name)
            self.setProperty('server.icon', 'script.plex/home/device/plex.png')
            self.setProperty('server.iconmod',
                             plexapp.SERVERMANAGER.selectedServer.isSecure and 'script.plex/home/device/lock.png' or '')
            self.setProperty('server.iconmod2',
                             plexapp.SERVERMANAGER.selectedServer.isLocal and 'script.plex/home/device/home_small.png'
                             or '')
        else:
            self.setProperty('server.name', T(32338, 'No Servers Found'))
            self.setProperty('server.icon', 'script.plex/home/device/error.png')
            self.setProperty('server.iconmod', '')
            self.setProperty('server.iconmod2', '')

    def genreClicked(self):
        mli = self.genreListControl.getSelectedItem()
        if not mli or not mli.dataSource:
            return
        cat = mli.dataSource
        # key is e.g. "/library/sections/2/all?genre=5" — extract the numeric genre ID
        key_str = str(cat.key)
        genre_id = key_str.split('genre=')[-1].split('&')[0] if 'genre=' in key_str else key_str
        filter_ = {'type': 'genre', 'display': T(32379, 'Genre'), 'sub': {'val': genre_id, 'display': str(cat.title)}}
        self.processCommand(opener.sectionClicked(self.section, filter_=filter_))
