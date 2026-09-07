{% extends "library_posters.xml.tpl" %}
{% block header_animation %}<animation effect="slide" end="0,{{ vscale(-135) }}" time="200" tween="quadratic" easing="out" condition="Integer.IsGreater(Container(101).ListItem.Property(index),9) + !ControlGroup(200).HasFocus(0) + String.IsEmpty(Window.Property(content.filling))">Conditional</animation>{% endblock %}
{% block hide_filter_from_index %}9{% endblock %}
{% block header_bg %}
<control type="image">
    <animation effect="fade" start="0" end="100" time="200" tween="quadratic" easing="out" reversible="true">VisibleChange</animation>
    <visible>ControlGroup(200).HasFocus(0) + Integer.IsGreater(Container(101).ListItem.Property(index),9)</visible>
    <posx>0</posx>
    <posy>0</posy>
    <width>1920</width>
    <height>{{ vscale(135) }}</height>
    <texture>script.plex/white-square.png</texture>
    <colordiffuse>C0000000</colordiffuse>
</control>
{% endblock %}
{% block content %}
<control type="group" id="50">
    <animation effect="slide" time="200" end="0,-224" tween="quadratic" easing="out" condition="Integer.IsGreater(Container(101).ListItem.Property(index),9) + String.IsEmpty(Window.Property(content.filling))">Conditional</animation>
    <animation effect="slide" end="220,0" time="200" tween="sine" easing="inout" condition="ControlGroup(9000).HasFocus(0)">Conditional</animation>
    <posx>60</posx>
    <posy>{{ vscale(135) }}</posy>
    <defaultcontrol>101</defaultcontrol>


    <control type="group" id="100">
        <visible>Integer.IsGreater(Container(101).NumItems,0) + String.IsEmpty(Window.Property(drawing))</visible>
        <defaultcontrol>101</defaultcontrol>
        <posx>0</posx>
        <posy>{{ vscale(-35) }}</posy>
        <width>1920</width>
        <height>1080</height>
        <control type="panel" id="101">
            <hitrect x="0" y="95" w="1780" h="1185" />
            <posx>0</posx>
            <posy>0</posy>
            <width>1800</width>
            <height>1198</height>
            <onup condition="Integer.IsLess(Container(101).ListItem.Property(index),5)">600</onup>
            <onup condition="Integer.IsLess(Container(101).ListItem.Property(index),10) + Integer.IsGreaterOrEqual(Container(101).ListItem.Property(index),5)">300</onup>
            <onleft>9000</onleft>
            <!-- Right off the grid lands on whichever of the two is actually there to take it:
                 the scrubber for alphabetical orderings, the scrollbar otherwise. A single
                 unconditional onright to 151 aimed at the scrubber even when it was hidden.
                 Same pair as script-plex-posters.xml.tpl. -->
            <onright condition="!String.IsEmpty(Window(10000).Property(script.plex.sort.alpha))">151</onright>
            <onright condition="String.IsEmpty(Window(10000).Property(script.plex.sort.alpha))">152</onright>
            <scrolltime>200</scrolltime>
            <orientation>vertical</orientation>
            <preloaditems>2</preloaditems>
            <!-- Links this panel to scrollbar 152's real scroll position/drag-to-scroll - was
                 missing here (same gap found and fixed in script-plex-posters.xml.tpl this
                 session; script.plexmod-multi's copy of this template already has it). -->
            <pagecontrol>152</pagecontrol>
            <!-- 164, not the old 176: the poster stays 144 wide, so this tightens the gap
                 between posters from 32px to 20px. That is what makes room for the scrubber
                 (150) and the scrollbar (152) to show side by side at the bottom of this file,
                 the way script-plex-posters.xml.tpl already does - at pitch 176 the last
                 column's art ran to x=1846 absolute (panel 101's own left 60 + the cell's 55
                 offset + 3 for the inner group + 9*176 + 144), which overlapped the scrubber's
                 own 1836 slot by 10px, and the two had to be mutually exclusive as a result.
                 At 164 that edge lands at 1738, leaving 98px clear before the scrubber.

                 164 is the floor, not a preference: this panel is 1800 wide and Kodi lays a
                 vertical panel out at floor(1800/pitch) columns, so 164-180 gives exactly 10
                 columns and 163 or less silently fits eleven. Keep any future change inside
                 that window or the eight Integer.IsGreater(...index),9) first-row clauses in
                 this file (which encode columns-1) all have to change with it.

                 The drop shadow below is 168 wide against a 144 poster and starts 3px left of
                 it, so it overhangs 21px to the right; at a 20px gap the last 1px is drawn over
                 by the next item (items render in order), which is not visible on a soft
                 gradient. Below a 21px gap it just clips progressively more. -->
            <!-- ITEM LAYOUT ########################################## -->
            <itemlayout width="164" height="{{ vscale(270) }}">
                <control type="group">
                    <posx>55</posx>
                    <posy>{{ vscale(137) }}</posy>
                    <control type="image">
                        <posx>0</posx>
                        <posy>0</posy>
                        <width>168</width>
                        <height>{{ vscale(237) }}</height>
                        <texture border="24">script.plex/drop-shadow-directional.png</texture>
                    </control>
                    <control type="group">
                        <posx>3</posx>
                        <posy>3</posy>
                        <control type="image">
                            <posx>0</posx>
                            <posy>0</posy>
                            <width>144</width>
                            <height>{{ vscale(213) }}</height>
                            <texture background="true" diffuse="script.plex/masks/poster-mask.png" fallback="$INFO[ListItem.Property(thumb.fallback)]">$INFO[ListItem.Thumb]</texture>
                            <aspectratio scalediffuse="false">scale</aspectratio>
                        </control>
                        <control type="group">
                            <visible>!String.IsEmpty(ListItem.Property(progress))</visible>
                            <posx>0</posx>
                            <posy>{{ vscale(203) }}</posy>
                            <control type="image">
                                <posx>0</posx>
                                <posy>0</posy>
                                <width>144</width>
                                <height>{{ vscale(10) }}</height>
                                <texture>script.plex/white-square.png</texture>
                                <colordiffuse>C0000000</colordiffuse>
                            </control>
                            <control type="image">
                                <posx>0</posx>
                                <posy>1</posy>
                                <width>144</width>
                                <height>{{ vscale(8) }}</height>
                                <texture>$INFO[ListItem.Property(progress)]</texture>
                                <colordiffuse>FFCC7B19</colordiffuse>
                            </control>
                        </control>
                        {% include "includes/watched_indicator.xml.tpl" with xoff=144 & uw_size=29 & wbg_w=20.3 & wbg_h=20.3 & count_zoom=26.2 & with_count=True & scale="small" %}
                        <control type="label">
                            <visible>String.IsEmpty(ListItem.Property(subtitle)) + !String.IsEmpty(ListItem.Property(year))</visible>
                            <scroll>false</scroll>
                            <posx>0</posx>
                            <posy>{{ vscale(218) }}</posy>
                            <width>144</width>
                            <height>{{ vscale(72) }}</height>
                            <font>font8</font>
                            <align>center</align>
                            <textcolor>FFFFFFFF</textcolor>
                            <label>$INFO[ListItem.Label] [COLOR A0FFFFFF]($INFO[ListItem.Property(year)])[/COLOR]</label>
                        </control>
                        <control type="label">
                            <visible>String.IsEmpty(ListItem.Property(subtitle)) + String.IsEmpty(ListItem.Property(year))</visible>
                            <scroll>false</scroll>
                            <posx>0</posx>
                            <posy>{{ vscale(218) }}</posy>
                            <width>144</width>
                            <height>{{ vscale(72) }}</height>
                            <font>font8</font>
                            <align>center</align>
                            <textcolor>FFFFFFFF</textcolor>
                            <label>$INFO[ListItem.Label]</label>
                        </control>
                        <control type="label">
                            <visible>!String.IsEmpty(ListItem.Property(subtitle))</visible>
                            <scroll>false</scroll>
                            <posx>0</posx>
                            <posy>{{ vscale(218) }}</posy>
                            <width>144</width>
                            <height>{{ vscale(72) }}</height>
                            <font>font8</font>
                            <align>center</align>
                            <textcolor>FFFFFFFF</textcolor>
                            <label>$INFO[ListItem.Property(subtitle)]</label>
                        </control>
                    </control>
                </control>
            </itemlayout>

            <!-- FOCUSED LAYOUT ####################################### -->
            <focusedlayout width="164" height="{{ vscale(270) }}">
                <control type="group">
                    <posx>55</posx>
                    <posy>{{ vscale(137) }}</posy>
                    <control type="group">
                        <!-- center = half the focus border's own size: the border (150x219 at
                             posx/posy 0, below) and the poster (144x213 at the inner group's 3,3)
                             share a centre exactly, since the border is 6px larger and starts 3px
                             earlier - so both centre on 75,109.5.

                             The old 127,185 was a pre-template holdover (679ede4c) that was never
                             retuned when this grid's poster geometry changed, and it pivoted 52px
                             right and 75.5px below the real centre. Live-measured result: the
                             border grew 6.35px left but only 1.15px right, leaving a 10.65px gap
                             to the poster on the left against 15.85px on the right (reported as
                             "approx 10px and 15px"), and it climbed 9.25px up against 1.7px down
                             instead of expanding in place.

                             end=104, not the old 105: matches script-plex-posters.xml.tpl so both
                             grids zoom by the same proportion. -->
                        <animation effect="zoom" start="100" end="104" time="100" center="75,{{ vscale(109.5) }}" reversible="false">Focus</animation>
                        <animation effect="zoom" start="104" end="100" time="100" center="75,{{ vscale(109.5) }}" reversible="false">UnFocus</animation>
                        <posx>0</posx>
                        <posy>0</posy>
                        <!-- No Control.HasFocus(101) gate on the drop shadow, unlike the focus
                             border at the end of this layout - same reasoning as
                             script-plex-posters.xml.tpl's own copy of this control: itemlayout
                             draws this shadow unconditionally, so gating it here made the selected
                             item the only poster without one once focus left the grid, and it
                             popped back in as Kodi settled the item's layout. -->
                        <control type="image">
                            <posx>0</posx>
                            <posy>0</posy>
                            <width>168</width>
                            <height>{{ vscale(237) }}</height>
                            <texture border="24">script.plex/drop-shadow-directional.png</texture>
                        </control>
                        <control type="group">
                            <posx>3</posx>
                            <posy>3</posy>
                            <control type="image">
                                <posx>0</posx>
                                <posy>0</posy>
                                <width>144</width>
                                <height>{{ vscale(213) }}</height>
                                <texture background="true" diffuse="script.plex/masks/poster-mask.png" fallback="$INFO[ListItem.Property(thumb.fallback)]">$INFO[ListItem.Thumb]</texture>
                                <aspectratio scalediffuse="false">scale</aspectratio>
                            </control>
                            <control type="group">
                                <visible>!String.IsEmpty(ListItem.Property(progress))</visible>
                                <posx>0</posx>
                                <posy>{{ vscale(203) }}</posy>
                                <control type="image">
                                    <posx>0</posx>
                                    <posy>0</posy>
                                    <width>144</width>
                                    <height>{{ vscale(10) }}</height>
                                    <texture>script.plex/white-square.png</texture>
                                    <colordiffuse>C0000000</colordiffuse>
                                </control>
                                <control type="image">
                                    <posx>0</posx>
                                    <posy>1</posy>
                                    <width>144</width>
                                    <height>{{ vscale(8) }}</height>
                                    <texture>$INFO[ListItem.Property(progress)]</texture>
                                    <colordiffuse>FFCC7B19</colordiffuse>
                                </control>
                            </control>
                            {% include "includes/watched_indicator.xml.tpl" with xoff=144 & uw_size=29 & wbg_w=20.3 & wbg_h=20.3 & count_zoom=26.2 & with_count=True & scale="small" %}
                            <control type="label">
                                <visible>String.IsEmpty(ListItem.Property(subtitle)) + !String.IsEmpty(ListItem.Property(year))</visible>
                                <scroll>true</scroll>
                                <scrollspeed>15</scrollspeed>
                                <posx>0</posx>
                                <posy>{{ vscale(218) }}</posy>
                                <width>144</width>
                                <height>{{ vscale(72) }}</height>
                                <font>font8</font>
                                <align>center</align>
                                <textcolor>FFFFFFFF</textcolor>
                                <label>$INFO[ListItem.Label] [COLOR A0FFFFFF]($INFO[ListItem.Property(year)])[/COLOR]</label>
                            </control>
                            <control type="label">
                                <visible>String.IsEmpty(ListItem.Property(subtitle)) + String.IsEmpty(ListItem.Property(year))</visible>
                                <scroll>true</scroll>
                                <scrollspeed>15</scrollspeed>
                                <posx>0</posx>
                                <posy>{{ vscale(218) }}</posy>
                                <width>144</width>
                                <height>{{ vscale(72) }}</height>
                                <font>font8</font>
                                <align>center</align>
                                <textcolor>FFFFFFFF</textcolor>
                                <label>$INFO[ListItem.Label]</label>
                            </control>
                            <control type="label">
                                <visible>!String.IsEmpty(ListItem.Property(subtitle))</visible>
                                <scroll>true</scroll>
                                <scrollspeed>15</scrollspeed>
                                <posx>0</posx>
                                <posy>{{ vscale(218) }}</posy>
                                <width>144</width>
                                <height>{{ vscale(20) }}</height>
                                <font>font8</font>
                                <align>center</align>
                                <textcolor>FFFFFFFF</textcolor>
                                <label>$INFO[ListItem.Property(subtitle)] - $INFO[ListItem.Label]</label>
                            </control>
                        </control>
                        <control type="image">
                            <visible>Control.HasFocus(101)</visible>
                            <posx>0</posx>
                            <posy>0</posy>
                            <width>150</width>
                            <height>{{ vscale(219) }}</height>
                            <texture border="10">script.plex/home/selected.png</texture>
                        </control>
                    </control>
                </control>
            </focusedlayout>
        </control>
    </control>

</control>

{% block buttons %}
<!-- Swapped with the filter row (600): this row now sits where 600 used to (right, next
     to the scrubber) so it's right-anchored like 600 was, and no longer needs the
     sidebar-expand slide 600 needed on the left. -->
<control type="grouplist" id="300">
    <animation effect="fade" start="0" end="100" time="200" reversible="true">VisibleChange</animation>
    <!-- Slides up and off-screen with the header instead of fading: the index>9 clause used to
         live in this row's own <visible> tag, so scrolling past it cut straight to invisible
         (via the fade above, triggered by the visible flip itself) rather than sliding away like
         the header/grid/scrubber/scrollbar all do. Those all stay technically visible throughout
         and use a Conditional slide instead - Kodi can't animate a transition out for a control
         whose <visible> has already gone false, so the index clause has to live in the slide's
         own condition, not here, for the same "keep it visible, slide it away" trick to work.
         Same fix as script-plex-posters.xml.tpl. The remaining clauses (no.content/
         no.content.filtered/initialized) are unrelated to scrolling and still gate real
         visibility. -->
    <visible>String.IsEmpty(Window.Property(no.content)) + String.IsEmpty(Window.Property(no.content.filtered)) + !String.IsEmpty(Window.Property(initialized))</visible>
    <!-- -277.5: matches header(200)'s own "slide by exactly your own height" trick (that one
         starts at posy=0 so its own -135 height is the delta outright; this row starts at
         posy=132.5, so the delta needed to land its bottom edge (posy+height) at 0 is
         -(132.5+145)=-277.5) - same condition group 50 uses for its own header-hide slide, so
         this moves in lockstep with the grid rather than on its own timing. -->
    <animation effect="slide" end="0,{{ vscale(-277.5, negpos=True) }}" time="200" tween="quadratic" easing="out" condition="Integer.IsGreater(Container(101).ListItem.Property(index),9) + String.IsEmpty(Window.Property(content.filling))">Conditional</animation>
    <defaultcontrol>301</defaultcontrol>
    <!-- 164, not the old 120: moves the whole row left so the view button's new label-pill
         (overlay 393 below) ends flush with the grid's own right edge when focused, instead of
         dangling in the margin past it. Same derivation as script-plex-posters.xml.tpl's own
         184, re-solved for this grid: panel(101) left=60 (group 50's own posx) + the cell's own
         55 offset + 9*164 (item pitch) for the 10th/last column = 1591 shadow-left; poster art
         sits 3px further in (inner group posx=3) and is 144 wide, so art's right edge =
         1591+3+144 = 1738 (absolute). Overlay 393's pill sits 18px short of its own group's
         right edge by construction (group_width = label_width+18 - see
         button-label-overlay-recipe), and group_width is what actually right-justifies against
         this row's own <right> anchor since 393 becomes the last flowed item once visible. So
         box_right = 1738+18 = 1756, and <right> = 1920-1756 = 164. -->
    <right>164</right>
    <!-- 132.5, not the old 110: re-centers the icon glyph now that its box shrank from 126x100 to
         theme.library.buttons' 70x70 (see context.py) - only vertically, since this row is
         right-anchored. Same value and same derivation as script-plex-posters.xml.tpl's own
         copy of this row; see that file for the full glyph-fraction math. -->
    <posy>{{ vscale(132.5) }}</posy>
    <width>1000</width>
    <height>{{ vscale(145) }}</height>
    <align>right</align>
    <!-- Missing the section-tabs clause left this row with no up-nav at all outside the
         audio-widget case (live-confirmed in script-plex-posters.xml.tpl, which had the same
         gap: pressing up did nothing) - library_posters.xml.tpl's filteropts_grouplist (600)
         already has exactly this same pair for the same reason. -->
    <onup condition="Control.IsVisible(320)">320</onup>
    <onup condition="Player.HasAudio + String.IsEmpty(Window(10000).Property(script.plex.theme_playing))">204</onup>
    <ondown>101</ondown>
    <onleft>210</onleft>
    <onright>151</onright>
    <itemgap>{{ theme.library.buttongroup.itemgap }}</itemgap>
    <orientation>horizontal</orientation>
    <scrolltime tween="quadratic" easing="out">200</scrolltime>
    <usecontrolcoords>true</usecontrolcoords>

    {% with attr = theme.library.buttons & template = "includes/themed_button.xml.tpl" & hitrect = theme.library.buttons_hitrect & ol = "includes/episode_button_label.xml.tpl" %}
        <!-- Play/Shuffle/View get the same label-on-focus pill overlay as the other button rows,
             identical to script-plex-posters.xml.tpl's own copy - same icon box size and itemgap
             (theme.library.buttons), same strings and measured widths, so the values carry over
             verbatim. More doesn't get one (not asked for). Bare includes for the real buttons;
             only the overlays get explicit nav, so Kodi's usecontrolcoords nav doesn't pick the
             overlay itself once it reflows into the list - see episode_button_label.xml.tpl. -->
        {% include template with name="play" & id=301 & visible="String.IsEmpty(Window.Property(disable_playback)) + [!String.IsEqual(Window(10000).Property(script.plex.item.type),collection) | String.IsEqual(Window.Property(media),collection)]" %}
        {% include ol with id=391 & visible="Control.HasFocus(301)" & name="play" &
            label="$ADDON[script.plexmod 33020]" & label_suffix_info="" &
            label_width=50 & pill_width=112 & group_width=68 &
            onleft=301 & onright=302
        %}
        {% include template with name="shuffle" & id=302 & visible="String.IsEmpty(Window.Property(disable_playback)) + [!String.IsEqual(Window(10000).Property(script.plex.item.type),collection) | String.IsEqual(Window.Property(media),collection)]" %}
        {% include ol with id=392 & visible="Control.HasFocus(302)" & name="shuffle" &
            label="$ADDON[script.plexmod 32935]" & label_suffix_info="" &
            label_width=84 & pill_width=146 & group_width=102 &
            onleft=302 & onright=303
        %}
        {% include template with name="more" & id=303 & visible="String.IsEmpty(Window.Property(disable_playback)) + [String.IsEmpty(Window.Property(no.options)) | Player.HasAudio]" %}
        {% include template with name="view" & id=304 %}
        <!-- No onright: 393 is the last item in this row once visible (nothing follows it to
             route around), same as 304's own bare include above. -->
        {% include ol with id=393 & visible="Control.HasFocus(304)" & name="view" &
            label="$ADDON[script.plexmod 35063]" & label_suffix_info="" &
            label_width=144 & pill_width=206 & group_width=162 &
            onleft=304
        %}
    {% endwith %}

</control>
{% endblock %}

<control type="group" id="150">
    <visible>!String.IsEmpty(Window(10000).Property(script.plex.sort.alpha)) + Integer.IsGreater(Container(101).NumItems,0) + String.IsEmpty(Window.Property(drawing))</visible>
    <defaultcontrol>151</defaultcontrol>
    <!-- posx leaves a 15px gap to the scrollbar below (152's left=1885): the scrubber's own list
         (151) is a flat 34px wide with no internal margin (key_scrubber_items.xml.tpl's item
         labels fill it edge to edge), so its right edge is posx+34 - solving 1885-(posx+34)=15
         gives posx=1836. Same value and same reasoning as script-plex-posters.xml.tpl. Both now
         show side by side instead of one instead of the other, room for which opened up left of
         the scrollbar once this grid's own item pitch shrank from 176 to 164 (itemlayout width,
         above). posy matches the scrollbar's own resting top; the slide
         animation mirrors the zoom the scrollbar does when the header hides on
         scroll, growing into the space the header vacates instead of resizing.
         End position centers the scrubber's full 27-key extent (26 letters + '#', 34px each =
         918) in the 1080-tall screen: (1080-918)/2 = 81 top margin, a 150-81=69px move up from
         the resting posy. -->
    <animation effect="slide" end="0,{{ vscale(-69, negpos=True) }}" time="200" tween="quadratic" easing="out" condition="Integer.IsGreater(Container(101).ListItem.Property(index),9) + String.IsEmpty(Window.Property(content.filling))">Conditional</animation>
    <posx>1836</posx>
    <posy>{{ vscale(150) }}</posy>
    <width>20</width>
    <height>920</height>
    <control type="list" id="151">
        <posx>0</posx>
        <posy>0</posy>
        <width>34</width>
        <height>1050</height>
        <onleft condition="Integer.IsGreater(Container(101).ListItem.Property(index),9) | !Integer.IsEqual(Container(151).ListItem.Property(index),0)">100</onleft>
        <onleft condition="!Integer.IsGreater(Container(101).ListItem.Property(index),9) + Integer.IsEqual(Container(151).ListItem.Property(index),0)">300</onleft>
        <onright>152</onright>
        <scrolltime>200</scrolltime>
        <orientation>vertical</orientation>
        {% include "includes/key_scrubber_items.xml.tpl" %}
    </control>
</control>

<!-- The proportional position indicator - now shown alongside the scrubber above for
     alphabetical orderings too, not instead of it, matching script-plex-posters.xml.tpl.
     script.plex.sort.alpha used to gate this control as the complement of the scrubber's own
     visible clause, because at the old 176 pitch the two physically overlapped (the scrubber
     had to sit at 1875, inside this control's own 1885 slot) and only one could ever show. -->
<control type="scrollbar" id="152">
    <visible>Integer.IsGreater(Container(101).NumItems,0) + String.IsEmpty(Window.Property(drawing))</visible>
    <hitrect x="1845" y="150" w="100" h="910" />
    <left>1885</left>
    <top>{{ vscale(150) }}</top>
    <width>12</width>
    <height>910</height>
    <!-- Slide, not the old zoom-to-fill-the-screen: matches the scrubber's own move (group 150,
         same -69) instead of growing this control's own height into the vacated header space.
         Now that the two show together they have to move together, or they separate on scroll. -->
    <animation effect="slide" end="0,{{ vscale(-69, negpos=True) }}" time="200" tween="quadratic" easing="out" condition="Integer.IsGreater(Container(101).ListItem.Property(index),9) + String.IsEmpty(Window.Property(content.filling))">Conditional</animation>
    {% include "includes/scrollbar_style.xml.tpl" %}
    <!-- Back to the scrubber when it's also showing (alpha orderings); straight to the grid/
         filter-row otherwise, mirroring the scrubber's own two-tier index routing (100 once the
         header's scrolled out of view past the first row, 300 while it's still up) since the
         scrubber itself isn't in the chain to make that hop for us then. A single unconditional
         onleft to 151 sent focus into a hidden scrubber for every non-alphabetical sort. -->
    <onleft condition="!String.IsEmpty(Window(10000).Property(script.plex.sort.alpha))">151</onleft>
    <onleft condition="String.IsEmpty(Window(10000).Property(script.plex.sort.alpha)) + Integer.IsGreater(Container(101).ListItem.Property(index),9)">100</onleft>
    <onleft condition="String.IsEmpty(Window(10000).Property(script.plex.sort.alpha)) + !Integer.IsGreater(Container(101).ListItem.Property(index),9)">300</onleft>
</control>
{% endblock content %}