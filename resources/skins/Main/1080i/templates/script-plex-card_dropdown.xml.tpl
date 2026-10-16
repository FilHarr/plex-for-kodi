{% extends "base.xml.tpl" %}
{% block backgroundcolor %}{% endblock %}
{% block headers %}
<onload>SetProperty(dropdown,1)</onload>
<defaultcontrol>100</defaultcontrol>
<zorder>100</zorder>
{% endblock %}
{% block controls %}
<!-- A plain dropdown in the Libraries picker's card style (dropdown.CardDropdownDialog; script-plex-card_list's
     frame): the video player's Subtitles and VS10 menus. A F2111111 backdrop (95%) (111) 20 wider than the list each
     side with the header in its top 66, each option its own 99111111 card (58 high in a 64 pitch - the picker's
     78/84 less 10 top and bottom, as the Settings dialog's), the focused
     one lit with 33FFFFFF, font8 text from 20 in. A dropdown with_indicator (VS10's current mode) shows the
     row's thumb at its right. DropdownDialog.onFirstInit() sizes the shadow (110), backdrop and list. -->
<control type="button" id="700">
    <!-- dummy for clicks off list -->
    <posx>0</posx>
    <posy>0</posy>
    <width>1920</width>
    <height>1080</height>
    <texturefocus>-</texturefocus>
    <texturenofocus>-</texturenofocus>
</control>
<control type="group" id="100">
    <defaultcontrol>250</defaultcontrol>
    <visible>!String.IsEmpty(Window.Property(show))</visible>
    <posx>0</posx>
    <posy>0</posy>
    <control type="image" id="110">
        <posx>-60</posx>
        <posy>{{ vscale(-106) }}</posy>
        <width>720</width>
        <height>{{ vscale(146) }}</height>
        <texture border="42">script.plex/drop-shadow.png</texture>
    </control>
    <control type="group">
        <visible>!String.IsEmpty(Window.Property(header))</visible>
        <posx>-20</posx>
        <posy>{{ vscale(-66) }}</posy>
        <control type="image" id="111">
            <posx>0</posx>
            <posy>0</posy>
            <width>640</width>
            <height>{{ vscale(132) }}</height>
            <texture colordiffuse="F2111111" border="10">script.plex/white-square-rounded.png</texture>
        </control>
        <control type="label">
            <posx>20</posx>
            <posy>0</posy>
            <width>600</width>
            <height>{{ vscale(66) }}</height>
            <font>font25_title</font>
            <align>center</align>
            <aligny>center</aligny>
            <textcolor>FFEEEEEE</textcolor>
            <scroll>true</scroll>
            <scrollspeed>15</scrollspeed>
            <label>$INFO[Window.Property(header)]</label>
        </control>
    </control>
    <control type="list" id="250">
        <posx>0</posx>
        <posy>0</posy>
        <width>600</width>
        <height>{{ vscale(640) }}</height>
        <onleft>noop</onleft>
        <onright condition="!String.IsEmpty(Window.Property(scroll))">1152</onright>
        <onright condition="String.IsEmpty(Window.Property(scroll))">noop</onright>
        <onup>noop</onup>
        <ondown>noop</ondown>
        <scrolltime>200</scrolltime>
        <orientation>vertical</orientation>
        <pagecontrol>1152</pagecontrol>
        <itemlayout height="{{ vscale(64) }}">
            <control type="image">
                <posx>0</posx>
                <posy>{{ vscale(3) }}</posy>
                <width>600</width>
                <height>{{ vscale(58) }}</height>
                <texture colordiffuse="99111111" border="10">script.plex/white-square-rounded.png</texture>
            </control>
            <control type="label">
                <posx>20</posx>
                <posy>0</posy>
                <width>540</width>
                <height>{{ vscale(64) }}</height>
                <font>font8</font>
                <align>left</align>
                <aligny>center</aligny>
                <textcolor>DDFFFFFF</textcolor>
                <label>$INFO[ListItem.Label]</label>
            </control>
            <control type="image">
                <visible>!String.IsEmpty(ListItem.Property(with.indicator))</visible>
                <posx>554</posx>
                <posy>{{ vscale(19) }}</posy>
                <width>26</width>
                <height>{{ vscale(26) }}</height>
                <texture colordiffuse="DDFFFFFF">$INFO[ListItem.Thumb]</texture>
                <aspectratio>keep</aspectratio>
            </control>
        </itemlayout>
        <focusedlayout height="{{ vscale(64) }}">
            <control type="image">
                <posx>0</posx>
                <posy>{{ vscale(3) }}</posy>
                <width>600</width>
                <height>{{ vscale(58) }}</height>
                <texture colordiffuse="99111111" border="10">script.plex/white-square-rounded.png</texture>
            </control>
            <control type="image">
                <posx>0</posx>
                <posy>{{ vscale(3) }}</posy>
                <width>600</width>
                <height>{{ vscale(58) }}</height>
                <texture colordiffuse="33FFFFFF" border="10">script.plex/white-square-rounded.png</texture>
            </control>
            <control type="label">
                <posx>20</posx>
                <posy>0</posy>
                <width>540</width>
                <height>{{ vscale(64) }}</height>
                <font>font8</font>
                <align>left</align>
                <aligny>center</aligny>
                <textcolor>FFFFFFFF</textcolor>
                <scroll>true</scroll>
                <scrollspeed>20</scrollspeed>
                <label>$INFO[ListItem.Label]</label>
            </control>
            <control type="image">
                <visible>!String.IsEmpty(ListItem.Property(with.indicator))</visible>
                <posx>554</posx>
                <posy>{{ vscale(19) }}</posy>
                <width>26</width>
                <height>{{ vscale(26) }}</height>
                <texture colordiffuse="FFFFFFFF">$INFO[ListItem.Thumb]</texture>
                <aspectratio>keep</aspectratio>
            </control>
        </focusedlayout>
    </control>
    <!-- 10 rows high, as CardDropdownDialog.maxRows: it only shows once the list scrolls -->
    <control type="scrollbar" id="1152">
        <hitrect x="600" y="0" w="50" h="{{ vscale(640) }}" />
        <left>604</left>
        <top>0</top>
        <width>12</width>
        <height>{{ vscale(640) }}</height>
        <visible>true</visible>
        <texturesliderbackground colordiffuse="40000000" border="5">script.plex/white-square-rounded.png</texturesliderbackground>
        <texturesliderbar colordiffuse="77FFFFFF" border="5">script.plex/white-square-rounded.png</texturesliderbar>
        <texturesliderbarfocus colordiffuse="FFE5A00D" border="5">script.plex/white-square-rounded.png</texturesliderbarfocus>
        <textureslidernib>-</textureslidernib>
        <textureslidernibfocus>-</textureslidernibfocus>
        <pulseonselect>false</pulseonselect>
        <orientation>vertical</orientation>
        <showonepage>false</showonepage>
        <onleft>250</onleft>
    </control>
</control>
{% endblock controls %}
