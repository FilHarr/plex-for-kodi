# coding=utf-8
"""
person.py's DiscoverCreditsTask: the Actor and Director screens' filmography from Plex's discover
service. getDiscoverCredits() returns (type, credits) pairs for every type, but a flat list of
credits when one type is asked for - the Director screen's case, which used to unpack each credit
dict into its keys and fail with "'str' object has no attribute 'get'" (live-caught 2026-09-28).

Importing lib.windows.* starts lib.player's monitor thread unless abort_requested is set first.
"""

from __future__ import absolute_import

from kodienv import ENV

ENV.abort_requested = True
from plexnet import media as plexmedia  # noqa: E402

from lib.windows import person  # noqa: E402

from .base import KodiTestCase  # noqa: E402


def credit(rating_key, title):
    return {'Metadata': {'ratingKey': rating_key, 'title': title, 'type': 'movie'}, 'role': ''}


class FakeRole(object):
    def __init__(self):
        self.asked = []

    def getDiscoverCredits(self, credit_type=None):
        self.asked.append(credit_type)
        if credit_type is not None:
            return [credit('a1', 'Alpha'), credit('b2', 'Beta')]
        return [('actor', [credit('c3', 'Gamma')]), ('director', [credit('a1', 'Alpha')])]


class DiscoverCreditsTaskTest(KodiTestCase):
    def setUp(self):
        original = plexmedia.Role.checkLibraryPresence
        plexmedia.Role.checkLibraryPresence = staticmethod(lambda server, guids: set())
        self.addCleanup(lambda: setattr(plexmedia.Role, 'checkLibraryPresence', original))

    def _run(self, credit_type):
        results = []
        role = FakeRole()
        task = person.DiscoverCreditsTask(role, None, lambda hubs, guids: results.append(hubs),
                                          credit_type=credit_type)
        # abort_requested (set above) would make every task read as canceled.
        task.isCanceled = lambda: False
        task.run()
        self.assertEqual([credit_type], role.asked)
        self.assertEqual(1, len(results))
        return [(group, [item.title for item in items]) for group, items in results[0]]

    def test_one_type_comes_back_as_one_group(self):
        self.assertEqual([('director', ['Alpha', 'Beta'])], self._run('director'))

    def test_every_type_keeps_its_groups(self):
        self.assertEqual([('actor', ['Gamma']), ('director', ['Alpha'])], self._run(None))
