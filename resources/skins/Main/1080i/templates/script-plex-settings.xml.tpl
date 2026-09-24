{% extends "base.xml.tpl" %}
{% block headers %}<defaultcontrol>300</defaultcontrol>{% endblock %}
{% block controls %}
<control type="image">
    <posx>0</posx>
    <posy>0</posy>
    <width>1920</width>
    <height>1080</height>
    <texture>script.plex/home/background-fallback.png</texture>
</control>

<control type="group">
    <animation effect="slide" end="-582,0" time="200" tween="quadratic" easing="out" condition="Control.HasFocus(125)">Conditional</animation>
    <posx>0</posx>
    <posy>0</posy>
    <control type="group">
        <control type="group">
            <animation effect="slide" end="-297,0" time="200" tween="quadratic" easing="out" condition="Control.HasFocus(125)">Conditional</animation>
            <control type="image">
                <posx>843</posx>
                <posy>125</posy>
                <width>1077</width>
                <height>955</height>
                <texture>script.plex/white-square.png</texture>
                <colordiffuse>32111111</colordiffuse>
            </control>
            <control type="image">
                <posx>0</posx>
                <posy>865</posy>
                <width>1920</width>
                <height>215</height>
                <texture>script.plex/white-square.png</texture>
                <colordiffuse>32000000</colordiffuse>
            </control>
        </control>
        <control type="image">
            <animation effect="slide" end="-297,0" time="200" tween="quadratic" easing="out" condition="Control.HasFocus(125)">Conditional</animation>
            <posx>843</posx>
            <posy>865</posy>
            <width>1077</width>
            <height>215</height>
            <texture>script.plex/white-square.png</texture>
            <colordiffuse>32111111</colordiffuse>
        </control>
        <control type="image">
            <animation effect="slide" end="-297,0" time="200" tween="quadratic" easing="out" condition="Control.HasFocus(125)">Conditional</animation>
            <posx>1920</posx>
            <posy>125</posy>
            <width>879</width>
            <height>955</height>
            <texture>script.plex/white-square.png</texture>
            <colordiffuse>66111111</colordiffuse>
        </control>
    </control>

    <control type="textbox">
        <animation effect="slide" end="-277,0" time="200" tween="quadratic" easing="out" condition="Control.HasFocus(125)">Conditional</animation>
        <visible>Control.HasFocus(100) | Control.HasFocus(125)</visible>
        <posx>872</posx>
        <posy>886.5</posy>
        <width>1024</width>
        <height>172</height>
        <font>font10</font>
        <textcolor>FFFFFFFF</textcolor>
        <align>left</align>
        <scrolltime>200</scrolltime>
        <autoscroll delay="5000" time="4000" repeat="15000"></autoscroll>
        <label>$INFO[Container(100).ListItem.Property(description)]</label>
    </control>

    <control type="group" id="50">
        <posx>248</posx>
        <posy>131.5</posy>
        <defaultcontrol always="true">75</defaultcontrol>
        <control type="list" id="75">
            <posx>0</posx>
            <posy>0</posy>
            <width>590</width>
            <height>741</height>
            <onleft>noop</onleft>
            <onright>noop</onright>
            <scrolltime>200</scrolltime>
            <orientation>vertical</orientation>
            <!-- ITEM LAYOUT ########################################## -->
            <itemlayout height="{{ vscale(75) }}">
                <control type="group">
                    <posx>88</posx>
                    <posy>{{ vscale(40) }}</posy>
                    <control type="label">
                        <posx>0</posx>
                        <posy>0</posy>
                        <width>414</width>
                        <height>{{ vscale(75) }}</height>
                        <font>font12</font>
                        <align>left</align>
                        <aligny>center</aligny>
                        <textcolor>FFFFFFFF</textcolor>
                        <label>$INFO[ListItem.Label]</label>
                    </control>
                    <control type="image">
                        <visible>String.IsEmpty(ListItem.Property(is.last))</visible>
                        <posx>0</posx>
                        <posy>{{ vscale(75) }}</posy>
                        <width>414</width>
                        <height>{{ vscale(2) }}</height>
                        <texture>script.plex/white-square.png</texture>
                        <colordiffuse>661F1F1F</colordiffuse>
                    </control>
                </control>
            </itemlayout>
            <focusedlayout height="{{ vscale(75) }}">
                <control type="group">
                    <visible>ControlGroup(50).HasFocus(0)</visible>
                    <control type="image">
                        <posx>0</posx>
                        <posy>0</posy>
                        <width>590</width>
                        <height>{{ vscale(155) }}</height>
                        <texture border="42">script.plex/drop-shadow.png</texture>
                    </control>
                    <control type="image">
                        <visible>Control.HasFocus(75)</visible>
                        <posx>40</posx>
                        <posy>{{ vscale(40) }}</posy>
                        <width>510</width>
                        <height>{{ vscale(75) }}</height>
                        <texture colordiffuse="FFE5A00D" border="10">script.plex/white-square-rounded.png</texture>
                    </control>
                    <control type="image">
                        <visible>!Control.HasFocus(75)</visible>
                        <posx>40</posx>
                        <posy>{{ vscale(40) }}</posy>
                        <width>510</width>
                        <height>{{ vscale(75) }}</height>
                        <texture colordiffuse="FFCC7B19" border="10">script.plex/white-square-rounded.png</texture>
                    </control>
                    <control type="image">
                        <visible>!Control.HasFocus(75)</visible>
                        <posx>512</posx>
                        <posy>{{ vscale(66) }}</posy>
                        <width>16</width>
                        <height>{{ vscale(23) }}</height>
                        <texture>script.plex/settings/expanded.png</texture>
                        <colordiffuse>FF000000</colordiffuse>
                    </control>
                    <control type="label">
                        <posx>88</posx>
                        <posy>{{ vscale(40) }}</posy>
                        <width>414</width>
                        <height>{{ vscale(75) }}</height>
                        <font>font12</font>
                        <align>left</align>
                        <aligny>center</aligny>
                        <textcolor>FF000000</textcolor>
                        <label>$INFO[ListItem.Label]</label>
                    </control>
                </control>
                <control type="label">
                    <visible>!ControlGroup(50).HasFocus(0)</visible>
                    <posx>88</posx>
                    <posy>{{ vscale(40) }}</posy>
                    <width>414</width>
                    <height>{{ vscale(75) }}</height>
                    <font>font12</font>
                    <align>left</align>
                    <aligny>center</aligny>
                    <textcolor>FFFFFFFF</textcolor>
                    <label>$INFO[ListItem.Label]</label>
                </control>
            </focusedlayout>
        </control>

        <control type="list" id="100">
            <visible>Integer.IsGreater(Container(100).NumItems,0)</visible>
            <enable>String.IsEmpty(Window.Property(section.about))</enable>
            <posx>604</posx>
            <posy>0</posy>
            <width>776</width>
            <height>715</height>
            <onleft>75</onleft>
            <onright>noop</onright>
            <scrolltime>200</scrolltime>
            <orientation>vertical</orientation>
            <pagecontrol>101</pagecontrol>
            <!-- ITEM LAYOUT ########################################## -->
            <itemlayout height="{{ vscale(75) }}">
                <control type="group">
                    <posx>88</posx>
                    <posy>{{ vscale(40) }}</posy>
                    <control type="label">
                        <posx>0</posx>
                        <posy>0</posy>
                        <width>500</width>
                        <height>{{ vscale(75) }}</height>
                        <font>font12</font>
                        <align>left</align>
                        <aligny>center</aligny>
                        <textcolor>FFFFFFFF</textcolor>
                        <scroll>true</scroll>
                        <label>$INFO[ListItem.Label]</label>
                    </control>
                    <control type="label">
                        <posx>200</posx>
                        <posy>0</posy>
                        <width>400</width>
                        <scroll>true</scroll>
                        <scrollspeed>25</scrollspeed>
                        <height>{{ vscale(75) }}</height>
                        <font>font12</font>
                        <align>right</align>
                        <aligny>center</aligny>
                        <textcolor>FFFFFFFF</textcolor>
                        <label>$INFO[ListItem.Label2]</label>
                    </control>
                    <control type="image">
                        <posx>0</posx>
                        <posy>{{ vscale(75) }}</posy>
                        <width>600</width>
                        <height>{{ vscale(2) }}</height>
                        <texture>script.plex/white-square.png</texture>
                        <colordiffuse>661F1F1F</colordiffuse>
                    </control>
                </control>
                <control type="group">
                    <posx>643</posx>
                    <posy>{{ vscale(55) }}</posy>
                    <control type="image">
                        <visible>!String.IsEmpty(ListItem.Property(checkbox))</visible>
                        <posx>0</posx>
                        <posy>0</posy>
                        <width>45</width>
                        <height>{{ vscale(45) }}</height>
                        <texture colordiffuse="EE000000" border="10">script.plex/settings/checkbox.png</texture>
                    </control>
                    <control type="image">
                        <visible>!String.IsEmpty(ListItem.Property(checkbox.checked))</visible>
                        <posx>0</posx>
                        <posy>0</posy>
                        <width>45</width>
                        <height>{{ vscale(45) }}</height>
                        <texture>script.plex/settings/checkmark.png</texture>
                    </control>
                </control>
            </itemlayout>
            <focusedlayout height="{{ vscale(75) }}">
                <control type="group">
                    <visible>Control.HasFocus(100) | Control.HasFocus(125)</visible>
                    <control type="image">
                        <posx>0</posx>
                        <posy>0</posy>
                        <width>776</width>
                        <height>{{ vscale(155) }}</height>
                        <texture border="42">script.plex/drop-shadow.png</texture>
                    </control>
                    <control type="image">
                        <visible>!Control.HasFocus(125)</visible>
                        <posx>40</posx>
                        <posy>{{ vscale(40) }}</posy>
                        <width>696</width>
                        <height>{{ vscale(75) }}</height>
                        <texture colordiffuse="FFE5A00D" border="10">script.plex/white-square-rounded.png</texture>
                    </control>
                    <control type="image">
                        <visible>Control.HasFocus(125)</visible>
                        <posx>40</posx>
                        <posy>{{ vscale(40) }}</posy>
                        <width>696</width>
                        <height>{{ vscale(75) }}</height>
                        <texture colordiffuse="FFCC7B19" border="10">script.plex/white-square-rounded.png</texture>
                    </control>
                    <control type="image">
                        <visible>Control.HasFocus(125)</visible>
                        <posx>698</posx>
                        <posy>{{ vscale(66) }}</posy>
                        <width>16</width>
                        <height>{{ vscale(23) }}</height>
                        <texture>script.plex/settings/expanded.png</texture>
                        <colordiffuse>FF000000</colordiffuse>
                    </control>
                    <control type="group">
                        <posx>88</posx>
                        <posy>{{ vscale(40) }}</posy>
                        <control type="label">
                            <posx>0</posx>
                            <posy>0</posy>
                            <width>500</width>
                            <height>{{ vscale(75) }}</height>
                            <font>font12</font>
                            <align>left</align>
                            <aligny>center</aligny>
                            <textcolor>FF000000</textcolor>
                            <scroll>true</scroll>
                            <label>$INFO[ListItem.Label]</label>
                        </control>
                        <control type="label">
                            <posx>200</posx>
                            <posy>0</posy>
                            <width>400</width>
                            <height>{{ vscale(75) }}</height>
                            <font>font12</font>
                            <align>right</align>
                            <aligny>center</aligny>
                            <textcolor>FF000000</textcolor>
                            <scroll>true</scroll>
                            <label>$INFO[ListItem.Label2]</label>
                        </control>
                    </control>
                </control>
                <control type="group">
                    <visible>!Control.HasFocus(100) + !Control.HasFocus(125)</visible>
                    <posx>88</posx>
                    <posy>{{ vscale(40) }}</posy>
                    <control type="label">
                        <posx>0</posx>
                        <posy>0</posy>
                        <width>400</width>
                        <height>{{ vscale(75) }}</height>
                        <font>font12</font>
                        <align>left</align>
                        <aligny>center</aligny>
                        <textcolor>FFFFFFFF</textcolor>
                        <scroll>true</scroll>
                        <label>$INFO[ListItem.Label]</label>
                    </control>
                    <control type="label">
                        <posx>200</posx>
                        <posy>0</posy>
                        <width>400</width>
                        <height>{{ vscale(75) }}</height>
                        <font>font12</font>
                        <align>right</align>
                        <aligny>center</aligny>
                        <textcolor>FFFFFFFF</textcolor>
                        <scroll>true</scroll>
                        <label>$INFO[ListItem.Label2]</label>
                    </control>
                    <control type="image">
                        <posx>0</posx>
                        <posy>{{ vscale(75) }}</posy>
                        <width>600</width>
                        <height>{{ vscale(2) }}</height>
                        <texture>script.plex/white-square.png</texture>
                        <colordiffuse>661F1F1F</colordiffuse>
                    </control>
                </control>
                <control type="group">
                    <posx>643</posx>
                    <posy>{{ vscale(55) }}</posy>
                    <control type="image">
                        <visible>!String.IsEmpty(ListItem.Property(checkbox))</visible>
                        <posx>0</posx>
                        <posy>0</posy>
                        <width>45</width>
                        <height>{{ vscale(45) }}</height>
                        <texture colordiffuse="EE000000" border="10">script.plex/settings/checkbox.png</texture>
                    </control>
                    <control type="image">
                        <visible>!String.IsEmpty(ListItem.Property(checkbox.checked))</visible>
                        <posx>0</posx>
                        <posy>0</posy>
                        <width>45</width>
                        <height>{{ vscale(45) }}</height>
                        <texture>script.plex/settings/checkmark.png</texture>
                    </control>
                </control>
            </focusedlayout>
        </control>

        <control type="scrollbar" id="101">
            <visible>Control.IsVisible(100) + !Control.IsVisible(125)</visible>
            <left>1388</left>
            <top>40</top>
            <width>9</width>
            <height>675</height>
            <visible>true</visible>
            <texturesliderbackground colordiffuse="66000000" border="4">script.plex/white-square-rounded-4r.png</texturesliderbackground>
            <texturesliderbar colordiffuse="66FFFFFF" border="4">script.plex/white-square-rounded-4r.png</texturesliderbar>
            <texturesliderbarfocus colordiffuse="FFE5A00D" border="4">script.plex/white-square-rounded-4r.png</texturesliderbarfocus>
            <textureslidernib>-</textureslidernib>
            <textureslidernibfocus>-</textureslidernibfocus>
            <pulseonselect>false</pulseonselect>
            <orientation>vertical</orientation>
            <showonepage>false</showonepage>
            <onleft>151</onleft>
        </control>

        <control type="list" id="125">
            <visible allowhiddenfocus="true">Control.HasFocus(125) + Integer.IsGreater(Container(100).NumItems,0)</visible>
            <enable>Integer.IsGreater(Container(100).NumItems,0) + String.IsEmpty(Window.Property(section.about))</enable>

            <posx>1383</posx>
            <posy>0</posy>
            <width>845</width>
            <height>715</height>
            <onleft>100</onleft>
            <scrolltime>200</scrolltime>
            <orientation>vertical</orientation>
            <pagecontrol>126</pagecontrol>
            <!-- ITEM LAYOUT ########################################## -->
            <itemlayout height="{{ vscale(75) }}">
                <control type="group">
                    <posx>88</posx>
                    <posy>{{ vscale(40) }}</posy>
                    <control type="label">
                        <posx>0</posx>
                        <posy>0</posy>
                        <width>594</width>
                        <height>{{ vscale(75) }}</height>
                        <font>font12</font>
                        <align>left</align>
                        <aligny>center</aligny>
                        <textcolor>FFFFFFFF</textcolor>
                        <label>$INFO[ListItem.Label]</label>
                    </control>
                    <control type="image">
                        <posx>0</posx>
                        <posy>{{ vscale(75) }}</posy>
                        <width>594</width>
                        <height>{{ vscale(2) }}</height>
                        <texture>script.plex/white-square.png</texture>
                        <colordiffuse>661F1F1F</colordiffuse>
                    </control>
                </control>
                <control type="group">
                    <posx>637</posx>
                    <posy>{{ vscale(55) }}</posy>
                    <control type="image">
                        <visible>!String.IsEmpty(ListItem.Property(checkbox.checked))</visible>
                        <posx>0</posx>
                        <posy>0</posy>
                        <width>45</width>
                        <height>{{ vscale(45) }}</height>
                        <texture>script.plex/settings/checkmark.png</texture>
                    </control>
                </control>
            </itemlayout>
            <focusedlayout height="{{ vscale(75) }}">
                <control type="image">
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>610</width>
                    <height>{{ vscale(155) }}</height>
                    <texture border="42">script.plex/drop-shadow.png</texture>
                </control>
                <control type="image">
                    <posx>40</posx>
                    <posy>{{ vscale(40) }}</posy>
                    <width>690</width>
                    <height>{{ vscale(75) }}</height>
                    <texture colordiffuse="FFE5A00D" border="10">script.plex/white-square-rounded.png</texture>
                </control>
                <control type="group">
                    <posx>88</posx>
                    <posy>{{ vscale(40) }}</posy>
                    <control type="label">
                        <posx>0</posx>
                        <posy>0</posy>
                        <width>594</width>
                        <height>{{ vscale(75) }}</height>
                        <font>font12</font>
                        <align>left</align>
                        <aligny>center</aligny>
                        <textcolor>FF000000</textcolor>
                        <label>$INFO[ListItem.Label]</label>
                    </control>
                </control>
                <control type="group">
                    <posx>637</posx>
                    <posy>{{ vscale(55) }}</posy>
                    <control type="image">
                        <visible>!String.IsEmpty(ListItem.Property(checkbox.checked))</visible>
                        <posx>0</posx>
                        <posy>0</posy>
                        <width>45</width>
                        <height>{{ vscale(45) }}</height>
                        <texture>script.plex/settings/checkmark.png</texture>
                    </control>
                </control>
            </focusedlayout>
        </control>

        <control type="scrollbar" id="126">
            <visible>Control.IsVisible(125)</visible>
            <left>2161</left>
            <top>40</top>
            <width>9</width>
            <height>675</height>
            <visible>true</visible>
            <texturesliderbackground colordiffuse="66000000" border="4">script.plex/white-square-rounded-4r.png</texturesliderbackground>
            <texturesliderbar colordiffuse="66FFFFFF" border="4">script.plex/white-square-rounded-4r.png</texturesliderbar>
            <texturesliderbarfocus colordiffuse="FFE5A00D" border="4">script.plex/white-square-rounded-4r.png</texturesliderbarfocus>
            <textureslidernib>-</textureslidernib>
            <textureslidernibfocus>-</textureslidernibfocus>
            <pulseonselect>false</pulseonselect>
            <orientation>vertical</orientation>
            <showonepage>false</showonepage>
            <onleft>151</onleft>
        </control>

    </control>
</control>


<control type="group" id="200">
    <posx>0</posx>
    <posy>0</posy>
    <width>1920</width>
    <height>125</height>
    <control type="image">
        <posx>0</posx>
        <posy>0</posy>
        <width>1920</width>
        <height>125</height>
        <texture>script.plex/white-square.png</texture>
        <colordiffuse>C0000000</colordiffuse>
    </control>
    <control type="grouplist">
        <posx>60</posx>
        <posy>{{ vscale(42.5) }}</posy>
        <width>1000</width>
        <height>{{ vscale(40) }}</height>
        <align>left</align>
        <itemgap>60</itemgap>
        <orientation>horizontal</orientation>
        <ondown>50</ondown>
        <control type="label">
            <width max="500">auto</width>
            <height>{{ vscale(40) }}</height>
            <font>font12</font>
            <align>left</align>
            <aligny>center</aligny>
            <textcolor>FFFFFFFF</textcolor>
            <label>[UPPERCASE]$INFO[Window.Property(heading)][/UPPERCASE]</label>
        </control>
    </control>
    <control type="label">
        <right>60</right>
        <posy>{{ vscale(30) }}</posy>
        <width>200</width>
        <height>{{ vscale(65) }}</height>
        <font>font12</font>
        <align>right</align>
        <aligny>center</aligny>
        <textcolor>FFFFFFFF</textcolor>
        <label>$INFO[System.Time]</label>
    </control>
</control>
{% endblock controls %}