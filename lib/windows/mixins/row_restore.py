# coding=utf-8

from lib.windows import kodigui


class RowRestoreMixin(object):
    """Back to a hosted screen lands on the row item it opened from, not on its default control.

    Back rebuilds a hosted screen from its back-stack entry (LibraryWindow.popBack()), and what the
    entry keeps of it is what restoreState() returns (LibraryWindow.
    _captureHostedShellRestoreState()) - here the row and item focused when something opened from
    it, handed back to the rebuilt screen as its restore_focus kwarg (on request, 2026-10-07).

    A screen using it:
      - sets self.restoreFocus = kwargs.get('restore_focus') in its constructor
      - gives restoreRows(): {list id: ManagedControlList} for every row something opens from
      - names the rows a worker fills, in asyncRestoreRows(), and runs each of those fills through
        _fillThenRestore(), whose restore waits for its rows
      - calls _restoreRowFocus() once its other rows are filled, focusing its default control
        only when that returns False
      - names its default controls in restoreDefaultFocusIds(): a worker-filled row only takes
        focus from one of those, never from wherever the user has gone meanwhile
    """
    def restoreRows(self):
        return {}

    def asyncRestoreRows(self):
        """The list ids of the rows a worker fills."""
        return ()

    def restoreDefaultFocusIds(self):
        return (0,)

    def restoreState(self):
        """What a back-stack entry keeps of this screen, as the constructor's kwargs: the row item
        focused. None away from the rows, which also drops a position kept from an earlier visit."""
        focus = self.getFocusId()
        row = self.restoreRows().get(focus)
        pos = row.getSelectedPos() if row is not None else None
        return {'restore_focus': (focus, pos) if pos is not None else None}

    def _restoreRowFocus(self, filled=None):
        """Focuses the row item restoreFocus names, once. filled: the row a worker fill has just
        filled (_fillThenRestore()) - only that row's restore applies then, and only while focus is
        still on a default control. True if it focused the row."""
        # tasks None: closed (TasksMixin.doClose()) - a worker's fill can finish after that
        if not self.restoreFocus or getattr(self, 'tasks', ()) is None:
            return False
        controlID, pos = self.restoreFocus
        if filled is not None and filled != controlID:
            return False
        row = self.restoreRows().get(controlID)
        if row is None:
            self.restoreFocus = None
            return False
        if not row.positionIsValid(pos):
            if filled is None and controlID in self.asyncRestoreRows():
                return False  # not filled yet: _fillThenRestore() does it
            self.restoreFocus = None
            return False
        self.restoreFocus = None
        if filled is not None and self.getFocusId() not in self.restoreDefaultFocusIds():
            return False
        row.setSelectedItemByPos(pos)
        # A row's group shows once its list has items, which Kodi only sees on its next evaluation -
        # a focus request that gets there first is refused.
        kodigui.waitForVisibility(controlID, amount=1)
        self.setFocusId(controlID)
        return True

    def _fillThenRestore(self, fill, *controlIDs):
        """fill, for a worker, then the restore waiting on one of the rows it fills
        (_restoreRowFocus())."""
        def run():
            fill()
            for controlID in controlIDs:
                if self._restoreRowFocus(filled=controlID):
                    break
        return run
