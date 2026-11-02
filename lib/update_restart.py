# coding=utf-8
"""
Kodi updating the add-on while it runs. Kodi neither stops a running script nor tells it: it takes the
add-on out of its list, renames the add-on's folder away, renames the new version's into its place, deletes
the old one and lists the add-on again (CAddonInstallJob::DoWork(), CFilesystemInstaller::InstallToFilesystem(),
Kodi 21). Screens already open keep the XML they loaded, but the release zip carries no compiled templates -
render_templates() writes them at startup - so the next screen opened found none, "XML File for Window is
missing", and the session ended (live on the AM6B, 2026-10-29: an update while idle on Home, then a tile).

A marker written into the add-on folder at startup goes with the old folder. It's untracked, so a release
(build.py's git archive) never carries it. Once it's gone, LibraryWindow's tick restarts the add-on, and the
new version renders its templates; MultiWindow._open() does the same if a screen is opened first. The restart
is recorded for the new run, which says why it's back on Home: at once, or once the user is back if they were
away when it happened (LibraryWindow._tickUpdate()).

Until that restart - the end of playback, say, which a restart would stop - the running copy carries on from
a snapshot of its own lib/ and resources/skins/ (compiled XML included) in addon_data, taken after each
render: hard links where the filesystem allows, which keep the old files once Kodi deletes the old folder,
copies otherwise. From the swap on, windows are built from the snapshot (skinPath()) and our modules not yet
imported come from it (_redirectImports()), so old code never meets the new version's files - only its
strings, which Kodi reloads with the install.
"""
from __future__ import absolute_import

import importlib
import json
import os
import shutil
import sys
import threading
import time

from kodi_six import xbmc
from kodi_six import xbmcaddon

from lib import util

MARKER_NAME = '.uno_session'
# kept across the restart in a global property: Kodi itself keeps running
NOTICE_PROP = 'update_restart'
# Away: the screensaver's on - the user's own measure of gone, which a question left up is hidden by too.
# With none set (Kodi's screensaver.mode None), no input for its wait time (screensaver.time, which Kodi
# keeps), read at most this often.
NO_SCREENSAVER_CHECK = 60
# a user who's there is told this long before the restart (LibraryWindow._tickUpdate())
RESTART_DELAY = 5
# the pre-restart notification, up through the delay and the restart: shutting down took 4 s on the AM6B
# (2026-10-29), then the start
RESTART_NOTICE_MS = 12000

# what the snapshot holds, under the add-on folder; never __pycache__ or bytecode
SNAPSHOT_DIRS = ('lib', os.path.join('resources', 'skins'))
SNAPSHOT_NAME = 'update_snapshot'

_markerPath = None
_addonPath = None
_version = None
_announcedAt = None
# (when read, the no-screensaver wait in seconds or None) (_noScreensaverWait())
_noScreensaver = (None, None)
# set once a snapshot of this run's files is complete
_snapshotPath = None
_usingSnapshot = False
_snapshotLock = threading.Lock()
_switchLock = threading.Lock()


def writeMarker():
    """At startup: this run's marker in the add-on folder."""
    global _markerPath, _addonPath, _version
    _version = util.ADDON.getAddonInfo('version')
    if os.getenv("INSTALLATION_DIR_AVOID_WRITE"):
        # the compiled templates live in addon_data there (kodigui.BaseFunctions.open()), which an
        # update leaves alone
        return
    addonPath = os.path.normpath(util.translatePath(util.ADDON.getAddonInfo('path')))
    path = os.path.join(addonPath, MARKER_NAME)
    try:
        with open(path, 'w') as f:
            f.write(_version)
    except (IOError, OSError) as e:
        util.LOG('Update check: could not write {0} ({1}), an update won\'t be noticed', path, e)
        return
    _markerPath = path
    _addonPath = addonPath


def filesReplaced():
    """The add-on folder this run started from has been replaced (an update or a reinstall)."""
    return _markerPath is not None and not os.path.exists(_markerPath)


def takeSnapshot():
    """After rendering the templates: bring the snapshot up to date with this run's files, on a thread of its
    own. Until it's done, a swap restarts as if there were none (the busy XML fallback, MultiWindow._open())."""
    global _snapshotPath
    if _markerPath is None or _usingSnapshot:
        return
    _snapshotPath = None
    thread = threading.Thread(target=_takeSnapshot, name='update-snapshot')
    thread.daemon = True
    thread.start()


def _snapshotFiles():
    """(relative path, full path) of what the snapshot holds"""
    for sub in SNAPSHOT_DIRS:
        for parent, dirs, names in os.walk(os.path.join(_addonPath, sub)):
            dirs[:] = [d for d in dirs if d != '__pycache__']
            for name in names:
                if not name.endswith(('.pyc', '.pyo')):
                    full = os.path.join(parent, name)
                    yield os.path.relpath(full, _addonPath), full


def _takeSnapshot():
    global _snapshotPath
    target = os.path.join(util.PROFILE, SNAPSHOT_NAME)
    started = time.time()
    counts = {'linked': 0, 'copied': 0, 'kept': 0, 'removed': 0}
    with _snapshotLock:
        try:
            canLink = True
            wanted = set()
            for rel, src in _snapshotFiles():
                dst = os.path.join(target, rel)
                wanted.add(os.path.normcase(dst))
                srcStat = os.stat(src)
                try:
                    dstStat = os.stat(dst)
                except OSError:
                    dstStat = None
                if dstStat is not None:
                    # the same file (a link), or a copy of it (copy2() keeps the time)
                    if os.path.samestat(srcStat, dstStat) or (dstStat.st_size == srcStat.st_size and
                                                              int(dstStat.st_mtime) == int(srcStat.st_mtime)):
                        counts['kept'] += 1
                        continue
                    os.remove(dst)
                else:
                    parent = os.path.dirname(dst)
                    if not os.path.isdir(parent):
                        os.makedirs(parent)
                if canLink:
                    try:
                        os.link(src, dst)
                        counts['linked'] += 1
                        continue
                    except (OSError, AttributeError, NotImplementedError) as e:
                        util.LOG('Update check: no hard links in {0} ({1}), copying instead', target, e)
                        canLink = False
                shutil.copy2(src, dst)
                counts['copied'] += 1

            # whatever a version before this one had, and the bytecode of imports from the snapshot
            for parent, dirs, names in os.walk(target, topdown=False):
                for name in names:
                    full = os.path.join(parent, name)
                    if os.path.normcase(full) not in wanted:
                        os.remove(full)
                        counts['removed'] += 1
                if parent != target and not os.listdir(parent):
                    os.rmdir(parent)
        except Exception as e:
            util.LOG('Update check: no snapshot ({0}), an update will restart at once', e)
            return

        # read while the swap happened: some of it may be the new version's
        if filesReplaced():
            util.LOG('Update check: our files were replaced while the snapshot was taken, not using it')
            return
        _snapshotPath = target
    util.LOG('Update check: snapshot of {0} up to date in {1:.0f} ms ({2} linked, {3} copied, {4} kept, {5} removed)',
             _version, (time.time() - started) * 1000, counts['linked'], counts['copied'], counts['kept'],
             counts['removed'])


def _norm(path):
    return os.path.normcase(os.path.normpath(path))


def _redirect(path, prefixes):
    """path under the add-on folder (as any of prefixes) -> the same under the snapshot; otherwise path"""
    normed = _norm(path)
    for prefix in prefixes:
        if normed == prefix or normed.startswith(prefix + os.sep):
            return os.path.join(_snapshotPath, os.path.normpath(path)[len(prefix):].lstrip(os.sep))
    return path


def _redirectImports():
    """Our modules not imported yet come from the snapshot: sys.path (_included_packages adds itself) and each
    loaded package's __path__, which its submodules are found through."""
    prefixes = {_norm(_addonPath), _norm(os.path.realpath(_addonPath))}
    sys.path[:] = [_redirect(p, prefixes) if isinstance(p, str) else p for p in sys.path]
    for module in list(sys.modules.values()):
        paths = getattr(module, '__path__', None)
        if isinstance(paths, list):
            paths[:] = [_redirect(p, prefixes) for p in paths]
    importlib.invalidate_caches()


def usingSnapshot():
    """Once our folder's been replaced, and a snapshot is there: switch to it, once. True while in use."""
    global _usingSnapshot
    if _usingSnapshot:
        return True
    if _snapshotPath is None or not filesReplaced():
        return False
    with _switchLock:
        if not _usingSnapshot:
            _redirectImports()
            _usingSnapshot = True
            util.LOG('Update check: our files were replaced; carrying on from the snapshot of {0} until the restart',
                     _version)
    return True


def skinPath(path):
    """A window's add-on path: the snapshot, once our folder's been replaced."""
    if path and usingSnapshot() and _norm(path) in (_norm(_addonPath), _norm(os.path.realpath(_addonPath))):
        return _snapshotPath
    return path


class _SwapWatch(object):
    """First on sys.meta_path: an import not loaded yet switches to the snapshot first if our folder's been
    replaced, so it's never the new version's. Finds nothing itself."""

    def find_spec(self, name, path=None, target=None):
        if _snapshotPath is not None and not _usingSnapshot:
            usingSnapshot()
        return None


def watchImports():
    """At startup, once."""
    if not any(isinstance(f, _SwapWatch) for f in sys.meta_path):
        sys.meta_path.insert(0, _SwapWatch())


_playerOpen = 0
# when the player window last closed: with no screensaver, the wait for "away" counts from there too (userAway())
_playerClosedAt = None


def playerOpened():
    """videoplayer.play(), around the player window: playback, and post-play after it."""
    global _playerOpen
    _playerOpen += 1


def playerClosed():
    global _playerOpen, _playerClosedAt
    _playerOpen = max(0, _playerOpen - 1)
    _playerClosedAt = time.time()


def installedVersion():
    """The version Kodi has installed now: the update's. util.ADDON, made at startup, still describes this run
    (live on the AM6B, 2026-11-02: the question said "updated to" the version it was updating from)."""
    try:
        return xbmcaddon.Addon(util.ADDON_ID).getAddonInfo('version')
    except Exception as e:
        # mid-install, Kodi lists no add-on
        util.DEBUG_LOG('Update check: no installed version ({0})', e)
        return util.ADDON.getAddonInfo('version')


def readyToRestart():
    """Kodi lists the new version (a restart's RunScript() before that would find no add-on), nothing
    plays - a restart stops playback (player_stop_on_exit) - and the player window is closed: post-play
    follows the end, and may play the next item (live on the PC, 2026-11-02: the notice came as the
    episode ended, the restart only once the next one had played and the player was left)."""
    return (xbmc.getCondVisibility('System.HasAddon({0})'.format(util.ADDON_ID))
            and not xbmc.Player().isPlaying() and not _playerOpen)


def screensaverWaitMinutes():
    """Kodi's screensaver wait time (screensaver.time), which it keeps with the screensaver off too."""
    try:
        return int(util.rpc.Settings.GetSettingValue(setting='screensaver.time').get('value') or 3)
    except Exception as e:
        util.DEBUG_LOG('Update check: no screensaver wait time ({0})', e)
        return 3


def _noScreensaverWait():
    """With no screensaver set, its wait time in seconds; None when there is one."""
    global _noScreensaver
    readAt, wait = _noScreensaver
    now = time.time()
    if readAt is None or now - readAt >= NO_SCREENSAVER_CHECK:
        wait = None
        try:
            if not screensaverSet():
                wait = screensaverWaitMinutes() * 60
        except Exception as e:
            util.DEBUG_LOG('Update check: no screensaver settings ({0})', e)
        _noScreensaver = (now, wait)
    return wait


def userAway():
    """The screensaver's on, or with none set, no input for its wait time. Playback never counts: Kodi holds the
    screensaver off during video, and without one the wait counts from the player closing too - Kodi's idle time
    runs on through a film."""
    if xbmc.getCondVisibility('System.ScreenSaverActive'):
        return True
    wait = _noScreensaverWait()
    if wait is None or _playerOpen or xbmc.Player().isPlaying():
        return False
    if _playerClosedAt is not None and time.time() - _playerClosedAt < wait:
        return False
    return xbmc.getGlobalIdleTime() >= wait


def screensaverSet():
    """Kodi has a screensaver (screensaver.mode isn't None)."""
    try:
        return bool(util.rpc.Settings.GetSettingValue(setting='screensaver.mode').get('value'))
    except Exception as e:
        util.DEBUG_LOG('Update check: no screensaver mode ({0})', e)
        return True


def awayDescription():
    """The "Update while I'm away" setting's description, for Kodi's screensaver as it's set now: whether there is
    one, and its wait time (Settings, as the row's shown)."""
    minutes = screensaverWaitMinutes()
    wait = util.T(35239, '1 minute') if minutes == 1 else util.T(35240, '{minutes} minutes').format(minutes=minutes)
    if screensaverSet():
        away = util.T(35241, "You're away once the screensaver starts.")
    else:
        away = util.T(35242, "You're away after {time} with no user input (Note: playback never counts as being "
                             "away).")
    return util.T(35232, "What happens if an update arrives while you're away, or you leave the restart question "
                         "unanswered. {away}\nRestart without asking: the addon restarts, and tells you why when "
                         "you're back.\nAsk when I'm back: the question waits for you.").format(
        away=away.format(time=wait))


# Settings (System): what a restart for an update waits for.
def asks():
    """update_restart_mode: "ask" - the user picks now, the next time they're away, or later
    (LibraryWindow._askUpdateRestart()) - or "auto": a notice and RESTART_DELAY seconds, at once if they're away."""
    return util.getSetting('update_restart_mode', 'ask') != 'auto'


def restartsWhileAway():
    """update_restart_away, asking only: an update that arrives while the user's away, or a question still up when
    they are, restarts without asking ("restart") or waits for them ("ask")."""
    return util.getSetting('update_restart_away', 'restart') != 'ask'


def askAgainAfter():
    """update_restart_reask, asking only: seconds after "Remind me later" before asking again, or None: not until
    the next start."""
    minutes = util.getSetting('update_restart_reask', '60')
    try:
        return int(minutes) * 60
    except (TypeError, ValueError):
        return None


def announce(delayed=True):
    """Tell a user who's there that a restart is coming, in a Kodi notification, which stays up across
    it: otherwise it looks like a crash. One who's away is told when they're back. delayed: the
    tick's restart, RESTART_DELAY seconds on; otherwise it's now."""
    global _announcedAt
    _announcedAt = time.time()
    util.LOG('Update check: our files were replaced; telling the user, restarting {0}',
             'in {0} s'.format(RESTART_DELAY) if delayed else 'now')
    if delayed:
        message = util.T(35218, 'The addon was updated in the background. Restarting in {seconds} seconds').format(
            seconds=RESTART_DELAY)
    else:
        message = util.T(35219, 'The addon was updated in the background. Restarting now')
    util.showNotification(message, time_ms=RESTART_NOTICE_MS)


def restart(reason, minimised=False, chosen=False):
    """Restart into the new version, recorded for its notice. False if there's no Home to close yet.
    Told beforehand by the tick's announce(); a screen that couldn't open, or Uno brought back after
    being minimised through the update (minimised), restarts at once, announced here unless the tick
    has just done it. chosen: the user picked "Now", and the new run needn't tell them why."""
    from lib.windows import windowutils
    away = userAway()
    # Kodi's ActivateWindow()/ReplaceWindow() end the screensaver (WakeUpScreenSaverAndDPMS(),
    # GUIBuiltins.cpp), and the new run's start uses them: it starts it again (live on the PC,
    # 2026-10-29)
    screensaver = xbmc.getCondVisibility('System.ScreenSaverActive')
    util.LOG('Update check: our files were replaced, {0}; restarting (user {1}{2})', reason,
             'away' if away else 'present', ', screensaver on' if screensaver else '')
    util.setGlobalProperty(NOTICE_PROP, json.dumps({'from': _version, 'away': away, 'screensaver': screensaver,
                                                    'minimised': minimised, 'chosen': chosen}), wait=True)
    # a restart the user chose ("Now") isn't announced: they've just answered the question
    if not away and not chosen and (_announcedAt is None or
                                    time.time() - _announcedAt > RESTART_NOTICE_MS / 1000.0):
        announce(delayed=False)
    return windowutils.restartAddon('add-on files replaced')


def takeNotice():
    """The restart's record, once, in the run it started: {'from': version, 'away': bool, 'screensaver': bool,
    'minimised': bool, 'chosen': bool}, or None."""
    raw = util.getGlobalProperty(NOTICE_PROP, consume=True)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except ValueError:
        return None
