{% extends "base.xml.tpl" %}
{% block backgroundcolor %}{% endblock %}
{% block controls %}
<!-- SummaryDialog's own popup (info.py) - originally ArtistWindow's Info popup, now shared by
     Seasons/Episodes/PrePlay's own summary-textbox click-targets too (on request) - forked off
     script-plex-media_details_dialog.xml.tpl once this screen's own sizing (then 600x1000, centered) and
     its separate title/summary font treatment diverged from that dialog's own technical-file-info
     layout. Same drop-shadow/rounded-rect panel shell/scrollbar mechanism as that dialog (and
     Settings' own "Settings" popup, playersettings.py, which they both originally copied) - see
     that file's own comment for the shell's general reasoning.

     The More settings dialog's box (includes/settings_card_frame.xml.tpl, playersettings.py): 640x876 from
     (1270, 103), its right edge 10 from the screen's, the shadow 40 past it all round. The title, subtitle
     and summary 25 in, at the same offsets from the top as before; the summary 20 clear of the bottom. -->
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
        <!-- F2, 95%, one colour across the panel (on request, 2026-10-08) - was D3, 83%, with a
             30000000 strip down its left 240 -->
        <colordiffuse>F2111111</colordiffuse>
    </control>
    <!-- Title: the settings and pickers' heading (includes/option_card_frame.xml.tpl) - font25_title,
         FFEEEEEE, centred in the panel's top 66, 560 wide from 40 in, scrolling when it's longer. Was font13
         made bold with [B], left-aligned, 20 down. -->
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
        <label>$INFO[Window.Property(title)]</label>
    </control>
    <!-- Subtitle - Episodes' own use only (its episode name, under the show title in "title" above);
         every other caller leaves Window.Property(subtitle) empty and this just doesn't render.
         Smaller/dimmer than the title (font10, FFD2CCCE - matches the summary's own textcolor
         below) so it reads as clearly secondary, on request; bold via [B] markup (on request).
         Centred under the title, just inside its 66: the two read as one heading. -->
    <control type="label">
        <visible>!String.IsEmpty(Window.Property(subtitle))</visible>
        <posx>40</posx>
        <posy>{{ vscale(58) }}</posy>
        <width>560</width>
        <height>{{ vscale(30) }}</height>
        <font>font10</font>
        <align>center</align>
        <aligny>center</aligny>
        <textcolor>FFD2CCCE</textcolor>
        <scroll>true</scroll>
        <scrollspeed>15</scrollspeed>
        <label>[B]$INFO[Window.Property(subtitle)][/B]</label>
    </control>
    <!-- The summary from under the heading, whether that's one line or two: the title alone from 66, its
         66's foot, as the settings' rows start; with Episodes' subtitle from 106, as far under that line
         (~20 clear of its text). Two of it, each with its own scrollbar below (Kodi can't move a
         scrollbar from Python), and SummaryDialog focuses the one showing. -->
    <control type="textbox">
        <visible>String.IsEmpty(Window.Property(subtitle))</visible>
        <posx>25</posx>
        <posy>{{ vscale(66) }}</posy>
        <pagecontrol>102</pagecontrol>
        <width>590</width>
        <height>{{ vscale(790) }}</height>
        <font>font10</font>
        <align>left</align>
        <textcolor>FFDDDDDD</textcolor>
        <label>$INFO[Window.Property(info)]</label>
    </control>
    <control type="textbox">
        <visible>!String.IsEmpty(Window.Property(subtitle))</visible>
        <posx>25</posx>
        <posy>{{ vscale(106) }}</posy>
        <pagecontrol>101</pagecontrol>
        <width>590</width>
        <height>{{ vscale(750) }}</height>
        <font>font10</font>
        <align>left</align>
        <textcolor>FFDDDDDD</textcolor>
        <label>$INFO[Window.Property(info)]</label>
    </control>
</control>
<!-- The Libraries picker's scrollbar as it looks (script-plex-card_list.xml.tpl, on request
     2026-10-08): 12 wide, rounded, a 40000000 track and a 77FFFFFF bar - and where the option pickers'
     sits (includes/option_card_frame.xml.tpl): 1894-1906, 4 in from the panel's right edge, its hitrect
     from 4 before it, 50 wide, over its own height. The bar keeps 77FFFFFF focused too, unlike the shared style
     (includes/scrollbar_style.xml.tpl) it's otherwise written from: this scrollbar always has the
     focus (SummaryDialog focuses it so the remote scrolls the text, info.py), so its focused bar is
     the only one ever seen - the pickers' brighten when focused (DDFFFFFF), as this one has no need to. -->
<control type="scrollbar" id="102">
    <visible>String.IsEmpty(Window.Property(subtitle))</visible>
    <hitrect x="1890" y="169" w="50" h="790" />
    <left>1894</left>
    <top>{{ vscale(169) }}</top>
    <width>12</width>
    <height>{{ vscale(790) }}</height>
    <onleft>noop</onleft>
    <texturesliderbackground colordiffuse="40000000" border="5">script.plex/white-square-rounded.png</texturesliderbackground>
    <texturesliderbar colordiffuse="77FFFFFF" border="5">script.plex/white-square-rounded.png</texturesliderbar>
    <texturesliderbarfocus colordiffuse="77FFFFFF" border="5">script.plex/white-square-rounded.png</texturesliderbarfocus>
    <textureslidernib>-</textureslidernib>
    <textureslidernibfocus>-</textureslidernibfocus>
    <pulseonselect>false</pulseonselect>
    <orientation>vertical</orientation>
    <showonepage>false</showonepage>
</control>
<control type="scrollbar" id="101">
    <visible>!String.IsEmpty(Window.Property(subtitle))</visible>
    <hitrect x="1890" y="209" w="50" h="750" />
    <left>1894</left>
    <top>{{ vscale(209) }}</top>
    <width>12</width>
    <height>{{ vscale(750) }}</height>
    <onleft>noop</onleft>
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
