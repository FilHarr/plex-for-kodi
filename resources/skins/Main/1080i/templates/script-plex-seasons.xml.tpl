{% extends "default.xml.tpl" %}
{% block header_topleft %}{% endblock %}
{% block header %}
    {{ super() }}
    {% include "includes/sidebar.xml.tpl" %}
{% endblock header %}
{% block content %}
<control type="group" id="50">
    <animation effect="slide" end="0,{{ vscale(-300) }}" time="200" tween="quadratic" easing="out" condition="!String.IsEmpty(Window.Property(on.extras))">Conditional</animation>

    <!-- Slide right while the sidebar rail is expanded (focused), matching Home/Library/Pre-play/Episodes -->
    <animation effect="slide" end="220,0" time="200" tween="sine" easing="inout" condition="ControlGroup(9000).HasFocus(0)">Conditional</animation>

    <animation type="Conditional" condition="Integer.IsGreater(Window.Property(hub.focus),0) + Control.IsVisible(500)" reversible="true">
        <effect type="slide" end="0,{{ vscale(-500) }}" time="200" tween="quadratic" easing="out"/>
    </animation>

    <animation type="Conditional" condition="Integer.IsGreater(Window.Property(hub.focus),1) + Control.IsVisible(501)" reversible="true">
        <effect type="slide" end="0,{{ vscale(-360) }}" time="200" tween="quadratic" easing="out"/>
    </animation>

    <animation type="Conditional" condition="Integer.IsGreater(Window.Property(hub.focus),2) + Control.IsVisible(502)" reversible="true">
        <effect type="slide" end="0,{{ vscale(-500) }}" time="200" tween="quadratic" easing="out"/>
    </animation>

    <!-- posx=60, not 0: clears the collapsed sidebar rail's icon column, matching Home/Library/Pre-play/
         Episodes. Every child below is positioned relative to this group, so the shift applies uniformly. -->
    <posx>60</posx>
    <posy>{{ vscale(155) }}</posy>
    <defaultcontrol>101</defaultcontrol>

    {% block buttons %}
        <control type="grouplist" id="300">
            <animation effect="fade" start="0" end="100" time="200" reversible="true">VisibleChange</animation>
            <visible>!String.IsEmpty(Window.Property(initialized))</visible>
            <defaultcontrol>302</defaultcontrol>
            <!-- posx/posy match Pre-play's button row exactly (script-plex-pre_play.xml.tpl) - same
                 152x121 button box (theme.seasons.buttons now kept in lockstep with theme.pre_play.buttons,
                 see context.py), so the same position clears the poster/hub-row stack the same way. -->
            <posx>22</posx>
            <posy>{{ vscale(481) }}</posy>
            <width>1000</width>
            <height>{{ vscale(145) }}</height>
            <onup>200</onup>
            <ondown>400</ondown>
            <onleft>9000</onleft>
            <itemgap>{{ theme.seasons.buttongroup.itemgap }}</itemgap>
            <orientation>horizontal</orientation>
            <scrolltime tween="quadratic" easing="out">200</scrolltime>
            <usecontrolcoords>true</usecontrolcoords>

            {% with attr = theme.seasons.buttons & template = "includes/themed_button.xml.tpl" & hitrect = None %} {# fixme: should hitrect be None? #}
                {% include template with name="info" & id=301 %}
                {% include template with name="play" & id=302 & visible="String.IsEmpty(Window.Property(disable_playback))" %}
                {% include "includes/wl_dynamic_buttons.xml.tpl" %}
                {% include "includes/wl_add_remove_buttons.xml.tpl" %}
                {% include template with name="shuffle" & id=303 & visible="String.IsEmpty(Window.Property(disable_playback))" %}
                {% include template with name="more" & id=304 & visible="String.IsEmpty(Window.Property(disable_playback))" %}
            {% endwith %}

        </control>
    {% endblock %}

    <control type="group">
        <posx>0</posx>
        <posy>0</posy>
        <width>1920</width>
        <height>{{ vscale(600) }}</height>
        <control type="group">
            <visible>String.IsEmpty(Window.Property(hide.poster))</visible>
            <control type="image">
                <posx>60</posx>
                <posy>0</posy>
                <width>314</width>
                <height>{{ vscale(467) }}</height>
                <texture background="true">script.plex/thumb_fallbacks/movie.png</texture>
                <animation effect="fade" start="0" end="100" time="0" delay="500">WindowOpen</animation>
                <aspectratio>scale</aspectratio>
            </control>
            <control type="image">
                <posx>60</posx>
                <posy>0</posy>
                <width>314</width>
                <height>{{ vscale(467) }}</height>
                <texture background="true">$INFO[Window.Property(thumb)]</texture>
                <aspectratio>scale</aspectratio>
            </control>
            {% include "includes/watched_indicator.xml.tpl" with itemref="Window" & xoff=314+60 & uw_size=48 & with_count=True & scale="large" %}
        </control>

        <!-- Title/clearlogo duplicated at two x-offsets (433 with the poster, 60 filling its slot when
             hidden) and switched with <visible>, since posx/width can't take a condition in Kodi - see
             script-plex-pre_play.xml.tpl for the reference implementation these mirror verbatim. -->
        <control type="label">
            <visible>String.IsEmpty(Window.Property(hide.poster)) + String.IsEmpty(Window.Property(clear.logo))</visible>
            <posx>433</posx>
            <posy>0</posy>
            <width>880</width>
            <height>{{ vscale(68) }}</height>
            <font>font45</font>
            <align>left</align>
            <aligny>bottom</aligny>
            <scroll>true</scroll>
            <scrollspeed>35</scrollspeed>
            <textcolor>FFFFFFFF</textcolor>
            <label>$INFO[Window.Property(title)]</label>
        </control>
        <control type="label">
            <visible>!String.IsEmpty(Window.Property(hide.poster)) + String.IsEmpty(Window.Property(clear.logo))</visible>
            <posx>60</posx>
            <posy>0</posy>
            <width>940</width>
            <height>{{ vscale(136) }}</height>
            <font>font45</font>
            <align>left</align>
            <aligny>bottom</aligny>
            <scroll>true</scroll>
            <scrollspeed>35</scrollspeed>
            <textcolor>FFFFFFFF</textcolor>
            <label>$INFO[Window.Property(title)]</label>
        </control>
        <control type="image">
            <visible>String.IsEmpty(Window.Property(hide.poster)) + !String.IsEmpty(Window.Property(clear.logo))</visible>
            <posx>433</posx>
            <posy>0</posy>
            <width>873</width>
            <height>{{ vscale(106) }}</height>
            <aspectratio align="left" aligny="bottom">keep</aspectratio>
            <texture background="true">$INFO[Window.Property(clear.logo)]</texture>
        </control>
        <control type="image">
            <visible>!String.IsEmpty(Window.Property(hide.poster)) + !String.IsEmpty(Window.Property(clear.logo))</visible>
            <posx>60</posx>
            <posy>0</posy>
            <width>760</width>
            <height>{{ vscale(136) }}</height>
            <aspectratio align="left" aligny="bottom">keep</aspectratio>
            <texture background="true">$INFO[Window.Property(clear.logo)]</texture>
        </control>
        {% include "includes/seasons_meta_row.xml.tpl" %}

        <control type="grouplist">
            <visible>!String.IsEmpty(Window.Property(rating)) | !String.IsEmpty(Window.Property(rating2))</visible>
            <!-- posx=1366, not 1426: offset -60 to cancel out group 50's own +60 sidebar-clearance shift -
                 matches Pre-play's identical ratings box exactly (position, width, and now the rating-stars
                 image below too, moved here from the info row to match Pre-play's content split). -->
            <posx>1366</posx>
            <posy>4</posy>
            <width>434</width>
            <height>{{ vscale(32) }}</height>
            <align>right</align>
            <itemgap>15</itemgap>
            <orientation>horizontal</orientation>
            <usecontrolcoords>true</usecontrolcoords>
            <control type="image">
                <visible>!String.IsEmpty(Window.Property(rating))</visible>
                <posy>2</posy>
                <width>63</width>
                <height>{{ vscale(30) }}</height>
                <texture fallback="script.plex/ratings/other/image.rating.png">$INFO[Window.Property(rating.image)]</texture>
                <aspectratio align="right">keep</aspectratio>
            </control>
            <control type="label">
                <visible>!String.IsEmpty(Window.Property(rating))</visible>
                <width>auto</width>
                <height>{{ vscale(30) }}</height>
                <font>font12</font>
                <align>left</align>
                <textcolor>FFFFFFFF</textcolor>
                <label>$INFO[Window.Property(rating)]</label>
            </control>
            <control type="image">
                <visible>!String.IsEmpty(Window.Property(rating2))</visible>
                <posy>2</posy>
                <width>40</width>
                <height>{{ vscale(30) }}</height>
                <texture fallback="script.plex/ratings/other/image.rating.png">$INFO[Window.Property(rating2.image)]</texture>
                <aspectratio align="right">keep</aspectratio>
            </control>
            <control type="label">
                <visible>!String.IsEmpty(Window.Property(rating2))</visible>
                <width>auto</width>
                <height>{{ vscale(30) }}</height>
                <font>font12</font>
                <align>left</align>
                <textcolor>FFFFFFFF</textcolor>
                <label>$INFO[Window.Property(rating2)]</label>
            </control>
            <control type="image">
                <visible>!String.IsEmpty(Window.Property(rating.stars))</visible>
                <posy>6</posy>
                <width>134</width>
                <height>{{ vscale(22) }}</height>
                <texture>script.plex/stars/$INFO[Window.Property(rating.stars)].png</texture>
            </control>
        </control>


        <!-- <control type="grouplist">
            <posx>466</posx>
            <posy>{{ vscale(237) }}</posy>
            <width>1360</width>
            <height>{{ vscale(30) }}</height>
            <align>left</align>
            <itemgap>15</itemgap>
            <orientation>horizontal</orientation>
            <usecontrolcoords>true</usecontrolcoords>
            <control type="button">
                <width>auto</width>
                <height>{{ vscale(30) }}</height>
                <font>font12</font>
                <align>center</align>
                <aligny>center</aligny>
                <focusedcolor>FFFFFFFF</focusedcolor>
                <textcolor>FFFFFFFF</textcolor>
                <textoffsetx>15</textoffsetx>
                <texturefocus colordiffuse="40000000" border="12">script.plex/white-square-rounded.png</texturefocus>
                <texturenofocus colordiffuse="40000000" border="12">script.plex/white-square-rounded.png</texturenofocus>
                <label>AUDIO</label>
            </control>
            <control type="label">
                <width max="1360">auto</width>
                <height>{{ vscale(30) }}</height>
                <font>font12</font>
                <align>left</align>
                <aligny>center</aligny>
                <scroll>true</scroll>
                <scrollspeed>25</scrollspeed>
                <textcolor>FFFFFFFF</textcolor>
                <label>$INFO[Window.Property(audio)]</label>
            </control>
            <control type="button">
                <visible>!String.IsEmpty(Window.Property(subtitles))</visible>
                <left>30</left>
                <width>auto</width>
                <height>{{ vscale(30) }}</height>
                <font>font12</font>
                <align>center</align>
                <aligny>center</aligny>
                <focusedcolor>FFFFFFFF</focusedcolor>
                <textcolor>FFFFFFFF</textcolor>
                <textoffsetx>15</textoffsetx>
                <texturefocus colordiffuse="40000000" border="12">script.plex/white-square-rounded.png</texturefocus>
                <texturenofocus colordiffuse="40000000" border="12">script.plex/white-square-rounded.png</texturenofocus>
                <label>SUBTITLES</label>
            </control>
            <control type="label">
                <visible>!String.IsEmpty(Window.Property(subtitles))</visible>
                <width>auto</width>
                <height>{{ vscale(30) }}</height>
                <font>font12</font>
                <align>left</align>
                <aligny>center</aligny>
                <textcolor>FFFFFFFF</textcolor>
                <label>$INFO[Window.Property(subtitles)]</label>
            </control>
        </control>
        <control type="textbox">
            <posx>466</posx>
            <posy>{{ vscale(300) }}</posy>
            <width>1360</width>
            <height>{{ vscale(113) }}</height>
            <font>font13</font>
            <align>left</align>
            <textcolor>FFFFFFFF</textcolor>
            <label>$INFO[Window.Property(summary)]</label>
        </control> -->
        {% include "includes/wl_availability.xml.tpl" %}
        <control type="textbox">
            <!-- Single control, not duplicated: width/height are identical in both poster states, only
                 posx/posy shift, so a zero-duration Conditional slide does the job of the <visible>-switched
                 pair used where size also changes (title/clearlogo above) - see script-plex-pre_play.xml.tpl's
                 identical treatment of its own summary box. -->
            <animation effect="slide" end="-373,{{ vscale(30) }}" time="0" condition="!String.IsEmpty(Window.Property(hide.poster))">Conditional</animation>
            <posx>433</posx>
            <posy>{{ vscale(176) }}</posy>
            <width>1080</width>
            <height>{{ vscale(152) }}</height>
            <font>font12</font>
            <align>left</align>
            <textcolor>FFFFFFFF</textcolor>
            <label>$INFO[Window.Property(summary)]</label>
        </control>
    </control>

    <control type="grouplist" id="60">
        <posx>0</posx>
        <!-- 540, not 565: aligns this row stack's top edge with Pre-play's cast-row equivalent
             (script-plex-pre_play.xml.tpl's own grouplist 60, also posy=540) - both sit in an identical
             group-50 frame (posx=60, posy=vscale(155)), so matching this one number lines up the absolute
             screen position. -->
        <posy>{{ vscale(540) }}</posy>
        <width>1920</width>
        <height>{{ vscale(1600) }}</height>

        <onup>300</onup>
        <itemgap>0</itemgap>

        <!-- Seasons -->
        <control type="group" id="500">
            <visible>Integer.IsGreater(Container(400).NumItems,0) + String.IsEmpty(Window.Property(drawing))</visible>
            <height>{{ vscale(380) }}</height>
            <width>1920</width>
            <control type="list" id="400">
                <!-- posx=40, not 0 (width shrunk from 1920 to 1880 to match, keeping the local right
                     edge fixed): gives departing thumbnails room to clear the collapsed sidebar rail's
                     icon column before this list's own clip boundary cuts them off - see Episodes'
                     identical fix (script-plex-episodes.xml.tpl grouplist 500, posx 0->40) for the full
                     rationale. Item layouts' own posx reduced by the same 40 below, canceling this out,
                     so resting/focused positions don't move. -->
                <posx>40</posx>
                <posy>{{ vscale(36) }}</posy>
                <width>1880</width>
                <height>{{ vscale(380) }}</height>
                <onup>300</onup>
                <ondown>401</ondown>
                <onleft>9000</onleft>
                <scrolltime>200</scrolltime>
                <orientation>horizontal</orientation>
                <preloaditems>4</preloaditems>
                <!-- ITEM LAYOUT ########################################## -->
                <itemlayout width="218">
                    <control type="group">
                        <posx>15</posx>
                        <posy>{{ vscale(29) }}</posy>
                        <control type="group">
                            <posx>5</posx>
                            <posy>5</posy>
                            <control type="image">
                                <posx>0</posx>
                                <posy>0</posy>
                                <width>158</width>
                                <height>{{ vscale(236) }}</height>
                                <texture>$INFO[ListItem.Property(thumb.fallback)]</texture>
                            </control>
                            <control type="image">
                                <posx>0</posx>
                                <posy>0</posy>
                                <width>158</width>
                                <height>{{ vscale(236) }}</height>
                                <texture background="true">$INFO[ListItem.Thumb]</texture>
                                <aspectratio>scale</aspectratio>
                            </control>
                            {% include "includes/watched_indicator.xml.tpl" with xoff=158 & with_count=True & scale="small" %}
                            <control type="group">
                                <visible>!String.IsEmpty(ListItem.Property(progress))</visible>
                                <posx>0</posx>
                                <posy>{{ vscale(230) }}</posy>
                                <control type="image">
                                    <posx>0</posx>
                                    <posy>0</posy>
                                    <width>158</width>
                                    <height>{{ vscale(6) }}</height>
                                    <texture>script.plex/white-square.png</texture>
                                    <colordiffuse>C0000000</colordiffuse>
                                </control>
                                <control type="image">
                                    <posx>0</posx>
                                    <posy>1</posy>
                                    <width>158</width>
                                    <height>{{ vscale(4) }}</height>
                                    <texture>$INFO[ListItem.Property(progress)]</texture>
                                    <colordiffuse>FFCC7B19</colordiffuse>
                                </control>
                            </control>
                            <control type="label">
                                <scroll>false</scroll>
                                <posx>0</posx>
                                <posy>{{ vscale(240) }}</posy>
                                <width>158</width>
                                <height>{{ vscale(54) }}</height>
                                <font>font10</font>
                                <align>center</align>
                                <textcolor>FFFFFFFF</textcolor>
                                <label>$INFO[ListItem.Label]</label>
                            </control>
                        </control>
                    </control>
                </itemlayout>

                <!-- FOCUSED LAYOUT ####################################### -->
                <focusedlayout width="218">
                    <control type="group">
                        <posx>15</posx>
                        <posy>{{ vscale(29) }}</posy>
                        <control type="group">
                            <animation effect="zoom" start="100" end="110" time="100" center="84,{{ vscale(123) }}" reversible="false">Focus</animation>
                            <animation effect="zoom" start="110" end="100" time="100" center="84,{{ vscale(123) }}" reversible="false">UnFocus</animation>
                            <posx>0</posx>
                            <posy>0</posy>
                            <control type="image">
                                <visible>Control.HasFocus(400)</visible>
                                <posx>-40</posx>
                                <posy>{{ vscale(-40) }}</posy>
                                <width>248</width>
                                <height>{{ vscale(326) }}</height>
                                <texture border="42">script.plex/drop-shadow.png</texture>
                            </control>
                            <control type="group">
                                <posx>5</posx>
                                <posy>5</posy>
                                    <control type="image">
                                    <posx>0</posx>
                                    <posy>0</posy>
                                    <width>158</width>
                                    <height>{{ vscale(236) }}</height>
                                    <texture>$INFO[ListItem.Property(thumb.fallback)]</texture>
                                </control>
                                <control type="image">
                                    <posx>0</posx>
                                    <posy>0</posy>
                                    <width>158</width>
                                    <height>{{ vscale(236) }}</height>
                                    <texture background="true">$INFO[ListItem.Thumb]</texture>
                                    <aspectratio>scale</aspectratio>
                                </control>
                                {% include "includes/watched_indicator.xml.tpl" with xoff=158 & with_count=True & scale="small" %}
                                <control type="group">
                                    <visible>!String.IsEmpty(ListItem.Property(progress))</visible>
                                    <posx>0</posx>
                                    <posy>{{ vscale(230) }}</posy>
                                    <control type="image">
                                        <posx>0</posx>
                                        <posy>0</posy>
                                        <width>158</width>
                                        <height>{{ vscale(6) }}</height>
                                        <texture>script.plex/white-square.png</texture>
                                        <colordiffuse>C0000000</colordiffuse>
                                    </control>
                                    <control type="image">
                                        <posx>0</posx>
                                        <posy>1</posy>
                                        <width>158</width>
                                        <height>{{ vscale(4) }}</height>
                                        <texture>$INFO[ListItem.Property(progress)]</texture>
                                        <colordiffuse>FFCC7B19</colordiffuse>
                                    </control>
                                </control>
                                <control type="label">
                                    <scroll>Control.HasFocus(400)</scroll>
                                    <posx>0</posx>
                                    <posy>{{ vscale(240) }}</posy>
                                    <width>158</width>
                                    <height>{{ vscale(54) }}</height>
                                    <font>font10</font>
                                    <align>center</align>
                                    <textcolor>FFFFFFFF</textcolor>
                                    <label>$INFO[ListItem.Label]</label>
                                </control>
                            </control>
                            <control type="image">
                                <visible>Control.HasFocus(400)</visible>
                                <posx>0</posx>
                                <posy>0</posy>
                                <width>168</width>
                                <height>{{ vscale(246) }}</height>
                                <texture border="10">script.plex/home/selected.png</texture>
                            </control>
                        </control>
                    </control>
                </focusedlayout>
            </control>
        </control>
        <!-- Seasons -->

        <!-- ROLES -->
        <control type="group" id="501">
            <visible>Integer.IsGreater(Container(401).NumItems,0) + String.IsEmpty(Window.Property(drawing))</visible>
            <defaultcontrol>401</defaultcontrol>
            <width>1920</width>
            <height>{{ vscale(400) }}</height>
            <control type="label">
                <posx>60</posx>
                <posy>{{ vscale(-20) }}</posy>
                <width>1000</width>
                <height>{{ vscale(80) }}</height>
                <font>font12</font>
                <align>left</align>
                <aligny>center</aligny>
                <textcolor>FFFFFFFF</textcolor>
                <label>[UPPERCASE]$ADDON[script.plexmod 32419][/UPPERCASE]</label>
            </control>
            <control type="list" id="401">
                <!-- posx=40, not 0 (width shrunk to match): see list 400's comment above for the full
                     rationale (sidebar rail clip-boundary clearance). -->
                <posx>40</posx>
                <posy>0</posy>
                <width>1880</width>
                <height>{{ vscale(400) }}</height>
                <onup>400</onup>
                <ondown>402</ondown>
                <onleft>9000</onleft>
                <scrolltime>200</scrolltime>
                <orientation>horizontal</orientation>
                <preloaditems>4</preloaditems>
                <!-- ITEM LAYOUT ########################################## -->
                <itemlayout width="304">
                    <control type="group">
                        <posx>15</posx>
                        <posy>{{ vscale(61) }}</posy>
                        <control type="group">
                            <posx>5</posx>
                            <posy>5</posy>
                            <control type="image">
                                <posx>0</posx>
                                <posy>0</posy>
                                <width>244</width>
                                <height>{{ vscale(244) }}</height>
                                <texture diffuse="script.plex/masks/role.png">script.plex/thumb_fallbacks/role.png</texture>
                            </control>
                            <control type="image">
                                <posx>0</posx>
                                <posy>0</posy>
                                <width>244</width>
                                <height>{{ vscale(244) }}</height>
                                <texture background="true" diffuse="script.plex/masks/role.png">$INFO[ListItem.Thumb]</texture>
                                <aspectratio scalediffuse="false" aligny="top">scale</aspectratio>
                            </control>
                            <control type="group">
                                <posx>0</posx>
                                <posy>{{ vscale(253) }}</posy>
                                <control type="label">
                                    <scroll>false</scroll>
                                    <posx>0</posx>
                                    <posy>0</posy>
                                    <width>244</width>
                                    <height>{{ vscale(60) }}</height>
                                    <font>font10</font>
                                    <align>center</align>
                                    <textcolor>AAFFFFFF</textcolor>
                                    <label>$INFO[ListItem.Label]</label>
                                </control>
                                <control type="label">
                                    <scroll>false</scroll>
                                    <posx>0</posx>
                                    <posy>{{ vscale(30) }}</posy>
                                    <width>244</width>
                                    <height>{{ vscale(60) }}</height>
                                    <font>font10</font>
                                    <align>center</align>
                                    <textcolor>AAFFFFFF</textcolor>
                                    <label>$INFO[ListItem.Label2]</label>
                                </control>
                            </control>
                        </control>
                    </control>
                </itemlayout>

                <!-- FOCUSED LAYOUT ####################################### -->
                <focusedlayout width="304">
                    <control type="group">
                        <posx>15</posx>
                        <posy>{{ vscale(61) }}</posy>
                        <control type="group">
                            <animation effect="zoom" start="100" end="110" time="100" center="127,{{ vscale(127) }}" reversible="false">Focus</animation>
                            <animation effect="zoom" start="110" end="100" time="100" center="127,{{ vscale(127) }}" reversible="false">UnFocus</animation>
                            <posx>0</posx>
                            <posy>0</posy>
                            <control type="image">
                                <visible>Control.HasFocus(401)</visible>
                                <posx>-40</posx>
                                <posy>{{ vscale(-40) }}</posy>
                                <width>334</width>
                                <height>{{ vscale(334) }}</height>
                                <texture border="42">script.plex/buttons/role-shadow.png</texture>
                            </control>
                            <control type="group">
                                <posx>5</posx>
                                <posy>5</posy>
                                <control type="image">
                                    <posx>0</posx>
                                    <posy>0</posy>
                                    <width>244</width>
                                    <height>{{ vscale(244) }}</height>
                                    <texture diffuse="script.plex/masks/role.png">script.plex/thumb_fallbacks/role.png</texture>
                                </control>
                                <control type="image">
                                    <posx>0</posx>
                                    <posy>0</posy>
                                    <width>244</width>
                                    <height>{{ vscale(244) }}</height>
                                    <texture background="true" diffuse="script.plex/masks/role.png">$INFO[ListItem.Thumb]</texture>
                                    <aspectratio scalediffuse="false" aligny="top">scale</aspectratio>
                                </control>
                                <control type="group">
                                    <posx>0</posx>
                                    <posy>{{ vscale(253) }}</posy>
                                    <control type="label">
                                        <scroll>Control.HasFocus(401)</scroll>
                                        <posx>0</posx>
                                        <posy>0</posy>
                                        <width>244</width>
                                        <height>{{ vscale(60) }}</height>
                                        <font>font10</font>
                                        <align>center</align>
                                        <textcolor>AAFFFFFF</textcolor>
                                        <label>$INFO[ListItem.Label]</label>
                                    </control>
                                    <control type="label">
                                        <scroll>Control.HasFocus(401)</scroll>
                                        <posx>0</posx>
                                        <posy>{{ vscale(30) }}</posy>
                                        <width>244</width>
                                        <height>{{ vscale(60) }}</height>
                                        <font>font10</font>
                                        <align>center</align>
                                        <textcolor>AAFFFFFF</textcolor>
                                        <label>$INFO[ListItem.Label2]</label>
                                    </control>
                                </control>
                            </control>
                            <control type="image">
                                <visible>Control.HasFocus(401)</visible>
                                <posx>0</posx>
                                <posy>0</posy>
                                <width>254</width>
                                <height>{{ vscale(254) }}</height>
                                <texture>script.plex/buttons/role-selected.png</texture>
                            </control>
                        </control>
                    </control>
                </focusedlayout>
            </control>
        </control>
        <!-- ROLES -->

        <!-- EXTRAS -->
        <control type="group" id="502">
            <visible>Integer.IsGreater(Container(402).NumItems,0) + String.IsEmpty(Window.Property(drawing))</visible>
            <height>{{ vscale(360) }}</height>
            <width>1920</width>
            <control type="label">
                <posx>60</posx>
                <posy>0</posy>
                <width>800</width>
                <height>{{ vscale(80) }}</height>
                <font>font12</font>
                <align>left</align>
                <aligny>center</aligny>
                <textcolor>FFFFFFFF</textcolor>
                <label>[UPPERCASE]$INFO[Window.Property(extras.header)][/UPPERCASE]</label>
            </control>
            <control type="list" id="402">
                <!-- posx=40, not 0 (width shrunk to match): see list 400's comment above for the full
                     rationale (sidebar rail clip-boundary clearance). -->
                <posx>40</posx>
                <posy>{{ vscale(18) }}</posy>
                <width>1880</width>
                <height>{{ vscale(430) }}</height>
                <onup>401</onup>
                <ondown>403</ondown>
                <onleft>9000</onleft>
                <scrolltime>200</scrolltime>
                <orientation>horizontal</orientation>
                <preloaditems>4</preloaditems>
                <!-- ITEM LAYOUT ########################################## -->
                <itemlayout width="359">
                    <control type="group">
                        <posx>15</posx>
                        <posy>{{ vscale(61) }}</posy>
                        <control type="group">
                            <posx>5</posx>
                            <posy>5</posy>
                            <control type="image">
                                <posx>0</posx>
                                <posy>0</posy>
                                <width>299</width>
                                <height>{{ vscale(168) }}</height>
                                <texture>$INFO[ListItem.Property(thumb.fallback)]</texture>
                                <aspectratio>scale</aspectratio>
                            </control>
                            <control type="image">
                                <posx>0</posx>
                                <posy>0</posy>
                                <width>299</width>
                                <height>{{ vscale(168) }}</height>
                                <texture background="true">$INFO[ListItem.Thumb]</texture>
                                <aspectratio>scale</aspectratio>
                            </control>
                            <control type="label">
                                <scroll>false</scroll>
                                <posx>0</posx>
                                <posy>{{ vscale(175) }}</posy>
                                <width>299</width>
                                <height>{{ vscale(60) }}</height>
                                <font>font12</font>
                                <align>center</align>
                                <textcolor>FFFFFFFF</textcolor>
                                <label>$INFO[ListItem.Label]</label>
                            </control>
                            <control type="label">
                                <scroll>false</scroll>
                                <posx>0</posx>
                                <posy>{{ vscale(210) }}</posy>
                                <width>299</width>
                                <height>{{ vscale(60) }}</height>
                                <font>font12</font>
                                <align>center</align>
                                <textcolor>FFFFFFFF</textcolor>
                                <label>$INFO[ListItem.Label2]</label>
                            </control>
                        </control>
                    </control>
                </itemlayout>

                <!-- FOCUSED LAYOUT ####################################### -->
                <focusedlayout width="359">
                    <control type="group">
                        <posx>15</posx>
                        <posy>{{ vscale(61) }}</posy>
                        <control type="group">
                            <animation effect="zoom" start="100" end="110" time="100" center="154.5,{{ vscale(87.5) }}" reversible="false">Focus</animation>
                            <animation effect="zoom" start="110" end="100" time="100" center="154.5,{{ vscale(87.5) }}" reversible="false">UnFocus</animation>
                            <posx>0</posx>
                            <posy>0</posy>
                            <control type="image">
                                <visible>Control.HasFocus(402)</visible>
                                <posx>-40</posx>
                                <posy>{{ vscale(-40) }}</posy>
                                <width>389</width>
                                <height>{{ vscale(258) }}</height>
                                <texture border="42">script.plex/drop-shadow.png</texture>
                            </control>
                            <control type="group">
                                <posx>5</posx>
                                <posy>5</posy>
                                <control type="image">
                                    <posx>0</posx>
                                    <posy>0</posy>
                                    <width>299</width>
                                    <height>{{ vscale(168) }}</height>
                                    <texture>$INFO[ListItem.Property(thumb.fallback)]</texture>
                                    <aspectratio>scale</aspectratio>
                                </control>
                                <control type="image">
                                    <posx>0</posx>
                                    <posy>0</posy>
                                    <width>299</width>
                                    <height>{{ vscale(168) }}</height>
                                    <texture background="true">$INFO[ListItem.Thumb]</texture>
                                    <aspectratio>scale</aspectratio>
                                </control>
                                <control type="group">
                                    <control type="label">
                                        <scroll>Control.HasFocus(402)</scroll>
                                        <posx>0</posx>
                                        <posy>{{ vscale(175) }}</posy>
                                        <width>299</width>
                                        <height>{{ vscale(60) }}</height>
                                        <font>font12</font>
                                        <align>center</align>
                                        <textcolor>FFFFFFFF</textcolor>
                                        <label>$INFO[ListItem.Label]</label>
                                    </control>
                                    <control type="label">
                                        <scroll>Control.HasFocus(402)</scroll>
                                        <posx>0</posx>
                                        <posy>{{ vscale(210) }}</posy>
                                        <width>299</width>
                                        <height>{{ vscale(60) }}</height>
                                        <font>font12</font>
                                        <align>center</align>
                                        <textcolor>FFFFFFFF</textcolor>
                                        <label>$INFO[ListItem.Label2]</label>
                                    </control>
                                </control>
                            </control>
                            <control type="image">
                                <visible>Control.HasFocus(402)</visible>
                                <posx>0</posx>
                                <posy>0</posy>
                                <width>309</width>
                                <height>{{ vscale(178) }}</height>
                                <texture border="10">script.plex/home/selected.png</texture>
                            </control>
                        </control>
                    </control>
                </focusedlayout>
            </control>
        </control>
        <!-- EXTRAS -->

        <!-- RELATED -->
        <control type="group" id="503">
            <visible>Integer.IsGreater(Container(403).NumItems,0) + String.IsEmpty(Window.Property(drawing))</visible>
            <defaultcontrol>403</defaultcontrol>
            <width>1920</width>
            <height>{{ vscale(520) }}</height>
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
            <control type="list" id="403">
                <!-- posx=40, not 0 (width shrunk to match): see list 400's comment above for the full
                     rationale (sidebar rail clip-boundary clearance). -->
                <posx>40</posx>
                <posy>{{ vscale(16) }}</posy>
                <width>1880</width>
                <height>{{ vscale(520) }}</height>
                <onup>402</onup>
                <ondown>403</ondown>
                <!-- onleft: noop while the leftmost item is the left-pagination boundary marker, so
                     RelatedPaginator's boundaryHit check (onAction) fires and loads the previous page
                     instead of the rail stealing focus mid-pagination. Once truly at the first item (no
                     boundary marker), onleft falls through to the sidebar (9000) - same pattern as
                     Episodes' related row. -->
                <onleft condition="!String.IsEmpty(Container(403).ListItem.Property(left.boundary))">noop</onleft>
                <onleft>9000</onleft>
                <onright>noop</onright>
                <scrolltime>200</scrolltime>
                <orientation>horizontal</orientation>
                <preloaditems>4</preloaditems>
                <!-- ITEM LAYOUT ########################################## -->
                <itemlayout width="304">
                    <control type="group">
                        <posx>15</posx>
                        <posy>{{ vscale(72) }}</posy>
                        <control type="group">
                            <posx>5</posx>
                            <posy>5</posy>
                            <control type="image">
                                <posx>0</posx>
                                <posy>0</posy>
                                <width>244</width>
                                <height>{{ vscale(361) }}</height>
                                <texture>$INFO[ListItem.Property(thumb.fallback)]</texture>
                            </control>
                            <control type="image">
                                <posx>0</posx>
                                <posy>0</posy>
                                <width>244</width>
                                <height>{{ vscale(361) }}</height>
                                <texture background="true">$INFO[ListItem.Thumb]</texture>
                                <aspectratio>scale</aspectratio>
                            </control>
                            <control type="group">
                                <visible>!String.IsEmpty(ListItem.Property(progress))</visible>
                                <posx>0</posx>
                                <posy>{{ vscale(351) }}</posy>
                                <control type="image">
                                    <posx>0</posx>
                                    <posy>0</posy>
                                    <width>244</width>
                                    <height>{{ vscale(10) }}</height>
                                    <texture>script.plex/white-square.png</texture>
                                    <colordiffuse>C0000000</colordiffuse>
                                </control>
                                <control type="image">
                                    <posx>0</posx>
                                    <posy>1</posy>
                                    <width>244</width>
                                    <height>{{ vscale(8) }}</height>
                                    <texture>$INFO[ListItem.Property(progress)]</texture>
                                    <colordiffuse>FFCC7B19</colordiffuse>
                                </control>
                            </control>
                            {% include "includes/watched_indicator.xml.tpl" with xoff=244 & uw_size=48 & with_count=True & scale="medium" %}
                            <control type="label">
                                <scroll>false</scroll>
                                <posx>0</posx>
                                <posy>{{ vscale(369) }}</posy>
                                <width>244</width>
                                <height>{{ vscale(38) }}</height>
                                <font>font10</font>
                                <align>center</align>
                                <textcolor>FFFFFFFF</textcolor>
                                <label>$INFO[ListItem.Label]</label>
                            </control>
                            <control type="group">
                                <visible>!String.IsEmpty(ListItem.Property(is.boundary))</visible>
                                <control type="image">
                                    <posx>0</posx>
                                    <posy>0</posy>
                                    <width>244</width>
                                    <height>{{ vscale(361) }}</height>
                                    <texture colordiffuse="FF404040">script.plex/white-square.png</texture>
                                </control>
                                <control type="image">
                                    <visible>String.IsEmpty(ListItem.Property(is.updating)) + !String.IsEmpty(ListItem.Property(right.boundary))</visible>
                                    <posx>91.5</posx>
                                    <posy>{{ vscale(130.5) }}</posy>
                                    <width>61</width>
                                    <height>{{ vscale(100) }}</height>
                                    <texture colordiffuse="40000000">script.plex/indicators/chevron-white.png</texture>
                                </control>
                                <control type="image">
                                    <visible>String.IsEmpty(ListItem.Property(is.updating)) + !String.IsEmpty(ListItem.Property(left.boundary))</visible>
                                    <posx>91.5</posx>
                                    <posy>{{ vscale(130.5) }}</posy>
                                    <width>61</width>
                                    <height>{{ vscale(100) }}</height>
                                    <texture colordiffuse="40000000">script.plex/indicators/chevron-white-l.png</texture>
                                </control>
                                <control type="image">
                                    <visible>!String.IsEmpty(ListItem.Property(is.updating))</visible>
                                    <posx>58</posx>
                                    <posy>{{ vscale(116.5) }}</posy>
                                    <width>128</width>
                                    <height>{{ vscale(128) }}</height>
                                    <texture>script.plex/home/busy.gif</texture>
                                </control>
                            </control>
                        </control>
                    </control>
                </itemlayout>

                <!-- FOCUSED LAYOUT ####################################### -->
                <focusedlayout width="304">
                    <control type="group">
                        <posx>15</posx>
                        <posy>{{ vscale(72) }}</posy>
                        <control type="group">
                            <animation effect="zoom" start="100" end="110" time="100" center="127,{{ vscale(180.5) }}" reversible="false">Focus</animation>
                            <animation effect="zoom" start="110" end="100" time="100" center="127,{{ vscale(180.5) }}" reversible="false">UnFocus</animation>
                            <posx>0</posx>
                            <posy>0</posy>
                            <control type="image">
                                <visible>Control.HasFocus(403)</visible>
                                <posx>-40</posx>
                                <posy>{{ vscale(-40) }}</posy>
                                <width>324</width>
                                <height>{{ vscale(441) }}</height>
                                <texture border="42">script.plex/drop-shadow.png</texture>
                            </control>
                            <control type="group">
                                <posx>5</posx>
                                <posy>5</posy>
                                <control type="image">
                                    <posx>0</posx>
                                    <posy>0</posy>
                                    <width>244</width>
                                    <height>{{ vscale(361) }}</height>
                                    <texture>$INFO[ListItem.Property(thumb.fallback)]</texture>
                                </control>
                                <control type="image">
                                    <posx>0</posx>
                                    <posy>0</posy>
                                    <width>244</width>
                                    <height>{{ vscale(361) }}</height>
                                    <texture background="true">$INFO[ListItem.Thumb]</texture>
                                    <aspectratio>scale</aspectratio>
                                </control>
                                <control type="group">
                                    <visible>!String.IsEmpty(ListItem.Property(progress))</visible>
                                    <posx>0</posx>
                                    <posy>{{ vscale(351) }}</posy>
                                    <control type="image">
                                        <posx>0</posx>
                                        <posy>0</posy>
                                        <width>244</width>
                                        <height>{{ vscale(10) }}</height>
                                        <texture>script.plex/white-square.png</texture>
                                        <colordiffuse>C0000000</colordiffuse>
                                    </control>
                                    <control type="image">
                                        <posx>0</posx>
                                        <posy>1</posy>
                                        <width>244</width>
                                        <height>{{ vscale(8) }}</height>
                                        <texture>$INFO[ListItem.Property(progress)]</texture>
                                        <colordiffuse>FFCC7B19</colordiffuse>
                                    </control>
                                </control>
                                {% include "includes/watched_indicator.xml.tpl" with xoff=244 & uw_size=48 & with_count=True & scale="medium" %}
                                <control type="label">
                                    <scroll>Control.HasFocus(403)</scroll>
                                    <posx>0</posx>
                                    <posy>{{ vscale(369) }}</posy>
                                    <width>244</width>
                                    <height>{{ vscale(38) }}</height>
                                    <font>font10</font>
                                    <align>center</align>
                                    <textcolor>FFFFFFFF</textcolor>
                                    <label>$INFO[ListItem.Label]</label>
                                </control>
                            </control>
                            <control type="image">
                                <visible>Control.HasFocus(403)</visible>
                                <posx>0</posx>
                                <posy>0</posy>
                                <width>254</width>
                                <height>{{ vscale(371) }}</height>
                                <texture border="10">script.plex/home/selected.png</texture>
                            </control>
                            <control type="group">
                                <visible>!String.IsEmpty(ListItem.Property(is.boundary))</visible>
                                <control type="image">
                                    <posx>0</posx>
                                    <posy>0</posy>
                                    <width>244</width>
                                    <height>{{ vscale(361) }}</height>
                                    <texture colordiffuse="FF404040">script.plex/white-square.png</texture>
                                </control>
                                <control type="image">
                                    <visible>String.IsEmpty(ListItem.Property(is.updating)) + !String.IsEmpty(ListItem.Property(right.boundary))</visible>
                                    <posx>91.5</posx>
                                    <posy>{{ vscale(130.5) }}</posy>
                                    <width>61</width>
                                    <height>{{ vscale(100) }}</height>
                                    <texture colordiffuse="40000000">script.plex/indicators/chevron-white.png</texture>
                                </control>
                                <control type="image">
                                    <visible>String.IsEmpty(ListItem.Property(is.updating)) + !String.IsEmpty(ListItem.Property(left.boundary))</visible>
                                    <posx>91.5</posx>
                                    <posy>{{ vscale(130.5) }}</posy>
                                    <width>61</width>
                                    <height>{{ vscale(100) }}</height>
                                    <texture colordiffuse="40000000">script.plex/indicators/chevron-white-l.png</texture>
                                </control>
                                <control type="image">
                                    <visible>!String.IsEmpty(ListItem.Property(is.updating))</visible>
                                    <posx>58</posx>
                                    <posy>{{ vscale(116.5) }}</posy>
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
        <!-- RELATED -->

    </control>
</control>
{% endblock content %}