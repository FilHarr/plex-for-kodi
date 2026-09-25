# coding=utf-8
"""
3e in the navigation review: a section's item type ('movie', 'episode', 'album', 'collection'...)
lives on its LibrarySettings, not in the module global library.ITEM_TYPE that every window and
worker used to share - a second LibraryWindow, or a section switch, changed it under anything
still running for the first.

Importing lib.windows.* starts lib.player's monitor thread unless abort_requested is set first.
"""

from __future__ import absolute_import

from kodienv import ENV

ENV.abort_requested = True
from lib.windows import library  # noqa: E402

from .base import KodiTestCase  # noqa: E402


class FakeServer(object):
    uuid = 'server-uuid'


class FakeSection(object):
    def __init__(self, key, type_):
        self.key = key
        self.TYPE = type_

    def getServer(self):
        return FakeServer()


class LibrarySettingsItemTypeTest(KodiTestCase):
    def test_starts_on_the_sections_own_type(self):
        self.assertEqual('show', library.LibrarySettings(FakeSection('2', 'show')).itemType)

    def test_two_sections_keep_their_own(self):
        shows = library.LibrarySettings(FakeSection('2', 'show'))
        music = library.LibrarySettings(FakeSection('3', 'artist'))
        music.setItemType('album')
        self.assertEqual('show', shows.itemType)
        self.assertEqual('album', music.itemType)

    def test_module_global_is_gone(self):
        self.assertFalse(hasattr(library, 'ITEM_TYPE'))


class ChunkRequestTaskItemTypeTest(KodiTestCase):
    def test_carries_the_type_it_was_set_up_with(self):
        task = library.ChunkRequestTask().setup(FakeSection('2', 'show'), 0, 10, None, item_type='episode')
        self.assertEqual('episode', task.itemType)
