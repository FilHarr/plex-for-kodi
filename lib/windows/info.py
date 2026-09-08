from __future__ import absolute_import

import os
import datetime

from plexnet.video import Episode, Movie, Clip

from kodi_six import xbmcgui

from lib import util
from lib.util import T
from . import kodigui
from lib import seamless_branching


def split2len(s, n):
    def _f(s, n):
        while s:
            yield s[:n]
            s = s[n:]
    return list(_f(s, n))


def formatMediaDetails(video, leading_newlines=0):
    """
    Formats technical media/part/stream details (file/part counts, per-part filename/size/
    duration, per-stream video/audio/subtitle detail, chapters, markers) for a video -
    MediaDetailsDialog's standalone popup (Info button, episodes.py's/preplay.py's button rows - on
    request, since everything else the old full-screen InfoWindow showed there duplicated what's
    already visible on the episode/pre-play screen itself). Returns '' (not None) when there's
    nothing to show, so callers can concatenate/strip freely without a None-check of their own.
    """
    if not isinstance(video, (Episode, Movie, Clip)):
        return ''

    medias = video.media()
    if not medias:
        return ''

    mediaCount = len(medias)
    onlyOneMedia = mediaCount == 1
    partCount = sum(len(m.parts) for m in medias)
    pcInfo = []
    if not onlyOneMedia:
        pcInfo.append("Files: {}".format(mediaCount))
    if partCount > 1:
        pcInfo.append("Parts: {}".format(partCount))
    pcInfoStr = ", ".join(pcInfo)

    addMedia = ["{}Media{}\n".format("\n" * leading_newlines, " ({})".format(pcInfoStr) if pcInfoStr else "")]
    for media_ in medias:
        if not media_.isAccessible():
            addMedia.append("Unavailable: {}\n\n".format(", ".join(os.path.basename(pf.file) for pf in media_.parts)))
            continue

        for part in media_.parts:
            if not part:
                addMedia.append("Unavailable: {}".format(os.path.basename(part.file)))
                continue

            pmFolder = part.getPathMappedUrl(return_only_folder=True)
            addMedia.append("File: ")
            splitFnAt = 74
            fnLen = len(os.path.basename(part.file))
            appended = False
            for s in split2len(os.path.basename(part.file), splitFnAt):
                if fnLen > splitFnAt and not appended:
                    addMedia.append("{}\n".format(s))
                    appended = True
                    continue
                addMedia.append("{}\n".format(s))
            if pmFolder:
                addMedia.append("Mapped via: {}\n".format(pmFolder))
            addMedia.append("Added: {}\n".format(datetime.datetime.fromtimestamp(
                video.addedAt.asFloat()).strftime("{} {}".format(util.shortDF, util.timeFormat))))
            addMedia.append("Duration: {}, Size: {}\n".format(util.durationToShortText(int(part.duration)),
                                                              util.simpleSize(int(part.size))))

            subs = []
            subsOver = 0
            for stream in part.streams:
                streamtype = stream.streamType.asInt()
                # video
                if streamtype == 1:
                    dovi = ""
                    if stream.DOVIPresent:
                        dovi = "Level: {}, Profile: {}, Version: {}, " \
                               "BL: {}{}, EL: {}, RPU: {}".format(stream.DOVILevel,
                                                                  stream.DOVIProfile,
                                                                  stream.DOVIVersion,
                                                                  stream.DOVIBLPresent,
                                                                  stream.DOVIBLPresent and
                                                                  " (compat ID: {})".format(stream.DOVIBLCompatID)
                                                                  or "",
                                                                  stream.DOVIELPresent,
                                                                  stream.DOVIRPUPresent)
                    addMedia.append("Video: {}x{}, {} {}/{}bit/{}/{}@{} kBit, {} fps{}\n".format(
                        stream.width, stream.height, stream.videoCodecRendering, stream.codec.upper(),
                        stream.bitDepth, stream.chromaSubsampling, stream.colorPrimaries, stream.bitrate,
                        stream.frameRate, dovi and "\nDoVi: {}\n".format(dovi) or ""))
                # audio
                elif streamtype == 2:
                    imdb_id = seamless_branching.sbm.get_imdb_id(video)
                    is_sb = (seamless_branching.sbm.is_seamless_branching_movie(imdb_id, stream, force_detection=True)
                             and " (SB!)" or "")
                    addMedia.append("Audio: {}{}, {}/{}ch@{} kBit, {} Hz{}\n".format(
                        stream.language,
                        " (default)" if stream.default else "",
                        stream.codec.upper(),
                        stream.channels, stream.bitrate,
                        stream.samplingRate,
                        is_sb))
                # subtitle
                elif streamtype == 3:
                    if len(subs) > 4:
                        subsOver += 1
                        continue
                    subs.append("{} ({})".format(stream.language, stream.codec.upper()))

            if subs:
                addMedia.append("Subtitles: {}{}\n".format(", ".join(subs),
                                                           subsOver and " (+{})".format(subsOver) or ''))
        if not onlyOneMedia:
            addMedia.append("--------------\n")

    chapters = []
    chOver = 0
    for index, chapter in enumerate(video.chapters):
        if len(chapters) > 4:
            chOver += 1
            continue
        chapters.append(chapter.tag or "Chapter #{}".format(str(index+1)))

    if chapters:
        addMedia.append("Chapters: {}{}\n".format(", ".join(chapters), chOver and " (+{})".format(chOver) or ''))

    if video.markers:
        addMedia.append("Markers: {}".format(", ".join(name for off, name in sorted(
            (int(marker.startTimeOffset), marker.type) for marker in video.markers))))

    return "".join(addMedia)


class MediaDetailsDialog(kodigui.BaseDialog):
    """
    Compact popup (matches VideoSettingsDialog's own shell - playersettings.py) showing just
    formatMediaDetails()'s technical breakdown, in place of InfoWindow's full-screen title/
    thumb/summary/media display - on request, since everything but the media details there
    duplicated what's already visible on the episode screen itself (Info button, episodes.py's/
    preplay.py's button rows). BaseDialog's own default already forwards to Kodi's native
    WindowXMLDialog handling, which closes a dialog on ACTION_NAV_BACK/ACTION_PREVIOUS_MENU without
    anything extra - onAction below only needs to add ACTION_SELECT_ITEM (OK/Enter) on top of that,
    on request.
    """
    xmlFile = 'script-plex-media_details_dialog.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    def __init__(self, *args, **kwargs):
        kodigui.BaseDialog.__init__(self, *args, **kwargs)
        self.video = kwargs.get('video')

    def onAction(self, action):
        if action == xbmcgui.ACTION_SELECT_ITEM:
            self.doClose()
            return
        kodigui.BaseDialog.onAction(self, action)

    def onFirstInit(self):
        self.setProperty('heading', T(35059, 'File info'))
        # lstrip() guards against the video having no media at all, which would otherwise leave
        # the textbox showing a lone leading blank line.
        details = formatMediaDetails(self.video).lstrip('\n')
        self.setProperty('info', details)
        # The textbox itself isn't in Kodi's focus chain - only its scrollbar (id 101) is, and
        # nothing focuses it automatically (no <defaultcontrol> in base.xml.tpl). Without this,
        # up/down never reaches the scrollbar, so long text just sits unscrollable.
        self.setFocusId(101)


def showMediaDetails(video):
    w = MediaDetailsDialog.open(video=video)
    del w
    util.garbageCollect()


class SummaryDialog(kodigui.BaseDialog):
    """
    Title (+ optional subtitle) + summary popup - originally ArtistWindow's own Info popup
    (subitems.py: name + summary is all that button ever showed there, no episode/file/stream
    detail to add, unlike Episodes'/PrePlay's own copy, so there's nothing left to justify a
    full-screen InfoWindow transition for it either), generalized to a shared dialog once
    Seasons'/Episodes'/PrePlay's own summary text got the same click-to-expand treatment (on
    request) - none of them needed anything artist-specific either, just a title and a body of
    text. Episodes is the only caller that populates subtitle (the episode's own name, under the
    show title) - every other caller leaves it empty. Was briefly rendered through
    MediaDetailsDialog's own shared xml file; forked into its own
    (script-plex-artist_info_dialog.xml) once this popup's own size (600x1000, centered) and its
    title/summary needing independently sized fonts diverged from that dialog's own layout - kept
    that filename even once this stopped being artist-specific, rather than a churn-only rename.
    """
    xmlFile = 'script-plex-artist_info_dialog.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    def __init__(self, *args, **kwargs):
        kodigui.BaseDialog.__init__(self, *args, **kwargs)
        self.title = kwargs.get('title')
        self.subtitle = kwargs.get('subtitle')
        self.info = kwargs.get('info')

    def onAction(self, action):
        if action == xbmcgui.ACTION_SELECT_ITEM:
            self.doClose()
            return
        kodigui.BaseDialog.onAction(self, action)

    def onFirstInit(self):
        # Separate title/subtitle/info properties, not one combined "[B]title[/B]\n\nsummary"
        # string (this dialog's own previous shape, sharing MediaDetailsDialog's single-textbox
        # layout) - the template renders these as distinct controls with their own fonts.
        self.setProperty('title', self.title or '')
        self.setProperty('subtitle', self.subtitle or '')
        self.setProperty('info', util.widenParagraphBreaks(self.info) if self.info else '')
        # See MediaDetailsDialog's own onFirstInit() comment - same underlying scrollbar mechanism,
        # same fix needed to make a long summary actually scrollable.
        self.setFocusId(101)


def showSummary(title, info, subtitle=None):
    w = SummaryDialog.open(title=title, subtitle=subtitle, info=info)
    del w
    util.garbageCollect()
