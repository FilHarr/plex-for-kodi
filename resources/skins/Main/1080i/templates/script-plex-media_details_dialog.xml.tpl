{% extends "base.xml.tpl" %}
{% block backgroundcolor %}{% endblock %}
{% block controls %}
<!-- Compact popup shell copied from script-plex-video_settings_dialog.xml.tpl (playersettings.py's
     own "Settings" popup) - same drop-shadow/rounded-rect panel, on request (Info button,
     episodes.py's/preplay.py's button rows, should look like the same kind of popup as Settings/More
     rather than opening the old full-screen InfoWindow). No title bar (dropped from both this and
     Settings' own copy, on request) - just the one panel layer, content starting near the top
     instead of below a header band. The list control there is swapped for a textbox+scrollbar
     instead (script-plex-info.xml.tpl's own pattern for its "info" property) since this shows one
     block of wrapped text, not a list of selectable rows. No player-OSD visibility guards
     (sliderdialog/osdvideosettings/etc, unlike Settings' own copy) - this dialog is only ever opened
     from a button row, never from the video-playback OSD. Only MediaDetailsDialog (info.py) renders
     through this file - SummaryDialog briefly shared it too (as ArtistInfoDialog, before it was
     generalized past just Artist) but was forked into its own
     (script-plex-artist_info_dialog.xml.tpl) once its size/font needs diverged; see that file's own
     comment for the reasoning, and info.py's own comment for why sharing one xml file across
     distinct window classes is fine in Kodi/this codebase in the first place. -->
<control type="group">
    <posx>460</posx>
    <posy>{{ vperc(vscale(600)) }}</posy>
    <control type="image">
        <posx>-40</posx>
        <posy>{{ vscale(-40) }}</posy>
        <width>1080</width>
        <height>{{ vscale(770) }}</height>
        <texture border="42">script.plex/drop-shadow.png</texture>
    </control>
    <!-- white-square-rounded.png (all 4 corners), not white-square-top-rounded.png+flipy (rounded
         top corners flipped to the bottom, leaving the top square) - top corners now curve too, on
         request, matching the bottom. Same fix as Settings' own copy of this shell. -->
    <control type="image">
        <posx>0</posx>
        <posy>0</posy>
        <width>1000</width>
        <height>{{ vscale(690) }}</height>
        <texture border="10">script.plex/white-square-rounded.png</texture>
        <colordiffuse>D3111111</colordiffuse>
    </control>
    <!-- white-square-left-rounded.png (both LEFT corners, right edge square) - see Settings' own
         copy's comment for why not the fully-rounded asset here (this layer is only 400 wide). -->
    <control type="image">
        <posx>0</posx>
        <posy>0</posy>
        <width>400</width>
        <height>{{ vscale(690) }}</height>
        <texture border="12">script.plex/white-square-left-rounded.png</texture>
        <colordiffuse>30000000</colordiffuse>
    </control>
    <control type="textbox">
        <posx>25</posx>
        <posy>{{ vscale(20) }}</posy>
        <pagecontrol>101</pagecontrol>
        <width>950</width>
        <height>{{ vscale(650) }}</height>
        <font>font10</font>
        <align>left</align>
        <textcolor>FFDDDDDD</textcolor>
        <label>$INFO[Window.Property(info)]</label>
    </control>
</control>
<control type="scrollbar" id="101">
    <hitrect x="1408" y="33" w="90" h="734" />
    <left>1450</left>
    <top>{{ vperc(vscale(600)) + vscale(20) }}</top>
    <width>10</width>
    <height>{{ vscale(650) }}</height>
    <onleft>noop</onleft>
    <visible>true</visible>
    <texturesliderbackground colordiffuse="30000000" border="5">script.plex/white-square.png</texturesliderbackground>
    <texturesliderbar colordiffuse="33FFFFFF" border="5">script.plex/white-square.png</texturesliderbar>
    <texturesliderbarfocus colordiffuse="FFE5A00D" border="5">script.plex/white-square.png</texturesliderbarfocus>
    <textureslidernib>-</textureslidernib>
    <textureslidernibfocus>-</textureslidernibfocus>
    <pulseonselect>false</pulseonselect>
    <orientation>vertical</orientation>
    <showonepage>false</showonepage>
</control>
{% endblock controls %}
