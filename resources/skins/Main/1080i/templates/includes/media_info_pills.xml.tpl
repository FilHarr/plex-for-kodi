{# Video/audio/subtitles "pill" row: each pill's background image and label, and the column group
   wrapping them, are sized and positioned entirely from Python
   (MediaInfoPillsMixin.resizeMediaInfoPills(), called wherever the caller's
   video.res/audio/subtitles info changes) rather than fixed here - Kodi has no way to size a
   background image to a label's rendered width in XML, but Control.setWidth()/setPosition() let
   the addon itself resize a control at runtime (already used elsewhere in this codebase - see
   seekdialog.py's seek bar and selection indicator). Dynamic sizing here still can't measure real
   text width through Kodi's own API - it isn't exposed to XML or Python - so MediaInfoPillsMixin
   measures against real per-character advance widths read from the font file (lib/windows/mixins/
   text_metrics.py) instead of an estimate.

   Laid out horizontally (video/audio/subtitles, left to right) - as a plain group, not a
   grouplist: a grouplist's own native flow only ever leaves its first item's position alone and
   actively recomputes every item after it, every frame, from its own internal offset-accumulation
   - which fought and clobbered Python's own explicit posx writes to the audio/subtitle columns
   (only the video column, item 0, was ever safe from that fight). Each <control type="group">
   below IS a pill's column (not a fixed-width cell it floats within), and Python owns its <width>
   (shrunk to the pill's real rendered width, capped at VIDEO/AUDIO/SUBTITLE_PILL_MAX_WIDTH in the
   mixin so one long audio title can't run the row into the buttons) and its posx outright, with
   nothing else contesting either. resizeMediaInfoPills() positions right-to-left off one fixed
   point - PILLS_ROW_MAX_WIDTH, the row's own worst-case total width - which the subtitle pill's
   right edge always sits flush against; audio then pins its own right edge to subtitles' actual
   resulting left edge minus PILLS_ITEMGAP, and video does the same against audio. Shrinking any
   pill closes the gap to its left neighbor instead of leaving it stranded mid-row, and an empty
   pill (hidden via its own <visible> below) is skipped so its neighbor takes over its slot. The
   <width>/<posx> declared below are just the pre-first-resize default (everything at max width,
   flush against each other), overwritten the moment real data arrives.

   Audio and subtitles have a leading icon (ids 317/316) video doesn't - resizeInfoPill() reserves
   PILL_ICON_LEFT_INSET + PILL_ICON_SIZE + PILL_ICON_TEXT_GAP in front of the label instead of the
   usual PILL_PADDING/2 whenever it's passed an icon_ctrl, so the pill still shrink-wraps correctly
   around icon + text together.

   The ids below (310-317 pill image/label/icon, 320/321/322 the column groups themselves) just
   need to be unique within the including window - MediaInfoPillsMixin.initMediaInfoPillControls()
   looks them up once and reuses those references from then on.

   posx/posy: caller-supplied, where this row sits on the page - the only thing left out of this
   include on purpose. posy is a raw (unscaled) number, scaled internally to match every other
   include in this directory (see pp_meta_row.xml.tpl).

   propref: the info-accessor prefix property values are read through, e.g. "Window.Property" (the
   default - pre_play has a single video, so its info lives on the window) or
   "Container(400).ListItem.Property" (a list's currently-focused item). #}
<control type="group">
    <posx>{{ posx }}</posx>
    <posy>{{ posy|vscale }}</posy>
    <width>789</width>
    <height>{{ vscale(30) }}</height>

    <control type="group" id="320">
        <visible>!String.IsEmpty({{ propref|default("Window.Property") }}(video.res))</visible>
        <posx>0</posx>
        <width>204</width>
        <height>{{ vscale(30) }}</height>
        <control type="image" id="310">
            <width>100</width>
            <height>{{ vscale(30) }}</height>
            <texture border="10" colordiffuse="E60A0F0D">script.plex/white-square-rounded.png</texture>
        </control>
        <control type="label" id="311">
            <posx>12</posx>
            <width>76</width>
            <height>{{ vscale(30) }}</height>
            <font>font8</font>
            <align>center</align>
            <aligny>center</aligny>
            <scroll>true</scroll>
            <scrollspeed>35</scrollspeed>
            <textcolor>DDFFFFFF</textcolor>
            <shadowcolor>66000000</shadowcolor>
            <label>$INFO[{{ propref|default("Window.Property") }}(video.res)]$INFO[{{ propref|default("Window.Property") }}(video.rendering), ]</label>
        </control>
    </control>

    <control type="group" id="321">
        <visible>!String.IsEmpty({{ propref|default("Window.Property") }}(audio))</visible>
        <posx>215</posx>
        <width>295</width>
        <height>{{ vscale(30) }}</height>
        <control type="image" id="312">
            <width>100</width>
            <height>{{ vscale(30) }}</height>
            <texture border="10" colordiffuse="E60A0F0D">script.plex/white-square-rounded.png</texture>
        </control>
        <control type="image" id="317">
            <!-- 12/16/6 (posx/width/PILL_ICON_TEXT_GAP before the label) come from
                 MediaInfoPillsMixin's PILL_ICON_* constants - keep both in sync. -->
            <posx>12</posx>
            <posy>{{ vscale(7) }}</posy>
            <width>16</width>
            <height>{{ vscale(16) }}</height>
            <colordiffuse>DDFFFFFF</colordiffuse>
            <texture>script.plex/media_info_pills/audio.png</texture>
        </control>
        <control type="label" id="313">
            <posx>34</posx>
            <width>60</width>
            <height>{{ vscale(30) }}</height>
            <font>font8</font>
            <align>center</align>
            <aligny>center</aligny>
            <scroll>true</scroll>
            <scrollspeed>35</scrollspeed>
            <textcolor>DDFFFFFF</textcolor>
            <shadowcolor>66000000</shadowcolor>
            <label>$INFO[{{ propref|default("Window.Property") }}(audio)]</label>
        </control>
    </control>

    <control type="group" id="322">
        <visible>!String.IsEmpty({{ propref|default("Window.Property") }}(subtitles))</visible>
        <posx>525</posx>
        <width>260</width>
        <height>{{ vscale(30) }}</height>
        <control type="image" id="314">
            <width>100</width>
            <height>{{ vscale(30) }}</height>
            <texture border="10" colordiffuse="E60A0F0D">script.plex/white-square-rounded.png</texture>
        </control>
        <control type="image" id="316">
            <!-- 12/16/6 (posx/width/PILL_ICON_TEXT_GAP before the label) come from
                 MediaInfoPillsMixin's PILL_ICON_* constants - keep both in sync. -->
            <posx>12</posx>
            <posy>{{ vscale(7) }}</posy>
            <width>16</width>
            <height>{{ vscale(16) }}</height>
            <colordiffuse>DDFFFFFF</colordiffuse>
            <texture>script.plex/media_info_pills/subtitle.png</texture>
        </control>
        <control type="label" id="315">
            <posx>34</posx>
            <width>60</width>
            <height>{{ vscale(30) }}</height>
            <font>font8</font>
            <align>center</align>
            <aligny>center</aligny>
            <scroll>true</scroll>
            <scrollspeed>35</scrollspeed>
            <textcolor>DDFFFFFF</textcolor>
            <shadowcolor>66000000</shadowcolor>
            <label>$INFO[{{ propref|default("Window.Property") }}(subtitles)]</label>
        </control>
    </control>
</control>
