{% extends "default.xml.tpl" %}
{% block headers %}<defaultcontrol>1001</defaultcontrol>{% endblock %}
{% block header %}
    {{ super() }}
    {% include "includes/sidebar.xml.tpl" %}
    <!-- Declared last so groups 802/901 draw on top - see script-plex-pre_play.xml.tpl's own copy
         of this include for the full reasoning. -->
    {% include "includes/sidebar_dropdowns.xml.tpl" %}
{% endblock header %}

{% block content %}
<!-- Search (search.SearchWindow), a sidebar destination shown by LibraryWindow. No background of
     its own: the shared one (includes/default_background.xml.tpl), showing the neutral colour
     panel - SearchWindow.paintInitialBackground(). -->
<control type="group" id="50">
    <!-- Slide right while the sidebar rail is expanded (focused), as every hosted screen does. -->
    <animation effect="slide" end="220,0" time="200" tween="sine" easing="inout" condition="ControlGroup(9000).HasFocus(0)">Conditional</animation>
    <!-- posx=60, not 0: clears the collapsed sidebar rail's icon column - see includes/sidebar.xml.tpl. -->
    <posx>60</posx>
    <posy>0</posy>
    <defaultcontrol>1001</defaultcontrol>

<!-- No panel of its own (the user, 2026-10-06): the controls sit on the screen's background,
     each key and button on its own tile. -->

<!-- Which servers a search asks (SearchWindow.chooseServers()): the media settings button's icon,
     on a multi-server account, right of the entry box -->
<control type="button" id="998">
    <visible>!String.IsEmpty(Window.Property(search.multi))</visible>
    <posx>422</posx>
    <posy>{{ vscale(64) }}</posy>
    <width>52</width>
    <height>{{ vscale(52) }}</height>
    <!-- not Left to the entry box but to the sidebar: a remote has no use for the box (OK on it
         opens Kodi's own keyboard), and a keyboard's typing focuses it anyway (SafeControlEdit
         grab_focus) - the user, 2026-10-07. With Kodi's keyboard there are no keys: to the box. -->
    <onleft condition="String.IsEmpty(Window.Property(hide.kbd))">9000</onleft>
    <onleft condition="!String.IsEmpty(Window.Property(hide.kbd))">650</onleft>
    <ondown>1006</ondown>
    <onright>2100</onright>
    <font>font12</font>
    <texturefocus colordiffuse="FFE5A00D">script.plex/buttons/player/modern/settings.png</texturefocus>
    <texturenofocus colordiffuse="FFFFFFFF">script.plex/buttons/player/modern/settings.png</texturenofocus>
    <label> </label>
</control>

<control type="group" id="899">
    <!-- ENTRY: level with the results' first row of art, the servers button to its right. With
         one server there's no servers button, and SearchWindow.onFirstInit() widens the box, its
         field and its text (652, 650, 651) to the keyboard's full 414. -->
    <control type="group">
        <posx>60</posx>
        <posy>{{ vscale(60) }}</posy>
        <width>354</width>
        <height>{{ vscale(60) }}</height>
        <control type="image" id="652">
            <posx>0</posx>
            <posy>0</posy>
            <width>354</width>
            <height>{{ vscale(60) }}</height>
            <texture colordiffuse="FF000000" border="10">script.plex/white-square-rounded.png</texture>
        </control>
        <control type="edit" id="650">
            <posx>0</posx>
            <posy>0</posy>
            <width>354</width>
            <height>{{ vscale(60) }}</height>
            <align>left</align>
            <aligny>center</aligny>
            <onleft>9000</onleft>
            <ondown condition="String.IsEmpty(Window.Property(hide.kbd))">1001</ondown>
            <ondown condition="!String.IsEmpty(Window.Property(hide.kbd))">2050</ondown>
            <onright condition="Control.IsVisible(998)">998</onright>
            <onright condition="!Control.IsVisible(998)">2100</onright>
            <!-- Kodi draws the text and its cursor while the field has focus (a keyboard's
                 Left/Right/Home/End move it, and keys go in where it is); otherwise 651 does -->
            <textcolor>00000000</textcolor>
            <focusedcolor>FFFFFFFF</focusedcolor>
            <label> </label>
            <hinttext> </hinttext>
            <font>font10</font>
            <textoffsetx>30</textoffsetx>
            <texturefocus border="10">script.plex/home/selected.png</texturefocus>
            <texturenofocus>-</texturenofocus>
            <pulseonselect>no</pulseonselect>
        </control>
        <!-- the text, while the field hasn't focus (SafeControlEdit.updateLabel()), with a caret at
             its end while typing goes in - from the left-hand column (SearchWindow.typesHere()),
             where the keyboard or a key off the field adds to the end -->
        <control type="label" id="651">
            <visible>!Control.HasFocus(650)</visible>
            <scroll>false</scroll>
            <posx>30</posx>
            <posy>0</posy>
            <width>294</width>
            <height>{{ vscale(60) }}</height>
            <align>left</align>
            <aligny>center</aligny>
            <textcolor>FFFFFFFF</textcolor>
            <font>font10</font>
            <label> </label>
        </control>
    </control>

    <!-- KEYBOARD: each key a rounded tile, 22FFFFFF at rest and 55FFFFFF focused (as the type
         buttons and Delete/Space/Clear). Up from the top row is the servers button, not the entry box
         (see the servers button's Left) - the user, 2026-10-07. -->
    <control type="group">
        <posx>60</posx>
        <posy>{{ vscale(144) }}</posy>
        <width>414</width>
        <height>{{ vscale(414) }}</height>
        <visible>String.IsEmpty(Window.Property(hide.kbd))</visible>

        <!-- BUTTONS ROW 1 -->
        <control type="group">
            <posx>0</posx>
            <posy>0</posy>
            <control type="group">
                <posx>0</posx>
                <posy>0</posy>
                <control type="button" id="1001">
                    <visible allowhiddenfocus="true">true</visible>
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>64</width>
                    <height>{{ vscale(64) }}</height>
                    <onup condition="Control.IsVisible(998)">998</onup>
                    <ondown>1007</ondown>
                    <onright>1002</onright>
                    <onleft>9000</onleft>
                    <font>font12</font>
                    <align>center</align>
                    <aligny>center</aligny>
                    <textcolor>FFFFFFFF</textcolor>
                    <focusedcolor>FFFFFFFF</focusedcolor>
                    <texturefocus colordiffuse="55FFFFFF" border="10">script.plex/white-square-rounded.png</texturefocus>
                    <texturenofocus colordiffuse="22FFFFFF" border="10">script.plex/white-square-rounded.png</texturenofocus>
                    <label>A</label>
                </control>
            </control>
            <control type="group">
                <posx>70</posx>
                <posy>0</posy>
                <control type="button" id="1002">
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>64</width>
                    <height>{{ vscale(64) }}</height>
                    <onup condition="Control.IsVisible(998)">998</onup>
                    <ondown>1008</ondown>
                    <onright>1003</onright>
                    <onleft>1001</onleft>
                    <font>font12</font>
                    <align>center</align>
                    <aligny>center</aligny>
                    <textcolor>FFFFFFFF</textcolor>
                    <focusedcolor>FFFFFFFF</focusedcolor>
                    <texturefocus colordiffuse="55FFFFFF" border="10">script.plex/white-square-rounded.png</texturefocus>
                    <texturenofocus colordiffuse="22FFFFFF" border="10">script.plex/white-square-rounded.png</texturenofocus>
                    <label>B</label>
                </control>
            </control>
            <control type="group">
                <posx>140</posx>
                <posy>0</posy>
                <control type="button" id="1003">
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>64</width>
                    <height>{{ vscale(64) }}</height>
                    <onup condition="Control.IsVisible(998)">998</onup>
                    <ondown>1009</ondown>
                    <onright>1004</onright>
                    <onleft>1002</onleft>
                    <font>font12</font>
                    <align>center</align>
                    <aligny>center</aligny>
                    <textcolor>FFFFFFFF</textcolor>
                    <focusedcolor>FFFFFFFF</focusedcolor>
                    <texturefocus colordiffuse="55FFFFFF" border="10">script.plex/white-square-rounded.png</texturefocus>
                    <texturenofocus colordiffuse="22FFFFFF" border="10">script.plex/white-square-rounded.png</texturenofocus>
                    <label>C</label>
                </control>
            </control>
            <control type="group">
                <posx>210</posx>
                <posy>0</posy>
                <control type="button" id="1004">
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>64</width>
                    <height>{{ vscale(64) }}</height>
                    <onup condition="Control.IsVisible(998)">998</onup>
                    <ondown>1010</ondown>
                    <onright>1005</onright>
                    <onleft>1003</onleft>
                    <font>font12</font>
                    <align>center</align>
                    <aligny>center</aligny>
                    <textcolor>FFFFFFFF</textcolor>
                    <focusedcolor>FFFFFFFF</focusedcolor>
                    <texturefocus colordiffuse="55FFFFFF" border="10">script.plex/white-square-rounded.png</texturefocus>
                    <texturenofocus colordiffuse="22FFFFFF" border="10">script.plex/white-square-rounded.png</texturenofocus>
                    <label>D</label>
                </control>
            </control>
            <control type="group">
                <posx>280</posx>
                <posy>0</posy>
                <control type="button" id="1005">
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>64</width>
                    <height>{{ vscale(64) }}</height>
                    <onup condition="Control.IsVisible(998)">998</onup>
                    <ondown>1011</ondown>
                    <onright>1006</onright>
                    <onleft>1004</onleft>
                    <font>font12</font>
                    <align>center</align>
                    <aligny>center</aligny>
                    <textcolor>FFFFFFFF</textcolor>
                    <focusedcolor>FFFFFFFF</focusedcolor>
                    <texturefocus colordiffuse="55FFFFFF" border="10">script.plex/white-square-rounded.png</texturefocus>
                    <texturenofocus colordiffuse="22FFFFFF" border="10">script.plex/white-square-rounded.png</texturenofocus>
                    <label>E</label>
                </control>
            </control>
            <control type="group">
                <posx>350</posx>
                <posy>0</posy>
                <control type="button" id="1006">
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>64</width>
                    <height>{{ vscale(64) }}</height>
                    <onup condition="Control.IsVisible(998)">998</onup>
                    <ondown>1012</ondown>
                    <onright>2100</onright>
                    <onleft>1005</onleft>
                    <font>font12</font>
                    <align>center</align>
                    <aligny>center</aligny>
                    <textcolor>FFFFFFFF</textcolor>
                    <focusedcolor>FFFFFFFF</focusedcolor>
                    <texturefocus colordiffuse="55FFFFFF" border="10">script.plex/white-square-rounded.png</texturefocus>
                    <texturenofocus colordiffuse="22FFFFFF" border="10">script.plex/white-square-rounded.png</texturenofocus>
                    <label>F</label>
                </control>
            </control>
        </control>
        <!-- BUTTONS ROW 2 -->
        <control type="group">
            <posx>0</posx>
            <posy>{{ vscale(70) }}</posy>
            <control type="group">
                <posx>0</posx>
                <posy>0</posy>
                <control type="button" id="1007">
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>64</width>
                    <height>{{ vscale(64) }}</height>
                    <onup>1001</onup>
                    <ondown>1013</ondown>
                    <onright>1008</onright>
                    <onleft>9000</onleft>
                    <font>font12</font>
                    <align>center</align>
                    <aligny>center</aligny>
                    <textcolor>FFFFFFFF</textcolor>
                    <focusedcolor>FFFFFFFF</focusedcolor>
                    <texturefocus colordiffuse="55FFFFFF" border="10">script.plex/white-square-rounded.png</texturefocus>
                    <texturenofocus colordiffuse="22FFFFFF" border="10">script.plex/white-square-rounded.png</texturenofocus>
                    <label>G</label>
                </control>
            </control>
            <control type="group">
                <posx>70</posx>
                <posy>0</posy>
                <control type="button" id="1008">
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>64</width>
                    <height>{{ vscale(64) }}</height>
                    <onup>1002</onup>
                    <ondown>1014</ondown>
                    <onright>1009</onright>
                    <onleft>1007</onleft>
                    <font>font12</font>
                    <align>center</align>
                    <aligny>center</aligny>
                    <textcolor>FFFFFFFF</textcolor>
                    <focusedcolor>FFFFFFFF</focusedcolor>
                    <texturefocus colordiffuse="55FFFFFF" border="10">script.plex/white-square-rounded.png</texturefocus>
                    <texturenofocus colordiffuse="22FFFFFF" border="10">script.plex/white-square-rounded.png</texturenofocus>
                    <label>H</label>
                </control>
            </control>
            <control type="group">
                <posx>140</posx>
                <posy>0</posy>
                <control type="button" id="1009">
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>64</width>
                    <height>{{ vscale(64) }}</height>
                    <onup>1003</onup>
                    <ondown>1015</ondown>
                    <onright>1010</onright>
                    <onleft>1008</onleft>
                    <font>font12</font>
                    <align>center</align>
                    <aligny>center</aligny>
                    <textcolor>FFFFFFFF</textcolor>
                    <focusedcolor>FFFFFFFF</focusedcolor>
                    <texturefocus colordiffuse="55FFFFFF" border="10">script.plex/white-square-rounded.png</texturefocus>
                    <texturenofocus colordiffuse="22FFFFFF" border="10">script.plex/white-square-rounded.png</texturenofocus>
                    <label>I</label>
                </control>
            </control>
            <control type="group">
                <posx>210</posx>
                <posy>0</posy>
                <control type="button" id="1010">
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>64</width>
                    <height>{{ vscale(64) }}</height>
                    <onup>1004</onup>
                    <ondown>1016</ondown>
                    <onright>1011</onright>
                    <onleft>1009</onleft>
                    <font>font12</font>
                    <align>center</align>
                    <aligny>center</aligny>
                    <textcolor>FFFFFFFF</textcolor>
                    <focusedcolor>FFFFFFFF</focusedcolor>
                    <texturefocus colordiffuse="55FFFFFF" border="10">script.plex/white-square-rounded.png</texturefocus>
                    <texturenofocus colordiffuse="22FFFFFF" border="10">script.plex/white-square-rounded.png</texturenofocus>
                    <label>J</label>
                </control>
            </control>
            <control type="group">
                <posx>280</posx>
                <posy>0</posy>
                <control type="button" id="1011">
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>64</width>
                    <height>{{ vscale(64) }}</height>
                    <onup>1005</onup>
                    <ondown>1017</ondown>
                    <onright>1012</onright>
                    <onleft>1010</onleft>
                    <font>font12</font>
                    <align>center</align>
                    <aligny>center</aligny>
                    <textcolor>FFFFFFFF</textcolor>
                    <focusedcolor>FFFFFFFF</focusedcolor>
                    <texturefocus colordiffuse="55FFFFFF" border="10">script.plex/white-square-rounded.png</texturefocus>
                    <texturenofocus colordiffuse="22FFFFFF" border="10">script.plex/white-square-rounded.png</texturenofocus>
                    <label>K</label>
                </control>
            </control>
            <control type="group">
                <posx>350</posx>
                <posy>0</posy>
                <control type="button" id="1012">
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>64</width>
                    <height>{{ vscale(64) }}</height>
                    <onup>1006</onup>
                    <ondown>1018</ondown>
                    <onright>2100</onright>
                    <onleft>1011</onleft>
                    <font>font12</font>
                    <align>center</align>
                    <aligny>center</aligny>
                    <textcolor>FFFFFFFF</textcolor>
                    <focusedcolor>FFFFFFFF</focusedcolor>
                    <texturefocus colordiffuse="55FFFFFF" border="10">script.plex/white-square-rounded.png</texturefocus>
                    <texturenofocus colordiffuse="22FFFFFF" border="10">script.plex/white-square-rounded.png</texturenofocus>
                    <label>L</label>
                </control>
            </control>
        </control>
        <!-- BUTTONS ROW 3 -->
        <control type="group">
            <posx>0</posx>
            <posy>{{ vscale(140) }}</posy>
            <control type="group">
                <posx>0</posx>
                <posy>0</posy>
                <control type="button" id="1013">
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>64</width>
                    <height>{{ vscale(64) }}</height>
                    <onup>1007</onup>
                    <ondown>1019</ondown>
                    <onright>1014</onright>
                    <onleft>9000</onleft>
                    <font>font12</font>
                    <align>center</align>
                    <aligny>center</aligny>
                    <textcolor>FFFFFFFF</textcolor>
                    <focusedcolor>FFFFFFFF</focusedcolor>
                    <texturefocus colordiffuse="55FFFFFF" border="10">script.plex/white-square-rounded.png</texturefocus>
                    <texturenofocus colordiffuse="22FFFFFF" border="10">script.plex/white-square-rounded.png</texturenofocus>
                    <label>M</label>
                </control>
            </control>
            <control type="group">
                <posx>70</posx>
                <posy>0</posy>
                <control type="button" id="1014">
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>64</width>
                    <height>{{ vscale(64) }}</height>
                    <onup>1008</onup>
                    <ondown>1020</ondown>
                    <onright>1015</onright>
                    <onleft>1013</onleft>
                    <font>font12</font>
                    <align>center</align>
                    <aligny>center</aligny>
                    <textcolor>FFFFFFFF</textcolor>
                    <focusedcolor>FFFFFFFF</focusedcolor>
                    <texturefocus colordiffuse="55FFFFFF" border="10">script.plex/white-square-rounded.png</texturefocus>
                    <texturenofocus colordiffuse="22FFFFFF" border="10">script.plex/white-square-rounded.png</texturenofocus>
                    <label>N</label>
                </control>
            </control>
            <control type="group">
                <posx>140</posx>
                <posy>0</posy>
                <control type="button" id="1015">
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>64</width>
                    <height>{{ vscale(64) }}</height>
                    <onup>1009</onup>
                    <ondown>1021</ondown>
                    <onright>1016</onright>
                    <onleft>1014</onleft>
                    <font>font12</font>
                    <align>center</align>
                    <aligny>center</aligny>
                    <textcolor>FFFFFFFF</textcolor>
                    <focusedcolor>FFFFFFFF</focusedcolor>
                    <texturefocus colordiffuse="55FFFFFF" border="10">script.plex/white-square-rounded.png</texturefocus>
                    <texturenofocus colordiffuse="22FFFFFF" border="10">script.plex/white-square-rounded.png</texturenofocus>
                    <label>O</label>
                </control>
            </control>
            <control type="group">
                <posx>210</posx>
                <posy>0</posy>
                <control type="button" id="1016">
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>64</width>
                    <height>{{ vscale(64) }}</height>
                    <onup>1010</onup>
                    <ondown>1022</ondown>
                    <onright>1017</onright>
                    <onleft>1015</onleft>
                    <font>font12</font>
                    <align>center</align>
                    <aligny>center</aligny>
                    <textcolor>FFFFFFFF</textcolor>
                    <focusedcolor>FFFFFFFF</focusedcolor>
                    <texturefocus colordiffuse="55FFFFFF" border="10">script.plex/white-square-rounded.png</texturefocus>
                    <texturenofocus colordiffuse="22FFFFFF" border="10">script.plex/white-square-rounded.png</texturenofocus>
                    <label>P</label>
                </control>
            </control>
            <control type="group">
                <posx>280</posx>
                <posy>0</posy>
                <control type="button" id="1017">
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>64</width>
                    <height>{{ vscale(64) }}</height>
                    <onup>1011</onup>
                    <ondown>1023</ondown>
                    <onright>1018</onright>
                    <onleft>1016</onleft>
                    <font>font12</font>
                    <align>center</align>
                    <aligny>center</aligny>
                    <textcolor>FFFFFFFF</textcolor>
                    <focusedcolor>FFFFFFFF</focusedcolor>
                    <texturefocus colordiffuse="55FFFFFF" border="10">script.plex/white-square-rounded.png</texturefocus>
                    <texturenofocus colordiffuse="22FFFFFF" border="10">script.plex/white-square-rounded.png</texturenofocus>
                    <label>Q</label>
                </control>
            </control>
            <control type="group">
                <posx>350</posx>
                <posy>0</posy>
                <control type="button" id="1018">
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>64</width>
                    <height>{{ vscale(64) }}</height>
                    <onup>1012</onup>
                    <ondown>1024</ondown>
                    <onright>2100</onright>
                    <onleft>1017</onleft>
                    <font>font12</font>
                    <align>center</align>
                    <aligny>center</aligny>
                    <textcolor>FFFFFFFF</textcolor>
                    <focusedcolor>FFFFFFFF</focusedcolor>
                    <texturefocus colordiffuse="55FFFFFF" border="10">script.plex/white-square-rounded.png</texturefocus>
                    <texturenofocus colordiffuse="22FFFFFF" border="10">script.plex/white-square-rounded.png</texturenofocus>
                    <label>R</label>
                </control>
            </control>
        </control>
        <!-- BUTTONS ROW 4 -->
        <control type="group">
            <posx>0</posx>
            <posy>{{ vscale(210) }}</posy>
            <control type="group">
                <posx>0</posx>
                <posy>0</posy>
                <control type="button" id="1019">
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>64</width>
                    <height>{{ vscale(64) }}</height>
                    <onup>1013</onup>
                    <ondown>1025</ondown>
                    <onright>1020</onright>
                    <onleft>9000</onleft>
                    <font>font12</font>
                    <align>center</align>
                    <aligny>center</aligny>
                    <textcolor>FFFFFFFF</textcolor>
                    <focusedcolor>FFFFFFFF</focusedcolor>
                    <texturefocus colordiffuse="55FFFFFF" border="10">script.plex/white-square-rounded.png</texturefocus>
                    <texturenofocus colordiffuse="22FFFFFF" border="10">script.plex/white-square-rounded.png</texturenofocus>
                    <label>S</label>
                </control>
            </control>
            <control type="group">
                <posx>70</posx>
                <posy>0</posy>
                <control type="button" id="1020">
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>64</width>
                    <height>{{ vscale(64) }}</height>
                    <onup>1014</onup>
                    <ondown>1026</ondown>
                    <onright>1021</onright>
                    <onleft>1019</onleft>
                    <font>font12</font>
                    <align>center</align>
                    <aligny>center</aligny>
                    <textcolor>FFFFFFFF</textcolor>
                    <focusedcolor>FFFFFFFF</focusedcolor>
                    <texturefocus colordiffuse="55FFFFFF" border="10">script.plex/white-square-rounded.png</texturefocus>
                    <texturenofocus colordiffuse="22FFFFFF" border="10">script.plex/white-square-rounded.png</texturenofocus>
                    <label>T</label>
                </control>
            </control>
            <control type="group">
                <posx>140</posx>
                <posy>0</posy>
                <control type="button" id="1021">
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>64</width>
                    <height>{{ vscale(64) }}</height>
                    <onup>1015</onup>
                    <ondown>1027</ondown>
                    <onright>1022</onright>
                    <onleft>1020</onleft>
                    <font>font12</font>
                    <align>center</align>
                    <aligny>center</aligny>
                    <textcolor>FFFFFFFF</textcolor>
                    <focusedcolor>FFFFFFFF</focusedcolor>
                    <texturefocus colordiffuse="55FFFFFF" border="10">script.plex/white-square-rounded.png</texturefocus>
                    <texturenofocus colordiffuse="22FFFFFF" border="10">script.plex/white-square-rounded.png</texturenofocus>
                    <label>U</label>
                </control>
            </control>
            <control type="group">
                <posx>210</posx>
                <posy>0</posy>
                <control type="button" id="1022">
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>64</width>
                    <height>{{ vscale(64) }}</height>
                    <onup>1016</onup>
                    <ondown>1028</ondown>
                    <onright>1023</onright>
                    <onleft>1021</onleft>
                    <font>font12</font>
                    <align>center</align>
                    <aligny>center</aligny>
                    <textcolor>FFFFFFFF</textcolor>
                    <focusedcolor>FFFFFFFF</focusedcolor>
                    <texturefocus colordiffuse="55FFFFFF" border="10">script.plex/white-square-rounded.png</texturefocus>
                    <texturenofocus colordiffuse="22FFFFFF" border="10">script.plex/white-square-rounded.png</texturenofocus>
                    <label>V</label>
                </control>
            </control>
            <control type="group">
                <posx>280</posx>
                <posy>0</posy>
                <control type="button" id="1023">
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>64</width>
                    <height>{{ vscale(64) }}</height>
                    <onup>1017</onup>
                    <ondown>1029</ondown>
                    <onright>1024</onright>
                    <onleft>1022</onleft>
                    <font>font12</font>
                    <align>center</align>
                    <aligny>center</aligny>
                    <textcolor>FFFFFFFF</textcolor>
                    <focusedcolor>FFFFFFFF</focusedcolor>
                    <texturefocus colordiffuse="55FFFFFF" border="10">script.plex/white-square-rounded.png</texturefocus>
                    <texturenofocus colordiffuse="22FFFFFF" border="10">script.plex/white-square-rounded.png</texturenofocus>
                    <label>W</label>
                </control>
            </control>
            <control type="group">
                <posx>350</posx>
                <posy>0</posy>
                <control type="button" id="1024">
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>64</width>
                    <height>{{ vscale(64) }}</height>
                    <onup>1018</onup>
                    <ondown>1030</ondown>
                    <onright>2100</onright>
                    <onleft>1023</onleft>
                    <font>font12</font>
                    <align>center</align>
                    <aligny>center</aligny>
                    <textcolor>FFFFFFFF</textcolor>
                    <focusedcolor>FFFFFFFF</focusedcolor>
                    <texturefocus colordiffuse="55FFFFFF" border="10">script.plex/white-square-rounded.png</texturefocus>
                    <texturenofocus colordiffuse="22FFFFFF" border="10">script.plex/white-square-rounded.png</texturenofocus>
                    <label>X</label>
                </control>
            </control>
        </control>
        <!-- BUTTONS ROW 5 -->
        <control type="group">
            <posx>0</posx>
            <posy>{{ vscale(280) }}</posy>
            <control type="group">
                <posx>0</posx>
                <posy>0</posy>
                <control type="button" id="1025">
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>64</width>
                    <height>{{ vscale(64) }}</height>
                    <onup>1019</onup>
                    <ondown>1031</ondown>
                    <onright>1026</onright>
                    <onleft>9000</onleft>
                    <font>font12</font>
                    <align>center</align>
                    <aligny>center</aligny>
                    <textcolor>FFFFFFFF</textcolor>
                    <focusedcolor>FFFFFFFF</focusedcolor>
                    <texturefocus colordiffuse="55FFFFFF" border="10">script.plex/white-square-rounded.png</texturefocus>
                    <texturenofocus colordiffuse="22FFFFFF" border="10">script.plex/white-square-rounded.png</texturenofocus>
                    <label>Y</label>
                </control>
            </control>
            <control type="group">
                <posx>70</posx>
                <posy>0</posy>
                <control type="button" id="1026">
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>64</width>
                    <height>{{ vscale(64) }}</height>
                    <onup>1020</onup>
                    <ondown>1032</ondown>
                    <onright>1027</onright>
                    <onleft>1025</onleft>
                    <font>font12</font>
                    <align>center</align>
                    <aligny>center</aligny>
                    <textcolor>FFFFFFFF</textcolor>
                    <focusedcolor>FFFFFFFF</focusedcolor>
                    <texturefocus colordiffuse="55FFFFFF" border="10">script.plex/white-square-rounded.png</texturefocus>
                    <texturenofocus colordiffuse="22FFFFFF" border="10">script.plex/white-square-rounded.png</texturenofocus>
                    <label>Z</label>
                </control>
            </control>
            <control type="group">
                <posx>140</posx>
                <posy>0</posy>
                <control type="button" id="1027">
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>64</width>
                    <height>{{ vscale(64) }}</height>
                    <onup>1021</onup>
                    <ondown>1033</ondown>
                    <onright>1028</onright>
                    <onleft>1026</onleft>
                    <font>font12</font>
                    <align>center</align>
                    <aligny>center</aligny>
                    <textcolor>FFFFFFFF</textcolor>
                    <focusedcolor>FFFFFFFF</focusedcolor>
                    <texturefocus colordiffuse="55FFFFFF" border="10">script.plex/white-square-rounded.png</texturefocus>
                    <texturenofocus colordiffuse="22FFFFFF" border="10">script.plex/white-square-rounded.png</texturenofocus>
                    <label>0[B][/B]</label>
                </control>
            </control>
            <control type="group">
                <posx>210</posx>
                <posy>0</posy>
                <control type="button" id="1028">
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>64</width>
                    <height>{{ vscale(64) }}</height>
                    <onup>1022</onup>
                    <ondown>1034</ondown>
                    <onright>1029</onright>
                    <onleft>1027</onleft>
                    <font>font12</font>
                    <align>center</align>
                    <aligny>center</aligny>
                    <textcolor>FFFFFFFF</textcolor>
                    <focusedcolor>FFFFFFFF</focusedcolor>
                    <texturefocus colordiffuse="55FFFFFF" border="10">script.plex/white-square-rounded.png</texturefocus>
                    <texturenofocus colordiffuse="22FFFFFF" border="10">script.plex/white-square-rounded.png</texturenofocus>
                    <label>1[B][/B]</label>
                </control>
            </control>
            <control type="group">
                <posx>280</posx>
                <posy>0</posy>
                <control type="button" id="1029">
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>64</width>
                    <height>{{ vscale(64) }}</height>
                    <onup>1023</onup>
                    <ondown>1035</ondown>
                    <onright>1030</onright>
                    <onleft>1028</onleft>
                    <font>font12</font>
                    <align>center</align>
                    <aligny>center</aligny>
                    <textcolor>FFFFFFFF</textcolor>
                    <focusedcolor>FFFFFFFF</focusedcolor>
                    <texturefocus colordiffuse="55FFFFFF" border="10">script.plex/white-square-rounded.png</texturefocus>
                    <texturenofocus colordiffuse="22FFFFFF" border="10">script.plex/white-square-rounded.png</texturenofocus>
                    <label>2[B][/B]</label>
                </control>
            </control>
            <control type="group">
                <posx>350</posx>
                <posy>0</posy>
                <control type="button" id="1030">
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>64</width>
                    <height>{{ vscale(64) }}</height>
                    <onup>1024</onup>
                    <ondown>1036</ondown>
                    <onright>2100</onright>
                    <onleft>1029</onleft>
                    <font>font12</font>
                    <align>center</align>
                    <aligny>center</aligny>
                    <textcolor>FFFFFFFF</textcolor>
                    <focusedcolor>FFFFFFFF</focusedcolor>
                    <texturefocus colordiffuse="55FFFFFF" border="10">script.plex/white-square-rounded.png</texturefocus>
                    <texturenofocus colordiffuse="22FFFFFF" border="10">script.plex/white-square-rounded.png</texturenofocus>
                    <label>3[B][/B]</label>
                </control>
            </control>
        </control>
        <!-- BUTTONS ROW 6 -->
        <control type="group">
            <posx>0</posx>
            <posy>{{ vscale(350) }}</posy>
            <control type="group">
                <posx>0</posx>
                <posy>0</posy>
                <control type="button" id="1031">
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>64</width>
                    <height>{{ vscale(64) }}</height>
                    <onup>1025</onup>
                    <ondown>951</ondown>
                    <onright>1032</onright>
                    <onleft>9000</onleft>
                    <font>font12</font>
                    <align>center</align>
                    <aligny>center</aligny>
                    <textcolor>FFFFFFFF</textcolor>
                    <focusedcolor>FFFFFFFF</focusedcolor>
                    <texturefocus colordiffuse="55FFFFFF" border="10">script.plex/white-square-rounded.png</texturefocus>
                    <texturenofocus colordiffuse="22FFFFFF" border="10">script.plex/white-square-rounded.png</texturenofocus>
                    <label>4[B][/B]</label>
                </control>
            </control>
            <control type="group">
                <posx>70</posx>
                <posy>0</posy>
                <control type="button" id="1032">
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>64</width>
                    <height>{{ vscale(64) }}</height>
                    <onup>1026</onup>
                    <ondown>951</ondown>
                    <onright>1033</onright>
                    <onleft>1031</onleft>
                    <font>font12</font>
                    <align>center</align>
                    <aligny>center</aligny>
                    <textcolor>FFFFFFFF</textcolor>
                    <focusedcolor>FFFFFFFF</focusedcolor>
                    <texturefocus colordiffuse="55FFFFFF" border="10">script.plex/white-square-rounded.png</texturefocus>
                    <texturenofocus colordiffuse="22FFFFFF" border="10">script.plex/white-square-rounded.png</texturenofocus>
                    <label>5[B][/B]</label>
                </control>
            </control>
            <control type="group">
                <posx>140</posx>
                <posy>0</posy>
                <control type="button" id="1033">
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>64</width>
                    <height>{{ vscale(64) }}</height>
                    <onup>1027</onup>
                    <ondown>952</ondown>
                    <onright>1034</onright>
                    <onleft>1032</onleft>
                    <font>font12</font>
                    <align>center</align>
                    <aligny>center</aligny>
                    <textcolor>FFFFFFFF</textcolor>
                    <focusedcolor>FFFFFFFF</focusedcolor>
                    <texturefocus colordiffuse="55FFFFFF" border="10">script.plex/white-square-rounded.png</texturefocus>
                    <texturenofocus colordiffuse="22FFFFFF" border="10">script.plex/white-square-rounded.png</texturenofocus>
                    <label>6[B][/B]</label>
                </control>
            </control>
            <control type="group">
                <posx>210</posx>
                <posy>0</posy>
                <control type="button" id="1034">
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>64</width>
                    <height>{{ vscale(64) }}</height>
                    <onup>1028</onup>
                    <ondown>952</ondown>
                    <onright>1035</onright>
                    <onleft>1033</onleft>
                    <font>font12</font>
                    <align>center</align>
                    <aligny>center</aligny>
                    <textcolor>FFFFFFFF</textcolor>
                    <focusedcolor>FFFFFFFF</focusedcolor>
                    <texturefocus colordiffuse="55FFFFFF" border="10">script.plex/white-square-rounded.png</texturefocus>
                    <texturenofocus colordiffuse="22FFFFFF" border="10">script.plex/white-square-rounded.png</texturenofocus>
                    <label>7[B][/B]</label>
                </control>
            </control>
            <control type="group">
                <posx>280</posx>
                <posy>0</posy>
                <control type="button" id="1035">
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>64</width>
                    <height>{{ vscale(64) }}</height>
                    <onup>1029</onup>
                    <ondown>953</ondown>
                    <onright>1036</onright>
                    <onleft>1034</onleft>
                    <font>font12</font>
                    <align>center</align>
                    <aligny>center</aligny>
                    <textcolor>FFFFFFFF</textcolor>
                    <focusedcolor>FFFFFFFF</focusedcolor>
                    <texturefocus colordiffuse="55FFFFFF" border="10">script.plex/white-square-rounded.png</texturefocus>
                    <texturenofocus colordiffuse="22FFFFFF" border="10">script.plex/white-square-rounded.png</texturenofocus>
                    <label>8[B][/B]</label>
                </control>
            </control>
            <control type="group">
                <posx>350</posx>
                <posy>0</posy>
                <control type="button" id="1036">
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>64</width>
                    <height>{{ vscale(64) }}</height>
                    <onup>1030</onup>
                    <ondown>953</ondown>
                    <onright>2100</onright>
                    <onleft>1035</onleft>
                    <font>font12</font>
                    <align>center</align>
                    <aligny>center</aligny>
                    <textcolor>FFFFFFFF</textcolor>
                    <focusedcolor>FFFFFFFF</focusedcolor>
                    <texturefocus colordiffuse="55FFFFFF" border="10">script.plex/white-square-rounded.png</texturefocus>
                    <texturenofocus colordiffuse="22FFFFFF" border="10">script.plex/white-square-rounded.png</texturenofocus>
                    <label>9[B][/B]</label>
                </control>
            </control>
        </control>
    </control>

    <!-- DELETE-ETC -->
    <control type="group" id="950">
        <posx>60</posx>
        <posy>{{ vscale(579) }}</posy>
        <width>414</width>
        <height>{{ vscale(60) }}</height>
        <visible>String.IsEmpty(Window.Property(hide.kbd))</visible>

        <control type="group">
            <posx>0</posx>
            <posy>0</posy>
            <control type="button" id="951">
                <posx>0</posx>
                <posy>0</posy>
                <width>134</width>
                <height>{{ vscale(60) }}</height>
                <onleft>9000</onleft>
                <onright>952</onright>
                <ondown>2050</ondown>
                <onup>1031</onup>
                <font>font12</font>
                <align>center</align>
                <aligny>center</aligny>
                <textcolor>FFFFFFFF</textcolor>
                <focusedcolor>FFFFFFFF</focusedcolor>
                <texturefocus colordiffuse="55FFFFFF" border="10">script.plex/white-square-rounded.png</texturefocus>
                <texturenofocus colordiffuse="22FFFFFF" border="10">script.plex/white-square-rounded.png</texturenofocus>
                <label> </label>
            </control>
            <!-- its icon: the button's own label is blank. 74x64 art at 40 high, not the 24 the others
                 are, centred: its 3px source stroke at the others' 1.9px on screen -->
            <control type="image">
                <posx>43.875</posx>
                <posy>{{ vscale(10) }}</posy>
                <width>46.25</width>
                <height>{{ vscale(40) }}</height>
                <texture colordiffuse="FFFFFFFF">script.plex/buttons/keyboard/delete.png</texture>
            </control>
        </control>
        <control type="group">
            <posx>140</posx>
            <posy>0</posy>
            <control type="button" id="952">
                <posx>0</posx>
                <posy>0</posy>
                <width>134</width>
                <height>{{ vscale(60) }}</height>
                <onleft>951</onleft>
                <onright>953</onright>
                <ondown>2050</ondown>
                <onup>1033</onup>
                <font>font12</font>
                <align>center</align>
                <aligny>center</aligny>
                <textcolor>FFFFFFFF</textcolor>
                <focusedcolor>FFFFFFFF</focusedcolor>
                <texturefocus colordiffuse="55FFFFFF" border="10">script.plex/white-square-rounded.png</texturefocus>
                <texturenofocus colordiffuse="22FFFFFF" border="10">script.plex/white-square-rounded.png</texturenofocus>
                <label> </label>
            </control>
            <!-- its icon: the button's own label is blank -->
            <control type="image">
                <posx>55</posx>
                <posy>{{ vscale(18) }}</posy>
                <width>24</width>
                <height>{{ vscale(24) }}</height>
                <texture colordiffuse="FFFFFFFF">script.plex/buttons/keyboard/space.png</texture>
            </control>
        </control>
        <control type="group">
            <posx>280</posx>
            <posy>0</posy>
            <control type="button" id="953">
                <posx>0</posx>
                <posy>0</posy>
                <width>134</width>
                <height>{{ vscale(60) }}</height>
                <onleft>952</onleft>
                <onright>2100</onright>
                <ondown>2050</ondown>
                <onup>1036</onup>
                <font>font12</font>
                <align>center</align>
                <aligny>center</aligny>
                <textcolor>FFFFFFFF</textcolor>
                <focusedcolor>FFFFFFFF</focusedcolor>
                <texturefocus colordiffuse="55FFFFFF" border="10">script.plex/white-square-rounded.png</texturefocus>
                <texturenofocus colordiffuse="22FFFFFF" border="10">script.plex/white-square-rounded.png</texturenofocus>
                <label> </label>
            </control>
            <!-- its icon: the button's own label is blank -->
            <control type="image">
                <posx>55</posx>
                <posy>{{ vscale(18) }}</posy>
                <width>24</width>
                <height>{{ vscale(24) }}</height>
                <texture colordiffuse="FFFFFFFF">script.plex/buttons/keyboard/clear.png</texture>
            </control>
        </control>
    </control>
</control>

<!-- The type buttons, above the results and level with their left edge: shown once a search has
     found something (has.results, SearchWindow.showResults() - whatever the type chosen, so one
     with no results can still be changed). -->
<control type="group">
    <visible>!String.IsEmpty(Window.Property(has.results))</visible>
    <posx>604</posx>
    <posy>{{ vscale(20) }}</posy>
    <width>459</width>
    <height>{{ vscale(87) }}</height>
    <!-- SECTIONS: the type buttons (SearchWindow.SECTION_BUTTONS), six across - All, then
         an icon each for Movies, Shows, Music, Photos and People. Each a rounded tile in the
         Libraries picker's tracking grey at rest (script-plex-card_list.xml.tpl), as the keys
         are, and focused two steps brighter than its focus grey (55 against 33 - the user,
         2026-10-07); the selected type's label or icon in the sidebar's active orange. -->
    <control type="group">
        <posx>0</posx>
        <posy>{{ vscale(13) }}</posy>
        <width>459</width>
        <height>{{ vscale(60) }}</height>

        <control type="group">
            <posx>0</posx>
            <posy>0</posy>
            <control type="image">
                <visible>!Control.HasFocus(911)</visible>
                <posx>0</posx>
                <posy>0</posy>
                <width>74</width>
                <height>{{ vscale(60) }}</height>
                <texture colordiffuse="22FFFFFF" border="10">script.plex/white-square-rounded.png</texture>
            </control>
            <control type="group">
                <control type="image">
                    <visible>Control.HasFocus(911)</visible>
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>74</width>
                    <height>{{ vscale(60) }}</height>
                    <texture colordiffuse="55FFFFFF" border="10">script.plex/white-square-rounded.png</texture>
                </control>
                <control type="label">
                    <visible>!String.IsEqual(Window.Property(search.section),all)</visible>
                    <scroll>false</scroll>
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>74</width>
                    <height>{{ vscale(60) }}</height>
                    <font>font12</font>
                    <align>center</align>
                    <aligny>center</aligny>
                    <textcolor>FFFFFFFF</textcolor>
                    <label>$ADDON[script.plexmod 32345]</label>
                </control>
                <control type="label">
                    <visible>String.IsEqual(Window.Property(search.section),all)</visible>
                    <scroll>false</scroll>
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>74</width>
                    <height>{{ vscale(60) }}</height>
                    <font>font12</font>
                    <align>center</align>
                    <aligny>center</aligny>
                    <textcolor>FFE5A00D</textcolor>
                    <label>$ADDON[script.plexmod 32345]</label>
                </control>
            </control>
        </control>
        <control type="group">
            <posx>77</posx>
            <posy>0</posy>
            <control type="image">
                <visible>!Control.HasFocus(912)</visible>
                <posx>0</posx>
                <posy>0</posy>
                <width>74</width>
                <height>{{ vscale(60) }}</height>
                <texture colordiffuse="22FFFFFF" border="10">script.plex/white-square-rounded.png</texture>
            </control>
            <control type="group">
                <control type="image">
                    <visible>Control.HasFocus(912)</visible>
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>74</width>
                    <height>{{ vscale(60) }}</height>
                    <texture colordiffuse="55FFFFFF" border="10">script.plex/white-square-rounded.png</texture>
                </control>
                <control type="image">
                    <visible>!String.IsEqual(Window.Property(search.section),movie)</visible>
                    <posx>25</posx>
                    <posy>{{ vscale(18) }}</posy>
                    <width>24</width>
                    <height>{{ vscale(24) }}</height>
                    <texture colordiffuse="FFFFFFFF">script.plex/home/type/movie.png</texture>
                </control>
                <control type="image">
                    <visible>String.IsEqual(Window.Property(search.section),movie)</visible>
                    <posx>25</posx>
                    <posy>{{ vscale(18) }}</posy>
                    <width>24</width>
                    <height>{{ vscale(24) }}</height>
                    <texture colordiffuse="FFE5A00D">script.plex/home/type/movie.png</texture>
                </control>
            </control>
        </control>
        <control type="group">
            <posx>154</posx>
            <posy>0</posy>
            <control type="image">
                <visible>!Control.HasFocus(913)</visible>
                <posx>0</posx>
                <posy>0</posy>
                <width>74</width>
                <height>{{ vscale(60) }}</height>
                <texture colordiffuse="22FFFFFF" border="10">script.plex/white-square-rounded.png</texture>
            </control>
            <control type="group">
                <control type="image">
                    <visible>Control.HasFocus(913)</visible>
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>74</width>
                    <height>{{ vscale(60) }}</height>
                    <texture colordiffuse="55FFFFFF" border="10">script.plex/white-square-rounded.png</texture>
                </control>
                <control type="image">
                    <visible>!String.IsEqual(Window.Property(search.section),show)</visible>
                    <posx>25</posx>
                    <posy>{{ vscale(18) }}</posy>
                    <width>24</width>
                    <height>{{ vscale(24) }}</height>
                    <texture colordiffuse="FFFFFFFF">script.plex/home/type/show.png</texture>
                </control>
                <control type="image">
                    <visible>String.IsEqual(Window.Property(search.section),show)</visible>
                    <posx>25</posx>
                    <posy>{{ vscale(18) }}</posy>
                    <width>24</width>
                    <height>{{ vscale(24) }}</height>
                    <texture colordiffuse="FFE5A00D">script.plex/home/type/show.png</texture>
                </control>
            </control>
        </control>
        <control type="group">
            <posx>231</posx>
            <posy>0</posy>
            <control type="image">
                <visible>!Control.HasFocus(914)</visible>
                <posx>0</posx>
                <posy>0</posy>
                <width>74</width>
                <height>{{ vscale(60) }}</height>
                <texture colordiffuse="22FFFFFF" border="10">script.plex/white-square-rounded.png</texture>
            </control>
            <control type="group">
                <control type="image">
                    <visible>Control.HasFocus(914)</visible>
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>74</width>
                    <height>{{ vscale(60) }}</height>
                    <texture colordiffuse="55FFFFFF" border="10">script.plex/white-square-rounded.png</texture>
                </control>
                <control type="image">
                    <visible>!String.IsEqual(Window.Property(search.section),artist)</visible>
                    <posx>25</posx>
                    <posy>{{ vscale(18) }}</posy>
                    <width>24</width>
                    <height>{{ vscale(24) }}</height>
                    <texture colordiffuse="FFFFFFFF">script.plex/home/type/artist.png</texture>
                </control>
                <control type="image">
                    <visible>String.IsEqual(Window.Property(search.section),artist)</visible>
                    <posx>25</posx>
                    <posy>{{ vscale(18) }}</posy>
                    <width>24</width>
                    <height>{{ vscale(24) }}</height>
                    <texture colordiffuse="FFE5A00D">script.plex/home/type/artist.png</texture>
                </control>
            </control>
        </control>
        <control type="group">
            <posx>308</posx>
            <posy>0</posy>
            <control type="image">
                <visible>!Control.HasFocus(915)</visible>
                <posx>0</posx>
                <posy>0</posy>
                <width>74</width>
                <height>{{ vscale(60) }}</height>
                <texture colordiffuse="22FFFFFF" border="10">script.plex/white-square-rounded.png</texture>
            </control>
            <control type="group">
                <control type="image">
                    <visible>Control.HasFocus(915)</visible>
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>74</width>
                    <height>{{ vscale(60) }}</height>
                    <texture colordiffuse="55FFFFFF" border="10">script.plex/white-square-rounded.png</texture>
                </control>
                <control type="image">
                    <visible>!String.IsEqual(Window.Property(search.section),photo)</visible>
                    <posx>25</posx>
                    <posy>{{ vscale(18) }}</posy>
                    <width>24</width>
                    <height>{{ vscale(24) }}</height>
                    <texture colordiffuse="FFFFFFFF">script.plex/home/type/photo.png</texture>
                </control>
                <control type="image">
                    <visible>String.IsEqual(Window.Property(search.section),photo)</visible>
                    <posx>25</posx>
                    <posy>{{ vscale(18) }}</posy>
                    <width>24</width>
                    <height>{{ vscale(24) }}</height>
                    <texture colordiffuse="FFE5A00D">script.plex/home/type/photo.png</texture>
                </control>
            </control>
        </control>
        <control type="group">
            <posx>385</posx>
            <posy>0</posy>
            <control type="image">
                <visible>!Control.HasFocus(916)</visible>
                <posx>0</posx>
                <posy>0</posy>
                <width>74</width>
                <height>{{ vscale(60) }}</height>
                <texture colordiffuse="22FFFFFF" border="10">script.plex/white-square-rounded.png</texture>
            </control>
            <control type="group">
                <control type="image">
                    <visible>Control.HasFocus(916)</visible>
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>74</width>
                    <height>{{ vscale(60) }}</height>
                    <texture colordiffuse="55FFFFFF" border="10">script.plex/white-square-rounded.png</texture>
                </control>
                <control type="image">
                    <visible>!String.IsEqual(Window.Property(search.section),people)</visible>
                    <posx>25</posx>
                    <posy>{{ vscale(18) }}</posy>
                    <width>24</width>
                    <height>{{ vscale(24) }}</height>
                    <texture colordiffuse="FFFFFFFF">script.plex/home/type/person.png</texture>
                </control>
                <control type="image">
                    <visible>String.IsEqual(Window.Property(search.section),people)</visible>
                    <posx>25</posx>
                    <posy>{{ vscale(18) }}</posy>
                    <width>24</width>
                    <height>{{ vscale(24) }}</height>
                    <texture colordiffuse="FFE5A00D">script.plex/home/type/person.png</texture>
                </control>
            </control>
        </control>

        <control type="group" id="900">
            <defaultcontrol>911</defaultcontrol>
            <control type="group">
                <posx>0</posx>
                <posy>0</posy>
                <control type="button" id="911">
                    <hitrect x="0" y="0" w="74" h="60" />
                    <posx>-40</posx>
                    <posy>{{ vscale(-40) }}</posy>
                    <width>154</width>
                    <height>{{ vscale(140) }}</height>
                    <onleft>899</onleft>
                    <onright>912</onright>
                    <ondown>2100</ondown>
                    <texturefocus>-</texturefocus>
                    <texturenofocus>-</texturenofocus>
                    <label> </label>
                </control>
            </control>
            <control type="group">
                <posx>77</posx>
                <posy>0</posy>
                <control type="button" id="912">
                    <hitrect x="0" y="0" w="74" h="60" />
                    <posx>-40</posx>
                    <posy>{{ vscale(-40) }}</posy>
                    <width>154</width>
                    <height>{{ vscale(140) }}</height>
                    <onleft>911</onleft>
                    <onright>913</onright>
                    <ondown>2100</ondown>
                    <texturefocus>-</texturefocus>
                    <texturenofocus>-</texturenofocus>
                    <label> </label>
                </control>
            </control>
            <control type="group">
                <posx>154</posx>
                <posy>0</posy>
                <control type="button" id="913">
                    <hitrect x="0" y="0" w="74" h="60" />
                    <posx>-40</posx>
                    <posy>{{ vscale(-40) }}</posy>
                    <width>154</width>
                    <height>{{ vscale(140) }}</height>
                    <onleft>912</onleft>
                    <onright>914</onright>
                    <ondown>2100</ondown>
                    <texturefocus>-</texturefocus>
                    <texturenofocus>-</texturenofocus>
                    <label> </label>
                </control>
            </control>
            <control type="group">
                <posx>231</posx>
                <posy>0</posy>
                <control type="button" id="914">
                    <hitrect x="0" y="0" w="74" h="60" />
                    <posx>-40</posx>
                    <posy>{{ vscale(-40) }}</posy>
                    <width>154</width>
                    <height>{{ vscale(140) }}</height>
                    <onleft>913</onleft>
                    <onright>915</onright>
                    <ondown>2100</ondown>
                    <texturefocus>-</texturefocus>
                    <texturenofocus>-</texturenofocus>
                    <label> </label>
                </control>
            </control>
            <control type="group">
                <posx>308</posx>
                <posy>0</posy>
                <control type="button" id="915">
                    <hitrect x="0" y="0" w="74" h="60" />
                    <posx>-40</posx>
                    <posy>{{ vscale(-40) }}</posy>
                    <width>154</width>
                    <height>{{ vscale(140) }}</height>
                    <onleft>914</onleft>
                    <onright>916</onright>
                    <ondown>2100</ondown>
                    <texturefocus>-</texturefocus>
                    <texturenofocus>-</texturenofocus>
                    <label> </label>
                </control>
            </control>
            <control type="group">
                <posx>385</posx>
                <posy>0</posy>
                <control type="button" id="916">
                    <hitrect x="0" y="0" w="74" h="60" />
                    <posx>-40</posx>
                    <posy>{{ vscale(-40) }}</posy>
                    <width>154</width>
                    <height>{{ vscale(140) }}</height>
                    <onleft>915</onleft>
                    <ondown>2100</ondown>
                    <texturefocus>-</texturefocus>
                    <texturenofocus>-</texturenofocus>
                    <label> </label>
                </control>
            </control>
        </control>
    </control>
</control>

<!-- STATUS, right of the type buttons, 40 clear of them and level with their middle (the
     buttons 60 high at 33): "Searching..." with its spinner while a search is out (searching,
     SearchWindow._search()), else a server whose results are missing (search.searchServers()):
     "Oscar isn't responding". Placed for the buttons whether or not they show. -->
<control type="group">
    <animation effect="fade" start="0" end="100" time="100" condition="!String.IsEmpty(Window.Property(searching))">Visible</animation>
    <visible>!String.IsEmpty(Window.Property(searching))</visible>
    <posx>1103</posx>
    <posy>{{ vscale(33) }}</posy>
    <!-- turning as Estuary's spinners do (DialogBusy.xml): a looping animation that's always on,
         round the image's own middle (center="auto"). It was a Visible animation round
         center="19.5,19.5", which is in the parent's coordinates, not the image's - off its
         middle once moved, so it wobbled - and started only by the image's own visibility
         changing; it didn't turn at all on the AM6B. -->
    <control type="image">
        <animation effect="rotate" start="0" end="-360" center="auto" time="1000" loop="true" reversible="false" condition="true">Conditional</animation>
        <posx>0</posx>
        <posy>{{ vscale(10.5) }}</posy>
        <width>39</width>
        <height>{{ vscale(39) }}</height>
        <texture colordiffuse="FFE5A00D">script.plex/indicators/spinner.png</texture>
    </control>
    <control type="label">
        <scroll>false</scroll>
        <posx>54</posx>
        <posy>0</posy>
        <width>663</width>
        <height>{{ vscale(60) }}</height>
        <font>font12</font>
        <aligny>center</aligny>
        <textcolor>FFFFFFFF</textcolor>
        <label>$ADDON[script.plexmod 32434]</label>
    </control>
</control>
<control type="label">
    <visible>!String.IsEmpty(Window.Property(search.note)) + String.IsEmpty(Window.Property(searching))</visible>
    <scroll>false</scroll>
    <posx>1103</posx>
    <posy>{{ vscale(33) }}</posy>
    <width>717</width>
    <height>{{ vscale(60) }}</height>
    <font>font10</font>
    <aligny>center</aligny>
    <textcolor>99FFFFFF</textcolor>
    <label>$INFO[Window.Property(search.note)]</label>
</control>

<!-- NO RESULTS: where the grid would be, as a library grid's own empty message is
     (library.xml.tpl's no_content): centred across the cards, at its height and in its type. -->
<control type="label">
    <visible>!String.IsEmpty(Window.Property(no.results)) + String.IsEmpty(Window.Property(searching))</visible>
    <scroll>false</scroll>
    <posx>604</posx>
    <posy>{{ vscale(465) }}</posy>
    <width>1216</width>
    <height>{{ vscale(35) }}</height>
    <font>font13</font>
    <align>center</align>
    <textcolor>FFFFFFFF</textcolor>
    <label>[B]$ADDON[script.plexmod 32435][/B]</label>
</control>

<!-- RESULTS: one grid, three cards across (SearchWindow.showHubs()), 40 in from where the results
     begin and from the screen's edge, 20 between. Each card (392x220) in a darker grey than the
     keys: the art 133 wide, 10 in from its left and centred top to bottom - a poster 10 clear of
     the card's top and bottom - its height the art's own (art.type: poster, square, 16:9 or
     round); right of it, at 151 and to 6 from the card's edge, the title, an episode's show,
     the type line (SearchWindow.typeLine()) and, on a multi-server account, the server. The
     gold ring round the focused card, 3 out - the panel starts 3
     before the first card for it. -->
<control type="panel" id="2100">
    <posx>601</posx>
    <posy>{{ vscale(110) }}</posy>
    <width>1236</width>
    <height>{{ vscale(960) }}</height>
    <onleft>899</onleft>
    <onup>900</onup>
    <orientation>vertical</orientation>
    <scrolltime tween="quadratic" easing="out">200</scrolltime>
    <preloaditems>2</preloaditems>
    <itemlayout width="412" height="{{ vscale(240) }}">
        <control type="group">
            <posx>3</posx>
            <posy>3</posy>
            <control type="group">
                <control type="image">
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>392</width>
                    <height>{{ vscale(220) }}</height>
                    <texture colordiffuse="12FFFFFF" border="10">script.plex/white-square-rounded.png</texture>
                </control>
                <control type="image">
                    <visible>String.IsEqual(ListItem.Property(art.type),poster)</visible>
                    <posx>10</posx>
                    <posy>{{ vscale(10) }}</posy>
                    <width>133</width>
                    <height>{{ vscale(200) }}</height>
                    <texture diffuse="script.plex/masks/poster-mask.png">$INFO[ListItem.Property(thumb.fallback)]</texture>
                    <aspectratio scalediffuse="false">scale</aspectratio>
                </control>
                <control type="image">
                    <visible>String.IsEqual(ListItem.Property(art.type),poster)</visible>
                    <posx>10</posx>
                    <posy>{{ vscale(10) }}</posy>
                    <width>133</width>
                    <height>{{ vscale(200) }}</height>
                    <texture background="true" diffuse="script.plex/masks/poster-mask.png">$INFO[ListItem.Thumb]</texture>
                    <aspectratio scalediffuse="false">scale</aspectratio>
                </control>
                <control type="image">
                    <visible>String.IsEqual(ListItem.Property(art.type),square)</visible>
                    <posx>10</posx>
                    <posy>{{ vscale(43) }}</posy>
                    <width>133</width>
                    <height>{{ vscale(133) }}</height>
                    <texture diffuse="script.plex/masks/square-mask.png">$INFO[ListItem.Property(thumb.fallback)]</texture>
                    <aspectratio scalediffuse="false">scale</aspectratio>
                </control>
                <control type="image">
                    <visible>String.IsEqual(ListItem.Property(art.type),square)</visible>
                    <posx>10</posx>
                    <posy>{{ vscale(43) }}</posy>
                    <width>133</width>
                    <height>{{ vscale(133) }}</height>
                    <texture background="true" diffuse="script.plex/masks/square-mask.png">$INFO[ListItem.Thumb]</texture>
                    <aspectratio scalediffuse="false">scale</aspectratio>
                </control>
                <control type="image">
                    <visible>String.IsEqual(ListItem.Property(art.type),ar16x9)</visible>
                    <posx>10</posx>
                    <posy>{{ vscale(72) }}</posy>
                    <width>133</width>
                    <height>{{ vscale(75) }}</height>
                    <texture diffuse="script.plex/masks/ar16x9-mask.png">$INFO[ListItem.Property(thumb.fallback)]</texture>
                    <aspectratio scalediffuse="false">scale</aspectratio>
                </control>
                <control type="image">
                    <visible>String.IsEqual(ListItem.Property(art.type),ar16x9)</visible>
                    <posx>10</posx>
                    <posy>{{ vscale(72) }}</posy>
                    <width>133</width>
                    <height>{{ vscale(75) }}</height>
                    <texture background="true" diffuse="script.plex/masks/ar16x9-mask.png">$INFO[ListItem.Thumb]</texture>
                    <aspectratio scalediffuse="false">scale</aspectratio>
                </control>
                <control type="image">
                    <visible>String.IsEqual(ListItem.Property(art.type),circle)</visible>
                    <posx>10</posx>
                    <posy>{{ vscale(43) }}</posy>
                    <width>133</width>
                    <height>{{ vscale(133) }}</height>
                    <texture diffuse="script.plex/masks/role.png">$INFO[ListItem.Property(thumb.fallback)]</texture>
                    <aspectratio scalediffuse="false" aligny="top">scale</aspectratio>
                </control>
                <control type="image">
                    <visible>String.IsEqual(ListItem.Property(art.type),circle)</visible>
                    <posx>10</posx>
                    <posy>{{ vscale(43) }}</posy>
                    <width>133</width>
                    <height>{{ vscale(133) }}</height>
                    <texture background="true" diffuse="script.plex/masks/role.png">$INFO[ListItem.Thumb]</texture>
                    <aspectratio scalediffuse="false" aligny="top">scale</aspectratio>
                </control>
                <control type="group">
                    <visible>String.IsEmpty(ListItem.Property(subtitle)) + !String.IsEmpty(ListItem.Property(server.name))</visible>
                    <posx>151</posx>
                    <posy>{{ vscale(69) }}</posy>
                    <control type="label">
                        <scroll>false</scroll>
                        <posx>0</posx>
                        <posy>{{ vscale(0) }}</posy>
                        <width>235</width>
                        <height>{{ vscale(32) }}</height>
                        <font>font10</font>
                        <align>left</align>
                        <aligny>center</aligny>
                        <textcolor>FFFFFFFF</textcolor>
                        <label>$INFO[ListItem.Label]</label>
                    </control>
                    <control type="label">
                        <scroll>false</scroll>
                        <posx>0</posx>
                        <posy>{{ vscale(32) }}</posy>
                        <width>235</width>
                        <height>{{ vscale(28) }}</height>
                        <font>font8</font>
                        <align>left</align>
                        <aligny>center</aligny>
                        <textcolor>AAFFFFFF</textcolor>
                        <label>$INFO[ListItem.Label2]</label>
                    </control>
                    <control type="label">
                        <scroll>false</scroll>
                        <posx>0</posx>
                        <posy>{{ vscale(60) }}</posy>
                        <width>235</width>
                        <height>{{ vscale(22) }}</height>
                        <font>font8</font>
                        <align>left</align>
                        <aligny>center</aligny>
                        <textcolor>99FFFFFF</textcolor>
                        <label>$INFO[ListItem.Property(server.name)]</label>
                    </control>
                </control>
                <control type="group">
                    <visible>String.IsEmpty(ListItem.Property(subtitle)) + String.IsEmpty(ListItem.Property(server.name))</visible>
                    <posx>151</posx>
                    <posy>{{ vscale(80) }}</posy>
                    <control type="label">
                        <scroll>false</scroll>
                        <posx>0</posx>
                        <posy>{{ vscale(0) }}</posy>
                        <width>235</width>
                        <height>{{ vscale(32) }}</height>
                        <font>font10</font>
                        <align>left</align>
                        <aligny>center</aligny>
                        <textcolor>FFFFFFFF</textcolor>
                        <label>$INFO[ListItem.Label]</label>
                    </control>
                    <control type="label">
                        <scroll>false</scroll>
                        <posx>0</posx>
                        <posy>{{ vscale(32) }}</posy>
                        <width>235</width>
                        <height>{{ vscale(28) }}</height>
                        <font>font8</font>
                        <align>left</align>
                        <aligny>center</aligny>
                        <textcolor>AAFFFFFF</textcolor>
                        <label>$INFO[ListItem.Label2]</label>
                    </control>
                </control>
                <control type="group">
                    <visible>!String.IsEmpty(ListItem.Property(subtitle)) + !String.IsEmpty(ListItem.Property(server.name))</visible>
                    <posx>151</posx>
                    <posy>{{ vscale(55) }}</posy>
                    <control type="label">
                        <scroll>false</scroll>
                        <posx>0</posx>
                        <posy>{{ vscale(0) }}</posy>
                        <width>235</width>
                        <height>{{ vscale(32) }}</height>
                        <font>font10</font>
                        <align>left</align>
                        <aligny>center</aligny>
                        <textcolor>FFFFFFFF</textcolor>
                        <label>$INFO[ListItem.Label]</label>
                    </control>
                    <control type="label">
                        <scroll>false</scroll>
                        <posx>0</posx>
                        <posy>{{ vscale(32) }}</posy>
                        <width>235</width>
                        <height>{{ vscale(28) }}</height>
                        <font>font8</font>
                        <align>left</align>
                        <aligny>center</aligny>
                        <textcolor>AAFFFFFF</textcolor>
                        <label>$INFO[ListItem.Property(subtitle)]</label>
                    </control>
                    <control type="label">
                        <scroll>false</scroll>
                        <posx>0</posx>
                        <posy>{{ vscale(60) }}</posy>
                        <width>235</width>
                        <height>{{ vscale(28) }}</height>
                        <font>font8</font>
                        <align>left</align>
                        <aligny>center</aligny>
                        <textcolor>AAFFFFFF</textcolor>
                        <label>$INFO[ListItem.Label2]</label>
                    </control>
                    <control type="label">
                        <scroll>false</scroll>
                        <posx>0</posx>
                        <posy>{{ vscale(88) }}</posy>
                        <width>235</width>
                        <height>{{ vscale(22) }}</height>
                        <font>font8</font>
                        <align>left</align>
                        <aligny>center</aligny>
                        <textcolor>99FFFFFF</textcolor>
                        <label>$INFO[ListItem.Property(server.name)]</label>
                    </control>
                </control>
                <control type="group">
                    <visible>!String.IsEmpty(ListItem.Property(subtitle)) + String.IsEmpty(ListItem.Property(server.name))</visible>
                    <posx>151</posx>
                    <posy>{{ vscale(66) }}</posy>
                    <control type="label">
                        <scroll>false</scroll>
                        <posx>0</posx>
                        <posy>{{ vscale(0) }}</posy>
                        <width>235</width>
                        <height>{{ vscale(32) }}</height>
                        <font>font10</font>
                        <align>left</align>
                        <aligny>center</aligny>
                        <textcolor>FFFFFFFF</textcolor>
                        <label>$INFO[ListItem.Label]</label>
                    </control>
                    <control type="label">
                        <scroll>false</scroll>
                        <posx>0</posx>
                        <posy>{{ vscale(32) }}</posy>
                        <width>235</width>
                        <height>{{ vscale(28) }}</height>
                        <font>font8</font>
                        <align>left</align>
                        <aligny>center</aligny>
                        <textcolor>AAFFFFFF</textcolor>
                        <label>$INFO[ListItem.Property(subtitle)]</label>
                    </control>
                    <control type="label">
                        <scroll>false</scroll>
                        <posx>0</posx>
                        <posy>{{ vscale(60) }}</posy>
                        <width>235</width>
                        <height>{{ vscale(28) }}</height>
                        <font>font8</font>
                        <align>left</align>
                        <aligny>center</aligny>
                        <textcolor>AAFFFFFF</textcolor>
                        <label>$INFO[ListItem.Label2]</label>
                    </control>
                </control>
            </control>
        </control>
    </itemlayout>
    <focusedlayout width="412" height="{{ vscale(240) }}">
        <control type="group">
            <posx>3</posx>
            <posy>3</posy>
            <control type="group">
                <control type="image">
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>392</width>
                    <height>{{ vscale(220) }}</height>
                    <texture colordiffuse="12FFFFFF" border="10">script.plex/white-square-rounded.png</texture>
                </control>
                <control type="image">
                    <visible>String.IsEqual(ListItem.Property(art.type),poster)</visible>
                    <posx>10</posx>
                    <posy>{{ vscale(10) }}</posy>
                    <width>133</width>
                    <height>{{ vscale(200) }}</height>
                    <texture diffuse="script.plex/masks/poster-mask.png">$INFO[ListItem.Property(thumb.fallback)]</texture>
                    <aspectratio scalediffuse="false">scale</aspectratio>
                </control>
                <control type="image">
                    <visible>String.IsEqual(ListItem.Property(art.type),poster)</visible>
                    <posx>10</posx>
                    <posy>{{ vscale(10) }}</posy>
                    <width>133</width>
                    <height>{{ vscale(200) }}</height>
                    <texture background="true" diffuse="script.plex/masks/poster-mask.png">$INFO[ListItem.Thumb]</texture>
                    <aspectratio scalediffuse="false">scale</aspectratio>
                </control>
                <control type="image">
                    <visible>String.IsEqual(ListItem.Property(art.type),square)</visible>
                    <posx>10</posx>
                    <posy>{{ vscale(43) }}</posy>
                    <width>133</width>
                    <height>{{ vscale(133) }}</height>
                    <texture diffuse="script.plex/masks/square-mask.png">$INFO[ListItem.Property(thumb.fallback)]</texture>
                    <aspectratio scalediffuse="false">scale</aspectratio>
                </control>
                <control type="image">
                    <visible>String.IsEqual(ListItem.Property(art.type),square)</visible>
                    <posx>10</posx>
                    <posy>{{ vscale(43) }}</posy>
                    <width>133</width>
                    <height>{{ vscale(133) }}</height>
                    <texture background="true" diffuse="script.plex/masks/square-mask.png">$INFO[ListItem.Thumb]</texture>
                    <aspectratio scalediffuse="false">scale</aspectratio>
                </control>
                <control type="image">
                    <visible>String.IsEqual(ListItem.Property(art.type),ar16x9)</visible>
                    <posx>10</posx>
                    <posy>{{ vscale(72) }}</posy>
                    <width>133</width>
                    <height>{{ vscale(75) }}</height>
                    <texture diffuse="script.plex/masks/ar16x9-mask.png">$INFO[ListItem.Property(thumb.fallback)]</texture>
                    <aspectratio scalediffuse="false">scale</aspectratio>
                </control>
                <control type="image">
                    <visible>String.IsEqual(ListItem.Property(art.type),ar16x9)</visible>
                    <posx>10</posx>
                    <posy>{{ vscale(72) }}</posy>
                    <width>133</width>
                    <height>{{ vscale(75) }}</height>
                    <texture background="true" diffuse="script.plex/masks/ar16x9-mask.png">$INFO[ListItem.Thumb]</texture>
                    <aspectratio scalediffuse="false">scale</aspectratio>
                </control>
                <control type="image">
                    <visible>String.IsEqual(ListItem.Property(art.type),circle)</visible>
                    <posx>10</posx>
                    <posy>{{ vscale(43) }}</posy>
                    <width>133</width>
                    <height>{{ vscale(133) }}</height>
                    <texture diffuse="script.plex/masks/role.png">$INFO[ListItem.Property(thumb.fallback)]</texture>
                    <aspectratio scalediffuse="false" aligny="top">scale</aspectratio>
                </control>
                <control type="image">
                    <visible>String.IsEqual(ListItem.Property(art.type),circle)</visible>
                    <posx>10</posx>
                    <posy>{{ vscale(43) }}</posy>
                    <width>133</width>
                    <height>{{ vscale(133) }}</height>
                    <texture background="true" diffuse="script.plex/masks/role.png">$INFO[ListItem.Thumb]</texture>
                    <aspectratio scalediffuse="false" aligny="top">scale</aspectratio>
                </control>
                <control type="group">
                    <visible>String.IsEmpty(ListItem.Property(subtitle)) + !String.IsEmpty(ListItem.Property(server.name))</visible>
                    <posx>151</posx>
                    <posy>{{ vscale(69) }}</posy>
                    <control type="label">
                        <scroll>Control.HasFocus(2100)</scroll>
                        <posx>0</posx>
                        <posy>{{ vscale(0) }}</posy>
                        <width>235</width>
                        <height>{{ vscale(32) }}</height>
                        <font>font10</font>
                        <align>left</align>
                        <aligny>center</aligny>
                        <textcolor>FFFFFFFF</textcolor>
                        <label>$INFO[ListItem.Label]</label>
                    </control>
                    <control type="label">
                        <scroll>false</scroll>
                        <posx>0</posx>
                        <posy>{{ vscale(32) }}</posy>
                        <width>235</width>
                        <height>{{ vscale(28) }}</height>
                        <font>font8</font>
                        <align>left</align>
                        <aligny>center</aligny>
                        <textcolor>AAFFFFFF</textcolor>
                        <label>$INFO[ListItem.Label2]</label>
                    </control>
                    <control type="label">
                        <scroll>false</scroll>
                        <posx>0</posx>
                        <posy>{{ vscale(60) }}</posy>
                        <width>235</width>
                        <height>{{ vscale(22) }}</height>
                        <font>font8</font>
                        <align>left</align>
                        <aligny>center</aligny>
                        <textcolor>99FFFFFF</textcolor>
                        <label>$INFO[ListItem.Property(server.name)]</label>
                    </control>
                </control>
                <control type="group">
                    <visible>String.IsEmpty(ListItem.Property(subtitle)) + String.IsEmpty(ListItem.Property(server.name))</visible>
                    <posx>151</posx>
                    <posy>{{ vscale(80) }}</posy>
                    <control type="label">
                        <scroll>Control.HasFocus(2100)</scroll>
                        <posx>0</posx>
                        <posy>{{ vscale(0) }}</posy>
                        <width>235</width>
                        <height>{{ vscale(32) }}</height>
                        <font>font10</font>
                        <align>left</align>
                        <aligny>center</aligny>
                        <textcolor>FFFFFFFF</textcolor>
                        <label>$INFO[ListItem.Label]</label>
                    </control>
                    <control type="label">
                        <scroll>false</scroll>
                        <posx>0</posx>
                        <posy>{{ vscale(32) }}</posy>
                        <width>235</width>
                        <height>{{ vscale(28) }}</height>
                        <font>font8</font>
                        <align>left</align>
                        <aligny>center</aligny>
                        <textcolor>AAFFFFFF</textcolor>
                        <label>$INFO[ListItem.Label2]</label>
                    </control>
                </control>
                <control type="group">
                    <visible>!String.IsEmpty(ListItem.Property(subtitle)) + !String.IsEmpty(ListItem.Property(server.name))</visible>
                    <posx>151</posx>
                    <posy>{{ vscale(55) }}</posy>
                    <control type="label">
                        <scroll>Control.HasFocus(2100)</scroll>
                        <posx>0</posx>
                        <posy>{{ vscale(0) }}</posy>
                        <width>235</width>
                        <height>{{ vscale(32) }}</height>
                        <font>font10</font>
                        <align>left</align>
                        <aligny>center</aligny>
                        <textcolor>FFFFFFFF</textcolor>
                        <label>$INFO[ListItem.Label]</label>
                    </control>
                    <control type="label">
                        <scroll>false</scroll>
                        <posx>0</posx>
                        <posy>{{ vscale(32) }}</posy>
                        <width>235</width>
                        <height>{{ vscale(28) }}</height>
                        <font>font8</font>
                        <align>left</align>
                        <aligny>center</aligny>
                        <textcolor>AAFFFFFF</textcolor>
                        <label>$INFO[ListItem.Property(subtitle)]</label>
                    </control>
                    <control type="label">
                        <scroll>false</scroll>
                        <posx>0</posx>
                        <posy>{{ vscale(60) }}</posy>
                        <width>235</width>
                        <height>{{ vscale(28) }}</height>
                        <font>font8</font>
                        <align>left</align>
                        <aligny>center</aligny>
                        <textcolor>AAFFFFFF</textcolor>
                        <label>$INFO[ListItem.Label2]</label>
                    </control>
                    <control type="label">
                        <scroll>false</scroll>
                        <posx>0</posx>
                        <posy>{{ vscale(88) }}</posy>
                        <width>235</width>
                        <height>{{ vscale(22) }}</height>
                        <font>font8</font>
                        <align>left</align>
                        <aligny>center</aligny>
                        <textcolor>99FFFFFF</textcolor>
                        <label>$INFO[ListItem.Property(server.name)]</label>
                    </control>
                </control>
                <control type="group">
                    <visible>!String.IsEmpty(ListItem.Property(subtitle)) + String.IsEmpty(ListItem.Property(server.name))</visible>
                    <posx>151</posx>
                    <posy>{{ vscale(66) }}</posy>
                    <control type="label">
                        <scroll>Control.HasFocus(2100)</scroll>
                        <posx>0</posx>
                        <posy>{{ vscale(0) }}</posy>
                        <width>235</width>
                        <height>{{ vscale(32) }}</height>
                        <font>font10</font>
                        <align>left</align>
                        <aligny>center</aligny>
                        <textcolor>FFFFFFFF</textcolor>
                        <label>$INFO[ListItem.Label]</label>
                    </control>
                    <control type="label">
                        <scroll>false</scroll>
                        <posx>0</posx>
                        <posy>{{ vscale(32) }}</posy>
                        <width>235</width>
                        <height>{{ vscale(28) }}</height>
                        <font>font8</font>
                        <align>left</align>
                        <aligny>center</aligny>
                        <textcolor>AAFFFFFF</textcolor>
                        <label>$INFO[ListItem.Property(subtitle)]</label>
                    </control>
                    <control type="label">
                        <scroll>false</scroll>
                        <posx>0</posx>
                        <posy>{{ vscale(60) }}</posy>
                        <width>235</width>
                        <height>{{ vscale(28) }}</height>
                        <font>font8</font>
                        <align>left</align>
                        <aligny>center</aligny>
                        <textcolor>AAFFFFFF</textcolor>
                        <label>$INFO[ListItem.Label2]</label>
                    </control>
                </control>
            </control>
        </control>
        <control type="image">
            <visible>Control.HasFocus(2100)</visible>
            <posx>0</posx>
            <posy>0</posy>
            <width>398</width>
            <height>{{ vscale(226) }}</height>
            <texture diffuse="script.plex/masks/ring-mask-search-card.png">script.plex/white-square.png</texture>
            <colordiffuse>FFE9A20D</colordiffuse>
        </control>
    </focusedlayout>
</control>

<!-- SEARCH HISTORY LIST: below Delete/Space/Clear, the keyboard's width. With Kodi's keyboard
     there's no keyboard here, and SearchWindow.onFirstInit() moves it up under the entry box. -->
<control type="group" id="2040">
    <posx>60</posx>
    <posy>{{ vscale(660) }}</posy>
    <!-- not while a search is under way: it's for an empty query, and the answer replaces it -->
    <visible>!String.IsEmpty(Window.Property(show.history)) + String.IsEmpty(Window.Property(searching))</visible>
    <control type="list" id="2050">
        <posx>0</posx>
        <posy>0</posy>
        <width>414</width>
        <height>{{ vscale(360) }}</height>
        <orientation>vertical</orientation>
        <onleft>9000</onleft>
        <onup condition="String.IsEmpty(Window.Property(hide.kbd))">951</onup>
        <onup condition="!String.IsEmpty(Window.Property(hide.kbd))">650</onup>
        <scrolltime>200</scrolltime>
        <itemlayout width="414" height="{{ vscale(40) }}">
            <control type="image">
                <posx>20</posx>
                <posy>{{ vscale(8) }}</posy>
                <width>24</width>
                <height>{{ vscale(24) }}</height>
                <texture colordiffuse="99FFFFFF">$INFO[ListItem.Property(icon)]</texture>
            </control>
            <control type="label">
                <posx>60</posx>
                <posy>0</posy>
                <width>334</width>
                <height>{{ vscale(40) }}</height>
                <font>font10</font>
                <align>left</align>
                <aligny>center</aligny>
                <textcolor>CCFFFFFF</textcolor>
                <label>$INFO[ListItem.Label]</label>
            </control>
        </itemlayout>
        <focusedlayout width="414" height="{{ vscale(40) }}">
            <control type="image">
                <!-- only with the list focused: Kodi draws the selected row's focused layout
                     whatever has focus -->
                <visible>Control.HasFocus(2050)</visible>
                <posx>0</posx>
                <posy>0</posy>
                <width>414</width>
                <height>{{ vscale(40) }}</height>
                <texture border="10">script.plex/home/selected.png</texture>
            </control>
            <control type="image">
                <posx>20</posx>
                <posy>{{ vscale(8) }}</posy>
                <width>24</width>
                <height>{{ vscale(24) }}</height>
                <texture colordiffuse="FFFFFFFF">$INFO[ListItem.Property(icon)]</texture>
            </control>
            <control type="label">
                <posx>60</posx>
                <posy>0</posy>
                <width>334</width>
                <height>{{ vscale(40) }}</height>
                <font>font10</font>
                <align>left</align>
                <aligny>center</aligny>
                <textcolor>FFFFFFFF</textcolor>
                <label>$INFO[ListItem.Label]</label>
            </control>
        </focusedlayout>
    </control>
</control>

</control>
{% endblock content %}