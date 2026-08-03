{% extends "default.xml.tpl" %}
{% block content %}
<control type="group" id="50">
    <animation effect="slide" end="0,{{ vscale(-125) }}" time="200" tween="quadratic" easing="out" condition="!String.IsEmpty(Window.Property(on.extras))">Conditional</animation>

    <animation type="Conditional" condition="Integer.IsGreater(Window.Property(hub.focus),0) + Control.IsVisible(500)" reversible="true">
        <effect type="slide" end="0,{{ vscale(-500) }}" time="200" tween="quadratic" easing="out"/>
    </animation>

    <animation type="Conditional" condition="Integer.IsGreater(Window.Property(hub.focus),2) + Control.IsVisible(502)" reversible="true">
        <effect type="slide" end="0,{{ vscale(-500) }}" time="200" tween="quadratic" easing="out"/>
    </animation>

    <animation type="Conditional" condition="Integer.IsGreater(Window.Property(hub.focus),3) + Control.IsVisible(503)" reversible="true">
        <effect type="slide" end="0,{{ vscale(-500) }}" time="200" tween="quadratic" easing="out"/>
    </animation>

    <ondown condition="!String.IsEmpty(Window.Property(disable_playback))">400</ondown>

    <posx>0</posx>
    <posy>{{ vscale(155) }}</posy>
    <!--<defaultcontrol>101</defaultcontrol>-->

    {% block buttons %}
        {% if theme.episodes.use_button_bg %}
            <control type="image">
                <visible>String.IsEmpty(Window.Property(disable_playback))</visible>
                <posx>60</posx>
                <posy>{{ vscale(369) }}</posy>
                <width>657</width>
                <height>{{ vscale(104) }}</height>
                <texture>script.plex/white-square.png</texture>
                <colordiffuse>{{ theme.episodes.button_bg_color|default(66000000) }}</colordiffuse>
            </control>
        {% endif %}
        <control type="grouplist" id="300">
            <visible allowhiddenfocus="!String.IsEmpty(Container(400).ListItem.Property(media.multiple))">String.IsEmpty(Container(400).ListItem.Property(media.multiple)) + !String.IsEmpty(Window.Property(initialized)) + String.IsEmpty(Window.Property(disable_playback))</visible>
            <defaultcontrol always="true">301</defaultcontrol>
            <posx>30</posx>
            <posy>{{ theme.episodes.buttongroup.posy|vscale }}</posy>
            <width>717</width>
            <height>{{ vscale(200) }}</height>
            <onup condition="Control.IsVisible(205)">205</onup>
            <onup>200</onup>
            <ondown>400</ondown>
            <align>center</align>
            <itemgap>{{ theme.episodes.buttongroup.itemgap }}</itemgap>
            <orientation>horizontal</orientation>
            <scrolltime tween="quadratic" easing="out">200</scrolltime>
            <usecontrolcoords>true</usecontrolcoords>

            {% with attr = theme.episodes.buttons & template = "includes/themed_button.xml.tpl" %}
                {% include template with name="info" & id=304 %}
                {% include template with name="play" & id=301 & onleft=304 & onright=305 &
                    enable="!String.IsEmpty(Window.Property(current_item.loaded))" & visible="!String.IsEmpty(Window.Property(current_item.loaded))" &
                    allowhiddenfocus=True
                %}
                {% include template with name="play" & id=306 & onleft=304 & onright=305 &
                                    visible="String.IsEmpty(Window.Property(current_item.loaded))"
                %}
                {% include template with name="settings" & id=305 %}
                {% include template with name="more" & id=303 %}
                {% include template with name="shuffle" & id=302 %}
            {% endwith %}
        </control>
        <control type="grouplist" id="1300">
            <visible>!String.IsEmpty(Container(400).ListItem.Property(media.multiple)) + !String.IsEmpty(Window.Property(initialized)) + String.IsEmpty(Window.Property(disable_playback))</visible>
            <defaultcontrol always="true">1301</defaultcontrol>
            <posx>30</posx>
            <posy>{{ theme.episodes.buttongroup_1300.posy|vscale }}</posy>
            <width>717</width>
            <height>{{ vscale(200) }}</height>
            <onup condition="Control.IsVisible(205)">205</onup>
            <onup>200</onup>
            <ondown>400</ondown>
            <align>center</align>
            <itemgap>{{ theme.episodes.buttongroup_1300.itemgap }}</itemgap>
            <orientation>horizontal</orientation>
            <scrolltime tween="quadratic" easing="out">200</scrolltime>
            <usecontrolcoords>true</usecontrolcoords>

            {% with attr = theme.episodes.buttons_1300 & template = "includes/themed_button.xml.tpl" %}
                {% include template with name="info" & id=1304 %}
                {% include template with name="play" & id=1301 & onleft=1304 & onright=1305 &
                    enable="!String.IsEmpty(Window.Property(current_item.loaded))" & visible="!String.IsEmpty(Window.Property(current_item.loaded))" &
                    allowhiddenfocus=True
                %}
                {% include template with name="play" & id=1306 & onleft=1304 & onright=1307 &
                                    visible="String.IsEmpty(Window.Property(current_item.loaded))"
                %}
                {% include template with name="media" & id=1307 %}
                {% include template with name="settings" & id=1305 %}
                {% include template with name="more" & id=1303 %}
                {% include template with name="shuffle" & id=1302 %}
            {% endwith %}

        </control>
    {% endblock %}

    <control type="group">
        <posx>0</posx>
        <posy>0</posy>
        <width>1920</width>
        <height>{{ vscale(600) }}</height>
        <control type="group">
            <control type="image">
                <visible>false</visible>
                <posx>60</posx>
                <posy>0</posy>
                <width>656</width>
                <height>{{ vscale(369) }}</height>
                <texture background="true">script.plex/home/background-fallback_black.png</texture>
                <aspectratio>scale</aspectratio>
            </control>
            <control type="image">
                <posx>60</posx>
                <posy>0</posy>
                <width>656</width>
                <height>{{ vscale(369) }}</height>
                <texture background="true" fallback="script.plex/thumb_fallbacks/show.png">$INFO[Container(400).ListItem.Thumb]</texture>
                <aspectratio>scale</aspectratio>
            </control>
            {% include "includes/watched_indicator.xml.tpl" with itemref="Container(400).ListItem" & xoff=656+60 & uw_size=35 & scale="large" %}
        </control>

        <!-- Sits one row above the meta row (which starts at 160), under whatever fills the top slot - the
             clear logo, or the show's title. Height capped at 46 so it doesn't clip into the meta row below -
             a grouplist clips its children and owns that region. 1084 is the column's right margin:
             776+1084 = 1860. -->
        <control type="grouplist">
            <posx>776</posx>
            <posy>{{ vscale(114) }}</posy>
            <width>1084</width>
            <height>{{ vscale(46) }}</height>
            <align>left</align>
            <itemgap>0</itemgap>
            <orientation>horizontal</orientation>
            <usecontrolcoords>true</usecontrolcoords>
            <!-- capped so a long title can't outgrow the group and get clipped instead of scrolling: 950
                 leaves the same ~134px margin for the unavailable button that follows as before, now that
                 the SxxEyy/date prefix that used to precede the title is gone -->
            <control type="label">
                <width max="950">auto</width>
                <height>{{ vscale(46) }}</height>
                <font>font13</font>
                <align>left</align>
                <aligny>top</aligny>
                <textcolor>FFFFFFFF</textcolor>
                <scroll>true</scroll>
                <scrollspeed>35</scrollspeed>
                <label>[B]$INFO[Container(400).ListItem.Property(title)][/B]</label>
            </control>
            <!-- Sits in the heading row rather than its own; that freed up vertical space for the logo above -->
            <control type="button">
                <visible>!String.IsEmpty(Container(400).ListItem.Property(unavailable))</visible>
                <posx>10</posx>
                <posy>6</posy>
                <width>auto</width>
                <height>{{ vscale(34) }}</height>
                <font>font12</font>
                <align>center</align>
                <aligny>center</aligny>
                <focusedcolor>FFFFFFFF</focusedcolor>
                <textcolor>FFFFFFFF</textcolor>
                <textoffsetx>15</textoffsetx>
                <texturefocus colordiffuse="FFAC3223" border="12">script.plex/white-square-rounded.png</texturefocus>
                <texturenofocus colordiffuse="FFAC3223" border="12">script.plex/white-square-rounded.png</texturenofocus>
                <label>$ADDON[script.plexmod 32312]</label>
            </control>
        </control>
        <control type="image">
            <visible>!String.IsEmpty(Container(400).ListItem.Property(rating.stars))</visible>
            <posx>1726</posx>
            <posy>6</posy>
            <width>134</width>
            <height>{{ vscale(22) }}</height>
            <texture>script.plex/stars/$INFO[Container(400).ListItem.Property(rating.stars)].png</texture>
        </control>
        <!-- Fills the same top slot the clear logo would, on the same box, so both variants put the show's
             identity in one place and the episode line at 114 under it. Bottom-aligned to land its baseline
             where the logo's bottom edge is. -->
        <control type="label">
            <visible>String.IsEmpty(Window.Property(clear.logo))</visible>
            <posx>776</posx>
            <posy>0</posy>
            <!-- 714, not the heading's 950: this box overlaps the ratings' y range, and 776+714 stops short
                 of them at 1560. The heading below clears them and can run wider. -->
            <width>714</width>
            <height>{{ vscale(68) }}</height>
            <!-- stands in for the logo and has its whole 100px box to fill, so it takes the largest face
                 the templates use; font32_title is the step down if this crowds the box -->
            <font>font45</font>
            <align>left</align>
            <aligny>bottom</aligny>
            <scroll>true</scroll>
            <scrollspeed>25</scrollspeed>
            <textcolor>FFFFFFFF</textcolor>
            <label>$INFO[Container(400).ListItem.Property(show.title)]</label>
        </control>
        <!-- Takes the watched/unwatched indicator's slot, flush to the thumb's top-right corner and using its
             texture, which is free exactly when this is showing: isWatched is viewCount>0 OR viewOffset>0, so
             an in-progress episode gets no unwatched dot, and isFullyWatched needs viewOffset empty, so it
             gets no checkmark either. Right-aligned via a grouplist because the pill's width follows its text;
             its right edge lands on xoff (656+60), the same anchor watched_indicator uses. Unconditional -
             keeping it out of the heading is what lets that row be a single label with no width juggling. -->
        <control type="grouplist">
            <visible>!String.IsEmpty(Container(400).ListItem.Property(remainingTime))</visible>
            <posx>416</posx>
            <posy>0</posy>
            <width>300</width>
            <height>{{ vscale(35) }}</height>
            <align>right</align>
            <itemgap>0</itemgap>
            <orientation>horizontal</orientation>
            <control type="button">
                <width>auto</width>
                <height>{{ vscale(35) }}</height>
                <font>font12</font>
                <align>center</align>
                <aligny>center</aligny>
                <focusedcolor>FFE5A00D</focusedcolor>
                <textcolor>FFE5A00D</textcolor>
                <textoffsetx>15</textoffsetx>
                <!-- The tight-radius twin of the _w texture the indicator uses (4px curve against its 12), and
                     9-sliced at exactly that: without a border the 100x100 source stretches to the pill's
                     width and the round flattens into an ellipse -->
                <texturefocus colordiffuse="CC000000" border="4">script.plex/white-square-bl-rounded.png</texturefocus>
                <texturenofocus colordiffuse="CC000000" border="4">script.plex/white-square-bl-rounded.png</texturenofocus>
                <label>$INFO[Container(400).ListItem.Property(remainingTime)]</label>
            </control>
        </control>

        <!-- Sized to match pre_play's poster-shown clear logo box (873x106, itself scaled off this box's old
             560x68 by the 106/68 ratio) rather than the movie/show screens' shorter 0..68 box - the logo now
             renders larger at the cost of no longer sharing their exact slot. Width trimmed from pre_play's
             873 to 784 (776+784=1560) so it can't run into the ratings badge, which starts at 1560 here vs
             1426 there. Bottom-aligned, so the taller box draws the logo lower; heading (114) still clears it
             with an 8px gap. -->
        <control type="image">
            <visible>!String.IsEmpty(Window.Property(clear.logo))</visible>
            <posx>776</posx>
            <posy>0</posy>
            <width>784</width>
            <height>{{ vscale(106) }}</height>
            <aspectratio align="left" aligny="bottom">keep</aspectratio>
            <texture background="true">$INFO[Window.Property(clear.logo)]</texture>
        </control>

        <control type="grouplist">
            <visible>!String.IsEmpty(Container(400).ListItem.Property(rating)) | !String.IsEmpty(Container(400).ListItem.Property(rating2))</visible>
            <posx>1560</posx>
            <posy>{{ vscale(50) }}</posy>
            <width>300</width>
            <height>{{ vscale(32) }}</height>
            <align>right</align>
            <itemgap>15</itemgap>
            <orientation>horizontal</orientation>
            <usecontrolcoords>true</usecontrolcoords>
            <control type="image">
                <visible>!String.IsEmpty(Container(400).ListItem.Property(rating))</visible>
                <posy>2</posy>
                <width>63</width>
                <height>{{ vscale(30) }}</height>
                <texture fallback="script.plex/ratings/other/image.rating.png">$INFO[Container(400).ListItem.Property(rating.image)]</texture>
                <aspectratio align="right">keep</aspectratio>
            </control>
            <control type="label">
                <visible>!String.IsEmpty(Container(400).ListItem.Property(rating))</visible>
                <width>auto</width>
                <height>{{ vscale(30) }}</height>
                <font>font12</font>
                <align>left</align>
                <textcolor>FFFFFFFF</textcolor>
                <label>$INFO[Container(400).ListItem.Property(rating)]</label>
            </control>
            <control type="image">
                <visible>!String.IsEmpty(Container(400).ListItem.Property(rating2))</visible>
                <posy>2</posy>
                <width>40</width>
                <height>{{ vscale(30) }}</height>
                <texture fallback="script.plex/ratings/other/image.rating.png">$INFO[Container(400).ListItem.Property(rating2.image)]</texture>
                <aspectratio align="right">keep</aspectratio>
            </control>
            <control type="label">
                <visible>!String.IsEmpty(Container(400).ListItem.Property(rating2))</visible>
                <width>auto</width>
                <height>{{ vscale(30) }}</height>
                <font>font12</font>
                <align>left</align>
                <textcolor>FFFFFFFF</textcolor>
                <label>$INFO[Container(400).ListItem.Property(rating2)]</label>
            </control>
        </control>

        <control type="grouplist">
            <posx>776</posx>
            <posy>{{ vscale(160) }}</posy>
            <width>1084</width>
            <height>{{ vscale(34) }}</height>
            <align>left</align>
            <itemgap>0</itemgap>
            <orientation>horizontal</orientation>
            <usecontrolcoords>true</usecontrolcoords>
            <control type="label">
                <width max="1084">auto</width>
                <height>{{ vscale(34) }}</height>
                <font>font10</font>
                <align>left</align>
                <scroll>true</scroll>
                <scrollspeed>25</scrollspeed>
                <textcolor>FFFFFFFF</textcolor>
                <label>$INFO[Container(400).ListItem.Property(duration)]$INFO[Container(400).ListItem.Property(genre), &#8226; ]$INFO[Container(400).ListItem.Property(date), &#8226; ]$INFO[Container(400).ListItem.Property(content.rating), &#8226; ]</label>
            </control>
        </control>

        <control type="textbox">
            <posx>776</posx>
            <posy>{{ vscale(200) }}</posy>
            <width>1084</width>
            <height>{{ vscale(172) }}</height>
            <font>font12</font>
            <align>left</align>
            <textcolor>FFFFFFFF</textcolor>
            <scrolltime>200</scrolltime>
            <autoscroll delay="2000" time="2000" repeat="10000">!Control.HasFocus(13)</autoscroll>
            <label>$INFO[Container(400).ListItem.Property(summary)]</label>
        </control>

        <!-- Video/audio/subtitles, formatted like pre_play's streams block: a vertical grouplist of
             label-per-line rows (grey uppercase tag + tab + value) instead of the pill buttons used above -->
        <control type="grouplist">
            <posx>776</posx>
            <posy>{{ vscale(378) }}</posy>
            <width>1084</width>
            <height>{{ vscale(90) }}</height>
            <align>left</align>
            <orientation>vertical</orientation>
            <usecontrolcoords>true</usecontrolcoords>
            <control type="label">
                <visible>!String.IsEmpty(Container(400).ListItem.Property(video.res))</visible>
                <width>auto</width>
                <height>{{ vscale(30) }}</height>
                <font>font10</font>
                <align>left</align>
                <aligny>top</aligny>
                <textcolor>FFFFFFFF</textcolor>
                <label>[COLOR grey][UPPERCASE]$ADDON[script.plexmod 32053][/UPPERCASE][/COLOR][TABS]2[/TABS]$INFO[Container(400).ListItem.Property(video.res)]$INFO[Container(400).ListItem.Property(video.rendering), &#8226; ]$INFO[Container(400).ListItem.Property(video.codec), &#8226; ]</label>
            </control>
            <control type="label">
                <visible>!String.IsEmpty(Container(400).ListItem.Property(audio))</visible>
                <width>auto</width>
                <height>{{ vscale(30) }}</height>
                <font>font10</font>
                <align>left</align>
                <aligny>top</aligny>
                <textcolor>FFFFFFFF</textcolor>
                <label>[COLOR grey][UPPERCASE]$ADDON[script.plexmod 32048][/UPPERCASE][/COLOR][TABS]2[/TABS]$INFO[Container(400).ListItem.Property(audio)]</label>
            </control>
            <control type="label">
                <visible>!String.IsEmpty(Container(400).ListItem.Property(subtitles))</visible>
                <width>auto</width>
                <height>{{ vscale(30) }}</height>
                <font>font10</font>
                <align>left</align>
                <aligny>top</aligny>
                <textcolor>FFFFFFFF</textcolor>
                <label>[COLOR grey][UPPERCASE]$ADDON[script.plexmod 32396][/UPPERCASE][/COLOR][TABS]2[/TABS]$INFO[Container(400).ListItem.Property(subtitles)]</label>
            </control>
        </control>

    </control>

    <!-- EPISODES -->
    <control type="grouplist" id="60">
        <visible>!String.IsEmpty(Window.Property(initialized))</visible>
        <posx>0</posx>
        <posy>{{ vscale(510) }}</posy>
        <width>1920</width>
        <height>{{ vscale(1800) }}</height>

        <onup condition="Control.IsVisible(300)">300</onup>
        <onup condition="Control.IsVisible(1300)">1300</onup>
        <onup condition="!Control.IsVisible(1300) + !Control.IsVisible(300)">200</onup>
        <itemgap>0</itemgap>

        <!-- EPISODES -->
        <!-- Fixed-center carousel: 500 is a full-width (1920) clipping mask (grouplist clips its children,
             a plain group doesn't - see the grouplist-60 comment above). Inside it, list 400 is oversized to
             2375 (5 item-cells of 475) and shifted -227.5, so the mask's edges fall mid-cell on the outer
             items instead of on a cell boundary - that's what turns the leftover width into a symmetric
             247.5px peek on both sides (edge-to-edge across the full row) rather than one lopsided sliver.
             focusposition=2 pins the true center cell (3rd of 5) as the fixed focus; items scroll under it.
             500's own onup/ondown/onleft/onright are required here (duplicated onto the child fixedlist too):
             a grouplist wrapper doesn't automatically forward its child's direction rules for keys outside its
             own orientation axis - same reason the buttongroup grouplists (300/1300) above define their own
             onup/ondown rather than relying on their buttons'. -->
        <control type="grouplist" id="500">
            <visible>Integer.IsGreater(Container(400).NumItems,0) + String.IsEmpty(Window.Property(drawing))</visible>
            <height>{{ vscale(360) }}</height>
            <width>1920</width>
            <usecontrolcoords>true</usecontrolcoords>
            <orientation>horizontal</orientation>
            <itemgap>0</itemgap>
            <onup condition="Control.IsVisible(300)">300</onup>
            <onup condition="Control.IsVisible(1300)">1300</onup>
            <ondown>402</ondown>
            <onleft>noop</onleft>
            <onright>noop</onright>
            <control type="fixedlist" id="400">
                <posx>-227.5</posx>
                <posy>{{ vscale(18) }}</posy>
                <width>2375</width>
                <height>{{ vscale(360) }}</height>
                <focusposition>2</focusposition>
                <onup condition="Control.IsVisible(300)">300</onup>
                <onup condition="Control.IsVisible(1300)">1300</onup>
                <ondown>402</ondown>
                <onleft>noop</onleft>
                <onright>noop</onright>
                <scrolltime>200</scrolltime>
                <orientation>horizontal</orientation>
                <preloaditems>5</preloaditems>
                <!-- ITEM LAYOUT ########################################## -->
                <itemlayout width="475">
                    <control type="group">
                        <posx>25</posx>
                        <posy>{{ vscale(-1) }}</posy>
                        <control type="group">
                            <posx>5</posx>
                            <posy>5</posy>
                            <control type="image">
                                <posx>0</posx>
                                <posy>0</posy>
                                <width>445</width>
                                <height>{{ vscale(250) }}</height>
                                <texture>$INFO[ListItem.Property(thumb.fallback)]</texture>
                                <aspectratio>scale</aspectratio>
                            </control>
                            <control type="image">
                                <posx>0</posx>
                                <posy>0</posy>
                                <width>445</width>
                                <height>{{ vscale(250) }}</height>
                                <texture background="true">$INFO[ListItem.Thumb]</texture>
                                <aspectratio>scale</aspectratio>
                            </control>
                            <!-- Dims every non-focused thumbnail so the fixed-center item pops; itemlayout only
                                 renders for items that aren't focused, so no HasFocus condition is needed here.
                                 Drawn before the badges/label below so they stay at full brightness on top. -->
                            <control type="image">
                                <posx>0</posx>
                                <posy>0</posy>
                                <width>445</width>
                                <height>{{ vscale(250) }}</height>
                                <texture>script.plex/white-square.png</texture>
                                <colordiffuse>E6000000</colordiffuse>
                            </control>
                            <control type="group">
                                <visible>!String.IsEmpty(ListItem.Property(progress))</visible>
                                <posx>0</posx>
                                <posy>{{ vscale(240) }}</posy>
                                <control type="image">
                                    <posx>0</posx>
                                    <posy>0</posy>
                                    <width>445</width>
                                    <height>{{ vscale(10) }}</height>
                                    <texture>script.plex/white-square.png</texture>
                                    <colordiffuse>C0000000</colordiffuse>
                                </control>
                                <control type="image">
                                    <posx>0</posx>
                                    <posy>1</posy>
                                    <width>445</width>
                                    <height>{{ vscale(8) }}</height>
                                    <texture>$INFO[ListItem.Property(progress)]</texture>
                                    <colordiffuse>FFCC7B19</colordiffuse>
                                </control>
                            </control>
                            <control type="group">
                                <visible>!String.IsEmpty(ListItem.Property(episode.number))</visible>
                                <posx>405</posx>
                                <posy>0</posy>
                                <control type="image">
                                    <posx>0</posx>
                                    <posy>0</posy>
                                    <width>40</width>
                                    <height>{{ vscale(32) }}</height>
                                    <texture>script.plex/white-square.png</texture>
                                    <colordiffuse>{{ indicators.watched_bg|default("CC000000") }}</colordiffuse>
                                </control>
                                <control type="label">{# rendered big then zoomed down so it never truncates/ellipsizes at the badge's actual width #}
                                    <animation effect="zoom" start="33" end="33" time="0" reversible="false" center="auto" condition="true">Conditional</animation>
                                    <posx>-20</posx>
                                    <posy>{{ vscale(-8) }}</posy>
                                    <width>80</width>
                                    <height>{{ vscale(48) }}</height>
                                    <font>font32_title</font>
                                    <align>center</align>
                                    <aligny>center</aligny>
                                    <textcolor>{{ indicators.textcolor|default("FFFFFFFF") }}</textcolor>
                                    <label>$INFO[ListItem.Property(episode.number)]</label>
                                </control>
                            </control>
                            {% include "includes/watched_indicator.xml.tpl" with xoff=405 & uw_size=35 & wbg_w=40 %}

                            <control type="label">
                                <scroll>false</scroll>
                                <posx>0</posx>
                                <posy>{{ vscale(257) }}</posy>
                                <width>445</width>
                                <height>{{ vscale(60) }}</height>
                                <font>font10</font>
                                <align>center</align>
                                <textcolor>AAFFFFFF</textcolor>
                                <label>$INFO[ListItem.Label]</label>
                            </control>
                            <control type="group">
                                <visible>!String.IsEmpty(ListItem.Property(is.boundary))</visible>
                                <control type="image">
                                    <posx>0</posx>
                                    <posy>0</posy>
                                    <width>445</width>
                                    <height>{{ vscale(250) }}</height>
                                    <texture colordiffuse="FF404040">script.plex/white-square.png</texture>
                                </control>
                                <control type="image">
                                    <visible>String.IsEmpty(ListItem.Property(is.updating)) + !String.IsEmpty(ListItem.Property(right.boundary))</visible>
                                    <posx>192</posx>
                                    <posy>{{ vscale(75) }}</posy>
                                    <width>61</width>
                                    <height>{{ vscale(100) }}</height>
                                    <texture colordiffuse="40000000">script.plex/indicators/chevron-white.png</texture>
                                </control>
                                <control type="image">
                                    <visible>String.IsEmpty(ListItem.Property(is.updating)) + !String.IsEmpty(ListItem.Property(left.boundary))</visible>
                                    <posx>192</posx>
                                    <posy>{{ vscale(75) }}</posy>
                                    <width>61</width>
                                    <height>{{ vscale(100) }}</height>
                                    <texture colordiffuse="40000000">script.plex/indicators/chevron-white-l.png</texture>
                                </control>
                                <control type="image">
                                    <visible>!String.IsEmpty(ListItem.Property(is.updating))</visible>
                                    <posx>158.5</posx>
                                    <posy>{{ vscale(61) }}</posy>
                                    <width>128</width>
                                    <height>{{ vscale(128) }}</height>
                                    <texture>script.plex/home/busy.gif</texture>
                                </control>
                            </control>
                        </control>
                    </control>
                </itemlayout>

                <!-- FOCUSED LAYOUT ####################################### -->
                <focusedlayout width="475">
                    <control type="group">
                        <posx>25</posx>
                        <posy>{{ vscale(-1) }}</posy>
                        <control type="group">
                            <animation effect="zoom" start="100" end="110" time="100" center="227.5,{{ vscale(130) }}" reversible="false">Focus</animation>
                            <animation effect="zoom" start="110" end="100" time="100" center="227.5,{{ vscale(130) }}" reversible="false">UnFocus</animation>
                            <posx>0</posx>
                            <posy>0</posy>
                            <control type="image">
                                <visible>Control.HasFocus(400)</visible>
                                <posx>-40</posx>
                                <posy>{{ vscale(-40) }}</posy>
                                <width>535</width>
                                <height>{{ vscale(340) }}</height>
                                <texture border="42">script.plex/drop-shadow.png</texture>
                            </control>
                            <control type="group">
                                <posx>5</posx>
                                <posy>5</posy>
                                <control type="image">
                                    <posx>0</posx>
                                    <posy>0</posy>
                                    <width>445</width>
                                    <height>{{ vscale(250) }}</height>
                                    <texture>$INFO[ListItem.Property(thumb.fallback)]</texture>
                                    <aspectratio>scale</aspectratio>
                                </control>
                                <control type="image">
                                    <posx>0</posx>
                                    <posy>0</posy>
                                    <width>445</width>
                                    <height>{{ vscale(250) }}</height>
                                    <texture background="true">$INFO[ListItem.Thumb]</texture>
                                    <aspectratio>scale</aspectratio>
                                </control>
                                <control type="group">
                                    <visible>!String.IsEmpty(ListItem.Property(progress))</visible>
                                    <posx>0</posx>
                                    <posy>{{ vscale(240) }}</posy>
                                    <control type="image">
                                        <posx>0</posx>
                                        <posy>0</posy>
                                        <width>445</width>
                                        <height>{{ vscale(10) }}</height>
                                        <texture>script.plex/white-square.png</texture>
                                        <colordiffuse>C0000000</colordiffuse>
                                    </control>
                                    <control type="image">
                                        <posx>0</posx>
                                        <posy>1</posy>
                                        <width>445</width>
                                        <height>{{ vscale(8) }}</height>
                                        <texture>$INFO[ListItem.Property(progress)]</texture>
                                        <colordiffuse>FFCC7B19</colordiffuse>
                                    </control>
                                </control>
                                <control type="group">
                                    <visible>!String.IsEmpty(ListItem.Property(episode.number))</visible>
                                    <posx>405</posx>
                                    <posy>0</posy>
                                    <control type="image">
                                        <posx>0</posx>
                                        <posy>0</posy>
                                        <width>40</width>
                                        <height>{{ vscale(32) }}</height>
                                        <texture>script.plex/white-square.png</texture>
                                        <colordiffuse>{{ indicators.watched_bg|default("CC000000") }}</colordiffuse>
                                    </control>
                                    <control type="label">{# rendered big then zoomed down so it never truncates/ellipsizes at the badge's actual width #}
                                        <animation effect="zoom" start="33" end="33" time="0" reversible="false" center="auto" condition="true">Conditional</animation>
                                        <posx>-20</posx>
                                        <posy>{{ vscale(-8) }}</posy>
                                        <width>80</width>
                                        <height>{{ vscale(48) }}</height>
                                        <font>font32_title</font>
                                        <align>center</align>
                                        <aligny>center</aligny>
                                        <textcolor>{{ indicators.textcolor|default("FFFFFFFF") }}</textcolor>
                                        <label>$INFO[ListItem.Property(episode.number)]</label>
                                    </control>
                                </control>
                                {% include "includes/watched_indicator.xml.tpl" with xoff=405 & uw_size=35 & wbg_w=40 %}

                                <control type="group">
                                    <visible>Control.HasFocus(400)</visible>
                                    <control type="label">
                                        <scroll>true</scroll>
                                        <posx>0</posx>
                                        <posy>{{ vscale(257) }}</posy>
                                        <width>445</width>
                                        <height>{{ vscale(60) }}</height>
                                        <font>font10</font>
                                        <align>center</align>
                                        <textcolor>AAFFFFFF</textcolor>
                                        <label>$INFO[ListItem.Label]</label>
                                    </control>
                                </control>
                                <control type="group">
                                    <visible>!Control.HasFocus(400)</visible>
                                    <control type="label">
                                        <scroll>false</scroll>
                                        <posx>0</posx>
                                        <posy>{{ vscale(257) }}</posy>
                                        <width>445</width>
                                        <height>{{ vscale(60) }}</height>
                                        <font>font10</font>
                                        <align>center</align>
                                        <textcolor>FFCC7B19</textcolor>
                                        <label>$INFO[ListItem.Label]</label>
                                    </control>
                                </control>
                                <control type="group">
                                    <visible>!String.IsEmpty(ListItem.Property(is.boundary))</visible>
                                    <control type="image">
                                        <posx>0</posx>
                                        <posy>0</posy>
                                        <width>445</width>
                                        <height>{{ vscale(250) }}</height>
                                        <texture colordiffuse="FF404040">script.plex/white-square.png</texture>
                                    </control>
                                    <control type="image">
                                        <visible>String.IsEmpty(ListItem.Property(is.updating)) + !String.IsEmpty(ListItem.Property(right.boundary))</visible>
                                        <posx>192</posx>
                                        <posy>{{ vscale(75) }}</posy>
                                        <width>61</width>
                                        <height>{{ vscale(100) }}</height>
                                        <texture colordiffuse="40000000">script.plex/indicators/chevron-white.png</texture>
                                    </control>
                                    <control type="image">
                                        <visible>String.IsEmpty(ListItem.Property(is.updating)) + !String.IsEmpty(ListItem.Property(left.boundary))</visible>
                                        <posx>192</posx>
                                        <posy>{{ vscale(75) }}</posy>
                                        <width>61</width>
                                        <height>{{ vscale(100) }}</height>
                                        <texture colordiffuse="40000000">script.plex/indicators/chevron-white-l.png</texture>
                                    </control>
                                    <control type="image">
                                        <visible>!String.IsEmpty(ListItem.Property(is.updating))</visible>
                                        <posx>158.5</posx>
                                        <posy>{{ vscale(61) }}</posy>
                                        <width>128</width>
                                        <height>{{ vscale(128) }}</height>
                                        <texture>script.plex/home/busy.gif</texture>
                                    </control>
                                </control>
                            </control>
                            <control type="image">
                                <visible>Control.HasFocus(400)</visible>
                                <posx>0</posx>
                                <posy>0</posy>
                                <width>455</width>
                                <height>{{ vscale(260) }}</height>
                                <texture border="10">script.plex/home/selected.png</texture>
                            </control>
                        </control>
                    </control>
                </focusedlayout>
            </control>
        </control>
        <!-- EPISODES -->

        <!-- ROLES -->
        <control type="group" id="502">
            <visible>Integer.IsGreater(Container(402).NumItems,0) + String.IsEmpty(Window.Property(drawing))</visible>
            <defaultcontrol>402</defaultcontrol>
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
            <control type="list" id="402">
                <posx>0</posx>
                <posy>0</posy>
                <width>1920</width>
                <height>{{ vscale(400) }}</height>
                <onup>400</onup>
                <ondown>403</ondown>
                <scrolltime>200</scrolltime>
                <orientation>horizontal</orientation>
                <preloaditems>4</preloaditems>
                <!-- ITEM LAYOUT ########################################## -->
                <itemlayout width="304">
                    <control type="group">
                        <posx>55</posx>
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
                        <posx>55</posx>
                        <posy>{{ vscale(61) }}</posy>
                        <control type="group">
                            <animation effect="zoom" start="100" end="110" time="100" center="127,{{ vscale(127) }}" reversible="false">Focus</animation>
                            <animation effect="zoom" start="110" end="100" time="100" center="127,{{ vscale(127) }}" reversible="false">UnFocus</animation>
                            <posx>0</posx>
                            <posy>0</posy>
                            <control type="image">
                                <visible>Control.HasFocus(402)</visible>
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
                                        <scroll>Control.HasFocus(402)</scroll>
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
                                        <scroll>Control.HasFocus(402)</scroll>
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
                                <visible>Control.HasFocus(402)</visible>
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
        <control type="group" id="503">
            <visible>Integer.IsGreater(Container(403).NumItems,0) + String.IsEmpty(Window.Property(drawing))</visible>
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
                <textcolor>AAFFFFFF</textcolor>
                <label>[UPPERCASE]$INFO[Window.Property(extras.header)][/UPPERCASE]</label>
            </control>
            <control type="list" id="403">
                <posx>0</posx>
                <posy>{{ vscale(18) }}</posy>
                <width>1920</width>
                <height>{{ vscale(430) }}</height>
                <onup>402</onup>
                <ondown>404</ondown>
                <scrolltime>200</scrolltime>
                <orientation>horizontal</orientation>
                <preloaditems>4</preloaditems>
                <!-- ITEM LAYOUT ########################################## -->
                <itemlayout width="359">
                    <control type="group">
                        <posx>55</posx>
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
                                <font>font10</font>
                                <align>center</align>
                                <textcolor>AAFFFFFF</textcolor>
                                <label>$INFO[ListItem.Label]</label>
                            </control>
                            <control type="label">
                                <scroll>false</scroll>
                                <posx>0</posx>
                                <posy>{{ vscale(205) }}</posy>
                                <width>299</width>
                                <height>{{ vscale(60) }}</height>
                                <font>font10</font>
                                <align>center</align>
                                <textcolor>AAFFFFFF</textcolor>
                                <label>$INFO[ListItem.Label2]</label>
                            </control>
                        </control>
                    </control>
                </itemlayout>

                <!-- FOCUSED LAYOUT ####################################### -->
                <focusedlayout width="359">
                    <control type="group">
                        <posx>55</posx>
                        <posy>{{ vscale(61) }}</posy>
                        <control type="group">
                            <animation effect="zoom" start="100" end="110" time="100" center="154.5,{{ vscale(87.5) }}" reversible="false">Focus</animation>
                            <animation effect="zoom" start="110" end="100" time="100" center="154.5,{{ vscale(87.5) }}" reversible="false">UnFocus</animation>
                            <posx>0</posx>
                            <posy>0</posy>
                            <control type="image">
                                <visible>Control.HasFocus(403)</visible>
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
                                        <scroll>Control.HasFocus(403)</scroll>
                                        <posx>0</posx>
                                        <posy>{{ vscale(175) }}</posy>
                                        <width>299</width>
                                        <height>{{ vscale(60) }}</height>
                                        <font>font10</font>
                                        <align>center</align>
                                        <textcolor>AAFFFFFF</textcolor>
                                        <label>$INFO[ListItem.Label]</label>
                                    </control>
                                    <control type="label">
                                        <scroll>Control.HasFocus(403)</scroll>
                                        <posx>0</posx>
                                        <posy>{{ vscale(205) }}</posy>
                                        <width>299</width>
                                        <height>{{ vscale(60) }}</height>
                                        <font>font10</font>
                                        <align>center</align>
                                        <textcolor>AAFFFFFF</textcolor>
                                        <label>$INFO[ListItem.Label2]</label>
                                    </control>
                                </control>
                            </control>
                            <control type="image">
                                <visible>Control.HasFocus(403)</visible>
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
        <control type="group" id="504">
            <visible>Integer.IsGreater(Container(404).NumItems,0) + String.IsEmpty(Window.Property(drawing))</visible>
            <defaultcontrol>404</defaultcontrol>
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
            <control type="list" id="404">
                <posx>0</posx>
                <posy>{{ vscale(16) }}</posy>
                <width>1920</width>
                <height>{{ vscale(520) }}</height>
                <onup>403</onup>
                <ondown>404</ondown>
                <onleft>noop</onleft>
                <onright>noop</onright>
                <scrolltime>200</scrolltime>
                <orientation>horizontal</orientation>
                <preloaditems>4</preloaditems>
                <!-- ITEM LAYOUT ########################################## -->
                <itemlayout width="304">
                    <control type="group">
                        <posx>55</posx>
                        <posy>{{ vscale(72) }}</posy>
                        <control type="group">
                            <posx>5</posx>
                            <posy>5</posy>
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
                        </control>
                    </control>
                </itemlayout>

                <!-- FOCUSED LAYOUT ####################################### -->
                <focusedlayout width="304">
                    <control type="group">
                        <posx>55</posx>
                        <posy>{{ vscale(72) }}</posy>
                        <control type="group">
                            <animation effect="zoom" start="100" end="110" time="100" center="127,{{ vscale(180.5) }}" reversible="false">Focus</animation>
                            <animation effect="zoom" start="110" end="100" time="100" center="127,{{ vscale(180.5) }}" reversible="false">UnFocus</animation>
                            <posx>0</posx>
                            <posy>0</posy>
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
                            <control type="image">
                                <visible>Control.HasFocus(404)</visible>
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
                                    <scroll>Control.HasFocus(404)</scroll>
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
                                <visible>Control.HasFocus(404)</visible>
                                <posx>0</posx>
                                <posy>0</posy>
                                <width>254</width>
                                <height>{{ vscale(371) }}</height>
                                <texture border="10">script.plex/home/selected.png</texture>
                            </control>
                        </control>
                    </control>
                </focusedlayout>
            </control>
        </control>
        <!-- / RELATED -->

    </control>
</control>
{% endblock content %}

{# widget now sits at the header's far right, past the tabs, so the header runs search -> tabs -> widget #}
{% block header_search_onright %}<onright condition="Control.IsVisible(205)">205</onright><onright>204</onright>{% endblock %}
{% block header_audiowidget_onleft %}<onleft condition="Control.IsVisible(205)">205</onleft><onleft>202</onleft>{% endblock %}

{% block header_middle_add %}
<!-- SEASON TABS -->
<!-- Fixed-center carousel, same technique as the episode row: this grouplist is a 1160-wide clipping mask,
     positioned for a symmetric 380px gap to each screen edge - matching the audio widget's collapsed hitbox
     at 1920-360=1560 on the right (380+1160=1540, 20px shy of it) and the equivalent 380 on the left, which
     used to be split between the header buttons (ending at 200) and ~300px of dead space left behind when the
     audio widget moved out to the header's far right (see default.xml.tpl). Inside the mask, fixedlist 205 is
     oversized to 7 item-cells of 200 (170 for the label, +30 filling in for the itemgap a fixedlist can't
     express) and shifted -120, so the mask's edges fall mid-cell on the outer tabs instead of on a cell
     boundary, leaving a symmetric ~80px peek on both sides that hints at more tabs off-screen rather than a
     hard cutoff. focusposition=3 pins the true center cell (4th of 7) as the fixed focus; tabs scroll under
     it. The wrapper's onup/onleft/onright/ondown are required here (duplicated onto the child fixedlist too)
     for the same reason noted on the episode row's carousel: a grouplist wrapper doesn't reliably forward a
     nested list's boundary-exit rules on its own. -->
<control type="grouplist">
    <visible>Integer.IsGreater(Container(205).NumItems,0)</visible>
    <posx>380</posx>
    <posy>0</posy>
    <width>1160</width>
    <height>{{ vscale(135) }}</height>
    <usecontrolcoords>true</usecontrolcoords>
    <orientation>horizontal</orientation>
    <onup>200</onup>
    <onleft>202</onleft>
    <onright condition="Control.IsVisible(204)">204</onright>
    <onright>noop</onright>
    <ondown condition="Control.IsVisible(300)">300</ondown>
    <ondown condition="Control.IsVisible(1300)">1300</ondown>
    <ondown>50</ondown>
    <control type="fixedlist" id="205">
        <posx>-120</posx>
        <posy>0</posy>
        <width>1400</width>
        <height>{{ vscale(135) }}</height>
        <focusposition>3</focusposition>
        <onup>200</onup>
        <onleft>202</onleft>
        <onright condition="Control.IsVisible(204)">204</onright>
        <onright>noop</onright>
        <ondown condition="Control.IsVisible(300)">300</ondown>
        <ondown condition="Control.IsVisible(1300)">1300</ondown>
        <ondown>50</ondown>
        <scrolltime tween="quadratic" easing="out">200</scrolltime>
        <orientation>horizontal</orientation>
        <preloaditems>7</preloaditems>
        <!-- ITEM LAYOUT ########################################## -->
        <itemlayout width="200" height="{{ vscale(135) }}">
            <control type="label">
                <posx>0</posx>
                <posy>0</posy>
                <width>170</width>
                <height>{{ vscale(135) }}</height>
                <font>font12</font>
                <align>center</align>
                <aligny>center</aligny>
                <textcolor>80FFFFFF</textcolor>
                <label>$INFO[ListItem.Label]</label>
            </control>
            <control type="image">
                <visible>!String.IsEmpty(ListItem.Property(current))</visible>
                <posx>25</posx>
                <posy>{{ vscale(94) }}</posy>
                <width>120</width>
                <height>2</height>
                <texture>script.plex/white-square.png</texture>
                <colordiffuse>FFE5A00D</colordiffuse>
            </control>
        </itemlayout>

        <!-- FOCUSED LAYOUT ####################################### -->
        {# Kodi applies this layout to whichever item holds the list's internal cursor, independent of whether
           control 205 itself has window focus - so without gating on Control.HasFocus(205), the cursor's item
           (which defaults to the current season) renders in the "focused" white year-round, making the tab bar
           look focused even when focus actually sits on the play button, and keeps showing white on whatever tab
           was last highlighted after focus moves away. Splitting into two labels keyed off actual control focus
           makes it fall back to the same grey as itemlayout the rest of the time; the current-season underline
           below is unaffected since it never depended on focus. #}
        <focusedlayout width="200" height="{{ vscale(135) }}">
            <control type="label">
                <visible>Control.HasFocus(205)</visible>
                <posx>0</posx>
                <posy>0</posy>
                <width>170</width>
                <height>{{ vscale(135) }}</height>
                <font>font12</font>
                <align>center</align>
                <aligny>center</aligny>
                <scroll>true</scroll>
                <scrollspeed>25</scrollspeed>
                <textcolor>FFFFFFFF</textcolor>
                <label>$INFO[ListItem.Label]</label>
            </control>
            <control type="label">
                <visible>!Control.HasFocus(205)</visible>
                <posx>0</posx>
                <posy>0</posy>
                <width>170</width>
                <height>{{ vscale(135) }}</height>
                <font>font12</font>
                <align>center</align>
                <aligny>center</aligny>
                <textcolor>80FFFFFF</textcolor>
                <label>$INFO[ListItem.Label]</label>
            </control>
            <control type="image">
                <visible>!String.IsEmpty(ListItem.Property(current))</visible>
                <posx>25</posx>
                <posy>{{ vscale(94) }}</posy>
                <width>120</width>
                <height>2</height>
                <texture>script.plex/white-square.png</texture>
                <colordiffuse>FFE5A00D</colordiffuse>
            </control>
        </focusedlayout>
    </control>
</control>
{% endblock %}