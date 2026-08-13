<!-- Square item layout (220x220) - uses hub_id variable -->
<itemlayout width="263" condition="String.IsEqual(Window.Property(hub.display.{{ hub_id }}),square)">
    <control type="group">
        <!-- 10, not 55: compensates for the parent grouplist's posx moving from 55 to 100
             (see script-plex-home.xml.tpl) so this item's resting position is unchanged. -->
        <posx>10</posx>
        <!-- Always top-anchored - see hub_itemlayout_poster.xml.tpl's own matching comment for why
             peek-above's crop no longer needs a manual per-type posy override here. -->
        <posy>{{ vscale(72) }}</posy>
        <control type="group">
            <control type="image">
                <posx>0</posx>
                <posy>0</posy>
                <width>244</width>
                <height>{{ vscale(244) }}</height>
                <texture border="24">script.plex/drop-shadow-directional.png</texture>
            </control>
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
                <!-- Fill for is.photo's letterboxed thumb below - photos keep their full frame
                     (no crop) so this shows through wherever the image doesn't reach. -->
                <visible>!String.IsEmpty(ListItem.Property(is.photo))</visible>
                <posx>0</posx>
                <posy>0</posy>
                <width>220</width>
                <height>{{ vscale(220) }}</height>
                <texture diffuse="script.plex/masks/square-mask.png">script.plex/white-square.png</texture>
                <colordiffuse>FF191B1E</colordiffuse>
            </control>
            <control type="image">
                <!-- Native fallback= (not a separate stacked/masked control - see this include's
                     own history) - Kodi shows this while ListItem.Thumb is empty/loading/failed,
                     swapping seamlessly once it resolves, so there's only ever one masked layer for
                     the art, never two independently-rounded corners that could misalign. -->
                <visible>String.IsEmpty(ListItem.Property(is.photo))</visible>
                <posx>0</posx>
                <posy>0</posy>
                <width>220</width>
                <height>{{ vscale(220) }}</height>
                <texture background="true" diffuse="script.plex/masks/square-mask.png" fallback="$INFO[ListItem.Property(thumb.fallback)]">$INFO[ListItem.Thumb]</texture>
                <aspectratio scalediffuse="false">scale</aspectratio>
            </control>
            <control type="image">
                <!-- Real photos vary wildly in aspect ratio - crop-to-fill (like posters/art) would
                     chop off arbitrary parts of someone's actual photo, so these get shown whole
                     and letterboxed instead, matching Plex's own photo hub presentation. -->
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
                <scroll>false</scroll>
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
                <scroll>false</scroll>
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
    </control>
</itemlayout>
