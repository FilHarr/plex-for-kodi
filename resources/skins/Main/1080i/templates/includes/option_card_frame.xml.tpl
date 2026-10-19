<!-- The option pickers' card frame, list and scrollbar (script-plex-settings_select_dialog and its tall
     _side twin for the video player's Subtitles picker): list_height is the list's and the scrollbar's
     height (Kodi can't resize a scrollbar from Python), in whole rows; row_height the row pitch and card_height
     its card (row_height less 6: 3 clear above and below); line1_y/line2_y the two-line rows' 22-high lines,
     centred on the card 24 apart. The centred pickers: 64 rows (58 cards), lines at 9 and 33, 10 rows (640).
     The tall one: 61 (55), 7.5 and 31.5, 13 rows (793). tick_y centres the current option's 26 tick on the
     row: 19 on 64, 17.5 on 61. -->
<!-- The Libraries picker's card style (script-plex-card_list.xml.tpl), at its 600 width: a F2111111 backdrop (95%) 20
     wider than the list each side with the heading in its top 66, each option its own 99111111 card (58 high in
     a 64 pitch - the picker's 78/84 less 10 top and bottom, as the Settings dialog's), the focused one lit with 33FFFFFF, font8 text, and a second line (Label2 - an audio track's
     detail, say) under it, dimmer, as the picker's server is. SelectDialog.fitFrame() sizes the list, backdrop
     and shadow to the options (up to 10, then it scrolls) and centres it all: frame_x/frame_y (group 200's place,
     the list's top left), backdrop_height and shadow_height here are only a start for the centred pickers. The
     tall one's are its own, so it opens in place rather than centred then jumping to the right (seen on a Shield). -->
<control type="group" id="200">
    <!-- out of the way of what its choices open: Kodi's subtitle search and the delay slider -->
    <visible>!Window.IsVisible(subtitlesearch) + !Window.IsVisible(sliderdialog)</visible>
    <posx>{{ frame_x }}</posx>
    <posy>{{ frame_y|vscale }}</posy>
    <control type="image" id="202">
        <posx>-60</posx>
        <posy>{{ vscale(-106) }}</posy>
        <width>720</width>
        <height>{{ shadow_height|vscale }}</height>
        <texture border="42">script.plex/drop-shadow.png</texture>
    </control>
    <control type="image" id="201">
        <posx>-20</posx>
        <posy>{{ vscale(-66) }}</posy>
        <width>640</width>
        <height>{{ backdrop_height|vscale }}</height>
        <texture colordiffuse="F2111111" border="10">script.plex/white-square-rounded.png</texture>
    </control>
    <control type="label">
        <posx>20</posx>
        <posy>{{ vscale(-66) }}</posy>
        <width>560</width>
        <height>{{ vscale(66) }}</height>
        <font>font25_title</font>
        <align>center</align>
        <aligny>center</aligny>
        <textcolor>FFEEEEEE</textcolor>
        <scroll>true</scroll>
        <scrollspeed>15</scrollspeed>
        <label>$INFO[Window.Property(heading)]</label>
    </control>
    <control type="list" id="100">
        <posx>0</posx>
        <posy>0</posy>
        <width>600</width>
        <height>{{ list_height|vscale }}</height>
        <onup>noop</onup>
        <ondown>noop</ondown>
        <onleft>noop</onleft>
        <onright>101</onright>
        <scrolltime>200</scrolltime>
        <orientation>vertical</orientation>
        <pagecontrol>101</pagecontrol>
        <itemlayout height="{{ row_height|vscale }}">
            <control type="image">
                <posx>0</posx>
                <posy>{{ vscale(3) }}</posy>
                <width>600</width>
                <height>{{ card_height|vscale }}</height>
                <texture colordiffuse="99111111" border="10">script.plex/white-square-rounded.png</texture>
            </control>
            <!-- font8: one line, or the option over its detail, told apart by brightness, centred on the card -->
            <control type="label">
                <visible>String.IsEmpty(ListItem.Label2)</visible>
                <posx>20</posx>
                <posy>0</posy>
                <width>520</width>
                <height>{{ row_height|vscale }}</height>
                <font>font8</font>
                <align>left</align>
                <aligny>center</aligny>
                <textcolor>DDFFFFFF</textcolor>
                <label>$INFO[ListItem.Label]</label>
            </control>
            <control type="label">
                <visible>!String.IsEmpty(ListItem.Label2)</visible>
                <posx>20</posx>
                <posy>{{ line1_y|vscale }}</posy>
                <width>520</width>
                <height>{{ vscale(22) }}</height>
                <font>font8</font>
                <align>left</align>
                <aligny>center</aligny>
                <textcolor>DDFFFFFF</textcolor>
                <label>$INFO[ListItem.Label]</label>
            </control>
            <control type="label">
                <visible>!String.IsEmpty(ListItem.Label2)</visible>
                <posx>20</posx>
                <posy>{{ line2_y|vscale }}</posy>
                <width>520</width>
                <height>{{ vscale(22) }}</height>
                <font>font8</font>
                <align>left</align>
                <aligny>center</aligny>
                <textcolor>88FFFFFF</textcolor>
                <label>$INFO[ListItem.Label2]</label>
            </control>
            <!-- the current option (SelectDialog's selected_idx): indicators/tick.png, at the right -->
            <control type="image">
                <visible>!String.IsEmpty(ListItem.Property(current))</visible>
                <posx>554</posx>
                <posy>{{ tick_y|vscale }}</posy>
                <width>26</width>
                <height>{{ vscale(26) }}</height>
                <texture colordiffuse="DDFFFFFF">script.plex/indicators/tick.png</texture>
                <aspectratio>keep</aspectratio>
            </control>
        </itemlayout>
        <focusedlayout height="{{ row_height|vscale }}">
            <control type="image">
                <posx>0</posx>
                <posy>{{ vscale(3) }}</posy>
                <width>600</width>
                <height>{{ card_height|vscale }}</height>
                <texture colordiffuse="99111111" border="10">script.plex/white-square-rounded.png</texture>
            </control>
            <control type="image">
                <visible>Control.HasFocus(100)</visible>
                <posx>0</posx>
                <posy>{{ vscale(3) }}</posy>
                <width>600</width>
                <height>{{ card_height|vscale }}</height>
                <texture colordiffuse="33FFFFFF" border="10">script.plex/white-square-rounded.png</texture>
            </control>
            <control type="label">
                <visible>String.IsEmpty(ListItem.Label2)</visible>
                <posx>20</posx>
                <posy>0</posy>
                <width>520</width>
                <height>{{ row_height|vscale }}</height>
                <font>font8</font>
                <align>left</align>
                <aligny>center</aligny>
                <textcolor>FFFFFFFF</textcolor>
                <scroll>true</scroll>
                <scrollspeed>20</scrollspeed>
                <label>$INFO[ListItem.Label]</label>
            </control>
            <control type="label">
                <visible>!String.IsEmpty(ListItem.Label2)</visible>
                <posx>20</posx>
                <posy>{{ line1_y|vscale }}</posy>
                <width>520</width>
                <height>{{ vscale(22) }}</height>
                <font>font8</font>
                <align>left</align>
                <aligny>center</aligny>
                <textcolor>FFFFFFFF</textcolor>
                <scroll>true</scroll>
                <scrollspeed>20</scrollspeed>
                <label>$INFO[ListItem.Label]</label>
            </control>
            <control type="label">
                <visible>!String.IsEmpty(ListItem.Label2)</visible>
                <posx>20</posx>
                <posy>{{ line2_y|vscale }}</posy>
                <width>520</width>
                <height>{{ vscale(22) }}</height>
                <font>font8</font>
                <align>left</align>
                <aligny>center</aligny>
                <textcolor>99FFFFFF</textcolor>
                <scroll>true</scroll>
                <scrollspeed>20</scrollspeed>
                <label>$INFO[ListItem.Label2]</label>
            </control>
            <!-- the current option (SelectDialog's selected_idx): indicators/tick.png, at the right -->
            <control type="image">
                <visible>!String.IsEmpty(ListItem.Property(current))</visible>
                <posx>554</posx>
                <posy>{{ tick_y|vscale }}</posy>
                <width>26</width>
                <height>{{ vscale(26) }}</height>
                <texture colordiffuse="FFFFFFFF">script.plex/indicators/tick.png</texture>
                <aspectratio>keep</aspectratio>
            </control>
        </focusedlayout>
    </control>
    <!-- the picker's, the list's height: it only shows once the list scrolls -->
    <control type="scrollbar" id="101">
        <hitrect x="600" y="0" w="50" h="{{ list_height|vscale }}" />
        <left>604</left>
        <top>0</top>
        <width>12</width>
        <height>{{ list_height|vscale }}</height>
        <texturesliderbackground colordiffuse="40000000" border="5">script.plex/white-square-rounded.png</texturesliderbackground>
        <texturesliderbar colordiffuse="77FFFFFF" border="5">script.plex/white-square-rounded.png</texturesliderbar>
        <texturesliderbarfocus colordiffuse="FFE5A00D" border="5">script.plex/white-square-rounded.png</texturesliderbarfocus>
        <textureslidernib>-</textureslidernib>
        <textureslidernibfocus>-</textureslidernibfocus>
        <pulseonselect>false</pulseonselect>
        <orientation>vertical</orientation>
        <showonepage>false</showonepage>
        <onleft>100</onleft>
    </control>
</control>
