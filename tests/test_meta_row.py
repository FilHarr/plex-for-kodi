# coding=utf-8
"""
includes/pp_meta_row.xml.tpl is shared by Home's hero (LibraryWindow.setHeroInfo()), Pre-play
(PrePlayWindow.setInfo()) and Show (ShowWindow.updateProperties()). A window starts with whatever its
reused window id last held, so each of those must write every property the row reads, or the row
shows another screen's value (live-reported 2026-09-24: Home's time-left pill carried over).

Checked against the source: each method's setProperty()/blankMetaRow() keys must cover
CommonMixin.META_ROW_PROPERTIES, and that list must match what the template reads.

Importing lib.windows.* starts lib.player's monitor thread unless abort_requested is set first.
"""

from __future__ import absolute_import

import inspect
import os
import re

from kodienv import ENV

ENV.abort_requested = True
from lib.windows import library, preplay, subitems  # noqa: E402
from lib.windows.mixins.common import CommonMixin  # noqa: E402

from .base import KodiTestCase, TEMPLATE_DIR  # noqa: E402

SET_KEY = re.compile(r"""set(?:Bool)?Property\(\s*['"]([^'"]+)['"]""")
BLANK_CALL = re.compile(r"blankMetaRow\(([^)]*)\)")
QUOTED = re.compile(r"""['"]([^'"]+)['"]""")


def keys_written(func):
    source = inspect.getsource(func)
    keys = set(SET_KEY.findall(source))
    for args in BLANK_CALL.findall(source):
        keys.update(QUOTED.findall(args))
    return keys


class MetaRowTest(KodiTestCase):
    def test_the_list_matches_what_the_template_reads(self):
        with open(os.path.join(TEMPLATE_DIR, 'includes', 'pp_meta_row.xml.tpl'), encoding='utf-8') as fp:
            template = fp.read()
        read = set(re.findall(r'Window\.Property\(([^)]+)\)', template)) - {'{{ prop }}'}
        # The text fields are one label each, generated from the loop's own list of names.
        for names in re.findall(r'\{% for prop in \(([^)]*)\) %\}', template):
            read.update(re.findall(r"'([^']+)'", names))
        self.assertEqual(read, set(CommonMixin.META_ROW_PROPERTIES))

    def test_every_screen_showing_the_row_writes_all_of_it(self):
        for func in (library.LibraryWindow.setHeroInfo, preplay.PrePlayWindow.setInfo,
                     subitems.ShowWindow.updateProperties):
            missing = set(CommonMixin.META_ROW_PROPERTIES) - keys_written(func)
            self.assertEqual(set(), missing, func.__qualname__)
