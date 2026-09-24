# coding=utf-8
"""
Back on the screens with a button row and extras rows (I1 in the navigation review): a scrolled row
goes back to its first item, then the extras rows retract to the button row (Episodes: the episode
row), then Back leaves.
CommonMixin.backToRowStartOrRetract() (mixins/common.py) is the shared handleBack(); each screen
lists its own rows in backResetRows(). LibraryWindow.onAction() calls handleBack() on a hosted
screen before popping the chain (test_library_chain.OnActionHandleBackTest).

Importing lib.windows.* starts lib.player's monitor thread unless abort_requested is set first.
"""

from __future__ import absolute_import

from kodienv import ENV

ENV.abort_requested = True
from lib import util  # noqa: E402
from lib.windows import episodes, preplay, subitems  # noqa: E402
from lib.windows.mixins.common import CommonMixin  # noqa: E402

from .base import KodiTestCase  # noqa: E402

BUTTONS_VISIBLE = 'Control.IsVisible(300)'


class FakeRow(object):
    def __init__(self, pos=0):
        self.pos = pos

    def getSelectedPos(self):
        return self.pos

    def selectItem(self, pos):
        self.pos = pos


class FakeScreen(CommonMixin):
    MAIN_BUTTON_GROUP_ID = 300
    ROW_ID = 402
    MAIN_ROW_ID = 400

    def __init__(self, focus=ROW_ID, on_extras=True, row_pos=0):
        self.focus = focus
        self.props = {'on.extras': '1' if on_extras else '', 'hub.focus': '3'}
        self.row = FakeRow(row_pos)
        self.focusCalls = []

    def backResetRows(self):
        return {self.ROW_ID: self.row}

    def getFocusId(self):
        return self.focus

    def getProperty(self, key):
        return self.props.get(key, '')

    def setProperty(self, key, value):
        self.props[key] = value

    def setFocusId(self, control_id):
        self.focusCalls.append(control_id)


class _BackCase(KodiTestCase):
    def setUp(self):
        super(_BackCase, self).setUp()
        self._fastBack = util.addonSettings.fastBack
        util.addonSettings.fastBack = False
        ENV.cond_visibility[BUTTONS_VISIBLE] = True

    def tearDown(self):
        util.addonSettings.fastBack = self._fastBack
        ENV.cond_visibility.pop(BUTTONS_VISIBLE, None)
        super(_BackCase, self).tearDown()


class BackToRowStartOrRetractTest(_BackCase):
    def test_scrolled_row_resets_to_first_item_and_stays(self):
        screen = FakeScreen(row_pos=4)
        self.assertTrue(screen.backToRowStartOrRetract())
        self.assertEqual(0, screen.row.pos)
        self.assertEqual([], screen.focusCalls, "one step per press: the reset, not the retract too")

    def test_row_on_first_item_retracts_to_buttons(self):
        screen = FakeScreen()
        self.assertTrue(screen.backToRowStartOrRetract())
        self.assertEqual([300], screen.focusCalls)

    def test_retract_does_not_wait_on_focus_having_landed(self):
        """setFocusId() is queued to Kodi's GUI thread, so HasFocus straight after reads False
        (the stub's default) - Back must still count as used (live-caught on Show)."""
        self.assertTrue(FakeScreen().backToRowStartOrRetract())

    def test_retract_scrolls_the_rows_back_down(self):
        """Pre-play/Artist never reset hub.focus in onFocus(), so a jump from a deeper row left
        the rows scrolled up and the buttons out of view (live-caught from Pre-play's Related)."""
        screen = FakeScreen()
        screen.backToRowStartOrRetract()
        self.assertEqual('0', screen.props['hub.focus'])
        self.assertEqual('', screen.props['on.extras'])

    def test_screen_can_retract_somewhere_other_than_the_buttons(self):
        """Episodes retracts to its episode row (400), which sits above the buttons."""
        ENV.cond_visibility['Control.IsVisible(400)'] = True
        try:
            screen = FakeScreen()
            screen.BACK_RETRACT_ID = 400
            self.assertTrue(screen.backToRowStartOrRetract())
            self.assertEqual([400], screen.focusCalls)
        finally:
            ENV.cond_visibility.pop('Control.IsVisible(400)', None)

    def test_episodes_retracts_to_its_episode_row(self):
        self.assertEqual(episodes.EpisodesWindow.EPISODE_LIST_ID, episodes.EpisodesWindow.BACK_RETRACT_ID)
        for cls in (subitems.ShowWindow, subitems.ArtistWindow, preplay.PrePlayWindow):
            self.assertIsNone(cls.BACK_RETRACT_ID, cls.__name__)

    def test_hidden_button_row_lets_back_leave(self):
        """Episodes under disable_playback hides group 300: nothing to retract to."""
        ENV.cond_visibility[BUTTONS_VISIBLE] = False
        screen = FakeScreen()
        self.assertFalse(screen.backToRowStartOrRetract())
        self.assertEqual([], screen.focusCalls)

    def test_main_row_leaves_straight_away(self):
        screen = FakeScreen(focus=FakeScreen.MAIN_ROW_ID, on_extras=False)
        self.assertFalse(screen.backToRowStartOrRetract())

    def test_button_row_leaves(self):
        screen = FakeScreen(focus=301, on_extras=False)
        self.assertFalse(screen.backToRowStartOrRetract())

    def test_fast_back_still_resets_the_row_but_skips_the_retract(self):
        util.addonSettings.fastBack = True
        screen = FakeScreen(row_pos=2)
        self.assertTrue(screen.backToRowStartOrRetract())
        self.assertFalse(screen.backToRowStartOrRetract())
        self.assertEqual([], screen.focusCalls)


class _Controls(object):
    """Stands in for a screen instance: every *ListControl attribute a backResetRows() reads."""

    def __init__(self, cls):
        for name in ('rolesListControl', 'reviewsListControl', 'extraListControl', 'relatedListControl',
                     'subItemListControl', 'popularTracksListControl', 'episodeListControl'):
            setattr(self, name, name)
        self.collectionListControls = ['collection0', 'collection1', 'collection2']
        self.albumTypeListControls = {404: 'live', 405: 'compilation'}
        for attr in dir(cls):
            if attr.endswith('_ID') or attr.endswith('_IDS'):
                setattr(self, attr, getattr(cls, attr))


class BackResetRowsTest(KodiTestCase):
    """Every extras row on every screen resets; each screen's main row doesn't."""

    def test_show(self):
        rows = subitems.ShowWindow.backResetRows(_Controls(subitems.ShowWindow))
        self.assertEqual({401, 402, 403}, set(rows))
        self.assertNotIn(subitems.ShowWindow.SUB_ITEM_LIST_ID, rows)

    def test_artist_includes_albums_and_has_no_roles_or_extras(self):
        rows = subitems.ArtistWindow.backResetRows(_Controls(subitems.ArtistWindow))
        self.assertEqual({400, 401, 402, 404, 405}, set(rows))
        self.assertNotIn(None, rows)

    def test_preplay(self):
        rows = preplay.PrePlayWindow.backResetRows(_Controls(preplay.PrePlayWindow))
        self.assertEqual({400, 401, 402, 403, 404, 405, 406}, set(rows))
        self.assertEqual('collection2', rows[406])

    def test_episodes(self):
        rows = episodes.EpisodesWindow.backResetRows(_Controls(episodes.EpisodesWindow))
        self.assertEqual({402, 403}, set(rows))
        self.assertNotIn(episodes.EpisodesWindow.EPISODE_LIST_ID, rows)

    def test_each_screen_hands_back_to_the_shared_steps(self):
        for cls in (subitems.ShowWindow, subitems.ArtistWindow, preplay.PrePlayWindow, episodes.EpisodesWindow):
            calls = []

            class Probe(object):
                def backToRowStartOrRetract(self):
                    calls.append(True)
                    return 'result'
            self.assertEqual('result', cls.handleBack(Probe()), cls.__name__)
            self.assertEqual([True], calls)
