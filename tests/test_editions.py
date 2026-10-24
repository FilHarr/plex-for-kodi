# coding=utf-8
"""
A film's or show's edition (editionTitle): its own title for Search, Continue Watching and the person page
(copies.sameTitleKey() - Plex gives an edition its film's guid, Deadpool 2's Super Duper Cut the plain film's,
checked live 2026-10-23), and on a caption's second line before the year (grid_labels.editionLine()), no longer
on the title.

Importing lib.windows.* starts lib.player's monitor thread unless abort_requested is set first - same guard the other
lib.windows.* tests use for the same reason.
"""

from __future__ import absolute_import

from kodienv import ENV

ENV.abort_requested = True
from lib.windows import copies, grid_labels  # noqa: E402

from .base import KodiTestCase  # noqa: E402

GUID = 'plex://movie/5d776c1c51dd69001fe37d4f'


class Item(dict):
    TYPE = 'movie'


class SameTitleTest(KodiTestCase):
    def test_an_edition_is_a_title_of_its_own(self):
        plain = Item(guid=GUID, year='2018')
        cut = Item(guid=GUID, year='2018', editionTitle='The Super Duper Cut')
        self.assertNotEqual(copies.sameTitleKey(plain), copies.sameTitleKey(cut))

    def test_copies_of_an_edition_are_still_one(self):
        a = Item(guid=GUID + '?lang=en', editionTitle='The Super Duper Cut')
        b = Item(guid=GUID, editionTitle='The Super Duper Cut')
        self.assertEqual(copies.sameTitleKey(a), copies.sameTitleKey(b))

    def test_without_an_edition_the_key_is_the_guid(self):
        self.assertEqual(GUID, copies.sameTitleKey(Item(guid=GUID)))


class EditionLineTest(KodiTestCase):
    def test_the_edition_before_the_year(self):
        self.assertEqual(u'The Final Cut \u2022 1982',
                         grid_labels.editionLine(Item(year='1982', editionTitle='The Final Cut')))

    def test_either_alone(self):
        self.assertEqual(u'1982', grid_labels.editionLine(Item(year='1982')))
        self.assertEqual(u'The Final Cut', grid_labels.editionLine(Item(editionTitle='The Final Cut')))
        self.assertEqual(u'', grid_labels.editionLine(Item()))

    def test_a_year_given_stands_in_for_the_items(self):
        self.assertEqual(u'The Final Cut \u2022 1982', grid_labels.editionLine(Item(editionTitle='The Final Cut'), '1982'))

    def test_a_see_more_film_caption(self):
        lines = grid_labels.lines('movie.recentlyadded', Item(title='Blade Runner', year='1982',
                                                               editionTitle='The Final Cut'))
        self.assertEqual((u'Blade Runner', u'The Final Cut \u2022 1982'), (lines.line1, lines.line2))
