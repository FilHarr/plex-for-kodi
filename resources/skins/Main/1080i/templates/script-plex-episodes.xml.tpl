{% extends "default.xml.tpl" %}
{# Blanks the default Home/Search topleft nav and slots the persistent sidebar rail in its
   place instead - see script-plex-pre_play.xml.tpl's identical opt-in and the comment there
   explaining why the rail must be appended after super()'s header output rather than filled
   into default.xml.tpl's header_sidebar block (that block sits inside header group 200, which
   slides off-screen on scroll). Ids 201/202 (Home/Search there) are reused by the rail's
   server/user buttons, so onClick handling for those ids moves to the section list below. #}
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
    <animation effect="slide" end="0,{{ vscale(-125) }}" time="200" tween="quadratic" easing="out" condition="!String.IsEmpty(Window.Property(on.extras))">Conditional</animation>
    <!-- Slide right while the sidebar rail is expanded (focused), matching Home/Library/Pre-play -->
    <animation effect="slide" end="220,0" time="200" tween="sine" easing="inout" condition="ControlGroup(9000).HasFocus(0)">Conditional</animation>

    <animation type="Conditional" condition="Integer.IsGreater(Window.Property(hub.focus),0) + Control.IsVisible(500)" reversible="true">
        <!-- -540, not -500: grown by the same 40px the episode row + button row wrapper grew when the
             episode thumbnails were resized to match Extras' own art size (445x250 -> 512x288) - see the
             wrapping group's own "492 = 347 + 145" comment below for the full math. Mirrored in Python
             (EpisodesWindow.getRoleItemDDPosition(), episodes.py) since that drag-drop position math
             reads this same slide amount. -->
        <effect type="slide" end="0,{{ vscale(-540) }}" time="200" tween="quadratic" easing="out"/>
    </animation>

    <animation type="Conditional" condition="Integer.IsGreater(Window.Property(hub.focus),2) + Control.IsVisible(502)" reversible="true">
        <effect type="slide" end="0,{{ vscale(-500) }}" time="200" tween="quadratic" easing="out"/>
    </animation>

    <ondown condition="!String.IsEmpty(Window.Property(disable_playback))">400</ondown>

    <!-- posx=60, not 0: clears the collapsed sidebar rail's icon column, matching the same
         resting-position shift pre_play/Library made when they adopted the rail. Every child
         below is positioned relative to this group, so the shift applies uniformly without
         touching any of their own pixel-tuned offsets. -->
    <posx>60</posx>
    <posy>{{ vscale(155) }}</posy>
    <!--<defaultcontrol>101</defaultcontrol>-->

    <control type="group">
        <posx>0</posx>
        <posy>0</posy>
        <width>1920</width>
        <height>{{ vscale(600) }}</height>
        <!-- Clearlogo/episode-title/metadata row: matches Recommended's own "focused hub item is an
             episode" treatment exactly (script-plex-recommended.xml.tpl's hero overlay - gated there on
             hero.type==episode, unconditional here since this screen only ever shows episodes). Ratings
             row and summary below match Seasons'/Pre-play's own instead (script-plex-seasons.xml.tpl).
             All of it lands at absolute x=113, matching the episode row/Roles/Extras below (see their
             own comments) rather than Recommended's/Seasons' own raw x=112/115 - group 50's own posx=60
             here + each control's own posx=53 reaches that column. Same idea on the y axis: group 50's own posy is still the
             old 155 here (Seasons/Pre-play tuned theirs to 135 - see that control's own comment - but
             moving Episodes' group 50 to match would shift the episode carousel/buttons/Roles/Extras
             below it too, well beyond this block), so every posy below is each reference screen's own
             raw value minus 20 to land at the same absolute y those screens reach with theirs. -->
        <control type="label">
            <visible>String.IsEmpty(Window.Property(clear.logo))</visible>
            <posx>53</posx>
            <posy>{{ vscale(-20) }}</posy>
            <width>616</width>
            <height>{{ vscale(109) }}</height>
            <font>font45</font>
            <align>left</align>
            <aligny>bottom</aligny>
            <scroll>true</scroll>
            <scrollspeed>35</scrollspeed>
            <textcolor>FFFFFFFF</textcolor>
            <label>$INFO[Container(400).ListItem.Property(show.title)]</label>
        </control>
        <!-- 660x98, not the old 1440x106: matches Recommended's own episode-variant clearlogo box exactly
             (CLEAR_LOGO_DIM_EPISODE, library.py) - leaves room for the episode-title line below it,
             replacing the old small always-on episode-name line that used to sit above the logo. -->
        <control type="image">
            <visible>!String.IsEmpty(Window.Property(clear.logo))</visible>
            <posx>53</posx>
            <posy>{{ vscale(-20) }}</posy>
            <width>660</width>
            <height>{{ vscale(98) }}</height>
            <aspectratio align="left" aligny="bottom">keep</aspectratio>
            <texture background="true">$INFO[Window.Property(clear.logo)]</texture>
        </control>
        <!-- Episode title, sitting under the show's clearlogo - matches Recommended's own episode-variant
             title label exactly (position, size, font, color). Only shown alongside the logo, same as
             Recommended's own: its no-logo fallback (the label above) has no room for a second line
             either. -->
        <control type="label">
            <visible>!String.IsEmpty(Window.Property(clear.logo))</visible>
            <posx>53</posx>
            <posy>{{ vscale(97) }}</posy>
            <width>660</width>
            <height>{{ vscale(51) }}</height>
            <font>font32_title</font>
            <align>left</align>
            <aligny>top</aligny>
            <scroll>true</scroll>
            <scrollspeed>35</scrollspeed>
            <textcolor>FFD2CCCE</textcolor>
            <label>$INFO[Container(400).ListItem.Property(title)]</label>
        </control>

        <!-- Metadata row: matches Recommended's/Pre-play's own includes/pp_meta_row.xml.tpl exactly
             (position, font, color) - not included directly since that file reads Window.Property, and
             this row needs to track whichever episode is currently focused in the carousel instead
             (Container(400).ListItem.Property). Genre is new here, between date and content rating,
             formatted the same way Pre-play's own genres.short is (first 2 genres, comma-joined - see
             EpisodesWindow.updateProperties()/setItemInfo(), episodes.py). -->
        <control type="grouplist">
            <posx>53</posx>
            <posy>{{ vscale(155) }}</posy>
            <width>708</width>
            <height>{{ vscale(30) }}</height>
            <align>left</align>
            <itemgap>0</itemgap>
            <orientation>horizontal</orientation>
            <usecontrolcoords>true</usecontrolcoords>
            <control type="label">
                <width>auto</width>
                <height>{{ vscale(30) }}</height>
                <font>font10</font>
                <align>left</align>
                <textcolor>FFD2CCCE</textcolor>
                <shadowcolor>66000000</shadowcolor>
                <label>$INFO[Container(400).ListItem.Property(duration)]$INFO[Container(400).ListItem.Property(date), &#8226; ]$INFO[Container(400).ListItem.Property(genres.short), &#8226; ]$INFO[Container(400).ListItem.Property(content.rating), &#8226; ]</label>
            </control>
            <control type="button">
                <visible>!String.IsEmpty(Container(400).ListItem.Property(remainingTime))</visible>
                <posx>10</posx>
                <width>auto</width>
                <height>{{ vscale(30) }}</height>
                <font>font10</font>
                <align>center</align>
                <aligny>top</aligny>
                <focusedcolor>FFE5A00D</focusedcolor>
                <textcolor>FFE5A00D</textcolor>
                <textoffsetx>15</textoffsetx>
                <texturefocus colordiffuse="40000000" border="8">script.plex/white-square-rounded-top-padded.png</texturefocus>
                <texturenofocus colordiffuse="40000000" border="8">script.plex/white-square-rounded-top-padded.png</texturenofocus>
                <label>$INFO[Container(400).ListItem.Property(remainingTime)]</label>
            </control>
            <control type="button">
                <visible>!String.IsEmpty(Container(400).ListItem.Property(unavailable))</visible>
                <posx>10</posx>
                <width>auto</width>
                <height>{{ vscale(30) }}</height>
                <font>font10</font>
                <align>center</align>
                <aligny>top</aligny>
                <focusedcolor>FFFFFFFF</focusedcolor>
                <textcolor>FFFFFFFF</textcolor>
                <textoffsetx>15</textoffsetx>
                <texturefocus colordiffuse="FFAC3223" border="8">script.plex/white-square-rounded-top-padded.png</texturefocus>
                <texturenofocus colordiffuse="FFAC3223" border="8">script.plex/white-square-rounded-top-padded.png</texturenofocus>
                <label>$ADDON[script.plexmod 32312]</label>
            </control>
        </control>

        <!-- Ratings row: matches Seasons' own exactly (script-plex-seasons.xml.tpl) - one icon+label pair
             per rating the item actually has (populateRatings(), lib/windows/mixins/ratings.py - already
             called per-episode in EpisodesWindow.setItemInfo(), episodes.py), replacing the old top-right
             rating/rating2-only pair. rating1..rating6 must match RatingsMixin.MAX_RATINGS exactly - not
             templated from that constant, this loop's own range() has to be kept in sync by hand if it
             ever changes. -->
        <control type="grouplist">
            <visible>{% for i in range(1, 7) %}{% if i > 1 %}| {% endif %}!String.IsEmpty(Container(400).ListItem.Property(rating{{ i }})){% endfor %}</visible>
            <posx>53</posx>
            <posy>{{ vscale(199) }}</posy>
            <width>708</width>
            <height>{{ vscale(32) }}</height>
            <align>left</align>
            <itemgap>5</itemgap>
            <orientation>horizontal</orientation>
            <usecontrolcoords>true</usecontrolcoords>
            {% for i in range(1, 7) %}
            <control type="group">
                <visible>!String.IsEmpty(Container(400).ListItem.Property(rating{{ i }}))</visible>
                <width>91</width>
                <height>{{ vscale(32) }}</height>
                <control type="image">
                    <posx>0</posx>
                    <posy>1</posy>
                    <width>40</width>
                    <height>{{ vscale(30) }}</height>
                    <texture fallback="script.plex/ratings/other/image.rating.png">$INFO[Container(400).ListItem.Property(rating{{ i }}.image)]</texture>
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
                    <label>$INFO[Container(400).ListItem.Property(rating{{ i }})]</label>
                </control>
            </control>
            {% endfor %}
            <control type="image">
                <visible>!String.IsEmpty(Container(400).ListItem.Property(rating.stars))</visible>
                <posy>6</posy>
                <width>134</width>
                <height>{{ vscale(22) }}</height>
                <texture>script.plex/stars/$INFO[Container(400).ListItem.Property(rating.stars)].png</texture>
            </control>
        </control>

        <control type="textbox">
            <!-- Matches Seasons'/Pre-play's own summary box exactly (position, size, font, color) - was
                 60,200,1080x152,font12,FFFFFFFF,no shadow. -->
            <posx>53</posx>
            <posy>{{ vscale(257) }}</posy>
            <width>813</width>
            <height>{{ vscale(90) }}</height>
            <font>font10</font>
            <align>left</align>
            <textcolor>FFD2CCCE</textcolor>
            <shadowcolor>66000000</shadowcolor>
            <scrolltime>200</scrolltime>
            <autoscroll delay="2000" time="2000" repeat="10000">true</autoscroll>
            <label>$INFO[Container(400).ListItem.Property(summary)]</label>
        </control>

        <!-- Video/audio/subtitles pill row, shared with pre_play (see includes/media_info_pills.xml.tpl).
             posx=1095 is 1920 (screen width) minus the row's own 765 width minus 60 to cancel out group
             50's own +60 sidebar-clearance shift, so its right edge still sits flush with the screen's
             right edge like it did before the sidebar (see group 50's own posx comment above, and
             pre_play's identical -60 treatment of this same include). posy=425 is no longer tied to the
             button row's own position at all (it used to track it, matching pre_play's own 47px-below-
             the-button-row convention, but drifted from that over a few earlier requests this session) -
             set directly on request instead, to land its top edge at absolute y=580 (group 50's own
             posy=155 + this 425 = 580). That puts it above the episode row's own top (absolute y=640, see
             that group's own comment), not below the buttons any more. propref reads off the currently-
             focused episode row item instead of the window, since this screen has one row per episode
             rather than pre_play's single video. -->
        {% include "includes/media_info_pills.xml.tpl" with posx=1095 & posy=425 & propref="Container(400).ListItem.Property" %}

    </control>

    <!-- EPISODES -->
    <!-- The episode row and its play button row are core to the episode being viewed, not supplementary info
         like Roles/Reviews/Extras below (grouplist 60, which auto-stacks by height and doesn't reliably honor
         a child's own posy as extra gap - a nested grouplist attempt here caused Roles to overlap the episode
         row instead of stacking after it). A plain group has none of that ambiguity: children always render
         at exactly the posx/posy they declare, same as the title/summary panel above. This group is a sibling
         of grouplist 60 within group 50 (matching pre_play/seasons, where grouplist 60 is likewise nested
         inside group 50 rather than being a top-level control) - posy is relative to group 50's own origin
         (155), not the window. 463 again, back up from the 443 it was dropped to on the previous
         request (see git history for the fuller back-and-forth before that): an unfocused card's own
         art (this row's own posy 0 + fixedlist's 18 + itemlayout's own outer group posy 4) tops out at
         absolute y=640 (155 + 463 + 0 + 18 + 4 = 640) again. The button row below has its own separate
         posy (see its own comment) - this time deliberately moved the opposite way to compensate, so
         it stays at the same absolute position it was already at rather than moving with this group.
         grouplist 60 (Roles) below was, again, deliberately left where it was. -->
    <control type="group">
        <posx>0</posx>
        <posy>{{ vscale(463) }}</posy>
        <width>1920</width>
        <!-- 452 = 307 (button row's own posy below, see its comment) + 145 (buttons) -->
        <height>{{ vscale(452) }}</height>

        <!-- Trying fixedlist again (see the child control's own comment below for focusposition=1/
             movement=1 vs the old dead-center focusposition=2) rather than the plain list Seasons' own
             season row uses (script-plex-seasons.xml.tpl id 400) - the focused item anchors to a fixed
             near-left cell instead of moving with the rest of the row. 500 is a clipping mask (grouplist
             clips its children, a plain group doesn't); the fixedlist inside it fills that mask directly
             (posx=0, width matching 500's own 1875) - focusposition=1 doesn't need the oversized/negative-
             shifted box the old dead-center version required, since the anchor cell isn't the middle one.
             500's own onup/ondown/onleft/onright are still required here (duplicated onto the child list
             too): a grouplist wrapper doesn't automatically forward its child's direction rules for keys
             outside its own orientation axis - same reason the buttongroup grouplists (300/1300) below
             define their own onup/ondown rather than relying on their buttons'.

             posx=45, not 0 (width shrunk from 1920 to 1875 to match, keeping the right edge fixed): clip
             edge lands at absolute x=105 (group 50's own posx=60 + this 45), matching Seasons' own clip
             line exactly (see Seasons' list 400's own comment). Also still gives departing thumbnails room
             to clear the collapsed sidebar rail's icon column before this grouplist's own clip boundary
             cuts them off, same rationale as Home's identical fix for its hub posters (script-plex-
             home.xml.tpl's grouplist 50, posx 55->100) - see that file's own comment for the full
             rationale. Kept even though this row is no longer fixed-center: departing items still scroll
             past this same left edge as the list pages, so the same sidebar-icon clearance concern still
             applies.

             onleft: noop while the focused item is the left-pagination boundary marker (Container(400)
             reads off whichever item currently has focus, same pattern the info row above uses) - pressing
             left there must stay put so EpisodesPaginator's boundaryHit check (onAction) fires and loads
             the previous page instead of the rail stealing focus mid-pagination. Once truly at the first
             episode (no boundary marker left to land on), onleft falls through to the sidebar (9000).
             onright stays an unconditional hard stop, same idiom as Roles/Extras/Related/Seasons' own season
             row below - past the last episode there's nothing to page to on the right that would need the
             same escape hatch, and a plain list with no onright would otherwise wrap natively to the first
             item instead of stopping. -->
        <control type="grouplist" id="500">
            <posx>45</posx>
            <posy>0</posy>
            <visible>Integer.IsGreater(Container(400).NumItems,0) + String.IsEmpty(Window.Property(drawing))</visible>
            <height>{{ vscale(400) }}</height>
            <width>1875</width>
            <usecontrolcoords>true</usecontrolcoords>
            <orientation>horizontal</orientation>
            <itemgap>0</itemgap>
            <onup condition="Control.IsVisible(205)">205</onup>
            <onup condition="Control.IsVisible(206)">206</onup>
            <onup>200</onup>
            <ondown condition="Control.IsVisible(300)">300</ondown>
            <ondown condition="Control.IsVisible(1300)">1300</ondown>
            <ondown>402</ondown>
            <onleft condition="!String.IsEmpty(Container(400).ListItem.Property(left.boundary))">noop</onleft>
            <onleft>9000</onleft>
            <onright>noop</onright>
            <control type="fixedlist" id="400">
                <!-- Trying fixedlist again, focusposition=1/movement=1 this time - not the old focusposition=2
                     dead-center pin (which needed the list oversized to 5 cells wide and negative-shifted to
                     keep that center cell fixed, see this row's git history). focusposition=1 anchors the
                     focused item to the SECOND cell of this fixedlist's own box (index 1, 0-based) instead of
                     the middle, so no oversizing/negative-shift is needed - posx/width stay a plain fit
                     against the clipping mask, same as this row's own plain-list version. movement=1 is
                     required alongside focusposition, not optional: a fixedlist with focusposition set but no
                     movement tag pins the list at its first loaded item and never actually scrolls its
                     underlying content to bring focusposition's cell into place, leaving blank space past the
                     end - live-verified elsewhere in this codebase (see git history for the fix). -->
                <focusposition>1</focusposition>
                <movement>1</movement>
                <posx>0</posx>
                <posy>{{ vscale(18) }}</posy>
                <width>1875</width>
                <height>{{ vscale(400) }}</height>
                <onup condition="Control.IsVisible(205)">205</onup>
                <onup condition="Control.IsVisible(206)">206</onup>
                <onup>200</onup>
                <ondown condition="Control.IsVisible(300)">300</ondown>
                <ondown condition="Control.IsVisible(1300)">1300</ondown>
                <ondown>402</ondown>
                <onleft condition="!String.IsEmpty(Container(400).ListItem.Property(left.boundary))">noop</onleft>
                <onleft>9000</onleft>
                <onright>noop</onright>
                <scrolltime>200</scrolltime>
                <orientation>horizontal</orientation>
                <preloaditems>5</preloaditems>
                <!-- ITEM LAYOUT ########################################## -->
                <!-- 512x288 art (was 445x250) and a 544 cell width (was 475) - matches Extras' own art size
                     and inter-item gap (cell width minus art width = 32 on both rows now). Every pixel value
                     below the art itself that used to read 445/250 is grown by the same amount (badge/
                     indicator right-inset, title posy, boundary-marker centering); the leading margin below
                     (was 25, left over from this row's old fixed-center card-fan spacing) is now 5, dropping
                     art to x=113 (105 clip edge + 5 + the inner group's own unchanged 3) to line up with the
                     page's header column/Roles/Extras - see grouplist 500's own comment above for the clip
                     edge and the header block's own comment for the shared x=113 baseline. Gap stays 32
                     either way (cell width minus art width), just redistributed from mostly-leading (28/4)
                     to the same split Seasons' own poster row uses (8/24). -->
                <itemlayout width="544">
                    <control type="group">
                        <posx>5</posx>
                        <posy>{{ vscale(4) }}</posy>
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
                            <!-- Dims every non-focused thumbnail so the fixed-center item pops; itemlayout only
                                 renders for items that aren't focused, so no HasFocus condition is needed here.
                                 colordiffuse tints this same masked draw directly rather than stacking a second
                                 independently-masked overlay control on top - two separate draws each using
                                 ar16x9-mask.png's own anti-aliased rounded corners left a thin seam where the
                                 overlay's edge alpha didn't quite reach 1.0 while the bright art beneath it
                                 still did, showing as a sliver of full-brightness bleed-through on colorful
                                 corners. One draw means one edge falloff, so there's nothing left to mismatch.
                                 FF333333, not FF404040: colordiffuse multiplies this control's own rendered
                                 color (art * mask), it doesn't composite a second layer over it - alpha must
                                 stay FF (fully opaque) or the result blends toward whatever's behind the card
                                 instead of staying solid. RGB 0x33 (20% brightness) raises the dim strength to
                                 80% on request, up from the 75% (0x40, 25% brightness) it was dropped to on
                                 an earlier request - see git history for the further-back 90%/0x19 figure
                                 this was originally derived from. -->
                            <control type="image">
                                <posx>0</posx>
                                <posy>0</posy>
                                <width>512</width>
                                <height>{{ vscale(288) }}</height>
                                <texture background="true" diffuse="script.plex/masks/ar16x9-mask.png" fallback="$INFO[ListItem.Property(thumb.fallback)]">$INFO[ListItem.Thumb]</texture>
                                <aspectratio scalediffuse="false">scale</aspectratio>
                                <colordiffuse>FF333333</colordiffuse>
                            </control>
                            <!-- Inset pill, not the old flush-bottom bar: matches Recommended's/Seasons' own
                                 poster progress bar exactly (includes/hub_itemlayout_poster.xml.tpl, itself
                                 matching official Plex's own measured inset) - 8px in from the art's left/
                                 right/bottom edges, pill-shaped via progress-bar-mask.png (radius = half the
                                 bar's own 8px height). Track and fill share one identical 496x8 box (512 art
                                 width minus the 8px inset on each side) - the progress asset itself
                                 (util.getProgressImage(), $INFO[ListItem.Property(progress)]) is already a
                                 fixed-width strip with only its own left portion opaque, so masking it at
                                 full box size gives a clean rounded left cap and a plain straight-cut right
                                 edge wherever the fill ends, no separate inset needed for that. -->
                            <control type="group">
                                <visible>!String.IsEmpty(ListItem.Property(progress))</visible>
                                <posx>8</posx>
                                <posy>{{ vscale(272) }}</posy>
                                <control type="image">
                                    <posx>0</posx>
                                    <posy>0</posy>
                                    <width>496</width>
                                    <height>{{ vscale(8) }}</height>
                                    <texture diffuse="script.plex/masks/progress-bar-mask.png">script.plex/white-square.png</texture>
                                    <colordiffuse>E60A0F1A</colordiffuse>
                                </control>
                                <control type="image">
                                    <posx>0</posx>
                                    <posy>0</posy>
                                    <width>496</width>
                                    <height>{{ vscale(8) }}</height>
                                    <texture diffuse="script.plex/masks/progress-bar-mask.png">$INFO[ListItem.Property(progress)]</texture>
                                    <colordiffuse>FFE5A00D</colordiffuse>
                                </control>
                            </control>
                            <control type="group">
                                <visible>!String.IsEmpty(ListItem.Property(episode.number))</visible>
                                <posx>472</posx>
                                <posy>0</posy>
                                <control type="image">
                                    <!-- Paired look: watched-indicator badge is present to the left, so only the
                                         outer corner touching the poster needs rounding; the inner corner stays
                                         square for a flush seam between the two badges. Mirrors
                                         watched_indicator.xml.tpl's own two mutually-exclusive branches (dot style
                                         vs checkmark/count style, indicators.use_unwatched) plus its independent
                                         with_count block - not just a flat property check - since e.g. the
                                         'unwatched' property is set on every unwatched episode regardless of which
                                         style is active, but only actually drives a visible control under the dot
                                         style. -->
                                    <visible>{% if indicators.use_unwatched %}[!String.IsEmpty(ListItem.Property(unwatched)) + String.IsEmpty(ListItem.Property(watched))] | !String.IsEmpty(ListItem.Property(unwatched.count)){% else %}!String.IsEmpty(ListItem.Property(watched)) | !String.IsEmpty(ListItem.Property(unwatched.count)){% endif %}</visible>
                                    <posx>0</posx>
                                    <posy>0</posy>
                                    <width>40</width>
                                    <height>{{ vscale(32) }}</height>
                                    <texture diffuse="script.plex/masks/badge-mask-tr-only.png">script.plex/white-square.png</texture>
                                    <colordiffuse>{{ indicators.watched_bg|default("CC000000") }}</colordiffuse>
                                </control>
                                <control type="image">
                                    <!-- Standalone look: no watched-indicator badge to its left, so round both
                                         corners for a self-contained pill shape instead of a flush-seam pairing.
                                         Exact negation of the sibling control's own condition above. -->
                                    <visible>{% if indicators.use_unwatched %}[String.IsEmpty(ListItem.Property(unwatched)) | !String.IsEmpty(ListItem.Property(watched))] + String.IsEmpty(ListItem.Property(unwatched.count)){% else %}String.IsEmpty(ListItem.Property(watched)) + String.IsEmpty(ListItem.Property(unwatched.count)){% endif %}</visible>
                                    <posx>0</posx>
                                    <posy>0</posy>
                                    <width>40</width>
                                    <height>{{ vscale(32) }}</height>
                                    <texture diffuse="script.plex/masks/badge-mask-tr.png">script.plex/white-square.png</texture>
                                    <colordiffuse>{{ indicators.watched_bg|default("CC000000") }}</colordiffuse>
                                </control>
                                <control type="label">{# rendered big then zoomed down so it never truncates/ellipsizes at the badge's actual width #}
                                    <animation effect="zoom" start="33" end="33" time="0" reversible="false" center="auto" condition="true">Conditional</animation>
                                    <posx>-20</posx>
                                    <posy>{{ vscale(-8) }}</posy>
                                    <width>80</width>
                                    <height>{{ vscale(48) }}</height>
                                    <font>font32_title</font>
                                    <align>center</align>
                                    <aligny>center</aligny>
                                    <textcolor>{{ indicators.textcolor|default("FFFFFFFF") }}</textcolor>
                                    <label>$INFO[ListItem.Property(episode.number)]</label>
                                </control>
                            </control>
                            {% include "includes/watched_indicator.xml.tpl" with xoff=472 & uw_size=35 & wbg_w=40 & wbg="script.plex/masks/badge-mask-bl-only.png" %}

                            <control type="group">
                                <visible>!String.IsEmpty(ListItem.Property(is.boundary))</visible>
                                <control type="image">
                                    <posx>0</posx>
                                    <posy>0</posy>
                                    <width>512</width>
                                    <height>{{ vscale(288) }}</height>
                                    <texture colordiffuse="FF404040">script.plex/white-square.png</texture>
                                </control>
                                <control type="image">
                                    <visible>String.IsEmpty(ListItem.Property(is.updating)) + !String.IsEmpty(ListItem.Property(right.boundary))</visible>
                                    <posx>225.5</posx>
                                    <posy>{{ vscale(94) }}</posy>
                                    <width>61</width>
                                    <height>{{ vscale(100) }}</height>
                                    <texture colordiffuse="40000000">script.plex/indicators/chevron-white.png</texture>
                                </control>
                                <control type="image">
                                    <visible>String.IsEmpty(ListItem.Property(is.updating)) + !String.IsEmpty(ListItem.Property(left.boundary))</visible>
                                    <posx>225.5</posx>
                                    <posy>{{ vscale(94) }}</posy>
                                    <width>61</width>
                                    <height>{{ vscale(100) }}</height>
                                    <texture colordiffuse="40000000">script.plex/indicators/chevron-white-l.png</texture>
                                </control>
                                <control type="image">
                                    <visible>!String.IsEmpty(ListItem.Property(is.updating))</visible>
                                    <posx>192</posx>
                                    <posy>{{ vscale(80) }}</posy>
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
                        <posy>{{ vscale(4) }}</posy>
                        <control type="group">
                            <!-- 259,147 = 3 (border offset, the inner group's own unchanged posx below,
                                 not this outer group's) + half the new art size (512/2, 288/2) - was
                                 227.5,130 for the old 445x250 art, same formula. Zoom itself dropped from
                                 110% to 104%, not just the art size - matches Extras'/Roles' own focus zoom
                                 exactly, on request, so the focused-state footprint (and the gap it eats
                                 into neighboring cards) matches those rows too, not just the resting size. -->
                            <animation effect="zoom" start="100" end="104" time="100" center="259,{{ vscale(147) }}" reversible="false">Focus</animation>
                            <animation effect="zoom" start="104" end="100" time="100" center="259,{{ vscale(147) }}" reversible="false">UnFocus</animation>
                            <posx>0</posx>
                            <posy>0</posy>
                            <control type="image">
                                <visible>Control.HasFocus(400)</visible>
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
                                <!-- Inset pill, matching itemlayout's own copy above - see that control's own
                                     comment for the full reasoning. -->
                                <control type="group">
                                    <visible>!String.IsEmpty(ListItem.Property(progress))</visible>
                                    <posx>8</posx>
                                    <posy>{{ vscale(272) }}</posy>
                                    <control type="image">
                                        <posx>0</posx>
                                        <posy>0</posy>
                                        <width>496</width>
                                        <height>{{ vscale(8) }}</height>
                                        <texture diffuse="script.plex/masks/progress-bar-mask.png">script.plex/white-square.png</texture>
                                        <colordiffuse>E60A0F1A</colordiffuse>
                                    </control>
                                    <control type="image">
                                        <posx>0</posx>
                                        <posy>0</posy>
                                        <width>496</width>
                                        <height>{{ vscale(8) }}</height>
                                        <texture diffuse="script.plex/masks/progress-bar-mask.png">$INFO[ListItem.Property(progress)]</texture>
                                        <colordiffuse>FFE5A00D</colordiffuse>
                                    </control>
                                </control>
                                <control type="group">
                                    <visible>!String.IsEmpty(ListItem.Property(episode.number))</visible>
                                    <posx>472</posx>
                                    <posy>0</posy>
                                    <control type="image">
                                        <!-- See itemlayout's own copy of these two controls for the full reasoning. -->
                                        <visible>{% if indicators.use_unwatched %}[!String.IsEmpty(ListItem.Property(unwatched)) + String.IsEmpty(ListItem.Property(watched))] | !String.IsEmpty(ListItem.Property(unwatched.count)){% else %}!String.IsEmpty(ListItem.Property(watched)) | !String.IsEmpty(ListItem.Property(unwatched.count)){% endif %}</visible>
                                        <posx>0</posx>
                                        <posy>0</posy>
                                        <width>40</width>
                                        <height>{{ vscale(32) }}</height>
                                        <texture diffuse="script.plex/masks/badge-mask-tr-only.png">script.plex/white-square.png</texture>
                                        <colordiffuse>{{ indicators.watched_bg|default("CC000000") }}</colordiffuse>
                                    </control>
                                    <control type="image">
                                        <visible>{% if indicators.use_unwatched %}[String.IsEmpty(ListItem.Property(unwatched)) | !String.IsEmpty(ListItem.Property(watched))] + String.IsEmpty(ListItem.Property(unwatched.count)){% else %}String.IsEmpty(ListItem.Property(watched)) + String.IsEmpty(ListItem.Property(unwatched.count)){% endif %}</visible>
                                        <posx>0</posx>
                                        <posy>0</posy>
                                        <width>40</width>
                                        <height>{{ vscale(32) }}</height>
                                        <texture diffuse="script.plex/masks/badge-mask-tr.png">script.plex/white-square.png</texture>
                                        <colordiffuse>{{ indicators.watched_bg|default("CC000000") }}</colordiffuse>
                                    </control>
                                    <control type="label">{# rendered big then zoomed down so it never truncates/ellipsizes at the badge's actual width #}
                                        <animation effect="zoom" start="33" end="33" time="0" reversible="false" center="auto" condition="true">Conditional</animation>
                                        <posx>-20</posx>
                                        <posy>{{ vscale(-8) }}</posy>
                                        <width>80</width>
                                        <height>{{ vscale(48) }}</height>
                                        <font>font32_title</font>
                                        <align>center</align>
                                        <aligny>center</aligny>
                                        <textcolor>{{ indicators.textcolor|default("FFFFFFFF") }}</textcolor>
                                        <label>$INFO[ListItem.Property(episode.number)]</label>
                                    </control>
                                </control>
                                {% include "includes/watched_indicator.xml.tpl" with xoff=472 & uw_size=35 & wbg_w=40 & wbg="script.plex/masks/badge-mask-bl-only.png" %}

                                <control type="group">
                                    <visible>!String.IsEmpty(ListItem.Property(is.boundary))</visible>
                                    <control type="image">
                                        <posx>0</posx>
                                        <posy>0</posy>
                                        <width>512</width>
                                        <height>{{ vscale(288) }}</height>
                                        <texture colordiffuse="FF404040">script.plex/white-square.png</texture>
                                    </control>
                                    <control type="image">
                                        <visible>String.IsEmpty(ListItem.Property(is.updating)) + !String.IsEmpty(ListItem.Property(right.boundary))</visible>
                                        <posx>225.5</posx>
                                        <posy>{{ vscale(94) }}</posy>
                                        <width>61</width>
                                        <height>{{ vscale(100) }}</height>
                                        <texture colordiffuse="40000000">script.plex/indicators/chevron-white.png</texture>
                                    </control>
                                    <control type="image">
                                        <visible>String.IsEmpty(ListItem.Property(is.updating)) + !String.IsEmpty(ListItem.Property(left.boundary))</visible>
                                        <posx>225.5</posx>
                                        <posy>{{ vscale(94) }}</posy>
                                        <width>61</width>
                                        <height>{{ vscale(100) }}</height>
                                        <texture colordiffuse="40000000">script.plex/indicators/chevron-white-l.png</texture>
                                    </control>
                                    <control type="image">
                                        <visible>!String.IsEmpty(ListItem.Property(is.updating))</visible>
                                        <posx>192</posx>
                                        <posy>{{ vscale(80) }}</posy>
                                        <width>128</width>
                                        <height>{{ vscale(128) }}</height>
                                        <texture>script.plex/home/busy.gif</texture>
                                    </control>
                                </control>
                            </control>
                            <control type="image">
                                <visible>Control.HasFocus(400)</visible>
                                <posx>0</posx>
                                <posy>0.5</posy>
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
        <!-- EPISODES -->

        <!-- Sits directly below the episode row. Like pre_play's button row (see its own posy comment),
             these icons are 180x145 source art stretched into their box with no aspectratio, and the opaque
             glyph is roughly centered with ~37% padding above and below it - so the box's declared top isn't
             where the icon becomes visible. 307: independently tuned against the episode row group's own
             posy and the media-info pills row's own posy below (neither is tied to this value, nor vice
             versa - see git history for the back-and-forth between all three this session) - see this
             file's own comments if any of the three need to move in step again. -->
        {% block buttons %}
            <control type="group">
                <posy>{{ vscale(307) }}</posy>
                <width>1920</width>
                <height>{{ vscale(145) }}</height>
                <control type="grouplist" id="300">
                    <visible allowhiddenfocus="!String.IsEmpty(Container(400).ListItem.Property(media.multiple))">String.IsEmpty(Container(400).ListItem.Property(media.multiple)) + !String.IsEmpty(Window.Property(initialized)) + String.IsEmpty(Window.Property(disable_playback))</visible>
                    <defaultcontrol always="true">301</defaultcontrol>
                    <!-- 22, matching pre_play's no-poster button row x position -->
                    <posx>22</posx>
                    <posy>0</posy>
                    <width>1000</width>
                    <height>{{ vscale(200) }}</height>
                    <onup>400</onup>
                    <ondown>402</ondown>
                    <onleft>9000</onleft>
                    <itemgap>{{ theme.episodes.buttongroup.itemgap }}</itemgap>
                    <orientation>horizontal</orientation>
                    <scrolltime tween="quadratic" easing="out">200</scrolltime>
                    <usecontrolcoords>true</usecontrolcoords>

                    {% with attr = theme.episodes.buttons & template = "includes/themed_button.xml.tpl" %}
                        {% include template with name="info" & id=304 %}
                        {% include template with name="play" & id=301 & onleft=304 & onright=305 &
                            enable="!String.IsEmpty(Window.Property(current_item.loaded))" & visible="!String.IsEmpty(Window.Property(current_item.loaded))" &
                            allowhiddenfocus=True
                        %}
                        {% include template with name="play" & id=306 & onleft=304 & onright=305 &
                                            visible="String.IsEmpty(Window.Property(current_item.loaded))"
                        %}
                        {% include template with name="settings" & id=305 %}
                        {% include template with name="more" & id=303 %}
                        {% include template with name="shuffle" & id=302 %}
                    {% endwith %}
                </control>
                <control type="grouplist" id="1300">
                    <visible>!String.IsEmpty(Container(400).ListItem.Property(media.multiple)) + !String.IsEmpty(Window.Property(initialized)) + String.IsEmpty(Window.Property(disable_playback))</visible>
                    <defaultcontrol always="true">1301</defaultcontrol>
                    <!-- 22, matching pre_play's no-poster button row x position -->
                    <posx>22</posx>
                    <posy>0</posy>
                    <width>1000</width>
                    <height>{{ vscale(200) }}</height>
                    <onup>400</onup>
                    <ondown>402</ondown>
                    <onleft>9000</onleft>
                    <itemgap>{{ theme.episodes.buttongroup.itemgap }}</itemgap>
                    <orientation>horizontal</orientation>
                    <scrolltime tween="quadratic" easing="out">200</scrolltime>
                    <usecontrolcoords>true</usecontrolcoords>

                    {% with attr = theme.episodes.buttons & template = "includes/themed_button.xml.tpl" %}
                        {% include template with name="info" & id=1304 %}
                        {% include template with name="play" & id=1301 & onleft=1304 & onright=1305 &
                            enable="!String.IsEmpty(Window.Property(current_item.loaded))" & visible="!String.IsEmpty(Window.Property(current_item.loaded))" &
                            allowhiddenfocus=True
                        %}
                        {% include template with name="play" & id=1306 & onleft=1304 & onright=1307 &
                                            visible="String.IsEmpty(Window.Property(current_item.loaded))"
                        %}
                        {% include template with name="media" & id=1307 %}
                        {% include template with name="settings" & id=1305 %}
                        {% include template with name="more" & id=1303 %}
                        {% include template with name="shuffle" & id=1302 %}
                    {% endwith %}

                </control>
            </control>
        {% endblock %}
    </control>

    <!-- Roles/Extras: supplementary info, unlike the episode row and its buttons above. This grouplist
         auto-stacks its direct children (502/503) purely by height and skips them entirely when their
         <visible> condition is false, so an empty Roles section doesn't leave a gap before Extras. 865, not
         derived from the episode row group's own posy+height any more (it used to exactly equal 373 + 492,
         back when this row sat directly under it) - the episode row group was bumped down 90px on request
         (see that control's own comment) but this one was deliberately left in place, so the two are no
         longer adjacent the way the math used to imply; 865 is now just this row's own fixed value, relative
         to group 50's origin same as the episode row group above. There used to be a Related row (504) too,
         but it always duplicated Seasons' own Related row exactly - both pulled from the same show object
         via the same code path (see script-plex-seasons.xml.tpl) - so it was removed rather than kept in
         sync by hand on two screens. -->
    <control type="grouplist" id="60">
        <visible>!String.IsEmpty(Window.Property(initialized))</visible>
        <posx>0</posx>
        <posy>{{ vscale(865) }}</posy>
        <width>1920</width>
        <height>{{ vscale(1800) }}</height>

        <onup condition="Control.IsVisible(205)">205</onup>
        <onup condition="Control.IsVisible(206)">206</onup>
        <onup>200</onup>
        <!-- 5, not 0: matches Seasons' own Roles/Extras/Related gap (script-plex-seasons.xml.tpl id 60). -->
        <itemgap>5</itemgap>

        <!-- ROLES -->
        <control type="group" id="502">
            <visible>Integer.IsGreater(Container(402).NumItems,0) + String.IsEmpty(Window.Property(drawing))</visible>
            <defaultcontrol>402</defaultcontrol>
            <width>1920</width>
            <height>{{ vscale(400) }}</height>
            <control type="label">
                <!-- posx=53, not 60: lands at absolute x=113 (group 50's own posx=60 + this 53), matching
                     the episode row/header block's shared baseline above rather than Seasons' own raw
                     x=115 (its label sits directly on its own list's art start, see that control's own
                     comment) - see the list's own comment below for the matching clip-edge shift. Style
                     still matches Seasons: font12/FFE9E6E7/no shadow/no uppercase, not the old
                     FFFFFFFF+shadow+uppercase treatment. -->
                <posx>53</posx>
                <posy>{{ vscale(-20) }}</posy>
                <width>1000</width>
                <height>{{ vscale(80) }}</height>
                <font>font12</font>
                <align>left</align>
                <aligny>center</aligny>
                <textcolor>FFE9E6E7</textcolor>
                <label>[B]$ADDON[script.plexmod 33609][/B]</label>
            </control>
            <control type="list" id="402">
                <!-- posx=43, not 0 (width grown to match, keeping the right edge fixed): clip edge lands
                     at absolute x=103 (group 50's own posx=60 + this 43), 2px inside Seasons' own clip
                     line (x=105) so that art (itemlayout's own unchanged 5+5 margin) lands at x=113 -
                     matching the episode row/header block's shared baseline above, not Seasons' own raw
                     x=115. -->
                <posx>43</posx>
                <posy>0</posy>
                <width>1877</width>
                <height>{{ vscale(400) }}</height>
                <onup condition="Control.IsVisible(300)">300</onup>
                <onup condition="Control.IsVisible(1300)">1300</onup>
                <onup>400</onup>
                <ondown>403</ondown>
                <onleft>9000</onleft>
                <!-- Hard stop, not Kodi's native wrap-to-first-item - matches Seasons' own Roles list. -->
                <onright>noop</onright>
                <scrolltime>200</scrolltime>
                <orientation>horizontal</orientation>
                <preloaditems>4</preloaditems>
                <!-- ITEM LAYOUT ########################################## -->
                <!-- 244x244 art (was 200x200) and the thinner role-selected-thin.png focus ring below -
                     matches Seasons' own Roles row exactly on request. -->
                <itemlayout width="274">
                    <control type="group">
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
                        <posx>5</posx>
                        <posy>{{ vscale(61) }}</posy>
                        <control type="group">
                            <animation effect="zoom" start="100" end="104" time="100" center="127,{{ vscale(127) }}" reversible="false">Focus</animation>
                            <animation effect="zoom" start="104" end="100" time="100" center="127,{{ vscale(127) }}" reversible="false">UnFocus</animation>
                            <posx>0</posx>
                            <posy>0</posy>
                            <control type="image">
                                <visible>Control.HasFocus(402)</visible>
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
                                        <scroll>Control.HasFocus(402)</scroll>
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
                                        <scroll>Control.HasFocus(402)</scroll>
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
                                <visible>Control.HasFocus(402)</visible>
                                <posx>0</posx>
                                <posy>0</posy>
                                <width>254</width>
                                <height>{{ vscale(254) }}</height>
                                <texture>script.plex/buttons/role-selected-thin.png</texture>
                            </control>
                        </control>
                    </control>
                </focusedlayout>
            </control>
        </control>
        <!-- ROLES -->

        <!-- EXTRAS -->
        <control type="group" id="503">
            <visible>Integer.IsGreater(Container(403).NumItems,0) + String.IsEmpty(Window.Property(drawing))</visible>
            <!-- 450, not 360: matches Seasons' own bump (script-plex-seasons.xml.tpl id 502) when its art
                 grew to 512x288 (Pre-play's own recipe). -->
            <height>{{ vscale(450) }}</height>
            <width>1920</width>
            <control type="label">
                <!-- posx=53, style FFE9E6E7/no uppercase - matches Seasons' own Extras label style, but
                     lands at x=113 not Seasons' own x=115 (see the Roles label's own comment above). -->
                <posx>53</posx>
                <posy>0</posy>
                <width>800</width>
                <height>{{ vscale(80) }}</height>
                <font>font12</font>
                <align>left</align>
                <aligny>center</aligny>
                <textcolor>FFE9E6E7</textcolor>
                <label>[B]$INFO[Window.Property(extras.header)][/B]</label>
            </control>
            <control type="list" id="403">
                <!-- posx=43, not 0 (width grown to match) - lands at x=103, 2px inside Seasons' own clip
                     line so art reaches x=113, see the Roles list's own comment above. -->
                <posx>43</posx>
                <posy>{{ vscale(18) }}</posy>
                <width>1877</width>
                <height>{{ vscale(430) }}</height>
                <onup>402</onup>
                <!-- Self-loop, not a route to a Related row any more - Extras is the last row now that
                     Related has been removed from Episodes (it always duplicated Seasons' own Related row
                     exactly, since both pull from the same show object - see script-plex-seasons.xml.tpl). -->
                <ondown>403</ondown>
                <onleft>9000</onleft>
                <!-- Hard stop, not Kodi's native wrap-to-first-item - matches Seasons' own Extras list. -->
                <onright>noop</onright>
                <scrolltime>200</scrolltime>
                <orientation>horizontal</orientation>
                <preloaditems>4</preloaditems>
                <!-- ITEM LAYOUT ########################################## -->
                <!-- Art 299x168 -> 512x288, rounded-corner ar16x9 mask, duration badge, ring-mask focus
                     indicator, second line below the title for the extra type - matches Seasons' own
                     Extras row exactly (itself matching Pre-play's, script-plex-pre_play.xml.tpl). Cell
                     width 544, matching Seasons'/Pre-play's own value. -->
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
                                <visible>Control.HasFocus(403)</visible>
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
                                    <scroll>Control.HasFocus(403)</scroll>
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
                                 matches Seasons'/Pre-play's own Extras row exactly. -->
                            <control type="image">
                                <visible>Control.HasFocus(403)</visible>
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

    </control>
</control>
{% endblock content %}

{# widget sits at the header's far right, past the tabs, so the header runs tabs -> widget. There's no
   more header_search_onright override here - it used to wire the default Search button's (id 202)
   onright, but that button is gone now that header_topleft is blanked above (id 202 is the sidebar's
   user button instead), so overriding a tag nested inside markup that no longer renders would be
   dead code. #}
{% block header_audiowidget_onleft %}<onleft condition="Control.IsVisible(205)">205</onleft><onleft condition="Control.IsVisible(206)">206</onleft><onleft>9000</onleft>{% endblock %}

{% block header_middle_add %}
<!-- SEASON TABS -->
<!-- "Show" (pinned, no dataSource - see EpisodesWindow._showTabItem()/onClick(), episodes.py) followed
     by every season, plain type="list" rather than the old fixedlist center-pinned carousel - matches
     the identical row now on script-plex-seasons.xml.tpl (the show/season page this "Show" tab returns
     to) exactly, both technique and layout: see that file's own comment for the full reasoning ("Show"
     has to stay pinned at the visible left edge, which a center-focus carousel can't guarantee). posx=120,
     not the old 100: matches this screen's own content column exactly (group 50's own posx=60 + its
     children's own posx=60), so the tab row's left edge lines up with the title/summary below instead of
     sitting 20px left of it. width=1420 (120 + 1420 = 1540) fills the rest of the header out to the same
     right boundary this row always used - 20px shy of the audio widget's collapsed hitbox at
     1920-360=1560. -->
<control type="fixedlist" id="205">
    <!-- Used once there are more than 6 seasons (7+ tabs including "Show") - below that, sibling
         control 206 (a plain type="list") takes over instead; fillSeasons()'s altControlAttr
         (mixins/seasons.py, called from here with EpisodesWindow.SEASONS_CONTROL_ATTR_ALT) decides
         which of the two gets the items and always leaves the other empty so its own <visible> below
         keeps it hidden. See script-plex-seasons.xml.tpl's own copy of this row (its 205 control's
         comment) for why a type="fixedlist" needs this split at low item counts: it computes each
         item's on-screen slot from distance to BOTH ends of the list, and once total items <=
         itemsPerPage a plain list flush-aligns correctly where a fixedlist doesn't. focusposition=3
         makes items 0-3 render at their own natural, unscrolled position and starts scrolling exactly
         once focus reaches index 4 (the 5th item) - which only matters once there are enough tabs to
         fill the row, i.e. exactly the >6 case this control now handles. -->
    <visible>Integer.IsGreater(Container(205).NumItems,0)</visible>
    <!-- The old fixedlist wrapper never carried this (an existing gap, not intentional per
         includes/section_tabs.xml.tpl's own comment on why every header-row control needs its own copy) -
         added to match on this rewrite, same as the new copy on script-plex-seasons.xml.tpl. -->
    <animation effect="slide" end="220,0" time="200" tween="sine" easing="inout" condition="ControlGroup(9000).HasFocus(0)">Conditional</animation>
    <posx>120</posx>
    <posy>0</posy>
    <width>1420</width>
    <height>{{ vscale(135) }}</height>
    <focusposition>3</focusposition>
    <!-- See script-plex-seasons.xml.tpl's own copy of this row for why this is needed (without it,
         Kodi pins the focused item at the focusposition slot from the very first item, leaving blank
         space at the left instead of a tab). Live-verified at cell width 170 (movement=4). At 200,
         itemsPerPage=floor(1420/200)=7, so movement is capped at 3 (itemsPerPage-1-focusposition) -
         see seasons.xml.tpl's own comment on the maxCursor off-by-one this avoids. -->
    <movement>3</movement>
    <preloaditems>4</preloaditems>
    <onup>200</onup>
    <onleft>9000</onleft>
    <onright condition="Control.IsVisible(204)">204</onright>
    <onright>noop</onright>
    <ondown>400</ondown>
    <orientation>horizontal</orientation>
    <!-- ITEM LAYOUT ########################################## -->
    <!-- 200, not 170 - matches the same widened cell on script-plex-seasons.xml.tpl's own copy of
         this row (see its own comment for the full reasoning). -->
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
    {# Kodi applies this layout to whichever item holds the list's internal cursor, independent of whether
       control 205 itself has window focus - so without gating on Control.HasFocus(205), the cursor's item
       (which defaults to the current season) renders in the "focused" white year-round, making the tab bar
       look focused even when focus actually sits on the play button, and keeps showing white on whatever tab
       was last highlighted after focus moves away. Splitting into two labels keyed off actual control focus
       makes it fall back to the same grey as itemlayout the rest of the time; the current-season underline
       below is unaffected since it never depended on focus. #}
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
    <posx>120</posx>
    <posy>0</posy>
    <width>1420</width>
    <height>{{ vscale(135) }}</height>
    <onup>200</onup>
    <onleft>9000</onleft>
    <onright condition="Control.IsVisible(204)">204</onright>
    <onright>noop</onright>
    <ondown>400</ondown>
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