# coding=utf-8
"""
lib/windows/previews.py - the preview pictures cut out of a downloaded index (docs/preview-thumbnails.md): one file
each under Kodi's temp folder, written once even when two threads ask at once (on Windows the second rename failed
once Kodi had the first open - seen live, 2026-10-20), and gone after clear(). The download itself needs a server;
it was checked against one by hand.
"""

from __future__ import absolute_import

import os
import shutil
import tempfile
import threading
import unittest

from kodienv import ENV

ENV.abort_requested = True
from lib.windows import previews  # noqa: E402
from lib.windows.bif_index import BifIndex  # noqa: E402

from .test_bif_index import build, jpeg  # noqa: E402


class PartAtTest(unittest.TestCase):
    # a two-file item: 55 minutes, then 50
    PARTS = [(11, 3300000), (12, 3000000)]

    def test_a_single_part(self):
        self.assertEqual(previews.part_at([(7, 6000000)], 1234567), (7, 1234567))

    def test_the_first_part(self):
        self.assertEqual(previews.part_at(self.PARTS, 0), (11, 0))
        self.assertEqual(previews.part_at(self.PARTS, 3299999), (11, 3299999))

    def test_into_the_second_part(self):
        self.assertEqual(previews.part_at(self.PARTS, 3300000), (12, 0))
        self.assertEqual(previews.part_at(self.PARTS, 4200000), (12, 900000))  # 1:10:00 is 15:00 into part 2

    def test_past_the_end(self):
        self.assertIsNone(previews.part_at(self.PARTS, 6300000))
        self.assertIsNone(previews.part_at([], 0))


class PreviewStoreTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.store = previews.PreviewStore()
        self.store.folder = os.path.join(self.dir, previews.FOLDER)
        os.makedirs(self.store.folder)
        self.pictures = [jpeg(i) for i in range(6)]
        path = os.path.join(self.store.folder, '42.bif')
        with open(path, 'wb') as f:
            f.write(build(self.pictures))
        self.store._indexes['42'] = BifIndex(path)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def local(self, special):
        return os.path.join(self.store.folder, special.split(previews.FOLDER + '/', 1)[1])

    def test_a_picture_by_time(self):
        special = self.store.picture(42, 12000)
        self.assertEqual(special, 'special://temp/{0}/42/2.jpg'.format(previews.FOLDER))
        with open(self.local(special), 'rb') as f:
            self.assertEqual(f.read(), self.pictures[2])

    def test_written_once_and_reused(self):
        first = self.store.picture(42, 5000)
        mtime = os.path.getmtime(self.local(first))
        self.assertEqual(self.store.picture(42, 9999), first)
        self.assertEqual(os.path.getmtime(self.local(first)), mtime)

    def test_two_threads_asking_at_once(self):
        results, errors = [], []
        start = threading.Event()

        def ask():
            start.wait()
            try:
                results.append(self.store.picture(42, 20000))
            except Exception as e:  # pragma: no cover - the failure being guarded against
                errors.append(e)

        threads = [threading.Thread(target=ask) for _ in range(8)]
        for t in threads:
            t.start()
        start.set()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])
        self.assertEqual(set(results), {'special://temp/{0}/42/4.jpg'.format(previews.FOLDER)})
        folder = os.path.join(self.store.folder, '42')
        self.assertEqual(os.listdir(folder), ['4.jpg'])

    def test_none_before_a_part_is_ready(self):
        self.assertIsNone(self.store.picture(7, 1000))

    def test_clear(self):
        self.store.picture(42, 0)
        self.store.clear()
        self.assertIsNone(self.store.picture(42, 0))
        self.assertEqual(os.listdir(self.store.folder), [])


if __name__ == '__main__':
    unittest.main()
