{% extends "default.xml.tpl" %}
{# Bounded grid view for a Collection's own members - see lib/windows/collection.py's
   BoundedGridWindow/CollectionWindow. Deliberately does NOT extend library.xml.tpl (no sidebar
   section-tabs row, no sort/filter/view-type-toggle chrome, no key-scrubber) - see
   hashed-orbiting-pizza.md's Phase 4. Same header/sidebar opt-in pattern as
   script-plex-episodes.xml.tpl/script-plex-pre_play.xml.tpl. #}
{# The header (the audio widget) slides off the top on scroll, as the library grid's does
   (library.xml.tpl's header_animation, same 125 and the same hold while the header has focus) -
   keyed to this grid's own scrolled state, the same condition as group 50's page slide. #}
{# Pre-play's full-screen dim behind the rows (includes/default_background.xml.tpl), on the
   same condition as the page slide: the grid past its first row. #}
{% block background %}{% include "includes/default_background.xml.tpl" with row_dim_condition="Integer.IsGreater(Container(101).CurrentItem,6)" %}{% endblock %}
{% block header_anim %}<animation effect="slide" end="0,{{ vscale(-125) }}" time="200" tween="quadratic" easing="out" condition="Integer.IsGreater(Container(101).CurrentItem,6) + !ControlGroup(200).HasFocus(0)">Conditional</animation>{% endblock %}
{% block header %}
    {{ super() }}
    {% include "includes/sidebar.xml.tpl" %}
    <!-- Declared last so groups 802/901 draw on top - see script-plex-pre_play.xml.tpl's own copy
         of this include for the full reasoning (this window is one of the seven real hosted-shell
         types too, same _sidebarTarget()-aware Python side, same onClick forwarding). -->
    {% include "includes/sidebar_dropdowns.xml.tpl" %}
{% endblock header %}
{% block content %}
<control type="group" id="50">
    <!-- Slide right while the sidebar rail is expanded (focused), matching every other
         sidebar-opted-in window (Library/Pre-play/Episodes). -->
    <animation effect="slide" end="220,0" time="200" tween="sine" easing="inout" condition="ControlGroup(9000).HasFocus(0)">Conditional</animation>
    <!-- The whole page scrolls, rather than the grid scrolling under a clip edge: off the first
         row (6 to a row - the panel is 1800 wide in 272 cells), everything slides up 450, taking
         the info panel off the top (group 60 goes a further 100, below, to clear the buttons) and
         putting the rows where a scrolled library grid has its own: the top one in view at
         y=113 and the one under it at 573 (script-plex-posters.xml.tpl: group 50's 125, less its
         115 slide, + group 100's -34 + the rows' 137). Row 1's item group rests at 563 (this
         group's 155 + group 100's 283 + the rows' 125 lead-in). The panel then scrolls its own
         rows as usual, its clip edges off the screen's. -->
    <animation effect="slide" end="0,{{ vscale(-450) }}" time="200" tween="quadratic" easing="out" condition="Integer.IsGreater(Container(101).CurrentItem,6)">Conditional</animation>
    <posx>60</posx>
    <posy>{{ vscale(155) }}</posy>
    <defaultcontrol>101</defaultcontrol>

    <!-- INFO PANEL ############################################ -->
    {# The home screen's hero overlay for a focused movie (script-plex-recommended.xml.tpl's
       hero-info group) verbatim - big clearlogo box with the font45 title fallback, summary
       textbox - with a collection-specific meta line (item count / year span) in the meta
       row's slot instead of includes/pp_meta_row.xml.tpl (on request, 2026-09-20). That overlay's host group sits at
       (52, 125); this window's group 50 is at (60, 155), so this group's own (-8, -30) offset puts
       every child at the same absolute position as its home counterpart (x=113 for the 61-inset
       controls, y=125 for the logo/title box). #}
    <control type="group" id="60">
        <!-- A further 100 on top of group 50's page slide, so the button row clears the top of
             the screen too (its bottom edge: 540 on screen at rest, less 550). -->
        <animation effect="slide" end="0,{{ vscale(-100) }}" time="200" tween="quadratic" easing="out" condition="Integer.IsGreater(Container(101).CurrentItem,6)">Conditional</animation>
        <posx>-8</posx>
        <posy>{{ vscale(-30) }}</posy>
        <width>1780</width>
        <!-- Down to the button row's bottom edge (345 + 70). -->
        <height>{{ vscale(415) }}</height>
        <control type="label">
            <visible>String.IsEmpty(Window.Property(clear.logo))</visible>
            <posx>61</posx>
            <posy>0</posy>
            <width>722</width>
            <height>{{ vscale(162) }}</height>
            <font>font45_title</font>
            <align>left</align>
            <aligny>center</aligny>
            <!-- The clearlogo box exactly (722x162 at the same origin), title text centred in it and
                 wrapped rather than scrolled - up to two lines of 45px fit (on request, 2026-09-20).
                 center is the only vertical alignment a Kodi label honours; "bottom" is silently top,
                 which is why the old 616x109/aligny=bottom box drew its text at the top edge. -->
            <wrapmultiline>true</wrapmultiline>
            <textcolor>FFFFFFFF</textcolor>
            <label>$INFO[Window.Property(collection.title)]</label>
        </control>
        <control type="image">
            <visible>!String.IsEmpty(Window.Property(clear.logo))</visible>
            <posx>61</posx>
            <posy>0</posy>
            <width>722</width>
            <height>{{ vscale(162) }}</height>
            <aspectratio align="left" aligny="bottom">keep</aspectratio>
            <texture background="true">$INFO[Window.Property(clear.logo)]</texture>
        </control>
        <!-- Meta line: "<n> items &#8226; <minYear>-<maxYear>" (collection.meta,
             CollectionWindow.setup()) in the pre-play meta row's own slot (includes/pp_meta_row.xml.tpl:
             61/175, 708x30, FFD2CCCE, 66000000 shadow), but in font30_title, the row headings' own
             font (on request) - a plain label rather than that include, which reads pre-play's own
             properties. -->
        <control type="label">
            <posx>61</posx>
            <posy>{{ vscale(175) }}</posy>
            <width>708</width>
            <height>{{ vscale(30) }}</height>
            <font>font30_title</font>
            <align>left</align>
            <textcolor>FFD2CCCE</textcolor>
            <shadowcolor>66000000</shadowcolor>
            <label>$INFO[Window.Property(collection.meta)]</label>
        </control>
        <control type="textbox">
            <posx>61</posx>
            <posy>{{ vscale(239) }}</posy>
            <width>813</width>
            <height>{{ vscale(90) }}</height>
            <font>font10</font>
            <align>left</align>
            <textcolor>FFD2CCCE</textcolor>
            <shadowcolor>66000000</shadowcolor>
            <scrolltime>200</scrolltime>
            <autoscroll delay="2000" time="2000" repeat="10000"/>
            <label>$INFO[Window.Property(collection.summary)]</label>
        </control>
        <!-- Invisible click/focus target laid over the summary textbox, and its focus highlight -
             script-plex-artist.xml.tpl's own 305 pair verbatim (see its comments for why it's a
             separate button, why both textures are "-", and why the highlight is its own image):
             a textbox has no click or focus of its own, so this is how the summary popup
             (CollectionWindow.summaryButtonClicked(), SUMMARY_BUTTON_ID) is reached. Only there
             when there's a summary to open - every nav tag routing through it carries the same
             condition so the chain closes up instead of dead-ending on a control that isn't
             there. Up from the button row (or the grid, when there's no row) lands here; up from
             here is the header. -->
        <control type="button" id="305">
            <visible>!String.IsEmpty(Window.Property(collection.summary))</visible>
            <posx>61</posx>
            <posy>{{ vscale(239) }}</posy>
            <width>813</width>
            <height>{{ vscale(90) }}</height>
            <onup>200</onup>
            <ondown condition="Control.IsVisible(300)">300</ondown>
            <ondown>101</ondown>
            <onleft>9000</onleft>
            <label> </label>
            <texturenofocus>-</texturenofocus>
            <texturefocus>-</texturefocus>
        </control>
        <control type="image">
            <visible>Control.HasFocus(305)</visible>
            <posx>56</posx>
            <posy>{{ vscale(234) }}</posy>
            <width>823</width>
            <height>{{ vscale(100) }}</height>
            <colordiffuse>33FFFFFF</colordiffuse>
            <texture border="10">script.plex/white-square-rounded.png</texture>
        </control>

        <!-- Play / Shuffle (CollectionWindow.playButtonClicked()): the album screen's button row
             (script-plex-album.xml.tpl, itself the Artist screen's) minus its More button -
             theme.artist's 70x70 icon boxes and label-on-focus pills, with Play's and Shuffle's
             measured widths. Under the summary with that screen's 16px gap (239 + 90 + 16).
             Only there when the collection can be queued (collection.playable). -->
        <control type="grouplist" id="300">
            <visible>!String.IsEmpty(Window.Property(collection.playable))</visible>
            <animation effect="fade" start="0" end="100" time="200" reversible="true">VisibleChange</animation>
            <defaultcontrol>301</defaultcontrol>
            <posx>61</posx>
            <posy>{{ vscale(345) }}</posy>
            <width>1000</width>
            <height>{{ vscale(70) }}</height>
            <align>left</align>
            <onup condition="!String.IsEmpty(Window.Property(collection.summary))">305</onup>
            <onup>200</onup>
            <ondown>101</ondown>
            <onleft>9000</onleft>
            <itemgap>{{ theme.artist.buttongroup.itemgap }}</itemgap>
            <orientation>horizontal</orientation>
            <scrolltime tween="quadratic" easing="out">200</scrolltime>
            <usecontrolcoords>true</usecontrolcoords>

            {% with attr = theme.artist.buttons & template = "includes/themed_button.xml.tpl" & hitrect = theme.artist.buttons_hitrect & ol = "includes/episode_button_label.xml.tpl" %}
                {% include template with name="play" & id=301 & overlay=True %}
                {% include ol with id=391 & visible="Control.HasFocus(301)" & name="play" &
                    label="$ADDON[script.plexmod 33020]" & label_suffix_info="" &
                    label_width=51 & pill_width=113 & group_width=69 &
                    onleft=301 & onright=302
                %}
                {% include template with name="shuffle" & id=302 & overlay=True %}
                {% include ol with id=392 & visible="Control.HasFocus(302)" & name="shuffle" &
                    label="$ADDON[script.plexmod 32935]" & label_suffix_info="" &
                    label_width=84 & pill_width=146 & group_width=102 &
                    onleft=302
                %}
            {% endwith %}
        </control>
    </control>

    <!-- GRID ################################################## -->
    <control type="group" id="100">
        <visible>Integer.IsGreater(Container(101).NumItems,0) + String.IsEmpty(Window.Property(drawing))</visible>
        <defaultcontrol>101</defaultcontrol>
        <posx>-5</posx>
        <!-- The panel's top edge is its clip edge. 283 puts it at y=438 on screen, so that once
         group 50 has slid up its 450 it's at -12, just off the screen's own top edge, and rows
         scroll off the screen rather than being cut mid-screen. The rows carry a 125px lead-in (the item
         group's posy below) to put row 1 where it was: its item group at 563 on screen, so a
         focused poster's top edge - its focus ring, zoomed 4% about y=183, so 7.3 above the
         item group - sits 33.5px under the buttons' glyphs, the same visible gap as from the
         summary box down to the glyphs' top (16px between the boxes plus the 17.5px Play's
         glyph leaves empty inside its 70px box, measured off modern/play.png). Nothing is
         drawn in the panel above row 1, so its rect overlapping the buttons shows nothing; the
         hitrect below keeps it off them for the mouse. -->
        <posy>{{ vscale(283) }}</posy>
        <width>1920</width>
        <height>1080</height>
        {# Lifted from script-plex-posters.xml.tpl's own panel/itemlayout/focusedlayout
           (script-plex-posters.xml.tpl:17-219) - the tile visuals themselves aren't
           LibraryWindow-specific, only the chunk-cache/sort/filter chrome around them was (see
           this plan's own note on this). onup/onright to the dropped filter-row/scrubber
           (600/151) removed - nothing above/right of the grid in this template.

           height/hitrect NOT copied verbatim, unlike the rest. 1190, that file's own height:
           once group 50 has slid up, the panel reaches from just off the top of the screen (-12)
           to past the bottom (1178), so nothing clips mid-screen. That holds floor(1190/460) = 2
           rows, as that file's does, so moving
           onto row 2 is the page slide alone and the panel first scrolls on row 3 - the row
           above the focused one stays in view, as on the Seasons page. At rest the panel runs
           off the bottom of the screen, row 2 peeking in ~54px. The hitrect starts at the
           rows' 125 lead-in, below the buttons. #}
        <control type="panel" id="101">
            <hitrect x="0" y="125" w="1780" h="1065" />
            <posx>0</posx>
            <posy>0</posy>
            <width>1800</width>
            <height>1190</height>
            <onleft>9000</onleft>
            <!-- wraparound=false alone didn't stop it live - onXXX destinations only kick in once
                 a container has exhausted its own internal items in that direction, and 'noop' is
                 this codebase's own established way to say "consume the press, don't move focus
                 anywhere" (includes/sidebar.xml.tpl:322, the server button's own ondown). -->
            <ondown>noop</ondown>
            <!-- Up from the grid's first row reaches the Play/Shuffle row (300), or the summary's
                 click target (305) when there's no row; otherwise consumed, as before. -->
            <onup condition="Control.IsVisible(300)">300</onup>
            <onup condition="!String.IsEmpty(Window.Property(collection.summary))">305</onup>
            <onup>noop</onup>
            <scrolltime>200</scrolltime>
            <orientation>vertical</orientation>
            <preloaditems>2</preloaditems>
            <wraparound>false</wraparound>
            <!-- ITEM LAYOUT ########################################## -->
            <!-- Card recipe copied from the movie/TV library grid (script-plex-posters.xml.tpl) on
                 request, 2026-09-20: 240x360 art (was 244x361), 264x384 shadow plate, 272-wide
                 items (32px art-to-art gap, was 287/43), 104% focus zoom (was 110%), 246x366
                 ring-mask ring and the inset 224x8 progress pill (was a full-width flat strip).
                 Still 6 columns in the 1800-wide panel. Both caption lines too - collection.py's
                 setItemInfo() sets 'year' for members (never 'subtitle', so the year label is
                 the one that shows). The item
                 group's posy is 125, not that file's 137: the rows' lead-in, which with the
                 panel's own posy above puts row 1 under the buttons and a scrolled page's
                 focused row at y=125 - see group 100's comment. -->
            <itemlayout width="272" height="{{ vscale(460) }}">
                <control type="group">
                    <posx>55</posx>
                    <posy>{{ vscale(125) }}</posy>
                    <control type="image">
                        <posx>0</posx>
                        <posy>0</posy>
                        <width>264</width>
                        <height>{{ vscale(384) }}</height>
                        <texture border="24">script.plex/drop-shadow-directional.png</texture>
                    </control>
                    <control type="group">
                        <posx>3</posx>
                        <posy>3</posy>
                        <control type="image">
                            <posx>0</posx>
                            <posy>0</posy>
                            <width>240</width>
                            <height>{{ vscale(360) }}</height>
                            <texture background="true" diffuse="script.plex/masks/poster-mask.png" fallback="$INFO[ListItem.Property(thumb.fallback)]">$INFO[ListItem.Thumb]</texture>
                            <aspectratio scalediffuse="false">scale</aspectratio>
                        </control>
                        <control type="group">
                            <visible>!String.IsEmpty(ListItem.Property(progress))</visible>
                            <posx>8</posx>
                            <posy>{{ vscale(344) }}</posy>
                            <control type="image">
                                <posx>0</posx>
                                <posy>0</posy>
                                <width>224</width>
                                <height>{{ vscale(8) }}</height>
                                <texture diffuse="script.plex/masks/progress-bar-mask.png">script.plex/white-square.png</texture>
                                <colordiffuse>E60A0F1A</colordiffuse>
                            </control>
                            <control type="image">
                                <posx>0</posx>
                                <posy>0</posy>
                                <width>224</width>
                                <height>{{ vscale(8) }}</height>
                                <texture diffuse="script.plex/masks/progress-bar-mask.png">$INFO[ListItem.Property(progress)]</texture>
                                <colordiffuse>FFE5A00D</colordiffuse>
                            </control>
                        </control>
                        {% include "includes/watched_indicator.xml.tpl" with xoff=240 & uw_size=48 & wbg_w=34.4 & wbg_h=34.4 & with_count=True & scale="medium" %}
                        <control type="label">
                            <scroll>false</scroll>
                            <posx>0</posx>
                            <posy>{{ vscale(371) }}</posy>
                            <width>240</width>
                            <height>{{ vscale(72) }}</height>
                            <font>font10</font>
                            <align>center</align>
                            <textcolor>FFFFFFFF</textcolor>
                            <label>$INFO[ListItem.Label]</label>
                        </control>
                        <control type="label">
                            <visible>!String.IsEmpty(ListItem.Property(subtitle))</visible>
                            <scroll>false</scroll>
                            <posx>0</posx>
                            <posy>{{ vscale(401) }}</posy>
                            <width>240</width>
                            <height>{{ vscale(72) }}</height>
                            <font>font8</font>
                            <align>center</align>
                            <textcolor>A0FFFFFF</textcolor>
                            <label>$INFO[ListItem.Property(subtitle)]</label>
                        </control>
                        <control type="label">
                            <visible>!String.IsEmpty(ListItem.Property(year)) + String.IsEmpty(ListItem.Property(subtitle))</visible>
                            <scroll>false</scroll>
                            <posx>0</posx>
                            <posy>{{ vscale(401) }}</posy>
                            <width>240</width>
                            <height>{{ vscale(72) }}</height>
                            <font>font8</font>
                            <align>center</align>
                            <textcolor>A0FFFFFF</textcolor>
                            <label>$INFO[ListItem.Property(year)]</label>
                        </control>
                    </control>
                </control>
            </itemlayout>

            <focusedlayout width="272" height="{{ vscale(460) }}">
                <control type="group">
                    <posx>55</posx>
                    <posy>{{ vscale(125) }}</posy>
                    <control type="group">
                        <animation effect="zoom" start="100" end="104" time="100" center="123,{{ vscale(183) }}" reversible="false">Focus</animation>
                        <animation effect="zoom" start="104" end="100" time="100" center="123,{{ vscale(183) }}" reversible="false">UnFocus</animation>
                        <posx>0</posx>
                        <posy>0</posy>
                        <control type="image">
                            <posx>0</posx>
                            <posy>0</posy>
                            <width>264</width>
                            <height>{{ vscale(384) }}</height>
                            <texture border="24">script.plex/drop-shadow-directional.png</texture>
                        </control>
                        <control type="group">
                            <posx>3</posx>
                            <posy>3</posy>
                            <control type="image">
                                <posx>0</posx>
                                <posy>0</posy>
                                <width>240</width>
                                <height>{{ vscale(360) }}</height>
                                <texture background="true" diffuse="script.plex/masks/poster-mask.png" fallback="$INFO[ListItem.Property(thumb.fallback)]">$INFO[ListItem.Thumb]</texture>
                                <aspectratio scalediffuse="false">scale</aspectratio>
                            </control>
                            <control type="group">
                                <visible>!String.IsEmpty(ListItem.Property(progress))</visible>
                                <posx>8</posx>
                                <posy>{{ vscale(344) }}</posy>
                                <control type="image">
                                    <posx>0</posx>
                                    <posy>0</posy>
                                    <width>224</width>
                                    <height>{{ vscale(8) }}</height>
                                    <texture diffuse="script.plex/masks/progress-bar-mask.png">script.plex/white-square.png</texture>
                                    <colordiffuse>E60A0F1A</colordiffuse>
                                </control>
                                <control type="image">
                                    <posx>0</posx>
                                    <posy>0</posy>
                                    <width>224</width>
                                    <height>{{ vscale(8) }}</height>
                                    <texture diffuse="script.plex/masks/progress-bar-mask.png">$INFO[ListItem.Property(progress)]</texture>
                                    <colordiffuse>FFE5A00D</colordiffuse>
                                </control>
                            </control>
                            {% include "includes/watched_indicator.xml.tpl" with xoff=240 & uw_size=48 & wbg_w=34.4 & wbg_h=34.4 & with_count=True & scale="medium" %}
                            <control type="label">
                                <scroll>true</scroll>
                                <posx>0</posx>
                                <posy>{{ vscale(371) }}</posy>
                                <width>240</width>
                                <height>{{ vscale(72) }}</height>
                                <font>font10</font>
                                <align>center</align>
                                <textcolor>FFFFFFFF</textcolor>
                                <label>$INFO[ListItem.Label]</label>
                            </control>
                            <control type="label">
                                <visible>!String.IsEmpty(ListItem.Property(subtitle))</visible>
                                <scroll>false</scroll>
                                <posx>0</posx>
                                <posy>{{ vscale(401) }}</posy>
                                <width>240</width>
                                <height>{{ vscale(72) }}</height>
                                <font>font8</font>
                                <align>center</align>
                                <textcolor>A0FFFFFF</textcolor>
                                <label>$INFO[ListItem.Property(subtitle)]</label>
                            </control>
                            <control type="label">
                                <visible>!String.IsEmpty(ListItem.Property(year)) + String.IsEmpty(ListItem.Property(subtitle))</visible>
                                <scroll>false</scroll>
                                <posx>0</posx>
                                <posy>{{ vscale(401) }}</posy>
                                <width>240</width>
                                <height>{{ vscale(72) }}</height>
                                <font>font8</font>
                                <align>center</align>
                                <textcolor>A0FFFFFF</textcolor>
                                <label>$INFO[ListItem.Property(year)]</label>
                            </control>
                        </control>
                        <control type="image">
                            <visible>Control.HasFocus(101)</visible>
                            <posx>0</posx>
                            <posy>0</posy>
                            <width>246</width>
                            <height>{{ vscale(366) }}</height>
                            <texture diffuse="script.plex/masks/ring-mask-poster.png">script.plex/white-square.png</texture>
                            <colordiffuse>FFE9A20D</colordiffuse>
                        </control>
                    </control>
                </control>
            </focusedlayout>
        </control>
    </control>
</control>
{% endblock content %}
