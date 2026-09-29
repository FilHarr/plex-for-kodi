# coding=utf-8
"""
LibrarySettings (lib/windows/library.py): a section's item type, and its sort and filters stored
per item type, in one settings blob per server.

These were the surviving half of test_pinned_sections.py, whose pinned-collections half went with
the feature (28275e45). The item type has since moved from the module global library.ITEM_TYPE
onto each LibrarySettings (3e in the navigation review), so they're written against that.

Importing anything under lib/windows/ pulls in lib.player, which starts a monitor thread
that spins until Kodi says abort. Setting abort_requested before the import lets that
thread exit immediately, otherwise the interpreter never shuts down.
"""

from __future__ import absolute_import

import json

from kodienv import ENV

ENV.abort_requested = True
from lib.windows.library import LibrarySettings  # noqa: E402

from .base import KodiTestCase  # noqa: E402


class FakeServer(object):
    uuid = "SERVERUUID"


class FakeSection(object):
    TYPE = "movie"

    def __init__(self, key="3"):
        self.key = key
        self.server = FakeServer()

    def getServer(self):
        return self.server


class LibrarySettingsTest(KodiTestCase):
    def setUp(self):
        super(LibrarySettingsTest, self).setUp()
        self.section = FakeSection()

    def stored(self):
        return json.loads(ENV.settings["library.settings.SERVERUUID"])

    def test_a_section_never_configured_opens_in_its_own_type(self):
        self.assertEqual("movie", LibrarySettings(self.section).itemType)

    def test_a_section_reopens_in_its_last_item_type(self):
        LibrarySettings(self.section).setItemType("collection")

        self.assertEqual("collection", LibrarySettings(self.section).itemType)

    def test_each_item_type_keeps_its_own_sort_and_filter(self):
        # switching type used to clear the filters of the type being switched to
        settings = LibrarySettings(self.section)
        settings.setSetting("filter", {"display": "Genre"})
        settings.setSetting("sort", "addedAt")

        settings.setItemType("collection")
        self.assertIsNone(settings.getSetting("filter"))
        settings.setSetting("sort", "titleSort")

        settings.setItemType("movie")
        self.assertEqual({"display": "Genre"}, settings.getSetting("filter"))
        self.assertEqual("addedAt", settings.getSetting("sort"))

        settings.setItemType("collection")
        self.assertEqual("titleSort", settings.getSetting("sort"))

    def test_a_stale_instance_does_not_revert_a_later_choice(self):
        # both instances load the blob before the choice; the older one's write must only
        # touch its own field, not put back the item type it read at construction
        chosen = LibrarySettings(self.section)
        stale = LibrarySettings(self.section)

        chosen.setItemType("collection")
        stale.setSetting("sort", "addedAt")

        self.assertEqual("collection", self.stored()["3"]["ITEM_TYPE"])
        self.assertEqual("addedAt", self.stored()["3"]["movie"]["sort"])

    def test_sections_on_one_server_store_apart(self):
        LibrarySettings(self.section).setSetting("sort", "addedAt")
        LibrarySettings(FakeSection(key="5")).setSetting("sort", "titleSort")

        self.assertEqual("addedAt", self.stored()["3"]["movie"]["sort"])
        self.assertEqual("titleSort", self.stored()["5"]["movie"]["sort"])

    def test_a_sectionless_instance_writes_nothing(self):
        LibrarySettings(self.section).setSetting("sort", "addedAt")
        LibrarySettings("SERVERUUID").setSetting("sort", "titleSort")

        self.assertEqual({"3": {"movie": {"sort": "addedAt"}}}, self.stored())
