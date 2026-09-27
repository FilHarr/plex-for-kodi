# coding=utf-8
"""A navigation request as a value (I5 in the navigation review).

Screens ask to go somewhere by passing one of these to navigate() (windowutils.GoHomeMixin): a
hosted screen hands it to its host, and Home acts on it through its navigation queue. A window
outside the chain hands it to Home the same way, then closes with it as its exitCommand, so the
blocking windows beneath it (each waiting in opener.handleOpen()) close in turn as it passes
through their processCommand().

It replaces the 'HOME' exit command and the section, force and go_root values that used to be
stashed on Home before that bubble started, and the closeOption that was set on Home before a
session-ending one: Home now sets closeOption itself, as it acts on a closeSession() intent.
"""
from __future__ import absolute_import


class NavIntent(object):
    HOME = 'home'
    CLOSE_SESSION = 'closeSession'

    __slots__ = ('kind', 'section', 'root', 'force', 'option')

    def __init__(self, kind, section=None, root=False, force=False, option=None):
        self.kind = kind
        self.section = section
        self.root = root
        self.force = force
        self.option = option

    def __repr__(self):
        if self.kind == self.CLOSE_SESSION:
            # a fast switch's option is a dict with a user id; the kind is enough for the log
            return 'NavIntent({0}, option={1})'.format(
                self.kind, self.option if not isinstance(self.option, dict) else sorted(self.option))
        return 'NavIntent({0}, section={1}, root={2}, force={3})'.format(
            self.kind, getattr(self.section, 'key', self.section), self.root, self.force)


def home(section=None, root=False, force=False):
    """Go Home: to section if one is given (force: even if it's already showing, to reset it),
    otherwise to Home's root (first row, item 0) if root, otherwise just back to what Home shows."""
    return NavIntent(NavIntent.HOME, section=section, root=root, force=force)


def closeSession(option):
    """End the session: Home sets closeOption to option and closes, and main.py acts on it once
    Home's window returns - exit, quit, restart, sign out, switch user ({'fast_switch': id} for a
    fast switch), go local or online, update."""
    return NavIntent(NavIntent.CLOSE_SESSION, option=option)


def isNavIntent(value):
    return isinstance(value, NavIntent)
