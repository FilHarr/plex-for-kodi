{% extends "library.xml.tpl" %}
{% block header_bg %}{% endblock %}
{% block header_animation %}{% endblock %}
{% block filteropts_animation %}{% endblock %}
{% block no_content %}{% endblock %}

{% block filteropts_grouplist %}
<control type="grouplist" id="600">
    <visible>String.IsEmpty(Window.Property(hide.filteroptions))</visible>
    <!-- Swapped with the buttons row (300): this row now sits where 300 used to (left,
         next to the sidebar), so it needs the same expand-slide 300 used to have. -->
    <animation effect="slide" end="220,0" time="200" tween="sine" easing="inout" condition="ControlGroup(9000).HasFocus(0)">Conditional</animation>
    <posx>105</posx>
    <posy>{{ vscale(127.5) }}</posy>
    <width>1000</width>
    <height>{{ vscale(65) }}</height>
    <align>left</align>
    <itemgap>0</itemgap>
    <orientation>horizontal</orientation>
    <onleft>9000</onleft>
    <onright>300</onright>
    <ondown>101</ondown>
    <onup condition="Control.IsVisible(320)">320</onup>
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
        <label>[CAPITALIZE]$INFO[Window.Property(filter2.display)][/CAPITALIZE]</label>
    </control>
    <control type="button" id="211">
        <width max="500">auto</width>
        <height>{{ vscale(65) }}</height>
        <font>font12</font>
        <textcolor>FFFFFFFF</textcolor>
        <focusedcolor>FFFFFFFF</focusedcolor>
        <align>center</align>
        <aligny>center</aligny>
        <texturefocus colordiffuse="33FFFFFF" border="10">script.plex/white-square-rounded.png</texturefocus>
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
        <focusedcolor>FFFFFFFF</focusedcolor>
        <disabledcolor>FFFFFFFF</disabledcolor>
        <align>center</align>
        <aligny>center</aligny>
        <texturefocus colordiffuse="33FFFFFF" border="10">script.plex/white-square-rounded.png</texturefocus>
        <texturenofocus>-</texturenofocus>
        <textoffsetx>20</textoffsetx>
        <textoffsety>0</textoffsety>
        <label>[CAPITALIZE]$INFO[Window.Property(media.type)][/CAPITALIZE]</label>
    </control>
    <control type="button" id="314">
        <!-- Same disabled-button placeholder trick as 311/310/313: a plain <label> here
             would sit mid-list rather than trailing, so it wouldn't break onright the way
             313 did, but it's kept as a button for consistency with the rest of the row. -->
        <enable>false</enable>
        <width max="60">auto</width>
        <height>{{ vscale(65) }}</height>
        <font>font12</font>
        <textcolor>gray</textcolor>
        <disabledcolor>gray</disabledcolor>
        <align>center</align>
        <aligny>center</aligny>
        <texturefocus>-</texturefocus>
        <texturenofocus>-</texturenofocus>
        <textoffsetx>0</textoffsetx>
        <textoffsety>0</textoffsety>
        <label>$ADDON[script.plexmod 35052]</label>
    </control>
    <control type="button" id="215">
        <!-- Blank 15px gap before the sort-direction icon, since itemgap above is 0 -
             disabled button (not a plain image), matching the same nav-safe placeholder
             pattern used elsewhere in this row. -->
        <enable>false</enable>
        <width>{{ vscale(15) }}</width>
        <height>{{ vscale(65) }}</height>
        <texturefocus>-</texturefocus>
        <texturenofocus>-</texturenofocus>
    </control>
    <control type="button" id="212">
        <!-- Ascending/descending indicator for the sort button below - see sortButtonClicked()/
             updateSortIcon() (library.py). type=button + enable=false, not type=image: a plain
             image here isn't a focusable-eligible control type, which breaks the grouplist's
             internal navigation - same class of issue as the plain-label case 313 already
             documents below. Direct grouplist child at the row's own full height (not a shorter
             box + <posy>, and not wrapped in a group): a shorter box with an explicit posy
             offset - even nested one level inside a group - measurably broke this row's
             right-navigation out to the play button when this sat after 210 instead of before
             it, for reasons that didn't trace back to any onright value. Matching every
             sibling's plain full-height footprint is what's proven not to disturb it, so the
             vertical offset is baked into the sort-asc/desc.png canvas's own transparent padding
             instead of a posy tag. Sits before 210 (between 314 and it), not after: 314 is
             already a proven-safe disabled placeholder ahead of a real focusable control, so
             this just extends that same already-working internal-flow skip rather than
             recreating the boundary-exit case 210's own onright comment covers. Two
             mutually-exclusive static-texture buttons, not one dynamic $INFO path -
             $INFO[Window.Property(...)] isn't evaluated inside <texturenofocus> the way it is
             inside an image control's <texture>, so that only rendered an empty box. Same
             swap-on-a-property pattern 310/312 already use above for the media-type button's
             artist variant. -->
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
        <!-- Explicit, not relying on the grouplist's own onright: the trailing item-count
             label below is non-focusable, which stops the grouplist from falling through to
             its container-level onright when 210 is the last focusable (but not last
             declared) child. Targets 301 (the play button) directly, not container 300. -->
        <onright>301</onright>
        <width max="300">auto</width>
        <height>{{ vscale(65) }}</height>
        <font>font12</font>
        <textcolor>FFFFFFFF</textcolor>
        <focusedcolor>FFFFFFFF</focusedcolor>
        <align>center</align>
        <aligny>center</aligny>
        <texturefocus colordiffuse="33FFFFFF" border="10">script.plex/white-square-rounded.png</texturefocus>
        <texturenofocus>-</texturenofocus>
        <textoffsetx>20</textoffsetx>
        <textoffsety>0</textoffsety>
        <label>[CAPITALIZE]$INFO[Window.Property(sort.display)][/CAPITALIZE]</label>
    </control>
    <control type="button" id="313">
        <!-- type=button + enable=false, not a plain label: a trailing plain <label> as the
             grouplist's last child breaks the list's onright boundary-fallback for whichever
             button precedes it (210 couldn't reach 300 on the right with a label here) - a
             disabled button matches the already-working 311/310 placeholder pattern above.
             Explicit onright of its own (previously relied only on being unreachable since
             disabled): belt-and-suspenders alongside 210/212/213's own onright, in case Kodi's
             right-navigation ever lands focus attempts here instead of falling through. -->
        <enable>false</enable>
        <onright>301</onright>
        <width max="400">auto</width>
        <height>{{ vscale(65) }}</height>
        <font>font10</font>
        <textcolor>gray</textcolor>
        <disabledcolor>gray</disabledcolor>
        <align>left</align>
        <aligny>center</aligny>
        <texturefocus>-</texturefocus>
        <texturenofocus>-</texturenofocus>
        <label>($INFO[Window.Property(items.count)] [LOWERCASE]$INFO[Window.Property(media.type)][/LOWERCASE])</label>
    </control>
</control>
{% endblock filteropts_grouplist %}

{% block content %}
    {# The left-hand detail pane (big art, its labels, the rule and the metadata textbox) and the
       list itself are the two parts that differ between this view's users, so each is a block:
       script-plex-listview-tracks.xml.tpl (the music section's track list) drops the pane outright
       and re-declares the list at its own geometry, while inheriting the filter row, the button
       row, the scrubber and the scrollbar from here unchanged. Everything a child overrides has to
       be re-declared whole - Kodi can't vary a control's width or position on a condition, which is
       why the track list needs its own template at all rather than a <visible> switch in this one. #}
    {% block listview_detail %}
    <control type="group">
        <animation effect="slide" end="220,0" time="200" tween="sine" easing="inout" condition="ControlGroup(9000).HasFocus(0)">Conditional</animation>
        <posx>115</posx>
        <posy>{{ vscale(248) }}</posy>
        <control type="group">
            <visible>String.IsEqual(Window.Property(media),photo) | String.IsEqual(Window.Property(media),photodirectory)</visible>
            <control type="image">
                <posx>0</posx>
                <posy>0</posy>
                <width>630</width>
                <height>{{ vscale(355) }}</height>
                <texture colordiffuse="A0000000">script.plex/white-square.png</texture>
            </control>
            <control type="image">
                <posx>0</posx>
                <posy>0</posy>
                <width>630</width>
                <height>{{ vscale(355) }}</height>
                <fadetime>500</fadetime>
                <texture background="true" fallback="script.plex/thumb_fallbacks/photo.png">$INFO[Container(101).ListItem.Thumb]</texture>
                <aspectratio>keep</aspectratio>
            </control>
        </control>
        <control type="image">
            <visible>String.IsEqual(Window.Property(media),artist)</visible>
            <posx>0</posx>
            <posy>0</posy>
            <width>355</width>
            <height>{{ vscale(355) }}</height>
            <fadetime>500</fadetime>
            <texture background="true" fallback="script.plex/thumb_fallbacks/music.png">$INFO[Container(101).ListItem.Thumb]</texture>
            <aspectratio>scale</aspectratio>
        </control>
        <control type="group">
            <visible>!String.IsEmpty(Container(101).ListItem.Label2)</visible>
            <control type="label">
                <posx>0</posx>
                <posy>{{ vscale(355) }}</posy>
                <width>310</width>
                <height>{{ vscale(80) }}</height>
                <font>font12</font>
                <align>left</align>
                <aligny>center</aligny>
                <textcolor>FFFFFFFF</textcolor>
                <label>[B]$INFO[Container(101).ListItem.Label][/B]</label>
            </control>
            <control type="label">
                <posx>630</posx>
                <posy>{{ vscale(355) }}</posy>
                <width>310</width>
                <height>{{ vscale(80) }}</height>
                <font>font12</font>
                <align>right</align>
                <aligny>center</aligny>
                <textcolor>FFFFFFFF</textcolor>
                <label>[B]$INFO[Container(101).ListItem.Label2][/B]</label>
            </control>
        </control>
        <control type="group">
            <visible>String.IsEmpty(Container(101).ListItem.Label2)</visible>
            <control type="label">
                <posx>0</posx>
                <posy>{{ vscale(355) }}</posy>
                <width>630</width>
                <height>{{ vscale(80) }}</height>
                <font>font12</font>
                <align>left</align>
                <aligny>center</aligny>
                <textcolor>FFFFFFFF</textcolor>
                <label>[B]$INFO[Container(101).ListItem.Label][/B]</label>
            </control>
        </control>
        <control type="image">
            <posx>0</posx>
            <posy>{{ vscale(435) }}</posy>
            <width>630</width>
            <height>{{ vscale(2) }}</height>
            <texture>script.plex/white-square.png</texture>
            <colordiffuse>40000000</colordiffuse>
        </control>
        <control type="textbox">
            <posx>0</posx>
            <posy>{{ vscale(463) }}</posy>
            <width>630</width>
            <height>{{ vscale(307) }}</height>
            <font>font12</font>
            <align>left</align>
            <textcolor>FFDDDDDD</textcolor>
            <label>$INFO[Container(101).ListItem.Property(camera.model),,[CR]]$INFO[Container(101).ListItem.Property(camera.lens),,[CR]]$INFO[Container(101).ListItem.Property(photo.dims),,[CR]]$INFO[Container(101).ListItem.Property(camera.settings),,[CR]]$INFO[Container(101).ListItem.Property(photo.summary),[CR],[CR]]$INFO[Container(101).ListItem.Property(summary)]</label>
            <autoscroll delay="2000" time="2000" repeat="10000"></autoscroll>
        </control>
    </control>

    {% endblock listview_detail %}

    {% block listview_list %}
    <control type="group" id="50">
        <posx>0</posx>
        <posy>{{ vscale(135) }}</posy>
        <defaultcontrol>101</defaultcontrol>

        <control type="group" id="100">
            <visible>Integer.IsGreater(Container(101).NumItems,0) + String.IsEmpty(Window.Property(drawing))</visible>
            <defaultcontrol>101</defaultcontrol>
            <posx>750</posx>
            <posy>{{ vscale(100) }}</posy>
            <width>1170</width>
            <height>1080</height>
            <control type="image">
                <posx>0</posx>
                <posy>0</posy>
                <width>1170</width>
                <height>1080</height>
                <texture>script.plex/white-square.png</texture>
                <colordiffuse>20000000</colordiffuse>
            </control>
            <control type="list" id="101">
                <hitrect x="60" y="0" w="1010" h="845" />
                <posx>0</posx>
                <posy>0</posy>
                <width>1170</width>
                <height>845</height>
                <onup>300</onup>
                <onright>151</onright>
                <onleft>210</onleft>
                <scrolltime>200</scrolltime>
                <orientation>vertical</orientation>
                <preloaditems>4</preloaditems>
                <!-- Links this list to scrollbar 152's real scroll position/drag-to-scroll - was
                     missing here (same gap found and fixed in script-plex-posters.xml.tpl this
                     session; script.plexmod-multi's copy of this template already has it). -->
                <pagecontrol>152</pagecontrol>
                <!-- ITEM LAYOUT ########################################## -->
                <itemlayout height="{{ vscale(76) }}">
                    <control type="group">
                        <posx>120</posx>
                        <posy>{{ vscale(24) }}</posy>
                        <control type="group">
                            {% include "includes/watched_indicator.xml.tpl" with xoff=915 & yoff=8 & uw_size=35 & uw_posy=-3 & with_count=True & force_nowbg=True & scale="large" & wbg="script.plex/white-square-rounded.png" %}

                            <control type="group">
                                <posx>0</posx>
                                <posy>0</posy>
                                <control type="label">
                                    <visible>String.IsEmpty(ListItem.Property(is.folder))</visible>
                                    <posx>0</posx>
                                    <posy>0</posy>
                                    <width>915</width>
                                    <height>{{ vscale(72) }}</height>
                                    <font>font10</font>
                                    <align>left</align>
                                    <aligny>center</aligny>
                                    <textcolor>FFFFFFFF</textcolor>
                                    <label>[B]$INFO[ListItem.Label][/B]</label>
                                </control>
                                <control type="label">
                                    <visible>!String.IsEmpty(ListItem.Property(is.folder))</visible>
                                    <posx>0</posx>
                                    <posy>0</posy>
                                    <width>915</width>
                                    <height>{{ vscale(72) }}</height>
                                    <font>font10</font>
                                    <align>left</align>
                                    <aligny>center</aligny>
                                    <textcolor>FFFFFFFF</textcolor>
                                    <label>[B]$INFO[ListItem.Label][COLOR FFE5A00D]/[/COLOR][/B]</label>
                                </control>
                            </control>
                        </control>
                        <control type="image">
                            <visible>String.IsEmpty(ListItem.Property(is.footer))</visible>
                            <posx>0</posx>
                            <posy>{{ vscale(72) }}</posy>
                            <width>915</width>
                            <height>{{ vscale(2) }}</height>
                            <texture>script.plex/white-square.png</texture>
                            <colordiffuse>40000000</colordiffuse>
                        </control>
                    </control>
                </itemlayout>

                <!-- FOCUSED LAYOUT ####################################### -->
                <focusedlayout height="{{ vscale(76) }}">
                    <control type="group">
                        <control type="group">
                            <visible>!Control.HasFocus(101)</visible>
                            <posx>120</posx>
                            <posy>{{ vscale(24) }}</posy>
                            <control type="group">
                                {% include "includes/watched_indicator.xml.tpl" with xoff=915 & yoff=8 & uw_size=35 & uw_posy=-3 & with_count=True & force_nowbg=True & scale="large" & wbg="script.plex/white-square-rounded.png" %}
                                <control type="group">
                                    <posx>0</posx>
                                    <posy>0</posy>
                                    <control type="group">
                                        <posx>0</posx>
                                        <posy>0</posy>
                                        <control type="label">
                                            <visible>String.IsEmpty(ListItem.Property(is.folder))</visible>
                                            <posx>0</posx>
                                            <posy>0</posy>
                                            <width>915</width>
                                            <height>{{ vscale(72) }}</height>
                                            <font>font10</font>
                                            <align>left</align>
                                            <aligny>center</aligny>
                                            <textcolor>FFFFFFFF</textcolor>
                                            <label>[B]$INFO[ListItem.Label][/B]</label>
                                        </control>
                                        <control type="label">
                                            <visible>!String.IsEmpty(ListItem.Property(is.folder))</visible>
                                            <posx>0</posx>
                                            <posy>0</posy>
                                            <width>915</width>
                                            <height>{{ vscale(72) }}</height>
                                            <font>font10</font>
                                            <align>left</align>
                                            <aligny>center</aligny>
                                            <textcolor>FFFFFFFF</textcolor>
                                            <label>[B]$INFO[ListItem.Label][COLOR FFE5A00D]/[/COLOR][/B]</label>
                                        </control>
                                    </control>
                                </control>
                            </control>
                            <control type="image">
                                <visible>String.IsEmpty(ListItem.Property(is.footer))</visible>
                                <posx>0</posx>
                                <posy>{{ vscale(72) }}</posy>
                                <width>915</width>
                                <height>{{ vscale(2) }}</height>
                                <texture>script.plex/white-square.png</texture>
                                <colordiffuse>40000000</colordiffuse>
                            </control>
                        </control>

                        <control type="group">
                            <visible>Control.HasFocus(101)</visible>
                            <posx>63</posx>
                            <posy>{{ vscale(21) }}</posy>
                            <control type="image">
                                <posx>-40</posx>
                                <posy>{{ vscale(-40) }}</posy>
                                <width>1085</width>
                                <height>{{ vscale(156) }}</height>
                                <texture border="40">script.plex/square-rounded-shadow.png</texture>
                            </control>
                            <control type="image">
                                <posx>0</posx>
                                <posy>0</posy>
                                <width>1005</width>
                                <height>{{ vscale(76) }}</height>
                                <texture border="12">script.plex/white-square-rounded.png</texture>
                                <colordiffuse>FFE5A00D</colordiffuse>
                            </control>

                            <control type="group">
                                {% include "includes/watched_indicator.xml.tpl" with xoff=973 & yoff=12 & uw_size=35 & with_count=True & force_nowbg=True & scale="large" & wbg="script.plex/white-square-rounded.png" %}
                                <control type="group">
                                    <posx>60</posx>
                                    <posy>0</posy>
                                    <control type="label">
                                        <visible>String.IsEmpty(ListItem.Property(is.folder))</visible>
                                        <posx>0</posx>
                                        <posy>0</posy>
                                        <width>885</width>
                                        <height>{{ vscale(72) }}</height>
                                        <font>font12</font>
                                        <align>left</align>
                                        <aligny>center</aligny>
                                        <textcolor>DF000000</textcolor>
                                        <label>[B]$INFO[ListItem.Label][/B]</label>
                                    </control>
                                    <control type="label">
                                        <visible>!String.IsEmpty(ListItem.Property(is.folder))</visible>
                                        <posx>0</posx>
                                        <posy>0</posy>
                                        <width>885</width>
                                        <height>{{ vscale(72) }}</height>
                                        <font>font10</font>
                                        <align>left</align>
                                        <aligny>center</aligny>
                                        <textcolor>FF000000</textcolor>
                                        <label>[B]$INFO[ListItem.Label]/[/B]</label>
                                    </control>
                                </control>
                            </control>
                        </control>
                    </control>
                </focusedlayout>
            </control>
        </control>
    </control>

    {% endblock listview_list %}

    {% block buttons %}
    <!-- Swapped with the filter row (600): this row now sits where 600 used to (right, next
         to the scrubber), so it's right-anchored like 600 was and no longer needs its own
         expand-slide (600 has it now). -->
    <control type="grouplist" id="300">
        <defaultcontrol>301</defaultcontrol>
        <!-- 132 and 132.5, matching the grid view's own row exactly (script-plex-squares.xml.tpl -
             see its comments for both derivations): 132 puts the focus pill's right edge on the
             content's right edge at 1770, which is where the track list's rows end too, and 132.5
             keeps the glyph on the same absolute line now the box is 70x70 rather than 126x100. -->
        <right>132</right>
        <posy>{{ vscale(132.5) }}</posy>
        <width>1000</width>
        <height>{{ vscale(145) }}</height>
        <align>right</align>
        <!-- Audio widget when something is playing, tab row otherwise - see the grid's own copy
             (script-plex-squares.xml.tpl). The 320 fallback is new here: this row only ever had
             the widget route, so up did nothing at all when nothing was playing. -->
        <onup condition="Player.HasAudio + String.IsEmpty(Window(10000).Property(script.plex.theme_playing))">204</onup>
        <onup condition="Control.IsVisible(320)">320</onup>
        <ondown>101</ondown>
        <onleft>210</onleft>
        <onright>151</onright>
        <itemgap>{{ theme.library.buttongroup.itemgap }}</itemgap>
        <orientation>horizontal</orientation>
        <scrolltime tween="quadratic" easing="out">200</scrolltime>
        <usecontrolcoords>true</usecontrolcoords>
        <visible>!String.IsEmpty(Window.Property(initialized))</visible>

        {# theme.library.buttons (70x70) and its hitrect, not the hardcoded 126x100 this used to
           carry, plus the label-on-focus pills on Play and Shuffle - the same treatment the grid
           view got, so the two match as you switch between them. #}
        {% with attr = theme.library.buttons & template = "includes/themed_button.xml.tpl" & hitrect = theme.library.buttons_hitrect & ol = "includes/episode_button_label.xml.tpl" %}
            {% include template with name="play" & id=301 & overlay=True & visible="String.IsEmpty(Window.Property(disable_playback)) + [!String.IsEqual(Window(10000).Property(script.plex.item.type),collection) | String.IsEqual(Window.Property(media),collection)]" %}
            {% include ol with id=391 & visible="Control.HasFocus(301)" & name="play" &
                label="$ADDON[script.plexmod 33020]" & label_suffix_info="" &
                label_width=50 & pill_width=112 & group_width=68 &
                onleft=301 & onright=302
            %}
            {% include template with name="shuffle" & id=302 & overlay=True & visible="String.IsEmpty(Window.Property(disable_playback)) + [!String.IsEqual(Window(10000).Property(script.plex.item.type),collection) | String.IsEqual(Window.Property(media),collection)]" %}
            {# Falls back to the scrubber when More isn't on screen - in a music section neither
               More nor View shows, leaving Shuffle as the row's last button. #}
            {% include ol with id=392 & visible="Control.HasFocus(302)" & name="shuffle" &
                label="$ADDON[script.plexmod 32935]" & label_suffix_info="" &
                label_width=84 & pill_width=146 & group_width=102 &
                onleft=302 & onright=303 & onright_cond="Control.IsVisible(303)" & onright_else=151
            %}
            {# More only where its menu has something in it: "Go to <section>", photodirectory-only
               (optionsButtonClicked(), library.py - no.options is set for every other section type).
               It used to also show on any section while music played, for a "Play Next" entry that
               skipped the track; dropped, the header's now-playing popout covers that now. #}
            {% include template with name="more" & id=303 & visible="String.IsEmpty(Window.Property(disable_playback)) + String.IsEmpty(Window.Property(no.options))" %}
            {# Hidden for music sections: Artists/Albums/Collections are pinned to the grid and
               Tracks to the list (MUSIC_VIEWTYPE_BY_ITEM_TYPE / forcedViewWindow(), library.py), so
               there is nothing here to toggle. Window.Property(media) is the section type, not the
               item type - the pin covers every item type in the section, so the section-level test is
               the right one. Photos and Playlists keep the button. #}
            {% include template with name="view" & id=304 & visible="String.IsEmpty(Window.Property(hide.filteroptions)) + !String.IsEqual(Window.Property(media),artist)" %}
        {% endwith %}

    </control>
    {% endblock %}

    <control type="group" id="150">
        <visible>!String.IsEmpty(Window(10000).Property(script.plex.sort.alpha)) + Integer.IsGreater(Container(101).NumItems,0) + String.IsEmpty(Window.Property(drawing))</visible>
        <defaultcontrol>151</defaultcontrol>
        <!-- posx matches where the scrollbar (id 152, below) rests when it's showing instead;
             posy matches the other 6 views' resting position for a consistent starting height.
             No animation here: this view never hides its header on scroll, so there's no freed
             space to grow into. -->
        <!-- 1836: leaves a 15px gap to the scrollbar (152's left=1885), which now shows alongside
             this rather than instead of it, as on the grid. The scrubber's own list is a flat 34px
             wide, so 1885 - (posx + 34) = 15 gives 1836. -->
        <posx>1836</posx>
        <posy>{{ vscale(150) }}</posy>
        <width>20</width>
        <height>920</height>
        <control type="list" id="151">
            <posx>0</posx>
            <posy>0</posy>
            <width>34</width>
            <height>1050</height>
            <!-- Left goes back into the rows from any real letter, and only reaches the button row
                 from the leading '#' - matching the grid (script-plex-squares.xml.tpl). Going the
                 whole way to the buttons from every letter meant losing your place in the list each
                 time you came back from the scrubber.
                 Simpler than the grid's own pair, which additionally sends '#' into the content
                 once the grid has scrolled past index 5: that exists because its button row slides
                 away with the header, and this view never hides its header at all, so the buttons
                 are always there to land on. -->
            <onleft condition="!Integer.IsEqual(Container(151).ListItem.Property(index),0)">100</onleft>
            <onleft>300</onleft>
            <onright>152</onright>
            <scrolltime>200</scrolltime>
            <orientation>vertical</orientation>
            {% include "includes/key_scrubber_items.xml.tpl" %}
        </control>
    </control>

    <!-- The proportional position indicator - shown alongside the scrubber above now, not instead
         of it (script.plex.sort.alpha only gates the scrubber itself), matching the grid. No slide
         animation on either: this view never hides its header on scroll, so there's no freed space
         to move into. -->
    <control type="scrollbar" id="152">
        <visible>Integer.IsGreater(Container(101).NumItems,0) + String.IsEmpty(Window.Property(drawing))</visible>
        <hitrect x="1845" y="150" w="100" h="910" />
        <left>1885</left>
        <!-- 150, not 15: rests level with the scrubber beside it, and with the hitrect above,
             which already assumed 150 back when the two were never on screen together. -->
        <top>{{ vscale(150) }}</top>
        <width>12</width>
        <height>910</height>
        <!-- Back to the scrubber when it's showing too (alpha orderings), else the button row. -->
        <onleft condition="!String.IsEmpty(Window(10000).Property(script.plex.sort.alpha))">151</onleft>
        <onleft>300</onleft>
        {% include "includes/scrollbar_style.xml.tpl" %}
    </control>
{% endblock content %}