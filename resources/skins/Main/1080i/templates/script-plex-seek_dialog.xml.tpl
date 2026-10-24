{% extends "base.xml.tpl" %}
{% block headers %}
    <defaultcontrol>800</defaultcontrol>
    <zorder>100</zorder>
{% endblock %}
{% block backgroundcolor %}{% endblock %}

{% block controls %}
<control type="group" id="804">
    <visible>!String.IsEmpty(Window.Property(show.blackout))</visible>
    <animation effect="fade" time="200" delay="200" end="0">Hidden</animation>
    <control type="image">
        <posx>0</posx>
        <posy>0</posy>
        <width>1920</width>
        <height>1080</height>
        <texture>script.plex/white-square.png</texture>
        <colordiffuse>FF000000</colordiffuse>
    </control>
</control>

<control type="group" id="802">
    <!-- This is the buttonless OSD -->
    <visible>[!String.IsEmpty(Window.Property(show.OSD)) | [String.IsEmpty(Window.Property(is_plextuary)) + Window.IsVisible(seekbar)] | !String.IsEmpty(Window.Property(button.seek))] + !Window.IsVisible(osdvideosettings) + !Window.IsVisible(osdaudiosettings) + !Window.IsVisible(osdsubtitlesettings) + !Window.IsVisible(subtitlesearch) + !Window.IsActive(playerprocessinfo) + !Window.IsActive(selectdialog) + !Window.IsVisible(osdcmssettings)</visible>
    <animation effect="fade" time="200" delay="200" end="0">Hidden</animation>

    <control type="group">
        <posx>0</posx>
        <posy>0</posy>
        <!-- Top/bottom shading: darkest at the screen edge, easing to nothing towards the centre
             (player-bar-fade.png is a white smoothstep alpha ramp; colordiffuse sets the edge darkness).
             Taller than the old flat 140px bars so the title and times still sit on most of the shade. -->
        <control type="image">
            <posx>0</posx>
            <posy>0</posy>
            <width>1920</width>
            <height>{{ vscale(240) }}</height>
            <texture>script.plex/player-bar-fade.png</texture>
            <colordiffuse>C0000000</colordiffuse>
        </control>
        <control type="image">
            <visible>String.IsEmpty(Window.Property(no.osd.hide_info)) | !String.IsEmpty(Window.Property(show.OSD))</visible>
            <posx>0</posx>
            <posy>{{ vscale(280) }}r</posy>
            <width>1920</width>
            <height>{{ vscale(280) }}</height>
            <texture flipy="true">script.plex/player-bar-fade.png</texture>
            <colordiffuse>C0000000</colordiffuse>
        </control>
    </control>

    <!-- The title, two lines (SeekDialog.setTitleLines()): osd.title in font30_title, white - a film's title, an
         episode's (or, its title hidden for spoilers, its show's) - and osd.subtitle under it in font10, "Ends at"'s
         grey: a film's year and runtime, an episode's S/E, show and runtime. The first line's capitals start where
         the old one-line font13 title's did (59: centred in 40-100), so its 36 box at 52 (Inter Bold 30's capitals
         22 high); the second's box under it at 89, about 11 below them. -->
    <control type="group">
        <posx>0</posx>
        <posy>{{ vscale(40) }}</posy>
        <control type="label">
            <posx>60</posx>
            <posy>{{ vscale(12) }}</posy>
            <width>1720</width>
            <height>{{ vscale(36) }}</height>
            <font>font30_title</font>
            <align>left</align>
            <aligny>center</aligny>
            <textcolor>FFFFFFFF</textcolor>
            <scroll>true</scroll>
            <scrollspeed>35</scrollspeed>
            <label>$INFO[Window.Property(osd.title)]</label>
        </control>
        <control type="label">
            <posx>60</posx>
            <posy>{{ vscale(49) }}</posy>
            <width>1720</width>
            <height>{{ vscale(30) }}</height>
            <font>font10</font>
            <align>left</align>
            <aligny>center</aligny>
            <textcolor>CCE9E6E7</textcolor>
            <label>$INFO[Window.Property(osd.subtitle)]</label>
        </control>
        <control type="label">
            <posx>1860</posx>
            <posy>0</posy>
            <width>300</width>
            <height>{{ vscale(60) }}</height>
            <font>font12</font>
            <align>right</align>
            <aligny>center</aligny>
            <textcolor>FFFFFFFF</textcolor>
            <label>$INFO[System.Time]</label>
        </control>
    </control>

    <!-- TIMES: the music player's (script-plex-music_player.xml.tpl, TIMES) - elapsed right-aligned
         in the 232px margin left of the bar, after the playback status icon, remaining left-aligned
         in the 192px one right of it, 20px clear of the bar's ends, font10 FFD2CCCE, in a 30px box at
         98r (2px above centred on the 85r bar). A right-aligned label's posx is its RIGHT edge
         (Kodi's control factory subtracts the width), hence tempo's 212. Direct play reads Kodi's player times; a transcode
         can't (it starts at an offset), so Python fills time.current/time.left/time.end instead.
         No leading zeros, and the hour only once there is one ("5:03", "1:05:03"), each time on its
         own - the remaining time can show an hour while the elapsed doesn't. Kodi has no "m:ss" time
         format, so direct play pairs Player.Time(m) (minutes in the hour, unpadded) with
         Player.Time(ss) under the hour and uses h:mm:ss from it, keyed on the value's own hh, as the
         music player does on the track's duration; Player.HasVideo keeps the literal ":" and "-"
         from showing on their own. Transcodes get the same from util.simplifiedTimeDisplay().
         While seeking (button.seek) both show the seek point's instead - time.seek.current and
         time.seek.left, from SeekDialog.updateProgress() - in place of the player's, and "Ends at"
         when playing on from there (time.seek.end).
         Tempo and "Ends at" sit one line lower (Ends at 10 further): tempo dimmed in the left margin, "Ends at" in the row
         hint's CCE9E6E7, right-aligned 20 from the screen's edge (1900) - a 24-hour "Ends at 23:45" (153) starts
         about where the remaining time does, and a 12-hour "Ends at 11:45 PM" (196, past the 172 margin) grows left
         under the bar's end, clear of it one line down. A scan's speed takes tempo's place while one runs
         (SeekDialog.showScanSpeed()): its direction's icon (scan.direction - indicators/osd-scan-forward.png and its
         mirror osd-scan-back.png, the user's forward, made white; none at 0x) then the speed (scan.label, "4x") in
         the seek times' FFD2CCCE, right-aligned together by a grouplist so the icon keeps to the text, 6 apart (a
         font10 space). The icon's glyph is the canvas's full width and 3/4 of its height, so a 22 box draws it 22 wide
         and 16.5 high, about font10's 17 digits, 4 down as the status icon.
         Like the bar and the buttons, they cross-fade with the card rows (501, 511) while either has focus. -->
    <control type="group">
        <visible>![Control.HasFocus(501) | Control.HasFocus(511)]</visible>
        <animation effect="fade" start="0" end="100" time="200">Visible</animation>
        <animation effect="fade" start="100" end="0" time="200">Hidden</animation>
        <posx>0</posx>
        <posy>{{ vscale(98) }}r</posy>
        <!-- The playback status - play or pause, white - left of the elapsed time, which is right-aligned to end
             20 clear of the bar (232). The icon stays put, centred at x 74, with room for the time to grow
             into (h:mm:ss, the widest, is 87 in font10 - Inter's digits are all 15, the colon 6 - so starts
             at 125). indicators/osd-play.png and osd-pause.png: the user's play-filled/pause-filled, made
             white, their glyphs the full 64 high - so a 22 box draws them 22 high (font10's digits are 17),
             the canvas (not the glyph) centred on 74 (73, then 1 right by eye) to keep the play triangle's own
             optical offset. 4 down centres the 22 on the 30 line. The seek marker matches the 22. -->
        <control type="image">
            <visible>Player.HasVideo + !Player.Paused + [String.IsEmpty(Window.Property(no.osd.hide_info)) | !String.IsEmpty(Window.Property(show.OSD))]</visible>
            <posx>63</posx>
            <posy>{{ vscale(4) }}</posy>
            <width>22</width>
            <height>{{ vscale(22) }}</height>
            <texture>script.plex/indicators/osd-play.png</texture>
            <colordiffuse>FFFFFFFF</colordiffuse>
        </control>
        <control type="image">
            <visible>Player.HasVideo + Player.Paused + [String.IsEmpty(Window.Property(no.osd.hide_info)) | !String.IsEmpty(Window.Property(show.OSD))]</visible>
            <posx>63</posx>
            <posy>{{ vscale(4) }}</posy>
            <width>22</width>
            <height>{{ vscale(22) }}</height>
            <texture>script.plex/indicators/osd-pause.png</texture>
            <colordiffuse>FFFFFFFF</colordiffuse>
        </control>
        <control type="label">
            <visible>Player.HasVideo + !String.IsEmpty(Window.Property(direct.play)) + String.IsEmpty(Window.Property(button.seek)) + String.IsEqual(Player.Time(hh),00) + [String.IsEmpty(Window.Property(no.osd.hide_info)) | !String.IsEmpty(Window.Property(show.OSD))]</visible>
            <posx>212</posx>
            <posy>0</posy>
            <width>172</width>
            <height>{{ vscale(30) }}</height>
            <font>font10</font>
            <align>right</align>
            <aligny>center</aligny>
            <textcolor>FFD2CCCE</textcolor>
            <label>$INFO[Player.Time(m)]:$INFO[Player.Time(ss)]</label>
        </control>
        <control type="label">
            <visible>Player.HasVideo + !String.IsEmpty(Window.Property(direct.play)) + String.IsEmpty(Window.Property(button.seek)) + !String.IsEqual(Player.Time(hh),00) + [String.IsEmpty(Window.Property(no.osd.hide_info)) | !String.IsEmpty(Window.Property(show.OSD))]</visible>
            <posx>212</posx>
            <posy>0</posy>
            <width>172</width>
            <height>{{ vscale(30) }}</height>
            <font>font10</font>
            <align>right</align>
            <aligny>center</aligny>
            <textcolor>FFD2CCCE</textcolor>
            <label>$INFO[Player.Time(h:mm:ss)]</label>
        </control>
        <control type="label">
            <visible>String.IsEmpty(Window.Property(direct.play)) + String.IsEmpty(Window.Property(button.seek)) + [String.IsEmpty(Window.Property(no.osd.hide_info)) | !String.IsEmpty(Window.Property(show.OSD))]</visible>
            <posx>212</posx>
            <posy>0</posy>
            <width>172</width>
            <height>{{ vscale(30) }}</height>
            <font>font10</font>
            <align>right</align>
            <aligny>center</aligny>
            <textcolor>FFD2CCCE</textcolor>
            <label>$INFO[Window.Property(time.current)]</label>
        </control>
        <control type="label">
            <visible>!String.IsEmpty(Window.Property(button.seek)) + [String.IsEmpty(Window.Property(no.osd.hide_info)) | !String.IsEmpty(Window.Property(show.OSD))]</visible>
            <posx>212</posx>
            <posy>0</posy>
            <width>172</width>
            <height>{{ vscale(30) }}</height>
            <font>font10</font>
            <align>right</align>
            <aligny>center</aligny>
            <textcolor>FFD2CCCE</textcolor>
            <label>$INFO[Window.Property(time.seek.current)]</label>
        </control>
        <control type="label">
            <visible>!String.IsEmpty(Window.Property(button.seek)) + [String.IsEmpty(Window.Property(no.osd.hide_info)) | !String.IsEmpty(Window.Property(show.OSD))]</visible>
            <posx>1748</posx>
            <posy>0</posy>
            <width>172</width>
            <height>{{ vscale(30) }}</height>
            <font>font10</font>
            <align>left</align>
            <aligny>center</aligny>
            <textcolor>FFD2CCCE</textcolor>
            <label>$INFO[Window.Property(time.seek.left),-]$INFO[Window.Property(time.add)]</label>
        </control>
        <control type="grouplist">
            <visible>!String.IsEmpty(Window.Property(scan.active))</visible>
            <posx>40</posx>
            <posy>{{ vscale(30) }}</posy>
            <width>172</width>
            <height>{{ vscale(30) }}</height>
            <orientation>horizontal</orientation>
            <align>right</align>
            <itemgap>6</itemgap>
            <usecontrolcoords>true</usecontrolcoords>
            <control type="image">
                <visible>String.IsEqual(Window.Property(scan.direction),forward)</visible>
                <posy>{{ vscale(4) }}</posy>
                <width>22</width>
                <height>{{ vscale(22) }}</height>
                <texture>script.plex/indicators/osd-scan-forward.png</texture>
                <colordiffuse>FFD2CCCE</colordiffuse>
            </control>
            <control type="image">
                <visible>String.IsEqual(Window.Property(scan.direction),back)</visible>
                <posy>{{ vscale(4) }}</posy>
                <width>22</width>
                <height>{{ vscale(22) }}</height>
                <texture>script.plex/indicators/osd-scan-back.png</texture>
                <colordiffuse>FFD2CCCE</colordiffuse>
            </control>
            <control type="label">
                <width>auto</width>
                <height>{{ vscale(30) }}</height>
                <font>font10</font>
                <aligny>center</aligny>
                <textcolor>FFD2CCCE</textcolor>
                <label>$INFO[Window.Property(scan.label)]</label>
            </control>
        </control>
        <control type="label">
            <visible>Player.IsTempo + String.IsEmpty(Window.Property(scan.active))</visible>
            <posx>212</posx>
            <posy>{{ vscale(30) }}</posy>
            <width>172</width>
            <height>{{ vscale(30) }}</height>
            <font>font10</font>
            <align>right</align>
            <aligny>center</aligny>
            <textcolor>99D2CCCE</textcolor>
            <label>$INFO[Player.PlaySpeed]x</label>
        </control>
        <control type="label">
            <visible>Player.HasVideo + !String.IsEmpty(Window.Property(direct.play)) + String.IsEmpty(Window.Property(button.seek)) + String.IsEqual(Player.TimeRemaining(hh),00) + [String.IsEmpty(Window.Property(no.osd.hide_info)) | !String.IsEmpty(Window.Property(show.OSD))]</visible>
            <posx>1748</posx>
            <posy>0</posy>
            <width>172</width>
            <height>{{ vscale(30) }}</height>
            <font>font10</font>
            <align>left</align>
            <aligny>center</aligny>
            <textcolor>FFD2CCCE</textcolor>
            <label>-$INFO[Player.TimeRemaining(m)]:$INFO[Player.TimeRemaining(ss)]$INFO[Window.Property(time.add)]</label>
        </control>
        <control type="label">
            <visible>Player.HasVideo + !String.IsEmpty(Window.Property(direct.play)) + String.IsEmpty(Window.Property(button.seek)) + !String.IsEqual(Player.TimeRemaining(hh),00) + [String.IsEmpty(Window.Property(no.osd.hide_info)) | !String.IsEmpty(Window.Property(show.OSD))]</visible>
            <posx>1748</posx>
            <posy>0</posy>
            <width>172</width>
            <height>{{ vscale(30) }}</height>
            <font>font10</font>
            <align>left</align>
            <aligny>center</aligny>
            <textcolor>FFD2CCCE</textcolor>
            <label>$INFO[Player.TimeRemaining(h:mm:ss),-]$INFO[Window.Property(time.add)]</label>
        </control>
        <control type="label">
            <visible>String.IsEmpty(Window.Property(direct.play)) + String.IsEmpty(Window.Property(button.seek)) + [String.IsEmpty(Window.Property(no.osd.hide_info)) | !String.IsEmpty(Window.Property(show.OSD))]</visible>
            <posx>1748</posx>
            <posy>0</posy>
            <width>172</width>
            <height>{{ vscale(30) }}</height>
            <font>font10</font>
            <align>left</align>
            <aligny>center</aligny>
            <textcolor>FFD2CCCE</textcolor>
            <label>$INFO[Window.Property(time.left),-]</label>
        </control>
        <control type="label">
            <visible>!String.IsEmpty(Window.Property(media.show_ends)) + !String.IsEmpty(Window.Property(direct.play)) + String.IsEmpty(Window.Property(button.seek)) + [String.IsEmpty(Window.Property(no.osd.hide_info)) | !String.IsEmpty(Window.Property(show.OSD))]</visible>
            <posx>1900</posx>
            <posy>{{ vscale(40) }}</posy>
            <width>300</width>
            <height>{{ vscale(30) }}</height>
            <font>font10</font>
            <align>right</align>
            <aligny>center</aligny>
            <textcolor>CCE9E6E7</textcolor>
            <label>$INFO[Window.Property(time.ends_label)] $INFO[Player.FinishTime($INFO[Window.Property(time.fmt.ends)])]</label>
        </control>
        <control type="label">
            <visible>!String.IsEmpty(Window.Property(media.show_ends)) + String.IsEmpty(Window.Property(direct.play)) + String.IsEmpty(Window.Property(button.seek)) + [String.IsEmpty(Window.Property(no.osd.hide_info)) | !String.IsEmpty(Window.Property(show.OSD))]</visible>
            <posx>1900</posx>
            <posy>{{ vscale(40) }}</posy>
            <width>300</width>
            <height>{{ vscale(30) }}</height>
            <font>font10</font>
            <align>right</align>
            <aligny>center</aligny>
            <textcolor>CCE9E6E7</textcolor>
            <label>$INFO[Window.Property(time.ends_label)] $INFO[Window.Property(time.end)]</label>
        </control>
        <control type="label">
            <visible>!String.IsEmpty(Window.Property(media.show_ends)) + !String.IsEmpty(Window.Property(button.seek)) + [String.IsEmpty(Window.Property(no.osd.hide_info)) | !String.IsEmpty(Window.Property(show.OSD))]</visible>
            <posx>1900</posx>
            <posy>{{ vscale(40) }}</posy>
            <width>300</width>
            <height>{{ vscale(30) }}</height>
            <font>font10</font>
            <align>right</align>
            <aligny>center</aligny>
            <textcolor>CCE9E6E7</textcolor>
            <label>$INFO[Window.Property(time.ends_label)] $INFO[Window.Property(time.seek.end)]</label>
        </control>
    </control>

    <!-- SEEKBAR: the music player's bar (script-plex-music_player.xml.tpl, see its SEEKBAR comment
         for the mask/<reveal> recipe) - from x 232 to 1728 (1496: the music player's 80% of the screen,
         less 40 on the left for the playback status icon beside the elapsed time), 8px tall,
         40FFFFFF track, rounded by masks/seekbar-mask-1496.png (the 1536 one's end caps). Every fill is an info-less
         <reveal> progress control set from Python with setPercent() (setBarPercent(),
         seekdialog.py): a transcode starts at an offset Kodi's Player.Progress doesn't know about.
         Layers, bottom up: buffer (206, direct play only), the played portion - gold (201), at rest -
         and while seeking (button.seek) in its place the gold scrubber (200) to the seek point.
         Focusing the timeline alone isn't seeking: only its left/right start that, so
         until then it looks as it does at rest. Python's BAR_X/BAR_RIGHT/SEEK_IMAGE_WIDTH must match
         232/1496. Cross-fades with the card rows (501, 511) while either has focus.
         The buffer and played fills end round: each stops 4 short of its point and a 4x8 half circle
         (indicators/seekbar-cap.png, drawn at 4x) in its colour butts up against it, ending at the point -
         butted rather than overlapping, or the translucent buffer would show a brighter seam. Kodi's own
         righttexture would round it only by stretching the fill's texture, mask and all. Python places
         the caps (setBarPercent()); under 4 played there's no cap, the bar's own rounded end doing it. The
         scrubber has none: its end is always under the seek marker. -->
    <control type="group">
        <visible>![Control.HasFocus(501) | Control.HasFocus(511)]</visible>
        <animation effect="fade" start="0" end="100" time="200">Visible</animation>
        <animation effect="fade" start="100" end="0" time="200">Hidden</animation>
        <posx>232</posx>
        <posy>{{ vscale(85) }}r</posy>
        <control type="image">
            <visible>String.IsEmpty(Window.Property(no.osd.hide_info)) | !String.IsEmpty(Window.Property(show.OSD))</visible>
            <posx>0</posx>
            <posy>0</posy>
            <width>1496</width>
            <height>{{ vscale(8) }}</height>
            <texture diffuse="script.plex/masks/seekbar-mask-1496.png">script.plex/white-square.png</texture>
            <colordiffuse>40FFFFFF</colordiffuse>
        </control>
        <control type="progress" id="206">
            <visible>!String.IsEmpty(Window.Property(show.buffer)) + [String.IsEmpty(Window.Property(no.osd.hide_info)) | !String.IsEmpty(Window.Property(show.OSD))]</visible>
            <description>Buffer</description>
            <posx>0</posx>
            <posy>0</posy>
            <width>1496</width>
            <height>{{ vscale(8) }}</height>
            <reveal>true</reveal>
            <texturebg>script.plex/transparent-6px.png</texturebg>
            <lefttexture>-</lefttexture>
            <midtexture diffuse="script.plex/masks/seekbar-mask-1496.png">script.plex/white-square-6px.png</midtexture>
            <righttexture>-</righttexture>
            <overlaytexture>-</overlaytexture>
            <colordiffuse>40FFFFFF</colordiffuse>
        </control>
        <!-- The buffer's rounded end (SeekDialog.setBarPercent() places it) -->
        <control type="image" id="210">
            <visible>!String.IsEmpty(Window.Property(show.buffer)) + [String.IsEmpty(Window.Property(no.osd.hide_info)) | !String.IsEmpty(Window.Property(show.OSD))]</visible>
            <posx>0</posx>
            <posy>2000</posy>
            <width>4</width>
            <height>{{ vscale(8) }}</height>
            <texture>script.plex/indicators/seekbar-cap.png</texture>
            <colordiffuse>40FFFFFF</colordiffuse>
        </control>
        <control type="progress" id="201">
            <visible>String.IsEmpty(Window.Property(button.seek)) + [String.IsEmpty(Window.Property(no.osd.hide_info)) | !String.IsEmpty(Window.Property(show.OSD))]</visible>
            <description>Progressbar</description>
            <posx>0</posx>
            <posy>0</posy>
            <width>1496</width>
            <height>{{ vscale(8) }}</height>
            <reveal>true</reveal>
            <texturebg>script.plex/transparent-6px.png</texturebg>
            <lefttexture>-</lefttexture>
            <midtexture diffuse="script.plex/masks/seekbar-mask-1496.png">script.plex/white-square-6px.png</midtexture>
            <righttexture>-</righttexture>
            <overlaytexture>-</overlaytexture>
            <colordiffuse>FFE5A00D</colordiffuse>
        </control>
        <!-- The played portion's rounded end (SeekDialog.setBarPercent() places it) -->
        <control type="image" id="208">
            <visible>String.IsEmpty(Window.Property(button.seek)) + [String.IsEmpty(Window.Property(no.osd.hide_info)) | !String.IsEmpty(Window.Property(show.OSD))]</visible>
            <posx>0</posx>
            <posy>2000</posy>
            <width>4</width>
            <height>{{ vscale(8) }}</height>
            <texture>script.plex/indicators/seekbar-cap.png</texture>
            <colordiffuse>FFE5A00D</colordiffuse>
        </control>
        <control type="progress" id="200">
            <visible>!String.IsEmpty(Window.Property(button.seek)) + [String.IsEmpty(Window.Property(no.osd.hide_info)) | !String.IsEmpty(Window.Property(show.OSD))]</visible>
            <animation effect="fade" time="100" delay="100" end="100">Visible</animation>
            <description>Scrubber</description>
            <posx>0</posx>
            <posy>0</posy>
            <width>1496</width>
            <height>{{ vscale(8) }}</height>
            <reveal>true</reveal>
            <texturebg>script.plex/transparent-6px.png</texturebg>
            <lefttexture>-</lefttexture>
            <midtexture diffuse="script.plex/masks/seekbar-mask-1496.png">script.plex/white-square-6px.png</midtexture>
            <righttexture>-</righttexture>
            <overlaytexture>-</overlaytexture>
            <colordiffuse>FFE5A00D</colordiffuse>
        </control>
    </control>
</control>
<control type="button" id="800">
    <visible allowhiddenfocus="true">String.IsEmpty(Window.Property(show.OSD))</visible>
    <posx>0</posx>
    <posy>0</posy>
    <width>1920</width>
    <height>1080</height>
    <texturefocus>-</texturefocus>
    <texturenofocus>-</texturenofocus>
    <label> </label>
    <onclick condition="String.IsEmpty(Window.Property(button.seek)) + String.IsEmpty(Window.Property(marker.countdown)) + !String.IsEmpty(Window.Property(mouse.mode))">SetProperty(show.OSD,1)</onclick>
</control>

<!-- PPI -->
<control type="group" id="803">
    <bottom>0</bottom>
    <height>{{ vscale(350) }}</height>
    <visible>!String.IsEmpty(Window.Property(show.PPI)) + String.IsEmpty(Window.Property(settings.visible))</visible>
    <animation effect="fade" start="0" end="100" time="300">Visible</animation>
    <animation effect="fade" start="100" end="0" time="200">Hidden</animation>
    <control type="image">
        <left>10</left>
        <top>{{ vscale(-220) }}</top>
        <right>10</right>
        <height>{{ vscale(420) }}</height>
        <texture border="40">buttons/dialogbutton-nofo.png</texture>
    </control>
    <control type="grouplist">
        <left>52</left>
        <top>{{ vscale(-184) }}</top>
        <width>1786</width>
        <height>{{ vscale(350) }}</height>
        <orientation>horizontal</orientation>
        <itemgap>10</itemgap>
        <control type="grouplist">
            <left>0</left>
            <top>0</top>
            <width>793</width>
            <control type="label">
                <width>793</width>
                <height>{{ vscale(50) }}</height>
                <aligny>bottom</aligny>
                <label>$INFO[Player.Process(videodecoder),[COLOR FFE5A00D]$LOCALIZE[31139]:[/COLOR] ]$VAR[VideoHWDecoder, (,)]</label>
                <font>font14</font>
                <shadowcolor>black</shadowcolor>
                <visible>Player.HasVideo</visible>
            </control>
            <control type="label">
                <width>793</width>
                <height>{{ vscale(50) }}</height>
                <aligny>bottom</aligny>
                <label>$INFO[Player.Process(pixformat),[COLOR FFE5A00D]$LOCALIZE[31140]:[/COLOR] ]</label>
                <font>font14</font>
                <shadowcolor>black</shadowcolor>
                <visible>Player.HasVideo</visible>
            </control>
            <control type="label">
                <width>793</width>
                <height>{{ vscale(50) }}</height>
                <aligny>bottom</aligny>
                <label>$INFO[Player.Process(deintmethod),[COLOR FFE5A00D]$LOCALIZE[16038]:[/COLOR] ]</label>
                <font>font14</font>
                <shadowcolor>black</shadowcolor>
                <visible>Player.HasVideo</visible>
            </control>
            <control type="label">
                <width>793</width>
                <height>{{ vscale(50) }}</height>
                <aligny>bottom</aligny>
                <label>$INFO[Player.Process(videowidth),[COLOR FFE5A00D]$LOCALIZE[38031]:[/COLOR] ,x]$INFO[Player.Process(videoheight),, px]$INFO[Player.Process(videodar),$COMMA , AR]$INFO[Player.Process(videofps),$COMMA , FPS]</label>
                <font>font14</font>
                <shadowcolor>black</shadowcolor>
                <visible>Player.HasVideo</visible>
            </control>
            <control type="textbox">
                <width>793</width>
                <height>{{ vscale(50) }}</height>
                <aligny>bottom</aligny>
                <autoscroll delay="1000" time="1000" repeat="2000"></autoscroll>
                <label>[COLOR FFE5A00D]$LOCALIZE[460]:[/COLOR] $INFO[Player.Process(audiochannels),,$COMMA ]$INFO[Player.Process(audiodecoder)]$INFO[Player.Process(audiobitspersample),$COMMA , bits]$INFO[Player.Process(audiosamplerate),$COMMA , Hz]</label>
                <font>font14</font>
                <shadowcolor>black</shadowcolor>
            </control>
            <control type="label">
                <width>793</width>
                <height>{{ vscale(50) }}</height>
                <aligny>bottom</aligny>
                <label>$INFO[System.Memory(used.percent),[COLOR FFE5A00D]$LOCALIZE[31030]:[/COLOR] ,]</label>
                <font>font14</font>
                <shadowcolor>black</shadowcolor>
            </control>
        </control>
        <control type="grouplist">
            <left>0</left>
            <top>0</top>
            <height>{{ vscale(350) }}</height>
            <width>993</width>
            <control type="label">
                <width>963</width>
                <height>{{ vscale(50) }}</height>
                <aligny>bottom</aligny>
                <label>$INFO[Window.Property(ppi.Status)]</label>
                <font>font14</font>
                <shadowcolor>black</shadowcolor>
                <visible>Player.HasVideo + !String.IsEmpty(Window.Property(ppi.Status))</visible>
            </control>
            <control type="label">
                <width>963</width>
                <height>{{ vscale(50) }}</height>
                <aligny>bottom</aligny>
                <label>[COLOR FFE5A00D]Mode:[/COLOR] $INFO[Window.Property(ppi.Mode)]</label>
                <font>font14</font>
                <shadowcolor>black</shadowcolor>
                <visible>Player.HasVideo + !String.IsEmpty(Window.Property(ppi.Mode))</visible>
            </control>
            <control type="label">
                <width>963</width>
                <height>{{ vscale(50) }}</height>
                <aligny>bottom</aligny>
                <label>[COLOR FFE5A00D]Container:[/COLOR] $INFO[Window.Property(ppi.Container)]</label>
                <font>font14</font>
                <shadowcolor>black</shadowcolor>
                <visible>Player.HasVideo + !String.IsEmpty(Window.Property(ppi.Container))</visible>
            </control>
            <control type="textbox">
                <width>963</width>
                <autoscroll delay="1000" time="1000" repeat="2000"></autoscroll>
                <height>{{ vscale(50) }}</height>
                <aligny>bottom</aligny>
                <label>[COLOR FFE5A00D]Video:[/COLOR] $INFO[Window.Property(ppi.Video)]</label>
                <font>font14</font>
                <shadowcolor>black</shadowcolor>
                <visible>Player.HasVideo + !String.IsEmpty(Window.Property(ppi.Video))</visible>
            </control>
            <control type="textbox">
                <width>963</width>
                <autoscroll delay="1000" time="1000" repeat="2000"></autoscroll>
                <height>{{ vscale(50) }}</height>
                <aligny>bottom</aligny>
                <label>$INFO[Window.Property(ppi.Audio),[COLOR FFE5A00D]Audio:[/COLOR] ]$INFO[Window.Property(ppi.Subtitles),   [COLOR FFE5A00D]Subtitle:[/COLOR] ]</label>
                <font>font14</font>
                <shadowcolor>black</shadowcolor>
                <visible>Player.HasVideo + [!String.IsEmpty(Window.Property(ppi.Audio)) | !String.IsEmpty(Window.Property(ppi.Subtitles))]</visible>
            </control>
            <control type="textbox">
                <width>963</width>
                <autoscroll delay="1000" time="1000" repeat="2000"></autoscroll>
                <height>{{ vscale(50) }}</height>
                <aligny>bottom</aligny>
                <label>[COLOR FFE5A00D]Server:[/COLOR] $INFO[Window.Property(ppi.User)]</label>
                <font>font14</font>
                <shadowcolor>black</shadowcolor>
                <visible>Player.HasVideo + !String.IsEmpty(Window.Property(ppi.User))</visible>
            </control>
            <control type="label">
                <width>963</width>
                <height>{{ vscale(50) }}</height>
                <aligny>bottom</aligny>
                <label>[COLOR FFE5A00D]Buffer:[/COLOR] $INFO[Player.CacheLevel]%$INFO[Window.Property(ppi.BufferMB), (of ~, MB]$INFO[Window.Property(ppi.ReadFactor),$COMMA Readfactor: ,x)]$INFO[Window.Property(ppi.AReadFactor),$COMMA Readfactor: ,)]</label>
                <font>font14</font>
                <shadowcolor>black</shadowcolor>
                <visible>Player.HasVideo + String.IsEmpty(Window.Property(ppi.Buffered))</visible>
            </control>
            <control type="label">
                <width>963</width>
                <height>{{ vscale(50) }}</height>
                <aligny>bottom</aligny>
                <label>[COLOR FFE5A00D]Buffer:[/COLOR] $INFO[Window.Property(ppi.Buffered)]% (% of Video cached)$INFO[Window.Property(ppi.BufferMB), (of ~, MB]$INFO[Window.Property(ppi.ReadFactor),$COMMA Readfactor:,x)]$INFO[Window.Property(ppi.AReadFactor),$COMMA Readfactor: ,)]</label>
                <font>font14</font>
                <shadowcolor>black</shadowcolor>
                <visible>Player.HasVideo + !String.IsEmpty(Window.Property(ppi.Buffered))</visible>
            </control>
        </control>
    </control>
    <control type="label">
        <left>52</left>
        <top>{{ vscale(120) }}</top>
        <width>1786</width>
        <height>{{ vscale(50) }}</height>
        <aligny>bottom</aligny>
        <label>$INFO[System.CpuUsage,[COLOR FFE5A00D]$LOCALIZE[13271][/COLOR] ]</label>
        <font>font14</font>
        <shadowcolor>black</shadowcolor>
    </control>
</control>
<control type="group" id="300">
    <visible>!String.IsEmpty(Window.Property(has.bif)) + !String.IsEmpty(Window.Property(bif.image)) + !String.IsEmpty(Window.Property(button.seek)) + [String.IsEmpty(Window.Property(no.osd.hide_info)) | !String.IsEmpty(Window.Property(show.OSD))]</visible>
    <animation effect="fade" time="100" delay="100" end="100">Visible</animation>
    <posx>0</posx>
    <!-- The size of the OSD's card rows' art (includes/osd_card_row.xml.tpl), 300x168, and rounded as it is, with
         masks/ar16x9-mask-300.png (corners 11); in a 2px black frame, 304x172, masked the same so it follows the
         curve. Above the buttons (909-979), 16 clear: 893 - 172. Python's setPosition() keeps this y, and slides it
         along the bar by the frame's width (SeekDialog.BIF_WIDTH). -->
    <posy>721</posy>
    <control type="image">
        <posx>0</posx>
        <posy>0</posy>
        <width>304</width>
        <height>{{ vscale(172) }}</height>
        <texture diffuse="script.plex/masks/ar16x9-mask-300.png">script.plex/white-square.png</texture>
        <colordiffuse>FF000000</colordiffuse>
    </control>
    <control type="image">
        <posx>2</posx>
        <posy>{{ vscale(2) }}</posy>
        <width>300</width>
        <height>{{ vscale(168) }}</height>
        <fadetime>10</fadetime>
        <texture diffuse="script.plex/masks/ar16x9-mask-300.png">$INFO[Window.Property(bif.image)]</texture>
        <!-- Preview pictures come at the film's own shape (320x132 for a 1920x800 file): fitted whole, the frame's
             black showing above and below, as the film sits on a 16:9 screen. -->
        <aspectratio scalediffuse="false">keep</aspectratio>
    </control>
</control>
<control type="group" id="801">
    <!-- This is the OSD with buttons -->
    <visible>!String.IsEmpty(Window.Property(show.OSD)) + !Window.IsVisible(osdvideosettings) + !Window.IsVisible(osdaudiosettings) + !Window.IsVisible(osdsubtitlesettings) + !Window.IsVisible(subtitlesearch) + !Window.IsActive(playerprocessinfo) + !Window.IsActive(selectdialog) + !Window.IsVisible(osdcmssettings)</visible>
    <animation effect="fade" time="200" delay="200" end="0">Hidden</animation>

    <!-- Above the timeline: up from it reaches these, up again the skip button. Hidden while a card row has
         focus (the rows' up goes to the timeline, not here). Each is a 70 box with a background pill: the
         focused-button pill of Pre-play/Seasons/Episodes (episode_button_label.xml.tpl), brighter - 4DFFFFFF,
         white-square-rounded, 51 high from 10 down (7.5 above the 35 glyph, 8.5 below), 8 in from the box's
         left (9.5 from the glyph) and so 54 wide, 9.5 the glyph's right too. Pills 10 apart: itemgap -6 on the
         70 boxes (a 64 pitch, SeekDialog.BUTTON_PITCH). Right-aligned, the last pill ending 80 from the
         screen's right edge (1840): the boxes end 8 past it, at 1848 (SeekDialog.BUTTONS_RIGHT).
         Navigation is each button's own: in their groups they aren't the grouplist's children, so its own
         left/right/up don't reach them. Up to the skip button, down to the timeline, left/right to the neighbour
         with dead stops at the ends; Subtitles and VS10 carry their visibility themselves as well as on their
         groups, so Kodi passes over a hidden one (through its own onleft/onright) rather than focusing it unseen. -->
    <control type="grouplist" id="400">
        <visible allowhiddenfocus="true">![Control.HasFocus(501) | Control.HasFocus(511)]</visible>
        <animation effect="fade" start="0" end="100" time="200">Visible</animation>
        <animation effect="fade" start="100" end="0" time="200">Hidden</animation>
        <defaultcontrol>403</defaultcontrol>
        <hitrect x="648" y="914" w="1200" h="60" />
        <posx>648</posx>
        <posy>{{ vscale(171) }}r</posy>
        <width>1200</width>
        <height>{{ vscale(124) }}</height>
        <align>right</align>
        <onup>791</onup>
        <!-- 0, not the old -40: matches Episodes'/Seasons'/Pre-play's own button rows' itemgap
             exactly (theme.episodes/seasons/pre_play.buttongroup.itemgap, context.py), now that this
             row's own boxes match theirs too (see id 421's own comment below) - the old -40 overlap
             existed to compensate for how much dead transparent padding the OLD 125x101 boxes/icon
             set carried around a much smaller glyph; that reasoning no longer applies now these are
             the same 70x70/5-5-60-60 boxes those other rows already use unpadded. Left at -40 this
             would badly overlap (70-40=30 effective pitch) rather than just look distorted. -->
        <itemgap>-6</itemgap>
        <orientation>horizontal</orientation>
        <scrolltime tween="quadratic" easing="out">200</scrolltime>
        <usecontrolcoords>true</usecontrolcoords>
        <!-- Every button/icon-group box below is 70x70 (was 125x101, then a 2026-09-04 101x101
             interim square-only fix, now this) - matches Episodes'/Seasons'/Pre-play's own button
             box size exactly (theme.*.buttons, context.py), on request, since this row's icons are
             the same modern-folder set those rows already use at that size. Matching hitrects
             (x/y=5, w/h=60 - or x=35 for the posx=30 twin-icon slots below, same 30 offset added to
             the new 5 margin the old 58 added to the old 28 margin) mirror theme.*.buttons_hitrect
             exactly too. The original 125x101 box's own ~1.238 aspect ratio had almost exactly
             matched the OLD (pre-2026-09-04) icon set's 180x145 canvas (~1.241) - not a coincidence,
             it was sized to it - which is why a plain resize (not just a square fix) is what actually
             matches these icons' real, already-correct convention elsewhere, rather than an arbitrary
             new number. -->
        <control type="group">
            <width>70</width>
            <height>{{ vscale(70) }}</height>
            <!-- the background: Pre-play's/Seasons'/Episodes' focused-button pill (episode_button_label.xml.tpl),
                 brighter (30%, not 20%) -->
            <control type="image">
                <posx>8</posx>
                <posy>{{ vscale(10) }}</posy>
                <width>54</width>
                <height>{{ vscale(51) }}</height>
                <texture colordiffuse="4DFFFFFF" border="10">script.plex/white-square-rounded.png</texture>
            </control>
            <control type="button" id="403">
                <hitrect x="5" y="5" w="60" h="60" />
                <posx>0</posx>
                <posy>0</posy>
                <width>70</width>
                <height>{{ vscale(70) }}</height>
                <font>font12</font>
                <onup>791</onup>
                <ondown>100</ondown>
                <onleft>noop</onleft>
                <onright>412</onright>
                <texturefocus{% if theme.buttons.useFocusColor %} colordiffuse="{{ theme.buttons.focusColor|default("FFE5A00D") }}"{% endif %}>{{ theme.assets.buttons.base }}settings{{ theme.assets.buttons.focusSuffix }}.png</texturefocus>
                <texturenofocus colordiffuse="CCE9E6E7">{{ theme.assets.buttons.base }}settings.png</texturenofocus>
                <label> </label>
            </control>
        </control>



        <!-- There's no Play/Pause button: OK on the timeline plays/pauses. Repeat and Shuffle are in the
             Settings dialog (playersettings.py), under Quality. -->
        <control type="group">
            <visible>!String.IsEmpty(Window.Property(nav.quick_subtitles))</visible>
            <width>70</width>
            <height>{{ vscale(70) }}</height>
            <!-- the background: Pre-play's/Seasons'/Episodes' focused-button pill (episode_button_label.xml.tpl),
                 brighter (30%, not 20%) -->
            <control type="image">
                <posx>8</posx>
                <posy>{{ vscale(10) }}</posy>
                <width>54</width>
                <height>{{ vscale(51) }}</height>
                <texture colordiffuse="4DFFFFFF" border="10">script.plex/white-square-rounded.png</texture>
            </control>
            <control type="button" id="412">
                <visible>!String.IsEmpty(Window.Property(nav.quick_subtitles))</visible>
                <hitrect x="5" y="5" w="60" h="60" />
                <posx>0</posx>
                <posy>0</posy>
                <width>70</width>
                <height>{{ vscale(70) }}</height>
                <font>font12</font>
                <onup>791</onup>
                <ondown>100</ondown>
                <onleft>403</onleft>
                <onright>413</onright>
                <texturefocus{% if theme.buttons.useFocusColor %} colordiffuse="{{ theme.buttons.focusColor|default("FFE5A00D") }}"{% endif %}>{{ theme.assets.buttons.base }}subtitle{{ theme.assets.buttons.focusSuffix }}.png</texturefocus>
                <texturenofocus colordiffuse="CCE9E6E7">{{ theme.assets.buttons.base }}subtitle.png</texturenofocus>
                <label> </label>
            </control>
        </control>

        <!-- VS10 mode switcher: nav.vs10 (seekdialog.py) - CoreELEC's VS10 builds (util.CE_VS10), unless
             "Show buttons" leaves it out. Opens the Settings dialog's VS10 Mode picker. -->
        <control type="group">
            <visible>!String.IsEmpty(Window.Property(nav.vs10))</visible>
            <width>70</width>
            <height>{{ vscale(70) }}</height>
            <!-- the background: Pre-play's/Seasons'/Episodes' focused-button pill (episode_button_label.xml.tpl),
                 brighter (30%, not 20%) -->
            <control type="image">
                <posx>8</posx>
                <posy>{{ vscale(10) }}</posy>
                <width>54</width>
                <height>{{ vscale(51) }}</height>
                <texture colordiffuse="4DFFFFFF" border="10">script.plex/white-square-rounded.png</texture>
            </control>
            <control type="button" id="413">
                <visible>!String.IsEmpty(Window.Property(nav.vs10))</visible>
                <hitrect x="5" y="5" w="60" h="60" />
                <posx>0</posx>
                <posy>0</posy>
                <width>70</width>
                <height>{{ vscale(70) }}</height>
                <font>font12</font>
                <onup>791</onup>
                <ondown>100</ondown>
                <onleft>412</onleft>
                <onright>noop</onright>
                <texturefocus{% if theme.buttons.useFocusColor %} colordiffuse="{{ theme.buttons.focusColor|default("FFE5A00D") }}"{% endif %}>script.plex/buttons/player/modern/vs10.png</texturefocus>
                <texturenofocus colordiffuse="CCE9E6E7">script.plex/buttons/player/modern/vs10.png</texturenofocus>
                <label> </label>
            </control>
        </control>
    </control>

    <!-- The timeline's focus target, over the SEEKBAR's 232/1496 bar: up to the buttons, down to the card rows.
         Its mouse area (SeekDialog.BAR_Y/BAR_BOTTOM match) stops short of the buttons above. -->
    <control type="group">
        <posx>232</posx>
        <posy>995</posy>
        <control type="button" id="100">
            <hitrect x="0" y="-15" w="1496" h="44" />
            <posx>0</posx>
            <posy>0</posy>
            <width>1496</width>
            <height>{{ vscale(10) }}</height>
            <!-- Settings, not the row: a grouplist goes back to the button it last had focus on -->
            <onup>403</onup>
            <ondown>501</ondown>
            <texturefocus>-</texturefocus>
            <texturenofocus>-</texturenofocus>
        </control>
    </control>

    <!-- The card rows below the timeline - see includes/osd_card_row.xml.tpl. Down from the timeline reaches the
         chapters, down again the play queue; either is passed over when empty. -->
    {% include "includes/osd_card_row.xml.tpl" with group_id=500 & list_id=501 & label_prop="chapters.label" & enable_prop="has.chapters" & onup=100 & ondown=511 & letterbox=True %}
    {% include "includes/osd_card_row.xml.tpl" with group_id=510 & list_id=511 & label_prop="queue.label" & enable_prop="has.queue" & onup=501 & ondown="noop" & letterbox=False %}

    <!-- ROW HINT: what's below, at the bottom of the OSD, centred - the card rows' headers and the down chevron
         (indicators/angle-small-down.png, the user's icon made white). From the buttons (or anywhere above the rows)
         it names both rows, or whichever exists; from the chapters, the play queue; from the play queue nothing, as
         nothing is below it. The text is SeekDialog.updateRowHint()'s rows.hint, not label variants chosen here by
         focus: those flipped the instant focus moved into a row, so the text vanished while the group - and the
         chevron - were still fading out; Python leaves it as it was when focus leaves for a row or for 800. Hidden
         with focus on 800 as well, or Back from the queue row would fade it in while the OSD fades out.
         A grouplist so the text and chevron centre together, the label sized to its text (auto). 1048-1072: below
         the timeline (995-1003; its times' second line, at the sides, 1012-1042), and just under the rows' second
         line when the chapters have focus. 24x24 chevron:
         its 38x20 glyph on a 64 canvas comes out about 14x8, the size of font8's (Inter 18) lower case. -->
    <control type="group">
        <visible>!Control.HasFocus(511) + !Control.HasFocus(800) + [!String.IsEmpty(Window.Property(has.queue)) | [!String.IsEmpty(Window.Property(has.chapters)) + !Control.HasFocus(501)]]</visible>
        <animation effect="fade" start="0" end="100" time="200">Visible</animation>
        <animation effect="fade" start="100" end="0" time="200">Hidden</animation>
        <control type="grouplist">
            <posx>0</posx>
            <posy>{{ vscale(1048) }}</posy>
            <width>1920</width>
            <height>{{ vscale(24) }}</height>
            <align>center</align>
            <itemgap>8</itemgap>
            <orientation>horizontal</orientation>
            <!-- so the chevron's posy applies: 2 down centres it on the text, which sits a little low in its box -->
            <usecontrolcoords>true</usecontrolcoords>
            <control type="label">
                <width>auto</width>
                <height>{{ vscale(24) }}</height>
                <font>font8</font>
                <aligny>center</aligny>
                <textcolor>CCE9E6E7</textcolor>
                <label>$INFO[Window.Property(rows.hint)]</label>
            </control>
            <control type="image">
                <posy>{{ vscale(2) }}</posy>
                <width>24</width>
                <height>{{ vscale(24) }}</height>
                <texture>script.plex/indicators/angle-small-down.png</texture>
                <colordiffuse>CCE9E6E7</colordiffuse>
            </control>
        </control>
    </control>
</control>
<!-- SEEK MARKER: a white dot on the bar at the seek point - or, with the timeline focused and not seeking,
     playback's - in place of the old time bubble above it (the times either side of the bar follow the seek
     point instead). 22 across, the playback status icon's size, centred on the bar: the bar runs 85r-77r
     (centre 81r), so the dot 92r-70r. The group's x is the point on the bar (SeekDialog.updateProgress()
     moves it there, keeping this y), the dot centred on it. indicators/seek-marker.png is drawn at 4x, 88px,
     to stay round at 4K. Under it a soft shadow, 2 down: seek-marker-shadow.png, the dot blurred by 3 in a
     34 box (6 clear each side), tinted black at 60%. -->
<control type="group" id="202">
    <visible>[Control.HasFocus(100) | !String.IsEmpty(Window.Property(button.seek))] + [String.IsEmpty(Window.Property(no.osd.hide_info)) | !String.IsEmpty(Window.Property(show.OSD))]</visible>
    <animation effect="fade" time="100" delay="100" end="100">Visible</animation>
    <posx>0</posx>
    <posy>{{ vscale(92) }}r</posy>
    <control type="image">
        <posx>-17</posx>
        <posy>{{ vscale(-4) }}</posy>
        <width>34</width>
        <height>{{ vscale(34) }}</height>
        <texture>script.plex/indicators/seek-marker-shadow.png</texture>
        <colordiffuse>99000000</colordiffuse>
    </control>
    <control type="image">
        <posx>-11</posx>
        <posy>0</posy>
        <width>22</width>
        <height>{{ vscale(22) }}</height>
        <texture>script.plex/indicators/seek-marker.png</texture>
        <colordiffuse>FFFFFFFF</colordiffuse>
    </control>
</control>

<!-- SKIP MARKER BUTTON -->
<!-- Above the buttons, which share the right of the screen with it: its foot at 909, 10 above their pills.
     Without the OSD it slides down to
     where it always sat (the pill's foot at 1000).
     Styled as the buttons are: their pill (4DFFFFFF, white-square-rounded, 51 high), font10 text in the row
     hint's CCE9E6E7 as their unfocused glyphs are, gold
     (the buttons' focus colour) when focused, 10 either side of it - the focused-button pill's text padding
     on Pre-play/Seasons/Episodes. Right edge at 1840 like the buttons' last pill, its foot 10 above their
     pills' tops (919). -->
<control type="grouplist" id="790">
    <visible>!String.IsEmpty(Window.Property(initialized))</visible>
    <ondown>403</ondown>
    <right>80</right>
    <top>858</top>
    <width>1670</width>
    <!-- 51 for the pill and 91 below it for the slide: a grouplist clips its children to its own box, so
         at the pill's own height the slid-down button was cut off entirely - shown with the OSD, never
         without it (it always had been, bar 3px: 143 high with a 100 slide) -->
    <height>{{ vscale(142) }}</height>
    <align>right</align>
    <orientation>horizontal</orientation>
    <control type="button" id="791">
        <visible>[[!String.IsEmpty(Window.Property(show.markerSkip)) + String.IsEmpty(Window.Property(show.markerSkip_OSDOnly))] | [!String.IsEmpty(Window.Property(show.markerSkip_OSDOnly)) + !String.IsEmpty(Window.Property(show.OSD))]] + ![Control.HasFocus(501) | Control.HasFocus(511)]</visible>
        <animation effect="fade" start="0" end="100" time="200">Visible</animation>
        <animation effect="fade" start="100" end="0" time="200">Hidden</animation>
        <!-- With the OSD shown, down goes to the buttons - always Settings, the first; with it hidden they can't
             take focus, and SeekDialog.onAction() opens the OSD (on the timeline) instead. -->
        <ondown>403</ondown>
        <!-- Down to its resting place without the OSD (the pill's foot at 1000), in two parts: 57 whenever the OSD
             is hidden, 34 more only when not seeking - a seek without the OSD shows the bar (995) and its times
             (982) there, so the pill stays 16 above them (966); that second part reverses, gliding it up and
             back. The grouplist is tall enough (142) to hold it either way. -->
        <animation type="Conditional" condition="String.IsEmpty(Window.Property(show.OSD)) + !Window.IsVisible(seekbar)" reversible="false">
            <effect type="slide" end="0,57" time="100" delay="100"></effect>
        </animation>
        <animation type="Conditional" condition="String.IsEmpty(Window.Property(show.OSD)) + !Window.IsVisible(seekbar) + String.IsEmpty(Window.Property(button.seek))" reversible="true">
            <effect type="slide" end="0,34" time="100" delay="100"></effect>
        </animation>
        <width>auto</width>
        <height>{{ vscale(51) }}</height>
        <align>center</align>
        <right>0</right>
        <top>0</top>
        <texturefocus colordiffuse="4DFFFFFF" border="10">script.plex/white-square-rounded.png</texturefocus>
        <texturenofocus colordiffuse="4DFFFFFF" border="10">script.plex/white-square-rounded.png</texturenofocus>
        <textoffsetx>10</textoffsetx>
        <aligny>center</aligny>
        <font>font10</font>
        <textcolor>CCE9E6E7</textcolor>
        <focusedcolor>{{ theme.buttons.focusColor|default('FFE5A00D') }}</focusedcolor>
        <label>$INFO[Window.Property(skipMarkerName)]</label>
    </control>
</control>
{% endblock controls %}