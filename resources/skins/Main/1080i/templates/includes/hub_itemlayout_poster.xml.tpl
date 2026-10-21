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
            <!-- The placeholder card under the art: the 4% fill the thumb_fallbacks images have, through the art's
                 own mask. fallback= alone (below) shows only while a tile has no URL yet (the grid's placeholder
                 items) or its art failed: a tile first drawn with its URL shows nothing until the art is in (Kodi's
                 GUIImage: no earlier picture to hold), so the same wait looked like a gap on some screens and a
                 placeholder on others. With this under it, every tile goes from card to art. Two layers through
                 the one mask was dropped once (f4ddffdc) for a glow at the rounded corners - the old, brighter
                 fallback showing through the art's anti-aliased edge; at 4% that's at most ~1%, which doesn't show. -->
            <control type="image">
                <posx>0</posx>
                <posy>0</posy>
                <width>240</width>
                <height>{{ vscale(360) }}</height>
                <texture diffuse="script.plex/masks/poster-mask.png">script.plex/white-square.png</texture>
                <aspectratio scalediffuse="false">scale</aspectratio>
                <colordiffuse>0AFFFFFF</colordiffuse>
            </control>
            <control type="image">
                <!-- fallback=: shown while ListItem.Thumb is empty (no URL yet) or failed - not while
                     it loads; the placeholder card above covers that (hub_itemlayout_poster.xml.tpl). -->
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
                     themselves (masks/progress-bar-mask-224.png, 448x10 - this 224x5 bar at 4K - with
                     radius = half its height, so the ends stay round once fitted to the box).
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
                <posy>{{ vscale(352) }}</posy>
                <control type="image">
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>224</width>
                    <height>{{ vscale(5) }}</height>
                    <texture diffuse="script.plex/masks/progress-bar-mask-224.png">script.plex/white-square.png</texture>
                    <colordiffuse>E60A0F1A</colordiffuse>
                </control>
                <control type="image">
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>224</width>
                    <height>{{ vscale(5) }}</height>
                    <texture diffuse="script.plex/masks/progress-bar-mask-224.png">$INFO[ListItem.Property(progress)]</texture>
                    <colordiffuse>FFE5A00D</colordiffuse>
                </control>
            </control>
            {% include "includes/watched_indicator.xml.tpl" with xoff=240 & uw_size=48 & wbg_w=34.4 & wbg_h=34.4 & with_count=True & scale="medium" %}
        </control>
        {% include "includes/hub_see_more_pill.xml.tpl" with px=3 & py=158 %}
    </control>
</itemlayout>
