{% extends "library_posters.xml.tpl" %}
{% block content %}
<control type="group" id="50">
    <animation effect="slide" time="200" end="0,{{ vscale(-115, negpos=True) }}" tween="quadratic" easing="out" condition="Integer.IsGreater(Container(101).ListItem.Property(index),5) + String.IsEmpty(Window.Property(content.filling))">Conditional</animation>
    <animation effect="slide" end="220,0" time="200" tween="sine" easing="inout" condition="ControlGroup(9000).HasFocus(0)">Conditional</animation>
    <posx>60</posx>
    <posy>{{ vscale(135) }}</posy>
    <defaultcontrol>101</defaultcontrol>

    <control type="group" id="100">
        <visible>Integer.IsGreater(Container(101).NumItems,0) + String.IsEmpty(Window.Property(drawing))</visible>
        <defaultcontrol>101</defaultcontrol>
        <posx>0</posx>
        <posy>{{ vscale(-35) }}</posy>
        <width>1920</width>
        <height>1080</height>
        <control type="panel" id="101">
            <hitrect x="0" y="95" w="1780" h="1185" />
            <posx>0</posx>
            <posy>0</posy>
            <width>1800</width>
            <height>1190</height>
            <onup condition="Integer.IsLess(Container(101).ListItem.Property(index),3)">600</onup>
            <onup condition="Integer.IsLess(Container(101).ListItem.Property(index),6) + Integer.IsGreaterOrEqual(Container(101).ListItem.Property(index),3)">300</onup>
            <onleft>9000</onleft>
            <onright>151</onright>
            <scrolltime>200</scrolltime>
            <orientation>vertical</orientation>
            <preloaditems>2</preloaditems>
            <!-- ITEM LAYOUT ########################################## -->
            <itemlayout width="283" height="{{ vscale(408) }}">
                <control type="group">
                    <posx>55</posx>
                    <posy>{{ vscale(137) }}</posy>
                    <control type="image">
                        <posx>0</posx>
                        <posy>0</posy>
                        <width>287</width>
                        <height>{{ vscale(412) }}</height>
                        <texture border="24">script.plex/drop-shadow-directional.png</texture>
                    </control>
                    <control type="group">
                        <posx>3</posx>
                        <posy>3</posy>
                        <control type="image">
                            <posx>0</posx>
                            <posy>0</posy>
                            <width>263</width>
                            <height>{{ vscale(388) }}</height>
                            <texture background="true" diffuse="script.plex/masks/poster-mask.png" fallback="$INFO[ListItem.Property(thumb.fallback)]">$INFO[ListItem.Thumb]</texture>
                            <aspectratio scalediffuse="false">scale</aspectratio>
                        </control>
                        <control type="group">
                            <visible>!String.IsEmpty(ListItem.Property(progress))</visible>
                            <posx>0</posx>
                            <posy>{{ vscale(378) }}</posy>
                            <control type="image">
                                <posx>0</posx>
                                <posy>0</posy>
                                <width>263</width>
                                <height>{{ vscale(10) }}</height>
                                <texture>script.plex/white-square.png</texture>
                                <colordiffuse>C0000000</colordiffuse>
                            </control>
                            <control type="image">
                                <posx>0</posx>
                                <posy>1</posy>
                                <width>263</width>
                                <height>{{ vscale(8) }}</height>
                                <texture>$INFO[ListItem.Property(progress)]</texture>
                                <colordiffuse>FFCC7B19</colordiffuse>
                            </control>
                        </control>
                        {% include "includes/watched_indicator.xml.tpl" with xoff=263 & uw_size=45 & wbg_w=37.1 & wbg_h=37.1 & with_count=True & scale="medium" %}
                    </control>
                </control>
            </itemlayout>

            <!-- FOCUSED LAYOUT ####################################### -->
            <focusedlayout width="283" height="{{ vscale(408) }}">
                <control type="group">
                    <posx>55</posx>
                    <posy>{{ vscale(137) }}</posy>
                    <control type="group">
                        <animation effect="zoom" start="100" end="105" time="100" center="127,{{ vscale(185) }}" reversible="false">Focus</animation>
                        <animation effect="zoom" start="105" end="100" time="100" center="127,{{ vscale(185) }}" reversible="false">UnFocus</animation>
                        <posx>0</posx>
                        <posy>0</posy>
                        <control type="image">
                            <visible>Control.HasFocus(101)</visible>
                            <posx>0</posx>
                            <posy>0</posy>
                            <width>287</width>
                            <height>{{ vscale(412) }}</height>
                            <texture border="24">script.plex/drop-shadow-directional.png</texture>
                        </control>
                        <!-- Selection border (cell-sized, original style) -->
                        <control type="image">
                            <visible>Control.HasFocus(101)</visible>
                            <posx>0</posx>
                            <posy>0</posy>
                            <width>269</width>
                            <height>{{ vscale(394) }}</height>
                            <texture diffuse="script.plex/masks/ring-mask-poster.png">script.plex/white-square.png</texture>
                            <colordiffuse>FFE9A20D</colordiffuse>
                        </control>
                        <control type="group">
                            <posx>3</posx>
                            <posy>3</posy>
                            <control type="image">
                                <posx>0</posx>
                                <posy>0</posy>
                                <width>263</width>
                                <height>{{ vscale(388) }}</height>
                                <texture background="true" diffuse="script.plex/masks/poster-mask.png" fallback="$INFO[ListItem.Property(thumb.fallback)]">$INFO[ListItem.Thumb]</texture>
                                <aspectratio scalediffuse="false">scale</aspectratio>
                            </control>
                            <control type="group">
                                <visible>!String.IsEmpty(ListItem.Property(progress))</visible>
                                <posx>0</posx>
                                <posy>{{ vscale(378) }}</posy>
                                <control type="image">
                                    <posx>0</posx>
                                    <posy>0</posy>
                                    <width>263</width>
                                    <height>{{ vscale(10) }}</height>
                                    <texture>script.plex/white-square.png</texture>
                                    <colordiffuse>C0000000</colordiffuse>
                                </control>
                                <control type="image">
                                    <posx>0</posx>
                                    <posy>1</posy>
                                    <width>263</width>
                                    <height>{{ vscale(8) }}</height>
                                    <texture>$INFO[ListItem.Property(progress)]</texture>
                                    <colordiffuse>FFCC7B19</colordiffuse>
                                </control>
                            </control>
                            {% include "includes/watched_indicator.xml.tpl" with xoff=263 & uw_size=45 & wbg_w=37.1 & wbg_h=37.1 & with_count=True & scale="medium" %}
                        </control>
                    </control>
                </control>
            </focusedlayout>
        </control>
    </control>

</control>

{% block buttons %}
<!-- Swapped with the filter row (600): this row now sits where 600 used to (right, next
     to the scrubber) so it's right-anchored like 600 was, and no longer needs the
     sidebar-expand slide 600 needed on the left. -->
<control type="grouplist" id="300">
    <animation effect="fade" start="0" end="100" time="200" reversible="true">VisibleChange</animation>
    <visible>!Integer.IsGreater(Container(101).ListItem.Property(index),5) + String.IsEmpty(Window.Property(no.content)) + String.IsEmpty(Window.Property(no.content.filtered)) + !String.IsEmpty(Window.Property(initialized))</visible>
    <defaultcontrol>301</defaultcontrol>
    <right>120</right>
    <posy>{{ vscale(110) }}</posy>
    <width>1000</width>
    <height>{{ vscale(145) }}</height>
    <align>right</align>
    <onup condition="Player.HasAudio + String.IsEmpty(Window(10000).Property(script.plex.theme_playing))">204</onup>
    <ondown>101</ondown>
    <onleft>210</onleft>
    <onright>151</onright>
    <itemgap>-20</itemgap>
    <orientation>horizontal</orientation>
    <scrolltime tween="quadratic" easing="out">200</scrolltime>
    <usecontrolcoords>true</usecontrolcoords>

    {% with attr = {"width": 126, "height": 100} & template = "includes/themed_button.xml.tpl" & hitrect = {"x": 20, "y": 20, "w": 86, "h": 60} %}
        {% include template with name="play" & id=301 & visible="String.IsEmpty(Window.Property(disable_playback)) + [!String.IsEqual(Window(10000).Property(script.plex.item.type),collection) | String.IsEqual(Window.Property(media),collection)]" %}
        {% include template with name="shuffle" & id=302 & visible="String.IsEmpty(Window.Property(disable_playback)) + [!String.IsEqual(Window(10000).Property(script.plex.item.type),collection) | String.IsEqual(Window.Property(media),collection)]" %}
        {% include template with name="more" & id=303 & visible="String.IsEmpty(Window.Property(disable_playback)) + [String.IsEmpty(Window.Property(no.options)) | Player.HasAudio]" %}
        {% include template with name="chapters" & id=304 %}
    {% endwith %}

</control>
{% endblock %}

<control type="group" id="150">
    <visible>!String.IsEmpty(Window(10000).Property(script.plex.sort.alpha)) + Integer.IsGreater(Container(101).NumItems,0) + String.IsEmpty(Window.Property(drawing))</visible>
    <defaultcontrol>151</defaultcontrol>
    <!-- posx/posy match where the scrollbar (id 152, below) rests when it's showing instead;
         the slide animation mirrors the zoom the scrollbar does when the header hides on
         scroll, growing into the space the header vacates instead of resizing.
         End position centers the scrubber's full 27-key extent (26 letters + '#', 34px each =
         918) in the 1080-tall screen: (1080-918)/2 = 81 top margin, a 150-81=69px move up from
         the resting posy. -->
    <animation effect="slide" end="0,{{ vscale(-69, negpos=True) }}" time="200" tween="quadratic" easing="out" condition="Integer.IsGreater(Container(101).ListItem.Property(index),5) + String.IsEmpty(Window.Property(content.filling))">Conditional</animation>
    <posx>1875</posx>
    <posy>{{ vscale(150) }}</posy>
    <width>20</width>
    <height>920</height>
    <control type="list" id="151">
        <posx>0</posx>
        <posy>0</posy>
        <width>34</width>
        <height>1050</height>
        <onleft condition="Integer.IsGreater(Container(101).ListItem.Property(index),5) | !Integer.IsEqual(Container(151).ListItem.Property(index),0)">100</onleft>
        <onleft condition="!Integer.IsGreater(Container(101).ListItem.Property(index),5) + Integer.IsEqual(Container(151).ListItem.Property(index),0)">300</onleft>
        <scrolltime>200</scrolltime>
        <orientation>vertical</orientation>
        {% include "includes/key_scrubber_items.xml.tpl" %}
    </control>
</control>

<!-- Shown instead of the scrubber above for sorts that don't produce alphabetical
     ordering (script.plex.sort.alpha unset) - a plain proportional position indicator. -->
<control type="scrollbar" id="152">
    <visible>String.IsEmpty(Window(10000).Property(script.plex.sort.alpha)) + Integer.IsGreater(Container(101).NumItems,0) + String.IsEmpty(Window.Property(drawing))</visible>
    <hitrect x="1845" y="150" w="100" h="910" />
    <left>1885</left>
    <top>{{ vscale(150) }}</top>
    <width>12</width>
    <height>910</height>
    <animation effect="zoom" time="200" start="1885,{{ vscale(150) }},12,910" end="1885,16,12,1055" tween="quadratic" easing="out" condition="Integer.IsGreater(Container(101).ListItem.Property(index),5) + String.IsEmpty(Window.Property(content.filling))">Conditional</animation>
    {% include "includes/scrollbar_style.xml.tpl" %}
    <onleft>151</onleft>
</control>
{% endblock content %}
