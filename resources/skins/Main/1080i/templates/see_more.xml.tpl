{% extends "default.xml.tpl" %}
{# The "See more" grid (lib/windows/see_more.py, spec ~/.claude/plans/see-all-grid.md): every item
   behind a row's "See more" tile, in that row's own tile. Not a screen of its own - each tile shape
   extends this with its panel's layouts and its own numbers (blocks below), as script-plex-posters-
   small extends library_posters: Kodi gives every cell of a panel the same size, so a grid's shape
   is fixed. On BoundedGridWindow (collection.py), so no sort, filter or view-type chrome.

   The page moves the same way on every grid (on request, 2026-10-09: "the movement of the top row
   and the header looks consistent across all the see more pages"):
   - focus leaving the first row slides the whole page - title, buttons, rows - up 60, and back
     coming back to it: the library grid's own way of showing a second row whose foot starts below
     the screen (script-plex-posters.xml.tpl's group 50). 60 is what a three-line poster row needs.
   - past the second row the panel scrolls a row pitch at a time, and the title and buttons slide
     away by exactly that pitch, in the same time and tween, so they scroll with it.
   For the rows to clip only at the screen's edges once slid, the panel runs 60 past the bottom:
   1139 tall. Kodi scrolls a panel as focus passes the last row its height holds whole (height over
   pitch, rounded down), which has to stay two - so every pitch is over 1139 / 3 and at most 1139 / 2
   (credits and squares 380, 16:9 383, posters 455, three-line posters 480).

   Blocks:
     layouts         - the panel's itemlayout and focusedlayout (cell width = column pitch, 6
                       columns of 270/272 in the 1867 the rows use, or 3 of 544 for 16:9;
                       height = row pitch)
     header_scroll   - the title's two slides on the panel's scroll, by the row pitch
     page_slide      - the page slide; a grid of other than 6 columns gives its own, with its
                       first row's last index (columns - 1) in place of 5
     hitrect_y       - where the tiles start, for the mouse #}
{# The grid's group, not the grid (101): the grid is hidden until its items are in, and Kodi logged
   "Control 101 ... has been asked to focus, but it can't" on every open (AM6B, 2026-10-09). A group
   with nothing to focus yet is passed over quietly - the library grid's way (library.xml.tpl);
   SeeMoreWindow.setup() and HubGridWindow.setup() focus the grid once it has items. #}
{% block headers %}<defaultcontrol>100</defaultcontrol>{% endblock %}
{# The 30% row dim (includes/default_background.xml.tpl) all the time, on request (2026-10-08):
   the screen is all rows, opened from one the screen behind it had already dimmed for. #}
{% block background %}{% include "includes/default_background.xml.tpl" with row_dim_condition="true" %}{% endblock %}
{% block header %}
    {{ super() }}
    {% include "includes/sidebar.xml.tpl" %}
    <!-- Declared last so groups 802/901 draw on top - see script-plex-pre_play.xml.tpl's own copy
         of this include for the full reasoning. -->
    {% include "includes/sidebar_dropdowns.xml.tpl" %}
{% endblock header %}
{% block content %}
<control type="group" id="50">
    <!-- Slide right while the sidebar rail is expanded (focused), matching every other screen. -->
    <animation effect="slide" end="220,0" time="200" tween="sine" easing="inout" condition="ControlGroup(9000).HasFocus(0)">Conditional</animation>
    <!-- The page slide (see the top): two animations, one each way, neither reversible - a
         reversed ease-out plays as an ease-in, which parted the header from the rows coming back
         down (live, 2026-10-08). Going one way, one plays and the other resets to nothing, in the
         same frame. Whichever is true when the screen opens is applied at its end without playing
         (Kodi's initial condition). -->
    {% block page_slide %}
    <animation effect="slide" start="0,0" end="0,{{ vscale(-60) }}" time="200" tween="quadratic" easing="out" reversible="false" condition="Integer.IsGreater(Container(101).ListItem.Property(index),5)">Conditional</animation>
    <animation effect="slide" start="0,{{ vscale(-60) }}" end="0,0" time="200" tween="quadratic" easing="out" reversible="false" condition="!Integer.IsGreater(Container(101).ListItem.Property(index),5)">Conditional</animation>
    {% endblock page_slide %}
    <!-- The Filmography screen's outer offsets: the title and the art's left edge land on x=113
         with every other screen's headings. -->
    <posx>52</posx>
    <posy>{{ vscale(125) }}</posy>
    <defaultcontrol>100</defaultcontrol>

    <!-- HEADER: the title and the group buttons, which scroll with the grid as one page (on
         request, 2026-10-08): the panel below covers the screen and draws every row far enough down
         its cell that these sit in the space above its first row. When the panel scrolls
         (Container(101).HasPrevious: its first row is past the top), they slide up by exactly its
         row pitch, in the same time and tween as its scroll (<scrolltime> below); scrolled back to
         the top, they come back the same way - one non-reversible slide each way, as the page's. -->
    <control type="group">
        {% block header_scroll %}{% endblock %}
    <!-- TITLE ############################################################################## -->
    <!-- The film or show name for its credits, a row's title for a row's items (SeeMoreWindow.
         title()), in the Recommended rows' title style (script-plex-recommended.xml.tpl's row
         title label: font30_title, FFD2CCCE, 66000000 shadow), on request (2026-10-08). -->
    <control type="label">
        <posx>61</posx>
        <posy>{{ vscale(-17) }}</posy>
        <width>1694</width>
        <height>{{ vscale(61) }}</height>
        <font>font30_title</font>
        <align>left</align>
        <aligny>center</aligny>
        <textcolor>FFD2CCCE</textcolor>
        <shadowcolor>66000000</shadowcolor>
        <label>$INFO[Window.Property(grid.title)]</label>
    </control>

    <!-- GROUP BUTTONS ###################################################################### -->
    <!-- Cast / Crew for credits (SeeMoreWindow.GROUP_BUTTON_IDS, labelGroupButtons()): the
         Filmography screen's type buttons as they are (script-plex-filmography.xml.tpl), the group
         shown in the sidebar's active orange by its label's colour tag. A grid without groups (a
         row's) has none; its tiles start higher instead (its own layouts). -->
    <control type="grouplist" id="910">
        <visible>!String.IsEmpty(Window.Property(grid.groups))</visible>
        <posx>61</posx>
        <posy>{{ vscale(70) }}</posy>
        <width>1694</width>
        <height>{{ vscale(60) }}</height>
        <orientation>horizontal</orientation>
        <align>left</align>
        <itemgap>3</itemgap>
        <usecontrolcoords>true</usecontrolcoords>
        <onleft>9000</onleft>
        <onright>noop</onright>
        <onup>noop</onup>
        <ondown>101</ondown>
        {% for i in range(4) %}
        <control type="button" id="{{ 911 + i }}">
            <visible>!String.IsEmpty(Window.Property(group.{{ i }}.label))</visible>
            <width>auto</width>
            <height>{{ vscale(60) }}</height>
            <font>font12</font>
            <align>center</align>
            <aligny>center</aligny>
            <textoffsetx>24</textoffsetx>
            <textcolor>FFFFFFFF</textcolor>
            <focusedcolor>FFFFFFFF</focusedcolor>
            <texturenofocus colordiffuse="22FFFFFF" border="10">script.plex/white-square-rounded.png</texturenofocus>
            <texturefocus colordiffuse="55FFFFFF" border="10">script.plex/white-square-rounded.png</texturefocus>
            <label>$INFO[Window.Property(group.{{ i }}.label)]</label>
        </control>
        {% endfor %}
    </control>
    </control>

    <!-- GRID ############################################################################### -->
    <!-- x: the rows' own clip recipe (script-plex-pre_play.xml.tpl's list 400) - 53, so each
         tile's 5 + 3 inset puts the art on x=113 and the clip edge on x=105, clear of the
         collapsed sidebar rail. y: from the screen's top - a container clips its items to its own
         box, so anything short of the screen's edges showed rows cut off mid-screen (live,
         2026-10-08) - to 60 below its bottom (see the top). Each tile sits far enough down its cell
         (its layouts' own offset - the library grid's way, script-plex-posters.xml.tpl) that the
         header shows above the first row; a tile's foot runs into the next cell's empty top.
         Scrolled, the row above's foot shows there instead, as on any scrolling page. -->
    <control type="group" id="100">
        <visible>Integer.IsGreater(Container(101).NumItems,0) + String.IsEmpty(Window.Property(drawing))</visible>
        <defaultcontrol>101</defaultcontrol>
        <posx>53</posx>
        <posy>{{ vscale(-125) }}</posy>
        <control type="panel" id="101">
            <!-- Mouse: only where the tiles are, not over the header above them -->
            <hitrect x="0" y="{% block hitrect_y %}{{ vscale(265) }}{% endblock %}" w="1867" h="{{ vscale(874) }}" />
            <posx>0</posx>
            <posy>0</posy>
            <width>1867</width>
            <height>{{ vscale(1139) }}</height>
            <onleft>9000</onleft>
            <onright>noop</onright>
            <onup condition="!String.IsEmpty(Window.Property(grid.groups))">910</onup>
            <onup>noop</onup>
            <!-- wraparound=false alone didn't stop top<->bottom wrapping in the Collection grid -
                 'noop' is needed too (script-plex-subdir.xml.tpl). -->
            <ondown>noop</ondown>
            <!-- The header's slide matches this exactly (time and tween) -->
            <scrolltime tween="quadratic" easing="out">200</scrolltime>
            <orientation>vertical</orientation>
            <preloaditems>2</preloaditems>
            <wraparound>false</wraparound>
            {% block layouts %}{% endblock %}
        </control>
    </control>
</control>
{% endblock content %}
