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
            <!-- Links this panel to scrollbar 152's real scroll position/drag-to-scroll - was
                 missing here (same gap found and fixed in script-plex-posters.xml.tpl this
                 session; script.plexmod-multi's copy of this template already has it). -->
            <pagecontrol>152</pagecontrol>
            <!-- ITEM LAYOUT ########################################## -->
            <!-- Cell 282 wide, not 287: the art sits 60px into the cell (55 + the card group's own 5)
                 and is 240 wide, so 282 puts adjacent tiles 42px apart - the same art-to-art gap the
                 Artist screen's rows use (includes/artist_album_row.xml.tpl's own 282). Still 6
                 columns in the 1800-wide panel; the 30px this frees up lands in the right margin.
                 The 343 row pitch is deliberately left alone - that is grid density, not tile
                 style, and the panel's own scroll animations are tuned to 6-per-row. -->
            <itemlayout width="282" height="{{ vscale(343) }}">
                <control type="group">
                    <posx>55</posx>
                    <posy>{{ vscale(97) }}</posy>
                    <control type="group">
                        <posx>5</posx>
                        <posy>5</posy>
                        <!-- ON THE is.folder PAIRS THROUGHOUT THIS TEMPLATE - read this once and
                             the rest follow. This one grid template serves all four square section
                             types (library.py's own TYPE test: artist, photo, photodirectory,
                             playlists), but is.folder is set in exactly ONE place in the codebase -
                             fillPhotos() (library.py), on items whose own TYPE is photodirectory.
                             So every !is.folder control here is a PHOTO SUBFOLDER tile and nothing
                             else: a music, playlist or track grid never renders one. They come in
                             mutually-exclusive pairs (a taller shadow, a taller focus ring) rather
                             than one control, because a skin can't make a height conditional. The
                             folder tile is the art plus a label band below it, so its boxes are the
                             ordinary ones plus the band's own 40. Anything that changes the card
                             recipe has to change both halves of each pair. -->
                        <!-- Same drop-shadow-directional.png treatment as the Recommended tab's
                             square hub tiles (hub_itemlayout_square.xml.tpl) - thumb+24 box,
                             inset (-3,-3) local, giving the same 3px top/left, 21px bottom/right
                             directional spread there. Always shown here (this is the itemlayout,
                             not gated on focus), same as the hub tile's own itemlayout copy. -->
                        <control type="image">
                            <visible>String.IsEmpty(ListItem.Property(is.folder))</visible>
                            <posx>-3</posx>
                            <posy>{{ vscale(-3) }}</posy>
                            <width>264</width>
                            <height>{{ vscale(264) }}</height>
                            <texture border="24">script.plex/drop-shadow-directional.png</texture>
                        </control>
                        <control type="image">
                            <visible>!String.IsEmpty(ListItem.Property(is.folder))</visible>
                            <posx>-3</posx>
                            <posy>{{ vscale(-3) }}</posy>
                            <width>264</width>
                            <height>{{ vscale(304) }}</height>
                            <texture border="24">script.plex/drop-shadow-directional.png</texture>
                        </control>
                        <control type="image">
                            <posx>0</posx>
                            <posy>0</posy>
                            <width>240</width>
                            <height>{{ vscale(240) }}</height>
                            <texture diffuse="script.plex/masks/square-mask.png">$INFO[ListItem.Property(thumb.fallback)]</texture>
                        </control>
                        <control type="image">
                            <posx>0</posx>
                            <posy>0</posy>
                            <width>240</width>
                            <height>{{ vscale(240) }}</height>
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
                        <!-- Photo subfolder only (see the note up top): the label band that makes
                             a folder tile read as a folder. Flush with the art's bottom edge, not
                             offset to the caption's own 9px, so it stays attached to the art. -->
                        <control type="image">
                            <visible>!String.IsEmpty(ListItem.Property(is.folder))</visible>
                            <posx>0</posx>
                            <posy>{{ vscale(240) }}</posy>
                            <width>240</width>
                            <height>{{ vscale(40) }}</height>
                            <texture>script.plex/white-square.png</texture>
                            <colordiffuse>80000000</colordiffuse>
                        </control>
                        <control type="label">
                            <scroll>false</scroll>
                            <posx>0</posx>
                            <posy>{{ vscale(249) }}</posy>
                            <width>240</width>
                            <height>{{ vscale(34) }}</height>
                            <font>font10</font>
                            <align>center</align>
                            <aligny>center</aligny>
                            <textcolor>FFFFFFFF</textcolor>
                            <label>$INFO[ListItem.Label]</label>
                        </control>
                        <control type="label">
                            <visible>!String.IsEmpty(ListItem.Property(album.artist))</visible>
                            <scroll>false</scroll>
                            <posx>0</posx>
                            <posy>{{ vscale(279) }}</posy>
                            <width>240</width>
                            <height>{{ vscale(34) }}</height>
                            <font>font10</font>
                            <align>center</align>
                            <aligny>center</aligny>
                            <textcolor>AAFFFFFF</textcolor>
                            <label>$INFO[ListItem.Property(album.artist)]</label>
                        </control>
                    </control>
                </control>
            </itemlayout>

            <!-- FOCUSED LAYOUT ####################################### -->
            <focusedlayout width="282" height="{{ vscale(343) }}">
                <control type="group">
                    <posx>55</posx>
                    <posy>{{ vscale(97) }}</posy>
                    <control type="group">
                        <animation effect="zoom" start="100" end="104" time="100" center="125,{{ vscale(125) }}" reversible="false">Focus</animation>
                        <animation effect="zoom" start="104" end="100" time="100" center="125,{{ vscale(125) }}" reversible="false">UnFocus</animation>
                        <posx>0</posx>
                        <posy>0</posy>
                        <!-- Same drop-shadow-directional.png treatment as the Recommended tab's
                             square hub tiles (hub_focusedlayout_square.xml.tpl) - see the
                             itemlayout copy above for the geometry reasoning. Always shown here
                             too (this focusedlayout only ever renders for the focused item
                             anyway, so a Control.HasFocus(101) gate would be redundant). -->
                        <!-- Same photo-subfolder pairing as the itemlayout's copy above. -->
                        <control type="image">
                            <visible>String.IsEmpty(ListItem.Property(is.folder))</visible>
                            <posx>2</posx>
                            <posy>{{ vscale(2) }}</posy>
                            <width>264</width>
                            <height>{{ vscale(264) }}</height>
                            <texture border="24">script.plex/drop-shadow-directional.png</texture>
                        </control>
                        <control type="image">
                            <visible>!String.IsEmpty(ListItem.Property(is.folder))</visible>
                            <posx>2</posx>
                            <posy>{{ vscale(2) }}</posy>
                            <width>264</width>
                            <height>{{ vscale(304) }}</height>
                            <texture border="24">script.plex/drop-shadow-directional.png</texture>
                        </control>
                        <control type="group">
                            <posx>5</posx>
                            <posy>5</posy>
                            <control type="image">
                                <posx>0</posx>
                                <posy>0</posy>
                                <width>240</width>
                                <height>{{ vscale(240) }}</height>
                                <texture diffuse="script.plex/masks/square-mask.png">$INFO[ListItem.Property(thumb.fallback)]</texture>
                            </control>
                            <control type="image">
                                <posx>0</posx>
                                <posy>0</posy>
                                <width>240</width>
                                <height>{{ vscale(240) }}</height>
                                <texture background="true" diffuse="script.plex/masks/square-mask.png">$INFO[ListItem.Thumb]</texture>
                                <aspectratio>scale</aspectratio>
                            </control>
                            <!-- Photo subfolder only (see the note up top): the label band that makes
                                 a folder tile read as a folder. Flush with the art's bottom edge, not
                                 offset to the caption's own 9px, so it stays attached to the art. -->
                            <control type="image">
                                <visible>!String.IsEmpty(ListItem.Property(is.folder))</visible>
                                <posx>0</posx>
                                <posy>{{ vscale(240) }}</posy>
                                <width>240</width>
                                <height>{{ vscale(40) }}</height>
                                <texture>script.plex/white-square.png</texture>
                                <colordiffuse>80000000</colordiffuse>
                            </control>
                            <control type="label">
                                <scroll>Control.HasFocus(101)</scroll>
                                <posx>0</posx>
                                <posy>{{ vscale(249) }}</posy>
                                <width>240</width>
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
                                <posy>{{ vscale(279) }}</posy>
                                <width>240</width>
                                <height>{{ vscale(34) }}</height>
                                <font>font10</font>
                                <align>center</align>
                                <aligny>center</aligny>
                                <textcolor>AAFFFFFF</textcolor>
                                <label>$INFO[ListItem.Property(album.artist)]</label>
                            </control>
                        </control>
                        <control type="group">
                            <visible>Control.HasFocus(101)</visible>
                            <!-- 246 = thumb (240) + 6, the ring-to-image margin the whole card
                                 recipe uses (the Recommended tab's hub tiles put a 226 ring around
                                 a 220 thumb for the same reason). -->
                            <!-- Ring-mask, not home/selected.png's 9-slice border: this is the
                                 Artist screen's treatment (includes/artist_album_row.xml.tpl and
                                 script-plex-artist.xml.tpl's Similar Artists row), where a flat
                                 white square is diffused through an RGBA ring mask and tinted
                                 FFE9A20D, rather than a pre-rendered border texture stretched to
                                 size. The mask's corner radius scales with the box instead of
                                 staying fixed at whatever the texture was authored at, and it
                                 carries no dark outer edge of its own. Same gold either way -
                                 selected.png's own ring pixels are E9A20D. -->
                            <control type="image">
                                <visible>String.IsEmpty(ListItem.Property(is.folder))</visible>
                                <posx>2</posx>
                                <posy>{{ vscale(2) }}</posy>
                                <width>246</width>
                                <height>{{ vscale(246) }}</height>
                                <texture diffuse="script.plex/masks/ring-mask-square.png">script.plex/white-square.png</texture>
                                <colordiffuse>FFE9A20D</colordiffuse>
                            </control>
                            <!-- Photo subfolder tiles (the only ones that ever set is.folder -
                                 see the note up top) keep the 9-slice border texture. Their ring is a 246x286
                                 rectangle, not a square, because it has to enclose the label band
                                 below the art as well: a square ring mask stretched to that box
                                 would render elliptical corners and an uneven ring thickness,
                                 which is exactly what a 9-slice border does not do. -->
                            <control type="image">
                                <visible>!String.IsEmpty(ListItem.Property(is.folder))</visible>
                                <posx>2</posx>
                                <posy>{{ vscale(2) }}</posy>
                                <width>246</width>
                                <height>{{ vscale(286) }}</height>
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
    <!-- Slides up and off with the header rather than fading, matching the poster grid
         (script-plex-posters.xml.tpl - see that row's own comment: the index>5 clause used to sit
         in <visible> here too, so scrolling past it cut this row straight to invisible while the
         header, grid, scrubber and scrollbar all slid away together). Kodi can't animate a
         control out once its <visible> has gone false, so the index clause has to live in the
         slide's own condition instead. The remaining clauses are unrelated to scrolling and still
         gate real visibility. -->
    <visible>String.IsEmpty(Window.Property(no.content)) + String.IsEmpty(Window.Property(no.content.filtered)) + !String.IsEmpty(Window.Property(initialized))</visible>
    <!-- -277.5 = -(posy 132.5 + height 145): lands the row's bottom edge at 0, the same
         "slide by your own extent" the poster grid and header(200) use, on the same condition
         group 50 uses, so it moves in lockstep with the grid. -->
    <animation effect="slide" end="0,{{ vscale(-277.5, negpos=True) }}" time="200" tween="quadratic" easing="out" condition="Integer.IsGreater(Container(101).ListItem.Property(index),5) + String.IsEmpty(Window.Property(content.filling))">Conditional</animation>
    <defaultcontrol>301</defaultcontrol>
    <!-- 132, by the poster grid's own formula, re-solved for this grid's wider cell: panel(101)
         left 60 + 5*282 (6 columns, this template's own itemlayout pitch) + the item's own 55 =
         1525 card-left, art sits 5 further in and is 240 wide, so the last column's art ends at
         1770 absolute. Overlay 391/392's pill finishes 18px short of its own group's right edge
         (button-label-overlay-recipe), and that group is what right-justifies against this
         anchor, so box_right = 1770 + 18 = 1788 and <right> = 1920 - 1788 = 132. -->
    <right>132</right>
    <!-- 132.5, not 110: re-centres the glyph now the box is theme.library.buttons' 70x70 instead
         of the old hardcoded 126x100. The button textures stretch into their box with no
         aspectratio, so the glyph's opaque fraction down the box is fixed - Play's own pixels
         reach 0.75 of it either way. Old box: 110 + 0.75*100 = 185 absolute. New box: 185 -
         0.75*70 = 132.5, landing the glyph in exactly the same place, and on the same absolute
         line as the poster grid's own row (which solved the identical sum). -->
    <posy>{{ vscale(132.5) }}</posy>
    <width>1000</width>
    <height>{{ vscale(145) }}</height>
    <align>right</align>
    <!-- Same up-route restoration as group 600's own onup above - the grid's own onup can land
         here directly too (Container(101).ListItem.Property(index) >= 3), so this needs the
         same fallback independently, not just inherited from 600. -->
    <!-- Audio widget first, tab row second - Kodi takes the first onup whose condition holds, so
         the old order sent up to the tabs whenever they were on screen, which is always, and the
         widget was only ever reachable from here on a screen without them. The condition is the
         widget group's own <visible> verbatim (library.xml.tpl), so this route exists exactly when
         there's something there to land on; its own <ondown>50</ondown> comes back into the
         content. Tabs stay the fallback for everything else, unchanged. -->
    <onup condition="Player.HasAudio + String.IsEmpty(Window(10000).Property(script.plex.theme_playing))">204</onup>
    <onup condition="Control.IsVisible(320)">320</onup>
    <ondown>101</ondown>
    <onleft>210</onleft>
    <onright>151</onright>
    <itemgap>{{ theme.library.buttongroup.itemgap }}</itemgap>
    <orientation>horizontal</orientation>
    <scrolltime tween="quadratic" easing="out">200</scrolltime>
    <usecontrolcoords>true</usecontrolcoords>

    {# theme.library.buttons (70x70) and its hitrect, not the hardcoded 126x100/20,20,86,60 this
       used to carry - the same box the poster grid's own Play/Shuffle row uses, and through it
       the same box as Seasons/Episodes/Pre-play. Play and Shuffle also gain the label-on-focus
       pill overlay those rows have (391/392), reusing their measured widths since it's the same
       text at the same font. More has never carried one anywhere; View doesn't get one here
       because it's hidden outright in music sections (forcedViewWindow(), library.py) and the
       music grid is what this was asked for. #}
    {% with attr = theme.library.buttons & template = "includes/themed_button.xml.tpl" & hitrect = theme.library.buttons_hitrect & ol = "includes/episode_button_label.xml.tpl" %}
        {# No section-level play/shuffle for playlists - each playlist item plays/shuffles
           itself (its own context menu), there's no single "the section" to play here the way
           a movie/show library has. #}
        {% include template with name="play" & id=301 & visible="String.IsEmpty(Window.Property(disable_playback)) + !String.IsEqual(Window.Property(media),playlists) + [!String.IsEqual(Window(10000).Property(script.plex.item.type),collection) | String.IsEqual(Window.Property(media),collection)]" %}
        {% include ol with id=391 & visible="Control.HasFocus(301)" & name="play" &
            label="$ADDON[script.plexmod 33020]" & label_suffix_info="" &
            label_width=50 & pill_width=112 & group_width=68 &
            onleft=301 & onright=302
        %}
        {% include template with name="shuffle" & id=302 & visible="String.IsEmpty(Window.Property(disable_playback)) + !String.IsEqual(Window.Property(media),playlists) + [!String.IsEqual(Window(10000).Property(script.plex.item.type),collection) | String.IsEqual(Window.Property(media),collection)]" %}
        {# onright falls back to the scrubber (151, this row's own boundary target) when More
           isn't on screen: in a music section neither More nor View shows any more, so Shuffle is
           the last button in the row and a bare onright=303 would point at a hidden control. #}
        {% include ol with id=392 & visible="Control.HasFocus(302)" & name="shuffle" &
            label="$ADDON[script.plexmod 32935]" & label_suffix_info="" &
            label_width=84 & pill_width=146 & group_width=102 &
            onleft=302 & onright=303 & onright_cond="Control.IsVisible(303)" & onright_else=151
        %}
        {# No More button for music sections. Its menu only ever holds two entries
           (optionsButtonClicked(), library.py): "Play Next", itself gated on Player.HasAudio +
           MusicPlayer.HasNext, and "Go to <section>", which is photodirectory-only. So in a music
           library it showed whenever audio was playing and opened an empty dropdown unless a next
           track happened to be queued. Photos (where the button carries its Go-to entry) and
           Playlists keep it. #}
        {% include template with name="more" & id=303 & visible="String.IsEmpty(Window.Property(disable_playback)) + [String.IsEmpty(Window.Property(no.options)) | Player.HasAudio] + !String.IsEqual(Window.Property(media),artist)" %}
        {# id 304 doubles as VIEWTYPE_BUTTON_ID (library.py) regardless of what this template
           labels it - a genuine view-type switch (poster/list layout) makes sense for a grid of
           playlists same as any other section, but "chapters" as a label/icon here never did
           (chapters are a video pre-play concept). Hidden for playlists on that mislabeling
           alone, independent of whether it's ever meaningfully clickable. #}
        {# Hidden for music sections: Artists/Albums/Collections are pinned to the grid and
           Tracks to the list (MUSIC_VIEWTYPE_BY_ITEM_TYPE / forcedViewWindow(), library.py), so
           there is nothing here to toggle. Window.Property(media) is the section type, not the
           item type - the pin covers every item type in the section, so the section-level test is
           the right one. Photos and Playlists keep the button. #}
        {% include template with name="view" & id=304 & visible="String.IsEmpty(Window.Property(hide.filteroptions)) + !String.IsEqual(Window.Property(media),playlists) + !String.IsEqual(Window.Property(media),artist)" %}
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
    <!-- 1836, not 1875: leaves a 15px gap to the scrollbar (152's left=1885), which now shows
         ALONGSIDE this rather than instead of it, exactly as on the poster grid. The scrubber's
         own list (151) is a flat 34px wide with no internal margin (key_scrubber_items.xml.tpl
         fills it edge to edge), so 1885 - (posx + 34) = 15 gives posx = 1836. Room for both
         opened up here for the same reason it did there - the grid's last column ends at 1770. -->
    <posx>1836</posx>
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
        <!-- The scrollbar is now a real neighbour to the right, so it needs reaching. (The poster
             grid's own copy of this routes left to 304/View specifically; this one stays on the
             grouplist 300, because View is hidden outright in music sections and More can be
             hidden too - there's no button here that's guaranteed to be the rightmost.) -->
        <onright>152</onright>
        <scrolltime>200</scrolltime>
        <orientation>vertical</orientation>
        {% include "includes/key_scrubber_items.xml.tpl" %}
    </control>
</control>

<!-- The proportional position indicator - now shown alongside the scrubber above for
     alphabetical orderings too, not instead of it (script.plex.sort.alpha only gates the scrubber
     itself now), matching the poster grid. Standalone sibling rather than nested in panel 101:
     the panel's own <pagecontrol>152</pagecontrol> is what links this to the grid's real scroll
     position and drag-to-scroll, and that works wherever 152 sits in the tree. -->
<control type="scrollbar" id="152">
    <visible>Integer.IsGreater(Container(101).NumItems,0) + String.IsEmpty(Window.Property(drawing))</visible>
    <hitrect x="1845" y="150" w="100" h="910" />
    <left>1885</left>
    <top>{{ vscale(150) }}</top>
    <width>12</width>
    <height>910</height>
    <!-- Slide, not the old zoom-to-fill-the-vacated-header-space: the same -69 the scrubber
         beside it uses, so the two stay level now that they show together (they rest level, both
         at 150). Zooming this one instead left it growing past a scrubber that had merely moved. -->
    <animation effect="slide" end="0,{{ vscale(-69, negpos=True) }}" time="200" tween="quadratic" easing="out" condition="Integer.IsGreater(Container(101).ListItem.Property(index),5) + String.IsEmpty(Window.Property(content.filling))">Conditional</animation>
    {% include "includes/scrollbar_style.xml.tpl" %}
    <!-- Back to the scrubber when it's showing too (alpha orderings); otherwise mirror the
         scrubber's own two-tier routing - the grid once the header has scrolled away, the button
         row while it's still up - since the scrubber isn't there to make that hop. -->
    <onleft condition="!String.IsEmpty(Window(10000).Property(script.plex.sort.alpha))">151</onleft>
    <onleft condition="String.IsEmpty(Window(10000).Property(script.plex.sort.alpha)) + Integer.IsGreater(Container(101).ListItem.Property(index),5)">100</onleft>
    <onleft condition="String.IsEmpty(Window(10000).Property(script.plex.sort.alpha)) + !Integer.IsGreater(Container(101).ListItem.Property(index),5)">300</onleft>
</control>
{% endblock content %}