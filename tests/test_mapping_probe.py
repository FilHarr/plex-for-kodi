# coding=utf-8
"""
lib/windows/mapping_probe.py and the sidebar's path-mapping dots - whether a path-mapped library's
share answers, ported from upstream HomeWindow's PathMappingProbeTask.

The probe's shares are real folders in the test profile (one made, one not), checked through the
xbmcvfs stub, so "down" and "back" are a folder disappearing and appearing.
"""

from __future__ import absolute_import

import os
import shutil
import tempfile
from unittest import mock

from kodienv import ENV

from lib.windows import mapping_probe, windowutils

from .base import KodiTestCase
from .test_path_mapping import manager
from .test_sidebar_model import ANIMAL, Section, SidebarCase, Shell


class MappedSection(Section):
    """A library with the properties the probe and the sidebar read (plexlibrary.LibrarySection)."""

    def __init__(self, key, title, roots, mgr, **kw):
        Section.__init__(self, key, title, **kw)
        self.mappedPaths = list(roots)
        self._mgr = mgr

    @property
    def isMapped(self):
        return bool(self.mappedPaths)

    @property
    def mappingBroken(self):
        return any(self._mgr.isMappingBroken(self.server.name, p) for p in self.mappedPaths)


class ProbeCase(KodiTestCase):
    def setUp(self):
        KodiTestCase.setUp(self)
        ENV.settings["path_mapping"] = "true"
        # each test's own shares: one there, one not
        root = tempfile.mkdtemp(dir=ENV.profile_root)
        self.addCleanup(shutil.rmtree, root, True)
        self.root = root
        self.up = os.path.join(root, "share_up") + os.sep
        self.down = os.path.join(root, "share_down") + os.sep
        os.makedirs(self.up)
        self.mgr = manager({ANIMAL.name: {self.up: "/data/movies/", self.down: "/data/tv/"}})
        self.tasks = []
        self.notices = []
        self.changes = []
        for patcher in (
                mock.patch.object(mapping_probe, 'pmm', self.mgr),
                mock.patch.object(mapping_probe, '_targets', []),
                mock.patch.object(mapping_probe, '_lastProbe', 0),
                mock.patch.object(mapping_probe, '_running', False),
                mock.patch.object(mapping_probe, '_onChange', lambda: self.changes.append(True)),
                mock.patch.object(mapping_probe.backgroundthread.BGThreader, 'addTask', self.tasks.append),
                mock.patch.object(mapping_probe.PathMappingProbeTask, 'isCanceled', lambda task: False),
                mock.patch.object(self.mgr, 'notify', self.notices.append)):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.movies = MappedSection('1', 'Movies', [self.up], self.mgr)
        self.tv = MappedSection('2', 'TV Shows', [self.down], self.mgr)

    def runTasks(self):
        while self.tasks:
            self.tasks.pop(0).run()


class ProbeTest(ProbeCase):
    def test_new_targets_are_checked_at_once(self):
        mapping_probe.setTargets([self.movies, self.tv])
        self.assertEqual(1, len(self.tasks))
        self.runTasks()
        self.assertFalse(self.mgr.isMappingBroken(ANIMAL.name, self.up))
        self.assertTrue(self.mgr.isMappingBroken(ANIMAL.name, self.down))
        self.assertEqual([True], self.changes)

    def test_the_same_targets_again_dont_check_again(self):
        mapping_probe.setTargets([self.movies, self.tv])
        self.runTasks()
        mapping_probe.setTargets([self.movies, self.tv])
        self.assertEqual([], self.tasks)

    def test_one_notification_per_run_naming_each_library(self):
        other = os.path.join(self.root, "share_gone") + os.sep
        self.mgr.PATH_MAP[ANIMAL.name][other] = "/data/music/"
        music = MappedSection('3', 'Music', [other], self.mgr)
        mapping_probe.setTargets([self.movies, self.tv, music])
        self.runTasks()
        self.assertEqual(1, len(self.notices))
        self.assertIn("TV Shows", self.notices[0])
        self.assertIn("Music", self.notices[0])
        self.assertNotIn("Movies", self.notices[0])

    def test_a_share_still_down_isnt_announced_again(self):
        mapping_probe.setTargets([self.tv])
        self.runTasks()
        mapping_probe.tick(mapping_probe.time.time() + mapping_probe.PROBE_INTERVAL + 1)
        self.runTasks()
        self.assertEqual(1, len(self.notices))
        # and nothing changed the second time, so no rebuild
        self.assertEqual([True], self.changes)

    def test_the_tick_checks_again_once_the_interval_is_up(self):
        mapping_probe.setTargets([self.tv])
        self.runTasks()
        mapping_probe.tick(mapping_probe.time.time() + 1)
        self.assertEqual([], self.tasks)
        mapping_probe.tick(mapping_probe.time.time() + mapping_probe.PROBE_INTERVAL + 1)
        self.assertEqual(1, len(self.tasks))

    def test_a_share_that_comes_back_is_found_by_the_tick(self):
        mapping_probe.setTargets([self.tv])
        self.runTasks()
        os.makedirs(self.down)
        mapping_probe.tick(mapping_probe.time.time() + mapping_probe.PROBE_INTERVAL + 1)
        self.runTasks()
        self.assertFalse(self.mgr.isMappingBroken(ANIMAL.name, self.down))
        self.assertEqual([True, True], self.changes)

    def test_one_run_at_a_time(self):
        mapping_probe.setTargets([self.tv])
        mapping_probe.tick(mapping_probe.time.time() + mapping_probe.PROBE_INTERVAL + 1)
        mapping_probe.start()
        self.assertEqual(1, len(self.tasks))

    def test_a_root_shared_by_two_libraries_is_checked_once(self):
        films = MappedSection('4', 'Films', [self.down], self.mgr)
        self.assertEqual([(ANIMAL.name, self.down, 'TV Shows')], mapping_probe.targetsFor([self.tv, films]))

    def test_entries_without_mappings_are_skipped(self):
        self.assertEqual([], mapping_probe.targetsFor([Section('5', 'Plain'), object()]))

    def test_no_mapping_no_targets(self):
        ENV.settings["path_mapping"] = "false"
        self.assertEqual([], mapping_probe.targetsFor([self.movies]))


class SidebarDotsTest(SidebarCase):
    def setUp(self):
        SidebarCase.setUp(self)
        self.mgr = manager({ANIMAL.name: {"/mnt/movies/": "/data/movies/"}})
        self.mgr.BROKEN_MAP = {ANIMAL.name: {"/mnt/movies/": True}}
        self.movies = MappedSection('1', 'Movies', ["/mnt/movies/"], self.mgr)
        self.listed(self.server.uuid, [self.movies])
        self.store('1')
        self.targets = []
        for patcher in (mock.patch.object(windowutils, 'pmm', self.mgr),
                        mock.patch.object(windowutils.mapping_probe, 'setTargets', self.targets.append)):
            patcher.start()
            self.addCleanup(patcher.stop)

    def item(self, sectionList, label):
        return [mli for mli in sectionList.items if mli.getLabel() == label][0]

    def test_a_share_thats_down_shows_with_the_mapped_dot(self):
        movies = self.item(self.build(Shell()), 'Movies')
        self.assertEqual('1', movies.getProperty('is.mapped.broken'))
        self.assertEqual('1', movies.getProperty('is.mapped'))

    def test_the_down_dot_shows_with_the_indicator_setting_off(self):
        self.settings['path_mapping_indicators'] = False
        movies = self.item(self.build(Shell()), 'Movies')
        self.assertEqual('1', movies.getProperty('is.mapped.broken'))
        self.assertEqual('', movies.getProperty('is.mapped'))

    def test_no_dots_without_path_mapping(self):
        # pmm.mapping reads it through path_mapping.py's own getSetting
        ENV.settings['path_mapping'] = 'false'
        movies = self.item(self.build(Shell()), 'Movies')
        self.assertEqual('', movies.getProperty('is.mapped.broken'))
        self.assertEqual('', movies.getProperty('is.mapped'))

    def test_the_build_hands_its_libraries_to_the_probe(self):
        self.build(Shell())
        self.assertEqual(1, len(self.targets))
        self.assertIn(self.movies, self.targets[0])
