# coding=utf-8
"""
Every Python ListItem call takes Kodi's GUI lock, so ManagedListItem skips the ones that change
nothing (step 4 in the navigation review): a property write of the value it already has, or of ''
for a property it never had, and empty art on a new item.
"""

from __future__ import absolute_import

from kodienv import ENV

ENV.abort_requested = True
from lib.windows import kodigui  # noqa: E402

from .base import KodiTestCase  # noqa: E402


class CountingListItem(object):
    def __init__(self):
        self.props = {}
        self.writes = []

    def setProperty(self, key, value):
        self.writes.append((key, value))
        self.props[key] = value


class ListItemWritesTest(KodiTestCase):
    def item(self):
        mli = kodigui.ManagedListItem('')
        mli._listItem = CountingListItem()
        return mli

    def test_same_value_again_is_not_written(self):
        mli = self.item()
        mli.setProperty('index', '4')
        mli.setProperty('index', '4')
        self.assertEqual(mli._listItem.writes, [('index', '4')])

    def test_empty_value_for_a_new_property_is_not_written(self):
        mli = self.item()
        mli.setProperty('progress', '')
        mli.setBoolProperty('watched', False)
        self.assertEqual(mli._listItem.writes, [])
        self.assertEqual(mli.getProperty('progress'), '')

    def test_changes_are_written_including_back_to_empty(self):
        mli = self.item()
        mli.setProperty('unwatched', '1')
        mli.setProperty('unwatched', '')
        self.assertEqual(mli._listItem.writes, [('unwatched', '1'), ('unwatched', '')])
        self.assertEqual(mli._listItem.props['unwatched'], '')

    def test_skipped_keys_are_still_tracked_for_a_rebind(self):
        # _updateListItem() replays every key the list has seen onto a fresh native item
        class Manager(object):
            _properties = {}
        mli = self.item()
        mli._manager = Manager()
        mli.setProperty('year', '')
        self.assertIn('year', Manager._properties)

    def test_new_item_without_artwork_sets_no_art(self):
        calls = []
        original = kodigui.xbmcgui.ListItem.setArt

        def setArt(li, values):
            calls.append(values)
            return original(li, values)
        kodigui.xbmcgui.ListItem.setArt = setArt
        try:
            kodigui.ManagedListItem('placeholder')
            kodigui.ManagedListItem('poster', thumbnailImage='http://thumb')
        finally:
            kodigui.xbmcgui.ListItem.setArt = original
        self.assertEqual(calls, [{'thumb': 'http://thumb', 'icon': ''}])
