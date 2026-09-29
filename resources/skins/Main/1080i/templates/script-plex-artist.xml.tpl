{% extends "default.xml.tpl" %}
{% block headers %}<defaultcontrol>100</defaultcontrol>{% endblock %}
{% block header %}
    {{ super() }}
    {% include "includes/sidebar.xml.tpl" %}
    <!-- Declared last so groups 802/901 draw on top - see script-plex-pre_play.xml.tpl's own copy
         of this include for the full reasoning (this window is one of the seven real hosted-shell
         types too, same _sidebarTarget()-aware Python side, same onClick forwarding - shared with
         script-plex-seasons.xml.tpl since ArtistWindow(subitems.py) subclasses ShowWindow without
         overriding onClick). -->
    {% include "includes/sidebar_dropdowns.xml.tpl" %}
{% endblock header %}
{% block content %}
<control type="group" id="50">
    <animation effect="slide" end="0,{{ vscale(-300) }}" time="200" tween="quadratic" easing="out" condition="!String.IsEmpty(Window.Property(on.extras))">Conditional</animation>

    <!-- One progressive depth scale, hub.focus 1-9 (ArtistWindow.onFocus()/HUB_FOCUS_TIERS,
         subitems.py: Popular Tracks=1, Albums=2, Live=3, Compilations=4, Singles & EPs=5,
         Soundtracks=6, Demos=7, Remixes=8, Related Artists=9 - control ids aren't allocated in that
         order, hence the explicit tier map instead of the plain controlID-399 arithmetic every other
         ShowWindow screen uses). Conditional animations that are simultaneously true stack additively
         (matches Seasons' own identical cascade, script-plex-seasons.xml.tpl - see that block's own
         comment for the mechanism) - each tier below is an INCREMENT equal to the height+itemgap of
         the row that just scrolled above it, not an absolute offset, and is gated on that same row's
         own Visible() so an artist missing a given album type (common - most have no Live/Demo/Remix
         albums) doesn't leave a gap-sized hole in the slide (grouplist 600 skips invisible children
         entirely when auto-stacking, so a row that contributed no real height shouldn't contribute a
         slide increment either). Row heights: Popular Tracks 196-596 (variable, see below), every
         album-type/Albums row 400,
         Related 520, itemgap 5 - see grouplist 600 and includes/artist_album_row.xml.tpl below.
         Popular Tracks is the one variable-height row: 196 for one track, +100 per track after
         that up to five, which is why its tier below is built from several stacked increments. -->
    <!-- Tier 1 (Popular Tracks) is the one row whose height varies with its content - see group
         501's own height comment and the spacers that follow it. Its increment is built the same
         way the row itself is: a 201 base (the one-track row + itemgap) plus 100 per extra track,
         each gated on the same NumItems condition as the matching spacer, relying on the additive
         stacking this block already documents. Five tracks = 601, the old fixed value. -->
    <animation type="Conditional" condition="Integer.IsGreater(Window.Property(hub.focus),1) + Control.IsVisible(501)" reversible="true">
        <effect type="slide" end="0,{{ vscale(-201) }}" time="200" tween="quadratic" easing="out"/>
    </animation>
    <animation type="Conditional" condition="Integer.IsGreater(Window.Property(hub.focus),1) + Control.IsVisible(501) + Integer.IsGreater(Container(402).NumItems,1)" reversible="true">
        <effect type="slide" end="0,{{ vscale(-100) }}" time="200" tween="quadratic" easing="out"/>
    </animation>
    <animation type="Conditional" condition="Integer.IsGreater(Window.Property(hub.focus),1) + Control.IsVisible(501) + Integer.IsGreater(Container(402).NumItems,2)" reversible="true">
        <effect type="slide" end="0,{{ vscale(-100) }}" time="200" tween="quadratic" easing="out"/>
    </animation>
    <animation type="Conditional" condition="Integer.IsGreater(Window.Property(hub.focus),1) + Control.IsVisible(501) + Integer.IsGreater(Container(402).NumItems,3)" reversible="true">
        <effect type="slide" end="0,{{ vscale(-100) }}" time="200" tween="quadratic" easing="out"/>
    </animation>
    <animation type="Conditional" condition="Integer.IsGreater(Window.Property(hub.focus),1) + Control.IsVisible(501) + Integer.IsGreater(Container(402).NumItems,4)" reversible="true">
        <effect type="slide" end="0,{{ vscale(-100) }}" time="200" tween="quadratic" easing="out"/>
    </animation>
    <animation type="Conditional" condition="Integer.IsGreater(Window.Property(hub.focus),2) + Control.IsVisible(502)" reversible="true">
        <effect type="slide" end="0,{{ vscale(-410) }}" time="200" tween="quadratic" easing="out"/>
    </animation>
    <animation type="Conditional" condition="Integer.IsGreater(Window.Property(hub.focus),3) + Control.IsVisible(503)" reversible="true">
        <effect type="slide" end="0,{{ vscale(-410) }}" time="200" tween="quadratic" easing="out"/>
    </animation>
    <animation type="Conditional" condition="Integer.IsGreater(Window.Property(hub.focus),4) + Control.IsVisible(504)" reversible="true">
        <effect type="slide" end="0,{{ vscale(-410) }}" time="200" tween="quadratic" easing="out"/>
    </animation>
    <animation type="Conditional" condition="Integer.IsGreater(Window.Property(hub.focus),5) + Control.IsVisible(505)" reversible="true">
        <effect type="slide" end="0,{{ vscale(-410) }}" time="200" tween="quadratic" easing="out"/>
    </animation>
    <animation type="Conditional" condition="Integer.IsGreater(Window.Property(hub.focus),6) + Control.IsVisible(506)" reversible="true">
        <effect type="slide" end="0,{{ vscale(-410) }}" time="200" tween="quadratic" easing="out"/>
    </animation>
    <animation type="Conditional" condition="Integer.IsGreater(Window.Property(hub.focus),7) + Control.IsVisible(507)" reversible="true">
        <effect type="slide" end="0,{{ vscale(-410) }}" time="200" tween="quadratic" easing="out"/>
    </animation>
    <animation type="Conditional" condition="Integer.IsGreater(Window.Property(hub.focus),8) + Control.IsVisible(508)" reversible="true">
        <effect type="slide" end="0,{{ vscale(-410) }}" time="200" tween="quadratic" easing="out"/>
    </animation>

    <!-- Slide right while the sidebar rail is expanded (focused), matching every other ported screen. -->
    <animation effect="slide" end="220,0" time="200" tween="sine" easing="inout" condition="ControlGroup(9000).HasFocus(0)">Conditional</animation>

    <!-- posx=52, not 60: matches Seasons'/Pre-play's own tuned value exactly
         (script-plex-seasons.xml.tpl) so the content column lands at the same absolute x as those
         screens - see includes/sidebar.xml.tpl for why some offset is still needed at all (clears
         the collapsed sidebar rail's icon column). -->
    <posx>52</posx>
    <posy>{{ vscale(125) }}</posy>
    <!-- 402 (Popular Tracks), not 400 (Albums): Popular Tracks is now the first row in grouplist 600's
         stack - see HUB_FOCUS_TIERS' own comment (subitems.py) for why. -->
    <defaultcontrol>402</defaultcontrol>

    {% block buttons %}
        <!-- Repositioned/retuned to match Seasons' own button row (script-plex-seasons.xml.tpl) -
             same 0/358 outer offset and 63/25 inner offset, same icon-box retune (theme.artist
             mirrors theme.seasons in context.py: 70x70 icons, itemgap 0, hitrect 5,5,60,60 in the
             modern theme) in place of this row's own old one-off 174x139/-50-itemgap tuning. No
             season-tab row to fall back onto (unlike Seasons' own dual onup), so onup just stays 200;
             onleft=9000 added to reach the sidebar - every other ported screen's button row already
             has this, this one just never did. -->
        <control type="group">
            <posx>0</posx>
            <posy>{{ vscale(358) }}</posy>
            <width>1920</width>
            <height>{{ vscale(200) }}</height>
            <control type="grouplist" id="300">
                <animation effect="fade" start="0" end="100" time="200" reversible="true">VisibleChange</animation>
                <!-- 302 (Play), not the old 301 (Info) - the Info button itself is gone from this
                     row now (on request): the summary textbox is its own click/focus target for the
                     same action (SUMMARY_BUTTON_ID, id 305, subitems.py), so the explicit button was
                     redundant. -->
                <defaultcontrol>302</defaultcontrol>
                <posx>63</posx>
                <posy>{{ vscale(25) }}</posy>
                <width>1000</width>
                <height>{{ vscale(145) }}</height>
                <!-- 305 (the summary click-target), not straight to 200: keeps that new focus stop
                     reachable from the button row via remote/keyboard, not just mouse/touch. -->
                <onup condition="!String.IsEmpty(Window.Property(summary))">305</onup>
                <!-- Fallback is exactly where 305's own onup goes, so the row behaves as if the
                     target simply weren't there. 200 is the header group, which has no focusable
                     children on this screen (the default header has no left-hand buttons),
                     so in practice this consumes the press. -->
                <onup>200</onup>
                <!-- 402 (Popular Tracks), not 400 - see group 50's own defaultcontrol comment above. -->
                <ondown>402</ondown>
                <onleft>9000</onleft>
                <itemgap>{{ theme.artist.buttongroup.itemgap }}</itemgap>
                <orientation>horizontal</orientation>
                <scrolltime tween="quadratic" easing="out">200</scrolltime>
                <usecontrolcoords>true</usecontrolcoords>

                <!-- Label-on-focus pill overlays (392-394): same recipe as every other button row
                     (episode_button_label.xml.tpl - see button-label-overlay-recipe). Play/More
                     reuse Pre-play's/Seasons' own $ADDON strings and measured widths, since it's the
                     same label text; Shuffle reuses Seasons' own. -->
                {% with attr = theme.artist.buttons & template = "includes/themed_button.xml.tpl" & hitrect = theme.artist.buttons_hitrect & ol = "includes/episode_button_label.xml.tpl" %}
                    {% include template with name="play" & id=302 & overlay=True %}
                    {% include ol with id=392 & visible="Control.HasFocus(302)" & name="play" &
                        label="$ADDON[script.plexmod 33020]" & label_suffix_info="" &
                        label_width=50 & pill_width=112 & group_width=68 &
                        onleft=302 & onright=303
                    %}
                    {% include template with name="shuffle" & id=303 & overlay=True %}
                    {% include ol with id=393 & visible="Control.HasFocus(303)" & name="shuffle" &
                        label="$ADDON[script.plexmod 32935]" & label_suffix_info="" &
                        label_width=84 & pill_width=146 & group_width=102 &
                        onleft=303 & onright=304
                    %}
                    {% include template with name="more" & id=304 & overlay=True %}
                    {% include ol with id=394 & visible="Control.HasFocus(304)" & name="more" &
                        label="$ADDON[script.plexmod 32307]" & label_suffix_info="" &
                        label_width=60 & pill_width=122 & group_width=78 &
                        onleft=304 & onright=""
                    %}
                {% endwith %}

            </control>
        </control>
    {% endblock %}

    <control type="group">
        <!-- posx=0, not the old thumb-layout's 60: that offset existed to clear the (now-removed)
             519-wide thumb, stacking on top of group 50's own posx and pushing title/genre/summary
             68px further right than Seasons' own column (52+0+61=113) once they were moved in to
             posx=61 each - matches Seasons' own inner group (posx=0) exactly now. -->
        <posx>0</posx>
        <posy>0</posy>
        <width>1920</width>
        <height>{{ vscale(367) }}</height>
        <!-- Title/genre-line/summary repositioned, resized and restyled to match Seasons' own
             header block exactly (script-plex-seasons.xml.tpl) - title's own big/bottom-aligned
             style, genre line using the seasons meta row's own position/size/style
             (includes/pp_meta_row.xml.tpl) but keeping this screen's own single artist.genre
             property rather than that include's compound duration/date/genres/rating line, summary
             matching Seasons' own textbox (autoscroll, not a scrollbar - the old pagecontrol=152
             here never had a matching scrollbar control to pair with, so it was always dead). Thumb
             dropped entirely (on request) - ArtistWindow.updateProperties() (subitems.py) no longer
             sets the now-unused 'thumb' property either. -->
        <control type="label">
            <!-- Position/style originally copied from Episodes' own episode-name label
                 (script-plex-episodes.xml.tpl, no-logo variant - Artist never has a clearlogo):
                 FFD2CCCE/aligny=top instead of the previous font45/FFFFFFFF/aligny=bottom big-title
                 treatment. posy=117, not that label's own raw 97: Episodes' own comment there notes
                 its 97 is "the reference screens' value minus 20" to compensate for Episodes' group
                 50 sitting at posy=155 instead of 135 - Artist's group already sits at 135 (matches
                 Seasons'/Pre-play's own baseline), so the untranslated 117 is the correct equivalent
                 here, not a literal copy of 97. Font since bumped up from that label's own
                 font32_title to font45_title (on request, through several intermediate sizes) and
                 width/height retuned to 708/61 (on request) - width now matches the genre line
                 below rather than that label's own 616/660. -->
            <posx>61</posx>
            <posy>{{ vscale(107) }}</posy>
            <width>708</width>
            <height>{{ vscale(61) }}</height>
            <font>font45_title</font>
            <align>left</align>
            <aligny>top</aligny>
            <scroll>true</scroll>
            <scrollspeed>35</scrollspeed>
            <textcolor>FFD2CCCE</textcolor>
            <label>$INFO[Window.Property(artist.title)]</label>
        </control>
        <control type="label">
            <posx>61</posx>
            <posy>{{ vscale(175) }}</posy>
            <width>708</width>
            <height>{{ vscale(30) }}</height>
            <font>font10</font>
            <align>left</align>
            <textcolor>FFD2CCCE</textcolor>
            <shadowcolor>66000000</shadowcolor>
            <label>$INFO[Window.Property(artist.genre)]</label>
        </control>
        <control type="textbox">
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
             and positioned to match it exactly, wired to infoButtonClicked() (SUMMARY_BUTTON_ID,
             subitems.py) - the only way left to reach it now that the button row's own explicit
             Info button (301) has been dropped entirely (on request, this became redundant with it).
             Blank label (matches themed_button.xml.tpl's own convention) so nothing draws over the
             textbox's real text.
             texturenofocus/texturefocus both "-" (explicit none, not just omitted - Kodi otherwise
             falls back to its own default button look, seen live as a dark box over the textbox) -
             the focus highlight itself is the separate image below instead, not this control's own
             texture, so it can be sized bigger than the actual hit area. -->
        <control type="button" id="305">
            <!-- No target when there's no summary to open: an enabled button over empty space
                 is a focus stop in the middle of the header that opens a blank popup. Every nav tag
                 routing through it carries the same condition, so the chain closes up instead of
                 dead-ending on a control that isn't there. -->
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
        <!-- Focus highlight for 305 above, kept as its own image rather than that button's own
             texturefocus so it can extend 5px past the button's own hit area on every side (on
             request) without changing what's actually clickable/focusable. -->
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

    <!-- One grouplist for the whole hub-row stack, matching Seasons'/Episodes'/Pre-play's own
         grouplist 60 convention - auto-stacks each row by its declared height+itemgap, in visual
         order: Popular Tracks, Albums, then the 6 otherAlbums hub types, then Related Artists.
         Control ids/order match ArtistWindow.ALBUM_TYPE_ROWS/HUB_FOCUS_TIERS exactly (subitems.py) -
         the two have to be kept in sync by hand. -->
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
    <control type="grouplist" id="600">
        <posx>0</posx>
        <!-- 466, not the old 585: moved up 119px so the gap from the button row's bottom edge to the
             first heading box matches Seasons'. This screen's buttons end at exactly the same absolute
             y as Seasons' (both 358 + 25 + the modern theme's 70px button height = 453), and Seasons
             sits its first label's 80px box 13px below that, so 453 + 13 = 466. Seasons and Episodes
             are deliberately tuned and were left alone. The old 585 came from the pre-grouplist
             group 100 and was never re-derived. -->
        <posy>{{ vscale(466) }}</posy>
        <width>1920</width>
        <height>{{ vscale(3940) }}</height>
        <onup>300</onup>
        <itemgap>5</itemgap>

        <!-- POPULAR TRACKS -->
        <!-- A real track row (title/duration on a pill, loosely script-plex-album.xml.tpl's own
             list recipe - the number column that recipe carries was dropped here on request),
             not another square-art carousel like the rows below it - these are tracks you click to
             play (popularTrackClicked(), subitems.py), not things you open. PopularLeaves entries
             arrive pre-sorted by ratingCount (server-side) - no client sort/pagination needed. -->
        <control type="group" id="501">
            <visible>Integer.IsGreater(Container(402).NumItems,0) + String.IsEmpty(Window.Property(drawing))</visible>
            <defaultcontrol>402</defaultcontrol>
            <posx>0</posx>
            <posy>0</posy>
            <width>1920</width>
            <!-- 196 = the ONE-track row height (86 + 100 + 10, the shared recipe's no-caption
                 variant), not the five-track 596 this used to declare. An artist with one or two
                 popular tracks is common, and grouplist 600 stacks the rows below by this declared
                 height, so a fixed 596 left up to 400px of dead space above Albums. The list below
                 keeps its full 500 height and simply overflows this group - groups don't clip, and
                 a list only ever draws the items it actually has - while the four conditional
                 spacers after this group (see below) hand back exactly 100px per track past the
                 first. Anything that changes this number has to change those spacers and group 50's
                 own tier-1 slide increments together. -->
            <height>{{ vscale(196) }}</height>
            <control type="label">
                <posx>61</posx>
                <posy>0</posy>
                <width>1000</width>
                <height>{{ vscale(80) }}</height>
                <font>font12</font>
                <align>left</align>
                <aligny>center</aligny>
                <textcolor>FFE9E6E7</textcolor>
                <label>[B]$INFO[Window.Property(popular_tracks.header)][/B]</label>
            </control>
            <control type="list" id="402">
                <posx>53</posx>
                <posy>{{ vscale(86) }}</posy>
                <width>1867</width>
                <height>{{ vscale(500) }}</height>
                <onup>300</onup>
                <ondown>400</ondown>
                <onleft>9000</onleft>
                <onright>noop</onright>
                <scrolltime>200</scrolltime>
                <orientation>vertical</orientation>
                <preloaditems>4</preloaditems>
                <!-- ITEM LAYOUT ########################################## -->
                <itemlayout height="{{ vscale(100) }}">
                    <control type="group">
                        <posx>8</posx>
                        <posy>0</posy>
                        <!-- Unfocused pill - geometry identical to the focused one below (same posy 4,
                             1694x92, same border="10" rounded texture), so focusing a row swaps the
                             pill's colour and nothing moves or resizes. 60000000 is the pre-play
                             review card's own unfocused panel tint (script-plex-pre_play.xml.tpl),
                             on request - a dark translucent bed rather than the lighter fill the
                             focus pill uses. -->
                        <control type="image">
                            <posx>0</posx>
                            <posy>{{ vscale(4) }}</posy>
                            <width>1694</width>
                            <height>{{ vscale(92) }}</height>
                            <texture border="10" colordiffuse="60000000">script.plex/white-square-rounded.png</texture>
                        </control>
                        <!-- Text stack: title on top, the track's own album under it, duration to the
                             right - two 30px line boxes styled like the album cards' own captions
                             (includes/artist_album_row.xml.tpl): FFFFFFFF first line, AAFFFFFF second,
                             neither bolded. font8 on the album line, not the cards' own font10 (on
                             request), so the two lines are 27.8px and 21.8px of actual line height
                             (InterUI at size 23 and 18; (1984+494)/2048 em per line).
                             Boxes at 23 and 50 inside the 100px row: that lands the title's line box at
                             24.1 and the album's bottom at 75.9, i.e. 20px clear of the pill's own
                             4..96 at both ends - the same breathing room the title had back when it was
                             a single font10 line centred on the old 76px row, and 2.2px of leading
                             between the two lines, unchanged from the font10/font10 pair. Row height
                             follows from that: 20 + 27.8 + 2.2 + 21.8 + 20 = 92 of pill, + 4px top and
                             bottom = 100.
                             The title is written twice, gated on whether this row is the track currently
                             playing - Kodi can't switch a single label's textcolor on a condition. The
                             playing row is tinted FFE5A00D (the theme's own accent, what the button focus
                             textures use) rather than carrying a now-playing glyph in a left gutter: with
                             the track number gone there's no column for one to live in, and reserving one
                             would indent every title for a marker that shows on at most one row. -->
                        <control type="label">
                            <visible>!String.IsEqual(ListItem.Property(track.ID),Window(10000).Property(script.plex.track.ID))</visible>
                            <scroll>false</scroll>
                            <posx>18</posx>
                            <posy>{{ vscale(23) }}</posy>
                            <width>1501</width>
                            <height>{{ vscale(30) }}</height>
                            <font>font10</font>
                            <align>left</align>
                            <aligny>center</aligny>
                            <textcolor>FFFFFFFF</textcolor>
                            <label>$INFO[ListItem.Label]</label>
                        </control>
                        <control type="label">
                            <visible>String.IsEqual(ListItem.Property(track.ID),Window(10000).Property(script.plex.track.ID))</visible>
                            <scroll>false</scroll>
                            <posx>18</posx>
                            <posy>{{ vscale(23) }}</posy>
                            <width>1501</width>
                            <height>{{ vscale(30) }}</height>
                            <font>font10</font>
                            <align>left</align>
                            <aligny>center</aligny>
                            <textcolor>FFE5A00D</textcolor>
                            <label>$INFO[ListItem.Label]</label>
                        </control>
                        <control type="label">
                            <scroll>false</scroll>
                            <posx>18</posx>
                            <posy>{{ vscale(50) }}</posy>
                            <width>1501</width>
                            <height>{{ vscale(30) }}</height>
                            <font>font8</font>
                            <align>left</align>
                            <aligny>center</aligny>
                            <textcolor>AAFFFFFF</textcolor>
                            <label>$INFO[ListItem.Property(track.album)]</label>
                        </control>
                        <control type="label">
                            <!-- 1526, not 1694-150: right edge lands 18px short of the pill's own
                                 right edge, mirroring the title's own 18px inset on the left. Kept
                                 centred on the full 76px row rather than sat on the title's line, so
                                 it reads against the two-line block as a whole. -->
                            <posx>1526</posx>
                            <posy>0</posy>
                            <width>150</width>
                            <height>{{ vscale(100) }}</height>
                            <font>font10</font>
                            <align>right</align>
                            <aligny>center</aligny>
                            <textcolor>D8FFFFFF</textcolor>
                            <label>$INFO[ListItem.Property(track.duration)]</label>
                        </control>
                    </control>
                </itemlayout>

                <!-- FOCUSED LAYOUT ####################################### -->
                <focusedlayout height="{{ vscale(100) }}">
                    <control type="group">
                        <!-- 8, matching the itemlayout's own group posx exactly - anything else
                             slides every label sideways the moment a row takes focus. -->
                        <posx>8</posx>
                        <posy>0</posy>
                        <!-- Focus highlight, built the same way as the button row's own focus pill
                             (episode_button_label.xml.tpl): white-square-rounded.png at border="10"
                             and 33FFFFFF - the same tint the sidebar's focused item and the library
                             filter/sort dropdowns use. The earlier version of this drew the same
                             texture with no border attribute at all, so Kodi stretched the 100x100
                             source's rounded corners into ~165px horizontal ramps across a box
                             this wide, and at 22FFFFFF there was barely anything left to see - reported
                             live as no visible focus at all. border="10" keeps the corners at their
                             native radius and stretches only the middle.
                             Inset 4px top/bottom (92 of the row's 100) so the rounded ends actually
                             read as a pill instead of butting against the rows above and below.
                             1694 wide, not the earlier 1647: this pill's left edge sits at absolute
                             x=113 (group 50's 52 + list 402's 53 + the item group's own 8 - the same
                             113 every heading on this screen aligns to), so 1920 - 113 - 113 = 1694
                             puts its right edge exactly as far from the screen edge as its left.
                             Gated on Control.HasFocus(402), with the itemlayout's own 60000000 pill
                             drawn instead when the row list doesn't have focus: Kodi renders a
                             list's focusedlayout for its SELECTED item regardless of whether the
                             control itself is focused, so an ungated focus pill here left one
                             popular track permanently lit while the user was somewhere else
                             entirely on the screen (whichever row the selection happened to rest
                             on - the first, or the last if the list had been entered from below).
                             Live-reported. This is the same reason the album and Similar Artists
                             rows gate their own focus rings on Control.HasFocus. Two controls
                             rather than one, because a texture's colordiffuse can't be switched on
                             a condition; identical geometry, so nothing moves or resizes as focus
                             arrives and the swap reads as a pure colour change. -->
                        <control type="image">
                            <visible>Control.HasFocus(402)</visible>
                            <posx>0</posx>
                            <posy>{{ vscale(4) }}</posy>
                            <width>1694</width>
                            <height>{{ vscale(92) }}</height>
                            <texture border="10" colordiffuse="33FFFFFF">script.plex/white-square-rounded.png</texture>
                        </control>
                        <control type="image">
                            <visible>!Control.HasFocus(402)</visible>
                            <posx>0</posx>
                            <posy>{{ vscale(4) }}</posy>
                            <width>1694</width>
                            <height>{{ vscale(92) }}</height>
                            <texture border="10" colordiffuse="60000000">script.plex/white-square-rounded.png</texture>
                        </control>
                        <!-- Text stack - see the itemlayout's own copy above. -->
                        <control type="label">
                            <visible>!String.IsEqual(ListItem.Property(track.ID),Window(10000).Property(script.plex.track.ID))</visible>
                            <scroll>Control.HasFocus(402)</scroll>
                            <posx>18</posx>
                            <posy>{{ vscale(23) }}</posy>
                            <width>1501</width>
                            <height>{{ vscale(30) }}</height>
                            <font>font10</font>
                            <align>left</align>
                            <aligny>center</aligny>
                            <textcolor>FFFFFFFF</textcolor>
                            <label>$INFO[ListItem.Label]</label>
                        </control>
                        <control type="label">
                            <visible>String.IsEqual(ListItem.Property(track.ID),Window(10000).Property(script.plex.track.ID))</visible>
                            <scroll>Control.HasFocus(402)</scroll>
                            <posx>18</posx>
                            <posy>{{ vscale(23) }}</posy>
                            <width>1501</width>
                            <height>{{ vscale(30) }}</height>
                            <font>font10</font>
                            <align>left</align>
                            <aligny>center</aligny>
                            <textcolor>FFE5A00D</textcolor>
                            <label>$INFO[ListItem.Label]</label>
                        </control>
                        <control type="label">
                            <scroll>false</scroll>
                            <posx>18</posx>
                            <posy>{{ vscale(50) }}</posy>
                            <width>1501</width>
                            <height>{{ vscale(30) }}</height>
                            <font>font8</font>
                            <align>left</align>
                            <aligny>center</aligny>
                            <textcolor>AAFFFFFF</textcolor>
                            <label>$INFO[ListItem.Property(track.album)]</label>
                        </control>
                        <control type="label">
                            <posx>1526</posx>
                            <posy>0</posy>
                            <width>150</width>
                            <height>{{ vscale(100) }}</height>
                            <font>font10</font>
                            <align>right</align>
                            <aligny>center</aligny>
                            <textcolor>D8FFFFFF</textcolor>
                            <label>$INFO[ListItem.Property(track.duration)]</label>
                        </control>
                    </control>
                </focusedlayout>
            </control>
        </control>
        <!-- POPULAR TRACKS -->

        <!-- POPULAR TRACKS ROW SPACERS - one per track past the first, each gated on the row's own
             item count. Group 501 above declares only the one-track height, so these hand its
             missing height back a track at a time: 95 + grouplist 600's own itemgap 5 = the 100px
             an extra track occupies. Four of them, because list 402 is 500 tall and shows at most
             five tracks before it scrolls - a sixth track needs no extra room. At five tracks the
             stack totals 196 + 4x100 + 5 = 601, exactly the footprint the old fixed 596 + itemgap
             had, so nothing below moves for a full row. Separate siblings rather than one
             variable-height control because a skin can't do arithmetic on NumItems, and duplicating
             the row itself at different heights isn't possible - control id 402 can only exist once.
             The same NumItems conditions drive group 50's tier-1 slide increments up top. -->
        <control type="group">
            <visible>Integer.IsGreater(Container(402).NumItems,1) + String.IsEmpty(Window.Property(drawing))</visible>
            <width>1920</width>
            <height>{{ vscale(95) }}</height>
            <!-- A real child rather than an empty group, so this is unambiguously a sized,
                 renderable control for grouplist 600's auto-stacking. No <texture> at all: an
                 image with none draws nothing, and the '-' no-op the button templates use has no
                 precedent on a plain image texture here. The three spacers below are identical. -->
            <control type="image">
                <width>1920</width>
                <height>{{ vscale(95) }}</height>
            </control>
        </control>
        <control type="group">
            <visible>Integer.IsGreater(Container(402).NumItems,2) + String.IsEmpty(Window.Property(drawing))</visible>
            <width>1920</width>
            <height>{{ vscale(95) }}</height>
            <control type="image">
                <width>1920</width>
                <height>{{ vscale(95) }}</height>
            </control>
        </control>
        <control type="group">
            <visible>Integer.IsGreater(Container(402).NumItems,3) + String.IsEmpty(Window.Property(drawing))</visible>
            <width>1920</width>
            <height>{{ vscale(95) }}</height>
            <control type="image">
                <width>1920</width>
                <height>{{ vscale(95) }}</height>
            </control>
        </control>
        <control type="group">
            <visible>Integer.IsGreater(Container(402).NumItems,4) + String.IsEmpty(Window.Property(drawing))</visible>
            <width>1920</width>
            <height>{{ vscale(95) }}</height>
            <control type="image">
                <width>1920</width>
                <height>{{ vscale(95) }}</height>
            </control>
        </control>

        {% with row = "includes/artist_album_row.xml.tpl" %}
            {% include row with id=400 & group_id=502 & onup=402 & ondown=404 & header_prop="albums.header" %}
            {% include row with id=404 & group_id=503 & onup=400 & ondown=405 & header_prop="live_albums.header" %}
            {% include row with id=405 & group_id=504 & onup=404 & ondown=406 & header_prop="compilation_albums.header" %}
            {% include row with id=406 & group_id=505 & onup=405 & ondown=407 & header_prop="single_albums.header" %}
            {% include row with id=407 & group_id=506 & onup=406 & ondown=408 & header_prop="soundtrack_albums.header" %}
            {% include row with id=408 & group_id=507 & onup=407 & ondown=409 & header_prop="demo_albums.header" %}
            {% include row with id=409 & group_id=508 & onup=408 & ondown=401 & header_prop="remix_albums.header" %}
        {% endwith %}

    <!-- similar artists -->
    <control type="group" id="500">
        <visible>Integer.IsGreater(Container(401).NumItems,0) + String.IsEmpty(Window.Property(drawing))</visible>
        <defaultcontrol>401</defaultcontrol>
        <width>1920</width>
        <height>{{ vscale(405) }}</height>
        <posx>0</posx>
        <posy>0</posy>
        <control type="label">
            <posx>61</posx>
            <posy>0</posy>
            <width>1000</width>
            <height>{{ vscale(80) }}</height>
            <font>font12</font>
            <align>left</align>
            <aligny>center</aligny>
            <textcolor>FFE9E6E7</textcolor>
            <label>[B]$INFO[Window.Property(related.header)][/B]</label>
        </control>
        <control type="fixedlist" id="401">
            <posx>53</posx>
            <posy>{{ vscale(22) }}</posy>
            <width>1867</width>
            <height>{{ vscale(380) }}</height>
            <onup>409</onup>
            <ondown>noop</ondown>
            <!-- RelatedPaginator always starts at offset=0 and never produces a left-boundary
                 marker (same as Episodes' Related row), so noop here was already a dead end -
                 safe to go straight to the sidebar. onright stays an unconditional hard stop. -->
            <onleft>9000</onleft>
            <onright>noop</onright>
            <scrolltime>200</scrolltime>
            <orientation>horizontal</orientation>
            <!-- Focus pinned to the row's first slot, the row scrolling under it - the same as
                 Recommended's hub rows (script-plex-recommended.xml.tpl, which explains the tail).
                 movement = itemsPerPage - 1, itemsPerPage being (1867 - 282) / 282 + 1 = 6: the last
                 items spread to the last whole slot, where this row, a plain list before, left them. -->
            <focusposition>0</focusposition>
            <movement>5</movement>
            <preloaditems>4</preloaditems>
            <!-- ITEM LAYOUT ########################################## -->
            <itemlayout width="282">
                <control type="group">
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
                        <texture border="24">script.plex/drop-shadow-directional.png</texture>
                    </control>
                    <control type="group">
                        <posx>3</posx>
                        <posy>3</posy>
                        <control type="image">
                            <posx>0</posx>
                            <posy>0</posy>
                            <width>240</width>
                            <height>{{ vscale(240) }}</height>
                            <texture background="true" diffuse="script.plex/masks/square-mask.png" fallback="$INFO[ListItem.Property(thumb.fallback)]">$INFO[ListItem.Thumb]</texture>
                            <aspectratio scalediffuse="false">scale</aspectratio>
                        </control>
                        <!-- Single caption line, flat (no wrapper group): the second line this row
                             used to carry was bound to ListItem.Property(year), which only the album
                             rows ever set (fill()/fillAlbumTypeRows(), subitems.py) - RelatedPaginator
                             never sets it, so it rendered blank on every tile. Same posy=249 first
                             line the album rows use (includes/artist_album_row.xml.tpl). -->
                        <control type="label">
                            <scroll>false</scroll>
                            <posx>0</posx>
                            <posy>{{ vscale(249) }}</posy>
                            <width>240</width>
                            <height>{{ vscale(30) }}</height>
                            <font>font10</font>
                            <align>center</align>
                            <textcolor>FFFFFFFF</textcolor>
                            <label>$INFO[ListItem.Label]</label>
                        </control>
                        <!-- Boundary/updating overlays, re-centred for 240 art: chevron (240-61)/2 = 89.5,
                             (240-100)/2 = 70; busy (240-128)/2 = 56. -->
                        <control type="group">
                            <visible>!String.IsEmpty(ListItem.Property(is.boundary))</visible>
                            <control type="image">
                                <posx>0</posx>
                                <posy>0</posy>
                                <width>240</width>
                                <height>{{ vscale(240) }}</height>
                                <texture colordiffuse="FF404040">script.plex/white-square.png</texture>
                            </control>
                            <control type="image">
                                <visible>String.IsEmpty(ListItem.Property(is.updating)) + !String.IsEmpty(ListItem.Property(right.boundary))</visible>
                                <posx>89.5</posx>
                                <posy>{{ vscale(70) }}</posy>
                                <width>61</width>
                                <height>{{ vscale(100) }}</height>
                                <texture colordiffuse="40000000">script.plex/indicators/chevron-white.png</texture>
                            </control>
                            <control type="image">
                                <visible>String.IsEmpty(ListItem.Property(is.updating)) + !String.IsEmpty(ListItem.Property(left.boundary))</visible>
                                <posx>89.5</posx>
                                <posy>{{ vscale(70) }}</posy>
                                <width>61</width>
                                <height>{{ vscale(100) }}</height>
                                <texture colordiffuse="40000000">script.plex/indicators/chevron-white-l.png</texture>
                            </control>
                            <control type="image">
                                <visible>!String.IsEmpty(ListItem.Property(is.updating))</visible>
                                <posx>56</posx>
                                <posy>{{ vscale(56) }}</posy>
                                <width>128</width>
                                <height>{{ vscale(128) }}</height>
                                <texture>script.plex/home/busy.gif</texture>
                            </control>
                        </control>
                    </control>
                </control>
            </itemlayout>

            <!-- FOCUSED LAYOUT ####################################### -->
            <focusedlayout width="282">
                <control type="group">
                    <posx>5</posx>
                    <posy>{{ vscale(61) }}</posy>
                    <control type="group">
                        <animation effect="zoom" start="100" end="104" time="100" center="123,{{ vscale(123) }}" reversible="false">Focus</animation>
                        <animation effect="zoom" start="104" end="100" time="100" center="123,{{ vscale(123) }}" reversible="false">UnFocus</animation>
                        <posx>0</posx>
                        <posy>0</posy>
                        <control type="image">
                            <!-- Ungated, unlike the focus ring below it: f10d4074 established that gating
                                 a card's drop shadow on Control.HasFocus makes the selected card the only
                                 one on screen without a shadow the moment focus leaves the list for the
                                 button row, sidebar or scrubber - and the shadow visibly pops back in as
                                 Kodi settles the layout. The itemlayout draws this same box
                                 unconditionally, so this one matches it. -->
                            <posx>0</posx>
                            <posy>0</posy>
                            <width>264</width>
                            <height>{{ vscale(264) }}</height>
                            <texture border="24">script.plex/drop-shadow-directional.png</texture>
                        </control>
                        <control type="group">
                            <posx>3</posx>
                            <posy>3</posy>
                            <control type="image">
                                <posx>0</posx>
                                <posy>0</posy>
                                <width>240</width>
                                <height>{{ vscale(240) }}</height>
                                <texture background="true" diffuse="script.plex/masks/square-mask.png" fallback="$INFO[ListItem.Property(thumb.fallback)]">$INFO[ListItem.Thumb]</texture>
                                <aspectratio scalediffuse="false">scale</aspectratio>
                            </control>
                            <!-- See the itemlayout's own copy above for why there's only one line. -->
                            <control type="label">
                                <scroll>Control.HasFocus(401)</scroll>
                                <posx>0</posx>
                                <posy>{{ vscale(249) }}</posy>
                                <width>240</width>
                                <height>{{ vscale(30) }}</height>
                                <font>font10</font>
                                <align>center</align>
                                <textcolor>FFFFFFFF</textcolor>
                                <label>$INFO[ListItem.Label]</label>
                            </control>
                            <!-- Boundary/updating overlays, re-centred for 240 art: chevron (240-61)/2 = 89.5,
                                 (240-100)/2 = 70; busy (240-128)/2 = 56. -->
                            <control type="group">
                                <visible>!String.IsEmpty(ListItem.Property(is.boundary))</visible>
                                <control type="image">
                                    <posx>0</posx>
                                    <posy>0</posy>
                                    <width>240</width>
                                    <height>{{ vscale(240) }}</height>
                                    <texture colordiffuse="FF404040">script.plex/white-square.png</texture>
                                </control>
                                <control type="image">
                                    <visible>String.IsEmpty(ListItem.Property(is.updating)) + !String.IsEmpty(ListItem.Property(right.boundary))</visible>
                                    <posx>89.5</posx>
                                    <posy>{{ vscale(70) }}</posy>
                                    <width>61</width>
                                    <height>{{ vscale(100) }}</height>
                                    <texture colordiffuse="40000000">script.plex/indicators/chevron-white.png</texture>
                                </control>
                                <control type="image">
                                    <visible>String.IsEmpty(ListItem.Property(is.updating)) + !String.IsEmpty(ListItem.Property(left.boundary))</visible>
                                    <posx>89.5</posx>
                                    <posy>{{ vscale(70) }}</posy>
                                    <width>61</width>
                                    <height>{{ vscale(100) }}</height>
                                    <texture colordiffuse="40000000">script.plex/indicators/chevron-white-l.png</texture>
                                </control>
                                <control type="image">
                                    <visible>!String.IsEmpty(ListItem.Property(is.updating))</visible>
                                    <posx>56</posx>
                                    <posy>{{ vscale(56) }}</posy>
                                    <width>128</width>
                                    <height>{{ vscale(128) }}</height>
                                    <texture>script.plex/home/busy.gif</texture>
                                </control>
                            </control>
                        </control>
                        <control type="image">
                            <visible>Control.HasFocus(401)</visible>
                            <posx>0</posx>
                            <posy>0</posy>
                            <width>246</width>
                            <height>{{ vscale(246) }}</height>
                            <texture diffuse="script.plex/masks/ring-mask-square.png">script.plex/white-square.png</texture>
                            <colordiffuse>FFE9A20D</colordiffuse>
                        </control>
                    </control>
                </control>
            </focusedlayout>
        </control>
    </control>
    </control>
</control>
{% endblock content %}