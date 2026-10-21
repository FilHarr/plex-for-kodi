# coding=utf-8
"""util.collectionCountText(): a library grid collection's second line, how many it holds in its library's word."""

from __future__ import absolute_import

import unittest

from kodienv import ENV

ENV.abort_requested = True
from lib import util  # noqa: E402

ENV.abort_requested = False


class CollectionCountTextTest(unittest.TestCase):
    def test_movies(self):
        self.assertEqual(util.collectionCountText(1, 'movie'), '1 movie')
        self.assertEqual(util.collectionCountText(12, 'movie'), '12 movies')
        self.assertEqual(util.collectionCountText(0, 'movie'), '0 movies')

    def test_shows(self):
        self.assertEqual(util.collectionCountText(1, 'show'), '1 show')
        self.assertEqual(util.collectionCountText(3, 'show'), '3 shows')

    def test_any_other_library(self):
        self.assertEqual(util.collectionCountText(1, 'artist'), '1 item')
        self.assertEqual(util.collectionCountText(5, 'photo'), '5 items')


def searchCollection(**attrs):
    from xml.etree import ElementTree
    from plexnet import plexlibrary
    return plexlibrary.Collection(ElementTree.Element('Directory', type='collection', **attrs))


class SearchCollectionCountTest(unittest.TestCase):
    """SearchWindow.collectionCount(): a collection result's third line, by its library's type
    (librarySectionType, as resolveCollections() sets it)."""

    def count(self, item):
        from lib.windows import search
        return search.SearchWindow.collectionCount(search.SearchWindow.__new__(search.SearchWindow), item)

    def test_by_library_type(self):
        self.assertEqual(self.count(searchCollection(childCount='12', librarySectionType='1')), '12 movies')
        self.assertEqual(self.count(searchCollection(childCount='1', librarySectionType='2')), '1 show')
        self.assertEqual(self.count(searchCollection(childCount='4', librarySectionType='8')), '4 items')

    def test_no_count_no_line(self):
        self.assertEqual(self.count(searchCollection(librarySectionType='1')), '')

    def test_not_a_collection(self):
        from unittest import mock
        self.assertEqual(self.count(mock.Mock(TYPE='movie')), '')


if __name__ == '__main__':
    unittest.main()
