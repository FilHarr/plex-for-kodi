"""
What a library grid asks the server for and what its placeholders carry (2026-10-27). A grid's
chunks leave out what its tiles never read (plexlibrary.gridListingParams()), by item type, and
keep the media for a sort whose caption reads it; summaries stay but for music. A placeholder
carries nothing: no index (the templates read Container(101).CurrentItem), no thumb fallback (the
templates draw the same card under every tile) and no letter (GridMixin._keyAt() works it out from
the position).

Importing lib.windows.library starts lib.player's monitor thread unless abort_requested is set
first - same guard the other lib.windows.* tests use for the same reason.
"""

from __future__ import absolute_import

from kodienv import ENV

ENV.abort_requested = True
from plexnet import plexlibrary  # noqa: E402
from lib.windows import library_grid  # noqa: E402

from .base import KodiTestCase  # noqa: E402


class GridListingParamsTest(KodiTestCase):
    def test_films_without_crew_media_or_tagline_but_with_their_summary(self):
        params = plexlibrary.gridListingParams('movie')
        self.assertIn('Role', params['excludeElements'].split(','))
        self.assertIn('Media', params['excludeElements'].split(','))
        self.assertEqual('tagline', params['excludeFields'])

    def test_a_media_sort_keeps_the_media(self):
        params = plexlibrary.gridListingParams('movie', keep_media=True)
        self.assertNotIn('Media', params['excludeElements'].split(','))
        self.assertIn('Role', params['excludeElements'].split(','))

    def test_episodes_keep_their_summary(self):
        self.assertNotIn('excludeFields', plexlibrary.gridListingParams('episode'))

    def test_music_leaves_out_its_summaries(self):
        self.assertEqual('summary', plexlibrary.gridListingParams('artist')['excludeFields'])
        self.assertEqual('summary', plexlibrary.gridListingParams('album')['excludeFields'])

    def test_collections_tracks_photos_and_folders_are_sent_whole(self):
        for kind in ('collection', 'track', 'photo', 'folder', '', None):
            self.assertIsNone(plexlibrary.gridListingParams(kind), kind)


class FakeSection(object):
    def __init__(self, type_):
        self.TYPE = type_


class FakeGrid(object):
    _listingParams = library_grid.GridMixin._listingParams
    _placeholderItems = library_grid.GridMixin._placeholderItems

    def __init__(self, section_type, item_type=None, sort='titleSort', sub_dir=None):
        self.section = FakeSection(section_type)
        self.itemType = item_type
        self.sort = sort
        self.subDir = sub_dir


class ListingParamsTest(KodiTestCase):
    def test_by_the_item_type_shown(self):
        self.assertEqual(plexlibrary.gridListingParams('album'),
                         FakeGrid('artist', item_type='album')._listingParams())
        self.assertEqual(plexlibrary.gridListingParams('movie'), FakeGrid('movie')._listingParams())

    def test_the_resolution_and_bitrate_sorts_keep_the_media(self):
        for sort in ('mediaHeight', 'mediaBitrate'):
            params = FakeGrid('movie', sort=sort)._listingParams()
            self.assertNotIn('Media', params['excludeElements'].split(','), sort)

    def test_the_watchlist_and_folders_are_sent_whole(self):
        self.assertIsNone(FakeGrid('movies_shows')._listingParams())
        self.assertIsNone(FakeGrid('movie', item_type='folder')._listingParams())
        self.assertIsNone(FakeGrid('movie', sub_dir='/library/sections/1/folder')._listingParams())


class PlaceholderItemsTest(KodiTestCase):
    def test_a_placeholder_carries_nothing(self):
        """A ListItem property write costs 0.2-0.7 ms on the AM6B (2026-10-28); the templates read
        Container(101).CurrentItem instead of an index on every tile."""
        items = FakeGrid('movie')._placeholderItems(5, 3)
        self.assertEqual([{}, {}, {}], [dict(mli.properties) for mli in items])
