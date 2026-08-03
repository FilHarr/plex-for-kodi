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
    # each pill centers within a column this wide (VIDEO/AUDIO/SUBTITLE_PILL_MAX_WIDTH) - these must
    # stay in sync with the matching <control type="group"> widths in media_info_pills.xml.tpl
    VIDEO_PILL_MAX_WIDTH = 200
    AUDIO_PILL_MAX_WIDTH = 295
    SUBTITLE_PILL_MAX_WIDTH = 260

    VIDEO_INFO_IMAGE_ID = 310
    VIDEO_INFO_LABEL_ID = 311
    AUDIO_INFO_IMAGE_ID = 312
    AUDIO_INFO_LABEL_ID = 313
    SUBTITLE_INFO_IMAGE_ID = 314
    SUBTITLE_INFO_LABEL_ID = 315

    def initMediaInfoPillControls(self):
        self.videoInfoImage = self.getControl(self.VIDEO_INFO_IMAGE_ID)
        self.videoInfoLabel = self.getControl(self.VIDEO_INFO_LABEL_ID)
        self.audioInfoImage = self.getControl(self.AUDIO_INFO_IMAGE_ID)
        self.audioInfoLabel = self.getControl(self.AUDIO_INFO_LABEL_ID)
        self.subtitleInfoImage = self.getControl(self.SUBTITLE_INFO_IMAGE_ID)
        self.subtitleInfoLabel = self.getControl(self.SUBTITLE_INFO_LABEL_ID)

    def measureFont8Width(self, text):
        units = sum(self.FONT8_CHAR_WIDTHS.get(ch, self.FONT8_CHAR_WIDTH_FALLBACK) for ch in (text or ''))
        return units * self.FONT8_POINT_SIZE / self.FONT8_UNITS_PER_EM

    def resizeInfoPill(self, image_ctrl, label_ctrl, text, max_width):
        width = min(max(self.PILL_PADDING + self.measureFont8Width(text), self.PILL_MIN_WIDTH), max_width)
        width = int(round(width))
        x = (max_width - width) // 2

        image_ctrl.setWidth(width)
        image_ctrl.setPosition(x, image_ctrl.getPosition()[1])

        label_ctrl.setWidth(width - self.PILL_PADDING)
        label_ctrl.setPosition(x + self.PILL_PADDING // 2, label_ctrl.getPosition()[1])
