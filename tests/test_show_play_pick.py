# coding=utf-8
"""
UtilMixin.getNextShowEp() (lib/windows/windowutils.py) - which episode the Seasons screen's Play
button starts a show on, and whether it resumes.

That screen is about a whole show, so it now prefers the server's own OnDeck pick (Show.onDeck,
already loaded by ShowWindow.setup()'s includeOnDeck=1 reload) over the local scan it used to do.
An on-deck entry is authoritative, specials included; the local scan is the fallback, used when
there's no on-deck at all or the pick isn't in the playlist. The scan's own skip-past-specials rule
(what reorder_with_specials() documents for 'default' mode) still applies when it has to choose
blind, and only then.

Importing lib.windows.windowutils starts lib.player's monitor thread unless abort_requested is set
first - same guard the other lib.windows.* tests use for the same reason.
"""

from __future__ import absolute_import

from kodienv import ENV

ENV.abort_requested = True
from lib.windows import windowutils  # noqa: E402

from .base import KodiTestCase  # noqa: E402

class FakeValue(object):
    """Mimics a plexnet PlexValue: usable as the value, with asInt() on top."""

    def __init__(self, value):
        self.value = value

    def asInt(self):
        return int(self.value)

    def __str__(self):
        return str(self.value)


class FakeEpisode(object):
    def __init__(self, rating_key, season=1, index=1, view_offset=0, view_count=0):
        self.ratingKey = rating_key
        self.parentIndex = FakeValue(season)
        self.index = FakeValue(index)
        self.viewOffset = FakeValue(view_offset)
        self.viewCount = FakeValue(view_count)
        self.duration = FakeValue(1000000)

    def get(self, attr, default=''):
        return getattr(self, attr)

    # plexnet's media.MediaItem compares on ratingKey, which is what lets an OnDeck copy of an
    # episode match the playlist's own copy of it.
    def __eq__(self, other):
        return self.ratingKey == getattr(other, 'ratingKey', None)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.ratingKey)

    def __repr__(self):
        return '<S{0}E{1}>'.format(self.parentIndex, self.index)


class FakePlaylist(object):
    def __init__(self):
        self.current = None

    def setCurrent(self, item):
        self.current = item
        return True


class FakeShowWindow(windowutils.UtilMixin):
    pass


class GetNextShowEpTest(KodiTestCase):
    def setUp(self):
        KodiTestCase.setUp(self)
        self.window = FakeShowWindow()
        self.pl = FakePlaylist()

    def run_(self, items, on_deck=None, specials_mode='default', start_over=False):
        return self.window.getNextShowEp(self.pl, items, on_deck=on_deck, specials_mode=specials_mode,
                                         start_over=start_over)

    # -- the server's pick ----------------------------------------------------------------
    def test_an_on_deck_pick_with_progress_wins_over_the_local_scan(self):
        s1e2 = FakeEpisode('2', index=2, view_offset=500)
        s1e5 = FakeEpisode('5', index=5, view_offset=900)
        items = [FakeEpisode('1'), s1e2, FakeEpisode('3'), FakeEpisode('4'), s1e5]

        self.assertTrue(self.run_(items, on_deck=[FakeEpisode('2', index=2, view_offset=500)]))
        # not s1e5, which is what the local scan's own reversed order would have picked
        self.assertEqual(s1e2, self.pl.current)

    def test_an_on_deck_pick_without_progress_starts_from_its_beginning(self):
        s1e3 = FakeEpisode('3', index=3)
        items = [FakeEpisode('1', view_count=1), FakeEpisode('2', view_count=1), s1e3]

        self.assertFalse(self.run_(items, on_deck=[FakeEpisode('3', index=3)]))
        self.assertEqual(s1e3, self.pl.current)

    def test_an_on_deck_pick_missing_from_the_playlist_falls_back_to_the_scan(self):
        s1e4 = FakeEpisode('4', index=4, view_offset=700)
        items = [FakeEpisode('1'), s1e4]

        # the server's pick is fully watched, so it never made it into the unwatched-only playlist
        self.assertTrue(self.run_(items, on_deck=[FakeEpisode('99', index=99, view_count=1)]))
        self.assertEqual(s1e4, self.pl.current)

    # -- specials -------------------------------------------------------------------------
    def test_an_unstarted_special_on_deck_is_honoured(self):
        # Battlestar's real case: the miniseries sits in season 0 and genuinely is episode one, so
        # the server's pick wins over the local scan's own skip-past-specials heuristic - even
        # though an in-progress regular episode is sitting right there.
        special = FakeEpisode('0', season=0, index=1)
        s1e2 = FakeEpisode('2', index=2, view_offset=400)
        items = [special, FakeEpisode('1'), s1e2]

        self.assertFalse(self.run_(items, on_deck=[FakeEpisode('0', season=0, index=1)]))
        self.assertEqual(special, self.pl.current)

    def test_the_local_scan_still_skips_specials_when_there_is_no_on_deck(self):
        # the heuristic is for picking blind, and is untouched - it just doesn't outrank the server
        special = FakeEpisode('0', season=0, index=1)
        s1e1 = FakeEpisode('1')
        items = [special, s1e1, FakeEpisode('2')]

        self.assertFalse(self.run_(items))
        self.assertEqual(s1e1, self.pl.current)

    def test_a_started_special_on_deck_is_honoured(self):
        special = FakeEpisode('0', season=0, index=1, view_offset=250)
        items = [special, FakeEpisode('1'), FakeEpisode('2')]

        self.assertTrue(self.run_(items, on_deck=[FakeEpisode('0', season=0, index=1,
                                                              view_offset=250)]))
        self.assertEqual(special, self.pl.current)

    # -- no on-deck: the behaviour that was there before ----------------------------------
    def test_without_on_deck_the_last_in_progress_episode_is_picked(self):
        s1e2 = FakeEpisode('2', index=2, view_offset=500)
        s1e5 = FakeEpisode('5', index=5, view_offset=900)
        items = [FakeEpisode('1'), s1e2, FakeEpisode('3'), FakeEpisode('4'), s1e5]

        self.assertTrue(self.run_(items))
        self.assertEqual(s1e5, self.pl.current)

    def test_without_on_deck_or_progress_the_first_unwatched_is_picked(self):
        s1e3 = FakeEpisode('3', index=3)
        items = [FakeEpisode('1', view_count=1), FakeEpisode('2', view_count=1), s1e3]

        self.assertFalse(self.run_(items))
        self.assertEqual(s1e3, self.pl.current)

    # -- picking blind: where they left off ------------------------------------------------
    def test_the_episode_after_the_latest_watched_one_is_picked(self):
        s1e3 = FakeEpisode('3', index=3)
        items = [FakeEpisode('1', view_count=1), FakeEpisode('2', view_count=1), s1e3,
                 FakeEpisode('4', index=4)]

        self.assertFalse(self.run_(items))
        self.assertEqual(s1e3, self.pl.current)

    def test_a_fully_watched_show_restarts_at_the_first_regular_episode(self):
        # the rewatch case: Show.all(unwatched=True) falls back to every episode, so nothing here
        # is unwatched. Used to wrap around to items[0] - a special - via revitems[k-2].
        s1e1 = FakeEpisode('1', view_count=1)
        items = [FakeEpisode('0', season=0, index=1, view_count=1), s1e1,
                 FakeEpisode('2', index=2, view_count=1)]

        self.assertFalse(self.run_(items))
        self.assertEqual(s1e1, self.pl.current)

    def test_only_the_first_episode_watched_still_advances(self):
        # the walk ran out of iterations to notice this one before
        s1e2 = FakeEpisode('2', index=2)
        items = [FakeEpisode('1', view_count=1), s1e2, FakeEpisode('3', index=3)]

        self.assertFalse(self.run_(items))
        self.assertEqual(s1e2, self.pl.current)

    # -- picking blind: specials, per tv_specials_order -------------------------------------
    def test_interleave_mode_lets_the_scan_start_on_a_special(self):
        # the queue was ordered by air date, so position in it is the answer - skipping season 0
        # would contradict the ordering the setting just applied
        special = FakeEpisode('0', season=0, index=1)
        items = [special, FakeEpisode('1'), FakeEpisode('2', index=2)]

        self.assertFalse(self.run_(items, specials_mode='interleave'))
        self.assertEqual(special, self.pl.current)

    def test_a_show_with_nothing_but_specials_still_plays_something(self):
        first = FakeEpisode('0', season=0, index=1)
        items = [first, FakeEpisode('9', season=0, index=2)]

        self.assertFalse(self.run_(items))
        self.assertEqual(first, self.pl.current)

    # -- Restart (start_over) ----------------------------------------------------------------
    def test_restart_starts_the_same_started_episode_unresumed(self):
        started = FakeEpisode('1', view_offset=600)

        self.assertFalse(self.run_([started], on_deck=[FakeEpisode('1', view_offset=600)], start_over=True))
        self.assertEqual(started, self.pl.current)

    def test_restart_picks_the_same_episode_resume_would(self):
        s1e2 = FakeEpisode('2', index=2, view_offset=500)
        items = [FakeEpisode('1'), s1e2, FakeEpisode('3', index=3, view_offset=900)]

        self.assertTrue(self.run_(items, on_deck=[FakeEpisode('2', index=2, view_offset=500)]))
        resumed = self.pl.current
        self.assertFalse(self.run_(items, on_deck=[FakeEpisode('2', index=2, view_offset=500)], start_over=True))
        self.assertEqual(resumed, self.pl.current)
