{% extends "base.xml.tpl" %}
{% block backgroundcolor %}{% endblock %}
{% block headers %}
<onload>SetProperty(dropdown,1)</onload>
<defaultcontrol>100</defaultcontrol>
{% endblock %}
{% block controls %}
<!-- Card lists (dropdown.CardListDialog: the Libraries picker, Manage Hubs, the search's servers), in
     the settings and pickers' frame (includes/option_card_frame.xml.tpl): the 30% dim, a F2111111 panel
     876 high from 103 (CardListDialog places and sizes it), the heading in font25_title in its top 66.
     Its own place across the screen. Each row three rounded cards: the row (its title in font20_title,
     and in font8 a second line - a library's server), a toggle tile (a library's pin, a hub's
     shown/hidden) and Move. Left/Right choose which Select acts on (Window.Property(picker.column):
     open, pin, move); the focused row shows the chosen card in the sidebar's focus grey. A 'single'
     row has its toggle only, where Move would be. -->
<control type="button" id="700">
    <!-- dummy for clicks off list -->
    <posx>0</posx>
    <posy>0</posy>
    <width>1920</width>
    <height>1080</height>
    <texturefocus>-</texturefocus>
    <texturenofocus>-</texturenofocus>
</control>
<!-- The full-screen dim behind it: 30% black, the settings and pickers' (option_card_frame.xml.tpl) -->
<control type="image">
    <posx>0</posx>
    <posy>0</posy>
    <width>1920</width>
    <height>1080</height>
    <texture>script.plex/white-square.png</texture>
    <colordiffuse>4D000000</colordiffuse>
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
            <texture colordiffuse="F2111111" border="10">script.plex/white-square-rounded.png</texture>
        </control>
        <control type="label">
            <posx>40</posx>
            <posy>0</posy>
            <width>560</width>
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
    <!-- Two lists, one shown (Window.Property(tall), CardListDialog): the pickers' rows, 61 apart with 55
         cards, 13 to the 793 (option_card_frame.xml.tpl); or, when a row has a second line (a
         library's server), 84 apart with 78 cards, 9 to 756. Rows in font20_title, the second line
         in font8. A list's rows are all one height, hence two. -->
    {% for list_id, bar_id, row_height, card_height, list_height, icon_y, tall in ((250, 1152, 61, 55, 793, 17.5, False), (251, 1153, 84, 78, 756, 29, True)) %}
    <control type="list" id="{{ list_id }}">
        <visible>{% if tall %}!{% endif %}String.IsEmpty(Window.Property(tall))</visible>
        <posx>0</posx>
        <posy>0</posy>
        <width>600</width>
        <height>{{ list_height|vscale }}</height>
        <!-- Left/Right choose a card (LibraryPickerDialog.onAction()), never leave the list -->
        <onleft>noop</onleft>
        <onright>noop</onright>
        <onup>noop</onup>
        <ondown>noop</ondown>
        <scrolltime>200</scrolltime>
        <orientation>vertical</orientation>
        <pagecontrol>{{ bar_id }}</pagecontrol>
        <itemlayout height="{{ row_height|vscale }}">
            <control type="image">
                <visible>!String.IsEmpty(ListItem.Property(buttons)) + String.IsEmpty(ListItem.Property(single))</visible>
                <posx>0</posx>
                <posy>{{ vscale(3) }}</posy>
                <width>472</width>
                <height>{{ card_height|vscale }}</height>
                <texture colordiffuse="99111111" border="10">script.plex/white-square-rounded.png</texture>
            </control>
            <control type="image">
                <visible>!String.IsEmpty(ListItem.Property(single))</visible>
                <posx>0</posx>
                <posy>{{ vscale(3) }}</posy>
                <width>536</width>
                <height>{{ card_height|vscale }}</height>
                <texture colordiffuse="99111111" border="10">script.plex/white-square-rounded.png</texture>
            </control>
            <control type="image">
                <visible>String.IsEmpty(ListItem.Property(buttons))</visible>
                <posx>0</posx>
                <posy>{{ vscale(3) }}</posy>
                <width>600</width>
                <height>{{ card_height|vscale }}</height>
                <texture colordiffuse="99111111" border="10">script.plex/white-square-rounded.png</texture>
            </control>
            <control type="image">
                <visible>!String.IsEmpty(ListItem.Property(buttons)) + String.IsEmpty(ListItem.Property(single))</visible>
                <posx>480</posx>
                <posy>{{ vscale(3) }}</posy>
                <width>56</width>
                <height>{{ card_height|vscale }}</height>
                <texture colordiffuse="99111111" border="10">script.plex/white-square-rounded.png</texture>
            </control>
            <control type="image">
                <visible>!String.IsEmpty(ListItem.Property(buttons))</visible>
                <posx>544</posx>
                <posy>{{ vscale(3) }}</posy>
                <width>56</width>
                <height>{{ card_height|vscale }}</height>
                <texture colordiffuse="99111111" border="10">script.plex/white-square-rounded.png</texture>
            </control>
            <!-- one line, or the title over its server in font8 -->
            <control type="label">
                <visible>String.IsEmpty(ListItem.Property(subtitle))</visible>
                <posx>20</posx>
                <posy>0</posy>
                <width>432</width>
                <height>{{ row_height|vscale }}</height>
                <font>font20_title</font>
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
                <font>font20_title</font>
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
                <visible>!String.IsEmpty(ListItem.Property(buttons)) + String.IsEmpty(ListItem.Property(single)) + String.IsEmpty(ListItem.Property(indicator.dim))</visible>
                <posx>495</posx>
                <posy>{{ icon_y|vscale }}</posy>
                <width>26</width>
                <height>{{ vscale(26) }}</height>
                <texture colordiffuse="FFFFFFFF">$INFO[ListItem.Thumb]</texture>
                <aspectratio>keep</aspectratio>
            </control>
            <control type="image">
                <visible>!String.IsEmpty(ListItem.Property(buttons)) + String.IsEmpty(ListItem.Property(single)) + !String.IsEmpty(ListItem.Property(indicator.dim))</visible>
                <posx>495</posx>
                <posy>{{ icon_y|vscale }}</posy>
                <width>26</width>
                <height>{{ vscale(26) }}</height>
                <texture colordiffuse="66FFFFFF">$INFO[ListItem.Thumb]</texture>
                <aspectratio>keep</aspectratio>
            </control>
            <control type="image">
                <visible>!String.IsEmpty(ListItem.Property(single)) + String.IsEmpty(ListItem.Property(indicator.dim))</visible>
                <posx>559</posx>
                <posy>{{ icon_y|vscale }}</posy>
                <width>26</width>
                <height>{{ vscale(26) }}</height>
                <texture colordiffuse="FFFFFFFF">$INFO[ListItem.Thumb]</texture>
                <aspectratio>keep</aspectratio>
            </control>
            <control type="image">
                <visible>!String.IsEmpty(ListItem.Property(single)) + !String.IsEmpty(ListItem.Property(indicator.dim))</visible>
                <posx>559</posx>
                <posy>{{ icon_y|vscale }}</posy>
                <width>26</width>
                <height>{{ vscale(26) }}</height>
                <texture colordiffuse="66FFFFFF">$INFO[ListItem.Thumb]</texture>
                <aspectratio>keep</aspectratio>
            </control>
            <control type="image">
                <visible>!String.IsEmpty(ListItem.Property(buttons)) + String.IsEmpty(ListItem.Property(single)) + String.IsEmpty(ListItem.Property(nomove))</visible>
                <posx>559</posx>
                <posy>{{ icon_y|vscale }}</posy>
                <width>26</width>
                <height>{{ vscale(26) }}</height>
                <texture colordiffuse="66FFFFFF">script.plex/indicators/move.png</texture>
                <aspectratio>keep</aspectratio>
            </control>
        </itemlayout>
        <focusedlayout height="{{ row_height|vscale }}">
            <control type="image">
                <visible>!String.IsEmpty(ListItem.Property(buttons)) + String.IsEmpty(ListItem.Property(single))</visible>
                <posx>0</posx>
                <posy>{{ vscale(3) }}</posy>
                <width>472</width>
                <height>{{ card_height|vscale }}</height>
                <texture colordiffuse="99111111" border="10">script.plex/white-square-rounded.png</texture>
            </control>
            <control type="image">
                <visible>!String.IsEmpty(ListItem.Property(single))</visible>
                <posx>0</posx>
                <posy>{{ vscale(3) }}</posy>
                <width>536</width>
                <height>{{ card_height|vscale }}</height>
                <texture colordiffuse="99111111" border="10">script.plex/white-square-rounded.png</texture>
            </control>
            <control type="image">
                <visible>String.IsEmpty(ListItem.Property(buttons))</visible>
                <posx>0</posx>
                <posy>{{ vscale(3) }}</posy>
                <width>600</width>
                <height>{{ card_height|vscale }}</height>
                <texture colordiffuse="99111111" border="10">script.plex/white-square-rounded.png</texture>
            </control>
            <control type="image">
                <visible>!String.IsEmpty(ListItem.Property(buttons)) + String.IsEmpty(ListItem.Property(single))</visible>
                <posx>480</posx>
                <posy>{{ vscale(3) }}</posy>
                <width>56</width>
                <height>{{ card_height|vscale }}</height>
                <texture colordiffuse="99111111" border="10">script.plex/white-square-rounded.png</texture>
            </control>
            <control type="image">
                <visible>!String.IsEmpty(ListItem.Property(buttons))</visible>
                <posx>544</posx>
                <posy>{{ vscale(3) }}</posy>
                <width>56</width>
                <height>{{ card_height|vscale }}</height>
                <texture colordiffuse="99111111" border="10">script.plex/white-square-rounded.png</texture>
            </control>
            <!-- the chosen card in the focus grey; the title card tinted when a button is -->
            <control type="image">
                <visible>String.IsEmpty(ListItem.Property(buttons))</visible>
                <posx>0</posx>
                <posy>{{ vscale(3) }}</posy>
                <width>600</width>
                <height>{{ card_height|vscale }}</height>
                <texture colordiffuse="33FFFFFF" border="10">script.plex/white-square-rounded.png</texture>
            </control>
            <control type="image">
                <visible>!String.IsEmpty(ListItem.Property(buttons)) + String.IsEmpty(ListItem.Property(single)) + String.IsEqual(Window.Property(picker.column),open) + String.IsEmpty(ListItem.Property(moving))</visible>
                <posx>0</posx>
                <posy>{{ vscale(3) }}</posy>
                <width>472</width>
                <height>{{ card_height|vscale }}</height>
                <texture colordiffuse="33FFFFFF" border="10">script.plex/white-square-rounded.png</texture>
            </control>
            <control type="image">
                <visible>!String.IsEmpty(ListItem.Property(buttons)) + String.IsEmpty(ListItem.Property(single)) + !String.IsEqual(Window.Property(picker.column),open) + String.IsEmpty(ListItem.Property(moving))</visible>
                <posx>0</posx>
                <posy>{{ vscale(3) }}</posy>
                <width>472</width>
                <height>{{ card_height|vscale }}</height>
                <texture colordiffuse="22FFFFFF" border="10">script.plex/white-square-rounded.png</texture>
            </control>
            <control type="image">
                <visible>!String.IsEmpty(ListItem.Property(single)) + String.IsEqual(Window.Property(picker.column),open) + String.IsEmpty(ListItem.Property(moving))</visible>
                <posx>0</posx>
                <posy>{{ vscale(3) }}</posy>
                <width>536</width>
                <height>{{ card_height|vscale }}</height>
                <texture colordiffuse="33FFFFFF" border="10">script.plex/white-square-rounded.png</texture>
            </control>
            <control type="image">
                <visible>!String.IsEmpty(ListItem.Property(single)) + !String.IsEqual(Window.Property(picker.column),open) + String.IsEmpty(ListItem.Property(moving))</visible>
                <posx>0</posx>
                <posy>{{ vscale(3) }}</posy>
                <width>536</width>
                <height>{{ card_height|vscale }}</height>
                <texture colordiffuse="22FFFFFF" border="10">script.plex/white-square-rounded.png</texture>
            </control>
            <control type="image">
                <visible>!String.IsEmpty(ListItem.Property(buttons)) + String.IsEmpty(ListItem.Property(single)) + String.IsEqual(Window.Property(picker.column),pin) + String.IsEmpty(ListItem.Property(moving))</visible>
                <posx>480</posx>
                <posy>{{ vscale(3) }}</posy>
                <width>56</width>
                <height>{{ card_height|vscale }}</height>
                <texture colordiffuse="33FFFFFF" border="10">script.plex/white-square-rounded.png</texture>
            </control>
            <control type="image">
                <visible>!String.IsEmpty(ListItem.Property(single)) + String.IsEqual(Window.Property(picker.column),pin) + String.IsEmpty(ListItem.Property(moving))</visible>
                <posx>544</posx>
                <posy>{{ vscale(3) }}</posy>
                <width>56</width>
                <height>{{ card_height|vscale }}</height>
                <texture colordiffuse="33FFFFFF" border="10">script.plex/white-square-rounded.png</texture>
            </control>
            <control type="image">
                <visible>!String.IsEmpty(ListItem.Property(buttons)) + String.IsEmpty(ListItem.Property(single)) + String.IsEqual(Window.Property(picker.column),move) + String.IsEmpty(ListItem.Property(moving))</visible>
                <posx>544</posx>
                <posy>{{ vscale(3) }}</posy>
                <width>56</width>
                <height>{{ card_height|vscale }}</height>
                <texture colordiffuse="33FFFFFF" border="10">script.plex/white-square-rounded.png</texture>
            </control>
            <!-- picked up to move: all three cards a step brighter -->
            <control type="image">
                <visible>!String.IsEmpty(ListItem.Property(buttons)) + String.IsEmpty(ListItem.Property(single)) + !String.IsEmpty(ListItem.Property(moving))</visible>
                <posx>0</posx>
                <posy>{{ vscale(3) }}</posy>
                <width>472</width>
                <height>{{ card_height|vscale }}</height>
                <texture colordiffuse="4DFFFFFF" border="10">script.plex/white-square-rounded.png</texture>
            </control>
            <control type="image">
                <visible>!String.IsEmpty(ListItem.Property(buttons)) + String.IsEmpty(ListItem.Property(single)) + !String.IsEmpty(ListItem.Property(moving))</visible>
                <posx>480</posx>
                <posy>{{ vscale(3) }}</posy>
                <width>56</width>
                <height>{{ card_height|vscale }}</height>
                <texture colordiffuse="4DFFFFFF" border="10">script.plex/white-square-rounded.png</texture>
            </control>
            <control type="image">
                <visible>!String.IsEmpty(ListItem.Property(buttons)) + String.IsEmpty(ListItem.Property(single)) + !String.IsEmpty(ListItem.Property(moving))</visible>
                <posx>544</posx>
                <posy>{{ vscale(3) }}</posy>
                <width>56</width>
                <height>{{ card_height|vscale }}</height>
                <texture colordiffuse="4DFFFFFF" border="10">script.plex/white-square-rounded.png</texture>
            </control>
            <!-- one line, or the title over its server in font8 -->
            <control type="label">
                <visible>String.IsEmpty(ListItem.Property(subtitle))</visible>
                <posx>20</posx>
                <posy>0</posy>
                <width>432</width>
                <height>{{ row_height|vscale }}</height>
                <font>font20_title</font>
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
                <font>font20_title</font>
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
                <visible>!String.IsEmpty(ListItem.Property(buttons)) + String.IsEmpty(ListItem.Property(single)) + String.IsEmpty(ListItem.Property(indicator.dim))</visible>
                <posx>495</posx>
                <posy>{{ icon_y|vscale }}</posy>
                <width>26</width>
                <height>{{ vscale(26) }}</height>
                <texture colordiffuse="FFFFFFFF">$INFO[ListItem.Thumb]</texture>
                <aspectratio>keep</aspectratio>
            </control>
            <control type="image">
                <visible>!String.IsEmpty(ListItem.Property(buttons)) + String.IsEmpty(ListItem.Property(single)) + !String.IsEmpty(ListItem.Property(indicator.dim)) + String.IsEqual(Window.Property(picker.column),pin) + String.IsEmpty(ListItem.Property(moving))</visible>
                <posx>495</posx>
                <posy>{{ icon_y|vscale }}</posy>
                <width>26</width>
                <height>{{ vscale(26) }}</height>
                <texture colordiffuse="99FFFFFF">$INFO[ListItem.Thumb]</texture>
                <aspectratio>keep</aspectratio>
            </control>
            <control type="image">
                <visible>!String.IsEmpty(ListItem.Property(buttons)) + String.IsEmpty(ListItem.Property(single)) + !String.IsEmpty(ListItem.Property(indicator.dim)) + ![String.IsEqual(Window.Property(picker.column),pin) + String.IsEmpty(ListItem.Property(moving))]</visible>
                <posx>495</posx>
                <posy>{{ icon_y|vscale }}</posy>
                <width>26</width>
                <height>{{ vscale(26) }}</height>
                <texture colordiffuse="66FFFFFF">$INFO[ListItem.Thumb]</texture>
                <aspectratio>keep</aspectratio>
            </control>
            <control type="image">
                <visible>!String.IsEmpty(ListItem.Property(single)) + String.IsEmpty(ListItem.Property(indicator.dim))</visible>
                <posx>559</posx>
                <posy>{{ icon_y|vscale }}</posy>
                <width>26</width>
                <height>{{ vscale(26) }}</height>
                <texture colordiffuse="FFFFFFFF">$INFO[ListItem.Thumb]</texture>
                <aspectratio>keep</aspectratio>
            </control>
            <control type="image">
                <visible>!String.IsEmpty(ListItem.Property(single)) + !String.IsEmpty(ListItem.Property(indicator.dim)) + String.IsEqual(Window.Property(picker.column),pin) + String.IsEmpty(ListItem.Property(moving))</visible>
                <posx>559</posx>
                <posy>{{ icon_y|vscale }}</posy>
                <width>26</width>
                <height>{{ vscale(26) }}</height>
                <texture colordiffuse="99FFFFFF">$INFO[ListItem.Thumb]</texture>
                <aspectratio>keep</aspectratio>
            </control>
            <control type="image">
                <visible>!String.IsEmpty(ListItem.Property(single)) + !String.IsEmpty(ListItem.Property(indicator.dim)) + ![String.IsEqual(Window.Property(picker.column),pin) + String.IsEmpty(ListItem.Property(moving))]</visible>
                <posx>559</posx>
                <posy>{{ icon_y|vscale }}</posy>
                <width>26</width>
                <height>{{ vscale(26) }}</height>
                <texture colordiffuse="66FFFFFF">$INFO[ListItem.Thumb]</texture>
                <aspectratio>keep</aspectratio>
            </control>
            <control type="image">
                <visible>!String.IsEmpty(ListItem.Property(buttons)) + String.IsEmpty(ListItem.Property(single)) + String.IsEmpty(ListItem.Property(nomove)) + [String.IsEqual(Window.Property(picker.column),move) | !String.IsEmpty(ListItem.Property(moving))]</visible>
                <posx>559</posx>
                <posy>{{ icon_y|vscale }}</posy>
                <width>26</width>
                <height>{{ vscale(26) }}</height>
                <texture colordiffuse="FFFFFFFF">script.plex/indicators/move.png</texture>
                <aspectratio>keep</aspectratio>
            </control>
            <control type="image">
                <visible>!String.IsEmpty(ListItem.Property(buttons)) + String.IsEmpty(ListItem.Property(single)) + String.IsEmpty(ListItem.Property(nomove)) + ![String.IsEqual(Window.Property(picker.column),move) | !String.IsEmpty(ListItem.Property(moving))]</visible>
                <posx>559</posx>
                <posy>{{ icon_y|vscale }}</posy>
                <width>26</width>
                <height>{{ vscale(26) }}</height>
                <texture colordiffuse="66FFFFFF">script.plex/indicators/move.png</texture>
                <aspectratio>keep</aspectratio>
            </control>
        </focusedlayout>
    </control>
    <!-- the list's height: it only shows once the list scrolls. Grey focused too, brighter (DDFFFFFF, the
         options' own text) over the 77FFFFFF it's otherwise, rather than the old orange (on request, 2026-10-23). Reached by Right past a row's last column
         (CardListDialog.onAction()) -->
    <control type="scrollbar" id="{{ bar_id }}">
        <hitrect x="600" y="0" w="50" h="{{ list_height|vscale }}" />
        <left>604</left>
        <top>0</top>
        <width>12</width>
        <height>{{ list_height|vscale }}</height>
        <visible>{% if tall %}!{% endif %}String.IsEmpty(Window.Property(tall))</visible>
        <texturesliderbackground colordiffuse="40000000" border="5">script.plex/white-square-rounded.png</texturesliderbackground>
        <texturesliderbar colordiffuse="77FFFFFF" border="5">script.plex/white-square-rounded.png</texturesliderbar>
        <texturesliderbarfocus colordiffuse="DDFFFFFF" border="5">script.plex/white-square-rounded.png</texturesliderbarfocus>
        <textureslidernib>-</textureslidernib>
        <textureslidernibfocus>-</textureslidernibfocus>
        <pulseonselect>false</pulseonselect>
        <orientation>vertical</orientation>
        <showonepage>false</showonepage>
        <onleft>{{ list_id }}</onleft>
    </control>
    {% endfor %}
</control>
{% endblock controls %}
