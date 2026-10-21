# coding=utf-8
"""
Collection.hasNoPicture() (plexnet/plexlibrary.py): an empty collection with no poster of its own, whose composite
PMS answers 404 for, so screens show the stand-in instead of asking. Checked against all 210 collections on the
user's server, 2026-10-21 (16 flagged, every one a 404; the rest all loaded).
"""

from __future__ import absolute_import

import unittest
from xml.etree import ElementTree

from kodienv import ENV

ENV.abort_requested = True
from lib import util  # noqa: E402,F401
from plexnet import plexlibrary  # noqa: E402

ENV.abort_requested = False

COMPOSITE = '/library/collections/28923/composite/1515933907?width=400&height=600'
OWN_POSTER = '/library/metadata/101344/thumb/1760000000'


def collection(**attrs):
    return plexlibrary.Collection(ElementTree.Element('Directory', type='collection', **attrs))


class HasNoPictureTest(unittest.TestCase):
    def test_empty_with_only_a_composite(self):
        self.assertTrue(collection(childCount='0', thumb=COMPOSITE).hasNoPicture())

    def test_empty_with_its_own_poster(self):
        self.assertFalse(collection(childCount='0', thumb=OWN_POSTER).hasNoPicture())

    def test_members_make_the_composite(self):
        self.assertFalse(collection(childCount='3', thumb=COMPOSITE).hasNoPicture())

    def test_no_count_isnt_taken_as_empty(self):
        self.assertFalse(collection(thumb=COMPOSITE).hasNoPicture())

    def test_no_thumb(self):
        self.assertFalse(collection(childCount='0').hasNoPicture())


if __name__ == '__main__':
    unittest.main()
