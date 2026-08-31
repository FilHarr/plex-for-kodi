<!-- Square focused layout (220x220) - uses hub_id variable -->
<focusedlayout width="263" condition="String.IsEqual(Window.Property(hub.display.{{ hub_id }}),square)">
    <control type="group">
        <!-- 5, not 55: compensates for the parent grouplist's posx moving from 55 to 105
             (see script-plex-recommended.xml.tpl) so this item's resting position is unchanged. -->
        <posx>5</posx>
        <!-- Always top-anchored - see hub_itemlayout_poster.xml.tpl's own matching comment for why
             peek-above's crop no longer needs a manual per-type posy override here. -->
        <posy>{{ vscale(72) }}</posy>
        <control type="group">
            <animation effect="zoom" start="100" end="110" time="100" center="110,{{ vscale(110) }}" reversible="false">Focus</animation>
            <animation effect="zoom" start="110" end="100" time="100" center="110,{{ vscale(110) }}" reversible="false">UnFocus</animation>
            <posx>0</posx>
            <posy>0</posy>
            <control type="image">
                <visible>Control.HasFocus({{ hub_id }})</visible>
                <posx>0</posx>
                <posy>0</posy>
                <width>244</width>
                <height>{{ vscale(244) }}</height>
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
                        <width>220</width>
                        <height>{{ vscale(220) }}</height>
                        <texture colordiffuse="FF404040">script.plex/white-square.png</texture>
                    </control>
                    <control type="image">
                        <visible>String.IsEmpty(ListItem.Property(is.updating))</visible>
                        <posx>79.5</posx>
                        <posy>{{ vscale(60) }}</posy>
                        <width>61</width>
                        <height>{{ vscale(100) }}</height>
                        <texture colordiffuse="40000000">script.plex/indicators/chevron-white.png</texture>
                    </control>
                    <control type="image">
                        <visible>!String.IsEmpty(ListItem.Property(is.updating))</visible>
                        <posx>46</posx>
                        <posy>{{ vscale(46) }}</posy>
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
                    <width>220</width>
                    <height>{{ vscale(220) }}</height>
                    <texture diffuse="script.plex/masks/square-mask.png">script.plex/white-square.png</texture>
                    <colordiffuse>FF191B1E</colordiffuse>
                </control>
                <control type="image">
                    <!-- Native fallback= - see hub_itemlayout_square.xml.tpl's own copy for the
                         full reasoning. -->
                    <visible>String.IsEmpty(ListItem.Property(is.photo))</visible>
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>220</width>
                    <height>{{ vscale(220) }}</height>
                    <texture background="true" diffuse="script.plex/masks/square-mask.png" fallback="$INFO[ListItem.Property(thumb.fallback)]">$INFO[ListItem.Thumb]</texture>
                    <aspectratio scalediffuse="false">scale</aspectratio>
                </control>
                <control type="image">
                    <visible>!String.IsEmpty(ListItem.Property(is.photo))</visible>
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>220</width>
                    <height>{{ vscale(220) }}</height>
                    <texture background="true" diffuse="script.plex/masks/square-mask.png" fallback="$INFO[ListItem.Property(thumb.fallback)]">$INFO[ListItem.Thumb]</texture>
                    <aspectratio scalediffuse="false">keep</aspectratio>
                </control>
                <control type="group">
                    <visible>!String.IsEmpty(ListItem.Property(progress))</visible>
                    <posx>0</posx>
                    <posy>{{ vscale(210) }}</posy>
                    <control type="image">
                        <posx>0</posx>
                        <posy>0</posy>
                        <width>220</width>
                        <height>{{ vscale(10) }}</height>
                        <texture>script.plex/white-square.png</texture>
                        <colordiffuse>C0000000</colordiffuse>
                    </control>
                    <control type="image">
                        <posx>0</posx>
                        <posy>1</posy>
                        <width>220</width>
                        <height>{{ vscale(8) }}</height>
                        <texture>$INFO[ListItem.Property(progress)]</texture>
                        <colordiffuse>FFCC7B19</colordiffuse>
                    </control>
                </control>
                <control type="label">
                    <scroll>Control.HasFocus({{ hub_id }})</scroll>
                    <posx>0</posx>
                    <posy>{{ vscale(230) }}</posy>
                    <width>220</width>
                    <height>{{ vscale(35) }}</height>
                    <font>font10</font>
                    <align>center</align>
                    <textcolor>FFFFFFFF</textcolor>
                    <label>$INFO[ListItem.Label]</label>
                </control>
                <control type="label">
                    <scroll>Control.HasFocus({{ hub_id }})</scroll>
                    <visible>!String.IsEmpty(Window.Property(hub.text2lines.{{ hub_id }}))</visible>
                    <posx>0</posx>
                    <posy>{{ vscale(257) }}</posy>
                    <width>220</width>
                    <height>{{ vscale(35) }}</height>
                    <font>font10</font>
                    <align>center</align>
                    <textcolor>FFFFFFFF</textcolor>
                    <label>$INFO[ListItem.Label2]</label>
                </control>
            </control>
            <control type="image">
                <visible>Control.HasFocus({{ hub_id }})</visible>
                <posx>0</posx>
                <posy>0</posy>
                <width>226</width>
                <height>{{ vscale(226) }}</height>
                <texture border="10">script.plex/home/selected.png</texture>
            </control>
        </control>
    </control>
</focusedlayout>
