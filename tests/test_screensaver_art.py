# coding=utf-8
"""
The Plex screensaver's art (plan Phase 9.4): random art from every server the sidebar has libraries
from, mixed together - it was the selected server's, which in the screensaver's own process, straight
after plex.init(), was usually not picked yet. Each server's first connection test is waited for;
one that doesn't answer is left out.

Importing lib.windows.* starts lib.player's monitor thread unless abort_requested is set first.
"""

from __future__ import absolute_import

from unittest import mock

from kodienv import ENV

ENV.abort_requested = True
from lib.windows import slidehshow  # noqa: E402

from .base import KodiTestCase  # noqa: E402


def server(name, arts, answers=True):
    s = mock.Mock()
    s.name = name
    s.library.randomArts.return_value = [mock.Mock(server=s, title=a) for a in arts]
    s.answers = answers
    return s


class FetchArtsTest(KodiTestCase):
    def fetch(self, sidebar, account=()):
        show = slidehshow.Slideshow.__new__(slidehshow.Slideshow)
        manager = mock.Mock()
        manager.getServers.return_value = list(account)
        with mock.patch.object(slidehshow.section_ids, 'sidebarServers', lambda: list(sidebar)), \
                mock.patch.object(slidehshow.section_ids, 'awaitConnection', lambda s, timeout: s.answers), \
                mock.patch.object(slidehshow.plexapp, 'SERVERMANAGER', manager):
            return show.fetchArts()

    def test_every_sidebar_servers_art_mixed(self):
        animal, oscar = server('Animal', ['a1', 'a2']), server('Oscar', ['o1'])
        images = self.fetch([animal, oscar])
        self.assertEqual(['a1', 'a2', 'o1'], sorted(i.title for i in images))
        # each image is drawn by its own server
        self.assertEqual({animal, oscar}, set(i.server for i in images))

    def test_a_server_not_answering_is_left_out(self):
        animal, oscar = server('Animal', ['a1']), server('Oscar', ['o1'], answers=False)
        self.assertEqual(['a1'], [i.title for i in self.fetch([animal, oscar])])
        oscar.library.randomArts.assert_not_called()

    def test_no_sidebar_servers_means_every_server(self):
        animal = server('Animal', ['a1'])
        self.assertEqual(['a1'], [i.title for i in self.fetch([], account=[animal])])
