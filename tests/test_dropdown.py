# coding=utf-8
"""
lib/windows/dropdown.py - the popup menu's action handling.

Kodi turns an Enter held for 500ms into ACTION_CONTEXT_MENU. Since a dropdown is
usually opened *by* long-pressing Enter, the next press often arrives the same way,
and the dialog used to ignore it: the menu sat there unresponsive to the very key
that had opened it, which reads as a frozen addon (see the 2026-07-25 report).

Importing lib/windows/ starts lib.player's monitor thread, which spins until Kodi
says abort; setting abort_requested first lets it exit immediately.
"""

from __future__ import absolute_import

from unittest import mock

import xbmcgui
from kodienv import ENV

ENV.abort_requested = True
from lib.windows import dropdown, kodigui  # noqa: E402

from .base import KodiTestCase  # noqa: E402


class FakeAction(object):
    """xbmcgui.Action compares equal to its id, which is how the addon tests actions."""

    def __init__(self, action_id):
        self.action_id = action_id

    def __eq__(self, other):
        return self.action_id == other

    def getId(self):
        return self.action_id


def dialog(moving=False, focus_id=0):
    """A DropdownDialog without a Kodi window behind it."""
    dlg = dropdown.DropdownDialog.__new__(dropdown.DropdownDialog)
    dlg.choice = None
    dlg.movingItem = "an item" if moving else None
    dlg.roundRobin = True
    dlg.suboptionCallback = None
    dlg.optionsList = None
    dlg.lastSelectedItem = None
    dlg._lastMoveTime = 0
    dlg.closed = []
    dlg.doClose = lambda **kw: dlg.closed.append(True)
    dlg.getFocusId = lambda: focus_id
    return dlg


class DropdownContextMenuTest(KodiTestCase):
    def test_a_held_enter_dismisses_the_menu(self):
        dlg = dialog()
        dlg.onAction(FakeAction(xbmcgui.ACTION_CONTEXT_MENU))

        self.assertEqual([True], dlg.closed)

    def test_dismissing_yields_no_choice(self):
        # showDropdown() returns the dialog's choice, so None means "cancelled"
        dlg = dialog()
        dlg.onAction(FakeAction(xbmcgui.ACTION_CONTEXT_MENU))

        self.assertIsNone(dlg.choice)

    def test_move_mode_still_ignores_it(self):
        # while moving an item, only up/down, select and back mean anything
        dlg = dialog(moving=True)
        dlg.onAction(FakeAction(xbmcgui.ACTION_CONTEXT_MENU))

        self.assertEqual([], dlg.closed)

    def test_other_actions_still_reach_the_base_handler(self):
        dlg = dialog()
        seen = []
        original = kodigui.BaseDialog.onAction
        kodigui.BaseDialog.onAction = lambda self, action: seen.append(action.getId())
        try:
            dlg.onAction(FakeAction(xbmcgui.ACTION_NAV_BACK))
        finally:
            kodigui.BaseDialog.onAction = original

        self.assertEqual([xbmcgui.ACTION_NAV_BACK], seen)
        self.assertEqual([], dlg.closed)


class SkipHeadingsTest(KodiTestCase):
    """A heading row (the Libraries picker's server names) is shown but never selected: moving onto
    one carries on to the next row in the same direction, or back at the end of the list."""

    class Row(object):
        def __init__(self, heading=False):
            self.heading = heading

        def getProperty(self, key):
            return '1' if key == 'heading' and self.heading else ''

    class Rows(object):
        def __init__(self, rows):
            self.items = rows
            self.selected = None

        def setSelectedItemByPos(self, pos):
            self.selected = pos

    def dialog(self, *headings):
        win = dropdown.DropdownDialog.__new__(dropdown.DropdownDialog)
        win.optionsList = self.Rows([self.Row(heading=h) for h in headings])
        return win

    def test_down_onto_a_heading_goes_on_to_the_row_below(self):
        win = self.dialog(False, True, False)
        self.assertEqual(2, win._skipHeadings(1, xbmcgui.ACTION_MOVE_DOWN))
        self.assertEqual(2, win.optionsList.selected)

    def test_up_onto_a_heading_goes_on_to_the_row_above(self):
        win = self.dialog(False, True, True, False)
        self.assertEqual(0, win._skipHeadings(2, xbmcgui.ACTION_MOVE_UP))

    def test_a_heading_first_sends_up_back_down(self):
        win = self.dialog(True, False)
        self.assertEqual(1, win._skipHeadings(0, xbmcgui.ACTION_MOVE_UP))

    def test_a_row_is_left_alone(self):
        win = self.dialog(False, True, False)
        self.assertEqual(2, win._skipHeadings(2, xbmcgui.ACTION_MOVE_DOWN))
        self.assertIsNone(win.optionsList.selected)


class LibraryPickerButtonsTest(KodiTestCase):
    """The Libraries picker's two buttons a row: Left/Right choose which one Select acts on, and it
    stays chosen; the row's choice carries it to the callback."""

    def picker(self, moving=False):
        dlg = dropdown.CardListDialog.__new__(dropdown.CardListDialog)
        dlg.movingItem = 'an item' if moving else None
        dlg.columns = dlg.COLUMNS
        dlg.column = dlg.PIN
        dlg.props = {}
        dlg.setProperty = lambda key, value: dlg.props.__setitem__(key, value)
        dlg.getFocusId = lambda: dlg.OPTIONS_LIST_ID
        return dlg

    def test_right_chooses_move_and_left_the_pin(self):
        dlg = self.picker()
        dlg.onAction(FakeAction(xbmcgui.ACTION_MOVE_RIGHT))
        self.assertEqual(('move', 'move'), (dlg.column, dlg.props['picker.column']))
        dlg.onAction(FakeAction(xbmcgui.ACTION_MOVE_LEFT))
        self.assertEqual(('pin', 'pin'), (dlg.column, dlg.props['picker.column']))

    def test_not_while_a_row_is_being_moved(self):
        dlg = self.picker(moving=True)
        dlg._handleMoveAction = lambda action: None
        dlg.onAction(FakeAction(xbmcgui.ACTION_MOVE_RIGHT))
        self.assertEqual('pin', dlg.column)

    def test_the_choice_carries_the_button(self):
        dlg = self.picker()
        dlg.column = dlg.MOVE
        row = {'key': 'library'}

        class Item(object):
            dataSource = row

        class Options(object):
            def getSelectedItem(self):
                return Item()

        dlg.optionsList = Options()
        with mock.patch.object(dropdown.DropdownHeaderDialog, 'setChoice', lambda self: None):
            dlg.setChoice()
        self.assertEqual('move', row['column'])


class LibraryPickerColumnsTest(KodiTestCase):
    picker = LibraryPickerButtonsTest.picker

    def test_open_pin_move_left_to_right_stopping_at_the_ends(self):
        dlg = self.picker()
        dlg.column = dlg.OPEN
        seen = []
        for action in (xbmcgui.ACTION_MOVE_LEFT, xbmcgui.ACTION_MOVE_RIGHT, xbmcgui.ACTION_MOVE_RIGHT,
                       xbmcgui.ACTION_MOVE_RIGHT, xbmcgui.ACTION_MOVE_LEFT):
            dlg.onAction(FakeAction(action))
            seen.append(dlg.column)
        self.assertEqual(['open', 'pin', 'move', 'move', 'pin'], seen)


class ManageHubsColumnsTest(KodiTestCase):
    picker = LibraryPickerButtonsTest.picker

    def test_two_tiles_only(self):
        dlg = self.picker()
        dlg.columns = (dlg.PIN, dlg.MOVE)
        dlg.onAction(FakeAction(xbmcgui.ACTION_MOVE_LEFT))
        self.assertEqual('pin', dlg.column)
        dlg.onAction(FakeAction(xbmcgui.ACTION_MOVE_RIGHT))
        self.assertEqual('move', dlg.column)
