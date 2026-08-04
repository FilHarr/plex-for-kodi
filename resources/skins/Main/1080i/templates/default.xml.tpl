{% extends "base.xml.tpl" %}{# this extends base and adds background and default header blocks #}
{% block controls %}
    {% block background %}
        {% include "includes/default_background.xml.tpl" %}
    {% endblock %}
    <!-- block content -->
    {% block content %}{% endblock %}

    {% block header %}
    <control type="group" id="200">
        {% block header_anim %}<animation effect="slide" end="0,{{ vscale(-300) }}" time="200" tween="quadratic" easing="out" condition="!String.IsEmpty(Window.Property(on.extras)) + !ControlGroup(200).HasFocus(0)">Conditional</animation>{% endblock %}
        <defaultcontrol always="true">201</defaultcontrol>
        <posx>0</posx>
        <posy>0</posy>
        <width>1920</width>
        <height>{{ vscale(135) }}</height>
        {% block header_bgfade %}
        <control type="image">
            <animation effect="fade" start="0" end="100" time="200" tween="quadratic" easing="out" reversible="true">VisibleChange</animation>
            <visible>ControlGroup(200).HasFocus(0) + !String.IsEmpty(Window.Property(on.extras))</visible>
            <posx>0</posx>
            <posy>0</posy>
            <width>1920</width>
            <height>{{ vscale(135) }}</height>
            <texture>script.plex/white-square.png</texture>
            <colordiffuse>C0000000</colordiffuse>
        </control>
        {% endblock %}
        {% block header_topleft %}
        <control type="grouplist">
            <posx>60</posx>
            <posy>{{ vscale(47.5) }}</posy>
            <width>1000</width>
            <height>{{ vscale(40) }}</height>
            <align>left</align>
            <itemgap>60</itemgap>
            <orientation>horizontal</orientation>
            <ondown>50</ondown>
            <control type="group">
                <width>40</width>
                <height>{{ vscale(40) }}</height>
                <control type="button" id="201">
                    <animation effect="zoom" start="100" end="144" time="100" center="20,{{ vscale(20) }}" reversible="false">Focus</animation>
                    <animation effect="zoom" start="144" end="100" time="100" center="20,{{ vscale(20) }}" reversible="false">UnFocus</animation>
                    <width>40</width>
                    <height>{{ vscale(40) }}</height>
                    <onright>202</onright>
                    <ondown>50</ondown>
                    <font>font12</font>
                    <focusedcolor>FF000000</focusedcolor>
                    <texturefocus colordiffuse="FFE5A00D">script.plex/buttons/home-focus.png</texturefocus>
                    <texturenofocus colordiffuse="99FFFFFF">script.plex/buttons/home.png</texturenofocus>
                    <label> </label>
                </control>
            </control>
            {% block topleft_add %}{% endblock %}
            <control type="group">
                <width>40</width>
                <height>{{ vscale(40) }}</height>
                <control type="button" id="202">
                    <animation effect="zoom" start="100" end="144" time="100" center="20,{{ vscale(20) }}" reversible="false">Focus</animation>
                    <animation effect="zoom" start="144" end="100" time="100" center="20,{{ vscale(20) }}" reversible="false">UnFocus</animation>
                    <width>40</width>
                    <height>{{ vscale(40) }}</height>
                    {% block header_search_onright %}<onright>204</onright>{% endblock %}
                    <onleft>201</onleft>
                    <ondown>50</ondown>
                    <font>font12</font>
                    <focusedcolor>FF000000</focusedcolor>
                    <texturefocus colordiffuse="FFE5A00D">script.plex/buttons/search-focus.png</texturefocus>
                    <texturenofocus colordiffuse="99FFFFFF">script.plex/buttons/search.png</texturenofocus>
                    <label> </label>
                </control>
            </control>
        </control>
        {% endblock header_topleft %}
        {% block header_sidebar %}{% endblock %}
        {% block header_middle_add %}{% endblock %}
        <control type="label">
            <right>60</right>
            <posy>{{ vscale(35) }}</posy>
            <width>200</width>
            <height>{{ vscale(65) }}</height>
            <font>font12</font>
            <align>right</align>
            <aligny>center</aligny>
            <textcolor>FFFFFFFF</textcolor>
            <label>$INFO[System.Time]</label>
        </control>
        {# declared after the time label so the popout below paints over it instead of the other way round #}
        <control type="group">
            <visible>Player.HasAudio + String.IsEmpty(Window(10000).Property(script.plex.theme_playing))</visible>
            {# 360r keeps a ~32px gap between the collapsed thumbnail and the time label to its right #}
            <posx>360r</posx>
            <posy>0</posy>
            {# collapsed to just the art thumbnail (63x63, +50% over the original 42x42); the rest pops out only while it's focused #}
            <control type="group">
                <animation effect="zoom" start="100" end="110" time="100" center="31.5,{{ vscale(67.5) }}" reversible="false">Focus</animation>
                <animation effect="zoom" start="110" end="100" time="100" center="31.5,{{ vscale(67.5) }}" reversible="false">UnFocus</animation>
                <control type="button" id="204">
                    <posx>0</posx>
                    <posy>{{ vscale(36) }}</posy>
                    <width>63</width>
                    <height>{{ vscale(63) }}</height>
                    {% block header_audiowidget_onleft %}<onleft>202</onleft>{% endblock %}
                    {% block header_audiowidget_onright %}{% endblock %}
                    <ondown>50</ondown>
                    <texturefocus>-</texturefocus>
                    <texturenofocus>-</texturenofocus>
                    <label> </label>
                </control>
                <control type="image">
                    <posx>0</posx>
                    <posy>{{ vscale(36) }}</posy>
                    <width>63</width>
                    <height>{{ vscale(63) }}</height>
                    <texture>$INFO[Player.Art(thumb)]</texture>
                </control>
                {# selected.png (the hub thumbnails' focus-ring asset) turned out to be the wrong tool here: its
                   border attribute only resizes how much of the image's corner gets 9-sliced, not the actual
                   stroke width along the straight edges - that width is baked into the source pixels, so
                   border="2" looked identical to border="5". Four thin rectangles - the same technique the
                   current-season underline just below uses - give exact, direct control over thickness instead #}
                <control type="group">
                    <visible>Control.HasFocus(204)</visible>
                    <control type="image">
                        <posx>-5</posx>
                        <posy>{{ vscale(31) }}</posy>
                        <width>73</width>
                        <height>2</height>
                        <texture>script.plex/white-square.png</texture>
                        <colordiffuse>FFE5A00D</colordiffuse>
                    </control>
                    <control type="image">
                        <posx>-5</posx>
                        <posy>{{ vscale(102) }}</posy>
                        <width>73</width>
                        <height>2</height>
                        <texture>script.plex/white-square.png</texture>
                        <colordiffuse>FFE5A00D</colordiffuse>
                    </control>
                    <control type="image">
                        <posx>-5</posx>
                        <posy>{{ vscale(31) }}</posy>
                        <width>2</width>
                        <height>{{ vscale(73) }}</height>
                        <texture>script.plex/white-square.png</texture>
                        <colordiffuse>FFE5A00D</colordiffuse>
                    </control>
                    <control type="image">
                        <posx>66</posx>
                        <posy>{{ vscale(31) }}</posy>
                        <width>2</width>
                        <height>{{ vscale(73) }}</height>
                        <texture>script.plex/white-square.png</texture>
                        <colordiffuse>FFE5A00D</colordiffuse>
                    </control>
                </control>
            </control>

            <control type="group">
                <visible>Control.HasFocus(204)</visible>
                <animation effect="fade" start="0" end="100" time="120" reversible="true">Visible</animation>
                {# extends over the time label by design - this group is declared after it, so it draws on top rather than shifting it #}
                <control type="image">
                    <posx>75</posx>
                    <posy>{{ vscale(30) }}</posy>
                    <width>260</width>
                    <height>{{ vscale(75) }}</height>
                    <texture colordiffuse="E0000000" border="10">script.plex/white-square-rounded.png</texture>
                </control>
                <control type="label">
                    <posx>90</posx>
                    <posy>{{ vscale(40) }}</posy>
                    <width>230</width>
                    <height>{{ vscale(20) }}</height>
                    <font>font10</font>
                    <align>left</align>
                    <aligny>center</aligny>
                    <textcolor>FFFFFFFF</textcolor>
                    <info>MusicPlayer.Artist</info>
                </control>
                <control type="label">
                    <posx>90</posx>
                    <posy>{{ vscale(64) }}</posy>
                    <width>230</width>
                    <height>{{ vscale(20) }}</height>
                    <font>font10</font>
                    <align>left</align>
                    <aligny>center</aligny>
                    <textcolor>FFFFFFFF</textcolor>
                    <info>MusicPlayer.Title</info>
                </control>
                <control type="progress">
                    <description>Progressbar</description>
                    <posx>90</posx>
                    <posy>{{ vscale(94) }}</posy>
                    <width>230</width>
                    <height>{{ vscale(1) }}</height>
                    <texturebg colordiffuse="9AFFFFFF">script.plex/white-square-1px.png</texturebg>
                    <lefttexture>-</lefttexture>
                    <midtexture colordiffuse="FFCC7B19">script.plex/white-square-1px.png</midtexture>
                    <righttexture>-</righttexture>
                    <overlaytexture>-</overlaytexture>
                    <info>Player.Progress</info>
                </control>
            </control>
        </control>
    </control>

    <control type="group">
        <visible>!String.IsEmpty(Window.Property(search.dialog))</visible>
        <control type="group" >
            <visible>!String.IsEmpty(Window.Property(search.dialog.hasresults))</visible>
            <control type="image">
                <posx>0</posx>
                <posy>0</posy>
                <width>1920</width>
                <height>1080</height>
                <texture>script.plex/home/background-fallback.png</texture>
                {% include "includes/scale_background.xml.tpl" %}
            </control>
            <control type="image">
                <posx>0</posx>
                <posy>0</posy>
                <width>1920</width>
                <height>1080</height>
                <texture background="true">$INFO[Window.Property(background)]</texture>
                {% include "includes/scale_background.xml.tpl" %}
            </control>
        </control>
        <control type="image">
            <posx>0</posx>
            <posy>0</posy>
            <width>1920</width>
            <height>1080</height>
            <texture colordiffuse="99606060">script.plex/white-square.png</texture>
        </control>
    </control>
    {% endblock header %}
{% endblock controls %}