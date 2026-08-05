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
   back the way Posters/Squares do theirs - a small trailing gray label on the inherited
   filter/sort row, not a restored title bar. Genres has no filter/sort of its own
   (genres.py never sets filter1.display/filter2.display/media.type/sort.display, so those
   buttons render empty either way, unchanged from before this screen had the sidebar - that's
   pre-existing and not something this rollout is fixing), so this is a verbatim copy of
   library.xml.tpl's own filteropts_grouplist (Kodi/ibis blocks replace wholesale, not append -
   the same reason library_posters.xml.tpl's own version is a full copy rather than
   {{ super() }}) with just the trailing label appended. #}
{% block filteropts_grouplist %}
<control type="grouplist" id="600">
    <visible>String.IsEmpty(Window.Property(hide.filteroptions))</visible>
    <visible>!Integer.IsGreater(Container(101).ListItem.Property(index),5) + String.IsEmpty(Window.Property(no.content)) + !String.IsEmpty(Window.Property(initialized))</visible>
    <animation effect="slide" time="200" end="0,{{ vscale(-115) }}" tween="quadratic" easing="out" condition="Integer.IsGreater(Container(101).ListItem.Property(index),5) + String.IsEmpty(Window.Property(content.filling))">Conditional</animation>
    <animation effect="fade" start="0" end="100" time="200" reversible="true">VisibleChange</animation>
    <right>170</right>
    <posy>{{ vscale(135) }}</posy>
    <width>1000</width>
    <height>{{ vscale(65) }}</height>
    <align>right</align>
    <itemgap>30</itemgap>
    <orientation>horizontal</orientation>
    <onleft condition="String.IsEmpty(Window.Property(no.content.filtered))">304</onleft>
    <onleft condition="!String.IsEmpty(Window.Property(no.content.filtered))">9000</onleft>
    <onright>151</onright>
    <ondown>101</ondown>
    <onup condition="Player.HasAudio + String.IsEmpty(Window(10000).Property(script.plex.theme_playing))">204</onup>
    <control type="button" id="311">
        <enable>false</enable>
        <width max="300">auto</width>
        <height>{{ vscale(65) }}</height>
        <font>font12</font>
        <textcolor>FFFFFFFF</textcolor>
        <focusedcolor>FFFFFFFF</focusedcolor>
        <disabledcolor>FFFFFFFF</disabledcolor>
        <align>center</align>
        <aligny>center</aligny>
        <texturefocus>-</texturefocus>
        <texturenofocus>-</texturenofocus>
        <textoffsetx>0</textoffsetx>
        <textoffsety>0</textoffsety>
        <label>[UPPERCASE]$INFO[Window.Property(filter2.display)][/UPPERCASE]</label>
    </control>
    <control type="button" id="211">
        <width max="500">auto</width>
        <height>{{ vscale(65) }}</height>
        <font>font12</font>
        <textcolor>FFFFFFFF</textcolor>
        <focusedcolor>FF000000</focusedcolor>
        <align>center</align>
        <aligny>center</aligny>
        <texturefocus colordiffuse="FFE5A00D" border="10">script.plex/white-square-rounded.png</texturefocus>
        <texturenofocus>-</texturenofocus>
        <textoffsetx>20</textoffsetx>
        <textoffsety>0</textoffsety>
        <label>[UPPERCASE]$INFO[Window.Property(filter1.display)][/UPPERCASE]</label>
    </control>
    <control type="button" id="310">
        <visible>!String.IsEqual(Window.Property(media),artist)</visible>
        <enable>false</enable>
        <width max="300">auto</width>
        <height>{{ vscale(65) }}</height>
        <font>font12</font>
        <textcolor>FFFFFFFF</textcolor>
        <focusedcolor>FFFFFFFF</focusedcolor>
        <disabledcolor>FFFFFFFF</disabledcolor>
        <align>center</align>
        <aligny>center</aligny>
        <texturenofocus>-</texturenofocus>
        <texturenofocus>-</texturenofocus>
        <textoffsetx>20</textoffsetx>
        <textoffsety>0</textoffsety>
        <label>[UPPERCASE]$INFO[Window.Property(media.type)][/UPPERCASE]</label>
    </control>
    <control type="button" id="312">
        <visible>String.IsEqual(Window.Property(media),artist)</visible>
        <width max="300">auto</width>
        <height>{{ vscale(65) }}</height>
        <font>font12</font>
        <textcolor>FFFFFFFF</textcolor>
        <focusedcolor>FF000000</focusedcolor>
        <disabledcolor>FFFFFFFF</disabledcolor>
        <align>center</align>
        <aligny>center</aligny>
        <texturefocus colordiffuse="FFE5A00D" border="10">script.plex/white-square-rounded.png</texturefocus>
        <texturenofocus>-</texturenofocus>
        <textoffsetx>20</textoffsetx>
        <textoffsety>0</textoffsety>
        <label>[UPPERCASE]$INFO[Window.Property(media.type)][/UPPERCASE]</label>
    </control>
    <control type="button" id="210">
        <width max="300">auto</width>
        <height>{{ vscale(65) }}</height>
        <font>font12</font>
        <textcolor>FFFFFFFF</textcolor>
        <focusedcolor>FF000000</focusedcolor>
        <align>center</align>
        <aligny>center</aligny>
        <texturefocus colordiffuse="FFE5A00D" border="10">script.plex/white-square-rounded.png</texturefocus>
        <texturenofocus>-</texturenofocus>
        <textoffsetx>20</textoffsetx>
        <textoffsety>0</textoffsety>
        <label>[UPPERCASE]$INFO[Window.Property(sort.display)][/UPPERCASE]</label>
    </control>
    <control type="label">
        <width max="400">auto</width>
        <height>{{ vscale(65) }}</height>
        <font>font10</font>
        <textcolor>FFFFFFFF</textcolor>
        <align>left</align>
        <aligny>center</aligny>
        <label>[COLOR=gray]$INFO[Window.Property(items.count)] $INFO[Window.Property(screen.title)][/COLOR]</label>
    </control>
</control>
{% endblock filteropts_grouplist %}

{% block content %}
<control type="group" id="50">
    <visible>!String.IsEmpty(Window.Property(initialized))</visible>
    <!-- Slide right while the sidebar rail is expanded (focused), matching every other ported screen -->
    <animation effect="slide" end="220,0" time="200" tween="sine" easing="inout" condition="ControlGroup(9000).HasFocus(0)">Conditional</animation>
    <defaultcontrol>101</defaultcontrol>
    <!-- posx=60, not 0: clears the collapsed sidebar rail's icon column, matching every other
         ported screen. -->
    <posx>60</posx>
    <posy>{{ vscale(135) }}</posy>

    <control type="panel" id="101">
        <!-- width=1800, not 1920 (hitrect matched): 1920 - 60 (this group's own sidebar-clearance
             shift) - 60 (the same right-margin convention every other ported screen's
             right-anchored content settled on) = 1800, matching Posters' own panel width exactly.
             Item cells shrunk below (480->450) so this still fits 4 full columns rather than
             reflowing to 3. -->
        <hitrect x="0" y="0" w="1800" h="945" />
        <posx>0</posx>
        <posy>0</posy>
        <width>1800</width>
        <height>{{ vscale(945) }}</height>
        <onup>200</onup>
        <onleft>9000</onleft>
        <scrolltime>200</scrolltime>
        <orientation>vertical</orientation>
        <preloaditems>2</preloaditems>

        <!-- ITEM LAYOUT ##########################################
             480->450 cell (art 450x253->420x236, margins unchanged at 15px/side): keeps 4 full
             columns in the panel's own reduced 1800 width (1800/450=4 exactly) instead of
             reflowing to 3 - see the panel's own width comment above. -->
        <itemlayout width="450" height="{{ vscale(273) }}">
            <control type="group">
                <posx>15</posx>
                <posy>15</posy>
                <!-- Genre art -->
                <control type="image">
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>420</width>
                    <height>{{ vscale(236) }}</height>
                    <texture background="true">$INFO[ListItem.Thumb]</texture>
                    <aspectratio>scale</aspectratio>
                </control>
                <!-- Dark overlay to make label readable -->
                <control type="image">
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>420</width>
                    <height>{{ vscale(236) }}</height>
                    <texture>script.plex/white-square.png</texture>
                    <colordiffuse>55000000</colordiffuse>
                </control>
                <!-- Genre name -->
                <control type="label">
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>420</width>
                    <height>{{ vscale(236) }}</height>
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
        <focusedlayout width="450" height="{{ vscale(273) }}">
            <control type="group">
                <posx>15</posx>
                <posy>15</posy>
                <control type="group">
                    <animation effect="zoom" start="100" end="105" time="100" center="210,{{ vscale(118) }}" reversible="false">Focus</animation>
                    <animation effect="zoom" start="105" end="100" time="100" center="210,{{ vscale(118) }}" reversible="false">UnFocus</animation>
                    <!-- Genre art -->
                    <control type="image">
                        <posx>0</posx>
                        <posy>0</posy>
                        <width>420</width>
                        <height>{{ vscale(236) }}</height>
                        <texture background="true">$INFO[ListItem.Thumb]</texture>
                        <aspectratio>scale</aspectratio>
                    </control>
                    <!-- Dark overlay -->
                    <control type="image">
                        <posx>0</posx>
                        <posy>0</posy>
                        <width>420</width>
                        <height>{{ vscale(236) }}</height>
                        <texture>script.plex/white-square.png</texture>
                        <colordiffuse>55000000</colordiffuse>
                    </control>
                    <!-- Genre name -->
                    <control type="label">
                        <scroll>Control.HasFocus(101)</scroll>
                        <posx>0</posx>
                        <posy>0</posy>
                        <width>420</width>
                        <height>{{ vscale(236) }}</height>
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
                        <control type="image">
                            <posx>0</posx>
                            <posy>0</posy>
                            <width>430</width>
                            <height>{{ vscale(246) }}</height>
                            <texture border="10">script.plex/home/selected.png</texture>
                        </control>
                    </control>
                </control>
            </control>
        </focusedlayout>
    </control>
</control>
{% endblock content %}
