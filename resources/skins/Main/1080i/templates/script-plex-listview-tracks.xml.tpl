{% extends "script-plex-listview-square.xml.tpl" %}
{# The music section's list view (TrackListWindow, library.py) - always the Tracks item type, since
   MUSIC_VIEWTYPE_BY_ITEM_TYPE pins Artists/Albums/Collections to the grid and only Tracks to the
   list. A separate template rather than a branch inside script-plex-listview-square.xml.tpl (which
   still serves Photos and Playlists): the two differ in list geometry and row height, and a skin
   can't vary a control's width or position on a condition.

   Everything but the list is inherited from the parent - header, tabs, filter/sort row, Play/
   Shuffle, the A-Z scrubber and its scrollbar - so only the two blocks below are declared here.

   Rows follow the Artist screen's Popular Tracks recipe verbatim (script-plex-artist.xml.tpl's
   list 402): a 100px row carrying a 1694->1650 wide pill inset 4px top and bottom, title on top,
   a dimmed second line under it, duration right-aligned, and the pill's colour swapping between
   60000000 and 33FFFFFF on focus. Three things differ, all of them asked for:
     - the pill is 1650 wide, not 1694
     - it starts at x=120, the same left edge as the music grid's first tile
       (script-plex-squares.xml.tpl), so the two views line up as you switch between them. 1650 is
       that grid's own art-to-art span too, so this list ends exactly where its last tile does
     - the second line is the ARTIST, not the album #}

{% block listview_detail %}{% endblock listview_detail %}

{% block listview_list %}
<control type="group" id="50">
    <!-- Slide right while the sidebar rail is expanded (focused), matching every other screen. The
         parent template carries this on its detail pane instead - the group this block replaces -
         so re-declaring the list here dropped it. -->
    <animation effect="slide" end="220,0" time="200" tween="sine" easing="inout" condition="ControlGroup(9000).HasFocus(0)">Conditional</animation>
    <posx>0</posx>
    <posy>{{ vscale(125) }}</posy>
    <defaultcontrol>101</defaultcontrol>

    <control type="group" id="100">
        <visible>Integer.IsGreater(Container(101).NumItems,0) + String.IsEmpty(Window.Property(drawing))</visible>
        <defaultcontrol>101</defaultcontrol>
        <!-- 120 absolute, matching the music grid's own first-tile art edge (panel 60 + the item's
             own 55 + the card group's 5). No dark backing plate behind the list, unlike the parent
             template's own copy - each row carries its own pill now, so a plate behind them just
             muddied the unfocused tint. -->
        <posx>120</posx>
        <posy>{{ vscale(100) }}</posy>
        <width>1650</width>
        <height>1080</height>
        <control type="list" id="101">
            <hitrect x="120" y="235" w="1650" h="800" />
            <posx>0</posx>
            <posy>0</posy>
            <width>1650</width>
            <!-- 800, not the parent's 845: an exact 8 rows of 100, so the list never clips a row
                 in half at the bottom the way 845 would (8.45). -->
            <height>{{ vscale(800) }}</height>
            <!-- 600 (the filter/sort row), not 300 (the buttons): up off the first row lands on
                 the sort and filter controls, mirroring the grid, where only its SECOND row routes
                 to the buttons and the first goes here (script-plex-squares.xml.tpl's panel 101).
                 A vertical list has no second-row equivalent to carry that other route, so the
                 buttons are reached from 600's own onright instead. -->
            <onup>600</onup>
            <onright>151</onright>
            <!-- 9000 (the sidebar), not 210 (the sort button in the filter row): left off a row
                 should open the sidebar, the way it does from the grid. The filter/sort row is
                 reached by going up instead (onup above). 210 came in with the parent template's
                 own list, whose layout puts that row within reach sideways. -->
            <onleft>9000</onleft>
            <!-- Stop at the last track rather than wrapping back to the first - see the album
                 screen's own copy of this pair (script-plex-album.xml.tpl) for why both tags are
                 needed. -->
            <wraparound>false</wraparound>
            <ondown>noop</ondown>
            <scrolltime>200</scrolltime>
            <orientation>vertical</orientation>
            <preloaditems>4</preloaditems>
            <!-- Links this list to scrollbar 152's real scroll position/drag-to-scroll. -->
            <pagecontrol>152</pagecontrol>

            <!-- ITEM LAYOUT ########################################## -->
            <itemlayout height="{{ vscale(100) }}">
                <control type="group">
                    <posx>0</posx>
                    <posy>0</posy>
                    <!-- Unfocused pill - identical geometry to the focused one below, so focus
                         swaps the colour and nothing moves. -->
                    <control type="image">
                        <posx>0</posx>
                        <posy>{{ vscale(4) }}</posy>
                        <width>1650</width>
                        <height>{{ vscale(92) }}</height>
                        <texture border="10" colordiffuse="60000000">script.plex/white-square-rounded.png</texture>
                    </control>
                    {% include "includes/track_row.xml.tpl" with list_id=101 & scroll_focused=False %}
                </control>
            </itemlayout>

            <!-- FOCUSED LAYOUT ####################################### -->
            <focusedlayout height="{{ vscale(100) }}">
                <control type="group">
                    <posx>0</posx>
                    <posy>0</posy>
                    <!-- Both pills gated on Control.HasFocus(101): Kodi renders a list's
                         focusedlayout for its SELECTED item whether or not the control has focus,
                         so an ungated focus pill leaves a row permanently lit while the user is
                         elsewhere on screen - live-confirmed on the Popular Tracks row this recipe
                         comes from. Two controls because a texture's colordiffuse can't be
                         switched on a condition. -->
                    <control type="image">
                        <visible>Control.HasFocus(101)</visible>
                        <posx>0</posx>
                        <posy>{{ vscale(4) }}</posy>
                        <width>1650</width>
                        <height>{{ vscale(92) }}</height>
                        <texture border="10" colordiffuse="33FFFFFF">script.plex/white-square-rounded.png</texture>
                    </control>
                    <control type="image">
                        <visible>!Control.HasFocus(101)</visible>
                        <posx>0</posx>
                        <posy>{{ vscale(4) }}</posy>
                        <width>1650</width>
                        <height>{{ vscale(92) }}</height>
                        <texture border="10" colordiffuse="60000000">script.plex/white-square-rounded.png</texture>
                    </control>
                    {% include "includes/track_row.xml.tpl" with list_id=101 & scroll_focused=True %}
                </control>
            </focusedlayout>
        </control>
    </control>
</control>
{% endblock listview_list %}
