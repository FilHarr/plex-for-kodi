{% extends "default.xml.tpl" %}
{% block content %}
<!-- Fixed-position hub row stack: whichever hub is logically focused always renders at the anchor's
     fixed position (HomeWindow.ANCHOR_ABS_Y, 424) - home.py rotates which of 5 physical row
     controls (403/401/400/402/404, permanently ordered offsets -2 to +2 from focus -
     HomeWindow.HUB_ROTATION_RING) currently plays that role, and every other role, as focus moves,
     rather than there being one physical control per hub actually scrolled, or content being
     rebound to match a fixed role every move (an earlier version of this design did that, and paid
     for it in visible texture-swap ghosting whenever a hub's data moved to a *different* physical
     control - see docs/notes/home-hub-fixed-focus-position-status.md for the full history, including
     three earlier <animation>-based attempts at a fixed clip line that failed, and why nesting hub
     rows as items inside one native vertical list is impossible - Kodi gives item-template content
     no real, addressable control identity, confirmed live, RuntimeError: Non-Existent Control).
     Because content stays glued to whichever control it's already bound to, all 5 controls are kept
     loaded at all times, so whichever one is about to become newly visible on any given transition
     already holds correct, previously-loaded content. id="50" is kept on the outer control because
     default.xml.tpl's header controls target it directly via <ondown>50</ondown>. -->
<!-- Outer clip: a grouplist (grouplist clips its children, a plain group doesn't - see
     script-plex-episodes.xml.tpl:271's own comment). Base position is y=135 (not y=424, the
     anchor's own resting position - see group 51's own posy below for how that's preserved) -
     permanently wide enough to show peek-above (folded in as a child of group 51 below, at its own
     fixed relative offset) - peek-above has no <visible> condition of its own any more; whether
     it's shown falls out entirely from where this clip's own boundary currently sits (see its own
     comment). Only the has-hero-art case still needs the clip to narrow *down* from this base (see
     the animation below) - a control's clip rect reliably follows its own current position
     (confirmed by this control's own behavior, and by the original pre-redesign row-0 mechanism),
     which is why the clip and the row content deliberately live on separate controls (this one
     clips, never moves on its own initiative beyond the one animation below; inner group 51 is what
     Python actually slides - see HomeWindow._startHubSlide()/_settleHubSlide()).
     Kept as id="50" since default.xml.tpl's header controls target it directly via
     <ondown>50</ondown> - only needs to route focus into 51 via defaultcontrol, never itself
     addressed from Python (grouplist controls aren't - see the id=502/Part 5 comment below). -->
<control type="grouplist" id="50">
    <!-- Keyed on no_hero_art alone, deliberately NOT also on hub.sliding: nudge the clip down from
         its y=135 base to a FIXED y=456 (a shift of +321 - must match HomeWindow.HUB_SLIDE_CLIP_SHIFT_HERO
         exactly) so the sliding row's own title/images, which otherwise briefly sweep through that
         band on their way past 424, never render above the hero summary text. 456 was originally
         chosen as the hero summary textbox's real bottom (431, at the time) + a gap (matching
         HomeWindow.ROW_GAP) - but that's a one-time starting point, not a relationship this value
         tracks: the user wants y=456 kept as-is even as the hero-info detail elements
         (clearlogo/meta row/summary) keep getting repositioned - see HUB_SLIDE_CLIP_SHIFT_HERO's own
         comment in home.py. Don't recompute 321 to match wherever the summary currently sits. No
         corresponding no-hero-art animation is needed - the clip is already at its widest (y=135) by
         default, so there's nothing further to shift to for that case.

         Tying this to no_hero_art rather than hub.sliding is what makes it only ever animate when
         hero-art status actually *changes* - for the overwhelmingly common case (moving between two
         hubs that both have or both lack hero art), this control is already sitting at the correct
         position from before the transition started, so it doesn't move at all during the slide.
         Found live: gating this on hub.sliding as well made it re-evaluate on *every* vertical move
         regardless of whether hero-art status changed, producing a spurious re-apply (harmless once
         this is instant, but still pointless work) on ordinary same-state transitions.

         time="0": this control's own move must be instant, not eased. This control shifts THIS
         control (50), which 51 - the Python-positioned row content - is nested inside, so the shift
         also adds directly to 51's own on-screen position (nested controls always render at
         parent-position + own-local-offset). HomeWindow._setNoHeroArt() counter-shifts 51's own
         local offset by this same signed amount, in the very same synchronous call that flips the
         no_hero_art property this animation is keyed on - so as long as THIS animation is also
         instant, both moves land in the same rendered frame and the anchor's absolute position never
         leaves ANCHOR_ABS_Y, not even for one intermediate frame. Was time="150" tween="sine"
         easing="inout" originally; with 51's own counter-shift applied instantly (see
         _setNoHeroArt()) but this control still easing over 150ms, the two were out of sync for that
         whole window - the entire row stack visibly swung through the full 321px difference before
         settling, on top of whatever the ordinary hub-to-hub row slide was already doing. Precedent
         for instant Conditional repositioning elsewhere in this codebase: seasons_meta_row.xml.tpl,
         script-plex-seasons.xml.tpl:261. -->
    <animation effect="slide" end="0,321" time="0"
               condition="String.IsEmpty(Window.Property(no_hero_art))">Conditional</animation>

    <defaultcontrol>51</defaultcontrol>
    <!-- posx=100, not 55: the sidebar rail is drawn on top (see its own comment in default.xml.tpl's
         header block) - this leaves room for the collapsed rail's icon column. Row title/item
         layout insets below have their own posx reduced by the same 45px this moved right, to keep
         resting positions unchanged (60->15, 55->10). -->
    <posx>100</posx>
    <posy>{{ vscale(135) }}</posy>
    <width>2085</width>
    <!-- 945 = 1080 (screen bottom) - 135 (this control's own base posy) - reaches to the bottom of
         the screen. Not compensated when the animation above shifts this control's own posy down
         by 321 - height stays fixed, so the clip's bottom edge (456+945=1401) also shifts down,
         comfortably past the screen bottom regardless, so nothing is newly clipped there. -->
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
             genuinely handing off control once Python had set it explicitly. HomeWindow now owns
             this control's position unconditionally and exclusively - every bind/slide/settle call
             (_bindAllHubSlots()/_startHubSlide()/_settleHubSlide()) always sets it explicitly via
             setPosition(), from HomeWindow.GROUP51_BASELINE_OFFSET (289) as the true absolute
             local-offset target, not a value added on top of anything else. The one gap this
             leaves: before HomeWindow's first bind ever runs, grouplist 50 auto-stacks this,
             its only child, flush to 0 (ignoring this declared posy, same as always) - a one-frame
             flash at init, corrected the instant onFirstInit's own first bind runs. -->
        <defaultcontrol>500</defaultcontrol>
        <posx>0</posx>
        <posy>{{ vscale(289) }}</posy>
        <width>2085</width>
        <height>{{ vscale(425) }}</height>
        <usecontrolcoords>true</usecontrolcoords>

        <!-- All 5 wrappers (500-504, wrapping list controls 400-404) share one uniform shape -
             wrapper > "has items" inner group > title label + list - since under rotation any of
             the 5 controls can end up playing any role (two-above/peek-above/anchor/peek-below/
             two-below) at different times, not just its original one.

             Position/height are Python-managed (HomeWindow._setRoleGeometry()/_roleLocalY(), called
             from _bindAllHubSlots()/_startHubSlide()/_finishHubSlide()) - the posy/height declared
             below are just the pre-bind fallback, matching whichever role this control starts in.
             Every role's Y is computed by the same one recurrence, walked outward from the anchor
             (fixed at HomeWindow.ANCHOR_ABS_Y, 424) in whichever direction is needed: each row's Y
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

             Title visibility only needs one remaining role signal: HomeWindow writes the currently-
             focused control's own id to hub.anchor_id as roles rotate, and each title's own
             condition compares against that (see below) - hidden only for the anchor's own title,
             and only during a has-hero-art slide (protects the separate hero-summary-text overlay -
             unrelated to cropping, still real even though hero art is currently force-disabled for
             this testing phase). Peek-above's title needs no special hiding of its own any more
             either - at H >= 364px (every real display type clears this with margin - tightest is
             square/no-second-line at 395, a 31px margin worth keeping in mind if a shorter display
             type is ever added), the title is naturally clipped away the same way the art is, for
             the same reason. -->
        {% for id, decl_posy, decl_height in ((503, -800, 277), (501, -289, 277), (500, 0, 425), (502, 489, 167), (504, 950, 167)) %}
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
                         unless this control is currently the anchor (hub.anchor_id) AND a
                         has-hero-art slide is in progress - peek-above/peek-below never hide their
                         title for this reason (String.IsEmpty(hub.sliding) | !String.IsEmpty(no_hero_art):
                         only the has-hero-art case needs hiding during a slide - see grouplist 50's
                         own comment for why the sweep-through-the-summary problem only exists then).
                         Peek-above's title needs no separate hide at all any more - it's naturally
                         clipped away the same way the art is (see this block's own comment). -->
                    <visible>!String.IsEqual(Window.Property(hub.anchor_id), {{ id - 100 }}) | [String.IsEmpty(Window.Property(hub.sliding)) | !String.IsEmpty(Window.Property(no_hero_art))]</visible>
                    <posx>15</posx>
                    <posy>0</posy>
                    <width>1000</width>
                    <height>{{ vscale(87) }}</height>
                    <font>font13</font>
                    <align>left</align>
                    <aligny>center</aligny>
                    <textcolor>FFFFFFFF</textcolor>
                    <shadowcolor>66000000</shadowcolor>
                    <label>[B]$INFO[Window.Property(hub.{{ id - 100 }})][/B]</label>
                </control>
                <control type="list" id="{{ id - 100 }}">
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
    <height>{{ vscale(135) }}</height>
    <control type="group">
        <visible>Player.HasAudio + String.IsEmpty(Window(10000).Property(script.plex.theme_playing))</visible>
        <posx>438</posx>
        <posy>0</posy>
        <control type="button" id="204">
            <visible>Player.HasAudio + String.IsEmpty(Window(10000).Property(script.plex.theme_playing))</visible>
            <posx>-10</posx>
            <posy>{{ vscale(38) }}</posy>
            <width>260</width>
            <height>{{ vscale(75) }}</height>
            <onleft>9001</onleft>
            <ondown>50</ondown>
            <font>font12</font>
            <textcolor>FFFFFFFF</textcolor>
            <focusedcolor>FF000000</focusedcolor>
            <align>right</align>
            <aligny>center</aligny>
            <texturefocus colordiffuse="FFE5A00D" border="10">script.plex/white-square-rounded.png</texturefocus>
            <texturenofocus>-</texturenofocus>
            <textoffsetx>100</textoffsetx>
            <textoffsety>0</textoffsety>
            <label> </label>
        </control>
        <control type="image">
            <posx>0</posx>
            <posy>{{ vscale(48) }}</posy>
            <width>42</width>
            <height>{{ vscale(42) }}</height>
            <texture>$INFO[Player.Art(thumb)]</texture>
        </control>

        <control type="group">
            <visible>!Control.HasFocus(204)</visible>
            <control type="label">
                <posx>53</posx>
                <posy>{{ vscale(48) }}</posy>
                <width>187</width>
                <height>{{ vscale(20) }}</height>
                <font>font10</font>
                <align>left</align>
                <aligny>center</aligny>
                <textcolor>FFFFFFFF</textcolor>
                <info>MusicPlayer.Artist</info>
            </control>
            <control type="label">
                <posx>53</posx>
                <posy>{{ vscale(72) }}</posy>
                <width>187</width>
                <height>{{ vscale(20) }}</height>
                <font>font10</font>
                <align>left</align>
                <aligny>center</aligny>
                <textcolor>FFFFFFFF</textcolor>
                <info>MusicPlayer.Title</info>
            </control>
        </control>
        <control type="group">
            <visible>Control.HasFocus(204)</visible>
            <control type="label">
                <posx>53</posx>
                <posy>{{ vscale(48) }}</posy>
                <width>187</width>
                <height>{{ vscale(20) }}</height>
                <font>font10</font>
                <align>left</align>
                <aligny>center</aligny>
                <textcolor>FF000000</textcolor>
                <info>MusicPlayer.Artist</info>
            </control>
            <control type="label">
                <posx>53</posx>
                <posy>{{ vscale(72) }}</posy>
                <width>187</width>
                <height>{{ vscale(20) }}</height>
                <font>font10</font>
                <align>left</align>
                <aligny>center</aligny>
                <textcolor>FF000000</textcolor>
                <info>MusicPlayer.Title</info>
            </control>
        </control>

        <control type="progress">
            <description>Progressbar</description>
            <posx>0</posx>
            <posy>{{ vscale(102) }}</posy>
            <width>240</width>
            <height>{{ vscale(1) }}</height>
            <texturebg colordiffuse="9AFFFFFF">script.plex/white-square-1px.png</texturebg>
            <lefttexture>-</lefttexture>
            <midtexture colordiffuse="FFCC7B19">script.plex/white-square-1px.png</midtexture>
            <righttexture>-</righttexture>
            <overlaytexture>-</overlaytexture>
            <info>Player.Progress</info>
        </control>
    </control>
    <control type="label">
        <right>60</right>
        <posy>{{ vscale(35) }}</posy>
        <width>200</width>
        <height>{{ vscale(65) }}</height>
        <font>font12</font>
        <align>right</align>
        <aligny>center</aligny>
        <textcolor>FFFFFFFF</textcolor>
        <label>$INFO[System.Time]</label>
    </control>
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
    <visible>String.IsEmpty(Window.Property(busy)) + !String.IsEmpty(Window.Property(no.content))</visible>
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
        <label>[B]$ADDON[script.plexmod 32452][/B]</label>
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
        <label>$ADDON[script.plexmod 32453]</label>
    </control>
</control>

<control type="group">
    <visible>String.IsEmpty(Window.Property(busy)) + !String.IsEmpty(Window.Property(loading.content))</visible>
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
        <label>[B]$ADDON[script.plexmod 34020][/B]</label>
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
        <label>[B]$ADDON[script.plexmod 34021][/B]</label>
    </control>
</control>

<control type="group">
    <visible>!String.IsEmpty(Window.Property(busy))</visible>
    <animation effect="fade" start="0" end="100">Visible</animation>
    <posx>840</posx>
    <posy>{{ vscale(465) }}</posy>
    <control type="image">
        <posx>0</posx>
        <posy>0</posy>
        <width>240</width>
        <height>{{ vscale(150) }}</height>
        <texture>script.plex/busy-back.png</texture>
        <colordiffuse>A0FFFFFF</colordiffuse>
    </control>
    <control type="image">
        <posx>75</posx>
        <posy>{{ vscale(56) }}</posy>
        <width>90</width>
        <height>{{ vscale(38) }}</height>
        <texture diffuse="script.plex/busy-diffuse.png">script.plex/busy.gif</texture>
    </control>
</control>


<!-- TODO(consistency pass): posy was 155, matching pre_play's own group id=50 exactly (see below) -
     now 135 (top edge flush with the header's own bottom) so the clearlogo/title can move up into
     the freed space; meta row/summary were each bumped +20 to stay anchored at their old absolute
     position. pre_play itself is untouched, so that parity claim is no longer true - decide whether
     to nudge pre_play's own group to match, or drop the parity claim, next time this is revisited. -->
<!-- Focused hub item info overlay - clearlogo/title, meta row and summary, matching pre_play's own
     details block (script-plex-pre_play.xml.tpl) exactly: same posx=52/posy=155 group offset as
     pre_play's own group id=50, same inner posx=60 controls, so this reads as the same UI language
     rather than a reinvention. No rating row here (Home has no single focused video the way pre_play
     does - ratings would only make sense per-hub-item and there's no room to duplicate the rating
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
    <!-- no_hero_art (HomeWindow.updateHeroFrom, home.py): hide the whole overlay - not just the
         art box in default_background.xml.tpl - for items with no real background art (Photos,
         many Music artists/albums), rather than showing text describing art that isn't there. -->
    <visible>!String.IsEmpty(Window.Property(title)) + String.IsEmpty(Window.Property(no_hero_art))</visible>
    <posx>52</posx>
    <posy>{{ vscale(135) }}</posy>
    <height>{{ vscale(296) }}</height>
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
    <control type="image">
        <visible>!String.IsEmpty(Window.Property(clear.logo))</visible>
        <posx>60</posx>
        <posy>0</posy>
        <width>616</width>
        <height>{{ vscale(109) }}</height>
        <aspectratio align="left" aligny="bottom">keep</aspectratio>
        <texture background="true">$INFO[Window.Property(clear.logo)]</texture>
    </control>
    {% include "includes/pp_meta_row.xml.tpl" %}
    <control type="textbox">
        <posx>60</posx>
        <posy>{{ vscale(201) }}</posy>
        <width>708</width>
        <height>{{ vscale(90) }}</height>
        <font>font12</font>
        <align>left</align>
        <textcolor>FFD2CCCE</textcolor>
        <shadowcolor>66000000</shadowcolor>
        <scrolltime>200</scrolltime>
        <autoscroll delay="2000" time="2000" repeat="10000"/>
        <label>$INFO[Window.Property(summary)]</label>
    </control>
</control>

{% include "includes/sidebar.xml.tpl" %}

<!-- Moved here (was nested inside header group 200 above) so the server/user dropdown popouts
     (groups 802/901) draw on top of the hero-info overlay and the sidebar rail, instead of behind
     them - Kodi draws later-declared siblings on top, and this include used to be the last thing
     inside group 200, which itself closes and gets painted over by every later block (hero-info
     overlay, then the rail). Absolute posx/posy inside sidebar_dropdowns.xml.tpl are unchanged by
     this move - group 200 was itself at posx=0/posy=0, so nothing there was actually relative to
     it. -->
{% include "includes/sidebar_dropdowns.xml.tpl" %}
{% endblock header %}
