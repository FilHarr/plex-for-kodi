{% extends "default.xml.tpl" %}
{# Bounded grid view for a Collection's own members - see lib/windows/collection.py's
   BoundedGridWindow/CollectionWindow. Deliberately does NOT extend library.xml.tpl (no sidebar
   section-tabs row, no sort/filter/view-type-toggle chrome, no key-scrubber) - see
   hashed-orbiting-pizza.md's Phase 4. Same header/sidebar opt-in pattern as
   script-plex-episodes.xml.tpl/script-plex-pre_play.xml.tpl. #}
{% block header_topleft %}{% endblock %}
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
    <posx>60</posx>
    <posy>{{ vscale(155) }}</posy>
    <defaultcontrol>101</defaultcontrol>

    <!-- INFO PANEL ############################################ -->
    {# Poster inset dropped per direct feedback - clearlogo/title and summary now use the exact
       size/position script-plex-recommended.xml.tpl's own focused-hub-item overlay uses
       (script-plex-recommended.xml.tpl:428-478: posx=60 inner offset, title/logo box
       616x{{vscale(109)}} font45, summary textbox 708x{{vscale(90)}} at posy={{vscale(201)}}
       font12), not a from-scratch size. Meta row (script-plex-recommended.xml.tpl:464,
       includes/pp_meta_row.xml.tpl - rating/duration pills) not included - nothing meaningful
       to show there for a whole collection. #}
    <control type="group" id="60">
        <posx>0</posx>
        <posy>0</posy>
        <width>1780</width>
        <height>{{ vscale(296) }}</height>
        <!-- Clearlogo-with-title-fallback: same pattern as script-plex-episodes.xml.tpl's own
             show.title/clear.logo pair (script-plex-episodes.xml.tpl:86-119) and the recommended
             hub overlay this is now sized to match - two sibling controls in the same box, gated
             on opposite Window.Property(clear.logo) emptiness checks, not a Python-side branch. -->
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
            <label>$INFO[Window.Property(collection.title)]</label>
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
        <control type="textbox">
            <posx>60</posx>
            <!-- posy=109 (was 201, matching the title box's own bottom edge exactly), height=182
                 (was 90) - reclaims the 92px gap that existed between them in the original
                 recommended-hub layout this was copied from, where it was occupied by a meta-row
                 of rating/duration pills (includes/pp_meta_row.xml.tpl) this window doesn't
                 include - nothing meaningful to show there for a whole collection. Bottom edge
                 (109+182=291) unchanged from before (201+90=291), so only the empty gap above the
                 text is reclaimed, not the space below it. -->
            <posy>{{ vscale(109) }}</posy>
            <width>708</width>
            <height>{{ vscale(182) }}</height>
            <font>font12</font>
            <align>left</align>
            <textcolor>FFD2CCCE</textcolor>
            <shadowcolor>66000000</shadowcolor>
            <scrolltime>200</scrolltime>
            <autoscroll delay="2000" time="2000" repeat="10000"/>
            <label>$INFO[Window.Property(collection.summary)]</label>
        </control>
    </control>

    <!-- GRID ################################################## -->
    <control type="group" id="100">
        <visible>Integer.IsGreater(Container(101).NumItems,0) + String.IsEmpty(Window.Property(drawing))</visible>
        <defaultcontrol>101</defaultcontrol>
        <posx>-5</posx>
        <!-- +102 from the last value (231): the panel's own top edge (its scroll-clip boundary)
             was overlapping the info panel's summary text above it, ending around vscale(446) -
             live-confirmed. Item content is shifted up by the same 102px within its own row box
             (itemlayout/focusedlayout's inner posy, 137->35 below) so visually nothing moves -
             only the clip boundary/scroll math changes, not what's actually on screen. -->
        <posy>{{ vscale(333) }}</posy>
        <width>1920</width>
        <height>1080</height>
        {# Lifted from script-plex-posters.xml.tpl's own panel/itemlayout/focusedlayout
           (script-plex-posters.xml.tpl:17-219) - the tile visuals themselves aren't
           LibraryWindow-specific, only the chunk-cache/sort/filter chrome around them was (see
           this plan's own note on this). onup/onright to the dropped filter-row/scrubber
           (600/151) removed - nothing above/right of the grid in this template.

           height/hitrect NOT copied verbatim, unlike the rest. A panel only scrolls once focus
           moves past floor(height/rowHeight) fully-accounted-for rows - rowHeight here is the
           itemlayout's own {{ vscale(460) }}. The previous 924 gave floor(924/460)=2, so scrolling
           only kicked in on row 3 - live-confirmed one row later than wanted. Dropped below
           2*460=920 to force floor(.../460)=1, so it triggers moving onto row 2 instead, with a
           deliberate ~90px peek of row 2 left visible (550-460) rather than cutting off right at
           460 - the same "let the next row peek in" idea script-plex-posters.xml.tpl's own 1190
           (row-3-scroll, ~230px peek there) uses, just recalibrated for a 1-row trigger. #}
        <control type="panel" id="101">
            <hitrect x="0" y="95" w="1780" h="545" />
            <posx>0</posx>
            <posy>0</posy>
            <width>1800</width>
            <height>550</height>
            <onleft>9000</onleft>
            <!-- wraparound=false alone didn't stop it live - onXXX destinations only kick in once
                 a container has exhausted its own internal items in that direction, and 'noop' is
                 this codebase's own established way to say "consume the press, don't move focus
                 anywhere" (includes/sidebar.xml.tpl:322, the server button's own ondown). -->
            <ondown>noop</ondown>
            <onup>noop</onup>
            <scrolltime>200</scrolltime>
            <orientation>vertical</orientation>
            <preloaditems>2</preloaditems>
            <wraparound>false</wraparound>
            <!-- ITEM LAYOUT ########################################## -->
            <itemlayout width="287" height="{{ vscale(460) }}">
                <control type="group">
                    <posx>55</posx>
                    <!-- -102 from the original 137 (script-plex-posters.xml.tpl's own value) -
                         compensates the panel's own +102 posy move above, so the poster/label
                         block renders at the same absolute screen position as before. -->
                    <posy>{{ vscale(35) }}</posy>
                    <control type="image">
                        <posx>0</posx>
                        <posy>0</posy>
                        <width>268</width>
                        <height>{{ vscale(385) }}</height>
                        <texture border="24">script.plex/drop-shadow-directional.png</texture>
                    </control>
                    <control type="group">
                        <posx>3</posx>
                        <posy>3</posy>
                        <control type="image">
                            <posx>0</posx>
                            <posy>0</posy>
                            <width>244</width>
                            <height>{{ vscale(361) }}</height>
                            <texture background="true" diffuse="script.plex/masks/poster-mask.png" fallback="$INFO[ListItem.Property(thumb.fallback)]">$INFO[ListItem.Thumb]</texture>
                            <aspectratio scalediffuse="false">scale</aspectratio>
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
                        {% include "includes/watched_indicator.xml.tpl" with xoff=244 & uw_size=45 & wbg_w=34.4 & wbg_h=34.4 & with_count=True & scale="medium" %}
                        <control type="label">
                            <scroll>false</scroll>
                            <posx>0</posx>
                            <posy>{{ vscale(371) }}</posy>
                            <width>244</width>
                            <height>{{ vscale(72) }}</height>
                            <font>font10</font>
                            <align>center</align>
                            <textcolor>FFFFFFFF</textcolor>
                            <label>$INFO[ListItem.Label]</label>
                        </control>
                    </control>
                </control>
            </itemlayout>

            <!-- FOCUSED LAYOUT ####################################### -->
            <focusedlayout width="287" height="{{ vscale(460) }}">
                <control type="group">
                    <posx>55</posx>
                    <!-- Same -102 compensation as itemlayout's identical group above. -->
                    <posy>{{ vscale(35) }}</posy>
                    <control type="group">
                        <animation effect="zoom" start="100" end="110" time="100" center="127,{{ vscale(185) }}" reversible="false">Focus</animation>
                        <animation effect="zoom" start="110" end="100" time="100" center="127,{{ vscale(185) }}" reversible="false">UnFocus</animation>
                        <posx>0</posx>
                        <posy>0</posy>
                        <control type="image">
                            <visible>Control.HasFocus(101)</visible>
                            <posx>0</posx>
                            <posy>0</posy>
                            <width>268</width>
                            <height>{{ vscale(385) }}</height>
                            <texture border="24">script.plex/drop-shadow-directional.png</texture>
                        </control>
                        <control type="group">
                            <posx>3</posx>
                            <posy>3</posy>
                            <control type="image">
                                <posx>0</posx>
                                <posy>0</posy>
                                <width>244</width>
                                <height>{{ vscale(361) }}</height>
                                <texture background="true" diffuse="script.plex/masks/poster-mask.png" fallback="$INFO[ListItem.Property(thumb.fallback)]">$INFO[ListItem.Thumb]</texture>
                                <aspectratio scalediffuse="false">scale</aspectratio>
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
                            {% include "includes/watched_indicator.xml.tpl" with xoff=244 & uw_size=45 & wbg_w=34.4 & wbg_h=34.4 & with_count=True & scale="medium" %}
                            <control type="label">
                                <scroll>true</scroll>
                                <posx>0</posx>
                                <posy>{{ vscale(371) }}</posy>
                                <width>244</width>
                                <height>{{ vscale(72) }}</height>
                                <font>font10</font>
                                <align>center</align>
                                <textcolor>FFFFFFFF</textcolor>
                                <label>$INFO[ListItem.Label]</label>
                            </control>
                        </control>
                        <control type="image">
                            <visible>Control.HasFocus(101)</visible>
                            <posx>0</posx>
                            <posy>0</posy>
                            <width>250</width>
                            <height>{{ vscale(367) }}</height>
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
