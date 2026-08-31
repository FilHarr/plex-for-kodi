# coding=utf-8
import math

from lib import util
from lib.i18n import T
from lib.windows import kodigui


class SeasonsMixin(object):
    SEASONS_CONTROL_ATTR = "subItemListControl"

    THUMB_DIMS = {
        'show': {
            'main.thumb': util.scaleResolution(347, 518),
            'item.thumb': util.scaleResolution(240, 360)
        },
        'episode': {
            'main.thumb': util.scaleResolution(347, 518),
            'item.thumb': util.scaleResolution(198, 295)
        },
        'artist': {
            'main.thumb': util.scaleResolution(519, 519),
            'item.thumb': util.scaleResolution(215, 215)
        }
    }

    def _createListItem(self, mediaItem, obj):
        mli = kodigui.ManagedListItem(
            obj.title or '',
            thumbnailImage=obj.defaultThumb.asTranscodedImageURL(*self.THUMB_DIMS[mediaItem.type]['item.thumb']),
            data_source=obj
        )
        episode_count = obj.leafCount.asInt()
        episode_str = T(35057, '{} episode') if episode_count == 1 else T(35056, '{} episodes')
        mli.setProperty('episode.count', episode_str.format(episode_count))
        return mli

    def getSeasonProgress(self, show, season):
        """
        calculates the season progress based on how many episodes are watched and, optionally, if there's an episode
        in progress, take that into account as well
        """
        viewed = season.viewedLeafCount.asInt()
        has_ondeck_progress = False
        for v in show.onDeck:
            if v.parentRatingKey == season.ratingKey and v.viewOffset.asInt():
                has_ondeck_progress = True
                break
        if has_ondeck_progress and viewed == season.leafCount.asInt():
            viewed -= 1
        watchedPerc = viewed / season.leafCount.asInt() * 100
        for v in show.onDeck:
            if v.parentRatingKey == season.ratingKey and v.viewOffset:
                vPerc = int((v.viewOffset.asInt() / v.duration.asFloat()) * 100)
                watchedPerc += vPerc / season.leafCount.asFloat()
        return watchedPerc > 0 and math.ceil(watchedPerc) or 0

    def fillSeasons(self, show, update=False, seasonsFilter=None, selectSeason=None, do_focus=True,
                     extraFirstItem=None, altControlAttr=None, altThreshold=6):
        try:
            seasons = show.seasons()
        except:
            raise util.NoDataException

        if not seasons or (seasonsFilter and not seasonsFilter(seasons)):
            return False

        items = []
        idx = 0
        focus = None
        current_idx = None

        # Episodes' own season-tab row (EpisodesWindow.SEASONS_LIST_ID) prepends a pinned "Show" entry
        # ahead of the real seasons - see episodes.py's own fillSeasons() call sites. ShowWindow's own
        # season row never passes this, so its behavior is unchanged.
        if extraFirstItem is not None:
            items.append(extraFirstItem)
            idx = 1
        for season in seasons:
            mli = self._createListItem(show, season)
            if mli:
                is_current = bool(selectSeason) and season == selectSeason
                mli.setProperty('index', str(idx))
                mli.setProperty('thumb.fallback', 'script.plex/thumb_fallbacks/show.png')
                mli.setBoolProperty('current', is_current)
                if is_current:
                    current_idx = idx
                seasonWatched = season.isWatched
                has_ondeck_progress = False
                for v in show.onDeck:
                    if v.parentRatingKey == season.ratingKey and v.viewOffset.asInt():
                        has_ondeck_progress = True
                        break
                if has_ondeck_progress and season.viewedLeafCount == season.leafCount:
                    seasonWatched = False
                mli.setProperty('unwatched.count', not seasonWatched and str(season.unViewedLeafCount) or '')
                mli.setBoolProperty('unwatched.count.large', not seasonWatched and season.unViewedLeafCount > 999)
                mli.setBoolProperty('watched', seasonWatched)
                if not selectSeason and not seasonWatched and focus is None and season.index.asInt() > 0:
                    focus = idx
                    mli.setProperty('progress', util.getProgressImage(None, self.getSeasonProgress(show, season)))
                items.append(mli)
                idx += 1

        subItemListControl = getattr(self, self.SEASONS_CONTROL_ATTR)
        # altControlAttr: same "fixedlist needs enough items, plain list doesn't" split as
        # ShowWindow's own season-tab row (subitems.py's fillSeasonTabs()) - only ever passed by a
        # caller with its own second, plain-list control to fall back to (EpisodesWindow's tab row);
        # ShowWindow's own season row (id=400, a plain list already) never passes this, so its own
        # behavior is unchanged.
        if altControlAttr is not None:
            altControl = getattr(self, altControlAttr)
            if len(seasons) <= altThreshold:
                subItemListControl, altControl = altControl, subItemListControl
            altControl.reset()
        if update:
            subItemListControl.replaceItems(items)
        else:
            subItemListControl.reset()
            subItemListControl.addItems(items)

        if do_focus:
            if selectSeason:
                if current_idx is not None:
                    subItemListControl.setSelectedItemByPos(current_idx)
            elif focus is not None:
                subItemListControl.setSelectedItemByPos(focus)

        return True
