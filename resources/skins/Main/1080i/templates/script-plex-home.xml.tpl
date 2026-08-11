{% extends "default.xml.tpl" %}
{% block content %}
<!-- Single fixed-position hub row ("anchor"): whichever hub is logically focused always renders
     here, at exactly row 0's old resting position - home.py rebinds this one physical control's
     content (title, items, display type) as focus moves between hubs, rather than there being one
     physical control per hub. See docs/notes/home-hub-fixed-focus-position-status.md for why: three
     <animation>-based attempts failed (a control's clip rect follows its own animated position, so
     nothing clipped correctly), and nesting hub rows as items inside one native vertical list is
     impossible (Kodi gives item-template content no real, addressable control identity - confirmed
     live, RuntimeError: Non-Existent Control). id="50" is kept on the outer control because
     default.xml.tpl's header controls target it directly via <ondown>50</ondown>. -->
<control type="group" id="50">
    <!-- Slide right while the sidebar rail is expanded (focused), so hub content doesn't sit under the labels -->
    <animation effect="slide" end="220,0" time="200" tween="sine" easing="inout" condition="ControlGroup(9000).HasFocus(0)">Conditional</animation>

    <defaultcontrol>500</defaultcontrol>
    <!-- posx=100, not 55: the sidebar rail is drawn on top (see its own comment in default.xml.tpl's
         header block) - this leaves room for the collapsed rail's icon column. Row titles/
         bifurcation lines and item layout insets below have their own posx reduced by the same 45px
         this moved right, to keep resting positions unchanged (60->15, 55->10). -->
    <posx>100</posx>
    <posy>{{ vscale(424) }}</posy>
    <width>2085</width>
    <height>{{ vscale(425) }}</height>
    <usecontrolcoords>true</usecontrolcoords>

    <control type="group" id="500">
        <visible>Integer.IsGreater(Container(400).NumItems,0) + String.IsEmpty(Window.Property(drawing))</visible>
        <defaultcontrol>400</defaultcontrol>
        <width>1920</width>
        <height>{{ vscale(425) }}</height>
        <control type="image">
            <visible>!String.IsEmpty(Window.Property(bifurcation_lines))</visible>
            <posx>15</posx>
            <posy>{{ vscale(12) }}</posy>
            <width>1800</width>
            <height>{{ vscale(2) }}</height>
            <texture>script.plex/white-square.png</texture>
            <colordiffuse>A0000000</colordiffuse>
        </control>
        <control type="label">
            <posx>15</posx>
            <posy>0</posy>
            <width>1000</width>
            <height>{{ vscale(87) }}</height>
            <font>font13</font>
            <align>left</align>
            <aligny>center</aligny>
            <textcolor>FFFFFFFF</textcolor>
            <shadowcolor>66000000</shadowcolor>
            <label>[B]$INFO[Window.Property(hub.400)][/B]</label>
        </control>
        <control type="list" id="400">
            <posx>0</posx>
            <posy>{{ vscale(29) }}</posy>
            <width>1920</width>
            <height>{{ vscale(515) }}</height>
            <!-- Vertical hub-to-hub navigation is handled entirely in Python (HomeWindow.onAction
                 intercepts MOVE_UP/MOVE_DOWN before this native nav map would fire) - there is no
                 other physical row control to hand focus to, so both are noop here. -->
            <onup>noop</onup>
            <ondown>noop</ondown>
            <onright>noop</onright>
            <onleft>9001</onleft>
            <scrolltime>200</scrolltime>
            <orientation>horizontal</orientation>
            <preloaditems>4</preloaditems>

            <!-- hub_id: the includes below key their conditions off Window.Property(hub.display.{{ hub_id }})
                 - always 400 now, but they still need it in scope. -->
            {% with hub_id = 400 %}
            <!-- Conditional item layouts - Kodi selects layout based on condition attribute -->
            {% include "includes/hub_itemlayout_poster.xml.tpl" %}
            {% include "includes/hub_itemlayout_square.xml.tpl" %}
            {% include "includes/hub_itemlayout_ar16x9.xml.tpl" %}
            <!-- Conditional focused layouts - Kodi selects layout based on condition attribute -->
            {% include "includes/hub_focusedlayout_poster.xml.tpl" %}
            {% include "includes/hub_focusedlayout_square.xml.tpl" %}
            {% include "includes/hub_focusedlayout_ar16x9.xml.tpl" %}
            {% endwith %}
        </control>
    </control>

    <!-- Peek rows: non-focusable previews of the previous/next hub, rendered with the exact same
         itemlayout/focusedlayout includes as the anchor above (just a different hub_id/control id) -
         they're meant to look identical to the focused row, not a simplified decorative version.
         Each is wrapped in its own clipping grouplist (a plain group doesn't clip - see
         script-plex-episodes.xml.tpl:271's own comment on this) sized shorter than full row content,
         so the crop is just a side effect of limited screen space, not a deliberately-thin sliver.
         home.py's HomeWindow._bindPeekHubs() populates control ids 401/402 and drives the
         hub.has_prev/hub.has_next visibility properties below. -->
    <control type="grouplist" id="501">
        <!-- Peek-above: only shown when the focused hub has no hero art - that's the only time the
             band between the header and the anchor (y~135-424) is actually free; when hero art is
             showing, that space is occupied by the title/meta/summary overlay (see
             script-plex-home.xml.tpl's header block) and default_background.xml.tpl's art box,
             which hide together via the same no_hero_art property.

             No title label/bifurcation line here (unlike 502 below) - this preview is meant to read
             as the *tail end* of the row above trailing into view, not a fresh row starting from its
             own top: the item templates' outer-group posy is overridden to a per-type negative value
             for hub_id 401 specifically (see hub_itemlayout_poster/square/ar16x9.xml.tpl), pushing
             each item up so its own bottom edge lands flush with this wrapper's bottom (right above
             the anchor) - the label, bifurcation line and top of the art fall above y=0 and are
             clipped away by this grouplist, same mechanism as everything else being cropped here. -->
        <visible>!String.IsEmpty(Window.Property(no_hero_art)) + !String.IsEmpty(Window.Property(hub.has_prev))</visible>
        <posx>0</posx>
        <!-- -289 = 135 (header's own bottom edge, absolute) - 424 (group 50's own absolute posy) -
             top edge sits flush with the header, using the full available band down to the anchor. -->
        <posy>{{ vscale(-289) }}</posy>
        <width>1920</width>
        <!-- 277 = 424 (anchor's absolute top) - 12 (gap) - 135 (header bottom). -->
        <height>{{ vscale(277) }}</height>
        <usecontrolcoords>true</usecontrolcoords>
        <orientation>vertical</orientation>
        <itemgap>0</itemgap>
        <control type="group">
            <visible>Integer.IsGreater(Container(401).NumItems,0) + String.IsEmpty(Window.Property(drawing))</visible>
            <width>1920</width>
            <height>{{ vscale(277) }}</height>
            <control type="list" id="401">
                <posx>0</posx>
                <posy>0</posy>
                <width>1920</width>
                <height>{{ vscale(277) }}</height>
                <!-- Never focused - Python never targets this id via setFocusId, and nothing else's
                     onup/ondown/onleft/onright points at it, so these are just defensive noops. -->
                <onup>noop</onup>
                <ondown>noop</ondown>
                <onleft>noop</onleft>
                <onright>noop</onright>
                <scrolltime>200</scrolltime>
                <orientation>horizontal</orientation>
                <preloaditems>4</preloaditems>

                {% with hub_id = 401 %}
                {% include "includes/hub_itemlayout_poster.xml.tpl" %}
                {% include "includes/hub_itemlayout_square.xml.tpl" %}
                {% include "includes/hub_itemlayout_ar16x9.xml.tpl" %}
                {% include "includes/hub_focusedlayout_poster.xml.tpl" %}
                {% include "includes/hub_focusedlayout_square.xml.tpl" %}
                {% include "includes/hub_focusedlayout_ar16x9.xml.tpl" %}
                {% endwith %}
            </control>
        </control>
    </control>

    <control type="grouplist" id="502">
        <!-- Peek-below: shown whenever a next hub exists, independent of hero art state - the band
             below the anchor is always free. Same top-anchored render as the anchor itself (title +
             bifurcation line + top of the art, cropped at the bottom) - unlike 501 above, this one
             reads as the *start* of the next row, so keeping its own title visible makes sense here.

             posy=489 (not immediately below the anchor's declared 425 height) / height reaching the
             screen bottom (1080): the anchor's declared height is a nominal figure - a 2-line ar16x9
             label (hub_itemlayout_ar16x9.xml.tpl, text2lines) actually bottoms out around 477 (see
             that file's own posy chain: 29 list + 72 item + 5 inner + 336 label2 posy + 35 height),
             well past 425, since the anchor is a plain, non-clipping group. 489 = 477 + 12px gap,
             keeping this row's own title clear of the anchor's real worst-case content regardless of
             which display type currently occupies it. -->
        <visible>!String.IsEmpty(Window.Property(hub.has_next))</visible>
        <posx>0</posx>
        <posy>{{ vscale(489) }}</posy>
        <width>1920</width>
        <!-- 167 = 1080 (screen bottom) - 424 (group 50's own absolute posy) - 489 (this grouplist's
             own relative posy above) - reaches exactly to the bottom of the screen. -->
        <height>{{ vscale(167) }}</height>
        <usecontrolcoords>true</usecontrolcoords>
        <orientation>vertical</orientation>
        <itemgap>0</itemgap>
        <control type="group">
            <visible>Integer.IsGreater(Container(402).NumItems,0) + String.IsEmpty(Window.Property(drawing))</visible>
            <width>1920</width>
            <height>{{ vscale(167) }}</height>
            <control type="image">
                <visible>!String.IsEmpty(Window.Property(bifurcation_lines))</visible>
                <posx>15</posx>
                <posy>{{ vscale(12) }}</posy>
                <width>1800</width>
                <height>{{ vscale(2) }}</height>
                <texture>script.plex/white-square.png</texture>
                <colordiffuse>A0000000</colordiffuse>
            </control>
            <control type="label">
                <posx>15</posx>
                <posy>0</posy>
                <width>1000</width>
                <height>{{ vscale(87) }}</height>
                <font>font13</font>
                <align>left</align>
                <aligny>center</aligny>
                <textcolor>FFFFFFFF</textcolor>
                <shadowcolor>66000000</shadowcolor>
                <label>[B]$INFO[Window.Property(hub.402)][/B]</label>
            </control>
            <control type="list" id="402">
                <posx>0</posx>
                <posy>{{ vscale(29) }}</posy>
                <width>1920</width>
                <height>{{ vscale(515) }}</height>
                <onup>noop</onup>
                <ondown>noop</ondown>
                <onleft>noop</onleft>
                <onright>noop</onright>
                <scrolltime>200</scrolltime>
                <orientation>horizontal</orientation>
                <preloaditems>4</preloaditems>

                {% with hub_id = 402 %}
                {% include "includes/hub_itemlayout_poster.xml.tpl" %}
                {% include "includes/hub_itemlayout_square.xml.tpl" %}
                {% include "includes/hub_itemlayout_ar16x9.xml.tpl" %}
                {% include "includes/hub_focusedlayout_poster.xml.tpl" %}
                {% include "includes/hub_focusedlayout_square.xml.tpl" %}
                {% include "includes/hub_focusedlayout_ar16x9.xml.tpl" %}
                {% endwith %}
            </control>
        </control>
    </control>
</control>

{% endblock content %}

{% block header %}
<control type="group" id="200">
    <posx>0</posx>
    <posy>0</posy>
    <width>1920</width>
    <height>{{ vscale(135) }}</height>
    <control type="group">
        <visible>Player.HasAudio + String.IsEmpty(Window(10000).Property(script.plex.theme_playing))</visible>
        <posx>438</posx>
        <posy>0</posy>
        <control type="button" id="204">
            <visible>Player.HasAudio + String.IsEmpty(Window(10000).Property(script.plex.theme_playing))</visible>
            <posx>-10</posx>
            <posy>{{ vscale(38) }}</posy>
            <width>260</width>
            <height>{{ vscale(75) }}</height>
            <onleft>9001</onleft>
            <ondown>50</ondown>
            <font>font12</font>
            <textcolor>FFFFFFFF</textcolor>
            <focusedcolor>FF000000</focusedcolor>
            <align>right</align>
            <aligny>center</aligny>
            <texturefocus colordiffuse="FFE5A00D" border="10">script.plex/white-square-rounded.png</texturefocus>
            <texturenofocus>-</texturenofocus>
            <textoffsetx>100</textoffsetx>
            <textoffsety>0</textoffsety>
            <label> </label>
        </control>
        <control type="image">
            <posx>0</posx>
            <posy>{{ vscale(48) }}</posy>
            <width>42</width>
            <height>{{ vscale(42) }}</height>
            <texture>$INFO[Player.Art(thumb)]</texture>
        </control>

        <control type="group">
            <visible>!Control.HasFocus(204)</visible>
            <control type="label">
                <posx>53</posx>
                <posy>{{ vscale(48) }}</posy>
                <width>187</width>
                <height>{{ vscale(20) }}</height>
                <font>font10</font>
                <align>left</align>
                <aligny>center</aligny>
                <textcolor>FFFFFFFF</textcolor>
                <info>MusicPlayer.Artist</info>
            </control>
            <control type="label">
                <posx>53</posx>
                <posy>{{ vscale(72) }}</posy>
                <width>187</width>
                <height>{{ vscale(20) }}</height>
                <font>font10</font>
                <align>left</align>
                <aligny>center</aligny>
                <textcolor>FFFFFFFF</textcolor>
                <info>MusicPlayer.Title</info>
            </control>
        </control>
        <control type="group">
            <visible>Control.HasFocus(204)</visible>
            <control type="label">
                <posx>53</posx>
                <posy>{{ vscale(48) }}</posy>
                <width>187</width>
                <height>{{ vscale(20) }}</height>
                <font>font10</font>
                <align>left</align>
                <aligny>center</aligny>
                <textcolor>FF000000</textcolor>
                <info>MusicPlayer.Artist</info>
            </control>
            <control type="label">
                <posx>53</posx>
                <posy>{{ vscale(72) }}</posy>
                <width>187</width>
                <height>{{ vscale(20) }}</height>
                <font>font10</font>
                <align>left</align>
                <aligny>center</aligny>
                <textcolor>FF000000</textcolor>
                <info>MusicPlayer.Title</info>
            </control>
        </control>

        <control type="progress">
            <description>Progressbar</description>
            <posx>0</posx>
            <posy>{{ vscale(102) }}</posy>
            <width>240</width>
            <height>{{ vscale(1) }}</height>
            <texturebg colordiffuse="9AFFFFFF">script.plex/white-square-1px.png</texturebg>
            <lefttexture>-</lefttexture>
            <midtexture colordiffuse="FFCC7B19">script.plex/white-square-1px.png</midtexture>
            <righttexture>-</righttexture>
            <overlaytexture>-</overlaytexture>
            <info>Player.Progress</info>
        </control>
    </control>
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

    {% include "includes/sidebar_dropdowns.xml.tpl" %}
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
            {% include "includes/scale_background.xml.tpl" %}
        </control>
        <control type="image">
            <posx>0</posx>
            <posy>0</posy>
            <width>1920</width>
            <height>1080</height>
            <texture background="true">$INFO[Window.Property(background)]</texture>
            {% include "includes/scale_background.xml.tpl" %}
        </control>
    </control>
    <control type="image">
        <posx>0</posx>
        <posy>0</posy>
        <width>1920</width>
        <height>1080</height>
        <texture colordiffuse="99606060">script.plex/white-square.png</texture>
        {% include "includes/scale_background.xml.tpl" %}
    </control>
</control>

<control type="group">
    <visible>String.IsEmpty(Window.Property(busy)) + !String.IsEmpty(Window.Property(no.content))</visible>
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
    <visible>String.IsEmpty(Window.Property(busy)) + !String.IsEmpty(Window.Property(loading.content))</visible>
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
        <label>[B]$ADDON[script.plexmod 34020][/B]</label>
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
        <label>[B]$ADDON[script.plexmod 34021][/B]</label>
    </control>
</control>

<control type="group">
    <visible>!String.IsEmpty(Window.Property(busy))</visible>
    <animation effect="fade" start="0" end="100">Visible</animation>
    <posx>840</posx>
    <posy>{{ vscale(465) }}</posy>
    <control type="image">
        <posx>0</posx>
        <posy>0</posy>
        <width>240</width>
        <height>{{ vscale(150) }}</height>
        <texture>script.plex/busy-back.png</texture>
        <colordiffuse>A0FFFFFF</colordiffuse>
    </control>
    <control type="image">
        <posx>75</posx>
        <posy>{{ vscale(56) }}</posy>
        <width>90</width>
        <height>{{ vscale(38) }}</height>
        <texture diffuse="script.plex/busy-diffuse.png">script.plex/busy.gif</texture>
    </control>
</control>


<!-- Focused hub item info overlay - clearlogo/title, meta row and summary, matching pre_play's own
     details block (script-plex-pre_play.xml.tpl) exactly: same posx=52/posy=155 group offset as
     pre_play's own group id=50, same inner posx=60 controls, so this reads as the same UI language
     rather than a reinvention. No rating row here (Home has no single focused video the way pre_play
     does - ratings would only make sense per-hub-item and there's no room to duplicate the rating
     row per hub), so the summary sits at pre_play's rating-row height (210) instead of its own
     summary height (252), filling the gap that would otherwise sit empty between the meta row and
     the hero art below. Driven entirely by the Window properties HomeWindow.setHeroInfo() sets on
     hub focus change (see home.py); hidden via the hide-via-empty-property idiom until the first hub
     item is focused. -->
<control type="group">
    <!-- Same slide-with-the-sidebar-rail animation as grouplist 50's hub content (see this file's
         own content block) - this overlay lives in the header block instead, as a sibling rather
         than a child of that grouplist, so it needs its own copy of the animation to move in sync
         rather than inheriting it. -->
    <animation effect="slide" end="220,0" time="200" tween="sine" easing="inout" condition="ControlGroup(9000).HasFocus(0)">Conditional</animation>
    <!-- no_hero_art (HomeWindow.updateHeroFrom, home.py): hide the whole overlay - not just the
         art box in default_background.xml.tpl - for items with no real background art (Photos,
         many Music artists/albums), rather than showing text describing art that isn't there. -->
    <visible>!String.IsEmpty(Window.Property(title)) + String.IsEmpty(Window.Property(no_hero_art))</visible>
    <posx>52</posx>
    <posy>{{ vscale(155) }}</posy>
    <control type="label">
        <visible>String.IsEmpty(Window.Property(clear.logo))</visible>
        <posx>60</posx>
        <posy>0</posy>
        <width>616</width>
        <height>{{ vscale(109) }}</height>
        <font>font45</font>
        <align>left</align>
        <aligny>bottom</aligny>
        <scroll>true</scroll>
        <scrollspeed>35</scrollspeed>
        <textcolor>FFFFFFFF</textcolor>
        <label>$INFO[Window.Property(title)]</label>
    </control>
    <control type="image">
        <visible>!String.IsEmpty(Window.Property(clear.logo))</visible>
        <posx>60</posx>
        <posy>0</posy>
        <width>616</width>
        <height>{{ vscale(109) }}</height>
        <aspectratio align="left" aligny="bottom">keep</aspectratio>
        <texture background="true">$INFO[Window.Property(clear.logo)]</texture>
    </control>
    {% include "includes/pp_meta_row.xml.tpl" %}
    <control type="textbox">
        <posx>60</posx>
        <posy>{{ vscale(186) }}</posy>
        <width>708</width>
        <height>{{ vscale(90) }}</height>
        <font>font12</font>
        <align>left</align>
        <textcolor>FFD2CCCE</textcolor>
        <shadowcolor>66000000</shadowcolor>
        <scrolltime>200</scrolltime>
        <autoscroll delay="2000" time="2000" repeat="10000"/>
        <label>$INFO[Window.Property(summary)]</label>
    </control>
</control>

{% include "includes/sidebar.xml.tpl" %}
{% endblock header %}
