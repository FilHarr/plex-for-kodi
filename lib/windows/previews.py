# coding=utf-8
"""
Preview thumbnails from each media part's whole index file (docs/preview-thumbnails.md): downloaded once in the
background soon after playback starts, the pictures cut out of it as needed (bif_index.BifIndex) into Kodi's temp
folder. Plex's one-picture-at-a-time request (PlexPlayer.getBifUrl()) can serve the wrong bytes for an index it
holds stale details of; the whole file is what the official apps download, and is always right. Until a part's file
is ready, or if its download fails, SeekDialog falls back to that request.

Kodi loads images under special://temp directly, without copying them into its texture cache and database
(CTextureCache::IsCachedImage, Kodi 21), so the pictures are written there, one file each, named by part and
picture so a name never shows a different image. All of it goes when the item's playback ends, and anything a crash
left behind at the first playback of the session.
"""
from __future__ import absolute_import

import os
import shutil
import threading
import time

from plexnet import asyncadapter, http
from plexnet import util as plexnet_util

from lib import util
from lib.kodi_util import ADDON_ID
from .bif_index import BifError, BifIndex

FOLDER = '{0}-previews'.format(ADDON_ID)
CHUNK = 64 * 1024


def part_at(parts, offset):
    """
    Which part offset (ms into the whole item) falls in, and how far into it: (part id, ms) - parts, (part id,
    duration ms) pairs in playing order, as a multi-part item's files follow each other. None past the end.
    """
    start = 0
    for part_id, duration in parts:
        if start <= offset < start + duration:
            return part_id, offset - start
        start += duration
    return None


class PreviewStore(object):
    def __init__(self):
        self.folder = os.path.join(util.translatePath('special://temp/'), FOLDER)
        self.special = 'special://temp/{0}/'.format(FOLDER)
        self._lock = threading.Lock()
        # one picture written at a time: the scan thread and the dialog's can ask for the same one at once, and on
        # Windows the second rename onto it fails once Kodi has the first open
        self._writeLock = threading.Lock()
        # bumped by clear(): a download from before it is dropped when it finishes
        self._generation = 0
        self._indexes = {}  # part id -> BifIndex
        self._swept = False

    def _sweepOnce(self):
        if self._swept:
            return
        self._swept = True
        shutil.rmtree(self.folder, ignore_errors=True)

    def start(self, parts, server, on_ready=None):
        """
        Downloads each part's index in a thread of its own: parts, (part id, index path) pairs - the path as
        PlexPart.getIndexPath() gives it. on_ready() is called (on that thread) as each one becomes usable.
        """
        with self._lock:
            generation = self._generation
        self._sweepOnce()
        for part_id, path in parts:
            thread = threading.Thread(target=self._download, args=(generation, str(part_id), path, server, on_ready),
                                      name='PreviewStore.download')
            thread.daemon = True
            thread.start()

    def _stale(self, generation):
        return generation != self._generation or util.MONITOR.abortRequested()

    def _download(self, generation, part_id, path, server, on_ready):
        dest = os.path.join(self.folder, '{0}.bif'.format(part_id))
        partial = dest + '.part'
        started = time.time()
        size = 0
        try:
            url = server.buildUrl(path, includeToken=True)
            if not url:
                return
            # each part's download is a thread of its own, so another may make it first
            os.makedirs(self.folder, exist_ok=True)
            session = asyncadapter.PlainSession()
            try:
                response = session.get(url, headers=plexnet_util.BASE_HEADERS.copy(), timeout=http.DEFAULT_TIMEOUT,
                                       stream=True)
                try:
                    if response.status_code != 200:
                        util.LOG("Previews: part {0}'s index: HTTP {1}", part_id, response.status_code)
                        return
                    with open(partial, 'wb') as f:
                        for chunk in response.iter_content(CHUNK):
                            if self._stale(generation):
                                return
                            f.write(chunk)
                            size += len(chunk)
                finally:
                    response.close()
            finally:
                session.close()
            os.replace(partial, dest)
            index = BifIndex(dest)
        except BifError as e:
            util.LOG("Previews: part {0}'s index unusable: {1}", part_id, e)
            return
        except Exception as e:
            util.LOG("Previews: part {0}'s index not downloaded: {1}", part_id, http.describeFailure(e))
            return
        finally:
            if os.path.exists(partial):
                try:
                    os.remove(partial)
                except OSError:
                    pass

        with self._lock:
            if self._stale(generation):
                stale = True
            else:
                stale = False
                self._indexes[part_id] = index
        if stale:
            self._remove(part_id)
            return

        util.DEBUG_LOG("Previews: part {0}'s index ready: {1} pictures, every {2} ms, {3} bytes in {4:.2f} s",
                       part_id, index.count, index.interval, size, time.time() - started)
        if on_ready:
            try:
                on_ready()
            except Exception:
                util.ERROR()

    def picture(self, part_id, ms):
        """
        The special:// path of the picture at or before ms into the part, written to disk the first time it's
        asked for; None while the part's index isn't ready (or the picture can't be had).
        """
        part_id = str(part_id)
        index = self._indexes.get(part_id)
        if index is None:
            return None
        i = index.index_at(ms)
        if i is None:
            return None
        name = '{0}/{1}.jpg'.format(part_id, i)
        path = os.path.join(self.folder, part_id, '{0}.jpg'.format(i))
        if os.path.exists(path):
            return self.special + name
        with self._writeLock:
            if not os.path.exists(path):
                partial = path + '.part'
                try:
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    # written under another name, then renamed: Kodi never reads half a picture
                    with open(partial, 'wb') as f:
                        f.write(index.picture(i))
                    os.replace(partial, path)
                except Exception:
                    if os.path.exists(partial):
                        try:
                            os.remove(partial)
                        except OSError:
                            pass
                    if not os.path.exists(path):
                        util.ERROR()
                        return None
        return self.special + name

    def _remove(self, part_id):
        for p in (os.path.join(self.folder, '{0}.bif'.format(part_id)),
                  os.path.join(self.folder, '{0}.bif.part'.format(part_id))):
            try:
                if os.path.exists(p):
                    os.remove(p)
            except OSError:
                pass
        shutil.rmtree(os.path.join(self.folder, part_id), ignore_errors=True)

    def clear(self):
        """Forgets every part's index and deletes its files; downloads still running are dropped when they end."""
        with self._lock:
            self._generation += 1
            parts = list(self._indexes)
            self._indexes = {}
        for part_id in parts:
            self._remove(part_id)


store = PreviewStore()
