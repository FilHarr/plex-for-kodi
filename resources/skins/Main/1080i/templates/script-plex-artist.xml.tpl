{% extends "default.xml.tpl" %}
{% block headers %}<defaultcontrol>100</defaultcontrol>{% endblock %}
{% block header_topleft %}{% endblock %}
{% block header %}
    {{ super() }}
    {% include "includes/sidebar.xml.tpl" %}
    <!-- Declared last so groups 802/901 draw on top - see script-plex-pre_play.xml.tpl's own copy
         of this include for the full reasoning (this window is one of the seven real hosted-shell
         types too, same _sidebarTarget()-aware Python side, same onClick forwarding - shared with
         script-plex-seasons.xml.tpl since ArtistWindow(subitems.py) subclasses ShowWindow without
         overriding onClick). -->
    {% include "includes/sidebar_dropdowns.xml.tpl" %}
{% endblock header %}
{% block content %}
<control type="group" id="50">
    <animation effect="slide" end="0,{{ vscale(-300) }}" time="200" tween="quadratic" easing="out" condition="!String.IsEmpty(Window.Property(on.extras))">Conditional</animation>

    <animation type="Conditional" condition="Integer.IsGreater(Window.Property(hub.focus),0) + Control.IsVisible(500)" reversible="true">
        <effect type="slide" end="0,{{ vscale(-500) }}" time="200" tween="quadratic" easing="out"/>
    </animation>

    <!-- Slide right while the sidebar rail is expanded (focused), matching every other ported screen. -->
    <animation effect="slide" end="220,0" time="200" tween="sine" easing="inout" condition="ControlGroup(9000).HasFocus(0)">Conditional</animation>

    <!-- posx=52, not 60: matches Seasons'/Pre-play's own tuned value exactly
         (script-plex-seasons.xml.tpl) so the content column lands at the same absolute x as those
         screens - see includes/sidebar.xml.tpl for why some offset is still needed at all (clears
         the collapsed sidebar rail's icon column). -->
    <posx>52</posx>
    <posy>{{ vscale(135) }}</posy>
    <defaultcontrol>400</defaultcontrol>

    {% block buttons %}
        <!-- Repositioned/retuned to match Seasons' own button row (script-plex-seasons.xml.tpl) -
             same 0/358 outer offset and 63/25 inner offset, same icon-box retune (theme.artist
             mirrors theme.seasons in context.py: 70x70 icons, itemgap 0, hitrect 5,5,60,60 in the
             modern theme) in place of this row's own old one-off 174x139/-50-itemgap tuning. No
             season-tab row to fall back onto (unlike Seasons' own dual onup), so onup just stays 200;
             onleft=9000 added to reach the sidebar - every other ported screen's button row already
             has this, this one just never did. -->
        <control type="group">
            <posx>0</posx>
            <posy>{{ vscale(358) }}</posy>
            <width>1920</width>
            <height>{{ vscale(200) }}</height>
            <control type="grouplist" id="300">
                <animation effect="fade" start="0" end="100" time="200" reversible="true">VisibleChange</animation>
                <!-- 302 (Play), not the old 301 (Info) - the Info button itself is gone from this
                     row now (on request): the summary textbox is its own click/focus target for the
                     same action (SUMMARY_BUTTON_ID, id 305, subitems.py), so the explicit button was
                     redundant. -->
                <defaultcontrol>302</defaultcontrol>
                <posx>63</posx>
                <posy>{{ vscale(25) }}</posy>
                <width>1000</width>
                <height>{{ vscale(145) }}</height>
                <!-- 305 (the summary click-target), not straight to 200: keeps that new focus stop
                     reachable from the button row via remote/keyboard, not just mouse/touch. -->
                <onup>305</onup>
                <ondown>400</ondown>
                <onleft>9000</onleft>
                <itemgap>{{ theme.artist.buttongroup.itemgap }}</itemgap>
                <orientation>horizontal</orientation>
                <scrolltime tween="quadratic" easing="out">200</scrolltime>
                <usecontrolcoords>true</usecontrolcoords>

                <!-- Label-on-focus pill overlays (392-394): same recipe as every other button row
                     (episode_button_label.xml.tpl - see button-label-overlay-recipe). Play/More
                     reuse Pre-play's/Seasons' own $ADDON strings and measured widths, since it's the
                     same label text; Shuffle reuses Seasons' own. -->
                {% with attr = theme.artist.buttons & template = "includes/themed_button.xml.tpl" & hitrect = theme.artist.buttons_hitrect & ol = "includes/episode_button_label.xml.tpl" %}
                    {% include template with name="play" & id=302 %}
                    {% include ol with id=392 & visible="Control.HasFocus(302)" & name="play" &
                        label="$ADDON[script.plexmod 33020]" & label_suffix_info="" &
                        label_width=50 & pill_width=112 & group_width=68 &
                        onleft=302 & onright=303
                    %}
                    {% include template with name="shuffle" & id=303 %}
                    {% include ol with id=393 & visible="Control.HasFocus(303)" & name="shuffle" &
                        label="$ADDON[script.plexmod 32935]" & label_suffix_info="" &
                        label_width=84 & pill_width=146 & group_width=102 &
                        onleft=303 & onright=304
                    %}
                    {% include template with name="more" & id=304 %}
                    {% include ol with id=394 & visible="Control.HasFocus(304)" & name="more" &
                        label="$ADDON[script.plexmod 32307]" & label_suffix_info="" &
                        label_width=60 & pill_width=122 & group_width=78 &
                        onleft=304 & onright=""
                    %}
                {% endwith %}

            </control>
        </control>
    {% endblock %}

    <control type="group">
        <!-- posx=0, not the old thumb-layout's 60: that offset existed to clear the (now-removed)
             519-wide thumb, stacking on top of group 50's own posx and pushing title/genre/summary
             68px further right than Seasons' own column (52+0+61=113) once they were moved in to
             posx=61 each - matches Seasons' own inner group (posx=0) exactly now. -->
        <posx>0</posx>
        <posy>0</posy>
        <width>1920</width>
        <height>{{ vscale(367) }}</height>
        <!-- Title/genre-line/summary repositioned, resized and restyled to match Seasons' own
             header block exactly (script-plex-seasons.xml.tpl) - title's own big/bottom-aligned
             style, genre line using the seasons meta row's own position/size/style
             (includes/pp_meta_row.xml.tpl) but keeping this screen's own single artist.genre
             property rather than that include's compound duration/date/genres/rating line, summary
             matching Seasons' own textbox (autoscroll, not a scrollbar - the old pagecontrol=152
             here never had a matching scrollbar control to pair with, so it was always dead). Thumb
             dropped entirely (on request) - ArtistWindow.updateProperties() (subitems.py) no longer
             sets the now-unused 'thumb' property either. -->
        <control type="label">
            <!-- Position/style originally copied from Episodes' own episode-name label
                 (script-plex-episodes.xml.tpl, no-logo variant - Artist never has a clearlogo):
                 FFD2CCCE/aligny=top instead of the previous font45/FFFFFFFF/aligny=bottom big-title
                 treatment. posy=117, not that label's own raw 97: Episodes' own comment there notes
                 its 97 is "the reference screens' value minus 20" to compensate for Episodes' group
                 50 sitting at posy=155 instead of 135 - Artist's group already sits at 135 (matches
                 Seasons'/Pre-play's own baseline), so the untranslated 117 is the correct equivalent
                 here, not a literal copy of 97. Font since bumped up from that label's own
                 font32_title to font45_title (on request, through several intermediate sizes) and
                 width/height retuned to 708/61 (on request) - width now matches the genre line
                 below rather than that label's own 616/660. -->
            <posx>61</posx>
            <posy>{{ vscale(107) }}</posy>
            <width>708</width>
            <height>{{ vscale(61) }}</height>
            <font>font45_title</font>
            <align>left</align>
            <aligny>top</aligny>
            <scroll>true</scroll>
            <scrollspeed>35</scrollspeed>
            <textcolor>FFD2CCCE</textcolor>
            <label>$INFO[Window.Property(artist.title)]</label>
        </control>
        <control type="label">
            <posx>61</posx>
            <posy>{{ vscale(175) }}</posy>
            <width>708</width>
            <height>{{ vscale(30) }}</height>
            <font>font10</font>
            <align>left</align>
            <textcolor>FFD2CCCE</textcolor>
            <shadowcolor>66000000</shadowcolor>
            <label>$INFO[Window.Property(artist.genre)]</label>
        </control>
        <control type="textbox">
            <posx>61</posx>
            <posy>{{ vscale(277) }}</posy>
            <width>813</width>
            <height>{{ vscale(90) }}</height>
            <font>font10</font>
            <align>left</align>
            <textcolor>FFD2CCCE</textcolor>
            <shadowcolor>66000000</shadowcolor>
            <scrolltime>200</scrolltime>
            <autoscroll delay="2000" time="2000" repeat="10000">true</autoscroll>
            <label>$INFO[Window.Property(summary)]</label>
        </control>
        <!-- Invisible click/focus target laid directly over the summary textbox above - textboxes
             have no click or focus of their own in Kodi, so this is a separate button control sized
             and positioned to match it exactly, wired to infoButtonClicked() (SUMMARY_BUTTON_ID,
             subitems.py) - the only way left to reach it now that the button row's own explicit
             Info button (301) has been dropped entirely (on request, this became redundant with it).
             Blank label (matches themed_button.xml.tpl's own convention) so nothing draws over the
             textbox's real text.
             texturenofocus/texturefocus both "-" (explicit none, not just omitted - Kodi otherwise
             falls back to its own default button look, seen live as a dark box over the textbox) -
             the focus highlight itself is the separate image below instead, not this control's own
             texture, so it can be sized bigger than the actual hit area. -->
        <control type="button" id="305">
            <posx>61</posx>
            <posy>{{ vscale(277) }}</posy>
            <width>813</width>
            <height>{{ vscale(90) }}</height>
            <onup>200</onup>
            <ondown>300</ondown>
            <onleft>9000</onleft>
            <label> </label>
            <texturenofocus>-</texturenofocus>
            <texturefocus>-</texturefocus>
        </control>
        <!-- Focus highlight for 305 above, kept as its own image rather than that button's own
             texturefocus so it can extend 5px past the button's own hit area on every side (on
             request) without changing what's actually clickable/focusable. -->
        <control type="image">
            <visible>Control.HasFocus(305)</visible>
            <posx>56</posx>
            <posy>{{ vscale(272) }}</posy>
            <width>823</width>
            <height>{{ vscale(100) }}</height>
            <colordiffuse>33FFFFFF</colordiffuse>
            <texture border="10">script.plex/white-square-rounded.png</texture>
        </control>
    </control>

    <control type="group" id="100">
        <visible>Integer.IsGreater(Container(400).NumItems,0) + String.IsEmpty(Window.Property(drawing))</visible>
        <defaultcontrol>400</defaultcontrol>
        <posx>0</posx>
        <posy>{{ vscale(585) }}</posy>
        <width>1920</width>
        <height>{{ vscale(360) }}</height>
        <control type="image">
            <posx>0</posx>
            <posy>0</posy>
            <width>1920</width>
            <height>{{ vscale(360) }}</height>
            <texture>script.plex/white-square.png</texture>
            <colordiffuse>20000000</colordiffuse>
        </control>
        <control type="list" id="400">
            <posx>0</posx>
            <posy>{{ vscale(-20) }}</posy>
            <width>1920</width>
            <height>{{ vscale(700) }}</height>
            <onup>300</onup>
            <ondown>401</ondown>
            <!-- No pagination on this list (fill() adds every album up front), so no boundary
                 markers to protect - straight to the sidebar. -->
            <onleft>9000</onleft>
            <scrolltime>200</scrolltime>
            <orientation>horizontal</orientation>
            <preloaditems>2</preloaditems>
            <!-- ITEM LAYOUT ########################################## -->
            <itemlayout width="260">
                <control type="group">
                    <posx>60</posx>
                    <posy>{{ vscale(60) }}</posy>
                    <control type="group">
                        <posx>0</posx>
                        <posy>0</posy>
                        <control type="image">
                            <posx>0</posx>
                            <posy>0</posy>
                            <width>215</width>
                            <height>{{ vscale(215) }}</height>
                            <texture>$INFO[ListItem.Property(thumb.fallback)]</texture>
                        </control>
                        <control type="image">
                            <posx>0</posx>
                            <posy>0</posy>
                            <width>215</width>
                            <height>{{ vscale(215) }}</height>
                            <texture background="true">$INFO[ListItem.Thumb]</texture>
                            <aspectratio>scale</aspectratio>
                        </control>
                        <control type="group">
                            <posx>0</posx>
                            <posy>{{ vscale(220) }}</posy>
                            <control type="label">
                                <posx>0</posx>
                                <posy>0</posy>
                                <width>215</width>
                                <height>{{ vscale(30) }}</height>
                                <font>font10</font>
                                <align>center</align>
                                <textcolor>FFFFFFFF</textcolor>
                                <label>$INFO[ListItem.Label]</label>
                            </control>
                            <control type="label">
                                <posx>0</posx>
                                <posy>{{ vscale(30) }}</posy>
                                <width>215</width>
                                <height>{{ vscale(30) }}</height>
                                <font>font10</font>
                                <align>center</align>
                                <textcolor>FFFFFFFF</textcolor>
                                <label>$INFO[ListItem.Property(year)]</label>
                            </control>
                        </control>
                    </control>
                </control>
            </itemlayout>

            <!-- FOCUSED LAYOUT ####################################### -->
            <focusedlayout width="260">
                <control type="group">
                    <posx>60</posx>
                    <posy>{{ vscale(60) }}</posy>
                    <control type="group">
                        <animation effect="zoom" start="100" end="110" time="100" center="107.5,{{ vscale(107.5) }}" reversible="false">Focus</animation>
                        <animation effect="zoom" start="110" end="100" time="100" center="107.5,{{ vscale(107.5) }}" reversible="false">UnFocus</animation>
                        <control type="group">
                            <posx>0</posx>
                            <posy>0</posy>
                            <control type="image">
                                <visible>Control.HasFocus(400)</visible>
                                <posx>-40</posx>
                                <posy>{{ vscale(-40) }}</posy>
                                <width>295</width>
                                <height>{{ vscale(295) }}</height>
                                <texture border="40">script.plex/square-rounded-shadow.png</texture>
                            </control>
                            <control type="image">
                                <posx>0</posx>
                                <posy>0</posy>
                                <width>215</width>
                                <height>{{ vscale(215) }}</height>
                                <texture>$INFO[ListItem.Property(thumb.fallback)]</texture>
                            </control>
                            <control type="image">
                                <posx>0</posx>
                                <posy>0</posy>
                                <width>215</width>
                                <height>{{ vscale(215) }}</height>
                                <texture background="true">$INFO[ListItem.Thumb]</texture>
                                <aspectratio>scale</aspectratio>
                            </control>
                            <control type="group">
                                <posx>0</posx>
                                <posy>{{ vscale(220) }}</posy>
                                <control type="label">
                                    <scroll>false</scroll>
                                    <posx>0</posx>
                                    <posy>0</posy>
                                    <width>215</width>
                                    <height>{{ vscale(30) }}</height>
                                    <font>font10</font>
                                    <align>center</align>
                                    <textcolor>FFFFFFFF</textcolor>
                                    <label>$INFO[ListItem.Label]</label>
                                </control>
                                <control type="label">
                                    <posx>0</posx>
                                    <posy>{{ vscale(30) }}</posy>
                                    <width>215</width>
                                    <height>{{ vscale(30) }}</height>
                                    <font>font10</font>
                                    <align>center</align>
                                    <textcolor>FFFFFFFF</textcolor>
                                    <label>$INFO[ListItem.Property(year)]</label>
                                </control>
                            </control>
                        </control>
                        <control type="image">
                            <visible>Control.HasFocus(400)</visible>
                            <posx>-5</posx>
                            <posy>{{ vscale(-5) }}</posy>
                            <width>225</width>
                            <height>{{ vscale(225) }}</height>
                            <texture border="10">script.plex/home/selected.png</texture>
                        </control>
                    </control>
                </control>
            </focusedlayout>
        </control>
    </control>

    <!-- similar artists -->
    <control type="group" id="500">
        <visible>Integer.IsGreater(Container(401).NumItems,0) + String.IsEmpty(Window.Property(drawing))</visible>
        <defaultcontrol>401</defaultcontrol>
        <width>1920</width>
        <height>{{ vscale(520) }}</height>
        <posx>0</posx>
        <posy>{{ vscale(945) }}</posy>
        <control type="label">
            <posx>60</posx>
            <posy>0</posy>
            <width>1000</width>
            <height>{{ vscale(80) }}</height>
            <font>font12</font>
            <align>left</align>
            <aligny>center</aligny>
            <textcolor>FFFFFFFF</textcolor>
            <label>[UPPERCASE]$INFO[Window.Property(related.header)][/UPPERCASE]</label>
        </control>
        <control type="list" id="401">
            <posx>0</posx>
            <posy>{{ vscale(16) }}</posy>
            <width>1920</width>
            <height>{{ vscale(520) }}</height>
            <onup>400</onup>
            <ondown>false</ondown>
            <!-- RelatedPaginator always starts at offset=0 and never produces a left-boundary
                 marker (same as Episodes' Related row), so noop here was already a dead end -
                 safe to go straight to the sidebar. onright stays an unconditional hard stop. -->
            <onleft>9000</onleft>
            <onright>noop</onright>
            <scrolltime>200</scrolltime>
            <orientation>horizontal</orientation>
            <preloaditems>4</preloaditems>
            <!-- ITEM LAYOUT ########################################## -->
            <itemlayout width="260">
                <control type="group">
                    <posx>60</posx>
                    <posy>{{ vscale(60) }}</posy>
                    <control type="group">
                        <posx>0</posx>
                        <posy>0</posy>
                        <control type="image">
                            <posx>0</posx>
                            <posy>0</posy>
                            <width>215</width>
                            <height>{{ vscale(215) }}</height>
                            <texture>$INFO[ListItem.Property(thumb.fallback)]</texture>
                        </control>
                        <control type="image">
                            <posx>0</posx>
                            <posy>0</posy>
                            <width>215</width>
                            <height>{{ vscale(215) }}</height>
                            <texture background="true">$INFO[ListItem.Thumb]</texture>
                            <aspectratio>scale</aspectratio>
                        </control>
                        <control type="group">
                            <posx>0</posx>
                            <posy>{{ vscale(220) }}</posy>
                            <control type="label">
                                <posx>0</posx>
                                <posy>0</posy>
                                <width>215</width>
                                <height>{{ vscale(30) }}</height>
                                <font>font10</font>
                                <align>center</align>
                                <textcolor>FFFFFFFF</textcolor>
                                <label>$INFO[ListItem.Label]</label>
                            </control>
                            <control type="label">
                                <posx>0</posx>
                                <posy>{{ vscale(30) }}</posy>
                                <width>215</width>
                                <height>{{ vscale(30) }}</height>
                                <font>font10</font>
                                <align>center</align>
                                <textcolor>FFFFFFFF</textcolor>
                                <label>$INFO[ListItem.Property(year)]</label>
                            </control>
                        </control>
                        <control type="group">
                            <visible>!String.IsEmpty(ListItem.Property(is.boundary))</visible>
                            <control type="image">
                                <posx>0</posx>
                                <posy>0</posy>
                                <width>215</width>
                                <height>{{ vscale(215) }}</height>
                                <texture colordiffuse="FF404040">script.plex/white-square.png</texture>
                            </control>
                            <control type="image">
                                <visible>String.IsEmpty(ListItem.Property(is.updating)) + !String.IsEmpty(ListItem.Property(right.boundary))</visible>
                                <posx>77</posx>
                                <posy>{{ vscale(57.5) }}</posy>
                                <width>61</width>
                                <height>{{ vscale(100) }}</height>
                                <texture colordiffuse="40000000">script.plex/indicators/chevron-white.png</texture>
                            </control>
                            <control type="image">
                                <visible>String.IsEmpty(ListItem.Property(is.updating)) + !String.IsEmpty(ListItem.Property(left.boundary))</visible>
                                <posx>77</posx>
                                <posy>{{ vscale(57.5) }}</posy>
                                <width>61</width>
                                <height>{{ vscale(100) }}</height>
                                <texture colordiffuse="40000000">script.plex/indicators/chevron-white-l.png</texture>
                            </control>
                            <control type="image">
                                <visible>!String.IsEmpty(ListItem.Property(is.updating))</visible>
                                <posx>43.5</posx>
                                <posy>{{ vscale(43.5) }}</posy>
                                <width>128</width>
                                <height>{{ vscale(128) }}</height>
                                <texture>script.plex/home/busy.gif</texture>
                            </control>
                        </control>
                    </control>
                </control>
            </itemlayout>

            <!-- FOCUSED LAYOUT ####################################### -->
            <focusedlayout width="260">
                <control type="group">
                    <posx>60</posx>
                    <posy>{{ vscale(60) }}</posy>
                    <control type="group">
                        <animation effect="zoom" start="100" end="110" time="100" center="107.5,{{ vscale(107.5) }}" reversible="false">Focus</animation>
                        <animation effect="zoom" start="110" end="100" time="100" center="107.5,{{ vscale(107.5) }}" reversible="false">UnFocus</animation>
                        <control type="group">
                            <posx>0</posx>
                            <posy>0</posy>
                            <control type="image">
                                <visible>Control.HasFocus(400)</visible>
                                <posx>-40</posx>
                                <posy>{{ vscale(-40) }}</posy>
                                <width>295</width>
                                <height>{{ vscale(295) }}</height>
                                <texture border="40">script.plex/square-rounded-shadow.png</texture>
                            </control>
                            <control type="image">
                                <posx>0</posx>
                                <posy>0</posy>
                                <width>215</width>
                                <height>{{ vscale(215) }}</height>
                                <texture>$INFO[ListItem.Property(thumb.fallback)]</texture>
                            </control>
                            <control type="image">
                                <posx>0</posx>
                                <posy>0</posy>
                                <width>215</width>
                                <height>{{ vscale(215) }}</height>
                                <texture background="true">$INFO[ListItem.Thumb]</texture>
                                <aspectratio>scale</aspectratio>
                            </control>
                            <control type="group">
                                <posx>0</posx>
                                <posy>{{ vscale(220) }}</posy>
                                <control type="label">
                                    <scroll>false</scroll>
                                    <posx>0</posx>
                                    <posy>0</posy>
                                    <width>215</width>
                                    <height>{{ vscale(30) }}</height>
                                    <font>font10</font>
                                    <align>center</align>
                                    <textcolor>FFFFFFFF</textcolor>
                                    <label>$INFO[ListItem.Label]</label>
                                </control>
                                <control type="label">
                                    <posx>0</posx>
                                    <posy>{{ vscale(30) }}</posy>
                                    <width>215</width>
                                    <height>{{ vscale(30) }}</height>
                                    <font>font10</font>
                                    <align>center</align>
                                    <textcolor>FFFFFFFF</textcolor>
                                    <label>$INFO[ListItem.Property(year)]</label>
                                </control>
                            </control>
                        </control>
                        <control type="image">
                            <visible>Control.HasFocus(401)</visible>
                            <posx>-5</posx>
                            <posy>{{ vscale(-5) }}</posy>
                            <width>225</width>
                            <height>{{ vscale(225) }}</height>
                            <texture border="10">script.plex/home/selected.png</texture>
                        </control>
                        <control type="group">
                            <visible>!String.IsEmpty(ListItem.Property(is.boundary))</visible>
                            <control type="image">
                                <posx>0</posx>
                                <posy>0</posy>
                                <width>215</width>
                                <height>{{ vscale(215) }}</height>
                                <texture colordiffuse="FF404040">script.plex/white-square.png</texture>
                            </control>
                            <control type="image">
                                <visible>String.IsEmpty(ListItem.Property(is.updating)) + !String.IsEmpty(ListItem.Property(right.boundary))</visible>
                                <posx>77</posx>
                                <posy>{{ vscale(57.5) }}</posy>
                                <width>61</width>
                                <height>{{ vscale(100) }}</height>
                                <texture colordiffuse="40000000">script.plex/indicators/chevron-white.png</texture>
                            </control>
                            <control type="image">
                                <visible>String.IsEmpty(ListItem.Property(is.updating)) + !String.IsEmpty(ListItem.Property(left.boundary))</visible>
                                <posx>77</posx>
                                <posy>{{ vscale(57.5) }}</posy>
                                <width>61</width>
                                <height>{{ vscale(100) }}</height>
                                <texture colordiffuse="40000000">script.plex/indicators/chevron-white-l.png</texture>
                            </control>
                            <control type="image">
                                <visible>!String.IsEmpty(ListItem.Property(is.updating))</visible>
                                <posx>43.5</posx>
                                <posy>{{ vscale(43.5) }}</posy>
                                <width>128</width>
                                <height>{{ vscale(128) }}</height>
                                <texture>script.plex/home/busy.gif</texture>
                            </control>
                        </control>
                    </control>
                </control>
            </focusedlayout>
        </control>
    </control>
</control>
{% endblock content %}