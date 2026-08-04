    <!-- Server dropdown (triggered from sidebar server button) -->
    <control type="group" id="802">
        <visible>Control.HasFocus(260) | !String.IsEmpty(Window.Property(show.servers))</visible>
        <posx>80</posx>
        <posy>{{ vscale(890) }}</posy>
        <control type="image" id="800">
            <posx>-40</posx>
            <posy>{{ vscale(-40) }}</posy>
            <width>580</width>
            <height>{{ vscale(146) }}</height>
            <texture border="42">script.plex/drop-shadow.png</texture>
        </control>
        <control type="list" id="260">
            <hitrect x="0" y="-10" w="500" h="910" />
            <posx>0</posx>
            <posy>0</posy>
            <width>500</width>
            <height>{{ vscale(900) }}</height>
            <onleft>9001</onleft>
            <onright>9001</onright>
            <onunfocus>SetProperty(show.servers,)</onunfocus>
            <scrolltime>200</scrolltime>
            <orientation>vertical</orientation>
            <pagecontrol>261</pagecontrol>
            <!-- ITEM LAYOUT ########################################## -->
            <itemlayout height="{{ vscale(100) }}">
                <control type="image">
                    <visible>!String.IsEmpty(ListItem.Property(first))</visible>
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>500</width>
                    <height>{{ vscale(100) }}</height>
                    <texture colordiffuse="FF1F1F1F" border="10">script.plex/white-square-top-rounded.png</texture>
                </control>
                <control type="image">
                    <visible>String.IsEmpty(ListItem.Property(first)) + String.IsEmpty(ListItem.Property(last)) + String.IsEmpty(ListItem.Property(only))</visible>
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>500</width>
                    <height>{{ vscale(100) }}</height>
                    <texture colordiffuse="FF1F1F1F">script.plex/white-square.png</texture>
                </control>
                <control type="image">
                    <visible>!String.IsEmpty(ListItem.Property(last))</visible>
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>500</width>
                    <height>{{ vscale(100) }}</height>
                    <texture flipy="true" colordiffuse="FF1F1F1F" border="10">script.plex/white-square-top-rounded.png</texture>
                </control>
                <control type="image">
                    <visible>!String.IsEmpty(ListItem.Property(only))</visible>
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>500</width>
                    <height>{{ vscale(100) }}</height>
                    <texture colordiffuse="FF1F1F1F" border="10">script.plex/white-square-top-rounded.png</texture>
                </control>
                <control type="group">
                    <visible>!String.IsEmpty(ListItem.Label2)</visible>
                    <control type="label">
                        <posx>20</posx>
                        <posy>{{ vscale(20) }}</posy>
                        <width>400</width>
                        <height>{{ vscale(35) }}</height>
                        <font>font12</font>
                        <align>left</align>
                        <aligny>center</aligny>
                        <textcolor>FFFFFFFF</textcolor>
                        <label>$INFO[ListItem.Label]</label>
                    </control>
                    <control type="label">
                        <posx>20</posx>
                        <posy>{{ vscale(50) }}</posy>
                        <width>400</width>
                        <height>{{ vscale(35) }}</height>
                        <font>font12</font>
                        <align>left</align>
                        <aligny>center</aligny>
                        <textcolor>FFA0A0A0</textcolor>
                        <label>$INFO[ListItem.Label2]</label>
                    </control>
                </control>
                <control type="label">
                    <visible>String.IsEmpty(ListItem.Label2)</visible>
                    <posx>20</posx>
                    <posy>0</posy>
                    <width>400</width>
                    <height>{{ vscale(100) }}</height>
                    <font>font12</font>
                    <align>left</align>
                    <aligny>center</aligny>
                    <textcolor>FFFFFFFF</textcolor>
                    <label>$INFO[ListItem.Label]</label>
                </control>

                <!-- not status + not current + local -->
                <control type="image">
                    <visible>String.IsEmpty(ListItem.Property(status)) + String.IsEmpty(ListItem.Property(current)) + !String.IsEmpty(ListItem.Property(local)) </visible>
                    <posx>456</posx>
                    <posy>{{ vscale(38) }}</posy>
                    <width>24</width>
                    <height>{{ vscale(21) }}</height>
                    <texture>script.plex/home/device/home.png</texture>
                </control>
                <!-- not status + current + local -->
                <control type="image">
                    <visible>String.IsEmpty(ListItem.Property(status)) + !String.IsEmpty(ListItem.Property(current)) + !String.IsEmpty(ListItem.Property(local)) </visible>
                    <posx>415</posx>
                    <posy>{{ vscale(38) }}</posy>
                    <width>24</width>
                    <height>{{ vscale(21) }}</height>
                    <texture>script.plex/home/device/home.png</texture>
                </control>
                <!-- status + not current + local -->
                <control type="image">
                    <visible>!String.IsEmpty(ListItem.Property(status)) + String.IsEmpty(ListItem.Property(current)) + !String.IsEmpty(ListItem.Property(local)) </visible>
                    <posx>415</posx>
                    <posy>{{ vscale(38) }}</posy>
                    <width>24</width>
                    <height>{{ vscale(21) }}</height>
                    <texture>script.plex/home/device/home.png</texture>
                </control>
                <!-- status + current + local -->
                <control type="image">
                    <visible>!String.IsEmpty(ListItem.Property(status)) + !String.IsEmpty(ListItem.Property(current)) + !String.IsEmpty(ListItem.Property(local)) </visible>
                    <posx>374</posx>
                    <posy>{{ vscale(38) }}</posy>
                    <width>24</width>
                    <height>{{ vscale(21) }}</height>
                    <texture>script.plex/home/device/home.png</texture>
                </control>
                <!-- status + not current -->
                <control type="image">
                    <visible>!String.IsEmpty(ListItem.Property(status)) + String.IsEmpty(ListItem.Property(current))</visible>
                    <posx>456</posx>
                    <posy>{{ vscale(38) }}</posy>
                    <width>24</width>
                    <height>{{ vscale(24) }}</height>
                    <texture>script.plex/home/device/$INFO[ListItem.Property(status)]</texture>
                </control>
                <!-- status + current -->
                <control type="image">
                    <visible>!String.IsEmpty(ListItem.Property(status)) + !String.IsEmpty(ListItem.Property(current))</visible>
                    <posx>415</posx>
                    <posy>{{ vscale(38) }}</posy>
                    <width>24</width>
                    <height>{{ vscale(24) }}</height>
                    <texture>script.plex/home/device/$INFO[ListItem.Property(status)]</texture>
                </control>
                <control type="image">
                    <visible>!String.IsEmpty(ListItem.Property(current))</visible>
                    <posx>449</posx>
                    <posy>{{ vscale(38) }}</posy>
                    <width>31</width>
                    <height>{{ vscale(24) }}</height>
                    <texture colordiffuse="FFFFFFFF">script.plex/home/device/check.png</texture>
                </control>

            </itemlayout>
            <focusedlayout height="{{ vscale(100) }}">
                <control type="image">
                    <visible>!String.IsEmpty(ListItem.Property(first))</visible>
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>500</width>
                    <height>{{ vscale(100) }}</height>
                    <texture colordiffuse="FFE5A00D" border="10">script.plex/white-square-top-rounded.png</texture>
                </control>
                <control type="image">
                    <visible>String.IsEmpty(ListItem.Property(first)) + String.IsEmpty(ListItem.Property(last)) + String.IsEmpty(ListItem.Property(only))</visible>
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>500</width>
                    <height>{{ vscale(100) }}</height>
                    <texture colordiffuse="FFE5A00D">script.plex/white-square.png</texture>
                </control>
                <control type="image">
                    <visible>!String.IsEmpty(ListItem.Property(last))</visible>
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>500</width>
                    <height>{{ vscale(100) }}</height>
                    <texture flipy="true" colordiffuse="FFE5A00D" border="10">script.plex/white-square-top-rounded.png</texture>
                </control>
                <control type="image">
                    <visible>!String.IsEmpty(ListItem.Property(only))</visible>
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>500</width>
                    <height>{{ vscale(100) }}</height>
                    <texture colordiffuse="FFE5A00D" border="10">script.plex/white-square-top-rounded.png</texture>
                </control>
                <control type="group">
                    <visible>!String.IsEmpty(ListItem.Label2)</visible>
                    <control type="label">
                        <posx>20</posx>
                        <posy>{{ vscale(20) }}</posy>
                        <width>400</width>
                        <height>{{ vscale(35) }}</height>
                        <font>font12</font>
                        <align>left</align>
                        <aligny>center</aligny>
                        <textcolor>FF000000</textcolor>
                        <label>$INFO[ListItem.Label]</label>
                    </control>
                    <control type="label">
                        <posx>20</posx>
                        <posy>{{ vscale(50) }}</posy>
                        <width>400</width>
                        <height>{{ vscale(35) }}</height>
                        <font>font12</font>
                        <align>left</align>
                        <aligny>center</aligny>
                        <textcolor>FFFFFFFF</textcolor>
                        <label>$INFO[ListItem.Label2]</label>
                    </control>
                </control>
                <control type="label">
                    <visible>String.IsEmpty(ListItem.Label2)</visible>
                    <posx>20</posx>
                    <posy>0</posy>
                    <width>400</width>
                    <height>{{ vscale(100) }}</height>
                    <font>font12</font>
                    <align>left</align>
                    <aligny>center</aligny>
                    <textcolor>FF000000</textcolor>
                    <label>$INFO[ListItem.Label]</label>
                </control>

                <!-- not status + not current + local -->
                <control type="image">
                    <visible>String.IsEmpty(ListItem.Property(status)) + String.IsEmpty(ListItem.Property(current)) + !String.IsEmpty(ListItem.Property(local)) </visible>
                    <posx>456</posx>
                    <posy>{{ vscale(38) }}</posy>
                    <width>24</width>
                    <height>{{ vscale(21) }}</height>
                    <texture>script.plex/home/device/home.png</texture>
                </control>
                <!-- not status + current + local -->
                <control type="image">
                    <visible>String.IsEmpty(ListItem.Property(status)) + !String.IsEmpty(ListItem.Property(current)) + !String.IsEmpty(ListItem.Property(local)) </visible>
                    <posx>415</posx>
                    <posy>{{ vscale(38) }}</posy>
                    <width>24</width>
                    <height>{{ vscale(21) }}</height>
                    <texture>script.plex/home/device/home.png</texture>
                </control>
                <!-- status + not current + local -->
                <control type="image">
                    <visible>!String.IsEmpty(ListItem.Property(status)) + String.IsEmpty(ListItem.Property(current)) + !String.IsEmpty(ListItem.Property(local)) </visible>
                    <posx>415</posx>
                    <posy>{{ vscale(38) }}</posy>
                    <width>24</width>
                    <height>{{ vscale(21) }}</height>
                    <texture>script.plex/home/device/home.png</texture>
                </control>
                <!-- status + current + local -->
                <control type="image">
                    <visible>!String.IsEmpty(ListItem.Property(status)) + !String.IsEmpty(ListItem.Property(current)) + !String.IsEmpty(ListItem.Property(local)) </visible>
                    <posx>374</posx>
                    <posy>{{ vscale(38) }}</posy>
                    <width>24</width>
                    <height>{{ vscale(21) }}</height>
                    <texture>script.plex/home/device/home.png</texture>
                </control>
                <control type="image">
                    <visible>!String.IsEmpty(ListItem.Property(status)) + String.IsEmpty(ListItem.Property(current))</visible>
                    <posx>456</posx>
                    <posy>{{ vscale(38) }}</posy>
                    <width>24</width>
                    <height>{{ vscale(24) }}</height>
                    <texture>script.plex/home/device/focus-$INFO[ListItem.Property(status)]</texture>
                </control>
                <control type="image">
                    <visible>!String.IsEmpty(ListItem.Property(status)) + !String.IsEmpty(ListItem.Property(current))</visible>
                    <posx>415</posx>
                    <posy>{{ vscale(38) }}</posy>
                    <width>24</width>
                    <height>{{ vscale(24) }}</height>
                    <texture>script.plex/home/device/focus-$INFO[ListItem.Property(status)]</texture>
                </control>
                <control type="image">
                    <visible>!String.IsEmpty(ListItem.Property(current))</visible>
                    <posx>449</posx>
                    <posy>{{ vscale(38) }}</posy>
                    <width>31</width>
                    <height>{{ vscale(24) }}</height>
                    <texture colordiffuse="FF000000">script.plex/home/device/check.png</texture>
                </control>

            </focusedlayout>
        </control>

        <control type="scrollbar" id="261">
            <posx>492</posx>
            <posy>{{ vscale(20) }}</posy>
            <width>8</width>
            <height>{{ vscale(860) }}</height>
            <texturesliderbackground>-</texturesliderbackground>
            <texturesliderbar colordiffuse="20FFFFFF" border="4">script.plex/white-square.png</texturesliderbar>
            <texturesliderbarfocus colordiffuse="20E5A00D" border="4">script.plex/white-square.png</texturesliderbarfocus>
            <textureslidernib>-</textureslidernib>
            <textureslidernibfocus>-</textureslidernibfocus>
            <pulseonselect>false</pulseonselect>
            <orientation>vertical</orientation>
            <showonepage>false</showonepage>
            <onleft>250</onleft>
        </control>
    </control>

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
