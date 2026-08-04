<!-- ITEM LAYOUT ########################################## -->
<itemlayout height="34">
    <control type="group">
        <posx>0</posx>
        <posy>0</posy>
        <control type="group">
            <posx>0</posx>
            <posy>0</posy>
            <control type="label">
                <visible>!String.IsEqual(Window(10000).Property(script.plex.key), ListItem.Property(letter))</visible>
                <posx>0</posx>
                <posy>0</posy>
                <width>34</width>
                <height>{{ vscale(32) }}</height>
                <font>font10</font>
                <align>center</align>
                <aligny>center</aligny>
                <textcolor>99FFFFFF</textcolor>
                <label>$INFO[ListItem.Label]</label>
            </control>
            <control type="label">
                <visible>String.IsEqual(Window(10000).Property(script.plex.key), ListItem.Property(key))</visible>
                <posx>0</posx>
                <posy>0</posy>
                <width>34</width>
                <height>{{ vscale(32) }}</height>
                <font>font10</font>
                <align>center</align>
                <aligny>center</aligny>
                <textcolor>FFE5A00D</textcolor>
                <label>$INFO[ListItem.Label]</label>
            </control>
        </control>
    </control>
</itemlayout>

<!-- FOCUSED LAYOUT ####################################### -->
<focusedlayout height="34">
    <control type="group">
        <posx>0</posx>
        <posy>0</posy>
        <control type="group">
            <posx>0</posx>
            <posy>0</posy>
            <control type="label">
                <visible>!String.IsEqual(Window(10000).Property(script.plex.key), ListItem.Property(letter))</visible>
                <posx>0</posx>
                <posy>0</posy>
                <width>34</width>
                <height>{{ vscale(32) }}</height>
                <font>font10</font>
                <align>center</align>
                <aligny>center</aligny>
                <textcolor>99FFFFFF</textcolor>
                <label>$INFO[ListItem.Label]</label>
            </control>
            <control type="label">
                <visible>String.IsEqual(Window(10000).Property(script.plex.key), ListItem.Property(key))</visible>
                <posx>0</posx>
                <posy>0</posy>
                <width>34</width>
                <height>{{ vscale(32) }}</height>
                <font>font10</font>
                <align>center</align>
                <aligny>center</aligny>
                <textcolor>FFE5A00D</textcolor>
                <label>$INFO[ListItem.Label]</label>
            </control>
        </control>

        <control type="group">
            <visible>Control.HasFocus(151)</visible>
            <posx>0</posx>
            <posy>0</posy>
            <control type="image">
                <visible>Control.HasFocus(151)</visible>
                <posx>0</posx>
                <posy>0</posy>
                <width>34</width>
                <height>{{ vscale(34) }}</height>
                <colordiffuse>FFE5A00D</colordiffuse>
                <texture border="12">script.plex/white-outline-rounded.png</texture>
            </control>
        </control>
    </control>
</focusedlayout>
