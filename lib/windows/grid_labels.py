# coding=utf-8
"""A "See more" grid tile's caption lines, by its row and its item (spec: ~/.claude/plans/
see-all-grid.md, Labels - the user's rules, 2026-10-08). The rows keep their own captions; these are
the grid's only.

lines(base, item) -> Lines(line1, line2, line3, rating): base is the row's identifier without its
library (hub_limits.baseIdentifier()). A rule's line that has nothing to show falls back to the item
type's own second line, so no tile is left with a blank where a line should be - except the one
deliberate blank: a whole show in Recently Added TV is its name alone."""
from __future__ import absolute_import

import collections
import datetime

from kodi_six import xbmc

from lib import util
from lib.util import T

Lines = collections.namedtuple('Lines', 'line1 line2 line3 rating')

# Rows whose tiles have three lines (the poster grid of three-line height, see_more.py)
THREE_LINE_ROWS = frozenset(('tv.recentlyaired', 'tv.recentlyadded', 'home.television.recent',
                             'tv.recentlyviewed', 'music.recent.added', 'home.music.recent'))
LAST_PLAYED_ROWS = frozenset(('movie.recentlyviewed', 'video.recentlyviewed', 'tv.recentlyviewed',
                              'music.recent.played'))
RECENTLY_ADDED_TV = frozenset(('tv.recentlyadded', 'home.television.recent'))
RECENTLY_ADDED_MUSIC = frozenset(('music.recent.added', 'home.music.recent'))
# Rows ranked by a rating, whose second line is that rating - its source's logo and score - for
# the item type the row ranks (Top Rated TV: the user, 2026-10-08; Top Unwatched Movies, to match
# it: 2026-10-09). The row's own rating, the flat audienceRating: the library's Ratings Source,
# or whatever source Plex fell back to for an item without one (Films' IMDb-less Hobbit edit is
# TMDB 10.0) - so the logo is the score's real source.
RATING_ROWS = {'tv.toprated': 'show', 'movie.topunwatched': 'movie'}

_ENGLISH_MONTHS = ('January', 'February', 'March', 'April', 'May', 'June', 'July', 'August',
                   'September', 'October', 'November', 'December')


def monthName(month):
    """Kodi's own month name in its language (strings 21-32), English if it has none."""
    return xbmc.getLocalizedString(20 + month) or _ENGLISH_MONTHS[month - 1]


def dateText(day):
    """"6 October 2026": no leading zero, the month in Kodi's language."""
    return u'{0} {1} {2}'.format(day.day, monthName(day.month), day.year)


def lastPlayedText(value, today=None):
    """lastViewedAt (epoch seconds) as "Today", "Yesterday", "2 days ago" ... "6 days ago", then the
    date from 7 days on."""
    try:
        played = datetime.date.fromtimestamp(int(value))
    except (TypeError, ValueError):
        return ''
    days = ((today or datetime.date.today()) - played).days
    if days <= 0:
        return T(35172, 'Today')
    if days == 1:
        return T(35173, 'Yesterday')
    if days < 7:
        return T(35174, '{0} days ago').format(days)
    return dateText(played)


def releaseText(value):
    """originallyAvailableAt (YYYY-MM-DD) as dateText()."""
    try:
        return dateText(datetime.datetime.strptime(str(value)[:10], '%Y-%m-%d').date())
    except ValueError:
        return ''


def addedText(value):
    try:
        return dateText(datetime.date.fromtimestamp(int(value)))
    except (TypeError, ValueError):
        return ''


def seasonEpisode(item):
    """"S1 • E2", as the rows show it (LibraryWindow.createEpisodeListItem())."""
    if not item.get('index'):
        return ''
    return u'{0} • {1}'.format(T(32310, 'S').format(item.get('parentIndex')),
                                    T(32311, 'E').format(item.get('index')))


def seasonsOrEpisodes(show):
    """"5 seasons", or "12 episodes" for a show of one season."""
    seasons = show.get('childCount').asInt()
    if seasons == 1 or not seasons:
        episodes = show.get('leafCount').asInt()
        if not episodes:
            return ''
        return (T(35057, '{} episode') if episodes == 1 else T(35056, '{} episodes')).format(episodes)
    return T(34003, '{} seasons').format(seasons)


def _typeDefault(item):
    """The item type's own second line: the fallback for every rule."""
    kind = item.TYPE
    if kind == 'movie' or kind == 'clip':
        return str(item.get('year') or '')
    if kind == 'show':
        return seasonsOrEpisodes(item)
    if kind == 'season':
        return item.get('title') or ''
    if kind == 'episode':
        return seasonEpisode(item)
    if kind == 'album':
        return item.get('title') or ''
    if kind == 'playlist':
        return util.durationToHoursMinutes(item.get('duration') and item.get('duration').asInt())
    if kind == 'photo':
        return releaseText(item.get('originallyAvailableAt'))
    return ''


def _first(item):
    """The first line: a show's or an artist's name for its episodes, seasons, albums; else the
    item's own title."""
    kind = item.TYPE
    if kind == 'episode':
        return item.get('grandparentTitle') or item.get('title') or ''
    if kind in ('season', 'album'):
        return item.get('parentTitle') or item.get('title') or ''
    return item.get('title') or ''


def lines(base, item):
    kind = item.TYPE
    first = _first(item)
    default = _typeDefault(item)
    second = third = ''
    rating = None

    if base in LAST_PLAYED_ROWS:
        played = lastPlayedText(item.get('lastViewedAt'))
        if kind == 'episode':
            second, third = default, played
        else:
            second = played
    elif base == 'tv.recentlyaired' and kind == 'episode':
        second, third = default, releaseText(item.get('originallyAvailableAt'))
    elif base in RECENTLY_ADDED_TV:
        if kind == 'episode':
            second, third = default, item.get('title') or ''
        elif kind == 'show':
            # a whole show added at once: its name alone, on request (2026-10-09)
            return Lines(first, '', '', None)
        else:
            second = default
    elif base in RECENTLY_ADDED_MUSIC and kind == 'album':
        second, third = item.get('title') or '', addedText(item.get('addedAt'))
    elif RATING_ROWS.get(base) == kind and item.get('audienceRating'):
        # always shown here, whatever "Show ratings for" says (the user, 2026-10-08)
        rating = audienceRating(item)
        second = ''
    elif kind == 'artist':
        return Lines(first, '', '', None)
    elif kind == 'collection':
        return Lines(first, '', '', None)
    else:
        second = default

    if not second and rating is None:
        second = default
    return Lines(first, second, third, rating)


def audienceRating(item):
    """(logo, score) of the item's flat audience rating. A Rotten Tomatoes score as a percentage
    (8.6 -> 86%), as pre-play shows it (RatingsMixin.populateRatings())."""
    source = str(item.get('audienceRatingImage') or '')
    value = item.get('audienceRating')
    if source.startswith('rottentomatoes'):
        text = '{0}%'.format(int(value.asFloat() * 10))
    else:
        text = str(value)
    return ratingImage(source), text


def ratingImage(source):
    """themoviedb://image.rating -> script.plex/ratings/tmdb/image.rating.png, as pre-play draws
    it (RatingsMixin.populateRatings())."""
    source = str(source or '')
    if not source:
        return ''
    return 'script.plex/ratings/{0}.png'.format(source.replace('themoviedb', 'tmdb').replace('://', '/'))
