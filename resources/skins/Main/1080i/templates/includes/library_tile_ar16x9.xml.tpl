<!-- The 16:9 library grid's tile (script-plex-ar16x9.xml.tpl, Other Videos sections, and their
     folders' screen, script-plex-subdir-ar16x9.xml.tpl): the Recommended 16:9 row's card (hub_itemlayout_ar16x9.xml.tpl - 512x288 art, the progress pill,
     the watched corner; when focused a 104% zoom and the 16:9 ring) with the poster grid's two
     caption lines under it (script-plex-posters.xml.tpl: the title, then the subtitle or the
     year/sort detail), 11 under the art as there.

     Params:
       focused - True inside the focusedlayout -->
<control type="group">
    <posx>55</posx>
    <posy>{{ vscale(137) }}</posy>
    <control type="group">
{% if focused %}
        <!-- 259,147 = the art's centre in this group's own frame (3 inset + 512/2, 3 + 288/2) -->
        <animation effect="zoom" start="100" end="104" time="100" center="259,{{ vscale(147) }}" reversible="false">Focus</animation>
        <animation effect="zoom" start="104" end="100" time="100" center="259,{{ vscale(147) }}" reversible="false">UnFocus</animation>
{% endif %}
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
            <control type="label">
                <scroll>{% if focused %}true{% else %}false{% endif %}</scroll>
                <posx>0</posx>
                <posy>{{ vscale(299) }}</posy>
                <width>512</width>
                <height>{{ vscale(72) }}</height>
                <font>font10</font>
                <align>center</align>
                <textcolor>FFFFFFFF</textcolor>
                <label>$INFO[ListItem.Label]</label>
            </control>
            <control type="label">
                <visible>!String.IsEmpty(ListItem.Property(subtitle))</visible>
                <scroll>false</scroll>
                <posx>0</posx>
                <posy>{{ vscale(329) }}</posy>
                <width>512</width>
                <height>{{ vscale(72) }}</height>
                <font>font8</font>
                <align>center</align>
                <textcolor>A0FFFFFF</textcolor>
                <label>$INFO[ListItem.Property(subtitle)]</label>
            </control>
            <control type="label">
                <visible>!String.IsEmpty(ListItem.Property(year)) + String.IsEmpty(ListItem.Property(subtitle))</visible>
                <scroll>false</scroll>
                <posx>0</posx>
                <posy>{{ vscale(329) }}</posy>
                <width>512</width>
                <height>{{ vscale(72) }}</height>
                <font>font8</font>
                <align>center</align>
                <textcolor>A0FFFFFF</textcolor>
                <label>$INFO[ListItem.Property(year)]</label>
            </control>
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
