{% extends "default.xml.tpl" %}
{# Stage B (quiet-orbiting-heron.md, Recommended-tab sharing) - near-verbatim copy of
   script-plex-home.xml.tpl's content+header structure, not a redesign. That layout has a
   long, hard-won history (docs/notes/home-hub-fixed-focus-position-status.md, three earlier
   <animation>-based attempts that failed) - reusing it directly avoids re-deriving geometry
   that's already been fought over once. Registered to a new window class (library.py) swapped
   in via LibraryWindow's contentMode='recommended' mechanism (Stage A), not to HomeWindow.

   No Python-side hub-fetch/rendering logic is wired to this yet (Stage C/D) - every
   Container(...)/Window.Property(...) reference below will evaluate empty/false until then,
   so this renders as an empty hub area, not a crash. onFocus()/onClick()/onReInit()
   (library.py) already short-circuit entirely for contentMode=='recommended' before touching
   any grid-specific attribute, so focusing/clicking these controls is inert, not unsafe.

   headers/defaultcontrol added, unlike script-plex-home.xml.tpl itself: HomeWindow's own
   onFirstInit() explicitly calls setFocusId() once real hub data loads, which is why it can
   get away without a window-level defaultcontrol. LibraryWindow's 'recommended' onFirstInit()
   branch doesn't do that yet (Stage C/D's job) - explicit here as the same defensive measure
   Stage A's placeholder needed for the same reason (live-confirmed as a Kodi crash on load
   without it, once before). #}
{% block headers %}<defaultcontrol>50</defaultcontrol>{% endblock %}
{% block content %}
<!-- Fixed-position hub row stack: whichever hub is logically focused always renders at the anchor's
     fixed position (LibraryWindow.ANCHOR_ABS_Y, 486) - library.py rotates which of 4 physical row
     controls (401/400/402/403, permanently ordered offsets -1 to +2 from focus -
     LibraryWindow.HUB_ROTATION_RING) currently plays that role, and every other role, as focus moves,
     rather than there being one physical control per hub actually scrolled, or content being
     rebound to match a fixed role every move (an earlier version of this design did that, and paid
     for it in visible texture-swap ghosting whenever a hub's data moved to a *different* physical
     control - see docs/notes/home-hub-fixed-focus-position-status.md for the full history, including
     three earlier <animation>-based attempts at a fixed clip line that failed, and why nesting hub
     rows as items inside one native vertical list is impossible - Kodi gives item-template content
     no real, addressable control identity, confirmed live, RuntimeError: Non-Existent Control).
     Because content stays glued to whichever control it's already bound to, all 4 controls are kept
     loaded at all times, so whichever one is about to become newly visible on any given transition
     already holds correct, previously-loaded content. id="50" is kept on the outer control because
     default.xml.tpl's header controls target it directly via <ondown>50</ondown>. -->
<!-- Outer clip: a grouplist (grouplist clips its children, a plain group doesn't - see
     script-plex-episodes.xml.tpl:271's own comment). Fixed at y=518 (not y=486, the anchor's own
     resting position - see group 51's own posy below for how that's preserved): the top edge of
     this clip is what stops the sliding rows' titles/images rendering up over the hero summary
     text above (they'd otherwise sweep through that band on their way past 486). 518 = 456 (the
     original target, chosen as the hero summary textbox's real bottom at the time, 431, + a
     ROW_GAP) + 92 - 30, each step in lockstep with ANCHOR_ABS_Y's own (+92 dropping the rows,
     then -30 raising them on request, 2026-09-20 - nothing above the rows moved that time, only
     this clip line and the stack) - a one-time starting point, not a relationship this value
     tracks: keep it as-is even as the hero-info detail elements (clearlogo/meta row/summary)
     get repositioned. Peek-above (folded in as a child of group 51
     below, at its own fixed relative offset) has no <visible> condition of its own; whether it's
     shown falls out entirely from where this clip's boundary sits (see its own comment).
     A control's clip rect reliably follows its own current position (confirmed by this control's
     own behavior, and by the original pre-redesign row-0 mechanism), which is why the clip and
     the row content deliberately live on separate controls (this one clips and never moves;
     inner group 51 is what Python positions - see LibraryWindow.onFirstInit()).
     History: this used to sit at y=135 with a Conditional slide to 548 keyed on no_hero_art,
     back when the hero overlay was only shown for movie/TV items and the rows moved up to fill
     the space otherwise. The overlay is unconditional now, so the position is baked in.
     Kept as id="50" since default.xml.tpl's header controls target it directly via
     <ondown>50</ondown> - only needs to route focus into 51 via defaultcontrol, never itself
     addressed from Python (grouplist controls aren't - see the id=502/Part 5 comment below). -->
<control type="grouplist" id="50">
    <defaultcontrol>51</defaultcontrol>
    <!-- posx=105, not 55: the sidebar rail is drawn on top (see its own comment in default.xml.tpl's
         header block) - this leaves room for the collapsed rail's icon column, moved right again on
         request (100->105) to put the clip edge at x=105. Row title/item layout insets below have
         their own posx reduced by the same 50px total this moved right, to keep resting positions
         unchanged (60->10, 55->5). -->
    <posx>105</posx>
    <posy>{{ vscale(518) }}</posy>
    <width>2085</width>
    <!-- Deliberately taller than the 562 that would reach the screen bottom exactly: 945 is the
         height this control always had (1080 - its old y=135 base), left uncompensated when it
         slid to 548, so the clip's bottom edge was already past the screen - in every live
         state with the overlay showing. Kept identical rather than tightened. -->
    <height>{{ vscale(945) }}</height>
    <usecontrolcoords>true</usecontrolcoords>
    <orientation>vertical</orientation>
    <itemgap>0</itemgap>

    <control type="group" id="51">
        <!-- Slide right while the sidebar rail is expanded (focused), so hub content doesn't sit under the labels -->
        <animation effect="slide" end="220,0" time="200" tween="sine" easing="inout" condition="ControlGroup(9000).HasFocus(0)">Conditional</animation>

        <!-- posy is declared here for documentation only. group 51 is grouplist 50's only direct
             child (no spacer sibling any more - a previous round used one to get this control's
             resting offset "for free" from the grouplist's own auto-stacking, but that produced a
             persistent ~289-308px too-low offset that survived even after every other variable was
             eliminated, consistent with the grouplist's auto-stack re-applying its own computed
             contribution on top of whatever this control's own posy already held, rather than
             genuinely handing off control once Python had set it explicitly. LibraryWindow owns
             this control's position exclusively - onFirstInit() sets it on every 'recommended'
             entry via setPosition(), to LibraryWindow.GROUP51_BASELINE_OFFSET (-32: 518 + -32 =
             486, ANCHOR_ABS_Y) as the true absolute local-offset target, not a value added on
             top of anything else. Since step 11 in the navigation review it's also what a slide
             moves: the wrappers inside it sit at fixed places in one tall stack, and this
             control's offset brings the focused row to the anchor line (_group51Y()). The one gap
             this leaves: before that first setPosition() runs, grouplist
             50 auto-stacks this, its only child, flush to 0 (ignoring this declared posy, same as
             always) - a one-frame flash at init. -->
        <defaultcontrol>500</defaultcontrol>
        <posx>0</posx>
        <posy>{{ vscale(-32) }}</posy>
        <width>2085</width>
        <height>{{ vscale(425) }}</height>
        <usecontrolcoords>true</usecontrolcoords>

        <!-- All 4 wrappers (500-503, wrapping list controls 400-403) share one uniform shape -
             wrapper > "has items" inner group > title label + list - since under rotation any of
             the 4 controls can end up playing any role (above/anchor/peek-below/below) at
             different times, not just its original one. Four, not five: see
             LibraryWindow.HUB_ROTATION_RING's own comment for why -1..+2 is every role a slide
             ever shows.

             Position/height are Python-managed (LibraryWindow._setRoleGeometry()/_stackY(), called
             from _bindAllHubSlots()/_startHubSlide()) - the posy/height declared below are just the
             pre-bind fallback, matching whichever role this control starts in. Each wrapper sits at
             its hub's place in one tall stack measured from the first hub, and group 51's offset
             brings the focused row to the anchor (LibraryWindow.ANCHOR_ABS_Y, 486); relative to the
             anchor, every row lands where the same one recurrence puts it: each row's Y
             is its neighbor's Y, plus or minus that neighbor's own real rendered content height
             (HomeWindow.ROW_CONTENT_HEIGHT, keyed by display type) plus a fixed gap
             (HomeWindow.ROW_GAP) - not a fixed constant for peek-above and a dynamic one for
             peek-below, which is what this used to do and is exactly what made peek-above need a
             separate, manual per-type crop to fake the same result a real clip already produces once
             positions are consistent (see below).

             This is also what crops peek-above's own content - not a manual per-type posy override
             any more (removed; see hub_itemlayout_poster/square/ar16x9.xml.tpl and the matching
             hub_focusedlayout_* files, each back down to one rendered variant). Once peek-above's Y
             is computed by the same stacking rule peek-below already used, its *bottom* edge always
             lands at exactly ANCHOR_ABS_Y - ROW_GAP regardless of the row's own real height (height
             only ever affects the top edge) - and grouplist 50's own real clip (the only actual clip
             in this whole hierarchy, y=135 to the screen bottom) cuts off whatever pokes out above
             that, for free, at whatever position the row is *currently* at, every frame - no second,
             separately-animated piece of state (a crop property) that could ever fall out of sync
             with position, at any point mid-slide, the way the old per-type override could.

             Title visibility only needs one remaining role signal: Python writes the currently-
             focused control's own id to hub.anchor_id as roles rotate, and each title's own
             condition compares against that (see below) - hidden only for the anchor's own title,
             and only during a slide (protects the separate hero-summary-text overlay - unrelated
             to cropping). Peek-above's title needs no special hiding of its own any more
             either - at H >= 364px (every real display type clears this with margin - tightest is
             square/no-second-line at 395, a 31px margin worth keeping in mind if a shorter display
             type is ever added), the title is naturally clipped away the same way the art is, for
             the same reason. -->
        {% for id, decl_posy, decl_height in ((501, -289, 277), (500, 0, 425), (502, 489, 167), (503, 950, 167)) %}
        <control type="group" id="{{ id }}">
            <posx>0</posx>
            <posy>{{ vscale(decl_posy) }}</posy>
            <width>1920</width>
            <height>{{ vscale(decl_height) }}</height>
            <usecontrolcoords>true</usecontrolcoords>
            {% if id == 500 %}<defaultcontrol>400</defaultcontrol>{% endif %}
            <control type="group">
                <visible>Integer.IsGreater(Container({{ id - 100 }}).NumItems,0) + String.IsEmpty(Window.Property(drawing))</visible>
                <width>1920</width>
                <height>{{ vscale(decl_height) }}</height>
                <control type="label">
                    <!-- See this whole block's own comment above for the full reasoning. Visible
                         unless this control is currently the anchor (hub.anchor_id) AND a slide
                         is in progress - peek-above/peek-below never hide their title for this
                         reason (see grouplist 50's own comment for the sweep-through-the-summary
                         problem this guards against). Peek-above's title needs no separate hide
                         at all any more - it's naturally clipped away the same way the art is
                         (see this block's own comment). -->
                    <visible>!String.IsEqual(Window.Property(hub.anchor_id), {{ id - 100 }}) | String.IsEmpty(Window.Property(hub.sliding))</visible>
                    <posx>10</posx>
                    <posy>0</posy>
                    <width>1000</width>
                    <height>{{ vscale(87) }}</height>
                    <!-- font30_title: InterUI at font13's own 30px but with a real
                         <style>bold</style> (skin.plextuary's font.xml) - the [B] markup this
                         used on font13 never rendered visibly bold. -->
                    <font>font30_title</font>
                    <align>left</align>
                    <aligny>center</aligny>
                    <textcolor>FFD2CCCE</textcolor>
                    <shadowcolor>66000000</shadowcolor>
                    <label>$INFO[Window.Property(hub.{{ id - 100 }})]</label>
                </control>
                <!-- fixedlist, not list (on request, 2026-09-21): the focused item stays pinned
                     at the row's start and the row scrolls under it, instead of the focus walking
                     across the screen and only scrolling once it hits the right edge. focusposition
                     0 is that pin; movement is how far the cursor may leave it, which Kodi only
                     lets happen at the row's tail (GUIFixedListContainer::SelectItem(): once the
                     remaining items fit in the cursor range they spread across the last slots
                     rather than scrolling on into blank space) or for a row short enough to fit
                     entirely (GetCursorRange() shrinks the range to the item count - no scroll at
                     all). The effective range is min(movement, itemsPerPage), itemsPerPage being
                     (width - item width) / item width + 1: 7 for 272-wide poster/square items,
                     3 for 544-wide 16:9 ones, so movement=5 gives a range of 5 (last poster in
                     the 6th slot) and 3 (last 16:9 tile in the 4th slot, the partially visible
                     one) respectively. The 16:9 case is a known, accepted compromise: one shared
                     control can't carry a per-display-type movement, and narrowing the width to
                     make itemsPerPage come out as 2 for 16:9 would clip the row short of the
                     screen edge (the list clips to its own box). It only shows on a 16:9 row
                     with more than 3 items, on its last few - and the only 16:9 rows left are
                     the home-video ones (home.videos.*/video.*), since the old episodes-only
                     home.continue hub was dropped the same day. -->
                <control type="fixedlist" id="{{ id - 100 }}">
                    <posx>0</posx>
                    <posy>{{ vscale(29) }}</posy>
                    <width>1920</width>
                    <height>{{ vscale(515) }}</height>
                    <!-- Vertical hub-to-hub navigation is handled entirely in Python
                         (HomeWindow.onAction intercepts MOVE_UP/MOVE_DOWN before native nav fires).
                         onleft exits to the sidebar - needed on all 5 now (any of them can be the
                         anchor), not just whichever used to be control 400. -->
                    <onup>noop</onup>
                    <ondown>noop</ondown>
                    <onleft>9001</onleft>
                    <onright>noop</onright>
                    <scrolltime>200</scrolltime>
                    <orientation>horizontal</orientation>
                    <focusposition>0</focusposition>
                    <movement>5</movement>
                    <preloaditems>4</preloaditems>

                    {% with hub_id = id - 100 %}
                    {% include "includes/hub_itemlayout_poster.xml.tpl" %}
                    {% include "includes/hub_itemlayout_square.xml.tpl" %}
                    {% include "includes/hub_itemlayout_ar16x9.xml.tpl" %}
                    {% include "includes/hub_focusedlayout_poster.xml.tpl" %}
                    {% include "includes/hub_focusedlayout_square.xml.tpl" %}
                    {% include "includes/hub_focusedlayout_ar16x9.xml.tpl" %}
                    {% endwith %}
                </control>
            </control>
        </control>
        {% endfor %}
    </control>
</control>

{% endblock content %}

{% block header %}
<control type="group" id="200">
    <posx>0</posx>
    <posy>0</posy>
    <width>1920</width>
    <height>{{ vscale(125) }}</height>
    <control type="label">
        <right>60</right>
        <posy>{{ vscale(30) }}</posy>
        <width>200</width>
        <height>{{ vscale(65) }}</height>
        <font>font12</font>
        <align>right</align>
        <aligny>center</aligny>
        <textcolor>FFFFFFFF</textcolor>
        <label>$INFO[System.Time]</label>
    </control>
    {# declared after the time label, same as default.xml.tpl's own copy of this group, so the
       popout below paints over the clock instead of the other way round - was declared before it
       here, which put the clock on top of the popout's own art/track-info card. #}
    <control type="group">
        <visible>Player.HasAudio + String.IsEmpty(Window(10000).Property(script.plex.theme_playing))</visible>
        {# 360r matches default.xml.tpl's own header widget - same collapsed-thumbnail/popout design,
           see that file's copy of this group for the full layout reasoning. onleft prefers the
           section-tabs row (320, includes/section_tabs.xml.tpl) when it's actually on screen - the
           symmetric return path for that row's own onright into this widget - falling back to the
           sidebar rail (9001), same as library.xml.tpl's own copy of this group, when there's no
           tab row (a 'mixed' section) to land on. #}
        <posx>360r</posx>
        <posy>0</posy>
        {# Collapsed to just the art thumbnail: 63x63, rounded through square-mask.png with the mask pinned
           to the control's own bounds - the corner treatment the music library's track rows use
           (includes/track_row.xml.tpl), at a smaller size. Centred in the 135px header (36 above and
           below). No zoom on focus - the ring below is the whole focus treatment. #}
        <control type="group">
            <control type="button" id="204">
                <posx>0</posx>
                <posy>{{ vscale(31) }}</posy>
                <width>63</width>
                <height>{{ vscale(63) }}</height>
                <onleft condition="Control.IsVisible(320)">320</onleft>
                <onleft>9001</onleft>
                <ondown>50</ondown>
                <texturefocus>-</texturefocus>
                <texturenofocus>-</texturenofocus>
                <label> </label>
            </control>
            <control type="image">
                <posx>0</posx>
                <posy>{{ vscale(31) }}</posy>
                <width>63</width>
                <height>{{ vscale(63) }}</height>
                <texture diffuse="script.plex/masks/square-mask.png">$INFO[Player.Art(thumb)]</texture>
                <aspectratio scalediffuse="false">scale</aspectratio>
            </control>
            {# Focus ring: the music grid's recipe (script-plex-squares.xml.tpl) - a flat white square diffused
               through an RGBA ring mask, tinted FFE9A20D, in a box 6px larger than the art at -3 on both axes.
               Its own mask rather than the shared ring-mask-square.png, though: that one is a 3px ring at its
               488px authored size, which scales to ~0.4px in a 69px box and all but disappears. This mask is
               authored at 69px native with a 2px ring, its corner radius square-mask.png's own (~2px at 63px)
               plus the 3px offset. selected.png's 9-slice border was rejected here long ago for the mirror-image
               reason - its stroke width is baked into the source pixels and can't be scaled down. #}
            <control type="image">
                <visible>Control.HasFocus(204)</visible>
                <posx>-3</posx>
                <posy>{{ vscale(28) }}</posy>
                <width>69</width>
                <height>{{ vscale(69) }}</height>
                <texture diffuse="script.plex/masks/ring-mask-square-69.png">script.plex/white-square.png</texture>
                <colordiffuse>FFE9A20D</colordiffuse>
            </control>
        </control>

        <control type="group">
            <visible>Control.HasFocus(204)</visible>
            <animation effect="fade" start="0" end="100" time="120" reversible="true">Visible</animation>
            {# Extends over the time label by design - this group is declared after it, so it draws on top rather
               than shifting it. Card is 75 tall around the 63px art (6px beyond it top and bottom), starting
               12px past the art's right edge; text/progress sit 15px inside it. Title over artist, both font8,
               in the track rows' colours (includes/track_row.xml.tpl): white title, AAFFFFFF artist. #}
            <control type="image">
                <posx>75</posx>
                <posy>{{ vscale(25) }}</posy>
                <width>260</width>
                <height>{{ vscale(75) }}</height>
                <texture colordiffuse="E0000000" border="10">script.plex/white-square-rounded.png</texture>
            </control>
            <control type="label">
                <posx>90</posx>
                <posy>{{ vscale(35) }}</posy>
                <width>230</width>
                <height>{{ vscale(20) }}</height>
                <font>font8</font>
                <align>left</align>
                <aligny>center</aligny>
                <textcolor>FFFFFFFF</textcolor>
                <info>MusicPlayer.Title</info>
            </control>
            <control type="label">
                <posx>90</posx>
                <posy>{{ vscale(59) }}</posy>
                <width>230</width>
                <height>{{ vscale(20) }}</height>
                <font>font8</font>
                <align>left</align>
                <aligny>center</aligny>
                <textcolor>AAFFFFFF</textcolor>
                <info>MusicPlayer.Artist</info>
            </control>
            <control type="progress">
                <description>Progressbar</description>
                <posx>90</posx>
                <posy>{{ vscale(89) }}</posy>
                <width>230</width>
                <height>{{ vscale(1) }}</height>
                <texturebg colordiffuse="9AFFFFFF">script.plex/white-square-1px.png</texturebg>
                <lefttexture>-</lefttexture>
                <midtexture colordiffuse="FFCC7B19">script.plex/white-square-1px.png</midtexture>
                <righttexture>-</righttexture>
                <overlaytexture>-</overlaytexture>
                <info>Player.Progress</info>
            </control>
        </control>
    </control>
    {# quiet-orbiting-heron.md plan item 0: ondown=50 targets grouplist 50's own <defaultcontrol>
       chain (already relied on elsewhere in this template) rather than a specific hub-list id -
       the rotation ring means which physical control is actually the anchor moves, so following
       the same defaultcontrol resolution the rest of this template already uses is more robust
       than hardcoding one. #}
    {% with tab_ondown = 50 %}{% include "includes/section_tabs.xml.tpl" %}{% endwith %}
</control>

<control type="group">
    <visible>!String.IsEmpty(Window.Property(search.dialog))</visible>
    <control type="group" >
        <visible>!String.IsEmpty(Window.Property(search.dialog.hasresults))</visible>
        <control type="image">
            <posx>0</posx>
            <posy>0</posy>
            <width>1920</width>
            <height>1080</height>
            <texture>script.plex/home/background-fallback.png</texture>
            {% include "includes/scale_background.xml.tpl" %}
        </control>
        <control type="image">
            <posx>0</posx>
            <posy>0</posy>
            <width>1920</width>
            <height>1080</height>
            <texture background="true">$INFO[Window.Property(background)]</texture>
            {% include "includes/scale_background.xml.tpl" %}
        </control>
    </control>
    <control type="image">
        <posx>0</posx>
        <posy>0</posy>
        <width>1920</width>
        <height>1080</height>
        <texture colordiffuse="99606060">script.plex/white-square.png</texture>
        {% include "includes/scale_background.xml.tpl" %}
    </control>
</control>

<control type="group">
    <visible>String.IsEmpty(Window.Property(busy)) + !String.IsEmpty(Window.Property(no.content)) + String.IsEmpty(Window.Property(server.unavailable))</visible>
    <posx>0</posx>
    <posy>{{ vscale(465) }}</posy>
    <control type="label">
        <scroll>false</scroll>
        <posx>60</posx>
        <posy>0</posy>
        <width>1800</width>
        <height>{{ vscale(35) }}</height>
        <font>font13</font>
        <align>center</align>
        <textcolor>FFFFFFFF</textcolor>
        <label>[B]$ADDON[script.plexmod 35132][/B]</label>
    </control>
    <control type="label">
        <scroll>false</scroll>
        <posx>60</posx>
        <posy>{{ vscale(60) }}</posy>
        <width>1800</width>
        <height>{{ vscale(35) }}</height>
        <font>font13</font>
        <align>center</align>
        <textcolor>FFCCCCCC</textcolor>
        <label>$ADDON[script.plexmod 35133]</label>
    </control>
</control>

<!-- Focused hub item info overlay - clearlogo/title, meta row and summary, matching pre_play's own
     details block (script-plex-pre_play.xml.tpl) exactly: same posx=52/posy=135 group offset as
     pre_play's own group id=50, same inner posx=61 controls (absolute x=113, the shared baseline
     Episodes/Seasons/Pre-play all use - see script-plex-episodes.xml.tpl's header block comment), so
     this reads as the same UI language rather than a reinvention. No rating row here (Home has no
     single focused video the way pre_play does - ratings would only make sense per-hub-item and
     there's no room to duplicate the rating
     row per hub), so the summary sits at pre_play's rating-row height (210) instead of its own
     summary height (252), filling the gap that would otherwise sit empty between the meta row and
     the hero art below. Driven entirely by the Window properties HomeWindow.setHeroInfo() sets on
     hub focus change (see home.py); hidden via the hide-via-empty-property idiom until the first hub
     item is focused. -->
<control type="group">
    <!-- Same slide-with-the-sidebar-rail animation as grouplist 50's hub content (see this file's
         own content block) - this overlay lives in the header block instead, as a sibling rather
         than a child of that grouplist, so it needs its own copy of the animation to move in sync
         rather than inheriting it. -->
    <animation effect="slide" end="220,0" time="200" tween="sine" easing="inout" condition="ControlGroup(9000).HasFocus(0)">Conditional</animation>
    <!-- no_hero_art (LibraryWindow._setNoHeroArt, library.py): hide the whole overlay - not just
         the art box in default_background.xml.tpl - while nothing is bound yet (fresh entry before
         the hubs land, or a section with no hubs). No longer a per-item-type gate: the overlay
         shows for every focused hub item, whatever its type. -->
    <visible>!String.IsEmpty(Window.Property(title)) + String.IsEmpty(Window.Property(no_hero_art))</visible>
    <posx>52</posx>
    <posy>{{ vscale(125) }}</posy>
    <height>{{ vscale(388) }}</height>
    <control type="label">
        <visible>String.IsEmpty(Window.Property(clear.logo)) + !String.IsEqual(Window.Property(hero.type),playlist) + !String.IsEqual(Window.Property(hero.type),album) + !String.IsEqual(Window.Property(hero.type),artist)</visible>
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
    <!-- Artist heading (on request, 2026-09-20): the Artist screen's own title control
         (script-plex-artist.xml.tpl) - font45_title, top-anchored 708x61 box at y=107 - but white
         rather than that screen's FFD2CCCE (on request, 2026-09-30). Artists never have a
         clearlogo, so this is their only heading. -->
    <control type="label">
        <visible>String.IsEqual(Window.Property(hero.type),artist)</visible>
        <posx>61</posx>
        <posy>{{ vscale(107) }}</posy>
        <width>708</width>
        <height>{{ vscale(61) }}</height>
        <font>font45_title</font>
        <align>left</align>
        <aligny>top</aligny>
        <scroll>true</scroll>
        <scrollspeed>35</scrollspeed>
        <textcolor>FFFFFFFF</textcolor>
        <label>$INFO[Window.Property(title)]</label>
    </control>
    <!-- Playlist heading (on request, 2026-09-20): the episode screen's own no-clearlogo title
         control (script-plex-episodes.xml.tpl - font45_title in a 61-tall bottom-anchored box,
         660 wide), landing at the same absolute bottom edge (125+48+61 = 234) as that screen's
         and as the font45 fallback above. Playlists never have a clearlogo, so this is their
         only heading; the items/runtime line below it sits where the episode title would. -->
    {% for hero_type, heading_width in (('playlist', 660), ('album', 900)) %}
    {# Albums (on request, 2026-09-30) take the same heading, 900 wide, with the album artist as
       the second line below it. #}
    <control type="label">
        <visible>String.IsEqual(Window.Property(hero.type),{{ hero_type }})</visible>
        <posx>61</posx>
        <posy>{{ vscale(48) }}</posy>
        <width>{{ heading_width }}</width>
        <height>{{ vscale(61) }}</height>
        <font>font45_title</font>
        <align>left</align>
        <aligny>bottom</aligny>
        <scroll>true</scroll>
        <scrollspeed>35</scrollspeed>
        <textcolor>FFFFFFFF</textcolor>
        <label>$INFO[Window.Property(title)]</label>
    </control>
    {% endfor %}
    <control type="image">
        <visible>!String.IsEmpty(Window.Property(clear.logo)) + String.IsEmpty(Window.Property(hero.small_logo))</visible>
        <posx>61</posx>
        <posy>0</posy>
        <width>722</width>
        <height>{{ vscale(162) }}</height>
        <aspectratio align="left" aligny="bottom">keep</aspectratio>
        <texture background="true">$INFO[Window.Property(clear.logo)]</texture>
    </control>
    <!-- Two-line variant (hero.small_logo - episodes and rolled-up seasons, see setHeroInfo(),
         library.py): smaller box, leaves room for the hero.subtitle line underneath it - see this
         group's own CLEAR_LOGO_DIM_EPISODE comment (library.py) for the budget. -->
    <control type="image">
        <visible>!String.IsEmpty(Window.Property(clear.logo)) + !String.IsEmpty(Window.Property(hero.small_logo))</visible>
        <posx>61</posx>
        <posy>0</posy>
        <width>660</width>
        <height>{{ vscale(98) }}</height>
        <aspectratio align="left" aligny="bottom">keep</aspectratio>
        <texture background="true">$INFO[Window.Property(clear.logo)]</texture>
    </control>
    <!-- Second line under the show's clearlogo - the episode title, or the season name for a
         rolled-up season item (hero.subtitle, setHeroInfo() - library.py; a playlist's
         "<n> items &#8226; <runtime>" uses the font30_title copy below instead): 19px gap below the 98px logo (13px original
         gap + 6px explicit drop), font32_title (bold variant, 32px - see this session's font-size
         math for the box budget - ~1.3x box-to-font ratio matching font10/height=vscale(30)
         elsewhere in this row) sized to that box. -->
    <control type="label">
        <visible>!String.IsEmpty(Window.Property(clear.logo)) + !String.IsEmpty(Window.Property(hero.small_logo))</visible>
        <posx>61</posx>
        <posy>{{ vscale(117) }}</posy>
        <width>660</width>
        <height>{{ vscale(51) }}</height>
        <font>font32_title</font>
        <align>left</align>
        <aligny>top</aligny>
        <scroll>true</scroll>
        <scrollspeed>35</scrollspeed>
        <textcolor>FFD2CCCE</textcolor>
        <label>$INFO[Window.Property(hero.subtitle)]</label>
    </control>
    <!-- Playlist/album copy of the line above: same slot and colour, font30_title instead of
         font32_title (on request) - a separate control only because a font can't be switched per
         item. -->
    <control type="label">
        <visible>String.IsEqual(Window.Property(hero.type),playlist) | String.IsEqual(Window.Property(hero.type),album)</visible>
        <posx>61</posx>
        <posy>{{ vscale(117) }}</posy>
        <width>660</width>
        <height>{{ vscale(51) }}</height>
        <font>font30_title</font>
        <align>left</align>
        <aligny>top</aligny>
        <scroll>true</scroll>
        <scrollspeed>35</scrollspeed>
        <textcolor>FFD2CCCE</textcolor>
        <label>$INFO[Window.Property(hero.subtitle)]</label>
    </control>
    {% include "includes/pp_meta_row.xml.tpl" %}
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
        <label>$INFO[Window.Property(summary)]</label>
    </control>
</control>

{% include "includes/server_unavailable.xml.tpl" %}

{% include "includes/sidebar.xml.tpl" %}

<!-- Sidebar declared last (not via default.xml.tpl's header_sidebar hook) so the server/user
     dropdown popouts (groups 802/901) and the rail itself draw on top of the hero-info overlay
     above, instead of behind it - matching script-plex-home.xml.tpl's own z-order exactly (see
     that file's own comment on this same pattern). -->
{% include "includes/sidebar_dropdowns.xml.tpl" %}
{% endblock header %}
