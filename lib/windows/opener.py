from __future__ import absolute_import

import six
from plexnet import playqueue, plexapp, plexlibrary

from lib import util
from . import busy


def open(obj, context=None, **kwargs):
    """context: the calling window (a UtilMixin instance), threaded through to whichever
    dispatch branch below has been made chain-aware (hashed-orbiting-pizza.md's Phase 4) - lets
    that branch call context.openWindow(...) (swap in place if context is a live chain host,
    else fall back to today's handleOpen()) instead of always calling handleOpen() unconditionally.
    None (the default, used by every caller not passing it) preserves today's behavior exactly.
    Wired for movie/episode/show/artist/season/album/director/actor (Phase 4 items 1-4);
    photo/track/playlist/collection/genre/section branches still ignore this parameter and always
    go through handleOpen()."""
    if isinstance(obj, playqueue.PlayQueue):
        if busy.widthDialog(obj.waitForInitialization, None):
            if obj.type == 'audio':
                from . import musicplayer
                return handleOpen(musicplayer.MusicPlayerWindow, track=obj.current(), playlist=obj)
            elif obj.type == 'photo':
                from . import photos
                return handleOpen(photos.PhotoWindow, play_queue=obj, **kwargs)
            else:
                from . import videoplayer
                videoplayer.play(play_queue=obj, **kwargs)
                return ''
    elif isinstance(obj, six.string_types):
        key = obj
        if not obj.startswith('/'):
            key = '/library/metadata/{0}'.format(obj)

        server = kwargs.pop("server", None) or plexapp.SERVERMANAGER.selectedServer
        return open(server.getObject(key), context=context, **kwargs)
    elif obj.TYPE == 'episode':
        return episodeClicked(obj, context=context, **kwargs)
    elif obj.TYPE == 'movie':
        return playableClicked(obj, context=context, **kwargs)
    elif obj.TYPE in ('show'):
        return showClicked(obj, context=context, **kwargs)
    elif obj.TYPE in ('artist'):
        return artistClicked(obj, context=context, **kwargs)
    elif obj.TYPE in ('season'):
        return seasonClicked(obj, context=context, **kwargs)
    elif obj.TYPE in ('album'):
        return albumClicked(obj, context=context, **kwargs)
    elif obj.TYPE in ('photo',):
        return photoClicked(obj, **kwargs)
    elif obj.TYPE in ('photodirectory'):
        return photoDirectoryClicked(obj, **kwargs)
    elif obj.TYPE in ('track'):
        album = obj.album()
        if album:
            return trackClicked(obj, album=album, **kwargs)
        return trackClicked(obj, **kwargs)
    elif obj.TYPE in ('playlist'):
        return playlistClicked(obj, context=context, **kwargs)
    elif obj.TYPE in ('clip'):
        from . import videoplayer
        return videoplayer.play(video=obj)
    elif obj.TYPE in ('collection'):
        return collectionClicked(obj, **kwargs)
    elif obj.TYPE in ('Genre'):
        return genreClicked(obj, context=context, **kwargs)
    elif obj.TYPE in ('Director'):
        return directorClicked(obj, context=context, **kwargs)
    elif obj.TYPE in ('Role'):
        return actorClicked(obj, context=context, **kwargs)


def handleOpen(winclass, **kwargs):
    w = None
    try:
        # we might just want the play preparation functionality of a window class to directly play an item or playlist
        # if so, we won't actually open the window, just instantiate it, as to not add it to the kodi window history
        autoPlay = kwargs.pop("auto_play", False)
        autoPlayOpen = kwargs.pop("auto_play_open", False)
        if autoPlay and winclass.supportsAutoPlay:
            # create but don't open window
            w = winclass.create(show=False, **kwargs)
            if autoPlayOpen and w.doAutoPlay(blind=not autoPlayOpen):
                # open window after autoPlay to be able to return to it after playback
                w.modal()
            else:
                # just autoPlay and don't open the window
                w.doAutoPlay()
                w.onBlindClose()
        else:
            w = winclass.open(**kwargs)
        return w.exitCommand or ''
    except AttributeError:
        # Same silent-return behavior as before (still falls through to `return ''` below,
        # nothing about control flow changes) - just logged now instead of swallowed with zero
        # trace. Live-confirmed this was actively hiding a real failure (a window silently
        # failing to open, with nothing in kodi.log to explain why) - not touching the other
        # except branches, which already log.
        util.ERROR()
    except util.NoDataException:
        raise
    except:
        util.ERROR()
    finally:
        del w
        util.garbageCollect()

    return ''


def playableClicked(playable, context=None, **kwargs):
    from . import preplay
    if kwargs.get('from_watchlist', False):
        win = preplay.PrePlayWindowWL
    else:
        win = preplay.PrePlayWindow
    if context is not None:
        context.openWindow(win, video=playable, **kwargs)
        return ''
    return handleOpen(win, video=playable, **kwargs)


def episodeClicked(episode, context=None, **kwargs):
    from . import episodes
    if context is not None:
        context.openWindow(episodes.EpisodesWindow, episode=episode, **kwargs)
        return ''
    return handleOpen(episodes.EpisodesWindow, episode=episode, **kwargs)


def showClicked(show, context=None, **kwargs):
    from . import subitems
    if context is not None:
        context.openWindow(subitems.ShowWindow, media_item=show, **kwargs)
        return ''
    return handleOpen(subitems.ShowWindow, media_item=show, **kwargs)


def artistClicked(artist, context=None, **kwargs):
    from . import subitems
    if context is not None:
        context.openWindow(subitems.ArtistWindow, media_item=artist, **kwargs)
        return ''
    return handleOpen(subitems.ArtistWindow, media_item=artist, **kwargs)


def seasonClicked(season, context=None, **kwargs):
    from . import episodes
    if context is not None:
        context.openWindow(episodes.EpisodesWindow, season=season, **kwargs)
        return ''
    return handleOpen(episodes.EpisodesWindow, season=season, **kwargs)


def albumClicked(album, context=None, **kwargs):
    from . import tracks
    if context is not None:
        context.openWindow(tracks.AlbumWindow, album=album, **kwargs)
        return ''
    return handleOpen(tracks.AlbumWindow, album=album, **kwargs)


def photoClicked(photo, **kwargs):
    from . import photos
    return handleOpen(photos.PhotoWindow, photo=photo, **kwargs)


def trackClicked(track, **kwargs):
    from . import musicplayer
    return handleOpen(musicplayer.MusicPlayerWindow, track=track, **kwargs)


def photoDirectoryClicked(photodirectory, **kwargs):
    return sectionClicked(photodirectory, **kwargs)


def playlistClicked(pl, context=None, **kwargs):
    from . import playlist
    if context is not None:
        context.openWindow(playlist.PlaylistWindow, playlist=pl, **kwargs)
        return ''
    return handleOpen(playlist.PlaylistWindow, playlist=pl, **kwargs)


def collectionClicked(collection, **kwargs):
    return sectionClicked(collection, **kwargs)


def sectionClicked(section, filter_=None, context=None, **kwargs):
    from . import library
    if context is not None:
        # hashed-orbiting-pizza.md Phase 4 item 8: reuse the live chain host's own
        # section-rendering in place (LibraryWindow.swapToSection()) instead of always opening a
        # second nested LibraryWindow below - preserves whatever chain (e.g. a hosted
        # PrePlayWindow) this was clicked from, for Back to return to. **kwargs (came_from etc.)
        # deliberately dropped on this path - meaningful only to a freshly-constructed
        # LibraryWindow's own __init__, which this path never calls.
        host = context._liveChainHost()
        if host is not None:
            host.swapToSection(section, filter_=filter_)
            return ''
    library.ITEM_TYPE = section.TYPE
    key = section.key
    if not key or not key.isdigit():
        key = section.getLibrarySectionId()
    viewtype = util.getSetting('viewtype.{0}.{1}'.format(section.server.uuid, key))
    if section.TYPE in ('artist', 'photo', 'photodirectory', 'playlists'):
        default = library.VIEWS_SQUARE.get(viewtype)
        return handleOpen(
            library.LibraryWindow, windows=library.VIEWS_SQUARE.get('all'), default_window=default, section=section, filter_=filter_, **kwargs
        )
    else:
        default = library.VIEWS_POSTER.get(viewtype)
        return handleOpen(
            library.LibraryWindow, windows=library.VIEWS_POSTER.get('all'), default_window=default, section=section, filter_=filter_, **kwargs
        )


def genreClicked(genre, context=None, **kwargs):
    section = plexlibrary.LibrarySection.fromFilter(genre)
    filter_ = {'type': genre.FILTER, 'display': 'Genre', 'sub': {'val': genre.id, 'display': genre.tag}}
    return sectionClicked(section, filter_, context=context, **kwargs)


def directorClicked(director, context=None, **kwargs):
    from . import person as person_window
    if context is not None:
        context.openWindow(person_window.DirectorWindow, role=director, **kwargs)
        return ''
    return handleOpen(person_window.DirectorWindow, role=director, **kwargs)


def actorClicked(actor, context=None, **kwargs):
    from . import person as person_window
    if context is not None:
        context.openWindow(person_window.ActorWindow, role=actor, **kwargs)
        return ''
    return handleOpen(person_window.ActorWindow, role=actor, **kwargs)
