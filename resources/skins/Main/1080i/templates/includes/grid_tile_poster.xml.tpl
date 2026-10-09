<!-- A "See more" grid's poster tile (see_more.xml.tpl's poster grids): the library poster grid's own
     card (script-plex-posters.xml.tpl - 240x360 art, the watched corner, the progress pill, a 104%
     zoom and the ring when focused) with up to three caption lines under it (see_more labels,
     spec ~/.claude/plans/see-all-grid.md): ListItem.Label, ListItem.Label2 - or a rating's logo and
     score (rating.image / rating, Top Rated TV) in its place - and ListItem.Property(line3). The
     square grid's caption style (hub_itemlayout_square.xml.tpl): font10, 27 apart, the first line
     bright and the rest dimmed.

     Params:
       focused - True inside a focusedlayout
       py      - the card's top inside the cell -->
<control type="group">
    <posx>5</posx>
    <posy>{{ py|vscale }}</posy>
    <control type="group">
        <visible>String.IsEmpty(ListItem.Property(is.boundary))</visible>
{% if focused %}
        <!-- the ring's centre, which the poster shares: 123,183 -->
        <animation effect="zoom" start="100" end="104" time="100" center="123,{{ vscale(183) }}" reversible="false">Focus</animation>
        <animation effect="zoom" start="104" end="100" time="100" center="123,{{ vscale(183) }}" reversible="false">UnFocus</animation>
{% endif %}
        <control type="image">
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
                <posx>0</posx>
                <posy>0</posy>
                <width>240</width>
                <height>{{ vscale(360) }}</height>
                <texture background="true" diffuse="script.plex/masks/poster-mask.png" fallback="$INFO[ListItem.Property(thumb.fallback)]">$INFO[ListItem.Thumb]</texture>
                <aspectratio scalediffuse="false">scale</aspectratio>
            </control>
            <control type="group">
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
            {% include "includes/grid_tile_captions.xml.tpl" with focused=focused & top1=371 & top2=401 & top3=426 %}
        </control>
{% if focused %}
        <control type="image">
            <visible>Control.HasFocus(101)</visible>
            <posx>0</posx>
            <posy>0</posy>
            <width>246</width>
            <height>{{ vscale(366) }}</height>
            <texture diffuse="script.plex/masks/ring-mask-poster.png">script.plex/white-square.png</texture>
            <colordiffuse>FFE9A20D</colordiffuse>
        </control>
{% endif %}
    </control>
</control>
