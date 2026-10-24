# coding=utf-8
"""
The library grid's Filter picker (GridMixin.pickFilter(), lib/windows/library_grid.py), in the pickers' style: All,
ticked while nothing's filtered, then the on/off filters, then the value filters with a chevron (the tick instead on
the one in use). A value filter opens its values in a picker over it; Back there comes back to the filters, a value
chosen closes both with it. showOptionsDialog is replaced by a script of what the user does.

Importing lib.windows.* starts lib.player's monitor thread unless abort_requested is set first - same guard the other
lib.windows.* tests use for the same reason.
"""

from __future__ import absolute_import

from kodienv import ENV

ENV.abort_requested = True
from unittest import mock  # noqa: E402
from lib.windows import library_grid  # noqa: E402

from .base import KodiTestCase  # noqa: E402

TICK = 'script.plex/indicators/tick.png'
BOOLS = [{'type': 'unwatched', 'display': 'Unplayed', 'indicator': TICK, 'is_bool': True},
         {'type': 'hdr', 'display': 'HDR', 'indicator': '', 'is_bool': True}]
VALUES = [{'type': 'genre', 'display': 'Genre', 'is_sub_list': True, 'indicator': ''},
          {'type': 'year', 'display': 'Year', 'is_sub_list': True, 'indicator': ''}]
GENRES = [{'val': '1', 'display': 'Action', 'indicator': ''}, {'val': '2', 'display': 'Drama', 'indicator': TICK}]


class FakeGrid(object):
    pickFilter = library_grid.GridMixin.pickFilter

    def __init__(self, filter_=None, bools=None):
        self.filter = filter_
        self.boolFilters = bools or {}

    def getBoolProperty(self, key):
        return False

    def subOptionCallback(self, option):
        return GENRES if option['type'] == 'genre' else [{'val': None, 'display': 'none', 'ignore': True}]


class Script(object):
    """showOptionsDialog as the user drives it: steps are, per picker opened, a function of (rows, on_choice) that
    returns the key chosen (or None for Back)."""

    def __init__(self, *steps):
        self.steps = list(steps)
        self.shown = []

    def __call__(self, heading, rows, on_choice=None, **kwargs):
        self.shown.append((heading, rows, kwargs.get('selected_idx')))
        return self.steps.pop(0)(rows, on_choice)


def choose(key):
    def step(rows, on_choice):
        if on_choice is not None and on_choice(key) is not None:
            return None
        return key
    return step


class FilterPickerTest(KodiTestCase):
    def run_(self, grid, script):
        with mock.patch.object(library_grid, 'showOptionsDialog', script), \
                mock.patch.object(library_grid.util, 'messageDialog', mock.Mock()):
            return grid.pickFilter(BOOLS, VALUES)

    def test_the_rows_and_their_ticks(self):
        script = Script(lambda rows, on_choice: None)
        self.run_(FakeGrid(bools={'unwatched': True}), script)
        rows = script.shown[0][1]
        self.assertEqual([('all', 'clear_filter'), ('bool', 'unwatched'), ('bool', 'hdr'), ('value', 'genre'),
                          ('value', 'year')], [r[0] for r in rows])
        self.assertEqual([False, True, False, False, False], [r[2] for r in rows])
        # the chevron on the value filters alone
        self.assertEqual([{}, {}, {}, {'more': '1'}, {'more': '1'}], [r[3] if len(r) > 3 else {} for r in rows])

    def test_all_is_ticked_and_focused_while_nothings_filtered(self):
        script = Script(lambda rows, on_choice: None)
        self.run_(FakeGrid(), script)
        heading, rows, focus = script.shown[0]
        self.assertEqual((0, True), (focus, rows[0][2]))

    def test_all_clears_the_filters(self):
        result = self.run_(FakeGrid(bools={'hdr': True}), Script(choose(('all', 'clear_filter'))))
        self.assertEqual('clear_filter', result['type'])

    def test_a_value_filter_chosen_through_its_values(self):
        def genre(rows, on_choice):
            return choose(('value', 'genre'))(rows, on_choice)
        script = Script(genre, lambda rows, on_choice: 0)
        result = self.run_(FakeGrid(), script)
        self.assertEqual('genre', result['type'])
        self.assertEqual('Action', result['sub']['display'])
        # the values' picker: headed by the filter, the current value focused
        self.assertEqual(('Genre', 1), (script.shown[1][0], script.shown[1][2]))

    def test_back_from_the_values_comes_back_to_the_filters(self):
        back = []

        def genreThenBack(rows, on_choice):
            back.append(on_choice(('value', 'genre')))
            return None
        script = Script(genreThenBack, lambda rows, on_choice: None)
        self.assertIsNone(self.run_(FakeGrid(), script))
        rows, focus = back[0]
        self.assertEqual(('value', 'genre'), rows[focus][0])

    def test_a_value_filter_with_no_values_says_so_and_stays(self):
        stayed = []

        def year(rows, on_choice):
            stayed.append(on_choice(('value', 'year')))
            return None
        self.run_(FakeGrid(), Script(year))
        self.assertIsNotNone(stayed[0])

    def test_the_filter_in_use_shows_its_value_and_is_focused(self):
        grid = FakeGrid(filter_=dict(VALUES[0], sub=GENRES[1]))
        script = Script(lambda rows, on_choice: None)
        self.run_(grid, script)
        heading, rows, focus = script.shown[0]
        self.assertEqual((('value', 'genre'), ('Genre', 'Drama'), True), rows[focus][:3])
        self.assertFalse(rows[0][2])

    def test_an_on_off_filter_chosen(self):
        result = self.run_(FakeGrid(), Script(choose(('bool', 'hdr'))))
        self.assertEqual('hdr', result['type'])
