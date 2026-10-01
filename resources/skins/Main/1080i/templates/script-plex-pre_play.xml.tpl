{% extends "default.xml.tpl" %}
{# Slots the persistent sidebar rail in at the header's left. Its server/user buttons are ids
   201/202, handled with the section list below. The rail itself is NOT filled in via default.xml.tpl's header_sidebar
   block - that block sits inside header group 200, which slides off-screen on scroll
   (header_anim above it), and the rail must stay fixed. Instead header is overridden here to
   render default's header via super() and then append the rail outside/after it, mirroring
   why library.xml.tpl's sidebar include sits outside its own group 200. #}
{% block header %}
    {{ super() }}
    {% include "includes/sidebar.xml.tpl" %}
    <!-- Declared last so groups 802/901 draw on top - same reasoning as library.xml.tpl/
         script-plex-recommended.xml.tpl's own copy of this include. This screen is one of the
         seven real hosted-shell types (LibraryWindow.swapTo(), library.py) - its own onAction is
         monkeypatched to the *host* LibraryWindow's while it's showing (shared chrome like the
         sidebar is handled centrally across the chain), but the host's own showUserMenu()/
         showServers()/doUserOption()/selectServer() are all _sidebarTarget()-aware (library.py -
         see that method's own comment for the live-confirmed native crash a naive version of this
         include hit, and why write operations specifically had to be retargeted, not just these
         controls added) so they correctly read/write *this* window's own controls, declared here,
         while this screen is the one actually live. This window's own onClick (SidebarMixin.
         handleSidebarDropdownClick(), called first thing in this window's own onClick()) forwards
         USER_LIST_ID/SERVER_LIST_ID clicks back to the host, since onClick - unlike onAction -
         isn't delegated for a real shell. -->
    {% include "includes/sidebar_dropdowns.xml.tpl" %}
{% endblock header %}
{% block content %}
<control type="group" id="50">
    <!-- -377, not -300: this is the base offset for the whole hub-row ladder, and it is the only
         thing that can position the FIRST row - Roles is hub.focus tier 0 (preplay.py sets
         controlID - 400) and the first tier animation below is gated on hub.focus>0, so nothing
         fires when Roles is focused. 301 - the 678 stack origin (group 50's own 135 + grouplist
         60's 543) = -377, which lands every row's heading box on y=301, matching Artist. Group 50
         and the header (group 200) no longer slide by the same amount, which is fine: the header
         is 135 tall and default.xml.tpl's header_anim already takes it fully off-screen at -300. -->
    <animation effect="slide" end="0,{{ vscale(-377) }}" time="200" tween="quadratic" easing="out" condition="!String.IsEmpty(Window.Property(on.extras))">Conditional</animation>
    <!-- Slide right while the sidebar rail is expanded (focused), matching Home/Library -->
    <animation effect="slide" end="220,0" time="200" tween="sine" easing="inout" condition="ControlGroup(9000).HasFocus(0)">Conditional</animation>

    <animation type="Conditional" condition="Integer.IsGreater(Window.Property(hub.focus),0) + Control.IsVisible(500)" reversible="true">
        <!-- 410 = Roles's own footprint (405 + grouplist 60's itemgap 5) - this tier's job is to scroll exactly one row, so every heading lands on y=301. -->
        <effect type="slide" end="0,{{ vscale(-410) }}" time="200" tween="quadratic" easing="out"/>
    </animation>

    <animation type="Conditional" condition="Integer.IsGreater(Window.Property(hub.focus),1) + Control.IsVisible(501)" reversible="true">
        <!-- 341 = Reviews's own footprint (336 + grouplist 60's itemgap 5) - this tier's job is to scroll exactly one row, so every heading lands on y=301. -->
        <effect type="slide" end="0,{{ vscale(-341) }}" time="200" tween="quadratic" easing="out"/>
    </animation>

    <animation type="Conditional" condition="Integer.IsGreater(Window.Property(hub.focus),2) + Control.IsVisible(502)" reversible="true">
        <!-- 458 = Extras's own footprint (453 + grouplist 60's itemgap 5) - this tier's job is to scroll exactly one row, so every heading lands on y=301. -->
        <effect type="slide" end="0,{{ vscale(-458) }}" time="200" tween="quadratic" easing="out"/>
    </animation>

    <animation type="Conditional" condition="Integer.IsGreater(Window.Property(hub.focus),3) + Control.IsVisible(503)" reversible="true">
        <!-- 530 = Related's own footprint (525 + grouplist 60's itemgap 5) - this tier's job is to scroll exactly one row, so every heading lands on y=301. -->
        <effect type="slide" end="0,{{ vscale(-530) }}" time="200" tween="quadratic" easing="out"/>
    </animation>

    <animation type="Conditional" condition="Integer.IsGreater(Window.Property(hub.focus),4) + Control.IsVisible(504)" reversible="true">
        <!-- 530 = Coll. Hub 1's own footprint (525 + grouplist 60's itemgap 5) - this tier's job is to scroll exactly one row, so every heading lands on y=301. -->
        <effect type="slide" end="0,{{ vscale(-530) }}" time="200" tween="quadratic" easing="out"/>
    </animation>

    <animation type="Conditional" condition="Integer.IsGreater(Window.Property(hub.focus),5) + Control.IsVisible(505)" reversible="true">
        <!-- 530 = Coll. Hub 2's own footprint (525 + grouplist 60's itemgap 5) - this tier's job is to scroll exactly one row, so every heading lands on y=301. -->
        <effect type="slide" end="0,{{ vscale(-530) }}" time="200" tween="quadratic" easing="out"/>
    </animation>

    <!-- posx=52, not 60: 60 cleared the collapsed sidebar rail's icon column (matching the same
         resting-position shift Home/Library made when they adopted the rail - e.g.
         script-plex-posters.xml.tpl's group 50 also moved from 0 to 60), but measured against real
         official Plex screenshots the resulting content column sat a consistent ~8px right of
         Plex's own (median x=122-123 here vs. x=114-115 there, measured per synopsis text row
         across two titles). 52 closes that gap. Every child below is positioned relative to this
         group, so the shift applies uniformly without touching any of their own pixel-tuned
         offsets - except includes/media_info_pills.xml.tpl's posx, which deliberately cancels this
         exact value to stay flush with the screen's right edge and must move with it (see that
         include's own call below). -->
    <posx>52</posx>
    <!-- posy=135, not the old 155: matches script-plex-recommended.xml.tpl's own hero-info overlay
         group exactly - the absolute origin right under the header bar (itself vscale(135) tall) -
         so the clearlogo/metadata/summary block (block details below, at its own local posy=0) lands
         at the same absolute y on both screens, instead of the 20px-lower position the old 155
         baseline put it at. Every other child of this group that used to be positioned against that
         155 baseline (the button row below, id 60's grouplist further down) has had its own posy
         bumped by the same 20px so their absolute positions - and their spacing relative to the
         details block above them - stay exactly where they were; only the details block itself
         actually moved. -->
    <posy>{{ vscale(125) }}</posy>
    <defaultcontrol>101</defaultcontrol>

    {% block buttons %}
        <control type="grouplist" id="300">
            <animation effect="fade" start="0" end="100" time="200" reversible="true">VisibleChange</animation>
            <visible>!String.IsEmpty(Window.Property(initialized))</visible>
            <defaultcontrol>302</defaultcontrol>
            <!-- 63, not the old 22: the button icons were re-cropped from an 180x145 padded canvas down
                 to a tight 80x80 one (see context.py's own comment on the 70x70/itemgap-0 box re-tune),
                 shrinking the box from 152x121 to 70x70 - old absolute glyph center-x was
                 52(group 50's own posx)+22+76.4(play.png's opaque center, scaled into the old 152-wide
                 box)=150.4; the outer offset (52) cancels out of the equation, so the new posx is just
                 22+76.4-35.44(same glyph center, scaled into the new 70-wide box)=62.96. -->
            <posx>63</posx>
            <!-- 460, not the old 435 (raised to sit under the (now higher, narrower) summary box like
                 official Plex's own button row does, instead of being anchored a fixed distance above the
                 cast row below - still true, unrelated to the value itself). The button textures used to
                 be 180x145 source art stretched into a 152x121 box with no aspectratio, with play.png's
                 opaque pixels reaching row 92 of 145 (~77.59px once stretched to 121) - now 80x80 art
                 (re-cropped, see posx's own comment above) into a 70x70 box, opaque pixels reaching row 60
                 of 80 (~52.5px once stretched to 70). This group sits inside id 50 (posy 135, see that
                 control's own comment on the 20px rebase), so re-solving for the same absolute glyph
                 bottom as before (135+435+77.59=647.59) against the new 52.5 offset keeps the icon's
                 visible bottom unchanged: 135+460+52.5=647.5. -->
            <posy>{{ vscale(460) }}</posy>
            <width>1000</width>
            <height>{{ vscale(145) }}</height>
            <!-- 350 (the summary click-target), not straight to 200: keeps that focus stop reachable
                 from the button row via remote/keyboard, not just mouse/touch - same fix Artist's/
                 Seasons'/Episodes' own button rows already got. -->
            <onup condition="!String.IsEmpty(Window.Property(summary))">350</onup>
            <!-- Fallback is 350's own onup, skipping the stop when there's no summary. -->
            <onup>200</onup>
            <ondown>400</ondown>
            <onleft>9000</onleft>
            <itemgap>{{ theme.pre_play.buttongroup.itemgap }}</itemgap>
            <orientation>horizontal</orientation>
            <scrolltime tween="quadratic" easing="out">200</scrolltime>
            <usecontrolcoords>true</usecontrolcoords>

            <!-- Label-on-focus pill overlays (390-399) below: same treatment/recipe Episodes'/
                 Seasons'/library-posters' own button rows already have (episode_button_label.xml.tpl -
                 see button-label-overlay-recipe). Info/Play/Add-remove-watchlist/Media settings/More
                 reuse those rows' own $ADDON strings/measured widths since it's the same label text;
                 Trailer is new here (string 35064 "Watch trailer", measured 140px, same +4px buffer
                 convention as every other call site as of 2026-09-04 - see that recipe). No overlay
                 for the watchlist-availability dynamic play states (2302-2305, wl_dynamic_buttons.xml.tpl)
                 - matching Seasons' own scope, never given one either. onleft on each overlay is its
                 own button's id, onright the next button in the row - mirroring the neighbours plain
                 usecontrolcoords geometric nav would already resolve to, since none of the real
                 buttons below pass explicit onleft/onright of their own to literally copy. -->
            {% with attr = theme.pre_play.buttons & hitrect = theme.pre_play.buttons_hitrect & template = "includes/themed_button.xml.tpl" & ol = "includes/episode_button_label.xml.tpl" %}
                {% include template with name="info" & id=304 & overlay=True %}
                {% include ol with id=390 & visible="Control.HasFocus(304)" & name="info" &
                    label="$ADDON[script.plexmod 35059]" & label_suffix_info="" &
                    label_width=92 & pill_width=154 & group_width=110 &
                    onleft=304 & onright=302
                %}
                <!-- Play / Resume+Restart are mutually exclusive by state, the same split Episodes'
                     own button row uses (script-plex-episodes.xml.tpl): a single Play until the video
                     has a view offset, then a dedicated Resume and Restart pair instead, on request.
                     The state comes from Window.Property(in.progress) here rather than Episodes'
                     Container(400).ListItem.Property of the same name - this screen's subject is the
                     window's own single video (setInfo(), preplay.py), not a row's selected item.
                     Ids 301/307, the only two left free in this screen's 300-block (302-306 are
                     Play/Trailer/Info/Settings/More, 308/309 the watchlist pair, 310-322 the media
                     info pills) - so they don't read in row order, unlike Episodes' own 308/309. -->
                {% include template with name="play" & id=302 & overlay=True & visible="String.IsEmpty(Window.Property(unavailable)) + String.IsEmpty(Window.Property(disable_playback)) + String.IsEmpty(Window.Property(in.progress))" %}
                {% include ol with id=391 & visible="Control.HasFocus(302)" & name="play" &
                    label="$ADDON[script.plexmod 33020]" & label_suffix_info="" &
                    label_width=51 & pill_width=113 & group_width=69 &
                    onleft=302 & onright=303
                %}
                {% include template with name="resume" & id=301 & overlay=True & visible="String.IsEmpty(Window.Property(unavailable)) + String.IsEmpty(Window.Property(disable_playback)) + !String.IsEmpty(Window.Property(in.progress))" %}
                <!-- Two width variants, not one covering both - straight copy of Episodes' own pair,
                     same label text, same font, same suffix: remainingTimeToShortText() (util.py) only
                     ever emits "Xm" (<=90 min) or "XhYm", and String.Contains(...,h) tells them apart
                     without another property. label_suffix_wprop, not label_suffix_info: the time-left
                     text is a window property on this screen (see the block comment above). -->
                {% include ol with id=397 & visible="Control.HasFocus(301) + !String.Contains(Window.Property(resume.timeleft),h)" & name="resume" &
                    label="$ADDON[script.plexmod 32316]" & label_suffix_wprop="resume.timeleft" &
                    label_width=208 & pill_width=270 & group_width=226 &
                    onleft=301 & onright=307
                %}
                {% include ol with id=399 & visible="Control.HasFocus(301) + String.Contains(Window.Property(resume.timeleft),h)" & name="resume" &
                    label="$ADDON[script.plexmod 32316]" & label_suffix_wprop="resume.timeleft" &
                    label_width=237 & pill_width=299 & group_width=255 &
                    onleft=301 & onright=307
                %}
                {% include template with name="restart" & id=307 & overlay=True & visible="String.IsEmpty(Window.Property(unavailable)) + String.IsEmpty(Window.Property(disable_playback)) + !String.IsEmpty(Window.Property(in.progress))" %}
                {% include ol with id=398 & visible="Control.HasFocus(307)" & name="restart" &
                    label="$ADDON[script.plexmod 35061]" & label_suffix_info="" &
                    label_width=82 & pill_width=144 & group_width=100 &
                    onleft=307 & onright=303
                %}
                {% include "includes/wl_dynamic_buttons.xml.tpl" %}
                {% include template with name="trailer" & id=303 & overlay=True & visible="!String.IsEmpty(Window.Property(trailer.button))" %}
                {% include ol with id=392 & visible="Control.HasFocus(303)" & name="trailer" &
                    label="$ADDON[script.plexmod 35064]" & label_suffix_info="" &
                    label_width=145 & pill_width=207 & group_width=163 &
                    onleft=303 & onright=308
                %}
                {% include "includes/wl_add_remove_buttons.xml.tpl" %}
                {% include ol with id=393 & visible="Control.HasFocus(308)" & name="watchlist" &
                    label="$ADDON[script.plexmod 35062]" & label_suffix_info="" &
                    label_width=181 & pill_width=243 & group_width=199 &
                    onleft=308 & onright=309
                %}
                {% include ol with id=394 & visible="Control.HasFocus(309)" & name="watchlisted" &
                    label="$ADDON[script.plexmod 34011]" & label_suffix_info="" &
                    label_width=255 & pill_width=317 & group_width=273 &
                    onleft=309 & onright=305
                %}
                {% include template with name="settings" & id=305 & overlay=True & visible="String.IsEmpty(Window.Property(disable_playback))" %}
                {% include ol with id=395 & visible="Control.HasFocus(305)" & name="settings" &
                    label="$ADDON[script.plexmod 35060]" & label_suffix_info="" &
                    label_width=164 & pill_width=226 & group_width=182 &
                    onleft=305 & onright=306
                %}
                {% include template with name="more" & id=306 & overlay=True & visible="String.IsEmpty(Window.Property(disable_playback))" %}
                {% include ol with id=396 & visible="Control.HasFocus(306)" & name="more" &
                    label="$ADDON[script.plexmod 32307]" & label_suffix_info="" &
                    label_width=61 & pill_width=123 & group_width=79 &
                    onleft=306 & onright=""
                %}
            {% endwith %}

        </control>
    {% endblock %}

    {% block details %}
        <control type="group">
            <posx>0</posx>
            <posy>0</posy>
            <width>1920</width>
            <height>{{ vscale(600) }}</height>
            <!-- No more poster-thumbnail fallback: the hero-art box (see default_background.xml.tpl,
                 anchored top-right at x691-1920/y0-691) covers what the small corner poster used to be
                 for, and title/clearlogo/meta/rating/summary now have a single fixed position and width
                 instead of being duplicated at two x-offsets and switched with <visible>. Column runs
                 x61-619 (width 558) inside this group (absolute x113-671 on screen, group 50 at posx=52)
                 to clear the hero-art box's left edge (691) with a 20px margin - the extra 1px past the
                 old x112 lines the column up with Episodes'/Seasons' own shared x=113 baseline (see
                 script-plex-episodes.xml.tpl's header block comment). -->
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
                <label>$INFO[Window.Property(title)]</label>
            </control>
            <!-- 722x162, matching script-plex-recommended.xml.tpl's own hero-info clearlogo box exactly
                 (bumped from the original 616x109 on request, for consistency between the two screens).
                 preplay.py's CLEAR_LOGO_DIM requests the transcoded clearlogo at this same 722x162 size. -->
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

            <!-- Moved from top-right (near the clock) to the left column, directly under the metadata
                 lines, matching official Plex's own placement. One icon+label pair per rating the
                 item actually has (populateRatings(), lib/windows/mixins/ratings.py) - not just a
                 critic/audience pair, since a single item can genuinely carry several same-type
                 ratings (e.g. IMDb, Rotten Tomatoes, and TMDB audience scores all at once) that used
                 to silently lose all but one. rating1..rating6 must match RatingsMixin.MAX_RATINGS
                 exactly (ratings.py) - not templated from that constant, this loop's own range()
                 has to be kept in sync by hand if it ever changes. Width bumped from the old
                 fixed-2-slot row's 558 to 708 (matching the meta row/summary box below) since up to
                 6 pairs need real room - still not a hard guarantee against overflow on an item
                 with an unusually high rating count, worth an eye on real data. -->
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
                <!-- Each rating is its own icon+label pair-group, not two direct grouplist items -
                     itemgap above is one uniform value for every direct child, so getting a
                     tighter icon-to-label gap than the gap between one rating and the next needs
                     its own smaller, explicit offset inside a wrapper the outer itemgap treats as
                     a single item. Costs the label's own auto-width sizing (Kodi needs this
                     group's own <width> up front to stack the *next* pair-group correctly, so the
                     label gets a fixed width generous enough for any realistic value - "100%" -
                     instead of shrinking to its actual text). -->
                {% for i in range(1, 7) %}
                <control type="group">
                    <visible>!String.IsEmpty(Window.Property(rating{{ i }}))</visible>
                    <width>91</width>
                    <height>{{ vscale(32) }}</height>
                    <!-- 40, not 56: matches the widest real asset at height=30 exactly (Rotten
                         Tomatoes' "spilled" badge, 40x30 native) - every other source (imdb/tmdb
                         48x48, RT's other 5 badges, the "other" fallback) renders narrower than
                         that at this height, so nothing clips and there's no leftover slack either. -->
                    <control type="image">
                        <posx>0</posx>
                        <posy>1</posy>
                        <width>40</width>
                        <height>{{ vscale(30) }}</height>
                        <texture fallback="script.plex/ratings/other/image.rating.png">$INFO[Window.Property(rating{{ i }}.image)]</texture>
                        <aspectratio align="right">keep</aspectratio>
                    </control>
                    <!-- 44, not 38: 38 clipped the "%" off Rotten Tomatoes values ("73%") - 44 gives
                         it enough room. -->
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
            {% block summary %}
                <control type="textbox">
                    <!-- 813x90 at posy=239, font10 - matching script-plex-recommended.xml.tpl's own
                         summary box exactly (bumped from 708x90/posy=233/font12 on request, for
                         consistency between the two screens). Right edge (112+813=925 on screen) now
                         reaches further into the hero-art box's left edge (691) than the clearlogo/
                         metadata column above (still 708 wide, see pp_meta_row.xml.tpl) - same
                         mismatch recommended's own version has - but that box is masked to fade to
                         transparent along its left edge (see default_background.xml.tpl), so text
                         overlapping that fade zone blends rather than crosses a hard image edge. -->
                    <posx>61</posx>
                    <posy>{{ vscale(277) }}</posy>
                    <width>813</width>
                    <height>{{ vscale(90) }}</height>
                    <font>font10</font>
                    <align>left</align>
                    <textcolor>FFD2CCCE</textcolor>
                    <shadowcolor>66000000</shadowcolor>
                    <scrolltime>200</scrolltime>
                    <autoscroll delay="2000" time="2000" repeat="10000">!Control.HasFocus(13)</autoscroll>
                    <label>$INFO[Window.Property(summary)]</label>
                </control>
                <!-- Invisible click/focus target laid directly over the summary textbox above -
                     textboxes have no click or focus of their own in Kodi, so this is a separate
                     button control sized and positioned to match it exactly, wired to
                     summaryButtonClicked() (SUMMARY_BUTTON_ID, preplay.py) - same recipe as Artist's/
                     Seasons'/Episodes' own copy, which this was ported from. Blank label (matches
                     themed_button.xml.tpl's own convention) so nothing draws over the textbox's real
                     text. texturenofocus/texturefocus both "-" (explicit none, not just omitted -
                     Kodi otherwise falls back to its own default button look) - the focus highlight
                     itself is the separate image below instead, not this control's own texture, so
                     it can be sized bigger than the actual hit area. No season-tab-style fallback
                     chain on its own onup (unlike Seasons'/Episodes' copy) - this screen has no
                     equivalent tab row, just the plain header (200) above. id=350, not 310: that
                     collided with includes/media_info_pills.xml.tpl's own video-pill background
                     image (also id 310, live in this same window) - live-reported as "the
                     background does not extend the full length of the label", since
                     Control.setWidth() calls meant for that pill
                     (MediaInfoPillsMixin.resizeMediaInfoPills()) were hitting this button instead. -->
                <control type="button" id="350">
                    <!-- No target when there's no summary: an enabled button over empty space is a
                         focus stop that opens a blank popup. The nav tag routing through it carries
                         the same condition, so the chain closes up. -->
                    <visible>!String.IsEmpty(Window.Property(summary))</visible>
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
                <!-- Focus highlight for 350 above, kept as its own image rather than that button's
                     own texturefocus so it can extend 5px past the button's own hit area on every
                     side, matching Artist's/Seasons'/Episodes' own copy. -->
                <control type="image">
                    <visible>Control.HasFocus(350)</visible>
                    <posx>56</posx>
                    <posy>{{ vscale(272) }}</posy>
                    <width>823</width>
                    <height>{{ vscale(100) }}</height>
                    <colordiffuse>33FFFFFF</colordiffuse>
                    <texture border="10">script.plex/white-square-rounded.png</texture>
                </control>
            {% endblock %}
            <!-- The streams block below (audio/subtitle pills, overridden by pre_play-wl.xml.tpl for the
                 watchlist screen's availability row) stays a single instance rather than duplicating:
                 Kodi/ibis blocks can only be defined once, so a subclass's override would only ever reach
                 one of two physical copies. Now laid out horizontally (see includes/media_info_pills.xml.tpl
                 for how/why the pills themselves are sized - position is the only thing pre_play-specific
                 left here). posx=998 is 1920 (screen width) minus 85 (the row's target inset from the
                 screen's right edge, on request - matching episodes' own identical inset now) minus the
                 row's own 785 width (200 + 295 + 260 + 2*15 PILLS_ITEMGAP in the mixin) minus 52 to
                 cancel out group 50's own +52 sidebar-clearance shift (52, not the original 60, since
                 group 50's own posx moved, see that control's own comment). posy=447, not 417: dropped
                 an explicit 30px on request (three 10px nudges) from the position that put the row's
                 bottom at absolute y=632, matching official Plex's own measured pill-row position
                 (614-632) and sitting 59px above the hero-art box's bottom edge (691) - not the old
                 legacy-vertical-stack-derived 498. The wrapping group's own posy=30
                 used to be a conditional slide applied only while the poster was hidden, to keep vertical
                 rhythm with the row above it; now applies unconditionally so this row (and pre_play-wl's
                 availability row, which shares this same wrapper) sits at the same place regardless of the
                 poster, matching the button row's own unification above. -->
            <control type="group">
                <posy>{{ vscale(30) }}</posy>
            {% block streams %}
                {% include "includes/media_info_pills.xml.tpl" with posx=998 & posy=447 %}
            {% endblock %}
            </control>
        </control>
    {% endblock %}

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
        <!-- 543, not the old 562: moved up 19px so the gap from the button row's bottom edge to the
             first heading box matches Seasons'. The buttons end at 460 + 70 (grouplist 300's own posy
             plus the modern theme's 70px button height) = 530, and Seasons sits its first label's 80px
             box 13px below that same edge, so 530 + 13 = 543. Seasons and Episodes are deliberately
             tuned and were left alone; this screen and Artist were brought to Seasons' value.
             History: 562 was 540->560 (compensating group 50's own posy rebase 155 -> 135, so this row
             kept its absolute position) plus two 1px nudges on 2026-09-04. -->
        <posy>{{ vscale(543) }}</posy>
        <width>1920</width>
        <height>{{ vscale(3400) }}</height>

        <onup>300</onup>
        <itemgap>5</itemgap>

        <!-- ROLES -->
        <control type="group" id="500">
            <visible>Integer.IsGreater(Container(400).NumItems,0) + String.IsEmpty(Window.Property(drawing))</visible>
            <defaultcontrol>400</defaultcontrol>
            <width>1920</width>
            <!-- 460, not the old 416 (+44, same delta as id 400's own list height bump below): the
                 Roles art grew 200->244 to match Episodes/Seasons (2026-09-04, on request), so this
                 needs the same extra room or Reviews (stacked right after via this grouplist's own
                 itemgap=0 auto-stacking) would inherit a too-tight gap. -->
            <height>{{ vscale(405) }}</height>
            <!-- Same heading pattern/string ("Credits", 33609) as the episode screen's own Roles section
                 (script-plex-episodes.xml.tpl id 502) and seasons.xml.tpl id 501 - Plex was missing one
                 here entirely. -->
            <control type="label">
                <posx>61</posx>
                <posy>0</posy>
                <width>1000</width>
                <height>{{ vscale(80) }}</height>
                <font>font30_title</font>
                <align>left</align>
                <aligny>center</aligny>
                <!-- Matches Episodes'/Seasons' own Roles heading style: font30_title, 66000000 shadow, no
                     uppercase (script-plex-seasons.xml.tpl id 401's own label, script-plex-episodes.xml.tpl
                     id 502's own label - normalized here 2026-09-04, on request). -->
                <textcolor>FFD2CCCE</textcolor>
                <shadowcolor>66000000</shadowcolor>
                <label>$ADDON[script.plexmod 33609]</label>
            </control>
            <control type="fixedlist" id="400">
                <!-- 53 = 113 - group 50's own posx=52 - the itemlayout's own 5+3 left margin, putting
                     the clip edge on x=105. That is 39px clear of the collapsed sidebar rail, whose
                     widest icon ends at x=66, so departing cards clip in open space rather than
                     mid-icon - see the SHARED HUB-ROW RECIPE at grouplist 60 above. -->
                <posx>53</posx>
                <posy>{{ vscale(22) }}</posy>
                <width>1867</width>
                <!-- 454, not the old 410 (+44, the same delta as the art's own 200->244 growth below) -
                     keeps Reviews (stacked right after via grouplist 60's auto-stacking) from
                     inheriting a too-tight gap now that Roles' own content is taller. -->
                <height>{{ vscale(380) }}</height>
                <onup>300</onup>
                <ondown>401</ondown>
                <onleft>9000</onleft>
                <scrolltime>200</scrolltime>
                <orientation>horizontal</orientation>
                <!-- Focus pinned to the row's first slot, the row scrolling under it - the same as
                     Recommended's hub rows (script-plex-recommended.xml.tpl, which explains the tail).
                     movement = itemsPerPage - 1, itemsPerPage being (1867 - 270) / 270 + 1 = 6: the last
                     items spread to the last whole slot, where this row, a plain list before, left them. -->
                <focusposition>0</focusposition>
                <movement>5</movement>
                <preloaditems>4</preloaditems>
                <!-- ITEM LAYOUT ########################################## -->
                <!-- 244x244 art (was 200x200), role-selected-thin.png focus ring, name label in
                     FFFFFFFF (was AAFFFFFF, matching the character label's own dimmed tone below it) -
                     matches Episodes'/Seasons' own Roles row exactly (2026-09-04, on request). -->
                <itemlayout width="270">
                    <control type="group">
                       <!-- 5, back to the old value: a uniform outer margin across every row here (matching Seasons' own convention), with the list's own clip line below doing the per-row x=113 compensation instead - see that control's own comment. -->
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
                                        <scroll>Control.HasFocus(400)</scroll>
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
                                        <scroll>Control.HasFocus(400)</scroll>
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
                                <visible>Control.HasFocus(400)</visible>
                                <posx>0</posx>
                                <posy>0</posy>
                                <width>246</width>
                                <height>{{ vscale(246) }}</height>
                                <texture>script.plex/buttons/role-selected-thin.png</texture>
                            </control>
                        </control>
                    </control>
                </focusedlayout>
            </control>
        </control>
        <!-- /ROLES -->

        <!-- REVIEWS -->
        <control type="group" id="501">
            <visible>Integer.IsGreater(Container(401).NumItems,0) + String.IsEmpty(Window.Property(drawing))</visible>
            <defaultcontrol>401</defaultcontrol>
            <width>1920</width>
            <!-- 376, not 446: reduced by the same 70px the review card/textbox shrank by below, so
                 the next section (Extras, id 502) doesn't inherit a dead gap. -->
            <height>{{ vscale(336) }}</height>
            <control type="label">
                <posx>61</posx>
                <posy>0</posy>
                <width>1000</width>
                <height>{{ vscale(80) }}</height>
                <font>font30_title</font>
                <align>left</align>
                <aligny>center</aligny>
                <!-- Same heading style as Roles/Extras/Related below - font30_title, 66000000 shadow, no
                     uppercase, matching Episodes'/Seasons' own section headers (normalized 2026-09-04,
                     on request) - Reviews has no direct Episodes/Seasons counterpart to copy verbatim
                     from, so this just applies their shared convention. -->
                <textcolor>FFD2CCCE</textcolor>
                <shadowcolor>66000000</shadowcolor>
                <label>$ADDON[script.plexmod 32953]</label>
            </control>
            <control type="fixedlist" id="401">
                <!-- 53: same derivation as every other list here - see the SHARED HUB-ROW RECIPE at grouplist 60 above. This row has no
                     inner group, so the recipe's 3px art inset is applied to the card and its content
                     block directly instead. -->
                <posx>53</posx>
                <posy>{{ vscale(22) }}</posy>
                <width>1867</width>
                <height>{{ vscale(310) }}</height>
                <onup>400</onup>
                <ondown>402</ondown>
                <onleft>9000</onleft>
                <scrolltime>200</scrolltime>
                <orientation>horizontal</orientation>
                <!-- Focus pinned to the row's first slot, the row scrolling under it - the same as
                     Recommended's hub rows (script-plex-recommended.xml.tpl, which explains the tail).
                     movement = itemsPerPage - 1, itemsPerPage being (1867 - 537) / 537 + 1 = 3: the last
                     items spread to the last whole slot, where this row, a plain list before, left them. -->
                <focusposition>0</focusposition>
                <movement>2</movement>
                <preloaditems>4</preloaditems>
                <!-- ITEM LAYOUT ########################################## -->
                <itemlayout width="537">
                    <control type="group">
                        <!-- 5 + the card's own 3px inset below = the recipe's 8px left margin. -->
                        <posx>5</posx>
                        <posy>{{ vscale(61) }}</posy>
                        <control type="image">
                            <posx>3</posx>
                            <posy>{{ vscale(3) }}</posy>
                            <width>505</width>
                            <height>{{ vscale(240) }}</height>
                            <!-- Reuses the real ar16x9 art mask (script.plex/masks/ar16x9-mask.png) as a
                                 diffuse mask over a plain white square, not border-sliced - matches how
                                 this same mask is used everywhere else in this codebase (e.g. the episode
                                 carousel's own dimming overlay, script-plex-episodes.xml.tpl), all plain
                                 diffuse+stretch with no border. A border=20 9-slice was tried first, but
                                 it renders the mask's native-resolution corner (781x440 canvas) unstretched
                                 at that same pixel size regardless of this card's much smaller box - a
                                 visibly different, chunkier corner than the same mask produces when scaled
                                 down with the rest of the image, which is what every other use of this
                                 mask in the codebase actually does. -->
                            <texture diffuse="script.plex/masks/ar16x9-mask.png">script.plex/white-square.png</texture>
                            <colordiffuse>60000000</colordiffuse>
                        </control>
                        <control type="group">
                            <posx>23</posx>
                            <posy>{{ vscale(23) }}</posy>
                            <control type="group">
                                <posx>-10</posx>
                                <posy>0</posy>
                                <control type="image">
                                    <posx>10</posx>
                                    <posy>{{ vscale(-5) }}</posy>
                                    <width>70</width>
                                    <height>{{ vscale(70) }}</height>
                                    <texture>script.plex/reviews/$INFO[ListItem.Thumb].png</texture>
                                </control>
                                <control type="label">
                                    <scroll>false</scroll>
                                    <posx>90</posx>
                                    <posy>0</posy>
                                    <width>400</width>
                                    <height>{{ vscale(30) }}</height>
                                    <font>font10</font>
                                    <align>left</align>
                                    <textcolor>DDFFFFFF</textcolor>
                                    <label>$INFO[ListItem.Label]</label>
                                </control>
                                <control type="label">
                                    <scroll>false</scroll>
                                    <posx>90</posx>
                                    <posy>{{ vscale(30) }}</posy>
                                    <width>400</width>
                                    <height>{{ vscale(30) }}</height>
                                    <font>font10</font>
                                    <align>left</align>
                                    <textcolor>66FFFFFF</textcolor>
                                    <label>$INFO[ListItem.Label2]</label>
                                </control>
                            </control>
                            <control type="textbox">
                                <posx>0</posx>
                                <posy>{{ vscale(80) }}</posy>
                                <!-- 465, not 480: tracks the card's own 520->505 shrink (same 20px
                                     inset on each side). -->
                                <width>465</width>
                                <!-- 120, not 190: room for 4 lines of font10 (23px, ~30px/line -
                                     see the reviewer name/label rows above, which use height=30
                                     per line of this same font). -->
                                <height>{{ vscale(120) }}</height>
                                <font>font10</font>
                                <align>left</align>
                                <textcolor>AAFFFFFF</textcolor>
                                <label>$INFO[ListItem.Property(text)]</label>
                            </control>
                        </control>
                    </control>
                </itemlayout>

                <!-- FOCUSED LAYOUT ####################################### -->
                <focusedlayout width="537">
                    <control type="group">
                        <posx>5</posx>
                        <posy>{{ vscale(61) }}</posy>
                        <control type="image">
                            <posx>3</posx>
                            <posy>{{ vscale(3) }}</posy>
                            <width>505</width>
                            <height>{{ vscale(240) }}</height>
                            <texture diffuse="script.plex/masks/ar16x9-mask.png">script.plex/white-square.png</texture>
                            <colordiffuse>80000000</colordiffuse>
                        </control>
                        <control type="group">
                            <posx>23</posx>
                            <posy>{{ vscale(23) }}</posy>
                            <control type="group">
                                <posx>-10</posx>
                                <posy>0</posy>
                                <control type="image">
                                    <posx>10</posx>
                                    <posy>{{ vscale(-5) }}</posy>
                                    <width>70</width>
                                    <height>{{ vscale(70) }}</height>
                                    <texture>script.plex/reviews/$INFO[ListItem.Thumb].png</texture>
                                </control>
                                <control type="label">
                                    <scroll>false</scroll>
                                    <posx>90</posx>
                                    <posy>0</posy>
                                    <width>400</width>
                                    <height>{{ vscale(30) }}</height>
                                    <font>font10</font>
                                    <align>left</align>
                                    <textcolor>DDFFFFFF</textcolor>
                                    <label>$INFO[ListItem.Label]</label>
                                </control>
                                <control type="label">
                                    <scroll>false</scroll>
                                    <posx>90</posx>
                                    <posy>{{ vscale(30) }}</posy>
                                    <width>400</width>
                                    <height>{{ vscale(30) }}</height>
                                    <font>font10</font>
                                    <align>left</align>
                                    <textcolor>66FFFFFF</textcolor>
                                    <label>$INFO[ListItem.Label2]</label>
                                </control>
                            </control>
                            <control type="textbox">
                                <posx>0</posx>
                                <posy>{{ vscale(80) }}</posy>
                                <width>465</width>
                                <height>{{ vscale(120) }}</height>
                                <font>font10</font>
                                <align>left</align>
                                <textcolor>DDFFFFFF</textcolor>
                                <label>$INFO[ListItem.Property(text)]</label>
                                <autoscroll delay="6000" time="3000" repeat="12000">Control.HasFocus(401)</autoscroll>
                            </control>
                        </control>
                        <!-- Ring-mask focus indicator, not a bordered selected.png overlay - matches how
                             ar16x9 art shows focus elsewhere (script-plex-episodes.xml.tpl's episode
                             cards): the same ring-mask-ar16x9.png diffused over white-square.png and
                             tinted the same orange (FFE9A20D), plain-stretched with no border, sized ~3px
                             larger than the card on every side so the ring traces just outside it. -->
                        <control type="image">
                            <visible>Control.HasFocus(401)</visible>
                            <posx>0</posx>
                            <posy>0</posy>
                            <width>511</width>
                            <height>{{ vscale(246) }}</height>
                            <texture diffuse="script.plex/masks/ring-mask-ar16x9.png">script.plex/white-square.png</texture>
                            <colordiffuse>FFE9A20D</colordiffuse>
                        </control>
                    </control>
                </focusedlayout>
            </control>
        </control>
        <!-- /REVIEWS -->

        <!-- EXTRAS -->
        <control type="group" id="502">
            <visible>Integer.IsGreater(Container(402).NumItems,0) + String.IsEmpty(Window.Property(drawing))</visible>
            <!-- 450, not 360: the art grew from 299x168 to 512x288 on request, so the list's own
                 content now bottoms out around 444 (list posy 18 + item posy 61 + 5 inner padding +
                 360 local content height) - this just needs to cover that, with a little slack, so
                 Related (stacked right after via this grouplist's own itemgap=0) doesn't overlap it. -->
            <height>{{ vscale(453) }}</height>
            <width>1920</width>
            <control type="label">
                <posx>61</posx>
                <posy>0</posy>
                <width>1000</width>
                <height>{{ vscale(80) }}</height>
                <font>font30_title</font>
                <align>left</align>
                <aligny>center</aligny>
                <!-- Matches Episodes'/Seasons' own Extras heading style: font30_title, 66000000 shadow, no
                     uppercase (normalized 2026-09-04, on request) - see the Roles label's own comment
                     above. -->
                <textcolor>FFD2CCCE</textcolor>
                <shadowcolor>66000000</shadowcolor>
                <label>$ADDON[script.plexmod 32305]</label>
            </control>
            <control type="fixedlist" id="402">
                <!-- 51, not 0 (width shrunk to match): same sidebar-clearance clip-line fix as the Roles list above - identical margin math (5px inner padding group). -->
                <posx>53</posx>
                <posy>{{ vscale(22) }}</posy>
                <width>1867</width>
                <height>{{ vscale(430) }}</height>
                <onup>401</onup>
                <ondown>403</ondown>
                <onleft>9000</onleft>
                <scrolltime>200</scrolltime>
                <orientation>horizontal</orientation>
                <!-- Focus pinned to the row's first slot, the row scrolling under it - the same as
                     Recommended's hub rows (script-plex-recommended.xml.tpl, which explains the tail).
                     movement = itemsPerPage - 1, itemsPerPage being (1867 - 544) / 544 + 1 = 3: the last
                     items spread to the last whole slot, where this row, a plain list before, left them. -->
                <focusposition>0</focusposition>
                <movement>2</movement>
                <preloaditems>4</preloaditems>
                <!-- ITEM LAYOUT ########################################## -->
                <itemlayout width="544">
                    <control type="group">
                        <!-- 5, back to the old value - see the Roles row's own comment above. -->
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
                            <!-- 512x288, exactly 16:9 - matches ar16x9-mask.png's own native aspect
                                 closely enough that the diffuse mask below needs no border-slicing to
                                 look right (see the reviews card fix earlier this session for why
                                 border+diffuse together has no working precedent here - plain
                                 diffuse+stretch is the proven pattern, and works cleanly here since the
                                 box and mask aspect ratios already match). -->
                            <control type="image">
                                <posx>0</posx>
                                <posy>0</posy>
                                <width>512</width>
                                <height>{{ vscale(288) }}</height>
                                <texture background="true" diffuse="script.plex/masks/ar16x9-mask.png" fallback="$INFO[ListItem.Property(thumb.fallback)]">$INFO[ListItem.Thumb]</texture>
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
                                    <font>font32</font>
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
                                <height>{{ vscale(60) }}</height>
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
                                    <texture background="true" diffuse="script.plex/masks/ar16x9-mask.png" fallback="$INFO[ListItem.Property(thumb.fallback)]">$INFO[ListItem.Thumb]</texture>
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
                                        <font>font32</font>
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
                                    <height>{{ vscale(60) }}</height>
                                    <font>font10</font>
                                    <align>center</align>
                                    <textcolor>FFFFFFFF</textcolor>
                                    <label>$INFO[ListItem.Label]</label>
                                </control>
                            </control>
                            <!-- Ring-mask focus indicator, not the old bordered selected.png overlay -
                                 matches how ar16x9 art actually does this on the episode screens
                                 (script-plex-episodes.xml.tpl): same ring-mask-ar16x9.png diffused over
                                 white-square.png, tinted FFE9A20D, plain-stretched with no border, and
                                 the same 3px overflow past the art on every side (episodes.xml.tpl uses
                                 5,5.5->445,250 art against a 0,0.5->451,255.5 ring - a 3px gap; this art
                                 sits at 5,5, so posx/posy=2 gives the same 3px gap here). Not identical
                                 in one respect: this art (512x288) is much closer to the mask's own
                                 native 781x440 resolution than episodes' 445x250 thumbs are, so the same
                                 asset's fixed-width line renders visibly thicker here even at a matching
                                 3px gap - a real limitation of a raster mask with no border-slice
                                 equivalent (see the reviews card's own comments on why border+diffuse
                                 isn't a working combination in this codebase). -->
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
        <!-- /EXTRAS -->

        <!-- RELATED -->
        <control type="group" id="503">
            <visible>Integer.IsGreater(Container(403).NumItems,0) + String.IsEmpty(Window.Property(drawing))</visible>
            <defaultcontrol>403</defaultcontrol>
            <width>1920</width>
            <height>{{ vscale(525) }}</height>
            <control type="label">
                <posx>61</posx>
                <posy>0</posy>
                <width>1000</width>
                <height>{{ vscale(80) }}</height>
                <font>font30_title</font>
                <align>left</align>
                <aligny>center</aligny>
                <!-- Matches Episodes'/Seasons' own Related heading style: font30_title, 66000000 shadow, no
                     uppercase (normalized 2026-09-04, on request) - see the Roles label's own comment
                     above. -->
                <textcolor>FFD2CCCE</textcolor>
                <shadowcolor>66000000</shadowcolor>
                <label>$INFO[Window.Property(related.header)]</label>
            </control>
            <control type="fixedlist" id="403">
                <!-- 53, not 0 (width shrunk to match): same sidebar-clearance clip-line fix as the Roles list above. 105, not 103: this row's own inner padding group is 3px, not 5, so the clip line only needs to close a 2px-smaller gap to reach the same x=113 art position. -->
                <posx>53</posx>
                <posy>{{ vscale(22) }}</posy>
                <width>1867</width>
                <height>{{ vscale(500) }}</height>
                <onup>402</onup>
                <ondown>404</ondown>
                <!-- noop was a leftover from a template shared with the bidirectional episode carousel:
                     these paginators (RelatedPaginator/CollectionPaginator) always start at offset=0 and
                     never produce a left-boundary marker, so there's no pagination state for noop to
                     protect here - safe to route straight to the sidebar. -->
                <onleft>9000</onleft>
                <onright>noop</onright>
                <scrolltime>200</scrolltime>
                <orientation>horizontal</orientation>
                <!-- Focus pinned to the row's first slot, the row scrolling under it - the same as
                     Recommended's hub rows (script-plex-recommended.xml.tpl, which explains the tail).
                     movement = itemsPerPage - 1, itemsPerPage being (1867 - 272) / 272 + 1 = 6: the last
                     items spread to the last whole slot, where this row, a plain list before, left them. -->
                <focusposition>0</focusposition>
                <movement>5</movement>
                <preloaditems>4</preloaditems>
                <!-- ITEM LAYOUT ########################################## -->
                <itemlayout width="272">
                    <control type="group">
                        <!-- 5, back to the old value - see the Roles row's own comment above. -->
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
                                <visible>!String.IsEmpty(ListItem.Label2)</visible>
                                <posx>0</posx>
                                <posy>{{ vscale(399) }}</posy>
                                <width>240</width>
                                <height>{{ vscale(30) }}</height>
                                <font>font10</font>
                                <align>center</align>
                                <textcolor>99FFFFFF</textcolor>
                                <label>$INFO[ListItem.Label2]</label>
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
                                <control type="label">
                                    <scroll>Control.HasFocus(403)</scroll>
                                    <visible>!String.IsEmpty(ListItem.Label2)</visible>
                                    <posx>0</posx>
                                    <posy>{{ vscale(399) }}</posy>
                                    <width>240</width>
                                    <height>{{ vscale(30) }}</height>
                                    <font>font10</font>
                                    <align>center</align>
                                    <textcolor>99FFFFFF</textcolor>
                                    <label>$INFO[ListItem.Label2]</label>
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
        <!-- /RELATED -->

        <!-- COLLECTION HUB 0 -->
        <control type="group" id="504">
            <visible>Integer.IsGreater(Container(404).NumItems,0) + String.IsEmpty(Window.Property(drawing))</visible>
            <defaultcontrol>404</defaultcontrol>
            <width>1920</width>
            <height>{{ vscale(525) }}</height>
            <control type="label">
                <posx>61</posx>
                <posy>0</posy>
                <width>1000</width>
                <height>{{ vscale(80) }}</height>
                <font>font30_title</font>
                <align>left</align>
                <aligny>center</aligny>
                <!-- Same normalized heading style as Roles/Extras/Related above (2026-09-04, on
                     request) - see the Roles label's own comment. -->
                <textcolor>FFD2CCCE</textcolor>
                <shadowcolor>66000000</shadowcolor>
                <label>$INFO[Window.Property(collection.header.0)]</label>
            </control>
            <control type="fixedlist" id="404">
                <!-- 53, not 0 (width shrunk to match) - see the Related list's own comment above, identical margin math. -->
                <posx>53</posx>
                <posy>{{ vscale(22) }}</posy>
                <width>1867</width>
                <height>{{ vscale(500) }}</height>
                <onup>403</onup>
                <ondown>405</ondown>
                <!-- noop was a leftover from a template shared with the bidirectional episode carousel:
                     these paginators (RelatedPaginator/CollectionPaginator) always start at offset=0 and
                     never produce a left-boundary marker, so there's no pagination state for noop to
                     protect here - safe to route straight to the sidebar. -->
                <onleft>9000</onleft>
                <onright>noop</onright>
                <scrolltime>200</scrolltime>
                <orientation>horizontal</orientation>
                <!-- Focus pinned to the row's first slot, the row scrolling under it - the same as
                     Recommended's hub rows (script-plex-recommended.xml.tpl, which explains the tail).
                     movement = itemsPerPage - 1, itemsPerPage being (1867 - 272) / 272 + 1 = 6: the last
                     items spread to the last whole slot, where this row, a plain list before, left them. -->
                <focusposition>0</focusposition>
                <movement>5</movement>
                <preloaditems>4</preloaditems>
                <itemlayout width="272">
                    <control type="group">
                        <!-- 5, back to the old value - see the Roles row's own comment above. -->
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
                                <visible>!String.IsEmpty(ListItem.Label2)</visible>
                                <posx>0</posx>
                                <posy>{{ vscale(399) }}</posy>
                                <width>240</width>
                                <height>{{ vscale(30) }}</height>
                                <font>font10</font>
                                <align>center</align>
                                <textcolor>99FFFFFF</textcolor>
                                <label>$INFO[ListItem.Label2]</label>
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
                <focusedlayout width="272">
                    <control type="group">
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
                                    <scroll>Control.HasFocus(404)</scroll>
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
                                    <scroll>Control.HasFocus(404)</scroll>
                                    <visible>!String.IsEmpty(ListItem.Label2)</visible>
                                    <posx>0</posx>
                                    <posy>{{ vscale(399) }}</posy>
                                    <width>240</width>
                                    <height>{{ vscale(30) }}</height>
                                    <font>font10</font>
                                    <align>center</align>
                                    <textcolor>99FFFFFF</textcolor>
                                    <label>$INFO[ListItem.Label2]</label>
                                </control>
                            </control>
                            <control type="image">
                                <visible>Control.HasFocus(404)</visible>
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
        <!-- /COLLECTION HUB 0 -->

        <!-- COLLECTION HUB 1 -->
        <control type="group" id="505">
            <visible>Integer.IsGreater(Container(405).NumItems,0) + String.IsEmpty(Window.Property(drawing))</visible>
            <defaultcontrol>405</defaultcontrol>
            <width>1920</width>
            <height>{{ vscale(525) }}</height>
            <control type="label">
                <posx>61</posx>
                <posy>0</posy>
                <width>1000</width>
                <height>{{ vscale(80) }}</height>
                <font>font30_title</font>
                <align>left</align>
                <aligny>center</aligny>
                <!-- Same normalized heading style as Roles/Extras/Related above (2026-09-04, on
                     request) - see the Roles label's own comment. -->
                <textcolor>FFD2CCCE</textcolor>
                <shadowcolor>66000000</shadowcolor>
                <label>$INFO[Window.Property(collection.header.1)]</label>
            </control>
            <control type="fixedlist" id="405">
                <!-- 53, not 0 (width shrunk to match) - see the Related list's own comment above, identical margin math. -->
                <posx>53</posx>
                <posy>{{ vscale(22) }}</posy>
                <width>1867</width>
                <height>{{ vscale(500) }}</height>
                <onup>404</onup>
                <ondown>406</ondown>
                <!-- noop was a leftover from a template shared with the bidirectional episode carousel:
                     these paginators (RelatedPaginator/CollectionPaginator) always start at offset=0 and
                     never produce a left-boundary marker, so there's no pagination state for noop to
                     protect here - safe to route straight to the sidebar. -->
                <onleft>9000</onleft>
                <onright>noop</onright>
                <scrolltime>200</scrolltime>
                <orientation>horizontal</orientation>
                <!-- Focus pinned to the row's first slot, the row scrolling under it - the same as
                     Recommended's hub rows (script-plex-recommended.xml.tpl, which explains the tail).
                     movement = itemsPerPage - 1, itemsPerPage being (1867 - 272) / 272 + 1 = 6: the last
                     items spread to the last whole slot, where this row, a plain list before, left them. -->
                <focusposition>0</focusposition>
                <movement>5</movement>
                <preloaditems>4</preloaditems>
                <itemlayout width="272">
                    <control type="group">
                        <!-- 5, back to the old value - see the Roles row's own comment above. -->
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
                                <visible>!String.IsEmpty(ListItem.Label2)</visible>
                                <posx>0</posx>
                                <posy>{{ vscale(399) }}</posy>
                                <width>240</width>
                                <height>{{ vscale(30) }}</height>
                                <font>font10</font>
                                <align>center</align>
                                <textcolor>99FFFFFF</textcolor>
                                <label>$INFO[ListItem.Label2]</label>
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
                <focusedlayout width="272">
                    <control type="group">
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
                                    <scroll>Control.HasFocus(405)</scroll>
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
                                    <scroll>Control.HasFocus(405)</scroll>
                                    <visible>!String.IsEmpty(ListItem.Label2)</visible>
                                    <posx>0</posx>
                                    <posy>{{ vscale(399) }}</posy>
                                    <width>240</width>
                                    <height>{{ vscale(30) }}</height>
                                    <font>font10</font>
                                    <align>center</align>
                                    <textcolor>99FFFFFF</textcolor>
                                    <label>$INFO[ListItem.Label2]</label>
                                </control>
                            </control>
                            <control type="image">
                                <visible>Control.HasFocus(405)</visible>
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
        <!-- /COLLECTION HUB 1 -->

        <!-- COLLECTION HUB 2 -->
        <control type="group" id="506">
            <visible>Integer.IsGreater(Container(406).NumItems,0) + String.IsEmpty(Window.Property(drawing))</visible>
            <defaultcontrol>406</defaultcontrol>
            <width>1920</width>
            <height>{{ vscale(525) }}</height>
            <control type="label">
                <posx>61</posx>
                <posy>0</posy>
                <width>1000</width>
                <height>{{ vscale(80) }}</height>
                <font>font30_title</font>
                <align>left</align>
                <aligny>center</aligny>
                <!-- Same normalized heading style as Roles/Extras/Related above (2026-09-04, on
                     request) - see the Roles label's own comment. -->
                <textcolor>FFD2CCCE</textcolor>
                <shadowcolor>66000000</shadowcolor>
                <label>$INFO[Window.Property(collection.header.2)]</label>
            </control>
            <control type="fixedlist" id="406">
                <!-- 53, not 0 (width shrunk to match) - see the Related list's own comment above, identical margin math. -->
                <posx>53</posx>
                <posy>{{ vscale(22) }}</posy>
                <width>1867</width>
                <height>{{ vscale(500) }}</height>
                <onup>405</onup>
                <!-- noop was a leftover from a template shared with the bidirectional episode carousel:
                     these paginators (RelatedPaginator/CollectionPaginator) always start at offset=0 and
                     never produce a left-boundary marker, so there's no pagination state for noop to
                     protect here - safe to route straight to the sidebar. -->
                <onleft>9000</onleft>
                <onright>noop</onright>
                <scrolltime>200</scrolltime>
                <orientation>horizontal</orientation>
                <!-- Focus pinned to the row's first slot, the row scrolling under it - the same as
                     Recommended's hub rows (script-plex-recommended.xml.tpl, which explains the tail).
                     movement = itemsPerPage - 1, itemsPerPage being (1867 - 272) / 272 + 1 = 6: the last
                     items spread to the last whole slot, where this row, a plain list before, left them. -->
                <focusposition>0</focusposition>
                <movement>5</movement>
                <preloaditems>4</preloaditems>
                <itemlayout width="272">
                    <control type="group">
                        <!-- 5, back to the old value - see the Roles row's own comment above. -->
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
                                <visible>!String.IsEmpty(ListItem.Label2)</visible>
                                <posx>0</posx>
                                <posy>{{ vscale(399) }}</posy>
                                <width>240</width>
                                <height>{{ vscale(30) }}</height>
                                <font>font10</font>
                                <align>center</align>
                                <textcolor>99FFFFFF</textcolor>
                                <label>$INFO[ListItem.Label2]</label>
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
                <focusedlayout width="272">
                    <control type="group">
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
                                    <scroll>Control.HasFocus(406)</scroll>
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
                                    <scroll>Control.HasFocus(406)</scroll>
                                    <visible>!String.IsEmpty(ListItem.Label2)</visible>
                                    <posx>0</posx>
                                    <posy>{{ vscale(399) }}</posy>
                                    <width>240</width>
                                    <height>{{ vscale(30) }}</height>
                                    <font>font10</font>
                                    <align>center</align>
                                    <textcolor>99FFFFFF</textcolor>
                                    <label>$INFO[ListItem.Label2]</label>
                                </control>
                            </control>
                            <control type="image">
                                <visible>Control.HasFocus(406)</visible>
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
        <!-- /COLLECTION HUB 2 -->
    </control>
</control>
{% endblock content %}