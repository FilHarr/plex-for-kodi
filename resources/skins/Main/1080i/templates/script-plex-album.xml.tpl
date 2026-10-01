{% extends "default.xml.tpl" %}
{% block headers %}<defaultcontrol>101</defaultcontrol>{% endblock %}
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
    <posy>{{ vscale(125) }}</posy>
    <defaultcontrol>101</defaultcontrol>

    <!-- COVER ############################################################################## -->
    <!-- Card recipe shared with the grid tiles and the Artist screen's album rows: shadow box =
         art + 24 at (-3,-3), art rounded by masks/square-mask.png, music.png via native fallback=
         for albums with no art of their own (not a second masked layer underneath - that bleeds
         through the corner anti-aliasing as a bright edge; see track_row.xml.tpl). -->
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
        <texture background="true" diffuse="script.plex/masks/square-mask.png" fallback="script.plex/thumb_fallbacks/music.png">$INFO[Window.Property(album.thumb)]</texture>
        <aspectratio scalediffuse="false">scale</aspectratio>
    </control>

    <!-- HERO TEXT ########################################################################## -->
    <!-- x=471: the cover's right edge (431) plus a 40px gutter. All three lines share it.
         Styled and spaced as Recommended's album hero (script-plex-recommended.xml.tpl, on request
         2026-09-30): album name font45_title white, artist font30_title FFD2CCCE, then the meta
         line and summary in font10 - each box the same distance below the name's as there
         (artist text +69, meta +127, summary +191). The whole block sits 17px higher than the
         cover's top edge: font45_title (InterUI at 45px) draws its capitals 17.1px below the top
         of its 64.4px line, so posy=-17 puts the name's capitals level with the top of the cover
         (computed from the font file, the same method as the "Just watched" heading in
         script-plex-video_player.xml.tpl). Widths stay this screen's own - it has more room. -->
    <control type="label">
        <posx>471</posx>
        <posy>{{ vscale(-17) }}</posy>
        <width>1250</width>
        <height>{{ vscale(61) }}</height>
        <font>font45_title</font>
        <align>left</align>
        <aligny>top</aligny>
        <scroll>true</scroll>
        <scrollspeed>35</scrollspeed>
        <textcolor>FFFFFFFF</textcolor>
        <label>$INFO[Window.Property(album.title)]</label>
    </control>
    <!-- The artist, and a click target opening that artist's own screen (artistButtonClicked(),
         tracks.py - the same place the More menu's "Go to artist" goes). One auto-width button that
         is the text, the hit area and the highlight (on request, 2026-09-30): Kodi measures the
         label and sizes the button to it plus textoffsetx either side, so the highlight hugs the
         name. font30_title's 42.9px line centred in the 51px box starts 4px down, at 52 - the
         +69 below the name Recommended's artist line sits at. 5px in from the left puts the text
         at x=471 with the rest. max=710 caps it; a longer name marquees while focused. -->
    <control type="button" id="306">
        <posx>466</posx>
        <posy>{{ vscale(48) }}</posy>
        <width max="710">auto</width>
        <height>{{ vscale(51) }}</height>
        <onup>200</onup>
        <ondown condition="!String.IsEmpty(Window.Property(summary))">305</ondown>
        <ondown>300</ondown>
        <onleft>9000</onleft>
        <font>font30_title</font>
        <align>left</align>
        <aligny>center</aligny>
        <textoffsetx>5</textoffsetx>
        <textcolor>FFD2CCCE</textcolor>
        <focusedcolor>FFD2CCCE</focusedcolor>
        <texturenofocus>-</texturenofocus>
        <texturefocus colordiffuse="33FFFFFF" border="10">script.plex/white-square-rounded.png</texturefocus>
        <label>$INFO[Window.Property(artist.title)]</label>
    </control>
    <control type="label">
        <!-- Release date then genres, both from album.meta (updateProperties(), tracks.py),
             bullet-separated. -->
        <posx>471</posx>
        <posy>{{ vscale(110) }}</posy>
        <width>1250</width>
        <height>{{ vscale(30) }}</height>
        <font>font10</font>
        <align>left</align>
        <textcolor>FFD2CCCE</textcolor>
        <shadowcolor>66000000</shadowcolor>
        <label>$INFO[Window.Property(album.meta)]</label>
    </control>

    <!-- Summary, in the Artist screen's own treatment (813x90, font10, FFD2CCCE, autoscrolling
         rather than scrollbar-driven) - also Recommended's. -->
    <control type="textbox">
        <posx>471</posx>
        <posy>{{ vscale(174) }}</posy>
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
        <posy>{{ vscale(174) }}</posy>
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
        <posy>{{ vscale(169) }}</posy>
        <width>823</width>
        <height>{{ vscale(100) }}</height>
        <colordiffuse>33FFFFFF</colordiffuse>
        <texture border="10">script.plex/white-square-rounded.png</texture>
    </control>

    {% block buttons %}
    <!-- The Artist screen's button row verbatim - theme.artist's 70x70 icon boxes and its
         label-on-focus pills, sharing Play's and Shuffle's own measured widths since it's the same
         text at the same font. Sits under the summary, in the hero's own column. -->
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
                label_width=51 & pill_width=113 & group_width=69 &
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
                label_width=61 & pill_width=123 & group_width=79 &
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
