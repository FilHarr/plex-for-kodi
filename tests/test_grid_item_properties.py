# coding=utf-8
"""
Grid list items carry only what the grid templates read (step 12 stage F in the navigation
review). The chunk writer (GridMixin._chunkCallback()) no longer writes summary or art, which only
the removed 16:9 list view read, or a per-item initialized or unwatched, which nothing read. Checked
here against the rendered templates of every view the chunk writer fills, for every played-
indicator style, so a template that starts reading one of them fails until the writer follows.
(The square list reads summary, but it only shows Photos, which fills its items
itself.) The Collection and folder screens' item writers (collection.py) are held to the same
rule.

Importing lib.windows.library starts lib.player's monitor thread unless abort_requested is set
first - same guard the other lib.windows.* tests use for the same reason.
"""

from __future__ import absolute_import

import copy
import inspect
import re
import tempfile

from kodienv import ENV

ENV.abort_requested = True
from lib.templating.context import TEMPLATE_CONTEXTS  # noqa: E402
from lib.windows import collection  # noqa: E402
from lib.windows import library  # noqa: E402
from lib.windows import library_grid  # noqa: E402

from .base import KodiTestCase, make_engine  # noqa: E402
from .test_templates import render_theme  # noqa: E402

# Every view the chunk writer fills: the poster grids for video sections, the square grid for
# music (artists, albums, collections) and the tracks list.
CHUNK_VIEWS = (library.PostersWindow, library.PostersSmallWindow, library.SquaresWindow,
               library.TrackListWindow)
NOT_WRITTEN = ('summary', 'art', 'initialized', 'unwatched')
# The Collection and folder screens: collection.BoundedGridWindow's own item writers.
BOUNDED_VIEWS = (collection.CollectionWindow, collection.SubDirWindow)
READ_RE = re.compile(r'ListItem\.Property\(([^)$]+)\)')


class GridItemPropertiesTest(KodiTestCase):
    @classmethod
    def setUpClass(cls):
        super(GridItemPropertiesTest, cls).setUpClass()
        cls.reads = {}
        for style in sorted(TEMPLATE_CONTEXTS['indicators']):
            context = copy.deepcopy(TEMPLATE_CONTEXTS)
            context['indicators']['START'] = {'INHERIT': style, 'style': style, 'hide_aw_bg': False}
            rendered = render_theme(make_engine(tempfile.mkdtemp(), context=context), 'modern-colored')
            for view in CHUNK_VIEWS + BOUNDED_VIEWS:
                name = view.xmlFile[len('script-plex-'):-len('.xml')]
                cls.reads[(style, view)] = set(READ_RE.findall(rendered[name]))

    def test_no_chunk_filled_view_reads_what_the_writer_leaves_out(self):
        for (style, view), reads in self.reads.items():
            with self.subTest(indicators=style, view=view.__name__):
                self.assertEqual(set(), reads & set(NOT_WRITTEN))

    def test_the_writer_leaves_them_out(self):
        source = inspect.getsource(library_grid.GridMixin._chunkCallback)
        for prop in NOT_WRITTEN:
            with self.subTest(prop=prop):
                self.assertNotIn("setProperty('{0}'".format(prop), source)

    def test_the_collection_and_folder_screens_read_none_of_them_either(self):
        for (style, view), reads in self.reads.items():
            if view in BOUNDED_VIEWS:
                with self.subTest(indicators=style, view=view.__name__):
                    self.assertEqual(set(), reads & set(NOT_WRITTEN))
                    self.assertIn('year', reads)

    def test_their_writers_leave_them_out(self):
        source = (inspect.getsource(collection.BoundedGridWindow.setItemInfo)
                  + inspect.getsource(collection.BoundedGridWindow.setWatchedInfo))
        for prop in NOT_WRITTEN:
            with self.subTest(prop=prop):
                self.assertNotIn("setProperty('{0}'".format(prop), source)

    def test_the_played_markers_are_still_read(self):
        for style in ('modern', 'modern_2024'):
            with self.subTest(indicators=style):
                self.assertIn('watched', self.reads[(style, library.PostersWindow)])
                self.assertIn('unwatched.count', self.reads[(style, library.PostersWindow)])

    def test_video_sections_are_posters_only(self):
        self.assertEqual((library.PostersWindow, library.PostersSmallWindow), library.VIEWS_POSTER['all'])
        self.assertNotIn('list', library.VIEWS_POSTER)
