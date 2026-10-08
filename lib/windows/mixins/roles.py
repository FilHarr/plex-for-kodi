# coding=utf-8

from kodi_six import xbmc

from lib import util
from lib.util import T
from .. import busy
from .. import credits
from .. import dropdown
from .. import kodigui
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
        arbitrary-depth drill chain, not just one hop. Default is None, for a host with no
        sidebar and so nothing to thread through.
        """
        return getattr(self, 'entrySectionId', None)

    def roleFromWatchlist(self):
        """Whether the sidebar entry PersonWindow should highlight is Watchlist -
        self.entryFromWatchlist, the same inherited-or-self-resolved flag roleSectionId() above
        uses. Watchlist ("discover") items report the literal string "watchlist" as their library
        section id, which never matches a real section's key - this lets PersonWindow fall back
        to highlighting the Watchlist rail entry instead of nothing, same as the sidebar's default
        rule (SidebarMixin.sidebarActiveSection()) does.
        """
        return getattr(self, 'entryFromWatchlist', False)

    def roleClicked(self):
        mli = self.rolesListControl.getSelectedItem()
        if not mli:
            return

        if mli.getProperty('is.more'):
            self.seeMoreCredits()
            return

        role = mli.dataSource
        if not role:
            return

        # Open the actor detail window directly
        self.processCommand(opener.open(role, context=self, section_id=self.roleSectionId(),
                                        from_watchlist=self.roleFromWatchlist()))

    def creditsItem(self):
        """The film or show whose credits the row shows (fillCreditsRow()) - the screen's own item.
        None on a screen whose row has no "See more" (Episodes)."""
        return None

    def fillCreditsRow(self):
        """The Cast & Crew row from credits.forItem(): Discover's list, or the server's, its first
        credits.ROW_MAX - up to two directors first when show_directors is on - then a "See more"
        tile when there are more, opening every credit (seeMoreCredits()). On a worker: it may ask
        Discover. False when the item has no credits."""
        itemCredits = credits.forItem(self.creditsItem())
        roles = itemCredits.row(util.getUserSetting('show_directors', True))
        if not roles:
            self.rolesListControl.reset()
            return False

        items = []
        for idx, role in enumerate(roles):
            mli = kodigui.ManagedListItem(role.tag, role.role or util.TRANSLATED_ROLES[role.translated_role],
                                          thumbnailImage=role.thumb.asTranscodedImageURL(*self.ROLES_DIM),
                                          data_source=role)
            mli.setProperty('index', str(idx))
            items.append(mli)
        if itemCredits.total > len(roles):
            # includes/role_tile.xml.tpl shows the hub rows' "See more" pill for it
            more = kodigui.ManagedListItem(T(35093, 'See more'))
            more.setBoolProperty('is.more', True)
            items.append(more)

        self.rolesListControl.reset()
        self.rolesListControl.addItems(items)
        return True

    def seeMoreCredits(self):
        """Every credit, Cast and Crew, in the credits grid (see_more.CreditsGridWindow)."""
        item = self.creditsItem()
        if item is None:
            return
        from .. import see_more
        self.openWindow(see_more.CreditsGridWindow, item=item, entry_section_id=self.roleSectionId(),
                        entry_from_watchlist=self.roleFromWatchlist())
