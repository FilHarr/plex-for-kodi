<!-- A "See more" grid's square tile (see_more.xml.tpl's square grids): the Recommended square row's
     own card (hub_itemlayout_square.xml.tpl / hub_focusedlayout_square.xml.tpl - 240x240 art, a
     real photo letterboxed whole, the progress pill, a 104% zoom and the square ring when focused)
     with up to three caption lines under it (grid_tile_captions.xml.tpl), at the row's own 250 and
     27 apart.

     Params:
       focused - True inside a focusedlayout
       py      - the card's top inside the cell -->
<control type="group">
    <posx>5</posx>
    <posy>{{ py|vscale }}</posy>
    <control type="group">
        <visible>String.IsEmpty(ListItem.Property(is.boundary))</visible>
{% if focused %}
        <!-- 123 = the art's centre in this group's own frame (3 inset + 240/2) -->
        <animation effect="zoom" start="100" end="104" time="100" center="123,{{ vscale(123) }}" reversible="false">Focus</animation>
        <animation effect="zoom" start="104" end="100" time="100" center="123,{{ vscale(123) }}" reversible="false">UnFocus</animation>
{% endif %}
        <control type="image">
            <posx>0</posx>
            <posy>0</posy>
            <width>264</width>
            <height>{{ vscale(264) }}</height>
            <texture border="24">script.plex/drop-shadow-directional.png</texture>
        </control>
        <control type="group">
            <posx>3</posx>
            <posy>3</posy>
            <control type="image">
                <!-- the fill a letterboxed photo shows on (is.photo) -->
                <visible>!String.IsEmpty(ListItem.Property(is.photo))</visible>
                <posx>0</posx>
                <posy>0</posy>
                <width>240</width>
                <height>{{ vscale(240) }}</height>
                <texture diffuse="script.plex/masks/square-mask.png">script.plex/white-square.png</texture>
                <colordiffuse>FF191B1E</colordiffuse>
            </control>
            <control type="image">
                <visible>String.IsEmpty(ListItem.Property(is.photo))</visible>
                <posx>0</posx>
                <posy>0</posy>
                <width>240</width>
                <height>{{ vscale(240) }}</height>
                <texture background="true" diffuse="script.plex/masks/square-mask.png" fallback="$INFO[ListItem.Property(thumb.fallback)]">$INFO[ListItem.Thumb]</texture>
                <aspectratio scalediffuse="false">scale</aspectratio>
            </control>
            <control type="image">
                <visible>!String.IsEmpty(ListItem.Property(is.photo))</visible>
                <posx>0</posx>
                <posy>0</posy>
                <width>240</width>
                <height>{{ vscale(240) }}</height>
                <texture background="true" diffuse="script.plex/masks/square-mask.png" fallback="$INFO[ListItem.Property(thumb.fallback)]">$INFO[ListItem.Thumb]</texture>
                <aspectratio scalediffuse="false">keep</aspectratio>
            </control>
            <control type="group">
                <visible>!String.IsEmpty(ListItem.Property(progress))</visible>
                <posx>8</posx>
                <posy>{{ vscale(224) }}</posy>
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
            {% include "includes/grid_tile_captions.xml.tpl" with focused=focused & top1=250 & top2=280 & top3=305 %}
        </control>
{% if focused %}
        <control type="image">
            <visible>Control.HasFocus(101)</visible>
            <posx>0</posx>
            <posy>0</posy>
            <width>246</width>
            <height>{{ vscale(246) }}</height>
            <texture diffuse="script.plex/masks/ring-mask-square.png">script.plex/white-square.png</texture>
            <colordiffuse>FFE9A20D</colordiffuse>
        </control>
{% endif %}
    </control>
</control>
