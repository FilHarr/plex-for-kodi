# coding=utf-8
"""
SpoilersMixin.spoilerCovered() (lib/windows/mixins/spoilers.py, docs/spoilers-everywhere.md): which episodes have
their spoilers hidden on the screens that build many items or follow focus, with no request on the calling thread -
a show's genres from the screen's own record, then the data cache, else fetched on a worker (covered meanwhile) and
the item redone through on_known.
"""

from __future__ import absolute_import

import threading
import unittest
from unittest import mock

from kodienv import ENV

ENV.abort_requested = True
from lib.windows.mixins import spoilers  # noqa: E402

ENV.abort_requested = False


class Show(object):
    def __init__(self, genres, fetched, gate=None):
        self._genres = genres
        self._fetched = fetched
        self._gate = gate

    def genres(self):
        if self._gate is not None:
            self._gate.wait(2)
        self._fetched.append(1)
        return [mock.Mock(tag=g) for g in self._genres]


class Episode(object):
    TYPE = 'episode'

    def __init__(self, show_key='7', watched=False, fully_watched=False, genres=('Drama',), fetched=None, gate=None,
                 played=None):
        self.isWatched = watched
        self.isFullyWatched = fully_watched
        self.isPlayed = fully_watched if played is None else played
        self.server = None
        self._show_key = show_key
        self._show = Show(genres, fetched if fetched is not None else [], gate)

    def get(self, attr):
        return self._show_key if attr == 'grandparentRatingKey' else None

    def show(self):
        return self._show


class Screen(spoilers.SpoilersMixin):
    def __init__(self, setting=('unwatched',), allowed=('Reality',)):
        self._setting, self._allowed = list(setting), list(allowed)
        spoilers.SpoilersMixin.__init__(self)

    def cacheSpoilerSettings(self):
        self.spoilerSetting = self._setting
        self.spoilersAllowedFor = self._allowed


def noCache(*args, **kwargs):
    return None


@mock.patch.object(spoilers.dcm, 'getCacheData', noCache)
class SpoilerCoveredTest(unittest.TestCase):
    def waitFor(self, screen, timeout=2.0):
        """Until the screen's genre fetches have all finished."""
        done = threading.Event()
        for _ in range(int(timeout / 0.01)):
            with screen._spoilerLock:
                if not screen._spoilerQueue:
                    done.set()
                    break
            done.wait(0.01)
        self.assertTrue(done.is_set(), "genre fetch didn't finish")

    def test_not_an_episode(self):
        self.assertFalse(Screen().spoilerCovered(mock.Mock(TYPE='movie')))

    def test_watched_needs_no_genres(self):
        fetched = []
        self.assertFalse(Screen().spoilerCovered(Episode(watched=True, fetched=fetched)))
        self.assertEqual(fetched, [])

    def test_in_progress_hides_until_played_once(self):
        screen = Screen(setting=('in_progress',), allowed=())
        # a first watch, part way through
        self.assertTrue(screen.spoilerCovered(Episode(watched=True, fully_watched=False, played=False)))
        self.assertFalse(screen.spoilerCovered(Episode(watched=True, fully_watched=True)))
        # a re-watch in progress: played once, with a resume point (seen live: For All Mankind S1E1, 2026-10-20)
        self.assertFalse(screen.spoilerCovered(Episode(watched=True, fully_watched=False, played=True)))

    def test_settings_off(self):
        self.assertFalse(Screen(setting=()).spoilerCovered(Episode()))

    def test_no_allowed_genres_needs_no_lookup(self):
        fetched = []
        self.assertTrue(Screen(allowed=()).spoilerCovered(Episode(fetched=fetched)))
        self.assertEqual(fetched, [])

    def test_unknown_genres_covered_then_redone(self):
        screen = Screen()
        known = []
        ep = Episode(genres=('Reality',))
        self.assertTrue(screen.spoilerCovered(ep, on_known=known.append))
        self.waitFor(screen)
        self.assertEqual(known, [ep])
        # now known: an allowed genre, so shown
        self.assertFalse(screen.spoilerCovered(ep))

    def test_one_fetch_per_show(self):
        screen = Screen()
        fetched, known = [], []
        # the fetch held until all five have asked, so each is waiting on it
        gate = threading.Event()
        eps = [Episode(show_key='9', genres=('Drama',), fetched=fetched, gate=gate) for _ in range(5)]
        for ep in eps:
            self.assertTrue(screen.spoilerCovered(ep, on_known=known.append))
        gate.set()
        self.waitFor(screen)
        self.assertEqual(len(fetched), 1)
        self.assertEqual(known, eps)
        self.assertTrue(screen.spoilerCovered(eps[0]))

    def test_a_show_with_no_genres_is_remembered(self):
        # the data cache drops an empty list, so the screen's own record keeps it
        screen = Screen()
        fetched = []
        ep = Episode(genres=(), fetched=fetched)
        screen.spoilerCovered(ep)
        self.waitFor(screen)
        self.assertTrue(screen.spoilerCovered(ep))
        self.assertEqual(len(fetched), 1)

    def test_a_failed_fetch_stays_covered(self):
        screen = Screen()
        ep = Episode()
        ep.show = mock.Mock(side_effect=RuntimeError('no server'))
        known = []
        self.assertTrue(screen.spoilerCovered(ep, on_known=known.append))
        self.waitFor(screen)
        self.assertEqual(known, [ep])
        self.assertTrue(screen.spoilerCovered(ep))

    def test_no_callback_once_the_screen_has_closed(self):
        screen = Screen()
        screen.isOpen = False
        known = []
        screen.spoilerCovered(Episode(), on_known=known.append)
        self.waitFor(screen)
        self.assertEqual(known, [])

    def test_cached_genres(self):
        screen = Screen()
        with mock.patch.object(spoilers.dcm, 'getCacheData', return_value=['Reality']):
            self.assertFalse(screen.spoilerCovered(Episode()))
        with mock.patch.object(spoilers.dcm, 'getCacheData', return_value=['Drama']):
            self.assertTrue(Screen().spoilerCovered(Episode()))


if __name__ == '__main__':
    unittest.main()
