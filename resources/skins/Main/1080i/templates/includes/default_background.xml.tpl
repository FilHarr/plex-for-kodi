{# The flat #111111 under everything is the window's own clear colour (default.xml.tpl's backgroundcolor, the photo
   viewer's), not a full-screen image: a clear costs next to nothing on a tiled GPU, a full-screen layer its whole fill,
   and the panel drew two of them, this image and its base fill (2026-10-28: at a 4K interface on the AM6B, animations
   stuttered). A literal colour, not $INFO[Window.Property(...)], which Kodi resolves against whatever dialog is on top
   (no clear at all while one is open). Only the Recommended view's cover copy keeps a flat layer: it has to hide the
   hub rows passing under it. The solid-background setting, which used to recolour the clear, gets a layer of its own. #}
{% if not panel_cover %}
<control type="image">
    <visible>!String.IsEmpty(Window.Property(use_solid_background))</visible>
    <posx>0</posx>
    <posy>0</posy>
    <width>1920</width>
    <height>1080</height>
    <texture>script.plex/white-square.png</texture>
    <colordiffuse>$INFO[Window.Property(background_colour)]</colordiffuse>
</control>
{% endif %}
<control type="group">
    <visible>String.IsEmpty(Window.Property(use_solid_background))</visible>
    {% if panel_cover %}
    <!-- The cover's own opaque base, which the rows passing under it need. The plain tinted square, not the
         flat background image (background="true"): with the panel's base fill gone, the rows showed through
         the cover, so its opacity had been the base fill's all along (the user, 2026-10-28). -->
    <control type="image">
        <posx>0</posx>
        <posy>0</posy>
        <width>1920</width>
        <height>1080</height>
        <texture>script.plex/white-square.png</texture>
        <!-- colors.Background (lib/colors.py) -->
        <colordiffuse>FF111111</colordiffuse>
    </control>
    {% endif %}
    {% include "includes/background_panel.xml.tpl" %}
    {# Whole top-right hero-art box (the art plus the scrim over it). Dropped at render
       time for the screens that never want it, rather than hidden at runtime via the no_hero_art
       window property below: library grids, list views and Genres are structurally incapable of
       wanting it, and driving that from Python proved unreliable - the property is only ever
       written by LibraryWindow.doRefill(), which onFirstInit()'s fast path (library.py, the
       `elif self.showPanelControl and not self.refill` branch) skips on every view-type swap,
       leaving each freshly constructed window's property unset and the box visible until the
       section was left and re-entered. library.xml.tpl passes suppress_hero_art=True for that
       whole chain. Negative flag deliberately: an undefined variable is falsy here, so every
       other caller of this include keeps the box with no change. #}
    {% if not suppress_hero_art %}
    {# Zoom of the item art inside the hero box, done purely in the skin and anchored at the
       screen's top-right corner: the art control below is made hero_zoom_pad wider than the
       1229x691 box, all of it added on the *left*, so the art's right edge stays on the screen's
       right edge; under <aspectratio>scale</aspectratio> the 16:9 texture then overflows the
       control's height, Kodi clips that overflow to the control rect (GUITexture.cpp sets a clip
       region whenever the scaled texture exceeds it), and aligny="top" keeps the art's top edge on
       the screen's top edge so only the bottom is cut. Zoom = (1229 + pad) / 1229, so 61 -> 1.05x, 122 ->
       1.10x, 406 -> 1.33x. The vignette mask has to be padded on the left by exactly the same
       amount (masks/background-vignette-zoom.png, generated from background-vignette.png by
       docs/notes/vignette-zoom-pad.py - re-run it after changing this) because scalediffuse="false"
       maps the mask onto the whole control rect. Not done via the transcode request: PMS's
       minSize=1 does NOT crop to a non-16:9 size, it returns the whole image scaled up (verified
       live), so there is nothing server-side that can zoom. #}
    {% with hero_zoom_pad = 61 %}
    <!-- shrunk to ~64% and anchored top-right, matching official Plex's own pre_play framing.
         The vignette mask below is a rounded-rectangle falloff (flat sides, curved corners only),
         not a smooth ellipse - fit against real pixel measurements off official Plex renders. An
         ellipse forces curvature into the middle of each edge, which faded too early and smeared
         the transition wider than the real, sharper corner-only curve. -->
    <control type="image">
        <!-- no fallback="" texture here: Kodi shows a fallback for the entire time the real
             texture is downloading/transcoding, not just on genuine failure, and an opaque one
             would sit on top of the color panel above and hide it for however long the art takes
             to fetch. The window's own clear colour (see the top of this file) already covers
             that spot regardless. -->
        <!-- no_hero_art (LibraryWindow._setNoHeroArt, library.py): hides this box on the
             Recommended tab while nothing is bound yet (fresh entry before the hubs land, or a
             section with no hubs), rather than showing the previous section's art. Not a
             per-item-type gate any more - once a hub item is focused the box shows for every
             type. Also set by VideoPlayerWindow while post-play is up
             (setPostPlayBackground, videoplayer.py): that screen's background is the colour
             panel alone. Empty/unset for every other window.
             hero.no_art (LibraryWindow.setHeroInfo, HERO_NO_ART_TYPES; also
             CollectionWindow.setup() for a collection with no art): keeps the info overlay on
             the left but not this art box.
             nav_hidden (global): post-play's hand-over to an item it opens - see default.xml.tpl. -->
        <visible>!String.IsEmpty(Window.Property(dynamic_backgrounds)) + String.IsEmpty(Window.Property(no_hero_art)) + String.IsEmpty(Window.Property(hero.no_art)) + String.IsEmpty(Window(10000).Property(script.plex.nav_hidden))</visible>
        <posx>{{ 691 - hero_zoom_pad }}</posx>
        <posy>0</posy>
        <width>{{ 1229 + hero_zoom_pad }}</width>
        <height>691</height>
        <!-- One layer: Kodi's own <fadetime> crossfade fades the old art out and the new in, the colour
             panel showing through the shared transparent moments. Upstream held the previous art solid
             on a second layer (background_static) under this one; the previous item's art should be gone
             the instant focus moves off it (on request), which left that layer drawing the same art twice
             (2026-10-26). 250ms: shorter reads as less of the previous item's art lingering. -->
        <fadetime>250</fadetime>
        <texture background="true" diffuse="script.plex/masks/background-vignette-zoom.png">{{ background_source|default("$INFO[Window.Property(background)]") }}</texture>
        <!-- lets the 4-corner tinted panel bleed through the art uniformly, not just at the
             vignette's own edge falloff - same sibling-<colordiffuse>-plus-diffuse-mask pattern
             as the scrim control below (colordiffuse as an attribute on <texture> alongside
             diffuse= silently does nothing, this sibling-element form is the one that works).
             White RGB, alpha only, so this is a pure opacity trim - no colour shift of its own.
             85 (52%): between the two stacked 40% layers' 64% and one's 40%, chosen side by side
             (2026-10-26). -->
        <colordiffuse>85FFFFFF</colordiffuse>
        <!-- unconditional (not the needs_scaling-gated scale_background include): "scale" is
             what makes the 16:9 texture cover this deliberately wider-than-16:9 control and overflow
             vertically for the zoom (the default "stretch" would just squash it wider), aligny="top"
             keeps the art's top edge on the screen's top edge (the overflow is cut off the bottom),
             and scalediffuse="false" pins the (padded) vignette mask to this control's rect - the
             default true maps it onto the enlarged texture rect instead, so it would be clipped
             along with the art. -->
        <aspectratio align="center" aligny="top" scalediffuse="false">scale</aspectratio>
    </control>
    {% endwith %}
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
    {% endif %}
    <!-- Full-canvas dim while focus is down in the row content (Roles/Reviews/Extras/Related/etc.)
         below the details block, so that content doesn't have to compete with the backdrop. Driven
         by row.focused (PrePlayWindow.onFocus, preplay.py; ShowWindow.onFocus, subitems.py;
         EpisodesWindow.onFocus, episodes.py) rather than the pre-existing hub.focus property that the
         row-slide animations elsewhere key off - hub.focus is deliberately never cleared once a row's
         been visited (those animations are meant to stay collapsed), but this scrim needs to toggle
         back off when focus returns above the row list, so it gets its own property that does.
         person.py doesn't opt in yet - same onFocus addition would extend this there too, if that
         screen ever gets this same row-scrolling layout. 4D, not 33: dimming increased from 20% to
         30% on request. row_dim_condition: a caller whose rows aren't separate controls can key
         the dim off its own condition instead (the Collection screen: its grid past the first
         row, the same condition as its page slide). -->
    <control type="image">
        <visible>{{ row_dim_condition|default("!String.IsEmpty(Window.Property(row.focused))") }}</visible>
        <animation effect="fade" start="0" end="100" time="600" reversible="true">VisibleChange</animation>
        <posx>0</posx>
        <posy>0</posy>
        <width>1920</width>
        <height>1080</height>
        <texture>script.plex/white-square.png</texture>
        <colordiffuse>4D000000</colordiffuse>
    </control>
</control>