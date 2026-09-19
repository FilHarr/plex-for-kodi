{% extends "base.xml.tpl" %}
{# Two columns: the music player's own screen (script-plex-music_player.xml.tpl) in a now-playing
   column on the left, and the play queue in the 520 on the right (1400..1920). The left column
   is that screen's markup at the sizes it has there, laid out as if for a 1440-wide column
   (centre 720: cover 640 wide at 400, text block 1250 wide at 95, transport row 1200 wide at
   120, seekbar at 80% of 1440 = 1152 at 144 with the times in the margins) and then shifted 20px
   left as a whole - so it reads as centred on 700 with 20px trimmed from each side, and the
   queue gets that 40. Every x below is the 1440 figure minus 20. #}
{% block controls %}
{% block backgroundcolor %}<backgroundcolor>0xff000000</backgroundcolor>{% endblock %}
{# BACKGROUND: the 4-corner tinted panel - the same corner-anchored falloff shape, mask and
   flips as the shared background (includes/default_background.xml.tpl), over the same flat base
   fill - but with each corner's colour set on the control itself from Python
   (CurrentPlaylistWindow.updateFromTrack, currentplaylist.py) rather than read out of a window
   property through $INFO[] on every frame.

   Why these two screens don't use the shared include's panel: here the panel IS the whole
   background - no hero art box, nothing covering the corners - and the property-driven version
   flashed the flat base on every single track change, including changes within one album, where
   the colours don't change and nothing is written at all (live, 2026-09-19; confirmed by
   temporarily colouring the base fill red). Kodi re-resolves both an $INFO[] <colordiffuse> and a
   String.IsEmpty() <visible> condition every frame, and a track change resets the info cache
   (Info.OnChanged), so for a frame those corners read empty and stopped drawing. Kodi's
   setColorDiffuse stores a constant CGUIInfoColor with no info label attached (Control.cpp), so
   there is nothing left to re-resolve, and the controls carry no visible condition or fade to
   flap either. The window's own backgroundcolor stays declared below for the same reason it used
   to be black here: this window is otherwise transparent, and what sits behind it is
   BackgroundWindow's own 0xff111111 - which is the base colour, and would be indistinguishable
   from this panel failing. #}
<control type="image">
    <posx>0</posx>
    <posy>0</posy>
    <width>1920</width>
    <height>1080</height>
    <texture>script.plex/white-square.png</texture>
    <colordiffuse>FF111111</colordiffuse>
</control>
<!-- topLeft -->
<control type="image" id="301">
    <posx>0</posx>
    <posy>0</posy>
    <width>1920</width>
    <height>1080</height>
    <texture diffuse="script.plex/masks/background-corner.png">script.plex/white-square.png</texture>
    <colordiffuse>00000000</colordiffuse>
</control>
<!-- topRight -->
<control type="image" id="302">
    <posx>0</posx>
    <posy>0</posy>
    <width>1920</width>
    <height>1080</height>
    <texture diffuse="script.plex/masks/background-corner.png" flipx="true">script.plex/white-square.png</texture>
    <colordiffuse>00000000</colordiffuse>
</control>
<!-- bottomLeft -->
<control type="image" id="303">
    <posx>0</posx>
    <posy>0</posy>
    <width>1920</width>
    <height>1080</height>
    <texture diffuse="script.plex/masks/background-corner.png" flipy="true">script.plex/white-square.png</texture>
    <colordiffuse>00000000</colordiffuse>
</control>
<!-- bottomRight -->
<control type="image" id="304">
    <posx>0</posx>
    <posy>0</posy>
    <width>1920</width>
    <height>1080</height>
    <texture diffuse="script.plex/masks/background-corner.png" flipx="true" flipy="true">script.plex/white-square.png</texture>
    <colordiffuse>00000000</colordiffuse>
</control>

<!-- ================================================================================
     NOW PLAYING (0..1440) - see script-plex-music_player.xml.tpl for each block's reasoning;
     only the x values differ here.
     ================================================================================ -->

<!-- Clock: the header's own (default.xml.tpl / library.xml.tpl / settings, user_select),
     verbatim - these two windows have no header, so it's declared here to keep it where every
     other screen has it. -->
<control type="label">
    <right>60</right>
    <posy>{{ vscale(35) }}</posy>
    <width>200</width>
    <height>{{ vscale(65) }}</height>
    <font>font12</font>
    <align>right</align>
    <aligny>center</aligny>
    <textcolor>FFFFFFFF</textcolor>
    <label>$INFO[System.Time]</label>
</control>

<!-- COVER: 640x640 - 380 = (1440 - 640) / 2 - 20 - top edge 10px above the header's bottom edge,
     as on the player screen. -->
<control type="image">
    <posx>380</posx>
    <posy>{{ vscale(125) }}</posy>
    <width>640</width>
    <height>{{ vscale(640) }}</height>
    <fadetime>250</fadetime>
    <texture background="true" diffuse="script.plex/masks/square-mask.png">$INFO[Window.Property(cover.url)]</texture>
    <aspectratio scalediffuse="false">scale</aspectratio>
</control>

<!-- TRACK TEXT: the player screen's block, 1250 wide (75 = (1440 - 1250) / 2 - 20). -->
<control type="group">
    <posx>75</posx>
    <posy>{{ vscale(785) }}</posy>
    <control type="label">
        <posx>0</posx>
        <posy>0</posy>
        <width>1250</width>
        <height>{{ vscale(61) }}</height>
        <font>font45_title</font>
        <align>center</align>
        <aligny>top</aligny>
        <scroll>true</scroll>
        <scrollspeed>35</scrollspeed>
        <textcolor>FFD2CCCE</textcolor>
        <label>$INFO[MusicPlayer.Title]</label>
    </control>
    <control type="label">
        <posx>0</posx>
        <posy>{{ vscale(68) }}</posy>
        <width>1250</width>
        <height>{{ vscale(30) }}</height>
        <font>font10</font>
        <align>center</align>
        <textcolor>FFD2CCCE</textcolor>
        <shadowcolor>66000000</shadowcolor>
        <label>$INFO[MusicPlayer.Artist]$INFO[MusicPlayer.Album, • ]</label>
    </control>
</control>

<!-- TIMES: the player screen's four labels either side of the bar, 104 wide, 20px clear of its
     ends - the elapsed ones ending at 104 (their posx is their RIGHT edge: Kodi subtracts the
     width from posx for a right-aligned label control - see the player template), the remaining
     ones starting at 1276 + 20 = 1296 and ending on the queue column's edge at 1400. -->
<control type="label">
    <visible>Player.HasAudio + String.IsEqual(Player.Duration(hh),00)</visible>
    <posx>104</posx>
    <posy>{{ vscale(153) }}r</posy>
    <width>104</width>
    <height>{{ vscale(30) }}</height>
    <font>font10</font>
    <align>right</align>
    <aligny>center</aligny>
    <textcolor>FFD2CCCE</textcolor>
    <label>$INFO[Player.Time(m)]:$INFO[Player.Time(ss)]</label>
</control>
<control type="label">
    <visible>Player.HasAudio + !String.IsEqual(Player.Duration(hh),00)</visible>
    <posx>104</posx>
    <posy>{{ vscale(153) }}r</posy>
    <width>104</width>
    <height>{{ vscale(30) }}</height>
    <font>font10</font>
    <align>right</align>
    <aligny>center</aligny>
    <textcolor>FFD2CCCE</textcolor>
    <label>$INFO[Player.Time(h:mm:ss)]</label>
</control>
<control type="label">
    <visible>Player.HasAudio + String.IsEqual(Player.Duration(hh),00)</visible>
    <posx>1296</posx>
    <posy>{{ vscale(153) }}r</posy>
    <width>104</width>
    <height>{{ vscale(30) }}</height>
    <font>font10</font>
    <align>left</align>
    <aligny>center</aligny>
    <textcolor>FFD2CCCE</textcolor>
    <label>-$INFO[Player.TimeRemaining(m)]:$INFO[Player.TimeRemaining(ss)]</label>
</control>
<control type="label">
    <visible>Player.HasAudio + !String.IsEqual(Player.Duration(hh),00)</visible>
    <posx>1296</posx>
    <posy>{{ vscale(153) }}r</posy>
    <width>104</width>
    <height>{{ vscale(30) }}</height>
    <font>font10</font>
    <align>left</align>
    <aligny>center</aligny>
    <textcolor>FFD2CCCE</textcolor>
    <label>$INFO[Player.TimeRemaining(h:mm:ss),-]</label>
</control>

<!-- TRANSPORT ROW: the shared include, 1200 wide (100 = (1440 - 1200) / 2 - 20). Left end is a
     dead stop (401's own noop); right end goes on into the queue list. -->
<control type="grouplist" id="400">
    <defaultcontrol>406</defaultcontrol>
    <hitrect x="100" y="980" w="1200" h="70" />
    <posx>100</posx>
    <posy>{{ vscale(100) }}r</posy>
    <width>1200</width>
    <height>{{ vscale(70) }}</height>
    <align>center</align>
    <onup>500</onup>
    <onleft>noop</onleft>
    <onright>100</onright>
    <itemgap>{{ theme.music_player.buttongroup.itemgap }}</itemgap>
    <orientation>horizontal</orientation>
    <scrolltime tween="quadratic" easing="out">200</scrolltime>
    <usecontrolcoords>true</usecontrolcoords>

    {% include "includes/music_player_buttons.xml.tpl" %}

</control>

<!-- SEEKBAR: the player screen's bar at 80% of 1440 (1152, at 124..1276), on
     masks/seekbar-mask-1152.png - the 1536 one's twin at this width, same recipe (a diffuse mask
     scales to its control, so the wider one would squash its caps here). Same layers: masked
     track, invisible focus button, two <reveal> progress controls for the played portion
     (unfocused / focused), and the scrubber (510, SEEK_IMAGE_ID - a <reveal> progress control
     driven by setSeekbarProgress(), currentplaylist.py). Python's BAR_X / BAR_RIGHT /
     SEEK_IMAGE_WIDTH there have to match the 124/1152 here. -->
<control type="group">
    <posx>124</posx>
    <posy>{{ vscale(140) }}r</posy>
    <control type="image">
        <posx>0</posx>
        <posy>0</posy>
        <width>1152</width>
        <height>{{ vscale(8) }}</height>
        <texture diffuse="script.plex/masks/seekbar-mask-1152.png">script.plex/white-square.png</texture>
        <colordiffuse>40FFFFFF</colordiffuse>
    </control>
    <control type="button" id="500">
        <enable>Player.HasAudio</enable>
        <hitrect x="0" y="-19" w="1152" h="48" />
        <posx>0</posx>
        <posy>0</posy>
        <width>1152</width>
        <height>{{ vscale(8) }}</height>
        <ondown>400</ondown>
        <onup>100</onup>
        <texturefocus>-</texturefocus>
        <texturenofocus>-</texturenofocus>
        <label> </label>
    </control>
    <control type="progress">
        <visible>!Control.HasFocus(500)</visible>
        <description>Progressbar</description>
        <posx>0</posx>
        <posy>0</posy>
        <width>1152</width>
        <height>{{ vscale(8) }}</height>
        <reveal>true</reveal>
        <texturebg>script.plex/transparent-6px.png</texturebg>
        <lefttexture>-</lefttexture>
        <midtexture diffuse="script.plex/masks/seekbar-mask-1152.png">script.plex/white-square-6px.png</midtexture>
        <righttexture>-</righttexture>
        <overlaytexture>-</overlaytexture>
        <colordiffuse>FFE5A00D</colordiffuse>
        <info>Player.Progress</info>
    </control>
    <control type="progress">
        <visible>Control.HasFocus(500)</visible>
        <description>Progressbar</description>
        <posx>0</posx>
        <posy>0</posy>
        <width>1152</width>
        <height>{{ vscale(8) }}</height>
        <reveal>true</reveal>
        <texturebg>script.plex/transparent-6px.png</texturebg>
        <lefttexture>-</lefttexture>
        <midtexture diffuse="script.plex/masks/seekbar-mask-1152.png">script.plex/white-square-6px.png</midtexture>
        <righttexture>-</righttexture>
        <overlaytexture>-</overlaytexture>
        <colordiffuse>FFAC5B00</colordiffuse>
        <info>Player.Progress</info>
    </control>
    <control type="progress" id="510">
        <visible>Control.HasFocus(500)</visible>
        <animation effect="fade" time="100" delay="100" end="100">Visible</animation>
        <description>Scrubber</description>
        <posx>0</posx>
        <posy>0</posy>
        <width>1152</width>
        <height>{{ vscale(8) }}</height>
        <reveal>true</reveal>
        <texturebg>script.plex/transparent-6px.png</texturebg>
        <lefttexture>-</lefttexture>
        <midtexture diffuse="script.plex/masks/seekbar-mask-1152.png">script.plex/white-square-6px.png</midtexture>
        <righttexture>-</righttexture>
        <overlaytexture>-</overlaytexture>
        <colordiffuse>FFE5A00D</colordiffuse>
    </control>
</control>

<!-- Seek-time bubble, wrapped at the bar's x so updateSelectedProgress()'s setPosition() on 202
     is relative to the bar's left edge - as on the player screen. -->
<control type="group">
    <posx>124</posx>
    <posy>0</posy>
    <control type="group" id="202">
        <visible>Control.HasFocus(500) + !String.IsEmpty(Window.Property(time.selection))</visible>
        <posx>0</posx>
        <posy>{{ vscale(184) }}r</posy>
        <control type="group" id="203">
            <posx>-50</posx>
            <posy>0</posy>
            <control type="image">
                <animation effect="fade" time="100" delay="100" end="100">Visible</animation>
                <posx>0</posx>
                <posy>0</posy>
                <width>101</width>
                <height>{{ vscale(39) }}</height>
                <texture>script.plex/indicators/player-selection-time_box.png</texture>
                <colordiffuse>D0000000</colordiffuse>
            </control>
            <control type="label">
                <posx>0</posx>
                <posy>0</posy>
                <width>101</width>
                <height>{{ vscale(40) }}</height>
                <font>font10</font>
                <align>center</align>
                <aligny>center</aligny>
                <textcolor>FFFFFFFF</textcolor>
                <label>$INFO[Window.Property(time.selection)]</label>
            </control>
        </control>
        <control type="image">
            <animation effect="fade" time="100" delay="100" end="100">Visible</animation>
            <posx>-6</posx>
            <posy>{{ vscale(39) }}</posy>
            <width>15</width>
            <height>{{ vscale(7) }}</height>
            <texture>script.plex/indicators/player-selection-time_arrow.png</texture>
            <colordiffuse>D0000000</colordiffuse>
        </control>
    </control>
</control>

<!-- ================================================================================
     PLAY QUEUE (1400..1920) - the Kodi music playlist (fillPlaylist(), currentplaylist.py), one
     row per track in the music section's list-view recipe (script-plex-listview-tracks.xml.tpl,
     whose row is the shared includes/track_row.xml.tpl): a 100px row carrying a 92-tall rounded
     pill, 60000000 unfocused / 33FFFFFF focused, 80px art at its left, title over a dimmed
     second line, the playing track's title in the accent colour. Two differences, both asked
     for: no duration, and the pill is 460 wide (20px inset each side of the 520 column, the
     scrollbar in the right inset), so the text boxes are 338 - ending 18px short of the pill's
     right edge, as that recipe's do. No backing plate behind the rows: each carries its own
     pill. Rows run from the cover's top line (125) for 9 whole rows, ending above the
     transport row. ================================================================================ -->
<control type="group" id="100">
    <visible>Integer.IsGreater(Container(101).NumItems,0) + String.IsEmpty(Window.Property(drawing))</visible>
    <defaultcontrol>101</defaultcontrol>
    <posx>1400</posx>
    <posy>0</posy>
    <width>520</width>
    <height>1080</height>
    <control type="list" id="101">
        <hitrect x="1420" y="125" w="460" h="900" />
        <posx>20</posx>
        <posy>{{ vscale(125) }}</posy>
        <width>460</width>
        <height>{{ vscale(900) }}</height>
        <onright>152</onright>
        <onleft>411</onleft>
        <!-- Stop at the ends rather than wrapping - see the album screen's own copy of this pair
             (script-plex-album.xml.tpl) for why both tags are needed. -->
        <wraparound>false</wraparound>
        <ondown>noop</ondown>
        <onup>noop</onup>
        <scrolltime>200</scrolltime>
        <orientation>vertical</orientation>
        <preloaditems>4</preloaditems>
        <pagecontrol>152</pagecontrol>

        <!-- ITEM LAYOUT ########################################## -->
        <itemlayout height="{{ vscale(100) }}">
            <control type="group">
                <posx>0</posx>
                <posy>0</posy>
                <control type="image">
                    <posx>0</posx>
                    <posy>{{ vscale(4) }}</posy>
                    <width>460</width>
                    <height>{{ vscale(92) }}</height>
                    <texture border="10" colordiffuse="60000000">script.plex/white-square-rounded.png</texture>
                </control>
                {% include "includes/track_row.xml.tpl" with list_id=101 & scroll_focused=False & text_width=338 & no_duration=True %}
            </control>
        </itemlayout>

        <!-- FOCUSED LAYOUT ####################################### -->
        <focusedlayout height="{{ vscale(100) }}">
            <control type="group">
                <posx>0</posx>
                <posy>0</posy>
                <!-- Both pills gated on Control.HasFocus(101) - Kodi renders the focusedlayout for
                     the selected item whether or not the list has focus (see the tracks list). -->
                <control type="image">
                    <visible>Control.HasFocus(101)</visible>
                    <posx>0</posx>
                    <posy>{{ vscale(4) }}</posy>
                    <width>460</width>
                    <height>{{ vscale(92) }}</height>
                    <texture border="10" colordiffuse="33FFFFFF">script.plex/white-square-rounded.png</texture>
                </control>
                <control type="image">
                    <visible>!Control.HasFocus(101)</visible>
                    <posx>0</posx>
                    <posy>{{ vscale(4) }}</posy>
                    <width>460</width>
                    <height>{{ vscale(92) }}</height>
                    <texture border="10" colordiffuse="60000000">script.plex/white-square-rounded.png</texture>
                </control>
                {% include "includes/track_row.xml.tpl" with list_id=101 & scroll_focused=True & text_width=338 & no_duration=True %}
            </control>
        </focusedlayout>
    </control>

    <control type="scrollbar" id="152">
        <hitrect x="468" y="129" w="52" h="892" />
        <left>488</left>
        <top>129</top>
        <width>12</width>
        <height>892</height>
        <onleft>101</onleft>
        <visible>true</visible>
        <texturesliderbackground colordiffuse="40000000" border="5">script.plex/white-square-rounded.png</texturesliderbackground>
        <texturesliderbar colordiffuse="77FFFFFF" border="5">script.plex/white-square-rounded.png</texturesliderbar>
        <texturesliderbarfocus colordiffuse="FFE5A00D" border="5">script.plex/white-square-rounded.png</texturesliderbarfocus>
        <textureslidernib>-</textureslidernib>
        <textureslidernibfocus>-</textureslidernibfocus>
        <pulseonselect>false</pulseonselect>
        <orientation>vertical</orientation>
        <showonepage>false</showonepage>
    </control>
</control>
{% endblock controls %}
