# -*- coding: utf-8 -*-
from __future__ import absolute_import
from . import plexobjects
from . import plexmedia
from . import media


class Audio(media.MediaItem):
    def __init__(self, *args, **kwargs):
        self._settings = None
        media.MediaItem.__init__(self, *args, **kwargs)

    def _setData(self, data):
        for k, v in data.attrib.items():
            setattr(self, k, plexobjects.PlexValue(v, self))

        self.key = plexobjects.PlexValue(self.key.replace('/children', ''), self)
        # Video._setData()/Collection._setData() both extract this (video.py, plexlibrary.py) -
        # Audio never picked it up since it doesn't call through media.MediaItem._setData() (the
        # attrib loop above is a separate, parallel implementation, not a super() call) - without
        # this, updateBackgroundFrom()'s getattr(ds, 'ultraBlurColors', None) always silently
        # returned None for Artist/Album/Track, falling back to the flat default panel color
        # instead of a real per-item tint, same gap Collection's own fix (plexlibrary.py) closed.
        self.ultraBlurColors = self._findUltraBlurColors(data)

    def isMusicItem(self):
        return True


@plexobjects.registerLibType
class Artist(Audio, media.RelatedMixin):
    TYPE = 'artist'

    # otherAlbums hub identifiers, kept apart rather than merged into one list (as a single
    # otherAlbums list used to) so ArtistWindow can render each type as its own row (on request),
    # not everything dumped into one row sorted by year - a Live Album and a studio album from the
    # same year used to sit side by side there, indistinguishable. Order matches the album-row
    # ordering in script-plex-artist.xml.tpl (grouplist 600).
    OTHER_ALBUM_HUBS = (
        ("liveAlbums", "artist.albums.live"),
        ("compilationAlbums", "artist.albums.compilation"),
        ("singleAlbums", "artist.albums.singles"),
        ("soundtrackAlbums", "artist.albums.soundtrack"),
        ("demoAlbums", "artist.albums.demo"),
        ("remixAlbums", "artist.albums.remix"),
    )

    def _setData(self, data):
        Audio._setData(self, data)
        for attr, _hub_id in self.OTHER_ALBUM_HUBS:
            setattr(self, attr, [])
        # <PopularLeaves> is a sibling of <Related>, not a hub inside it - relatedHubs() (media.py)
        # can't reach it. Only present when the request carried includePopularLeaves=1 (see
        # ArtistWindow.fill(), subitems.py); absent otherwise, so PlexItemList's own data=None
        # handling (empty list) covers that case for free.
        self.popularTracks = []
        if self.isFullObject():
            self.countries = plexobjects.PlexItemList(data, media.Country, media.Country.TYPE, server=self.server)
            self.genres = plexobjects.PlexItemList(data, media.Genre, media.Genre.TYPE, server=self.server)
            self.similar = plexobjects.PlexItemList(data, media.Similar, media.Similar.TYPE, server=self.server)
            for attr, hub_id in self.OTHER_ALBUM_HUBS:
                setattr(self, attr, self.relatedHubs(data, Album, hub_id))
            self.popularTracks = plexobjects.PlexItemList(data.find("PopularLeaves"), Track, "Track",
                                                          server=self.server)

    def albums(self):
        path = '%s/children' % self.key
        return plexobjects.listItems(self.server, path, Album.TYPE)

    def album(self, title):
        path = '%s/children' % self.key
        return plexobjects.findItem(self.server, path, title)

    def tracks(self, watched=None):
        leavesKey = '/library/metadata/%s/allLeaves' % self.ratingKey
        return plexobjects.listItems(self.server, leavesKey, watched=watched)

    def all(self, *args, **kwargs):
        return self.tracks()

    def track(self, title):
        path = '/library/metadata/%s/allLeaves' % self.ratingKey
        return plexobjects.findItem(self.server, path, title)

    def isFullObject(self):
        # plex bug? http://bit.ly/1Sc2J3V
        fixed_key = self.key.replace('/children', '')
        return self.initpath == fixed_key

    def refresh(self):
        self.server.query('/library/metadata/%s/refresh' % self.ratingKey)


@plexobjects.registerLibType
class Album(Audio):
    TYPE = 'album'

    def _setData(self, data):
        Audio._setData(self, data)
        if self.isFullObject():
            self.genres = plexobjects.PlexItemList(data, media.Genre, media.Genre.TYPE, server=self.server)

    @property
    def defaultTitle(self):
        return self.parentTitle or self.title

    def tracks(self, watched=None):
        path = '%s/children' % self.key
        return plexobjects.listItems(self.server, path, watched=watched)

    def track(self, title):
        path = '%s/children' % self.key
        return plexobjects.findItem(self.server, path, title)

    def all(self, *args, **kwargs):
        return self.tracks()

    def isFullObject(self):
        # plex bug? http://bit.ly/1Sc2J3V
        fixed_key = self.key.replace('/children', '')
        return self.initpath == fixed_key

    def artist(self):
        return plexobjects.listItems(self.server, self.parentKey)[0]

    def watched(self):
        return self.tracks(watched=True)

    def unwatched(self):
        return self.tracks(watched=False)


@plexobjects.registerLibType
class Track(Audio):
    TYPE = 'track'

    def _setData(self, data):
        Audio._setData(self, data)
        if self.isFullObject():
            self.moods = plexobjects.PlexItemList(data, media.Mood, media.Mood.TYPE, server=self.server)
            self.media = plexobjects.PlexMediaItemList(data, plexmedia.PlexMedia, media.Media.TYPE, initpath=self.initpath, server=self.server, media=self)

        # data for active sessions
        self.user = self._findUser(data)
        self.player = self._findPlayer(data)
        self.transcodeSession = self._findTranscodeSession(data)

    @property
    def defaultTitle(self):
        return self.parentTitle or self.title

    @property
    def settings(self):
        if not self._settings:
            from . import plexapp
            self._settings = plexapp.PlayerSettingsInterface()

        return self._settings

    @property
    def thumbUrl(self):
        return self.server.url(self.parentThumb)

    def album(self):
        return plexobjects.listItems(self.server, self.parentKey)[0]

    def artist(self):
        return plexobjects.listItems(self.server, self.grandparentKey)[0]

    def getStreamURL(self, **params):
        return self._getStreamURL(**params)

    @property
    def defaultThumb(self):
        return self.__dict__.get('thumb') or self.__dict__.get('parentThumb') or self.get('grandparentThumb')

    @property
    def defaultArt(self):
        return self.__dict__.get('art') or self.get('grandparentArt')
