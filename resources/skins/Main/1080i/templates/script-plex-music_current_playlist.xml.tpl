{% extends "base.xml.tpl" %}
{# Two columns: the music player's own screen (script-plex-music_player.xml.tpl), re-centred in
   a 1440-wide now-playing column on the left, and the play queue in the 480 on the right - a
   75/25 split. Everything in the left column is that screen's markup with x recalculated for
   the narrower centre (720, not 960): cover 640 wide at 400, text block 1250 wide at 95,
   transport row 1200 wide at 120. The seekbar keeps that screen's 80%-of-column rule, so it is
   1152 wide at 144 with the times in the 144px margins, on its own native-size mask. #}
{% block backgroundcolor %}<backgroundcolor>0xff000000</backgroundcolor>{% endblock %}
{% block controls %}

<!-- ================================================================================
     NOW PLAYING (0..1440) - see script-plex-music_player.xml.tpl for each block's reasoning;
     only the x values differ here.
     ================================================================================ -->

<!-- COVER: 640x640, centred in the column (400 = (1440 - 640) / 2), top edge 10px above the
     header's bottom edge - as on the player screen. -->
<control type="image">
    <posx>400</posx>
    <posy>{{ vscale(125) }}</posy>
    <width>640</width>
    <height>{{ vscale(640) }}</height>
    <texture diffuse="script.plex/masks/square-mask.png">script.plex/thumb_fallbacks/music.png</texture>
</control>
<control type="image">
    <posx>400</posx>
    <posy>{{ vscale(125) }}</posy>
    <width>640</width>
    <height>{{ vscale(640) }}</height>
    <texture background="true" diffuse="script.plex/masks/square-mask.png">$INFO[Player.Art(thumb)]</texture>
    <aspectratio scalediffuse="false">scale</aspectratio>
</control>

<!-- TRACK TEXT: the player screen's block, 1250 wide centred in the column (95 = (1440 - 1250) / 2). -->
<control type="group">
    <posx>95</posx>
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

<!-- TIMES: the player screen's four labels in this column's 144px margins - 124 wide, 20px clear
     of the bar's ends. The elapsed labels' posx is their RIGHT edge (Kodi subtracts the width
     from posx for a right-aligned label control - see the player template). -->
<control type="label">
    <visible>Player.HasAudio + String.IsEqual(Player.Duration(hh),00)</visible>
    <posx>124</posx>
    <posy>{{ vscale(153) }}r</posy>
    <width>124</width>
    <height>{{ vscale(30) }}</height>
    <font>font10</font>
    <align>right</align>
    <aligny>center</aligny>
    <textcolor>FFD2CCCE</textcolor>
    <label>$INFO[Player.Time(m)]:$INFO[Player.Time(ss)]</label>
</control>
<control type="label">
    <visible>Player.HasAudio + !String.IsEqual(Player.Duration(hh),00)</visible>
    <posx>124</posx>
    <posy>{{ vscale(153) }}r</posy>
    <width>124</width>
    <height>{{ vscale(30) }}</height>
    <font>font10</font>
    <align>right</align>
    <aligny>center</aligny>
    <textcolor>FFD2CCCE</textcolor>
    <label>$INFO[Player.Time(h:mm:ss)]</label>
</control>
<control type="label">
    <visible>Player.HasAudio + String.IsEqual(Player.Duration(hh),00)</visible>
    <posx>1316</posx>
    <posy>{{ vscale(153) }}r</posy>
    <width>124</width>
    <height>{{ vscale(30) }}</height>
    <font>font10</font>
    <align>left</align>
    <aligny>center</aligny>
    <textcolor>FFD2CCCE</textcolor>
    <label>-$INFO[Player.TimeRemaining(m)]:$INFO[Player.TimeRemaining(ss)]</label>
</control>
<control type="label">
    <visible>Player.HasAudio + !String.IsEqual(Player.Duration(hh),00)</visible>
    <posx>1316</posx>
    <posy>{{ vscale(153) }}r</posy>
    <width>124</width>
    <height>{{ vscale(30) }}</height>
    <font>font10</font>
    <align>left</align>
    <aligny>center</aligny>
    <textcolor>FFD2CCCE</textcolor>
    <label>$INFO[Player.TimeRemaining(h:mm:ss),-]</label>
</control>

<!-- TRANSPORT ROW: the shared include, 1200 wide centred in the column (120 = (1440 - 1200) / 2).
     Left end is a dead stop (401's own noop); right end goes on into the queue list. -->
<control type="grouplist" id="400">
    <defaultcontrol>406</defaultcontrol>
    <hitrect x="120" y="980" w="1200" h="70" />
    <posx>120</posx>
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

<!-- SEEKBAR: the player screen's bar at 80% of this column (1152, at 144..1296), on
     masks/seekbar-mask-1152.png - the 1536 one's twin at this width, same recipe (a diffuse mask
     scales to its control, so the wider one would squash its caps here). Same layers: masked
     track, invisible focus button, two <reveal> progress controls for the played portion
     (unfocused / focused), and the scrubber (510, SEEK_IMAGE_ID - a <reveal> progress control
     driven by setSeekbarProgress(), currentplaylist.py). Python's BAR_X / BAR_RIGHT /
     SEEK_IMAGE_WIDTH there have to match the 144/1152 here. -->
<control type="group">
    <posx>144</posx>
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
        <onright>100</onright>
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
    <posx>144</posx>
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
     PLAY QUEUE (1440..1920) - the Kodi music playlist (fillPlaylist(), currentplaylist.py), one
     100px row per track, with the playing one marked by the playing-circle in place of its
     number. Row geometry for the 480px column, 20px inset each side (content 0..420 within the
     row group at 20): number 0..40 / thumb 74 at 52 / text at 142, 190 wide / duration 80 wide
     right-aligned to 420. The focused card is the same 420 box with its 100px thumb at 52 and
     the text narrowed to 160 to make room. The scrollbar sits in the right inset.
     ================================================================================ -->
<control type="group" id="100">
    <visible>Integer.IsGreater(Container(101).NumItems,0) + String.IsEmpty(Window.Property(drawing))</visible>
    <defaultcontrol>101</defaultcontrol>
    <posx>1440</posx>
    <posy>0</posy>
    <width>480</width>
    <height>1080</height>
    <control type="image">
        <posx>0</posx>
        <posy>0</posy>
        <width>480</width>
        <height>1080</height>
        <texture>script.plex/white-square.png</texture>
        <colordiffuse>20000000</colordiffuse>
    </control>
    <control type="list" id="101">
        <posx>0</posx>
        <posy>0</posy>
        <width>480</width>
        <height>1080</height>
        <onright>152</onright>
        <onleft>411</onleft>
        <scrolltime>200</scrolltime>
        <orientation>vertical</orientation>
        <preloaditems>4</preloaditems>
        <pagecontrol>152</pagecontrol>
        <!-- ITEM LAYOUT ########################################## -->
        <itemlayout height="{{ vscale(100) }}">
            <control type="group">
                <posx>20</posx>
                <posy>{{ vscale(24) }}</posy>
                <control type="label">
                    <visible>!String.IsEqual(ListItem.Property(track.ID),Window(10000).Property(script.plex.track.ID))</visible>
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>40</width>
                    <height>{{ vscale(100) }}</height>
                    <font>font10</font>
                    <align>center</align>
                    <aligny>center</aligny>
                    <textcolor>D8FFFFFF</textcolor>
                    <label>[B]$INFO[ListItem.Property(track.number)][/B]</label>
                </control>
                <control type="image">
                    <visible>String.IsEqual(ListItem.Property(track.ID),Window(10000).Property(script.plex.track.ID))</visible>
                    <posx>2</posx>
                    <posy>{{ vscale(32.5) }}</posy>
                    <width>35</width>
                    <height>{{ vscale(35) }}</height>
                    <texture>script.plex/indicators/playing-circle.png</texture>
                    <colordiffuse>FFE5A00D</colordiffuse>
                </control>
                <control type="image">
                    <posx>52</posx>
                    <posy>{{ vscale(11) }}</posy>
                    <width>74</width>
                    <height>{{ vscale(74) }}</height>
                    <texture>$INFO[ListItem.Thumb]</texture>
                    <aspectratio>scale</aspectratio>
                </control>
                <control type="group">
                    <posx>142</posx>
                    <posy>0</posy>
                    <control type="label">
                        <posx>0</posx>
                        <posy>{{ vscale(15) }}</posy>
                        <width>190</width>
                        <height>{{ vscale(30) }}</height>
                        <font>font10</font>
                        <align>left</align>
                        <aligny>center</aligny>
                        <textcolor>FFFFFFFF</textcolor>
                        <label>[B]$INFO[ListItem.Label][/B]</label>
                    </control>
                    <control type="label">
                        <posx>0</posx>
                        <posy>{{ vscale(50) }}</posy>
                        <width>190</width>
                        <height>{{ vscale(30) }}</height>
                        <font>font10</font>
                        <align>left</align>
                        <aligny>center</aligny>
                        <textcolor>B8FFFFFF</textcolor>
                        <label>$INFO[ListItem.Label2]</label>
                    </control>
                </control>
                <control type="label">
                    <posx>340</posx>
                    <posy>0</posy>
                    <width>80</width>
                    <height>{{ vscale(100) }}</height>
                    <font>font10</font>
                    <align>right</align>
                    <aligny>center</aligny>
                    <textcolor>D8FFFFFF</textcolor>
                    <label>[B]$INFO[ListItem.Property(track.duration)][/B]</label>
                </control>
                <control type="image">
                    <visible>String.IsEmpty(ListItem.Property(is.footer))</visible>
                    <posx>0</posx>
                    <posy>{{ vscale(97) }}</posy>
                    <width>420</width>
                    <height>{{ vscale(2) }}</height>
                    <texture>script.plex/white-square.png</texture>
                    <colordiffuse>40000000</colordiffuse>
                </control>
            </control>
        </itemlayout>

        <!-- FOCUSED LAYOUT ####################################### -->
        <focusedlayout height="{{ vscale(100) }}">
            <control type="group">
                <control type="group">
                    <visible>!Control.HasFocus(101)</visible>
                    <posx>20</posx>
                    <posy>{{ vscale(24) }}</posy>
                    <control type="label">
                        <visible>!String.IsEqual(ListItem.Property(track.ID),Window(10000).Property(script.plex.track.ID))</visible>
                        <posx>0</posx>
                        <posy>0</posy>
                        <width>40</width>
                        <height>{{ vscale(100) }}</height>
                        <font>font10</font>
                        <align>center</align>
                        <aligny>center</aligny>
                        <textcolor>D8FFFFFF</textcolor>
                        <label>[B]$INFO[ListItem.Property(track.number)][/B]</label>
                    </control>
                    <control type="image">
                        <visible>String.IsEqual(ListItem.Property(track.ID),Window(10000).Property(script.plex.track.ID))</visible>
                        <posx>2</posx>
                        <posy>{{ vscale(32.5) }}</posy>
                        <width>35</width>
                        <height>{{ vscale(35) }}</height>
                        <texture>script.plex/indicators/playing-circle.png</texture>
                        <colordiffuse>FFE5A00D</colordiffuse>
                    </control>
                    <control type="image">
                        <posx>52</posx>
                        <posy>{{ vscale(11) }}</posy>
                        <width>74</width>
                        <height>{{ vscale(74) }}</height>
                        <texture>$INFO[ListItem.Thumb]</texture>
                        <aspectratio>scale</aspectratio>
                    </control>
                    <control type="group">
                        <posx>142</posx>
                        <posy>0</posy>
                        <control type="label">
                            <posx>0</posx>
                            <posy>{{ vscale(15) }}</posy>
                            <width>190</width>
                            <height>{{ vscale(30) }}</height>
                            <font>font10</font>
                            <align>left</align>
                            <aligny>center</aligny>
                            <textcolor>FFFFFFFF</textcolor>
                            <label>[B]$INFO[ListItem.Label][/B]</label>
                        </control>
                        <control type="label">
                            <posx>0</posx>
                            <posy>{{ vscale(50) }}</posy>
                            <width>190</width>
                            <height>{{ vscale(30) }}</height>
                            <font>font10</font>
                            <align>left</align>
                            <aligny>center</aligny>
                            <textcolor>B8FFFFFF</textcolor>
                            <label>$INFO[ListItem.Label2]</label>
                        </control>
                    </control>
                    <control type="label">
                        <posx>340</posx>
                        <posy>0</posy>
                        <width>80</width>
                        <height>{{ vscale(100) }}</height>
                        <font>font10</font>
                        <align>right</align>
                        <aligny>center</aligny>
                        <textcolor>D8FFFFFF</textcolor>
                        <label>[B]$INFO[ListItem.Property(track.duration)][/B]</label>
                    </control>
                    <control type="image">
                        <visible>String.IsEmpty(ListItem.Property(is.footer))</visible>
                        <posx>0</posx>
                        <posy>{{ vscale(97) }}</posy>
                        <width>420</width>
                        <height>{{ vscale(2) }}</height>
                        <texture>script.plex/white-square.png</texture>
                        <colordiffuse>40000000</colordiffuse>
                    </control>
                </control>

                <control type="group">
                    <visible>Control.HasFocus(101)</visible>
                    <posx>20</posx>
                    <posy>{{ vscale(21) }}</posy>
                    <control type="image">
                        <posx>-40</posx>
                        <posy>{{ vscale(-40) }}</posy>
                        <width>500</width>
                        <height>{{ vscale(180) }}</height>
                        <texture border="40">script.plex/square-rounded-shadow.png</texture>
                    </control>
                    <control type="image">
                        <posx>0</posx>
                        <posy>0</posy>
                        <width>420</width>
                        <height>{{ vscale(100) }}</height>
                        <texture border="12">script.plex/white-square-rounded.png</texture>
                        <colordiffuse>FFE5A00D</colordiffuse>
                    </control>
                    <control type="label">
                        <visible>!String.IsEqual(ListItem.Property(track.ID),Window(10000).Property(script.plex.track.ID))</visible>
                        <posx>0</posx>
                        <posy>0</posy>
                        <width>40</width>
                        <height>{{ vscale(100) }}</height>
                        <font>font12</font>
                        <align>center</align>
                        <aligny>center</aligny>
                        <textcolor>B8000000</textcolor>
                        <label>[B]$INFO[ListItem.Property(track.number)][/B]</label>
                    </control>
                    <control type="image">
                        <visible>String.IsEqual(ListItem.Property(track.ID),Window(10000).Property(script.plex.track.ID))</visible>
                        <posx>2</posx>
                        <posy>{{ vscale(32.5) }}</posy>
                        <width>35</width>
                        <height>{{ vscale(35) }}</height>
                        <texture>script.plex/indicators/playing-circle.png</texture>
                        <colordiffuse>FF000000</colordiffuse>
                    </control>
                    <control type="image">
                        <posx>52</posx>
                        <posy>0</posy>
                        <width>100</width>
                        <height>{{ vscale(100) }}</height>
                        <texture>$INFO[ListItem.Thumb]</texture>
                        <aspectratio>scale</aspectratio>
                    </control>
                    <control type="group">
                        <posx>164</posx>
                        <posy>0</posy>
                        <control type="label">
                            <posx>0</posx>
                            <posy>{{ vscale(16) }}</posy>
                            <width>160</width>
                            <height>{{ vscale(30) }}</height>
                            <font>font12</font>
                            <align>left</align>
                            <aligny>center</aligny>
                            <textcolor>DF000000</textcolor>
                            <label>[B]$INFO[ListItem.Label][/B]</label>
                        </control>
                        <control type="label">
                            <posx>0</posx>
                            <posy>{{ vscale(51) }}</posy>
                            <width>160</width>
                            <height>{{ vscale(30) }}</height>
                            <font>font10</font>
                            <align>left</align>
                            <aligny>center</aligny>
                            <textcolor>98000000</textcolor>
                            <label>$INFO[ListItem.Label2]</label>
                        </control>
                    </control>
                    <control type="label">
                        <posx>332</posx>
                        <posy>0</posy>
                        <width>80</width>
                        <height>{{ vscale(100) }}</height>
                        <font>font12</font>
                        <align>right</align>
                        <aligny>center</aligny>
                        <textcolor>B8000000</textcolor>
                        <label>[B]$INFO[ListItem.Property(track.duration)][/B]</label>
                    </control>
                </control>
            </control>
        </focusedlayout>
    </control>

    <control type="scrollbar" id="152">
        <hitrect x="428" y="33" w="52" h="1014" />
        <left>448</left>
        <top>33</top>
        <width>12</width>
        <height>1014</height>
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
