{% extends "library.xml.tpl" %}
{% block headers %}<defaultcontrol>50</defaultcontrol>{% endblock %}

{# Genres used to predate the sidebar rollout and opted out of it entirely (restoring
   library.xml.tpl's pre-sidebar top-left Home/Search nav verbatim). That override block is
   gone now, so this screen picks up library.xml.tpl's sidebar-enabled defaults (blank
   header_topleft/header_defaultcontrol, header_audiowidget_onleft2->9001,
   header_filteropts_onleft_nocontent->9000, header_filteropts_onup->204, header_sidebar
   includes the rail) the same way Posters/Squares/Listview already do.

   The one thing that override was also doing double duty for: it was the only place
   screen.title/items.count rendered (a bold title bar, not just Home/Search icons). Losing it
   would silently drop the page heading, so filteropts_grouplist is overridden below to add it
   back - a small gray "N Categories" label, left-aligned to match where other sidebar screens'
   own content starts.

   Genres has no filter/sort of its own (genres.py never sets filter1.display/filter2.display/
   media.type/sort.display), so library.xml.tpl's own filter/sort buttons are dropped entirely
   here rather than carried over empty-labeled: with header_defaultcontrol back to blank (see
   above), library.xml.tpl's own always-focus-201 override that used to paper over this is gone
   too, so those buttons would otherwise become 2 reachable-but-blank focus stops (ids 211/210 -
   the only two of the five without either enable=false or a false <visible>) when pressing up
   off the genre grid. A plain, non-focusable label sidesteps that entirely; the panel's own
   onup below is pointed past this block directly at the audio-widget button/sidebar instead of
   relying on group 200's default-descendant resolution finding whichever control happens to be
   first, which is what surfaced the blank buttons in the first place. #}
{% block filteropts_grouplist %}
<control type="label">
    <visible>String.IsEmpty(Window.Property(hide.filteroptions))</visible>
    <visible>!Integer.IsGreater(Container(101).ListItem.Property(index),5) + String.IsEmpty(Window.Property(no.content)) + !String.IsEmpty(Window.Property(initialized))</visible>
    <animation effect="slide" time="200" end="0,{{ vscale(-115) }}" tween="quadratic" easing="out" condition="Integer.IsGreater(Container(101).ListItem.Property(index),5) + String.IsEmpty(Window.Property(content.filling))">Conditional</animation>
    <animation effect="fade" start="0" end="100" time="200" reversible="true">VisibleChange</animation>
    <!-- Slide right while the sidebar rail is expanded, matching group 50's own identical
         animation below - this label sits outside group 50 (it's in library.xml.tpl's header
         group 200, not the content block), so it needs its own copy to move with the grid
         instead of getting left behind under the expanded rail. Same as library_posters.xml.tpl's
         own filteropts_grouplist override does for its left-anchored version. -->
    <animation effect="slide" end="220,0" time="200" tween="sine" easing="inout" condition="ControlGroup(9000).HasFocus(0)">Conditional</animation>
    <!-- posx=120, not 60: matches the grid's own thumbnail left edge (group 50 posx=60 +
         itemlayout group posx=60 = 120 absolute - see the panel/itemlayout comments below), not
         the screen's general sidebar-clearance x (60, what header_topleft used). -->
    <posx>120</posx>
    <posy>{{ vscale(125) }}</posy>
    <width>600</width>
    <height>{{ vscale(65) }}</height>
    <font>font10</font>
    <align>left</align>
    <aligny>center</aligny>
    <textcolor>FFFFFFFF</textcolor>
    <label>[COLOR=gray]$INFO[Window.Property(items.count)] $ADDON[script.plexmod 34102][/COLOR]</label>
</control>
{% endblock filteropts_grouplist %}

{% block content %}
<control type="group" id="50">
    <visible>!String.IsEmpty(Window.Property(initialized))</visible>
    <!-- Slide up by the same 80px posy was pushed down by (135->215, see below) once the
         filteropts_grouplist label above hides on scroll (same index>5 trigger it uses) - lands
         the grid exactly back at the un-adjusted 135 it would sit at without the label to clear,
         so it rises to fill the vacated space instead of leaving it empty like Posters/Squares
         do with their own equivalent slide-up. -->
    <animation effect="slide" time="200" end="0,{{ vscale(-80, negpos=True) }}" tween="quadratic" easing="out" condition="Integer.IsGreater(Container(101).ListItem.Property(index),5) + String.IsEmpty(Window.Property(content.filling))">Conditional</animation>
    <!-- Slide right while the sidebar rail is expanded (focused), matching every other ported screen -->
    <animation effect="slide" end="220,0" time="200" tween="sine" easing="inout" condition="ControlGroup(9000).HasFocus(0)">Conditional</animation>
    <defaultcontrol>101</defaultcontrol>
    <!-- posx=60, not 0: clears the collapsed sidebar rail's icon column, matching every other
         ported screen. -->
    <posx>60</posx>
    <!-- posy=215, not 135: the filteropts_grouplist label above sits at 135-200 (posy 135,
         height 65) - starting the grid at 135 like before would put the first row of thumbnails
         right under it. 215 clears it with a ~15px gap. Panel height reduced by the same 80
         below so its bottom edge still lands at the screen's own 1080 (215+865=1080, same as the
         original 135+945). -->
    <posy>{{ vscale(215) }}</posy>

    <control type="panel" id="101">
        <!-- width=1810, not the bare 1768 (4 * the 442-wide cell below): the panel clips its own
             rendering to this width, and the rightmost column's focus-zoom (105%, centered on
             the art's own midpoint at local x=1585.5 for that column) pushes its focus ring's
             right edge out to panel-local x=1800.2 (204.5px right of that center, grown by 5% =
             +10.2px past the ring's unzoomed edge at 1790) - a bare 1768 clipped that overflow.
             1810 leaves ~10px of headroom past the computed 1800.2 minimum without adding a
             visible 5th column (1810/442 still floors to 4; the leftover 42px is unused trailing
             space, not a partial column). Hitrect matched. -->
        <hitrect x="0" y="0" w="1810" h="865" />
        <posx>0</posx>
        <posy>0</posy>
        <width>1810</width>
        <height>{{ vscale(865) }}</height>
        <!-- Not onup=200: group 200 has no focusable descendant of its own once
             header_topleft/header_defaultcontrol are gone (see filteropts_grouplist's own
             comment above) other than the audio-widget button and the section tabs, so target
             those/the sidebar directly rather than relying on Kodi finding a default descendant
             of 200. -->
        <onup condition="Control.IsVisible(320)">320</onup>
        <onup condition="Player.HasAudio + String.IsEmpty(Window(10000).Property(script.plex.theme_playing))">204</onup>
        <onup>9000</onup>
        <onleft>9000</onleft>
        <scrolltime>200</scrolltime>
        <orientation>vertical</orientation>
        <preloaditems>2</preloaditems>

        <!-- ITEM LAYOUT ##########################################
             450->442 cell, 375->399 art: gap between thumbnails is cell width minus art width
             (the left margin below is constant across columns, so it cancels out of that
             subtraction) - 450-375 gave the old 75px gap, 442-399 gives 43px. Left margin held
             at 60 (unchanged, still matches where Posters/Squares' own thumbnails start) so the
             grid's own left edge stays at the same 120 absolute (60 here + group 50's own
             posx=60) the filteropts_grouplist label above aligns to - that pins the overall
             thumbnail span at a fixed 120-1845 (1725px: 4*399 + 3*43), which is what set the
             399 art width in the first place (art width solved from 4W+3*43=1725, not the other
             way around). Art height 211->225 to hold its ~16:9 aspect ratio at the new width,
             then 226: zoomed 104% about its centre when focused, an odd height put both of the
             art's edges on half pixels at 1080p, which Kodi rounds the same way, so the art sat
             half a pixel low in its ring - the gap above it twice the gap below (the user,
             2026-10-09, AM6B; 4K was even). An even height keeps both gaps the same. -->
        <itemlayout width="442" height="{{ vscale(287) }}">
            <control type="group">
                <posx>60</posx>
                <posy>15</posy>
                <!-- Genre art -->
                <control type="image">
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>399</width>
                    <height>{{ vscale(226) }}</height>
                    <texture background="true" diffuse="script.plex/masks/ar16x9-mask-399.png">$INFO[ListItem.Thumb]</texture>
                    <aspectratio scalediffuse="false">scale</aspectratio>
                </control>
                <!-- Dark overlay to make label readable -->
                <control type="image">
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>399</width>
                    <height>{{ vscale(226) }}</height>
                    <texture diffuse="script.plex/masks/ar16x9-mask-399.png">script.plex/white-square.png</texture>
                    <colordiffuse>55000000</colordiffuse>
                </control>
                <!-- Genre name -->
                <control type="label">
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>399</width>
                    <height>{{ vscale(226) }}</height>
                    <font>font13</font>
                    <align>center</align>
                    <aligny>center</aligny>
                    <textcolor>FFFFFFFF</textcolor>
                    <shadowcolor>DD000000</shadowcolor>
                    <label>$INFO[ListItem.Label]</label>
                </control>
            </control>
        </itemlayout>

        <!-- FOCUSED LAYOUT ####################################### -->
        <focusedlayout width="442" height="{{ vscale(287) }}">
            <control type="group">
                <posx>60</posx>
                <posy>15</posy>
                <control type="group">
                    <!-- center=art midpoint (399/2, 226/2). 104%, the 16:9 card's own (hub_focusedlayout_
                         ar16x9.xml.tpl), on request (2026-10-09) - was 105. -->
                    <animation effect="zoom" start="100" end="104" time="100" center="199.5,{{ vscale(113) }}" reversible="false">Focus</animation>
                    <animation effect="zoom" start="104" end="100" time="100" center="199.5,{{ vscale(113) }}" reversible="false">UnFocus</animation>
                    <!-- Genre art -->
                    <control type="image">
                        <posx>0</posx>
                        <posy>0</posy>
                        <width>399</width>
                        <height>{{ vscale(226) }}</height>
                        <texture background="true" diffuse="script.plex/masks/ar16x9-mask-399.png">$INFO[ListItem.Thumb]</texture>
                        <aspectratio scalediffuse="false">scale</aspectratio>
                    </control>
                    <!-- Dark overlay -->
                    <control type="image">
                        <posx>0</posx>
                        <posy>0</posy>
                        <width>399</width>
                        <height>{{ vscale(226) }}</height>
                        <texture diffuse="script.plex/masks/ar16x9-mask-399.png">script.plex/white-square.png</texture>
                        <colordiffuse>55000000</colordiffuse>
                    </control>
                    <!-- Genre name -->
                    <control type="label">
                        <scroll>Control.HasFocus(101)</scroll>
                        <posx>0</posx>
                        <posy>0</posy>
                        <width>399</width>
                        <height>{{ vscale(226) }}</height>
                        <font>font13</font>
                        <align>center</align>
                        <aligny>center</aligny>
                        <textcolor>FFFFFFFF</textcolor>
                        <shadowcolor>DD000000</shadowcolor>
                        <label>$INFO[ListItem.Label]</label>
                    </control>
                    <!-- Focus ring -->
                    <control type="group">
                        <visible>Control.HasFocus(101)</visible>
                        <!-- The 16:9 card's ring (ring-mask-ar16x9.png, drawn at 518x294 round
                             512x288 art) made for this art's size, ring-mask-ar16x9-399.png: 3 out
                             each side, a 2 stroke 1 clear of the art, the art's 11 corners + 3 -
                             not stretched, which would thin the stroke and the corners by 0.78
                             (on request, 2026-10-09; was the 9-slice home/selected.png). -->
                        <control type="image">
                            <posx>-3</posx>
                            <posy>{{ vscale(-3) }}</posy>
                            <width>405</width>
                            <height>{{ vscale(232) }}</height>
                            <texture diffuse="script.plex/masks/ring-mask-ar16x9-399.png">script.plex/white-square.png</texture>
                            <colordiffuse>FFE9A20D</colordiffuse>
                        </control>
                    </control>
                </control>
            </control>
        </focusedlayout>
    </control>
</control>
{% endblock content %}
