# coding=utf-8
"""
Grid list items carry only the properties their view reads (step 12 stage F in the navigation
review): each grid view class names the optional properties its template reads (ITEM_PROPERTIES),
and a chunk writes only those. Checked here against the rendered templates, for every played-
indicator style, so a template change that starts or stops reading one fails until the view's
list follows.

Importing lib.windows.library starts lib.player's monitor thread unless abort_requested is set
first - same guard the other lib.windows.* tests use for the same reason.
"""

from __future__ import absolute_import

import copy
import re

from kodienv import ENV

ENV.abort_requested = True
from lib.templating.context import TEMPLATE_CONTEXTS  # noqa: E402
from lib.windows import library  # noqa: E402
from lib.windows import library_grid  # noqa: E402

from .base import KodiTestCase, make_engine  # noqa: E402
from .test_templates import render_theme  # noqa: E402

GRID_VIEWS = (library.PostersWindow, library.PostersSmallWindow, library.ListView16x9Window,
              library.SquaresWindow, library.ListViewSquareWindow, library.TrackListWindow)
READ_RE = re.compile(r'ListItem\.Property\(([^)$]+)\)')


class GridItemPropertiesTest(KodiTestCase):
    @classmethod
    def setUpClass(cls):
        super(GridItemPropertiesTest, cls).setUpClass()
        import tempfile
        cls.reads = {}
        for style in sorted(TEMPLATE_CONTEXTS['indicators']):
            context = copy.deepcopy(TEMPLATE_CONTEXTS)
            context['indicators']['START'] = {'INHERIT': style, 'style': style, 'hide_aw_bg': False}
            rendered = render_theme(make_engine(tempfile.mkdtemp(), context=context), 'modern-colored')
            for view in GRID_VIEWS:
                name = view.xmlFile[len('script-plex-'):-len('.xml')]
                cls.reads[(style, view)] = set(READ_RE.findall(rendered[name]))

    def test_each_view_writes_the_optional_properties_its_template_reads(self):
        for (style, view), reads in sorted(self.reads.items(), key=lambda kv: (kv[0][0], kv[0][1].__name__)):
            with self.subTest(indicators=style, view=view.__name__):
                self.assertEqual(reads & library_grid.OPTIONAL_ITEM_PROPERTIES, set(view.ITEM_PROPERTIES))

    def test_no_grid_reads_the_properties_items_no_longer_carry(self):
        for (style, view), reads in self.reads.items():
            with self.subTest(indicators=style, view=view.__name__):
                self.assertNotIn('initialized', reads)
                self.assertNotIn('unwatched', reads)

    def test_the_played_markers_are_still_read(self):
        for style in ('modern', 'modern_2024'):
            with self.subTest(indicators=style):
                self.assertIn('watched', self.reads[(style, library.PostersWindow)])
                self.assertIn('unwatched.count', self.reads[(style, library.PostersWindow)])

    def test_a_switch_to_a_view_that_reads_more_refills(self):
        # LibraryWindow.onFirstInit() reuses the items only when the view's set is covered.
        self.assertFalse(library.ListView16x9Window.ITEM_PROPERTIES <= library.PostersWindow.ITEM_PROPERTIES)
        self.assertTrue(library.PostersWindow.ITEM_PROPERTIES <= library.ListView16x9Window.ITEM_PROPERTIES)
