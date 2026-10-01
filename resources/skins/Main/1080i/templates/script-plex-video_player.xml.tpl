{% extends "default.xml.tpl" %}
{% block header %}
<control type="group">
    <visible>!String.IsEmpty(Window.Property(post.play))</visible>
    {{ super() }}
</control>
{% endblock header %}

{# Art and headings use the Recommended hub recipe (includes/hub_itemlayout_ar16x9.xml.tpl,
    hub_itemlayout_poster.xml.tpl and their focused layouts): art rounded by a diffuse mask, a
    directional drop-shadow plate with the art inset (3,3), the inset pill progress bar, a 104%
    focus zoom and a masked gold ring, and row headings in font30_title. Every tile uses that
    recipe's own art sizes (512x288, 240x360), since the masks scale with the control. Captions stay
    under the art, as there is no hero overlay here to carry the focused item's title. #}
{% block content %}
<control type="group">
    <visible>!String.IsEmpty(Window.Property(post.play))</visible>
    <control type="group" id="50">
        <animation effect="slide" end="0,{{ vscale(-300) }}" time="200" tween="quadratic" easing="out" condition="!String.IsEmpty(Window.Property(on.extras))">Conditional</animation>

        {# On Deck's height (460) + 140, less the 23 the rows moved up, so Related lands where it
           always has #}
        <animation type="Conditional" condition="Integer.IsGreater(Window.Property(hub.focus),0) + Control.IsVisible(500)" reversible="true">
            <effect type="slide" end="0,{{ vscale(-577) }}" time="200" tween="quadratic" easing="out"/>
        </animation>

        <posx>0</posx>
        {# puts the top of the "Just watched" heading's capitals at y=70: font30_title's cell is
           ~42.9px (InterUI's bbox at 30px), centred in the 87px label box, and its cap height sits
           ~11.4px below the cell top, so the capitals start ~33.5px into the box (47 + 33.5 - 10.5) #}
        <posy>{{ vscale(-10.5) }}</posy>
        <defaultcontrol>102</defaultcontrol>

        <control type="label">
            <scroll>false</scroll>
            <posx>62</posx>
            <posy>{{ vscale(47) }}</posy>
            <width>512</width>
            <height>{{ vscale(87) }}</height>
            <font>font30_title</font>
            <align>left</align>
            <aligny>center</aligny>
            <textcolor>FFD2CCCE</textcolor>
            <shadowcolor>66000000</shadowcolor>
            <label>$ADDON[script.plexmod 35094]</label>
        </control>

        <control type="group" id="100">
            <defaultcontrol>102</defaultcontrol>
            <control type="group">
                <posx>0</posx>
                <posy>0</posy>
                <width>1920</width>
                <height>{{ vscale(580) }}</height>
                <control type="group">
                    <posx>57</posx>
                    <posy>{{ vscale(128) }}</posy>
                    <control type="group">
                        <animation effect="zoom" start="100" end="104" time="100" center="259,{{ vscale(147) }}" reversible="true" condition="Control.HasFocus(101)">Conditional</animation>
                        <control type="image">
                            <posx>0</posx>
                            <posy>0</posy>
                            <width>536</width>
                            <height>{{ vscale(312) }}</height>
                            <texture border="24">script.plex/drop-shadow-directional.png</texture>
                        </control>
                        <control type="group">
                            <posx>3</posx>
                            <posy>3</posy>
                            <control type="image">
                                <posx>0</posx>
                                <posy>0</posy>
                                <width>512</width>
                                <height>{{ vscale(288) }}</height>
                                <texture background="true" diffuse="script.plex/masks/ar16x9-mask.png" fallback="$INFO[Window.Property(thumb.fallback)]">$INFO[Window.Property(prev.thumb)]</texture>
                                <aspectratio scalediffuse="false">scale</aspectratio>
                            </control>
                            {# 64px disc with the button rows' restart/play glyph at ~38.7px - the old 46px
                               replay icon's proportion to its 76px disc. tile-*.png are 2x masters of those
                               glyphs, filling their canvas, so this scales them down rather than up. #}
                            <control type="group">
                                <posx>224</posx>
                                <posy>{{ vscale(112) }}</posy>
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
                                    <texture>script.plex/indicators/tile-restart.png</texture>
                                </control>
                            </control>
                        </control>
                        {# captions as the Related posters': 11px under the art, zooming with it, and
                           the title only scrolling while focused (a label's <scroll> can't be
                           conditional, hence the pair) #}
                        <control type="group">
                            <posx>3</posx>
                            <posy>3</posy>
                            <control type="label">
                                <visible>!Control.HasFocus(101)</visible>
                                <scroll>false</scroll>
                                <posx>0</posx>
                                <posy>{{ vscale(299) }}</posy>
                                <width>512</width>
                                <height>{{ vscale(35) }}</height>
                                <font>font10</font>
                                <align>center</align>
                                <textcolor>FFFFFFFF</textcolor>
                                <label>$INFO[Window.Property(prev.title)]</label>
                            </control>
                            <control type="label">
                                <visible>Control.HasFocus(101)</visible>
                                <scroll>true</scroll>
                                <posx>0</posx>
                                <posy>{{ vscale(299) }}</posy>
                                <width>512</width>
                                <height>{{ vscale(35) }}</height>
                                <font>font10</font>
                                <align>center</align>
                                <textcolor>FFFFFFFF</textcolor>
                                <label>$INFO[Window.Property(prev.title)]</label>
                            </control>
                            <control type="label">
                                <scroll>false</scroll>
                                <posx>0</posx>
                                <posy>{{ vscale(329) }}</posy>
                                <width>512</width>
                                <height>{{ vscale(35) }}</height>
                                <font>font8</font>
                                <align>center</align>
                                <textcolor>A0FFFFFF</textcolor>
                                <label>$INFO[Window.Property(prev.subtitle)]</label>
                            </control>
                        </control>
                        <control type="image">
                            <visible>Control.HasFocus(101)</visible>
                            <posx>0</posx>
                            <posy>0.5</posy>
                            <width>518</width>
                            <height>{{ vscale(294) }}</height>
                            <texture diffuse="script.plex/masks/ring-mask-ar16x9.png">script.plex/white-square.png</texture>
                            <colordiffuse>FFE9A20D</colordiffuse>
                        </control>
                    </control>
                    <control type="button" id="101">
                        <posx>-2</posx>
                        <posy>{{ vscale(-2) }}</posy>
                        <width>522</width>
                        <height>{{ vscale(298) }}</height>
                        <onup>200</onup>
                        <ondown>400</ondown>
                        <onright>102</onright>
                        <texturefocus>-</texturefocus>
                        <texturenofocus>-</texturenofocus>
                    </control>
                </control>

                <control type="group">
                    <visible>!String.IsEmpty(Window.Property(has.next))</visible>
                    <control type="label">
                        <scroll>false</scroll>
                        <posx>606</posx>
                        <posy>{{ vscale(47) }}</posy>
                        <width>512</width>
                        <height>{{ vscale(87) }}</height>
                        <font>font30_title</font>
                        <align>left</align>
                        <aligny>center</aligny>
                        <textcolor>FFD2CCCE</textcolor>
                        <shadowcolor>66000000</shadowcolor>
                        {# countdown ("Playing next • in 12s") runs on after the heading while auto-play is pending #}
                        <label>$ADDON[script.plexmod 32439]$INFO[Window.Property(countdown), &#8226; ]</label>
                    </control>
                    <control type="group">
                        <posx>601</posx>
                        <posy>{{ vscale(128) }}</posy>
                        <control type="group">
                            <animation effect="zoom" start="100" end="104" time="100" center="259,{{ vscale(147) }}" reversible="true" condition="Control.HasFocus(102)">Conditional</animation>
                            <control type="image">
                                <posx>0</posx>
                                <posy>0</posy>
                                <width>536</width>
                                <height>{{ vscale(312) }}</height>
                                <texture border="24">script.plex/drop-shadow-directional.png</texture>
                            </control>
                            <control type="group">
                                <posx>3</posx>
                                <posy>3</posy>
                                <control type="image">
                                    <posx>0</posx>
                                    <posy>0</posy>
                                    <width>512</width>
                                    <height>{{ vscale(288) }}</height>
                                    <texture background="true" diffuse="script.plex/masks/ar16x9-mask.png" fallback="$INFO[Window.Property(thumb.fallback)]">$INFO[Window.Property(next.thumb)]</texture>
                                    <aspectratio scalediffuse="false">scale</aspectratio>
                                </control>
                                {# same as Just watched's restart overlay #}
                                <control type="group">
                                    <posx>224</posx>
                                    <posy>{{ vscale(112) }}</posy>
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
                                    </control>
                                </control>
                            </control>
                            {# same caption treatment as Just watched's #}
                            <control type="group">
                                <posx>3</posx>
                                <posy>3</posy>
                                <control type="label">
                                    <visible>!Control.HasFocus(102)</visible>
                                    <scroll>false</scroll>
                                    <posx>0</posx>
                                    <posy>{{ vscale(299) }}</posy>
                                    <width>512</width>
                                    <height>{{ vscale(35) }}</height>
                                    <font>font10</font>
                                    <align>center</align>
                                    <textcolor>FFFFFFFF</textcolor>
                                    <label>$INFO[Window.Property(next.title)]</label>
                                </control>
                                <control type="label">
                                    <visible>Control.HasFocus(102)</visible>
                                    <scroll>true</scroll>
                                    <posx>0</posx>
                                    <posy>{{ vscale(299) }}</posy>
                                    <width>512</width>
                                    <height>{{ vscale(35) }}</height>
                                    <font>font10</font>
                                    <align>center</align>
                                    <textcolor>FFFFFFFF</textcolor>
                                    <label>$INFO[Window.Property(next.title)]</label>
                                </control>
                                <control type="label">
                                    <scroll>false</scroll>
                                    <posx>0</posx>
                                    <posy>{{ vscale(329) }}</posy>
                                    <width>512</width>
                                    <height>{{ vscale(35) }}</height>
                                    <font>font8</font>
                                    <align>center</align>
                                    <textcolor>A0FFFFFF</textcolor>
                                    <label>$INFO[Window.Property(next.subtitle)]</label>
                                </control>
                            </control>
                            <control type="image">
                                <visible>Control.HasFocus(102)</visible>
                                <posx>0</posx>
                                <posy>0.5</posy>
                                <width>518</width>
                                <height>{{ vscale(294) }}</height>
                                <texture diffuse="script.plex/masks/ring-mask-ar16x9.png">script.plex/white-square.png</texture>
                                <colordiffuse>FFE9A20D</colordiffuse>
                            </control>
                        </control>
                        <control type="button" id="102">
                            <posx>-2</posx>
                            <posy>{{ vscale(-2) }}</posy>
                            <width>522</width>
                            <height>{{ vscale(298) }}</height>
                            <onup>200</onup>
                            <ondown>400</ondown>
                            <onleft>101</onleft>
                            <texturefocus>-</texturefocus>
                            <texturenofocus>-</texturenofocus>
                        </control>
                    </control>
                </control>
            </control>

            <control type="group">
                <visible>!String.IsEmpty(Window.Property(has.next))</visible>
                {# heading style; capitals start at the Playing next art's unfocused top edge (131): the
                   box is font30_title's own cell height (~42.9), so centring barely moves the text, and
                   the capitals sit ~11.4 below the cell top #}
                <control type="label">
                    <scroll>true</scroll>
                    <posx>1177</posx>
                    <posy>{{ vscale(119.5) }}</posy>
                    <width>683</width>
                    <height>{{ vscale(43) }}</height>
                    <font>font30_title</font>
                    <align>left</align>
                    <aligny>center</aligny>
                    <textcolor>FFD2CCCE</textcolor>
                    <shadowcolor>66000000</shadowcolor>
                    <label>$INFO[Window.Property(info.title)]</label>
                </control>
                {# 32px from each line's baseline to the next line's capitals (font12's 35.75px cell
                   overhangs this 32px box by ~1.9px; the summary's text is top-aligned) #}
                <control type="label">
                    <scroll>false</scroll>
                    <posx>1177</posx>
                    <posy>{{ vscale(177.2) }}</posy>
                    <width>683</width>
                    <height>{{ vscale(32) }}</height>
                    <font>font12</font>
                    <align>left</align>
                    <aligny>center</aligny>
                    <textcolor>A0FFFFFF</textcolor>
                    <label>$INFO[Window.Property(info.date)]$INFO[Window.Property(info.duration), &#8226; ]</label>
                </control>
                {# bottom edge at the Playing next art's unfocused bottom (131 + 288 = 419) #}
                <control type="textbox">
                    <autoscroll delay="2000" time="2000" repeat="10000">true</autoscroll>
                    <posx>1177</posx>
                    <posy>{{ vscale(225.5) }}</posy>
                    <width>683</width>
                    <height>{{ vscale(193.5) }}</height>
                    <font>font12</font>
                    <align>left</align>
                    <textcolor>FFFFFFFF</textcolor>
                    <label>$INFO[Window.Property(info.summary)]</label>
                </control>
            </control>
        </control>

        {# Row spacing matches Recommended's (ROW_GAP, library.py): ~60.5px from the lowest content
           above - art there, captions' baseline here - to the next heading's capitals. 507 does
           that below the top band's captions; On Deck's 460 height does it between rows. #}
        <control type="grouplist" id="60">
            <posx>0</posx>
            <posy>{{ vscale(507) }}</posy>
            <width>1920</width>
            <height>{{ vscale(1610) }}</height>

            <onup>300</onup>
            <itemgap>0</itemgap>

            <control type="group" id="500">
                <visible>Integer.IsGreater(Container(400).NumItems,0) + String.IsEmpty(Window.Property(drawing))</visible>
                <height>{{ vscale(460) }}</height>
                <width>1920</width>
                <control type="label">
                    <posx>62</posx>
                    <posy>0</posy>
                    <width>1000</width>
                    <height>{{ vscale(87) }}</height>
                    <font>font30_title</font>
                    <align>left</align>
                    <aligny>center</aligny>
                    <textcolor>FFD2CCCE</textcolor>
                    <shadowcolor>66000000</shadowcolor>
                    <label>$ADDON[script.plexmod 32440]</label>
                </control>
                <control type="list" id="400">
                    <posx>0</posx>
                    <posy>{{ vscale(29) }}</posy>
                    <width>1920</width>
                    <height>{{ vscale(440) }}</height>
                    <onup>100</onup>
                    <ondown>401</ondown>
                    <onleft>noop</onleft>
                    <onright>noop</onright>
                    <scrolltime>200</scrolltime>
                    <orientation>horizontal</orientation>
                    <preloaditems>4</preloaditems>
                    <!-- ITEM LAYOUT ########################################## -->
                    <itemlayout width="544">
                        <control type="group">
                            <posx>57</posx>
                            <posy>{{ vscale(52) }}</posy>
                            <control type="image">
                                <posx>0</posx>
                                <posy>0</posy>
                                <width>536</width>
                                <height>{{ vscale(312) }}</height>
                                <texture border="24">script.plex/drop-shadow-directional.png</texture>
                            </control>
                            <control type="group">
                                <posx>3</posx>
                                <posy>3</posy>
                                <control type="image">
                                    <posx>0</posx>
                                    <posy>0</posy>
                                    <width>512</width>
                                    <height>{{ vscale(288) }}</height>
                                    <texture background="true" diffuse="script.plex/masks/ar16x9-mask.png" fallback="$INFO[ListItem.Property(thumb.fallback)]">$INFO[ListItem.Thumb]</texture>
                                    <aspectratio scalediffuse="false">scale</aspectratio>
                                </control>
                                <control type="group">
                                    <visible>!String.IsEmpty(ListItem.Property(progress))</visible>
                                    <posx>8</posx>
                                    <posy>{{ vscale(272) }}</posy>
                                    <control type="image">
                                        <posx>0</posx>
                                        <posy>0</posy>
                                        <width>496</width>
                                        <height>{{ vscale(8) }}</height>
                                        <texture diffuse="script.plex/masks/progress-bar-mask.png">script.plex/white-square.png</texture>
                                        <colordiffuse>E60A0F1A</colordiffuse>
                                    </control>
                                    <control type="image">
                                        <posx>0</posx>
                                        <posy>0</posy>
                                        <width>496</width>
                                        <height>{{ vscale(8) }}</height>
                                        <texture diffuse="script.plex/masks/progress-bar-mask.png">$INFO[ListItem.Property(progress)]</texture>
                                        <colordiffuse>FFE5A00D</colordiffuse>
                                    </control>
                                </control>
                                {% include "includes/watched_indicator.xml.tpl" with xoff=512 & uw_size=35 & wbg_w=40 %}
                                <control type="group">
                                    <visible>!String.IsEmpty(ListItem.Property(is.boundary))</visible>
                                    <control type="image">
                                        <posx>0</posx>
                                        <posy>0</posy>
                                        <width>512</width>
                                        <height>{{ vscale(288) }}</height>
                                        <texture diffuse="script.plex/masks/ar16x9-mask.png">script.plex/white-square.png</texture>
                                        <colordiffuse>FF404040</colordiffuse>
                                    </control>
                                    <control type="image">
                                        <visible>String.IsEmpty(ListItem.Property(is.updating)) + !String.IsEmpty(ListItem.Property(right.boundary))</visible>
                                        <posx>225.5</posx>
                                        <posy>{{ vscale(94) }}</posy>
                                        <width>61</width>
                                        <height>{{ vscale(100) }}</height>
                                        <texture colordiffuse="40000000">script.plex/indicators/chevron-white.png</texture>
                                    </control>
                                    <control type="image">
                                        <visible>String.IsEmpty(ListItem.Property(is.updating)) + !String.IsEmpty(ListItem.Property(left.boundary))</visible>
                                        <posx>225.5</posx>
                                        <posy>{{ vscale(94) }}</posy>
                                        <width>61</width>
                                        <height>{{ vscale(100) }}</height>
                                        <texture colordiffuse="40000000">script.plex/indicators/chevron-white-l.png</texture>
                                    </control>
                                    <control type="image">
                                        <visible>!String.IsEmpty(ListItem.Property(is.updating))</visible>
                                        <posx>192</posx>
                                        <posy>{{ vscale(80) }}</posy>
                                        <width>128</width>
                                        <height>{{ vscale(128) }}</height>
                                        <texture>script.plex/home/busy.gif</texture>
                                    </control>
                                </control>
                                <control type="label">
                                    <scroll>false</scroll>
                                    <posx>0</posx>
                                    <posy>{{ vscale(299) }}</posy>
                                    <width>512</width>
                                    <height>{{ vscale(35) }}</height>
                                    <font>font10</font>
                                    <align>center</align>
                                    <textcolor>FFFFFFFF</textcolor>
                                    <label>$INFO[ListItem.Label]</label>
                                </control>
                                <control type="label">
                                    <scroll>false</scroll>
                                    <posx>0</posx>
                                    <posy>{{ vscale(329) }}</posy>
                                    <width>512</width>
                                    <height>{{ vscale(35) }}</height>
                                    <font>font8</font>
                                    <align>center</align>
                                    <textcolor>A0FFFFFF</textcolor>
                                    <label>$INFO[ListItem.Label2]</label>
                                </control>
                            </control>
                        </control>
                    </itemlayout>

                    <!-- FOCUSED LAYOUT ####################################### -->
                    <focusedlayout width="544">
                        <control type="group">
                            <posx>57</posx>
                            <posy>{{ vscale(52) }}</posy>
                            <control type="group">
                                <animation effect="zoom" start="100" end="104" time="100" center="259,{{ vscale(147) }}" reversible="false">Focus</animation>
                                <animation effect="zoom" start="104" end="100" time="100" center="259,{{ vscale(147) }}" reversible="false">UnFocus</animation>
                                <control type="image">
                                    <posx>0</posx>
                                    <posy>0</posy>
                                    <width>536</width>
                                    <height>{{ vscale(312) }}</height>
                                    <texture border="24">script.plex/drop-shadow-directional.png</texture>
                                </control>
                                <control type="group">
                                    <posx>3</posx>
                                    <posy>3</posy>
                                    <control type="image">
                                        <posx>0</posx>
                                        <posy>0</posy>
                                        <width>512</width>
                                        <height>{{ vscale(288) }}</height>
                                        <texture background="true" diffuse="script.plex/masks/ar16x9-mask.png" fallback="$INFO[ListItem.Property(thumb.fallback)]">$INFO[ListItem.Thumb]</texture>
                                        <aspectratio scalediffuse="false">scale</aspectratio>
                                    </control>
                                    <control type="group">
                                        <visible>!String.IsEmpty(ListItem.Property(progress))</visible>
                                        <posx>8</posx>
                                        <posy>{{ vscale(272) }}</posy>
                                        <control type="image">
                                            <posx>0</posx>
                                            <posy>0</posy>
                                            <width>496</width>
                                            <height>{{ vscale(8) }}</height>
                                            <texture diffuse="script.plex/masks/progress-bar-mask.png">script.plex/white-square.png</texture>
                                            <colordiffuse>E60A0F1A</colordiffuse>
                                        </control>
                                        <control type="image">
                                            <posx>0</posx>
                                            <posy>0</posy>
                                            <width>496</width>
                                            <height>{{ vscale(8) }}</height>
                                            <texture diffuse="script.plex/masks/progress-bar-mask.png">$INFO[ListItem.Property(progress)]</texture>
                                            <colordiffuse>FFE5A00D</colordiffuse>
                                        </control>
                                    </control>
                                    {% include "includes/watched_indicator.xml.tpl" with xoff=512 & uw_size=35 & wbg_w=40 %}
                                    <control type="group">
                                        <visible>!String.IsEmpty(ListItem.Property(is.boundary))</visible>
                                        <control type="image">
                                            <posx>0</posx>
                                            <posy>0</posy>
                                            <width>512</width>
                                            <height>{{ vscale(288) }}</height>
                                            <texture diffuse="script.plex/masks/ar16x9-mask.png">script.plex/white-square.png</texture>
                                            <colordiffuse>FF404040</colordiffuse>
                                        </control>
                                        <control type="image">
                                            <visible>String.IsEmpty(ListItem.Property(is.updating)) + !String.IsEmpty(ListItem.Property(right.boundary))</visible>
                                            <posx>225.5</posx>
                                            <posy>{{ vscale(94) }}</posy>
                                            <width>61</width>
                                            <height>{{ vscale(100) }}</height>
                                            <texture colordiffuse="40000000">script.plex/indicators/chevron-white.png</texture>
                                        </control>
                                        <control type="image">
                                            <visible>String.IsEmpty(ListItem.Property(is.updating)) + !String.IsEmpty(ListItem.Property(left.boundary))</visible>
                                            <posx>225.5</posx>
                                            <posy>{{ vscale(94) }}</posy>
                                            <width>61</width>
                                            <height>{{ vscale(100) }}</height>
                                            <texture colordiffuse="40000000">script.plex/indicators/chevron-white-l.png</texture>
                                        </control>
                                        <control type="image">
                                            <visible>!String.IsEmpty(ListItem.Property(is.updating))</visible>
                                            <posx>192</posx>
                                            <posy>{{ vscale(80) }}</posy>
                                            <width>128</width>
                                            <height>{{ vscale(128) }}</height>
                                            <texture>script.plex/home/busy.gif</texture>
                                        </control>
                                    </control>
                                    <control type="label">
                                        <scroll>true</scroll>
                                        <posx>0</posx>
                                        <posy>{{ vscale(299) }}</posy>
                                        <width>512</width>
                                        <height>{{ vscale(35) }}</height>
                                        <font>font10</font>
                                        <align>center</align>
                                        <textcolor>FFFFFFFF</textcolor>
                                        <label>$INFO[ListItem.Label]</label>
                                    </control>
                                    <control type="label">
                                        <scroll>false</scroll>
                                        <posx>0</posx>
                                        <posy>{{ vscale(329) }}</posy>
                                        <width>512</width>
                                        <height>{{ vscale(35) }}</height>
                                        <font>font8</font>
                                        <align>center</align>
                                        <textcolor>A0FFFFFF</textcolor>
                                        <label>$INFO[ListItem.Label2]</label>
                                    </control>
                                </control>
                                <control type="image">
                                    <visible>Control.HasFocus(400)</visible>
                                    <posx>0</posx>
                                    <posy>0.5</posy>
                                    <width>518</width>
                                    <height>{{ vscale(294) }}</height>
                                    <texture diffuse="script.plex/masks/ring-mask-ar16x9.png">script.plex/white-square.png</texture>
                                    <colordiffuse>FFE9A20D</colordiffuse>
                                </control>
                            </control>
                        </control>
                    </focusedlayout>
                </control>
            </control>

            <control type="group" id="501">
                <visible>Integer.IsGreater(Container(401).NumItems,0) + String.IsEmpty(Window.Property(drawing))</visible>
                <defaultcontrol>401</defaultcontrol>
                <width>1920</width>
                <height>{{ vscale(530) }}</height>
                <control type="label">
                    <posx>62</posx>
                    <posy>0</posy>
                    <width>1000</width>
                    <height>{{ vscale(87) }}</height>
                    <font>font30_title</font>
                    <align>left</align>
                    <aligny>center</aligny>
                    <textcolor>FFD2CCCE</textcolor>
                    <shadowcolor>66000000</shadowcolor>
                    <label>$INFO[Window.Property(related.header)]</label>
                </control>
                <control type="list" id="401">
                    <posx>0</posx>
                    <posy>{{ vscale(29) }}</posy>
                    <width>1920</width>
                    <height>{{ vscale(500) }}</height>
                    <onup>400</onup>
                    <onleft>noop</onleft>
                    <onright>noop</onright>
                    <scrolltime>200</scrolltime>
                    <orientation>horizontal</orientation>
                    <preloaditems>4</preloaditems>
                    <!-- ITEM LAYOUT ########################################## -->
                    <itemlayout width="272">
                        <control type="group">
                            <posx>57</posx>
                            <posy>{{ vscale(52) }}</posy>
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
                                <control type="group">
                                    <visible>!String.IsEmpty(ListItem.Property(is.boundary))</visible>
                                    <control type="image">
                                        <posx>0</posx>
                                        <posy>0</posy>
                                        <width>240</width>
                                        <height>{{ vscale(360) }}</height>
                                        <texture diffuse="script.plex/masks/poster-mask.png">script.plex/white-square.png</texture>
                                        <colordiffuse>FF404040</colordiffuse>
                                    </control>
                                    <control type="image">
                                        <visible>String.IsEmpty(ListItem.Property(is.updating)) + !String.IsEmpty(ListItem.Property(right.boundary))</visible>
                                        <posx>89.5</posx>
                                        <posy>{{ vscale(130) }}</posy>
                                        <width>61</width>
                                        <height>{{ vscale(100) }}</height>
                                        <texture colordiffuse="40000000">script.plex/indicators/chevron-white.png</texture>
                                    </control>
                                    <control type="image">
                                        <visible>String.IsEmpty(ListItem.Property(is.updating)) + !String.IsEmpty(ListItem.Property(left.boundary))</visible>
                                        <posx>89.5</posx>
                                        <posy>{{ vscale(130) }}</posy>
                                        <width>61</width>
                                        <height>{{ vscale(100) }}</height>
                                        <texture colordiffuse="40000000">script.plex/indicators/chevron-white-l.png</texture>
                                    </control>
                                    <control type="image">
                                        <visible>!String.IsEmpty(ListItem.Property(is.updating))</visible>
                                        <posx>56</posx>
                                        <posy>{{ vscale(116) }}</posy>
                                        <width>128</width>
                                        <height>{{ vscale(128) }}</height>
                                        <texture>script.plex/home/busy.gif</texture>
                                    </control>
                                </control>
                                <control type="label">
                                    <scroll>false</scroll>
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
                                    <visible>!String.IsEmpty(ListItem.Property(subtitle))</visible>
                                    <scroll>false</scroll>
                                    <posx>0</posx>
                                    <posy>{{ vscale(401) }}</posy>
                                    <width>240</width>
                                    <height>{{ vscale(72) }}</height>
                                    <font>font8</font>
                                    <align>center</align>
                                    <textcolor>A0FFFFFF</textcolor>
                                    <label>$INFO[ListItem.Property(subtitle)]</label>
                                </control>
                            </control>
                        </control>
                    </itemlayout>

                    <!-- FOCUSED LAYOUT ####################################### -->
                    <focusedlayout width="272">
                        <control type="group">
                            <posx>57</posx>
                            <posy>{{ vscale(52) }}</posy>
                            <control type="group">
                                <animation effect="zoom" start="100" end="104" time="100" center="123,{{ vscale(183) }}" reversible="false">Focus</animation>
                                <animation effect="zoom" start="104" end="100" time="100" center="123,{{ vscale(183) }}" reversible="false">UnFocus</animation>
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
                                    <control type="group">
                                        <visible>!String.IsEmpty(ListItem.Property(is.boundary))</visible>
                                        <control type="image">
                                            <posx>0</posx>
                                            <posy>0</posy>
                                            <width>240</width>
                                            <height>{{ vscale(360) }}</height>
                                            <texture diffuse="script.plex/masks/poster-mask.png">script.plex/white-square.png</texture>
                                            <colordiffuse>FF404040</colordiffuse>
                                        </control>
                                        <control type="image">
                                            <visible>String.IsEmpty(ListItem.Property(is.updating)) + !String.IsEmpty(ListItem.Property(right.boundary))</visible>
                                            <posx>89.5</posx>
                                            <posy>{{ vscale(130) }}</posy>
                                            <width>61</width>
                                            <height>{{ vscale(100) }}</height>
                                            <texture colordiffuse="40000000">script.plex/indicators/chevron-white.png</texture>
                                        </control>
                                        <control type="image">
                                            <visible>String.IsEmpty(ListItem.Property(is.updating)) + !String.IsEmpty(ListItem.Property(left.boundary))</visible>
                                            <posx>89.5</posx>
                                            <posy>{{ vscale(130) }}</posy>
                                            <width>61</width>
                                            <height>{{ vscale(100) }}</height>
                                            <texture colordiffuse="40000000">script.plex/indicators/chevron-white-l.png</texture>
                                        </control>
                                        <control type="image">
                                            <visible>!String.IsEmpty(ListItem.Property(is.updating))</visible>
                                            <posx>56</posx>
                                            <posy>{{ vscale(116) }}</posy>
                                            <width>128</width>
                                            <height>{{ vscale(128) }}</height>
                                            <texture>script.plex/home/busy.gif</texture>
                                        </control>
                                    </control>
                                    <control type="label">
                                        <scroll>true</scroll>
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
                                        <visible>!String.IsEmpty(ListItem.Property(subtitle))</visible>
                                        <scroll>false</scroll>
                                        <posx>0</posx>
                                        <posy>{{ vscale(401) }}</posy>
                                        <width>240</width>
                                        <height>{{ vscale(72) }}</height>
                                        <font>font8</font>
                                        <align>center</align>
                                        <textcolor>A0FFFFFF</textcolor>
                                        <label>$INFO[ListItem.Property(subtitle)]</label>
                                    </control>
                                </control>
                                <control type="image">
                                    <visible>Control.HasFocus(401)</visible>
                                    <posx>0</posx>
                                    <posy>0</posy>
                                    <width>246</width>
                                    <height>{{ vscale(366) }}</height>
                                    <texture diffuse="script.plex/masks/ring-mask-poster.png">script.plex/white-square.png</texture>
                                    <colordiffuse>FFE9A20D</colordiffuse>
                                </control>
                            </control>
                        </control>
                    </focusedlayout>
                </control>
            </control>
        </control>
    </control>
</control>
{% endblock content %}
