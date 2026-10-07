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
{# Restyled on the Album screen (script-plex-album.xml.tpl), on request 2026-10-07: the same cover,
   hero text, button row and pill track list, at the same coordinates. Where a playlist has no
   counterpart to an album's field, the slot carries the playlist's own: count and runtime stand
   in the artist line's place (plain text - there's nowhere for it to go), as on Recommended's
   playlist hero, and the meta line says "Smart playlist" for a smart one. Rows are includes/playlist_row.xml.tpl - the album row plus each item's art. #}
<control type="group" id="50">
    <!-- Slide right while the sidebar rail is expanded (focused), matching every other screen. -->
    <animation effect="slide" end="220,0" time="200" tween="sine" easing="inout" condition="ControlGroup(9000).HasFocus(0)">Conditional</animation>
    <!-- The Album screen's own outer offsets: the left column lands on x=113 with every heading. -->
    <posx>52</posx>
    <posy>{{ vscale(125) }}</posy>
    <defaultcontrol>101</defaultcontrol>

    <!-- COVER ############################################################################## -->
    <!-- The Album screen's cover recipe. The fallback is the playlist type's (playlist.thumb.fallback,
         setProperties(), playlist.py); an empty playlist has no composite and gets that image as its
         thumb by another path (util.standInThumb()). -->
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
        <texture background="true" diffuse="script.plex/masks/square-mask.png" fallback="$INFO[Window.Property(playlist.thumb.fallback)]">$INFO[Window.Property(playlist.thumb)]</texture>
        <aspectratio scalediffuse="false">scale</aspectratio>
    </control>

    <!-- HERO TEXT ########################################################################## -->
    <!-- The Album screen's hero lines at its positions - see that file for the arithmetic. -->
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
        <label>$INFO[Window.Property(playlist.title)]</label>
    </control>
    <!-- "24 tracks • 1h 32m" (util.playlistSubtitle(), the line Recommended's playlist hero shows),
         in the artist line's place and type. The same 51px box, centred, so the text sits exactly
         where the Album screen's artist name does. -->
    <control type="label">
        <posx>471</posx>
        <posy>{{ vscale(48) }}</posy>
        <width>1250</width>
        <height>{{ vscale(51) }}</height>
        <font>font30_title</font>
        <align>left</align>
        <aligny>center</aligny>
        <textcolor>FFD2CCCE</textcolor>
        <label>$INFO[Window.Property(playlist.subtitle)]</label>
    </control>
    <control type="label">
        <!-- "Smart playlist" for a smart one, otherwise empty (setProperties(), playlist.py). -->
        <posx>471</posx>
        <posy>{{ vscale(110) }}</posy>
        <width>1250</width>
        <height>{{ vscale(30) }}</height>
        <font>font10</font>
        <align>left</align>
        <textcolor>FFD2CCCE</textcolor>
        <shadowcolor>66000000</shadowcolor>
        <label>$INFO[Window.Property(playlist.meta)]</label>
    </control>

    <!-- The playlist's description, if it has one, in the Album screen's summary treatment. -->
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
    <!-- Click target over the summary, opening the summary popup (summaryButtonClicked(),
         playlist.py). Gone with no summary, as on the Album screen. Up goes to the header group, as
         the Album screen's artist line (the next stop up there) does. -->
    <control type="button" id="305">
        <visible>!String.IsEmpty(Window.Property(summary))</visible>
        <posx>471</posx>
        <posy>{{ vscale(174) }}</posy>
        <width>813</width>
        <height>{{ vscale(90) }}</height>
        <onup>200</onup>
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
    <!-- The Album screen's button row, less More: this screen has never had a menu to put behind
         it (its one entry, "Play Next", went from every screen). -->
    <control type="grouplist" id="300">
        <!-- Gone for an empty playlist: there's nothing to play (playlistListClicked(), playlist.py,
             would ask it for a current item it doesn't have). -->
        <visible>Integer.IsGreater(Container(101).NumItems,0)</visible>
        <animation effect="fade" start="0" end="100" time="200" reversible="true">VisibleChange</animation>
        <defaultcontrol>301</defaultcontrol>
        <posx>471</posx>
        <posy>{{ vscale(313) }}</posy>
        <width>1000</width>
        <height>{{ vscale(70) }}</height>
        <align>left</align>
        <onup condition="!String.IsEmpty(Window.Property(summary))">305</onup>
        <onup>200</onup>
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
                onleft=302
            %}
        {% endwith %}
    </control>
    {% endblock %}

    <!-- ITEM LIST ########################################################################## -->
    <!-- The Album screen's track list: same box, 5 rows of 100 showing, no scrollbar, no wrap. No
         header row - the count is in the hero, and the list's positions are the playlist's own
         (playlist.py fills and plays by position). -->
    <control type="list" id="101">
        <hitrect x="113" y="535" w="1694" h="500" />
        <posx>53</posx>
        <posy>{{ vscale(400) }}</posy>
        <width>1867</width>
        <height>{{ vscale(500) }}</height>
        <onup>300</onup>
        <onleft>9000</onleft>
        <onright>noop</onright>
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
                {% include "includes/playlist_row.xml.tpl" with focused=False %}
            </control>
        </itemlayout>

        <!-- FOCUSED LAYOUT ####################################### -->
        <focusedlayout height="{{ vscale(100) }}">
            <control type="group">
                <posx>8</posx>
                <posy>0</posy>
                {% include "includes/playlist_row.xml.tpl" with focused=True %}
            </control>
        </focusedlayout>
    </control>

</control>
{% endblock content %}
