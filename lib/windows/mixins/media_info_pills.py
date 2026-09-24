# coding=utf-8

from .text_metrics import FONT8_POINT_SIZE, measureTextWidth


class MediaInfoPillsMixin(object):
    # The pill backgrounds built by includes/media_info_pills.xml.tpl have to be sized to fit their
    # own labels, which means estimating rendered text width - see text_metrics.py for why that's
    # an estimate and how the per-character widths were obtained. A single flat px-per-character
    # constant was tried first and couldn't work: video's short, digit/uppercase-heavy strings
    # (e.g. "4K DV P7/HDR") measure ~10.5px/char in font8's actual typeface while audio/subtitles'
    # longer, lowercase-heavy ones measure ~9.15-9.2px/char.

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
        return measureTextWidth(text, FONT8_POINT_SIZE)

    def resizeInfoPill(self, group_ctrl, image_ctrl, label_ctrl, text, max_width, right_edge, icon_ctrl=None):
        right_inset = self.PILL_PADDING // 2
        if icon_ctrl is not None:
            left_inset = self.PILL_ICON_LEFT_INSET + self.PILL_ICON_SIZE + self.PILL_ICON_TEXT_GAP
        else:
            left_inset = self.PILL_PADDING // 2

        # +2: small margin on top of the measured text width itself (not the insets). Added when the
        # measurement summed exact advances and text landed a couple px tighter than that; the
        # measurement now rounds per glyph at the screen's render size the way Kodi does (see
        # text_metrics.measureTextWidth()), and the margin stays for what it still doesn't model.
        width = min(max(left_inset + right_inset + self.measureFont8Width(text) + 2, self.PILL_MIN_WIDTH), max_width)
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
