{% extends "default.xml.tpl" %}
{% block headers %}<defaultcontrol>101</defaultcontrol>{% endblock %}
{% block header_topleft %}{% endblock %}
{% block header %}
    {{ super() }}
    {% include "includes/sidebar.xml.tpl" %}
    <!-- Declared last so groups 802/901 draw on top - see script-plex-pre_play.xml.tpl's own copy
         of this include for the full reasoning (this window is one of the seven real hosted-shell
         types too, same _sidebarTarget()-aware Python side, same onClick forwarding). -->
    {% include "includes/sidebar_dropdowns.xml.tpl" %}
{% endblock header %}
{% block content %}
{# Redesigned on the Artist screen's model (script-plex-artist.xml.tpl): hero text in that screen's
   own type and colours, its button row, and a track list built to its Popular Tracks row recipe.
   The cover is the one thing the Artist screen has no equivalent for - it stays, at 370x370 with
   the skin's usual rounded corners and card shadow, with the hero text to its right and the list
   running the full width below both. #}
<control type="group" id="50">
    <!-- Slide right while the sidebar rail is expanded (focused), matching every other screen. -->
    <animation effect="slide" end="220,0" time="200" tween="sine" easing="inout" condition="ControlGroup(9000).HasFocus(0)">Conditional</animation>
    <!-- posx=52/posy=135: the Artist screen's own outer offsets, so this screen's left column
         lands on the same absolute x=113 every heading in the skin aligns to. -->
    <posx>52</posx>
    <posy>{{ vscale(135) }}</posy>
    <defaultcontrol>101</defaultcontrol>

    <!-- COVER ############################################################################## -->
    <!-- Card recipe shared with the grid tiles and the Artist screen's album rows: shadow box =
         art + 24 at (-3,-3), art rounded by masks/square-mask.png, fallback layer underneath for
         albums with no art of their own. -->
    <control type="image">
        <posx>58</posx>
        <posy>{{ vscale(-3) }}</posy>
        <width>394</width>
        <height>{{ vscale(394) }}</height>
        <texture border="24">script.plex/drop-shadow-directional.png</texture>
    </control>
    <control type="image">
        <posx>61</posx>
        <posy>0</posy>
        <width>370</width>
        <height>{{ vscale(370) }}</height>
        <texture diffuse="script.plex/masks/square-mask.png">script.plex/thumb_fallbacks/music.png</texture>
    </control>
    <control type="image">
        <posx>61</posx>
        <posy>0</posy>
        <width>370</width>
        <height>{{ vscale(370) }}</height>
        <texture background="true" diffuse="script.plex/masks/square-mask.png">$INFO[Window.Property(album.thumb)]</texture>
        <aspectratio scalediffuse="false">scale</aspectratio>
    </control>

    <!-- HERO TEXT ########################################################################## -->
    <!-- x=471: the cover's right edge (431) plus a 40px gutter. All three lines share it. -->
    <control type="label">
        <!-- The album name, in the Artist screen's own title treatment (font45_title, FFD2CCCE,
             top-aligned, marquee) - that screen shows the artist name here, which on this screen
             moves down to the line below. -->
        <posx>471</posx>
        <posy>0</posy>
        <width>1250</width>
        <height>{{ vscale(61) }}</height>
        <font>font45_title</font>
        <align>left</align>
        <aligny>top</aligny>
        <scroll>true</scroll>
        <scrollspeed>35</scrollspeed>
        <textcolor>FFD2CCCE</textcolor>
        <label>$INFO[Window.Property(album.title)]</label>
    </control>
    <control type="label">
        <!-- The artist, styled exactly as the meta line below it rather than as a second title.
             posy=68 centres its 30px box in the gap between the title's box (ends at 61) and the
             meta row (starts at 105): 7px clear above and below. -->
        <posx>471</posx>
        <posy>{{ vscale(68) }}</posy>
        <!-- 700, not the meta row's 1250: this line is a click target (306 below) as well as text,
             and a target spanning the full column would make most of an empty row clickable. -->
        <width>700</width>
        <height>{{ vscale(30) }}</height>
        <font>font10</font>
        <align>left</align>
        <textcolor>FFD2CCCE</textcolor>
        <shadowcolor>66000000</shadowcolor>
        <label>$INFO[Window.Property(artist.title)]</label>
    </control>
    <!-- Click target over the artist line, opening that artist's own screen (artistButtonClicked(),
         tracks.py - the same place the More menu's "Go to artist" goes). Same construction as the
         summary target below and on the Artist/Seasons screens: a real button, since a label has no
         click or focus of its own, with both textures explicitly "-" so Kodi doesn't fall back to
         its default button look, and the highlight drawn as a separate image so it can sit proud of
         the hit area. -->
    <control type="button" id="306">
        <posx>471</posx>
        <posy>{{ vscale(68) }}</posy>
        <width>700</width>
        <height>{{ vscale(30) }}</height>
        <onup>200</onup>
        <ondown condition="!String.IsEmpty(Window.Property(summary))">305</ondown>
        <ondown>300</ondown>
        <onleft>9000</onleft>
        <label> </label>
        <texturenofocus>-</texturenofocus>
        <texturefocus>-</texturefocus>
    </control>
    <control type="image">
        <visible>Control.HasFocus(306)</visible>
        <posx>466</posx>
        <posy>{{ vscale(63) }}</posy>
        <width>710</width>
        <height>{{ vscale(40) }}</height>
        <colordiffuse>33FFFFFF</colordiffuse>
        <texture border="10">script.plex/white-square-rounded.png</texture>
    </control>
    <control type="label">
        <!-- Release date then genres, both from album.meta (updateProperties(), tracks.py), joined
             with the same " / " the Artist screen's own genre line uses between genres. -->
        <posx>471</posx>
        <posy>{{ vscale(105) }}</posy>
        <width>1250</width>
        <height>{{ vscale(30) }}</height>
        <font>font10</font>
        <align>left</align>
        <textcolor>FFD2CCCE</textcolor>
        <shadowcolor>66000000</shadowcolor>
        <label>$INFO[Window.Property(album.meta)]</label>
    </control>

    <!-- Summary, in the Artist screen's own treatment (813x90, font10, FFD2CCCE, autoscrolling
         rather than scrollbar-driven). posy=207 keeps that screen's exact gap from the genre row:
         it puts its summary at 277 with the genre line at 175, so 102 below it, and this screen's
         meta row sits at 105. No invisible info-dialog button over it, unlike that screen - this
         window has no SUMMARY_BUTTON_ID handler to wire one to. -->
    <control type="textbox">
        <posx>471</posx>
        <posy>{{ vscale(207) }}</posy>
        <width>813</width>
        <height>{{ vscale(90) }}</height>
        <font>font10</font>
        <align>left</align>
        <textcolor>FFD2CCCE</textcolor>
        <shadowcolor>66000000</shadowcolor>
        <scrolltime>200</scrolltime>
        <autoscroll delay="2000" time="2000" repeat="10000">true</autoscroll>
        <label>$INFO[Window.Property(summary)]</label>
    </control>
    <!-- Click target over the summary, opening the same popup the Artist and Seasons screens'
         own summaries do (summaryButtonClicked(), tracks.py). -->
    <control type="button" id="305">
        <!-- Gone entirely when the album has no summary: an enabled target over empty space gave a
             focusable stop in the middle of the header that opened a blank popup. The two nav tags
             that route through it carry the same condition, so the chain closes up rather than
             dead-ending on a control that isn't there (306's ondown and 300's onup below). -->
        <visible>!String.IsEmpty(Window.Property(summary))</visible>
        <posx>471</posx>
        <posy>{{ vscale(207) }}</posy>
        <width>813</width>
        <height>{{ vscale(90) }}</height>
        <onup>306</onup>
        <ondown>300</ondown>
        <onleft>9000</onleft>
        <label> </label>
        <texturenofocus>-</texturenofocus>
        <texturefocus>-</texturefocus>
    </control>
    <control type="image">
        <visible>Control.HasFocus(305)</visible>
        <posx>466</posx>
        <posy>{{ vscale(202) }}</posy>
        <width>823</width>
        <height>{{ vscale(100) }}</height>
        <colordiffuse>33FFFFFF</colordiffuse>
        <texture border="10">script.plex/white-square-rounded.png</texture>
    </control>

    {% block buttons %}
    <!-- The Artist screen's button row verbatim - theme.artist's 70x70 icon boxes and its
         label-on-focus pills, sharing Play's and Shuffle's own measured widths since it's the same
         text at the same font. Sits under the meta line, in the hero's own column. -->
    <control type="grouplist" id="300">
        <animation effect="fade" start="0" end="100" time="200" reversible="true">VisibleChange</animation>
        <defaultcontrol>301</defaultcontrol>
        <posx>471</posx>
        <posy>{{ vscale(313) }}</posy>
        <width>1000</width>
        <height>{{ vscale(70) }}</height>
        <align>left</align>
        <!-- 305 (the summary's click target), not 200: the Artist screen's own button row routes up
             the same way, and 200 is the header GROUP - a bare container, so pressing up here was a
             dead press. The chain above this row is 305 -> 306 (the artist line) -> 200, which is
             where that screen's own summary target hands off too. -->
        <onup condition="!String.IsEmpty(Window.Property(summary))">305</onup>
        <onup>306</onup>
        <ondown>101</ondown>
        <onleft>9000</onleft>
        <itemgap>{{ theme.artist.buttongroup.itemgap }}</itemgap>
        <orientation>horizontal</orientation>
        <scrolltime tween="quadratic" easing="out">200</scrolltime>
        <usecontrolcoords>true</usecontrolcoords>

        {% with attr = theme.artist.buttons & template = "includes/themed_button.xml.tpl" & hitrect = theme.artist.buttons_hitrect & ol = "includes/episode_button_label.xml.tpl" %}
            {% include template with name="play" & id=301 & overlay=True %}
            {% include ol with id=391 & visible="Control.HasFocus(301)" & name="play" &
                label="$ADDON[script.plexmod 33020]" & label_suffix_info="" &
                label_width=50 & pill_width=112 & group_width=68 &
                onleft=301 & onright=302
            %}
            {% include template with name="shuffle" & id=302 & overlay=True %}
            {% include ol with id=392 & visible="Control.HasFocus(302)" & name="shuffle" &
                label="$ADDON[script.plexmod 32935]" & label_suffix_info="" &
                label_width=84 & pill_width=146 & group_width=102 &
                onleft=302 & onright=303
            %}
            {% include template with name="more" & id=303 & overlay=True %}
            {% include ol with id=393 & visible="Control.HasFocus(303)" & name="more" &
                label="$ADDON[script.plexmod 32307]" & label_suffix_info="" &
                label_width=60 & pill_width=122 & group_width=78 &
                onleft=303
            %}
        {% endwith %}
    </control>
    {% endblock %}

    <!-- TRACK LIST ######################################################################### -->
    <!-- No standalone heading above the list: the track count is a header ROW inside it now, the
         same shape multi-disc albums use for their disc separators (fillTracks(), tracks.py). -->
    <control type="list" id="101">
        <!-- posx=53 plus the row's own 8 puts the pill at local 61, absolute 113 - the same left
             edge as the hero text and the heading above it, and the same way Popular Tracks lands
             on it. 500 tall is exactly 5 rows of 100, so the bottom row is never clipped in half;
             the list scrolls past that. -->
        <hitrect x="113" y="535" w="1694" h="500" />
        <posx>53</posx>
        <posy>{{ vscale(400) }}</posy>
        <width>1867</width>
        <height>{{ vscale(500) }}</height>
        <onup>300</onup>
        <onleft>9000</onleft>
        <!-- Hard stop: nothing sits right of the rows any more, the scrollbar included. -->
        <onright>noop</onright>
        <!-- Kodi lists wrap top<->bottom by default - moving down off the last track was sending
             focus back to the first. wraparound=false alone doesn't stop it (an onXXX destination
             only applies once the container has exhausted its own items in that direction), so it
             takes the pair, same as the poster grid and Collection/Subdir screens. Up is already
             handled: the first row is a header, and checkForHeaderFocus() (tracks.py) re-issues the
             move, which then exits via onup. -->
        <wraparound>false</wraparound>
        <ondown>noop</ondown>
        <scrolltime>200</scrolltime>
        <orientation>vertical</orientation>
        <preloaditems>4</preloaditems>

        <!-- ITEM LAYOUT ########################################## -->
        <itemlayout height="{{ vscale(100) }}">
            <control type="group">
                <posx>8</posx>
                <posy>0</posy>
                {% include "includes/album_track_row.xml.tpl" with focused=False %}
            </control>
        </itemlayout>

        <!-- FOCUSED LAYOUT ####################################### -->
        <focusedlayout height="{{ vscale(100) }}">
            <control type="group">
                <posx>8</posx>
                <posy>0</posy>
                {% include "includes/album_track_row.xml.tpl" with focused=True %}
            </control>
        </focusedlayout>
    </control>

</control>
{% endblock content %}
