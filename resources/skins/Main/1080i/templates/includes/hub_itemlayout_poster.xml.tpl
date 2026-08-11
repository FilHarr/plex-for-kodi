<!-- Poster item layout (220x325) - uses hub_id variable -->
<itemlayout width="248" condition="String.IsEqual(Window.Property(hub.display.{{ hub_id }}),poster)">
    <control type="group">
        <!-- 10, not 55: compensates for the parent grouplist's posx moving from 55 to 100
             (see script-plex-home.xml.tpl) so this item's resting position is unchanged. -->
        <posx>10</posx>
        <!-- hub_id 401 (peek-above, script-plex-home.xml.tpl's grouplist 501) shows the *bottom* of
             the item instead of the top: -51 = 277 (that grouplist's own height) - 328 (this item's
             own full content height: 3 inner group posy + 325 art) - pushes the item up so its
             bottom edge lands flush with the wrapper's own bottom, with the top (and the row title,
             which peek-above omits entirely) clipped away above y=0. -->
        <posy>{% if hub_id == 401 %}{{ vscale(-51) }}{% else %}{{ vscale(72) }}{% endif %}</posy>
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
                <!-- Matches official Plex's own poster progress bar: inset from the art's edges
                     (not full-bleed) and lifted clear of the bottom corner (not flush with it),
                     pill-shaped via the same diffuse-mask technique as the poster corners
                     themselves (masks/progress-bar-mask.png, radius = half the bar's own height).
                     Track and fill share one identical box - the progress percentage asset
                     (util.getProgressImage(), $INFO[ListItem.Property(progress)]) is always a
                     fixed-width strip with only its own left portion opaque, so masking it at full
                     box size still gives a clean rounded left cap and a plain straight-cut right
                     edge wherever the fill happens to end, with no separate inset needed to hide
                     square corners. Fill colour FFE5A00D matches official's measured fill exactly -
                     it's also this skin's own existing accent gold (see e.g. the meta row's
                     remainingTime pill). -->
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
    </control>
</itemlayout>
