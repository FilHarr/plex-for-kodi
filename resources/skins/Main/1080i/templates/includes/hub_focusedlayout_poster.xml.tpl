<!-- Poster focused layout (240x360) - uses hub_id variable -->
<focusedlayout width="272" condition="String.IsEqual(Window.Property(hub.display.{{ hub_id }}),poster)">
    <control type="group">
        <!-- 5, not 55: compensates for the parent grouplist's posx moving from 55 to 105
             (see script-plex-recommended.xml.tpl) so this item's resting position is unchanged. -->
        <posx>5</posx>
        <!-- Always top-anchored - see hub_itemlayout_poster.xml.tpl's own matching comment for why
             peek-above's crop no longer needs a manual per-type posy override here. -->
        <posy>{{ vscale(52) }}</posy>
        <control type="group">
            <!-- The whole card is hidden for the row's "See more" item (is.more) - see
                 includes/hub_see_more_pill.xml.tpl, the sibling below that shows in its place. -->
            <visible>String.IsEmpty(ListItem.Property(is.more))</visible>
            <animation effect="zoom" start="100" end="104" time="100" center="120,{{ vscale(180) }}" reversible="false">Focus</animation>
            <animation effect="zoom" start="104" end="100" time="100" center="120,{{ vscale(180) }}" reversible="false">UnFocus</animation>
            <posx>0</posx>
            <posy>0</posy>
            <control type="image">
                <visible>Control.HasFocus({{ hub_id }})</visible>
                <posx>0</posx>
                <posy>0</posy>
                <width>264</width>
                <height>{{ vscale(384) }}</height>
                <texture border="24">script.plex/drop-shadow-directional.png</texture>
            </control>
            <control type="group">
                <posx>3</posx>
                <posy>3</posy>
                <control type="image">
                    <!-- See hub_itemlayout_poster.xml.tpl's own copy of this control for the full
                         reasoning (native fallback=, not a separate stacked/masked control). -->
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>240</width>
                    <height>{{ vscale(360) }}</height>
                    <texture background="true" diffuse="script.plex/masks/poster-mask.png" fallback="$INFO[ListItem.Property(thumb.fallback)]">$INFO[ListItem.Thumb]</texture>
                    <aspectratio scalediffuse="false">scale</aspectratio>
                </control>
                <control type="group">
                    <!-- See hub_itemlayout_poster.xml.tpl's own copy of this control for the full
                         reasoning - kept identical here so the bar doesn't jump on focus change. -->
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
                {% include "includes/watched_indicator.xml.tpl" with xoff=240 & uw_size=48 & wbg_w=34.4 & wbg_h=34.4 & with_count=True & scale="medium" %}
            </control>
            <control type="image">
                <visible>Control.HasFocus({{ hub_id }})</visible>
                <posx>0</posx>
                <posy>0</posy>
                <width>246</width>
                <height>{{ vscale(366) }}</height>
                <texture diffuse="script.plex/masks/ring-mask-poster.png">script.plex/white-square.png</texture>
                <colordiffuse>FFE9A20D</colordiffuse>
            </control>
        </control>
        {% include "includes/hub_see_more_pill.xml.tpl" with px=3 & py=158 & focused=True %}
    </control>
</focusedlayout>
