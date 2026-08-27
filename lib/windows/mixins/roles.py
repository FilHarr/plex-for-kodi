# coding=utf-8

from kodi_six import xbmc

from lib import util
from .. import busy
from .. import dropdown
from .. import opener


class RolesMixin(object):
    def getRoleItemDDPosition(self, y=None, container_id='400'):
        y = util.vscale(600 if y is None else y)

        tries = 0
        focus = xbmc.getInfoLabel('Container({}).Position'.format(container_id))
        while tries < util.MONITOR.waitAmount(2) and focus == '':
            focus = xbmc.getInfoLabel('Container({}).Position'.format(container_id))
            util.MONITOR.waitFor()
            tries += 1

        try:
            focus = int(focus)
        except ValueError:
            return -1, -1

        x = ((focus + 1) * 304) - 100
        return x, y

    def roleSectionId(self):
        """Library section id PersonWindow's sidebar should highlight when opened from here -
        self.entrySectionId (Sidebar entry-section persistence), not the host item's own real
        section: host windows resolve entrySectionId to their own real section only when they're
        themselves a genesis point (opened from the sidebar/Home/Search/Watchlist), and otherwise
        inherit it from whatever they were drilled in from - so this stays correct across an
        arbitrary-depth drill chain, not just one hop. Default is None (VideoPlayerWindow has no
        sidebar, so it has nothing to thread through).
        """
        return getattr(self, 'entrySectionId', None)

    def roleFromWatchlist(self):
        """Whether the sidebar entry PersonWindow should highlight is Watchlist -
        self.entryFromWatchlist, the same inherited-or-self-resolved flag roleSectionId() above
        uses. Watchlist ("discover") items report the literal string "watchlist" as their library
        section id, which never matches a real section's key - this lets PersonWindow fall back
        to highlighting the Watchlist rail entry instead of nothing, same as PrePlayWindow's own
        buildSectionList() does.
        """
        return getattr(self, 'entryFromWatchlist', False)

    def roleClicked(self):
        mli = self.rolesListControl.getSelectedItem()
        if not mli:
            return

        role = mli.dataSource
        if not role:
            return

        # Open the actor detail window directly
        self.processCommand(opener.open(role, context=self, section_id=self.roleSectionId(),
                                        from_watchlist=self.roleFromWatchlist()))
