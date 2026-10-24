<!-- The 4-corner tinted background panel over its flat base fill: every screen's (includes/default_background.xml.tpl)
     and the music player's and play queue's, which have nothing over it.

     One corner-anchored falloff shape (masks/background-corner.png), drawn 4x with flipx/flipy for the other 3 corners,
     each tinted solid via colordiffuse - official Plex Android's mechanism (decompiled - see
     docs/notes/hero-art-background-status.md), not a blur or a bilinear 4-corner blend. The colours are the item's
     ultraBlurColors (util.backgroundPanelCorners), set from Python on the controls themselves
     (BaseWindow._paintPanelLayer(), kodigui.py, setColorDiffuse()) rather than through $INFO[Window.Property(...)]:
     Kodi resolves an $INFO colour against the topmost modal dialog while one is open, so every picker or dialog turned
     the corners transparent (2026-10-22), and re-resolves it every frame, so a music track change's info reset dropped
     them for a frame (2026-09-19). A corner with no colour is fully transparent, showing the base fill. colordiffuse
     as a sibling of a texture with diffuse=, as here: the two as attributes on one <texture> tag silently does nothing.

     Two layers (a: 2101-2104, b: 2105-2108), each a group shown by background_panel_layer: a colordiffuse has no fade
     of its own in Kodi, but a group's <visible> change can fade (VisibleChange). BaseWindow._setPanelCorners() paints
     the new colours onto the hidden layer and flips background_panel_layer, so the two cross-fade.

     Params:
       panel_cover - the Recommended view's second copy, over its hub rows: ids 2111-2118.
       static - layer a alone, always shown, and the base fill too: no <visible> condition or fade at all. The music
         screens' (BaseWindow.PANEL_CROSSFADE False), where the panel is the whole background: a <visible> condition
         on a window property also drops out for a frame on each track change, and the screen flashed to the base
         fill (2026-09-19). -->
<control type="image">
    {% if not static %}<visible>!String.IsEmpty(Window.Property(dynamic_backgrounds))</visible>{% endif %}
    <posx>0</posx>
    <posy>0</posy>
    <width>1920</width>
    <height>1080</height>
    <texture>script.plex/white-square.png</texture>
    <!-- colors.Background (lib/colors.py) -->
    <colordiffuse>FF111111</colordiffuse>
</control>
{% for layer, corners in (('a', ((2101, 2111, ''), (2102, 2112, ' flipx="true"'), (2103, 2113, ' flipy="true"'), (2104, 2114, ' flipx="true" flipy="true"'))), ('b', ((2105, 2115, ''), (2106, 2116, ' flipx="true"'), (2107, 2117, ' flipy="true"'), (2108, 2118, ' flipx="true" flipy="true"')))) %}{% if layer == 'a' or not static %}
<control type="group">
    {% if not static %}<visible>String.IsEqual(Window.Property(background_panel_layer),{{ layer }})</visible>
    <animation effect="fade" start="0" end="100" time="200" reversible="true">VisibleChange</animation>{% endif %}
    {% for cid, cover_cid, flips in corners %}
    <control type="image" id="{% if panel_cover %}{{ cover_cid }}{% else %}{{ cid }}{% endif %}">
        <posx>0</posx>
        <posy>0</posy>
        <width>1920</width>
        <height>1080</height>
        <texture diffuse="script.plex/masks/background-corner.png"{{ flips }}>script.plex/white-square.png</texture>
        <colordiffuse>00000000</colordiffuse>
    </control>
    {% endfor %}
</control>
{% endif %}{% endfor %}
