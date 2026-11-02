# coding=utf-8
"""
Kodi updating the add-on while it runs (lib/update_restart.py). Kodi neither stops the running script nor
tells it: it swaps the add-on folder for the new version's, and the release zip carries no compiled
templates, so the next screen opened found no XML and the session ended (live on the AM6B, 2026-10-29).
A marker in the add-on folder tells the swap; Home's tick, or the screen that fails to open, restarts
into the new version, and the new run says why it's back on Home.
"""

from __future__ import absolute_import

import importlib
import json
import os
import shutil
import sys
import tempfile

import xbmc
from kodienv import ENV

from .base import KodiTestCase, ensure_plex_interface

try:
    from unittest import mock
except ImportError:
    import mock

# importing lib.windows.* (videoplayer: lib.player) starts lib.player's monitor thread unless this is set first
ENV.abort_requested = True
ensure_plex_interface()

from lib import update_restart  # noqa: E402
from lib import util  # noqa: E402
from lib.windows import busy, kodigui, library, windowutils  # noqa: E402

HAS_ADDON = 'System.HasAddon({0})'.format(util.ADDON_ID)
# away, with no screensaver and its wait at a minute (noScreensaver())
AWAY = 60


def noScreensaver(test, minutes=1):
    """Kodi's screensaver None, its wait time minutes: no input that long is away"""
    ENV.kodi_settings['screensaver.mode'] = ''
    ENV.kodi_settings['screensaver.time'] = minutes
    for name, value in (('_noScreensaver', (None, None)), ('_playerClosedAt', None), ('_playerOpen', 0)):
        patcher = mock.patch.object(update_restart, name, value)
        patcher.start()
        test.addCleanup(patcher.stop)


class MarkerTest(KodiTestCase):
    """The marker goes with the folder it was written into; nothing else counts as replaced."""

    def setUp(self):
        KodiTestCase.setUp(self)
        self.addon_dir = tempfile.mkdtemp(prefix='pm4k-addon-')
        self.addCleanup(shutil.rmtree, self.addon_dir, True)
        info = dict(path=self.addon_dir, version='0.4.1')
        patcher = mock.patch.object(util.ADDON, 'getAddonInfo', side_effect=lambda key: info.get(key, ''))
        patcher.start()
        self.addCleanup(patcher.stop)
        for name in ('_markerPath', '_version'):
            patcher = mock.patch.object(update_restart, name, None)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_the_marker_is_written_into_the_addon_folder(self):
        update_restart.writeMarker()
        path = os.path.join(self.addon_dir, update_restart.MARKER_NAME)
        with open(path) as f:
            self.assertEqual(f.read(), '0.4.1')
        self.assertFalse(update_restart.filesReplaced())

    def test_a_replaced_folder_has_no_marker(self):
        update_restart.writeMarker()
        # Kodi renames the folder away and the new one in: the new one never had it
        os.remove(os.path.join(self.addon_dir, update_restart.MARKER_NAME))
        self.assertTrue(update_restart.filesReplaced())

    def test_no_marker_written_means_nothing_is_ever_replaced(self):
        # a read-only install keeps its compiled templates in addon_data, which an update leaves alone
        with mock.patch.dict(os.environ, {'INSTALLATION_DIR_AVOID_WRITE': '1'}):
            update_restart.writeMarker()
        self.assertFalse(os.path.exists(os.path.join(self.addon_dir, update_restart.MARKER_NAME)))
        self.assertFalse(update_restart.filesReplaced())

    def test_a_folder_it_cannot_write_to_is_not_checked(self):
        with mock.patch('builtins.open', side_effect=OSError('read-only')):
            update_restart.writeMarker()
        self.assertFalse(update_restart.filesReplaced())


class SnapshotTest(KodiTestCase):
    """The snapshot of our files, and the running copy carrying on from it once Kodi has replaced the folder."""

    def setUp(self):
        KodiTestCase.setUp(self)
        root = tempfile.mkdtemp(prefix='pm4k-snapshot-')
        self.addCleanup(shutil.rmtree, root, True)
        self.addon_dir = os.path.join(root, 'script.plexmod-uno')
        self.profile = os.path.join(root, 'addon_data')
        os.makedirs(self.profile)
        self.write_version('old')
        info = dict(path=self.addon_dir, version='0.4.1')
        patchers = [mock.patch.object(util.ADDON, 'getAddonInfo', side_effect=lambda key: info.get(key, '')),
                    mock.patch.object(util, 'PROFILE', self.profile),
                    # a package of its own, not lib: lib's already imported, from the real add-on
                    mock.patch.object(update_restart, 'SNAPSHOT_DIRS',
                                      ('snaptestpkg', os.path.join('resources', 'skins')))]
        for name, value in (('_markerPath', None), ('_addonPath', None), ('_version', None),
                            ('_snapshotPath', None), ('_usingSnapshot', False)):
            patchers.append(mock.patch.object(update_restart, name, value))
        for patcher in patchers:
            patcher.start()
            self.addCleanup(patcher.stop)
        self.addCleanup(self.forget_package)
        update_restart.writeMarker()
        self.snapshot = os.path.join(self.profile, update_restart.SNAPSHOT_NAME)

    def write_version(self, which):
        files = {
            'snaptestpkg/__init__.py': '',
            'snaptestpkg/later.py': 'VALUE = {0!r}\n'.format(which),
            'snaptestpkg/__pycache__/later.cpython-38.pyc': 'bytecode',
            'resources/skins/Main/1080i/script-plex-home.xml': '<window>{0}</window>'.format(which),
            'resources/skins/Main/media/tile.png': which,
            'resources/language/resource.language.en_gb/strings.po': which,
        }
        for rel, text in files.items():
            full = os.path.join(self.addon_dir, *rel.split('/'))
            if not os.path.isdir(os.path.dirname(full)):
                os.makedirs(os.path.dirname(full))
            with open(full, 'w') as f:
                f.write(text)

    def swap(self):
        """Kodi's install: the folder renamed away, the new version's renamed in, the old one deleted."""
        old = self.addon_dir + '-old'
        os.rename(self.addon_dir, old)
        self.write_version('new')
        shutil.rmtree(old)

    def forget_package(self):
        for name in [n for n in sys.modules if n == 'snaptestpkg' or n.startswith('snaptestpkg.')]:
            del sys.modules[name]
        sys.path[:] = [p for p in sys.path if 'pm4k-snapshot-' not in p]
        sys.meta_path[:] = [f for f in sys.meta_path if not isinstance(f, update_restart._SwapWatch)]

    def read(self, *parts):
        with open(os.path.join(*parts)) as f:
            return f.read()

    def test_it_holds_our_code_and_compiled_skin(self):
        update_restart._takeSnapshot()
        self.assertEqual(update_restart._snapshotPath, self.snapshot)
        self.assertEqual(self.read(self.snapshot, 'snaptestpkg', 'later.py'), "VALUE = 'old'\n")
        self.assertEqual(self.read(self.snapshot, 'resources', 'skins', 'Main', '1080i', 'script-plex-home.xml'),
                         '<window>old</window>')
        self.assertTrue(os.path.exists(os.path.join(self.snapshot, 'resources', 'skins', 'Main', 'media', 'tile.png')))
        # no bytecode, and nothing outside its folders
        self.assertFalse(os.path.exists(os.path.join(self.snapshot, 'snaptestpkg', '__pycache__')))
        self.assertFalse(os.path.exists(os.path.join(self.snapshot, 'resources', 'language')))

    def test_files_are_hard_links_where_possible(self):
        update_restart._takeSnapshot()
        self.assertTrue(os.path.samefile(os.path.join(self.addon_dir, 'snaptestpkg', 'later.py'),
                                         os.path.join(self.snapshot, 'snaptestpkg', 'later.py')))

    def test_without_hard_links_it_copies(self):
        with mock.patch('os.link', side_effect=OSError('not here')):
            update_restart._takeSnapshot()
        later = os.path.join(self.snapshot, 'snaptestpkg', 'later.py')
        self.assertFalse(os.path.samefile(os.path.join(self.addon_dir, 'snaptestpkg', 'later.py'), later))
        self.assertEqual(self.read(later), "VALUE = 'old'\n")
        # an unchanged copy is kept next time, a changed file copied again
        before = os.stat(later).st_ino
        home = os.path.join(self.addon_dir, 'resources', 'skins', 'Main', '1080i', 'script-plex-home.xml')
        with open(home, 'w') as f:
            f.write('<window>re-rendered, longer</window>')
        with mock.patch('os.link', side_effect=OSError('not here')):
            update_restart._takeSnapshot()
        self.assertEqual(os.stat(later).st_ino, before)
        self.assertEqual(self.read(self.snapshot, 'resources', 'skins', 'Main', '1080i', 'script-plex-home.xml'),
                         '<window>re-rendered, longer</window>')

    def test_files_gone_from_the_folder_go_from_the_snapshot(self):
        update_restart._takeSnapshot()
        os.remove(os.path.join(self.addon_dir, 'resources', 'skins', 'Main', 'media', 'tile.png'))
        update_restart._takeSnapshot()
        self.assertFalse(os.path.exists(os.path.join(self.snapshot, 'resources', 'skins', 'Main', 'media', 'tile.png')))

    def test_after_the_swap_windows_are_built_from_the_snapshot(self):
        update_restart._takeSnapshot()
        self.assertEqual(update_restart.skinPath(self.addon_dir), self.addon_dir)
        self.swap()
        self.assertEqual(update_restart.skinPath(self.addon_dir), self.snapshot)
        self.assertEqual(update_restart.skinPath(self.addon_dir + os.sep), self.snapshot)
        # the old version's XML, though its folder's gone
        self.assertEqual(self.read(self.snapshot, 'resources', 'skins', 'Main', '1080i', 'script-plex-home.xml'),
                         '<window>old</window>')
        # other paths (a read-only install's addon_data) are left alone
        self.assertEqual(update_restart.skinPath(self.profile), self.profile)

    def test_after_the_swap_a_new_import_is_the_old_version(self):
        sys.path.insert(0, self.addon_dir)
        importlib.import_module('snaptestpkg')
        update_restart.watchImports()
        update_restart._takeSnapshot()
        self.swap()
        # nothing has asked for the snapshot yet: the import itself switches to it
        self.assertEqual(importlib.import_module('snaptestpkg.later').VALUE, 'old')
        self.assertTrue(update_restart._usingSnapshot)
        self.assertIn(os.path.normcase(self.snapshot), [os.path.normcase(os.path.normpath(p)) for p in sys.path])

    def test_without_the_swap_imports_are_untouched(self):
        sys.path.insert(0, self.addon_dir)
        update_restart.watchImports()
        update_restart._takeSnapshot()
        self.assertEqual(importlib.import_module('snaptestpkg.later').VALUE, 'old')
        self.assertFalse(update_restart._usingSnapshot)
        self.assertIn(self.addon_dir, sys.path)

    def test_a_snapshot_taken_during_the_swap_is_not_used(self):
        os.remove(os.path.join(self.addon_dir, update_restart.MARKER_NAME))
        update_restart._takeSnapshot()
        self.assertIsNone(update_restart._snapshotPath)
        self.assertEqual(update_restart.skinPath(self.addon_dir), self.addon_dir)

    def test_no_snapshot_means_the_old_way(self):
        # still being taken, say: the restart goes ahead as it would have
        self.swap()
        self.assertFalse(update_restart.usingSnapshot())
        self.assertEqual(update_restart.skinPath(self.addon_dir), self.addon_dir)


class RestartTest(KodiTestCase):
    """restart() records the update for the new run, then closes Home with "restart"."""

    def setUp(self):
        KodiTestCase.setUp(self)
        noScreensaver(self)
        self.home = mock.Mock(closeOption=None)
        for target, name, value in ((windowutils, 'HOME', self.home), (windowutils, '_restarting', False),
                                    (update_restart, '_version', '0.4.1'), (update_restart, '_announcedAt', None)):
            patcher = mock.patch.object(target, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def _record(self):
        return json.loads(util.getGlobalProperty(update_restart.NOTICE_PROP))

    def test_it_closes_home_to_restart(self):
        self.assertTrue(update_restart.restart('test'))
        self.assertEqual(self.home.closeOption, 'restart')
        self.home.doClose.assert_called_once_with()

    def test_recent_input_means_the_user_is_present(self):
        ENV.idle_time = 3
        update_restart.restart('test')
        self.assertEqual(self._record(),
                         {'from': '0.4.1', 'away': False, 'screensaver': False, 'minimised': False,
                          'chosen': False})

    def test_a_restart_after_being_minimised_says_so(self):
        update_restart.restart('test', minimised=True)
        self.assertTrue(self._record()['minimised'])

    def test_a_minute_without_input_means_away(self):
        ENV.idle_time = AWAY
        update_restart.restart('test')
        self.assertTrue(self._record()['away'])

    def test_the_screensaver_means_away(self):
        ENV.cond_visibility['System.ScreenSaverActive'] = True
        update_restart.restart('test')
        self.assertTrue(self._record()['away'])
        # for the new run to start it again: its windows end it
        self.assertTrue(self._record()['screensaver'])

    def notifications(self):
        return [b for b in ENV.builtins if b.startswith('Notification(')]

    def test_a_restart_not_announced_by_the_tick_is_announced_here(self):
        # a screen that couldn't open, before the tick noticed
        ENV.idle_time = 3
        update_restart.restart('test')
        self.assertEqual(len(self.notifications()), 1)
        self.assertIn('Restarting now', self.notifications()[0])

    def test_one_the_tick_just_announced_is_not_announced_again(self):
        ENV.idle_time = 3
        update_restart.announce()
        update_restart.restart('test')
        self.assertEqual(len(self.notifications()), 1)

    def test_a_restart_the_user_chose_gets_no_notification(self):
        # they've just answered "Now"
        ENV.idle_time = 3
        update_restart.restart('test', chosen=True)
        self.assertEqual(self.notifications(), [])
        self.assertTrue(self._record()['chosen'])

    def test_a_user_who_is_away_gets_no_notification(self):
        # nobody to see it; the new run's pop-up waits for them instead
        ENV.idle_time = AWAY
        update_restart.restart('test')
        self.assertEqual(self.notifications(), [])

    def test_the_new_run_takes_the_record_once(self):
        update_restart.restart('test')
        self.assertEqual(update_restart.takeNotice(),
                         {'from': '0.4.1', 'away': False, 'screensaver': False, 'minimised': False,
                          'chosen': False})
        self.assertIsNone(update_restart.takeNotice())

    def test_only_the_first_restart_closes_home(self):
        # the tick's and a failed screen's, or a skin reload's at the same time
        update_restart.restart('test')
        windowutils.restartAfterSkinReload('test')
        self.home.doClose.assert_called_once_with()

    def test_no_home_yet_cannot_restart(self):
        with mock.patch.object(windowutils, 'HOME', None):
            self.assertFalse(update_restart.restart('test'))

    def test_a_close_that_fails_can_be_tried_again(self):
        self.home.doClose.side_effect = [RuntimeError('XML File for Window is missing'), None]
        self.assertRaises(RuntimeError, update_restart.restart, 'test')
        self.assertTrue(update_restart.restart('test'))
        self.assertEqual(self.home.doClose.call_count, 2)


class BusyDialogTest(KodiTestCase):
    """busy.dialog(): LibraryWindow.doClose() is wrapped in it, and the restart runs that with the busy XML
    gone (live on the AM6B, 2026-11-02)."""

    def setUp(self):
        KodiTestCase.setUp(self)
        patcher = mock.patch.object(busy.BusyWindow, 'create',
                                    side_effect=RuntimeError('XML File for Window is missing'))
        patcher.start()
        self.addCleanup(patcher.stop)
        self.calls = []

        @busy.dialog()
        def close():
            self.calls.append('close')
            return 'closed'
        self.close = close

    def test_after_the_swap_it_goes_ahead_without_the_busy_window(self):
        with mock.patch.object(update_restart, 'filesReplaced', return_value=True):
            self.assertEqual(self.close(), 'closed')
        self.assertEqual(self.calls, ['close'])

    def test_with_our_files_in_place_it_is_still_an_error(self):
        with mock.patch.object(update_restart, 'filesReplaced', return_value=False):
            self.assertRaises(RuntimeError, self.close)
        self.assertEqual(self.calls, [])


class TickTest(KodiTestCase):
    """LibraryWindow._tickUpdate(): the restart once the folder's replaced, and the new run's pop-up."""

    def setUp(self):
        KodiTestCase.setUp(self)
        noScreensaver(self)
        self.posted = []
        self.win = library.LibraryWindow.__new__(library.LibraryWindow)
        self.win._shuttingDown = False
        self.win._ignoreTick = False
        self.win._backStack = []
        self.postedKwargs = []
        self.win.postUI = lambda name, fn, args=(), kwargs=None: (self.posted.append((name, fn, args)),
                                                                   self.postedKwargs.append(kwargs))
        self.replaced = False
        self.now = 1000.0
        self.asking = False
        self.awayRestarts = True
        self.askAgainAfter = 3600
        for patcher in (mock.patch.object(update_restart, 'filesReplaced', side_effect=lambda: self.replaced),
                        mock.patch.object(library.time, 'time', side_effect=lambda: self.now),
                        mock.patch.object(update_restart, '_announcedAt', None),
                        # the settings: TickTest's the automatic restart, AskTest the question
                        mock.patch.object(update_restart, 'asks', side_effect=lambda: self.asking),
                        mock.patch.object(update_restart, 'restartsWhileAway', side_effect=lambda: self.awayRestarts),
                        mock.patch.object(update_restart, 'askAgainAfter', side_effect=lambda: self.askAgainAfter)):
            patcher.start()
            self.addCleanup(patcher.stop)
        ENV.cond_visibility[HAS_ADDON] = True
        # away unless a test says otherwise: no notice, no delay
        ENV.idle_time = AWAY
        # on screen, not minimised
        util.setGlobalProperty('is_active', '1')

    def names(self):
        return [name for name, _, _ in self.posted]

    def notifications(self):
        return [b for b in ENV.builtins if b.startswith('Notification(')]

    def test_a_replaced_folder_restarts_once(self):
        self.replaced = True
        self.assertTrue(self.win._tickUpdate())
        self.now += 1
        self.assertTrue(self.win._tickUpdate())
        self.assertEqual(self.names(), ['restart for update'])
        self.assertIs(self.posted[0][1], update_restart.restart)

    def test_a_user_who_is_away_is_restarted_at_once_without_a_notice(self):
        self.replaced = True
        self.win._tickUpdate()
        self.assertEqual(self.names(), ['restart for update'])
        self.assertEqual(self.notifications(), [])

    def test_a_user_who_is_there_is_told_and_the_restart_waits(self):
        self.replaced = True
        ENV.idle_time = 2
        self.win._tickUpdate()
        self.assertEqual(len(self.notifications()), 1)
        self.assertIn('The addon was updated in the background. Restarting in 5 seconds', self.notifications()[0])
        self.assertEqual(self.posted, [])
        self.now += update_restart.RESTART_DELAY - 1
        self.win._tickUpdate()
        self.assertEqual(self.posted, [])
        self.now += 1
        self.win._tickUpdate()
        self.assertEqual(self.names(), ['restart for update'])
        # told once
        self.assertEqual(len(self.notifications()), 1)

    def test_playback_during_the_wait_starts_it_over_after(self):
        self.replaced = True
        ENV.idle_time = 2
        self.win._tickUpdate()
        xbmc.Player.playing_audio = True
        self.now += update_restart.RESTART_DELAY
        self.win._tickUpdate()
        self.assertEqual(self.posted, [])
        xbmc.Player.playing_audio = False
        self.win._tickUpdate()
        self.assertEqual(self.posted, [])
        self.assertEqual(len(self.notifications()), 2)
        self.now += update_restart.RESTART_DELAY
        self.win._tickUpdate()
        self.assertEqual(self.names(), ['restart for update'])

    def test_the_restart_and_its_notice_wait_for_the_player_window(self):
        # the video's ended, post-play is up and may play the next one (live on the PC, 2026-11-02)
        self.replaced = True
        ENV.idle_time = 2
        update_restart.playerOpened()
        self.addCleanup(update_restart.playerClosed)
        self.win._tickUpdate()
        self.now += update_restart.RESTART_DELAY
        self.win._tickUpdate()
        self.assertEqual(self.posted, [])
        self.assertEqual(self.notifications(), [])
        update_restart.playerClosed()
        self.win._tickUpdate()
        self.assertEqual(len(self.notifications()), 1)
        self.now += update_restart.RESTART_DELAY
        self.win._tickUpdate()
        self.assertEqual(self.names(), ['restart for update'])

    def test_videoplayer_play_marks_the_player_window_open(self):
        from lib.windows import videoplayer
        seen = []

        def open_(**kwargs):
            seen.append(update_restart.readyToRestart())
            return mock.Mock(openAfterClose=None, playbackFailed=False)
        with mock.patch.object(videoplayer.VideoPlayerWindow, 'open', side_effect=open_), \
                mock.patch.object(videoplayer, 'player'):
            videoplayer.play()
        self.assertEqual(seen, [False])
        self.assertTrue(update_restart.readyToRestart())

    def test_the_restart_waits_for_kodi_to_list_the_new_version(self):
        self.replaced = True
        ENV.cond_visibility[HAS_ADDON] = False
        self.assertTrue(self.win._tickUpdate())
        self.assertEqual(self.posted, [])

    def test_the_restart_waits_for_music_to_end(self):
        # tick() itself already returns early while a video plays
        self.replaced = True
        xbmc.Player.playing_audio = True
        self.win._tickUpdate()
        self.assertEqual(self.posted, [])
        xbmc.Player.playing_audio = False
        self.win._tickUpdate()
        self.assertEqual(self.names(), ['restart for update'])

    def test_the_rest_of_the_tick_waits_for_the_restart(self):
        self.replaced = True
        ENV.idle_time = 2
        self.win._lastHubsRefresh = 0
        with mock.patch.object(library.mapping_probe, 'tick') as probe:
            self.win.tick()
        probe.assert_not_called()
        self.assertEqual(self.posted, [])

    def test_minimised_waits_to_be_brought_back(self):
        # closing our windows now would take the user's own Kodi screen back a step for each
        self.replaced = True
        ENV.idle_time = 2
        util.setGlobalProperty('is_active', '')
        for _ in range(3):
            self.assertTrue(self.win._tickUpdate())
            self.now += update_restart.RESTART_DELAY
        self.assertEqual(self.posted, [])
        self.assertEqual(self.notifications(), [])

    def test_brought_back_after_being_minimised_restarts_at_once(self):
        self.replaced = True
        ENV.idle_time = 2
        util.setGlobalProperty('is_active', '')
        self.win._tickUpdate()
        util.setGlobalProperty('is_active', '1')
        self.win._tickUpdate()
        self.assertEqual(self.names(), ['restart for update'])
        self.assertEqual(self.postedKwargs, [{'minimised': True}])
        # no countdown: restart() itself says it's now
        self.assertEqual(self.notifications(), [])

    def test_no_record_no_notice(self):
        self.win._updateNotice = None
        self.assertFalse(self.win._tickUpdate())
        self.assertEqual(self.posted, [])

    def test_a_user_who_was_present_is_told_at_once(self):
        self.win._updateNotice = {'from': '0.4.1', 'away': False}
        self.win._tickUpdate()
        self.win._tickUpdate()
        self.assertEqual(self.names(), ['update notice'])
        self.assertEqual(self.posted[0][2], ({'from': '0.4.1', 'away': False},))

    def test_a_user_who_was_away_is_told_when_they_are_back(self):
        self.win._updateNotice = {'from': '0.4.1', 'away': True}
        for idle in (400, 401, 402):
            ENV.idle_time = idle
            self.win._tickUpdate()
        self.assertEqual(self.posted, [])
        # a key, or the one that ends the screensaver
        ENV.idle_time = 0
        self.win._tickUpdate()
        ENV.idle_time = 1
        self.win._tickUpdate()
        self.assertEqual(self.names(), ['update notice'])

    def test_a_press_during_the_restart_counts_as_back(self):
        self.win._updateNotice = {'from': '0.4.1', 'away': True}
        ENV.idle_time = 2
        self.win._tickUpdate()
        self.assertEqual(self.names(), ['update notice'])

    def screensaverStarts(self):
        return ENV.builtins.count('ActivateScreensaver')

    def test_the_screensaver_our_start_ended_is_started_again(self):
        self.win._updateNotice = {'from': '0.4.1', 'away': True, 'screensaver': True}
        ENV.idle_time = 300
        self.win._tickUpdate()
        self.assertEqual(self.screensaverStarts(), 1)
        ENV.idle_time = 301
        self.win._tickUpdate()
        self.assertEqual(self.screensaverStarts(), 1)
        # the press that ends it is the user coming back
        ENV.idle_time = 0
        self.win._tickUpdate()
        self.assertEqual(self.names(), ['update notice'])

    def test_a_screensaver_still_on_is_left_alone(self):
        self.win._updateNotice = {'from': '0.4.1', 'away': True, 'screensaver': True}
        ENV.idle_time = 300
        ENV.cond_visibility['System.ScreenSaverActive'] = True
        self.win._tickUpdate()
        self.assertEqual(self.screensaverStarts(), 0)

    def test_no_screensaver_before_none_after(self):
        self.win._updateNotice = {'from': '0.4.1', 'away': True, 'screensaver': False}
        ENV.idle_time = 300
        self.win._tickUpdate()
        self.assertEqual(self.screensaverStarts(), 0)

    def test_a_user_back_during_the_restart_gets_the_notice_not_the_screensaver(self):
        self.win._updateNotice = {'from': '0.4.1', 'away': True, 'screensaver': True}
        ENV.idle_time = 1
        self.win._tickUpdate()
        self.assertEqual(self.screensaverStarts(), 0)
        self.assertEqual(self.names(), ['update notice'])

    def test_the_notice_names_the_new_version(self):
        with mock.patch.object(library.optionsdialog, 'show') as show, \
                mock.patch.object(util.ADDON, 'getAddonInfo',
                                  side_effect=lambda key: {'name': 'Plex Uno', 'version': '0.4.2'}.get(key, '')):
            self.win._showUpdateNotice({'from': '0.4.1', 'away': True})
        heading, text, button = show.call_args[0]
        self.assertEqual(heading, 'Plex Uno updated')
        self.assertEqual(text, 'Plex Uno was updated to 0.4.2 while you were away. '
                               'The addon was restarted during the update.')

    def test_the_notice_for_a_user_who_was_there(self):
        with mock.patch.object(library.optionsdialog, 'show') as show, \
                mock.patch.object(util.ADDON, 'getAddonInfo',
                                  side_effect=lambda key: {'name': 'Plex Uno', 'version': '0.4.2'}.get(key, '')):
            self.win._showUpdateNotice({'from': '0.4.1', 'away': False})
        self.assertEqual(show.call_args[0][1], 'Plex Uno was updated to 0.4.2 in the background.')

    def test_the_notice_after_being_minimised(self):
        with mock.patch.object(library.optionsdialog, 'show') as show, \
                mock.patch.object(util.ADDON, 'getAddonInfo',
                                  side_effect=lambda key: {'name': 'Plex Uno', 'version': '0.4.2'}.get(key, '')):
            self.win._showUpdateNotice({'from': '0.4.1', 'away': False, 'minimised': True})
        self.assertEqual(show.call_args[0][1], 'Plex Uno was updated to 0.4.2 while it was minimised. '
                                               'A restart was required to complete the update.')


class AskTest(KodiTestCase):
    """The update_restart_mode "ask" setting: the question, its three answers, and asking again. TickTest's set-up,
    not its tests."""
    names = TickTest.names
    notifications = TickTest.notifications

    def setUp(self):
        TickTest.setUp(self)
        self.asking = True
        self.replaced = True
        # present unless a test says otherwise
        ENV.idle_time = 2
        self.win.section = mock.Mock(key=None)
        self.win._isHostedShell = False

    def ask(self, answer, abandoned=False):
        """The question posted and answered: 0 Now, 1 Next time I'm away, 2 Remind me later, None Back"""
        dialog = mock.Mock(buttonChoice=answer)
        posted = len(self.posted)
        with mock.patch.object(library.optionsdialog.OptionsDialog, 'create', return_value=dialog), \
                mock.patch.object(update_restart, 'restart') as restart:
            if abandoned:
                self.win._updatePromptAbandoned = True
            self.win._askUpdateRestart()
        self.posted = self.posted[:posted]
        return restart

    def test_a_user_who_is_there_is_asked_without_a_notice(self):
        self.win._tickUpdate()
        self.assertEqual(self.names(), ['update restart question'])
        self.assertEqual(self.notifications(), [])
        # once
        self.win._tickUpdate()
        self.assertEqual(self.names(), ['update restart question'])

    def test_the_question_names_the_installed_version(self):
        # util.ADDON, made at startup, still says the running version (live on the AM6B, 2026-11-02)
        running = {'name': 'Plex Uno', 'version': '0.4.3~beta10'}
        with mock.patch.object(util.ADDON, 'getAddonInfo', side_effect=lambda key: running.get(key, '')), \
                mock.patch.dict(ENV.addon_info, {'version': '0.4.3~beta11'}), \
                mock.patch.object(library.optionsdialog.OptionsDialog, 'create',
                                  return_value=mock.Mock(buttonChoice=2)) as create:
            self.win._askUpdateRestart()
        info = create.call_args[1]['info']
        self.assertIn('Plex Uno was updated to 0.4.3~beta11 in the background', info)

    def test_now_restarts_and_the_new_run_says_nothing(self):
        self.win._tickUpdate()
        restart = self.ask(0)
        restart.assert_called_once_with('the user chose now', chosen=True)
        self.win._tickUpdate()
        self.assertEqual(self.names(), ['update restart question'])
        # the new run
        self.replaced = False
        self.win._updateNotice = {'from': '0.4.1', 'away': False, 'chosen': True}
        self.win._tickUpdate()
        self.assertIsNone(self.win._updateNotice)
        self.assertNotIn('update notice', self.names())

    def test_next_time_away_waits_for_the_user_to_go(self):
        self.win._tickUpdate()
        self.ask(1)
        self.now += 7200
        self.win._tickUpdate()
        self.assertEqual(self.names(), ['update restart question'])
        ENV.idle_time = AWAY
        self.win._tickUpdate()
        self.assertEqual(self.names(), ['update restart question', 'restart for update'])
        self.assertEqual(self.posted[-1][2], ('the user chose the next time they were away',))

    def test_next_time_away_restarts_away_whatever_the_away_setting(self):
        self.awayRestarts = False
        self.win._tickUpdate()
        self.ask(1)
        ENV.idle_time = AWAY
        self.win._tickUpdate()
        self.assertEqual(self.names()[-1], 'restart for update')

    def test_later_never_restarts_while_away(self):
        self.win._tickUpdate()
        self.ask(2)
        ENV.idle_time = AWAY
        self.now += 7200
        self.win._tickUpdate()
        self.assertEqual(self.names(), ['update restart question'])

    def test_back_is_later(self):
        self.win._tickUpdate()
        self.ask(None)
        self.assertEqual(self.win._updateChoice, 'later')

    def test_later_asks_again_on_home_once_the_time_has_passed(self):
        self.win._tickUpdate()
        self.ask(2)
        self.now += 3599
        self.win._tickUpdate()
        self.assertEqual(self.names(), ['update restart question'])
        self.now += 1
        self.win._tickUpdate()
        self.assertEqual(self.names(), ['update restart question', 'update restart question'])

    def item_page(self):
        """a season or film page, opened from a library: hosted, with a way back"""
        self.win._isHostedShell = True
        self.win._backStack = [(None, {'section': mock.Mock(key='1'), 'filter_': None})]

    def test_later_waits_for_a_natural_break(self):
        self.win._tickUpdate()
        self.ask(2)
        self.now += 7200
        self.item_page()
        self.win._tickUpdate()
        self.assertEqual(self.names(), ['update restart question'])
        # playback over (the player window shut): yes
        update_restart.playerOpened()
        self.win._tickUpdate()
        update_restart.playerClosed()
        self.win._tickUpdate()
        self.assertEqual(self.names(), ['update restart question', 'update restart question'])

    def test_a_library_is_top_level_too(self):
        self.win._tickUpdate()
        self.ask(2)
        self.now += 3600
        self.win.section = mock.Mock(key='1')
        self.win._tickUpdate()
        self.assertEqual(self.names(), ['update restart question', 'update restart question'])

    def test_back_from_away_on_an_item_page_is_a_break(self):
        # left on a season page for an hour
        self.win._tickUpdate()
        self.ask(2)
        self.item_page()
        self.now += 3600
        ENV.idle_time = AWAY
        self.win._tickUpdate()
        self.assertEqual(self.names(), ['update restart question'])
        ENV.idle_time = 1
        self.win._tickUpdate()
        self.assertEqual(self.names(), ['update restart question', 'update restart question'])
        # once
        self.ask(2)
        self.now += 3600
        self.win._tickUpdate()
        self.assertEqual(self.names(), ['update restart question', 'update restart question'])

    def test_away_before_the_time_is_up_is_not(self):
        self.win._tickUpdate()
        self.ask(2)
        self.item_page()
        self.now += 600
        ENV.idle_time = AWAY
        self.win._tickUpdate()
        ENV.idle_time = 1
        self.now += 3600
        self.win._tickUpdate()
        self.assertEqual(self.names(), ['update restart question'])

    def test_not_until_next_start_never_asks_again(self):
        self.askAgainAfter = None
        self.win._tickUpdate()
        self.ask(2)
        self.now += 10 ** 6
        self.win._tickUpdate()
        self.assertEqual(self.names(), ['update restart question'])

    def test_an_update_while_away_restarts_without_asking(self):
        ENV.idle_time = AWAY
        self.win._tickUpdate()
        self.assertEqual(self.names(), ['restart for update'])

    def test_or_waits_for_the_user_and_asks(self):
        self.awayRestarts = False
        ENV.idle_time = AWAY
        self.win._tickUpdate()
        self.assertEqual(self.posted, [])
        ENV.idle_time = 1
        self.win._tickUpdate()
        self.assertEqual(self.names(), ['update restart question'])

    def test_an_unanswered_question_restarts_when_the_user_has_gone(self):
        prompt = self.win._updatePrompt = mock.Mock()
        ENV.idle_time = AWAY - 1
        self.win._tickUpdate()
        prompt.doClose.assert_not_called()
        ENV.idle_time = AWAY
        self.win._tickUpdate()
        prompt.doClose.assert_called_once_with()
        self.win._updatePrompt = None
        restart = self.ask(None, abandoned=True)
        restart.assert_called_once_with('the restart question went unanswered')

    def test_or_stays_up_for_them(self):
        self.awayRestarts = False
        prompt = self.win._updatePrompt = mock.Mock()
        ENV.idle_time = 10 ** 5
        self.win._tickUpdate()
        prompt.doClose.assert_not_called()

    def test_no_question_during_playback_or_minimised(self):
        update_restart.playerOpened()
        self.addCleanup(update_restart.playerClosed)
        self.win._tickUpdate()
        util.setGlobalProperty('is_active', '')
        update_restart.playerClosed()
        self.win._tickUpdate()
        self.assertEqual(self.posted, [])
        # brought back: asked
        util.setGlobalProperty('is_active', '1')
        self.win._tickUpdate()
        self.assertEqual(self.names(), ['update restart question'])


class AwayTest(KodiTestCase):
    """userAway(): the screensaver's on - or, with none set, no input for its wait time."""

    def setUp(self):
        KodiTestCase.setUp(self)
        for name, value in (('_noScreensaver', (None, None)), ('_playerClosedAt', None), ('_playerOpen', 0)):
            patcher = mock.patch.object(update_restart, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_with_a_screensaver_it_is_the_screensaver(self):
        ENV.idle_time = 10 ** 5
        self.assertFalse(update_restart.userAway())
        ENV.cond_visibility['System.ScreenSaverActive'] = True
        self.assertTrue(update_restart.userAway())

    def test_without_one_it_is_its_wait_time(self):
        noScreensaver(self, minutes=10)
        ENV.idle_time = 599
        self.assertFalse(update_restart.userAway())
        ENV.idle_time = 600
        self.assertTrue(update_restart.userAway())

    def test_without_one_playback_never_counts(self):
        # Kodi's idle time runs on through a film
        noScreensaver(self, minutes=10)
        ENV.idle_time = 10 ** 4
        update_restart.playerOpened()
        self.addCleanup(update_restart.playerClosed)
        self.assertFalse(update_restart.userAway())
        with mock.patch.object(update_restart.time, 'time', return_value=1000.0):
            update_restart.playerClosed()
        with mock.patch.object(update_restart.time, 'time', return_value=1000.0 + 599):
            self.assertFalse(update_restart.userAway())
        with mock.patch.object(update_restart.time, 'time', return_value=1000.0 + 600):
            update_restart._noScreensaver = (None, None)
            self.assertTrue(update_restart.userAway())

    def test_the_description_has_the_screensaver_as_set(self):
        ENV.kodi_settings['screensaver.time'] = 3
        desc = update_restart.awayDescription()
        self.assertIn("You're away once the screensaver starts.", desc)
        self.assertNotIn('user input', desc)
        noScreensaver(self, minutes=1)
        desc = update_restart.awayDescription()
        self.assertIn("You're away after 1 minute with no user input (Note: playback never counts", desc)
        self.assertNotIn('{', desc)

    def test_the_settings_are_read_once_a_minute(self):
        noScreensaver(self, minutes=10)
        update_restart.userAway()
        calls = len(ENV.jsonrpc_calls)
        update_restart.userAway()
        self.assertEqual(len(ENV.jsonrpc_calls), calls)


class SettingsTest(KodiTestCase):
    """The three settings as update_restart reads them."""

    def settings(self, **values):
        return mock.patch.object(util, 'getSetting', side_effect=lambda key, default=None: values.get(key, default))

    def test_defaults(self):
        with self.settings():
            self.assertTrue(update_restart.asks())
            self.assertTrue(update_restart.restartsWhileAway())
            self.assertEqual(update_restart.askAgainAfter(), 3600)

    def test_set(self):
        with self.settings(update_restart_mode='auto', update_restart_away='ask', update_restart_reask='240'):
            self.assertFalse(update_restart.asks())
            self.assertFalse(update_restart.restartsWhileAway())
            self.assertEqual(update_restart.askAgainAfter(), 4 * 3600)
        with self.settings(update_restart_reask='never'):
            self.assertIsNone(update_restart.askAgainAfter())


class OpenBackstopTest(KodiTestCase):
    """MultiWindow._open(): a screen with no XML after the swap restarts rather than ending the session."""

    def setUp(self):
        KodiTestCase.setUp(self)
        self.mw = kodigui.MultiWindow.__new__(kodigui.MultiWindow)
        self.mw._allClosed = False
        self.mw._current = mock.Mock()
        self.mw._next = library.LibraryWindow
        self.mw._setupCurrent = mock.Mock(side_effect=RuntimeError('XML File for Window is missing'))

    def test_a_missing_xml_after_the_swap_restarts(self):
        with mock.patch.object(update_restart, 'filesReplaced', return_value=True), \
                mock.patch.object(update_restart, 'restart', return_value=True) as restart:
            self.mw._open()
        restart.assert_called_once_with('opening LibraryWindow')

    def test_a_missing_xml_with_our_files_in_place_is_still_an_error(self):
        with mock.patch.object(update_restart, 'filesReplaced', return_value=False):
            self.assertRaises(RuntimeError, self.mw._open)

    def test_no_home_to_close_is_still_an_error(self):
        with mock.patch.object(update_restart, 'filesReplaced', return_value=True), \
                mock.patch.object(update_restart, 'restart', return_value=False):
            self.assertRaises(RuntimeError, self.mw._open)
