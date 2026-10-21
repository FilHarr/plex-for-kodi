<!-- An OSD card row below the video player's timeline: the chapters (group 500 / list 501) and the play queue
     (group 510 / list 511), stacked - down from the timeline reaches the chapters, down again the queue. Each is
     never seen until it has focus, and then cross-fades in where the seekbar, times, buttons and skip button were
     (they fade out while either row has focus); up goes back the way it came.
     Never hidden while unfocused, only faded to nothing (the reversible Conditional below): Kodi only runs a list's
     scroll while it's drawn, so this way SeekDialog.syncRows() can move a row onto the playing chapter or item out of
     sight - selected as it took focus, the scroll played during the fade-in. Group 801's own delayed Hidden fade
     keeps it drawn while the OSD closes, so leaving the OSD from a row fades it out too rather than leaving that to
     replay on the next open. An empty row can't take focus, so Kodi passes over it to the next one in the same
     direction (its own onup/ondown) - hence the enable condition as well, and the chapters' ondown to the queue.
     Each item: art, its name, and a smaller line under it (the 'sub' property - a chapter's start time; a queue
     item's S/E, show and length, or a film's year and length), gold on the queue's playing item ('playing'), which
     also gets post-play's play overlay on its art.
     Full screen width; 300x168 art (SeekDialog.CHAPTER_THUMB_DIM requests it at that size), 40 apart, the first at
     x 40 under the header. Header 779, list 809-1049: the layouts start 12 down so the focused item's zoom and ring
     (about 7px above the art) stay inside the list, which clips to its own box.
     A fixedlist like the other screens' hub rows: focus stays in the first slot and the items scroll under it.
     movement = itemsPerPage - 1, itemsPerPage being (1920 - 340) / 340 + 1 = 5; without it Kodi pins the focus slot
     from item 1 and leaves blank space past the last item.
     Uses: group_id, list_id, label_prop (the header's window property), enable_prop (set while the row has items),
     onup, ondown. -->
<control type="group" id="{{ group_id }}">
    <animation effect="fade" start="100" end="0" time="200" reversible="true" condition="!Control.HasFocus({{ list_id }})">Conditional</animation>
    <posx>0</posx>
    <posy>{{ vscale(779) }}</posy>
    <!-- The header. A 30 box at -5 keeps the text's centre where an older 20 box at 0 had it, the 25 font growing
         round it rather than down into the row. -->
    <control type="label">
        <posx>40</posx>
        <posy>{{ vscale(-5) }}</posy>
        <width>1800</width>
        <height>{{ vscale(30) }}</height>
        <font>font25_title</font>
        <align>left</align>
        <aligny>center</aligny>
        <textcolor>FFFFFFFF</textcolor>
        <!-- the row titles' shadow elsewhere (Recommended's, album_track_row.xml.tpl's) -->
        <shadowcolor>66000000</shadowcolor>
        <label>$INFO[Window.Property({{ label_prop }})]</label>
    </control>
    <control type="fixedlist" id="{{ list_id }}">
        <enable>!String.IsEmpty(Window.Property({{ enable_prop }}))</enable>
        <hitrect x="-20" y="-20" w="10" h="10" />
        <posx>0</posx>
        <posy>{{ vscale(30) }}</posy>
        <width>1920</width>
        <height>{{ vscale(240) }}</height>
        <onup>{{ onup }}</onup>
        <ondown>{{ ondown }}</ondown>
        <!-- Dead stops at both ends: with no onleft/onright of its own, a list wraps round. -->
        <onleft>noop</onleft>
        <onright>noop</onright>
        <focusposition>0</focusposition>
        <movement>4</movement>
        <scrolltime>200</scrolltime>
        <orientation>horizontal</orientation>
        <preloaditems>4</preloaditems>
        <!-- The 16:9 card treatment (hub_focusedlayout_ar16x9.xml.tpl), made for this 300x168 art the way Categories
             made it for its 399 (script-plex-genres.xml.tpl): rounded corners from masks/ar16x9-mask-300.png and a
             ring from masks/ring-mask-ar16x9-300.png, both drawn at this size (4x) rather than the 512x288 card's
             stretched, which would shrink the corners and thin the ring - art corners 11, ring 3 out each side, a
             2px stroke 1 clear of the art, corners 14. The focused art zooms 104% about its own centre; 168, not
             169, so that zoom leaves it centred in its ring at 1080p. The fallback sits under the art with the same
             mask and box, so their corners can't disagree. -->
        <itemlayout width="340">
            <control type="group">
                <!-- A dark card under the placeholder: these rows sit over the video, where the semi-transparent
                     placeholder on a light picture reads as a gap. The art covers it once it's in; FF262626 is the
                     spoiler card's fill, so the two differ only by their icon. -->
                <control type="image">
                    <posx>40</posx>
                    <posy>{{ vscale(12) }}</posy>
                    <width>300</width>
                    <height>{{ vscale(168) }}</height>
                    <texture diffuse="script.plex/masks/ar16x9-mask-300.png">script.plex/white-square.png</texture>
                    <aspectratio scalediffuse="false">scale</aspectratio>
                    <colordiffuse>FF262626</colordiffuse>
                </control>
                <control type="image">
                    <visible>String.IsEmpty(ListItem.Property(spoiler))</visible>
                    <posx>40</posx>
                    <posy>{{ vscale(12) }}</posy>
                    <width>300</width>
                    <height>{{ vscale(168) }}</height>
                    <texture diffuse="script.plex/masks/ar16x9-mask-300.png">script.plex/thumb_fallbacks/movie16x9.png</texture>
                    <aspectratio scalediffuse="false">scale</aspectratio>
                    <colordiffuse>FFAAAAAA</colordiffuse>
                </control>
                <control type="image">
                    <posx>40</posx>
                    <posy>{{ vscale(12) }}</posy>
                    <width>300</width>
                    <height>{{ vscale(168) }}</height>
                    <texture background="true" diffuse="script.plex/masks/ar16x9-mask-300.png">$INFO[ListItem.Thumb]</texture>
                    <aspectratio scalediffuse="false">scale</aspectratio>
                    <colordiffuse>FFAAAAAA</colordiffuse>
                </control>
                <!-- Spoilers (SeekDialog.spoilerHiding()): pictures hidden, so the card's dark fill and the eye-slash
                     (indicators/hidden.png, as for hidden hubs) - not the film placeholder, which means "no picture". -->
                <control type="group">
                    <visible>!String.IsEmpty(ListItem.Property(spoiler))</visible>
                    <control type="image">
                        <posx>40</posx>
                        <posy>{{ vscale(12) }}</posy>
                        <width>300</width>
                        <height>{{ vscale(168) }}</height>
                        <texture diffuse="script.plex/masks/ar16x9-mask-300.png">script.plex/white-square.png</texture>
                        <aspectratio scalediffuse="false">scale</aspectratio>
                        <colordiffuse>FF262626</colordiffuse>
                    </control>
                    <control type="image">
                        <posx>166</posx>
                        <posy>{{ vscale(72) }}</posy>
                        <width>48</width>
                        <height>{{ vscale(48) }}</height>
                        <texture>script.plex/indicators/hidden.png</texture>
                        <colordiffuse>66FFFFFF</colordiffuse>
                    </control>
                </control>
                <!-- The playing item: post-play's play overlay (script-plex-video_player.xml.tpl, the next item's art) -
                     a 64 dark circle centred on the art (190,96) with the 38.75 play glyph in it - the glyph gold, as this
                     item's second line is. -->
                <control type="group">
                    <visible>!String.IsEmpty(ListItem.Property(playing))</visible>
                    <posx>158</posx>
                    <posy>{{ vscale(64) }}</posy>
                    <control type="image">
                        <posx>0</posx>
                        <posy>0</posy>
                        <width>64</width>
                        <height>{{ vscale(64) }}</height>
                        <texture colordiffuse="99000000">script.plex/indicators/circle-152.png</texture>
                    </control>
                    <control type="image">
                        <posx>12.625</posx>
                        <posy>{{ vscale(12.625) }}</posy>
                        <width>38.75</width>
                        <height>{{ vscale(38.75) }}</height>
                        <texture>script.plex/indicators/tile-play.png</texture>
                        <colordiffuse>CCE5A00D</colordiffuse>
                    </control>
                </control>
                <control type="label">
                    <posx>40</posx>
                    <posy>{{ vscale(188) }}</posy>
                    <width>300</width>
                    <height>{{ vscale(24) }}</height>
                    <font>font20_title</font>
                    <align>center</align>
                    <aligny>center</aligny>
                    <textcolor>FFAAAAAA</textcolor>
                    <label>$INFO[ListItem.Label]</label>
                </control>
                <control type="label">
                    <visible>String.IsEmpty(ListItem.Property(playing))</visible>
                    <posx>40</posx>
                    <posy>{{ vscale(212) }}</posy>
                    <width>300</width>
                    <height>{{ vscale(24) }}</height>
                    <font>font8</font>
                    <align>center</align>
                    <aligny>center</aligny>
                    <textcolor>99AAAAAA</textcolor>
                    <label>$INFO[ListItem.Property(sub)]</label>
                </control>
                <control type="label">
                    <visible>!String.IsEmpty(ListItem.Property(playing))</visible>
                    <posx>40</posx>
                    <posy>{{ vscale(212) }}</posy>
                    <width>300</width>
                    <height>{{ vscale(24) }}</height>
                    <font>font8</font>
                    <align>center</align>
                    <aligny>center</aligny>
                    <textcolor>CCE5A00D</textcolor>
                    <label>$INFO[ListItem.Property(sub)]</label>
                </control>
            </control>
        </itemlayout>
        <focusedlayout width="340">
            <control type="group">
                <control type="group">
                    <!-- 190,96 = the art's centre (40 + 300/2, 12 + 168/2) -->
                    <animation effect="zoom" start="100" end="104" time="100" center="190,{{ vscale(96) }}" reversible="false">Focus</animation>
                    <animation effect="zoom" start="104" end="100" time="100" center="190,{{ vscale(96) }}" reversible="false">UnFocus</animation>
                    <!-- A dark card under the placeholder: these rows sit over the video, where the semi-transparent
                         placeholder on a light picture reads as a gap. The art covers it once it's in; FF262626 is the
                         spoiler card's fill, so the two differ only by their icon. -->
                    <control type="image">
                        <posx>40</posx>
                        <posy>{{ vscale(12) }}</posy>
                        <width>300</width>
                        <height>{{ vscale(168) }}</height>
                        <texture diffuse="script.plex/masks/ar16x9-mask-300.png">script.plex/white-square.png</texture>
                        <aspectratio scalediffuse="false">scale</aspectratio>
                        <colordiffuse>FF262626</colordiffuse>
                    </control>
                    <control type="image">
                        <visible>String.IsEmpty(ListItem.Property(spoiler))</visible>
                        <posx>40</posx>
                        <posy>{{ vscale(12) }}</posy>
                        <width>300</width>
                        <height>{{ vscale(168) }}</height>
                        <texture diffuse="script.plex/masks/ar16x9-mask-300.png">script.plex/thumb_fallbacks/movie16x9.png</texture>
                        <aspectratio scalediffuse="false">scale</aspectratio>
                    </control>
                    <control type="image">
                        <posx>40</posx>
                        <posy>{{ vscale(12) }}</posy>
                        <width>300</width>
                        <height>{{ vscale(168) }}</height>
                        <texture background="true" diffuse="script.plex/masks/ar16x9-mask-300.png">$INFO[ListItem.Thumb]</texture>
                        <aspectratio scalediffuse="false">scale</aspectratio>
                    </control>
                    <!-- Spoilers (SeekDialog.spoilerHiding()): pictures hidden, so the card's dark fill and the eye-slash
                         (indicators/hidden.png, as for hidden hubs) - not the film placeholder, which means "no picture". -->
                    <control type="group">
                        <visible>!String.IsEmpty(ListItem.Property(spoiler))</visible>
                        <control type="image">
                            <posx>40</posx>
                            <posy>{{ vscale(12) }}</posy>
                            <width>300</width>
                            <height>{{ vscale(168) }}</height>
                            <texture diffuse="script.plex/masks/ar16x9-mask-300.png">script.plex/white-square.png</texture>
                            <aspectratio scalediffuse="false">scale</aspectratio>
                            <colordiffuse>FF262626</colordiffuse>
                        </control>
                        <control type="image">
                            <posx>166</posx>
                            <posy>{{ vscale(72) }}</posy>
                            <width>48</width>
                            <height>{{ vscale(48) }}</height>
                            <texture>script.plex/indicators/hidden.png</texture>
                            <colordiffuse>B3FFFFFF</colordiffuse>
                        </control>
                    </control>
                    <!-- The playing item: post-play's play overlay (script-plex-video_player.xml.tpl, the next item's art) -
                         a 64 dark circle centred on the art (190,96) with the 38.75 play glyph in it - the glyph gold, as this
                         item's second line is. -->
                    <control type="group">
                        <visible>!String.IsEmpty(ListItem.Property(playing))</visible>
                        <posx>158</posx>
                        <posy>{{ vscale(64) }}</posy>
                        <control type="image">
                            <posx>0</posx>
                            <posy>0</posy>
                            <width>64</width>
                            <height>{{ vscale(64) }}</height>
                            <texture colordiffuse="99000000">script.plex/indicators/circle-152.png</texture>
                        </control>
                        <control type="image">
                            <posx>12.625</posx>
                            <posy>{{ vscale(12.625) }}</posy>
                            <width>38.75</width>
                            <height>{{ vscale(38.75) }}</height>
                            <texture>script.plex/indicators/tile-play.png</texture>
                            <colordiffuse>FFE5A00D</colordiffuse>
                        </control>
                    </control>
                    <control type="image">
                        <visible>Control.HasFocus({{ list_id }})</visible>
                        <posx>37</posx>
                        <posy>{{ vscale(9) }}</posy>
                        <width>306</width>
                        <height>{{ vscale(174) }}</height>
                        <texture diffuse="script.plex/masks/ring-mask-ar16x9-300.png">script.plex/white-square.png</texture>
                        <colordiffuse>FFE9A20D</colordiffuse>
                    </control>
                </control>
                <control type="label">
                    <posx>40</posx>
                    <posy>{{ vscale(188) }}</posy>
                    <width>300</width>
                    <height>{{ vscale(24) }}</height>
                    <font>font20_title</font>
                    <align>center</align>
                    <aligny>center</aligny>
                    <scroll>true</scroll>
                    <textcolor>FFD2CCCE</textcolor>
                    <label>$INFO[ListItem.Label]</label>
                </control>
                <control type="label">
                    <visible>String.IsEmpty(ListItem.Property(playing))</visible>
                    <posx>40</posx>
                    <posy>{{ vscale(212) }}</posy>
                    <width>300</width>
                    <height>{{ vscale(24) }}</height>
                    <font>font8</font>
                    <align>center</align>
                    <aligny>center</aligny>
                    <textcolor>CCD2CCCE</textcolor>
                    <label>$INFO[ListItem.Property(sub)]</label>
                </control>
                <control type="label">
                    <visible>!String.IsEmpty(ListItem.Property(playing))</visible>
                    <posx>40</posx>
                    <posy>{{ vscale(212) }}</posy>
                    <width>300</width>
                    <height>{{ vscale(24) }}</height>
                    <font>font8</font>
                    <align>center</align>
                    <aligny>center</aligny>
                    <textcolor>FFE5A00D</textcolor>
                    <label>$INFO[ListItem.Property(sub)]</label>
                </control>
            </control>
        </focusedlayout>
    </control>
</control>
