# coding=utf-8
"""
lib/windows/collection.py's buildSubDirSection() - the synthetic, folder-scoped Section a
directory click builds (library.py's showPanelClicked()) and SubDirWindow.openDirectory() reuses
to drill further (hashed-orbiting-pizza.md's Phase 4).

This is the one piece of that work with no live coverage yet: the addon's own library has no
nested folders to click through, so the two-hop (folder-within-a-folder) path has never actually
run. What makes it safe on paper is that PlexObject.data is never reassigned after construction -
each synthetic Section is rebuilt from the *original* real Section's XML, not from the previous
hop's own (already-mutated) instance - so the real numeric librarySectionID survives no matter how
many hops deep this recurses. That invariant is exactly what a live folder-less test rig can't
exercise, so it's asserted here directly instead.

Importing lib.windows.collection starts lib.player's monitor thread unless abort_requested is set
first - same guard test_dropdown.py uses for the same reason.
"""

from __future__ import absolute_import

from xml.etree import ElementTree as ET

from kodienv import ENV

ENV.abort_requested = True
from lib.windows import collection  # noqa: E402

from plexnet import plexlibrary  # noqa: E402

from .base import KodiTestCase  # noqa: E402


def _movieSection(key="3", title="Movies", library_section_id="3"):
    root = ET.fromstring(
        '<MediaContainer><Directory key="{0}" title="{1}" librarySectionID="{2}"/></MediaContainer>'
        .format(key, title, library_section_id)
    )
    return plexlibrary.MovieSection(root.find("Directory"), initpath="/library/sections/3")


def _directory(key, title):
    return plexlibrary.Generic(ET.fromstring('<Directory key="{0}" title="{1}"/>'.format(key, title)))


class BuildSubDirSectionTest(KodiTestCase):
    def test_first_hop_scopes_key_and_title_to_the_clicked_folder(self):
        section = _movieSection()
        folder = _directory("/library/sections/3/folder/abc", "Films (Drive 1)")

        synthetic = collection.buildSubDirSection(section, folder)

        self.assertEqual(folder.key, synthetic.key)
        self.assertEqual(folder.title, synthetic.title)
        self.assertEqual("3", synthetic.getLibrarySectionId())
        # A fresh, distinct instance - not a mutation of the real section object, which stays
        # reusable for the caller's own further clicks in the same session.
        self.assertIsNot(section, synthetic)
        self.assertEqual("3", section.key)

    def test_second_hop_still_resolves_the_real_library_section_id(self):
        """
        The recursive case SubDirWindow.openDirectory() exercises for a folder-within-a-folder -
        untestable live against this addon's own library (no nested folders exist there). The real
        librarySectionID must survive a second hop even though the first hop's own .key is by then
        a folder path, not a digit.
        """
        section = _movieSection()
        firstHop = collection.buildSubDirSection(section, _directory("/library/.../abc", "Films (Drive 1)"))
        self.assertFalse(firstHop.key.isdigit())

        secondHop = collection.buildSubDirSection(firstHop, _directory("/library/.../abc/def", "Extras"))

        self.assertEqual("/library/.../abc/def", secondHop.key)
        self.assertEqual("Extras", secondHop.title)
        self.assertEqual("3", secondHop.getLibrarySectionId())

    def test_a_non_numeric_starting_key_falls_back_to_librarySectionID(self):
        """
        The defensive branch (`if not sectionId.isdigit(): sectionId = newSection.
        getLibrarySectionId()`) that a real top-level movie section's own numeric key never
        actually exercises in practice (see the module docstring) - covered directly here so it
        isn't silently dead code nobody would notice breaking.
        """
        section = _movieSection(key="/library/sections/3/folder", library_section_id="3")
        self.assertFalse(section.key.isdigit())

        synthetic = collection.buildSubDirSection(section, _directory("/library/.../abc", "Films (Drive 1)"))

        self.assertEqual("3", synthetic.getLibrarySectionId())
