<!-- Poster item layout (240x360) - uses hub_id variable -->
<itemlayout width="272" condition="String.IsEqual(Window.Property(hub.display.{{ hub_id }}),poster)">
    <control type="group">
        <!-- 5, not 55: compensates for the parent grouplist's posx moving from 55 to 105
             (see script-plex-recommended.xml.tpl) so this item's resting position is unchanged. -->
        <posx>5</posx>
        <!-- Always top-anchored, same posy regardless of role/hub_id - peek-above's own "bottom-
             flush, tail end" crop look no longer needs a manual per-type negative-posy override
             here: it falls out for free once row positions are computed by the stacking formula in
             script-plex-home.xml.tpl's own comment (see there for the full reasoning) - grouplist
             50's real clip cuts off whatever pokes out above it, at whatever position this row is
             currently at. -->
        <posy>{{ vscale(52) }}</posy>
        <control type="group">
            <!-- The whole card is hidden for the row's "See more" item (is.more) - see
                 includes/hub_see_more_pill.xml.tpl, the sibling below that shows in its place. -->
            <visible>String.IsEmpty(ListItem.Property(is.more))</visible>
            <control type="image">
                <posx>0</posx>
                <posy>0</posy>
                <width>264</width>
                <height>{{ vscale(384) }}</height>
                <texture border="24">script.plex/drop-shadow-directional.png</texture>
            </control>
            <posx>3</posx>
            <posy>3</posy>
            <control type="image">
                <!-- Native fallback= (not a separate stacked/masked control - see this include's
                     own history) - Kodi shows this while ListItem.Thumb is empty/loading/failed,
                     swapping seamlessly once it resolves, so there's only ever one masked layer for
                     the art, never two independently-rounded corners that could misalign. -->
                <posx>0</posx>
                <posy>0</posy>
                <width>240</width>
                <height>{{ vscale(360) }}</height>
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
                <posy>{{ vscale(344) }}</posy>
                <control type="image">
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>224</width>
                    <height>{{ vscale(8) }}</height>
                    <texture diffuse="script.plex/masks/progress-bar-mask.png">script.plex/white-square.png</texture>
                    <colordiffuse>E60A0F1A</colordiffuse>
                </control>
                <control type="image">
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>224</width>
                    <height>{{ vscale(8) }}</height>
                    <texture diffuse="script.plex/masks/progress-bar-mask.png">$INFO[ListItem.Property(progress)]</texture>
                    <colordiffuse>FFE5A00D</colordiffuse>
                </control>
            </control>
            {% include "includes/watched_indicator.xml.tpl" with xoff=240 & uw_size=43 & wbg_w=32 & wbg_h=32 & with_count=True & scale="medium" %}
        </control>
        {% include "includes/hub_see_more_pill.xml.tpl" with px=3 & py=158 %}
    </control>
</itemlayout>
