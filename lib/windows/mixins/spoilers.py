# coding=utf-8
import threading

from lib import util
from lib.data_cache import dcm
from lib.genres import GENRES_TV_BY_SYN
from plexnet import util as pnUtil
from .. import kodigui


class SpoilersMixin(object):
    def __init__(self, *args, **kwargs):
        self._noSpoilers = None
        self.spoilerSetting = ["unwatched"]
        self.noTitles = False
        self.noRatings = False
        self.noImages = False
        self.noResumeImages = False
        self.noSummaries = False
        self.spoilersAllowedFor = True
        # spoilerCovered(): show genres this screen has looked up (show ratingKey -> tags, empty lists too,
        # which the data cache drops), the shows being fetched and who's waiting on each, and the fetch queue
        self._spoilerGenres = {}
        self._spoilerWaiting = {}
        self._spoilerQueue = []
        self._spoilerLock = threading.Lock()
        self.cacheSpoilerSettings()

    def cacheSpoilerSettings(self):
        self.spoilerSetting = util.getSetting('no_episode_spoilers4')
        self.noTitles = 'no_unwatched_episode_titles' in self.spoilerSetting
        self.noRatings = 'hide_ratings' in self.spoilerSetting
        self.noImages = 'blur_images' in self.spoilerSetting
        self.noResumeImages = 'blur_resume_images' in self.spoilerSetting
        self.noSummaries = 'hide_summary' in self.spoilerSetting
        self.spoilersAllowedFor = util.getSetting('spoilers_allowed_genres2')

    @property
    def noSpoilers(self):
        return self.getNoSpoilers()

    def getCachedGenres(self, rating_key, server=None):
        genres = dcm.getCacheData("show_genres", rating_key, server=server)
        if genres:
            return [pnUtil.AttributeDict(tag=g) for g in genres]

    def getNoSpoilers(self, item=None, show=None):
        """
        when called without item or show, retains a global noSpoilers value, otherwise return dynamically based on item
        or show
        returns: "off" if spoilers unnecessary, otherwise "unwatched" or "funwatched"
        """
        if not item and not show and self._noSpoilers is not None:
            return self._noSpoilers

        if item and item.type != "episode":
            return "off"

        nope = "funwatched" if "in_progress" in self.spoilerSetting else "unwatched" \
            if "unwatched" in self.spoilerSetting else "off"

        if nope != "off" and self.spoilersAllowedFor:
            # instead of making possibly multiple separate API calls to find genres for episode's shows, try to get
            # a cached value instead
            genres = []
            if item or show:
                genres = self.getCachedGenres(item and item.grandparentRatingKey or show.ratingKey,
                                              server=(item or show).server)

            if not genres:
                show = getattr(self, "show_", show or (item and item.show()) or None)
                if not show:
                    return "off"

            if not genres and show:
                genres = show.genres()

            for g in genres:
                main_tag = GENRES_TV_BY_SYN.get(g.tag)
                if main_tag and main_tag in self.spoilersAllowedFor:
                    nope = "off"
                    break

        if item or show:
            self._noSpoilers = nope
            return self._noSpoilers
        return nope

    def spoilerCovered(self, ep, on_known=None):
        """
        Whether ep's spoilers are hidden - an episode the settings cover: unwatched, or never played with "In
        progress", outside the allowed genres (as hideSpoilers()) - with no request on the calling thread, for a
        screen that builds many items or follows focus (docs/spoilers-everywhere.md). Its show's genres come from
        this screen's own record, then the data cache. When neither has them the answer is True - hiding is the
        safe way to be wrong - and they're fetched on a worker, one show at a time, which then calls on_known(ep)
        (on that worker, while the screen is open: spoilerScreenOpen()) so the item can be redone.
        """
        if getattr(ep, 'TYPE', None) != 'episode':
            return False
        if 'in_progress' in self.spoilerSetting:
            # played once already: a re-watch in progress has nothing left to spoil
            if ep.isPlayed:
                return False
        elif 'unwatched' in self.spoilerSetting:
            if ep.isWatched:
                return False
        else:
            return False
        if not self.spoilersAllowedFor:
            return True
        key = ep.get('grandparentRatingKey')
        if not key:
            return True
        key = u'{0}'.format(key)
        with self._spoilerLock:
            genres = self._spoilerGenres.get(key)
        if genres is None:
            genres = dcm.getCacheData("show_genres", key, server=ep.server)
            if genres:
                with self._spoilerLock:
                    self._spoilerGenres[key] = list(genres)
            else:
                self._fetchShowGenres(key, ep, on_known)
                return True
        return not any(GENRES_TV_BY_SYN.get(g) in self.spoilersAllowedFor for g in genres)

    def spoilerScreenOpen(self):
        """Whether spoilerCovered()'s callbacks may still touch this screen."""
        gone = getattr(self, '_gone', None)
        if callable(gone):
            return not gone()
        return getattr(self, 'isOpen', True) and not getattr(self, '_closing', False)

    def _fetchShowGenres(self, key, ep, on_known):
        with self._spoilerLock:
            waiting = self._spoilerWaiting.get(key)
            if waiting is not None:
                if on_known:
                    waiting.append((ep, on_known))
                return
            self._spoilerWaiting[key] = [(ep, on_known)] if on_known else []
            self._spoilerQueue.append((key, ep))
            start = len(self._spoilerQueue) == 1
        if start:
            thread = threading.Thread(target=self._showGenresWorker, name='SpoilersMixin.genres')
            thread.daemon = True
            thread.start()

    def _showGenresWorker(self):
        while True:
            with self._spoilerLock:
                if not self._spoilerQueue:
                    return
                key, ep = self._spoilerQueue[0]
            genres = []
            try:
                if self.spoilerScreenOpen() and not util.MONITOR.abortRequested():
                    show = ep.show()
                    genres = [g.tag for g in (show and show.genres() or [])]
            except Exception as e:
                # covered, then: no exemption without the genres
                util.DEBUG_LOG("Spoilers: no genres for show {0}: {1}", key, e)
            with self._spoilerLock:
                self._spoilerGenres[key] = genres
                waiting = self._spoilerWaiting.pop(key, [])
                self._spoilerQueue.pop(0)
            for item, on_known in waiting:
                if not self.spoilerScreenOpen():
                    break
                try:
                    on_known(item)
                except kodigui.ScreenClosed:
                    break
                except Exception:
                    util.ERROR()

    def hideSpoilers(self, ep, fully_watched=None, watched=None, use_cache=True):
        """
        returns boolean on whether we should hide spoilers for the given episode
        """
        watched = watched if watched is not None else ep.isWatched
        # "In progress" hides an episode until it's been played once: a re-watch in progress (played, with a resume
        # point - not isFullyWatched) has nothing left to spoil
        fullyWatched = fully_watched if fully_watched is not None else ep.isPlayed
        nspoil = self.getNoSpoilers(item=ep if not use_cache else None)
        return ((nspoil == 'funwatched' and not fullyWatched) or
                (nspoil == 'unwatched' and not watched))

    def getThumbnailOpts(self, ep, fully_watched=None, watched=None, hide_spoilers=None):
        if not self.noImages or self.getNoSpoilers(item=ep) == "off":
            return {}
        return (hide_spoilers if hide_spoilers is not None else
                self.hideSpoilers(ep, fully_watched=fully_watched, watched=watched)) \
            and {"blur": util.addonSettings.episodeNoSpoilerBlur} or {}
