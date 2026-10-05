# coding=utf-8
"""
The sidebar opens a section only on a click (windowutils.SidebarMixin). Browsing the section list
moves nothing but the highlight, and whenever the list doesn't have focus its selection is the
section actually on screen (is.active) - reselectActiveSection() snaps it back when focus leaves
the list, or enters it from outside the sidebar.

Importing lib.windows.windowutils starts lib.player's monitor thread unless abort_requested is set
first - same guard the other lib.windows.* tests use for the same reason.
"""

from __future__ import absolute_import

from kodienv import ENV

ENV.abort_requested = True
from lib.windows import windowutils  # noqa: E402

from .base import KodiTestCase  # noqa: E402

CONTENT_ID = 101


class FakeItem(object):
    def __init__(self, active=False, data_source=None, search=False):
        self.properties = {}
        if active:
            self.properties['is.active'] = '1'
        if search:
            self.properties['is.search'] = '1'
        self.dataSource = data_source

    def getProperty(self, key):
        return self.properties.get(key, '')


class FakeSectionList(object):
    """Python-side items only. __getitem__ fails the test: the snap must not make a native
    getListItem() call per entry."""

    def __init__(self, items, selected=0):
        self.items = items
        self.selected = selected
        self.selectCalls = []

    def __getitem__(self, idx):
        raise AssertionError('reads must use .items, not a native getListItem() per entry')

    def setSelectedItemByPos(self, pos):
        self.selectCalls.append(pos)
        self.selected = pos

    def getSelectedItem(self):
        return self.items[self.selected]


class FakeSidebarWindow(windowutils.SidebarMixin):
    def __init__(self, items, selected=0):
        self.sectionList = FakeSectionList(items, selected)
        self.deferCalls = []
        self.goHomeCalls = []
        self.searchClicked = False

    def _deferOpenSection(self, section, force=False):
        self.deferCalls.append((section, force))

    def goHome(self, section=None, with_root=False, force=False):
        self.goHomeCalls.append((section, force))

    def searchButtonClicked(self):
        self.searchClicked = True


def _sidebar():
    # Search, Home, Movies (active), TV Shows
    return [FakeItem(search=True), FakeItem(data_source='home'), FakeItem(active=True, data_source='movies'),
            FakeItem(data_source='tv')]


class ReselectActiveSectionTest(KodiTestCase):
    def test_leaving_the_list_snaps_back_to_the_active_section(self):
        win = FakeSidebarWindow(_sidebar(), selected=3)  # browsed down to TV Shows, not clicked

        win.reselectActiveSection(CONTENT_ID, win.SECTION_LIST_ID)

        self.assertEqual([2], win.sectionList.selectCalls)

    def test_entering_the_list_from_content_snaps_to_the_active_section(self):
        win = FakeSidebarWindow(_sidebar(), selected=0)

        win.reselectActiveSection(win.SECTION_LIST_ID, CONTENT_ID)

        self.assertEqual([2], win.sectionList.selectCalls)

    def test_down_onto_the_libraries_button_leaves_the_list_where_it_is(self):
        win = FakeSidebarWindow(_sidebar(), selected=3)
        win.reselectActiveSection(win.SERVER_BUTTON_ID, win.SECTION_LIST_ID)
        self.assertEqual([], win.sectionList.selectCalls)

    def test_up_from_the_libraries_button_lands_on_the_last_entry(self):
        win = FakeSidebarWindow(_sidebar(), selected=2)
        win.reselectActiveSection(win.SECTION_LIST_ID, win.SERVER_BUTTON_ID)
        self.assertEqual([3], win.sectionList.selectCalls)

    def test_leaving_the_libraries_button_snaps_back_to_the_active_section(self):
        win = FakeSidebarWindow(_sidebar(), selected=3)
        win.reselectActiveSection(CONTENT_ID, win.SERVER_BUTTON_ID)
        self.assertEqual([2], win.sectionList.selectCalls)

    def test_moving_within_the_sidebar_leaves_the_selection_alone(self):
        for previous in (windowutils.SidebarMixin.SECTION_LIST_ID, windowutils.SidebarMixin.SIDEBAR_GROUP_ID,
                         windowutils.SidebarMixin.USER_BUTTON_ID):
            win = FakeSidebarWindow(_sidebar(), selected=3)
            win.reselectActiveSection(win.SECTION_LIST_ID, previous)
            self.assertEqual([], win.sectionList.selectCalls, previous)

    def test_focus_moving_between_other_controls_leaves_the_selection_alone(self):
        win = FakeSidebarWindow(_sidebar(), selected=3)

        win.reselectActiveSection(CONTENT_ID, CONTENT_ID + 1)

        self.assertEqual([], win.sectionList.selectCalls)

    def test_no_active_entry_selects_nothing(self):
        win = FakeSidebarWindow([FakeItem(search=True), FakeItem(data_source='home')], selected=1)

        win.reselectActiveSection(CONTENT_ID, win.SECTION_LIST_ID)

        self.assertEqual([], win.sectionList.selectCalls)


class SectionClickedTest(KodiTestCase):
    def setUp(self):
        self._home = windowutils.HOME

    def tearDown(self):
        windowutils.HOME = self._home

    def test_click_on_home_opens_in_place_with_force(self):
        win = FakeSidebarWindow(_sidebar(), selected=3)
        windowutils.HOME = win

        win.sectionClicked()

        self.assertEqual([('tv', True)], win.deferCalls)
        self.assertEqual([], win.goHomeCalls)

    def test_click_on_the_active_section_still_acts(self):
        win = FakeSidebarWindow(_sidebar(), selected=2)
        windowutils.HOME = win

        win.sectionClicked()

        self.assertEqual([('movies', True)], win.deferCalls)

    def test_click_from_a_descendant_bubbles_with_force(self):
        win = FakeSidebarWindow(_sidebar(), selected=3)
        windowutils.HOME = object()

        win.sectionClicked()

        self.assertEqual([('tv', True)], win.goHomeCalls)
        self.assertEqual([], win.deferCalls)

    def test_click_on_search_opens_search(self):
        win = FakeSidebarWindow(_sidebar(), selected=0)
        windowutils.HOME = win

        win.sectionClicked()

        self.assertTrue(win.searchClicked)
        self.assertEqual([], win.deferCalls)
