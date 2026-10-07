<!-- One row of the playlist screen's item list (script-plex-playlist.xml.tpl), shared between its
     itemlayout and focusedlayout so the two can't drift.

     The Album screen's row (includes/album_track_row.xml.tpl) - the 1694 pill inset 4px top and
     bottom, the duration 1526..1676 and the 60000000 / 33FFFFFF pill colours - with the music
     list view's art and text stack (includes/track_row.xml.tpl) in place of its number column, on
     request 2026-10-07:
       art       80 tall at (6,10): 6px clear of the pill's left edge, top and bottom - the track
                 row's own margins. Its shape follows the item (playlist.py's updateListItem()):
                 square for tracks, a 53-wide poster (2:3) for films (the 'poster' property), and
                 142 wide (16:9) for episodes and clips (the 'video' property without 'poster')
       text      18px right of the art (the track row's gap), so it starts at 104 beside a square
                 as there, 77 beside a poster, 166 beside a 16:9 - ending at 1519 as the album row's
                 title does. The track row's two line boxes: title at 23 in font10, second line
                 (artist / album, show / episode, or year) at 50 in font8 AAFFFFFF
       mixed     in a playlist of both films and 16:9 items (playlist.mixed, noteArtShape(),
                 playlist.py) a poster sits centred in the 16:9 art's width - at 50, (142-53)/2
                 in from 6 - and its text starts at 166 with the 16:9 rows', so the list lines up
       video     the hub tiles' inset progress pill under the art, and the watched tick in the
                 art's top-right corner, both scaled to the 80px art
     The playing track is marked by its title in the theme accent alone, as in the track row: with
     the number column gone there's no column for the now-playing glyph.

     Params:
       focused - True in a focusedlayout, False in an itemlayout. Drives both the pill colour and
         whether the title marquees. -->

{% if focused %}
<!-- Both pills gated on Control.HasFocus(101) - see album_track_row.xml.tpl. -->
<control type="image">
    <visible>Control.HasFocus(101)</visible>
    <posx>0</posx>
    <posy>{{ vscale(4) }}</posy>
    <width>1694</width>
    <height>{{ vscale(92) }}</height>
    <texture border="10" colordiffuse="33FFFFFF">script.plex/white-square-rounded.png</texture>
</control>
<control type="image">
    <visible>!Control.HasFocus(101)</visible>
    <posx>0</posx>
    <posy>{{ vscale(4) }}</posy>
    <width>1694</width>
    <height>{{ vscale(92) }}</height>
    <texture border="10" colordiffuse="60000000">script.plex/white-square-rounded.png</texture>
</control>
{% else %}
<control type="image">
    <posx>0</posx>
    <posy>{{ vscale(4) }}</posy>
    <width>1694</width>
    <height>{{ vscale(92) }}</height>
    <texture border="10" colordiffuse="60000000">script.plex/white-square-rounded.png</texture>
</control>
{% endif %}

{# The art and text, once per art shape and text column: Kodi can't move a control on a condition,
   so each is its own group, gated on the row's 'video' and 'poster' properties and, for a poster,
   the window's playlist.mixed. art_x is the art's left edge, 6 - or, for a poster in a mixed
   playlist, 50, centring it in the 16:9 art's 6..148. text_x is 18px after the art, or the 16:9
   rows' 166 for that poster. #}
{% for shape, art_x, art_w, mask, text_x in (("square", 6, 80, "square-mask", 104), ("wide", 6, 142, "ar16x9-mask", 166), ("poster", 6, 53, "poster-mask", 77), ("poster_mixed", 50, 53, "poster-mask", 166)) %}
<control type="group">
    {% if shape == "square" %}
    <visible>String.IsEmpty(ListItem.Property(video))</visible>
    {% elif shape == "wide" %}
    <visible>!String.IsEmpty(ListItem.Property(video)) + String.IsEmpty(ListItem.Property(poster))</visible>
    {% elif shape == "poster" %}
    <visible>!String.IsEmpty(ListItem.Property(poster)) + String.IsEmpty(Window.Property(playlist.mixed))</visible>
    {% else %}
    <visible>!String.IsEmpty(ListItem.Property(poster)) + !String.IsEmpty(Window.Property(playlist.mixed))</visible>
    {% endif %}
    <!-- Art, through the skin's usual mask, with native fallback= (thumb.fallback,
         updateListItem(), playlist.py) - see track_row.xml.tpl for why not a layer underneath. -->
    <control type="image">
        <posx>{{ art_x }}</posx>
        <posy>{{ vscale(10) }}</posy>
        <width>{{ art_w }}</width>
        <height>{{ vscale(80) }}</height>
        <texture background="true" diffuse="script.plex/masks/{{ mask }}.png" fallback="$INFO[ListItem.Property(thumb.fallback)]">$INFO[ListItem.Thumb]</texture>
        <aspectratio scalediffuse="false">scale</aspectratio>
    </control>
{% if shape != "square" %}
    <!-- Progress: the hub tiles' inset pill, 6px in from the art's sides and bottom. -->
    <control type="group">
        <visible>!String.IsEmpty(ListItem.Property(progress))</visible>
        <posx>{{ art_x + 6 }}</posx>
        <posy>{{ vscale(78) }}</posy>
        <control type="image">
            <posx>0</posx>
            <posy>0</posy>
            <width>{{ art_w - 12 }}</width>
            <height>{{ vscale(6) }}</height>
            <texture diffuse="script.plex/masks/progress-bar-mask.png">script.plex/white-square.png</texture>
            <colordiffuse>E60A0F1A</colordiffuse>
        </control>
        <control type="image">
            <posx>0</posx>
            <posy>0</posy>
            <width>{{ art_w - 12 }}</width>
            <height>{{ vscale(6) }}</height>
            <texture diffuse="script.plex/masks/progress-bar-mask.png">$INFO[ListItem.Property(progress)]</texture>
            <colordiffuse>FFE5A00D</colordiffuse>
        </control>
    </control>
    {% include "includes/watched_indicator.xml.tpl" with xoff=art_x+art_w & yoff=10 & uw_size=24 & wbg_w=24 & wbg_h=24 %}
{% endif %}

    <!-- Title, twice for the now-playing tint (album_track_row.xml.tpl's reasoning, including the
         explicit non-empty test). -->
    <control type="label">
        <visible>String.IsEmpty(Window(10000).Property(script.plex.track.ID)) | !String.IsEqual(ListItem.Property(track.ID),Window(10000).Property(script.plex.track.ID))</visible>
        <scroll>{% if focused %}Control.HasFocus(101){% else %}false{% endif %}</scroll>
        <posx>{{ text_x }}</posx>
        <posy>{{ vscale(23) }}</posy>
        <width>{{ 1519 - text_x }}</width>
        <height>{{ vscale(30) }}</height>
        <font>font10</font>
        <align>left</align>
        <aligny>center</aligny>
        <textcolor>FFFFFFFF</textcolor>
        <label>$INFO[ListItem.Label]</label>
    </control>
    <control type="label">
        <visible>!String.IsEmpty(Window(10000).Property(script.plex.track.ID)) + String.IsEqual(ListItem.Property(track.ID),Window(10000).Property(script.plex.track.ID))</visible>
        <scroll>{% if focused %}Control.HasFocus(101){% else %}false{% endif %}</scroll>
        <posx>{{ text_x }}</posx>
        <posy>{{ vscale(23) }}</posy>
        <width>{{ 1519 - text_x }}</width>
        <height>{{ vscale(30) }}</height>
        <font>font10</font>
        <align>left</align>
        <aligny>center</aligny>
        <textcolor>FFE5A00D</textcolor>
        <label>$INFO[ListItem.Label]</label>
    </control>
    <control type="label">
        <scroll>false</scroll>
        <posx>{{ text_x }}</posx>
        <posy>{{ vscale(50) }}</posy>
        <width>{{ 1519 - text_x }}</width>
        <height>{{ vscale(30) }}</height>
        <font>font8</font>
        <align>left</align>
        <aligny>center</aligny>
        <textcolor>AAFFFFFF</textcolor>
        <label>$INFO[ListItem.Label2]</label>
    </control>
</control>
{% endfor %}

<control type="label">
    <posx>1526</posx>
    <posy>0</posy>
    <width>150</width>
    <height>{{ vscale(100) }}</height>
    <font>font10</font>
    <align>right</align>
    <aligny>center</aligny>
    <textcolor>D8FFFFFF</textcolor>
    <label>$INFO[ListItem.Property(track.duration)]</label>
</control>
