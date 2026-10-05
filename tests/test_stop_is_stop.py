# coding=utf-8
"""
Stopping a video before its end (the user, 2026-10-05): the same every time, however far in - back
to wherever playback started from, never post-play. Post-play is for a video that plays to its end.
Whether what was played counts as watched is the server's call, from the timeline reports: the
add-on no longer decides by its own played threshold / completion behaviour (both settings gone),
and the episodes screen no longer marks episodes watched itself - it asks the server, once the
stop's report has reached it.

Importing lib.windows.* starts lib.player's monitor thread unless abort_requested is set first.
"""

from __future__ import absolute_import

import time
from unittest import mock

from kodienv import ENV

ENV.abort_requested = True
from lib import player  # noqa: E402
from lib.windows import episodes  # noqa: E402
from plexnet import nowplayingmanager, plexobjects  # noqa: E402

from .base import KodiTestCase  # noqa: E402


class StopTest(KodiTestCase):
    def stop(self, external=False):
        handler = player.SeekPlayerHandler.__new__(player.SeekPlayerHandler)
        handler.__dict__.update(
            dialog=None, seeking=player.SeekPlayerHandler.NO_SEEK, queuingNext=False, queuingSpecific=False,
            inBingeMode=False, stoppedManually=True, endedManually=False, skipPostPlay=False, duration=60 * 60000,
            playlist=None, player=mock.Mock(isExternal=external))
        for name in ('updateNowPlaying', 'triggerProgressEvent', 'hideOSD', 'sessionEnded'):
            setattr(handler, name, mock.Mock())
        handler.next = mock.Mock(return_value=True)
        with mock.patch.object(player.SeekPlayerHandler, 'videoPlayedFac', new_callable=mock.PropertyMock,
                               return_value=0.97):
            handler.onPlayBackStopped()
        return handler

    def test_stopping_near_the_end_is_still_a_stop(self):
        handler = self.stop()
        handler.next.assert_not_called()
        handler.triggerProgressEvent.assert_called_once_with()
        handler.sessionEnded.assert_called_once_with()

    def test_an_external_players_stop_gets_post_play(self):
        # it can't tell a stop from the end
        handler = self.stop(external=True)
        handler.next.assert_called_once_with(on_end=True)
        self.assertTrue(handler.stoppedManually)  # no auto-advance
        handler.sessionEnded.assert_not_called()


class ProgressEventTest(KodiTestCase):
    def test_the_event_carries_the_position_only(self):
        handler = player.SeekPlayerHandler.__new__(player.SeekPlayerHandler)
        video = mock.Mock(isExtra=False, ratingKey=7, type='episode', parentRatingKey=6, grandparentRatingKey=5)
        handler.player = mock.Mock(video=video)
        handler._progressHld = {'7': 3500000}
        handler.triggerProgressEvent()
        handler.player.trigger.assert_called_once_with('video.progress', data=(5, 6, '7', 3500000))


class WaitForTimelinesTest(KodiTestCase):
    def test_waits_until_the_reports_are_answered_or_the_timeout(self):
        manager = nowplayingmanager.NowPlayingManager()
        token = object()
        manager._pendingTimelines.add(token)
        started = time.time()
        manager.waitForTimelines(0.2)
        self.assertGreaterEqual(time.time() - started, 0.2)

        context = mock.Mock(timelineToken=token, playQueue=None)
        manager.onTimelineResponse(None, None, context)
        started = time.time()
        manager.waitForTimelines(5)
        self.assertLess(time.time() - started, 0.1)


class Episode(object):
    mediaChoice = None

    def __init__(self, key, viewCount, viewOffset=0):
        self.ratingKey = key
        self.server = mock.Mock()
        self.data = {'viewCount': viewCount, 'viewOffset': viewOffset}

    def get(self, key, default=None):
        return plexobjects.PlexValue(str(self.data.get(key, default)))

    def reload(self, data=None, **kwargs):
        self.data.update(data.server)


class Row(object):
    def __init__(self, server):
        self.attrib = {'ratingKey': server.pop('key')}
        self.server = server


class SettleWithServerTest(KodiTestCase):
    def test_the_servers_word_on_each_episode_played(self):
        watched, partway, rewatched = Episode('1', 0), Episode('2', 0), Episode('3', 1)
        dlg = episodes.EpisodesWindow.__new__(episodes.EpisodesWindow)
        dlg.show_ = mock.Mock(ratingKey='s')
        dlg.season = mock.Mock(ratingKey='se')
        dlg.episodeListControl = [mock.Mock(dataSource=None)] + \
            [mock.Mock(dataSource=ep) for ep in (watched, partway, rewatched, Episode('4', 0))]
        progress = {'s': {'se': {'1': 3500000, '2': 1200000, '3': 30000}}}
        answer = [Row({'key': '1', 'viewCount': 1, 'viewOffset': 0}),
                  Row({'key': '2', 'viewCount': 0, 'viewOffset': 1190000}),
                  Row({'key': '3', 'viewCount': 1, 'viewOffset': 0})]
        with mock.patch.dict(episodes.VIDEO_PROGRESS, progress, clear=True), \
                mock.patch.object(episodes.plexapp.util.APP, 'nowplayingmanager', create=True) as npm, \
                mock.patch.object(episodes.plexobjects, 'listItems', return_value=answer) as fetch:
            dlg._settleProgressWithServer()
            settled = dict(episodes.VIDEO_PROGRESS['s']['se'])
        npm.waitForTimelines.assert_called_once_with(episodes.TIMELINE_WAIT)
        self.assertEqual('/library/metadata/1,2,3', fetch.call_args[0][1])
        # watched just now (the count went up); a resume point; a re-watch stopped early
        self.assertEqual({'1': True, '2': 1190000, '3': 0}, settled)

    def test_no_answer_leaves_the_players_positions(self):
        dlg = episodes.EpisodesWindow.__new__(episodes.EpisodesWindow)
        dlg.show_ = mock.Mock(ratingKey='s')
        dlg.season = mock.Mock(ratingKey='se')
        dlg.episodeListControl = [mock.Mock(dataSource=Episode('1', 0))]
        with mock.patch.dict(episodes.VIDEO_PROGRESS, {'s': {'se': {'1': 3500000}}}, clear=True), \
                mock.patch.object(episodes.plexapp.util.APP, 'nowplayingmanager', create=True), \
                mock.patch.object(episodes.plexobjects, 'listItems', side_effect=Exception('timed out')):
            dlg._settleProgressWithServer()
            self.assertEqual({'1': 3500000}, episodes.VIDEO_PROGRESS['s']['se'])
