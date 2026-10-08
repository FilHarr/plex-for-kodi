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
The items are in memory, and a group goes into the grid whole (GroupPaginator).

CreditsGridWindow is the first: a film's or show's every credit, from the Cast & Crew row."""
from __future__ import absolute_import

from lib import util
from lib.util import T
from . import collection
from . import credits
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
