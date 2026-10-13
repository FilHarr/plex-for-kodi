# coding=utf-8
"""plex.direct host mapping, ported from upstream HomeWindow.checkPlexDirectHosts() (home.py @ 2707bbe7),
which went with HomeWindow in 12675d11 and wasn't ported then.

A server's secure connections are named like 1-2-3-4.<hash>.plex.direct, meant to resolve through public DNS to
the IP in the name. Routers and DNS filters with DNS-rebind protection refuse to return a LAN IP for a public
name. The add-on's own requests never notice (plexnet/http.py reads the IP out of the name), but Kodi's do -
artwork and playback - so the names are written to the <hosts> block of advancedsettings.xml (lib/plex_hosts.py),
which Kodi reads like a hosts file after a restart.

check() runs on whichever thread calls it: LibraryWindow's first init for the stored servers, and its
loaded:server_connections handler (plexnet's thread) for the ones from plex.tv. With handle_plexdirect at "ask",
the question is posted to the main thread instead (post), as the update prompt is. State lives here rather
than on a window: a nested LibraryWindow and Settings reach the same mapping, and it outlives a Home restart.
"""
from __future__ import absolute_import

import threading

from plexnet import plexapp
from plexnet import plexresource

from lib import util
from lib.plex_hosts import pdm
from lib.util import T
from . import optionsdialog

# pdm's state is changed from plexnet's threads and from the main thread
_lock = threading.RLock()
# the question is waiting on the main thread
_promptPosted = False
# hosts the question was dismissed for: not asked again this session (upstream asked on every plex.tv refresh)
_declined = set()


def reset():
    """A new root LibraryWindow: a question posted to the last one never ran."""
    global _promptPosted
    _promptPosted = False


def check(servers, source="stored", post=None):
    """Collect the plex.direct names of servers that aren't in advancedsettings.xml yet, and map them as
    handle_plexdirect says. post(fn) runs fn on the main thread; it's needed for "ask"."""
    global _promptPosted
    handlePD = util.getSetting('handle_plexdirect', 'ask')
    if handlePD == "never":
        return

    forcePD = util.getSetting('force_pd_mapping', False)
    servers = list(servers)
    util.DEBUG_LOG("PlexDirect: check: {} ({})", servers, source)

    with _lock:
        hosts = []
        names = []
        for server in servers:
            force_check = False
            # an active connection that's marked as local, but which a combination of settings doesn't let us
            # reach insecurely: force plex.direct handling for it
            if (server.activeConnection and ".plex.direct:" in server.activeConnection.address and
                    not server.activeConnection.pdHostnameResolved) or forcePD:
                util.DEBUG_LOG("PlexDirect: Forcing check for plex.direct connections of: {} (force: {})",
                               server, forcePD)
                force_check = True

            if not force_check:
                # only stored or plex.tv servers
                if server.sourceType not in (None, plexresource.ResourceConnection.SOURCE_MYPLEX):
                    continue
                # honouring dnsRebindingProtection=1 when the server has it at 0, or publicAddressMatches=1 when
                # the server has it at 0 and hasn't been seen on the LAN: no mapping, unless a name fails
                if (((util.addonSettings.honorPlextvDnsrebind and not server.dnsRebindingProtection) or
                        (util.addonSettings.honorPlextvPam and not server.sameNetwork and
                         not server.anyLANConnection))
                        and not server.anyPDHostNotResolvable):
                    util.DEBUG_LOG("PlexDirect: Ignoring DNS handling for plex.direct connections of: {}", server)
                    continue
            hosts += [c.address for c in server.connections]
            names.append(server.name)

        pdHosts = [host for host in hosts if ".plex.direct:" in host]
        util.DEBUG_LOG("PlexDirect: Checking host mapping for {} {} connections: {}, servers: {}",
                       len(pdHosts), source, ", ".join(pdHosts), ", ".join(names))

        newHosts = set(pdHosts) - set(pdm.getHosts())
        if newHosts:
            force_mapping = []
            # even a Docker address gets mapped when it's the one that didn't resolve
            for server in servers:
                if not server.anyPDHostNotResolvable and not forcePD:
                    continue
                addrs = [c.address for c in server.connections
                         if ".plex.direct:" in c.address and (not c.pdHostnameResolved or forcePD)]
                force_mapping += addrs
                util.DEBUG_LOG("PlexDirect: Forcing mapping for connections via: {}", addrs)
            pdm.newHosts(newHosts, source=source, force_mapping=force_mapping)

        util.DEBUG_LOG("PlexDirect: hosts to add to advancedsettings.xml: {}", pdm.diff)

        # plex.tv's resources can be in before anything else; then the stored servers are as good as theirs
        force = plexapp.MANAGER.gotResources
        if not (((source == "stored" and plexapp.ACCOUNT.isOffline) or source == "myplex" or force or forcePD)
                and pdm.differs):
            return

        if handlePD != "ask":
            _write()
            # quietly: this may be plexnet's thread
            _announce(dialog=False)
            return

        if pdm.diff <= _declined:
            util.DEBUG_LOG("PlexDirect: already asked about these hosts this session")
            return
        if _promptPosted or post is None:
            return
        _promptPosted = True
    post(_prompt)


def _prompt():
    """Main thread: ask whether to write the new hosts. Dismissed, they're left out until the next session."""
    global _promptPosted
    try:
        with _lock:
            if not pdm.differs:
                return
            count = len(pdm.diff)
        # not holding the lock while a dialog is up: plexnet's threads would wait on it
        button = optionsdialog.show(
            T(32993, '').format(count),
            T(32994, '').format(count),
            T(32328, 'Yes'),
            T(32035, 'Always'),
            T(32033, 'Never'),
        )
        with _lock:
            if button not in (0, 1, 2):
                _declined.update(pdm.diff)
                pdm.resetHosts()
                return
            if button == 1:
                util.setSetting('handle_plexdirect', 'always')
            elif button == 2:
                util.setSetting('handle_plexdirect', 'never')
                pdm.resetHosts()
                return
            firstMapping = not pdm.hadHosts
            _write()
        # the first time, a dialog rather than a notification
        _announce(dialog=firstMapping)
    finally:
        _promptPosted = False


def _write():
    """Under _lock."""
    pdm.write()
    util.LOG("PlexDirect: wrote {} plex.direct host(s) to advancedsettings.xml", len(pdm))


def _announce(dialog):
    """Kodi reads advancedsettings.xml at start, so the mapping needs a Kodi restart."""
    if dialog:
        optionsdialog.show(
            T(32995, ''),
            T(32996, ''),
            T(32997, 'OK'),
        )
    else:
        util.showNotification(T(32996, ''), header=T(32995, ''))
