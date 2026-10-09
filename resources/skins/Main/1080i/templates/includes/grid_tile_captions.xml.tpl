<!-- A "See more" grid tile's caption lines (grid_tile_poster/_square.xml.tpl), inside the card's
     art group: up to three - the first font10 and bright, the rest font8 and dimmed
     (on request, 2026-10-09). The second line is a rating's logo and score in
     pre-play's rating style (script-plex-seasons.xml.tpl's ratings) when the item has one
     (rating.image: Top Rated TV), centred under the art.

     Params:
       focused - True inside a focusedlayout: long lines scroll while the grid has focus
       top1, top2, top3 - each line's top, under the art; precomputed - ibis leaves arithmetic
                 in an expression as literal text. Line 2 is 30 below line 1 and A0FFFFFF, the
                 library poster grid's own (script-plex-posters.xml.tpl), on request (2026-10-09);
                 line 3 is 25 below line 2: each label's text starts at its box's top, so a line
                 ends its own font size down - font10 23, font8 18 (skin.plextuary's Font.xml) -
                 and the same step again left a gap 5 bigger under the font8 line 2 (live).
       width    - the art's width, which the lines are centred under (240; 512 on the 16:9 grid)
       rating_x - the rating group's left, centring its 91 under the art: (width - 91) / 2,
                  precomputed (74; 210 on the 16:9 grid) -->
<control type="label">
    <scroll>{% if focused %}Control.HasFocus(101){% else %}false{% endif %}</scroll>
    <posx>0</posx>
    <posy>{{ top1|vscale }}</posy>
    <width>{{ width|default(240) }}</width>
    <height>{{ vscale(35) }}</height>
    <font>font10</font>
    <align>center</align>
    <textcolor>FFFFFFFF</textcolor>
    <label>$INFO[ListItem.Label]</label>
</control>
<control type="label">
    <visible>String.IsEmpty(ListItem.Property(rating.image))</visible>
    <scroll>{% if focused %}Control.HasFocus(101){% else %}false{% endif %}</scroll>
    <posx>0</posx>
    <posy>{{ top2|vscale }}</posy>
    <width>{{ width|default(240) }}</width>
    <height>{{ vscale(35) }}</height>
    <font>font8</font>
    <align>center</align>
    <textcolor>A0FFFFFF</textcolor>
    <label>$INFO[ListItem.Label2]</label>
</control>
<control type="group">
    <!-- 91 wide, as pre-play's: the logo right-aligned in its 40, the score 7 after it -->
    <visible>!String.IsEmpty(ListItem.Property(rating.image))</visible>
    <posx>{{ rating_x|default(74) }}</posx>
    <posy>{{ top2|vscale }}</posy>
    <!-- Two copies of the logo, by its source. Every logo's visible part is centred near 17 here,
         but the score is a top-aligned font8 line whose digits sit about 5-18 down (Inter 18px,
         skin.plextuary) - centre ~12. A Rotten Tomatoes logo fills the whole 30 and covers the
         digits either way; TMDB's and IMDb's are short marks in a square image (13-15 tall,
         ratings/*/image.rating.png), which read low beside them - so those two sit 4 higher (on
         request, 2026-10-09; 5 was marginally too high, live), the rest where they were. -->
    <control type="image">
        <visible>!String.Contains(ListItem.Property(rating.image),/tmdb/) + !String.Contains(ListItem.Property(rating.image),/imdb/)</visible>
        <posx>0</posx>
        <posy>{{ vscale(2) }}</posy>
        <width>40</width>
        <height>{{ vscale(30) }}</height>
        <texture fallback="script.plex/ratings/other/image.rating.png">$INFO[ListItem.Property(rating.image)]</texture>
        <aspectratio align="right">keep</aspectratio>
    </control>
    <control type="image">
        <visible>String.Contains(ListItem.Property(rating.image),/tmdb/) | String.Contains(ListItem.Property(rating.image),/imdb/)</visible>
        <posx>0</posx>
        <posy>{{ vscale(-2) }}</posy>
        <width>40</width>
        <height>{{ vscale(30) }}</height>
        <texture fallback="script.plex/ratings/other/image.rating.png">$INFO[ListItem.Property(rating.image)]</texture>
        <aspectratio align="right">keep</aspectratio>
    </control>
    <control type="label">
        <posx>47</posx>
        <posy>0</posy>
        <width>60</width>
        <height>{{ vscale(35) }}</height>
        <font>font8</font>
        <align>left</align>
        <textcolor>A0FFFFFF</textcolor>
        <label>$INFO[ListItem.Property(rating)]</label>
    </control>
</control>
<control type="label">
    <visible>!String.IsEmpty(ListItem.Property(line3))</visible>
    <scroll>{% if focused %}Control.HasFocus(101){% else %}false{% endif %}</scroll>
    <posx>0</posx>
    <posy>{{ top3|vscale }}</posy>
    <width>{{ width|default(240) }}</width>
    <height>{{ vscale(35) }}</height>
    <font>font8</font>
    <align>center</align>
    <textcolor>A0FFFFFF</textcolor>
    <label>$INFO[ListItem.Property(line3)]</label>
</control>
