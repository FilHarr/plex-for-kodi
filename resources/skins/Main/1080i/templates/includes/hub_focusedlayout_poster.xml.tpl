<!-- Poster focused layout (220x325) - uses hub_id variable -->
<focusedlayout width="248" condition="String.IsEqual(Window.Property(hub.display.{{ hub_id }}),poster)">
    <control type="group">
        <!-- 10, not 55: compensates for the parent grouplist's posx moving from 55 to 100
             (see script-plex-home.xml.tpl) so this item's resting position is unchanged. -->
        <posx>10</posx>
        <!-- Always top-anchored - see hub_itemlayout_poster.xml.tpl's own matching comment for why
             peek-above's crop no longer needs a manual per-type posy override here. -->
        <posy>{{ vscale(72) }}</posy>
        <control type="group">
            <animation effect="zoom" start="100" end="110" time="100" center="110,{{ vscale(162.5) }}" reversible="false">Focus</animation>
            <animation effect="zoom" start="110" end="100" time="100" center="110,{{ vscale(162.5) }}" reversible="false">UnFocus</animation>
            <posx>0</posx>
            <posy>0</posy>
            <control type="image">
                <visible>Control.HasFocus({{ hub_id }})</visible>
                <posx>-36</posx>
                <posy>{{ vscale(-36) }}</posy>
                <width>301</width>
                <height>{{ vscale(406) }}</height>
                <texture border="42">script.plex/drop-shadow.png</texture>
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
                        <height>{{ vscale(325) }}</height>
                        <texture colordiffuse="FF404040">script.plex/white-square.png</texture>
                    </control>
                    <control type="image">
                        <visible>String.IsEmpty(ListItem.Property(is.updating))</visible>
                        <posx>82.5</posx>
                        <posy>{{ vscale(117.5) }}</posy>
                        <width>55</width>
                        <height>{{ vscale(90) }}</height>
                        <texture colordiffuse="40000000">script.plex/indicators/chevron-white.png</texture>
                    </control>
                    <control type="image">
                        <visible>!String.IsEmpty(ListItem.Property(is.updating))</visible>
                        <posx>52</posx>
                        <posy>{{ vscale(105) }}</posy>
                        <width>115</width>
                        <height>{{ vscale(115) }}</height>
                        <texture>script.plex/home/busy.gif</texture>
                    </control>
                </control>
                <control type="image">
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>220</width>
                    <height>{{ vscale(325) }}</height>
                    <texture diffuse="script.plex/masks/poster-mask.png">$INFO[ListItem.Property(thumb.fallback)]</texture>
                </control>
                <control type="image">
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>220</width>
                    <height>{{ vscale(325) }}</height>
                    <texture background="true" diffuse="script.plex/masks/poster-mask.png">$INFO[ListItem.Thumb]</texture>
                    <aspectratio scalediffuse="false">scale</aspectratio>
                </control>
                <control type="group">
                    <!-- See hub_itemlayout_poster.xml.tpl's own copy of this control for the full
                         reasoning - kept identical here so the bar doesn't jump on focus change. -->
                    <visible>!String.IsEmpty(ListItem.Property(progress))</visible>
                    <posx>8</posx>
                    <posy>{{ vscale(309) }}</posy>
                    <control type="image">
                        <posx>0</posx>
                        <posy>0</posy>
                        <width>204</width>
                        <height>{{ vscale(8) }}</height>
                        <texture diffuse="script.plex/masks/progress-bar-mask.png">script.plex/white-square.png</texture>
                        <colordiffuse>E60A0F1A</colordiffuse>
                    </control>
                    <control type="image">
                        <posx>0</posx>
                        <posy>0</posy>
                        <width>204</width>
                        <height>{{ vscale(8) }}</height>
                        <texture diffuse="script.plex/masks/progress-bar-mask.png">$INFO[ListItem.Property(progress)]</texture>
                        <colordiffuse>FFE5A00D</colordiffuse>
                    </control>
                </control>
                {% include "includes/watched_indicator.xml.tpl" with xoff=220 & uw_size=43 & with_count=True & scale="medium" %}
            </control>
            <control type="image">
                <visible>Control.HasFocus({{ hub_id }})</visible>
                <posx>0</posx>
                <posy>0</posy>
                <width>226</width>
                <height>{{ vscale(331) }}</height>
                <texture border="10">script.plex/home/selected.png</texture>
            </control>
        </control>
    </control>
</focusedlayout>
