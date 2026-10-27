{% extends "base.xml.tpl" %}
{% block window_animation %}{% include "includes/dialog_close_fade.xml.tpl" %}{% endblock %}
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
<!-- The More settings dialog's box (includes/settings_card_frame.xml.tpl, playersettings.py): 640x876 from
     (1270, 103), its right edge 10 from the screen's, the shadow 40 past it all round, one F2111111 colour
     across it. The text 25 in, 20 clear above and below; the scrollbar where the pickers' is, 4 in from its right edge. -->
<!-- The full-screen dim behind it: 30% black, as the settings and pickers' (includes/option_card_frame.xml.tpl) -->
<control type="image">
    <posx>0</posx>
    <posy>0</posy>
    <width>1920</width>
    <height>1080</height>
    <texture>script.plex/white-square.png</texture>
    <colordiffuse>4D000000</colordiffuse>
</control>
<control type="group">
    <posx>1270</posx>
    <posy>{{ vscale(103) }}</posy>
    <control type="image">
        <posx>-40</posx>
        <posy>{{ vscale(-40) }}</posy>
        <width>720</width>
        <height>{{ vscale(956) }}</height>
        <texture border="42">script.plex/drop-shadow.png</texture>
    </control>
    <control type="image">
        <posx>0</posx>
        <posy>0</posy>
        <width>640</width>
        <height>{{ vscale(876) }}</height>
        <texture border="10">script.plex/white-square-rounded.png</texture>
        <colordiffuse>F2111111</colordiffuse>
    </control>
    <!-- Title: "File info" (MediaDetailsDialog's heading), the settings and pickers' heading
         (includes/option_card_frame.xml.tpl) - font25_title, FFEEEEEE, centred in the panel's top 66 - and
         the text from that 66's foot, as the settings' rows start (and the Summary dialog's, under its title). -->
    <control type="label">
        <posx>40</posx>
        <posy>0</posy>
        <width>560</width>
        <height>{{ vscale(66) }}</height>
        <font>font25_title</font>
        <align>center</align>
        <aligny>center</aligny>
        <textcolor>FFEEEEEE</textcolor>
        <scroll>true</scroll>
        <scrollspeed>15</scrollspeed>
        <label>$INFO[Window.Property(heading)]</label>
    </control>
    <control type="textbox">
        <posx>25</posx>
        <posy>{{ vscale(66) }}</posy>
        <pagecontrol>101</pagecontrol>
        <width>590</width>
        <height>{{ vscale(790) }}</height>
        <font>font10</font>
        <align>left</align>
        <textcolor>FFDDDDDD</textcolor>
        <label>$INFO[Window.Property(info)]</label>
    </control>
</control>
<!-- The Summary dialog's scrollbar (script-plex-artist_info_dialog.xml.tpl): 12 wide, rounded, a 40000000
     track and a 77FFFFFF bar, focused too - it always has the focus (onFirstInit(), info.py), so its focused
     bar is the only one seen; was 10 wide, square, and orange. Where the pickers' sits: 1894-1906, 4 in from the panel's right edge. -->
<control type="scrollbar" id="101">
    <hitrect x="1890" y="169" w="50" h="790" />
    <left>1894</left>
    <top>{{ vscale(169) }}</top>
    <width>12</width>
    <height>{{ vscale(790) }}</height>
    <onleft>noop</onleft>
    <visible>true</visible>
    <texturesliderbackground colordiffuse="40000000" border="5">script.plex/white-square-rounded.png</texturesliderbackground>
    <texturesliderbar colordiffuse="77FFFFFF" border="5">script.plex/white-square-rounded.png</texturesliderbar>
    <texturesliderbarfocus colordiffuse="77FFFFFF" border="5">script.plex/white-square-rounded.png</texturesliderbarfocus>
    <textureslidernib>-</textureslidernib>
    <textureslidernibfocus>-</textureslidernibfocus>
    <pulseonselect>false</pulseonselect>
    <orientation>vertical</orientation>
    <showonepage>false</showonepage>
</control>
{% endblock controls %}
