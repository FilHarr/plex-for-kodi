<!-- One row of the album screen's track list (script-plex-album.xml.tpl), shared between its
     itemlayout and focusedlayout so the two can't drift.

     The Artist screen's Popular Tracks recipe (script-plex-artist.xml.tpl's list 402) with two
     changes, both asked for: a single title line rather than title-over-album, so it's centred on
     the row instead of sitting at the 23/50 two-line offsets; and a track-number column ahead of
     it. Everything else is that recipe verbatim - a 100px row carrying a 1694 pill inset 4px top
     and bottom, duration right-aligned 18px short of the pill's right edge, and the pill swapping
     60000000 for 33FFFFFF on focus.

     Columns: the number is centred in the whole 0..86 space ahead of the title rather than
     right-aligned against it, the title runs 86..1519, and the duration 1526..1676 - the recipe's
     own 7px gap before it, 18px short of the pill's right edge.

     Every album carries at least one header row (fillTracks(), tracks.py, via is.header),
     rendered as a bare heading with no pill: "12 tracks" on a single-disc album, and
     "Disc 1, 7 tracks" per disc on a multi-disc one. Sentence case, not uppercased here - the
     Python side writes the text exactly as it should read.

     Params:
       focused - True in a focusedlayout, False in an itemlayout. Drives both the pill colour and
         whether the title marquees. -->

<!-- DISC separator ######################################################################### -->
<control type="label">
    <visible>!String.IsEmpty(ListItem.Property(is.header))</visible>
    <posx>18</posx>
    <posy>0</posy>
    <width>800</width>
    <height>{{ vscale(100) }}</height>
    <!-- Recommended's row-title style (font30_title, FFD2CCCE, 66000000 shadow), as every other
         row heading uses. -->
    <font>font30_title</font>
    <align>left</align>
    <aligny>center</aligny>
    <textcolor>FFD2CCCE</textcolor>
    <shadowcolor>66000000</shadowcolor>
    <label>$INFO[ListItem.Label]</label>
</control>

<!-- TRACK ################################################################################## -->
<control type="group">
    <visible>String.IsEmpty(ListItem.Property(is.header))</visible>
{% if focused %}
    <!-- Both pills gated on Control.HasFocus(101): Kodi renders a list's focusedlayout for its
         SELECTED item whether or not the control has focus, so an ungated focus pill leaves one row
         permanently lit while the user is elsewhere on screen. Two controls because a texture's
         colordiffuse can't be switched on a condition; identical geometry, so nothing moves. -->
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

    <!-- Number column, on every row: the playing track is marked by its title in the accent alone
         (below), as in the music list view's rows and the playlist screen's - the now-playing glyph
         that used to take the number's place went on request, 2026-10-07. -->
    <control type="label">
        <posx>0</posx>
        <posy>0</posy>
        <width>86</width>
        <height>{{ vscale(100) }}</height>
        <font>font10</font>
        <align>center</align>
        <aligny>center</aligny>
        <textcolor>D8FFFFFF</textcolor>
        <label>$INFO[ListItem.Property(track.number)]</label>
    </control>

    <!-- Title, written twice because Kodi can't switch a label's textcolor on a condition. The
         explicit non-empty test matters: String.IsEqual("","") is TRUE, so without it every row
         would render as the playing track whenever nothing was playing. playing.here
         (updatePlayingHere(), tracks.py) limits it to music playing from this album's own queue:
         the same track playing from Popular Tracks or a playlist isn't marked. -->
    <control type="label">
        <visible>String.IsEmpty(Window(10000).Property(script.plex.track.ID)) | !String.IsEqual(ListItem.Property(track.ID),Window(10000).Property(script.plex.track.ID)) | String.IsEmpty(Window.Property(playing.here))</visible>
        <scroll>{% if focused %}Control.HasFocus(101){% else %}false{% endif %}</scroll>
        <posx>86</posx>
        <posy>0</posy>
        <width>1433</width>
        <height>{{ vscale(100) }}</height>
        <font>font10</font>
        <align>left</align>
        <aligny>center</aligny>
        <textcolor>FFFFFFFF</textcolor>
        <label>$INFO[ListItem.Label]</label>
    </control>
    <control type="label">
        <visible>!String.IsEmpty(Window(10000).Property(script.plex.track.ID)) + String.IsEqual(ListItem.Property(track.ID),Window(10000).Property(script.plex.track.ID)) + !String.IsEmpty(Window.Property(playing.here))</visible>
        <scroll>{% if focused %}Control.HasFocus(101){% else %}false{% endif %}</scroll>
        <posx>86</posx>
        <posy>0</posy>
        <width>1433</width>
        <height>{{ vscale(100) }}</height>
        <font>font10</font>
        <align>left</align>
        <aligny>center</aligny>
        <textcolor>FFE5A00D</textcolor>
        <label>$INFO[ListItem.Label]</label>
    </control>

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
</control>
