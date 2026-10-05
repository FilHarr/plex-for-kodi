<!-- ========== SIDEBAR RAIL ========== -->
<!-- Persistent vertical nav rail: icons-only when unfocused, icons+labels while any
     descendant (section list, server/user buttons or their dropdowns) has focus.
     Declared last so it z-orders above everything else, including hub content and the
     overlays above - Kodi gives controls no independent z-index, only paint order, and
     there's no way to make that conditional on the rail's expand state. Posters clip
     before reaching the collapsed rail's full width instead (see the hub grouplist's own
     posx comment in script-plex-home.xml.tpl), so they read as sliding behind the rail
     rather than getting cut off mid-icon. -->
<control type="group" id="9000">
    <posx>0</posx>
    <posy>0</posy>
    <width>300</width>
    <height>1080</height>
    <defaultcontrol>9001</defaultcontrol>

    <!-- User button at top (overlays avatar area) -->
    <control type="button" id="202">
        <posx>8</posx>
        <!-- posy=42, not 30: measured against official Plex, the avatar's center sits at y=74, not the
             62 this (and the avatar group below, which this button overlays) computed to. -->
        <posy>{{ vscale(42) }}</posy>
        <width>284</width>
        <height>{{ vscale(64) }}</height>
        <font>font10</font>
        <textcolor>00000000</textcolor>
        <focusedcolor>00000000</focusedcolor>
        <align>left</align>
        <aligny>center</aligny>
        <onup>noop</onup>
        <ondown>9001</ondown>
        <onright condition="!String.IsEmpty(Window.Property(server.unavailable))">2600</onright><onright>50</onright>
        <texturefocus colordiffuse="33FFFFFF" border="10">script.plex/white-square-rounded.png</texturefocus>
        <texturenofocus>-</texturenofocus>
        <label> </label>
        <onunfocus condition="!String.IsEmpty(Window.Property(show.options))">SetFocus(250)</onunfocus>
    </control>
    <!-- User avatar area at top (visual overlay, not focusable) -->
    <control type="group">
        <posx>0</posx>
        <!-- posy=42, not 30: see button 202's own comment above - moves the 44-tall avatar image (itself
             at posy=10 within this group) down 12px so its center lands at y=74, matching official
             Plex's own measured avatar position (was y=62). -->
        <posy>{{ vscale(42) }}</posy>
        <width>300</width>
        <height>{{ vscale(80) }}</height>
        <!-- Avatar image (always visible) -->
        <control type="image">
            <posx>18</posx>
            <posy>{{ vscale(10) }}</posy>
            <width>44</width>
            <height>{{ vscale(44) }}</height>
            <texture diffuse="script.plex/home/avatar-diffuse.png" fallback="script.plex/gray-square.png">$INFO[Window.Property(user.avatar)]</texture>
        </control>
        <!-- Avatar letter fallback (always visible when no avatar) -->
        <control type="label">
            <visible>String.IsEmpty(Window.Property(user.avatar))</visible>
            <posx>18</posx>
            <posy>{{ vscale(10) }}</posy>
            <width>44</width>
            <height>{{ vscale(44) }}</height>
            <font>font12</font>
            <align>center</align>
            <aligny>center</aligny>
            <textcolor>FFFFFFFF</textcolor>
            <label>[B]$INFO[Window.Property(user.avatar.letter)][/B]</label>
        </control>
        <control type="image">
            <visible>!String.IsEmpty(Window(10000).Property(script.plex.update_available))</visible>
            <posx>50</posx>
            <posy>{{ vscale(40) }}</posy>
            <width>16</width>
            <height>{{ vscale(14) }}</height>
            <texture>script.plex/home/device/update_small.png</texture>
            <colordiffuse>FF00CC00</colordiffuse>
        </control>
        <!-- Username label (expanded only) -->
        <control type="label">
            <visible>ControlGroup(9000).HasFocus(0)</visible>
            <animation effect="fade" start="0" end="100" time="200">Visible</animation>
            <animation effect="fade" start="100" end="0" time="200">Hidden</animation>
            <posx>75</posx>
            <posy>{{ vscale(10) }}</posy>
            <width>210</width>
            <height>{{ vscale(44) }}</height>
            <font>font12</font>
            <align>left</align>
            <aligny>center</aligny>
            <textcolor>FFFFFFFF</textcolor>
            <label>$INFO[Window.Property(user.name)]</label>
        </control>
    </control>

    <!-- Section list (sidebar items) -->
    <control type="fixedlist" id="9001">
        <posx>0</posx>
        <!-- posy=118, barely changed from 120: with the 88-tall rows below (was 72), row 1's center
             lands at 118+44=162, matching official Plex's own measured first-icon (search) position.
             The pitch change below does almost all the work here, not this. -->
        <posy>{{ vscale(118) }}</posy>
        <width>300</width>
        <!-- height=880 (10 items x 88): raised from 792 (9 items) to fit a 10th sidebar entry - the
             hard ceiling before overlapping the server button (id 201, posy=1009) is 1009-118=891 (this
             list's own posy is 118), so 880 leaves 11px of margin, no pitch/icon shrink needed. -->
        <height>{{ vscale(880) }}</height>
        <onright condition="!String.IsEmpty(Window.Property(server.unavailable))">2600</onright><onright>50</onright>
        <onup>202</onup>
        <ondown>201</ondown>
        <scrolltime>200</scrolltime>
        <orientation>vertical</orientation>
        <focusposition>3</focusposition>
        <!-- movement=6, not higher: fixedlist's own cursor math is maxCursor = min(focusposition +
             movement, itemsPerPage) (Kodi's GUIFixedListContainer::GetCursorRange), but valid row slots
             only run 0..itemsPerPage-1 - with itemsPerPage now 10 (880/88) and movement=7, maxCursor
             would land on 10, one past the last real slot. SelectItem() then pins an 11th+ item's cursor
             at that invalid slot instead of clamping to 9, which renders it below the control's own clip
             rect - invisible, not scrolled into view. Confirmed against Kodi's actual C++ source, not
             guessed - re-derived here from itemsPerPage=9/movement=5's identical reasoning when this
             list only fit 9 items; re-verify this same math again if itemsPerPage ever changes further
             (e.g. an 11th+ sidebar entry needing this list to scroll instead of grow). movement=6 caps
             maxCursor at 9 (itemsPerPage-1), the last valid slot. -->
        <movement>6</movement>
        <pagecontrol>0</pagecontrol>
        <!-- SIDEBAR ITEM LAYOUT (unfocused list) -->
        <!-- height=88, not 72: measured against official Plex, icon-to-icon pitch is a very consistent
             88px (confirmed across 7 consecutive gaps, +/-1px) - fixedlist has no separate item-gap
             control, the item height IS the pitch. Every posy below that was tuned against the old
             72-tall row is recentered against this new 88-tall one in the same ratio. -->
        <itemlayout height="{{ vscale(88) }}">
            <control type="group">
                <visible>!String.IsEmpty(ListItem.Property(item))</visible>
                <posx>0</posx>
                <posy>0</posy>
                <width>300</width>
                <height>{{ vscale(88) }}</height>
                <!-- Active indicator bar (left edge) -->
                <control type="image">
                    <visible>!String.IsEmpty(ListItem.Property(is.active))</visible>
                    <posx>0</posx>
                    <posy>{{ vscale(24) }}</posy>
                    <width>3</width>
                    <height>{{ vscale(40) }}</height>
                    <texture>script.plex/white-square.png</texture>
                    <colordiffuse>FFE5A00D</colordiffuse>
                </control>
                <!-- Section icon - dimmer while sidebar is collapsed, or while its server isn't answering -->
                <control type="image">
                    <visible>[!ControlGroup(9000).HasFocus(0) | !String.IsEmpty(ListItem.Property(is.offline))]</visible>
                    <posx>26</posx>
                    <posy>{{ vscale(30) }}</posy>
                    <width>28</width>
                    <height>{{ vscale(28) }}</height>
                    <texture>$INFO[ListItem.Icon]</texture>
                    <colordiffuse>26FFFFFF</colordiffuse>
                </control>
                <!-- Section icon - normal while sidebar is expanded -->
                <control type="image">
                    <visible>ControlGroup(9000).HasFocus(0) + String.IsEmpty(ListItem.Property(is.offline))</visible>
                    <posx>26</posx>
                    <posy>{{ vscale(30) }}</posy>
                    <width>28</width>
                    <height>{{ vscale(28) }}</height>
                    <texture>$INFO[ListItem.Icon]</texture>
                    <colordiffuse>99FFFFFF</colordiffuse>
                </control>
                <!-- Active icon overlay (orange tint) -->
                <control type="image">
                    <visible>!String.IsEmpty(ListItem.Property(is.active))</visible>
                    <posx>26</posx>
                    <posy>{{ vscale(30) }}</posy>
                    <width>28</width>
                    <height>{{ vscale(28) }}</height>
                    <texture>$INFO[ListItem.Icon]</texture>
                    <colordiffuse>FFE5A00D</colordiffuse>
                </control>
                <!-- Path-mapping indicator dot -->
                <control type="image">
                    <visible>!String.IsEmpty(ListItem.Property(is.mapped)) + String.IsEmpty(ListItem.Property(is.mapped.broken))</visible>
                    <posx>46</posx>
                    <posy>{{ vscale(26) }}</posy>
                    <width>8</width>
                    <height>{{ vscale(8) }}</height>
                    <texture>script.plex/white-square-rounded-4r.png</texture>
                    <colordiffuse>FF666666</colordiffuse>
                </control>
                <control type="image">
                    <visible>!String.IsEmpty(ListItem.Property(is.mapped.broken))</visible>
                    <posx>46</posx>
                    <posy>{{ vscale(26) }}</posy>
                    <width>8</width>
                    <height>{{ vscale(8) }}</height>
                    <texture>script.plex/white-square-rounded-4r.png</texture>
                    <colordiffuse>FFCC2222</colordiffuse>
                </control>
                <!-- Section label (expanded only): one line, or - when the account has more than one
                     server (ListItem.Property(server.name), set for libraries only) - the library over
                     its server's name. Kodi labels only centre vertically, so each line's box is
                     placed: together they centre on the row like the single line (y=44). -->
                <control type="label">
                    <visible>ControlGroup(9000).HasFocus(0) + String.IsEmpty(ListItem.Property(server.name)) + String.IsEmpty(ListItem.Property(is.offline))</visible>
                    <posx>68</posx>
                    <posy>0</posy>
                    <width>220</width>
                    <height>{{ vscale(88) }}</height>
                    <font>font10</font>
                    <align>left</align>
                    <aligny>center</aligny>
                    <textcolor>99FFFFFF</textcolor>
                    <label>$INFO[ListItem.Label]</label>
                </control>
                <control type="label">
                    <visible>ControlGroup(9000).HasFocus(0) + !String.IsEmpty(ListItem.Property(server.name)) + String.IsEmpty(ListItem.Property(is.offline))</visible>
                    <posx>68</posx>
                    <posy>{{ vscale(19) }}</posy>
                    <width>220</width>
                    <height>{{ vscale(28) }}</height>
                    <font>font10</font>
                    <align>left</align>
                    <aligny>center</aligny>
                    <textcolor>99FFFFFF</textcolor>
                    <label>$INFO[ListItem.Label]</label>
                </control>
                <control type="label">
                    <visible>ControlGroup(9000).HasFocus(0) + !String.IsEmpty(ListItem.Property(server.name)) + String.IsEmpty(ListItem.Property(is.offline))</visible>
                    <posx>68</posx>
                    <posy>{{ vscale(48) }}</posy>
                    <width>220</width>
                    <height>{{ vscale(20) }}</height>
                    <font>font8</font>
                    <align>left</align>
                    <aligny>center</aligny>
                    <textcolor>66FFFFFF</textcolor>
                    <label>$INFO[ListItem.Property(server.name)]</label>
                </control>
                <!-- The same, dimmed: a library whose server isn't answering, or is no longer
                     on the account (ListItem.Property(is.offline)) -->
                <control type="label">
                    <visible>ControlGroup(9000).HasFocus(0) + String.IsEmpty(ListItem.Property(server.name)) + !String.IsEmpty(ListItem.Property(is.offline))</visible>
                    <posx>68</posx>
                    <posy>0</posy>
                    <width>220</width>
                    <height>{{ vscale(88) }}</height>
                    <font>font10</font>
                    <align>left</align>
                    <aligny>center</aligny>
                    <textcolor>40FFFFFF</textcolor>
                    <label>$INFO[ListItem.Label]</label>
                </control>
                <control type="label">
                    <visible>ControlGroup(9000).HasFocus(0) + !String.IsEmpty(ListItem.Property(server.name)) + !String.IsEmpty(ListItem.Property(is.offline))</visible>
                    <posx>68</posx>
                    <posy>{{ vscale(19) }}</posy>
                    <width>220</width>
                    <height>{{ vscale(28) }}</height>
                    <font>font10</font>
                    <align>left</align>
                    <aligny>center</aligny>
                    <textcolor>40FFFFFF</textcolor>
                    <label>$INFO[ListItem.Label]</label>
                </control>
                <control type="label">
                    <visible>ControlGroup(9000).HasFocus(0) + !String.IsEmpty(ListItem.Property(server.name)) + !String.IsEmpty(ListItem.Property(is.offline))</visible>
                    <posx>68</posx>
                    <posy>{{ vscale(48) }}</posy>
                    <width>220</width>
                    <height>{{ vscale(20) }}</height>
                    <font>font8</font>
                    <align>left</align>
                    <aligny>center</aligny>
                    <textcolor>33FFFFFF</textcolor>
                    <label>$INFO[ListItem.Property(server.name)]</label>
                </control>
            </control>
        </itemlayout>
        <!-- SIDEBAR FOCUSED ITEM LAYOUT -->
        <focusedlayout height="{{ vscale(88) }}">
            <control type="group">
                <visible>!String.IsEmpty(ListItem.Property(item))</visible>
                <posx>0</posx>
                <posy>0</posy>
                <width>300</width>
                <height>{{ vscale(88) }}</height>
                <!-- Focus highlight background (only when list itself has focus) -->
                <control type="image">
                    <visible>Control.HasFocus(9001)</visible>
                    <posx>8</posx>
                    <posy>{{ vscale(14) }}</posy>
                    <width>284</width>
                    <height>{{ vscale(60) }}</height>
                    <texture border="10">script.plex/white-square-rounded.png</texture>
                    <colordiffuse>33FFFFFF</colordiffuse>
                </control>
                <!-- Active indicator bar (left edge) -->
                <control type="image">
                    <visible>!String.IsEmpty(ListItem.Property(is.active))</visible>
                    <posx>0</posx>
                    <posy>{{ vscale(24) }}</posy>
                    <width>3</width>
                    <height>{{ vscale(40) }}</height>
                    <texture>script.plex/white-square.png</texture>
                    <colordiffuse>FFE5A00D</colordiffuse>
                </control>
                <!-- Section icon - orange when focused or active -->
                <control type="image">
                    <visible>Control.HasFocus(9001) | !String.IsEmpty(ListItem.Property(is.active))</visible>
                    <posx>26</posx>
                    <posy>{{ vscale(30) }}</posy>
                    <width>28</width>
                    <height>{{ vscale(28) }}</height>
                    <texture>$INFO[ListItem.Icon]</texture>
                    <colordiffuse>FFE5A00D</colordiffuse>
                </control>
                <!-- Section icon - normal when not focused and not active, dimmer while sidebar is collapsed -->
                <control type="image">
                    <visible>[!ControlGroup(9000).HasFocus(0) | !String.IsEmpty(ListItem.Property(is.offline))] + !Control.HasFocus(9001) + String.IsEmpty(ListItem.Property(is.active))</visible>
                    <posx>26</posx>
                    <posy>{{ vscale(30) }}</posy>
                    <width>28</width>
                    <height>{{ vscale(28) }}</height>
                    <texture>$INFO[ListItem.Icon]</texture>
                    <colordiffuse>26FFFFFF</colordiffuse>
                </control>
                <!-- Section icon - normal when not focused and not active, and sidebar is expanded -->
                <control type="image">
                    <visible>ControlGroup(9000).HasFocus(0) + !Control.HasFocus(9001) + String.IsEmpty(ListItem.Property(is.active)) + String.IsEmpty(ListItem.Property(is.offline))</visible>
                    <posx>26</posx>
                    <posy>{{ vscale(30) }}</posy>
                    <width>28</width>
                    <height>{{ vscale(28) }}</height>
                    <texture>$INFO[ListItem.Icon]</texture>
                    <colordiffuse>99FFFFFF</colordiffuse>
                </control>
                <!-- Path-mapping indicator dot -->
                <control type="image">
                    <visible>!String.IsEmpty(ListItem.Property(is.mapped)) + String.IsEmpty(ListItem.Property(is.mapped.broken))</visible>
                    <posx>46</posx>
                    <posy>{{ vscale(26) }}</posy>
                    <width>8</width>
                    <height>{{ vscale(8) }}</height>
                    <texture>script.plex/white-square-rounded-4r.png</texture>
                    <colordiffuse>AAFFFFFF</colordiffuse>
                </control>
                <control type="image">
                    <visible>!String.IsEmpty(ListItem.Property(is.mapped.broken))</visible>
                    <posx>46</posx>
                    <posy>{{ vscale(26) }}</posy>
                    <width>8</width>
                    <height>{{ vscale(8) }}</height>
                    <texture>script.plex/white-square-rounded-4r.png</texture>
                    <colordiffuse>FFFF4444</colordiffuse>
                </control>
                <!-- Section label (expanded only): one line, or - when the account has more than one
                     server (ListItem.Property(server.name), set for libraries only) - the library over
                     its server's name. Kodi labels only centre vertically, so each line's box is
                     placed: together they centre on the row like the single line (y=44). -->
                <control type="label">
                    <visible>ControlGroup(9000).HasFocus(0) + String.IsEmpty(ListItem.Property(server.name)) + Control.HasFocus(9001)</visible>
                    <posx>68</posx>
                    <posy>0</posy>
                    <width>220</width>
                    <height>{{ vscale(88) }}</height>
                    <font>font10</font>
                    <align>left</align>
                    <aligny>center</aligny>
                    <textcolor>FFFFFFFF</textcolor>
                    <focusedcolor>FFFFFFFF</focusedcolor>
                    <label>$INFO[ListItem.Label]</label>
                </control>
                <control type="label">
                    <visible>ControlGroup(9000).HasFocus(0) + !String.IsEmpty(ListItem.Property(server.name)) + Control.HasFocus(9001)</visible>
                    <posx>68</posx>
                    <posy>{{ vscale(19) }}</posy>
                    <width>220</width>
                    <height>{{ vscale(28) }}</height>
                    <font>font10</font>
                    <align>left</align>
                    <aligny>center</aligny>
                    <textcolor>FFFFFFFF</textcolor>
                    <focusedcolor>FFFFFFFF</focusedcolor>
                    <label>$INFO[ListItem.Label]</label>
                </control>
                <control type="label">
                    <visible>ControlGroup(9000).HasFocus(0) + !String.IsEmpty(ListItem.Property(server.name)) + Control.HasFocus(9001)</visible>
                    <posx>68</posx>
                    <posy>{{ vscale(48) }}</posy>
                    <width>220</width>
                    <height>{{ vscale(20) }}</height>
                    <font>font8</font>
                    <align>left</align>
                    <aligny>center</aligny>
                    <textcolor>99FFFFFF</textcolor>
                    <label>$INFO[ListItem.Property(server.name)]</label>
                </control>
                <!-- The same in the unfocused row's colours while focus is elsewhere in the sidebar (the
                     Libraries button under the list): Kodi still draws the selected row with this
                     layout then -->
                <control type="label">
                    <visible>ControlGroup(9000).HasFocus(0) + String.IsEmpty(ListItem.Property(server.name)) + String.IsEmpty(ListItem.Property(is.offline)) + !Control.HasFocus(9001)</visible>
                    <posx>68</posx>
                    <posy>0</posy>
                    <width>220</width>
                    <height>{{ vscale(88) }}</height>
                    <font>font10</font>
                    <align>left</align>
                    <aligny>center</aligny>
                    <textcolor>99FFFFFF</textcolor>
                    <label>$INFO[ListItem.Label]</label>
                </control>
                <control type="label">
                    <visible>ControlGroup(9000).HasFocus(0) + !String.IsEmpty(ListItem.Property(server.name)) + String.IsEmpty(ListItem.Property(is.offline)) + !Control.HasFocus(9001)</visible>
                    <posx>68</posx>
                    <posy>{{ vscale(19) }}</posy>
                    <width>220</width>
                    <height>{{ vscale(28) }}</height>
                    <font>font10</font>
                    <align>left</align>
                    <aligny>center</aligny>
                    <textcolor>99FFFFFF</textcolor>
                    <label>$INFO[ListItem.Label]</label>
                </control>
                <control type="label">
                    <visible>ControlGroup(9000).HasFocus(0) + !String.IsEmpty(ListItem.Property(server.name)) + String.IsEmpty(ListItem.Property(is.offline)) + !Control.HasFocus(9001)</visible>
                    <posx>68</posx>
                    <posy>{{ vscale(48) }}</posy>
                    <width>220</width>
                    <height>{{ vscale(20) }}</height>
                    <font>font8</font>
                    <align>left</align>
                    <aligny>center</aligny>
                    <textcolor>66FFFFFF</textcolor>
                    <label>$INFO[ListItem.Property(server.name)]</label>
                </control>
                <!-- The same, dimmed: a library whose server isn't answering, or is no longer
                     on the account (ListItem.Property(is.offline)) -->
                <control type="label">
                    <visible>ControlGroup(9000).HasFocus(0) + String.IsEmpty(ListItem.Property(server.name)) + !String.IsEmpty(ListItem.Property(is.offline)) + !Control.HasFocus(9001)</visible>
                    <posx>68</posx>
                    <posy>0</posy>
                    <width>220</width>
                    <height>{{ vscale(88) }}</height>
                    <font>font10</font>
                    <align>left</align>
                    <aligny>center</aligny>
                    <textcolor>40FFFFFF</textcolor>
                    <focusedcolor>FFFFFFFF</focusedcolor>
                    <label>$INFO[ListItem.Label]</label>
                </control>
                <control type="label">
                    <visible>ControlGroup(9000).HasFocus(0) + !String.IsEmpty(ListItem.Property(server.name)) + !String.IsEmpty(ListItem.Property(is.offline)) + !Control.HasFocus(9001)</visible>
                    <posx>68</posx>
                    <posy>{{ vscale(19) }}</posy>
                    <width>220</width>
                    <height>{{ vscale(28) }}</height>
                    <font>font10</font>
                    <align>left</align>
                    <aligny>center</aligny>
                    <textcolor>40FFFFFF</textcolor>
                    <focusedcolor>FFFFFFFF</focusedcolor>
                    <label>$INFO[ListItem.Label]</label>
                </control>
                <control type="label">
                    <visible>ControlGroup(9000).HasFocus(0) + !String.IsEmpty(ListItem.Property(server.name)) + !String.IsEmpty(ListItem.Property(is.offline)) + !Control.HasFocus(9001)</visible>
                    <posx>68</posx>
                    <posy>{{ vscale(48) }}</posy>
                    <width>220</width>
                    <height>{{ vscale(20) }}</height>
                    <font>font8</font>
                    <align>left</align>
                    <aligny>center</aligny>
                    <textcolor>33FFFFFF</textcolor>
                    <label>$INFO[ListItem.Property(server.name)]</label>
                </control>
            </control>
        </focusedlayout>
    </control>

    <!-- Server button at bottom of sidebar -->
    <control type="button" id="201">
        <posx>8</posx>
        <!-- posy=1009, not 990: measured against official Plex, the bottom gear icon's center sits at
             y=1034, not the 1015 this (and the icon+name overlay group below, which this button
             overlays) computed to. -->
        <posy>{{ vscale(1009) }}</posy>
        <width>284</width>
        <height>{{ vscale(50) }}</height>
        <font>font10</font>
        <textcolor>00000000</textcolor>
        <focusedcolor>00000000</focusedcolor>
        <disabledcolor>00000000</disabledcolor>
        <align>center</align>
        <aligny>center</aligny>
        <onup>9001</onup>
        <onright condition="!String.IsEmpty(Window.Property(server.unavailable))">2600</onright><onright>50</onright>
        <ondown>noop</ondown>
        <texturefocus colordiffuse="33FFFFFF" border="10">script.plex/white-square-rounded.png</texturefocus>
        <texturenofocus>-</texturenofocus>
        <label> </label>
        <onunfocus condition="!String.IsEmpty(Window.Property(show.servers))">SetFocus(260)</onunfocus>
    </control>
    <!-- Server icon + name overlay -->
    <control type="group">
        <posx>10</posx>
        <!-- posy=1009, not 990: see button 201's own comment above - moves the icon (itself at posy=10
             within this group) down 19px so its center lands at y=1034, matching official Plex's own
             measured gear position (was y=1015). -->
        <posy>{{ vscale(1009) }}</posy>
        <width>280</width>
        <height>{{ vscale(50) }}</height>
        <control type="image">
            <posx>15</posx>
            <posy>{{ vscale(10) }}</posy>
            <width>30</width>
            <height>{{ vscale(30) }}</height>
            <texture>$INFO[Window.Property(server.icon)]</texture>
        </control>
        <!-- secure -->
        <control type="image">
            <visible>!String.IsEmpty(Window.Property(server.iconmod))</visible>
            <posx>4</posx>
            <posy>{{ vscale(16) }}</posy>
            <width>14</width>
            <height>{{ vscale(12) }}</height>
            <texture>$INFO[Window.Property(server.iconmod2)]</texture>
            <colordiffuse>FFEEEEEE</colordiffuse>
        </control>
        <!-- local -->
        <control type="image">
            <visible>String.IsEmpty(Window.Property(server.iconmod))</visible>
            <posx>4</posx>
            <posy>{{ vscale(30) }}</posy>
            <width>14</width>
            <height>{{ vscale(12) }}</height>
            <texture>$INFO[Window.Property(server.iconmod2)]</texture>
            <colordiffuse>FFEEEEEE</colordiffuse>
        </control>
        <!-- Server name (expanded only) -->
        <control type="label">
            <visible>ControlGroup(9000).HasFocus(0)</visible>
            <animation effect="fade" start="0" end="100" time="200">Visible</animation>
            <animation effect="fade" start="100" end="0" time="200">Hidden</animation>
            <posx>55</posx>
            <posy>0</posy>
            <width>210</width>
            <height>{{ vscale(50) }}</height>
            <font>font10</font>
            <align>left</align>
            <aligny>center</aligny>
            <textcolor>FFFFFFFF</textcolor>
            <label>$INFO[Window.Property(server.name)]</label>
        </control>
    </control>
</control>
