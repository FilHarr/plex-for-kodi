# coding=utf-8
"""
Group rows in the option picker (lib/windows/dialog.py): groupedOptions() puts a blank optionGroup() between the
groups with options in, and SelectDialog.onAction() passes focus over a group row - after Kodi has made the move, as
the album screen passes over its disc rows - and still rounds from one end of the list to the other. The real
methods are bound onto a small double whose list records where it's sent.

Importing lib.windows.* starts lib.player's monitor thread unless abort_requested is set first - same guard the other
lib.windows.* tests use for the same reason.
"""

from __future__ import absolute_import

from kodienv import ENV

ENV.abort_requested = True
from kodi_six import xbmcgui  # noqa: E402
from lib.windows import dialog  # noqa: E402

from .base import KodiTestCase  # noqa: E402

UP, DOWN = xbmcgui.ACTION_MOVE_UP, xbmcgui.ACTION_MOVE_DOWN


class FakeControl(object):
    def __init__(self, owner):
        self.owner = owner

    def getSelectedPosition(self):
        return self.owner.pos


class FakeList(object):
    def __init__(self, size):
        self.pos = 0
        self.items = size
        self.control = FakeControl(self)

    def size(self):
        return self.items

    def setSelectedItemByPos(self, pos):
        self.pos = pos


class FakePicker(object):
    D = dialog.SelectDialog
    OPTIONS_LIST_ID = D.OPTIONS_LIST_ID
    onAction, isGroup, firstOption = D.onAction, D.isGroup, D.firstOption

    def __init__(self, options):
        self.options = options
        self.optionsList = FakeList(len(options))
        self.nonPlayback = True
        self.roundRobin = True
        self.lastSelectedItem = self.firstOption()
        self.optionsList.pos = self.lastSelectedItem

    def getFocusId(self):
        return self.OPTIONS_LIST_ID

    def press(self, action):
        """Kodi's own move (onup/ondown are noop at the ends), then the picker's onAction()."""
        if action == UP and self.optionsList.pos > 0:
            self.optionsList.pos -= 1
        elif action == DOWN and self.optionsList.pos < len(self.options) - 1:
            self.optionsList.pos += 1
        try:
            self.onAction(action)
        except AttributeError:
            # kodigui.BaseDialog.onAction() on this double, once the picker had nothing to do
            pass
        return self.optionsList.pos


def picker(*groups):
    return FakePicker(dialog.groupedOptions(*[[(k, k) for k in g] for g in groups]))


class GroupedOptionsTest(KodiTestCase):
    def test_a_blank_group_row_between_groups(self):
        options = dialog.groupedOptions([('a', 'A')], [('b', 'B'), ('c', 'C')])
        self.assertEqual(['a', dialog.GROUP, 'b', 'c'], [o[0] for o in options])
        self.assertEqual('', options[1][1])

    def test_empty_groups_leave_no_row(self):
        options = dialog.groupedOptions([], [('a', 'A')], [], [('b', 'B')], [])
        self.assertEqual(['a', dialog.GROUP, 'b'], [o[0] for o in options])


class PassingOverTest(KodiTestCase):
    def test_down_passes_over_a_group_row(self):
        p = picker(['a'], ['b', 'c'])
        self.assertEqual(2, p.press(DOWN))

    def test_up_passes_over_a_group_row(self):
        p = picker(['a'], ['b', 'c'])
        p.optionsList.pos = p.lastSelectedItem = 2
        self.assertEqual(0, p.press(UP))

    def test_still_rounds_from_the_last_to_the_first(self):
        p = picker(['a'], ['b'])
        p.optionsList.pos = p.lastSelectedItem = 2
        self.assertEqual(0, p.press(DOWN))

    def test_still_rounds_from_the_first_to_the_last(self):
        p = picker(['a'], ['b'])
        self.assertEqual(2, p.press(UP))

    def test_a_list_without_groups_moves_as_before(self):
        p = picker(['a', 'b', 'c'])
        self.assertEqual(1, p.press(DOWN))
        self.assertEqual(2, p.press(DOWN))
        self.assertEqual(0, p.press(DOWN))
