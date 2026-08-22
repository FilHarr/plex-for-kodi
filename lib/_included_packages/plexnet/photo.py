# -*- coding: utf-8 -*-
from __future__ import absolute_import
from . import media
from . import plexobjects
from . import plexmedia


class Photo(media.MediaItem):
    TYPE = 'photo'

    def _setData(self, data):
        self.art = plexobjects.PlexValue('')
        media.MediaItem._setData(self, data)
        # Video._setData()/Collection._setData() both extract this (video.py, plexlibrary.py) -
        # Photo never did, leaving updateBackgroundFrom()'s getattr(ds, 'ultraBlurColors', None)
        # silently None here too, same gap Collection's own fix closed.
        self.ultraBlurColors = self._findUltraBlurColors(data)

        if self.isFullObject():
            self.media = plexobjects.PlexMediaItemList(data, plexmedia.PlexMedia, media.Media.TYPE,
                                                       initpath=self.initpath, server=self.server, media=self)

    def analyze(self):
        """ The primary purpose of media analysis is to gather information about that media
            item. All of the media you add to a Library has properties that are useful to
            know–whether it's a video file, a music track, or one of your photos.
        """
        self.server.query('/%s/analyze' % self.key)

    def markWatched(self):
        path = '/:/scrobble?key=%s&identifier=com.plexapp.plugins.library' % self.ratingKey
        self.server.query(path)
        self.reload()

    def markUnwatched(self):
        path = '/:/unscrobble?key=%s&identifier=com.plexapp.plugins.library' % self.ratingKey
        self.server.query(path)
        self.reload()

    def play(self, client):
        client.playMedia(self)

    def refresh(self):
        self.server.query('%s/refresh' % self.key, method=self.server.session.put)

    def isPhotoOrDirectoryItem(self):
        return True


class PhotoDirectory(media.MediaItem):
    TYPE = 'photodirectory'
    ALLOWED_FILTERS = ()
    ALLOWED_SORT = ()
    DEFAULT_SORT = 'titleSort'
    DEFAULT_SORT_DESC = False

    def _setData(self, data):
        media.MediaItem._setData(self, data)
        # Same gap as Photo just above - never extracted, so a focused photo *folder* always fell
        # back to the flat default panel color instead of a real per-item tint.
        self.ultraBlurColors = self._findUltraBlurColors(data)

    def all(self, *args, **kwargs):
        path = self.key
        return plexobjects.listItems(self.server, path)

    def isPhotoOrDirectoryItem(self):
        return True


@plexobjects.registerLibFactory('photo')
@plexobjects.registerLibFactory('image')
def PhotoFactory(data, initpath=None, server=None, container=None, **kwargs):
    if data.tag == 'Photo':
        return Photo(data, initpath=initpath, server=server, container=container)
    else:
        return PhotoDirectory(data, initpath=initpath, server=server, container=container)
