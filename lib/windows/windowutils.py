from __future__ import absolute_import

from lib import util
from lib.util import T
from . import dropdown
from . import opener

HOME = None


class GoHomeMixin():
    def goHome(self, section=None, with_root=False):
        HOME.go_root = with_root

        if section:
            self.closeWithCommand('HOME:{0}'.format(section))
        else:
            self.closeWithCommand('HOME')

        HOME.show()

    def goHomeRoot(self, *args, **kwargs):
        HOME.go_root = True
        self.closeWithCommand('HOME')
        HOME.show()


class SidebarMixin():
    """Control ids for the persistent vertical nav rail (includes/sidebar.xml.tpl)
    and its server/user dropdowns (includes/sidebar_dropdowns.xml.tpl). Any window
    that includes header_sidebar (see default.xml.tpl) can mix this in to reuse the
    same ids instead of redeclaring them.
    """
    SIDEBAR_GROUP_ID = 9000
    SECTION_LIST_ID = 9001

    SERVER_BUTTON_ID = 201
    USER_BUTTON_ID = 202

    USER_LIST_ID = 250
    SERVER_LIST_ID = 260
    SERVER_LIST_SCROLLBAR_ID = 261

    SERVER_MENU_GROUP_ID = 802
    SERVER_MENU_BG_ID = 800
    USER_MENU_BG_ID = 801
    USER_MENU_GROUP_ID = 901

    def reselectActiveSection(self, controlID, previousFocusID):
        """Call from onFocus(controlID), passing the control that had focus immediately before
        (self.lastFocusID, captured before it gets overwritten with controlID). If focus just moved
        onto the section list from outside the sidebar's own controls, snap the highlight to
        whichever item carries is.active - the section actually on screen - instead of leaving it on
        the list's last internally-browsed position, or, on a window's first focus event, index 0,
        which is always Search.
        """
        if controlID != self.SECTION_LIST_ID:
            return

        if previousFocusID in (self.SIDEBAR_GROUP_ID, self.SECTION_LIST_ID,
                                self.SERVER_BUTTON_ID, self.USER_BUTTON_ID):
            return

        sectionList = getattr(self, 'sectionList', None)
        if not sectionList:
            return

        for i in range(sectionList.size()):
            mli = sectionList[i]
            if mli and mli.getProperty('is.active'):
                sectionList.setSelectedItemByPos(i)
                return


class UtilMixin(GoHomeMixin):
    def __init__(self):
        self.exitCommand = None

    def openItem(self, obj, **kwargs):
        self.processCommand(opener.open(obj, **kwargs))

    def openWindow(self, window_class, **kwargs):
        self.processCommand(opener.handleOpen(window_class, **kwargs))

    def processCommand(self, command):
        if command and command.startswith('HOME'):
            self.exitCommand = command
            self.doClose()
        elif command and command == "NODATA":
            raise util.NoDataException

    def closeWithCommand(self, command):
        self.exitCommand = command
        self.doClose()

    def showAudioPlayer(self, **kwargs):
        from . import musicplayer
        self.processCommand(opener.handleOpen(musicplayer.MusicPlayerWindow, **kwargs))

    def getNextShowEp(self, pl, items, title):
        revitems = list(reversed(items))
        in_progress = [i for i in revitems if i.get('viewOffset').asInt()]
        if in_progress:
            n = in_progress[0]
            pl.setCurrent(n)

            if not util.getSetting('assume_resume'):
                choice = dropdown.showDropdown(
                    options=[
                        {'key': 'resume', 'display': T(32429, 'Resume from {0}').format(
                            util.timeDisplay(n.viewOffset.asInt()).lstrip('0').lstrip(':'))},
                        {'key': 'play', 'display': T(32317, 'Play from beginning')}
                    ],
                    pos=(660, 441),
                    set_dropdown_prop=False,
                    header=u'{0} - {1} \u2022 {2}'.format(title,
                                                          T(32310, 'S').format(n.parentIndex),
                                                          T(32311, 'E').format(n.index))
                )

                if not choice:
                    return None

                if choice['key'] == 'resume':
                    return True
            else:
                return True
            return False

        watched = False
        for (k, i) in enumerate(revitems):
            if watched:
                try:
                    pl.setCurrent(revitems[k-2])
                    return False
                except IndexError:
                    break
            if i.get('viewCount').asInt() > 0:
                watched = True

        non_special = [i for i in revitems if i.get('parentIndex').asInt() and i.get('viewCount').asInt() == 0]
        use = items[0]
        if non_special:
            use = non_special[-1]
        pl.setCurrent(use)
        return False



def shutdownHome():
    global HOME
    if HOME:
        HOME.shutdown()
    del HOME
    HOME = None
