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

    def __init__(self, colours, fail=None, posters=None):
        self.colours = colours
        self.fail = fail
        self.paths = []
        # ratingKey -> its poster's URL as the server gives it now
        self.posters = posters or {}

    def query(self, path):
        self.paths.append(path)
        if self.fail:
            raise self.fail
        container = ET.Element('MediaContainer')
        for key in path.rsplit('/', 1)[-1].split(','):
            elem = ET.SubElement(container, 'Directory', {'ratingKey': key, 'thumb': self.posters.get(key, '')})
            if self.colours.get(key):
                ET.SubElement(elem, 'UltraBlurColors', self.colours[key])
        return container


class Episode(object):
    TYPE = 'episode'

    def __init__(self, server, season, show, own=None, seasonPoster=None):
        self.server = server
        self.parentRatingKey = season
        self.grandparentRatingKey = show
        self.ultraBlurColors = own
        self.parentThumb = seasonPoster

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


class NewPosterTest(KodiTestCase):
    """A season's colours come mostly from its poster: another poster, or a metadata refresh, has
    them asked for again (2026-10-13, House of the Dragon's season 3)."""

    def setUp(self):
        panel_colors.CACHE.clear()
        self.addCleanup(panel_colors.CACHE.clear)
        self.server = FakeServer({'10': SEASON}, posters={'10': '/library/metadata/10/thumb/100'})
        panel_colors.warm([Episode(self.server, '10', '1', OWN, '/library/metadata/10/thumb/100')])
        self.server.paths = []

    def test_a_newer_poster_asks_again(self):
        self.server.colours = {'10': SHOW}
        self.server.posters = {'10': '/library/metadata/10/thumb/200'}
        episode = Episode(self.server, '10', '1', OWN, '/library/metadata/10/thumb/200')
        panel_colors.warm([episode])
        self.assertEqual(1, len(self.server.paths))
        self.assertEqual(SHOW, panel_colors.coloursFor(episode))

    def test_the_same_poster_asks_nothing(self):
        panel_colors.warm([Episode(self.server, '10', '1', OWN, '/library/metadata/10/thumb/100')])
        self.assertEqual([], self.server.paths)

    def test_a_smaller_stamp_asks_again(self):
        """A metadata refresh can give a smaller stamp than the one before."""
        panel_colors.warm([Episode(self.server, '10', '1', OWN, '/library/metadata/10/thumb/50')])
        self.assertEqual(1, len(self.server.paths))

    def test_no_poster_asks_nothing(self):
        panel_colors.warm([Episode(self.server, '10', '1', OWN, None)])
        self.assertEqual([], self.server.paths)

    def test_the_stamp(self):
        self.assertEqual(1791848398, panel_colors.stamp('/library/metadata/100952/thumb/1791848398'))
        self.assertEqual(0, panel_colors.stamp(None))


ARTIST_ART = {'topLeft': '03030f', 'topRight': '161517', 'bottomLeft': '0b0c13', 'bottomRight': '101215'}
COVER = {'topLeft': '4e1337', 'topRight': '340f03', 'bottomLeft': '665f19', 'bottomRight': '913b5d'}


class CoverServer(object):
    """/services/ultrablur/colors?url=<image>: the colours PMS works out for an image it serves."""
    uuid = 'server'
    name = 'Server'

    def __init__(self, covers):
        self.covers = covers
        self.asked = []

    def query(self, path, params=None):
        assert path == '/services/ultrablur/colors', path
        self.asked.append(params['url'])
        container = ET.Element('MediaContainer')
        if self.covers.get(params['url']):
            ET.SubElement(container, 'UltraBlurColors', self.covers[params['url']])
        return container


class Music(object):
    def __init__(self, server, TYPE, own=None, **data):
        self.server = server
        self.TYPE = TYPE
        self.ultraBlurColors = own
        self.data = data

    def get(self, name, default=None):
        return self.data.get(name, default)


class AlbumCoverTest(KodiTestCase):
    """An album's colours from its cover, not the artist's background Plex makes them from (8 of Barenaked Ladies'
    11 albums on Animal the same, 2026-10-23); a track's from its album's cover."""

    def setUp(self):
        panel_colors.CACHE.clear()
        self.addCleanup(panel_colors.CACHE.clear)
        self.server = CoverServer({'/library/metadata/5/thumb/100': COVER})

    def album(self, cover='/library/metadata/5/thumb/100'):
        return Music(self.server, 'album', ARTIST_ART, ratingKey='5', thumb=cover)

    def test_an_album_takes_its_covers_colours(self):
        album = self.album()
        panel_colors.warmCovers([album])
        self.assertEqual(COVER, panel_colors.coloursFor(album))

    def test_a_track_takes_its_albums_covers(self):
        track = Music(self.server, 'track', ARTIST_ART, parentRatingKey='5', parentThumb='/library/metadata/5/thumb/100')
        panel_colors.warmCovers([track])
        self.assertEqual(COVER, panel_colors.coloursFor(track))
        # and the album, as the Album screen paints it, from the same answer
        self.assertEqual(COVER, panel_colors.coloursFor(self.album()))
        self.assertEqual(1, len(self.server.asked))

    def test_not_warmed_is_its_own_and_asks_nothing(self):
        self.assertEqual(ARTIST_ART, panel_colors.coloursFor(self.album()))
        self.assertEqual([], self.server.asked)

    def test_the_episode_warm_before_rows_show_asks_nothing_for_albums(self):
        """warm() runs before a grid's chunk or a row shows: one request per cover would hold them up."""
        panel_colors.warm([self.album()])
        self.assertEqual([], self.server.asked)

    def test_the_same_cover_asks_nothing_again_and_another_asks(self):
        panel_colors.warmCovers([self.album()])
        panel_colors.warmCovers([self.album()])
        self.assertEqual(1, len(self.server.asked))
        panel_colors.warmCovers([self.album('/library/metadata/5/thumb/200')])
        self.assertEqual(2, len(self.server.asked))

    def test_no_colours_for_the_cover_leaves_its_own(self):
        album = self.album('/library/metadata/5/thumb/999')
        panel_colors.warmCovers([album])
        self.assertEqual(ARTIST_ART, panel_colors.coloursFor(album))

    def test_warm_later_does_it_on_its_worker(self):
        album = self.album()
        panel_colors.warmLater([album])
        worker = panel_colors._laterWorker[0]
        if worker is not None:
            worker.join(5)
        self.assertEqual(COVER, panel_colors.coloursFor(album))

    def test_warm_later_without_albums_starts_nothing(self):
        panel_colors.warmLater([Music(self.server, 'movie')])
        self.assertEqual([], self.server.asked)

    def test_a_refused_cover_isnt_asked_again_and_the_rest_go_on(self):
        """Animal answers one cover with a 500 every time: it was asked again on every warm (2026-10-23)."""
        class Refusing(CoverServer):
            def query(self, path, params=None):
                if params['url'].endswith('/bad'):
                    self.asked.append(params['url'])
                    raise plexnet.exceptions.BadRequest('(500) internal_server_error')
                return CoverServer.query(self, path, params)

        self.server = Refusing({'/library/metadata/5/thumb/100': COVER})
        bad = Music(self.server, 'album', ARTIST_ART, ratingKey='4', thumb='/library/metadata/4/bad')
        panel_colors.warmCovers([bad, self.album()])
        self.assertEqual(ARTIST_ART, panel_colors.coloursFor(bad))
        self.assertEqual(COVER, panel_colors.coloursFor(self.album()))
        panel_colors.warmCovers([bad])
        self.assertEqual(1, self.server.asked.count('/library/metadata/4/bad'))
