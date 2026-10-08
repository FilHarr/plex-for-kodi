<!-- A cast & crew tile: 240x240 art under the role mask, the name and the character or job below
     it, on the role shadow; focused, a 104% zoom and the thin role ring. One tile for the cast rows
     of Pre-play (list 400), Seasons (401) and Episodes (402), and the credits grid
     (script-plex-see_more_credits.xml.tpl), which shows the same tiles, on request (2026-10-08).

     A row's trailing "See more" item (is.more, set by the row's fill - film and show screens, when
     there are more than 20 credits) hides the card and shows includes/hub_see_more_pill.xml.tpl in
     its place, as the hub rows do. The pill centres on the art: 3 + 120 - 25 = 98. The grid's
     paging items (is.boundary, pagination.py) hide the card too: an empty cell, which the next
     page replaces as soon as it's reached.

     Params:
       list_id - the list's control id, for the focus gates
       focused - True inside a focusedlayout
       py      - the card's top inside the item (61 in the rows) -->
<control type="group">
    <posx>5</posx>
    <posy>{{ py|vscale }}</posy>
    <control type="group">
        <visible>String.IsEmpty(ListItem.Property(is.more)) + String.IsEmpty(ListItem.Property(is.boundary))</visible>
{% if focused %}
        <control type="group">
            <animation effect="zoom" start="100" end="104" time="100" center="123,{{ vscale(123) }}" reversible="false">Focus</animation>
            <animation effect="zoom" start="104" end="100" time="100" center="123,{{ vscale(123) }}" reversible="false">UnFocus</animation>
            <posx>0</posx>
            <posy>0</posy>
{% endif %}
            <!-- Ungated in both layouts: gating a card's drop shadow on Control.HasFocus (f10d4074)
                 left the selected card the only one on screen without a shadow once focus left the
                 list, popping back in as Kodi settled the layout. -->
            <control type="image">
                <posx>0</posx>
                <posy>0</posy>
                <width>264</width>
                <height>{{ vscale(264) }}</height>
                <texture>script.plex/buttons/role-shadow-directional.png</texture>
            </control>
            <control type="group">
                <posx>3</posx>
                <posy>3</posy>
                <control type="image">
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>240</width>
                    <height>{{ vscale(240) }}</height>
                    <texture diffuse="script.plex/masks/role.png">script.plex/thumb_fallbacks/role.png</texture>
                </control>
                <control type="image">
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>240</width>
                    <height>{{ vscale(240) }}</height>
                    <texture background="true" diffuse="script.plex/masks/role.png">$INFO[ListItem.Thumb]</texture>
                    <aspectratio scalediffuse="false" aligny="top">scale</aspectratio>
                </control>
                <control type="group">
                    <posx>0</posx>
                    <posy>{{ vscale(249) }}</posy>
                    <control type="label">
                        <scroll>{% if focused %}Control.HasFocus({{ list_id }}){% else %}false{% endif %}</scroll>
                        <posx>0</posx>
                        <posy>0</posy>
                        <width>240</width>
                        <height>{{ vscale(30) }}</height>
                        <font>font10</font>
                        <align>center</align>
                        <textcolor>FFFFFFFF</textcolor>
                        <label>$INFO[ListItem.Label]</label>
                    </control>
                    <control type="label">
                        <scroll>{% if focused %}Control.HasFocus({{ list_id }}){% else %}false{% endif %}</scroll>
                        <posx>0</posx>
                        <posy>{{ vscale(30) }}</posy>
                        <width>240</width>
                        <height>{{ vscale(30) }}</height>
                        <font>font10</font>
                        <align>center</align>
                        <textcolor>AAFFFFFF</textcolor>
                        <label>$INFO[ListItem.Label2]</label>
                    </control>
                </control>
            </control>
{% if focused %}
            <!-- The thinner-stroke ring (~5px of a 299px canvas), closer to the poster ring's own
                 thickness, on request. -->
            <control type="image">
                <visible>Control.HasFocus({{ list_id }})</visible>
                <posx>0</posx>
                <posy>0</posy>
                <width>246</width>
                <height>{{ vscale(246) }}</height>
                <texture>script.plex/buttons/role-selected-thin.png</texture>
            </control>
        </control>
{% endif %}
    </control>
    {% include "includes/hub_see_more_pill.xml.tpl" with hub_id=list_id & px=3 & py=98 & focused=focused %}
</control>
