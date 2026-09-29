# coding=utf-8
"""
lib/templating/core.py's strip_compiled() (step 13 in the navigation review): compiled windows lose
their comments, indentation and blank lines, and keep their line breaks. Every template, in every
played-indicator style, must parse to the same element tree either way - tags, attributes and
text, with only the whitespace around a text ignored - so nothing Kodi reads changes.
"""

from __future__ import absolute_import

import copy
import tempfile
import xml.etree.ElementTree as ET

from lib.templating import core
from lib.templating.context import TEMPLATE_CONTEXTS

from .base import KodiTestCase, make_engine
from .test_templates import render_theme


def canon(el):
    return (el.tag, sorted(el.attrib.items()), (el.text or '').strip(), (el.tail or '').strip(),
            [canon(child) for child in el])


class StripCompiledTest(KodiTestCase):
    def render(self, style, strip):
        context = copy.deepcopy(TEMPLATE_CONTEXTS)
        context['indicators']['START'] = {'INHERIT': style, 'style': style, 'hide_aw_bg': False}
        original = core.strip_compiled
        if not strip:
            core.strip_compiled = lambda xml: xml
        try:
            return render_theme(make_engine(tempfile.mkdtemp(), context=context), 'modern-colored')
        finally:
            core.strip_compiled = original

    def test_every_window_parses_to_the_same_tree(self):
        for style in sorted(TEMPLATE_CONTEXTS['indicators']):
            plain, stripped = self.render(style, False), self.render(style, True)
            for name in sorted(plain):
                with self.subTest(indicators=style, window=name):
                    self.assertEqual(canon(ET.fromstring(plain[name])), canon(ET.fromstring(stripped[name])))
                    self.assertNotIn('<!--', stripped[name])
                    self.assertLess(len(stripped[name]), len(plain[name]))

    def test_line_breaks_stay_and_indentation_goes(self):
        out = core.strip_compiled('<window>\n    <!-- why -->\n    <control type="label">\n\n'
                                  '        <label>Two words</label>\n    </control>\n</window>\n')
        self.assertEqual('<window>\n<control type="label">\n<label>Two words</label>\n</control>\n</window>\n', out)

    def test_a_multi_line_comment_goes_whole(self):
        out = core.strip_compiled('<a>\n  <!-- one\n  two -->\n  <b/>\n</a>')
        self.assertEqual('<a>\n<b/>\n</a>\n', out)
