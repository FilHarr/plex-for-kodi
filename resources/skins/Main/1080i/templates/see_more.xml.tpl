{% extends "default.xml.tpl" %}
{# The "See more" grid (lib/windows/see_more.py, spec ~/.claude/plans/see-all-grid.md): every item
   behind a row's "See more" tile, in that row's own tile. Not a screen of its own - each tile shape
   extends this with its panel's item size and layouts (blocks below), as script-plex-posters-small
   extends library_posters: Kodi gives every cell of a panel the same size, so a grid's shape is
   fixed. On BoundedGridWindow (collection.py), so no sort, filter or view-type chrome.

   Block layouts: the panel's itemlayout and focusedlayout, whose width and height are its column
   and row pitch - 6 columns fit the 1867 the rows use at 270 (cast & crew) or 272 (posters,
   squares). #}
{% block headers %}<defaultcontrol>101</defaultcontrol>{% endblock %}
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
    <!-- The Filmography screen's outer offsets: the title and the art's left edge land on x=113
         with every other screen's headings. -->
    <posx>52</posx>
    <posy>{{ vscale(125) }}</posy>
    <defaultcontrol>101</defaultcontrol>

    <!-- HEADER: the title and the group buttons, which scroll with the grid as one page (on
         request, 2026-10-08): the panel below covers the screen and draws every row far enough down
         its cell that these sit in the space above its first row. When the panel scrolls
         (Container(101).HasPrevious: its first row is past the top), they slide up by exactly its
         row pitch, 360, in the same time and tween as its scroll (<scrolltime> below), so nothing
         moves relative to anything else; scrolled back to the top, they come back the same way.
         Two animations, one each way, neither reversible: a reversed ease-out plays as an ease-in,
         which parted the header from the row coming back down with it (live, 2026-10-08). Going
         up, the first plays and the second resets to nothing; coming back, the first resets and
         the second plays from -360 - the same frame, so no jump. Whichever is true when the screen
         opens is applied at its end without playing (Kodi's initial condition). -->
    <control type="group">
        <animation effect="slide" start="0,0" end="0,{{ vscale(-360) }}" time="200" tween="quadratic" easing="out" reversible="false" condition="Container(101).HasPrevious">Conditional</animation>
        <animation effect="slide" start="0,{{ vscale(-360) }}" end="0,0" time="200" tween="quadratic" easing="out" reversible="false" condition="!Container(101).HasPrevious">Conditional</animation>
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
         shown in the sidebar's active orange by its label's colour tag. Gone for a grid with no
         groups, and the panel moves up into their place (grid.groups). -->
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
         collapsed sidebar rail. y: the whole screen - a container clips its items to its own box, so
         anything short of the screen's edges showed rows cut off mid-screen (live, 2026-10-08).
         Each tile sits 277 down its cell (the layouts' own offset - the library grid's way,
         script-plex-posters.xml.tpl), so the first row starts under the buttons and the header
         shows above it; a tile's foot runs into the next cell's empty top. Scrolled, the row
         above's foot shows there instead, as on any scrolling page.
         Kodi scrolls a panel as focus passes the last row its height holds whole - height over
         row pitch, rounded down - so that has to be two: a third would sit mostly below the screen
         with focus on it. Hence a 360 pitch (the layouts') and 1079 tall, not 1080: 1079 / 360
         holds two, and the row below peeks in at the bottom. -->
    <control type="group" id="100">
        <visible>Integer.IsGreater(Container(101).NumItems,0) + String.IsEmpty(Window.Property(drawing))</visible>
        <posx>53</posx>
        <posy>{{ vscale(-125) }}</posy>
        <control type="panel" id="101">
            <!-- Mouse: only where the tiles are, not over the header above them -->
            <hitrect x="0" y="{{ vscale(265) }}" w="1867" h="{{ vscale(814) }}" />
            <posx>0</posx>
            <posy>0</posy>
            <width>1867</width>
            <height>{{ vscale(1079) }}</height>
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
