# coding=utf-8
"""
The season card's own Play/Resume button (lib/windows/episodes.py) - which episode it starts, and
which of the two buttons the card shows.

The card is a pseudo-item pinned ahead of episode 1 (EpisodesWindow.createSeasonCardItem()) and
carries no dataSource, so unlike a real episode card it has nothing for episodeListClicked() to
play. Its episode comes from _seasonPick(), the same scan _defaultEpisode() already uses to decide
where the screen lands - deliberately NOT the show's own OnDeck entry, which is a whole-show
heuristic and can point at a different season entirely (ShowWindow's Play button on the Seasons
screen does use it, and that screen is about the whole show - see tests/test_show_play_pick.py).

Importing lib.windows.episodes starts lib.player's monitor thread unless abort_requested is set
first - same guard the other lib.windows.* tests use for the same reason.
"""

from __future__ import absolute_import

from kodienv import ENV

ENV.abort_requested = True
from lib.windows import episodes  # noqa: E402

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
        self.duration = FakeValue(1800000)

    # video.py's own definitions: isWatched is viewCount OR viewOffset, isFullyWatched is viewCount
    # AND no viewOffset - so "watched but not fully" is exactly "has a view offset".
    @property
    def isWatched(self):
        return bool(self.viewCount.asInt() or self.viewOffset.asInt())

    @property
    def isFullyWatched(self):
        return bool(self.viewCount.asInt() and not self.viewOffset.asInt())

    def __repr__(self):
        return '<S{0}E{1}>'.format(self.parentIndex, self.index)


class FakeSeason(object):
    def __init__(self, rating_key, eps):
        self.ratingKey = rating_key
        self.eps = eps
        self.calls = 0

    def episodes(self):
        self.calls += 1
        return self.eps

    @property
    def viewedLeafCount(self):
        return FakeValue(len([e for e in self.eps if e.viewCount.asInt()]))


class FakeListItem(object):
    def __init__(self):
        self.props = {}

    def setProperty(self, key, value):
        self.props[key] = value

    def setBoolProperty(self, key, value):
        self.props[key] = value and '1' or ''

    def getProperty(self, key):
        return self.props.get(key, '')


class FakeControl(object):
    def __init__(self):
        self.width = None

    def setWidth(self, width):
        self.width = width


class FakeEpisodesWindow(episodes.EpisodesWindow):
    """The real methods under test, with the xbmcgui.Window half of the class stubbed out.

    Deliberately no __init__ chain-up: building a real window needs a skin, a server and a show.
    """

    def __init__(self, season):
        self.season = season
        self.show_ = season
        self._seasonCardPick = None
        self.wprops = {}
        self.controls = {}
        self.focusId = 0
        self.focusHistory = []

    def postpone_simple(self, func, *args, **kwargs):
        # Inline: the real one queues a BGThreader task, and the assertions raced its worker -
        # test_nothing_to_play_clears_the_label failed about one run in six.
        func(*args, **kwargs)

    def setProperty(self, key, value):
        self.wprops[key] = value

    def getProperty(self, key):
        return self.wprops.get(key, '')

    def getControl(self, cid):
        return self.controls.setdefault(cid, FakeControl())

    def getFocusId(self):
        return self.focusId

    def setCondFocusId(self, cid):
        self.focusHistory.append(cid)
        self.focusId = cid


class SeasonCardPickTest(KodiTestCase):
    def setUp(self):
        KodiTestCase.setUp(self)
        # applySeasonCardPlayState() only moves focus onto a control it can see; neither of these
        # means anything without a real window behind them.
        self._realWait = episodes.kodigui.waitForVisibility
        self._realVisible = episodes.xbmc.getCondVisibility
        episodes.kodigui.waitForVisibility = lambda *args, **kwargs: True
        episodes.xbmc.getCondVisibility = lambda cond: True

    def tearDown(self):
        episodes.kodigui.waitForVisibility = self._realWait
        episodes.xbmc.getCondVisibility = self._realVisible
        KodiTestCase.tearDown(self)

    def window(self, eps):
        return FakeEpisodesWindow(FakeSeason('s1', eps))

    # -- which episode ---------------------------------------------------------------------
    def test_an_in_progress_episode_wins_over_an_earlier_unwatched_one(self):
        s1e4 = FakeEpisode('4', index=4, view_offset=600000)
        eps = [FakeEpisode('1', view_count=1), FakeEpisode('2', index=2), FakeEpisode('3', index=3),
               s1e4]
        w = self.window(eps)

        self.assertEqual(s1e4, w.seasonCardEpisode())

    def test_without_progress_the_first_unwatched_is_picked(self):
        s1e3 = FakeEpisode('3', index=3)
        eps = [FakeEpisode('1', view_count=1), FakeEpisode('2', index=2, view_count=1), s1e3]
        w = self.window(eps)

        self.assertEqual(s1e3, w.seasonCardEpisode())

    def test_a_fully_watched_season_rewatches_from_the_top(self):
        # _defaultEpisode() answers None here (land on the card rather than episode 1); Play still
        # has to start somewhere.
        s1e1 = FakeEpisode('1', view_count=1)
        eps = [s1e1, FakeEpisode('2', index=2, view_count=1)]
        w = self.window(eps)

        self.assertEqual(s1e1, w.seasonCardEpisode())
        self.assertIsNone(w._defaultEpisode())

    def test_an_untouched_season_starts_at_episode_one(self):
        s1e1 = FakeEpisode('1')
        w = self.window([s1e1, FakeEpisode('2', index=2)])

        # the screen itself lands on the card for this case, but Play means episode 1
        self.assertIsNone(w._defaultEpisode())
        self.assertEqual(s1e1, w.seasonCardEpisode())

    def test_a_failed_listing_leaves_nothing_to_play(self):
        w = self.window([])
        w.season.episodes = lambda: 1 / 0

        self.assertIsNone(w.seasonCardEpisode())

    # -- the scan is paid for once ---------------------------------------------------------
    def test_the_screens_own_scan_is_handed_over_rather_than_repeated(self):
        w = self.window([FakeEpisode('1'), FakeEpisode('2', index=2)])

        w._defaultEpisode()
        w.seasonCardEpisode()
        self.assertEqual(1, w.season.calls)

    def test_switching_season_re_scans(self):
        w = self.window([FakeEpisode('1', view_count=1)])
        w._defaultEpisode()

        s2e1 = FakeEpisode('21', season=2)
        w.season = FakeSeason('s2', [s2e1])
        self.assertEqual(s2e1, w.seasonCardEpisode())

    # -- what the button row is told --------------------------------------------------------
    def test_a_started_episode_gives_the_card_resume_and_restart(self):
        # 30 minutes long, 10 in
        eps = [FakeEpisode('4', index=4, view_offset=600000)]
        w = self.window(eps)
        mli = FakeListItem()

        w.updateSeasonCardPlayState(mli)

        self.assertEqual('1', mli.getProperty('in.progress'))
        self.assertEqual('20m left', mli.getProperty('resume.timeleft'))
        self.assertEqual('S1E4', w.getProperty('play.episode'))

    def test_an_unstarted_episode_leaves_the_card_on_play(self):
        w = self.window([FakeEpisode('2', index=2)])
        mli = FakeListItem()

        w.updateSeasonCardPlayState(mli)

        self.assertEqual('', mli.getProperty('in.progress'))
        self.assertEqual('', mli.getProperty('resume.timeleft'))
        self.assertEqual('S1E2', w.getProperty('play.episode'))

    def test_nothing_to_play_clears_the_label(self):
        w = self.window([])
        w.season.episodes = lambda: 1 / 0
        mli = FakeListItem()
        w.setProperty('play.episode', 'S9E9')

        w.updateSeasonCardPlayState(mli)

        self.assertEqual('', w.getProperty('play.episode'))
        self.assertEqual('', mli.getProperty('in.progress'))

    # -- the label's own width ---------------------------------------------------------------
    def test_the_play_overlay_is_shrunk_to_the_label_it_shows(self):
        w = self.window([FakeEpisode('2', index=2)])
        mli = FakeListItem()

        w.updateSeasonCardPlayState(mli)

        label = w.controls[w.SEASON_CARD_PLAY_LABEL_TEXT_ID].width
        self.assertIsNotNone(label)
        # the skin's own starting width is the worst case ("Play S12E345"), so a short one must come
        # out under it - and the pill/group follow the include's own formula
        self.assertLess(label, 160)
        self.assertEqual(label + 62, w.controls[w.SEASON_CARD_PLAY_LABEL_PILL_ID].width)
        self.assertEqual(label + 18, w.controls[w.SEASON_CARD_PLAY_LABEL_GROUP_ID].width)

    def test_the_resume_overlay_measures_the_time_left_too(self):
        short = self.window([FakeEpisode('4', index=4, view_offset=600000)])
        short.updateSeasonCardPlayState(FakeListItem())
        shortWidth = short.controls[short.SEASON_CARD_RESUME_LABEL_TEXT_ID].width

        # 30 minutes long, 1 minute in - "29m left" is the same shape, but a longer episode number
        longer = FakeEpisodesWindow(FakeSeason('s1', [FakeEpisode('4', season=12, index=345,
                                                                  view_offset=60000)]))
        longer.updateSeasonCardPlayState(FakeListItem())
        longerWidth = longer.controls[longer.SEASON_CARD_RESUME_LABEL_TEXT_ID].width

        self.assertLess(shortWidth, longerWidth)
        # the skin's own starting width, "Resume S12E345 <bullet> 1h31m left"
        self.assertLessEqual(longerWidth, 346)

    # -- focus ------------------------------------------------------------------------------
    def test_focus_moves_off_a_button_that_just_went_invisible(self):
        # the background resolve landing while the button row already has focus: Play was showing,
        # the answer turns out to be an in-progress episode, so Play is replaced by Resume/Restart
        w = self.window([FakeEpisode('4', index=4, view_offset=600000)])
        w.focusId = w.PLAY_BUTTON_ID
        mli = FakeListItem()

        w.updateSeasonCardPlayState(mli)

        self.assertEqual([w.RESUME_BUTTON_ID], w.focusHistory)

    def test_focus_is_left_alone_when_the_row_is_not_on_a_play_button(self):
        w = self.window([FakeEpisode('4', index=4, view_offset=600000)])
        w.focusId = w.EPISODE_LIST_ID
        w.updateSeasonCardPlayState(FakeListItem())

        self.assertEqual([], w.focusHistory)
