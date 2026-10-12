# coding=utf-8
"""
The rows Plex builds from watch history, which it gives out of date (checked live on Animal,
2026-10-12/13): their items' progress and art URLs are brought up to date from the items
themselves (home.freshenWatchHistoryRows()).

Importing lib.windows.* starts lib.player's monitor thread unless abort_requested is set first.
"""

from __future__ import absolute_import

from unittest import mock
from xml.etree import ElementTree

from kodienv import ENV

ENV.abort_requested = True
from lib.windows import home  # noqa: E402
from plexnet import plexobjects  # noqa: E402

from .base import KodiTestCase  # noqa: E402


class Item(object):
    def __init__(self, ratingKey, **attrs):
        self.ratingKey = ratingKey
        self.attrs = dict(attrs)

    def get(self, attr, default=''):
        return plexobjects.PlexValue(self.attrs.get(attr, default))

    def set(self, attr, value):
        self.attrs[attr] = u'{0}'.format(value)


class Row(object):
    def __init__(self, identifier, items, title='Continue Watching'):
        self.hubIdentifier = identifier
        self.title = title
        self.items = list(items)
        self.key = '/hubs/sections/22/continueWatching/items'
        self.more = plexobjects.PlexValue('0')
        self.size = plexobjects.PlexValue(str(len(items)))


def answer(xml):
    return ElementTree.fromstring(xml)


class FreshenTest(KodiTestCase):
    def setUp(self):
        super(FreshenTest, self).setUp()
        self.server = mock.Mock()

    def freshen(self, row, xml):
        self.server.query = mock.Mock(return_value=answer(xml))
        home.freshenWatchHistoryRows(self.server, [row])

    def test_the_art_as_it_is_now(self):
        row = Row('tv.inprogress.23', [Item('1', parentThumb='/library/metadata/9/thumb/100', art='/a/100')])
        self.freshen(row, '<MediaContainer><Video ratingKey="1" parentThumb="/library/metadata/9/thumb/200" '
                          'art="/a/200"/></MediaContainer>')
        self.assertEqual('/library/metadata/9/thumb/200', row.items[0].attrs['parentThumb'])
        self.assertEqual('/a/200', row.items[0].attrs['art'])
        self.server.query.assert_called_once_with('/library/metadata/1', params={'excludeElements': home.FRESHEN_EXCLUDED})

    def test_progress_from_another_librarys_copy(self):
        row = Row('movie.inprogress.22', [Item('1', viewOffset='2148022', lastViewedAt='100')])
        self.freshen(row, '<MediaContainer><Video ratingKey="1" viewOffset="5296056" lastViewedAt="200"/>'
                          '</MediaContainer>')
        self.assertEqual('5296056', row.items[0].attrs['viewOffset'])
        self.assertEqual('200', row.items[0].attrs['lastViewedAt'])

    def test_a_next_episode_keeps_the_rows_last_watched(self):
        """Not started, it has none of its own: the row's is the show's, which Home sorts by."""
        row = Row('continueWatching', [Item('1', lastViewedAt='300')])
        self.freshen(row, '<MediaContainer><Video ratingKey="1"/></MediaContainer>')
        self.assertEqual('300', row.items[0].attrs['lastViewedAt'])

    def test_every_item_in_batches(self):
        items = [Item(str(k)) for k in range(home.METADATA_BATCH + 5)]
        self.freshen(Row('continueWatching', items), '<MediaContainer/>')
        self.assertEqual(2, self.server.query.call_count)

    def test_other_rows_are_left_alone(self):
        self.server.query = mock.Mock()
        home.freshenWatchHistoryRows(self.server, [Row('movie.recentlyadded.22', [Item('1')])])
        self.server.query.assert_not_called()

    def test_a_failure_leaves_the_row(self):
        row = Row('continueWatching', [Item('1', art='/a/100')])
        self.server.query = mock.Mock(side_effect=Exception('gone'))
        home.freshenWatchHistoryRows(self.server, [row])
        self.assertEqual('/a/100', row.items[0].attrs['art'])
