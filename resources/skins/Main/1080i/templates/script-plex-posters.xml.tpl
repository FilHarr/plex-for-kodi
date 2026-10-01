{% extends "library_posters.xml.tpl" %}
{% block content %}
<control type="group" id="50">
    <animation effect="slide" time="200" end="0,{{ vscale(-115, negpos=True) }}" tween="quadratic" easing="out" condition="Integer.IsGreater(Container(101).ListItem.Property(index),5) + String.IsEmpty(Window.Property(content.filling))">Conditional</animation>
    <animation effect="slide" end="220,0" time="200" tween="sine" easing="inout" condition="ControlGroup(9000).HasFocus(0)">Conditional</animation>
    <posx>60</posx>
    <posy>{{ vscale(125) }}</posy>
    <defaultcontrol>101</defaultcontrol>

    <control type="group" id="100">
        <visible>Integer.IsGreater(Container(101).NumItems,0) + String.IsEmpty(Window.Property(drawing))</visible>
        <defaultcontrol>101</defaultcontrol>
        <posx>0</posx>
        <!-- -34, not the old -35: nudges the poster grid down 1px (2026-09-04, on request) without
             moving the button row above it (a sibling under group 50, not a child of this group) or
             the scrollbar (152, a standalone top-level control positioned via its own <top>, not
             derived from this group's posy at all - see that control's own comment on why it isn't
             nested here). -->
        <posy>{{ vscale(-34) }}</posy>
        <width>1920</width>
        <height>1080</height>
        <control type="panel" id="101">
            <hitrect x="0" y="95" w="1780" h="1185" />
            <posx>0</posx>
            <posy>0</posy>
            <width>1800</width>
            <height>1190</height>
            <!-- The actual fix for "scrollbar doesn't drive the grid": Kodi links a scrollbar to
                 a list/panel's real scroll position (and drag-to-scroll) via <pagecontrol>
                 referencing the scrollbar's own control id - it does NOT require nesting the
                 scrollbar inside the container at all. Found by checking script.plexmod-multi's
                 copy of this same template, which already carries this tag; ours had silently
                 lost it somewhere along the way. Nesting scrollbar 152 inside this panel (this
                 session's own earlier, wrong approach) was reverted - it dragged in clipping
                 issues (panel width) and inherited two of group 50's own animations that never
                 applied to it before, for no benefit once pagecontrol alone does the job with 152
                 staying exactly where it always was, as a standalone sibling below. -->
            <pagecontrol>152</pagecontrol>
            <onup condition="Integer.IsLess(Container(101).ListItem.Property(index),3)">600</onup>
            <onup condition="Integer.IsLess(Container(101).ListItem.Property(index),6) + Integer.IsGreaterOrEqual(Container(101).ListItem.Property(index),3)">300</onup>
            <onleft>9000</onleft>
            <!-- Straight to the scrollbar (152) when it's the only one of the two showing
                 (non-alpha orderings) - the scrubber (151) isn't in the chain at all then, so
                 routing through it first would be a dead press (it's invisible). -->
            <onright condition="!String.IsEmpty(Window(10000).Property(script.plex.sort.alpha))">151</onright>
            <onright condition="String.IsEmpty(Window(10000).Property(script.plex.sort.alpha))">152</onright>
            <!-- Kodi panels wrap top<->bottom by default - moving down at the very last row was
                 sending focus back to the first row instead of stopping. Top wasn't an issue (the
                 onup conditions above already route out to controls 600/300). wraparound=false
                 alone didn't stop it live - onXXX destinations only kick in once a container has
                 exhausted its own internal items in that direction, and 'noop' is this codebase's
                 own established way to say "consume the press, don't move focus anywhere"
                 (includes/sidebar.xml.tpl:322, the server button's own ondown). -->
            <ondown>noop</ondown>
            <scrolltime>200</scrolltime>
            <orientation>vertical</orientation>
            <preloaditems>2</preloaditems>
            <wraparound>false</wraparound>
            <!-- ITEM LAYOUT ########################################## -->
            <itemlayout width="272" height="{{ vscale(460) }}">
                <control type="group">
                    <posx>55</posx>
                    <posy>{{ vscale(137) }}</posy>
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
                            <!-- Matches the recommended-row/pre_play/seasons poster style: inset,
                                 pill-shaped via the same diffuse-mask technique as the poster
                                 corners themselves, rather than a full-bleed flat bar. -->
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
                        <control type="label">
                            <scroll>false</scroll>
                            <posx>0</posx>
                            <posy>{{ vscale(371) }}</posy>
                            <width>240</width>
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
                            <posy>{{ vscale(401) }}</posy>
                            <width>240</width>
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
                            <posy>{{ vscale(401) }}</posy>
                            <width>240</width>
                            <height>{{ vscale(72) }}</height>
                            <font>font8</font>
                            <align>center</align>
                            <textcolor>A0FFFFFF</textcolor>
                            <label>$INFO[ListItem.Property(year)]</label>
                        </control>
                    </control>
                </control>
            </itemlayout>

            <!-- FOCUSED LAYOUT ####################################### -->
            <focusedlayout width="272" height="{{ vscale(460) }}">
                <control type="group">
                    <posx>55</posx>
                    <posy>{{ vscale(137) }}</posy>
                    <control type="group">
                        <!-- center = half the focus ring's own size, not half the poster's: the ring
                             (246x366 at posx/posy 0, below) and the poster (240x360 at the inner
                             group's 3,3) share a centre exactly, since the ring is 6px larger and
                             starts 3px earlier - so both centre on 123,183. The old 120,180 was
                             half the poster's own dimensions with the 3px inset forgotten, which
                             pivoted 3px up and left of the real centre. Only ~0.25px of asymmetry
                             at this zoom, so invisible here, but script-plex-posters-small.xml.tpl
                             had the same class of error at 52px and was very visible. -->
                        <animation effect="zoom" start="100" end="104" time="100" center="123,{{ vscale(183) }}" reversible="false">Focus</animation>
                        <animation effect="zoom" start="104" end="100" time="100" center="123,{{ vscale(183) }}" reversible="false">UnFocus</animation>
                        <posx>0</posx>
                        <posy>0</posy>
                        <!-- No Control.HasFocus(101) gate on the drop shadow, unlike the focus ring
                             at the end of this layout. The ring genuinely should only show while
                             the grid holds focus; the shadow should not, because every unfocused
                             item in itemlayout draws it unconditionally. Gating it made the
                             selected item the only poster on screen without a shadow the moment
                             focus moved to the button row/sidebar/scrubber, and the shadow
                             visibly popped back in as Kodi settled the item's layout. -->
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
                            <control type="label">
                                <scroll>true</scroll>
                                <posx>0</posx>
                                <posy>{{ vscale(371) }}</posy>
                                <width>240</width>
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
                                <posy>{{ vscale(401) }}</posy>
                                <width>240</width>
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
                                <posy>{{ vscale(401) }}</posy>
                                <width>240</width>
                                <height>{{ vscale(72) }}</height>
                                <font>font8</font>
                                <align>center</align>
                                <textcolor>A0FFFFFF</textcolor>
                                <label>$INFO[ListItem.Property(year)]</label>
                            </control>
                        </control>
                        <control type="image">
                            <visible>Control.HasFocus(101)</visible>
                            <posx>0</posx>
                            <posy>0</posy>
                            <width>246</width>
                            <height>{{ vscale(366) }}</height>
                            <texture diffuse="script.plex/masks/ring-mask-poster.png">script.plex/white-square.png</texture>
                            <colordiffuse>FFE9A20D</colordiffuse>
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
    <!-- Slides up and off-screen with the header instead of fading: the index>5 clause used to
         live in this row's own <visible> tag, so scrolling past it cut straight to invisible
         (via the fade above, triggered by the visible flip itself) rather than sliding away like
         the header/grid/scrubber/scrollbar all do (live-confirmed: this row faded, everything
         else moved). Those all stay technically visible throughout and use a Conditional slide
         instead - Kodi can't animate a transition out for a control whose <visible> has already
         gone false, so the index clause has to live in the slide's own condition, not here, for
         the same "keep it visible, slide it away" trick to work. The remaining clauses (no.content/
         no.content.filtered/initialized) are unrelated to scrolling and still gate real
         visibility. -->
    <visible>String.IsEmpty(Window.Property(no.content)) + String.IsEmpty(Window.Property(no.content.filtered)) + !String.IsEmpty(Window.Property(initialized))</visible>
    <!-- -277.5: matches header(200)'s own "slide by exactly your own height" trick (that one
         starts at posy=0 so its own -135 height is the delta outright; this row starts at
         posy=132.5, so the delta needed to land its bottom edge (posy+height) at 0 is
         -(132.5+145)=-277.5) - same condition group 50 uses for its own header-hide slide, so
         this moves in lockstep with the grid rather than on its own timing. -->
    <animation effect="slide" end="0,{{ vscale(-277.5, negpos=True) }}" time="200" tween="quadratic" easing="out" condition="Integer.IsGreater(Container(101).ListItem.Property(index),5) + String.IsEmpty(Window.Property(content.filling))">Conditional</animation>
    <defaultcontrol>301</defaultcontrol>
    <!-- 184, not the old 120: moves the whole row left so the view button's new label-pill
         (overlay 393 below) ends flush with the grid's own right edge when focused, instead of
         dangling in the margin past it. Grid math: panel(101) left=60 (group 50's own posx; 100/
         101 contribute 0 on top of it) + item cell's own 55 offset + 5*272 (item pitch) for the
         6th/last column (CHUNK_SIZE's own comment above confirms 6 columns for this grid) =
         1475 shadow-left; poster art sits 3px further in (inner group posx=3) and is 240 wide, so
         art's right edge = 1475+3+240 = 1718 (absolute).
         Overlay 393's pill sits 18px short of its own group's right edge by construction
         (group_width = label_width+18, pill's own local right edge = -62+pill_width =
         label_width - see button-label-overlay-recipe) - and group_width is what actually
         right-justifies against this row's own <right> anchor, since 393 becomes the last flowed
         item once visible. So solving for the row's box-right edge that puts the pill's right
         edge at 1718: box_right = 1718+18 = 1736, and <right> = 1920-1736 = 184. -->
    <right>184</right>
    <!-- 132.5, not the old 110: re-centers the icon glyph now that its box shrank from 126x100 to
         theme.library.buttons' 70x70 (see context.py) - only vertically, since this row is
         right-anchored (unlike Seasons'/Episodes'/PrePlay's own left-anchored rows, whose own
         retune needed a posx recompute too - here align=right on a generous, non-trimming width
         already re-centers the row horizontally as its flowed content shrinks, no manual offset
         needed). The button textures are stretched into their box with no aspectratio (same as
         those other rows), so the glyph's opaque-pixel fraction down the box is fixed regardless
         of box size - Play's own opaque pixels reach row 60 of the 80x80 source art (see
         pre_play's own identical math), a 0.75 fraction either way: old box, 0.75*100=75px down;
         new box, 0.75*70=52.5px down. Re-solving for the same absolute glyph bottom as before
         (110+0+75=185) against the new 52.5 offset: 185-52.5=132.5. -->
    <posy>{{ vscale(132.5) }}</posy>
    <width>1000</width>
    <height>{{ vscale(145) }}</height>
    <align>right</align>
    <!-- Missing an unconditional fallback left this row with no up-nav at all outside the
         audio-widget case (live-confirmed: pressing up did nothing) - library_posters.xml.tpl's
         filteropts_grouplist (600) already has exactly this same pair for the same reason, since
         these two rows swapped positions (see this row's own comment above). -->
    <!-- Audio widget first, tab row second - Kodi takes the first onup whose condition holds, so
         the old order sent up to the tabs whenever they were on screen, which is always, and the
         widget was only ever reachable from here on a screen without them. The condition is the
         widget group's own <visible> verbatim (library.xml.tpl), so this route exists exactly when
         there's something there to land on; its own <ondown>50</ondown> comes back into the
         content. Tabs stay the fallback. Deliberately NOT applied to the filter/sort row (600),
         whose up should always land on the tabs. -->
    <onup condition="Player.HasAudio + String.IsEmpty(Window(10000).Property(script.plex.theme_playing))">204</onup>
    <onup condition="Control.IsVisible(320)">320</onup>
    <ondown>101</ondown>
    <onleft>210</onleft>
    <onright>151</onright>
    <itemgap>{{ theme.library.buttongroup.itemgap }}</itemgap>
    <orientation>horizontal</orientation>
    <scrolltime tween="quadratic" easing="out">200</scrolltime>
    <usecontrolcoords>true</usecontrolcoords>

    {% with attr = theme.library.buttons & template = "includes/themed_button.xml.tpl" & hitrect = theme.library.buttons_hitrect & ol = "includes/episode_button_label.xml.tpl" %}
        <!-- Play/Shuffle/View get the same label-on-focus pill overlay as Seasons/Episodes/
             PrePlay's own button rows (icon box size/itemgap match exactly - theme.library.buttons
             mirrors theme.seasons.buttons) - Play/Shuffle reuse those rows' own $ADDON strings/
             measured widths since it's the same label text; View's "Change view" is unique to this
             row (added alongside the view-type icon itself, string 35063). More doesn't get one
             (not asked for). Bare includes below (no onleft/onright) for the real buttons, matching
             Seasons' own button row - only the overlays get explicit nav, mirroring their own
             button's neighbours (needed so Kodi's usecontrolcoords nav doesn't pick the overlay
             itself once it reflows into the list - see episode_button_label.xml.tpl). -->
        {% include template with name="play" & id=301 & overlay=True & visible="String.IsEmpty(Window.Property(disable_playback)) + [!String.IsEqual(Window(10000).Property(script.plex.item.type),collection) | String.IsEqual(Window.Property(media),collection)]" %}
        {% include ol with id=391 & visible="Control.HasFocus(301)" & name="play" &
            label="$ADDON[script.plexmod 33020]" & label_suffix_info="" &
            label_width=51 & pill_width=113 & group_width=69 &
            onleft=301 & onright=302
        %}
        {% include template with name="shuffle" & id=302 & overlay=True & visible="String.IsEmpty(Window.Property(disable_playback)) + [!String.IsEqual(Window(10000).Property(script.plex.item.type),collection) | String.IsEqual(Window.Property(media),collection)]" %}
        {% include ol with id=392 & visible="Control.HasFocus(302)" & name="shuffle" &
            label="$ADDON[script.plexmod 32935]" & label_suffix_info="" &
            label_width=84 & pill_width=146 & group_width=102 &
            onleft=302 & onright=303
        %}
        {# More only where its menu has something in it: "Go to <section>", photodirectory-only
           (optionsButtonClicked(), library.py - no.options is set for every other section type).
           It used to also show on any section while music played, for a "Play Next" entry that
           skipped the track; dropped, the header's now-playing popout covers that now. #}
        {% include template with name="more" & id=303 & visible="String.IsEmpty(Window.Property(disable_playback)) + String.IsEmpty(Window.Property(no.options))" %}
        {% include template with name="view" & id=304 & overlay=True %}
        <!-- label_width=146: "Change view" measured at font10/23px via Inter-Regular.ttf (PIL
             font.getlength, 142px; 140 in the old InterUI.ttf) + the +2px clipping-safety buffer every other call site here
             uses, +2px more (2026-09-04 pass, applied to every label_width in this file/
             episodes/seasons - see button-label-overlay-recipe) - pill_width/group_width follow
             the recipe's own +62/+18 formula. No onright: 393 is the last item in this row once
             visible (nothing follows it to route around), same as 304's own bare include above. -->
        {% include ol with id=393 & visible="Control.HasFocus(304)" & name="view" &
            label="$ADDON[script.plexmod 35063]" & label_suffix_info="" &
            label_width=146 & pill_width=208 & group_width=164 &
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
         gives posx=1836. Both now show side by side instead of one instead of the other, room
         for which opened up left of the scrollbar once the poster grid's own item pitch shrank
         (itemlayout width, above). posy matches the scrollbar's own resting top; the slide
         animation mirrors the zoom the scrollbar does when the header hides on scroll, growing
         into the space the header vacates instead of resizing.
         End position centers the scrubber's full 27-key extent (26 letters + '#', 34px each =
         918) in the 1080-tall screen: (1080-918)/2 = 81 top margin, a 150-81=69px move up from
         the resting posy. -->
    <animation effect="slide" end="0,{{ vscale(-69, negpos=True) }}" time="200" tween="quadratic" easing="out" condition="Integer.IsGreater(Container(101).ListItem.Property(index),5) + String.IsEmpty(Window.Property(content.filling))">Conditional</animation>
    <posx>1836</posx>
    <posy>{{ vscale(150) }}</posy>
    <width>20</width>
    <height>920</height>
    <control type="list" id="151">
        <posx>0</posx>
        <posy>0</posy>
        <width>34</width>
        <height>1050</height>
        <onleft condition="Integer.IsGreater(Container(101).ListItem.Property(index),5) | !Integer.IsEqual(Container(151).ListItem.Property(index),0)">100</onleft>
        <!-- 304 (View), not 300: entering the button row from the right has to land on its
             RIGHTMOST button rather than restoring the row's own remembered child. Targeting the
             grouplist by id gives you whatever was focused last, which is right for up/down entry
             but wrong from the side. View is the last real button in the row and carries no
             visibility condition here, so no fallback chain is needed in this direction (unlike
             the leftmost, see library_posters.xml.tpl). -->
        <onleft condition="!Integer.IsGreater(Container(101).ListItem.Property(index),5) + Integer.IsEqual(Container(151).ListItem.Property(index),0)">304</onleft>
        <onright>152</onright>
        <scrolltime>200</scrolltime>
        <orientation>vertical</orientation>
        {% include "includes/key_scrubber_items.xml.tpl" %}
    </control>
</control>

<!-- The proportional position indicator - now shown alongside the scrubber above for
     alphabetical orderings too (not just instead of it), at the same posx/hitrect it always
     rests at for every other ordering (script.plex.sort.alpha only used to gate the scrubber
     itself, above). Standalone sibling, not nested inside panel 101 - it doesn't need to be:
     panel 101's own <pagecontrol>152</pagecontrol> (above) is what actually links this to the
     grid's real scroll position/drag-to-scroll, and that tag works regardless of where 152 sits
     in the control tree (confirmed against script.plexmod-multi's own copy of this template,
     which already has pagecontrol wired up exactly this way, standalone scrollbar included). An
     earlier attempt this session nested 152 inside the panel instead, on the mistaken assumption
     that nesting was required for the link - it wasn't, and nesting brought its own problems
     (panel clipping, inheriting group 50's animations) for no benefit, so it's reverted here. -->
<control type="scrollbar" id="152">
    <visible>Integer.IsGreater(Container(101).NumItems,0) + String.IsEmpty(Window.Property(drawing))</visible>
    <hitrect x="1845" y="150" w="100" h="910" />
    <left>1885</left>
    <top>{{ vscale(150) }}</top>
    <width>12</width>
    <height>910</height>
    <!-- Slide, not the old zoom-to-fill-the-screen: matches the scrubber's own move (group 150,
         same -69) instead of growing this control's own height to fill the vacated header space.
         Same delta as the scrubber rather than independently centering this control's own 910
         height (which would want -85, (1080-910)/2) so the two stay level with each other, since
         they sit side by side and started level (both resting at posy/top=150). -->
    <animation effect="slide" end="0,{{ vscale(-69, negpos=True) }}" time="200" tween="quadratic" easing="out" condition="Integer.IsGreater(Container(101).ListItem.Property(index),5) + String.IsEmpty(Window.Property(content.filling))">Conditional</animation>
    {% include "includes/scrollbar_style.xml.tpl" %}
    <!-- Back to the scrubber when it's also showing (alpha orderings); straight to the grid/
         filter-row otherwise, mirroring the scrubber's own two-tier index routing (100 once the
         header's scrolled out of view past index 5, 300 while it's still up) since the scrubber
         itself isn't in the chain to make that hop for us then. -->
    <onleft condition="!String.IsEmpty(Window(10000).Property(script.plex.sort.alpha))">151</onleft>
    <onleft condition="String.IsEmpty(Window(10000).Property(script.plex.sort.alpha)) + Integer.IsGreater(Container(101).ListItem.Property(index),5)">100</onleft>
    <onleft condition="String.IsEmpty(Window(10000).Property(script.plex.sort.alpha)) + !Integer.IsGreater(Container(101).ListItem.Property(index),5)">304</onleft>
</control>
{% endblock content %}