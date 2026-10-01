<!-- A hub row's trailing "See more" item (is.more - LibraryWindow._bindHubToControl(), library.py:
     appended when the row's 20-item cap, home.HUB_ROW_MAX_ITEMS, cut the hub short). Replaces the
     old "load more" placeholder tile (is.end + in-row pagination) - on request, 2026-09-21. A pill,
     not a tile: the card (shadow/art/ring/zoom) is hidden for this item by its own is.more gate in
     each hub_itemlayout_*/hub_focusedlayout_* include, and this sits where the card's art would
     be, flush with its left edge and centred on its height.

     Params:
       hub_id - the row's list control id, for the focus gate
       px, py - this group's own position inside the item's outer group. px is 3 everywhere:
                the card's own art inset, so the pill's left edge sits exactly where this item's
                art would start - 32px after the previous tile's art, the row's own gap (left-
                aligned, not centred on the art, on request). py is per display type, centring
                the 50-tall pill on the art's height - see each call site

     The section tabs' (includes/section_tabs.xml.tpl) 50-tall 33FFFFFF rounded focus pill, but
     font10 (23px, on request - was the tabs' font12) and sized to the caption: "See more" at
     font10 is 103px of Inter advance width (102 in the old InterUI) with a 17px cap height, which
     a 50px pill centres with ~16.5px of clear space above and below the caps - so 137 = 103 + 2 x 17, the same
     clearance left and right, on request. Unfocused it keeps a fainter fill so the item still
     reads as a control at rest (the tabs are bare text at rest - a text-only "See more" at the
     end of a row of art would read as a stray label). The fill is gated on real control focus,
     not just selection - a focusedlayout renders for a row's selected item whether or not the
     row has focus. The caption is the item's own label (T(35093)). -->
<control type="group">
    <visible>!String.IsEmpty(ListItem.Property(is.more))</visible>
    <posx>{{ px }}</posx>
    <posy>{{ py|vscale }}</posy>
    <control type="image">
        <visible>!Control.HasFocus({{ hub_id }})</visible>
        <posx>0</posx>
        <posy>0</posy>
        <width>137</width>
        <height>{{ vscale(50) }}</height>
        <colordiffuse>1AFFFFFF</colordiffuse>
        <texture border="10">script.plex/white-square-rounded.png</texture>
    </control>
    <control type="image">
        <visible>Control.HasFocus({{ hub_id }})</visible>
        <posx>0</posx>
        <posy>0</posy>
        <width>137</width>
        <height>{{ vscale(50) }}</height>
        <colordiffuse>33FFFFFF</colordiffuse>
        <texture border="10">script.plex/white-square-rounded.png</texture>
    </control>
    <control type="label">
        <posx>0</posx>
        <posy>0</posy>
        <width>137</width>
        <height>{{ vscale(50) }}</height>
        <font>font10</font>
        <align>center</align>
        <aligny>center</aligny>
        <textcolor>FFFFFFFF</textcolor>
        <label>$INFO[ListItem.Label]</label>
    </control>
</control>
