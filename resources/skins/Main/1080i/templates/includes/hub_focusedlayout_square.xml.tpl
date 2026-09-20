<!-- Square focused layout (240x240) - uses hub_id variable. Same card recipe as
     hub_itemlayout_square.xml.tpl (see its own header comment), plus the music screens' focus
     treatment (script-plex-squares.xml.tpl's focusedlayout): 104% zoom about the art's own
     centre and a 246 ring-mask-square.png ring (240 art + the 6px ring-to-image margin the whole
     card recipe uses) tinted FFE9A20D - not the old 110% zoom / home/selected.png 9-slice border.
     The ring is still gated on Control.HasFocus (this layout renders for the selected item of
     every row, focused or not - only the focused row should show a ring). The shadow is not
     gated, matching the music screens, so a row's selected tile keeps its plate when the row
     isn't focused rather than losing it the way the poster/16:9 hub tiles do. -->
<focusedlayout width="272" condition="String.IsEqual(Window.Property(hub.display.{{ hub_id }}),square)">
    <control type="group">
        <!-- 5, not 55: compensates for the parent grouplist's posx moving from 55 to 105
             (see script-plex-recommended.xml.tpl) so this item's resting position is unchanged. -->
        <posx>5</posx>
        <!-- Always top-anchored - see hub_itemlayout_poster.xml.tpl's own matching comment for why
             peek-above's crop no longer needs a manual per-type posy override here. -->
        <!-- 52, matching hub_itemlayout_poster.xml.tpl (was 72): the same title-to-art gap on
             every row type, on request (2026-09-20). ROW_CONTENT_HEIGHT (library.py) dropped by
             the same 20 for this type. -->
        <posy>{{ vscale(52) }}</posy>
        <control type="group">
            <!-- 123 = the art's centre in this group's own frame (3 inset + 240/2). -->
            <animation effect="zoom" start="100" end="104" time="100" center="123,{{ vscale(123) }}" reversible="false">Focus</animation>
            <animation effect="zoom" start="104" end="100" time="100" center="123,{{ vscale(123) }}" reversible="false">UnFocus</animation>
            <posx>0</posx>
            <posy>0</posy>
            <control type="image">
                <posx>0</posx>
                <posy>0</posy>
                <width>264</width>
                <height>{{ vscale(264) }}</height>
                <texture border="24">script.plex/drop-shadow-directional.png</texture>
            </control>
            <control type="group">
                <posx>3</posx>
                <posy>3</posy>
                <control type="group">
                    <visible>!String.IsEmpty(ListItem.Property(is.end))</visible>
                    <control type="image">
                        <posx>0</posx>
                        <posy>0</posy>
                        <width>240</width>
                        <height>{{ vscale(240) }}</height>
                        <texture colordiffuse="FF404040">script.plex/white-square.png</texture>
                    </control>
                    <control type="image">
                        <visible>String.IsEmpty(ListItem.Property(is.updating))</visible>
                        <posx>89.5</posx>
                        <posy>{{ vscale(70) }}</posy>
                        <width>61</width>
                        <height>{{ vscale(100) }}</height>
                        <texture colordiffuse="40000000">script.plex/indicators/chevron-white.png</texture>
                    </control>
                    <control type="image">
                        <visible>!String.IsEmpty(ListItem.Property(is.updating))</visible>
                        <posx>56</posx>
                        <posy>{{ vscale(56) }}</posy>
                        <width>128</width>
                        <height>{{ vscale(128) }}</height>
                        <texture>script.plex/home/busy.gif</texture>
                    </control>
                </control>
                <control type="image">
                    <!-- See hub_itemlayout_square.xml.tpl's own copy of this control for the full
                         reasoning. -->
                    <visible>!String.IsEmpty(ListItem.Property(is.photo))</visible>
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>240</width>
                    <height>{{ vscale(240) }}</height>
                    <texture diffuse="script.plex/masks/square-mask.png">script.plex/white-square.png</texture>
                    <colordiffuse>FF191B1E</colordiffuse>
                </control>
                <control type="image">
                    <!-- Native fallback= - see hub_itemlayout_square.xml.tpl's own copy for the
                         full reasoning. -->
                    <visible>String.IsEmpty(ListItem.Property(is.photo))</visible>
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>240</width>
                    <height>{{ vscale(240) }}</height>
                    <texture background="true" diffuse="script.plex/masks/square-mask.png" fallback="$INFO[ListItem.Property(thumb.fallback)]">$INFO[ListItem.Thumb]</texture>
                    <aspectratio scalediffuse="false">scale</aspectratio>
                </control>
                <control type="image">
                    <visible>!String.IsEmpty(ListItem.Property(is.photo))</visible>
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>240</width>
                    <height>{{ vscale(240) }}</height>
                    <texture background="true" diffuse="script.plex/masks/square-mask.png" fallback="$INFO[ListItem.Property(thumb.fallback)]">$INFO[ListItem.Thumb]</texture>
                    <aspectratio scalediffuse="false">keep</aspectratio>
                </control>
                <control type="group">
                    <visible>!String.IsEmpty(ListItem.Property(progress))</visible>
                    <posx>0</posx>
                    <posy>{{ vscale(230) }}</posy>
                    <control type="image">
                        <posx>0</posx>
                        <posy>0</posy>
                        <width>240</width>
                        <height>{{ vscale(10) }}</height>
                        <texture>script.plex/white-square.png</texture>
                        <colordiffuse>C0000000</colordiffuse>
                    </control>
                    <control type="image">
                        <posx>0</posx>
                        <posy>1</posy>
                        <width>240</width>
                        <height>{{ vscale(8) }}</height>
                        <texture>$INFO[ListItem.Property(progress)]</texture>
                        <colordiffuse>FFCC7B19</colordiffuse>
                    </control>
                </control>
                <!-- hub.nolabels.<id> - see hub_itemlayout_square.xml.tpl's own copy. -->
                <control type="label">
                    <visible>String.IsEmpty(Window.Property(hub.nolabels.{{ hub_id }}))</visible>
                    <scroll>Control.HasFocus({{ hub_id }})</scroll>
                    <posx>0</posx>
                    <posy>{{ vscale(250) }}</posy>
                    <width>240</width>
                    <height>{{ vscale(35) }}</height>
                    <font>font10</font>
                    <align>center</align>
                    <textcolor>FFFFFFFF</textcolor>
                    <label>$INFO[ListItem.Label]</label>
                </control>
                <control type="label">
                    <visible>String.IsEmpty(Window.Property(hub.nolabels.{{ hub_id }})) + !String.IsEmpty(Window.Property(hub.text2lines.{{ hub_id }}))</visible>
                    <scroll>Control.HasFocus({{ hub_id }})</scroll>
                    <posx>0</posx>
                    <posy>{{ vscale(277) }}</posy>
                    <width>240</width>
                    <height>{{ vscale(35) }}</height>
                    <font>font10</font>
                    <align>center</align>
                    <!-- AAFFFFFF, not FFFFFFFF: the music grid's own second-line colour (script-plex-squares.xml.tpl's
                     album.artist label) - title bright, detail line dimmed. -->
                <textcolor>AAFFFFFF</textcolor>
                    <label>$INFO[ListItem.Label2]</label>
                </control>
            </control>
            <control type="image">
                <visible>Control.HasFocus({{ hub_id }})</visible>
                <posx>0</posx>
                <posy>0</posy>
                <width>246</width>
                <height>{{ vscale(246) }}</height>
                <texture diffuse="script.plex/masks/ring-mask-square.png">script.plex/white-square.png</texture>
                <colordiffuse>FFE9A20D</colordiffuse>
            </control>
        </control>
    </control>
</focusedlayout>
