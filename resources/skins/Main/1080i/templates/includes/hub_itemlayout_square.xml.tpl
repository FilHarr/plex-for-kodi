<!-- Square item layout (244x244) - uses hub_id variable -->
<itemlayout width="287" condition="String.IsEqual(Window.Property(hub.display.{{ hub_id }}),square)">
    <control type="group">
        <!-- 10, not 55: compensates for the parent grouplist's posx moving from 55 to 100
             (see script-plex-home.xml.tpl) so this item's resting position is unchanged. -->
        <posx>10</posx>
        <!-- hub_id 401 (peek-above, script-plex-home.xml.tpl's grouplist 501) shows the *bottom* of
             the item instead of the top: -44 = 277 (that grouplist's own height) - 321 (this item's
             own full content height: 5 inner group posy + 316 worst-case 2-line label bottom) -
             pushes the item up so its bottom edge lands flush with the wrapper's own bottom, with
             the top (and the row title, which peek-above omits entirely) clipped away above y=0. -->
        <posy>{% if hub_id == 401 %}{{ vscale(-44) }}{% else %}{{ vscale(72) }}{% endif %}</posy>
        <control type="group">
            <posx>5</posx>
            <posy>5</posy>
            <control type="group">
                <visible>!String.IsEmpty(ListItem.Property(is.end))</visible>
                <control type="image">
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>244</width>
                    <height>{{ vscale(244) }}</height>
                    <texture colordiffuse="FF404040">script.plex/white-square.png</texture>
                </control>
                <control type="image">
                    <visible>String.IsEmpty(ListItem.Property(is.updating))</visible>
                    <posx>91.5</posx>
                    <posy>{{ vscale(72) }}</posy>
                    <width>61</width>
                    <height>{{ vscale(100) }}</height>
                    <texture colordiffuse="40000000">script.plex/indicators/chevron-white.png</texture>
                </control>
                <control type="image">
                    <visible>!String.IsEmpty(ListItem.Property(is.updating))</visible>
                    <posx>58</posx>
                    <posy>{{ vscale(58) }}</posy>
                    <width>128</width>
                    <height>{{ vscale(128) }}</height>
                    <texture>script.plex/home/busy.gif</texture>
                </control>
            </control>
            <control type="image">
                <posx>0</posx>
                <posy>0</posy>
                <width>244</width>
                <height>{{ vscale(244) }}</height>
                <texture>$INFO[ListItem.Property(thumb.fallback)]</texture>
            </control>
            <control type="image">
                <posx>0</posx>
                <posy>0</posy>
                <width>244</width>
                <height>{{ vscale(244) }}</height>
                <texture background="true">$INFO[ListItem.Thumb]</texture>
                <aspectratio>scale</aspectratio>
            </control>
            <control type="group">
                <visible>!String.IsEmpty(ListItem.Property(progress))</visible>
                <posx>0</posx>
                <posy>{{ vscale(234) }}</posy>
                <control type="image">
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>244</width>
                    <height>{{ vscale(10) }}</height>
                    <texture>script.plex/white-square.png</texture>
                    <colordiffuse>C0000000</colordiffuse>
                </control>
                <control type="image">
                    <posx>0</posx>
                    <posy>1</posy>
                    <width>244</width>
                    <height>{{ vscale(8) }}</height>
                    <texture>$INFO[ListItem.Property(progress)]</texture>
                    <colordiffuse>FFCC7B19</colordiffuse>
                </control>
            </control>
            <control type="label">
                <scroll>false</scroll>
                <posx>0</posx>
                <posy>{{ vscale(254) }}</posy>
                <width>244</width>
                <height>{{ vscale(35) }}</height>
                <font>font10</font>
                <align>center</align>
                <textcolor>FFFFFFFF</textcolor>
                <label>$INFO[ListItem.Label]</label>
            </control>
            <control type="label">
                <scroll>false</scroll>
                <visible>!String.IsEmpty(Window.Property(hub.text2lines.{{ hub_id }}))</visible>
                <posx>0</posx>
                <posy>{{ vscale(281) }}</posy>
                <width>244</width>
                <height>{{ vscale(35) }}</height>
                <font>font10</font>
                <align>center</align>
                <textcolor>FFFFFFFF</textcolor>
                <label>$INFO[ListItem.Label2]</label>
            </control>
        </control>
    </control>
</itemlayout>
