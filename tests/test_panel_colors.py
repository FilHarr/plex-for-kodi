# coding=utf-8
"""An episode's colour panel takes its season's colours, or its show's when the season has none,
wherever it's shown (lib/windows/panel_colors.py; the user, 2026-10-09). Checked live on Animal the
same day: 130 episodes across both TV libraries' rows, 34 seasons in one 48 ms request, all 130
matching."""

from __future__ import absolute_import

import xml.etree.ElementTree as ET

from kodienv import ENV

ENV.abort_requested = True
import plexnet  # noqa: E402
from lib.windows import panel_colors  # noqa: E402

from .base import KodiTestCase  # noqa: E402

SEASON = {'topLeft': '111111', 'topRight': '222222', 'bottomLeft': '333333', 'bottomRight': '444444'}
SHOW = {'topLeft': 'aaaaaa', 'topRight': 'bbbbbb', 'bottomLeft': 'cccccc', 'bottomRight': 'dddddd'}


class FakeServer(object):
    uuid = 'server'
    name = 'Server'

    def __init__(self, colours, fail=None):
        self.colours = colours
        self.fail = fail
        self.paths = []

    def query(self, path):
        self.paths.append(path)
        if self.fail:
            raise self.fail
        container = ET.Element('MediaContainer')
        for key in path.rsplit('/', 1)[-1].split(','):
            elem = ET.SubElement(container, 'Directory', {'ratingKey': key})
            if self.colours.get(key):
                ET.SubElement(elem, 'UltraBlurColors', self.colours[key])
        return container


class Episode(object):
    TYPE = 'episode'

    def __init__(self, server, season, show, own=None):
        self.server = server
        self.parentRatingKey = season
        self.grandparentRatingKey = show
        self.ultraBlurColors = own

    def get(self, name, default=None):
        return getattr(self, name, default)


class Hub(object):
    def __init__(self, *items):
        self.items = list(items)


OWN = {'topLeft': '010101', 'topRight': '020202', 'bottomLeft': '030303', 'bottomRight': '040404'}


class PanelColoursTest(KodiTestCase):
    def setUp(self):
        panel_colors.CACHE.clear()
        self.addCleanup(panel_colors.CACHE.clear)

    def warmed(self, server, episode):
        panel_colors.warmHubs([Hub(episode)])
        return panel_colors.coloursFor(episode)

    def test_an_episode_takes_its_seasons_colours(self):
        server = FakeServer({'10': SEASON, '1': SHOW})
        self.assertEqual(SEASON, self.warmed(server, Episode(server, '10', '1', OWN)))

    def test_a_season_without_colours_falls_back_to_the_show(self):
        server = FakeServer({'1': SHOW})
        self.assertEqual(SHOW, self.warmed(server, Episode(server, '10', '1', OWN)))

    def test_neither_leaves_the_episodes_own(self):
        server = FakeServer({})
        self.assertEqual(OWN, self.warmed(server, Episode(server, '10', '1', OWN)))

    def test_a_refusal_leaves_the_episodes_own(self):
        server = FakeServer({'10': SEASON}, fail=plexnet.exceptions.BadRequest('(401) unauthorized'))
        self.assertEqual(OWN, self.warmed(server, Episode(server, '10', '1', OWN)))

    def test_not_warmed_is_its_own_and_asks_nothing(self):
        """coloursFor() runs as focus moves: it never asks the server itself."""
        server = FakeServer({'10': SEASON})
        self.assertEqual(OWN, panel_colors.coloursFor(Episode(server, '10', '1', OWN)))
        self.assertEqual([], server.paths)

    def test_the_same_season_everywhere_once_warmed(self):
        """Another copy of the episode - a grid's, post-play's - finds the season kept."""
        server = FakeServer({'10': SEASON})
        panel_colors.warm([Episode(server, '10', '1', OWN)])
        self.assertEqual(SEASON, panel_colors.coloursFor(Episode(server, '10', '1', OWN)))

    def test_anything_else_is_its_own(self):
        server = FakeServer({'10': SEASON})
        movie = Episode(server, '10', '1', OWN)
        movie.TYPE = 'movie'
        panel_colors.warm([movie])
        self.assertEqual([], server.paths)
        self.assertEqual(OWN, panel_colors.coloursFor(movie))

    def test_one_request_for_a_rows_seasons_and_none_again(self):
        server = FakeServer({'10': SEASON, '11': SEASON})
        hubs = [Hub(Episode(server, '10', '1'), Episode(server, '11', '1')), Hub(Episode(server, '10', '1'))]
        panel_colors.warmHubs(hubs)
        self.assertEqual(['/library/metadata/10,11'], server.paths)
        panel_colors.warmHubs(hubs)
        self.assertEqual(1, len(server.paths))

    def test_batches_of_forty(self):
        server = FakeServer({})
        panel_colors.warm([Episode(server, str(100 + i), None) for i in range(41)])
        self.assertEqual([40, 1], [path.count(',') + 1 for path in server.paths])
