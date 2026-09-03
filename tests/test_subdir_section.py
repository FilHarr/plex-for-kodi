# coding=utf-8
"""
lib/windows/collection.py's buildSubDirSection() - the synthetic, folder-scoped Section a
directory click builds (library.py's showPanelClicked()) and SubDirWindow.openDirectory() reuses
to drill further (hashed-orbiting-pizza.md's Phase 4).

This is the one piece of that work with no live coverage yet: the addon's own library has no
nested folders to click through, so the two-hop (folder-within-a-folder) path has never actually
run. What makes it safe on paper is that PlexObject.data is never reassigned after construction -
each synthetic Section is rebuilt from the *original* real Section's XML, not from the previous
hop's own (already-mutated) instance - so the real numeric librarySectionID survives no matter how
many hops deep this recurses. That invariant is exactly what a live folder-less test rig can't
exercise, so it's asserted here directly instead.

Importing lib.windows.collection starts lib.player's monitor thread unless abort_requested is set
first - same guard test_dropdown.py uses for the same reason.
"""

from __future__ import absolute_import

from xml.etree import ElementTree as ET

from kodienv import ENV

ENV.abort_requested = True
from lib.windows import collection  # noqa: E402

from plexnet import plexlibrary  # noqa: E402

from .base import KodiTestCase  # noqa: E402


def _movieSection(key="3", title="Movies", library_section_id="3"):
    root = ET.fromstring(
        '<MediaContainer><Directory key="{0}" title="{1}" librarySectionID="{2}"/></MediaContainer>'
        .format(key, title, library_section_id)
    )
    return plexlibrary.MovieSection(root.find("Directory"), initpath="/library/sections/3")


def _directory(key, title):
    return plexlibrary.Generic(ET.fromstring('<Directory key="{0}" title="{1}"/>'.format(key, title)))


class BuildSubDirSectionTest(KodiTestCase):
    def test_first_hop_scopes_key_and_title_to_the_clicked_folder(self):
        section = _movieSection()
        folder = _directory("/library/sections/3/folder/abc", "Films (Drive 1)")

        synthetic = collection.buildSubDirSection(section, folder)

        self.assertEqual(folder.key, synthetic.key)
        self.assertEqual(folder.title, synthetic.title)
        self.assertEqual("3", synthetic.getLibrarySectionId())
        # A fresh, distinct instance - not a mutation of the real section object, which stays
        # reusable for the caller's own further clicks in the same session.
        self.assertIsNot(section, synthetic)
        self.assertEqual("3", section.key)

    def test_second_hop_still_resolves_the_real_library_section_id(self):
        """
        The recursive case SubDirWindow.openDirectory() exercises for a folder-within-a-folder -
        untestable live against this addon's own library (no nested folders exist there). The real
        librarySectionID must survive a second hop even though the first hop's own .key is by then
        a folder path, not a digit.
        """
        section = _movieSection()
        firstHop = collection.buildSubDirSection(section, _directory("/library/.../abc", "Films (Drive 1)"))
        self.assertFalse(firstHop.key.isdigit())

        secondHop = collection.buildSubDirSection(firstHop, _directory("/library/.../abc/def", "Extras"))

        self.assertEqual("/library/.../abc/def", secondHop.key)
        self.assertEqual("Extras", secondHop.title)
        self.assertEqual("3", secondHop.getLibrarySectionId())

    def test_a_non_numeric_starting_key_falls_back_to_librarySectionID(self):
        """
        The defensive branch (`if not sectionId.isdigit(): sectionId = newSection.
        getLibrarySectionId()`) that a real top-level movie section's own numeric key never
        actually exercises in practice (see the module docstring) - covered directly here so it
        isn't silently dead code nobody would notice breaking.
        """
        section = _movieSection(key="/library/sections/3/folder", library_section_id="3")
        self.assertFalse(section.key.isdigit())

        synthetic = collection.buildSubDirSection(section, _directory("/library/.../abc", "Films (Drive 1)"))

        self.assertEqual("3", synthetic.getLibrarySectionId())


class _FakePaginator(object):
    """For SelectInitialItemTest - only exercises _selectInitialItem()'s own three-way dispatch
    (in-page select / jumpToPosition() / fall back to 0), not jumpToPosition()'s own math (see
    JumpToPositionTest below for that, against the real BoundedGridPaginator)."""

    def __init__(self, current_amount, jump_succeeds=False):
        self._currentAmount = current_amount
        self._jump_succeeds = jump_succeeds
        self.jumpToPositionCalls = []

    def jumpToPosition(self, pos):
        self.jumpToPositionCalls.append(pos)
        return self._jump_succeeds


class _FakeGridControl(object):
    def __init__(self):
        self.selectItemCalls = []

    def selectItem(self, pos):
        self.selectItemCalls.append(pos)


class _FakeBoundedGridWindow(object):
    """A hand-built double carrying only what BoundedGridWindow._selectInitialItem() (the real,
    unbound method under test below) actually touches - same style test_library_chain.py's
    FakeHostWindow uses, not a real ControlledWindow instance."""

    _selectInitialItem = collection.BoundedGridWindow._selectInitialItem

    def __init__(self, restore_pos, current_amount, jump_succeeds=False):
        self._restoreItemPos = restore_pos
        self.paginator = _FakePaginator(current_amount, jump_succeeds=jump_succeeds)
        self.gridControl = _FakeGridControl()


class SelectInitialItemTest(KodiTestCase):
    """CollectionWindow/SubDirWindow.setup() both call this, once, right after
    self.paginator.paginate()'s initial-page load - live-reported (2026-09-03) as never
    restoring focus at all before this existed (always item 0), the counterpart to
    library.py's own grid-position restore for LibraryWindow's own showPanelControl. Then
    live-reported again the same day: a position only reached by scrolling the paginator past its
    initial page still fell back to item 0 - fixed by trying
    BoundedGridPaginator.jumpToPosition() (JumpToPositionTest below) before giving up."""

    def test_restores_the_pending_position_when_in_range(self):
        """Cheap path: the position is already within the just-loaded initial page, no extra
        fetch needed - jumpToPosition() must not even be tried."""
        shell = _FakeBoundedGridWindow(restore_pos=17, current_amount=40)

        shell._selectInitialItem()

        self.assertEqual([17], shell.gridControl.selectItemCalls)
        self.assertEqual([], shell.paginator.jumpToPositionCalls)

    def test_falls_back_to_item_zero_when_nothing_pending(self):
        shell = _FakeBoundedGridWindow(restore_pos=None, current_amount=40)

        shell._selectInitialItem()

        self.assertEqual([0], shell.gridControl.selectItemCalls)
        self.assertEqual([], shell.paginator.jumpToPositionCalls)

    def test_tries_jump_to_position_when_beyond_the_loaded_page(self):
        """A position beyond the initial page (self.paginator._currentAmount) can't be selected
        directly - falls to BoundedGridPaginator.jumpToPosition() instead of item 0. On success,
        jumpToPosition() has already done the real selection itself (see its own test) - this
        must not also call gridControl.selectItem() again on top of it."""
        shell = _FakeBoundedGridWindow(restore_pos=99, current_amount=40, jump_succeeds=True)

        shell._selectInitialItem()

        self.assertEqual([99], shell.paginator.jumpToPositionCalls)
        self.assertEqual([], shell.gridControl.selectItemCalls)

    def test_falls_back_to_item_zero_when_jump_to_position_also_fails(self):
        """jumpToPosition() itself returns False when the position no longer exists at all (e.g.
        the collection's content changed) - only then does this fall back to item 0."""
        shell = _FakeBoundedGridWindow(restore_pos=99, current_amount=40, jump_succeeds=False)

        shell._selectInitialItem()

        self.assertEqual([99], shell.paginator.jumpToPositionCalls)
        self.assertEqual([0], shell.gridControl.selectItemCalls)

    def test_falls_back_to_item_zero_for_a_negative_position(self):
        shell = _FakeBoundedGridWindow(restore_pos=-1, current_amount=40, jump_succeeds=False)

        shell._selectInitialItem()

        self.assertEqual([0], shell.gridControl.selectItemCalls)


class _FakeMLI(object):
    """Stands in for a real kodigui.ManagedListItem - populate() (pagination.py) calls
    setProperty()/setBoolProperty() on every real item it builds, but jumpToPosition()'s own
    offset/relative-index math (what JumpToPositionTest below actually exercises) never reads
    anything back off them, so a no-op is enough."""

    def __init__(self, value):
        self.value = value

    def setProperty(self, *args, **kwargs):
        pass

    def setBoolProperty(self, *args, **kwargs):
        pass


class _FakeGridControlWithItems(object):
    """Real ManagedControlList.replaceItems()/size() shape, minus any native control binding -
    enough for jumpToPosition() (collection.py), which only ever calls these two plus
    selectItem()."""

    def __init__(self):
        self.items = []
        self.selectItemCalls = []

    def replaceItems(self, items):
        self.items = items

    def size(self):
        return len(self.items)

    def selectItem(self, pos):
        self.selectItemCalls.append(pos)


class _FakeJumpPaginator(collection.BoundedGridPaginator):
    """Real BoundedGridPaginator, minus the two places it would otherwise need a genuine
    CollectionWindow/SubDirWindow parentWindow and a real server round trip - createListItem()/
    prepareListItem() (BoundedGridPaginator's own overrides) call self.parentWindow.setItemInfo()/
    setWatchedInfo(); getData() (CollectionPaginator/SubDirPaginator's own job normally) would
    otherwise need a real Section/collection object. Deterministic in-memory data instead: a
    "list" of plain integers 0..leaf_count-1, page (offset, amount) sliced directly."""

    def createListItem(self, data):
        return _FakeMLI(data)

    def prepareListItem(self, data, mli):
        pass

    def getData(self, offset, amount):
        return list(range(offset, min(offset + amount, self.leafCount)))


class JumpToPositionTest(KodiTestCase):
    """BoundedGridPaginator.jumpToPosition() (collection.py) - a direct, one-fetch jump to
    whichever page contains an arbitrary absolute position, for restoring a grid selection beyond
    the paginator's own initial page (live-reported, 2026-09-03: fell back to item 0 for any such
    position before this existed). page_size=60/orphans=12 throughout, matching
    BoundedGridPaginator's own real defaults - amount is always 72."""

    @staticmethod
    def _paginator(leaf_count):
        control = _FakeGridControlWithItems()
        paginator = _FakeJumpPaginator(control, parent_window=None, page_size=60, orphans=12,
                                        leaf_count=leaf_count)
        return paginator, control

    def test_out_of_range_position_is_a_no_op(self):
        paginator, control = self._paginator(leaf_count=100)

        self.assertFalse(paginator.jumpToPosition(150))
        self.assertEqual([], control.selectItemCalls)

    def test_negative_position_is_a_no_op(self):
        paginator, control = self._paginator(leaf_count=100)

        self.assertFalse(paginator.jumpToPosition(-1))
        self.assertEqual([], control.selectItemCalls)

    def test_jumps_to_and_selects_a_position_deep_past_the_initial_page(self):
        paginator, control = self._paginator(leaf_count=200)

        self.assertTrue(paginator.jumpToPosition(150))

        # Centered window: amount = pageSize(60) + orphans(12) = 72, offset = 150 - 72//2 = 114.
        self.assertEqual(114, paginator.offset)
        # offset > 0, so control index 0 is the left-boundary sentinel - position 150 is this
        # page's 36th item (150 - 114), landing at control index 37.
        self.assertEqual([37], control.selectItemCalls)

    def test_position_near_the_very_start_needs_no_left_boundary_shift(self):
        paginator, control = self._paginator(leaf_count=200)

        self.assertTrue(paginator.jumpToPosition(5))

        # offset would go negative (5 - 36) without the max(0, ...) clamp.
        self.assertEqual(0, paginator.offset)
        # offset == 0 here - no left-boundary sentinel, so the shift is skipped entirely.
        self.assertEqual([5], control.selectItemCalls)

    def test_the_fetch_window_is_clamped_to_not_run_past_the_end_of_the_list(self):
        paginator, control = self._paginator(leaf_count=200)

        self.assertTrue(paginator.jumpToPosition(195))

        # Naive centering (195 - 36 = 159) would need items up to 159 + 72 = 231, past leafCount
        # (200) - clamped so the fetched window ends exactly at the list's real end instead.
        self.assertEqual(200 - 72, paginator.offset)
