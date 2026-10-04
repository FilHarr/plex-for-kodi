"""
What the sidebar shows, apart from which entry is highlighted: its entries (Search, Home,
Watchlist, Playlists, the libraries), the per-section show/hide/order preferences behind them, and
the server and user labels below them. windowutils.SidebarMixin turns these into list items and
window properties; each window keeps only its own highlight rule (sidebarActiveSection()).

Still the selected server's libraries only. The preferences are the account's, keyed by library id
(section_ids.sectionId()), so they already hold libraries from any server.
"""
from __future__ import absolute_import

import json
import threading

import plexnet
from plexnet import plexapp

from lib import backgroundthread
from lib import util
from lib.util import T
from . import home
from . import section_ids
from .section_ids import sectionId


def loadNavSettings():
    """The per-library show/hide/order preferences: {library id: {"show": bool}, "order": [library
    ids]}, one setting per account."""
    section_ids.migrate()
    return section_ids.loadJson(section_ids.sidebarKey())


def saveNavSettings(navSettings):
    util.setSetting(section_ids.sidebarKey(), json.dumps(navSettings))


def isShown(navSettings, section):
    sid = sectionId(section)
    return sid not in navSettings or navSettings[sid].get("show", True)


def refreshWatchlistSection():
    """Build home.watchlist_section afresh, when the watchlist is on. LibraryWindow does this for
    each sidebar it builds; the other screens show the one it made."""
    if plexapp.ACCOUNT.isOffline or not util.getUserSetting("use_watchlist", True):
        return
    from plexnet import plexlibrary
    try:
        section = plexlibrary.WatchlistSection(None, server=plexapp.SERVERMANAGER.getDiscoverServer())
    except plexnet.exceptions.BadRequest as e:
        # WatchlistSection() asks discover.provider.plex.tv straight away; a 503 there used to
        # leave the whole window half built. Without it the sidebar just has no Watchlist.
        util.DEBUG_LOG('Watchlist section unavailable ({0}), skipping for this session', e)
        home.watchlist_section = None
        return
    section.title = T(34000, 'Watchlist')
    home.watchlist_section = section


# Whether each server has any playlists, by server uuid: the sidebar shows Playlists only then.
_hasPlaylists = {}
_playlistsLock = threading.Lock()
_playlistsChecking = set()


def notePlaylists(server, playlists):
    """Record a playlists answer fetched elsewhere (the Playlists section's own view), so the next
    sidebar build doesn't ask again. A failed fetch, which leaves the server suspect, says
    nothing."""
    if server is None or server.suspect or server.offline:
        return
    with _playlistsLock:
        _hasPlaylists[server.uuid] = bool(playlists)


def hasPlaylists(server, onChange=None):
    """Whether to show Playlists for this server. Asked on the main thread for every sidebar build,
    and a blocking query there holds up the whole screen - up to the connect timeout on a server
    that has just died. So a known answer is used as it stands, and checked again on a worker for
    next time: onChange() runs (on that worker) if it turns out to have changed. Only a server never
    asked yet is asked here, as every build used to."""
    with _playlistsLock:
        known = _hasPlaylists.get(server.uuid)
    if known is None:
        if server.offline:
            return False
        answer = server.playlists()
        notePlaylists(server, answer)
        return bool(answer)
    _checkPlaylistsLater(server, known, onChange)
    return known


def _checkPlaylistsLater(server, known, onChange):
    with _playlistsLock:
        if server.uuid in _playlistsChecking:
            return
        _playlistsChecking.add(server.uuid)
    PlaylistsCheckTask(server, known, onChange).start()


class PlaylistsCheckTask(backgroundthread.Task):
    def __init__(self, server, known, onChange):
        backgroundthread.Task.__init__(self)
        self.server = server
        self.known = known
        self.onChange = onChange

    def run(self):
        try:
            if self.isCanceled() or self.server.offline:
                return
            answer = self.server.playlists()
            notePlaylists(self.server, answer)
            with _playlistsLock:
                now = _hasPlaylists.get(self.server.uuid)
            if now is not None and now != self.known and self.onChange and not self.isCanceled():
                util.DEBUG_LOG('Sidebar: {0} {1} playlists now', self.server.name, 'has' if now else 'has no')
                self.onChange()
        except:
            util.ERROR()
        finally:
            with _playlistsLock:
                _playlistsChecking.discard(self.server.uuid)


def sections(navSettings, onPlaylistsChange=None):
    """The sidebar's entries after Search and Home, in the user's order with hidden ones dropped:
    Watchlist, Playlists, then the selected server's libraries."""
    server = plexapp.SERVERMANAGER.selectedServer
    entries = []

    if (not plexapp.ACCOUNT.isOffline and util.getUserSetting("use_watchlist", True) and home.watchlist_section
            and home.watchlist_section.has_data()
            and isShown(navSettings, home.watchlist_section)):
        entries.append(home.watchlist_section)

    if isShown(navSettings, home.playlists_section) and hasPlaylists(server, onChange=onPlaylistsChange):
        entries.append(home.playlists_section)

    for section in server.library.sections():
        if isShown(navSettings, section):
            entries.append(section)

    if "order" in navSettings:
        order = navSettings["order"]

        def orderPos(s):
            sid = sectionId(s)
            if sid in order:
                return order.index(sid), 0
            return -1, 0

        entries = sorted(entries, key=orderPos)

    return entries


def matchSection(entries, sectionId, fromWatchlist=False):
    """The entry for sectionId; failing that, Watchlist when the screen was reached from it.
    sectionId can be a real section's key, empty, or "watchlist" (what discover items report),
    which matches no entry and so falls through to the Watchlist check."""
    if sectionId:
        for section in entries:
            if section.key == sectionId:
                return section
    if fromWatchlist:
        return home.watchlist_section
    return None


def serverAndUserProperties():
    """The window properties for the user's avatar and name and the selected server's icon and
    name, in the order they're set."""
    account = plexapp.ACCOUNT
    title = account.title or account.username or ' '
    props = [
        ('user.name', title),
        ('user.avatar', account.safeUserThumb(account.ID, thumb=account.thumb)),
        ('user.avatar.letter', title[0].upper()),
    ]

    server = plexapp.SERVERMANAGER.selectedServer
    if server and server.offline:
        # still selected, but not answering (PlexServerManager.setServerOnline())
        props += [('server.name', server.name),
                  ('server.icon', 'script.plex/home/device/error.png'),
                  ('server.iconmod', ''),
                  ('server.iconmod2', '')]
    elif server:
        props += [('server.name', server.name),
                  ('server.icon', 'script.plex/home/device/plex.png'),
                  ('server.iconmod', server.isSecure and 'script.plex/home/device/lock.png' or ''),
                  ('server.iconmod2', server.isLocal and 'script.plex/home/device/home_small.png' or '')]
    else:
        props += [('server.name', T(32338, 'No Servers Found')),
                  ('server.icon', 'script.plex/home/device/error.png'),
                  ('server.iconmod', ''),
                  ('server.iconmod2', '')]
    return props
