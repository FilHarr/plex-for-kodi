<!-- Poster item layout (220x325) - uses hub_id variable -->
<itemlayout width="248" condition="String.IsEqual(Window.Property(hub.display.{{ hub_id }}),poster)">
    <control type="group">
        <!-- 10, not 55: compensates for the parent grouplist's posx moving from 55 to 100
             (see script-plex-home.xml.tpl) so this item's resting position is unchanged. -->
        <posx>10</posx>
        <!-- Always top-anchored, same posy regardless of role/hub_id - peek-above's own "bottom-
             flush, tail end" crop look no longer needs a manual per-type negative-posy override
             here: it falls out for free once row positions are computed by the stacking formula in
             script-plex-home.xml.tpl's own comment (see there for the full reasoning) - grouplist
             50's real clip cuts off whatever pokes out above it, at whatever position this row is
             currently at. -->
        <posy>{{ vscale(72) }}</posy>
        <control type="group">
            <control type="image">
                <posx>0</posx>
                <posy>0</posy>
                <width>244</width>
                <height>{{ vscale(349) }}</height>
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
                <!-- Native fallback= (not a separate stacked/masked control - see this include's
                     own history) - Kodi shows this while ListItem.Thumb is empty/loading/failed,
                     swapping seamlessly once it resolves, so there's only ever one masked layer for
                     the art, never two independently-rounded corners that could misalign. -->
                <posx>0</posx>
                <posy>0</posy>
                <width>220</width>
                <height>{{ vscale(325) }}</height>
                <texture background="true" diffuse="script.plex/masks/poster-mask.png" fallback="$INFO[ListItem.Property(thumb.fallback)]">$INFO[ListItem.Thumb]</texture>
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
