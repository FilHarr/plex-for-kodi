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
         file's other working examples). -->
    <control type="image">
        <visible>!String.IsEmpty(Window.Property(background_panel_tl))</visible>
        <fadetime>1000</fadetime>
        <posx>0</posx>
        <posy>0</posy>
        <width>1920</width>
        <height>1080</height>
        <texture diffuse="script.plex/masks/background-corner.png">script.plex/white-square.png</texture>
        <colordiffuse>$INFO[Window.Property(background_panel_tl)]</colordiffuse>
    </control>
    <control type="image">
        <visible>!String.IsEmpty(Window.Property(background_panel_tr))</visible>
        <fadetime>1000</fadetime>
        <posx>0</posx>
        <posy>0</posy>
        <width>1920</width>
        <height>1080</height>
        <texture diffuse="script.plex/masks/background-corner.png" flipx="true">script.plex/white-square.png</texture>
        <colordiffuse>$INFO[Window.Property(background_panel_tr)]</colordiffuse>
    </control>
    <control type="image">
        <visible>!String.IsEmpty(Window.Property(background_panel_bl))</visible>
        <fadetime>1000</fadetime>
        <posx>0</posx>
        <posy>0</posy>
        <width>1920</width>
        <height>1080</height>
        <texture diffuse="script.plex/masks/background-corner.png" flipy="true">script.plex/white-square.png</texture>
        <colordiffuse>$INFO[Window.Property(background_panel_bl)]</colordiffuse>
    </control>
    <control type="image">
        <visible>!String.IsEmpty(Window.Property(background_panel_br))</visible>
        <fadetime>1000</fadetime>
        <posx>0</posx>
        <posy>0</posy>
        <width>1920</width>
        <height>1080</height>
        <texture diffuse="script.plex/masks/background-corner.png" flipx="true" flipy="true">script.plex/white-square.png</texture>
        <colordiffuse>$INFO[Window.Property(background_panel_br)]</colordiffuse>
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
        <visible>!String.IsEmpty(Window.Property(dynamic_backgrounds))</visible>
        <posx>691</posx>
        <posy>0</posy>
        <width>1229</width>
        <height>691</height>
        <!-- 500ms, not instant: this layer sits statically behind the crossfading one below for most
             of its life, but BaseWindow._scheduleBackgroundStaticSync() (kodigui.py) catches it up to
             match roughly 0.5s after every change, once that crossfade settles - see that method's own
             comment for why. Without a fadetime here, that catch-up was itself an abrupt, visible
             texture-reload pop despite the top layer already showing the same art by then; fading it
             folds the catch-up into something that reads as a continuation of the original crossfade
             rather than a second, separate flash. -->
        <fadetime>500</fadetime>
        <texture background="true" diffuse="script.plex/masks/background-vignette.png">$INFO[Window.Property(background_static)]</texture>
        {% include "includes/scale_background.xml.tpl" %}
    </control>
    <control type="image">
        <visible>!String.IsEmpty(Window.Property(dynamic_backgrounds))</visible>
        <posx>691</posx>
        <posy>0</posy>
        <width>1229</width>
        <height>691</height>
        <fadetime>500</fadetime>
        <texture background="true" diffuse="script.plex/masks/background-vignette.png">{{ background_source|default("$INFO[Window.Property(background)]") }}</texture>
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
        <visible>!String.IsEmpty(Window.Property(dynamic_backgrounds))</visible>
        <fadetime>1000</fadetime>
        <posx>691</posx>
        <posy>0</posy>
        <width>1229</width>
        <height>691</height>
        <texture diffuse="script.plex/masks/background-vignette.png">script.plex/white-square.png</texture>
        <colordiffuse>66000000</colordiffuse>
    </control>
</control>