from __future__ import absolute_import

import json
from kodi_six import xbmc
from kodi_six import xbmcgui
from plexnet import plexapp

from lib import util
from lib.util import T
from . import busy
from . import home
from . import kodigui
from . import playlist
from . import search
from . import windowutils


class PlaylistsWindow(kodigui.ControlledWindow, windowutils.UtilMixin, windowutils.SidebarMixin):
    xmlFile = 'script-plex-playlists.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    THUMB_DIMS = {
        'audio': {
            'item.thumb': util.scaleResolution(270, 270)
        },
        'video': {
            'item.thumb': util.scaleResolution(610, 344)
        }
    }

    AUDIO_PL_LIST_ID = 101
    VIDEO_PL_LIST_ID = 301

    OPTIONS_GROUP_ID = 200

    PLAYER_STATUS_BUTTON_ID = 204

    def __init__(self, *args, **kwargs):
        kodigui.ControlledWindow.__init__(self, *args, **kwargs)
        self.exitCommand = None
        self.lastFocusID = None

    def onFirstInit(self):
        self.audioPLListControl = kodigui.ManagedControlList(self, self.AUDIO_PL_LIST_ID, 5)
        self.videoPLListControl = kodigui.ManagedControlList(self, self.VIDEO_PL_LIST_ID, 5)

        self.sectionList = kodigui.ManagedControlList(self, self.SECTION_LIST_ID, 15)
        self.buildSectionList()
        self.displayServerAndUser()

        self.fill()
        if self.audioPLListControl.size():
            self.setFocusId(self.AUDIO_PL_LIST_ID)
        else:
            self.setFocusId(self.VIDEO_PL_LIST_ID)

    def onFocus(self, controlID):
        self.reselectActiveSection(controlID, self.lastFocusID)
        self.lastFocusID = controlID

    def onAction(self, action):
        try:
            if action == xbmcgui.ACTION_CONTEXT_MENU:
                if not xbmc.getCondVisibility('ControlGroup({0}).HasFocus(0)'.format(self.OPTIONS_GROUP_ID)):
                    self.setFocusId(self.OPTIONS_GROUP_ID)
                    return
            # elif action in(xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_CONTEXT_MENU):
            #     if not xbmc.getCondVisibility('ControlGroup({0}).HasFocus(0)'.format(self.OPTIONS_GROUP_ID)):
            #         self.setFocusId(self.OPTIONS_GROUP_ID)
            #         return

        except:
            util.ERROR()

        kodigui.ControlledWindow.onAction(self, action)

    def onClick(self, controlID):
        if controlID == self.SECTION_LIST_ID:
            self.sectionClicked()
        elif controlID == self.AUDIO_PL_LIST_ID:
            self.playlistListClicked(self.audioPLListControl)
        elif controlID == self.VIDEO_PL_LIST_ID:
            self.playlistListClicked(self.videoPLListControl)
        elif controlID == self.PLAYER_STATUS_BUTTON_ID:
            self.showAudioPlayer()

    def searchButtonClicked(self):
        self.processCommand(search.dialog(self))

    def buildSectionList(self):
        """Populate the sidebar's section list. Mirrors library.py's buildSectionList()/
        home.py's showSections() and preplay.py's own copy - see library.py:675 for why this
        isn't shared code yet.
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

        if "order" in navSettings:
            order = navSettings["order"]

            def orderPos(s):
                if s.key in order:
                    return order.index(s.key), 0
                return -1, 0

            sections = sorted(sections, key=orderPos)

        for section in sections:
            mli = kodigui.ManagedListItem(section.title,
                                          iconImage='script.plex/home/type/{0}.png'.format(section.type),
                                          data_source=section)
            mli.setProperty('item', '1')
            if section == home.playlists_section:
                mli.setProperty('is.playlists', '1')
                mli.setIconImage('script.plex/home/type/playlists.png')
                # This window IS the Playlists destination - unlike every other ported screen,
                # there's no getLibrarySectionId() to compare against a "current" item, so just
                # mark this entry active directly rather than leaving nothing highlighted.
                mli.setProperty('is.active', '1')
            elif section == home.watchlist_section:
                mli.setIconImage('script.plex/home/type/watchlist.png')
            items.append(mli)

        self.sectionList.reset()
        self.sectionList.addItems(items)

    # sectionClicked() now provided by SidebarMixin - its default _dispatchSectionOpen() covers
    # this window's needs exactly (including the section == self.lastSection skip, which now also
    # covers clicking "Playlists" while already here - previously that reopened a redundant second
    # PlaylistsWindow instance on top of this one).

    def displayServerAndUser(self):
        """Sidebar avatar/username and server icon/name. Mirrors library.py's/preplay.py's
        displayServerAndUser() (see library.py:777 for why home.py's own version doesn't
        reach this window - window properties are per-window).
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

    def playlistListClicked(self, list_control):
        mli = list_control.getSelectedItem()
        if not mli:
            return

        self.openWindow(playlist.PlaylistWindow, playlist=mli.dataSource)

    def createListItem(self, obj):
        dimensions = self.THUMB_DIMS.get(obj.playlistType)

        if not dimensions:
            return

        w, h = dimensions['item.thumb']

        if obj.playlistType == 'audio':
            thumb = obj.buildComposite(width=w, height=h, media='thumb')
        else:
            thumb = obj.buildComposite(width=w, height=h, media='art')

        mli = kodigui.ManagedListItem(
            obj.title or '',
            util.durationToText(obj.duration.asInt()),
            # thumbnailImage=obj.composite.asTranscodedImageURL(*self.THUMB_DIMS[obj.playlistType]['item.thumb']),
            thumbnailImage=thumb,
            data_source=obj
        )
        mli.setProperty('thumb.fallback', 'script.plex/thumb_fallbacks/{0}.png'.format(obj.playlistType == 'audio' and 'music' or 'movie'))

        return mli

    @busy.dialog()
    def fill(self):
        items = {
            'audio': [],
            'video': []
        }
        playlists = plexapp.SERVERMANAGER.selectedServer.playlists()

        self.setProperty(
            'background',
            util.backgroundFromArt(playlists[0].composite, width=self.width, height=self.height)
        )

        for pl in playlists:
            mli = self.createListItem(pl)
            if mli:
                items[pl.playlistType].append(mli)

        self.audioPLListControl.addItems(items['audio'])
        self.videoPLListControl.addItems(items['video'])
