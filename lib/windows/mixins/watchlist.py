# coding=utf-8
import traceback

from lib import backgroundthread, util
from lib.i18n import T
from lib.windows import kodigui
from lib.windows import optionsdialog
from lib.windows.dialog import showOptionsDialog
from plexnet import plexapp, plexobjects, util as pnUtil, exceptions


class WatchlistCheckBaseTask(backgroundthread.Task):
    def setup(self, server_uuid, guid, callback):
        self.server_uuid = server_uuid
        self.guid = guid
        self.callback = callback
        return self

    def getServer(self):
        return plexapp.SERVERMANAGER.getServer(self.server_uuid)


class AvailabilityCheckTask(WatchlistCheckBaseTask):
    def setup(self, *args, **kwargs):
        media_type = kwargs.pop('media_type', None)
        WatchlistCheckBaseTask.setup(self, *args)
        self.media_type = media_type
        return self

    def run(self):
        if self.isCanceled():
            return

        server = None
        found = None
        try:
            if self.isCanceled():
                return

            server = self.getServer()
            res = server.query("/library/all", guid=self.guid, type=plexobjects.searchType(self.media_type))
            if res and res.get("size", 0):
                # find ratingKey
                found = []
                for child in res:
                    if child.tag in ("Directory", "Video"):
                        rk = child.get("ratingKey")
                        if rk:
                            metadata = {"rating_key": rk, "resolution": None, "bitrate": None, "season_count": None,
                                        "available": None, "server_uuid": str(self.server_uuid), "type": self.media_type,
                                        "library_title": child.get("librarySectionTitle")}

                            # find resolution for movies
                            if self.media_type == "movie":
                                for _child in child:
                                    if _child.tag == "Media":
                                        metadata["resolution"] = _child.get("videoResolution")
                                        metadata["bitrate"] = _child.get("bitrate")
                                        break
                            else:
                                metadata["season_count"] = child.get("childCount")
                            metadata["available"] = child.get("originallyAvailableAt")
                            found.append((server.name, metadata))

                if found:
                    # sort by quality
                    if self.media_type == "movie" and len(found) > 1:
                        found.sort(key=lambda item: int(item[1]["bitrate"]), reverse=True)
        except:
            util.ERROR()
            found = None
        finally:
            del server

        # always resolve the callback, otherwise the window's availability-checking state never settles
        self.callback(found or None)


class IsWatchlistedTask(WatchlistCheckBaseTask):
    def run(self):
        if self.isCanceled():
            return

        is_wl = None
        try:
            is_wl = is_watchlisted(guid=self.guid, server=self.getServer())
        except:
            util.ERROR()

        # always resolve the callback; None = state unknown, keep the old one
        self.callback(is_wl)


def is_watchlisted(guid, server):
    """
    Returns True/False for the item's watchlist state, None if the state couldn't be determined
    (e.g. discover endpoint gateway timeout).
    """
    try:
        res = server.query("/library/metadata/{}/userState".format(guid))
    except Exception as e:
        util.LOG("Watchlist: userState check for {} failed: {}", guid, repr(e))
        return None

    # some etree foo to find the watchlisted state
    if res and res.get("size", 0):
        for child in res:
            if child.tag == "UserState":
                if child.get("watchlistedAt", None):
                    return True
        return False


def is_continuing_series(guid, server):
    """
    Is a show still being made? Discover's isContinuingSeries="1"; an ended show has no such attribute. True when
    Discover couldn't be asked - a show stays on the watchlist rather than coming off on a guess.
    """
    try:
        res = server.query("/library/metadata/{}".format(guid))
    except Exception as e:
        util.LOG("Watchlist: series status check for {} failed: {}", guid, repr(e))
        return True

    if res is not None:
        for child in res:
            return child.get("isContinuingSeries") == "1"
    return True


def regular_episode_count(guid, server):
    """
    A show's episodes outside the specials (season 0), by Discover's seasons - its show-level leafCount counts the
    specials too. None when Discover couldn't be asked.
    """
    try:
        res = server.query("/library/metadata/{}/children".format(guid))
    except Exception as e:
        util.LOG("Watchlist: season check for {} failed: {}", guid, repr(e))
        return None

    if res is None:
        return None
    return sum(int(child.get("leafCount") or 0) for child in res if child.get("index") != "0")


def shouldAutoRemove(ref):
    """
    Watchlist auto-remove's rule: the setting on and ref fully watched - for a show, every episode on the server
    played, the show ended, and the server holding at least the episodes Discover lists outside the specials. One
    still being made, or with episodes the server hasn't got, stays watchlisted for those still to watch.
    """
    if not util.getUserSetting('watchlist_auto_remove', True):
        util.DEBUG_LOG("Watchlist: auto-remove is off, keeping {} on the watchlist", ref.ratingKey)
        return False
    if not getattr(ref, 'isFullyWatched', False):
        return False
    if ref.TYPE == 'show' and ref.guid and ref.guid.startswith("plex://"):
        server = pnUtil.SERVERMANAGER.getDiscoverServer()
        g = GUIDToRatingKey(ref.guid)
        if is_continuing_series(g, server):
            util.LOG("Watchlist: Show {} is still running, keeping it on the watchlist", ref.ratingKey)
            return False

        expected = regular_episode_count(g, server)
        try:
            have = sum(s.leafCount.asInt() for s in ref.seasons() if s.index.asInt() != 0)
        except Exception as e:
            util.LOG("Watchlist: Couldn't count the episodes of show {}: {}", ref.ratingKey, repr(e))
            have = None
        if expected is None or have is None or have < expected:
            util.LOG("Watchlist: Show {} has {} of {} episodes here, keeping it on the watchlist",
                     ref.ratingKey, have, expected)
            return False
    return True


def wl_wrap(f):
    def wrapper(cls, item, *args, **kwargs):
        if not cls.wl_enabled:
            return

        # if watchlist not wanted, return

        return f(cls, item, *args, **kwargs)
    return wrapper


def GUIDToRatingKey(guid):
    return guid.rsplit("/")[-1]


def removeFromWatchlistBlind(guid, ref):
    if not util.getUserSetting("use_watchlist", True) or pnUtil.ACCOUNT.isOffline:
        return

    util.DEBUG_LOG("Watchlist: Blind: Trying to blindly remove {}", guid)
    try:
        if not guid or not guid.startswith("plex://"):
            return

        server = pnUtil.SERVERMANAGER.getDiscoverServer()

        g = GUIDToRatingKey(guid)
        if not is_watchlisted(g, server):
            # False or None (state unknown, e.g. gateway timeout); don't touch the watchlist blindly
            return

        tries = 0
        while tries < 3:
            server.query("/actions/removeFromWatchlist", ratingKey=g, method="put")
            state = is_watchlisted(g, server)
            if state is None:
                util.LOG("Watchlist: Blind: Couldn't verify removal of {}", guid)
                return
            if not state:
                break
            util.LOG("Watchlist: Blind: Item still watchlisted, retrying ({}/3)", tries + 1)
            util.MONITOR.waitForAbort(0.1)
            tries += 1
        else:
            util.LOG("Watchlist: Blind: Action failed.")
            return
    except:
        exc = traceback.format_exc()
        util.DEBUG_LOG("Watchlist: Failed to blindly remove {}: {}", guid, exc)
    else:
        util.DEBUG_LOG("Watchlist: Possibly Removed {}", guid)
        util.showNotification(T(34077, "{} successfully removed from Watchlist").format(ref.defaultTitle),
                              time_ms=3000, header=T(34000, "Watchlist"))


def watchlistRef(item):
    """What stands on the watchlist for an item: an episode's or season's show - fetched again, so its watched counts
    include what was just marked - otherwise the item itself."""
    if item.TYPE in ('episode', 'season'):
        return item.show().reload(skip_cache=True)
    return item


def autoRemoveFromWatchlistBlind(ref):
    """Watchlist auto-remove where the screen keeps no watchlist state of its own (a grid, a collection, a screen
    closing behind auto-play): ref off the watchlist when shouldAutoRemove() says so. removeFromWatchlistBlind()
    alone is the explicit Remove from watchlist."""
    if shouldAutoRemove(ref):
        removeFromWatchlistBlind(ref.guid, ref)


class WatchlistUtilsMixin(object):
    WL_BTN_WAIT = 2302
    WL_BTN_MULTIPLE = 2303
    WL_BTN_SINGLE = 2304
    WL_BTN_UPCOMING = 2305

    WL_BTN_STATE_NOT_WATCHLISTED = 308
    WL_BTN_STATE_WATCHLISTED = 309

    WL_DYNAMIC_BTNS = (WL_BTN_WAIT, WL_BTN_MULTIPLE, WL_BTN_SINGLE, WL_BTN_UPCOMING)

    WL_BTN_STATE_BTNS = (WL_BTN_STATE_NOT_WATCHLISTED, WL_BTN_STATE_WATCHLISTED)

    @property
    def WL_RELEVANT_BTNS(self):
        """The screen's Play button and the availability states shown in its place."""
        return (self.PLAY_BUTTON_ID,) + self.WL_DYNAMIC_BTNS

    wl_availability = None

    def __init__(self, *args, **kwargs):
        super(WatchlistUtilsMixin, self).__init__()
        self.wl_availability = []
        self.is_watchlisted = False
        self.wl_enabled = False
        self.wl_ref = None
        self.wl_item_children = []

    def watchlist_setup(self, item):
        self.wl_enabled = util.getUserSetting("use_watchlist", True) and not pnUtil.ACCOUNT.isOffline \
            and item.guid and item.guid.startswith("plex://")
        self.wl_ref = GUIDToRatingKey(item.guid)
        self.setBoolProperty("watchlist_enabled", self.wl_enabled)

    @wl_wrap
    def wl_item_verbose(self, meta):
        if meta["type"] == "movie":
            res = "{}p".format(meta['resolution']) if not "k" in meta['resolution'] else meta['resolution'].upper()
            sub = '{} ({})'.format(res, pnUtil.bitrateToString(int(meta['bitrate']) * 1024))
        else:
            season_str = T(34006, '{} season') if int(meta["season_count"]) == 1 else T(34003, '{} seasons')
            sub = season_str.format(meta['season_count'])
        return sub

    @wl_wrap
    def wl_item_opener(self, ref, item_open_callback, selected_item=None):
        if len(self.wl_availability) > 1 and not selected_item:
            # choose
            # in the option picker: the server and library, then (dimmer, under it) the copy's resolution or
            # seasons
            options = []
            for idx, tup in enumerate(self.wl_availability):
                server, meta = tup
                options.append((idx, (u'{0} / {1}'.format(server, meta["library_title"]), self.wl_item_verbose(meta))))

            choice = showOptionsDialog(T(34004, 'Choose server'), options, non_playback=True,
                                       dialog_props=self.dialogProps, menu=True)
            if choice is None:
                return

            return self.wl_item_opener(ref, item_open_callback, selected_item=self.wl_availability[choice][1])

        item_meta = selected_item or self.wl_availability[0][1]
        rk = item_meta.get("rating_key", None)
        if rk:
            # the item opens on the server it's on; what it plays with follows it (item.server)
            server = plexapp.SERVERMANAGER.getServer(item_meta["server_uuid"])
            item_open_callback(item=rk, inherit_from_watchlist=False, server=server, is_watchlisted=True,
                               directly_from_watchlist=True,
                               came_from=self.wl_ref)

            self.checkIsWatchlisted(ref)

    @wl_wrap
    def wl_auto_remove(self, ref):
        util.LOG("Watchlist: DEBUG: %s, %s, %s %s" % (ref.ratingKey, self.is_watchlisted, ref.isFullyWatched, util.getUserSetting('watchlist_auto_remove', True)))
        if self.is_watchlisted and shouldAutoRemove(ref):
            # _modifyWatchlist returns the new watchlisted state; anything other than False means
            # the removal couldn't be verified (e.g. gateway timeout)
            if self.removeFromWatchlist(ref) is not False:
                util.LOG("Watchlist: Couldn't auto-remove item {} from watchlist", ref.ratingKey)
                return
            util.LOG("Watchlist: Item {} is fully watched, removed from watchlist", ref.ratingKey)
            util.showNotification(T(34077, "{} successfully removed from Watchlist").format(ref.defaultTitle),
                                  time_ms=3000, header=T(34000, "Watchlist"))
            return True
        elif not ref.isFullyWatched:
            util.LOG("Watchlist: Item {} is not fully watched, skipping", ref.ratingKey)

    @wl_wrap
    def watchlistItemAvailable(self, item, shortcut_watchlisted=False):
        """
        Is a watchlisted item available on any of the user's Plex servers?
        :param item:
        :return:
        """

        if shortcut_watchlisted:
            self.is_watchlisted = True
            self.setBoolProperty("is_watchlisted", True)
        self.setBoolProperty("wl_availability_checking", True)
        self.wl_checking_servers = len(list(pnUtil.SERVERMANAGER.connectedServers))
        self.wl_play_button_id = self.WL_BTN_WAIT

        def wl_set_btn():
            if not self.lastFocusID or self.lastFocusID in self.WL_RELEVANT_BTNS:
                change_to = None
                if self.wl_checking_servers:
                    change_to = self.WL_BTN_WAIT
                elif len(self.wl_availability) > 1:
                    change_to = self.WL_BTN_MULTIPLE
                elif len(self.wl_availability) == 1:
                    change_to = self.WL_BTN_SINGLE
                elif not self.wl_availability:
                    change_to = self.WL_BTN_UPCOMING

                if change_to and self.wl_play_button_id != change_to:
                    self.wl_play_button_id = change_to
                    # wait for visibility
                    kodigui.waitForVisibility(self.wl_play_button_id)
                    self.focusPlayButton(extended=True)

        wl_set_btn()

        def wl_av_callback(data):
            if data:
                self.wl_availability += data
                for server_name, metadata in data:
                    util.DEBUG_LOG("Watchlist availability: {}: {}", server_name, metadata)
                    self.wl_item_children.append(metadata['rating_key'])

            self.setBoolProperty("wl_availability", len(self.wl_availability) == 1)
            self.setBoolProperty("wl_availability_multiple", len(self.wl_availability) > 1)
            self.wl_checking_servers -= 1
            if self.wl_checking_servers == 0:
                self.setBoolProperty("wl_availability_checking", False)
            if self.wl_availability:
                compute = ", ".join("{}: {}".format(sn, self.wl_item_verbose(meta)) for sn, meta in self.wl_availability)
                self.setProperty("wl_server_availability_verbose", compute)

            wl_set_btn()

        for cserver in pnUtil.SERVERMANAGER.connectedServers:
            task = AvailabilityCheckTask().setup(cserver.uuid, item.guid, wl_av_callback, media_type=item.type)
            backgroundthread.BGThreader.addTask(task)

    @wl_wrap
    def checkIsWatchlisted(self, item):
        """
        Is an item on the user's watch list?
        :param item:
        :return:
        """

        if not self.wl_enabled:
            return False

        def callback(state):
            if state is None:
                util.LOG("Watchlist: Couldn't parse watchlist response, assuming old state")
                return
            self.is_watchlisted = state
            self.setBoolProperty("is_watchlisted", state)
            util.DEBUG_LOG("Watchlist state for item {}: {}", item.ratingKey, state)

        wl_rk = GUIDToRatingKey(item.guid)
        task = IsWatchlistedTask().setup('plexdiscover', wl_rk, callback)
        backgroundthread.BGThreader.addTask(task)

    def _modifyWatchlist(self, item, method="addToWatchlist"):
        server = pnUtil.SERVERMANAGER.getDiscoverServer()

        try:
            g = GUIDToRatingKey(item.guid)
            tries = 0
            wl_action_failed = False
            while tries < 3:
                server.query("/actions/{}".format(method), ratingKey=g, method="put")
                is_wl = is_watchlisted(g, server)
                if is_wl is None:
                    # couldn't verify the action (e.g. gateway timeout); don't claim success, don't keep retrying
                    util.LOG("Watchlist: Couldn't verify action {} for {}", method, item.ratingKey)
                    wl_action_failed = True
                    break
                if (is_wl and method == "addToWatchlist") or (not is_wl and method == "removeFromWatchlist"):
                    break
                util.LOG("Watchlist: Action didn't succeed, retrying ({}/3)", tries + 1)
                util.MONITOR.waitForAbort(0.1)
                tries += 1
            else:
                util.LOG("Watchlist: Action failed.")
                wl_action_failed = True

            if wl_action_failed:
                return self.is_watchlisted

            util.LOG("Watchlist action {} for {} succeeded", method, item.ratingKey)
            self.is_watchlisted = method == "addToWatchlist"
            self.setBoolProperty("is_watchlisted", method == "addToWatchlist")
            pnUtil.APP.trigger("watchlist:modified")
            return method == "addToWatchlist"
        except exceptions.BadRequest:
            util.LOG("Watchlist action {} for {} failed", method, item.ratingKey)
            return self.is_watchlisted

    @wl_wrap
    def addToWatchlist(self, item):
        return self._modifyWatchlist(item)

    @wl_wrap
    def removeFromWatchlist(self, item):
        return self._modifyWatchlist(item, method="removeFromWatchlist")

    @wl_wrap
    def toggleWatchlist(self, item):
        """The watchlist button (pre-play, Seasons): the new watchlisted state. Removing asks first when Confirm item
        actions is on, as the library grid's Remove from watchlist does; a "No" leaves it watchlisted."""
        if self.is_watchlisted and util.getSetting('home_confirm_actions'):
            button = optionsdialog.show(u'{0}?'.format(T(34011, "Remove from watchlist")), '',
                                        T(32328, 'Yes'), T(32329, 'No'),
                                        dialog_props=getattr(self, "carriedProps", getattr(self, "dialogProps", None)))
            if button != 0:
                return True
        return self._modifyWatchlist(item, method="removeFromWatchlist" if self.is_watchlisted else "addToWatchlist")
