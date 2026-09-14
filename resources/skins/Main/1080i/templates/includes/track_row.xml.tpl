<!-- The contents of a track row in the music section's list view
     (script-plex-listview-tracks.xml.tpl) - album art, text stack, duration - shared between its
     itemlayout and focusedlayout so the two can't drift, the way the Artist screen's own Popular
     Tracks row (script-plex-artist.xml.tpl) has to keep two hand-maintained copies in step.

     Geometry is that row's recipe re-solved for a 1650 pill, plus the 80x80 album thumb it doesn't
     have:
       art       80x80 at (6,10). 6px clear of the pill's left edge, and 6px of its top and bottom
                 too (the pill is 92 of the row's 100, so centring the art in the row centres it in
                 the pill) - a uniform margin on all three sides it touches. Rounded by the same
                 masks/square-mask.png every other piece of art in the skin uses, so the corner
                 radius scales with the box exactly as the grid's tiles do
       text      starts at 104: the art's right edge (86) plus the same 18px gap the text used to
                 take from the pill's edge. Box is 1371 wide, still ending at 1475
       duration  unchanged at 1482, 150 wide, ending 18px short of the pill's right edge (1632),
                 leaving the recipe's own 7px gap after the text box
     Line boxes at 23 and 50 inside the 100px row put the title's line at 24.1 and the second line's
     bottom at 75.9 - 20px clear of the pill's 4..96 at both ends.

     Fields come from _chunkCallback() (library.py), which is what actually builds library grid and
     list rows - NOT createTrackListItem(), which only ever serves hub tiles. That callback sets a
     track's Label to a composite "Artist - Album: Title" and its Label2 to a duration in
     durationToText()'s "2m 23s" form, both of which other views rely on, so this row reads its own
     track.title / track.artist / track.duration properties instead and leaves those two alone.

     The now-playing gate carries an explicit non-empty test on the window property as well as the
     comparison: String.IsEqual("","") is TRUE, so a row with no track.ID set at all rendered as
     though it were the playing track whenever nothing was playing - live-reported as every first
     line showing in the accent colour.

     Params:
       list_id - the enclosing list's control id, for the scroll condition
       scroll_focused - True in a focusedlayout (title marquees while the list has focus), False in
         an itemlayout (nothing scrolls; every unfocused row would otherwise marquee at once) -->

<!-- Album art. Two layers, the same pairing the grid tiles use: the fallback underneath (set on
     every item in this fill path by CreateDefaultItemsTask, library.py - music.png for a music
     section) and the real thumb over it, which simply doesn't paint while it loads or when the
     album has no art. scalediffuse="false" keeps the rounded mask pinned to the control's own
     bounds instead of being scaled along with art whose aspect ratio isn't square - without it the
     corners drift and square off, live-confirmed elsewhere in this skin. -->
<control type="image">
    <posx>6</posx>
    <posy>{{ vscale(10) }}</posy>
    <width>80</width>
    <height>{{ vscale(80) }}</height>
    <texture diffuse="script.plex/masks/square-mask.png">$INFO[ListItem.Property(thumb.fallback)]</texture>
</control>
<control type="image">
    <posx>6</posx>
    <posy>{{ vscale(10) }}</posy>
    <width>80</width>
    <height>{{ vscale(80) }}</height>
    <texture background="true" diffuse="script.plex/masks/square-mask.png">$INFO[ListItem.Thumb]</texture>
    <aspectratio scalediffuse="false">scale</aspectratio>
</control>

<!-- The title is written twice, gated on whether this row is the track currently playing: Kodi
     can't switch a single label's textcolor on a condition. FFE5A00D is the theme accent, the same
     now-playing treatment Popular Tracks uses. -->
<control type="label">
    <visible>String.IsEmpty(Window(10000).Property(script.plex.track.ID)) | !String.IsEqual(ListItem.Property(track.ID),Window(10000).Property(script.plex.track.ID))</visible>
    <scroll>{% if scroll_focused %}Control.HasFocus({{ list_id }}){% else %}false{% endif %}</scroll>
    <posx>104</posx>
    <posy>{{ vscale(23) }}</posy>
    <width>1371</width>
    <height>{{ vscale(30) }}</height>
    <font>font10</font>
    <align>left</align>
    <aligny>center</aligny>
    <textcolor>FFFFFFFF</textcolor>
    <label>$INFO[ListItem.Property(track.title)]</label>
</control>
<control type="label">
    <visible>!String.IsEmpty(Window(10000).Property(script.plex.track.ID)) + String.IsEqual(ListItem.Property(track.ID),Window(10000).Property(script.plex.track.ID))</visible>
    <scroll>{% if scroll_focused %}Control.HasFocus({{ list_id }}){% else %}false{% endif %}</scroll>
    <posx>104</posx>
    <posy>{{ vscale(23) }}</posy>
    <width>1371</width>
    <height>{{ vscale(30) }}</height>
    <font>font10</font>
    <align>left</align>
    <aligny>center</aligny>
    <textcolor>FFE5A00D</textcolor>
    <label>$INFO[ListItem.Property(track.title)]</label>
</control>
<control type="label">
    <scroll>false</scroll>
    <posx>104</posx>
    <posy>{{ vscale(50) }}</posy>
    <width>1371</width>
    <height>{{ vscale(30) }}</height>
    <font>font8</font>
    <align>left</align>
    <aligny>center</aligny>
    <textcolor>AAFFFFFF</textcolor>
    <label>$INFO[ListItem.Property(track.artist)]</label>
</control>
<control type="label">
    <posx>1482</posx>
    <posy>0</posy>
    <width>150</width>
    <height>{{ vscale(100) }}</height>
    <font>font10</font>
    <align>right</align>
    <aligny>center</aligny>
    <textcolor>D8FFFFFF</textcolor>
    <label>$INFO[ListItem.Property(track.duration)]</label>
</control>
