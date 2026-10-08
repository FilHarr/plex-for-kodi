{% extends "base.xml.tpl" %}
{% block backgroundcolor %}{% endblock %}
{% block controls %}
<!-- SummaryDialog's own popup (info.py) - originally ArtistWindow's Info popup, now shared by
     Seasons/Episodes/PrePlay's own summary-textbox click-targets too (on request) - forked off
     script-plex-media_details_dialog.xml.tpl once this screen's own sizing (600x1000, centered) and
     its separate title/summary font treatment diverged from that dialog's own technical-file-info
     layout. Same drop-shadow/rounded-rect panel shell/scrollbar mechanism as that dialog (and
     Settings' own "Settings" popup, playersettings.py, which they both originally copied) - see
     that file's own comment for the shell's general reasoning.

     posx=660/width=600: centers a 600-wide panel in the 1920-wide canvas ((1920-600)/2). posy uses
     vperc() (util/filters.py) instead of a literal number - vperc(height) resolves to the y position
     that vertically centers a box of that height in the 1080-tall canvas ((1080-height)/2) - the
     literal-460/1000-wide original panel used the exact same 50/50 horizontal math, just written out
     by hand since a plain width doesn't need a helper function to center. -->
<control type="group">
    <posx>660</posx>
    <posy>{{ vperc(vscale(1000)) }}</posy>
    <control type="image">
        <posx>-40</posx>
        <posy>{{ vscale(-40) }}</posy>
        <width>680</width>
        <height>{{ vscale(1080) }}</height>
        <texture border="42">script.plex/drop-shadow.png</texture>
    </control>
    <control type="image">
        <posx>0</posx>
        <posy>0</posy>
        <width>600</width>
        <height>{{ vscale(1000) }}</height>
        <texture border="10">script.plex/white-square-rounded.png</texture>
        <!-- F2, 95%, one colour across the panel (on request, 2026-10-08) - was D3, 83%, with a
             30000000 strip down its left 240 -->
        <colordiffuse>F2111111</colordiffuse>
    </control>
    <!-- Title - its own control/font (font13, independent of the summary's font10 below) so the two
         can be sized separately, on request. Bold via [B] markup (same as this dialog's own previous
         single-textbox "[B]{title}[/B]\n\n{summary}" treatment), not a *_title font variant - keeps
         this in plain non-title fonts like the summary below it. -->
    <control type="label">
        <posx>25</posx>
        <posy>{{ vscale(20) }}</posy>
        <width>550</width>
        <height>{{ vscale(50) }}</height>
        <font>font13</font>
        <align>left</align>
        <textcolor>FFFFFFFF</textcolor>
        <label>[B]$INFO[Window.Property(title)][/B]</label>
    </control>
    <!-- Subtitle - Episodes' own use only (its episode name, under the show title in "title" above);
         every other caller leaves Window.Property(subtitle) empty and this just doesn't render.
         Smaller/dimmer than the title (font10, FFD2CCCE - matches the summary's own textcolor
         below) so it reads as clearly secondary, on request; bold via [B] markup (on request).
         posy=60, not the slot's own natural 70 (net 10px closer to the title above it, on request -
         moved 15px up then 5px back down) - the slot's own reserved space (title 20-70, summary
         fixed from 110) is unchanged, so this now sits with extra breathing room below it rather
         than the original even 20px gap both sides. -->
    <control type="label">
        <visible>!String.IsEmpty(Window.Property(subtitle))</visible>
        <posx>25</posx>
        <posy>{{ vscale(60) }}</posy>
        <width>550</width>
        <height>{{ vscale(30) }}</height>
        <font>font10</font>
        <align>left</align>
        <textcolor>FFD2CCCE</textcolor>
        <label>[B]$INFO[Window.Property(subtitle)][/B]</label>
    </control>
    <control type="textbox">
        <posx>25</posx>
        <posy>{{ vscale(110) }}</posy>
        <pagecontrol>101</pagecontrol>
        <width>550</width>
        <height>{{ vscale(870) }}</height>
        <font>font10</font>
        <align>left</align>
        <textcolor>FFDDDDDD</textcolor>
        <label>$INFO[Window.Property(info)]</label>
    </control>
</control>
<!-- left/top/hitrect scaled over from script-plex-media_details_dialog.xml.tpl's own copy rather
     than re-derived from scratch (that one's own hitrect y/h don't line up with a literal
     recomputation from its visible posy/height either - likely hand-tuned live rather than
     computed) - live-check this one's own click zone once the dialog's actually up. -->
<!-- The Libraries picker's scrollbar as it looks (script-plex-card_list.xml.tpl, on request
     2026-10-08): 12 wide, rounded, a 40000000 track and a 77FFFFFF bar - its right edge where the old
     10-wide one's was, on the panel's. The bar keeps 77FFFFFF focused too, unlike the shared style
     (includes/scrollbar_style.xml.tpl) it's otherwise written from: this scrollbar always has the
     focus (SummaryDialog focuses it so the remote scrolls the text, info.py), so its focused bar is
     the only one ever seen, where the picker's never takes focus and never turns orange. -->
<control type="scrollbar" id="101">
    <hitrect x="1208" y="33" w="90" h="1044" />
    <left>1248</left>
    <top>{{ vperc(vscale(1000)) + vscale(110) }}</top>
    <width>12</width>
    <height>{{ vscale(870) }}</height>
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
