{% extends "default.xml.tpl" %}
{% block headers %}<defaultcontrol>100</defaultcontrol>{% endblock %}

{# No top-right hero-art box on anything in this chain - the poster/square grids and both list
   views (via library_posters.xml.tpl) plus Genres. Only Recommended's hub-focused item wants it,
   and script-plex-recommended.xml.tpl extends default.xml.tpl directly, so it is unaffected.
   Replaces the runtime no_hero_art property for these screens; see default_background.xml.tpl's
   own comment on the flag for the view-swap bug that made the property approach unreliable. #}
{% block background %}{% include "includes/default_background.xml.tpl" with suppress_hero_art=True %}{% endblock %}

{# header_middle_add is default.xml.tpl's hook, but the header block below fully replaces
   default.xml.tpl's header body (see {% block header %} immediately following) and never
   references header_middle_add - so overriding that block name here would be dead code,
   never rendered. Inlined directly into the real body instead (right after the audio-widget
   group, before filteropts_grouplist), same as script-plex-recommended.xml.tpl does. #}

{% block header %}
<control type="group" id="200">
    {% block header_animation %}<animation effect="slide" end="0,{{ vscale(-125) }}" time="200" tween="quadratic" easing="out" condition="Integer.IsGreater(Container(101).ListItem.Property(index),5) + !ControlGroup(200).HasFocus(0) + String.IsEmpty(Window.Property(content.filling))">Conditional</animation>{% endblock %}
    {% block header_defaultcontrol %}{% endblock %}
    <posx>0</posx>
    <posy>0</posy>
    <width>1920</width>
    <height>{{ vscale(125) }}</height>
    <visible>!String.IsEmpty(Window.Property(initialized))</visible>
    {% block header_bg %}
    <control type="image">
        <animation effect="fade" start="0" end="100" time="200" tween="quadratic" easing="out" reversible="true">VisibleChange</animation>
        <visible>ControlGroup(200).HasFocus(0) + Integer.IsGreater(Container(101).ListItem.Property(index),5)</visible>
        <posx>0</posx>
        <posy>0</posy>
        <width>1920</width>
        <height>{{ vscale(125) }}</height>
        <texture>script.plex/white-square.png</texture>
        <colordiffuse>C0000000</colordiffuse>
    </control>
    {% endblock %}
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
    {# declared after the time label, same as default.xml.tpl's own copy of this group, so the
       popout below paints over the clock instead of the other way round - was declared before it
       here, which put the clock on top of the popout's own art/track-info card. #}
    <control type="group">
        <visible>Player.HasAudio + String.IsEmpty(Window(10000).Property(script.plex.theme_playing))</visible>
        {# 360r matches default.xml.tpl's own header widget - same collapsed-thumbnail/popout design,
           see that file's copy of this group for the full layout reasoning. onleft prefers the
           section-tabs row (320, includes/section_tabs.xml.tpl) when it's actually on screen -
           the symmetric return path for that row's own onright into this widget - falling back to
           the sidebar rail (9001) when there's no tab row to land on. #}
        <posx>360r</posx>
        <posy>0</posy>
        {# Collapsed to just the art thumbnail: 63x63, rounded through square-mask.png with the mask pinned
           to the control's own bounds - the corner treatment the music library's track rows use
           (includes/track_row.xml.tpl), at a smaller size. Centred in the 135px header (36 above and
           below). No zoom on focus - the ring below is the whole focus treatment. #}
        <control type="group">
            <control type="button" id="204">
                <posx>0</posx>
                <posy>{{ vscale(31) }}</posy>
                <width>63</width>
                <height>{{ vscale(63) }}</height>
                {% block header_audiowidget_onleft %}<onleft condition="Control.IsVisible(320)">320</onleft><onleft>9001</onleft>{% endblock %}
                <ondown>50</ondown>
                <texturefocus>-</texturefocus>
                <texturenofocus>-</texturenofocus>
                <label> </label>
            </control>
            <control type="image">
                <posx>0</posx>
                <posy>{{ vscale(31) }}</posy>
                <width>63</width>
                <height>{{ vscale(63) }}</height>
                <texture diffuse="script.plex/masks/square-mask.png">$INFO[Player.Art(thumb)]</texture>
                <aspectratio scalediffuse="false">scale</aspectratio>
            </control>
            {# Focus ring: the music grid's recipe (script-plex-squares.xml.tpl) - a flat white square diffused
               through an RGBA ring mask, tinted FFE9A20D, in a box 6px larger than the art at -3 on both axes.
               Its own mask rather than the shared ring-mask-square.png, though: that one is a 3px ring at its
               488px authored size, which scales to ~0.4px in a 69px box and all but disappears. This mask is
               authored at 69px native with a 2px ring, its corner radius square-mask.png's own (~2px at 63px)
               plus the 3px offset. selected.png's 9-slice border was rejected here long ago for the mirror-image
               reason - its stroke width is baked into the source pixels and can't be scaled down. #}
            <control type="image">
                <visible>Control.HasFocus(204)</visible>
                <posx>-3</posx>
                <posy>{{ vscale(28) }}</posy>
                <width>69</width>
                <height>{{ vscale(69) }}</height>
                <texture diffuse="script.plex/masks/ring-mask-square-69.png">script.plex/white-square.png</texture>
                <colordiffuse>FFE9A20D</colordiffuse>
            </control>
        </control>

        <control type="group">
            <visible>Control.HasFocus(204)</visible>
            <animation effect="fade" start="0" end="100" time="120" reversible="true">Visible</animation>
            {# Extends over the time label by design - this group is declared after it, so it draws on top rather
               than shifting it. Card is 75 tall around the 63px art (6px beyond it top and bottom), starting
               12px past the art's right edge; text/progress sit 15px inside it. Title over artist, both font8,
               in the track rows' colours (includes/track_row.xml.tpl): white title, AAFFFFFF artist. #}
            <control type="image">
                <posx>75</posx>
                <posy>{{ vscale(25) }}</posy>
                <width>260</width>
                <height>{{ vscale(75) }}</height>
                <texture colordiffuse="E0000000" border="10">script.plex/white-square-rounded.png</texture>
            </control>
            <control type="label">
                <posx>90</posx>
                <posy>{{ vscale(35) }}</posy>
                <width>230</width>
                <height>{{ vscale(20) }}</height>
                <font>font8</font>
                <align>left</align>
                <aligny>center</aligny>
                <textcolor>FFFFFFFF</textcolor>
                <info>MusicPlayer.Title</info>
            </control>
            <control type="label">
                <posx>90</posx>
                <posy>{{ vscale(59) }}</posy>
                <width>230</width>
                <height>{{ vscale(20) }}</height>
                <font>font8</font>
                <align>left</align>
                <aligny>center</aligny>
                <textcolor>AAFFFFFF</textcolor>
                <info>MusicPlayer.Artist</info>
            </control>
            <control type="progress">
                <description>Progressbar</description>
                <posx>90</posx>
                <posy>{{ vscale(89) }}</posy>
                <width>230</width>
                <height>{{ vscale(1) }}</height>
                <texturebg colordiffuse="9AFFFFFF">script.plex/white-square-1px.png</texturebg>
                <lefttexture>-</lefttexture>
                <midtexture colordiffuse="FFCC7B19">script.plex/white-square-1px.png</midtexture>
                <righttexture>-</righttexture>
                <overlaytexture>-</overlaytexture>
                <info>Player.Progress</info>
            </control>
        </control>
    </control>
    {% with tab_ondown = 101 %}{% include "includes/section_tabs.xml.tpl" %}{% endwith %}
    {% block filteropts_grouplist %}
    <control type="grouplist"{% block filteropts_grouplist_attrs %} id="600"{% endblock %}>
        <visible>String.IsEmpty(Window.Property(hide.filteroptions))</visible>
        <visible>!Integer.IsGreater(Container(101).ListItem.Property(index),{% block hide_filter_from_index %}5{% endblock %}) + String.IsEmpty(Window.Property(no.content)) + !String.IsEmpty(Window.Property(initialized))</visible>
        <animation effect="slide" time="200" end="0,{{ vscale(-115) }}" tween="quadratic" easing="out" condition="Integer.IsGreater(Container(101).ListItem.Property(index),{% block hide_filter_from_index %}5{% endblock %}) + String.IsEmpty(Window.Property(content.filling))">Conditional</animation>
        {% block filteropts_animation %}
            <animation effect="fade" start="0" end="100" time="200" reversible="true">VisibleChange</animation>
        {% endblock %}
        <right>170</right>
        <posy>{{ vscale(125) }}</posy>
        <width>1000</width>
        <height>{{ vscale(65) }}</height>
        <align>right</align>
        <itemgap>30</itemgap>
        <orientation>horizontal</orientation>
        {% block header_filteropts_onleft_nocontent %}<onleft>9000</onleft>{% endblock %}
        <onright>300</onright>
        <ondown>101</ondown>
        {% block header_filteropts_onup %}<onup condition="Control.IsVisible(320)">320</onup><onup condition="Player.HasAudio + String.IsEmpty(Window(10000).Property(script.plex.theme_playing))">204</onup>{% endblock %}
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
            <label>[CAPITALIZE]$INFO[Window.Property(filter2.display)][/CAPITALIZE]</label>
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
            <label>[CAPITALIZE]$INFO[Window.Property(filter1.display)][/CAPITALIZE]</label>
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
            <textoffsetx>20</textoffsetx>
            <textoffsety>0</textoffsety>
            <label>[CAPITALIZE]$INFO[Window.Property(media.type)][/CAPITALIZE]</label>
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
            <label>[CAPITALIZE]$INFO[Window.Property(media.type)][/CAPITALIZE]</label>
        </control>
        <control type="button" id="212">
            <!-- Ascending/descending indicator for the sort button below - see sortButtonClicked()/
                 updateSortIcon() (library.py). type=button + enable=false, not type=image: a
                 plain image here isn't a focusable-eligible control type, which breaks the
                 grouplist's internal navigation. Direct grouplist child at the row's own full
                 height (not a shorter box + <posy>, and not wrapped in a group): a shorter box
                 with an explicit posy offset - even nested one level inside a group - measurably
                 broke this row's right-navigation out to the play button when this sat after 210
                 instead of before it, for reasons that didn't trace back to any onright value.
                 Matching every sibling's plain full-height footprint is what's proven not to
                 disturb it, so the vertical offset is baked into the sort-asc/desc.png canvas's
                 own transparent padding instead of a posy tag. Two mutually-exclusive
                 static-texture buttons, not one dynamic $INFO path - $INFO[Window.Property(...)]
                 isn't evaluated inside <texturenofocus> the way it is inside an image control's
                 <texture>, so that only rendered an empty box. Same swap-on-a-property pattern
                 310/312 already use above for the media-type button's artist variant. -->
            <visible>!String.IsEqual(Window.Property(sort.icon),desc)</visible>
            <enable>false</enable>
            <width>{{ vscale(30) }}</width>
            <height>{{ vscale(65) }}</height>
            <texturefocus>-</texturefocus>
            <texturenofocus>script.plex/indicators/sort-asc.png</texturenofocus>
        </control>
        <control type="button" id="213">
            <visible>String.IsEqual(Window.Property(sort.icon),desc)</visible>
            <enable>false</enable>
            <width>{{ vscale(30) }}</width>
            <height>{{ vscale(65) }}</height>
            <texturefocus>-</texturefocus>
            <texturenofocus>script.plex/indicators/sort-desc.png</texturenofocus>
        </control>
        <control type="button" id="210">
            <!-- Explicit, not relying on the grouplist's own onright: nothing else follows 210
                 in this (unused) template. Targets 301 (the play button) directly, not
                 container 300. -->
            <onright>301</onright>
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
            <label>[CAPITALIZE]$INFO[Window.Property(sort.display)][/CAPITALIZE]</label>
        </control>
    </control>
    {% endblock filteropts_grouplist %}
</control>

{# The sidebar rail lives outside group 200 deliberately, mirroring script-plex-home.xml.tpl -
   group 200 slides off-screen on scroll (header_animation above), and nothing in the sidebar
   (including the user/server buttons) should move when that happens. #}
{% block header_sidebar %}{% include "includes/sidebar.xml.tpl" %}{% endblock %}

{% block no_content %}
<control type="group">
    <visible>!String.IsEmpty(Window.Property(no.content))</visible>
    <posx>0</posx>
    <posy>{{ vscale(465) }}</posy>
    <control type="label">
        <scroll>false</scroll>
        <posx>60</posx>
        <posy>0</posy>
        <width>1800</width>
        <height>{{ vscale(35) }}</height>
        <font>font13</font>
        <align>center</align>
        <textcolor>FFFFFFFF</textcolor>
        <label>[B]$ADDON[script.plexmod 32452][/B]</label>
    </control>
    <control type="label">
        <scroll>false</scroll>
        <posx>60</posx>
        <posy>{{ vscale(60) }}</posy>
        <width>1800</width>
        <height>{{ vscale(35) }}</height>
        <font>font13</font>
        <align>center</align>
        <textcolor>FFCCCCCC</textcolor>
        <label>$ADDON[script.plexmod 32453]</label>
    </control>
</control>

<control type="group">
    <visible>!String.IsEmpty(Window.Property(no.content.filtered))</visible>
    <posx>0</posx>
    <posy>{{ vscale(465) }}</posy>
    <control type="label">
        <scroll>false</scroll>
        <posx>60</posx>
        <posy>0</posy>
        <width>1800</width>
        <height>{{ vscale(35) }}</height>
        <font>font13</font>
        <align>center</align>
        <textcolor>FFFFFFFF</textcolor>
        <label>[B]$ADDON[script.plexmod 32454][/B]</label>
    </control>
    <control type="label">
        <scroll>false</scroll>
        <posx>60</posx>
        <posy>{{ vscale(60) }}</posy>
        <width>1800</width>
        <height>{{ vscale(35) }}</height>
        <font>font13</font>
        <align>center</align>
        <textcolor>FFCCCCCC</textcolor>
        <label>$ADDON[script.plexmod 32455]</label>
    </control>
</control>

<control type="group">
    <visible>!String.IsEmpty(Window.Property(search.dialog))</visible>
    <control type="group" >
        <visible>!String.IsEmpty(Window.Property(search.dialog.hasresults))</visible>
        <control type="image">
            <posx>0</posx>
            <posy>0</posy>
            <width>1920</width>
            <height>1080</height>
            <texture>script.plex/home/background-fallback.png</texture>
        </control>
        <control type="image">
            <posx>0</posx>
            <posy>0</posy>
            <width>1920</width>
            <height>1080</height>
            <texture background="true">$INFO[Window.Property(background)]</texture>
        </control>
    </control>
    <control type="image">
        <posx>0</posx>
        <posy>0</posy>
        <width>1920</width>
        <height>1080</height>
        <texture colordiffuse="99606060">script.plex/white-square.png</texture>
    </control>
</control>
{% endblock %}

{# Stage 3 (quiet-orbiting-heron.md's Cold Start plan) - declared last, same reasoning as
   script-plex-recommended.xml.tpl's own copy of this include: the server/user dropdown popouts
   (groups 802/901) need to draw on top of everything else in this block, not behind it. #}
{% include "includes/sidebar_dropdowns.xml.tpl" %}
{% endblock header %}