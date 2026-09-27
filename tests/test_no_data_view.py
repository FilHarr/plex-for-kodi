# coding=utf-8
"""
A hosted screen whose item has gone (deleted on the server, or the server unreachable). Its setup
raises NoDataException, and it closes with navintent.noData() as its exitCommand. Nothing asked
for another screen, so the host's _open() loop set the same one up again, from the same _next and
kwargs. The host now goes back instead, as Back would, with the notice the hub menu's opens show
(LibraryWindow.viewClosed()).

Pre-play never noticed: plexnet's reload() returns the item unchanged when the fetch fails, so it
carried on and crashed reading fields only a full reload fills (live on the AM6B, 2026-09-27, a
movie deleted in Plex Web). reload() now records the failure (reloadFailed).
"""

from __future__ import absolute_import

from xml.etree import ElementTree as ET

from kodienv import ENV

ENV.abort_requested = True
from plexnet import exceptions as plexExceptions, video  # noqa: E402
from lib.windows import kodigui, library, navintent  # noqa: E402

from .base import KodiTestCase, ensure_plex_interface, fixture  # noqa: E402

try:
    from unittest import mock
except ImportError:
    import mock


class FailingView(object):
    """A screen whose onInit found no data and closed itself."""

    def __init__(self, host):
        self.host = host
        self.exitCommand = None

    def modal(self):
        self.host.builds += 1
        if self.host.builds >= self.host.stopAfter:
            self.host._allClosed = True
        self.exitCommand = navintent.noData()

    def doClose(self):
        pass


class LoopHost(object):
    _open = kodigui.MultiWindow._open
    viewClosed = kodigui.MultiWindow.viewClosed

    def __init__(self, stop_after):
        self.builds = 0
        self.stopAfter = stop_after
        self._allClosed = False
        self._openBaseWinID = None
        self._next = FailingView
        self._current = None

    def _setupCurrent(self, cls):
        self._current = cls(self)


class OpenLoopTest(KodiTestCase):
    def test_without_a_host_hook_a_screen_that_closes_itself_is_set_up_again(self):
        """Why LibraryWindow.viewClosed() exists: the loop itself only stops when asked to."""
        host = LoopHost(stop_after=3)
        with mock.patch.object(kodigui.MONITOR, 'abortRequested', return_value=False), \
                mock.patch.object(kodigui, 'ensureBaseWindow'):
            host._open()
        self.assertEqual(3, host.builds)


class GoodView(object):
    def __init__(self, host):
        self.host = host
        self.exitCommand = None

    def modal(self):
        self.host.shown.append(type(self).__name__)
        self.host._allClosed = True

    def doClose(self):
        pass


class BuildFailingHost(LoopHost):
    """Episodes loads its show as it's constructed: a 404 there escaped _open() and ended the
    session (live on the AM6B, 2026-09-27)."""

    def __init__(self, recover):
        LoopHost.__init__(self, stop_after=99)
        self.recover = recover
        self.shown = []
        self._next = 'Episodes'

    def _setupCurrent(self, cls):
        if cls == 'Episodes':
            raise plexExceptions.BadRequest('(404) not_found')
        self._current = cls(self)

    def viewFailed(self, error):
        if not self.recover:
            return False
        self._next = GoodView
        return True


class BuildFailureTest(KodiTestCase):
    def _open(self, host):
        with mock.patch.object(kodigui.MONITOR, 'abortRequested', return_value=False),                 mock.patch.object(kodigui, 'ensureBaseWindow'):
            host._open()

    def test_a_screen_that_fails_to_build_lets_the_host_pick_another(self):
        host = BuildFailingHost(recover=True)
        self._open(host)
        self.assertEqual(['GoodView'], host.shown)

    def test_without_a_host_that_recovers_the_error_still_raises(self):
        with self.assertRaises(plexExceptions.BadRequest):
            self._open(BuildFailingHost(recover=False))


class ViewClosedHost(object):
    viewClosed = library.LibraryWindow.viewClosed
    viewFailed = library.LibraryWindow.viewFailed
    _goBackFromFailedScreen = library.LibraryWindow._goBackFromFailedScreen
    popBack = library.LibraryWindow.popBack

    def __init__(self, back_stack, hosted=True):
        self._allClosed = False
        self._isHostedShell = hosted
        self._backStack = back_stack
        self.section = 'films'
        self.calls = []

    def openSection(self, section=None, **kwargs):
        self.calls.append(('openSection', section, kwargs))
        return True

    def swapTo(self, cls, push=True, **kwargs):
        self.calls.append(('swapTo', cls, push, kwargs))


class View(object):
    def __init__(self, exit_command):
        self.exitCommand = exit_command


class LibraryViewClosedTest(KodiTestCase):
    def setUp(self):
        super(LibraryViewClosedTest, self).setUp()
        patcher = mock.patch.object(library.util, 'ERROR')
        self.notice = patcher.start()
        self.addCleanup(patcher.stop)

    def test_no_data_goes_back_to_the_screen_before(self):
        host = ViewClosedHost([('ShowWindow', {'media_item': 'show'})])
        host.viewClosed(View(navintent.noData()))
        self.assertEqual([('swapTo', 'ShowWindow', False, {'media_item': 'show'})], host.calls)
        self.assertTrue(self.notice.called)

    def test_no_data_goes_back_to_the_section_the_chain_started_from(self):
        """The failed screen has already closed, so openSection() mustn't decline for it not
        being Kodi's current window."""
        host = ViewClosedHost([(None, {'section': 'films', 'filter_': None})])
        host._pendingRestoreItemPos = host._pendingRestoreHubId = None
        host.viewClosed(View(navintent.noData()))
        self.assertEqual(1, len(host.calls))
        name, section, kwargs = host.calls[0]
        self.assertEqual(('openSection', 'films'), (name, section))
        self.assertTrue(kwargs['view_gone'])

    def test_a_screen_closed_for_any_other_reason_is_left_alone(self):
        host = ViewClosedHost([('ShowWindow', {})])
        host.viewClosed(View(None))
        host.viewClosed(View(navintent.home()))
        self.assertEqual([], host.calls)
        self.assertFalse(self.notice.called)

    def test_only_hosted_screens(self):
        host = ViewClosedHost([('ShowWindow', {})], hosted=False)
        host.viewClosed(View(navintent.noData()))
        self.assertEqual([], host.calls)

    def test_a_hosted_screen_that_fails_to_build_goes_back_too(self):
        host = ViewClosedHost([('ShowWindow', {'media_item': 'show'})])
        host._next = 'EpisodesWindow'
        self.assertTrue(host.viewFailed(plexExceptions.BadRequest('(404) not_found')))
        self.assertEqual([('swapTo', 'ShowWindow', False, {'media_item': 'show'})], host.calls)
        self.assertTrue(self.notice.called)

    def test_a_view_of_its_own_that_fails_to_build_is_not_handled(self):
        host = ViewClosedHost([], hosted=False)
        host._next = 'PostersWindow'
        self.assertFalse(host.viewFailed(plexExceptions.BadRequest('(500) error')))
        self.assertEqual([], host.calls)

    def test_not_once_the_host_is_closing(self):
        host = ViewClosedHost([('ShowWindow', {})])
        host._allClosed = True
        host.viewClosed(View(navintent.noData()))
        self.assertEqual([], host.calls)


def movie():
    ensure_plex_interface()
    root = ET.fromstring(fixture("plexnet", "movie.xml"))
    return video.Movie(root.find("Video"))


class ReloadFailedTest(KodiTestCase):
    def test_a_failed_reload_is_recorded_and_a_good_one_clears_it(self):
        m = movie()
        self.assertFalse(m.reloadFailed)
        m.server = mock.Mock()
        m.server.query.side_effect = Exception('(404) not_found')
        with mock.patch.object(m, 'clearCache'):
            m.reload()
        self.assertTrue(m.reloadFailed)

        root = ET.fromstring(fixture("plexnet", "movie.xml"))
        m.server.query.side_effect = None
        m.server.query.return_value = [root.find("Video")]
        m.reload()
        self.assertFalse(m.reloadFailed)
