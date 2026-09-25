# coding=utf-8
"""
3d in the navigation review (E2): a section's Recommended hub rows are fetched on a worker, and the
bind is posted back to the main thread (MultiWindow.postUI()) instead of running on the worker.

Importing lib.windows.* starts lib.player's monitor thread unless abort_requested is set first.
"""

from __future__ import absolute_import

from kodienv import ENV

ENV.abort_requested = True
from lib.windows import library  # noqa: E402

from .base import KodiTestCase  # noqa: E402


class FakeHost(object):
    """Just what the fetch callback and the posted bind touch."""
    _recommendedHubsFetchedFor = library.LibraryWindow._recommendedHubsFetchedFor
    _bindFetchedHubs = library.LibraryWindow._bindFetchedHubs
    closing = False
    contentMode = 'recommended'

    def __init__(self):
        self._listGeneration = 1
        self.posted = []
        self.bound = []
        self.focused = 0

    def postUI(self, name, fn, args=(), kwargs=None):
        self.posted.append((name, fn, args))

    def _recommendedHubsCallback(self, section, hubs, generation):
        self.bound.append((section, hubs, generation))

    def _focusAnchorHub(self):
        self.focused += 1


class FetchedHubsTest(KodiTestCase):
    def test_the_bind_is_posted_not_run_on_the_worker(self):
        host = FakeHost()
        host._recommendedHubsFetchedFor(1)('section', 'hubs')
        self.assertEqual([], host.bound, 'the bind runs on the main thread, not the worker')
        name, fn, args = host.posted[0]
        fn(*args)
        self.assertEqual([('section', 'hubs', 1)], host.bound)
        self.assertEqual(1, host.focused)

    def test_a_bind_after_a_swap_leaves_focus_alone(self):
        host = FakeHost()
        host._recommendedHubsFetchedFor(1)('section', 'hubs')
        host._listGeneration = 2
        name, fn, args = host.posted[0]
        fn(*args)
        self.assertEqual(0, host.focused)
