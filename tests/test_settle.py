# coding=utf-8
"""
Hero writes that wait for the cursor to rest (step 12 stage D in the navigation review):
MultiWindow.settleLater()'s one pending write, re-armed by every press and dropped when the view
changes or something newer is written, and the hub rows' two temporary variants. The real methods
are bound onto small doubles, the style test_hub_item_interactivity.py uses.

Importing lib.windows.library starts lib.player's monitor thread unless abort_requested is set
first - same guard the other lib.windows.* tests use for the same reason.
"""

from __future__ import absolute_import

from kodienv import ENV

ENV.abort_requested = True
from lib.windows import kodigui  # noqa: E402
from lib.windows import library  # noqa: E402

from .base import KodiTestCase  # noqa: E402


class FakeView(object):
    _closing = False


def host():
    h = object.__new__(kodigui.MultiWindow)
    h.__dict__.update(_current=FakeView(), _settle=None, _tickers=[])
    return h


class SettleLaterTest(KodiTestCase):
    def test_it_runs_once_the_wait_is_over(self):
        h, ran = host(), []
        h.settleLater(lambda: ran.append(1))
        due = h._settle[0]
        self.assertTrue(h._tickSettle(due - 0.01))
        self.assertEqual([], ran)
        self.assertFalse(h._tickSettle(due))
        self.assertEqual([1], ran)
        self.assertIsNone(h._settle)

    def test_each_press_replaces_the_write_and_restarts_the_wait(self):
        h, ran = host(), []
        h.settleLater(lambda: ran.append('first'))
        first_due = h._settle[0]
        h.settleLater(lambda: ran.append('second'))
        self.assertGreaterEqual(h._settle[0], first_due)
        h._tickSettle(h._settle[0])
        self.assertEqual(['second'], ran)

    def test_a_new_view_drops_it(self):
        h, ran = host(), []
        h.settleLater(lambda: ran.append(1))
        due = h._settle[0]
        h._current = FakeView()
        self.assertFalse(h._tickSettle(due))
        self.assertEqual([], ran)

    def test_a_closing_view_drops_it(self):
        h, ran = host(), []
        h.settleLater(lambda: ran.append(1))
        h._current._closing = True
        self.assertFalse(h._tickSettle(h._settle[0]))
        self.assertEqual([], ran)

    def test_cancel_drops_it(self):
        h, ran = host(), []
        h.settleLater(lambda: ran.append(1))
        due = h._settle[0]
        h.cancelSettle()
        self.assertFalse(h._tickSettle(due))
        self.assertEqual([], ran)

    def test_it_uses_the_ticker(self):
        h = host()
        h.settleLater(lambda: None)
        self.assertEqual([h._tickSettle], h._tickers)


class FakeItem(object):
    def __init__(self, ds):
        self.dataSource = ds


class FakeHero(object):
    _updateHeroFromFocusedHubItem = library.LibraryWindow._updateHeroFromFocusedHubItem
    _writeHero = library.LibraryWindow._writeHero

    def __init__(self, settle_all):
        self.settleAll = settle_all
        self.calls = []
        self.pending = None

    def settleLater(self, fn):
        self.pending = fn

    def setHeroInfo(self, ds):
        self.calls.append(('text', ds))

    def updatePanelFrom(self, ds):
        self.calls.append(('panel', ds))

    def updateArtFrom(self, ds):
        self.calls.append(('art', ds))

    def updateBackgroundFrom(self, ds):
        self.calls.append(('panel+art', ds))

    def _setNoHeroArt(self, value):
        self.calls.append(('no_hero_art', value))


class HubVariantTest(KodiTestCase):
    def test_art_waits_the_text_and_colours_follow(self):
        hero = FakeHero(settle_all=False)
        hero._updateHeroFromFocusedHubItem(400, mli=FakeItem('film'))
        self.assertEqual([('text', 'film'), ('panel', 'film'), ('no_hero_art', False)], hero.calls)
        del hero.calls[:]
        hero.pending()
        self.assertEqual([('art', 'film')], hero.calls)

    def test_everything_waits(self):
        hero = FakeHero(settle_all=True)
        hero._updateHeroFromFocusedHubItem(400, mli=FakeItem('film'))
        self.assertEqual([], hero.calls)
        hero.pending()
        self.assertEqual([('text', 'film'), ('panel+art', 'film'), ('no_hero_art', False)], hero.calls)
