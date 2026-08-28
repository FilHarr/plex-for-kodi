{% extends "library_posters.xml.tpl" %}
{% block filteropts_grouplist %}
<control type="grouplist" id="600">
    <visible>String.IsEmpty(Window.Property(hide.filteroptions))</visible>
    <visible>!Integer.IsGreater(Container(101).ListItem.Property(index),{% block hide_filter_from_index %}5{% endblock %}) + String.IsEmpty(Window.Property(no.content)) + !String.IsEmpty(Window.Property(initialized))</visible>
    <animation effect="slide" time="200" end="0,{{ vscale(-115) }}" tween="quadratic" easing="out" condition="Integer.IsGreater(Container(101).ListItem.Property(index),{% block hide_filter_from_index %}5{% endblock %}) + String.IsEmpty(Window.Property(content.filling))">Conditional</animation>
    {% block filteropts_animation %}
        <animation effect="fade" start="0" end="100" time="200" reversible="true">VisibleChange</animation>
    {% endblock %}
    <!-- Swapped with the buttons row (300): this row now sits where 300 used to (left,
         next to the sidebar), so it needs the same expand-slide the content/scrubber use. -->
    <animation effect="slide" end="220,0" time="200" tween="sine" easing="inout" condition="ControlGroup(9000).HasFocus(0)">Conditional</animation>
    <posx>105</posx>
    <posy>{{ vscale(127.5) }}</posy>
    <width>1000</width>
    <height>65</height>
    <align>left</align>
    <itemgap>0</itemgap>
    <orientation>horizontal</orientation>
    <onleft>9000</onleft>
    <onright>300</onright>
    <ondown>101</ondown>
    <!-- Restores the up-route into the tab row (320) that library_posters.xml.tpl's own
         default filteropts_grouplist has (its onup, line 23 there) - lost here because this
         block fully overrides that one rather than extending it. Matters for every section
         using this template, not just playlists, but only actually surfaced once Playlists had
         a tab row worth reaching (Music/Video) - see section_tabs.xml.tpl's own comment on this
         being the intended entry point "from below". Checked first, same precedence
         library.xml.tpl's header_filteropts_onup block uses. -->
    <onup condition="Control.IsVisible(320)">320</onup>
    <onup condition="Player.HasAudio + String.IsEmpty(Window(10000).Property(script.plex.theme_playing))">204</onup>
    <control type="button" id="311">
        <!-- No genre/category filter concept for playlists - see 211's own comment. -->
        <visible>!String.IsEqual(Window.Property(media),playlists)</visible>
        <enable>false</enable>
        <width max="300">auto</width>
        <height>65</height>
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
        <!-- Playlists port: playlists never populate filter1.display/self.filter (no genre/
             category filter concept for playlists at all, unlike Artist/Movie/Show), so this
             would otherwise show a stale/blank filter button. -->
        <visible>!String.IsEqual(Window.Property(media),playlists)</visible>
        <width max="500">auto</width>
        <height>65</height>
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
        <visible>!String.IsEqual(Window.Property(media),artist) + !String.IsEqual(Window.Property(media),playlists)</visible>
        <enable>false</enable>
        <width max="300">auto</width>
        <height>65</height>
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
        <!-- Artist/Album/Collection/Track item-type dropdown. Playlists used this too until the
             user asked for Music/Video to be real tabList tabs (id 320) instead of a floating
             dropdown button here - see buildTabList()/itemTypeButtonClicked() (library.py). -->
        <visible>String.IsEqual(Window.Property(media),artist)</visible>
        <width max="300">auto</width>
        <height>65</height>
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
        <!-- Same disabled-button placeholder trick as 311/310 above: a plain <label> here
             would sit mid-list rather than trailing, so it wouldn't break onright the way
             the old trailing label below did, but it's kept as a button for consistency
             with the rest of the row. -->
        <!-- "by" only ever makes sense trailing a genre/category filter selection (211/311/310
             above) - playlists has none of those, so on its own this just reads as a stray
             floating word. -->
        <visible>!String.IsEqual(Window.Property(media),playlists)</visible>
        <enable>false</enable>
        <width max="60">auto</width>
        <height>65</height>
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
        <visible>!String.IsEqual(Window.Property(media),playlists)</visible>
        <enable>false</enable>
        <width>15</width>
        <height>65</height>
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
        <visible>!String.IsEqual(Window.Property(media),playlists) + !String.IsEqual(Window.Property(sort.icon),desc)</visible>
        <enable>false</enable>
        <width>30</width>
        <height>65</height>
        <texturefocus>-</texturefocus>
        <texturenofocus>script.plex/indicators/sort-asc.png</texturenofocus>
    </control>
    <control type="button" id="213">
        <visible>!String.IsEqual(Window.Property(media),playlists) + String.IsEqual(Window.Property(sort.icon),desc)</visible>
        <enable>false</enable>
        <width>30</width>
        <height>65</height>
        <texturefocus>-</texturefocus>
        <texturenofocus>script.plex/indicators/sort-desc.png</texturenofocus>
    </control>
    <control type="button" id="210">
        <!-- Explicit, not relying on the grouplist's own onright: the trailing item-count
             label below is non-focusable, which stops the grouplist from falling through to
             its container-level onright when 210 is the last focusable (but not last
             declared) child. -->
        <!-- No sort concept for playlists (SORT_KEYS['playlists'] is empty, library.py) -
             same treatment 211/311/310 above already give the genre/category filter buttons. -->
        <!-- Targets 301 (the play button) directly, not container 300. -->
        <visible>!String.IsEqual(Window.Property(media),playlists)</visible>
        <onright>301</onright>
        <width max="300">auto</width>
        <height>65</height>
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
        <visible>!String.IsEqual(Window.Property(media),playlists)</visible>
        <enable>false</enable>
        <onright>301</onright>
        <width max="400">auto</width>
        <height>65</height>
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
<control type="group" id="50">
    <!-- Playlists has no sort/filter/play/shuffle row (600/300 are effectively empty there -
         see their own per-control playlists visibility conditions above), leaving a dead band
         between the tab row (320, bottom edge at y=135) and this grid's first row (currently
         y=232: this group's own posy 135 + the itemlayout group's own 97 offset). Reclaims part
         of that gap for playlists only - stacks additively with the scroll-based slides below
         (same Conditional-animation-composition already relied on for those two), so scrolling
         still slides it further up on top of this. First-pass offset, not pixel-measured against
         a live screenshot - may want retuning after a live look. -->
    <animation effect="slide" time="200" end="0,{{ vscale(-73) }}" condition="String.IsEqual(Window.Property(media),playlists)">Conditional</animation>
    <animation effect="slide" time="200" end="0,{{ vscale(-135) }}" condition="Integer.IsGreater(Container(101).ListItem.Property(index),5)">Conditional</animation>
    <animation effect="slide" time="200" end="0,{{ vscale(-200) }}" condition="Integer.IsGreater(Container(101).ListItem.Property(index),5) + Integer.IsGreater(Container(101).Position,5)">Conditional</animation>
    <animation effect="slide" end="220,0" time="200" tween="sine" easing="inout" condition="ControlGroup(9000).HasFocus(0)">Conditional</animation>
    <posx>60</posx>
    <posy>{{ vscale(135) }}</posy>
    <defaultcontrol>101</defaultcontrol>


    <control type="group" id="100">
        <visible>Integer.IsGreater(Container(101).NumItems,0) + String.IsEmpty(Window.Property(drawing))</visible>
        <defaultcontrol>101</defaultcontrol>
        <posx>0</posx>
        <posy>0</posy>
        <width>1920</width>
        <height>1080</height>
        <control type="panel" id="101">
            <hitrect x="0" y="95" w="1780" h="1185" />
            <posx>0</posx>
            <posy>0</posy>
            <width>1800</width>
            <height>1280</height>
            <onup condition="Integer.IsLess(Container(101).ListItem.Property(index),3)">600</onup>
            <onup condition="Integer.IsLess(Container(101).ListItem.Property(index),6) + Integer.IsGreaterOrEqual(Container(101).ListItem.Property(index),3)">300</onup>
            <onleft>9000</onleft>
            <onright>151</onright>
            <scrolltime>200</scrolltime>
            <orientation>vertical</orientation>
            <preloaditems>2</preloaditems>
            <!-- ITEM LAYOUT ########################################## -->
            <itemlayout width="287" height="{{ vscale(343) }}">
                <control type="group">
                    <posx>55</posx>
                    <posy>{{ vscale(97) }}</posy>
                    <control type="group">
                        <posx>5</posx>
                        <posy>5</posy>
                        <!-- Same drop-shadow-directional.png treatment as the Recommended tab's
                             square hub tiles (hub_itemlayout_square.xml.tpl) - thumb+24 box,
                             inset (-3,-3) local, giving the same 3px top/left, 21px bottom/right
                             directional spread there. Always shown here (this is the itemlayout,
                             not gated on focus), same as the hub tile's own itemlayout copy. -->
                        <control type="image">
                            <visible>String.IsEmpty(ListItem.Property(is.folder))</visible>
                            <posx>-3</posx>
                            <posy>{{ vscale(-3) }}</posy>
                            <width>268</width>
                            <height>{{ vscale(268) }}</height>
                            <texture border="24">script.plex/drop-shadow-directional.png</texture>
                        </control>
                        <control type="image">
                            <visible>!String.IsEmpty(ListItem.Property(is.folder))</visible>
                            <posx>-3</posx>
                            <posy>{{ vscale(-3) }}</posy>
                            <width>268</width>
                            <height>{{ vscale(308) }}</height>
                            <texture border="24">script.plex/drop-shadow-directional.png</texture>
                        </control>
                        <control type="image">
                            <posx>0</posx>
                            <posy>0</posy>
                            <width>244</width>
                            <height>{{ vscale(244) }}</height>
                            <texture diffuse="script.plex/masks/square-mask.png">$INFO[ListItem.Property(thumb.fallback)]</texture>
                        </control>
                        <control type="image">
                            <posx>0</posx>
                            <posy>0</posy>
                            <width>244</width>
                            <height>{{ vscale(244) }}</height>
                            <texture background="true" diffuse="script.plex/masks/square-mask.png">$INFO[ListItem.Thumb]</texture>
                            <!-- scalediffuse="false": without it, Kodi scales the diffuse mask
                                 texture along with the aspectratio-adjusted art instead of
                                 keeping it fixed to the control's own bounds - the mask's rounded
                                 shape then drifts/stretches with the source art's own aspect
                                 ratio instead of staying a clean 244x244 rounded square, live-
                                 confirmed as square corners surviving on non-square-ish art.
                                 Matches hub_itemlayout_square.xml.tpl/
                                 hub_focusedlayout_square.xml.tpl's own identical guard. -->
                            <aspectratio scalediffuse="false">scale</aspectratio>
                        </control>
                        <control type="image">
                            <visible>!String.IsEmpty(ListItem.Property(is.folder))</visible>
                            <posx>0</posx>
                            <posy>{{ vscale(244) }}</posy>
                            <width>244</width>
                            <height>{{ vscale(40) }}</height>
                            <texture>script.plex/white-square.png</texture>
                            <colordiffuse>80000000</colordiffuse>
                        </control>
                        <control type="label">
                            <scroll>true</scroll>
                            <posx>0</posx>
                            <posy>{{ vscale(244) }}</posy>
                            <width>244</width>
                            <height>{{ vscale(34) }}</height>
                            <font>font10</font>
                            <align>center</align>
                            <aligny>center</aligny>
                            <textcolor>FFFFFFFF</textcolor>
                            <label>$INFO[ListItem.Label]</label>
                        </control>
                        <control type="label">
                            <visible>!String.IsEmpty(ListItem.Property(album.artist))</visible>
                            <scroll>true</scroll>
                            <posx>0</posx>
                            <posy>{{ vscale(278) }}</posy>
                            <width>244</width>
                            <height>{{ vscale(34) }}</height>
                            <font>font10</font>
                            <align>center</align>
                            <aligny>center</aligny>
                            <textcolor>FFAAAAAA</textcolor>
                            <label>$INFO[ListItem.Property(album.artist)]</label>
                        </control>
                    </control>
                </control>
            </itemlayout>

            <!-- FOCUSED LAYOUT ####################################### -->
            <focusedlayout width="287" height="{{ vscale(343) }}">
                <control type="group">
                    <posx>55</posx>
                    <posy>{{ vscale(97) }}</posy>
                    <control type="group">
                        <animation effect="zoom" start="100" end="110" time="100" center="127,{{ vscale(127) }}" reversible="false">Focus</animation>
                        <animation effect="zoom" start="110" end="100" time="100" center="127,{{ vscale(127) }}" reversible="false">UnFocus</animation>
                        <posx>0</posx>
                        <posy>0</posy>
                        <!-- Same drop-shadow-directional.png treatment as the Recommended tab's
                             square hub tiles (hub_focusedlayout_square.xml.tpl) - see the
                             itemlayout copy above for the geometry reasoning. Always shown here
                             too (this focusedlayout only ever renders for the focused item
                             anyway, so a Control.HasFocus(101) gate would be redundant). -->
                        <control type="image">
                            <visible>String.IsEmpty(ListItem.Property(is.folder))</visible>
                            <posx>2</posx>
                            <posy>{{ vscale(2) }}</posy>
                            <width>268</width>
                            <height>{{ vscale(268) }}</height>
                            <texture border="24">script.plex/drop-shadow-directional.png</texture>
                        </control>
                        <control type="image">
                            <visible>!String.IsEmpty(ListItem.Property(is.folder))</visible>
                            <posx>2</posx>
                            <posy>{{ vscale(2) }}</posy>
                            <width>268</width>
                            <height>{{ vscale(308) }}</height>
                            <texture border="24">script.plex/drop-shadow-directional.png</texture>
                        </control>
                        <control type="group">
                            <posx>5</posx>
                            <posy>5</posy>
                            <control type="image">
                                <posx>0</posx>
                                <posy>0</posy>
                                <width>244</width>
                                <height>{{ vscale(244) }}</height>
                                <texture diffuse="script.plex/masks/square-mask.png">$INFO[ListItem.Property(thumb.fallback)]</texture>
                            </control>
                            <control type="image">
                                <posx>0</posx>
                                <posy>0</posy>
                                <width>244</width>
                                <height>{{ vscale(244) }}</height>
                                <texture background="true" diffuse="script.plex/masks/square-mask.png">$INFO[ListItem.Thumb]</texture>
                                <aspectratio>scale</aspectratio>
                            </control>
                            <control type="image">
                                <visible>!String.IsEmpty(ListItem.Property(is.folder))</visible>
                                <posx>0</posx>
                                <posy>{{ vscale(244) }}</posy>
                                <width>244</width>
                                <height>{{ vscale(40) }}</height>
                                <texture>script.plex/white-square.png</texture>
                                <colordiffuse>80000000</colordiffuse>
                            </control>
                            <control type="label">
                                <scroll>Control.HasFocus(101)</scroll>
                                <posx>0</posx>
                                <posy>{{ vscale(244) }}</posy>
                                <width>244</width>
                                <height>{{ vscale(34) }}</height>
                                <font>font10</font>
                                <align>center</align>
                                <aligny>center</aligny>
                                <textcolor>FFFFFFFF</textcolor>
                                <label>$INFO[ListItem.Label]</label>
                            </control>
                            <control type="label">
                                <visible>!String.IsEmpty(ListItem.Property(album.artist))</visible>
                                <scroll>Control.HasFocus(101)</scroll>
                                <posx>0</posx>
                                <posy>{{ vscale(278) }}</posy>
                                <width>244</width>
                                <height>{{ vscale(34) }}</height>
                                <font>font10</font>
                                <align>center</align>
                                <aligny>center</aligny>
                                <textcolor>FFAAAAAA</textcolor>
                                <label>$INFO[ListItem.Property(album.artist)]</label>
                            </control>
                        </control>
                        <control type="group">
                            <visible>Control.HasFocus(101)</visible>
                            <!-- 250 = thumb (244) + 6, matching the Recommended tab hub tiles'
                                 own thumb+6 ring-to-image margin (hub_focusedlayout_square.xml.tpl:
                                 226 ring around a 220 thumb) - was 254 (a 10px margin) before. -->
                            <control type="image">
                                <visible>String.IsEmpty(ListItem.Property(is.folder))</visible>
                                <posx>2</posx>
                                <posy>{{ vscale(2) }}</posy>
                                <width>250</width>
                                <height>{{ vscale(250) }}</height>
                                <texture border="10">script.plex/home/selected.png</texture>
                            </control>
                            <control type="image">
                                <visible>!String.IsEmpty(ListItem.Property(is.folder))</visible>
                                <posx>2</posx>
                                <posy>{{ vscale(2) }}</posy>
                                <width>250</width>
                                <height>{{ vscale(290) }}</height>
                                <texture border="10">script.plex/home/selected.png</texture>
                            </control>
                        </control>
                    </control>
                </control>
            </focusedlayout>
        </control>
    </control>
</control>

{% block buttons %}
<!-- Swapped with the filter row (600): this row now sits where 600 used to (right, next
     to the scrubber) so it's right-anchored like 600 was, and no longer needs the
     sidebar-expand slide 600 needed on the left. -->
<control type="grouplist" id="300">
    <animation effect="fade" start="0" end="100" time="200" reversible="true">VisibleChange</animation>
    <visible>!Integer.IsGreater(Container(101).ListItem.Property(index),5) + String.IsEmpty(Window.Property(no.content)) + String.IsEmpty(Window.Property(no.content.filtered)) + !String.IsEmpty(Window.Property(initialized))</visible>
    <defaultcontrol>301</defaultcontrol>
    <right>120</right>
    <posy>{{ vscale(110) }}</posy>
    <width>1000</width>
    <height>{{ vscale(145) }}</height>
    <align>right</align>
    <!-- Same up-route restoration as group 600's own onup above - the grid's own onup can land
         here directly too (Container(101).ListItem.Property(index) >= 3), so this needs the
         same fallback independently, not just inherited from 600. -->
    <onup condition="Control.IsVisible(320)">320</onup>
    <onup condition="Player.HasAudio + String.IsEmpty(Window(10000).Property(script.plex.theme_playing))">204</onup>
    <ondown>101</ondown>
    <onleft>210</onleft>
    <onright>151</onright>
    <itemgap>-20</itemgap>
    <orientation>horizontal</orientation>
    <scrolltime tween="quadratic" easing="out">200</scrolltime>
    <usecontrolcoords>true</usecontrolcoords>

    {% with attr = {"width": 126, "height": 100} & template = "includes/themed_button.xml.tpl" & hitrect = {"x": 20, "y": 20, "w": 86, "h": 60} %}
        {# No section-level play/shuffle for playlists - each playlist item plays/shuffles
           itself (its own context menu), there's no single "the section" to play here the way
           a movie/show library has. #}
        {% include template with name="play" & id=301 & visible="String.IsEmpty(Window.Property(disable_playback)) + !String.IsEqual(Window.Property(media),playlists) + [!String.IsEqual(Window(10000).Property(script.plex.item.type),collection) | String.IsEqual(Window.Property(media),collection)]" %}
        {% include template with name="shuffle" & id=302 & visible="String.IsEmpty(Window.Property(disable_playback)) + !String.IsEqual(Window.Property(media),playlists) + [!String.IsEqual(Window(10000).Property(script.plex.item.type),collection) | String.IsEqual(Window.Property(media),collection)]" %}
        {% include template with name="more" & id=303 & visible="String.IsEmpty(Window.Property(disable_playback)) + [String.IsEmpty(Window.Property(no.options)) | Player.HasAudio]" %}
        {# id 304 doubles as VIEWTYPE_BUTTON_ID (library.py) regardless of what this template
           labels it - a genuine view-type switch (poster/list layout) makes sense for a grid of
           playlists same as any other section, but "chapters" as a label/icon here never did
           (chapters are a video pre-play concept). Hidden for playlists on that mislabeling
           alone, independent of whether it's ever meaningfully clickable. #}
        {% include template with name="chapters" & id=304 & visible="String.IsEmpty(Window.Property(hide.filteroptions)) + !String.IsEqual(Window.Property(media),playlists)" %}
    {% endwith %}

</control>
{% endblock %}

<control type="group" id="150">
    <visible>!String.IsEmpty(Window(10000).Property(script.plex.sort.alpha)) + Integer.IsGreater(Container(101).NumItems,0) + String.IsEmpty(Window.Property(drawing))</visible>
    <defaultcontrol>151</defaultcontrol>
    <!-- posx/posy match where the scrollbar (id 152, below) rests when it's showing instead;
         the slide animation mirrors the zoom the scrollbar does when the header hides on
         scroll, growing into the space the header vacates instead of resizing.
         End position centers the scrubber's full 27-key extent (26 letters + '#', 34px each =
         918) in the 1080-tall screen: (1080-918)/2 = 81 top margin, a 150-81=69px move up from
         the resting posy. -->
    <animation effect="slide" end="0,{{ vscale(-69, negpos=True) }}" time="200" tween="quadratic" easing="out" condition="Integer.IsGreater(Container(101).ListItem.Property(index),5) + String.IsEmpty(Window.Property(content.filling))">Conditional</animation>
    <posx>1875</posx>
    <posy>{{ vscale(150) }}</posy>
    <width>20</width>
    <height>920</height>
    <control type="list" id="151">
        <posx>0</posx>
        <posy>0</posy>
        <width>34</width>
        <height>1050</height>
        <onleft condition="Integer.IsGreater(Container(101).ListItem.Property(index),5) | !Integer.IsEqual(Container(151).ListItem.Property(index),0)">100</onleft>
        <onleft condition="!Integer.IsGreater(Container(101).ListItem.Property(index),5) + Integer.IsEqual(Container(151).ListItem.Property(index),0)">300</onleft>
        <scrolltime>200</scrolltime>
        <orientation>vertical</orientation>
        {% include "includes/key_scrubber_items.xml.tpl" %}
    </control>
</control>

<!-- Shown instead of the scrubber above for sorts that don't produce alphabetical
     ordering (script.plex.sort.alpha unset) - a plain proportional position indicator. -->
<control type="scrollbar" id="152">
    <visible>String.IsEmpty(Window(10000).Property(script.plex.sort.alpha)) + Integer.IsGreater(Container(101).NumItems,0) + String.IsEmpty(Window.Property(drawing))</visible>
    <hitrect x="1845" y="150" w="100" h="910" />
    <left>1885</left>
    <top>{{ vscale(150) }}</top>
    <width>12</width>
    <height>910</height>
    <animation effect="zoom" time="200" start="1885,{{ vscale(150) }},12,910" end="1885,16,12,1055" tween="quadratic" easing="out" condition="Integer.IsGreater(Container(101).ListItem.Property(index),5) + String.IsEmpty(Window.Property(content.filling))">Conditional</animation>
    {% include "includes/scrollbar_style.xml.tpl" %}
    <onleft>151</onleft>
</control>
{% endblock content %}