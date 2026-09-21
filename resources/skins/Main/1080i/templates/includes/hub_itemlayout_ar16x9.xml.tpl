<!-- 16x9 item layout (512x288) - uses hub_id variable.
     Card recipe matches the episode screen's row (script-plex-episodes.xml.tpl's fixedlist 400)
     exactly, on request (2026-09-20): 512x288 art under ar16x9-mask.png, 536x312
     drop-shadow-directional.png plate with the art inset (3,3), the inset 496x8 progress bar,
     the top-right episode-number badge and the paired watched indicator to its left. Grew from
     352x198 (was a 395-wide item). Deliberately NOT the episode screen's off-focus colordiffuse
     dimming - every tile here renders at full brightness. No caption lines under the art any
     more either - the hero overlay carries the focused item's title/episode code instead.
     Item width 544 = 512 art + 32 gap: the art sits 8px into the item (the outer group's own 5 +
     the card group's 3), so adjacent tiles' art is 32px apart - same as the poster and square
     hub tiles, and the episode screen itself. -->
<itemlayout width="544" condition="String.IsEqual(Window.Property(hub.display.{{ hub_id }}),ar16x9)">
    <control type="group">
        <!-- 5, not 55: compensates for the parent grouplist's posx moving from 55 to 105
             (see script-plex-recommended.xml.tpl) so this item's resting position is unchanged. -->
        <posx>5</posx>
        <!-- Always top-anchored - see hub_itemlayout_poster.xml.tpl's own matching comment for why
             peek-above's crop no longer needs a manual per-type posy override here. 52 matches
             that file's own offset so every row type has the same title-to-art gap;
             ROW_CONTENT_HEIGHT (library.py) is derived from it. -->
        <posy>{{ vscale(52) }}</posy>
        <control type="group">
            <!-- The whole card is hidden for the row's "See more" item (is.more) - see
                 includes/hub_see_more_pill.xml.tpl, the sibling below that shows in its place. -->
            <visible>String.IsEmpty(ListItem.Property(is.more))</visible>
            <control type="image">
                <posx>0</posx>
                <posy>0</posy>
                <width>536</width>
                <height>{{ vscale(312) }}</height>
                <texture border="24">script.plex/drop-shadow-directional.png</texture>
            </control>
            <posx>3</posx>
            <posy>3</posy>
            <control type="image">
                <!-- Fill for is.photo's letterboxed thumb below - photos keep their full frame
                     (no crop) so this shows through wherever the image doesn't reach. -->
                <visible>!String.IsEmpty(ListItem.Property(is.photo))</visible>
                <posx>0</posx>
                <posy>0</posy>
                <width>512</width>
                <height>{{ vscale(288) }}</height>
                <texture diffuse="script.plex/masks/ar16x9-mask.png">script.plex/white-square.png</texture>
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
                <width>512</width>
                <height>{{ vscale(288) }}</height>
                <texture background="true" diffuse="script.plex/masks/ar16x9-mask.png" fallback="$INFO[ListItem.Property(thumb.fallback)]">$INFO[ListItem.Thumb]</texture>
                <aspectratio scalediffuse="false">scale</aspectratio>
            </control>
            <control type="image">
                <!-- Real photos vary wildly in aspect ratio - crop-to-fill (like posters/art) would
                     chop off arbitrary parts of someone's actual photo, so these get shown whole
                     and letterboxed instead, matching Plex's own photo hub presentation. -->
                <visible>!String.IsEmpty(ListItem.Property(is.photo))</visible>
                <posx>0</posx>
                <posy>0</posy>
                <width>512</width>
                <height>{{ vscale(288) }}</height>
                <texture background="true" diffuse="script.plex/masks/ar16x9-mask.png" fallback="$INFO[ListItem.Property(thumb.fallback)]">$INFO[ListItem.Thumb]</texture>
                <aspectratio scalediffuse="false">keep</aspectratio>
            </control>
            <!-- Progress bar: the episode screen's inset pill (8px in from each side, 8px above
                 the art's bottom edge, progress-bar-mask.png rounded ends), not the old
                 full-width strip. -->
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
            <!-- Episode-number badge, top-right (episode.number - createEpisodeListItem(),
                 library.py; only episodes carry it, so clips/photos in a 16:9 hub get no badge).
                 Verbatim copy of the episode screen's own badge - see script-plex-episodes.xml.tpl
                 for the paired/standalone mask reasoning. -->
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
            <!-- Watched indicator: paired to the badge's left when there is one (episode screen's
                 own geometry - bl-only mask so the two badges meet in a flush seam), otherwise
                 standalone in the art's top-right corner with the default rounded mask. -->
            <control type="group">
                <visible>!String.IsEmpty(ListItem.Property(episode.number))</visible>
                {% include "includes/watched_indicator.xml.tpl" with xoff=472 & uw_size=35 & wbg_w=40 & wbg="script.plex/masks/badge-mask-bl-only.png" %}
            </control>
            <control type="group">
                <visible>String.IsEmpty(ListItem.Property(episode.number))</visible>
                {% include "includes/watched_indicator.xml.tpl" with xoff=512 & uw_size=35 & wbg_w=40 %}
            </control>
        </control>
        {% include "includes/hub_see_more_pill.xml.tpl" with px=3 & py=122 %}
    </control>
</itemlayout>
