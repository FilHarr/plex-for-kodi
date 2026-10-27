<!-- The Settings dialog's card frame, list and scrollbar (script-plex-video_settings_dialog), in the Libraries picker's card style (script-plex-card_list.xml.tpl): a F2111111
     backdrop (95%) 20 wider than the list each side with the heading in its top 66, each row its own 99111111
     card, the focused one lit with 33FFFFFF. The heading in font25_title; a row's setting on the left in
     font20_title, its value right-aligned in font8. 600 wide, as the option pickers: the name column 176 - the
     longest name, Show Stream Info, is 172 in font20_title (Inter Bold 20), plus 4 for clipping - then a 20 gap,
     the value's 364 and 20 of padding. list_height is the list's and the scrollbar's height (Kodi can't resize
     a scrollbar from Python), in whole rows; row_height the row pitch and card_height its card (row_height
     less 6: 3 clear above and below): 61 rows (55 cards), 13 of them (793). frame_x/frame_y place group 200 (the
     list's top left), backdrop_height and shadow_height size the frame, its own, so it opens in place - placed
     only from Python, a slower box (a Shield) showed it centred first, then jumping to the right. -->
<!-- out of the way of Kodi's own windows its rows open. Not of an option picker: that opens over this, in its
     place, as the add-on's Settings stack theirs, nested (dialog.pickerOpen() - its dim this one's), so the
     picker's fade out (includes/dialog_close_fade.xml.tpl) shows this still under it. Hidden while one was up,
     this came back only once the picker had faded away. -->
<!-- The full-screen dim behind it: 30% black, the screens' own row-scroll dim's (default_background.xml.tpl),
     shown with the frame below. -->
<control type="image">
    <visible>!Window.IsVisible(sliderdialog) +!Window.IsVisible(osdvideosettings) + !Window.IsVisible(osdaudiosettings) + !Window.IsVisible(osdsubtitlesettings) + !Window.IsVisible(subtitlesearch) + !Window.IsActive(selectdialog) + !Window.IsVisible(osdcmssettings)</visible>
    <posx>0</posx>
    <posy>0</posy>
    <width>1920</width>
    <height>1080</height>
    <texture>script.plex/white-square.png</texture>
    <colordiffuse>4D000000</colordiffuse>
</control>
<control type="group" id="200">
    <visible>!Window.IsVisible(sliderdialog) +!Window.IsVisible(osdvideosettings) + !Window.IsVisible(osdaudiosettings) + !Window.IsVisible(osdsubtitlesettings) + !Window.IsVisible(subtitlesearch) + !Window.IsActive(selectdialog) + !Window.IsVisible(osdcmssettings)</visible>
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
        <posx>0</posx>
        <posy>{{ vscale(-66) }}</posy>
        <width>600</width>
        <height>{{ vscale(66) }}</height>
        <font>font25_title</font>
        <align>center</align>
        <aligny>center</aligny>
        <textcolor>FFEEEEEE</textcolor>
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
            <control type="label">
                <visible>!String.IsEmpty(ListItem.Label2)</visible>
                <posx>20</posx>
                <posy>0</posy>
                <width>176</width>
                <height>{{ row_height|vscale }}</height>
                <font>font20_title</font>
                <align>left</align>
                <aligny>center</aligny>
                <textcolor>DDFFFFFF</textcolor>
                <label>$INFO[ListItem.Label]</label>
            </control>
            <!-- a row without a value (an action - pre-play's Mark Played, Go to..., Delete - or Kodi
                 settings): its name across the card, not clipped to the name column -->
            <control type="label">
                <visible>String.IsEmpty(ListItem.Label2)</visible>
                <posx>20</posx>
                <posy>0</posy>
                <width>560</width>
                <height>{{ row_height|vscale }}</height>
                <font>font20_title</font>
                <align>left</align>
                <aligny>center</aligny>
                <textcolor>DDFFFFFF</textcolor>
                <label>$INFO[ListItem.Label]</label>
            </control>
            <control type="label">
                <posx>216</posx>
                <posy>0</posy>
                <width>364</width>
                <height>{{ row_height|vscale }}</height>
                <font>font8</font>
                <align>right</align>
                <aligny>center</aligny>
                <textcolor>AAFFFFFF</textcolor>
                <label>$INFO[ListItem.Label2]</label>
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
                <visible>!String.IsEmpty(ListItem.Label2)</visible>
                <posx>20</posx>
                <posy>0</posy>
                <width>176</width>
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
                <visible>String.IsEmpty(ListItem.Label2)</visible>
                <posx>20</posx>
                <posy>0</posy>
                <width>560</width>
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
                <posx>216</posx>
                <posy>0</posy>
                <width>364</width>
                <height>{{ row_height|vscale }}</height>
                <font>font8</font>
                <align>right</align>
                <aligny>center</aligny>
                <textcolor>DDFFFFFF</textcolor>
                <scroll>true</scroll>
                <scrollspeed>20</scrollspeed>
                <label>$INFO[ListItem.Label2]</label>
            </control>
        </focusedlayout>
    </control>
    <!-- the pickers', the list's height: it only shows once the list scrolls. Grey focused too, brighter (DDFFFFFF, the
         options' own text) over the 77FFFFFF it's otherwise, rather than the old orange (on request, 2026-10-23) -->
    <control type="scrollbar" id="101">
        <hitrect x="600" y="0" w="50" h="{{ list_height|vscale }}" />
        <left>604</left>
        <top>0</top>
        <width>12</width>
        <height>{{ list_height|vscale }}</height>
        <texturesliderbackground colordiffuse="40000000" border="5">script.plex/white-square-rounded.png</texturesliderbackground>
        <texturesliderbar colordiffuse="77FFFFFF" border="5">script.plex/white-square-rounded.png</texturesliderbar>
        <texturesliderbarfocus colordiffuse="DDFFFFFF" border="5">script.plex/white-square-rounded.png</texturesliderbarfocus>
        <textureslidernib>-</textureslidernib>
        <textureslidernibfocus>-</textureslidernibfocus>
        <pulseonselect>false</pulseonselect>
        <orientation>vertical</orientation>
        <showonepage>false</showonepage>
        <onleft>100</onleft>
    </control>
</control>
