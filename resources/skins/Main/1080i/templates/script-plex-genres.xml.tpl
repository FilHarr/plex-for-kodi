{% extends "library.xml.tpl" %}
{% block headers %}<defaultcontrol>50</defaultcontrol>{% endblock %}

{# Genres predates the sidebar rollout and isn't part of it - restore library.xml.tpl's
   original top-left nav (Home/Search buttons) and focus targets verbatim so this screen
   is unaffected. #}
{% block header_defaultcontrol %}<defaultcontrol always="true">201</defaultcontrol>{% endblock %}
{% block header_topleft %}
<control type="grouplist">
    <posx>60</posx>
    <posy>{{ vscale(47.5) }}</posy>
    <width>1000</width>
    <height>{{ vscale(40) }}</height>
    <align>left</align>
    <itemgap>60</itemgap>
    <orientation>horizontal</orientation>
    <ondown condition="String.IsEmpty(Window.Property(no.content.filtered))">50</ondown>
    <ondown condition="!String.IsEmpty(Window.Property(no.content.filtered))">600</ondown>
    <control type="group">
        <width>40</width>
        <height>{{ vscale(40) }}</height>
        <control type="button" id="201">
            <animation effect="zoom" start="100" end="144" time="100" center="20,{{ vscale(20) }}" reversible="false">Focus</animation>
            <animation effect="zoom" start="144" end="100" time="100" center="20,{{ vscale(20) }}" reversible="false">UnFocus</animation>
            <width>40</width>
            <height>{{ vscale(40) }}</height>
            <onright>202</onright>
            <ondown condition="String.IsEmpty(Window.Property(no.content.filtered))">50</ondown>
            <ondown condition="!String.IsEmpty(Window.Property(no.content.filtered))">600</ondown>
            <font>font12</font>
            <focusedcolor>FF000000</focusedcolor>
            <texturefocus colordiffuse="FFE5A00D">script.plex/buttons/home-focus.png</texturefocus>
            <texturenofocus colordiffuse="99FFFFFF">script.plex/buttons/home.png</texturenofocus>
            <label> </label>
        </control>
    </control>
    <control type="label">
        <width max="300">auto</width>
        <height>{{ vscale(40) }}</height>
        <font>font12</font>
        <align>left</align>
        <aligny>center</aligny>
        <textcolor>FFFFFFFF</textcolor>
        <label>[UPPERCASE]$INFO[Window.Property(screen.title)][/UPPERCASE][COLOR=gray]$INFO[Window.Property(items.count),  (,)][/COLOR]</label>
        <scroll>true</scroll>
    </control>
    <control type="group">
        <width>40</width>
        <height>{{ vscale(40) }}</height>
        <control type="button" id="202">
            <animation effect="zoom" start="100" end="144" time="100" center="20,{{ vscale(20) }}" reversible="false">Focus</animation>
            <animation effect="zoom" start="144" end="100" time="100" center="20,{{ vscale(20) }}" reversible="false">UnFocus</animation>
            <width>40</width>
            <height>{{ vscale(40) }}</height>
            <onright condition="String.IsEmpty(Window.Property(no.content.filtered))">204</onright>
            <onright condition="!String.IsEmpty(Window.Property(no.content.filtered))">600</onright>
            <onleft>201</onleft>
            <ondown condition="String.IsEmpty(Window.Property(no.content.filtered))">50</ondown>
            <ondown condition="!String.IsEmpty(Window.Property(no.content.filtered))">600</ondown>
            <font>font12</font>
            <focusedcolor>FF000000</focusedcolor>
            <texturefocus colordiffuse="FFE5A00D">script.plex/buttons/search-focus.png</texturefocus>
            <texturenofocus colordiffuse="99FFFFFF">script.plex/buttons/search.png</texturenofocus>
            <label> </label>
        </control>
    </control>
</control>
{% endblock header_topleft %}
{% block header_audiowidget_onleft2 %}<onleft>202</onleft>{% endblock %}
{% block header_filteropts_onleft_nocontent %}<onleft condition="!String.IsEmpty(Window.Property(no.content.filtered))">200</onleft>{% endblock %}
{% block header_filteropts_onup %}<onup>200</onup>{% endblock %}
{% block header_sidebar %}{% endblock %}

{% block content %}
<control type="group" id="50">
    <visible>!String.IsEmpty(Window.Property(initialized))</visible>
    <defaultcontrol>101</defaultcontrol>
    <posx>0</posx>
    <posy>{{ vscale(135) }}</posy>

    <control type="panel" id="101">
        <hitrect x="0" y="0" w="1920" h="945" />
        <posx>0</posx>
        <posy>0</posy>
        <width>1920</width>
        <height>{{ vscale(945) }}</height>
        <onup>200</onup>
        <scrolltime>200</scrolltime>
        <orientation>vertical</orientation>
        <preloaditems>2</preloaditems>

        <!-- ITEM LAYOUT ########################################## -->
        <itemlayout width="480" height="{{ vscale(290) }}">
            <control type="group">
                <posx>15</posx>
                <posy>15</posy>
                <!-- Genre art -->
                <control type="image">
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>450</width>
                    <height>{{ vscale(253) }}</height>
                    <texture background="true">$INFO[ListItem.Thumb]</texture>
                    <aspectratio>scale</aspectratio>
                </control>
                <!-- Dark overlay to make label readable -->
                <control type="image">
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>450</width>
                    <height>{{ vscale(253) }}</height>
                    <texture>script.plex/white-square.png</texture>
                    <colordiffuse>55000000</colordiffuse>
                </control>
                <!-- Genre name -->
                <control type="label">
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>450</width>
                    <height>{{ vscale(253) }}</height>
                    <font>font13</font>
                    <align>center</align>
                    <aligny>center</aligny>
                    <textcolor>FFFFFFFF</textcolor>
                    <shadowcolor>DD000000</shadowcolor>
                    <label>$INFO[ListItem.Label]</label>
                </control>
            </control>
        </itemlayout>

        <!-- FOCUSED LAYOUT ####################################### -->
        <focusedlayout width="480" height="{{ vscale(290) }}">
            <control type="group">
                <posx>15</posx>
                <posy>15</posy>
                <control type="group">
                    <animation effect="zoom" start="100" end="105" time="100" center="225,{{ vscale(126) }}" reversible="false">Focus</animation>
                    <animation effect="zoom" start="105" end="100" time="100" center="225,{{ vscale(126) }}" reversible="false">UnFocus</animation>
                    <!-- Genre art -->
                    <control type="image">
                        <posx>0</posx>
                        <posy>0</posy>
                        <width>450</width>
                        <height>{{ vscale(253) }}</height>
                        <texture background="true">$INFO[ListItem.Thumb]</texture>
                        <aspectratio>scale</aspectratio>
                    </control>
                    <!-- Dark overlay -->
                    <control type="image">
                        <posx>0</posx>
                        <posy>0</posy>
                        <width>450</width>
                        <height>{{ vscale(253) }}</height>
                        <texture>script.plex/white-square.png</texture>
                        <colordiffuse>55000000</colordiffuse>
                    </control>
                    <!-- Genre name -->
                    <control type="label">
                        <scroll>Control.HasFocus(101)</scroll>
                        <posx>0</posx>
                        <posy>0</posy>
                        <width>450</width>
                        <height>{{ vscale(253) }}</height>
                        <font>font13</font>
                        <align>center</align>
                        <aligny>center</aligny>
                        <textcolor>FFFFFFFF</textcolor>
                        <shadowcolor>DD000000</shadowcolor>
                        <label>$INFO[ListItem.Label]</label>
                    </control>
                    <!-- Focus ring -->
                    <control type="group">
                        <visible>Control.HasFocus(101)</visible>
                        <control type="image">
                            <posx>0</posx>
                            <posy>0</posy>
                            <width>460</width>
                            <height>{{ vscale(263) }}</height>
                            <texture border="10">script.plex/home/selected.png</texture>
                        </control>
                    </control>
                </control>
            </control>
        </focusedlayout>
    </control>
</control>
{% endblock content %}
