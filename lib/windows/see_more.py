# coding=utf-8
"""The "See more" grid: every item behind a row's "See more" tile, in that row's own tile, under
a title (spec: ~/.claude/plans/see-all-grid.md, agreed 2026-10-08).

One window class for every row that has the tile, on collection.BoundedGridWindow - a plain
bounded grid with the sidebar, no sort or filter. A subclass per tile shape (each its own XML,
see_more.xml.tpl's children) says what the grid holds:
  - title(): the heading
  - groups(): [(label, [item])] - a button per named group over the grid (Cast / Crew); a
    single group with no label has none
  - createListItem(), itemClicked(): an item's tile and what selecting it opens

CreditsGridWindow: a film's or show's every credit, from the Cast & Crew row - in memory, a group
going into the grid whole (GroupPaginator).
HubGridWindow (Poster/Poster3/SquareGridWindow): a Recommended row's every item, from its "See
more" tile - from the server, a chunk at a time into a grid of placeholders, as the library grid."""
from __future__ import absolute_import

import threading

from lib import util
from lib.util import T
from plexnet import plexobjects
from . import collection
from . import credits
from . import grid_labels
from . import hub_limits
from . import kodigui
from . import opener


class GroupPaginator(collection.BoundedGridPaginator):
    """The group shown (SeeMoreWindow.groupItems), whole: it's in memory, and paging it - a
    boundary item at the 60th, the next page loaded with the grid back at its top - read as the
    grid wrapping round (live, 2026-10-08). The tile is all createListItem()'s - no
    BoundedGridPaginator item info or watch state on top."""
    def __init__(self, control, parent_window, leaf_count):
        collection.BoundedGridPaginator.__init__(self, control, parent_window=parent_window,
                                                 leaf_count=leaf_count)
        self.initialPageSize = max(leaf_count, 1)

    def getData(self, offset, amount):
        return self.parentWindow.groupItems[offset:offset + amount]

    def createListItem(self, data):
        return self.parentWindow.createListItem(data)

    def prepareListItem(self, data, mli):
        pass


class SeeMoreWindow(collection.BoundedGridWindow):
    # The background stays the screen's own item's (backgroundItem()), not the focused tile's
    BACKGROUND_FOLLOWS_FOCUS = False
    # One per group, see_more.xml.tpl's grouplist 910 - clear of the sidebar's user menu group
    # (901), as the Filmography screen's type buttons are
    GROUP_BUTTON_IDS = (911, 912, 913, 914)

    def __init__(self, *args, **kwargs):
        collection.BoundedGridWindow.__init__(self, *args, **kwargs)
        # The group shown, an index - kept through Back (restoreState())
        self.group = kwargs.get('group') or 0
        self._groups = []
        self.groupItems = []

    def title(self):
        raise NotImplementedError

    def groups(self):
        raise NotImplementedError

    def setup(self):
        self.setProperty('grid.title', self.title())
        self._groups = [group for group in self.groups() if group[1]][:len(self.GROUP_BUTTON_IDS)]
        # A button for every named group, even one alone ("Cast (9)" for a show without crew): the
        # buttons' place under the title is part of the page (see_more.xml.tpl)
        self.setBoolProperty('grid.groups', any(group[0] for group in self._groups))
        if not 0 <= self.group < len(self._groups):
            self.group = 0
        self.showGroup(self.group)
        self.setFocusId(self.GRID_ID)

    def showGroup(self, index):
        """The group's items in the grid, from its first - or, rebuilt by Back, from the item Back
        left (BoundedGridWindow._selectInitialItem(), once)."""
        self.group = index
        self.labelGroupButtons()
        self.groupItems = self._groups[index][1] if self._groups else []
        self.paginator = GroupPaginator(self.gridControl, parent_window=self, leaf_count=len(self.groupItems))
        if not self.groupItems:
            self.gridControl.reset()
            return
        self.paginator.paginate()
        self._selectInitialItem()
        self._restoreItemPos = None

    def labelGroupButtons(self):
        """"Cast (9)", the group shown in the sidebar's active orange, as the Filmography screen's
        type buttons are labelled (FilmographyWindow.labelTypeButtons()); '' hides a button."""
        for i in range(len(self.GROUP_BUTTON_IDS)):
            label = ''
            if i < len(self._groups) and self._groups[i][0]:
                label = u'{0} ({1})'.format(self._groups[i][0], len(self._groups[i][1]))
                if i == self.group:
                    label = u'[COLOR FFE5A00D]{0}[/COLOR]'.format(label)
            self.setProperty('group.{0}.label'.format(i), label)

    def restoreState(self):
        """What Back rebuilds this screen with (LibraryWindow._captureHostedShellRestoreState()):
        the group shown and the item focused in it, as an absolute position - the paginator only
        holds a page, with a boundary item first when it isn't the first page."""
        state = {'group': self.group}
        if self.paginator is not None and self.gridControl:
            mli = self.gridControl.getSelectedItem()
            if mli and not mli.getProperty('is.boundary'):
                relative = mli.pos()
                if self.paginator.offset > 0:
                    relative -= 1
                state['_restoreItemPos'] = self.paginator.offset + relative
        return state

    def handleBack(self):
        """Back while down the grid goes to its first item before it leaves the screen, as the
        library grid's does (GridMixin.gridBack()), on request (2026-10-08). The host asks this
        before popping the chain (kodigui.BaseWindow.handleBack())."""
        if self.getFocusId() != self.GRID_ID or not self.gridControl:
            return False
        mli = self.gridControl.getSelectedItem()
        if not mli or not mli.pos():
            return False
        self.gridControl.selectItem(0)
        return True

    def onClick(self, controlID):
        if controlID not in self.GROUP_BUTTON_IDS:
            collection.BoundedGridWindow.onClick(self, controlID)
            return
        # Not live, or a sidebar click (kodigui.BaseWindow.routeClickToHost()), as the base's own
        if self.routeClickToHost(controlID):
            return
        index = self.GROUP_BUTTON_IDS.index(controlID)
        if index < len(self._groups) and index != self.group:
            self.showGroup(index)


class CreditsGridWindow(SeeMoreWindow):
    """A film's or show's every credit, Cast or Crew, from its Cast & Crew row's "See more" tile
    (RolesMixin.seeMoreCredits()) - the list the row was filled from (credits.cachedForItem()),
    so nothing is asked for. Its tile is the row's own (includes/role_tile.xml.tpl)."""
    xmlFile = 'script-plex-see_more_credits.xml'
    # The rows' own (preplay.py, subitems.py)
    ROLES_DIM = util.scaleResolution(334, 334)

    def __init__(self, *args, **kwargs):
        SeeMoreWindow.__init__(self, *args, **kwargs)
        self.item = kwargs.get('item')
        if self.entrySectionId is None and not self.entryFromWatchlist:
            self.entrySectionId = self.item.getLibrarySectionId()

    def backgroundItem(self):
        # The film's or show's own art from the first frame, as the screen it came from shows it
        return self.item

    def title(self):
        return self.item.title or ''

    def groups(self):
        itemCredits = credits.cachedForItem(self.item)
        return [(T(32419, 'Cast'), itemCredits.cast), (T(35166, 'Crew'), itemCredits.crew)]

    def setup(self):
        self.updateBackgroundFrom(self.item)
        SeeMoreWindow.setup(self)

    def createListItem(self, role):
        """The row's tile (RolesMixin.fillCreditsRow()): the name, and the character or job."""
        return kodigui.ManagedListItem(role.tag, role.role or util.TRANSLATED_ROLES[role.translated_role],
                                       thumbnailImage=role.thumb.asTranscodedImageURL(*self.ROLES_DIM),
                                       data_source=role)

    def itemClicked(self):
        """The person screen, as from the row (RolesMixin.roleClicked())."""
        mli = self.gridControl.getSelectedItem()
        if not mli or mli.dataSource is None:
            return
        self.processCommand(opener.open(mli.dataSource, context=self, section_id=self.entrySectionId,
                                        from_watchlist=self.entryFromWatchlist))


class HubGridWindow(SeeMoreWindow):
    """A Recommended row's every item, from its "See more" tile (LibraryWindow.hubSeeMoreClicked()):
    the row's whole list from the server - as far as hub_limits lets it reach: a Recently Released or
    Watched row's window, a Recently Added row's number - in the row's tile shape, with the grid's own
    caption lines (grid_labels). No group buttons: the title is the row's, as the row shows it.

    Such a list runs to hundreds, so it's the library grid's way rather than the credits': every
    position an empty tile at once (setup()), and the items fetched a chunk at a time, the first
    where focus starts and the rest as it moves (_requestAround(), library_grid.ChunkRequestTask's
    way)."""
    # No hero art, only the colour panel, from the focused item - the library grid's background
    # (on request, 2026-10-09; the credits grid keeps its film's or show's art): onAction() and
    # _fetchChunk(), not BoundedGridWindow's updateBackgroundFrom(), which paints the art too
    BACKGROUND_FOLLOWS_FOCUS = False
    CHUNK_SIZE = 60
    # How far past the focused item a chunk is asked for: two rows of six, so the next screenful is
    # there before it's reached
    CHUNK_AHEAD = 12
    # The rows' own (LibraryWindow.THUMB_POSTER_DIM / THUMB_SQUARE_DIM)
    THUMB_DIM = util.scaleResolution(240, 360)
    FALLBACKS = {
        'movie': 'movie', 'clip': 'movie', 'show': 'show', 'season': 'show', 'episode': 'show',
        'album': 'music', 'artist': 'music', 'track': 'music', 'photo': 'photo', 'playlist': 'movie',
        'collection': 'movie',
    }
    VIDEO_TYPES = ('movie', 'clip', 'show', 'season', 'episode')

    def __init__(self, *args, **kwargs):
        SeeMoreWindow.__init__(self, *args, **kwargs)
        self.hub = kwargs.get('hub')
        self.rowTitle = kwargs.get('title') or self.hub.title or ''
        self.base = hub_limits.baseIdentifier(self.hub)
        self.total = 0
        self._requested = set()
        self._fillLock = threading.Lock()

    def title(self):
        return self.rowTitle

    def groups(self):
        return []

    @property
    def gridKey(self):
        return self.hub.__dict__.get('gridKey') or self.hub.key

    def count(self):
        """How many the grid holds: the list's own total (a size-0 request), no more than a
        Recently Added row's limit (hub.gridMax)."""
        try:
            data = self.hub.server.query(self.gridKey, limit=0)
        except Exception as e:
            util.DEBUG_LOG('See more: no count for {0}: {1}', self.gridKey, e)
            return 0
        total = data.attrib.get('totalSize') if data is not None else None
        total = int(total) if total is not None else len(self.hub.items)
        gridMax = self.hub.__dict__.get('gridMax')
        return min(total, gridMax) if gridMax is not None else total

    def setup(self):
        self.setProperty('grid.title', self.rowTitle)
        self.setBoolProperty('grid.groups', False)
        self.labelGroupButtons()
        self.total = self.count()
        kind = self.hub.items[0].TYPE if self.hub.items else None
        fallback = 'script.plex/thumb_fallbacks/{0}.png'.format(self.FALLBACKS.get(kind, 'movie'))
        placeholders = []
        for pos in range(self.total):
            mli = kodigui.ManagedListItem('')
            mli.setProperty('thumb.fallback', fallback)
            mli.setProperty('index', str(pos))
            placeholders.append(mli)
        self.gridControl.reset()
        if not placeholders:
            return
        self.gridControl.addItems(placeholders)
        pos = self._restoreItemPos
        self._restoreItemPos = None
        if pos is None or not 0 <= pos < self.total:
            pos = 0
        self.gridControl.selectItem(pos)
        self.setFocusId(self.GRID_ID)
        self._requestAround(pos)

    def restoreState(self):
        """The item focused, for Back (LibraryWindow._captureHostedShellRestoreState()): every
        position is in the grid, so its position is the absolute one."""
        mli = self.gridControl.getSelectedItem() if self.gridControl else None
        return {'_restoreItemPos': mli.pos() if mli else None}

    def handleBack(self):
        # the first item's chunk, if Back to it (SeeMoreWindow.handleBack()) comes from far down
        if SeeMoreWindow.handleBack(self):
            self._requestAround(0)
            return True
        return False

    def onAction(self, action):
        SeeMoreWindow.onAction(self, action)
        if self.gridControl and self.getFocusId() == self.GRID_ID and action.getId() in collection.MOVE_SET:
            mli = self.gridControl.getSelectedItem()
            if mli:
                self._requestAround(mli.pos())
                # `is not None`: an unopened Playlist is falsy (library_grid's own note)
                if mli.dataSource is not None:
                    self.updatePanelFrom(mli.dataSource)

    def _requestAround(self, pos):
        for start in set(((pos // self.CHUNK_SIZE) * self.CHUNK_SIZE,
                          (min(pos + self.CHUNK_AHEAD, self.total - 1) // self.CHUNK_SIZE) * self.CHUNK_SIZE)):
            if start in self._requested or start >= self.total:
                continue
            self._requested.add(start)
            self.postpone_simple(self._fetchChunk, start)

    def _fetchChunk(self, start):
        """On a worker: the chunk at start, written into its placeholders."""
        size = min(self.CHUNK_SIZE, self.total - start)
        try:
            items = plexobjects.listItems(self.hub.server, self.gridKey, offset=start, limit=size)
        except Exception as e:
            util.DEBUG_LOG('See more: chunk {0} of {1} failed: {2}', start, self.gridKey, e)
            self._requested.discard(start)
            return
        try:
            with self._fillLock:
                for offset, obj in enumerate(items):
                    pos = start + offset
                    if pos >= self.total:
                        break
                    self.fillItem(self.gridControl[pos], obj)
                # the panel's first colours: the item focus starts on, once its chunk is in
                selected = self.gridControl.getSelectedPos()
                if selected is not None and start <= selected < start + len(items):
                    self.updatePanelFrom(items[selected - start])
        except kodigui.ScreenClosed:
            pass

    def fillItem(self, mli, obj):
        lines = grid_labels.lines(self.base, obj)
        mli.dataSource = obj
        mli.setLabel(lines.line1)
        mli.setLabel2(lines.line2)
        mli.setProperty('line3', lines.line3)
        if lines.rating is not None:
            mli.setProperty('rating.image', lines.rating[0])
            mli.setProperty('rating', lines.rating[1])
        mli.setThumbnailImage(self.thumbFor(obj))
        if obj.TYPE == 'photo':
            mli.setProperty('is.photo', '1')
        if obj.TYPE in self.VIDEO_TYPES:
            self.setWatchedInfo(obj, mli)

    def thumbFor(self, obj):
        w, h = self.THUMB_DIM
        if obj.TYPE == 'playlist':
            fallback = 'script.plex/thumb_fallbacks/{0}.png'.format(
                obj.playlistType == 'audio' and 'music' or 'movie')
            return obj.buildComposite(width=w, height=h, media='thumb') or util.standInThumb(fallback)
        if obj.TYPE == 'collection' and not obj.defaultThumb:
            return obj.server.getImageTranscodeURL(obj.artCompositeURL(w * 2, h * 2), w, h)
        return obj.defaultThumb.asTranscodedImageURL(w, h)

    def itemClicked(self):
        """Opens the item as its row does (LibraryWindow.hubItemClicked() - opener.open())."""
        mli = self.gridControl.getSelectedItem()
        if not mli or mli.dataSource is None:
            return
        self.processCommand(opener.open(mli.dataSource, context=self, entry_section_id=self.entrySectionId,
                                        entry_from_watchlist=self.entryFromWatchlist))


class PosterGridWindow(HubGridWindow):
    xmlFile = 'script-plex-see_more_poster.xml'


class Poster3GridWindow(HubGridWindow):
    """The poster grid of three caption lines (episode rows - grid_labels.THREE_LINE_ROWS)."""
    xmlFile = 'script-plex-see_more_poster3.xml'


class SquareGridWindow(HubGridWindow):
    xmlFile = 'script-plex-see_more_square.xml'
    THUMB_DIM = util.scaleResolution(240, 240)


def hubGridWindow(display_type, base):
    """The grid class for a row of this display type (LibraryWindow.getHubDisplayType()). A 16:9
    row's grid isn't built yet (stage 3): it opens as posters meanwhile."""
    if display_type == 'square':
        return SquareGridWindow
    if base in grid_labels.THREE_LINE_ROWS:
        return Poster3GridWindow
    return PosterGridWindow
