from __future__ import absolute_import

import json
from kodi_six import xbmc
from kodi_six import xbmcgui
from plexnet import playqueue, plexapp

from lib import util
from lib.util import T
from lib import player
from . import busy
from . import dropdown
from . import home
from . import info
from . import kodigui
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

    OPTIONS_GROUP_ID = 200

    PLAYER_STATUS_BUTTON_ID = 204

    PLAY_BUTTON_ID = 301
    SHUFFLE_BUTTON_ID = 302
    OPTIONS_BUTTON_ID = 303

    # Invisible click targets laid over the header's summary textbox and artist line - textboxes
    # and labels have no click or focus of their own in Kodi, so each needs a real button control
    # sized to match it (script-plex-album.xml.tpl). Same 305 the Seasons/Artist screens use for
    # their own summary (subitems.py).
    SUMMARY_BUTTON_ID = 305
    ARTIST_BUTTON_ID = 306

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
        self._selectActiveSection()
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

    def onReInit(self):
        if self.lastPlayingRK:
            self.selectTrack(self.lastPlayingRK)

    def onPlayingTrackChanged(self, *args, **kwargs):
        self.lastPlayingRK = util.getGlobalProperty("track.ID")

    def setup(self):
        # The album arrives as a partial object from whatever list was clicked, and Album._setData()
        # (plexnet/audio.py) only populates genres when isFullObject() - so without this reload the
        # header's meta line would have a date and nothing else. Guarded: a failed reload should
        # cost the genres, not the screen.
        try:
            self.album.reload()
        except:
            util.ERROR('AlbumWindow: album reload failed, meta line may be incomplete')

        self.updateProperties()
        self.fillTracks()

    def doClose(self, **kw):
        player.PLAYER.off('started.audio', self.onPlayingTrackChanged)
        kodigui.ControlledWindow.doClose(self)

    def selectTrack(self, ratingKey):
        if not ratingKey:
            return
        for mli in self.trackListControl:
            # Not every row is a track: fillTracks() puts a disc header in front of each disc's
            # tracks, and those are ManagedListItems with no data source at all. Every album has
            # at least one, at position 0, so this walked straight into it and raised on the very
            # first row - meaning the playing track never got reselected on the way back to this
            # screen (live, returning from the player).
            if mli.dataSource and mli.dataSource.ratingKey == ratingKey:
                self.trackListControl.setSelectedItem(mli)

    def onAction(self, action):
        controlID = self.getFocusId()

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
            if action == xbmcgui.ACTION_CONTEXT_MENU:
                # Swallowed: this screen has no per-item context menu, and the jump into
                # OPTIONS_GROUP_ID (the header, group 200) that used to live here is the same one
                # Episodes/Seasons/Artist/Pre-play just lost - script-plex-album.xml blanks
                # header_topleft in favour of the sidebar, leaving group 200 with only the audio
                # widget (204, focusable just while Player.HasAudio), so with nothing playing Kodi
                # drops focus entirely and the screen goes dead to everything but Back. See
                # episodes.py's own copy of this branch for the full story.
                return
        except:
            util.ERROR()

        kodigui.ControlledWindow.onAction(self, action)

    def onClick(self, controlID):
        if self.handleSidebarDropdownClick(controlID):
            return
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
        elif controlID == self.SUMMARY_BUTTON_ID:
            self.summaryButtonClicked()
        elif controlID == self.ARTIST_BUTTON_ID:
            self.artistButtonClicked()

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
            # if xbmc.getCondVisibility('Player.HasAudio') and self.section.TYPE == 'artist':
            #     options.append({'key': 'add_to_queue', 'display': 'Add To Queue'})

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

        if choice['key'] == 'mark_watched':
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
            self.artistButtonClicked()
        elif choice['key'] == 'to_section':
            self.goHome(self.album.getLibrarySectionId())

    def summaryButtonClicked(self):
        # The same popup the Seasons/Artist screens' own summary targets open
        # (summaryButtonClicked(), subitems.py), rather than the old InfoWindow.
        info.showSummary(self.album.title, self.album.get('summary'))

    def artistButtonClicked(self):
        # Exactly what the More menu's own "Go to artist" entry does (optionsButtonClicked() above,
        # which now calls through here) - the header's artist line is just a more direct way to it.
        self.processCommand(opener.open(self.album.parentRatingKey, context=self,
                                        entry_section_id=self.entrySectionId))

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

    # Both of these go through opener, which builds a server play queue and then hands it to the
    # music player - the same thing video, photos and Plex playlists already do, so the session is
    # one Plex knows about and other clients can see or take over. They used to push a
    # LocalPlaylist straight into Kodi's own playlist, which the server never heard about.
    #
    # opener opens the player with handleOpen(), not openWindow(): it's a chrome-only player
    # window, never a library screen, so it must open ON TOP of this one. openWindow() is
    # chain-aware: with this screen hosted in the library's window chain it swapped the player in
    # as a hosted shell, and the player's own Stop button (stopButtonClicked(), musicplayer.py - a
    # plain doClose(), no chain pop) then left the host's _next still pointing at the player, so
    # its _open() loop built a fresh one with the same kwargs, whose play() restarted from the
    # start. Only Back popped the chain properly - hence Stop working from an un-hosted Album
    # screen and not from a hosted one (live, 2026-09-18).
    def playButtonClicked(self, shuffle=False):
        # The album itself, so the queue is the whole album from its first track. plexnet drops
        # the start key when shuffling, which is what we want here.
        pq = playqueue.createPlayQueueForItem(self.album, options={'shuffle': shuffle})
        if not pq:
            util.DEBUG_LOG('AlbumWindow: no play queue for {}', self.album)
            return
        self.processCommand(opener.open(pq))

    def trackPanelClicked(self):
        mli = self.trackListControl.getSelectedItem()
        if not mli:
            return

        # No album= kwarg: opener queues the track's own album and starts on the track, which is
        # this album, in album order - the same thing it does for a track clicked in the library's
        # Tracks list view or in a hub.
        self.processCommand(opener.trackClicked(mli.dataSource))

    def updateProperties(self):
        # The shared background path (kodigui.BaseWindow), same as Movies/Shows/Seasons/Artist:
        # it drives the 4-corner tinted panel from the item's own ultraBlurColors - which Audio
        # items do carry (Audio._setData(), plexnet/audio.py) - crossfades between items, and sets
        # the hero art at opacity=100. Was a bare setProperty('background', ...) here, which got the
        # art but never the colour panel, so this screen sat on the flat default tint while every
        # other detail screen picked up the item's own.
        #
        # Art resolution differs slightly as a result: this path falls back art -> parentArt ->
        # grandparentArt, so an album with no art of its own now shows the artist's rather than
        # nothing. Honours the dynamic-backgrounds setting too, again like those screens - with it
        # off, the background stays whatever the default is instead of being set from the album.
        self.updateBackgroundFrom(self.album)
        self.setProperty('album.thumb', self.album.thumb.asTranscodedImageURL(*self.THUMB_SQUARE_DIM))
        self.setProperty('artist.title', self.album.parentTitle or '')
        self.setProperty('album.title', self.album.title)
        self.setProperty('album.meta', self.albumMetaLine())
        self.setProperty('summary', util.summaryForBox(self.album.get('summary')))

    def albumMetaLine(self):
        """The header's second meta line: release date, then genres, bullet-separated.

        Date and separator both follow the TV episode meta row (setItemInfo(), episodes.py): the
        date reads "1 Sep, 2026" - day, abbreviated month, year, with no leading zero on the day -
        and the fields are joined with " • " rather than a slash, the same bullet that row and
        the photo meta lines use. asDatetime() with no format string returns a real datetime, so
        dt.day drops the leading zero on its own (util.cleanLeadingZeros can't: its regex needs a
        preceding space, having been built for a zero appearing mid-string).

        Falls back to the bare year where the server has no full date, and each part is optional -
        an album with neither renders an empty line rather than a stray separator.
        """
        date = ''
        try:
            dt = self.album.originallyAvailableAt.asDatetime()
            if dt:
                date = u'{0} {1}'.format(dt.day, dt.strftime('%b, %Y'))
        except:
            pass
        if not date:
            date = self.album.year or ''

        try:
            genres = [g.tag for g in util.removeDups(self.album.genres())][:6]
        except:
            genres = []

        return u' • '.join([part for part in [date] + genres if part])

    def createListItem(self, obj):
        mli = kodigui.ManagedListItem(obj.title, data_source=obj)
        mli.setProperty('track.number', str(obj.index) or '')
        mli.setProperty('track.duration', util.simplifiedTimeDisplay(obj.duration.asInt()))
        return mli

    #@busy.dialog()
    def fillTracks(self):
        """Fill the track list, one header row per disc.

        Every album gets at least one header (is.header, rendered by
        includes/album_track_row.xml.tpl as a bare heading with no pill): a single-disc album's
        reads "12 tracks", and each disc of a multi-disc one reads "Disc 2, 7 tracks", so the count
        always sits with the rows it counts rather than in a heading above the whole list.

        Tracks are grouped up front rather than headers being back-filled as a new disc number
        appears, which is what the previous version did - it had to insert "Disc 1" retroactively at
        position 0 the moment it first saw a disc 2, and couldn't know any disc's length until it
        had passed it, which a per-disc count needs.

        checkForHeaderFocus() (above) is what keeps these rows from being landable: it re-issues the
        move that arrived on one. That already ran for multi-disc albums; single-disc albums now
        have a header too, and the first one sits at the top of the list, where onFirstInit()'s own
        MOVE_DOWN call steps off it.
        """
        discs = []
        for track in self.album.tracks():
            disc = track.parentIndex.asInt()
            if not discs or discs[-1][0] != disc:
                discs.append((disc, []))
            discs[-1][1].append(track)

        multiDisc = len(discs) > 1
        items = []
        idx = 0

        for disc, discTracks in discs:
            count = len(discTracks)
            countText = (T(35073, '{} tracks') if count != 1 else T(35074, '{} track')).format(count)
            header = T(35075, 'Disc {0}, {1}').format(disc, countText) if multiDisc else countText
            items.append(kodigui.ManagedListItem(header, properties={'is.header': '1'}))

            for track in discTracks:
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

        self.trackListControl.replaceItems(items)
