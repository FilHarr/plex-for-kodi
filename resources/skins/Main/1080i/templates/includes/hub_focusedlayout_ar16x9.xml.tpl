<!-- 16x9 focused layout (512x288) - uses hub_id variable. Same card recipe as
     hub_itemlayout_ar16x9.xml.tpl (see its own header comment), plus the episode screen's focus
     treatment (script-plex-episodes.xml.tpl's focusedlayout): 104% zoom about the art's own
     centre and a 518x294 ring-mask-ar16x9.png ring (art + the 6px ring-to-image margin the whole
     card recipe uses) tinted FFE9A20D - not the old 110% zoom / home/selected.png 9-slice border.
     The ring is still gated on Control.HasFocus (this layout renders for the selected item of
     every row, focused or not - only the focused row should show a ring). The shadow is not
     gated, matching the episode screen and the square hub tiles. -->
<focusedlayout width="544" condition="String.IsEqual(Window.Property(hub.display.{{ hub_id }}),ar16x9)">
    <control type="group">
        <!-- 5, not 55: compensates for the parent grouplist's posx moving from 55 to 105
             (see script-plex-recommended.xml.tpl) so this item's resting position is unchanged. -->
        <posx>5</posx>
        <!-- Always top-anchored - see hub_itemlayout_poster.xml.tpl's own matching comment. -->
        <posy>{{ vscale(52) }}</posy>
        <control type="group">
            <!-- 259,147 = the art's centre in this group's own frame (3 inset + 512/2, 3 + 288/2)
                 - the episode screen's own zoom centre. -->
            <animation effect="zoom" start="100" end="104" time="100" center="259,{{ vscale(147) }}" reversible="false">Focus</animation>
            <animation effect="zoom" start="104" end="100" time="100" center="259,{{ vscale(147) }}" reversible="false">UnFocus</animation>
            <posx>0</posx>
            <posy>0</posy>
            <control type="image">
                <posx>0</posx>
                <posy>0</posy>
                <width>536</width>
                <height>{{ vscale(312) }}</height>
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
                        <width>512</width>
                        <height>{{ vscale(288) }}</height>
                        <texture colordiffuse="FF404040">script.plex/white-square.png</texture>
                    </control>
                    <control type="image">
                        <visible>String.IsEmpty(ListItem.Property(is.updating))</visible>
                        <posx>225.5</posx>
                        <posy>{{ vscale(94) }}</posy>
                        <width>61</width>
                        <height>{{ vscale(100) }}</height>
                        <texture colordiffuse="40000000">script.plex/indicators/chevron-white.png</texture>
                    </control>
                    <control type="image">
                        <visible>!String.IsEmpty(ListItem.Property(is.updating))</visible>
                        <posx>192</posx>
                        <posy>{{ vscale(80) }}</posy>
                        <width>128</width>
                        <height>{{ vscale(128) }}</height>
                        <texture>script.plex/home/busy.gif</texture>
                    </control>
                </control>
                <control type="image">
                    <!-- See hub_itemlayout_ar16x9.xml.tpl's own copy of this control for the full
                         reasoning. -->
                    <visible>!String.IsEmpty(ListItem.Property(is.photo))</visible>
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>512</width>
                    <height>{{ vscale(288) }}</height>
                    <texture diffuse="script.plex/masks/ar16x9-mask.png">script.plex/white-square.png</texture>
                    <colordiffuse>FF191B1E</colordiffuse>
                </control>
                <control type="image">
                    <!-- Native fallback= - see hub_itemlayout_ar16x9.xml.tpl's own copy for the
                         full reasoning. -->
                    <visible>String.IsEmpty(ListItem.Property(is.photo))</visible>
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>512</width>
                    <height>{{ vscale(288) }}</height>
                    <texture background="true" diffuse="script.plex/masks/ar16x9-mask.png" fallback="$INFO[ListItem.Property(thumb.fallback)]">$INFO[ListItem.Thumb]</texture>
                    <aspectratio scalediffuse="false">scale</aspectratio>
                </control>
                <control type="image">
                    <visible>!String.IsEmpty(ListItem.Property(is.photo))</visible>
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>512</width>
                    <height>{{ vscale(288) }}</height>
                    <texture background="true" diffuse="script.plex/masks/ar16x9-mask.png" fallback="$INFO[ListItem.Property(thumb.fallback)]">$INFO[ListItem.Thumb]</texture>
                    <aspectratio scalediffuse="false">keep</aspectratio>
                </control>
                <control type="group">
                    <visible>!String.IsEmpty(ListItem.Property(progress))</visible>
                    <posx>8</posx>
                    <posy>{{ vscale(272) }}</posy>
                    <control type="image">
                        <posx>0</posx>
                        <posy>0</posy>
                        <width>496</width>
                        <height>{{ vscale(8) }}</height>
                        <texture diffuse="script.plex/masks/progress-bar-mask.png">script.plex/white-square.png</texture>
                        <colordiffuse>E60A0F1A</colordiffuse>
                    </control>
                    <control type="image">
                        <posx>0</posx>
                        <posy>0</posy>
                        <width>496</width>
                        <height>{{ vscale(8) }}</height>
                        <texture diffuse="script.plex/masks/progress-bar-mask.png">$INFO[ListItem.Property(progress)]</texture>
                        <colordiffuse>FFE5A00D</colordiffuse>
                    </control>
                </control>
                <!-- Episode-number badge + watched indicator - see hub_itemlayout_ar16x9.xml.tpl's
                     own copies. -->
                <control type="group">
                    <visible>!String.IsEmpty(ListItem.Property(episode.number))</visible>
                    <posx>472</posx>
                    <posy>0</posy>
                    <control type="image">
                        <visible>{% if indicators.use_unwatched %}[!String.IsEmpty(ListItem.Property(unwatched)) + String.IsEmpty(ListItem.Property(watched))] | !String.IsEmpty(ListItem.Property(unwatched.count)){% else %}!String.IsEmpty(ListItem.Property(watched)) | !String.IsEmpty(ListItem.Property(unwatched.count)){% endif %}</visible>
                        <posx>0</posx>
                        <posy>0</posy>
                        <width>40</width>
                        <height>{{ vscale(32) }}</height>
                        <texture diffuse="script.plex/masks/badge-mask-tr-only.png">script.plex/white-square.png</texture>
                        <colordiffuse>{{ indicators.watched_bg|default("CC000000") }}</colordiffuse>
                    </control>
                    <control type="image">
                        <visible>{% if indicators.use_unwatched %}[String.IsEmpty(ListItem.Property(unwatched)) | !String.IsEmpty(ListItem.Property(watched))] + String.IsEmpty(ListItem.Property(unwatched.count)){% else %}String.IsEmpty(ListItem.Property(watched)) + String.IsEmpty(ListItem.Property(unwatched.count)){% endif %}</visible>
                        <posx>0</posx>
                        <posy>0</posy>
                        <width>40</width>
                        <height>{{ vscale(32) }}</height>
                        <texture diffuse="script.plex/masks/badge-mask-tr.png">script.plex/white-square.png</texture>
                        <colordiffuse>{{ indicators.watched_bg|default("CC000000") }}</colordiffuse>
                    </control>
                    <control type="label">{# rendered big then zoomed down so it never truncates/ellipsizes at the badge's actual width #}
                        <animation effect="zoom" start="33" end="33" time="0" reversible="false" center="auto" condition="true">Conditional</animation>
                        <posx>-20</posx>
                        <posy>{{ vscale(-8) }}</posy>
                        <width>80</width>
                        <height>{{ vscale(48) }}</height>
                        <font>font32_title</font>
                        <align>center</align>
                        <aligny>center</aligny>
                        <textcolor>{{ indicators.textcolor|default("FFFFFFFF") }}</textcolor>
                        <label>$INFO[ListItem.Property(episode.number)]</label>
                    </control>
                </control>
                <control type="group">
                    <visible>!String.IsEmpty(ListItem.Property(episode.number))</visible>
                    {% include "includes/watched_indicator.xml.tpl" with xoff=472 & uw_size=35 & wbg_w=40 & wbg="script.plex/masks/badge-mask-bl-only.png" %}
                </control>
                <control type="group">
                    <visible>String.IsEmpty(ListItem.Property(episode.number))</visible>
                    {% include "includes/watched_indicator.xml.tpl" with xoff=512 & uw_size=35 & wbg_w=40 %}
                </control>
            </control>
            <control type="image">
                <visible>Control.HasFocus({{ hub_id }})</visible>
                <posx>0</posx>
                <posy>0.5</posy>
                <width>518</width>
                <height>{{ vscale(294) }}</height>
                <texture diffuse="script.plex/masks/ring-mask-ar16x9.png">script.plex/white-square.png</texture>
                <colordiffuse>FFE9A20D</colordiffuse>
            </control>
        </control>
    </control>
</focusedlayout>
