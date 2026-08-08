{# Video/audio/subtitles "pill" row: each pill's background image and label are sized and
   positioned entirely from Python (MediaInfoPillsMixin.resizeInfoPill(), called wherever the
   caller's video.res/audio/subtitles info changes) rather than fixed here - Kodi has no way to
   size a background image to a label's rendered width in XML, but Control.setWidth()/
   setPosition() let the addon itself resize a control at runtime (already used elsewhere in this
   codebase - see seekdialog.py's seek bar and selection indicator). Dynamic sizing here still
   can't measure real text width through Kodi's own API - it isn't exposed to XML or Python - so
   MediaInfoPillsMixin measures against real per-character advance widths read from InterUI.ttf
   instead of an estimate. Laid out horizontally (video/audio/subtitles, left to right), each in its
   own fixed-width column - 200/295/260, VIDEO/AUDIO/SUBTITLE_PILL_MAX_WIDTH in the mixin, and the
   <width> on each <control type="group"> below - the two must stay in sync, since the Python side
   centers each pill within max_width (x = (max_width - pill_width) / 2). The ids below (310-315)
   just need to be unique within the including window -
   MediaInfoPillsMixin.initMediaInfoPillControls() looks them up once and reuses those references
   from then on.

   posx/posy: caller-supplied, where this row sits on the page - the only thing left out of this
   include on purpose. posy is a raw (unscaled) number, scaled internally to match every other
   include in this directory (see pp_meta_row.xml.tpl).

   propref: the info-accessor prefix property values are read through, e.g. "Window.Property" (the
   default - pre_play has a single video, so its info lives on the window) or
   "Container(400).ListItem.Property" (a list's currently-focused item). #}
<control type="grouplist">
    <posx>{{ posx }}</posx>
    <posy>{{ posy|vscale }}</posy>
    <width>765</width>
    <height>{{ vscale(30) }}</height>
    <orientation>horizontal</orientation>
    <itemgap>5</itemgap>
    <usecontrolcoords>true</usecontrolcoords>

    <control type="group">
        <visible>!String.IsEmpty({{ propref|default("Window.Property") }}(video.res))</visible>
        <width>200</width>
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
            <align>left</align>
            <aligny>center</aligny>
            <scroll>true</scroll>
            <scrollspeed>35</scrollspeed>
            <textcolor>DDFFFFFF</textcolor>
            <shadowcolor>66000000</shadowcolor>
            <label>$INFO[{{ propref|default("Window.Property") }}(video.res)]$INFO[{{ propref|default("Window.Property") }}(video.rendering), ]</label>
        </control>
    </control>

    <control type="group">
        <visible>!String.IsEmpty({{ propref|default("Window.Property") }}(audio))</visible>
        <width>295</width>
        <height>{{ vscale(30) }}</height>
        <control type="image" id="312">
            <width>100</width>
            <height>{{ vscale(30) }}</height>
            <texture border="10" colordiffuse="E60A0F0D">script.plex/white-square-rounded.png</texture>
        </control>
        <control type="label" id="313">
            <posx>12</posx>
            <width>76</width>
            <height>{{ vscale(30) }}</height>
            <font>font8</font>
            <align>left</align>
            <aligny>center</aligny>
            <scroll>true</scroll>
            <scrollspeed>35</scrollspeed>
            <textcolor>DDFFFFFF</textcolor>
            <shadowcolor>66000000</shadowcolor>
            <label>$INFO[{{ propref|default("Window.Property") }}(audio)]</label>
        </control>
    </control>

    <control type="group">
        <visible>!String.IsEmpty({{ propref|default("Window.Property") }}(subtitles))</visible>
        <width>260</width>
        <height>{{ vscale(30) }}</height>
        <control type="image" id="314">
            <width>100</width>
            <height>{{ vscale(30) }}</height>
            <texture border="10" colordiffuse="E60A0F0D">script.plex/white-square-rounded.png</texture>
        </control>
        <control type="label" id="315">
            <posx>12</posx>
            <width>76</width>
            <height>{{ vscale(30) }}</height>
            <font>font8</font>
            <align>left</align>
            <aligny>center</aligny>
            <scroll>true</scroll>
            <scrollspeed>35</scrollspeed>
            <textcolor>DDFFFFFF</textcolor>
            <shadowcolor>66000000</shadowcolor>
            <label>$INFO[{{ propref|default("Window.Property") }}(subtitles)]</label>
        </control>
    </control>
</control>
