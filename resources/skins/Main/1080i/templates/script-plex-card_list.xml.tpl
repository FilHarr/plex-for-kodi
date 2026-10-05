{% extends "base.xml.tpl" %}
{% block backgroundcolor %}{% endblock %}
{% block headers %}
<onload>SetProperty(dropdown,1)</onload>
<defaultcontrol>100</defaultcontrol>
{% endblock %}
{% block controls %}
<!-- Card lists (dropdown.CardListDialog: the Libraries picker, Manage Hubs):
     script-plex-dropdown_header's frame, with rows of 84, each three rounded cards: the row (its
     title, and in font8 a second line - a library's server), a toggle tile (a library's pin, a
     hub's shown/hidden) and Move. Left/Right choose which Select acts on
     (Window.Property(picker.column): open, pin, move); the focused row shows the chosen card in the
     sidebar's focus grey. Written from the header dropdown; keep the frame in step with it. -->
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
        <posy>{{ vperc(vscale(-106)) }}</posy>
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
            <texture colordiffuse="D3111111" border="10">script.plex/white-square-rounded.png</texture>
        </control>
        <control type="label">
            <posx>20</posx>
            <posy>0</posy>
            <width>600</width>
            <height>{{ vscale(66) }}</height>
            <font>font12</font>
            <align>center</align>
            <aligny>center</aligny>
            <textcolor>FFEEEEEE</textcolor>
            <scroll>true</scroll>
            <scrollspeed>15</scrollspeed>
            <label>[B]$INFO[Window.Property(header)][/B]</label>
        </control>
    </control>
    <control type="list" id="250">
        <posx>0</posx>
        <posy>0</posy>
        <width>600</width>
        <height>{{ vscale(840) }}</height>
        <!-- Left/Right choose a card (LibraryPickerDialog.onAction()), never leave the list -->
        <onleft>noop</onleft>
        <onright>noop</onright>
        <onup>noop</onup>
        <ondown>noop</ondown>
        <scrolltime>200</scrolltime>
        <orientation>vertical</orientation>
        <pagecontrol>1152</pagecontrol>
        <itemlayout height="{{ vscale(84) }}">
            <control type="image">
                <visible>!String.IsEmpty(ListItem.Property(buttons))</visible>
                <posx>0</posx>
                <posy>{{ vscale(3) }}</posy>
                <width>472</width>
                <height>{{ vscale(78) }}</height>
                <texture colordiffuse="99111111" border="10">script.plex/white-square-rounded.png</texture>
            </control>
            <control type="image">
                <visible>String.IsEmpty(ListItem.Property(buttons))</visible>
                <posx>0</posx>
                <posy>{{ vscale(3) }}</posy>
                <width>600</width>
                <height>{{ vscale(78) }}</height>
                <texture colordiffuse="99111111" border="10">script.plex/white-square-rounded.png</texture>
            </control>
            <control type="image">
                <visible>!String.IsEmpty(ListItem.Property(buttons))</visible>
                <posx>480</posx>
                <posy>{{ vscale(3) }}</posy>
                <width>56</width>
                <height>{{ vscale(78) }}</height>
                <texture colordiffuse="99111111" border="10">script.plex/white-square-rounded.png</texture>
            </control>
            <control type="image">
                <visible>!String.IsEmpty(ListItem.Property(buttons))</visible>
                <posx>544</posx>
                <posy>{{ vscale(3) }}</posy>
                <width>56</width>
                <height>{{ vscale(78) }}</height>
                <texture colordiffuse="99111111" border="10">script.plex/white-square-rounded.png</texture>
            </control>
            <!-- one line, or the title over its server in font8 -->
            <control type="label">
                <visible>String.IsEmpty(ListItem.Property(subtitle))</visible>
                <posx>20</posx>
                <posy>0</posy>
                <width>432</width>
                <height>{{ vscale(84) }}</height>
                <font>font12</font>
                <align>left</align>
                <aligny>center</aligny>
                <textcolor>DDFFFFFF</textcolor>
                <scroll>true</scroll>
                <scrollspeed>20</scrollspeed>
                <label>$INFO[ListItem.Label]</label>
            </control>
            <control type="label">
                <visible>!String.IsEmpty(ListItem.Property(subtitle))</visible>
                <posx>20</posx>
                <posy>{{ vscale(12) }}</posy>
                <width>432</width>
                <height>{{ vscale(36) }}</height>
                <font>font12</font>
                <align>left</align>
                <aligny>center</aligny>
                <textcolor>DDFFFFFF</textcolor>
                <scroll>true</scroll>
                <scrollspeed>20</scrollspeed>
                <label>$INFO[ListItem.Label]</label>
            </control>
            <control type="label">
                <visible>!String.IsEmpty(ListItem.Property(subtitle))</visible>
                <posx>20</posx>
                <posy>{{ vscale(48) }}</posy>
                <width>432</width>
                <height>{{ vscale(22) }}</height>
                <font>font8</font>
                <align>left</align>
                <aligny>center</aligny>
                <textcolor>88FFFFFF</textcolor>
                <label>$INFO[ListItem.Property(subtitle)]</label>
            </control>
            <control type="image">
                <visible>!String.IsEmpty(ListItem.Property(buttons)) + String.IsEmpty(ListItem.Property(indicator.dim))</visible>
                <posx>495</posx>
                <posy>{{ vscale(29) }}</posy>
                <width>26</width>
                <height>{{ vscale(26) }}</height>
                <texture colordiffuse="FFFFFFFF">$INFO[ListItem.Thumb]</texture>
                <aspectratio>keep</aspectratio>
            </control>
            <control type="image">
                <visible>!String.IsEmpty(ListItem.Property(buttons)) + !String.IsEmpty(ListItem.Property(indicator.dim))</visible>
                <posx>495</posx>
                <posy>{{ vscale(29) }}</posy>
                <width>26</width>
                <height>{{ vscale(26) }}</height>
                <texture colordiffuse="66FFFFFF">$INFO[ListItem.Thumb]</texture>
                <aspectratio>keep</aspectratio>
            </control>
            <control type="image">
                <visible>!String.IsEmpty(ListItem.Property(buttons)) + String.IsEmpty(ListItem.Property(nomove))</visible>
                <posx>559</posx>
                <posy>{{ vscale(29) }}</posy>
                <width>26</width>
                <height>{{ vscale(26) }}</height>
                <texture colordiffuse="66FFFFFF">script.plex/indicators/move.png</texture>
                <aspectratio>keep</aspectratio>
            </control>
        </itemlayout>
        <focusedlayout height="{{ vscale(84) }}">
            <control type="image">
                <visible>!String.IsEmpty(ListItem.Property(buttons))</visible>
                <posx>0</posx>
                <posy>{{ vscale(3) }}</posy>
                <width>472</width>
                <height>{{ vscale(78) }}</height>
                <texture colordiffuse="99111111" border="10">script.plex/white-square-rounded.png</texture>
            </control>
            <control type="image">
                <visible>String.IsEmpty(ListItem.Property(buttons))</visible>
                <posx>0</posx>
                <posy>{{ vscale(3) }}</posy>
                <width>600</width>
                <height>{{ vscale(78) }}</height>
                <texture colordiffuse="99111111" border="10">script.plex/white-square-rounded.png</texture>
            </control>
            <control type="image">
                <visible>!String.IsEmpty(ListItem.Property(buttons))</visible>
                <posx>480</posx>
                <posy>{{ vscale(3) }}</posy>
                <width>56</width>
                <height>{{ vscale(78) }}</height>
                <texture colordiffuse="99111111" border="10">script.plex/white-square-rounded.png</texture>
            </control>
            <control type="image">
                <visible>!String.IsEmpty(ListItem.Property(buttons))</visible>
                <posx>544</posx>
                <posy>{{ vscale(3) }}</posy>
                <width>56</width>
                <height>{{ vscale(78) }}</height>
                <texture colordiffuse="99111111" border="10">script.plex/white-square-rounded.png</texture>
            </control>
            <!-- the chosen card in the focus grey; the title card tinted when a button is -->
            <control type="image">
                <visible>String.IsEmpty(ListItem.Property(buttons))</visible>
                <posx>0</posx>
                <posy>{{ vscale(3) }}</posy>
                <width>600</width>
                <height>{{ vscale(78) }}</height>
                <texture colordiffuse="33FFFFFF" border="10">script.plex/white-square-rounded.png</texture>
            </control>
            <control type="image">
                <visible>!String.IsEmpty(ListItem.Property(buttons)) + String.IsEqual(Window.Property(picker.column),open) + String.IsEmpty(ListItem.Property(moving))</visible>
                <posx>0</posx>
                <posy>{{ vscale(3) }}</posy>
                <width>472</width>
                <height>{{ vscale(78) }}</height>
                <texture colordiffuse="33FFFFFF" border="10">script.plex/white-square-rounded.png</texture>
            </control>
            <control type="image">
                <visible>!String.IsEmpty(ListItem.Property(buttons)) + !String.IsEqual(Window.Property(picker.column),open) + String.IsEmpty(ListItem.Property(moving))</visible>
                <posx>0</posx>
                <posy>{{ vscale(3) }}</posy>
                <width>472</width>
                <height>{{ vscale(78) }}</height>
                <texture colordiffuse="22FFFFFF" border="10">script.plex/white-square-rounded.png</texture>
            </control>
            <control type="image">
                <visible>!String.IsEmpty(ListItem.Property(buttons)) + String.IsEqual(Window.Property(picker.column),pin) + String.IsEmpty(ListItem.Property(moving))</visible>
                <posx>480</posx>
                <posy>{{ vscale(3) }}</posy>
                <width>56</width>
                <height>{{ vscale(78) }}</height>
                <texture colordiffuse="33FFFFFF" border="10">script.plex/white-square-rounded.png</texture>
            </control>
            <control type="image">
                <visible>!String.IsEmpty(ListItem.Property(buttons)) + String.IsEqual(Window.Property(picker.column),move) + String.IsEmpty(ListItem.Property(moving))</visible>
                <posx>544</posx>
                <posy>{{ vscale(3) }}</posy>
                <width>56</width>
                <height>{{ vscale(78) }}</height>
                <texture colordiffuse="33FFFFFF" border="10">script.plex/white-square-rounded.png</texture>
            </control>
            <!-- picked up to move: all three cards a step brighter -->
            <control type="image">
                <visible>!String.IsEmpty(ListItem.Property(buttons)) + !String.IsEmpty(ListItem.Property(moving))</visible>
                <posx>0</posx>
                <posy>{{ vscale(3) }}</posy>
                <width>472</width>
                <height>{{ vscale(78) }}</height>
                <texture colordiffuse="4DFFFFFF" border="10">script.plex/white-square-rounded.png</texture>
            </control>
            <control type="image">
                <visible>!String.IsEmpty(ListItem.Property(buttons)) + !String.IsEmpty(ListItem.Property(moving))</visible>
                <posx>480</posx>
                <posy>{{ vscale(3) }}</posy>
                <width>56</width>
                <height>{{ vscale(78) }}</height>
                <texture colordiffuse="4DFFFFFF" border="10">script.plex/white-square-rounded.png</texture>
            </control>
            <control type="image">
                <visible>!String.IsEmpty(ListItem.Property(buttons)) + !String.IsEmpty(ListItem.Property(moving))</visible>
                <posx>544</posx>
                <posy>{{ vscale(3) }}</posy>
                <width>56</width>
                <height>{{ vscale(78) }}</height>
                <texture colordiffuse="4DFFFFFF" border="10">script.plex/white-square-rounded.png</texture>
            </control>
            <!-- one line, or the title over its server in font8 -->
            <control type="label">
                <visible>String.IsEmpty(ListItem.Property(subtitle))</visible>
                <posx>20</posx>
                <posy>0</posy>
                <width>432</width>
                <height>{{ vscale(84) }}</height>
                <font>font12</font>
                <align>left</align>
                <aligny>center</aligny>
                <textcolor>FFFFFFFF</textcolor>
                <scroll>true</scroll>
                <scrollspeed>20</scrollspeed>
                <label>$INFO[ListItem.Label]</label>
            </control>
            <control type="label">
                <visible>!String.IsEmpty(ListItem.Property(subtitle))</visible>
                <posx>20</posx>
                <posy>{{ vscale(12) }}</posy>
                <width>432</width>
                <height>{{ vscale(36) }}</height>
                <font>font12</font>
                <align>left</align>
                <aligny>center</aligny>
                <textcolor>FFFFFFFF</textcolor>
                <scroll>true</scroll>
                <scrollspeed>20</scrollspeed>
                <label>$INFO[ListItem.Label]</label>
            </control>
            <control type="label">
                <visible>!String.IsEmpty(ListItem.Property(subtitle))</visible>
                <posx>20</posx>
                <posy>{{ vscale(48) }}</posy>
                <width>432</width>
                <height>{{ vscale(22) }}</height>
                <font>font8</font>
                <align>left</align>
                <aligny>center</aligny>
                <textcolor>99FFFFFF</textcolor>
                <label>$INFO[ListItem.Property(subtitle)]</label>
            </control>
            <control type="image">
                <visible>!String.IsEmpty(ListItem.Property(buttons)) + String.IsEmpty(ListItem.Property(indicator.dim))</visible>
                <posx>495</posx>
                <posy>{{ vscale(29) }}</posy>
                <width>26</width>
                <height>{{ vscale(26) }}</height>
                <texture colordiffuse="FFFFFFFF">$INFO[ListItem.Thumb]</texture>
                <aspectratio>keep</aspectratio>
            </control>
            <control type="image">
                <visible>!String.IsEmpty(ListItem.Property(buttons)) + !String.IsEmpty(ListItem.Property(indicator.dim)) + String.IsEqual(Window.Property(picker.column),pin) + String.IsEmpty(ListItem.Property(moving))</visible>
                <posx>495</posx>
                <posy>{{ vscale(29) }}</posy>
                <width>26</width>
                <height>{{ vscale(26) }}</height>
                <texture colordiffuse="99FFFFFF">$INFO[ListItem.Thumb]</texture>
                <aspectratio>keep</aspectratio>
            </control>
            <control type="image">
                <visible>!String.IsEmpty(ListItem.Property(buttons)) + !String.IsEmpty(ListItem.Property(indicator.dim)) + ![String.IsEqual(Window.Property(picker.column),pin) + String.IsEmpty(ListItem.Property(moving))]</visible>
                <posx>495</posx>
                <posy>{{ vscale(29) }}</posy>
                <width>26</width>
                <height>{{ vscale(26) }}</height>
                <texture colordiffuse="66FFFFFF">$INFO[ListItem.Thumb]</texture>
                <aspectratio>keep</aspectratio>
            </control>
            <control type="image">
                <visible>!String.IsEmpty(ListItem.Property(buttons)) + String.IsEmpty(ListItem.Property(nomove)) + [String.IsEqual(Window.Property(picker.column),move) | !String.IsEmpty(ListItem.Property(moving))]</visible>
                <posx>559</posx>
                <posy>{{ vscale(29) }}</posy>
                <width>26</width>
                <height>{{ vscale(26) }}</height>
                <texture colordiffuse="FFFFFFFF">script.plex/indicators/move.png</texture>
                <aspectratio>keep</aspectratio>
            </control>
            <control type="image">
                <visible>!String.IsEmpty(ListItem.Property(buttons)) + String.IsEmpty(ListItem.Property(nomove)) + ![String.IsEqual(Window.Property(picker.column),move) | !String.IsEmpty(ListItem.Property(moving))]</visible>
                <posx>559</posx>
                <posy>{{ vscale(29) }}</posy>
                <width>26</width>
                <height>{{ vscale(26) }}</height>
                <texture colordiffuse="66FFFFFF">script.plex/indicators/move.png</texture>
                <aspectratio>keep</aspectratio>
            </control>
        </focusedlayout>
    </control>
    <!-- 10 rows high, as LibraryPickerDialog.maxRows: it only shows once the list scrolls -->
    <control type="scrollbar" id="1152">
        <hitrect x="600" y="0" w="50" h="{{ vscale(840) }}" />
        <left>604</left>
        <top>0</top>
        <width>12</width>
        <height>{{ vscale(840) }}</height>
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
