# coding=utf-8
from __future__ import absolute_import

import json

from kodi_six import xbmcgui

from lib import util
from lib.util import T
from plexnet import plexapp
from . import home
from . import kodigui
from . import pagination
from . import preplay
from . import search
from . import windowutils
from .mixins.common import CommonMixin
from .mixins.tasks import TasksMixin

# Movement actions that can land the grid selection on a paginator boundary sentinel - same set
# library.py's MOVE_SET (library.py:47-58) covers, just not imported from there (BoundedGridWindow
# deliberately doesn't depend on library.py at all).
MOVE_SET = frozenset((
    xbmcgui.ACTION_MOVE_LEFT, xbmcgui.ACTION_MOVE_RIGHT, xbmcgui.ACTION_MOVE_UP, xbmcgui.ACTION_MOVE_DOWN,
    xbmcgui.ACTION_PAGE_UP, xbmcgui.ACTION_PAGE_DOWN,
))

# Matches library.py's THUMB_POSTER_DIM/ART_AR16X9_DIM (library.py:63,66) - same tile markup is
# lifted from script-plex-posters.xml.tpl, so the same fetch dimensions apply.
THUMB_DIM = util.scaleResolution(268, 402)
ART_DIM = util.scaleResolution(630, 355)
# Matches the clearlogo/title box size script-plex-recommended.xml.tpl's own focused-hub-item
# overlay uses (script-plex-recommended.xml.tpl:445,459) - the info panel is now sized to match
# that overlay directly, not a from-scratch size (the collection poster inset this used to sit
# beside was dropped per direct feedback).
CLEAR_LOGO_DIM = util.scaleResolution(616, 109)


class BoundedGridPaginator(pagination.MCLPaginator):
    """Shared paginator shape for BoundedGridWindow's grid - one bounded fetch (getData() returns
    a real, already-populated page from the server, no chunk-cache/placeholder-then-hydrate split
    the way LibraryWindow's ChunkRequestTask/CreateDefaultItemsTask need - see hashed-orbiting-
    pizza.md's Phase 4). CollectionWindow/SubDirWindow each just override getData()."""
    initialPageSize = 60
    pageSize = 60
    orphans = 12

    def createListItem(self, data):
        mli = super(BoundedGridPaginator, self).createListItem(data)
        self.parentWindow.setItemInfo(data, mli)
        return mli

    def prepareListItem(self, data, mli):
        self.parentWindow.setWatchedInfo(data, mli)

    def jumpToPosition(self, pos):
        """Load and select whichever page contains absolute position `pos` directly - for
        BoundedGridWindow._selectInitialItem() restoring a position beyond the initial page (see
        its own docstring). Unlike nextPage()/initialPage() (built for boundary-sentinel-triggered
        sliding, one page-worth at a time in a known direction inferred from self._direction),
        this targets an arbitrary absolute index in one fetch, centered so ordinary left/right
        scrolling from the restored position works normally afterward either way.

        Returns True if it positioned the control on a real item, False if `pos` is out of range
        or the fetch came back empty - the caller should fall back to its own default then."""
        if not (0 <= pos < self.leafCount):
            return False

        amount = self.pageSize + self.orphans
        offset = max(0, pos - amount // 2)
        if offset + amount > self.leafCount:
            offset = max(0, self.leafCount - amount)

        self.offset = offset
        self._direction = None
        data = self.getData(offset, amount)
        if not data:
            return False

        self._lastAmount = self._currentAmount
        self._currentAmount = len(data)
        self.populate(data)

        # A left-boundary sentinel occupies control index 0 whenever this page doesn't start at
        # the real beginning of the list (moreLeft, populate()'s own condition) - same "+1" shift
        # MCLPaginator.selectItem()'s own "left" branch (pagination.py) accounts for.
        relative = pos - offset + (1 if offset > 0 else 0)
        if not (0 <= relative < self.control.size()):
            return False
        self.control.selectItem(relative)
        return True


class CollectionPaginator(BoundedGridPaginator):
    def getData(self, offset, amount):
        return self.parentWindow.collection.all(offset, amount)


class BoundedGridWindow(kodigui.ControlledWindow, windowutils.UtilMixin, windowutils.SidebarMixin,
                         CommonMixin, TasksMixin):
    """Bounded grid view for a curated/incidental set of items - a Collection's own members
    (CollectionWindow), or a folder browsed within a movie section (SubDirWindow, not yet built).

    Deliberately NOT shaped like library.py's LibraryWindow - no LibrarySettings, no sort/filter,
    no view-type toggle, no chunk-cache/CreateDefaultItemsTask. Shaped instead like episodes.py's
    EpisodesWindow: a plain bounded content view with sidebar chrome and nothing else. See
    hashed-orbiting-pizza.md's Phase 4 for the full reasoning - this class exists because a
    collection/subDir view leans on very little of LibraryWindow beyond "show items in a grid",
    and dragging in the rest (persisted per-section settings, tab row, chunk-cache) turned out to
    be the real cost of folding these into the descendant-container work, not a design-mechanism
    gap.
    """
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    # Real NAV_BACK dismiss, not just the flag-flip ControlledBase.close() does - same reasoning
    # as PrePlayWindow/EpisodesWindow (kodigui.ControlledWindow.onAction()'s own comment): without
    # this the window can linger on the stack and swallow input after a genuine back-out.
    dismissOnClose = True

    GRID_ID = 101

    def __init__(self, *args, **kwargs):
        kodigui.ControlledWindow.__init__(self, *args, **kwargs)
        TasksMixin.__init__(self)
        self.exitCommand = None
        self.parentList = kwargs.get('parent_list')

        # Sidebar entry-section persistence - same contract as every other descendant shell
        # (PrePlayWindow/EpisodesWindow/ShowWindow); resolved once here from whatever ancestor
        # passed it down, falling back to this item's own real section when this is itself a
        # genesis point. Subclasses finish this fallback (they know how to resolve their own
        # "real section") in their own __init__, after calling this one.
        self.entrySectionId = kwargs.get('entry_section_id')
        self.entryFromWatchlist = kwargs.get('entry_from_watchlist', False)

        self.gridControl = None
        self.sectionList = None
        self.paginator = None
        self.initialized = False
        self.lastItem = None
        self.lastFocusID = None

        # library.py's LibraryWindow._captureHostedShellRestoreState()/popBack() thread this
        # through when reconstructing this shell for a Back landing back on it, so setup() can
        # restore the item that was focused when a chain left here, instead of always defaulting
        # to item 0 (_selectInitialItem() below). None on every other, non-restoring construction
        # (a genuine fresh entry, or a forward swap to a different shell) - same as no kwarg
        # passed at all.
        self._restoreItemPos = kwargs.get('_restoreItemPos')

    def onFirstInit(self):
        self.gridControl = kodigui.ManagedControlList(self, self.GRID_ID, 5)
        if self.sectionList is None:
            self.sectionList = kodigui.ManagedControlList(self, self.SECTION_LIST_ID, 15)
            self.buildSectionList()
        else:
            self.sectionList.newControl(self)
        self.displayServerAndUser()
        self.setup()
        self.setBoolProperty('initialized', True)
        self.initialized = True

    def onAction(self, action):
        controlID = self.getFocusId()

        # checkSectionItem() must run from onAction() too, not just onFocus() - Kodi only fires
        # onFocus() on a control-level focus change, not as the selected item within an already-
        # focused list changes while arrowing through it. Without this, settling on a different
        # sidebar section while already inside the list never got noticed - live-confirmed as
        # "focus navigation doesn't trigger at all". Same pattern as preplay.py's own onAction()
        # (preplay.py:250-251).
        if controlID == self.SECTION_LIST_ID:
            self.checkSectionItem(action=action)

        if controlID == self.GRID_ID and action.getId() in MOVE_SET:
            # paginate() itself calls populate(), which fully repopulates gridControl - no
            # separate reload step needed (unlike EpisodesWindow, there's no per-item async
            # detail-refresh pass here; getData() already returns real, display-ready objects -
            # see BoundedGridPaginator).
            if self.paginator and self.paginator.boundaryHit:
                self.paginator.paginate()
            # Mirrors library.py's own MOVE_SET handling (library.py:1955-1982) - keep the
            # background/ultrablur tint in sync with whatever's actually focused, not stuck on
            # whatever setup() set it to once at open time.
            mli = self.gridControl.getSelectedItem()
            if mli and mli.dataSource is not None:
                self.updateBackgroundFrom(mli.dataSource)
        kodigui.ControlledWindow.onAction(self, action)

    def onClick(self, controlID):
        if self.handleSidebarDropdownClick(controlID):
            return
        if controlID == self.GRID_ID:
            self.itemClicked()
        elif controlID == self.SECTION_LIST_ID:
            self.sectionClicked()

    def onFocus(self, controlID):
        # reselectActiveSection() (SidebarMixin) snaps the highlight to the section actually on
        # screen (is.active in buildSectionList()) instead of leaving it wherever the list's
        # internal cursor last was - index 0 (Search) on a window's first focus event, which is
        # exactly what was showing up. Needs the PREVIOUS focus id, so this must read
        # self.lastFocusID before overwriting it, not after. Never wired up before now.
        self.reselectActiveSection(controlID, self.lastFocusID)
        self.lastFocusID = controlID

        if controlID == self.SECTION_LIST_ID:
            self.checkSectionItem()

    def setup(self):
        raise NotImplementedError

    def createListItem(self, data):
        # Base construction only (empty label, dataSource wired up) - the paginator's own
        # createListItem() calls this via MCLPaginator.createListItem()'s default delegation
        # (pagination.py:48-49), then immediately calls setItemInfo() to fill in the rest. Mirrors
        # EpisodesWindow.createListItem() (episodes.py:1727-1731)'s identical split.
        return kodigui.ManagedListItem('', data_source=data)

    def setItemInfo(self, data, mli):
        # Shared by CollectionWindow and SubDirWindow - genuinely generic, not collection-specific:
        # handles the same movie/show/nested-collection/plain-directory mix either shell's grid can
        # contain. defaultTitle/defaultThumb/defaultArt are all base PlexObject-level fallbacks
        # (plexobjects.py), so this works unchanged for a Generic/TYPE=='Directory' folder entry too.
        mli.setLabel(data.defaultTitle)
        mli.setProperty('summary', util.widenParagraphBreaks(data.get('summary')))
        if data.TYPE == 'collection':
            # Collections often have no own poster - fall back to a composite of member posters,
            # same as library.py's _chunkCallback() (library.py:4071-4076) and the dead-code
            # createCollectionListItem() (library.py:5291-5294) both already do.
            mli.setThumbnailImage(data.artCompositeURL(*THUMB_DIM))
        else:
            mli.setThumbnailImage(data.defaultThumb.asTranscodedImageURL(*THUMB_DIM))
            mli.setProperty('art', data.defaultArt.asTranscodedImageURL(*ART_DIM))
        if not data.isDirectory() and data.get('duration').asInt():
            mli.setLabel2(util.durationToText(data.fixedDuration()))

    def setWatchedInfo(self, data, mli):
        # Mirrors library.py's _chunkCallback() generic-item branch (library.py:4098-4105) -
        # proven-correct shape for the same heterogeneous movie/show/directory mix, minus the
        # LibraryWindow-specific sort-column/chunk-cache bits. TYPE == 'Directory' (the class-level
        # type, matching production exactly), NOT isDirectory() (the tag-name-based method) - shows
        # and seasons are also tag-shaped like a Directory in Plex's API (they're containers, not
        # playable items) but have a real registered TYPE ('show'/'season') and DO want a badge via
        # the unwatched.count branch below - isDirectory() was wrongly excluding them entirely.
        # Live-confirmed: this class of bug is exactly what silently broke show-clicking too, see
        # itemClicked()'s own note.
        if data.TYPE == 'Directory':
            return
        if not data.isWatched:
            if data.TYPE == 'show' or data.TYPE == 'season':
                # No .asInt() here - unlike Episode's unViewedLeafCount (PlexValue, episodes.py:120
                # calls .asInt() on it), Show/Season's is a plain Python int already - live-confirmed
                # via a real AttributeError doing exactly what episodes.py's pattern does. Matches
                # library.py's own identical show/season branch (library.py:4101) exactly, which
                # never called .asInt() here either - should have just copied that directly instead
                # of borrowing episodes.py's shape for a different underlying type.
                mli.setProperty('unwatched.count', str(data.unViewedLeafCount))
                mli.setBoolProperty('unwatched.count.large', data.unViewedLeafCount > 999)
            else:
                mli.setProperty('unwatched', '1')
        elif data.isFullyWatched:
            mli.setBoolProperty('watched', '1')
        mli.setProperty('progress', util.getProgressImage(data))

    def itemClicked(self):
        """Scoped version of library.py's showPanelClicked() dispatch (library.py:3366-3482) -
        only the four cases actually reachable from inside a collection/subDir: a real movie/show,
        another (nested) collection, or (SubDirWindow only) another folder. Not photo/artist/
        album/track/playlists - those aren't reachable from a folder-browsed movie section or a
        movie/show collection in practice; see the plan's own note on this assumption."""
        mli = self.gridControl.getSelectedItem()
        if not mli or mli.dataSource is None:
            return

        data = mli.dataSource
        extra_kwargs = {
            'entry_section_id': self.entrySectionId,
            'entry_from_watchlist': self.entryFromWatchlist,
        }

        # TYPE checks first, isDirectory() (tag-shape, not class-level type) last - live-confirmed
        # bug: shows come back from Plex's API as <Directory type="show">, so isDirectory() is
        # True for them too. Checking it before TYPE == 'show' meant every show silently matched
        # the directory branch (openDirectory(), a no-op stub reserved for SubDirWindow) instead -
        # nothing opened, nothing threw, so nothing logged either. library.py's own
        # showPanelClicked() already gets this ordering right (library.py:3420-3429) - isDirectory()
        # only ever gets checked *inside* the movie-type branch there, after collection/show/season/
        # episode have already been ruled out, which is what makes it safe to use as a fallback.
        if data.TYPE == 'collection':
            self.openWindow(CollectionWindow, collection=data, **extra_kwargs)
        elif data.TYPE == 'show':
            # self.openItem() (opener.open() -> opener.showClicked(), context=self), not a direct
            # self.openWindow(subitems.ShowWindow, ...) - see library.py's own showPanelClicked()
            # comment (identical fix, same live-confirmed skipChildren-bypass gap) for why.
            self.openItem(data, parent_list=self.gridControl, **extra_kwargs)
        elif data.isDirectory():
            self.openDirectory(data, extra_kwargs)
        else:
            self.openWindow(preplay.PrePlayWindow, video=data, parent_list=self.gridControl,
                            **extra_kwargs)

    def _selectInitialItem(self):
        """Shared tail of both CollectionWindow.setup() and SubDirWindow.setup(), called right
        after self.paginator.paginate()'s initial-page load: selects self._restoreItemPos
        (an *absolute* list position - library.py's _captureHostedShellRestoreState()) when
        there's a valid one pending, otherwise item 0 - the plain, always-item-0 behavior both had
        before this existed.

        self.paginator._currentAmount (set by the paginate() call that always immediately
        precedes this) is the real item count on the just-loaded initial page (offset always 0
        here, so a control-relative index and an absolute one are the same thing), excluding the
        right-boundary sentinel MLI populate() may have appended - selecting that sentinel instead
        of a real item would be a real, if harmless-looking, bug (it's a focusable `is.boundary`
        item, not the grid item the position was actually captured against).

        A position beyond that initial page (live-reported, 2026-09-03: "put back to item 0" for
        anything only reached by scrolling the paginator further) falls to
        BoundedGridPaginator.jumpToPosition() instead - a direct, one-fetch jump to whichever page
        actually contains it, rather than the cheap in-page select above. Only once *that* also
        fails (position no longer exists at all, e.g. the collection changed) does this fall back
        to item 0, same as always."""
        pos = self._restoreItemPos
        if pos is not None and 0 <= pos < self.paginator._currentAmount:
            self.gridControl.selectItem(pos)
        elif pos is not None and self.paginator.jumpToPosition(pos):
            pass
        else:
            self.gridControl.selectItem(0)

    def openDirectory(self, data, extra_kwargs):
        """Hook: only SubDirWindow (see its own override below) needs to open a further subfolder -
        a CollectionWindow's own members should never themselves be plain directories. Left as a
        no-op here rather than NotImplementedError, since reaching this from a real collection
        would indicate unexpected server data, not a programming error."""
        pass

    def searchButtonClicked(self):
        self.processCommand(search.dialog(self, section_id=self.entrySectionId or None))

    def buildSectionList(self):
        """Populate the sidebar's section list - verbatim copy of preplay.py's own
        buildSectionList() (preplay.py:387-469), itself already duplicated (not shared) across
        library.py/episodes.py/preplay.py - see preplay.py's own docstring for why."""
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

        activeSectionId = self.entrySectionId
        activeSection = None
        if activeSectionId:
            for section in sections:
                if section.key == activeSectionId:
                    activeSection = section
                    break
        if activeSection is None and self.entryFromWatchlist:
            activeSection = home.watchlist_section

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
            if section == activeSection:
                mli.setProperty('is.active', '1')
            items.append(mli)

        self.sectionList.reset()
        self.sectionList.addItems(items)

    def displayServerAndUser(self):
        """Sidebar avatar/username and server icon/name - verbatim copy of preplay.py's own
        displayServerAndUser() (preplay.py:474-497)."""
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


class CollectionWindow(BoundedGridWindow):
    xmlFile = 'script-plex-collection.xml'

    def __init__(self, *args, **kwargs):
        BoundedGridWindow.__init__(self, *args, **kwargs)
        self.collection = kwargs.get('collection')
        if self.entrySectionId is None and not self.entryFromWatchlist:
            self.entrySectionId = self.collection.getLibrarySectionId()

    def setup(self):
        # summary/childCount read via .get() (raw XML attribute access, PlexValue-wrapped), same
        # convention library.py's _chunkCallback() uses for the same kind of field - live-confirmed
        # against a real server response (2026-08-24): both populate correctly.
        self.setProperty('collection.title', self.collection.title)
        self.setProperty('collection.summary', util.widenParagraphBreaks(self.collection.get('summary')))
        # Same clearlogo-with-title-fallback pattern as PrePlayWindow/EpisodesWindow - the template
        # shows whichever of the two sibling controls matches whether this property is empty, not
        # a Python-side branch. util.clearLogoFrom() itself already returns '' safely when the
        # collection has no clearLogo field at all (most won't - see its own docstring).
        self.setProperty('clear.logo', util.clearLogoFrom(self.collection, *CLEAR_LOGO_DIM))

        self.updateBackgroundFrom(self.collection)

        leafCount = self.collection.get('childCount').asInt()

        self.paginator = CollectionPaginator(self.gridControl, parent_window=self, leaf_count=leafCount)
        self.paginator.paginate()
        self._selectInitialItem()
        # Explicit, not relied on via XML <defaultcontrol> - default.xml.tpl's own window-level
        # defaultcontrol (default.xml.tpl:12, the header Home button) wins over a nested one
        # declared on a content group, same reason episodes.py's own template has an abandoned,
        # commented-out attempt at exactly this (script-plex-episodes.xml.tpl:39). Mirrors
        # library.py's doRefill()/fill() doing the identical self.setFocusId(POSTERS_PANEL_ID)
        # after populating its own grid (library.py:3683-3684).
        self.setFocusId(self.GRID_ID)


def buildSubDirSection(section, datasource):
    """Synthetic, folder-scoped section for one directory click - identical construction to what
    library.py's showPanelClicked() used to build inline before SubDirWindow existed. `section` is
    whatever section this folder was reached from (a real section for the first hop out of a real
    LibraryWindow, or an already-synthetic one when SubDirWindow.openDirectory() drills further);
    `datasource` is the clicked Directory item whose own key becomes the new section's key. Shared
    so both callers build the exact same shape rather than keeping two copies in sync - see
    hashed-orbiting-pizza.md's Phase 4 "SubDirWindow" notes.
    """
    cls = section.__class__
    newSection = cls(section.data, section.initpath, section.server, section.container)
    sectionId = newSection.key
    if not sectionId.isdigit():
        sectionId = newSection.getLibrarySectionId()
    newSection.set('librarySectionID', sectionId)
    newSection.key = datasource.key
    newSection.title = datasource.title
    return newSection


class SubDirPaginator(BoundedGridPaginator):
    def getData(self, offset, amount):
        return self.parentWindow.section.folder(offset, amount, subDir=True)


class SubDirWindow(BoundedGridWindow):
    xmlFile = 'script-plex-subdir.xml'

    def __init__(self, *args, **kwargs):
        BoundedGridWindow.__init__(self, *args, **kwargs)
        self.section = kwargs.get('section')
        if self.entrySectionId is None and not self.entryFromWatchlist:
            self.entrySectionId = self.section.getLibrarySectionId()

    def setup(self):
        # No info panel/title - a subDir folder has no comparable metadata to a Collection's
        # summary/childCount/clearLogo, per the plan's own decision on this.
        leafCount = self.section.folder(0, 0, subDir=True).totalSize.asInt()

        self.paginator = SubDirPaginator(self.gridControl, parent_window=self, leaf_count=leafCount)
        self.paginator.paginate()
        self._selectInitialItem()
        # Same explicit-focus requirement as CollectionWindow.setup() - see its own comment for why
        # the XML <defaultcontrol> alone doesn't reliably win initial window focus here.
        self.setFocusId(self.GRID_ID)

        # No single owning item to seed the background from (unlike CollectionWindow's own
        # self.collection) - seed it from whatever the grid's own initial selection turned out to
        # be instead, same as the MOVE_SET re-tint BoundedGridWindow.onAction() already does on
        # every subsequent focus change.
        mli = self.gridControl.getSelectedItem()
        if mli and mli.dataSource is not None:
            self.updateBackgroundFrom(mli.dataSource)

    def openDirectory(self, data, extra_kwargs):
        self.openWindow(SubDirWindow, section=buildSubDirSection(self.section, data), **extra_kwargs)
