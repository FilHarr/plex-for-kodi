# coding=utf-8
"""
Server-advertised sort options for music sections: plexlibrary.LibrarySection.listSorts() /
sortArg() and LibraryWindow.serverSortOptions() / getSortOpts() / sortDisplay().

The static SORT_KEYS lists in sortButtonClicked() were missing sorts the server accepts (nine of
thirteen for tracks) and had one default direction wrong, so real sections now read
/library/sections/<id>/sorts?type=N&includeAdvanced=1 instead - includeAdvanced being the flag
without which the server trims the list to a basic subset. The fixture below is the response
PMS 1.43.4 gave for type=9 (albums) on 2026-09-19, trimmed; the "Album Artist" sort's compound
key and descKey shape are what sortArg() has to reproduce.

Importing lib.windows.library starts lib.player's monitor thread unless abort_requested is set
first - same guard test_dropdown.py uses for the same reason.
"""

from __future__ import absolute_import

from xml.etree import ElementTree as ET

from kodienv import ENV

ENV.abort_requested = True
from lib.windows import library  # noqa: E402
from lib.windows import library_grid  # noqa: E402

from plexnet import exceptions, plexlibrary  # noqa: E402

from .base import KodiTestCase  # noqa: E402

ALBUM_ARTIST_KEY = 'artist.titleSort,album.titleSort,album.index,album.id,album.originallyAvailableAt'
ALBUM_SORTS_PATH = '/library/sections/10/sorts?includeAdvanced=1&type=9'

ALBUM_SORTS_XML = (
    '<MediaContainer size="5">'
    '<Directory defaultDirection="asc" descKey="titleSort:desc" key="titleSort" title="Title"/>'
    '<Directory default="asc" defaultDirection="asc" descKey="artist.titleSort:desc,album.titleSort,album.index,'
    'album.id,album.originallyAvailableAt" key="{0}" title="Album Artist"/>'
    '<Directory defaultDirection="desc" descKey="lastViewedAt:desc" key="lastViewedAt" title="Date Played"/>'
    '<Directory defaultDirection="desc" descKey="ratingCount:desc" key="ratingCount" title="Popularity"/>'
    '<Directory defaultDirection="desc" descKey="somethingNew:desc" key="somethingNew" title="Something New"/>'
    '</MediaContainer>'
).format(ALBUM_ARTIST_KEY)


class FakeServer(object):
    uuid = 'fake-server'

    def __init__(self, responses):
        self.responses = responses
        self.requests = []

    def query(self, path, offset=None, limit=None, **kwargs):
        self.requests.append(path)
        response = self.responses.get(path)
        if response is None:
            raise exceptions.BadRequest(path)
        if isinstance(response, Exception):
            raise response
        return ET.fromstring(response)

    def getServer(self):
        return self


def _musicSection(server):
    root = ET.fromstring('<MediaContainer><Directory key="10" type="artist" title="Music"/></MediaContainer>')
    return plexlibrary.MusicSection(root.find('Directory'), initpath='/library/sections', server=server)


def _movieSection(server, key="2"):
    root = ET.fromstring('<MediaContainer><Directory key="{0}" type="movie" title="Movies"/></MediaContainer>'.format(key))
    return plexlibrary.MovieSection(root.find('Directory'), initpath='/library/sections', server=server)


class _Settings(object):
    def __init__(self, item_type):
        self.itemType = item_type

    def getItemType(self):
        return self.itemType


class _Window(object):
    """Just the state the four LibraryWindow methods under test read."""
    usesServerSorts = library.LibraryWindow.usesServerSorts
    serverSortOptions = library.LibraryWindow.serverSortOptions
    getSortOpts = library.LibraryWindow.getSortOpts
    sortDisplay = library.LibraryWindow.sortDisplay

    def __init__(self, section, item_type='album', sort='titleSort', desc=False):
        self.section = section
        self.librarySettings = _Settings(item_type)
        self.sort = sort
        self.sortDesc = desc


class SortArgTest(KodiTestCase):
    def test_a_plain_key_is_key_colon_direction(self):
        self.assertEqual('addedAt:desc', plexlibrary.sortArg(('addedAt', 'desc')))
        self.assertEqual('titleSort:asc', plexlibrary.sortArg(('titleSort', 'asc')))

    def test_a_compound_key_takes_the_direction_on_its_leading_component(self):
        """Matches the server's own descKey for the sort; 'a,b,c:desc' is not that shape."""
        self.assertEqual('artist.titleSort:desc,album.titleSort,album.index,album.id,album.originallyAvailableAt',
                         plexlibrary.sortArg((ALBUM_ARTIST_KEY, 'desc')))


class ListSortsTest(KodiTestCase):
    def test_requests_the_typed_endpoint_and_caches_per_type(self):
        server = FakeServer({ALBUM_SORTS_PATH: ALBUM_SORTS_XML})
        section = _musicSection(server)

        sorts = section.listSorts(libtype='album')
        self.assertEqual(['titleSort', ALBUM_ARTIST_KEY, 'lastViewedAt', 'ratingCount', 'somethingNew'],
                         [s.key for s in sorts])
        self.assertEqual('asc', sorts[1].defaultDirection)

        section.listSorts(libtype='album')
        self.assertEqual([ALBUM_SORTS_PATH], server.requests)

    def test_filters_and_sorts_do_not_share_a_cache_slot(self):
        server = FakeServer({
            ALBUM_SORTS_PATH: ALBUM_SORTS_XML,
            '/library/sections/10/filters?type=9': '<MediaContainer><Directory filter="genre" filterType="string" '
                                                   'key="/library/sections/10/genre?type=9" title="Genre"/></MediaContainer>',
        })
        section = _musicSection(server)
        self.assertEqual(['genre'], [f.filter for f in section.listFilters(libtype='album')])
        self.assertEqual(5, len(section.listSorts(libtype='album')))

    def test_a_failed_request_returns_empty_and_is_not_cached(self):
        server = FakeServer({})
        section = _musicSection(server)
        self.assertEqual([], section.listSorts(libtype='album'))
        # The typed request failed, so it retried untyped - both 400 here - and cached neither.
        self.assertEqual([ALBUM_SORTS_PATH, '/library/sections/10/sorts?includeAdvanced=1'], server.requests)
        section.listSorts(libtype='album')
        self.assertEqual(4, len(server.requests))


class ServerSortOptionsTest(KodiTestCase):
    def setUp(self):
        super(ServerSortOptionsTest, self).setUp()
        self.server = FakeServer({ALBUM_SORTS_PATH: ALBUM_SORTS_XML})
        self.section = _musicSection(self.server)

    def test_real_sections_use_the_server_except_for_collections(self):
        self.assertTrue(_Window(self.section).usesServerSorts())
        self.assertTrue(_Window(_movieSection(self.server), item_type='movie').usesServerSorts())
        self.assertTrue(_Window(_movieSection(self.server), item_type=None).usesServerSorts())
        # Collections keep the static list (the server only advertises Title; the addon also
        # offers Date Added / Content Rating, which the server does honour).
        self.assertFalse(_Window(self.section, item_type='collection').usesServerSorts())
        # A synthetic folder section's key is a path, not a section id.
        self.assertFalse(_Window(_movieSection(self.server, key='/library/sections/2/folder?parent=1')).usesServerSorts())
        # The watchlist isn't a PMS section at all.
        watchlist = plexlibrary.WatchlistSection.__new__(plexlibrary.WatchlistSection)
        self.assertFalse(_Window(watchlist).usesServerSorts())

    def test_options_keep_server_order_with_localized_labels_where_pm4k_has_them(self):
        options = _Window(self.section).serverSortOptions()

        self.assertEqual(['titleSort', 'artist.titleSort', 'lastViewedAt', 'ratingCount', 'somethingNew'],
                         [o['type'] for o in options])
        # pm4k's own strings win for keys it knows...
        self.assertEqual(library_grid.SORT_KEYS['artist']['titleSort']['title'], options[0]['title'])
        self.assertEqual(library_grid.SORT_KEYS['artist']['artist.titleSort']['display'], options[1]['display'])
        self.assertEqual(library_grid.SORT_KEYS['artist']['ratingCount']['display'], options[3]['display'])
        # ...and the server's title stands in for one it has never heard of.
        self.assertEqual('Something New', options[4]['title'])
        self.assertEqual('Something New', options[4]['display'])

    def test_default_direction_comes_from_the_server(self):
        options = {o['type']: o for o in _Window(self.section).serverSortOptions()}
        self.assertFalse(options['titleSort']['defSortDesc'])
        self.assertFalse(options['artist.titleSort']['defSortDesc'])
        self.assertTrue(options['lastViewedAt']['defSortDesc'])

    def test_the_short_key_is_the_leading_component_and_the_full_key_is_kept_alongside(self):
        """self.sort / LibrarySettings hold 'artist.titleSort' as they always have, so isAlphaSort(),
        the SORT_KEYS lookups and previously persisted settings are untouched; the compound key
        only surfaces in getSortOpts()."""
        option = _Window(self.section).serverSortOptions()[1]
        self.assertEqual('artist.titleSort', option['type'])
        self.assertEqual(ALBUM_ARTIST_KEY, option['serverKey'])

    def test_get_sort_opts_expands_to_the_full_server_key(self):
        window = _Window(self.section, sort='artist.titleSort', desc=True)
        self.assertEqual((ALBUM_ARTIST_KEY, 'desc'), window.getSortOpts())
        self.assertEqual('artist.titleSort:desc,album.titleSort,album.index,album.id,album.originallyAvailableAt',
                         plexlibrary.sortArg(window.getSortOpts()))

    def test_get_sort_opts_passes_a_plain_key_through(self):
        self.assertEqual(('titleSort', 'asc'), _Window(self.section, sort='titleSort').getSortOpts())
        # Unknown to the server too: sent as-is (the caller's resetSort() path is sortDisplay()'s job).
        self.assertEqual(('bogus', 'asc'), _Window(self.section, sort='bogus').getSortOpts())

    def test_get_sort_opts_does_not_touch_the_server_for_collections(self):
        window = _Window(self.section, item_type='collection', sort='addedAt', desc=True)
        self.assertEqual(('addedAt', 'desc'), window.getSortOpts())
        self.assertEqual([], self.server.requests)

    def test_sort_display_falls_back_to_the_server_title_then_none(self):
        self.assertEqual(library_grid.SORT_KEYS['artist']['titleSort']['display'],
                         _Window(self.section, sort='titleSort').sortDisplay())
        self.assertEqual('Something New', _Window(self.section, sort='somethingNew').sortDisplay())
        self.assertIsNone(_Window(self.section, sort='bogus').sortDisplay())

    def test_no_server_sorts_means_no_options_so_the_static_lists_take_over(self):
        section = _musicSection(FakeServer({}))
        self.assertEqual([], _Window(section).serverSortOptions())
        self.assertEqual(('artist.titleSort', 'asc'), _Window(section, sort='artist.titleSort').getSortOpts())


class LegacySortKeysTest(KodiTestCase):
    def test_every_alias_targets_a_key_with_labels(self):
        """A stored 'resolution' / 'photos.titleSort' setting has to land on a key SORT_KEYS
        knows, or sortDisplay() would reset the user's sort to Title on next open."""
        self.assertEqual('mediaHeight', library.LEGACY_SORT_KEYS['resolution'])
        self.assertEqual('photo.titleSort', library.LEGACY_SORT_KEYS['photos.titleSort'])
        for old, new in library.LEGACY_SORT_KEYS.items():
            self.assertTrue(any(new in keys for keys in library_grid.SORT_KEYS.values()), new)
            self.assertFalse(any(old in keys for keys in library_grid.SORT_KEYS.values()), old)
