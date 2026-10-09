{% extends "default.xml.tpl" %}
{# The Filmography button, not the poster row (on request, 2026-10-08): focusing the row slides
   the screen down to it (group 50 below), which it did as the screen opened. The button shows
   once its property is set, after this is read, so person.py focuses it too (focusDefault()). #}
{# The Filmography button's group (303), not the button (302): the button shows only once
   filmography.available is set, after the window opens, and Kodi logged "Control 302 ... has been
   asked to focus, but it can't" each time (AM6B, 2026-10-09). A group with nothing to focus yet is
   passed over quietly; focusDefault() (person.py) focuses the button once it shows. #}
{% block headers %}<defaultcontrol>303</defaultcontrol>{% endblock %}
{% block header %}
    {{ super() }}
    {% include "includes/sidebar.xml.tpl" %}
    <!-- Declared last so groups 802/901 draw on top - see script-plex-pre_play.xml.tpl's own copy
         of this include for the full reasoning (this window is one of the seven real hosted-shell
         types too, same _sidebarTarget()-aware Python side, same onClick forwarding - shared with
         ActorWindow/DirectorWindow since they subclass PersonWindow (person.py) without
         overriding onClick or xmlFile). -->
    {% include "includes/sidebar_dropdowns.xml.tpl" %}
{% endblock header %}

{% block content %}
<!-- No background of its own: the shared one (includes/default_background.xml.tpl), showing the
     neutral colour panel - person.py's paintInitialBackground(). -->

<!-- Main Content -->
<control type="group" id="50">
    <!-- Slide right while the sidebar rail is expanded (focused), matching every other ported screen. -->
    <animation effect="slide" end="220,0" time="200" tween="sine" easing="inout" condition="ControlGroup(9000).HasFocus(0)">Conditional</animation>
    <!-- Into the poster row (its filter button or its posters, group 500), the screen slides up so
         the whole row shows - its last caption line, at 1263 where it rests, ends at 1038 - and back
         down out of it (on request, 2026-10-08). -->
    <animation effect="slide" end="0,{{ vscale(-225) }}" time="200" tween="sine" easing="inout" condition="ControlGroup(500).HasFocus(0)">Conditional</animation>
    <!-- posx=60, not 0: clears the collapsed sidebar rail's icon column - see includes/sidebar.xml.tpl. -->
    <posx>60</posx>
    <posy>0</posy>

    <!-- Person Details Section -->
    <control type="group">
        <posx>60</posx>
        <posy>{{ vscale(120) }}</posy>
        <width>1800</width>
        <height>{{ vscale(580) }}</height>

        <!-- Photo: Discover's 2:3 cover poster (person.py's onPersonDetails(); on request,
             2026-10-08 - it was the square photo in a circle), 376x564: the text column's height at
             its longest, its top level with the name's box. A poster card as the row's below have
             them - the rounded poster mask on the directional drop shadow (shadow box the art plus
             24, the art 3 in), the person fallback until it loads. The square photo, without a
             cover poster, is cropped to the shape from its top. -->
        <control type="group">
            <posx>0</posx>
            <posy>0</posy>
            <control type="image">
                <posx>-3</posx>
                <posy>{{ vscale(-3) }}</posy>
                <width>400</width>
                <height>{{ vscale(588) }}</height>
                <texture border="24">script.plex/drop-shadow-directional.png</texture>
            </control>
            <control type="image">
                <posx>0</posx>
                <posy>0</posy>
                <width>376</width>
                <height>{{ vscale(564) }}</height>
                <texture background="true" diffuse="script.plex/masks/poster-mask.png" fallback="script.plex/thumb_fallbacks/role.png">$INFO[Window.Property(person.thumb)]</texture>
                <aspectratio scalediffuse="false" aligny="top">scale</aspectratio>
            </control>
        </control>

        <!-- Person Info (on request, 2026-10-08): the name; the credit types, Discover's names in its
             order less Appearances and Additional Credits (person.creditTypesLine()); born, with
             the age while they're alive; died, with the age then; the bio, in pre-play's summary
             box and opening the whole of it the same way; the social links, an icon and the
             handle a line; the Filmography button. A vertical grouplist, so a line with nothing to
             show is hidden and everything below moves up - each line a group carrying the gap
             above it, so a hidden line takes its gap with it: 25 above born, 15 above died, 25
             above the bio, 25 above the first social link and 15 above each other, 25 above the
             button (on request, 2026-10-08). Its two focus stops, the bio and the button, carry their own navigation: a
             grouplist's own is broken by the labels between (see library_posters.xml.tpl's
             notes), its children's explicit tags aren't. Each child 5 in from its edge: a
             grouplist clips to its own box, and the bio's focus highlight reaches 5 outside the
             bio. -->
        <control type="grouplist">
            <!-- 416: 40 right of the 376 poster, as it was of the 300 photo -->
            <posx>416</posx>
            <posy>0</posy>
            <width>1400</width>
            <height>{{ vscale(580) }}</height>
            <orientation>vertical</orientation>
            <itemgap>0</itemgap>
            <usecontrolcoords>true</usecontrolcoords>
            <onleft>9000</onleft>

            <!-- Name: Recommended's hero heading for an album (script-plex-recommended.xml.tpl) -
                 font45_title, white, a 61-tall box -->
            <control type="label">
                <posx>5</posx>
                <width>1400</width>
                <height>{{ vscale(61) }}</height>
                <font>font45_title</font>
                <align>left</align>
                <aligny>center</aligny>
                <textcolor>FFFFFFFF</textcolor>
                <label>$INFO[Window.Property(person.name)]</label>
            </control>

            <!-- Credit types: "Producer, Actor, Writer, Editor" - the hero's album artist line under
                 that heading, font30_title, but white. A 36 box, close round its 30px text. -->
            <control type="label">
                <posx>5</posx>
                <visible>!String.IsEmpty(Window.Property(person.credit_types))</visible>
                <width>1400</width>
                <height>{{ vscale(36) }}</height>
                <font>font30_title</font>
                <align>left</align>
                <aligny>center</aligny>
                <textcolor>FFFFFFFF</textcolor>
                <label>$INFO[Window.Property(person.credit_types)]</label>
            </control>

            <!-- Born, then died (PersonWindow.lifeLines()): "Born" / "Died" in the bio's grey, then
                 20 along the date in white, "2 April 1975 (51)" - font10, a 26 box. -->
            {# The gap and the line's height with it written out: ibis can't do arithmetic inside a
               call's arguments - vscale(gap + 26) rendered as the text "vscale(['gap'])", a 0
               height, and the lines collapsed onto each other. #}
            {% for prop, string_id, gap, line_height in (("born", 35164, 25, 51), ("died", 35165, 15, 41)) %}
            <control type="group">
                <posx>5</posx>
                <visible>!String.IsEmpty(Window.Property(person.{{ prop }}))</visible>
                <width>1400</width>
                <height>{{ vscale(line_height) }}</height>
                <control type="grouplist">
                    <posx>0</posx>
                    <posy>{{ vscale(gap) }}</posy>
                    <width>1400</width>
                    <height>{{ vscale(26) }}</height>
                    <orientation>horizontal</orientation>
                    <itemgap>20</itemgap>
                    <control type="label">
                        <width>auto</width>
                        <height>{{ vscale(26) }}</height>
                        <font>font10</font>
                        <aligny>center</aligny>
                        <textcolor>FFD2CCCE</textcolor>
                        <label>$ADDON[script.plexmod {{ string_id }}]</label>
                    </control>
                    <control type="label">
                        <width>auto</width>
                        <height>{{ vscale(26) }}</height>
                        <font>font10</font>
                        <aligny>center</aligny>
                        <textcolor>FFFFFFFF</textcolor>
                        <label>$INFO[Window.Property(person.{{ prop }})]</label>
                    </control>
                </control>
            </control>
            {% endfor %}

            <!-- Bio: pre-play's summary box (script-plex-pre_play.xml.tpl) - 813x90, font10, its grey
                 and shadow, the text cut to its three lines (util.summaryForBox()), an invisible
                 button over it opening the whole of it (summaryButtonClicked()), and its focus
                 highlight 5px out on every side. 25 above it. -->
            <control type="group">
                <posx>5</posx>
                <visible>!String.IsEmpty(Window.Property(person.summary))</visible>
                <width>823</width>
                <height>{{ vscale(115) }}</height>
                <control type="textbox">
                    <posx>0</posx>
                    <posy>{{ vscale(25) }}</posy>
                    <width>813</width>
                    <height>{{ vscale(90) }}</height>
                    <font>font10</font>
                    <align>left</align>
                    <textcolor>FFD2CCCE</textcolor>
                    <shadowcolor>66000000</shadowcolor>
                    <scrolltime>200</scrolltime>
                    <autoscroll delay="2000" time="2000" repeat="10000">true</autoscroll>
                    <label>$INFO[Window.Property(person.summary)]</label>
                </control>
                <control type="button" id="310">
                    <visible>!String.IsEmpty(Window.Property(person.summary))</visible>
                    <posx>0</posx>
                    <posy>{{ vscale(25) }}</posy>
                    <width>813</width>
                    <height>{{ vscale(90) }}</height>
                    <onup condition="Player.HasAudio + String.IsEmpty(Window(10000).Property(script.plex.theme_playing))">204</onup>
                    <onup>noop</onup>
                    <ondown condition="Control.IsVisible(302)">302</ondown>
                    <ondown condition="Control.IsVisible(300)">300</ondown>
                    <ondown>400</ondown>
                    <onleft>9000</onleft>
                    <onright>noop</onright>
                    <label> </label>
                    <texturenofocus>-</texturenofocus>
                    <texturefocus>-</texturefocus>
                </control>
                <control type="image">
                    <visible>Control.HasFocus(310)</visible>
                    <posx>-5</posx>
                    <posy>{{ vscale(20) }}</posy>
                    <width>823</width>
                    <height>{{ vscale(100) }}</height>
                    <colordiffuse>33FFFFFF</colordiffuse>
                    <texture border="10">script.plex/white-square-rounded.png</texture>
                </control>
            </control>

            <!-- Social links (PersonWindow.setSocialLinks()): the network's icon
                 (script.plex/social/<source>.png, the link icon for one without its own), white,
                 then the handle in the bio's grey, centred on the icon's height - a 40 line (the
                 icon 40, 80% bigger than its first 22 - on request, 2026-10-08), 25 above the
                 first, 15 above the others. -->
            {% for i, gap, line_height in ((0, 25, 65), (1, 15, 55), (2, 15, 55)) %}
            <control type="group">
                <posx>5</posx>
                <visible>!String.IsEmpty(Window.Property(person.social.{{ i }}.label))</visible>
                <width>813</width>
                <height>{{ vscale(line_height) }}</height>
                <control type="image">
                    <posx>0</posx>
                    <posy>{{ vscale(gap) }}</posy>
                    <width>40</width>
                    <height>{{ vscale(40) }}</height>
                    <texture>$INFO[Window.Property(person.social.{{ i }}.icon)]</texture>
                    <aspectratio>keep</aspectratio>
                </control>
                <control type="label">
                    <posx>52</posx>
                    <posy>{{ vscale(gap) }}</posy>
                    <width>761</width>
                    <height>{{ vscale(40) }}</height>
                    <font>font10</font>
                    <align>left</align>
                    <aligny>center</aligny>
                    <textcolor>FFD2CCCE</textcolor>
                    <shadowcolor>66000000</shadowcolor>
                    <label>$INFO[Window.Property(person.social.{{ i }}.label)]</label>
                </control>
            </control>
            {% endfor %}

            <!-- Filmography: every credit Discover has (person.py's openFilmography()), shown once
                 the person's plex.tv key is known (updateFilmographyButton()). Search's type
                 buttons' tile (script-plex-search.xml.tpl) - 22FFFFFF at rest, 55FFFFFF focused,
                 60 tall, font12 - sized to its caption, 25 above it. -->
            <control type="group" id="303">
                <posx>5</posx>
                <visible>!String.IsEmpty(Window.Property(filmography.available))</visible>
                <defaultcontrol>302</defaultcontrol>
                <width>813</width>
                <height>{{ vscale(85) }}</height>
                <control type="button" id="302">
                    <visible>!String.IsEmpty(Window.Property(filmography.available))</visible>
                    <posx>0</posx>
                    <posy>{{ vscale(25) }}</posy>
                    <width>auto</width>
                    <height>{{ vscale(60) }}</height>
                    <font>font12</font>
                    <align>center</align>
                    <aligny>center</aligny>
                    <textoffsetx>24</textoffsetx>
                    <textcolor>FFFFFFFF</textcolor>
                    <focusedcolor>FFFFFFFF</focusedcolor>
                    <texturenofocus colordiffuse="22FFFFFF" border="10">script.plex/white-square-rounded.png</texturenofocus>
                    <texturefocus colordiffuse="55FFFFFF" border="10">script.plex/white-square-rounded.png</texturefocus>
                    <onup condition="Control.IsVisible(310)">310</onup>
                    <onup condition="Player.HasAudio + String.IsEmpty(Window(10000).Property(script.plex.theme_playing))">204</onup>
                    <onup>noop</onup>
                    <ondown condition="Control.IsVisible(300)">300</ondown>
                    <ondown>400</ondown>
                    <onleft>9000</onleft>
                    <onright>noop</onright>
                    <label>$ADDON[script.plexmod 35160]</label>
                </control>
            </control>
        </control>
    </control>

    <!-- Filmography List -->
    <control type="group" id="500">
        <posx>0</posx>
        <!-- 730, not 460: below the text column at its longest (every line, three social links -
             it ends at 684), on request (2026-10-08). The posters' bottom edge may run off the
             screen. -->
        <posy>{{ vscale(730) }}</posy>
        <width>1920</width>
        <height>{{ vscale(535) }}</height>

        <!-- The row's title in a Recommended row's (script-plex-recommended.xml.tpl): font30_title,
             the light grey, its shadow, not capitalised (on request, 2026-10-08) - then the filter
             button after it. A grouplist lays the two end to end, the title's width being its
             text's in whatever language. Its left edge at x=120, with the posters'. An 80-tall box,
             the art 6 below it, as pre-play's rows have them (script-plex-pre_play.xml.tpl's SHARED
             HUB-ROW RECIPE; on request, 2026-10-08). -->
        <control type="grouplist">
            <posx>60</posx>
            <posy>0</posy>
            <width>1700</width>
            <height>{{ vscale(80) }}</height>
            <orientation>horizontal</orientation>
            <itemgap>30</itemgap>
            <usecontrolcoords>true</usecontrolcoords>
            <onleft>9000</onleft>
            <onright>noop</onright>
            <control type="label">
                <width>auto</width>
                <height>{{ vscale(80) }}</height>
                <font>font30_title</font>
                <align>left</align>
                <aligny>center</aligny>
                <textcolor>FFD2CCCE</textcolor>
                <shadowcolor>66000000</shadowcolor>
                <label>$ADDON[script.plexmod 32476]</label>
            </control>
            <control type="button" id="300">
                <!-- Only for a row of both films and shows (filmography.mixed, onFilmography() -
                     person.py): with one kind, All is all there is (on request, 2026-10-08). -->
                <visible>!String.IsEmpty(Window.Property(filmography.mixed))</visible>
                <posy>{{ vscale(15) }}</posy>
                <width>auto</width>
                <height>{{ vscale(50) }}</height>
                <font>font12</font>
                <align>center</align>
                <aligny>center</aligny>
                <focusedcolor>FF000000</focusedcolor>
                <textcolor>FFFFFFFF</textcolor>
                <textoffsetx>15</textoffsetx>
                <texturefocus colordiffuse="FFFFFFFF" border="8">script.plex/white-square-rounded-top-padded.png</texturefocus>
                <texturenofocus colordiffuse="40FFFFFF" border="8">script.plex/white-square-rounded-top-padded.png</texturenofocus>
                <onup condition="Control.IsVisible(302)">302</onup>
                <onup condition="Control.IsVisible(310)">310</onup>
                <onup>201</onup>
                <ondown condition="Integer.IsGreater(Container(400).NumItems,0)">400</ondown>
                <ondown>noop</ondown>
                <onleft>9000</onleft>
                <label>$INFO[Window.Property(filmography.filter)]</label>
            </control>
        </control>
        <!-- A Recommended poster row (includes/hub_itemlayout_poster.xml.tpl and its focused twin)
             with the movie grid's labels under each card (script-plex-posters.xml.tpl), on request
             2026-10-08: the 240x360 masked poster on its directional drop shadow, the inset
             progress pill, the watched tick or unwatched count, the orange ring and 104% zoom on
             focus; the title in font10 white, the year under it in font8 A0FFFFFF, and under that
             where it is: the server of the copy it opens, and for a title in more than one library
             or on more than one server how many others, as Search's line has it ("Animal + 1" -
             copies, set by createFilmographyListItem()). 540 tall, not Recommended's 515, for that
             third line. A fixedlist
             pinned at its first slot, as Recommended's rows are (focusposition 0, movement 5 - see
             script-plex-recommended.xml.tpl for the arithmetic): the row scrolls under the focused
             card. The art's left edge lands at x=120, with the photo and the row's heading. -->
        <control type="fixedlist" id="400">
            <posx>0</posx>
            <!-- 22, and the item's 61 below: the art's top at 86, 6 under the heading's box -->
            <posy>{{ vscale(22) }}</posy>
            <width>1920</width>
            <height>{{ vscale(540) }}</height>
            <onup condition="Control.IsVisible(300)">300</onup>
            <onup condition="Control.IsVisible(302)">302</onup>
            <onup condition="Control.IsVisible(310)">310</onup>
            <onup>noop</onup>
            <ondown>noop</ondown>
            <!-- The whole filmography is loaded at once (person.PersonFilmographyTask), with no
                 boundary markers to page in, so Left at the first item goes straight to the sidebar. -->
            <onleft>9000</onleft>
            <onright>noop</onright>
            <scrolltime>200</scrolltime>
            <orientation>horizontal</orientation>
            <focusposition>0</focusposition>
            <movement>5</movement>
            <preloaditems>4</preloaditems>
            {% for focused in (False, True) %}
            <{% if focused %}focusedlayout{% else %}itemlayout{% endif %} width="272" height="{{ vscale(540) }}">
                <control type="group">
                    <posx>57</posx>
                    <posy>{{ vscale(61) }}</posy>
                    <control type="group">
                        {% if focused %}
                        <!-- The grid's centre: the ring's, 3px out from the poster on every side. -->
                        <animation effect="zoom" start="100" end="104" time="100" center="123,{{ vscale(183) }}" reversible="false">Focus</animation>
                        <animation effect="zoom" start="104" end="100" time="100" center="123,{{ vscale(183) }}" reversible="false">UnFocus</animation>
                        {% endif %}
                        <!-- Ungated in the focused layout too, as on the grid: every card draws one. -->
                        <control type="image">
                            <posx>0</posx>
                            <posy>0</posy>
                            <width>264</width>
                            <height>{{ vscale(384) }}</height>
                            <texture border="24">script.plex/drop-shadow-directional.png</texture>
                        </control>
                        <control type="group">
                            <posx>3</posx>
                            <posy>3</posy>
                            <control type="image">
                                <posx>0</posx>
                                <posy>0</posy>
                                <width>240</width>
                                <height>{{ vscale(360) }}</height>
                                <texture background="true" diffuse="script.plex/masks/poster-mask.png" fallback="$INFO[ListItem.Property(thumb.fallback)]">$INFO[ListItem.Thumb]</texture>
                                <aspectratio scalediffuse="false">scale</aspectratio>
                            </control>
                            <control type="group">
                                <visible>!String.IsEmpty(ListItem.Property(progress))</visible>
                                <posx>8</posx>
                                <posy>{{ vscale(344) }}</posy>
                                <control type="image">
                                    <posx>0</posx>
                                    <posy>0</posy>
                                    <width>224</width>
                                    <height>{{ vscale(8) }}</height>
                                    <texture diffuse="script.plex/masks/progress-bar-mask.png">script.plex/white-square.png</texture>
                                    <colordiffuse>E60A0F1A</colordiffuse>
                                </control>
                                <control type="image">
                                    <posx>0</posx>
                                    <posy>0</posy>
                                    <width>224</width>
                                    <height>{{ vscale(8) }}</height>
                                    <texture diffuse="script.plex/masks/progress-bar-mask.png">$INFO[ListItem.Property(progress)]</texture>
                                    <colordiffuse>FFE5A00D</colordiffuse>
                                </control>
                            </control>
                            {% include "includes/watched_indicator.xml.tpl" with xoff=240 & uw_size=48 & wbg_w=34.4 & wbg_h=34.4 & with_count=True & scale="medium" %}
                            <control type="label">
                                <scroll>{% if focused %}Control.HasFocus(400){% else %}false{% endif %}</scroll>
                                <posx>0</posx>
                                <posy>{{ vscale(371) }}</posy>
                                <width>240</width>
                                <height>{{ vscale(72) }}</height>
                                <font>font10</font>
                                <align>center</align>
                                <textcolor>FFFFFFFF</textcolor>
                                <label>$INFO[ListItem.Label]</label>
                            </control>
                            <control type="label">
                                <scroll>false</scroll>
                                <posx>0</posx>
                                <posy>{{ vscale(401) }}</posy>
                                <width>240</width>
                                <height>{{ vscale(72) }}</height>
                                <font>font8</font>
                                <align>center</align>
                                <textcolor>A0FFFFFF</textcolor>
                                <label>$INFO[ListItem.Property(year)]</label>
                            </control>
                            <control type="label">
                                <scroll>false</scroll>
                                <posx>0</posx>
                                <posy>{{ vscale(425) }}</posy>
                                <width>240</width>
                                <height>{{ vscale(72) }}</height>
                                <font>font8</font>
                                <align>center</align>
                                <textcolor>A0FFFFFF</textcolor>
                                <label>$INFO[ListItem.Property(copies)]</label>
                            </control>
                        </control>
                        {% if focused %}
                        <control type="image">
                            <visible>Control.HasFocus(400)</visible>
                            <posx>0</posx>
                            <posy>0</posy>
                            <width>246</width>
                            <height>{{ vscale(366) }}</height>
                            <texture diffuse="script.plex/masks/ring-mask-poster.png">script.plex/white-square.png</texture>
                            <colordiffuse>FFE9A20D</colordiffuse>
                        </control>
                        {% endif %}
                    </control>
                </control>
            </{% if focused %}focusedlayout{% else %}itemlayout{% endif %}>
            {% endfor %}
        </control>

        <!-- Loading and nothing found, in the posters' place - the art is 86 to 446 in the row, its
             middle 266 - with the heading above them (on request, 2026-10-08; they were a screen's
             width wide at 650 and 700, from before the text column grew down to them). -->
        <!-- Loading: Search's spinner (script-plex-search.xml.tpl's STATUS), 39 and orange, turning
             as Estuary's do - always on, round its own middle - in the middle of the screen. 900,
             not 960: group 50's 60 cancelled. -->
        <control type="image">
            <visible>!String.IsEmpty(Window.Property(loading))</visible>
            <animation effect="rotate" start="0" end="-360" center="auto" time="1000" loop="true" reversible="false" condition="true">Conditional</animation>
            <posx>{{ 900 - 19.5 }}</posx>
            <posy>{{ vscale(246.5) }}</posy>
            <width>39</width>
            <height>{{ vscale(39) }}</height>
            <texture colordiffuse="FFE5A00D">script.plex/indicators/spinner.png</texture>
        </control>
        <!-- Nothing found: under the heading, at the posters' left edge, on the art's middle -->
        <control type="label">
            <visible>String.IsEmpty(Window.Property(loading)) + !Integer.IsGreater(Container(400).NumItems,0)</visible>
            <posx>60</posx>
            <posy>{{ vscale(236) }}</posy>
            <width>1700</width>
            <height>{{ vscale(60) }}</height>
            <font>font13</font>
            <align>left</align>
            <aligny>center</aligny>
            <textcolor>99FFFFFF</textcolor>
            <label>$ADDON[script.plexmod 32478]</label>
        </control>
    </control>

</control>
{% endblock content %}
