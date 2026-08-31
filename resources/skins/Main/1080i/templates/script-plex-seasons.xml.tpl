{% extends "default.xml.tpl" %}
{% block header_topleft %}{% endblock %}
<!-- default.xml.tpl's own header_anim only hides the header (and this screen's season-tab row inside
     it, id=205) once on.extras fires - i.e. tier 2+ (Roles/Extras/Related), not tier 1 (the season row
     itself, hub.focus>0 + Visible(500) - see group 50's own tier comment above content). The season-tab
     row should disappear as soon as the season row starts sliding up too, not one tier later - so this
     override swaps the gating condition to hub.focus>0, matching tier 1 exactly. -->
{% block header_anim %}<animation effect="slide" end="0,{{ vscale(-300) }}" time="200" tween="quadratic" easing="out" condition="Integer.IsGreater(Window.Property(hub.focus),0) + !ControlGroup(200).HasFocus(0)">Conditional</animation>{% endblock %}
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
    <animation effect="slide" end="0,{{ vscale(-300) }}" time="200" tween="quadratic" easing="out" condition="!String.IsEmpty(Window.Property(on.extras))">Conditional</animation>

    <!-- Slide right while the sidebar rail is expanded (focused), matching Home/Library/Pre-play/Episodes -->
    <animation effect="slide" end="220,0" time="200" tween="sine" easing="inout" condition="ControlGroup(9000).HasFocus(0)">Conditional</animation>

    <!-- One progressive depth scale, hub.focus 1-4 (ShowWindow.onFocus(), subitems.py: controlID-399,
         not -400, gives the season row its own tier 1 instead of colliding with the button row's own
         reset-to-'0') - each tier's own Visible() gate checks the SECTION that tier is named after, not
         the one hub.focus has just reached, so a slide only accumulates for sections that actually
         exist (e.g. a show with no roles data skips straight from tier 1 to tier 3's slide amount).
         Conditional animations that are simultaneously true stack additively (all lower tiers stay true
         once you're deeper in), so each tier's own value here is an INCREMENT on top of the tiers below
         it, not an absolute offset - e.g. the roles tier's own -115 plus the season row tier's -415
         above it reaches the same -530 total Roles always used, from back when it was the first (and
         only) tier active there; extras/related's own increments (now -428/-426 - see tier 3's own
         comment for why it grew, and the dedicated Related-compensation animation below tier 4 for a
         5th term that also had to be added) didn't need adjusting to match, since they're added on top
         of that already-corrected running total. -530 was itself
         chosen to mirror Episodes' identical slide exactly, plus the same 30px delta between the two
         screens' row+buttons wrapper heights (482 here vs Episodes' 452) - see that group's own posy
         comment below. Related (tier 4) has no Visible() gate, matching this same omission from before
         the season row got its own tier - redundant there anyway, since being focused in Related already
         proves it's visible. -->
    <animation type="Conditional" condition="Integer.IsGreater(Window.Property(hub.focus),0) + Control.IsVisible(500)" reversible="true">
        <!-- -309, not -424: reduced 115px on request (124px reduction to 300, then +9 restored to
             account for the season count label/list's own 9px drop - see this same tier's earlier
             comment history). Roles/Extras/Related's own resting positions (their cumulative totals
             -539/-899/-1325) are unchanged - only the roles tier's own increment below absorbs the
             difference, growing more negative (-115 -> -230) to keep its total at -539; extras/related's
             own increments (-360/-426) didn't need adjusting, since they're added on top of that
             already-corrected running total (additive stacking, see the block comment above). -->
        <effect type="slide" end="0,{{ vscale(-309) }}" time="200" tween="quadratic" easing="out"/>
    </animation>

    <animation type="Conditional" condition="Integer.IsGreater(Window.Property(hub.focus),1) + Control.IsVisible(501)" reversible="true">
        <effect type="slide" end="0,{{ vscale(-230) }}" time="200" tween="quadratic" easing="out"/>
    </animation>

    <animation type="Conditional" condition="Integer.IsGreater(Window.Property(hub.focus),2) + Control.IsVisible(502)" reversible="true">
        <!-- -428, not -360: increased 68px on request (extras row grew taller when its art was matched
             to Pre-play's own 512x288 recipe - see that control's own comment). This value's only job is
             correctly revealing Extras itself when hub.focus=3 - don't grow it further to compensate
             Related's own position too (that was tried and overshot Extras' own reveal - see the
             dedicated Related-compensation animation below instead, which handles that separately).
             Cumulative total below it: Extras -967 (was -899). -->
        <effect type="slide" end="0,{{ vscale(-428) }}" time="200" tween="quadratic" easing="out"/>
    </animation>

    <animation type="Conditional" condition="Integer.IsGreater(Window.Property(hub.focus),3)" reversible="true">
        <!-- -426, not -500: reduced 74px on request - this is the tier a show with no Roles/Extras data
             actually sees as its 2nd (and last) slide, right after the season row's own tier 1, since
             tiers 2/3 never fire without their own section present to gate on. -->
        <effect type="slide" end="0,{{ vscale(-426) }}" time="200" tween="quadratic" easing="out"/>
    </animation>

    <animation type="Conditional" condition="Integer.IsGreater(Window.Property(hub.focus),3) + Control.IsVisible(502)" reversible="true">
        <!-- Related-only compensation for Extras' presence, split out from tier 3 rather than folded into
             it: tier 3's -428 is tuned to correctly reveal Extras itself (hub.focus=3) - growing it
             further to also fix Related's own position (hub.focus=4) overshot Extras' own reveal (tried,
             reported live as "extras row now sits too high"). This term only fires alongside tier 4
             (Related focused) and only when Extras is actually visible, adding the extra 27px Related
             alone needs to land in the same place regardless of whether Extras exists - grouplist 60
             skips invisible children entirely, so Extras' full auto-stack footprint (height 450 + itemgap
             5 = 455) has to be accounted for somewhere, just not inside tier 3 any more. Cumulative total:
             Related -1420 (was -1325 before any of today's Extras-height changes). -->
        <effect type="slide" end="0,{{ vscale(-27) }}" time="200" tween="quadratic" easing="out"/>
    </animation>

    <!-- posx=52, not the old 60: matches Pre-play's own tuned value exactly (script-plex-pre_play.xml.tpl
         - see that control's own comment for the real-Plex-screenshot measurement behind it), so the
         content column lands at the same absolute x as Pre-play. Every child below is positioned
         relative to this group, so the shift applies uniformly - none of them (season row/buttons,
         Roles/Extras/Related, which all use their own independent posx values for unrelated reasons,
         e.g. sidebar-rail scroll clearance) needs any compensating change for this. -->
    <posx>52</posx>
    <!-- 135, not the old 155: matches Pre-play's own group 50 baseline exactly (script-plex-pre_play.xml.tpl
         - see that control's own comment) so clearlogo/metadata/rating/summary land at the same absolute
         y as Pre-play. Everything below this group that used to be positioned against the 155 baseline
         (the season-row-+-buttons group, grouplist 60) has had its own posy bumped by the same 20px so
         their absolute positions stay exactly where they were - only the header content itself moved. -->
    <posy>{{ vscale(135) }}</posy>
    <!-- 302 (the play button), not the stale 101 or the old 400 (season row) - matches Python's own
         onFirstInit(), which now stays on the play button rather than moving focus to the season row
         once it's populated - see ShowWindow.onFirstInit(). -->
    <defaultcontrol>302</defaultcontrol>

    <control type="group">
        <posx>0</posx>
        <posy>0</posy>
        <width>1920</width>
        <height>{{ vscale(600) }}</height>
        <!-- No corner poster (dropped on request to match Pre-play's own layout exactly -
             script-plex-pre_play.xml.tpl - see that file's own comment on its details block for the
             full reasoning): clearlogo/meta/rating/summary all sit at a single fixed posx=60 column
             instead of being duplicated at two x-offsets and switched by hide.poster's own <visible>. -->
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
        <!-- 722x162, matching Pre-play's own clearlogo box exactly - ShowWindow.CLEAR_LOGO_DIM
             (subitems.py) requests the transcoded clearlogo at this same size. -->
        <control type="image">
            <visible>!String.IsEmpty(Window.Property(clear.logo))</visible>
            <posx>60</posx>
            <posy>0</posy>
            <width>722</width>
            <height>{{ vscale(162) }}</height>
            <aspectratio align="left" aligny="bottom">keep</aspectratio>
            <texture background="true">$INFO[Window.Property(clear.logo)]</texture>
        </control>
        {% include "includes/pp_meta_row.xml.tpl" %}

        <!-- Ratings row: identical to Pre-play's own (script-plex-pre_play.xml.tpl) - one icon+label
             pair per rating the item actually has (populateRatings(), lib/windows/mixins/ratings.py),
             not just a critic/audience pair. rating1..rating6 must match RatingsMixin.MAX_RATINGS
             exactly - not templated from that constant, this loop's own range() has to be kept in
             sync by hand if it ever changes. -->
        <control type="grouplist">
            <visible>{% for i in range(1, 7) %}{% if i > 1 %}| {% endif %}!String.IsEmpty(Window.Property(rating{{ i }})){% endfor %}</visible>
            <posx>60</posx>
            <posy>{{ vscale(219) }}</posy>
            <width>708</width>
            <height>{{ vscale(32) }}</height>
            <align>left</align>
            <itemgap>5</itemgap>
            <orientation>horizontal</orientation>
            <usecontrolcoords>true</usecontrolcoords>
            {% for i in range(1, 7) %}
            <control type="group">
                <visible>!String.IsEmpty(Window.Property(rating{{ i }}))</visible>
                <width>91</width>
                <height>{{ vscale(32) }}</height>
                <control type="image">
                    <posx>0</posx>
                    <posy>1</posy>
                    <width>40</width>
                    <height>{{ vscale(30) }}</height>
                    <texture fallback="script.plex/ratings/other/image.rating.png">$INFO[Window.Property(rating{{ i }}.image)]</texture>
                    <aspectratio align="right">keep</aspectratio>
                </control>
                <control type="label">
                    <posx>47</posx>
                    <posy>1</posy>
                    <width>44</width>
                    <height>{{ vscale(30) }}</height>
                    <font>font8</font>
                    <align>left</align>
                    <aligny>center</aligny>
                    <textcolor>FFD2CCCE</textcolor>
                    <label>$INFO[Window.Property(rating{{ i }})]</label>
                </control>
            </control>
            {% endfor %}
            <control type="image">
                <visible>!String.IsEmpty(Window.Property(rating.stars))</visible>
                <posy>6</posy>
                <width>134</width>
                <height>{{ vscale(22) }}</height>
                <texture>script.plex/stars/$INFO[Window.Property(rating.stars)].png</texture>
            </control>
        </control>

        <!-- posx=60, not the old 376: no poster to clear any more, matching the rest of this column. -->
        {% include "includes/wl_availability.xml.tpl" with posx=60 %}
        <control type="textbox">
            <!-- Matches Pre-play's own summary box exactly - single fixed position, no more poster-
                 shown/poster-hidden slide. -->
            <posx>60</posx>
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
    </control>

    <!-- SEASON ROW + BUTTONS -->
    <!-- A plain group, not nested inside grouplist 60 below: a grouplist auto-stacks its children by
         height and doesn't reliably honor a child's own posy as extra gap (nesting the season row here
         caused it to overlap Roles instead of stacking after it) - same reasoning as Episodes' identical
         sibling-group treatment of its episode row + button row (script-plex-episodes.xml.tpl). 358, not
         the old 393: moved up 35px on request. -->
    <control type="group">
        <posx>0</posx>
        <posy>{{ vscale(358) }}</posy>
        <width>1920</width>
        <!-- 613 = 103 (season row's own posy below, see its comment) + 510 (season row's own height,
             see id 500's own comment - grown 9px to match its content's own 9px drop). -->
        <height>{{ vscale(613) }}</height>

        {% block buttons %}
            <control type="grouplist" id="300">
                <animation effect="fade" start="0" end="100" time="200" reversible="true">VisibleChange</animation>
                <visible>!String.IsEmpty(Window.Property(initialized))</visible>
                <defaultcontrol>302</defaultcontrol>
                <!-- Sits above the season row on request, not below (matching Episodes' original
                     button-row-under-carousel order, which this used to share) - a plain posy=0, no
                     pull-up hack needed since there's nothing directly above it to compensate for.
                     82, not the old 121/145: measured the actual opaque glyph content of each button
                     icon this row can show (info/play/shuffle/more/play_plus/watchlist/watchlisted,
                     180x145 native PNGs, see script.plex/buttons/player/modern/) - the widest vertical
                     extent across all of them (watchlist/watchlisted) runs y49-97 of 145 native, which
                     scales to ~41-81 at this row's 121-tall display size. usecontrolcoords means each
                     button still renders at its own full 121-tall stretch regardless of this box's own
                     height (verified nothing here relies on grouplist-level clipping - each button
                     already carries its own explicit <hitrect>), so shrinking this to 82 (the glyph's
                     own display-space bottom, +1px) only trims the empty reserved space below the
                     icons, not the icons themselves. -->
                <posx>22</posx>
                <posy>0</posy>
                <width>1000</width>
                <height>{{ vscale(82) }}</height>
                <!-- 205 or 206 first (whichever of the season-tab row's two controls is active - see
                     that block's own comment), falling back to 200 (header) when neither is visible -
                     same dual-onup fallback Episodes' own button/content controls use to reach their
                     identical tab row. -->
                <onup condition="Control.IsVisible(205)">205</onup>
                <onup condition="Control.IsVisible(206)">206</onup>
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

        <!-- Seasons -->
        <control type="group" id="500">
            <visible>Integer.IsGreater(Container(400).NumItems,0) + String.IsEmpty(Window.Property(drawing))</visible>
            <!-- 103, not 0: sits below the button row (82 tall), moved up 29px on request from the
                 102 that gave a plain 20px gap, then down 10px three more times on later requests. -->
            <posx>0</posx>
            <posy>{{ vscale(103) }}</posy>
            <!-- 510 = 45 (list's own posy below) + 465 (list's own height, see its comment). Grew 9px
                 (from 501) to match the label + list both dropping 9px on request. -->
            <height>{{ vscale(510) }}</height>
            <width>1920</width>
            <!-- "X Seasons"/"X Season", bold, font12 (bumped from font10 on request). 30, not the
                 original 21: dropped 9px on request, along with the list below it. posx=63, not 60:
                 nudged 3px right on request, matching Recommended's own row-title x (115). -->
            <control type="label">
                <posx>63</posx>
                <posy>{{ vscale(30) }}</posy>
                <width>800</width>
                <height>{{ vscale(30) }}</height>
                <font>font12</font>
                <align>left</align>
                <aligny>center</aligny>
                <!-- FFE9E6E7, midpoint between the summary text's FFD2CCCE and pure white. -->
                <textcolor>FFE9E6E7</textcolor>
                <label>[B]$INFO[Window.Property(season.count)][/B]</label>
            </control>
            <control type="list" id="400">
                <!-- posx=53, not 40: clip line moved to match Recommended's own hub-row clip edge
                     exactly (script-plex-recommended.xml.tpl's outer group, posx=105 - this list sits
                     inside group 50's own posx=52, so 53 here lands at the same absolute x=105). Width
                     shrunk to keep the local posx+width=1920 invariant (was 1880=1920-40, now
                     1867=1920-53). Item layout's own posx reduced by the same 13 below, netting out to
                     the 3px-right nudge those items also got on request (15->5, not a full cancel) - see
                     that control's own comment. -->
                <posx>53</posx>
                <!-- 45, not the original 36: dropped 9px on request, along with the label above it. -->
                <posy>{{ vscale(45) }}</posy>
                <width>1867</width>
                <!-- 465, not the old 380: sized to the item's actual content, focused state included -
                     item posy(29) + the label's own bottom edge (426, relative to the zoom-animated
                     group's origin: 3px inner padding + art 360 + 9px gap + label 54) grown by the 4%
                     focus zoom (distance from the zoom center at y180 scales by 1.04: 180 + (426-180)*1.04
                     = 435.84) = 464.84, rounded up to 465. The drop-shadow (384) and the ring-mask focus
                     indicator (366) both zoom the same way but stay well under this - the label is the
                     real tallest element, not either of those. -->
                <height>{{ vscale(465) }}</height>
                <onup>300</onup>
                <ondown>401</ondown>
                <onleft>9000</onleft>
                <!-- Hard stop, not Kodi's native wrap-to-first-item: same established idiom as the
                     Related row below and the hub rows on Recommended (script-plex-recommended.xml.tpl) -
                     a type="list" with no onright falls back to wrapping internally. -->
                <onright>noop</onright>
                <scrolltime>200</scrolltime>
                <orientation>horizontal</orientation>
                <preloaditems>4</preloaditems>
                <!-- ITEM LAYOUT ########################################## -->
                <!-- 240x360 poster, matching Related below and recommended's own hub poster rows exactly
                     (same drop-shadow/ring sizing, focus zoom, and item gap too) - grown from the old
                     158x236. Progress bar and label keep this row's own existing thin-bar/single-line
                     styling (not adopted from recommended's pill-shaped inset bar, which this row never
                     used to begin with), just repositioned/widened for the bigger poster. -->
                <itemlayout width="272">
                    <control type="group">
                        <!-- 5, not 15: nets a 3px rightward nudge against the list's own +13 clip-line
                             move above (105 vs the old 92), matching Recommended's poster edge (x=113)
                             exactly. -->
                        <posx>5</posx>
                        <posy>{{ vscale(29) }}</posy>
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
                            {% include "includes/watched_indicator.xml.tpl" with xoff=240 & wbg_w=22.3 & wbg_h=22.3 & count_zoom=28.7 & with_count=True & scale="small" %}
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
                            <control type="label">
                                <scroll>false</scroll>
                                <posx>0</posx>
                                <posy>{{ vscale(369) }}</posy>
                                <width>240</width>
                                <height>{{ vscale(30) }}</height>
                                <font>font10</font>
                                <align>center</align>
                                <textcolor>FFFFFFFF</textcolor>
                                <label>$INFO[ListItem.Label]</label>
                            </control>
                            <control type="label">
                                <scroll>false</scroll>
                                <posx>0</posx>
                                <posy>{{ vscale(399) }}</posy>
                                <width>240</width>
                                <height>{{ vscale(24) }}</height>
                                <font>font10</font>
                                <align>center</align>
                                <textcolor>AAFFFFFF</textcolor>
                                <label>$INFO[ListItem.Property(episode.count)]</label>
                            </control>
                        </control>
                    </control>
                </itemlayout>

                <!-- FOCUSED LAYOUT ####################################### -->
                <focusedlayout width="272">
                    <control type="group">
                        <!-- 5, not 15 - see the matching itemlayout's own comment above. -->
                        <posx>5</posx>
                        <posy>{{ vscale(29) }}</posy>
                        <control type="group">
                            <animation effect="zoom" start="100" end="104" time="100" center="120,{{ vscale(180) }}" reversible="false">Focus</animation>
                            <animation effect="zoom" start="104" end="100" time="100" center="120,{{ vscale(180) }}" reversible="false">UnFocus</animation>
                            <posx>0</posx>
                            <posy>0</posy>
                            <control type="image">
                                <visible>Control.HasFocus(400)</visible>
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
                                {% include "includes/watched_indicator.xml.tpl" with xoff=240 & wbg_w=22.3 & wbg_h=22.3 & count_zoom=28.7 & with_count=True & scale="small" %}
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
                                <control type="label">
                                    <scroll>Control.HasFocus(400)</scroll>
                                    <posx>0</posx>
                                    <posy>{{ vscale(369) }}</posy>
                                    <width>240</width>
                                    <height>{{ vscale(30) }}</height>
                                    <font>font10</font>
                                    <align>center</align>
                                    <textcolor>FFFFFFFF</textcolor>
                                    <label>$INFO[ListItem.Label]</label>
                                </control>
                                <control type="label">
                                    <scroll>false</scroll>
                                    <posx>0</posx>
                                    <posy>{{ vscale(399) }}</posy>
                                    <width>240</width>
                                    <height>{{ vscale(24) }}</height>
                                    <font>font10</font>
                                    <align>center</align>
                                    <textcolor>AAFFFFFF</textcolor>
                                    <label>$INFO[ListItem.Property(episode.count)]</label>
                                </control>
                            </control>
                            <!-- Ring-mask focus indicator, not the old bordered selected.png overlay -
                                 matches Related below and recommended's own poster rows. -->
                            <control type="image">
                                <visible>Control.HasFocus(400)</visible>
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
        <!-- Seasons -->
    </control>
    <!-- SEASON ROW + BUTTONS -->

    <!-- Roles/Extras/Related: supplementary info, unlike the season row and its buttons above. Stacks
         immediately at the wrapper's own bottom edge, no extra gap - matching Episodes' identical
         zero-gap transition from its button row into its own Roles/Extras/Related grouplist 60. 971 =
         358 (season-row-+-buttons group's own start, moved up 35px on request) + 613 (its height, now
         sized to the season row's actual focused-state content - see id 500's own comment - grown 30px
         total to match that row's own three 10px moves down, then a further 9px to match the season
         count label + list's own 9px drop). -->
    <control type="grouplist" id="60">
        <posx>0</posx>
        <posy>{{ vscale(971) }}</posy>
        <width>1920</width>
        <height>{{ vscale(1600) }}</height>

        <onup>400</onup>
        <!-- 5, not 0: gap between adjacent sections (Roles/Extras/Related) increased 5px on request. -->
        <itemgap>5</itemgap>

        <!-- ROLES -->
        <control type="group" id="501">
            <visible>Integer.IsGreater(Container(401).NumItems,0) + String.IsEmpty(Window.Property(drawing))</visible>
            <defaultcontrol>401</defaultcontrol>
            <width>1920</width>
            <!-- 445 = original 400 + the 45px drop applied to the label and list below, so grouplist 60's
                 auto-stack still hands Extras (502) the correct start position. -->
            <height>{{ vscale(445) }}</height>
            <control type="label">
                <!-- posx=63, not 60: nudged 3px right on request, matching the season count label. -->
                <posx>63</posx>
                <posy>{{ vscale(25) }}</posy>
                <width>1000</width>
                <height>{{ vscale(80) }}</height>
                <font>font12</font>
                <align>left</align>
                <aligny>center</aligny>
                <!-- Matches the season count label's own style: font12, bold, no shadow, no uppercase. -->
                <textcolor>FFE9E6E7</textcolor>
                <label>[B]$ADDON[script.plexmod 33609][/B]</label>
            </control>
            <control type="list" id="401">
                <!-- posx=53, not 40 (width shrunk to match): see list 400's comment above for the full
                     rationale (clip-line moved to match Recommended's own, x=105). -->
                <posx>53</posx>
                <posy>{{ vscale(45) }}</posy>
                <width>1867</width>
                <height>{{ vscale(400) }}</height>
                <onup>400</onup>
                <ondown>402</ondown>
                <onleft>9000</onleft>
                <!-- Hard stop, not Kodi's native wrap-to-first-item - see the season row's own comment. -->
                <onright>noop</onright>
                <scrolltime>200</scrolltime>
                <orientation>horizontal</orientation>
                <preloaditems>4</preloaditems>
                <!-- ITEM LAYOUT ########################################## -->
                <itemlayout width="274">
                    <control type="group">
                        <!-- 5, not 15: nets a 3px rightward nudge against the list's own +13 clip-line
                             move above - see the season row's matching comment. -->
                        <posx>5</posx>
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
                                    <textcolor>FFFFFFFF</textcolor>
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
                <focusedlayout width="274">
                    <control type="group">
                        <!-- 5, not 15 - see the matching itemlayout's own comment above. -->
                        <posx>5</posx>
                        <posy>{{ vscale(61) }}</posy>
                        <control type="group">
                            <animation effect="zoom" start="100" end="104" time="100" center="127,{{ vscale(127) }}" reversible="false">Focus</animation>
                            <animation effect="zoom" start="104" end="100" time="100" center="127,{{ vscale(127) }}" reversible="false">UnFocus</animation>
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
                                        <textcolor>FFFFFFFF</textcolor>
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
                                <!-- role-selected-thin.png, not the shared role-selected.png: a dedicated,
                                     thinner-stroke variant of that same ring texture, scoped to this row
                                     only (Pre-play/Episodes/Search/Video-player all still use the original,
                                     unaffected) - reduces the native stroke from ~6px to ~5px (of a 299px
                                     canvas) to sit closer to the poster ring's own thickness on request. -->
                                <texture>script.plex/buttons/role-selected-thin.png</texture>
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
            <!-- 450, not 360: matches Pre-play's own bump (script-plex-pre_play.xml.tpl) when its art
                 grew from 299x168 to 512x288 - grouplist 60 above auto-stacks Related (503) right after
                 this by its declared height, so this just needs to cover the taller art with a little
                 slack. The extra-type second line (on request, below the title - Pre-play doesn't have
                 one) fits inside the same 300-360 footprint Pre-play's own single-line title textbox
                 used, so no further height increase was needed for it. -->
            <height>{{ vscale(450) }}</height>
            <width>1920</width>
            <control type="label">
                <!-- posx=63, not 60: nudged 3px right on request, matching the season count label. -->
                <posx>63</posx>
                <posy>0</posy>
                <width>800</width>
                <height>{{ vscale(80) }}</height>
                <font>font12</font>
                <align>left</align>
                <aligny>center</aligny>
                <!-- Matches the season count label's own style: font12, bold, no uppercase. -->
                <textcolor>FFE9E6E7</textcolor>
                <label>[B]$INFO[Window.Property(extras.header)][/B]</label>
            </control>
            <control type="list" id="402">
                <!-- posx=53, not 40 (width shrunk to match): see list 400's comment above for the full
                     rationale (clip-line moved to match Recommended's own, x=105). -->
                <posx>53</posx>
                <posy>{{ vscale(18) }}</posy>
                <width>1867</width>
                <height>{{ vscale(430) }}</height>
                <onup>401</onup>
                <ondown>403</ondown>
                <onleft>9000</onleft>
                <!-- Hard stop, not Kodi's native wrap-to-first-item - see the season row's own comment. -->
                <onright>noop</onright>
                <scrolltime>200</scrolltime>
                <orientation>horizontal</orientation>
                <preloaditems>4</preloaditems>
                <!-- ITEM LAYOUT ########################################## -->
                <!-- Art 299x168 -> 512x288, rounded-corner ar16x9 mask, duration badge, ring-mask focus
                     indicator - matches Pre-play's own extras row exactly (script-plex-pre_play.xml.tpl)
                     on request; only the outer positioning (posx=5, the resting x=115 baseline the rest
                     of this screen's rows share) stays this screen's own, not Pre-play's. Cell width 544,
                     matching Pre-play's own value exactly (not the old extras row's 60px margin, which
                     was an outlier - this screen's other three rows all use a ~30-32px margin, and 512 +
                     that lands on the same 544 Pre-play already uses). Second line below the title is
                     the extra type (e.g. "Trailer"), back on request - Pre-play doesn't have one, relying
                     on the duration badge instead. -->
                <itemlayout width="544">
                    <control type="group">
                        <posx>5</posx>
                        <posy>{{ vscale(61) }}</posy>
                        <control type="group">
                            <posx>5</posx>
                            <posy>5</posy>
                            <control type="image">
                                <posx>0</posx>
                                <posy>0</posy>
                                <width>512</width>
                                <height>{{ vscale(288) }}</height>
                                <texture diffuse="script.plex/masks/ar16x9-mask.png">$INFO[ListItem.Property(thumb.fallback)]</texture>
                                <aspectratio scalediffuse="false">scale</aspectratio>
                            </control>
                            <control type="image">
                                <posx>0</posx>
                                <posy>0</posy>
                                <width>512</width>
                                <height>{{ vscale(288) }}</height>
                                <texture background="true" diffuse="script.plex/masks/ar16x9-mask.png">$INFO[ListItem.Thumb]</texture>
                                <aspectratio scalediffuse="false">scale</aspectratio>
                            </control>
                            <control type="group">
                                <posx>0</posx>
                                <posy>0</posy>
                                <width>512</width>
                                <height>{{ vscale(288) }}</height>
                                <control type="image">
                                    <right>10</right>
                                    <bottom>10</bottom>
                                    <width>64</width>
                                    <height>26</height>
                                    <texture>script.plex/white-square-rounded.png</texture>
                                    <colordiffuse>99000000</colordiffuse>
                                </control>
                                <control type="label">
                                    <animation effect="zoom" start="60" end="60" time="0" reversible="false" center="auto" condition="true">Conditional</animation>
                                    <right>42</right>
                                    <bottom>10</bottom>
                                    <width>auto</width>
                                    <height>26</height>
                                    <font>font32_title</font>
                                    <align>center</align>
                                    <aligny>center</aligny>
                                    <textcolor>FFEEEEEE</textcolor>
                                    <label>$INFO[ListItem.Property(extra.duration)]</label>
                                </control>
                            </control>
                            <control type="textbox">
                                <posx>0</posx>
                                <posy>{{ vscale(300) }}</posy>
                                <width>512</width>
                                <height>{{ vscale(30) }}</height>
                                <font>font10</font>
                                <align>center</align>
                                <textcolor>FFFFFFFF</textcolor>
                                <label>$INFO[ListItem.Label]</label>
                            </control>
                            <!-- Extra type (e.g. "Trailer") - back on request, same style as Roles' own
                                 second line (font10, AAFFFFFF). Title textbox above shrunk from 60 to 30
                                 (one line) so this sits right under the actual text instead of a top-
                                 aligned box's own dead space below a short title. -->
                            <control type="label">
                                <scroll>false</scroll>
                                <posx>0</posx>
                                <posy>{{ vscale(330) }}</posy>
                                <width>512</width>
                                <height>{{ vscale(30) }}</height>
                                <font>font10</font>
                                <align>center</align>
                                <textcolor>AAFFFFFF</textcolor>
                                <label>$INFO[ListItem.Label2]</label>
                            </control>
                        </control>
                    </control>
                </itemlayout>

                <!-- FOCUSED LAYOUT ####################################### -->
                <focusedlayout width="544">
                    <control type="group">
                        <posx>5</posx>
                        <posy>{{ vscale(61) }}</posy>
                        <control type="group">
                            <animation effect="zoom" start="100" end="104" time="100" center="261,{{ vscale(149) }}" reversible="false">Focus</animation>
                            <animation effect="zoom" start="104" end="100" time="100" center="261,{{ vscale(149) }}" reversible="false">UnFocus</animation>
                            <posx>0</posx>
                            <posy>0</posy>
                            <control type="image">
                                <visible>Control.HasFocus(402)</visible>
                                <posx>-40</posx>
                                <posy>{{ vscale(-40) }}</posy>
                                <width>602</width>
                                <height>{{ vscale(378) }}</height>
                                <texture border="42">script.plex/drop-shadow.png</texture>
                            </control>
                            <control type="group">
                                <posx>5</posx>
                                <posy>5</posy>
                                <control type="image">
                                    <posx>0</posx>
                                    <posy>0</posy>
                                    <width>512</width>
                                    <height>{{ vscale(288) }}</height>
                                    <texture diffuse="script.plex/masks/ar16x9-mask.png">$INFO[ListItem.Property(thumb.fallback)]</texture>
                                    <aspectratio scalediffuse="false">scale</aspectratio>
                                </control>
                                <control type="image">
                                    <posx>0</posx>
                                    <posy>0</posy>
                                    <width>512</width>
                                    <height>{{ vscale(288) }}</height>
                                    <texture background="true" diffuse="script.plex/masks/ar16x9-mask.png">$INFO[ListItem.Thumb]</texture>
                                    <aspectratio scalediffuse="false">scale</aspectratio>
                                </control>
                                <control type="group">
                                    <posx>0</posx>
                                    <posy>0</posy>
                                    <width>512</width>
                                    <height>{{ vscale(288) }}</height>
                                    <control type="image">
                                        <right>10</right>
                                        <bottom>10</bottom>
                                        <width>64</width>
                                        <height>26</height>
                                        <texture>script.plex/white-square-rounded.png</texture>
                                        <colordiffuse>99000000</colordiffuse>
                                    </control>
                                    <control type="label">
                                        <animation effect="zoom" start="60" end="60" time="0" reversible="false" center="auto" condition="true">Conditional</animation>
                                        <right>42</right>
                                        <bottom>10</bottom>
                                        <width>auto</width>
                                        <height>26</height>
                                        <font>font32_title</font>
                                        <align>center</align>
                                        <aligny>center</aligny>
                                        <textcolor>FFEEEEEE</textcolor>
                                        <label>$INFO[ListItem.Property(extra.duration)]</label>
                                    </control>
                                </control>
                                <control type="textbox">
                                    <posx>0</posx>
                                    <posy>{{ vscale(300) }}</posy>
                                    <width>512</width>
                                    <height>{{ vscale(30) }}</height>
                                    <font>font10</font>
                                    <align>center</align>
                                    <textcolor>FFFFFFFF</textcolor>
                                    <label>$INFO[ListItem.Label]</label>
                                </control>
                                <control type="label">
                                    <scroll>Control.HasFocus(402)</scroll>
                                    <posx>0</posx>
                                    <posy>{{ vscale(330) }}</posy>
                                    <width>512</width>
                                    <height>{{ vscale(30) }}</height>
                                    <font>font10</font>
                                    <align>center</align>
                                    <textcolor>AAFFFFFF</textcolor>
                                    <label>$INFO[ListItem.Label2]</label>
                                </control>
                            </control>
                            <!-- Ring-mask focus indicator, not the old bordered selected.png overlay -
                                 matches Pre-play's own extras row exactly: ring-mask-ar16x9.png diffused
                                 over white-square.png, tinted FFE9A20D, plain-stretched with no border,
                                 3px overflow past the art on every side. -->
                            <control type="image">
                                <visible>Control.HasFocus(402)</visible>
                                <posx>2</posx>
                                <posy>{{ vscale(2) }}</posy>
                                <width>518</width>
                                <height>{{ vscale(294) }}</height>
                                <texture diffuse="script.plex/masks/ring-mask-ar16x9.png">script.plex/white-square.png</texture>
                                <colordiffuse>FFE9A20D</colordiffuse>
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
                <!-- posx=63, not 60: nudged 3px right on request, matching the season count label. -->
                <posx>63</posx>
                <posy>0</posy>
                <width>1000</width>
                <height>{{ vscale(80) }}</height>
                <font>font12</font>
                <align>left</align>
                <aligny>center</aligny>
                <!-- Matches the season count label's own style: font12, bold, no uppercase. -->
                <textcolor>FFE9E6E7</textcolor>
                <label>[B]$INFO[Window.Property(related.header)][/B]</label>
            </control>
            <control type="list" id="403">
                <!-- posx=53, not 40 (width shrunk to match): see list 400's comment above for the full
                     rationale (clip-line moved to match Recommended's own, x=105). -->
                <posx>53</posx>
                <posy>{{ vscale(16) }}</posy>
                <width>1867</width>
                <height>{{ vscale(520) }}</height>
                <onup>402</onup>
                <ondown>403</ondown>
                <!-- Plain onleft to the sidebar - RelatedPaginator (pagination.py) is append-only now
                     (loaded items are never discarded/re-fetched), so there's no left-pagination boundary
                     marker to special-case any more; scrolling back left is just native list navigation
                     through items that are still there. -->
                <onleft>9000</onleft>
                <onright>noop</onright>
                <scrolltime>200</scrolltime>
                <orientation>horizontal</orientation>
                <preloaditems>4</preloaditems>
                <!-- ITEM LAYOUT ########################################## -->
                <itemlayout width="272">
                    <control type="group">
                        <!-- 5, not 15: nets a 3px rightward nudge against the list's own +13 clip-line
                             move above - see the season row's matching comment. -->
                        <posx>5</posx>
                        <posy>{{ vscale(72) }}</posy>
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
                                <posx>0</posx>
                                <posy>{{ vscale(351) }}</posy>
                                <control type="image">
                                    <posx>0</posx>
                                    <posy>0</posy>
                                    <width>240</width>
                                    <height>{{ vscale(10) }}</height>
                                    <texture>script.plex/white-square.png</texture>
                                    <colordiffuse>C0000000</colordiffuse>
                                </control>
                                <control type="image">
                                    <posx>0</posx>
                                    <posy>1</posy>
                                    <width>240</width>
                                    <height>{{ vscale(8) }}</height>
                                    <texture>$INFO[ListItem.Property(progress)]</texture>
                                    <colordiffuse>FFCC7B19</colordiffuse>
                                </control>
                            </control>
                            {% include "includes/watched_indicator.xml.tpl" with xoff=240 & uw_size=48 & wbg_w=34.4 & wbg_h=34.4 & with_count=True & scale="medium" %}
                            <control type="label">
                                <scroll>false</scroll>
                                <posx>0</posx>
                                <posy>{{ vscale(369) }}</posy>
                                <width>240</width>
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
                                    <width>240</width>
                                    <height>{{ vscale(360) }}</height>
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
                <focusedlayout width="272">
                    <control type="group">
                        <!-- 5, not 15 - see the matching itemlayout's own comment above. -->
                        <posx>5</posx>
                        <posy>{{ vscale(72) }}</posy>
                        <control type="group">
                            <animation effect="zoom" start="100" end="104" time="100" center="120,{{ vscale(180) }}" reversible="false">Focus</animation>
                            <animation effect="zoom" start="104" end="100" time="100" center="120,{{ vscale(180) }}" reversible="false">UnFocus</animation>
                            <posx>0</posx>
                            <posy>0</posy>
                            <control type="image">
                                <visible>Control.HasFocus(403)</visible>
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
                                    <posx>0</posx>
                                    <posy>{{ vscale(351) }}</posy>
                                    <control type="image">
                                        <posx>0</posx>
                                        <posy>0</posy>
                                        <width>240</width>
                                        <height>{{ vscale(10) }}</height>
                                        <texture>script.plex/white-square.png</texture>
                                        <colordiffuse>C0000000</colordiffuse>
                                    </control>
                                    <control type="image">
                                        <posx>0</posx>
                                        <posy>1</posy>
                                        <width>240</width>
                                        <height>{{ vscale(8) }}</height>
                                        <texture>$INFO[ListItem.Property(progress)]</texture>
                                        <colordiffuse>FFCC7B19</colordiffuse>
                                    </control>
                                </control>
                                {% include "includes/watched_indicator.xml.tpl" with xoff=240 & uw_size=48 & wbg_w=34.4 & wbg_h=34.4 & with_count=True & scale="medium" %}
                                <control type="label">
                                    <scroll>Control.HasFocus(403)</scroll>
                                    <posx>0</posx>
                                    <posy>{{ vscale(369) }}</posy>
                                    <width>240</width>
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
                                <width>246</width>
                                <height>{{ vscale(366) }}</height>
                                <texture diffuse="script.plex/masks/ring-mask-poster.png">script.plex/white-square.png</texture>
                                <colordiffuse>FFE9A20D</colordiffuse>
                            </control>
                            <control type="group">
                                <visible>!String.IsEmpty(ListItem.Property(is.boundary))</visible>
                                <control type="image">
                                    <posx>0</posx>
                                    <posy>0</posy>
                                    <width>240</width>
                                    <height>{{ vscale(360) }}</height>
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

{% block header_audiowidget_onleft %}<onleft condition="Control.IsVisible(205)">205</onleft><onleft condition="Control.IsVisible(206)">206</onleft><onleft>9000</onleft>{% endblock %}

{% block header_middle_add %}
<!-- SEASON TABS -->
<!-- "Show" (pinned, id-less/no dataSource, always the 'current'-underlined tab - see fillSeasonTabs(),
     subitems.py) followed by every real season, mirroring Episodes' own season-tab row
     (script-plex-episodes.xml.tpl) one level up: from here each tab actually opens that season's
     Episodes window (seasonTabClicked(), subitems.py), where the same row reappears with that season's
     own tab underlined instead. A plain type="list", not that file's fixedlist center-pinned carousel -
     same reasoning as includes/section_tabs.xml.tpl's own choice: "Show" has to stay pinned at the
     visible left edge, which a center-focus carousel can't guarantee once several seasons scroll under
     it. posx=115 matches the row/label/art baseline shared with the rest of this screen (season row,
     roles, extras, related - all absolute x=115) and Recommended's own hub rows.
     width=1425 (115 + 1425 = 1540) fills the rest of the header out to the same right boundary Episodes
     itself stops at - 20px shy of the audio widget's collapsed hitbox at 1920-360=1560 (see
     header_audiowidget_onleft above, copied from Episodes' identical override). -->
<control type="fixedlist" id="205">
    <!-- Used once there are more than 6 seasons (7+ tabs including "Show") - below that, sibling
         control 206 (a plain type="list") takes over instead; fillSeasonTabs() (subitems.py) decides
         which of the two gets the items and always leaves the other empty so its own <visible> below
         keeps it hidden. Why the split: Kodi's fixedlist computes each item's on-screen slot from its
         distance to BOTH ends of the list, not just the start - once total items <= itemsPerPage (~7
         at this cell width), that end-of-list snapping pushes item 0 away from x=0 instead of resting
         flush left, making a short row look shifted right/centered. A plain list has no such quirk
         (it only starts scrolling once genuinely necessary), but it also can't do the "start scrolling
         before you strictly have to" behavior focusposition/movement give below - which only matters
         once there are enough tabs to fill the row, i.e. exactly the >6 case this control now handles.
         focusposition=3 makes items 0-3 (Show + 3 seasons) render at their own natural, unscrolled
         positions - Kodi's fixedlist offset is max(0, selectedIndex - focusposition), which is 0 for
         any selected index <= 3 - and starts scrolling exactly once focus reaches index 4 (the 5th
         item), on request. -->
    <visible>Integer.IsGreater(Container(205).NumItems,0)</visible>
    <animation effect="slide" end="220,0" time="200" tween="sine" easing="inout" condition="ControlGroup(9000).HasFocus(0)">Conditional</animation>
    <posx>115</posx>
    <posy>0</posy>
    <width>1425</width>
    <height>{{ vscale(135) }}</height>
    <focusposition>3</focusposition>
    <!-- Without this, Kodi pins the focused item at the focusposition slot from the very first item
         (per Kodi's own documented fixedlist behavior - "if not specified, the list will scroll
         immediately"), leaving blank space to its left instead of a tab sitting flush at x=115 - see
         includes/sidebar.xml.tpl's own focusposition+movement pair for the precedent. Live-verified at
         cell width 170 (movement=4). At 200, itemsPerPage=floor(1425/200)=7, so movement is capped at
         3 (itemsPerPage-1-focusposition) - sidebar.xml.tpl's own comment on maxCursor=min(focusposition+
         movement,itemsPerPage): movement=4 here would put maxCursor at 7, one past the last valid slot
         (6), pinning an item's cursor outside the clip rect the same way that file warns about. -->
    <movement>3</movement>
    <preloaditems>4</preloaditems>
    <onup>200</onup>
    <onleft>9000</onleft>
    <!-- Past the last tab, focus should reach the audio widget (204) same as every other row on this
         header, not dead-end at noop - previously missing here (Episodes' own copy already had it). -->
    <onright condition="Control.IsVisible(204)">204</onright>
    <onright>noop</onright>
    <ondown>300</ondown>
    <orientation>horizontal</orientation>
    <!-- ITEM LAYOUT ########################################## -->
    <!-- 200, not 170: cell widened again on request (7 tabs visible instead of ~8.4). Label 170 (200-30,
         same 30px total side margin as before) and underline 120 (25px margin each side of the label,
         unchanged) - both scaled to match, same as the earlier 170/160 tightenings. -->
    <itemlayout width="200" height="{{ vscale(135) }}">
        <control type="label">
            <posx>0</posx>
            <posy>0</posy>
            <width>170</width>
            <height>{{ vscale(135) }}</height>
            <font>font10</font>
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
    <!-- Split into two Control.HasFocus(205)-gated labels, same reasoning as Episodes' own tab row:
         without it, whichever item holds the list's internal cursor renders "focused" white even when
         real window focus sits elsewhere (e.g. the play button). -->
    <focusedlayout width="200" height="{{ vscale(135) }}">
        <control type="label">
            <visible>Control.HasFocus(205)</visible>
            <posx>0</posx>
            <posy>0</posy>
            <width>170</width>
            <height>{{ vscale(135) }}</height>
            <font>font10</font>
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
            <font>font10</font>
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

<control type="list" id="206">
    <!-- Plain-list twin of 205 for <=6 seasons (<=7 tabs) - see 205's own comment above for why. No
         focusposition/movement/preloaditems: a plain list already renders every item at its natural
         position and only scrolls if focus would otherwise leave the visible width, which never
         happens at this item count. -->
    <visible>Integer.IsGreater(Container(206).NumItems,0)</visible>
    <animation effect="slide" end="220,0" time="200" tween="sine" easing="inout" condition="ControlGroup(9000).HasFocus(0)">Conditional</animation>
    <posx>115</posx>
    <posy>0</posy>
    <width>1425</width>
    <height>{{ vscale(135) }}</height>
    <onup>200</onup>
    <onleft>9000</onleft>
    <onright condition="Control.IsVisible(204)">204</onright>
    <onright>noop</onright>
    <ondown>300</ondown>
    <orientation>horizontal</orientation>
    <itemlayout width="200" height="{{ vscale(135) }}">
        <control type="label">
            <posx>0</posx>
            <posy>0</posy>
            <width>170</width>
            <height>{{ vscale(135) }}</height>
            <font>font10</font>
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
    <focusedlayout width="200" height="{{ vscale(135) }}">
        <control type="label">
            <visible>Control.HasFocus(206)</visible>
            <posx>0</posx>
            <posy>0</posy>
            <width>170</width>
            <height>{{ vscale(135) }}</height>
            <font>font10</font>
            <align>center</align>
            <aligny>center</aligny>
            <scroll>true</scroll>
            <scrollspeed>25</scrollspeed>
            <textcolor>FFFFFFFF</textcolor>
            <label>$INFO[ListItem.Label]</label>
        </control>
        <control type="label">
            <visible>!Control.HasFocus(206)</visible>
            <posx>0</posx>
            <posy>0</posy>
            <width>170</width>
            <height>{{ vscale(135) }}</height>
            <font>font10</font>
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
{% endblock %}