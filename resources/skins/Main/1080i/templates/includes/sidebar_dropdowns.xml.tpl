    <!-- User options dropdown (triggered from sidebar user button) -->
    <control type="group" id="901">
        <visible>Control.HasFocus(250) | !String.IsEmpty(Window.Property(show.options))</visible>
        <posx>80</posx>
        <posy>{{ vscale(42) }}</posy>
        <control type="image" id="801">
            <posx>-40</posx>
            <posy>{{ vscale(-40) }}</posy>
            <width>380</width>
            <height>{{ vscale(146) }}</height>
            <texture border="42">script.plex/drop-shadow.png</texture>
        </control>
        <control type="list" id="250">
            <hitrect x="0" y="-10" w="300" h="422" />
            <posx>0</posx>
            <posy>0</posy>
            <width>300</width>
            <height>{{ vscale(422) }}</height>
            <onleft>9001</onleft>
            <onunfocus>SetProperty(show.options,)</onunfocus>
            <scrolltime>200</scrolltime>
            <orientation>vertical</orientation>
            <!-- ITEM LAYOUT ########################################## -->
            <itemlayout height="{{ vscale(66) }}">
                <control type="image">
                    <visible>!String.IsEmpty(ListItem.Property(first))</visible>
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>300</width>
                    <height>{{ vscale(66) }}</height>
                    <texture colordiffuse="FF1F1F1F" border="10">script.plex/white-square-top-rounded.png</texture>
                </control>
                <control type="image">
                    <visible>String.IsEmpty(ListItem.Property(first)) + String.IsEmpty(ListItem.Property(last)) + String.IsEmpty(ListItem.Property(only))</visible>
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>300</width>
                    <height>{{ vscale(66) }}</height>
                    <texture colordiffuse="FF1F1F1F">script.plex/white-square.png</texture>
                </control>
                <control type="image">
                    <visible>!String.IsEmpty(ListItem.Property(last))</visible>
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>300</width>
                    <height>{{ vscale(66) }}</height>
                    <texture flipy="true" colordiffuse="FF1F1F1F" border="10">script.plex/white-square-top-rounded.png</texture>
                </control>
                <control type="image">
                    <visible>!String.IsEmpty(ListItem.Property(only))</visible>
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>300</width>
                    <height>{{ vscale(66) }}</height>
                    <texture colordiffuse="FF1F1F1F" border="10">script.plex/white-square-rounded.png</texture>
                </control>
                <control type="label">
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>300</width>
                    <height>{{ vscale(66) }}</height>
                    <font>font12</font>
                    <align>center</align>
                    <aligny>center</aligny>
                    <textcolor>FFFFFFFF</textcolor>
                    <label>$INFO[ListItem.Label]</label>
                </control>
            </itemlayout>
            <focusedlayout height="{{ vscale(66) }}">
                <control type="image">
                    <visible>!String.IsEmpty(ListItem.Property(first))</visible>
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>300</width>
                    <height>{{ vscale(66) }}</height>
                    <texture colordiffuse="FFE5A00D" border="10">script.plex/white-square-top-rounded.png</texture>
                </control>
                <control type="image">
                    <visible>String.IsEmpty(ListItem.Property(first)) + String.IsEmpty(ListItem.Property(last)) + String.IsEmpty(ListItem.Property(only))</visible>
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>300</width>
                    <height>{{ vscale(66) }}</height>
                    <texture colordiffuse="FFE5A00D">script.plex/white-square.png</texture>
                </control>
                <control type="image">
                    <visible>!String.IsEmpty(ListItem.Property(last))</visible>
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>300</width>
                    <height>{{ vscale(66) }}</height>
                    <texture flipy="true" colordiffuse="FFE5A00D" border="10">script.plex/white-square-top-rounded.png</texture>
                </control>
                <control type="image">
                    <visible>!String.IsEmpty(ListItem.Property(only))</visible>
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>300</width>
                    <height>{{ vscale(66) }}</height>
                    <texture colordiffuse="FFE5A00D" border="10">script.plex/white-square-rounded.png</texture>
                </control>
                <control type="label">
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>300</width>
                    <height>{{ vscale(66) }}</height>
                    <font>font12</font>
                    <align>center</align>
                    <aligny>center</aligny>
                    <textcolor>FF000000</textcolor>
                    <label>$INFO[ListItem.Label]</label>
                </control>
            </focusedlayout>
        </control>
    </control>
