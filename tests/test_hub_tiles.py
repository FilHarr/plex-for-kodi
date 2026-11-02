# coding=utf-8
"""
A hub row's GUI calls (the Recommended view's load, 2026-11-02): each tile is given only what its
row's layout reads (HubsMixin.HUB_TILE_READS, held to the templates here), a row written over
another has only what changed written (ManagedControlList.replaceWithValues()), a row off screen
is emptied and filled afresh, and the rows on screen are bound before the ones off it.

Importing lib.windows.library starts lib.player's monitor thread unless abort_requested is set
first - same guard the other lib.windows.* tests use for the same reason.
"""

from __future__ import absolute_import

import os
import re
from unittest import mock

from kodienv import ENV

ENV.abort_requested = True
from lib.windows import kodigui  # noqa: E402
from lib.windows import library_hubs  # noqa: E402

from .base import KodiTestCase  # noqa: E402

TEMPLATES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         'resources', 'skins', 'Main', '1080i', 'templates')
INCLUDE = re.compile(r'{%\s*include\s+"([^"]+)"')
PROPERTY = re.compile(r'(?:ListItem|}})\.Property\(([a-z0-9._]+)\)')

# every native ListItem call the code under test makes, in order
CALLS = []


class CountingListItem(kodigui.xbmcgui.ListItem):
    def setLabel(self, label):
        CALLS.append(('setLabel', label))
        super(CountingListItem, self).setLabel(label)

    def setLabel2(self, label):
        CALLS.append(('setLabel2', label))
        super(CountingListItem, self).setLabel2(label)

    def setPath(self, path):
        CALLS.append(('setPath', path))
        super(CountingListItem, self).setPath(path)

    def setArt(self, values):
        CALLS.append(('setArt', values.get('thumb')))
        super(CountingListItem, self).setArt(values)

    def setProperty(self, key, value):
        CALLS.append(('setProperty', key, value))
        super(CountingListItem, self).setProperty(key, value)


class FakeNativeList(object):
    def __init__(self):
        self.items = []
        self.selected = 0

    def addItems(self, items):
        CALLS.append(('addItems', len(items)))
        self.items.extend(items)

    def removeItem(self, idx):
        CALLS.append(('removeItem', idx))
        del self.items[idx]

    def reset(self):
        CALLS.append(('reset',))
        self.items = []

    def getListItem(self, idx):
        CALLS.append(('getListItem', idx))
        return self.items[idx]

    def getSelectedPosition(self):
        return self.selected

    def selectItem(self, idx):
        self.selected = idx


def managedList():
    ml = object.__new__(kodigui.ManagedControlList)
    ml.control = FakeNativeList()
    ml.controlID = 400
    ml.items = []
    ml._idCounter = 0
    ml._properties = {}
    ml._sortKey = None
    ml._maxViewIndex = 5
    ml._guard = None
    ml.dataSource = None
    return ml


class CountingCase(KodiTestCase):
    def setUp(self):
        super(CountingCase, self).setUp()
        patcher = mock.patch.object(kodigui.xbmcgui, 'ListItem', CountingListItem)
        patcher.start()
        self.addCleanup(patcher.stop)
        del CALLS[:]


def tile(label, thumb='', label2='', ds=None, **props):
    return label, label2, thumb, props, ds


class TemplateReadsTest(KodiTestCase):
    """HUB_TILE_READS is what each layout reads: a property left out would never show, one left
    in costs a write per tile."""

    def read(self, name, seen):
        if name in seen:
            return set()
        seen.add(name)
        with open(os.path.join(TEMPLATES, *name.split('/')), encoding='utf-8') as f:
            text = f.read()
        found = set(PROPERTY.findall(text))
        for include in INCLUDE.findall(text):
            found |= self.read(include, seen)
        return found

    def test_each_layout_reads_what_its_tiles_are_given(self):
        for display in ('poster', 'square', 'ar16x9'):
            seen = set()
            reads = (self.read('includes/hub_itemlayout_{0}.xml.tpl'.format(display), seen)
                     | self.read('includes/hub_focusedlayout_{0}.xml.tpl'.format(display), seen))
            self.assertEqual(reads, set(library_hubs.HubsMixin.HUB_TILE_READS[display]), display)


class ReplaceWithValuesTest(CountingCase):
    def filled(self, values):
        ml = managedList()
        ml.replaceWithValues(values)
        del CALLS[:]
        return ml

    def test_into_an_empty_list_each_item_is_added_with_its_values(self):
        ml = managedList()
        items = ml.replaceWithValues([tile('Alien', 'http://a', '1979', **{'thumb.fallback': 'f'}),
                                      tile('Heat')])
        self.assertEqual([('setArt', 'http://a'), ('setProperty', 'thumb.fallback', 'f'), ('addItems', 2)],
                         CALLS)
        self.assertEqual(['Alien', 'Heat'], [li.getLabel() for li in ml.control.items])
        self.assertEqual('1979', ml.control.items[0].getLabel2())
        self.assertEqual(items, ml.items)
        self.assertEqual('f', items[0].getProperty('thumb.fallback'))

    def test_the_same_values_again_write_nothing(self):
        values = [tile('Alien', 'http://a', **{'watched': '1'}), tile('Heat', 'http://h')]
        ml = self.filled(values)
        ml.replaceWithValues(values)
        self.assertEqual([], CALLS)

    def test_only_what_changed_is_written(self):
        ml = self.filled([tile('Alien', 'http://a', **{'thumb.fallback': 'f', 'watched': '1'})])
        old = ml.items[0]
        items = ml.replaceWithValues([tile('Aliens', 'http://a', **{'thumb.fallback': 'f', 'progress': 'p'})])
        self.assertEqual([('getListItem', 0), ('setLabel', 'Aliens')],
                         CALLS[:2])
        self.assertEqual({('setProperty', 'watched', ''), ('setProperty', 'progress', 'p')}, set(CALLS[2:]))
        native = ml.control.items[0]
        self.assertEqual('Aliens', native.getLabel())
        self.assertEqual('', native.getProperty('watched'))
        self.assertEqual('p', native.getProperty('progress'))
        self.assertEqual({'thumb.fallback': 'f', 'progress': 'p'}, items[0].properties)
        self.assertFalse(old._valid)

    def test_new_art_is_written(self):
        ml = self.filled([tile('Alien', 'http://a')])
        ml.replaceWithValues([tile('Alien', 'http://b')])
        self.assertEqual([('getListItem', 0), ('setArt', 'http://b')], CALLS)

    def test_a_longer_row_grows_and_a_shorter_one_shrinks_from_the_end(self):
        ml = self.filled([tile('A'), tile('B')])
        ml.replaceWithValues([tile('A'), tile('B'), tile('C')])
        self.assertEqual([('addItems', 1), ('getListItem', 2), ('setLabel', 'C')], CALLS)
        del CALLS[:]
        ml.replaceWithValues([tile('A')])
        self.assertEqual([('removeItem', 2), ('removeItem', 1)], CALLS)
        self.assertEqual(['A'], [li.getLabel() for li in ml.control.items])

    def test_an_item_written_nothing_still_reaches_its_native_item(self):
        ml = self.filled([tile('A'), tile('B')])
        items = ml.replaceWithValues([tile('A'), tile('B')])
        items[1].setProperty('watched', '1')
        self.assertEqual('1', ml.control.items[1].getProperty('watched'))


class Obj(object):
    """A hub item, with what the tile builders read."""

    def __init__(self, type_, title, rk, **attrs):
        self.type = type_
        self.TYPE = type_
        self.title = title
        self.defaultTitle = title
        self.ratingKey = rk
        self.year = attrs.pop('year', '')
        self.isWatched = attrs.pop('isWatched', False)
        self.isPlayed = attrs.pop('isPlayed', False)
        self.index = attrs.pop('index', None)
        self.parentIndex = attrs.pop('parentIndex', None)
        self._attrs = attrs
        thumb = mock.Mock()
        thumb.asTranscodedImageURL.side_effect = lambda w, h: 'http://{0}/{1}x{2}'.format(rk, w, h)
        self.defaultThumb = thumb
        self.defaultArt = thumb

    def get(self, key, default=None):
        return self._attrs.get(key, default)


class Hub(object):
    def __init__(self, identifier, items):
        self.hubIdentifier = identifier
        self.title = identifier
        self.items = items
        self.more = False

    def getCleanHubIdentifier(self, is_home=False):
        return self.hubIdentifier


class Host(library_hubs.HubsMixin):
    HUB_CONTROL_ID = 400

    def __init__(self, display):
        self.section = mock.Mock(key='1')
        self.display = display
        self.props = {}
        self.hubControls = [managedList() for i in range(4)]
        self._hubReselectPositions = {}
        self.visibleHubs = []

    def getHubDisplayType(self, hub, identifier):
        return self.display

    def getHubRenderFlags(self, hub, identifier):
        return {'with_progress': True, 'text2lines': False, 'no_labels': False,
                'with_art': self.display == 'ar16x9'}

    def setProperty(self, key, value):
        self.props[key] = value


class BindRowTest(CountingCase):
    def setUp(self):
        super(BindRowTest, self).setUp()
        for patcher in (mock.patch.object(library_hubs.util, 'getProgressImage', lambda obj: ''),
                        mock.patch.object(library_hubs.hub_limits, 'hasSeeMore', return_value=False)):
            patcher.start()
            self.addCleanup(patcher.stop)

    def bind(self, display, items, offscreen=False, host=None):
        host = host or Host(display)
        host._bindHubToControl(Hub('row', items), 0, offscreen=offscreen)
        return host

    def native(self, host, idx=0):
        return host.hubControls[0].control.items[idx]

    def test_a_poster_row_leaves_out_what_its_layout_doesnt_read(self):
        host = self.bind('poster', [Obj('movie', 'Alien', 1, year='1979', isPlayed=True)])
        props = self.native(host)._props
        # 'unwatched' is the 16:9 layout's alone
        self.assertEqual({'thumb.fallback': 'script.plex/thumb_fallbacks/movie.png', 'watched': '1'}, props)
        self.assertEqual('1979', self.native(host).getLabel2())

    def test_a_16x9_row_has_the_episode_badge_and_unwatched(self):
        episode = Obj('episode', 'Pilot', 2, index=1, parentIndex=1, grandparentTitle='Lost')
        host = self.bind('ar16x9', [episode])
        props = self.native(host)._props
        self.assertEqual('1', props['unwatched'])
        self.assertTrue(props['episode.number'])
        self.assertNotIn('watched', props)
        self.assertEqual('Lost', self.native(host).getLabel())
        # label2 goes in with the item: no setLabel2 call
        self.assertNotIn('setLabel2', [c[0] for c in CALLS])

    def test_see_more_ends_a_cut_short_row(self):
        with mock.patch.object(library_hubs.hub_limits, 'hasSeeMore', return_value=True):
            host = self.bind('poster', [Obj('movie', 'Alien', 1)])
        self.assertEqual('1', self.native(host, 1).getProperty('is.more'))
        self.assertIsNone(host.hubControls[0].items[1].dataSource)

    def test_an_offscreen_row_is_emptied_and_filled_afresh(self):
        host = self.bind('poster', [Obj('movie', 'Alien', 1)])
        del CALLS[:]
        self.bind('poster', [Obj('movie', 'Heat', 2)], offscreen=True, host=host)
        self.assertEqual(('reset',), CALLS[0])
        self.assertNotIn('getListItem', [c[0] for c in CALLS])
        self.assertEqual(['Heat'], [li.getLabel() for li in host.hubControls[0].control.items])
        # the row keeps its hub - reset() clears it, so it comes after: See more and the row's
        # menu read it (live 2026-11-02)
        self.assertEqual('Heat', host.hubControls[0].dataSource.items[0].title)

    def test_an_onscreen_row_is_written_over(self):
        host = self.bind('poster', [Obj('movie', 'Alien', 1)])
        del CALLS[:]
        self.bind('poster', [Obj('movie', 'Heat', 2)], host=host)
        self.assertNotIn(('reset',), CALLS)
        self.assertEqual(['Heat'], [li.getLabel() for li in host.hubControls[0].control.items])


class OrderHost(Host):
    def __init__(self):
        Host.__init__(self, 'poster')
        self.visibleHubs = ['h0', 'h1', 'h2', 'h3']
        self.focusedHubIndex = 1
        self._anchorRingPos = self.HUB_ROTATION_RING.index(400)
        self.bound = []

    def _bindHubToControl(self, hub, control_index, offscreen=False):
        self.bound.append((hub, offscreen))

    def _settleHubSlide(self):
        pass

    def setBoolProperty(self, key, value):
        pass

    def getControl(self, control_id):
        return None

    def _setRoleGeometry(self, wrapper, role, focused_index):
        pass

    def _placeStack(self, focused_index):
        pass

    def _previewSelectedItem(self, hub):
        return None

    def updateHeroFrom(self, ds):
        pass


class BindOrderTest(KodiTestCase):
    def test_the_rows_on_screen_come_first(self):
        host = OrderHost()
        host._bindAllHubSlots()
        # the anchor, the row peeking in below, then the row above and the one below that
        self.assertEqual([('h1', False), ('h2', False), ('h0', True), ('h3', True)], host.bound)
