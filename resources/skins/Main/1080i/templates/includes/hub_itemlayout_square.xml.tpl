<!-- Square item layout (240x240) - uses hub_id variable.
     Card recipe matches the music screens' square grid (script-plex-squares.xml.tpl) and the
     Artist screen's album rows (includes/artist_album_row.xml.tpl) exactly: 240 art, thumb+24
     drop-shadow-directional.png plate inset (-3,-3) for a 3px top/left, 21px bottom/right spread.
     Grew from 220 on request (2026-09-20) so square hub tiles are the same size as everywhere else.
     Item width 272 = 240 art + 32 gap: the art sits 8px into the item (the outer group's own 5 +
     the card group's 3), so adjacent tiles' art is 32px apart - the same art-to-art gap the
     episode screen's 16:9 row uses (script-plex-episodes.xml.tpl's 544-wide items / 512 art). -->
<itemlayout width="272" condition="String.IsEqual(Window.Property(hub.display.{{ hub_id }}),square)">
    <control type="group">
        <!-- 5, not 55: compensates for the parent grouplist's posx moving from 55 to 105
             (see script-plex-recommended.xml.tpl) so this item's resting position is unchanged. -->
        <posx>5</posx>
        <!-- Always top-anchored - see hub_itemlayout_poster.xml.tpl's own matching comment for why
             peek-above's crop no longer needs a manual per-type posy override here. -->
        <!-- 52, matching hub_itemlayout_poster.xml.tpl (was 72): the same title-to-art gap on
             every row type, on request (2026-09-20). ROW_CONTENT_HEIGHT (library.py) dropped by
             the same 20 for this type. -->
        <posy>{{ vscale(52) }}</posy>
        <control type="group">
            <control type="image">
                <posx>0</posx>
                <posy>0</posy>
                <width>264</width>
                <height>{{ vscale(264) }}</height>
                <texture border="24">script.plex/drop-shadow-directional.png</texture>
            </control>
            <posx>3</posx>
            <posy>3</posy>
            <control type="group">
                <visible>!String.IsEmpty(ListItem.Property(is.end))</visible>
                <control type="image">
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>240</width>
                    <height>{{ vscale(240) }}</height>
                    <texture colordiffuse="FF404040">script.plex/white-square.png</texture>
                </control>
                <control type="image">
                    <visible>String.IsEmpty(ListItem.Property(is.updating))</visible>
                    <posx>89.5</posx>
                    <posy>{{ vscale(70) }}</posy>
                    <width>61</width>
                    <height>{{ vscale(100) }}</height>
                    <texture colordiffuse="40000000">script.plex/indicators/chevron-white.png</texture>
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
            <control type="image">
                <!-- Fill for is.photo's letterboxed thumb below - photos keep their full frame
                     (no crop) so this shows through wherever the image doesn't reach. -->
                <visible>!String.IsEmpty(ListItem.Property(is.photo))</visible>
                <posx>0</posx>
                <posy>0</posy>
                <width>240</width>
                <height>{{ vscale(240) }}</height>
                <texture diffuse="script.plex/masks/square-mask.png">script.plex/white-square.png</texture>
                <colordiffuse>FF191B1E</colordiffuse>
            </control>
            <control type="image">
                <!-- Native fallback= (not a separate stacked/masked control - see this include's
                     own history) - Kodi shows this while ListItem.Thumb is empty/loading/failed,
                     swapping seamlessly once it resolves, so there's only ever one masked layer for
                     the art, never two independently-rounded corners that could misalign. -->
                <visible>String.IsEmpty(ListItem.Property(is.photo))</visible>
                <posx>0</posx>
                <posy>0</posy>
                <width>240</width>
                <height>{{ vscale(240) }}</height>
                <texture background="true" diffuse="script.plex/masks/square-mask.png" fallback="$INFO[ListItem.Property(thumb.fallback)]">$INFO[ListItem.Thumb]</texture>
                <aspectratio scalediffuse="false">scale</aspectratio>
            </control>
            <control type="image">
                <!-- Real photos vary wildly in aspect ratio - crop-to-fill (like posters/art) would
                     chop off arbitrary parts of someone's actual photo, so these get shown whole
                     and letterboxed instead, matching Plex's own photo hub presentation. -->
                <visible>!String.IsEmpty(ListItem.Property(is.photo))</visible>
                <posx>0</posx>
                <posy>0</posy>
                <width>240</width>
                <height>{{ vscale(240) }}</height>
                <texture background="true" diffuse="script.plex/masks/square-mask.png" fallback="$INFO[ListItem.Property(thumb.fallback)]">$INFO[ListItem.Thumb]</texture>
                <aspectratio scalediffuse="false">keep</aspectratio>
            </control>
            <control type="group">
                <visible>!String.IsEmpty(ListItem.Property(progress))</visible>
                <posx>0</posx>
                <posy>{{ vscale(230) }}</posy>
                <control type="image">
                    <posx>0</posx>
                    <posy>0</posy>
                    <width>240</width>
                    <height>{{ vscale(10) }}</height>
                    <texture>script.plex/white-square.png</texture>
                    <colordiffuse>C0000000</colordiffuse>
                </control>
                <control type="image">
                    <posx>0</posx>
                    <posy>1</posy>
                    <width>240</width>
                    <height>{{ vscale(8) }}</height>
                    <texture>$INFO[ListItem.Property(progress)]</texture>
                    <colordiffuse>FFCC7B19</colordiffuse>
                </control>
            </control>
            <!-- hub.nolabels.<id> (LibraryWindow.getHubRenderFlags()'s no_labels, library.py):
                 music hubs (album/artist/track items) show bare art with nothing underneath, on
                 request (2026-09-20); photo and playlist hubs keep their captions. Row height
                 follows this too - ROW_CONTENT_HEIGHT_SQUARE_NO_LABELS. -->
            <control type="label">
                <visible>String.IsEmpty(Window.Property(hub.nolabels.{{ hub_id }}))</visible>
                <scroll>false</scroll>
                <posx>0</posx>
                <posy>{{ vscale(250) }}</posy>
                <width>240</width>
                <height>{{ vscale(35) }}</height>
                <font>font10</font>
                <align>center</align>
                <textcolor>FFFFFFFF</textcolor>
                <label>$INFO[ListItem.Label]</label>
            </control>
            <control type="label">
                <visible>String.IsEmpty(Window.Property(hub.nolabels.{{ hub_id }})) + !String.IsEmpty(Window.Property(hub.text2lines.{{ hub_id }}))</visible>
                <scroll>false</scroll>
                <posx>0</posx>
                <posy>{{ vscale(277) }}</posy>
                <width>240</width>
                <height>{{ vscale(35) }}</height>
                <font>font10</font>
                <align>center</align>
                <!-- AAFFFFFF, not FFFFFFFF: the music grid's own second-line colour (script-plex-squares.xml.tpl's
                     album.artist label) - title bright, detail line dimmed. -->
                <textcolor>AAFFFFFF</textcolor>
                <label>$INFO[ListItem.Label2]</label>
            </control>
        </control>
    </control>
</itemlayout>
