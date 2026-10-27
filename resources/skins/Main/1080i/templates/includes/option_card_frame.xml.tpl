<!-- The option pickers' card frame, list and scrollbar (script-plex-settings_select_dialog): list_height is the
     list's and the scrollbar's height (Kodi can't resize a scrollbar from Python), in whole rows; row_height the
     row pitch and card_height its card (row_height less 6: 3 clear above and below); line1_y/line2_y the two-line
     rows' 22-high lines, centred on the card 24 apart: 61 rows (55 cards), lines at 7.5 and 31.5, 13 rows (793).
     tick_y centres the current option's 26 tick on the row: 17.5 on 61. -->
<!-- The Libraries picker's card style (script-plex-card_list.xml.tpl), at its 600 width: a F2111111 backdrop (95%) 20
     wider than the list each side with the heading in its top 66, each option its own 99111111 card (58 high in
     a 64 pitch - the picker's 78/84 less 10 top and bottom, as the Settings dialog's), the focused one lit with 33FFFFFF, font8 text, and a second line (Label2 - an audio track's
     detail, say) under it, dimmer, as the picker's server is. frame_x/frame_y (group 200's place, the list's top
     left), backdrop_height and shadow_height are the frame's own, so it opens in place - placed only from Python,
     a slower box (a Shield) showed it centred first, then jumping to the right. SelectDialog.fitFrame() sizes the
     list to the options (up to 13, then it scrolls). list_width is the list's and its cards' (600), text_width
     the option labels' (520, clear of the tick at tick_x, 554), label_width the heading's and a group row's (560),
     backdrop_y/backdrop_width the panel's top (-66, the heading in it) and width (640), shadow_y/shadow_width its
     shadow's, scrollbar_x the scrollbar's (604): the user menu's (script-plex-user_menu.xml.tpl) are narrower,
     with no heading. -->
<!-- The full-screen dim behind it: 30% black, the screens' own row-scroll dim's (default_background.xml.tpl),
     shown with the frame below. None for a picker opened over another one (nested, SelectDialog), whose dim
     is already there. -->
<control type="image">
    <visible>!Window.IsVisible(subtitlesearch) + !Window.IsVisible(sliderdialog) + String.IsEmpty(Window.Property(nested))</visible>
    <posx>0</posx>
    <posy>0</posy>
    <width>1920</width>
    <height>1080</height>
    <texture>script.plex/white-square.png</texture>
    <colordiffuse>4D000000</colordiffuse>
</control>
<control type="group" id="200">
    <!-- out of the way of what its choices open: Kodi's subtitle search and the delay slider -->
    <visible>!Window.IsVisible(subtitlesearch) + !Window.IsVisible(sliderdialog)</visible>
    <!-- A sidebar section's menu (SelectDialog's beside_sidebar): next to the expanded sidebar, as the Libraries
         picker and Manage Hubs (dropdown.CardListDialog) - its panel's left edge at 325, the content's with the
         sidebar open, so the list at 345: 945 left of 1290. A slide that takes no time, from its first frame, so
         it never shows at the right first (the property's set before it's shown). -->
    <animation effect="slide" end="-945,0" time="0" condition="!String.IsEmpty(Window.Property(beside_sidebar))">Conditional</animation>
    <posx>{{ frame_x }}</posx>
    <posy>{{ frame_y|vscale }}</posy>
    <control type="image" id="202">
        <posx>-60</posx>
        <posy>{{ shadow_y|vscale }}</posy>
        <width>{{ shadow_width }}</width>
        <height>{{ shadow_height|vscale }}</height>
        <texture border="42">script.plex/drop-shadow.png</texture>
    </control>
    <control type="image" id="201">
        <posx>-20</posx>
        <posy>{{ backdrop_y|vscale }}</posy>
        <width>{{ backdrop_width }}</width>
        <height>{{ backdrop_height|vscale }}</height>
        <texture colordiffuse="F2111111" border="10">script.plex/white-square-rounded.png</texture>
    </control>
    <control type="label">
        <posx>20</posx>
        <posy>{{ vscale(-66) }}</posy>
        <width>{{ label_width }}</width>
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
        <width>{{ list_width }}</width>
        <height>{{ list_height|vscale }}</height>
        <onup>noop</onup>
        <ondown>noop</ondown>
        <onleft>noop</onleft>
        <onright>101</onright>
        <scrolltime>200</scrolltime>
        <orientation>vertical</orientation>
        <pagecontrol>101</pagecontrol>
        <itemlayout height="{{ row_height|vscale }}">
            <control type="group">
                <visible>String.IsEmpty(ListItem.Property(group))</visible>
                <control type="image">
                    <posx>0</posx>
                    <posy>{{ vscale(3) }}</posy>
                    <width>{{ list_width }}</width>
                    <height>{{ card_height|vscale }}</height>
                    <texture colordiffuse="99111111" border="10">script.plex/white-square-rounded.png</texture>
                </control>
                <!-- font8: one line, or the option over its detail, told apart by brightness, centred on the card -->
                <control type="label">
                    <visible>String.IsEmpty(ListItem.Label2) + String.IsEmpty(ListItem.Property(menu))</visible>
                    <posx>20</posx>
                    <posy>0</posy>
                    <width>{{ text_width }}</width>
                    <height>{{ row_height|vscale }}</height>
                    <font>font8</font>
                    <align>left</align>
                    <aligny>center</aligny>
                    <textcolor>DDFFFFFF</textcolor>
                    <label>$INFO[ListItem.Label]</label>
                </control>
                <!-- a menu (showOptionsDialog(menu=True): a screen's first pop-up, its rows actions): the
                     option as the More settings rows have theirs, font20_title -->
                <control type="label">
                    <visible>String.IsEmpty(ListItem.Label2) + !String.IsEmpty(ListItem.Property(menu))</visible>
                    <posx>20</posx>
                    <posy>0</posy>
                    <width>{{ text_width }}</width>
                    <height>{{ row_height|vscale }}</height>
                    <font>font20_title</font>
                    <align>left</align>
                    <aligny>center</aligny>
                    <textcolor>DDFFFFFF</textcolor>
                    <label>$INFO[ListItem.Label]</label>
                </control>
                <control type="label">
                    <visible>!String.IsEmpty(ListItem.Label2) + String.IsEmpty(ListItem.Property(menu))</visible>
                    <posx>20</posx>
                    <posy>{{ line1_y|vscale }}</posy>
                    <width>{{ text_width }}</width>
                    <height>{{ vscale(22) }}</height>
                    <font>font8</font>
                    <align>left</align>
                    <aligny>center</aligny>
                    <textcolor>DDFFFFFF</textcolor>
                    <label>$INFO[ListItem.Label]</label>
                </control>
                <!-- a menu (showOptionsDialog(menu=True): a screen's first pop-up, its rows actions): the
                     option as the More settings rows have theirs, font20_title -->
                <control type="label">
                    <visible>!String.IsEmpty(ListItem.Label2) + !String.IsEmpty(ListItem.Property(menu))</visible>
                    <posx>20</posx>
                    <posy>{{ line1_y|vscale }}</posy>
                    <width>{{ text_width }}</width>
                    <height>{{ vscale(22) }}</height>
                    <font>font20_title</font>
                    <align>left</align>
                    <aligny>center</aligny>
                    <textcolor>DDFFFFFF</textcolor>
                    <label>$INFO[ListItem.Label]</label>
                </control>
                <control type="label">
                    <visible>!String.IsEmpty(ListItem.Label2)</visible>
                    <posx>20</posx>
                    <posy>{{ line2_y|vscale }}</posy>
                    <width>{{ text_width }}</width>
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
                    <posx>{{ tick_x }}</posx>
                    <posy>{{ tick_y|vscale }}</posy>
                    <width>26</width>
                    <height>{{ vscale(26) }}</height>
                    <texture colordiffuse="DDFFFFFF">script.plex/indicators/tick.png</texture>
                    <aspectratio>keep</aspectratio>
                </control>
                <!-- a row that opens more choices of its own (a 'more' property, showOptionsDialog()'s fourth
                     element): indicators/angle-small-right.png where the tick goes - the tick instead once it's
                     ticked -->
                <control type="image">
                    <visible>!String.IsEmpty(ListItem.Property(more)) + String.IsEmpty(ListItem.Property(current))</visible>
                    <posx>{{ tick_x }}</posx>
                    <posy>{{ tick_y|vscale }}</posy>
                    <width>26</width>
                    <height>{{ vscale(26) }}</height>
                    <texture colordiffuse="DDFFFFFF">script.plex/indicators/angle-small-right.png</texture>
                    <aspectratio>keep</aspectratio>
                </control>
            </control>
            <!-- a group row (dialog.optionGroup()): no card, and its title, if it has one, as the heading of the
                 cards under it - in the picker's heading's font25_title and FFEEEEEE, low in the row, so
                 it sits with them -->
            <control type="label">
                <visible>!String.IsEmpty(ListItem.Property(group))</visible>
                <posx>20</posx>
                <posy>{{ vscale(26) }}</posy>
                <width>{{ label_width }}</width>
                <height>{{ vscale(35) }}</height>
                <font>font25_title</font>
                <align>left</align>
                <aligny>center</aligny>
                <textcolor>FFEEEEEE</textcolor>
                <label>$INFO[ListItem.Label]</label>
            </control>
        </itemlayout>
        <focusedlayout height="{{ row_height|vscale }}">
            <control type="group">
                <visible>String.IsEmpty(ListItem.Property(group))</visible>
                <control type="image">
                    <posx>0</posx>
                    <posy>{{ vscale(3) }}</posy>
                    <width>{{ list_width }}</width>
                    <height>{{ card_height|vscale }}</height>
                    <texture colordiffuse="99111111" border="10">script.plex/white-square-rounded.png</texture>
                </control>
                <control type="image">
                    <visible>Control.HasFocus(100)</visible>
                    <posx>0</posx>
                    <posy>{{ vscale(3) }}</posy>
                    <width>{{ list_width }}</width>
                    <height>{{ card_height|vscale }}</height>
                    <texture colordiffuse="33FFFFFF" border="10">script.plex/white-square-rounded.png</texture>
                </control>
                <control type="label">
                    <visible>String.IsEmpty(ListItem.Label2) + String.IsEmpty(ListItem.Property(menu))</visible>
                    <posx>20</posx>
                    <posy>0</posy>
                    <width>{{ text_width }}</width>
                    <height>{{ row_height|vscale }}</height>
                    <font>font8</font>
                    <align>left</align>
                    <aligny>center</aligny>
                    <textcolor>FFFFFFFF</textcolor>
                    <scroll>true</scroll>
                    <scrollspeed>20</scrollspeed>
                    <label>$INFO[ListItem.Label]</label>
                </control>
                <!-- a menu (showOptionsDialog(menu=True): a screen's first pop-up, its rows actions): the
                     option as the More settings rows have theirs, font20_title -->
                <control type="label">
                    <visible>String.IsEmpty(ListItem.Label2) + !String.IsEmpty(ListItem.Property(menu))</visible>
                    <posx>20</posx>
                    <posy>0</posy>
                    <width>{{ text_width }}</width>
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
                    <visible>!String.IsEmpty(ListItem.Label2) + String.IsEmpty(ListItem.Property(menu))</visible>
                    <posx>20</posx>
                    <posy>{{ line1_y|vscale }}</posy>
                    <width>{{ text_width }}</width>
                    <height>{{ vscale(22) }}</height>
                    <font>font8</font>
                    <align>left</align>
                    <aligny>center</aligny>
                    <textcolor>FFFFFFFF</textcolor>
                    <scroll>true</scroll>
                    <scrollspeed>20</scrollspeed>
                    <label>$INFO[ListItem.Label]</label>
                </control>
                <!-- a menu (showOptionsDialog(menu=True): a screen's first pop-up, its rows actions): the
                     option as the More settings rows have theirs, font20_title -->
                <control type="label">
                    <visible>!String.IsEmpty(ListItem.Label2) + !String.IsEmpty(ListItem.Property(menu))</visible>
                    <posx>20</posx>
                    <posy>{{ line1_y|vscale }}</posy>
                    <width>{{ text_width }}</width>
                    <height>{{ vscale(22) }}</height>
                    <font>font20_title</font>
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
                    <width>{{ text_width }}</width>
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
                    <posx>{{ tick_x }}</posx>
                    <posy>{{ tick_y|vscale }}</posy>
                    <width>26</width>
                    <height>{{ vscale(26) }}</height>
                    <texture colordiffuse="FFFFFFFF">script.plex/indicators/tick.png</texture>
                    <aspectratio>keep</aspectratio>
                </control>
                <!-- a row that opens more choices of its own (a 'more' property, showOptionsDialog()'s fourth
                     element): indicators/angle-small-right.png where the tick goes - the tick instead once it's
                     ticked -->
                <control type="image">
                    <visible>!String.IsEmpty(ListItem.Property(more)) + String.IsEmpty(ListItem.Property(current))</visible>
                    <posx>{{ tick_x }}</posx>
                    <posy>{{ tick_y|vscale }}</posy>
                    <width>26</width>
                    <height>{{ vscale(26) }}</height>
                    <texture colordiffuse="FFFFFFFF">script.plex/indicators/angle-small-right.png</texture>
                    <aspectratio>keep</aspectratio>
                </control>
            </control>
            <!-- a group row (dialog.optionGroup()): no card, and its title, if it has one, as the heading of the
                 cards under it - in the picker's heading's font25_title and FFEEEEEE, low in the row, so
                 it sits with them -->
            <control type="label">
                <visible>!String.IsEmpty(ListItem.Property(group))</visible>
                <posx>20</posx>
                <posy>{{ vscale(26) }}</posy>
                <width>{{ label_width }}</width>
                <height>{{ vscale(35) }}</height>
                <font>font25_title</font>
                <align>left</align>
                <aligny>center</aligny>
                <textcolor>FFEEEEEE</textcolor>
                <label>$INFO[ListItem.Label]</label>
            </control>
        </focusedlayout>
    </control>
    <!-- the picker's, the list's height: it only shows once the list scrolls. Grey focused too, brighter (DDFFFFFF, the
         options' own text) over the 77FFFFFF it's otherwise, rather than the old orange (on request, 2026-10-23) -->
    <control type="scrollbar" id="101">
        <hitrect x="{{ list_width }}" y="0" w="50" h="{{ list_height|vscale }}" />
        <left>{{ scrollbar_x }}</left>
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
