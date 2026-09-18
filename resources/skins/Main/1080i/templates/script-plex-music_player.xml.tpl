{% extends "base.xml.tpl" %}
{% block headers %}<defaultcontrol>406</defaultcontrol>{% endblock %}
{# Solid black, not the shared default_background include with Player.Art(landscape) as its hero
   layer: this screen shows the cover itself, so the art-derived backdrop only competed with it. #}
{% block backgroundcolor %}<backgroundcolor>0xff000000</backgroundcolor>{% endblock %}
{% block controls %}

<!-- COVER: 640x640, centred horizontally, top edge 10px above the header's bottom edge (group
     200 in default.xml.tpl is 135 tall). Rounded by the same masks/square-mask.png the Album screen's
     cover and the grid tiles use; fallback layer underneath for tracks with no art. -->
<control type="image">
    <posx>640</posx>
    <posy>{{ vscale(125) }}</posy>
    <width>640</width>
    <height>{{ vscale(640) }}</height>
    <texture diffuse="script.plex/masks/square-mask.png">script.plex/thumb_fallbacks/music.png</texture>
</control>
<control type="image">
    <posx>640</posx>
    <posy>{{ vscale(125) }}</posy>
    <width>640</width>
    <height>{{ vscale(640) }}</height>
    <texture background="true" diffuse="script.plex/masks/square-mask.png">$INFO[Player.Art(thumb)]</texture>
    <aspectratio scalediffuse="false">scale</aspectratio>
</control>

<!-- TRACK TEXT: centred under the cover, in the Album screen's hero-text treatment
     (script-plex-album.xml.tpl) - title in its album-name style (font45_title, FFD2CCCE,
     top-aligned 61px box, marquee), then artist and album on one line in its meta-line style
     (font10, FFD2CCCE, 30px box) 68 below the title's top, the same offset that screen uses
     between its title and artist lines. The bullet is the one albumMetaLine() (tracks.py) joins
     that screen's date and genres with; as an $INFO prefix it only renders when there's an album.
     posy=785: 20 below the cover's bottom edge (125 + 640); the meta line ends at 883, clear of
     the seek-time bubble (184r = 896) and the seekbar (140r). -->
<control type="group">
    <posx>335</posx>
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

<!-- TIMES: elapsed at the bar's left end, time remaining at its right, in the 192px margins the
     80% bar leaves on each side - a 30px box at 153r, 2px above centred on the bar (140r, 8
     tall, centre 136r; centred would be 151r) as the glyphs sat visually low, and 20px clear
     of its ends, so the seek-time bubble above the bar never
     lands on them. Same type and colour as the meta line under the cover.
     Two labels per side because Kodi has no "m:ss" time format: under an hour the pair
     Player.Time(m) (minutes in the hour, no leading zero) + ":" + Player.Time(ss) gives "3:41",
     and at an hour or more Player.Time(h:mm:ss) gives "1:03:41" - which one shows is keyed on
     the track's duration (Player.Duration(hh) is "00" under an hour), not the elapsed time, so
     the format doesn't change part-way through a track. The Player.HasAudio guard keeps the
     literal ":" / "-" of the short forms from showing on their own.
     The elapsed label's posx is its RIGHT edge: for a label control with <align>right</align>,
     Kodi's control factory subtracts the width from posx (GUIControlFactory.cpp, the "hacks we
     used to support" branch) - the same rule that let this file's old up-next labels sit at
     "posx 0, width 1000" inside a group at x=1845. The header's own right-aligned time label
     (default.xml.tpl) sidesteps it with <right> instead. -->
<control type="label">
    <visible>Player.HasAudio + String.IsEqual(Player.Duration(hh),00)</visible>
    <posx>172</posx>
    <posy>{{ vscale(153) }}r</posy>
    <width>172</width>
    <height>{{ vscale(30) }}</height>
    <font>font10</font>
    <align>right</align>
    <aligny>center</aligny>
    <textcolor>FFD2CCCE</textcolor>
    <label>$INFO[Player.Time(m)]:$INFO[Player.Time(ss)]</label>
</control>
<control type="label">
    <visible>Player.HasAudio + !String.IsEqual(Player.Duration(hh),00)</visible>
    <posx>172</posx>
    <posy>{{ vscale(153) }}r</posy>
    <width>172</width>
    <height>{{ vscale(30) }}</height>
    <font>font10</font>
    <align>right</align>
    <aligny>center</aligny>
    <textcolor>FFD2CCCE</textcolor>
    <label>$INFO[Player.Time(h:mm:ss)]</label>
</control>
<control type="label">
    <visible>Player.HasAudio + String.IsEqual(Player.Duration(hh),00)</visible>
    <posx>1748</posx>
    <posy>{{ vscale(153) }}r</posy>
    <width>172</width>
    <height>{{ vscale(30) }}</height>
    <font>font10</font>
    <align>left</align>
    <aligny>center</aligny>
    <textcolor>FFD2CCCE</textcolor>
    <label>-$INFO[Player.TimeRemaining(m)]:$INFO[Player.TimeRemaining(ss)]</label>
</control>
<control type="label">
    <visible>Player.HasAudio + !String.IsEqual(Player.Duration(hh),00)</visible>
    <posx>1748</posx>
    <posy>{{ vscale(153) }}r</posy>
    <width>172</width>
    <height>{{ vscale(30) }}</height>
    <font>font10</font>
    <align>left</align>
    <aligny>center</aligny>
    <textcolor>FFD2CCCE</textcolor>
    <label>$INFO[Player.TimeRemaining(h:mm:ss),-]</label>
</control>

<!-- TRANSPORT ROW: theme.music_player's 70x70 boxes at itemgap 0 (context.py), centred in a
     1200-wide box, with a label pill reflowing the row on focus - the other screens' button-row
     treatment, see includes/music_player_buttons.xml.tpl. 100r puts the boxes 30px under the
     seekbar (140r, 8 tall) and 30px off the bottom edge. -->
<control type="grouplist" id="400">
    <defaultcontrol>406</defaultcontrol>
    <hitrect x="360" y="980" w="1200" h="70" />
    <posx>360</posx>
    <posy>{{ vscale(100) }}r</posy>
    <width>1200</width>
    <height>{{ vscale(70) }}</height>
    <align>center</align>
    <onup>500</onup>
    <!-- Dead stops at both ends. A grouplist with no onleft/onright of its own wraps: it wires
         the first child's left to the last child and the last child's right to the first
         (CGUIControlGroupList::AddControl). These are what the end children inherit instead. -->
    <onleft>noop</onleft>
    <onright>noop</onright>
    <itemgap>{{ theme.music_player.buttongroup.itemgap }}</itemgap>
    <orientation>horizontal</orientation>
    <scrolltime tween="quadratic" easing="out">200</scrolltime>
    <usecontrolcoords>true</usecontrolcoords>

    {% include "includes/music_player_buttons.xml.tpl" with music_player=True %}

</control>

<!-- SEEKBAR: 80% of the screen width (1536), centred (x 192..1728), in the poster/episode
     tiles' pill recipe (includes/hub_itemlayout_poster.xml.tpl): 8px tall, track and fill
     FFE5A00D in one identical box, both rounded by a diffuse mask - so it works over any
     background. The track is 40FFFFFF rather than that recipe's E60A0F1A: that near-black
     reads over poster art but all but vanished against this screen's black, and translucent
     white stays a visible, neutral track whatever ends up behind it. The mask is masks/seekbar-mask.png rather than that recipe's progress-bar-mask
     .png: a diffuse mask scales to its control, and that 408x16 one is only the right shape
     squeezed onto a ~224px bar - stretched across 1536px its semicircle caps became 30px tapers.
     seekbar-mask is the bar's own native 1536x8, with its caps lifted from that mask as it renders
     on a 224x8 poster bar, so the curve is that one exactly.
     The fill and the scrubber are progress controls, not that recipe's fixed-percentage strip:
     the fill has to follow Player.Progress live, and the scrubber's position is set from Python
     (updateSelectedProgress(), currentplaylist.py). <reveal> is what makes the mask work on
     them: without it a progress control stretches its midtexture to the played width, taking the
     mask with it; with it (Kodi's GUIProgressControl::UpdateLayout, no left/right textures) the
     midtexture is laid out at the full control width and clipped to the played fraction, so the
     mask sits over the whole box and the fill ends in that recipe's rounded left cap and straight
     cut. That layout also sizes the midtexture's height by its texture height relative to the
     texturebg's, hence the matching 6px pair. The colours are the control-level <colordiffuse>,
     which a progress control passes to all its textures (CGUIProgressControl::UpdateColors) -
     not a colordiffuse= attribute next to diffuse= on the midtexture tag, the combination this
     skin has found to silently do nothing.
     Focused, the played portion dims to FFAC5B00 and the scrubber (200) takes the gold. Python's
     geometry lives in musicplayer.py (BAR_X, BAR_RIGHT, SEEK_IMAGE_WIDTH) and has to match the
     192/1536 here. -->
<control type="group">
    <posx>192</posx>
    <posy>{{ vscale(140) }}r</posy>
    <control type="image">
        <posx>0</posx>
        <posy>0</posy>
        <width>1536</width>
        <height>{{ vscale(8) }}</height>
        <texture diffuse="script.plex/masks/seekbar-mask.png">script.plex/white-square.png</texture>
        <colordiffuse>40FFFFFF</colordiffuse>
    </control>
    <control type="button" id="500">
        <enable>Player.HasAudio</enable>
        <hitrect x="0" y="-19" w="1536" h="48" />
        <posx>0</posx>
        <posy>0</posy>
        <width>1536</width>
        <height>{{ vscale(8) }}</height>
        <ondown>400</ondown>
        <texturefocus>-</texturefocus>
        <texturenofocus>-</texturenofocus>
        <label> </label>
    </control>
    <control type="progress">
        <visible>!Control.HasFocus(500)</visible>
        <description>Progressbar</description>
        <posx>0</posx>
        <posy>0</posy>
        <width>1536</width>
        <height>{{ vscale(8) }}</height>
        <reveal>true</reveal>
        <texturebg>script.plex/transparent-6px.png</texturebg>
        <lefttexture>-</lefttexture>
        <midtexture diffuse="script.plex/masks/seekbar-mask.png">script.plex/white-square-6px.png</midtexture>
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
        <width>1536</width>
        <height>{{ vscale(8) }}</height>
        <reveal>true</reveal>
        <texturebg>script.plex/transparent-6px.png</texturebg>
        <lefttexture>-</lefttexture>
        <midtexture diffuse="script.plex/masks/seekbar-mask.png">script.plex/white-square-6px.png</midtexture>
        <righttexture>-</righttexture>
        <overlaytexture>-</overlaytexture>
        <colordiffuse>FFAC5B00</colordiffuse>
        <info>Player.Progress</info>
    </control>
    <!-- Scrubber: no <info> - MusicPlayerWindow.setSeekbarProgress() (musicplayer.py) drives it
         with ControlProgress.setPercent(), which an info-less progress control keeps. -->
    <control type="progress" id="200">
        <visible>Control.HasFocus(500)</visible>
        <animation effect="fade" time="100" delay="100" end="100">Visible</animation>
        <description>Scrubber</description>
        <posx>0</posx>
        <posy>0</posy>
        <width>1536</width>
        <height>{{ vscale(8) }}</height>
        <reveal>true</reveal>
        <texturebg>script.plex/transparent-6px.png</texturebg>
        <lefttexture>-</lefttexture>
        <midtexture diffuse="script.plex/masks/seekbar-mask.png">script.plex/white-square-6px.png</midtexture>
        <righttexture>-</righttexture>
        <overlaytexture>-</overlaytexture>
        <colordiffuse>FFE5A00D</colordiffuse>
    </control>
</control>

<!-- Seek-time bubble. Wrapped in a group at the bar's x so updateSelectedProgress()'s
     setPosition(w, SELECTION_INDICATOR_Y) on 202, which is relative to the bar's left edge,
     lands over the bar - the 184r/-50 defaults below are only what shows before the first
     seek action repositions it. -->
<control type="group">
    <posx>192</posx>
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
{% endblock controls %}