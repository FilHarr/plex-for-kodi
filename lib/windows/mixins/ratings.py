# coding=utf-8
from lib import util


class RatingsMixin(object):
    # Cap on how many of an item's ratings get their own slot (rating1.. - see populateRatings()
    # below). Not a real architectural limit, just a fixed-control-count template can render
    # without a native <list> control - real-world items rarely carry more than 4-5 (IMDb, RT
    # critic, RT audience, TMDB, occasionally one more from a less common agent), so this is
    # generous headroom, not a tight cap expected to actually bite in practice.
    MAX_RATINGS = 6

    # Sort priority for populateRatings()'s multi-source ratings1..N (user's own explicit choice,
    # not a Plex/official-app convention): IMDb, then Rotten Tomatoes critic, then RT audience,
    # then TMDB, then anything else in whatever order the server returned it (Python's sort is
    # stable, so ties - including multiple same-priority "anything else" entries - keep their
    # original relative order rather than being reshuffled).
    @staticmethod
    def _ratingSortKey(r):
        source = str(r.image).split('://', 1)[0]
        if source == 'imdb':
            return 0
        rtype = str(r.type)
        if source == 'rottentomatoes' and rtype == 'critic':
            return 1
        if source == 'rottentomatoes' and rtype == 'audience':
            return 2
        if source == 'themoviedb':
            return 3
        return 4

    def populateRatings(self, video, ref, hide_ratings=False):
        """Ratings display, in two layers:

        rating1.image/rating1 .. rating{MAX_RATINGS}.image/rating{MAX_RATINGS} - every rating the
        item's own <Rating> child-element list carries (video.ratings - Movie/Show/Episode's own
        _setData(), video.py), sorted per _ratingSortKey() above and capped at MAX_RATINGS. This is
        the real, current data - PMS exposes every agent-provided critic/audience score here, not
        just the one it also happens to mirror onto the item's flat rating/audienceRating
        attributes for older-client backward compatibility (confirmed live: a title with an RT
        critic score, an RT audience score, an IMDb score, and a TMDB score, but no flat `rating`
        attribute at all - the old code below couldn't see the RT critic score, or any but one of
        the three audience scores, no matter what).

        The rating/rating.image aliases for the first rating are gone: no template or code read
        them (checked 2026-09-26 across every template and compiled window), and each write is a
        GUI-locked call - per episode tile, while the Episodes window is being drawn (step 4 in the
        navigation review).
        """
        def sanitize(src):
            return src.replace("themoviedb", "tmdb").replace('://', '/')

        def formatValue(r):
            # Rotten Tomatoes' own value is 0-10 like everything else here, but displayed as a
            # percentage (matching this method's own pre-existing convention for the flat
            # rating/audienceRating fields, applied here per-entry instead).
            if str(r.image).split('://', 1)[0] == 'rottentomatoes':
                return '{0}%'.format(int(r.value.asFloat() * 10))
            return r.value

        setProperty = getattr(ref, "setProperty")
        clear_keys = ['rating.stars']
        for i in range(1, self.MAX_RATINGS + 1):
            clear_keys += ['rating{0}'.format(i), 'rating{0}.image'.format(i)]
        getattr(ref, "setProperties")(clear_keys, '')

        if video.userRating:
            stars = str(int(round((video.userRating.asFloat() / 10) * 5)))
            setProperty('rating.stars', stars)

        if hide_ratings:
            return

        if video.TYPE == "movie" and "movies" not in util.getSetting("show_ratings"):
            return

        if (video.TYPE in ("episode", "show", "season") and
                "series" not in util.getSetting("show_ratings")):
            return

        ratings = sorted(getattr(video, 'ratings', None) or [], key=self._ratingSortKey)

        if ratings:
            for i, r in enumerate(ratings[:self.MAX_RATINGS], start=1):
                setProperty('rating{0}'.format(i), formatValue(r))
                setProperty('rating{0}.image'.format(i), 'script.plex/ratings/{0}.png'.format(sanitize(r.image)))
            return

        # Fallback: no <Rating> list at all (older PMS, or an agent that only ever populated the
        # flat fields) - same behavior this method always had.
        audienceRating = video.audienceRating

        if video.rating or audienceRating:
            if video.rating:
                rating = video.rating
                if video.ratingImage.startswith('rottentomatoes:'):
                    rating = '{0}%'.format(int(rating.asFloat() * 10))

                setProperty('rating1', rating)
                if video.ratingImage:
                    setProperty('rating1.image', 'script.plex/ratings/{0}.png'.format(sanitize(video.ratingImage)))
            if audienceRating:
                if video.audienceRatingImage.startswith('rottentomatoes:'):
                    audienceRating = '{0}%'.format(int(audienceRating.asFloat() * 10))
                setProperty('rating2', audienceRating)
                if video.audienceRatingImage:
                    setProperty('rating2.image',
                                'script.plex/ratings/{0}.png'.format(sanitize(video.audienceRatingImage)))
