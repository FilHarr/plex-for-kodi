from __future__ import absolute_import

import six
from plexnet import playqueue, plexapp, plexlibrary

from lib import util
from . import busy


def open(obj, context=None, **kwargs):
    """context: the calling window (a UtilMixin instance), threaded through to whichever
    dispatch branch below has been made chain-aware (hashed-orbiting-pizza.md's Phase 4, plus
    follow-up passes) - lets that branch call context.openWindow(...) (swap in place if context is
    a live chain host, else fall back to today's handleOpen()) instead of always calling
    handleOpen() unconditionally. None (the default, used by every caller not passing it)
    preserves today's behavior exactly.

    Every branch is context-aware now except photo/track/clip - those three deliberately stay on
    handleOpen() always: PhotoWindow/MusicPlayerWindow/VideoPlayerWindow are chrome-only
    player/viewer windows, not library screens, out of this plan's scope (see
    hashed-orbiting-pizza.md's "Current state")."""
    if isinstance(obj, playqueue.PlayQueue):
        # delay=True: the spinner only appears if the server is actually slow to hand back the
        # queue. Without it BusyWindow is shown the instant this is called, which put a spinner on
        # screen for every track click once music started going through play queues.
        if busy.widthDialog(obj.waitForInitialization, None, delay=True):
            if obj.type == 'audio':
                from . import musicplayer
                # **kwargs, as the photo branch below already does: track clicks route through
                # here now (trackClicked), and they carry the same dialog_props/window_props
                # carry-over every other opener branch passes on. handleOpen() pops the auto_play
                # pair, so library.py's Play All still works the same way.
                return handleOpen(musicplayer.MusicPlayerWindow, track=obj.current(), playlist=obj, **kwargs)
            elif obj.type == 'photo':
                from . import photos
                return handleOpen(photos.PhotoWindow, play_queue=obj, **kwargs)
            else:
                from . import videoplayer
                videoplayer.play(play_queue=obj, context=context, **kwargs)
                return ''
    elif isinstance(obj, six.string_types):
        key = obj
        if not obj.startswith('/'):
            key = '/library/metadata/{0}'.format(obj)

        # the key's own server: two servers can have the same key
        server = kwargs.pop("server")
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
        return photoDirectoryClicked(obj, context=context, **kwargs)
    elif obj.TYPE in ('track'):
        # No obj.album() lookup any more: createPlayQueueForItem() derives the album from the
        # track's own parentRatingKey (playqueue.py's track branch), so that round trip bought
        # nothing.
        return trackClicked(obj, **kwargs)
    elif obj.TYPE in ('playlist'):
        return playlistClicked(obj, context=context, **kwargs)
    elif obj.TYPE in ('clip'):
        from . import videoplayer
        return videoplayer.play(video=obj, context=context)
    elif obj.TYPE in ('collection'):
        return collectionClicked(obj, context=context, **kwargs)
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
        if w is not None:
            ref = util.windowRef(w)
            del w
            util.collectIfAlive(ref)

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

    # skipChildren (set on the Show - the "Seasons" library option set to Hide for single-season
    # shows, see episodes.py's own EpisodesWindow.reset() comment for how that's detected/verified
    # live) means this show's single season isn't a meaningful level of its own - Plex's own apps
    # skip the season-selection screen entirely for it, going straight to the episode list. Ported
    # here, opener.open()'s single show-click funnel, so every entry point (library grid, hubs,
    # watchlist, search, related rows) gets that behavior, not just Continue Watching's episode-level
    # clicks (which already bypass ShowWindow by construction - they open EpisodesWindow directly
    # with an episode, never a show, so there's nothing to change there).
    try:
        skip_children = show.get('skipChildren').asBool()
    except AttributeError:
        # Not a real PlexObject (e.g. a test double) - every genuine Show has .get(), so this only
        # ever means "can't be a skipChildren show".
        skip_children = False

    if skip_children:
        # No busy.widthDialog() wrapper here (deliberately): that creates/shows/closes a real,
        # separate native BusyWindow synchronously - a plausible contributor to an intermittent
        # unresponsive-black-screen hang on Back, but live-confirmed NOT the actual cause (removing
        # it alone didn't stop the hang). The seasons fetch is small (~1KB) - not worth a spinner
        # regardless.
        try:
            seasons = show.seasons()
        except:
            seasons = None
        if seasons:
            # Straight to the season. With a chain host, openWindow() posts the swap
            # (MultiWindow.postNav()), so it runs after this click, from the view's wait loop. A
            # standalone context used to open it 0.15 s later from a threading.Timer (the #27239
            # note in windowutils.py), a blocking open on that timer's thread: a window driven from
            # a second thread (S1 in the navigation review). It now opens on this thread, as every
            # other open from a standalone window does.
            return seasonClicked(seasons[0], context=context, **kwargs)

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


def trackClicked(track, container_path=None, **kwargs):
    """Play a track, as a Plex client does: a server play queue of the container it belongs to,
    starting at the track.

    Every track click lands here - the album screen's track list, the music library's Tracks list
    view, a home hub, a search result - and they all queue the track's own album, so they all read
    the same way whichever screen you came from. container_path overrides that for callers with a
    different listable container in hand (ArtistWindow's popular-tracks row, subitems.py).

    Falls back to playing the single track on its own if the server won't give us a queue (a
    secondary server, or an item that isn't a library item - see
    PlayQueueFactory.canCreateRemotePlayQueue).
    """
    pq = playqueue.createPlayQueueForItem(track, options={'containerPath': container_path})
    if pq:
        return open(pq, **kwargs)

    util.DEBUG_LOG('trackClicked: no play queue for {}, playing the track alone', track)
    from . import musicplayer
    return handleOpen(musicplayer.MusicPlayerWindow, track=track, **kwargs)


def photoDirectoryClicked(photodirectory, context=None, **kwargs):
    return sectionClicked(photodirectory, context=context, **kwargs)


def playlistClicked(pl, context=None, **kwargs):
    from . import playlist
    if context is not None:
        context.openWindow(playlist.PlaylistWindow, playlist=pl, **kwargs)
        return ''
    return handleOpen(playlist.PlaylistWindow, playlist=pl, **kwargs)


def collectionClicked(collection, context=None, **kwargs):
    """A collection's grid (collection.CollectionWindow), as the Collections tab opens it
    (library_grid). It went through sectionClicked(), which showed it as a library - the
    library's Recommended rows asked for at the collection's key, 404 (live, 2026-10-07, from
    Search; a Recommended row's collection went the same way)."""
    from . import collection as collection_
    if context is not None:
        context.openWindow(collection_.CollectionWindow, collection=collection, **kwargs)
        return ''
    return handleOpen(collection_.CollectionWindow, collection=collection, **kwargs)


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
