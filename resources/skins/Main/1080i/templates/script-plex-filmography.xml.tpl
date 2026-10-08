{% extends "default.xml.tpl" %}
{% block headers %}<defaultcontrol>101</defaultcontrol>{% endblock %}
{% block header %}
    {{ super() }}
    {% include "includes/sidebar.xml.tpl" %}
    <!-- Declared last so groups 802/901 draw on top - see script-plex-pre_play.xml.tpl's own copy
         of this include for the full reasoning. -->
    {% include "includes/sidebar_dropdowns.xml.tpl" %}
{% endblock header %}
{% block content %}
{# A person's whole filmography as Discover has it (filmography.py), on Plex's own filmography
   screen's plan: a button per credit type with its count, over that type's credits, newest
   first - the year, the title, "as" the role, and the server it's on if it's in a library there.
   On the Playlist/Album screens' frame: the same outer offsets, heading type and row pill. #}
<control type="group" id="50">
    <!-- Slide right while the sidebar rail is expanded (focused), matching every other screen. -->
    <animation effect="slide" end="220,0" time="200" tween="sine" easing="inout" condition="ControlGroup(9000).HasFocus(0)">Conditional</animation>
    <!-- The Album screen's own outer offsets: the left column lands on x=113 with every heading. -->
    <posx>52</posx>
    <posy>{{ vscale(125) }}</posy>
    <defaultcontrol>101</defaultcontrol>

    <!-- HEADING ############################################################################ -->
    <!-- "Stan Lee Filmography": the person's name, then "Filmography" straight after it in the
         Playlist screen's subtitle grey (on request, 2026-10-08) - its title line, at the left
         column. -->
    <control type="label">
        <posx>61</posx>
        <posy>{{ vscale(-17) }}</posy>
        <width>1694</width>
        <height>{{ vscale(61) }}</height>
        <font>font45_title</font>
        <align>left</align>
        <aligny>top</aligny>
        <textcolor>FFFFFFFF</textcolor>
        <label>$INFO[Window.Property(person.name)] [COLOR FFD2CCCE]$ADDON[script.plexmod 35160][/COLOR]</label>
    </control>

    <!-- TYPE BUTTONS ####################################################################### -->
    <!-- One per credit type (FilmographyWindow.TYPE_BUTTON_IDS, onCredits()), labelled "Producer
         (126)" and so on, gone without one. Search's type buttons (script-plex-search.xml.tpl):
         a rounded tile, 22FFFFFF at rest and 55FFFFFF focused, 60 tall, font12, 3 apart, the
         type shown in the sidebar's active orange - here by its label's own colour tag
         (showType()), since each is sized to its label (width auto) rather than a fixed tile.
         A click shows the type, as Search's do. -->
    <control type="grouplist" id="910">
        <visible>String.IsEmpty(Window.Property(loading))</visible>
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
        <onup condition="Player.HasAudio + String.IsEmpty(Window(10000).Property(script.plex.theme_playing))">204</onup>
        <onup>noop</onup>
        <ondown>101</ondown>
        {% for i in range(8) %}
        <control type="button" id="{{ 911 + i }}">
            <visible>!String.IsEmpty(Window.Property(type.{{ i }}.label))</visible>
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
            <label>$INFO[Window.Property(type.{{ i }}.label)]</label>
        </control>
        {% endfor %}
    </control>

    <!-- Loading, and nothing found -->
    <control type="image">
        <visible>!String.IsEmpty(Window.Property(loading))</visible>
        <posx>876</posx>
        <posy>{{ vscale(400) }}</posy>
        <width>64</width>
        <height>{{ vscale(64) }}</height>
        <texture>script.plex/indicators/busy-photo.gif</texture>
    </control>
    <control type="label">
        <visible>!String.IsEmpty(Window.Property(no.credits))</visible>
        <posx>61</posx>
        <posy>{{ vscale(400) }}</posy>
        <width>1694</width>
        <height>{{ vscale(60) }}</height>
        <font>font13</font>
        <align>center</align>
        <aligny>center</aligny>
        <textcolor>99FFFFFF</textcolor>
        <label>$ADDON[script.plexmod 35163]</label>
    </control>

    <!-- CREDIT LIST ######################################################################## -->
    <!-- The Album/Playlist screens' track list box and row pill (includes/playlist_row.xml.tpl),
         8 rows of 100 showing (to 1075 - on request, 2026-10-08), without art: the year in a column of its own, then the title with
         "as" its role after it in grey (one label - createListItem() - so the role follows the
         title), and "On <server>" right-aligned in the accent for one in a library. -->
    <control type="list" id="101">
        <posx>53</posx>
        <posy>{{ vscale(150) }}</posy>
        <width>1867</width>
        <height>{{ vscale(800) }}</height>
        <onup>910</onup>
        <onleft>9000</onleft>
        <onright>noop</onright>
        <ondown>noop</ondown>
        <wraparound>false</wraparound>
        <scrolltime>200</scrolltime>
        <orientation>vertical</orientation>
        <preloaditems>4</preloaditems>
        {% for focused in (False, True) %}
        <{% if focused %}focusedlayout{% else %}itemlayout{% endif %} height="{{ vscale(100) }}">
            <control type="group">
                <posx>8</posx>
                <posy>0</posy>
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
                <control type="label">
                    <posx>30</posx>
                    <posy>0</posy>
                    <width>80</width>
                    <height>{{ vscale(100) }}</height>
                    <font>font10</font>
                    <align>left</align>
                    <aligny>center</aligny>
                    <textcolor>AAFFFFFF</textcolor>
                    <label>$INFO[ListItem.Property(year)]</label>
                </control>
                <control type="label">
                    <scroll>{% if focused %}Control.HasFocus(101){% else %}false{% endif %}</scroll>
                    <posx>120</posx>
                    <posy>0</posy>
                    <width>1224</width>
                    <height>{{ vscale(100) }}</height>
                    <font>font10</font>
                    <align>left</align>
                    <aligny>center</aligny>
                    <textcolor>FFFFFFFF</textcolor>
                    <label>$INFO[ListItem.Label]</label>
                </control>
                <control type="label">
                    <posx>1354</posx>
                    <posy>0</posy>
                    <width>310</width>
                    <height>{{ vscale(100) }}</height>
                    <font>font10</font>
                    <align>right</align>
                    <aligny>center</aligny>
                    <textcolor>FFE5A00D</textcolor>
                    <label>$INFO[ListItem.Property(server)]</label>
                </control>
            </control>
        </{% if focused %}focusedlayout{% else %}itemlayout{% endif %}>
        {% endfor %}
    </control>
</control>
{% endblock content %}
