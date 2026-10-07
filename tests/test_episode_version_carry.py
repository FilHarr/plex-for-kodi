# coding=utf-8
"""
The episode screen opened on an episode with a version chosen (Search's Open from, the user,
2026-10-07): its list is built from the season, fetched fresh, so its own copy of the episode
takes the same version, by the version's id (EpisodesPaginator._carryVersion()), before its info
is shown - its reloads keep it from there (EpisodesReloadTask's fromMediaChoice).

Importing lib.windows.* starts lib.player's monitor thread unless abort_requested is set first.
"""

from __future__ import absolute_import

from kodienv import ENV

ENV.abort_requested = True
from lib.windows import episodes  # noqa: E402

from .base import KodiTestCase  # noqa: E402


class Version(object):
    def __init__(self, mediaID):
        self.id = mediaID
        self.attrs = {}

    def set(self, key, value):
        self.attrs[key] = value


class Choice(object):
    def __init__(self, media, partIndex=0):
        self.media = media
        self.partIndex = partIndex


class Episode(object):
    def __init__(self, ratingKey, *versions):
        self.ratingKey = ratingKey
        self.media = list(versions)
        self.mediaChoice = None

    def __eq__(self, other):
        return isinstance(other, Episode) and self.ratingKey == other.ratingKey

    def __ne__(self, other):
        return not self.__eq__(other)

    def setMediaChoice(self, media, partIndex=0):
        self.mediaChoice = Choice(media, partIndex)


class CarryVersionTest(KodiTestCase):
    def paginator(self, opened):
        pager = episodes.EpisodesPaginator.__new__(episodes.EpisodesPaginator)
        pager.parentWindow = type('Window', (), {'episode': opened})()
        return pager

    def test_the_lists_copy_takes_the_chosen_version(self):
        opened = Episode('7', Version('a'), Version('b'))
        opened.setMediaChoice(opened.media[1])
        fresh = Episode('7', Version('a'), Version('b'))
        self.paginator(opened)._carryVersion(fresh)
        self.assertEqual('b', fresh.mediaChoice.media.id)
        self.assertEqual((1, ''), (fresh.media[1].attrs['selected'], fresh.media[0].attrs['selected']))

    def test_another_episode_untouched(self):
        opened = Episode('7', Version('a'), Version('b'))
        opened.setMediaChoice(opened.media[1])
        other = Episode('8', Version('c'), Version('d'))
        self.paginator(opened)._carryVersion(other)
        self.assertIsNone(other.mediaChoice)

    def test_no_choice_nothing(self):
        fresh = Episode('7', Version('a'), Version('b'))
        self.paginator(Episode('7', Version('a'), Version('b')))._carryVersion(fresh)
        self.assertIsNone(fresh.mediaChoice)

    def test_a_choice_of_its_own_kept(self):
        opened = Episode('7', Version('a'), Version('b'))
        opened.setMediaChoice(opened.media[1])
        fresh = Episode('7', Version('a'), Version('b'))
        fresh.setMediaChoice(fresh.media[0])
        self.paginator(opened)._carryVersion(fresh)
        self.assertEqual('a', fresh.mediaChoice.media.id)
