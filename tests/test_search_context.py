# coding=utf-8
"""
lib/windows/search.py's SearchDialog.hubItemClicked() - hashed-orbiting-pizza.md Phase 5
follow-up. Every search.dialog() caller (library.py, preplay.py, episodes.py, subitems.py,
person.py, tracks.py, collection.py, genres.py, playlist.py, playlists.py, videoplayer.py) passes
itself as parent_window, captured on the dialog as self.parentWindow - previously unused for
opening a clicked result, so every one of the seven hosted shell types opened from a search
result opened as a second real nested window instead of swapping into a live chain, and anything
drilled into further from there kept nesting too (a standalone shell's own _chainHost is always
None). hubItemClicked() now passes context=self.parentWindow through to opener.open() - inert
(same as before) when parentWindow isn't a live chain host, chain-aware when it is.

Constructing a real SearchDialog here would pull in the native WindowXMLDialog machinery
(pointless for a pure-Python test) - the real, bound hubItemClicked() is called directly against
a lightweight FakeSearchDialog double instead, same style test_library_chain.py/
test_opener_context.py use for their own real-shell/opener call-routing tests.

Importing lib.windows.search starts lib.player's monitor thread unless abort_requested is set
first - same guard the other lib.windows.* tests use for the same reason.
"""

from __future__ import absolute_import

from kodienv import ENV

ENV.abort_requested = True
from lib.windows import search  # noqa: E402

from .base import KodiTestCase  # noqa: E402


class FakeHubItem(object):
    def __init__(self, type_, exists=True):
        self.TYPE = type_
        self._exists = exists

    def exists(self):
        return self._exists


class FakeManagedControlList(object):
    def __init__(self, control_id, selected_item=None):
        self.controlID = control_id
        self._selected = selected_item
        self.removedItems = []

    def getSelectedItem(self):
        return self._selected

    def removeManagedItem(self, mli):
        self.removedItems.append(mli)


class FakeManagedListItem(object):
    def __init__(self, data_source):
        self.dataSource = data_source


class FakeEdit(object):
    def getText(self):
        return ''


class FakeParentWindow(object):
    """Stands in for whichever UtilMixin window was current when Search opened - the exact
    object search.dialog()'s own callers pass as parent_window."""
    pass


class FakeSearchDialog(object):
    """Carries only the attributes the real, bound hubItemClicked() (imported directly off
    search.SearchDialog below) actually touches - not a real SearchDialog instance."""

    hubItemClicked = search.SearchDialog.hubItemClicked

    def __init__(self, control, mli):
        self.hubControls = [control]
        self.edit = FakeEdit()
        self.parentWindow = FakeParentWindow()
        self.exitCommand = None
        self.isActive = True
        self.closed = False
        self.shown = False
        self.processedCommands = []
        self.historyAdded = []

    def addToHistory(self, title):
        self.historyAdded.append(title)

    def doClose(self):
        self.closed = True

    def show(self):
        self.shown = True

    def processCommand(self, command):
        self.processedCommands.append(command)


class HubItemClickedContextTest(KodiTestCase):
    def _click(self, hubItem):
        mli = FakeManagedListItem(hubItem)
        control = FakeManagedControlList(2100, selected_item=mli)
        dialog = FakeSearchDialog(control, mli)

        calls = []
        originalOpen = search.opener.open

        def fakeOpen(obj, context=None, **kwargs):
            calls.append((obj, context))
            return ''

        search.opener.open = fakeOpen
        try:
            dialog.hubItemClicked(2100)
        finally:
            search.opener.open = originalOpen

        return dialog, calls

    def test_passes_the_parent_window_as_context(self):
        hubItem = FakeHubItem('movie')

        dialog, calls = self._click(hubItem)

        self.assertEqual(1, len(calls))
        obj, context = calls[0]
        self.assertIs(hubItem, obj)
        self.assertIs(dialog.parentWindow, context)

    def test_closes_itself_before_opening_the_item(self):
        """context is only meaningful if the dialog has already released the screen back to its
        parent by the time opener.open() runs - regression guard for that ordering."""
        hubItem = FakeHubItem('show')
        wasClosedDuringOpen = []

        mli = FakeManagedListItem(hubItem)
        control = FakeManagedControlList(2100, selected_item=mli)
        dialog = FakeSearchDialog(control, mli)

        def fakeOpen(obj, context=None, **kwargs):
            wasClosedDuringOpen.append(dialog.closed)
            return ''

        originalOpen = search.opener.open
        search.opener.open = fakeOpen
        try:
            dialog.hubItemClicked(2100)
        finally:
            search.opener.open = originalOpen

        self.assertEqual([True], wasClosedDuringOpen)

    def test_a_genre_director_or_role_result_also_gets_the_context(self):
        """These three TYPEs are the ones opener.open()'s dispatch already threads context into
        alongside the seven main shell types (hashed-orbiting-pizza.md Phase 4 items 4/8) -
        confirming search doesn't special-case them out."""
        for type_ in ('Genre', 'Director', 'Role'):
            hubItem = FakeHubItem(type_)
            dialog, calls = self._click(hubItem)
            self.assertEqual(dialog.parentWindow, calls[0][1], "TYPE={0}".format(type_))
