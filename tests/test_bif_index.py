# coding=utf-8
"""
lib/windows/bif_index.py - reading a downloaded preview index file (docs/preview-thumbnails.md). The files here are
built in the test, in the layout Plex serves (checked against real ones, 2026-10-19).
"""

from __future__ import absolute_import

import os
import shutil
import struct
import tempfile
import unittest

from kodienv import ENV

ENV.abort_requested = True
from lib.windows.bif_index import BifError, BifIndex, MAGIC  # noqa: E402


def build(pictures, interval=5000, timestamps=None, magic=MAGIC):
    """A preview index of these picture byte strings."""
    count = len(pictures)
    timestamps = list(range(count)) if timestamps is None else timestamps
    header = magic + struct.pack('<III', 0, count, interval) + b'\x00' * 44
    offset = len(header) + 8 * (count + 1)
    table = b''
    for ts, pic in zip(timestamps, pictures):
        table += struct.pack('<II', ts, offset)
        offset += len(pic)
    table += struct.pack('<II', 0xFFFFFFFF, offset)
    return header + table + b''.join(pictures)


def jpeg(n):
    return b'\xff\xd8\xff\xe0' + bytes([n]) * (10 + n) + b'\xff\xd9'


class BifIndexTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def write(self, data, name='p.bif'):
        path = os.path.join(self.dir, name)
        with open(path, 'wb') as f:
            f.write(data)
        return path

    def test_header_and_table(self):
        idx = BifIndex(self.write(build([jpeg(i) for i in range(5)])))
        self.assertEqual((idx.count, idx.interval), (5, 5000))
        self.assertEqual(idx.times, [0, 5000, 10000, 15000, 20000])

    def test_pictures(self):
        pics = [jpeg(i) for i in range(5)]
        idx = BifIndex(self.write(build(pics)))
        self.assertEqual([idx.picture(i) for i in range(5)], pics)

    def test_index_at(self):
        idx = BifIndex(self.write(build([jpeg(i) for i in range(5)])))
        self.assertEqual([idx.index_at(ms) for ms in (0, 4999, 5000, 7500, 20000, 99999)], [0, 0, 1, 1, 4, 4])

    def test_index_at_before_the_first_picture(self):
        idx = BifIndex(self.write(build([jpeg(0), jpeg(1)], timestamps=[2, 3])))
        self.assertEqual(idx.index_at(0), 0)

    def test_uneven_timestamps(self):
        idx = BifIndex(self.write(build([jpeg(i) for i in range(3)], timestamps=[0, 1, 5])))
        self.assertEqual([idx.index_at(ms) for ms in (6000, 24999, 25000)], [1, 1, 2])

    def test_interval_0_means_a_second(self):
        idx = BifIndex(self.write(build([jpeg(0), jpeg(1)], interval=0)))
        self.assertEqual((idx.interval, idx.times), (1000, [0, 1000]))

    def test_no_pictures(self):
        idx = BifIndex(self.write(build([])))
        self.assertIsNone(idx.index_at(1000))

    def test_bad_magic(self):
        with self.assertRaises(BifError):
            BifIndex(self.write(build([jpeg(0)], magic=b'\x89PNG\r\n\x1a\n')))

    def test_a_short_file(self):
        with self.assertRaises(BifError):
            BifIndex(self.write(MAGIC + b'\x00' * 10))

    def test_a_table_cut_short(self):
        data = build([jpeg(i) for i in range(5)])
        with self.assertRaises(BifError):
            BifIndex(self.write(data[:64 + 20]))

    def test_pictures_cut_short(self):
        data = build([jpeg(i) for i in range(5)])
        with self.assertRaises(BifError):
            BifIndex(self.write(data[:-5]))

    def test_offsets_into_the_table(self):
        data = bytearray(build([jpeg(i) for i in range(3)]))
        struct.pack_into('<I', data, 64 + 4, 70)  # the first picture "inside" the table
        with self.assertRaises(BifError):
            BifIndex(self.write(bytes(data)))


if __name__ == '__main__':
    unittest.main()
