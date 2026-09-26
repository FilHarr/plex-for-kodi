# coding=utf-8
"""A navigation request as a value (I5 in the navigation review).

Screens ask to go somewhere by passing one of these to navigate() (windowutils.GoHomeMixin): a
hosted screen hands it to its host, and Home acts on it through its navigation queue. A window
outside the chain hands it to Home the same way, then closes with it as its exitCommand, so the
blocking windows beneath it (each waiting in opener.handleOpen()) close in turn as it passes
through their processCommand().

It replaces the 'HOME' exit command and the section, force and go_root values that used to be
stashed on Home before that bubble started.
"""
from __future__ import absolute_import


class NavIntent(object):
    HOME = 'home'

    __slots__ = ('kind', 'section', 'root', 'force')

    def __init__(self, kind, section=None, root=False, force=False):
        self.kind = kind
        self.section = section
        self.root = root
        self.force = force

    def __repr__(self):
        return 'NavIntent({0}, section={1}, root={2}, force={3})'.format(
            self.kind, getattr(self.section, 'key', self.section), self.root, self.force)


def home(section=None, root=False, force=False):
    """Go Home: to section if one is given (force: even if it's already showing, to reset it),
    otherwise to Home's root (first row, item 0) if root, otherwise just back to what Home shows."""
    return NavIntent(NavIntent.HOME, section=section, root=root, force=force)


def isNavIntent(value):
    return isinstance(value, NavIntent)
