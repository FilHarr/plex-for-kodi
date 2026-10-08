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

import xml.etree.ElementTree as ET
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


def credit(title, ratingKey, type_='movie'):
    """A Discover credit, as /library/people/{key}/credits gives it."""
    return {'Metadata': {'title': title, 'ratingKey': ratingKey, 'type': type_}}


class Film(object):
    def __init__(self, title, guid, srv, type_='movie', titleSort=''):
        self.title = title
        self.type = type_
        self.TYPE = type_
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

    def test_discovers_titles_in_a_library_join_each_servers_own(self):
        # Stan Lee, live (2026-10-08): the servers credit him on 41 titles, Discover on 21 more that
        # are in a library - Logan, executive producer. Iron Man is in both, and comes once.
        animal, oscar = server('a', 'Animal'), server('o', 'Oscar')
        ironman = mock.Mock(ratingKey='1')
        inLibraries = {'Animal': [ET.Element('Video', ratingKey='1'), ET.Element('Video', ratingKey='2')],
                       'Oscar': [ET.Element('Video', ratingKey='3')]}
        asked, versioned = [], []

        def byGuid(srv, guids):
            asked.append((srv.name, tuple(guids)))
            return inLibraries[srv.name]

        def addVersions(srv, elems):
            versioned.append((srv.name, tuple(elem.get('ratingKey') for elem in elems)))
            return elems
        groups = [('producer', 'Producer', [credit('Iron Man', 'ironman'), credit('Logan', 'logan')])]
        with mock.patch.object(person, 'discoverCredits', lambda role, key: groups), \
                mock.patch.object(plexmedia.Role, 'libraryItemsByGuid', staticmethod(byGuid)), \
                mock.patch.object(person, 'addVersions', addVersions), \
                mock.patch.object(person, 'libraryItems', lambda srv, elems, initpath: [e.get('ratingKey') for e in elems]):
            _, items = self.run_task(Role(animal, tagKey='5d77'), [oscar, animal],
                                     {'Animal': [ironman], 'Oscar': []})
        self.assertEqual(['3', ironman, '2'], items)
        self.assertEqual({('Animal', ('plex://movie/ironman', 'plex://movie/logan')),
                          ('Oscar', ('plex://movie/ironman', 'plex://movie/logan'))},
                         set((name, tuple(sorted(guids))) for name, guids in asked))
        # only those the server's own answer didn't have get their versions fetched
        self.assertEqual({('Animal', ('2',)), ('Oscar', ('3',))}, set(versioned))

    def test_no_discover_answer_leaves_the_servers_own(self):
        animal = server('a', 'Animal')

        def fails(role, key):
            raise Exception('timed out')
        with mock.patch.object(person, 'discoverCredits', fails):
            _, items = self.run_task(Role(animal, tagKey='5d77'), [animal], {'Animal': ['Die Hard']})
        self.assertEqual(['Die Hard'], items)

    def test_the_credit_types_line_comes_from_discovers_groups(self):
        animal = server('a', 'Animal')
        groups = [('producer', 'Producer', []), ('actor', 'Actor', []), ('appeared', 'Appearances', []),
                  ('writer', 'Writer', []), ('other', 'Additional Credits', [])]
        lines = []
        with mock.patch.object(person, 'discoverCredits', lambda role, key: groups):
            task = person.PersonFilmographyTask(Role(animal, tagKey='5d77'), [animal], lambda items: None,
                                                on_credit_types=lines.append)
            task.isCanceled = lambda: False
            with mock.patch.object(person, 'libraryFilmography', lambda srv, key: []):
                task.run()
        self.assertEqual(['Producer, Actor, Writer'], lines)

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


class VersionsTest(KodiTestCase):
    """Open from's versions (live, 2026-10-08): repeated by /library/people/{key}/media, missing from
    /library/all."""

    def test_a_version_listed_once_per_credit_is_kept_once(self):
        # Stan Lee is cast and writer on Animal's Films copy of The Avengers: its 4K and 1080p
        # came twice each
        elem = ET.fromstring('<Video><Media id="201469"/><Media id="225648"/><Media id="201469"/>'
                             '<Media id="225648"/><Genre tag="Action"/></Video>')
        person._dropRepeatedVersions(elem)
        self.assertEqual(['201469', '225648'], [media.get('id') for media in elem.findall('Media')])
        self.assertEqual(1, len(elem.findall('Genre')))

    def test_films_from_library_all_get_their_versions_from_their_own_library(self):
        logan = ET.Element('Video', type='movie', ratingKey='76679', guid='plex://movie/logan', librarySectionID='22')
        blade = ET.Element('Video', type='movie', ratingKey='74145', guid='plex://movie/blade', librarySectionID='22')
        loki = ET.Element('Directory', type='show', ratingKey='5', guid='plex://show/loki', librarySectionID='18')
        listing = ET.fromstring('<MediaContainer librarySectionID="22">'
                                '<Video ratingKey="76679"><Media id="201428"/><Media id="225692"/></Video>'
                                '<Video ratingKey="74145"><Media id="182357"/></Video></MediaContainer>')
        srv = server('a', 'Animal')
        srv.query.return_value = listing
        self.assertEqual([logan, blade, loki], person.addVersions(srv, [logan, blade, loki]))
        self.assertEqual(['201428', '225692'], [media.get('id') for media in logan.findall('Media')])
        self.assertEqual(['182357'], [media.get('id') for media in blade.findall('Media')])
        # one query, the films' library's, by guid - a show has no versions to fetch
        self.assertEqual(1, srv.query.call_count)
        path = srv.query.call_args[0][0]
        self.assertTrue(path.startswith('/library/sections/22/all?guid='), path)


class PersonTextTest(KodiTestCase):
    """The lines beside the person's photo (on request, 2026-10-08)."""

    def window(self):
        win = person.PersonWindow.__new__(person.PersonWindow)
        win.props = {}
        win.setProperty = lambda key, value: win.props.__setitem__(key, value)
        return win

    def test_alive_the_age_goes_with_the_birth(self):
        win = self.window()
        with mock.patch.object(win, 'calculateAge', lambda born, died=None: 51):
            self.assertEqual(('2 April 1975 (51)', ''), win.lifeLines('1975-04-02', ''))

    def test_dead_the_age_goes_with_the_death(self):
        win = self.window()
        with mock.patch.object(win, 'calculateAge', lambda born, died=None: 95):
            self.assertEqual(('28 December 1922', '12 November 2018 (95)'),
                             win.lifeLines('1922-12-28', '2018-11-12'))

    def test_the_filter_shows_only_for_films_and_shows_together(self):
        animal = server('a', 'Animal')
        for films, mixed in (([Film('Die Hard', 'plex://movie/1', animal)], ''),
                             ([Film('Die Hard', 'plex://movie/1', animal),
                               Film('Fortitude', 'plex://show/2', animal, type_='show')], '1')):
            win = self.window()
            win.setBoolProperty = lambda key, value: win.props.__setitem__(key, value and '1' or '')
            # a Back restore's filter, which one kind of title leaves nothing to narrow
            win.filmographyFilter = 'show'
            win.applyFilmographyFilter = lambda: None
            win.onFilmography(films)
            self.assertEqual(mixed, win.props['filmography.mixed'])
            self.assertEqual('show' if mixed else None, win.filmographyFilter)

    def test_no_dates_no_lines(self):
        self.assertEqual(('', ''), self.window().lifeLines('', ''))

    def test_social_links_an_icon_and_a_handle_each_in_discovers_order(self):
        win = self.window()
        win.setSocialLinks([{'source': 'facebook', 'id': 'realstanlee'}, {'source': 'tiktok', 'id': 'stan'},
                            {'source': 'instagram', 'id': ''}])
        self.assertEqual({'person.social.0.icon': 'script.plex/social/facebook.png', 'person.social.0.label': 'realstanlee',
                          # a network without an icon of its own gets the link one
                          'person.social.1.icon': 'script.plex/social/link.png', 'person.social.1.label': 'stan',
                          # no handle, no line
                          'person.social.2.icon': '', 'person.social.2.label': ''}, win.props)


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
        win.filled = None
        win.fillFilmography = lambda: setattr(win, 'filled', [i.title for i in win.filmographyItems])
        with mock.patch.object(person.sidebar_model, 'loadNavSettings', lambda: {'entries': []}):
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

    def test_the_copy_shown_is_the_one_search_would_open(self):
        # Oscar's part-watched over Animal's, whatever the quality (copies.pickCopy())
        animal, oscar = server('a', 'Animal'), server('o', 'Oscar')
        watching = Film('Die Hard', 'plex://movie/diehard', oscar)
        watching.attrs.update(viewOffset='60000', lastViewedAt='100')
        win = self.window([Film('Die Hard', 'plex://movie/diehard', animal), watching])
        self.assertIs(watching, win.filmographyItems[0])

    def test_a_server_only_guid_is_its_own_title(self):
        animal, oscar = server('a', 'Animal'), server('o', 'Oscar')
        win = self.window([Film('Home video', 'tv.plex.agents.none://98691', animal),
                           Film('Other video', 'tv.plex.agents.none://98691', oscar)])
        self.assertEqual(['Home video', 'Other video'], win.filled)

    def test_open_from_lists_every_copy(self):
        animal, oscar = server('a', 'Animal'), server('o', 'Oscar')
        first, second = Film('Die Hard', 'plex://movie/diehard', animal), Film('Die Hard', 'plex://movie/diehard', oscar)
        win = self.window([first, second])
        shown = win.filmographyItems[0]
        self.assertEqual([shown, first if shown is second else second], win.copiesOf(shown))
        win.filmographyListControl = mock.Mock()
        win.filmographyListControl.getSelectedItem.return_value = mock.Mock(dataSource=shown)
        opened = []
        win.filmographyItemClicked = opened.append
        with mock.patch.object(person.copies, 'chooseFrom', lambda entries, multi: entries[1]),                 mock.patch.object(person.plexapp, 'SERVERMANAGER', mock.Mock(getServers=lambda: [animal, oscar])):
            self.assertTrue(win.openFrom())
        self.assertEqual([win.copiesOf(shown)[1]], opened)

    def test_one_copy_no_open_from(self):
        win = self.window([Film('Dogma', 'plex://movie/dogma', server('a', 'Animal'))])
        win.filmographyListControl = mock.Mock()
        win.filmographyListControl.getSelectedItem.return_value = mock.Mock(dataSource=win.filmographyItems[0])
        self.assertFalse(win.openFrom())

    def test_title_sort_wins(self):
        animal = server('a', 'Animal')
        win = self.window([Film('The Zebra', 'plex://movie/1', animal, titleSort='Zebra'),
                           Film('Mouse', 'plex://movie/2', animal)])
        self.assertEqual(['Mouse', 'The Zebra'], win.filled)

    def test_newest_first_by_title_within_a_date(self):
        # on request, 2026-10-08: by release date, a bare year before that year's dates, undated last
        animal = server('a', 'Animal')
        films = [Film('Undated', 'plex://movie/1', animal), Film('Iron Man', 'plex://movie/2', animal),
                 Film('Logan', 'plex://movie/3', animal), Film('Avengers', 'plex://movie/4', animal),
                 Film('Year only', 'plex://movie/5', animal), Film('Endgame', 'plex://movie/6', animal)]
        for film, date in zip(films[1:], ('2008-04-30', '2017-02-28', '2017-02-28', '2017', '2019-04-24')):
            film.attrs['originallyAvailableAt' if '-' in date else 'year'] = date
        win = self.window(films)
        self.assertEqual(['Endgame', 'Avengers', 'Logan', 'Year only', 'Iron Man', 'Undated'], win.filled)
