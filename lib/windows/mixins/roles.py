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
        """Library section id of the item roles are being browsed from, if any. Host windows
        that track a "current item" (PrePlayWindow, EpisodesWindow, ShowWindow/ArtistWindow)
        override this so PersonWindow's sidebar can highlight the section the click came from;
        default is None (VideoPlayerWindow has no sidebar, so it has nothing to thread through).
        """
        return None

    def roleFromWatchlist(self):
        """Whether the item roles are being browsed from was itself reached via the watchlist.
        Watchlist ("discover") items report the literal string "watchlist" as their library
        section id, which never matches a real section's key - this lets PersonWindow fall back
        to highlighting the Watchlist rail entry instead of nothing, same as PrePlayWindow's own
        buildSectionList() does.
        """
        return False

    def roleClicked(self):
        mli = self.rolesListControl.getSelectedItem()
        if not mli:
            return

        role = mli.dataSource
        if not role:
            return

        # Open the actor detail window directly
        self.processCommand(opener.open(role, section_id=self.roleSectionId(),
                                        from_watchlist=self.roleFromWatchlist()))
