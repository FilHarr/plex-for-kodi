# coding=utf-8
"""
A downloaded preview index file (BIF) - Plex's preview thumbnails for one media part: a 64-byte header, a table of
(timestamp, offset) pairs, then the JPEGs (docs/preview-thumbnails.md). Kodi-free, so it's unit-tested
(tests/test_bif_index.py); lib/windows/previews.py downloads the files and cuts pictures out with it.

Layout (little-endian): magic 89 42 49 46 0D 0A 1A 0A; version (4); picture count (4); interval in ms (4, 0 meaning
1000); 44 reserved. Then count + 1 entries of timestamp (4, in intervals) and offset (4); the last, timestamp
0xFFFFFFFF, gives the end of the last picture.
"""
from __future__ import absolute_import

import bisect
import struct

MAGIC = b'\x89BIF\r\n\x1a\n'
HEADER_SIZE = 64
ENTRY_SIZE = 8


class BifError(Exception):
    pass


class BifIndex(object):
    """
    Reads the header and the offset table and keeps only those (8 bytes a picture); pictures are read from the file
    when asked for. Raises BifError for anything that isn't a whole, consistent index.
    """
    def __init__(self, path):
        self.path = path
        with open(path, 'rb') as f:
            header = f.read(HEADER_SIZE)
            if len(header) < HEADER_SIZE or header[:8] != MAGIC:
                raise BifError('not a preview index')
            self.version, count, interval = struct.unpack_from('<III', header, 8)
            table = f.read(ENTRY_SIZE * (count + 1))
            if len(table) < ENTRY_SIZE * (count + 1):
                raise BifError('offset table cut short')
            f.seek(0, 2)
            size = f.tell()

        self.interval = interval or 1000
        self.count = count
        entries = [struct.unpack_from('<II', table, ENTRY_SIZE * i) for i in range(count + 1)]
        self.times = [timestamp * self.interval for timestamp, _ in entries[:count]]
        self.offsets = [offset for _, offset in entries]

        pictures_start = HEADER_SIZE + ENTRY_SIZE * (count + 1)
        if count and self.offsets[0] < pictures_start:
            raise BifError('pictures start inside the offset table')
        if any(b < a for a, b in zip(self.offsets, self.offsets[1:])):
            raise BifError('offsets out of order')
        if any(b < a for a, b in zip(self.times, self.times[1:])):
            raise BifError('timestamps out of order')
        if self.offsets[-1] > size:
            raise BifError('pictures past the end of the file')

    def index_at(self, ms):
        """The picture at or before a time (ms into the part), or None if there are none."""
        if not self.count:
            return None
        return max(0, bisect.bisect_right(self.times, ms) - 1)

    def picture(self, index):
        """That picture's JPEG bytes."""
        start, end = self.offsets[index], self.offsets[index + 1]
        with open(self.path, 'rb') as f:
            f.seek(start)
            return f.read(end - start)
