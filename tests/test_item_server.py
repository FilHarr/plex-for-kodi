# coding=utf-8
"""
What an item is played or shown with follows the item's own server: its playback settings (binge
mode, skip intro, media version...) and the data cache (genres, audio choice). Both used to follow
whichever server was selected, switched for a moment by the Watchlist opener ('change:tempServer')
and switched back before the item had even been played. With no server selected any more (plan
Phase 9), an item without one gets the global settings and no cache.
"""

from __future__ import absolute_import

from unittest import mock

from lib import data_cache, playback_utils

from .base import KodiTestCase


class Server(object):
    def __init__(self, uuid):
        self.uuid = uuid


ANIMAL = Server('animal-uuid-0000aaaa')
OSCAR = Server('oscar-uuid-0000bbbb')


class Item(object):
    def __init__(self, rating_key, server):
        self.ratingKey = rating_key
        self.server = server


class PlaybackSettingsTest(KodiTestCase):
    def setUp(self):
        super(PlaybackSettingsTest, self).setUp()
        self.manager = playback_utils.PlaybackManager.__new__(playback_utils.PlaybackManager)
        self.manager._data = {}
        self.manager._currentUserID = '1'
        self.manager.glob = playback_utils.PlaybackSettings(**dict((k, False) for k in playback_utils.ATTR_MAP.values()))
        patcher = mock.patch.object(playback_utils.PlaybackManager, 'save')
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_settings_are_kept_under_the_items_server(self):
        self.manager(Item('5', OSCAR), key='binge_mode', value=True)
        self.assertIn(OSCAR.uuid, self.manager._data)
        self.assertNotIn(ANIMAL.uuid, self.manager._data)
        self.assertTrue(self.manager(Item('5', OSCAR)).binge_mode)
        # another server's item "5" is another item
        self.assertFalse(self.manager(Item('5', ANIMAL)).binge_mode)

    def test_an_item_without_a_server_gets_the_global_settings(self):
        self.manager(Item('5', None), key='binge_mode', value=True)
        self.assertEqual({}, self.manager._data)
        self.assertFalse(self.manager(Item('5', None)).binge_mode)


class DataCacheTest(KodiTestCase):
    def setUp(self):
        super(DataCacheTest, self).setUp()
        self.cache = data_cache.DataCacheManager.__new__(data_cache.DataCacheManager)
        self.cache.DATA_CACHES = {"general": {}, "cache": {}}

    def test_data_is_kept_under_the_items_server(self):
        self.cache.setCacheData('show_genres', '5', ['Drama'], server=OSCAR)
        self.assertEqual(['Drama'], self.cache.getCacheData('show_genres', '5', server=OSCAR))
        self.assertIsNone(self.cache.getCacheData('show_genres', '5', server=ANIMAL))

    def test_no_server_is_no_servers(self):
        self.cache.setCacheData('show_genres', '5', ['Drama'])
        self.assertIsNone(self.cache.getCacheData('show_genres', '5', server=ANIMAL))
