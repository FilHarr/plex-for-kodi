{# The selected server isn't answering: shown where an empty view's rows or grid would be
   (library.xml.tpl's grid views, script-plex-recommended.xml.tpl). LibraryWindow.
   updateServerUnavailable() sets server.unavailable (the heading) only while the view has nothing
   to show, and server.unavailable.detail under it. "Try again" retests at once
   (LibraryWindow.retryServerNow()); Left goes back to the sidebar, whose Right comes here while
   this shows (includes/sidebar.xml.tpl). Same placement and type as the grid's "no content"
   message, which stands aside for this. #}
<control type="group">
    <visible>!String.IsEmpty(Window.Property(server.unavailable))</visible>
    <posx>0</posx>
    <posy>{{ vscale(430) }}</posy>
    <control type="label">
        <scroll>false</scroll>
        <posx>60</posx>
        <posy>0</posy>
        <width>1800</width>
        <height>{{ vscale(35) }}</height>
        <font>font13</font>
        <align>center</align>
        <textcolor>FFFFFFFF</textcolor>
        <label>[B]$INFO[Window.Property(server.unavailable)][/B]</label>
    </control>
    <control type="label">
        <scroll>false</scroll>
        <posx>60</posx>
        <posy>{{ vscale(60) }}</posy>
        <width>1800</width>
        <height>{{ vscale(35) }}</height>
        <font>font13</font>
        <align>center</align>
        <textcolor>FFCCCCCC</textcolor>
        <label>$INFO[Window.Property(server.unavailable.detail)]</label>
    </control>
    <control type="button" id="2600">
        <animation effect="zoom" start="100" end="110,120" time="100" center="auto" reversible="false">Focus</animation>
        <animation effect="zoom" start="110,120" end="100" time="100" center="auto" reversible="false">UnFocus</animation>
        <posx>790</posx>
        <posy>{{ vscale(110) }}</posy>
        <width>340</width>
        <height>{{ vscale(143, 1.1) }}</height>
        <font>font10</font>
        <texturefocus colordiffuse="FFE5A00D" border="50">script.plex/buttons/blank-focus.png</texturefocus>
        <texturenofocus colordiffuse="99FFFFFF" border="50">script.plex/buttons/blank.png</texturenofocus>
        <align>center</align>
        <aligny>center</aligny>
        <textcolor>FF000000</textcolor>
        <focusedcolor>FF000000</focusedcolor>
        <label>$ADDON[script.plexmod 35032]</label>
        <onleft>9001</onleft>
    </control>
</control>
