<!-- Shared album-type row for script-plex-artist.xml.tpl's grouplist 600 - one include per otherAlbums
     hub type (plus Albums itself), parameterized by list id/group id/nav/header property so all 7
     call sites share one recipe instead of 7 copies. Square 240x240 art (script.plex/masks/square-mask.png
     + ring-mask-square.png), matching the 240-wide card convention used everywhere else in this codebase
     (poster rows are 240 wide too, just taller) - not a one-off size. Shadow/ring follow the shared
     hub-row card recipe: shadow box = art + 24 at (0,0) with the art inset 3px inside it
     (drop-shadow-directional.png, border=24), ring = art + 6 at (0,0). See grouplist 600's own
     comment in script-plex-artist.xml.tpl for the full recipe and why it's shared.
     Cell width 282 for 240 art: the card's own 8px left inset (group posx=5 + art group posx=3)
     plus a 34px remainder on the right, so adjacent tiles sit 42px apart. The whole of the 22px
     added over the original 260 falls on the right-hand side - splitting it would have shifted
     the row's first tile off the clip line described below. Kept in step with the Similar Artists
     row (script-plex-artist.xml.tpl's list 401), which carries its own copy of this geometry.
     posx=51 on the list (not 53): the clip line follows from the recipe, not the other way round -
     it sits at 113 minus the itemlayout's own 10px left margin, so absolute x=103 (group 50's own
     posx=52 + this 51). Rows with a smaller item margin clip at 105 by the same rule. Both are far
     clear of the sidebar rail, whose collapsed icon column ends at x=66. -->
<control type="group" id="{{ group_id }}">
    <visible>Integer.IsGreater(Container({{ id }}).NumItems,0) + String.IsEmpty(Window.Property(drawing))</visible>
    <defaultcontrol>{{ id }}</defaultcontrol>
    <posx>0</posx>
    <posy>0</posy>
    <width>1920</width>
    <height>{{ vscale(405) }}</height>
    <control type="label">
        <posx>61</posx>
        <posy>0</posy>
        <width>1000</width>
        <height>{{ vscale(80) }}</height>
        <font>font12</font>
        <align>left</align>
        <aligny>center</aligny>
        <textcolor>FFE9E6E7</textcolor>
        <label>[B]$INFO[Window.Property({{ header_prop }})][/B]</label>
    </control>
    <control type="list" id="{{ id }}">
        <posx>53</posx>
        <posy>{{ vscale(22) }}</posy>
        <width>1867</width>
        <height>{{ vscale(380) }}</height>
        <onup>{{ onup }}</onup>
        <ondown>{{ ondown }}</ondown>
        <onleft>9000</onleft>
        <!-- Hard stop, not Kodi's native wrap-to-first-item - matches every row on Seasons/Episodes/
             Pre-play (script-plex-seasons.xml.tpl). These rows are filled fully up front (no lazy
             pagination), so there's no boundary marker to protect either. -->
        <onright>noop</onright>
        <scrolltime>200</scrolltime>
        <orientation>horizontal</orientation>
        <preloaditems>4</preloaditems>
        <!-- ITEM LAYOUT ########################################## -->
        <itemlayout width="282">
            <control type="group">
                <posx>5</posx>
                <posy>{{ vscale(61) }}</posy>
                <!-- Resting shadow, ungated: matches the poster rows, the home hubs and every library
                     grid, where an unfocused card still sits on its own shadow. The focusedlayout draws
                     the same box gated on Control.HasFocus, so the focused card keeps its own. -->
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
                        <posx>0</posx>
                        <posy>0</posy>
                        <width>240</width>
                        <height>{{ vscale(240) }}</height>
                        <texture diffuse="script.plex/masks/square-mask.png">$INFO[ListItem.Property(thumb.fallback)]</texture>
                    </control>
                    <control type="image">
                        <posx>0</posx>
                        <posy>0</posy>
                        <width>240</width>
                        <height>{{ vscale(240) }}</height>
                        <texture background="true" diffuse="script.plex/masks/square-mask.png">$INFO[ListItem.Thumb]</texture>
                        <aspectratio scalediffuse="false">scale</aspectratio>
                    </control>
                    <control type="label">
                        <scroll>false</scroll>
                        <posx>0</posx>
                        <posy>{{ vscale(249) }}</posy>
                        <width>240</width>
                        <height>{{ vscale(30) }}</height>
                        <font>font10</font>
                        <align>center</align>
                        <textcolor>FFFFFFFF</textcolor>
                        <label>$INFO[ListItem.Label]</label>
                    </control>
                    <control type="label">
                        <scroll>false</scroll>
                        <posx>0</posx>
                        <posy>{{ vscale(279) }}</posy>
                        <width>240</width>
                        <height>{{ vscale(30) }}</height>
                        <font>font10</font>
                        <align>center</align>
                        <textcolor>AAFFFFFF</textcolor>
                        <label>$INFO[ListItem.Property(year)]</label>
                    </control>
                </control>
            </control>
        </itemlayout>

        <!-- FOCUSED LAYOUT ####################################### -->
        <focusedlayout width="282">
            <control type="group">
                <posx>5</posx>
                <posy>{{ vscale(61) }}</posy>
                <control type="group">
                    <animation effect="zoom" start="100" end="104" time="100" center="123,{{ vscale(123) }}" reversible="false">Focus</animation>
                    <animation effect="zoom" start="104" end="100" time="100" center="123,{{ vscale(123) }}" reversible="false">UnFocus</animation>
                    <posx>0</posx>
                    <posy>0</posy>
                    <control type="image">
                        <!-- Ungated, unlike the focus ring below it: f10d4074 established that gating a
                             card's drop shadow on Control.HasFocus makes the selected card the only one
                             on screen without a shadow the moment focus leaves the list for the button
                             row, sidebar or scrubber - and the shadow visibly pops back in as Kodi
                             settles the layout. The itemlayout draws this same box unconditionally, so
                             this one matches it. -->
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
                            <posx>0</posx>
                            <posy>0</posy>
                            <width>240</width>
                            <height>{{ vscale(240) }}</height>
                            <texture diffuse="script.plex/masks/square-mask.png">$INFO[ListItem.Property(thumb.fallback)]</texture>
                        </control>
                        <control type="image">
                            <posx>0</posx>
                            <posy>0</posy>
                            <width>240</width>
                            <height>{{ vscale(240) }}</height>
                            <texture background="true" diffuse="script.plex/masks/square-mask.png">$INFO[ListItem.Thumb]</texture>
                            <aspectratio scalediffuse="false">scale</aspectratio>
                        </control>
                        <control type="label">
                            <scroll>Control.HasFocus({{ id }})</scroll>
                            <posx>0</posx>
                            <posy>{{ vscale(249) }}</posy>
                            <width>240</width>
                            <height>{{ vscale(30) }}</height>
                            <font>font10</font>
                            <align>center</align>
                            <textcolor>FFFFFFFF</textcolor>
                            <label>$INFO[ListItem.Label]</label>
                        </control>
                        <control type="label">
                            <scroll>false</scroll>
                            <posx>0</posx>
                            <posy>{{ vscale(279) }}</posy>
                            <width>240</width>
                            <height>{{ vscale(30) }}</height>
                            <font>font10</font>
                            <align>center</align>
                            <textcolor>AAFFFFFF</textcolor>
                            <label>$INFO[ListItem.Property(year)]</label>
                        </control>
                    </control>
                    <control type="image">
                        <visible>Control.HasFocus({{ id }})</visible>
                        <posx>0</posx>
                        <posy>0</posy>
                        <width>246</width>
                        <height>{{ vscale(246) }}</height>
                        <texture diffuse="script.plex/masks/ring-mask-square.png">script.plex/white-square.png</texture>
                        <colordiffuse>FFE9A20D</colordiffuse>
                    </control>
                </control>
            </control>
        </focusedlayout>
    </control>
</control>
