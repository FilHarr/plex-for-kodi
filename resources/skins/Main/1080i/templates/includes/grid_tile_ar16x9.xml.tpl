<!-- A "See more" grid's 16:9 tile (script-plex-see_more_ar16x9.xml.tpl): the Recommended 16:9 row's
     own card (hub_itemlayout_ar16x9.xml.tpl / hub_focusedlayout_ar16x9.xml.tpl - 512x288 art, the
     progress pill, the watched corner, a 104% zoom and the 16:9 ring when focused) with up to three
     caption lines under it (grid_tile_captions.xml.tpl), 11 under the art as the poster grid's.
     No episode-number badge: the caption's second line carries S/E.

     Params:
       focused - True inside a focusedlayout
       py      - the card's top inside the cell -->
<control type="group">
    <posx>5</posx>
    <posy>{{ py|vscale }}</posy>
    <control type="group">
        <visible>String.IsEmpty(ListItem.Property(is.boundary))</visible>
{% if focused %}
        <!-- 259,147 = the art's centre in this group's own frame (3 inset + 512/2, 3 + 288/2) -->
        <animation effect="zoom" start="100" end="104" time="100" center="259,{{ vscale(147) }}" reversible="false">Focus</animation>
        <animation effect="zoom" start="104" end="100" time="100" center="259,{{ vscale(147) }}" reversible="false">UnFocus</animation>
{% endif %}
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
            <control type="image">
                <posx>0</posx>
                <posy>0</posy>
                <width>512</width>
                <height>{{ vscale(288) }}</height>
                <texture background="true" diffuse="script.plex/masks/ar16x9-mask.png" fallback="$INFO[ListItem.Property(thumb.fallback)]">$INFO[ListItem.Thumb]</texture>
                <aspectratio scalediffuse="false">scale</aspectratio>
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
            {% include "includes/watched_indicator.xml.tpl" with xoff=512 & uw_size=35 & wbg_w=40 %}
            {% include "includes/grid_tile_captions.xml.tpl" with focused=focused & top1=299 & top2=329 & top3=354 & width=512 & rating_x=210 %}
        </control>
{% if focused %}
        <control type="image">
            <visible>Control.HasFocus(101)</visible>
            <posx>0</posx>
            <posy>0.5</posy>
            <width>518</width>
            <height>{{ vscale(294) }}</height>
            <texture diffuse="script.plex/masks/ring-mask-ar16x9.png">script.plex/white-square.png</texture>
            <colordiffuse>FFE9A20D</colordiffuse>
        </control>
{% endif %}
    </control>
</control>
