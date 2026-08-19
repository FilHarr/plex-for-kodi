{# Section tabs (quiet-orbiting-heron.md, plan item 0): switches LibraryWindow's contentMode
   ('library'/'recommended') in place, via switchTab() (library.py). Styled after
   script-plex-episodes.xml.tpl's season tabs (label/underline treatment, same font/colors,
   same Control.HasFocus()-gated label split so the bar doesn't look permanently "focused") but
   deliberately a plain type="list", not that file's type="fixedlist" center-pinned carousel -
   only ever a handful of tabs (2 today: Recommended/Library; Playlists/Collections/Categories
   planned, never enough to need scroll-under-a-fixed-point behavior), so a simple left-anchored
   list is simpler and correct here.

   posx=100: same sidebar-clearance floor used elsewhere content sits near the rail (e.g.
   script-plex-recommended.xml.tpl's grouplist 50). Included directly into each site's real
   header body (library.xml.tpl, script-plex-recommended.xml.tpl) rather than via a block-name
   override - library.xml.tpl's own header block fully replaces default.xml.tpl's, so the
   default header_middle_add hook is never actually rendered there.

   Item cells are 200 wide (not season tabs' 170 label / 200 cell split, since fixedlist reserves
   extra room for its own scroll-under-focus peek that this plain list doesn't need) - 150 clipped
   "Recommended" under Kodi's default label truncation. Underline stays centered under the wider
   label (posx 50 = (200-100)/2, was 25 for a 150 cell).

   onleft routes to the sidebar (9000), matching every other header control's convention.
   onright is a dead end (noop) rather than routing further right - there's nothing to its right
   in the header row today, and reaching remaining/later tabs is via left/right within the list
   itself, same as season tabs. ondown's correct target differs by including template (grid
   content vs. hub content) - passed in via {% with tab_ondown = ... %} at each include site, not
   hardcoded here. Entry from below is via each including template's content control routing its
   own onup here first (Control.IsVisible(320) gated, falling back to its prior target when the
   tab row isn't present) - same relationship season tabs' fixedlist 205 has with the episode row's
   onup, not a sidebar onright override (sidebar's onright is hardcoded skin-wide to control/group
   50 - see script-plex-episodes.xml.tpl's own season tabs, which are entered the same way).

   Slide-right-while-sidebar-expanded animation matches every other header/content control that
   sits outside its screen's own content group 50 (see e.g. script-plex-genres.xml.tpl's
   filteropts_grouplist label) - group 50 gets this for free since it's animated directly, but
   anything in the header row (this included) needs its own copy to move with it instead of
   getting left behind under the expanded rail. #}
<control type="list" id="320">
    <animation effect="slide" end="220,0" time="200" tween="sine" easing="inout" condition="ControlGroup(9000).HasFocus(0)">Conditional</animation>
    <posx>100</posx>
    <posy>0</posy>
    <width>500</width>
    <height>{{ vscale(135) }}</height>
    <onleft>9000</onleft>
    <onright>noop</onright>
    <onup>noop</onup>
    <ondown>{{ tab_ondown }}</ondown>
    <orientation>horizontal</orientation>
    <itemlayout width="200" height="{{ vscale(135) }}">
        <control type="label">
            <posx>0</posx>
            <posy>0</posy>
            <width>200</width>
            <height>{{ vscale(135) }}</height>
            <font>font12</font>
            <align>center</align>
            <aligny>center</aligny>
            <textcolor>80FFFFFF</textcolor>
            <label>$INFO[ListItem.Label]</label>
        </control>
        <control type="image">
            <visible>!String.IsEmpty(ListItem.Property(current))</visible>
            <posx>50</posx>
            <posy>{{ vscale(94) }}</posy>
            <width>100</width>
            <height>2</height>
            <texture>script.plex/white-square.png</texture>
            <colordiffuse>FFE5A00D</colordiffuse>
        </control>
    </itemlayout>
    <focusedlayout width="200" height="{{ vscale(135) }}">
        <control type="label">
            <visible>Control.HasFocus(320)</visible>
            <posx>0</posx>
            <posy>0</posy>
            <width>200</width>
            <height>{{ vscale(135) }}</height>
            <font>font12</font>
            <align>center</align>
            <aligny>center</aligny>
            <textcolor>FFFFFFFF</textcolor>
            <label>$INFO[ListItem.Label]</label>
        </control>
        <control type="label">
            <visible>!Control.HasFocus(320)</visible>
            <posx>0</posx>
            <posy>0</posy>
            <width>200</width>
            <height>{{ vscale(135) }}</height>
            <font>font12</font>
            <align>center</align>
            <aligny>center</aligny>
            <textcolor>80FFFFFF</textcolor>
            <label>$INFO[ListItem.Label]</label>
        </control>
        <control type="image">
            <visible>!String.IsEmpty(ListItem.Property(current))</visible>
            <posx>50</posx>
            <posy>{{ vscale(94) }}</posy>
            <width>100</width>
            <height>2</height>
            <texture>script.plex/white-square.png</texture>
            <colordiffuse>FFE5A00D</colordiffuse>
        </control>
    </focusedlayout>
</control>
