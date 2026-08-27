from __future__ import absolute_import

import json
from kodi_six import xbmc
from kodi_six import xbmcgui
from plexnet import playlist, plexapp

from lib import util
from lib.util import T
from lib import player
from . import busy
from . import dropdown
from . import home
from . import kodigui
from . import musicplayer
from . import opener
from . import search
from . import windowutils


class AlbumWindow(kodigui.ControlledWindow, windowutils.UtilMixin, windowutils.SidebarMixin):
    xmlFile = 'script-plex-album.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    THUMB_AR16X9_DIM = util.scaleResolution(178, 100)
    THUMB_SQUARE_DIM = util.scaleResolution(630, 630)

    TRACKS_LIST_ID = 101
    LIST_OPTIONS_BUTTON_ID = 111

    OPTIONS_GROUP_ID = 200

    PLAYER_STATUS_BUTTON_ID = 204

    PLAY_BUTTON_ID = 301
    SHUFFLE_BUTTON_ID = 302
    OPTIONS_BUTTON_ID = 303

    def __init__(self, *args, **kwargs):
        kodigui.ControlledWindow.__init__(self, *args, **kwargs)
        self.album = kwargs.get('album')
        self.parentList = kwargs.get('parentList')

        # Sidebar entry-section persistence (ported from Sidebar-Tab-Unification's
        # mellow-pondering-magpie.md, 2026-08-18) - see preplay.py's PrePlayWindow.__init__ for the
        # full reasoning. No watchlist concept in the music library, so just the section id, always
        # inherited or self-resolved.
        self.entrySectionId = kwargs.get('entry_section_id') or self.album.getLibrarySectionId()

        self.albums = None
        self.exitCommand = None
        self.lastPlayingRK = None
        self.lastFocusID = None
        # hashed-orbiting-pizza.md Phase 2: None here means "build my own sectionList" (a
        # standalone/un-hosted open) - a hosted open (LibraryWindow._setupCurrent(), library.py)
        # overwrites this with the host's own sectionList object before onFirstInit() runs.
        self.sectionList = None

    def onFirstInit(self):
        self.trackListControl = kodigui.ManagedControlList(self, self.TRACKS_LIST_ID, 5)

        if self.sectionList is None:
            self.sectionList = kodigui.ManagedControlList(self, self.SECTION_LIST_ID, 15)
            self.buildSectionList()
        else:
            self.sectionList.newControl(self)
        self.displayServerAndUser()

        self.setup()
        self.setFocusId(self.TRACKS_LIST_ID)
        player.PLAYER.on('started.audio', self.onPlayingTrackChanged)
        try:
            self.checkForHeaderFocus(xbmcgui.ACTION_MOVE_DOWN)
        except AttributeError:
            raise util.NoDataException

    def onFocus(self, controlID):
        self.reselectActiveSection(controlID, self.lastFocusID)
        self.lastFocusID = controlID

        if controlID == self.SECTION_LIST_ID:
            self.checkSectionItem()

    def onReInit(self):
        if self.lastPlayingRK:
            self.selectTrack(self.lastPlayingRK)

    def onPlayingTrackChanged(self, *args, **kwargs):
        self.lastPlayingRK = util.getGlobalProperty("track.ID")

    def setup(self):
        self.updateProperties()
        self.fillTracks()

    def doClose(self, **kw):
        player.PLAYER.off('started.audio', self.onPlayingTrackChanged)
        kodigui.ControlledWindow.doClose(self)

    def selectTrack(self, ratingKey):
        if not ratingKey:
            return
        for mli in self.trackListControl:
            if mli.dataSource.ratingKey == ratingKey:
                self.trackListControl.setSelectedItem(mli)

    def onAction(self, action):
        controlID = self.getFocusId()

        if controlID == self.SECTION_LIST_ID:
            self.checkSectionItem(action=action)

        try:
            if action == xbmcgui.ACTION_LAST_PAGE and xbmc.getCondVisibility('ControlGroup(300).HasFocus(0)'):
                self.next()
            elif action == xbmcgui.ACTION_NEXT_ITEM:
                self.next()
            elif action == xbmcgui.ACTION_FIRST_PAGE and xbmc.getCondVisibility('ControlGroup(300).HasFocus(0)'):
                self.prev()
            elif action == xbmcgui.ACTION_PREV_ITEM:
                self.prev()

            if controlID == self.TRACKS_LIST_ID:
                self.checkForHeaderFocus(action)
            if controlID == self.LIST_OPTIONS_BUTTON_ID and self.checkOptionsAction(action):
                return
            elif action == xbmcgui.ACTION_CONTEXT_MENU:
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

    def checkOptionsAction(self, action):
        if action == xbmcgui.ACTION_MOVE_UP:
            mli = self.trackListControl.getSelectedItem()
            if not mli:
                return False
            pos = mli.pos() - 1
            if self.trackListControl.positionIsValid(pos):
                self.setFocusId(self.TRACKS_LIST_ID)
                self.trackListControl.selectItem(pos)
            return True
        elif action == xbmcgui.ACTION_MOVE_DOWN:
            mli = self.trackListControl.getSelectedItem()
            if not mli:
                return False
            pos = mli.pos() + 1
            if self.trackListControl.positionIsValid(pos):
                self.setFocusId(self.TRACKS_LIST_ID)
                self.trackListControl.selectItem(pos)
            return True

        return False

    def onClick(self, controlID):
        if controlID == self.SECTION_LIST_ID:
            self.sectionClicked()
        elif controlID == self.TRACKS_LIST_ID:
            self.trackPanelClicked()
        elif controlID == self.PLAYER_STATUS_BUTTON_ID:
            self.showAudioPlayer()
        elif controlID == self.PLAY_BUTTON_ID:
            self.playButtonClicked()
        elif controlID == self.SHUFFLE_BUTTON_ID:
            self.shuffleButtonClicked()
        elif controlID == self.OPTIONS_BUTTON_ID:
            self.optionsButtonClicked()
        elif controlID == self.LIST_OPTIONS_BUTTON_ID:
            mli = self.trackListControl.getSelectedItem()
            if mli:
                self.optionsButtonClicked(mli)

    def getAlbums(self):
        if not self.albums:
            self.albums = self.album.artist().albums()

        if not self.albums:
            return False

        return True

    def next(self):
        if not self._next():
            return
        self.setup()

    @busy.dialog()
    def _next(self):
        if self.parentList:
            mli = self.parentList.getListItemByDataSource(self.album)
            if not mli:
                return False

            pos = mli.pos() + 1
            if not self.parentList.positionIsValid(pos):
                pos = 0

            self.album = self.parentList.getListItem(pos).dataSource
        else:
            if not self.getAlbums():
                return False

            if self.album not in self.albums:
                return False

            pos = self.albums.index(self.album)
            pos += 1
            if pos >= len(self.albums):
                pos = 0

            self.album = self.albums[pos]

        return True

    def prev(self):
        if not self._prev():
            return
        self.setup()

    @busy.dialog()
    def _prev(self):
        if self.parentList:
            mli = self.parentList.getListItemByDataSource(self.album)
            if not mli:
                return False

            pos = mli.pos() - 1
            if pos < 0:
                pos = self.parentList.size() - 1

            self.album = self.parentList.getListItem(pos).dataSource
        else:
            if not self.getAlbums():
                return False

            if self.album not in self.albums:
                return False

            pos = self.albums.index(self.album)
            pos -= 1
            if pos < 0:
                pos = len(self.albums) - 1

            self.album = self.albums[pos]

        return True

    def searchButtonClicked(self):
        self.processCommand(search.dialog(self, section_id=self.album.getLibrarySectionId() or None))

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

        # self.entrySectionId (Sidebar entry-section persistence) - inherited from wherever this
        # window was drilled in from, or this window's own real section if it's itself a genesis
        # point - see preplay.py's buildSectionList().
        activeSectionId = self.entrySectionId

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
            if activeSectionId and section.key == activeSectionId:
                mli.setProperty('is.active', '1')
            items.append(mli)

        self.sectionList.reset()
        self.sectionList.addItems(items)

    # sectionClicked() now provided by SidebarMixin - its default _dispatchSectionOpen() covers
    # this window's needs exactly.

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

    def shuffleButtonClicked(self):
        self.playButtonClicked(shuffle=True)

    def optionsButtonClicked(self, item=None):
        options = []

        if item:
            if item.dataSource.isWatched:
                options.append({'key': 'mark_unwatched', 'display': T(32318, 'Mark Unplayed')})
            else:
                options.append({'key': 'mark_watched', 'display': T(32319, 'Mark Played')})

            # if False:
            #     options.append({'key': 'add_to_playlist', 'display': '[COLOR FF808080]Add To Playlist[/COLOR]'})
        else:
            if xbmc.getCondVisibility('Player.HasAudio + MusicPlayer.HasNext'):
                options.append({'key': 'play_next', 'display': T(32325, 'Play Next')})

            # if xbmc.getCondVisibility('Player.HasAudio') and self.section.TYPE == 'artist':
            #     options.append({'key': 'add_to_queue', 'display': 'Add To Queue'})

            if options:
                options.append(dropdown.SEPARATOR)

            options.append({'key': 'to_artist', 'display': T(32301, 'Go to Artist')})
            options.append({'key': 'to_section', 'display': T(32302, u'Go to {0}').format(self.album.getLibrarySectionTitle())})

        pos = (460, 1106)
        bottom = True
        setDropdownProp = False
        if item:
            viewPos = self.trackListControl.getViewPosition()
            if viewPos > 6:
                pos = (1490, 312 + (viewPos * 100))
                bottom = True
            else:
                pos = (1490, 167 + (viewPos * 100))
                bottom = False
            setDropdownProp = True
        choice = dropdown.showDropdown(options, pos, pos_is_bottom=bottom, close_direction='right', set_dropdown_prop=setDropdownProp)
        if not choice:
            return

        if choice['key'] == 'play_next':
            xbmc.executebuiltin('PlayerControl(Next)')
        elif choice['key'] == 'mark_watched':
            media = item and item.dataSource or self.album
            media.markWatched()
            self.updateItems(item)
            util.MONITOR.watchStatusChanged()
        elif choice['key'] == 'mark_unwatched':
            media = item and item.dataSource or self.album
            media.markUnwatched()
            self.updateItems(item)
            util.MONITOR.watchStatusChanged()
        elif choice['key'] == 'to_artist':
            self.processCommand(opener.open(self.album.parentRatingKey, context=self, entry_section_id=self.entrySectionId))
        elif choice['key'] == 'to_section':
            self.goHome(self.album.getLibrarySectionId())

    def checkForHeaderFocus(self, action):
        if action in (xbmcgui.ACTION_MOVE_UP, xbmcgui.ACTION_PAGE_UP):
            if self.trackListControl.getSelectedItem().getProperty('is.header'):
                xbmc.executebuiltin('Action(up)')
        if action in (xbmcgui.ACTION_MOVE_DOWN, xbmcgui.ACTION_PAGE_DOWN, xbmcgui.ACTION_MOVE_LEFT, xbmcgui.ACTION_MOVE_RIGHT):
            if self.trackListControl.getSelectedItem().getProperty('is.header'):
                xbmc.executebuiltin('Action(down)')

    def updateItems(self, item=None):
        if item:
            self.album.reload()
            item.setProperty('watched', item.dataSource.isWatched and '1' or '')
        else:
            self.fillTracks()

    def playButtonClicked(self, shuffle=False):
        pl = playlist.LocalPlaylist(self.album.all(), self.album.getServer())
        pl.startShuffled = shuffle
        self.openWindow(musicplayer.MusicPlayerWindow, track=pl.current(), playlist=pl)

    def trackPanelClicked(self):
        mli = self.trackListControl.getSelectedItem()
        if not mli:
            return

        self.openWindow(musicplayer.MusicPlayerWindow, track=mli.dataSource, album=self.album)

    def updateProperties(self):
        self.setProperty(
            'background',
            util.backgroundFromArt(self.album.art, width=self.width, height=self.height)
        )
        self.setProperty('album.thumb', self.album.thumb.asTranscodedImageURL(*self.THUMB_SQUARE_DIM))
        self.setProperty('artist.title', self.album.parentTitle or '')
        self.setProperty('album.title', self.album.title)

    def createListItem(self, obj):
        mli = kodigui.ManagedListItem(obj.title, data_source=obj)
        mli.setProperty('track.number', str(obj.index) or '')
        mli.setProperty('track.duration', util.simplifiedTimeDisplay(obj.duration.asInt()))
        return mli

    #@busy.dialog()
    def fillTracks(self):
        items = []
        idx = 0
        multiDisc = 0

        for track in self.album.tracks():
            disc = track.parentIndex.asInt()
            if disc > 1:
                if not multiDisc:
                    items.insert(0, kodigui.ManagedListItem(u'{0} 1'.format(T(32420, 'Disc').upper()), properties={'is.header': '1'}))

                if disc != multiDisc:
                    items[-1].setProperty('is.footer', '1')
                    multiDisc = disc
                    items.append(kodigui.ManagedListItem('{0} {1}'.format(T(32420, 'Disc').upper(), disc), properties={'is.header': '1'}))

            mli = self.createListItem(track)
            if mli:
                mli.setProperty('track.ID', track.ratingKey)
                mli.setProperty('index', str(idx))
                mli.setProperty('artist', self.album.parentTitle)
                mli.setProperty('disc', str(disc))
                mli.setProperty('album', self.album.title)
                mli.setProperty('number', '{0:0>2}'.format(track.index))
                items.append(mli)
                idx += 1

        if items:
            items[-1].setProperty('is.footer', '1')

        self.trackListControl.replaceItems(items)
