# coding=utf-8
"""
An arrow press's GUI calls on a grid and a hub row (step 12 stage B in the navigation review):
one selection lookup per press, handed on to everything that needs the item or its position, and
the key property and the letter list's selection written only when the letter changes. The real
methods are bound onto small doubles, the style test_hub_item_interactivity.py uses.

Importing lib.windows.library starts lib.player's monitor thread unless abort_requested is set
first - same guard the other lib.windows.* tests use for the same reason.
"""

from __future__ import absolute_import

from kodienv import ENV

ENV.abort_requested = True
from lib.windows import kodigui  # noqa: E402
from lib.windows import library  # noqa: E402
from lib.windows import library_grid  # noqa: E402

from .base import KodiTestCase  # noqa: E402


class FakeNativeList(object):
    """The native control under a ManagedControlList, counting the GUI calls made on it."""

    def __init__(self, selected):
        self.selected = selected
        self.calls = []

    def getSelectedPosition(self):
        self.calls.append('getSelectedPosition')
        return self.selected

    def getListItem(self, pos):
        self.calls.append(('getListItem', pos))
        return 'native-%d' % pos


class FakeItem(object):
    def __init__(self, key='A', data_source=None, is_more=False):
        self.properties = {'key': key}
        if is_more:
            self.properties['is.more'] = '1'
        self.dataSource = data_source
        self._listItem = None
        self.posCalls = 0

    def getProperty(self, name):
        return self.properties.get(name, '')

    def pos(self):
        self.posCalls += 1
        raise AssertionError('pos() scans the list; the lookup already has the position')


def managedList(items, selected):
    ml = object.__new__(kodigui.ManagedControlList)
    ml.control = FakeNativeList(selected)
    ml.items = items
    return ml


class SelectedItemAndPosTest(KodiTestCase):
    def test_one_position_read_and_one_item_fetch(self):
        items = [FakeItem(), FakeItem(), FakeItem()]
        ml = managedList(items, 1)
        mli, pos = ml.getSelectedItemAndPos()
        self.assertIs(items[1], mli)
        self.assertEqual(1, pos)
        self.assertEqual(['getSelectedPosition', ('getListItem', 1)], ml.control.calls)
        self.assertEqual('native-1', mli._listItem)

    def test_an_out_of_range_selection_means_the_last_item(self):
        items = [FakeItem(), FakeItem()]
        mli, pos = managedList(items, 7).getSelectedItemAndPos()
        self.assertIs(items[1], mli)
        self.assertEqual(1, pos)

    def test_an_empty_list_has_no_selection(self):
        self.assertEqual((None, None), managedList([], 0).getSelectedItemAndPos())
        self.assertIsNone(managedList([], 0).getSelectedItem())

    def test_getSelectedItem_is_the_same_lookup(self):
        items = [FakeItem(), FakeItem()]
        self.assertIs(items[0], managedList(items, 0).getSelectedItem())


class FakeKeyList(object):
    def __init__(self):
        self.selected = []

    def selectItem(self, pos):
        self.selected.append(pos)


class FakeKeyItem(object):
    def __init__(self, pos):
        self._pos = pos

    def pos(self):
        return self._pos


class FakeGrid(object):
    """Carries only what the real, bound grid methods below touch."""

    updateKey = library_grid.GridMixin.updateKey
    selectKey = library_grid.GridMixin.selectKey
    _keyUpdateDue = library_grid.GridMixin._keyUpdateDue
    onItemChanged = library_grid.GridMixin.onItemChanged
    gridFocus = library_grid.GridMixin.gridFocus
    updateItem = library_grid.GridMixin.updateItem
    KEY_LIST_ID = library.PostersWindow.KEY_LIST_ID

    def __init__(self):
        self.lastItem = None
        self._shownKey = None
        self.keyListControl = FakeKeyList()
        self.keyItems = {'A': FakeKeyItem(1), 'B': FakeKeyItem(2)}
        self.showPanelControl = managedList([FakeItem('A')], 0)
        self.tasks = []
        self.photoShown = []

    def recordFocus(self, controlID):
        pass

    def showPhotoItemProperties(self, ds):
        self.photoShown.append(ds)


class FakeTask(object):
    def __init__(self, start, end):
        self.start, self.end = start, end

    def contains(self, pos):
        return self.start <= pos < self.end


class KeyWritesTest(KodiTestCase):
    def setUp(self):
        super(KeyWritesTest, self).setUp()
        self.written = []
        self._orig = library_grid.util.setGlobalProperty
        library_grid.util.setGlobalProperty = lambda k, v: self.written.append((k, v))

    def tearDown(self):
        library_grid.util.setGlobalProperty = self._orig
        super(KeyWritesTest, self).tearDown()

    def test_the_letter_is_written_once_per_change(self):
        grid = FakeGrid()
        for item in (FakeItem('A'), FakeItem('A'), FakeItem('B'), FakeItem('B')):
            if grid._keyUpdateDue(item):
                grid.updateKey(item)
        self.assertEqual([('key', 'A'), ('key', 'B')], self.written)
        self.assertEqual([1, 2], grid.keyListControl.selected)

    def test_the_letter_list_taking_focus_forces_the_next_write(self):
        grid = FakeGrid()
        grid.updateKey(FakeItem('A'))
        grid.gridFocus(grid.KEY_LIST_ID)
        self.assertTrue(grid._keyUpdateDue(FakeItem('A')))

    def test_a_new_photo_is_due_even_within_one_letter(self):
        class Photo(object):
            TYPE = 'photo'
        grid = FakeGrid()
        first = FakeItem('A', data_source=Photo())
        grid.updateKey(first)
        self.assertFalse(grid._keyUpdateDue(first))
        second = FakeItem('A', data_source=Photo())
        self.assertTrue(grid._keyUpdateDue(second))
        grid.updateKey(second)
        self.assertEqual(2, len(grid.photoShown))
        self.assertEqual([('key', 'A')], self.written)

    def test_updateItem_uses_the_callers_position(self):
        grid = FakeGrid()
        task = FakeTask(20, 30)
        grid.tasks = [FakeTask(0, 10), task]
        moved = []
        orig = library_grid.backgroundthread.BGThreader.moveToFront
        library_grid.backgroundthread.BGThreader.moveToFront = moved.append
        try:
            grid.updateItem(FakeItem(), 25)
        finally:
            library_grid.backgroundthread.BGThreader.moveToFront = orig
        self.assertEqual([task], moved)


class FakeRatingItem(object):
    ratingKey = 7


class FakeHub(object):
    def getCleanHubIdentifier(self, is_home=False):
        return 'hub.x'


class FakeSection(object):
    key = '1'


class FakeHubControl(object):
    def __init__(self, mli, pos):
        self.mli, self.pos = mli, pos
        self.dataSource = FakeHub()
        self.lookups = 0

    def getSelectedItemAndPos(self):
        self.lookups += 1
        return self.mli, self.pos

    def getSelectedItem(self):
        raise AssertionError('a second lookup')

    def getSelectedPos(self):
        raise AssertionError('a second lookup')


class FakeHubsWindow(object):
    checkHubItem = library.LibraryWindow.checkHubItem
    hubMemoryKey = library.LibraryWindow.hubMemoryKey
    HUB_CONTROL_ID = library.RecommendedWindow.HUB_CONTROL_ID

    def __init__(self, control):
        self.hubControls = [control]
        self.section = FakeSection()
        self._hubReselectPositions = {}
        self.heroFrom = []

    def _updateHeroFromFocusedHubItem(self, control_id, mli=None, timing=None):
        self.heroFrom.append(mli)


class HubRowLookupTest(KodiTestCase):
    def test_one_lookup_feeds_the_hero_and_the_position(self):
        mli = FakeItem(data_source=FakeRatingItem())
        control = FakeHubControl(mli, 4)
        window = FakeHubsWindow(control)
        window.checkHubItem(window.HUB_CONTROL_ID, action=None)
        self.assertEqual(1, control.lookups)
        self.assertEqual([mli], window.heroFrom)
        self.assertEqual({'hub.x': ('7', 4)}, window._hubReselectPositions)

    def test_see_more_is_neither_shown_nor_remembered(self):
        control = FakeHubControl(FakeItem(is_more=True), 9)
        window = FakeHubsWindow(control)
        window.checkHubItem(window.HUB_CONTROL_ID, action=None)
        self.assertEqual([], window.heroFrom)
        self.assertEqual({}, window._hubReselectPositions)


class HeroArtSizeTest(KodiTestCase):
    """kodigui.HERO_ART_SIZE follows the hero art box in includes/default_background.xml.tpl: a
    16:9 image that covers the box's width (1229 plus the zoom pad) and so its height too."""

    def test_the_size_covers_the_template_box(self):
        import os
        import re
        from .base import TEMPLATE_DIR
        with open(os.path.join(TEMPLATE_DIR, 'includes', 'default_background.xml.tpl'), encoding='utf-8') as fp:
            tpl = fp.read()
        pad = int(re.search(r'hero_zoom_pad = (\d+)', tpl).group(1))
        box = re.search(r'<width>\{\{ (\d+) \+ hero_zoom_pad \}\}</width>\s*<height>(\d+)</height>', tpl)
        width, height = int(box.group(1)) + pad, int(box.group(2))
        art_w, art_h = kodigui.HERO_ART_SIZE
        self.assertEqual(width, art_w)
        self.assertEqual(round(width * 9 / 16.0), art_h)
        self.assertGreaterEqual(art_h, height)
