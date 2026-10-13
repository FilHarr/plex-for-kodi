# coding=utf-8
"""Whether path-mapped libraries' shares answer, for the sidebar's red "share is down" dot and its
notification. Ported from upstream HomeWindow.startPathMappingProbe()/PathMappingProbeTask
(home.py @ 2707bbe7), which went with HomeWindow in 12675d11; only playback noticed a dead share
after that (pmm.reportMappedFileMissing()).

The sidebar's build hands its libraries over (setTargets()); the root LibraryWindow's tick asks
again every PROBE_INTERVAL s while no video plays (tick()). The check runs on a worker: a dead
SMB/NFS share blocks until the mount times out. When a share's state changes, onChange() runs on
that worker - LibraryWindow posts a sidebar rebuild, which reads section.mappingBroken afresh.
State lives here because every screen builds its own sidebar from the same libraries.
"""
from __future__ import absolute_import

import threading
import time

from lib import backgroundthread
from lib import util
from lib.path_mapping import pmm
from lib.util import T

PROBE_INTERVAL = 60

_lock = threading.Lock()
# (server name, Kodi-side root, library title), one per root
_targets = []
_lastProbe = 0
_running = False
_onChange = None


def setOnChange(fn):
    """fn() runs on the probe's worker when a share's state changed."""
    global _onChange
    _onChange = fn


def targetsFor(sections):
    """Each mapped root of these sidebar entries once, with the first library that uses it."""
    targets = []
    seen = set()
    if not pmm.mapping:
        return targets
    for section in sections:
        server = getattr(section, 'server', None)
        server_name = server and getattr(server, 'name', None)
        if not server_name:
            continue
        for map_path in getattr(section, 'mappedPaths', None) or ():
            if (server_name, map_path) in seen:
                continue
            seen.add((server_name, map_path))
            targets.append((server_name, map_path, section.title))
    return targets


def setTargets(sections):
    """The sidebar was built with these entries: check their shares now if they're new to us."""
    global _targets
    targets = targetsFor(sections)
    with _lock:
        if targets == _targets:
            return
        _targets = targets
    if targets:
        start()


def tick(now=None):
    """Every PROBE_INTERVAL s, so a share that comes back loses its red dot without a rebuild."""
    now = now or time.time()
    with _lock:
        due = _targets and not _running and now - _lastProbe > PROBE_INTERVAL
    if due:
        start()


def start():
    global _lastProbe, _running
    with _lock:
        if _running or not _targets:
            return
        _running = True
        _lastProbe = time.time()
        targets = list(_targets)
    backgroundthread.BGThreader.addTask(PathMappingProbeTask().setup(targets, _done))


def _done(changed):
    global _running
    with _lock:
        _running = False
    if changed and _onChange:
        try:
            _onChange()
        except Exception:
            util.ERROR()


class PathMappingProbeTask(backgroundthread.Task):
    """Checks the Kodi-side roots of mapped libraries. Runs in the background because a
    dead SMB/NFS share blocks for the full mount timeout, which would stall the section
    list every time it's drawn.
    """
    def setup(self, targets, callback):
        self.targets = targets
        self.callback = callback
        return self

    def run(self):
        changed = False
        announce = []
        try:
            util.DEBUG_LOG("Path mapping probe: checking {} root(s)", len(self.targets))
            for server_name, map_path, title in self.targets:
                if self.isCanceled():
                    return

                if pmm.verifyMapping(server_name, map_path):
                    changed = True
                util.DEBUG_LOG("Path mapping probe: {} -> {}", map_path,
                               pmm.isMappingBroken(server_name, map_path) and "unreachable" or "ok")

                if (pmm.isMappingBroken(server_name, map_path)
                        and pmm.claimNotification(server_name, map_path, "root")):
                    announce.append(title or map_path)

            if self.isCanceled():
                return

            if announce:
                # one popup for the whole run: Kodi queues notifications, so one per library
                # would keep the screen covered for 5s * number of mapped libraries
                pmm.notify(T(35037, "Path mapping unavailable for: {}").format(" / ".join(announce)))
        finally:
            self.callback(changed)
