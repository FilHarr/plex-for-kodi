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
    <!-- -95, not -300: the base offset for the hub-row ladder. With the tiers below it puts every hub
         heading box on y=301 and the season count label on y=326 - that label is 30px with
         aligny=center against the headings' 80px, so 326+15 and 301+40 put both texts on the same
         centre line (341). Pre-play and Artist land on 301 too. The header's own -300 (block
         header_anim above) is separate and stays - it only has to clear a 135px header. -->
    <animation effect="slide" end="0,{{ vscale(-95) }}" time="200" tween="quadratic" easing="out" condition="!String.IsEmpty(Window.Property(on.extras))">Conditional</animation>

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
        <!-- -300 places the season row's own label: its rest y is 626 (group 50's 135 + the wrapper's 358 +
             group 500's 103 + the label's 30), and 626 - 300 = 326. -->
        <effect type="slide" end="0,{{ vscale(-300) }}" time="200" tween="quadratic" easing="out"/>
    </animation>

    <animation type="Conditional" condition="Integer.IsGreater(Window.Property(hub.focus),1) + Control.IsVisible(501)" reversible="true">
        <!-- -410 = Roles' own footprint (405 + grouplist 60's itemgap 5). Gated on Roles, so a show with no
             cast skips it and Extras still lands on 301. -->
        <effect type="slide" end="0,{{ vscale(-410) }}" time="200" tween="quadratic" easing="out"/>
    </animation>

    <animation type="Conditional" condition="Integer.IsGreater(Window.Property(hub.focus),2) + Control.IsVisible(502)" reversible="true">
        <!-- -410 = Roles' footprint again; this is the tier that brings Extras up past Roles. -->
        <effect type="slide" end="0,{{ vscale(-410) }}" time="200" tween="quadratic" easing="out"/>
    </animation>

    <animation type="Conditional" condition="Integer.IsGreater(Window.Property(hub.focus),3)" reversible="true">
        <!-- -410 = Roles' footprint. Ungated, so it fires for Related whether or not Extras exists; the
             gated companion below adds the remainder when Extras IS present. -->
        <effect type="slide" end="0,{{ vscale(-410) }}" time="200" tween="quadratic" easing="out"/>
    </animation>

    <animation type="Conditional" condition="Integer.IsGreater(Window.Property(hub.focus),3) + Control.IsVisible(502)" reversible="true">
        <!-- -48 completes Extras' own 458 footprint (410 from the ungated tier above plus 48 here), and only
             when Extras is actually visible. -->
        <effect type="slide" end="0,{{ vscale(-48) }}" time="200" tween="quadratic" easing="out"/>
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
             full reasoning): clearlogo/meta/rating/summary all sit at a single fixed posx=61 column
             (absolute x=113, matching Episodes'/Pre-play's own shared baseline - see
             script-plex-episodes.xml.tpl's header block comment) instead of being duplicated at two
             x-offsets and switched by hide.poster's own <visible>. -->
        <control type="label">
            <!-- font45_title, not font45; height=61, not the old 109 (on request, matching Artist's
                 own title control - script-plex-artist.xml.tpl). posy=48, not 0: aligny=bottom
                 anchors text to the box's own BOTTOM edge, so shrinking height by 48px (109-61) while
                 leaving posy alone would have pulled the text up 48px and left dead space below it,
                 between the new bottom edge and the metadata row underneath (tuned against the old
                 109-tall box's own bottom) - moving posy down by that same 48px keeps the bottom
                 edge (and the text anchored to it) exactly where it was. width=660, not the old 616
                 (on request, matching Episodes' own copy of this control). -->
            <visible>String.IsEmpty(Window.Property(clear.logo))</visible>
            <posx>61</posx>
            <posy>{{ vscale(48) }}</posy>
            <width>660</width>
            <height>{{ vscale(61) }}</height>
            <font>font45_title</font>
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
            <posx>61</posx>
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
            <posx>61</posx>
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

        <!-- posx=61, not the old 376: no poster to clear any more, matching the rest of this column. -->
        {% include "includes/wl_availability.xml.tpl" with posx=61 %}
        <control type="textbox">
            <!-- Matches Pre-play's own summary box exactly - single fixed position, no more poster-
                 shown/poster-hidden slide. -->
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
             and positioned to match it exactly, wired to summaryButtonClicked() (SUMMARY_BUTTON_ID,
             subitems.py) - same recipe as Artist's own copy (script-plex-artist.xml.tpl), which this
             was ported from. Blank label (matches themed_button.xml.tpl's own convention) so nothing
             draws over the textbox's real text. texturenofocus/texturefocus both "-" (explicit none,
             not just omitted - Kodi otherwise falls back to its own default button look) - the focus
             highlight itself is the separate image below instead, not this control's own texture, so
             it can be sized bigger than the actual hit area. -->
        <control type="button" id="305">
            <posx>61</posx>
            <posy>{{ vscale(277) }}</posy>
            <width>813</width>
            <height>{{ vscale(90) }}</height>
            <onup condition="Control.IsVisible(205)">205</onup>
            <onup condition="Control.IsVisible(206)">206</onup>
            <onup>200</onup>
            <ondown>300</ondown>
            <onleft>9000</onleft>
            <label> </label>
            <texturenofocus>-</texturenofocus>
            <texturefocus>-</texturefocus>
        </control>
        <!-- Focus highlight for 305 above, kept as its own image rather than that button's own
             texturefocus so it can extend 5px past the button's own hit area on every side, matching
             Artist's own copy. -->
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
                     button-row-under-carousel order, which this used to share).
                     63, not the old 22: the button icons were re-cropped from an 180x145 padded canvas
                     down to a tight 80x80 one (see context.py's own comment on the 70x70/itemgap-0 box
                     re-tune), shrinking the box from 152x121 to 70x70 - old absolute glyph center-x was
                     52(group 50's own posx, matches pre_play's own tuned value)+22+76.4(play.png's
                     opaque center, scaled into the old 152-wide box)=150.4; the outer offset (52)
                     cancels out of the equation, so the new posx is just
                     22+76.4-35.44(same glyph center, scaled into the new 70-wide box)=62.96.
                     25, not the old plain 0: the glyph is roughly vertically centered within its own
                     box on both the old and new icon crops (see context.py's own comment), so shrinking
                     the box from a fixed top edge (posy) pulls the centered glyph upward with it, same
                     as it does for Episodes'/PrePlay's own button rows (their own posy comments derive
                     +25 too) - this row's old 0 never had that compensation baked in only because there
                     was nothing else it needed to line up against, not because the icon crop doesn't
                     affect it the same way. Live-confirmed: leaving this at 0 (even after reverting the
                     height below back to a generous, non-trimming value) still left the row sitting
                     visibly too high - height was a red herring, this was the actual cause.
                     145, not 82: kept as the generous, non-trimming box Episodes'/PrePlay's own button
                     rows already use (200/145, both already much bigger than any button's own 70-tall
                     render) rather than the old tight trim (82, later 58) - unrelated to the posy fix
                     above, just not worth re-attempting now that the actual cause is understood. -->
                <posx>63</posx>
                <posy>{{ vscale(25) }}</posy>
                <width>1000</width>
                <height>{{ vscale(145) }}</height>
                <!-- 305 (the summary click-target), not straight to 205/206/200: keeps that focus
                     stop reachable from the button row via remote/keyboard, not just mouse/touch -
                     same reasoning as Artist's own copy. The season-tab row fallback (205/206/200)
                     this used to carry directly has moved up onto 305's own onup instead, one level
                     further up the chain. -->
                <onup>305</onup>
                <ondown>400</ondown>
                <onleft>9000</onleft>
                <itemgap>{{ theme.seasons.buttongroup.itemgap }}</itemgap>
                <orientation>horizontal</orientation>
                <scrolltime tween="quadratic" easing="out">200</scrolltime>
                <usecontrolcoords>true</usecontrolcoords>

                {% with attr = theme.seasons.buttons & template = "includes/themed_button.xml.tpl" & hitrect = theme.seasons.buttons_hitrect & ol = "includes/episode_button_label.xml.tpl" %}
                    <!-- Info dropped entirely (on request) - this row has no per-episode/per-item
                         detail to show one for, unlike Episodes' own copy. Label-on-focus overlays
                         for the rest, same mechanism/geometry as Episodes' button row (icon box
                         size/itemgap match exactly - theme.seasons.buttons in context.py mirrors
                         theme.episodes.buttons) - shared include, not a seasons-specific copy. -->
                    <!-- Real buttons below keep their original bare includes (no onleft/onright) -
                         this row never had explicit nav overrides between them the way Episodes'
                         own row does, and the watchlist dynamic-button cluster right after Play
                         (wl_dynamic_buttons.xml.tpl - multiple mutually-exclusive states this
                         doesn't touch/fully model) makes guessing a single correct onright target
                         for Play itself too risky to add here. Only the new overlays get explicit
                         onleft/onright (mirroring their own button's id, same defensive pattern
                         Episodes' button row already relies on) - that's the part live-confirmed
                         necessary there. -->
                    <!-- Play / Resume are the same action here (playButtonClicked(), subitems.py -
                         the show-level pick resumes by itself when the episode it lands on is
                         in progress); only the icon and label differ, and a button's own textures
                         can't be swapped on a condition, so it's two mutually-exclusive buttons.
                         play.in.progress/play.episode/resume.timeleft come from
                         ShowWindow.setPlayButtonState() - see there for why the label can be
                         specific about the episode at all, and when it can't.
                         Both overlays carry pill/label ids because their text isn't fixed at build
                         time: the episode number's digit count varies ("Play S1E1" measures 111px,
                         "Play S12E345" 155px), so the widths below are the worst case and
                         setPlayButtonState() shrinks the three controls to the real string.
                         Resume's own worst case is "Resume S12E345 &#8226; 1h31m left" = 346
                         measured (InterUI.ttf at font10); it was 290 until 2026-09-11, which is a
                         typical string ("Resume S5E14 &#8226; 41m left"), not a worst case. Only
                         ever visible if the resize doesn't land (its own except path), but a
                         too-small start clips where a too-large one just reads roomy. -->
                    {% include template with name="play" & id=302 &
                        visible="String.IsEmpty(Window.Property(disable_playback)) + String.IsEmpty(Window.Property(play.in.progress))"
                    %}
                    {% include ol with id=391 & visible="Control.HasFocus(302)" & name="play" &
                        label="$ADDON[script.plexmod 33020] $INFO[Window.Property(play.episode)]" & label_suffix_info="" &
                        label_width=160 & pill_width=222 & group_width=178 &
                        pill_id=396 & label_id=397 &
                        onleft=302 & onright=308
                    %}
                    {% include template with name="resume" & id=301 &
                        visible="String.IsEmpty(Window.Property(disable_playback)) + !String.IsEmpty(Window.Property(play.in.progress))"
                    %}
                    {% include ol with id=398 & visible="Control.HasFocus(301)" & name="resume" &
                        label="$ADDON[script.plexmod 32316] $INFO[Window.Property(play.episode)]" &
                        label_suffix_wprop="resume.timeleft" &
                        label_width=346 & pill_width=408 & group_width=364 &
                        pill_id=399 & label_id=307 &
                        onleft=301 & onright=308
                    %}
                    {% include "includes/wl_dynamic_buttons.xml.tpl" %}
                    {% include "includes/wl_add_remove_buttons.xml.tpl" %}
                    {% include ol with id=392 & visible="Control.HasFocus(308)" & name="watchlist" &
                        label="$ADDON[script.plexmod 35062]" & label_suffix_info="" &
                        label_width=180 & pill_width=242 & group_width=198 &
                        onleft=308 & onright=309
                    %}
                    {% include ol with id=393 & visible="Control.HasFocus(309)" & name="watchlisted" &
                        label="$ADDON[script.plexmod 34011]" & label_suffix_info="" &
                        label_width=251 & pill_width=313 & group_width=269 &
                        onleft=309 & onright=303
                    %}
                    {% include template with name="shuffle" & id=303 &
                        visible="String.IsEmpty(Window.Property(disable_playback))"
                    %}
                    {% include ol with id=394 & visible="Control.HasFocus(303)" & name="shuffle" &
                        label="$ADDON[script.plexmod 32935]" & label_suffix_info="" &
                        label_width=84 & pill_width=146 & group_width=102 &
                        onleft=303 & onright=304
                    %}
                    {% include template with name="more" & id=304 &
                        visible="String.IsEmpty(Window.Property(disable_playback))"
                    %}
                    {% include ol with id=395 & visible="Control.HasFocus(304)" & name="more" &
                        label="$ADDON[script.plexmod 32307]" & label_suffix_info="" &
                        label_width=60 & pill_width=122 & group_width=78 &
                        onleft=304 & onright=""
                    %}
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
                            <animation effect="zoom" start="100" end="104" time="100" center="123,{{ vscale(183) }}" reversible="false">Focus</animation>
                            <animation effect="zoom" start="104" end="100" time="100" center="123,{{ vscale(183) }}" reversible="false">UnFocus</animation>
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
    <!-- SHARED HUB-ROW RECIPE - every row in this grouplist is built to the same geometry, and so
         are the hub rows on the other three screens (Seasons/Episodes/Pre-play/Artist). Change it
         in all four together, not per row:
             heading label          1000x80 at posy 0, posx = 113 - group 50's own posx
                                    (61 here on Seasons/Pre-play/Artist, 53 on Episodes, whose
                                    group 50 sits 8px further right) -> absolute x=113 everywhere
             heading -> art         6                           -> art top is always 86
             art -> caption         9
             caption block          60 (two 30px font10 lines, the second one optional)
             caption -> row bottom  10, plus this grouplist's own itemgap 5 = a 15px row gap
             row height             86 + art_h + 9 + 60 + 10  =  art_h + 165
             list posy              22  (= 86 - the itemlayout's own 61 - the inner group's own 3)
             list posx              113 - group 50's own posx - 8 (the item's own 5 + 3 left margin)
             card                   shadow box = art + 24 at (0,0), art inset (3,3),
                                    ring = art + 6 at (0,0)
         The card part is the same recipe the home hubs and every library grid already use
         (includes/hub_itemlayout_*.xml.tpl): drop-shadow-directional.png at border=24, a real cast
         shadow with zero alpha along its top and left edge. The circular Roles card is the one that
         can't use a rounded-rect texture, so it fills the identical box with
         role-shadow-directional.png (a disc built to the same measured falloff), plain stretch.
         Rows with no caption slot - Pre-play's Reviews, Artist's Popular Tracks - use
         86 + content height + 10 for their row height instead. -->
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
            <!-- 405 = 86 + art 240 + 9 + caption 60 + 10 - see the SHARED HUB-ROW RECIPE at grouplist 60 above. The old 445
                 carried a 45px drop on this row's own label and list; both now sit on the shared
                 recipe instead, so the extra height went with them. -->
            <height>{{ vscale(405) }}</height>
            <control type="label">
                <!-- posx=61, not 60: lands at absolute x=113 (group 50's own posx=52 + this 61), matching
                     the page-wide baseline (see the list's own comment below and
                     script-plex-episodes.xml.tpl's header block comment), not this row's own old raw
                     x=115. -->
                <posx>61</posx>
                <posy>0</posy>
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
                <!-- 53 = 113 - group 50's own posx=52 - the itemlayout's own 5+3 left margin, so the
                     art lands on the page-wide x=113 baseline and the clip edge on x=105 - see the SHARED HUB-ROW RECIPE at grouplist 60 above. -->
                <posx>53</posx>
                <posy>{{ vscale(22) }}</posy>
                <width>1867</width>
                <height>{{ vscale(380) }}</height>
                <onup>400</onup>
                <ondown>402</ondown>
                <onleft>9000</onleft>
                <!-- Hard stop, not Kodi's native wrap-to-first-item - see the season row's own comment. -->
                <onright>noop</onright>
                <scrolltime>200</scrolltime>
                <orientation>horizontal</orientation>
                <preloaditems>4</preloaditems>
                <!-- ITEM LAYOUT ########################################## -->
                <itemlayout width="270">
                    <control type="group">
                        <!-- 5, not 15: nets a 3px rightward nudge against the list's own +13 clip-line
                             move above - see the season row's matching comment. -->
                        <posx>5</posx>
                        <posy>{{ vscale(61) }}</posy>
                        <!-- Resting shadow, ungated: matches the poster rows, the home hubs and every library
                             grid, where an unfocused card still sits on its own shadow. The focusedlayout draws
                             the same box gated on Control.HasFocus, so the focused card keeps its own. -->
                        <control type="image">
                            <posx>0</posx>
                            <posy>0</posy>
                            <width>264</width>
                            <height>{{ vscale(264) }}</height>
                            <texture>script.plex/buttons/role-shadow-directional.png</texture>
                        </control>
                        <control type="group">
                            <posx>3</posx>
                            <posy>3</posy>
                            <control type="image">
                                <posx>0</posx>
                                <posy>0</posy>
                                <width>240</width>
                                <height>{{ vscale(240) }}</height>
                                <texture diffuse="script.plex/masks/role.png">script.plex/thumb_fallbacks/role.png</texture>
                            </control>
                            <control type="image">
                                <posx>0</posx>
                                <posy>0</posy>
                                <width>240</width>
                                <height>{{ vscale(240) }}</height>
                                <texture background="true" diffuse="script.plex/masks/role.png">$INFO[ListItem.Thumb]</texture>
                                <aspectratio scalediffuse="false" aligny="top">scale</aspectratio>
                            </control>
                            <control type="group">
                                <posx>0</posx>
                                <posy>{{ vscale(249) }}</posy>
                                <control type="label">
                                    <scroll>false</scroll>
                                    <posx>0</posx>
                                    <posy>0</posy>
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
                                    <posy>{{ vscale(30) }}</posy>
                                    <width>240</width>
                                    <height>{{ vscale(30) }}</height>
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
                <focusedlayout width="270">
                    <control type="group">
                        <!-- 5, not 15 - see the matching itemlayout's own comment above. -->
                        <posx>5</posx>
                        <posy>{{ vscale(61) }}</posy>
                        <control type="group">
                            <animation effect="zoom" start="100" end="104" time="100" center="123,{{ vscale(123) }}" reversible="false">Focus</animation>
                            <animation effect="zoom" start="104" end="100" time="100" center="123,{{ vscale(123) }}" reversible="false">UnFocus</animation>
                            <posx>0</posx>
                            <posy>0</posy>
                            <control type="image">
                                <!-- Ungated, unlike the focus ring below it: f10d4074 established that
                                     gating a card's drop shadow on Control.HasFocus makes the selected
                                     card the only one on screen without a shadow the moment focus leaves
                                     the list for the button row, sidebar or scrubber - and the shadow
                                     visibly pops back in as Kodi settles the layout. The itemlayout draws
                                     this same box unconditionally, so this one matches it. -->
                                <posx>0</posx>
                                <posy>0</posy>
                                <width>264</width>
                                <height>{{ vscale(264) }}</height>
                                <texture>script.plex/buttons/role-shadow-directional.png</texture>
                            </control>
                            <control type="group">
                                <posx>3</posx>
                                <posy>3</posy>
                                <control type="image">
                                    <posx>0</posx>
                                    <posy>0</posy>
                                    <width>240</width>
                                    <height>{{ vscale(240) }}</height>
                                    <texture diffuse="script.plex/masks/role.png">script.plex/thumb_fallbacks/role.png</texture>
                                </control>
                                <control type="image">
                                    <posx>0</posx>
                                    <posy>0</posy>
                                    <width>240</width>
                                    <height>{{ vscale(240) }}</height>
                                    <texture background="true" diffuse="script.plex/masks/role.png">$INFO[ListItem.Thumb]</texture>
                                    <aspectratio scalediffuse="false" aligny="top">scale</aspectratio>
                                </control>
                                <control type="group">
                                    <posx>0</posx>
                                    <posy>{{ vscale(249) }}</posy>
                                    <control type="label">
                                        <scroll>Control.HasFocus(401)</scroll>
                                        <posx>0</posx>
                                        <posy>0</posy>
                                        <width>240</width>
                                        <height>{{ vscale(30) }}</height>
                                        <font>font10</font>
                                        <align>center</align>
                                        <textcolor>FFFFFFFF</textcolor>
                                        <label>$INFO[ListItem.Label]</label>
                                    </control>
                                    <control type="label">
                                        <scroll>Control.HasFocus(401)</scroll>
                                        <posx>0</posx>
                                        <posy>{{ vscale(30) }}</posy>
                                        <width>240</width>
                                        <height>{{ vscale(30) }}</height>
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
                                <width>246</width>
                                <height>{{ vscale(246) }}</height>
                                <!-- role-selected-thin.png, not the shared role-selected.png: a dedicated,
                                     thinner-stroke variant of that same ring texture - reduces the native
                                     stroke from ~6px to ~5px (of a 299px canvas) to sit closer to the
                                     poster ring's own thickness on request. Episodes' own Roles row
                                     (script-plex-episodes.xml.tpl) and Pre-play's own (script-plex-pre_play.xml.tpl,
                                     2026-09-04) both since matched this too, on request each time - Search/
                                     Video-player still use the original role-selected.png, unaffected. -->
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
            <height>{{ vscale(453) }}</height>
            <width>1920</width>
            <control type="label">
                <!-- posx=61, not 60: lands at absolute x=113, matching the page-wide baseline - see the
                     Roles label's own comment above. -->
                <posx>61</posx>
                <posy>0</posy>
                <width>1000</width>
                <height>{{ vscale(80) }}</height>
                <font>font12</font>
                <align>left</align>
                <aligny>center</aligny>
                <!-- Matches the season count label's own style: font12, bold, no uppercase. -->
                <textcolor>FFE9E6E7</textcolor>
                <label>[B]$INFO[Window.Property(extras.header)][/B]</label>
            </control>
            <control type="list" id="402">
                <!-- 53: same derivation as the Roles list above - see the SHARED HUB-ROW RECIPE at grouplist 60 above. -->
                <posx>53</posx>
                <posy>{{ vscale(22) }}</posy>
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
                        <!-- Resting shadow, ungated: matches the poster rows, the home hubs and every library
                             grid, where an unfocused card still sits on its own shadow. The focusedlayout draws
                             the same box gated on Control.HasFocus, so the focused card keeps its own. -->
                        <control type="image">
                            <posx>0</posx>
                            <posy>0</posy>
                            <width>536</width>
                            <height>{{ vscale(312) }}</height>
                            <texture border="24">script.plex/drop-shadow-directional.png</texture>
                        </control>
                        <control type="group">
                            <posx>3</posx>
                            <posy>3</posy>
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
                                <posy>{{ vscale(297) }}</posy>
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
                                <posy>{{ vscale(327) }}</posy>
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
                            <animation effect="zoom" start="100" end="104" time="100" center="259,{{ vscale(147) }}" reversible="false">Focus</animation>
                            <animation effect="zoom" start="104" end="100" time="100" center="259,{{ vscale(147) }}" reversible="false">UnFocus</animation>
                            <posx>0</posx>
                            <posy>0</posy>
                            <control type="image">
                                <!-- Ungated, unlike the focus ring below it: f10d4074 established that
                                     gating a card's drop shadow on Control.HasFocus makes the selected
                                     card the only one on screen without a shadow the moment focus leaves
                                     the list for the button row, sidebar or scrubber - and the shadow
                                     visibly pops back in as Kodi settles the layout. The itemlayout draws
                                     this same box unconditionally, so this one matches it. -->
                                <posx>0</posx>
                                <posy>0</posy>
                                <width>536</width>
                                <height>{{ vscale(312) }}</height>
                                <texture border="24">script.plex/drop-shadow-directional.png</texture>
                            </control>
                            <control type="group">
                                <posx>3</posx>
                                <posy>3</posy>
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
                                    <posy>{{ vscale(297) }}</posy>
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
                                    <posy>{{ vscale(327) }}</posy>
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
                                <posx>0</posx>
                                <posy>0</posy>
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
            <height>{{ vscale(525) }}</height>
            <control type="label">
                <!-- posx=61, not 63: the shared hub-row heading column, landing at absolute x=113 like
                     every other row on all four screens. -->
                <posx>61</posx>
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
                <posy>{{ vscale(22) }}</posy>
                <width>1867</width>
                <height>{{ vscale(500) }}</height>
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
                        <posy>{{ vscale(61) }}</posy>
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
                                <height>{{ vscale(30) }}</height>
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
                        <posy>{{ vscale(61) }}</posy>
                        <control type="group">
                            <animation effect="zoom" start="100" end="104" time="100" center="123,{{ vscale(183) }}" reversible="false">Focus</animation>
                            <animation effect="zoom" start="104" end="100" time="100" center="123,{{ vscale(183) }}" reversible="false">UnFocus</animation>
                            <posx>0</posx>
                            <posy>0</posy>
                            <control type="image">
                                <!-- Ungated, unlike the focus ring below it: f10d4074 established that
                                     gating a card's drop shadow on Control.HasFocus makes the selected
                                     card the only one on screen without a shadow the moment focus leaves
                                     the list for the button row, sidebar or scrubber - and the shadow
                                     visibly pops back in as Kodi settles the layout. The itemlayout draws
                                     this same box unconditionally, so this one matches it. -->
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
                                    <height>{{ vscale(30) }}</height>
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
    <!-- 305 (the summary click-target), not straight to 300: visits it in top-to-bottom order on
         the way down, matching 305's own onup back up to here/206. -->
    <ondown>305</ondown>
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
        <!-- Focus background, gated the same as the white-text label below (real window focus, not
             just cursor position) - same 33FFFFFF rounded pill used elsewhere for a focus highlight
             (e.g. the summary click-target, button-row label overlays). Drawn first so the label/
             underline render on top of it. -->
        <control type="image">
            <visible>Control.HasFocus(205)</visible>
            <posx>0</posx>
            <posy>{{ vscale(42) }}</posy>
            <width>170</width>
            <height>{{ vscale(50) }}</height>
            <colordiffuse>33FFFFFF</colordiffuse>
            <texture border="10">script.plex/white-square-rounded.png</texture>
        </control>
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
    <!-- 305 (the summary click-target), not straight to 300: visits it in top-to-bottom order on
         the way down, matching 305's own onup back up to here/206. -->
    <ondown>305</ondown>
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
        <!-- Focus background - see 205's own copy of this control above for the full reasoning. -->
        <control type="image">
            <visible>Control.HasFocus(206)</visible>
            <posx>0</posx>
            <posy>{{ vscale(42) }}</posy>
            <width>170</width>
            <height>{{ vscale(50) }}</height>
            <colordiffuse>33FFFFFF</colordiffuse>
            <texture border="10">script.plex/white-square-rounded.png</texture>
        </control>
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