<control type="group">
    <visible>String.IsEmpty(Window.Property(use_solid_background))</visible>
    <control type="image">
        <visible>String.IsEmpty(Window.Property(use_bg_fallback))</visible>
        <posx>0</posx>
        <posy>0</posy>
        <width>1920</width>
        <height>1080</height>
        <texture background="true">script.plex/home/background-fallback_black.png</texture>
    </control>
    <control type="image">
        <visible>!String.IsEmpty(Window.Property(use_bg_fallback))</visible>
        <posx>0</posx>
        <posy>0</posy>
        <width>1920</width>
        <height>1080</height>
        <texture background="true">script.plex/home/background-fallback.png</texture>
        {% include "includes/scale_background.xml.tpl" %}
    </control>
    <!-- flat base fill under the 4 corner tints below - colors.Background (lib/colors.py) hardcoded
         here to match this file's existing convention of literal hex colordiffuse values (see the
         scrim control below). Also the fallback the panel degrades to when an item has no
         ultraBlurColors data at all (all 4 corner controls below stay hidden in that case). -->
    <control type="image">
        <visible>!String.IsEmpty(Window.Property(dynamic_backgrounds))</visible>
        <posx>0</posx>
        <posy>0</posy>
        <width>1920</width>
        <height>1080</height>
        <texture>script.plex/white-square.png</texture>
        <colordiffuse>FF111111</colordiffuse>
    </control>
    <!-- 4-corner tinted-panel composite, matching official Plex Android's real mechanism (decompiled
         - see docs/notes/hero-art-background-status.md): one shared corner-anchored falloff shape,
         drawn 4x with flipx/flipy for the other 3 corners, each tinted solid via colordiffuse - not
         a blur, not a bilinear 4-corner blend. Colors come from the item's ultraBlurColors PMS
         metadata (Phase 1 - see util.backgroundPanelCorners), not real pixel extraction from the art
         (Phase 2, not yet implemented). Each control hides independently via String.IsEmpty when
         that corner has no color, falling back to the flat base fill above. Uses the same
         sibling-<colordiffuse>-plus-diffuse-mask pattern as the scrim control below - colordiffuse
         and diffuse= combined as attributes on one <texture> tag silently does nothing (see this
         file's other working examples).

         Duplicated into two layers (_a/_b) rather than one set of 4 controls: a control's
         <colordiffuse> has no fade of its own in Kodi, and - unlike what the old single-layer
         version assumed - <fadetime> doesn't generically fade any control's <visible> transition
         either; every other use of <fadetime> in this codebase is on a <control type="image">,
         where it drives that control's own internal texture-crossfade-on-change, a narrower,
         different feature. The generic way to fade a control (here, a group) across a <visible>
         transition is an explicit <animation effect="fade">VisibleChange</animation>, same pattern
         already used elsewhere in this skin (e.g. includes/sidebar.xml.tpl). BaseWindow.
         _setPanelCorners (kodigui.py) writes each new item's colors into whichever layer is
         currently hidden, then flips background_panel_layer, so that animation cross-fades
         old->new the same way the hero art layers above already do via texture-change crossfade. -->
    <control type="group">
        <visible>String.IsEqual(Window.Property(background_panel_layer),a)</visible>
        <animation effect="fade" start="0" end="100" time="200" reversible="true">VisibleChange</animation>
        <control type="image">
            <visible>!String.IsEmpty(Window.Property(background_panel_tl_a))</visible>
            <posx>0</posx>
            <posy>0</posy>
            <width>1920</width>
            <height>1080</height>
            <texture diffuse="script.plex/masks/background-corner.png">script.plex/white-square.png</texture>
            <colordiffuse>$INFO[Window.Property(background_panel_tl_a)]</colordiffuse>
        </control>
        <control type="image">
            <visible>!String.IsEmpty(Window.Property(background_panel_tr_a))</visible>
            <posx>0</posx>
            <posy>0</posy>
            <width>1920</width>
            <height>1080</height>
            <texture diffuse="script.plex/masks/background-corner.png" flipx="true">script.plex/white-square.png</texture>
            <colordiffuse>$INFO[Window.Property(background_panel_tr_a)]</colordiffuse>
        </control>
        <control type="image">
            <visible>!String.IsEmpty(Window.Property(background_panel_bl_a))</visible>
            <posx>0</posx>
            <posy>0</posy>
            <width>1920</width>
            <height>1080</height>
            <texture diffuse="script.plex/masks/background-corner.png" flipy="true">script.plex/white-square.png</texture>
            <colordiffuse>$INFO[Window.Property(background_panel_bl_a)]</colordiffuse>
        </control>
        <control type="image">
            <visible>!String.IsEmpty(Window.Property(background_panel_br_a))</visible>
            <posx>0</posx>
            <posy>0</posy>
            <width>1920</width>
            <height>1080</height>
            <texture diffuse="script.plex/masks/background-corner.png" flipx="true" flipy="true">script.plex/white-square.png</texture>
            <colordiffuse>$INFO[Window.Property(background_panel_br_a)]</colordiffuse>
        </control>
    </control>
    <control type="group">
        <visible>String.IsEqual(Window.Property(background_panel_layer),b)</visible>
        <animation effect="fade" start="0" end="100" time="200" reversible="true">VisibleChange</animation>
        <control type="image">
            <visible>!String.IsEmpty(Window.Property(background_panel_tl_b))</visible>
            <posx>0</posx>
            <posy>0</posy>
            <width>1920</width>
            <height>1080</height>
            <texture diffuse="script.plex/masks/background-corner.png">script.plex/white-square.png</texture>
            <colordiffuse>$INFO[Window.Property(background_panel_tl_b)]</colordiffuse>
        </control>
        <control type="image">
            <visible>!String.IsEmpty(Window.Property(background_panel_tr_b))</visible>
            <posx>0</posx>
            <posy>0</posy>
            <width>1920</width>
            <height>1080</height>
            <texture diffuse="script.plex/masks/background-corner.png" flipx="true">script.plex/white-square.png</texture>
            <colordiffuse>$INFO[Window.Property(background_panel_tr_b)]</colordiffuse>
        </control>
        <control type="image">
            <visible>!String.IsEmpty(Window.Property(background_panel_bl_b))</visible>
            <posx>0</posx>
            <posy>0</posy>
            <width>1920</width>
            <height>1080</height>
            <texture diffuse="script.plex/masks/background-corner.png" flipy="true">script.plex/white-square.png</texture>
            <colordiffuse>$INFO[Window.Property(background_panel_bl_b)]</colordiffuse>
        </control>
        <control type="image">
            <visible>!String.IsEmpty(Window.Property(background_panel_br_b))</visible>
            <posx>0</posx>
            <posy>0</posy>
            <width>1920</width>
            <height>1080</height>
            <texture diffuse="script.plex/masks/background-corner.png" flipx="true" flipy="true">script.plex/white-square.png</texture>
            <colordiffuse>$INFO[Window.Property(background_panel_br_b)]</colordiffuse>
        </control>
    </control>
    <!-- shrunk to ~64% and anchored top-right, matching official Plex's own pre_play framing.
         The vignette mask below is a rounded-rectangle falloff (flat sides, curved corners only),
         not a smooth ellipse - fit against real pixel measurements off official Plex renders. An
         ellipse forces curvature into the middle of each edge, which faded too early and smeared
         the transition wider than the real, sharper corner-only curve. -->
    <control type="image">
        <!-- no fallback="" texture here: Kodi shows a fallback for the entire time the real
             texture is downloading/transcoding, not just on genuine failure, and an opaque one
             would sit on top of the color panel above and hide it for however long the art takes
             to fetch. The plain black base fallback control at the top of this file already
             covers that spot regardless. -->
        <!-- no_hero_art (HomeWindow.updateHeroFrom, home.py): hides this box for items with no
             real background art (Photos, many Music artists/albums), rather than showing the
             previous item's art or a placeholder - empty/unset for every other window, so this
             only ever actively hides anything on the home screen. -->
        <visible>!String.IsEmpty(Window.Property(dynamic_backgrounds)) + String.IsEmpty(Window.Property(no_hero_art))</visible>
        <posx>691</posx>
        <posy>0</posy>
        <width>1229</width>
        <height>691</height>
        <!-- 250ms, not instant: this layer sits statically behind the crossfading one below for most
             of its life, but BaseWindow._scheduleBackgroundStaticSync() (kodigui.py) catches it up to
             match roughly 0.25s after every change, once that crossfade settles - see that method's own
             comment for why, and keep it in sync with that timer if this ever changes again. Without a
             fadetime here, that catch-up was itself an abrupt, visible texture-reload pop despite the
             top layer already showing the same art by then; fading it folds the catch-up into something
             that reads as a continuation of the original crossfade rather than a second, separate flash.
             Shortened from an original 500ms/0.5s pairing on request - shorter reads as less of the
             previous item's art visibly lingering/blending under the new one during the transition. -->
        <fadetime>250</fadetime>
        <texture background="true" diffuse="script.plex/masks/background-vignette.png">$INFO[Window.Property(background_static)]</texture>
        <!-- lets the 4-corner tinted panel bleed through the art uniformly, not just at the
             vignette's own edge falloff - same sibling-<colordiffuse>-plus-diffuse-mask pattern
             as the scrim control below (colordiffuse as an attribute on <texture> alongside
             diffuse= silently does nothing, this sibling-element form is the one that works).
             White RGB, alpha only, so this is a pure opacity trim - no colour shift of its own. -->
        <colordiffuse>66FFFFFF</colordiffuse>
        {% include "includes/scale_background.xml.tpl" %}
    </control>
    <control type="image">
        <visible>!String.IsEmpty(Window.Property(dynamic_backgrounds)) + String.IsEmpty(Window.Property(no_hero_art))</visible>
        <posx>691</posx>
        <posy>0</posy>
        <width>1229</width>
        <height>691</height>
        <fadetime>250</fadetime>
        <texture background="true" diffuse="script.plex/masks/background-vignette.png">{{ background_source|default("$INFO[Window.Property(background)]") }}</texture>
        <colordiffuse>66FFFFFF</colordiffuse>
        {% include "includes/scale_background.xml.tpl" %}
    </control>
    <!-- a flat, neutral scrim directly over the art box - official Plex's own key art plateaus
         well short of full brightness even on its palest art (measured ~40% dimmed toward black),
         but stays achromatic doing it. An earlier version tinted this with the item's own
         ultrablur color instead of black, which measured out as a visible pink/hue cast against
         real Plex screenshots that isn't actually there. Uses the same vignette mask as the art
         layers above so it fades out at the box edges instead of ending in a hard rectangle where
         the art has already faded to reveal the panel underneath. -->
    <control type="image">
        <!-- temporarily disabled for testing (hardcoded false) - re-enable by restoring the
             condition below. -->
        <visible>false</visible>
        <!-- <visible>!String.IsEmpty(Window.Property(dynamic_backgrounds)) + String.IsEmpty(Window.Property(no_hero_art))</visible> -->
        <fadetime>1000</fadetime>
        <posx>691</posx>
        <posy>0</posy>
        <width>1229</width>
        <height>691</height>
        <texture diffuse="script.plex/masks/background-vignette.png">script.plex/white-square.png</texture>
        <colordiffuse>33000000</colordiffuse>
    </control>
    <!-- Full-canvas dim while focus is down in the row content (Roles/Reviews/Extras/Related/etc.)
         below the details block, so that content doesn't have to compete with the backdrop. Driven
         by row.focused (PrePlayWindow.onFocus, preplay.py; ShowWindow.onFocus, subitems.py;
         EpisodesWindow.onFocus, episodes.py) rather than the pre-existing hub.focus property that the
         row-slide animations elsewhere key off - hub.focus is deliberately never cleared once a row's
         been visited (those animations are meant to stay collapsed), but this scrim needs to toggle
         back off when focus returns above the row list, so it gets its own property that does.
         person.py doesn't opt in yet - same onFocus addition would extend this there too, if that
         screen ever gets this same row-scrolling layout. 4D, not 33: dimming increased from 20% to
         30% on request. -->
    <control type="image">
        <visible>!String.IsEmpty(Window.Property(row.focused))</visible>
        <animation effect="fade" start="0" end="100" time="600" reversible="true">VisibleChange</animation>
        <posx>0</posx>
        <posy>0</posy>
        <width>1920</width>
        <height>1080</height>
        <texture>script.plex/white-square.png</texture>
        <colordiffuse>4D000000</colordiffuse>
    </control>
</control>