# coding=utf-8


class MediaInfoPillsMixin(object):
    # Kodi has no way to measure a string's actual rendered pixel width from Python (no
    # Control.getTextWidth() or similar), so the video/audio/subtitles pill backgrounds built by
    # includes/media_info_pills.xml.tpl can't ask Kodi how wide a label will render. A single flat
    # px-per-character estimate was tried first, but a real measurement showed why it couldn't
    # work: video's short, digit/uppercase-heavy strings (e.g. "4K DV P7/HDR") measure ~10.5px/char
    # in font8's actual typeface, while audio/subtitles' longer, lowercase- and punctuation-heavy
    # strings measure ~9.15-9.2px/char - character shapes vary too much for one constant to fit
    # both. FONT8_CHAR_WIDTHS below are the real per-character advance widths read straight out of
    # InterUI.ttf via fontTools (font design units, 2048/em) - the typeface behind font8 in the
    # "Default" skin.plextuary fontset, which lookandfeel.font in guisettings.xml confirms is what's
    # actually active. Covers printable ASCII only; anything outside that (accented language names,
    # etc.) falls back to FONT8_CHAR_WIDTH_FALLBACK, an unweighted average across this same table.
    # If the active Kodi "Skin Fonts" setting ever changes away from "Default", these widths stop
    # matching the real typeface in use and would need re-measuring against whichever font file
    # replaces it.
    FONT8_POINT_SIZE = 18
    FONT8_UNITS_PER_EM = 2048
    FONT8_CHAR_WIDTHS = {
        ' ': 550, '!': 589, '"': 954, '#': 1297, '$': 1314, '%': 2011, '&': 1319, "'": 614,
        '(': 800, ')': 800, '*': 1328, '+': 1328, ',': 550, '-': 1328, '.': 550, '/': 738,
        '0': 1328, '1': 1328, '2': 1328, '3': 1328, '4': 1328, '5': 1328, '6': 1328, '7': 1328,
        '8': 1328, '9': 1328, ':': 550, ';': 550, '<': 1328, '=': 1328, '>': 1328, '?': 1047,
        '@': 1978, 'A': 1413, 'B': 1340, 'C': 1496, 'D': 1478, 'E': 1231, 'F': 1209, 'G': 1528,
        'H': 1522, 'I': 550, 'J': 1169, 'K': 1376, 'L': 1158, 'M': 1850, 'N': 1543, 'O': 1566,
        'P': 1308, 'Q': 1566, 'R': 1318, 'S': 1314, 'T': 1322, 'U': 1524, 'V': 1413, 'W': 2018,
        'X': 1397, 'Y': 1390, 'Z': 1288, '[': 800, ']': 800, '^': 965, '_': 934,
        '`': 661, 'a': 1150, 'b': 1254, 'c': 1170, 'd': 1254, 'e': 1194, 'f': 758, 'g': 1256,
        'h': 1211, 'i': 496, 'j': 496, 'k': 1124, 'l': 496, 'm': 1794, 'n': 1210, 'o': 1228,
        'p': 1254, 'q': 1254, 'r': 771, 's': 1081, 't': 670, 'u': 1211, 'v': 1151, 'w': 1676,
        'x': 1118, 'y': 1151, 'z': 1131, '{': 800, '|': 681, '}': 800, '~': 1328,
    }
    FONT8_CHAR_WIDTH_FALLBACK = sum(FONT8_CHAR_WIDTHS.values()) / len(FONT8_CHAR_WIDTHS)

    PILL_PADDING = 24  # 12px inset either side of the label within its pill
    PILL_MIN_WIDTH = 60
    # reserved space at the front of a pill that has a leading icon (audio, subtitles) instead of
    # the label's usual PILL_PADDING/2 left inset - must stay in sync with the icon <control>'s own
    # posx/width in media_info_pills.xml.tpl
    PILL_ICON_SIZE = 16
    PILL_ICON_LEFT_INSET = 12
    PILL_ICON_TEXT_GAP = 6
    # each pill's own column group shrinks to its actual width, capped at these maximums - must
    # stay in sync with the matching <control type="group"> widths in media_info_pills.xml.tpl
    VIDEO_PILL_MAX_WIDTH = 200
    AUDIO_PILL_MAX_WIDTH = 295
    SUBTITLE_PILL_MAX_WIDTH = 260
    # spacing between pills - used below to derive the row's total max width, the fixed anchor the
    # subtitle pill's right edge pins to (see resizeInfoPill()); episodes.xml.tpl/pre_play.xml.tpl's
    # own posx for this include must stay in sync since they each cancel out this exact total width
    # to hit their own target screen position (see their own comments at the include call)
    PILLS_ITEMGAP = 15
    PILLS_ROW_MAX_WIDTH = VIDEO_PILL_MAX_WIDTH + AUDIO_PILL_MAX_WIDTH + SUBTITLE_PILL_MAX_WIDTH + 2 * PILLS_ITEMGAP

    VIDEO_INFO_IMAGE_ID = 310
    VIDEO_INFO_LABEL_ID = 311
    AUDIO_INFO_IMAGE_ID = 312
    AUDIO_INFO_LABEL_ID = 313
    SUBTITLE_INFO_IMAGE_ID = 314
    SUBTITLE_INFO_LABEL_ID = 315
    SUBTITLE_INFO_ICON_ID = 316
    AUDIO_INFO_ICON_ID = 317
    VIDEO_INFO_GROUP_ID = 320
    AUDIO_INFO_GROUP_ID = 321
    SUBTITLE_INFO_GROUP_ID = 322

    def initMediaInfoPillControls(self):
        self.videoInfoGroup = self.getControl(self.VIDEO_INFO_GROUP_ID)
        self.videoInfoImage = self.getControl(self.VIDEO_INFO_IMAGE_ID)
        self.videoInfoLabel = self.getControl(self.VIDEO_INFO_LABEL_ID)
        self.audioInfoGroup = self.getControl(self.AUDIO_INFO_GROUP_ID)
        self.audioInfoImage = self.getControl(self.AUDIO_INFO_IMAGE_ID)
        self.audioInfoLabel = self.getControl(self.AUDIO_INFO_LABEL_ID)
        self.audioInfoIcon = self.getControl(self.AUDIO_INFO_ICON_ID)
        self.subtitleInfoGroup = self.getControl(self.SUBTITLE_INFO_GROUP_ID)
        self.subtitleInfoImage = self.getControl(self.SUBTITLE_INFO_IMAGE_ID)
        self.subtitleInfoLabel = self.getControl(self.SUBTITLE_INFO_LABEL_ID)
        self.subtitleInfoIcon = self.getControl(self.SUBTITLE_INFO_ICON_ID)

    def measureFont8Width(self, text):
        units = sum(self.FONT8_CHAR_WIDTHS.get(ch, self.FONT8_CHAR_WIDTH_FALLBACK) for ch in (text or ''))
        return units * self.FONT8_POINT_SIZE / self.FONT8_UNITS_PER_EM

    def resizeInfoPill(self, group_ctrl, image_ctrl, label_ctrl, text, max_width, right_edge, icon_ctrl=None):
        right_inset = self.PILL_PADDING // 2
        if icon_ctrl is not None:
            left_inset = self.PILL_ICON_LEFT_INSET + self.PILL_ICON_SIZE + self.PILL_ICON_TEXT_GAP
        else:
            left_inset = self.PILL_PADDING // 2

        width = min(max(left_inset + right_inset + self.measureFont8Width(text), self.PILL_MIN_WIDTH), max_width)
        width = int(round(width))

        group_ctrl.setWidth(width)
        group_ctrl.setPosition(right_edge - width, group_ctrl.getPosition()[1])

        image_ctrl.setWidth(width)
        image_ctrl.setPosition(0, image_ctrl.getPosition()[1])

        if icon_ctrl is not None:
            icon_ctrl.setPosition(self.PILL_ICON_LEFT_INSET, icon_ctrl.getPosition()[1])

        label_ctrl.setWidth(width - left_inset - right_inset)
        label_ctrl.setPosition(left_inset, label_ctrl.getPosition()[1])

    def resizeMediaInfoPills(self, video_text, audio_text, subtitles_text):
        # The row has exactly one true fixed point - PILLS_ROW_MAX_WIDTH, the row's own worst-case
        # total width, which the subtitle pill's right edge always sits flush against. Audio and
        # video then each pin their own right edge to wherever their next-door neighbor actually
        # ended up (not a static constant), so the whole row cascades right-to-left off that one
        # anchor: shrinking any pill closes the gap to its left neighbor instead of leaving it
        # stranded mid-row. An empty (hidden, via <visible> in the template) pill contributes
        # nothing to the cascade, so its neighbor takes over its slot exactly like the grouplist's
        # own native reflow does when a flow item's <visible> goes false.
        right_edge = self.PILLS_ROW_MAX_WIDTH
        self.resizeInfoPill(self.subtitleInfoGroup, self.subtitleInfoImage, self.subtitleInfoLabel,
                             subtitles_text, self.SUBTITLE_PILL_MAX_WIDTH, right_edge,
                             icon_ctrl=self.subtitleInfoIcon)
        if subtitles_text:
            right_edge = self.subtitleInfoGroup.getPosition()[0] - self.PILLS_ITEMGAP

        self.resizeInfoPill(self.audioInfoGroup, self.audioInfoImage, self.audioInfoLabel,
                             audio_text, self.AUDIO_PILL_MAX_WIDTH, right_edge,
                             icon_ctrl=self.audioInfoIcon)
        if audio_text:
            right_edge = self.audioInfoGroup.getPosition()[0] - self.PILLS_ITEMGAP

        self.resizeInfoPill(self.videoInfoGroup, self.videoInfoImage, self.videoInfoLabel,
                             video_text, self.VIDEO_PILL_MAX_WIDTH, right_edge)
