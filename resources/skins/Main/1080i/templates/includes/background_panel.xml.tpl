<!-- The colour panel over its flat base fill: every screen's (includes/default_background.xml.tpl) and the music
     player's and play queue's, which have nothing over it.

     The whole panel as one small texture Python draws from the item's 4 corner colours (lib/panel_texture.py) and sets
     with setImage() (BaseWindow._paintPanelTexture(), kodigui.py), which Kodi stretches over the screen: one opaque
     draw. Set from Python on the control itself rather than through $INFO[Window.Property(...)]: Kodi resolves an
     $INFO against the topmost modal dialog while one is open, so every picker or dialog lost the panel (2026-10-22),
     and re-resolves it every frame, so a music track change's info reset dropped it for a frame (2026-09-19). An item
     with no colours at all gets no texture: the window's own colour shows.

     Its own <fadetime> crossfades one item's panel into the next's, so it needs no second layer. The diffuse is the
     dither (docs/notes/panel-dither.py): Kodi multiplies the texture by it, so it costs no layer of its own. Not
     background="true": the files are tiny, and that would put every one in Kodi's texture cache.

     Params:
       panel_cover - the Recommended view's second copy, over its hub rows: id 2119.
       static - no fade, and the base fill under it: the music screens', where the panel is the whole background and
         changes with every track. Only they draw the base fill: everywhere else the window clears to the same colour
         (default.xml.tpl), or, in the Recommended view's cover, its flat image does (default_background.xml.tpl). -->
{% if static %}
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
<control type="image" id="{% if panel_cover %}2119{% else %}2109{% endif %}">
    <posx>0</posx>
    <posy>0</posy>
    <width>1920</width>
    <height>1080</height>
    {% if not static %}<fadetime>200</fadetime>{% endif %}
    <texture diffuse="script.plex/masks/panel-dither.png"></texture>
</control>
