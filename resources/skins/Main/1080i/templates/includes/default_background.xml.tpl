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
    {# The hero art, top right. Dropped at render
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
    <!-- The hero art over the colour panel, as Plex's own apps place it: the right two thirds of the top two thirds,
         unzoomed, at full strength, through a cut-out (masks/hero-art-cutout.png, docs/notes/hero-art-cutout.py) - the
         art in full at the screen's top right corner, the panel fully over it at the box's left and bottom edges.
         Wherever there's no art (none, loading, mid-fade) the panel under it shows. Not a slice of the panel drawn
         back over the art: Kodi fades each image on its own, so two fading layers inside the box and one outside drew
         the box's edges as lines on every item change. -->
    <control type="image">
        <!-- no fallback="" texture here: Kodi shows a fallback for the entire time the real
             texture is downloading/transcoding, not just on genuine failure, and an opaque one
             would hide the colour panel for however long the art takes to fetch. -->
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
        <posx>640</posx>
        <posy>0</posy>
        <width>1280</width>
        <height>720</height>
        <!-- One layer: Kodi's own <fadetime> crossfade fades the old art out and the new in, the colour
             panel showing through the shared transparent moments. Upstream held the previous art solid
             on a second layer (background_static) under this one; the previous item's art should be gone
             the instant focus moves off it (on request), which left that layer drawing the same art twice
             (2026-10-26). 250ms: shorter reads as less of the previous item's art lingering. -->
        <fadetime>250</fadetime>
        <texture background="true" diffuse="script.plex/masks/hero-art-cutout.png">{{ background_source|default("$INFO[Window.Property(background)]") }}</texture>
        <!-- cover: non-16:9 art is cropped to the box (Kodi clips the overflow to the control); scalediffuse="false"
             keeps the cut-out on the box rather than on the overflowing art -->
        <aspectratio align="center" aligny="center" scalediffuse="false">scale</aspectratio>
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