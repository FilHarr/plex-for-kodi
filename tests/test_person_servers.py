# coding=utf-8
"""
person.py across servers (the user, 2026-10-06): the person screen used to ask only the server the
person was opened from, so another server's films never showed, and its "Not in Library" rows
listed films that are in a library - on the other server. Checked live: Alan Rickman's plex.tv key
(tagKey) is the same on Animal and Oscar; Animal has 13 of his films, each in two libraries, Oscar
3 others. Each server answers /library/people/{key}/media whole.

Importing lib.windows.* starts lib.player's monitor thread unless abort_requested is set first.
"""

from __future__ import absolute_import

from unittest import mock

from kodienv import ENV

ENV.abort_requested = True
from plexnet import media as plexmedia, plexobjects  # noqa: E402

from lib.windows import person  # noqa: E402

from .base import KodiTestCase  # noqa: E402


def server(uuid, name, offline=False):
    s = mock.Mock(uuid=uuid, offline=offline, gone=False)
    s.name = name
    return s


class Role(object):
    def __init__(self, srv, tagKey='', id_='136810', tag='Alan Rickman'):
        self.server = srv
        self.id = id_
        self.tag = tag
        self.attrs = {'tagKey': tagKey}

    def get(self, key, default=''):
        return plexobjects.PlexValue(self.attrs.get(key, default))


class Film(object):
    def __init__(self, title, guid, srv, type_='movie', titleSort=''):
        self.title = title
        self.type = type_
        self.server = srv
        self.guid = guid
        self.attrs = {'title': title, 'titleSort': titleSort, 'guid': guid}

    def get(self, key, default=''):
        return plexobjects.PlexValue(self.attrs.get(key, default))


class PersonServersTest(KodiTestCase):
    def test_the_sidebars_answering_servers_then_the_roles_own(self):
        animal, oscar, down = server('a', 'Animal'), server('o', 'Oscar'), server('d', 'Down', offline=True)
        other = server('x', 'Other')
        manager = mock.Mock(serversByUuid={'a': animal, 'o': oscar, 'd': down, 'x': other})
        with mock.patch.object(person.sidebar_model, 'sidebarServers', lambda: [oscar, down, animal]), \
                mock.patch.object(person.plexapp, 'SERVERMANAGER', manager):
            self.assertEqual([oscar, animal], person.personServers(Role(animal)))
            self.assertEqual([oscar, animal, other], person.personServers(Role(other)))
            # Discover's server isn't one of the account's: not asked
            self.assertEqual([oscar, animal], person.personServers(Role(server('discover', 'Discover'))))


class FilmographyTaskTest(KodiTestCase):
    def run_task(self, role, servers, answers):
        asked = []

        def films(srv, key):
            asked.append((srv.name, key))
            return answers[srv.name]
        got = []
        with mock.patch.object(person, 'libraryFilmography', films):
            task = person.PersonFilmographyTask(role, servers, got.append)
            task.isCanceled = lambda: False
            task.run()
        return asked, got[0]

    def test_every_server_asked_by_the_plex_key_in_their_order(self):
        animal, oscar = server('a', 'Animal'), server('o', 'Oscar')
        asked, items = self.run_task(Role(animal, tagKey='5d77'), [oscar, animal],
                                     {'Animal': ['Die Hard'], 'Oscar': ['Dogma']})
        self.assertEqual({('Animal', '5d77'), ('Oscar', '5d77')}, set(asked))
        self.assertEqual(['Dogma', 'Die Hard'], items)

    def test_without_a_key_only_its_own_server_by_its_id(self):
        animal, oscar = server('a', 'Animal'), server('o', 'Oscar')
        with mock.patch.object(person, 'personKey', lambda role: None):
            asked, items = self.run_task(Role(animal), [oscar, animal], {'Animal': ['Die Hard'], 'Oscar': ['Dogma']})
        self.assertEqual([('Animal', '136810')], asked)
        self.assertEqual(['Die Hard'], items)

    def test_a_server_that_fails_is_left_out(self):
        animal, oscar = server('a', 'Animal'), server('o', 'Oscar')

        def films(srv, key):
            if srv.name == 'Oscar':
                raise Exception('404')
            return ['Die Hard']
        got = []
        with mock.patch.object(person, 'libraryFilmography', films):
            task = person.PersonFilmographyTask(Role(animal, tagKey='5d77'), [oscar, animal], got.append)
            task.isCanceled = lambda: False
            task.run()
        self.assertEqual([['Die Hard']], got)


class LibraryPresenceTest(KodiTestCase):
    def test_in_a_library_on_any_server_the_first_that_has_it(self):
        animal, oscar = server('a', 'Animal'), server('o', 'Oscar')
        have = {'Animal': {'plex://movie/diehard', 'plex://movie/both'}, 'Oscar': {'plex://movie/dogma', 'plex://movie/both'}}
        with mock.patch.object(plexmedia.Role, 'checkLibraryPresence',
                               staticmethod(lambda srv, guids: have[srv.name] & set(guids))):
            present = person.libraryPresence([oscar, animal], ['plex://movie/diehard', 'plex://movie/dogma',
                                                               'plex://movie/both', 'plex://movie/neither'])
        self.assertEqual({'plex://movie/diehard': animal, 'plex://movie/dogma': oscar, 'plex://movie/both': oscar},
                         present)

    def test_no_servers_nothing(self):
        self.assertEqual({}, person.libraryPresence(None, ['plex://movie/x']))


class FilmographyListTest(KodiTestCase):
    """What's loaded, as the filter has it: one entry for copies of a film, by title."""

    def window(self, items, filter_=None):
        win = person.PersonWindow.__new__(person.PersonWindow)
        win.filmographyAllItems = items
        win.filmographyFilter = filter_
        win.getItemBitrate = lambda item: 0
        win.filled = None
        win.fillFilmography = lambda: setattr(win, 'filled', [i.title for i in win.filmographyItems])
        win.applyFilmographyFilter()
        return win

    def test_copies_on_two_servers_are_one_by_title(self):
        animal, oscar = server('a', 'Animal'), server('o', 'Oscar')
        win = self.window([Film('Die Hard', 'plex://movie/diehard', animal),
                           Film('Dogma', 'plex://movie/dogma', oscar),
                           Film('Alice in Wonderland', 'plex://movie/alice', animal),
                           Film('Die Hard', 'plex://movie/diehard', oscar)])
        self.assertEqual(['Alice in Wonderland', 'Die Hard', 'Dogma'], win.filled)
        self.assertEqual(2, len(win.filmographyByGuid['plex://movie/diehard']))

    def test_the_filter_works_on_whats_loaded(self):
        animal = server('a', 'Animal')
        win = self.window([Film('Die Hard', 'plex://movie/1', animal),
                           Film('Fortitude', 'plex://show/2', animal, type_='show')], filter_='show')
        self.assertEqual(['Fortitude'], win.filled)

    def test_title_sort_wins(self):
        animal = server('a', 'Animal')
        win = self.window([Film('The Zebra', 'plex://movie/1', animal, titleSort='Zebra'),
                           Film('Mouse', 'plex://movie/2', animal)])
        self.assertEqual(['Mouse', 'The Zebra'], win.filled)
