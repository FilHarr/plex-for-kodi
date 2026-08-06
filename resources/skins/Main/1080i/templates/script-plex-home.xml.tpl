{% extends "default.xml.tpl" %}
{% block content %}
<control type="grouplist" id="50">
    <!-- Slide right while the sidebar rail is expanded (focused), so hub content doesn't sit under the labels -->
    <animation effect="slide" end="220,0" time="200" tween="sine" easing="inout" condition="ControlGroup(9000).HasFocus(0)">Conditional</animation>

    <!-- Dynamic focus animations for hub rows -->
    <!-- Both stages below collapse row 0 out of view and are keyed off ITS actual display type
         (hub.display.400), not the type of whichever row currently has focus - the -555 "fully
         collapsed" stage stays flat once focus passes row 1 no matter how much deeper you scroll
         (every i beyond 1 produces the same effect), so this was never a per-row cumulative
         slide, just two fixed states sized to how tall row 0 itself is. The collapsed-stage
         values below are exact: -(row 0's real full pitch), matching the 555/500/445 pitches the
         hub rows above now render at. The partial-stage values (poster's hand-tuned -345, and
         ar16x9/square scaled from it by the same 345/555 ratio) are an estimate, not measured -
         flag if the transition feels off for a non-poster row 0. -->
    {% for display_type, transitional_end in [('poster', -345), ('ar16x9', -311), ('square', -277)] %}
    <animation type="Conditional" condition="Integer.IsGreater(Window.Property(hub.focus),0) + Control.IsVisible(500) + String.IsEqual(Window.Property(hub.display.400),{{ display_type }})" reversible="true">
        <effect type="slide" end="0,{{ vscale(transitional_end) }}" time="200" tween="sine" easing="inout"/>
    </animation>
    {% endfor %}

    <!-- Subsequent hubs: fully collapse row 0 once focus has passed row 1 -->
    {% for i in range(1, core.hub_count) %}
    {% for display_type, collapsed_end in [('poster', -555), ('ar16x9', -500), ('square', -445)] %}
    <animation type="Conditional" condition="Integer.IsGreater(Window.Property(hub.focus),{{ i }}) + Control.IsVisible({{ i + 499 }}) + String.IsEqual(Window.Property(hub.display.400),{{ display_type }})" reversible="true">
        <effect type="slide" end="0,{{ vscale(collapsed_end) }}" time="200" tween="sine" easing="inout"/>
    </animation>
    {% endfor %}
    {% endfor %}

    <defaultcontrol>500</defaultcontrol>
    <!-- posx=100, not 55: the sidebar rail is drawn on top (see its own comment in default.xml.tpl's
         header block), so this is purely about where departing posters get clipped as they scroll
         out of focus - this grouplist clips its children to its own rect, so its left edge is that
         clip boundary. 55 sat right at the collapsed rail's icon column, so a departing poster
         visibly clipped mid-icon instead of clearing the rail's full condensed width first; 100
         gives it that extra room. Row titles/bifurcation lines and item layout insets below have
         their own posx reduced by the same 45px this moved right, to keep resting positions
         unchanged (60->15, 55->10). -->
    <posx>100</posx>
    <posy>{{ vscale(96) }}</posy>
    <width>2085</width>
    {% with n = core.hub_count %}{% with grouplist_height = n * 555 + 320 %}
    <height>{{ vscale(grouplist_height) }}</height>
    {% endwith %}{% endwith %}
    <itemgap>20</itemgap>
    <orientation>vertical</orientation>
    <usecontrolcoords>true</usecontrolcoords>
    <scrolltime tween="quadratic" easing="out">200</scrolltime>

    <!-- DYNAMIC HUB ROWS - Generated from hub_count setting -->
    {% for i in range(core.hub_count) %}
    {% with group_id = i + 500 & hub_id = i + 400 & spacer_id = i + 600 & is_first_hub = loop.is_first & is_last_hub = loop.is_last %}
    <!-- Row pitch varies by display type, but the hub's list control itself must stay a single
         physical control: home.py caches it via getControl() once at init (self.hubControls,
         home.py ~749), and Kodi's control lookup for a duplicated id always resolves to the same
         one instance regardless of which sibling's <visible> is actually true - unlike native
         focus/visibility handling, which is duplicate-id-aware (that's why the
         hub_itemlayout_*/hub_focusedlayout_* conditional selection works). Duplicating this
         list's id silently sent content to a hidden variant, leaving the visible (shorter) row
         empty. So the content group below is single and fixed at the shortest type's (square)
         real content extent, and a small conditional spacer - safe to duplicate since nothing
         ever targets it from Python - restores the rest of the pitch for taller types. -->
    <control type="group" id="{{ group_id }}">
        <visible>Integer.IsGreater(Container({{ hub_id }}).NumItems,0) + String.IsEmpty(Window.Property(drawing))</visible>
        <defaultcontrol>{{ hub_id }}</defaultcontrol>
        <width>1920</width>
        <height>{{ vscale(425) }}</height>
        <control type="image">
            <visible>!String.IsEmpty(Window.Property(bifurcation_lines))</visible>
            <posx>15</posx>
            <posy>{{ vscale(12) }}</posy>
            <width>1800</width>
            <height>{{ vscale(2) }}</height>
            <texture>script.plex/white-square.png</texture>
            <colordiffuse>A0000000</colordiffuse>
        </control>
        <control type="label">
            <posx>15</posx>
            <posy>0</posy>
            <width>1000</width>
            <height>{{ vscale(87) }}</height>
            <font>font12</font>
            <align>left</align>
            <aligny>center</aligny>
            <textcolor>FFFFFFFF</textcolor>
            <label>[UPPERCASE]$INFO[Window.Property(hub.{{ hub_id }})][/UPPERCASE]</label>
        </control>
        <control type="list" id="{{ hub_id }}">
            <posx>0</posx>
            <posy>{{ vscale(29) }}</posy>
            <width>1920</width>
            <height>{{ vscale(515) }}</height>
            <onup>{% if not is_first_hub %}{{ hub_id - 1 }}{% else %}noop{% endif %}</onup>
            <ondown>{% if is_last_hub %}{{ hub_id }}{% else %}{{ hub_id + 1 }}{% endif %}</ondown>
            <onright>noop</onright>
            <onleft>9001</onleft>
            <scrolltime>200</scrolltime>
            <orientation>horizontal</orientation>
            <preloaditems>4</preloaditems>

            <!-- Conditional item layouts - Kodi selects layout based on condition attribute -->
            {% include "includes/hub_itemlayout_poster.xml.tpl" %}
            {% include "includes/hub_itemlayout_square.xml.tpl" %}
            {% include "includes/hub_itemlayout_ar16x9.xml.tpl" %}
            <!-- Conditional focused layouts - Kodi selects layout based on condition attribute -->
            {% include "includes/hub_focusedlayout_poster.xml.tpl" %}
            {% include "includes/hub_focusedlayout_square.xml.tpl" %}
            {% include "includes/hub_focusedlayout_ar16x9.xml.tpl" %}
        </control>
    </control>
    <!-- Pitch top-up for types taller than the square baseline above; absent entirely for
         square, so it doesn't add a second itemgap on top of an already-correct pitch. -->
    {% for display_type, extra_height in [('poster', 90), ('ar16x9', 35)] %}
    <control type="group" id="{{ spacer_id }}">
        <visible>Integer.IsGreater(Container({{ hub_id }}).NumItems,0) + String.IsEmpty(Window.Property(drawing)) + String.IsEqual(Window.Property(hub.display.{{ hub_id }}),{{ display_type }})</visible>
        <width>1920</width>
        <height>{{ vscale(extra_height) }}</height>
    </control>
    {% endfor %}
    {% endwith %}
    {% endfor %}

    <control type="label">
        <!-- DUMMY -->
        <width>1920</width>
        <height>{{ vscale(100) }}</height>
        <font>font12</font>
        <align>left</align>
        <aligny>center</aligny>
        <textcolor>00FFFFFF</textcolor>
        <label> </label>
    </control>
</control>

{% endblock content %}

{% block header %}
<control type="group" id="200">
    <posx>0</posx>
    <posy>0</posy>
    <width>1920</width>
    <height>{{ vscale(135) }}</height>
    <control type="group">
        <visible>Player.HasAudio + String.IsEmpty(Window(10000).Property(script.plex.theme_playing))</visible>
        <posx>438</posx>
        <posy>0</posy>
        <control type="button" id="204">
            <visible>Player.HasAudio + String.IsEmpty(Window(10000).Property(script.plex.theme_playing))</visible>
            <posx>-10</posx>
            <posy>{{ vscale(38) }}</posy>
            <width>260</width>
            <height>{{ vscale(75) }}</height>
            <onleft>9001</onleft>
            <ondown>50</ondown>
            <font>font12</font>
            <textcolor>FFFFFFFF</textcolor>
            <focusedcolor>FF000000</focusedcolor>
            <align>right</align>
            <aligny>center</aligny>
            <texturefocus colordiffuse="FFE5A00D" border="10">script.plex/white-square-rounded.png</texturefocus>
            <texturenofocus>-</texturenofocus>
            <textoffsetx>100</textoffsetx>
            <textoffsety>0</textoffsety>
            <label> </label>
        </control>
        <control type="image">
            <posx>0</posx>
            <posy>{{ vscale(48) }}</posy>
            <width>42</width>
            <height>{{ vscale(42) }}</height>
            <texture>$INFO[Player.Art(thumb)]</texture>
        </control>

        <control type="group">
            <visible>!Control.HasFocus(204)</visible>
            <control type="label">
                <posx>53</posx>
                <posy>{{ vscale(48) }}</posy>
                <width>187</width>
                <height>{{ vscale(20) }}</height>
                <font>font10</font>
                <align>left</align>
                <aligny>center</aligny>
                <textcolor>FFFFFFFF</textcolor>
                <info>MusicPlayer.Artist</info>
            </control>
            <control type="label">
                <posx>53</posx>
                <posy>{{ vscale(72) }}</posy>
                <width>187</width>
                <height>{{ vscale(20) }}</height>
                <font>font10</font>
                <align>left</align>
                <aligny>center</aligny>
                <textcolor>FFFFFFFF</textcolor>
                <info>MusicPlayer.Title</info>
            </control>
        </control>
        <control type="group">
            <visible>Control.HasFocus(204)</visible>
            <control type="label">
                <posx>53</posx>
                <posy>{{ vscale(48) }}</posy>
                <width>187</width>
                <height>{{ vscale(20) }}</height>
                <font>font10</font>
                <align>left</align>
                <aligny>center</aligny>
                <textcolor>FF000000</textcolor>
                <info>MusicPlayer.Artist</info>
            </control>
            <control type="label">
                <posx>53</posx>
                <posy>{{ vscale(72) }}</posy>
                <width>187</width>
                <height>{{ vscale(20) }}</height>
                <font>font10</font>
                <align>left</align>
                <aligny>center</aligny>
                <textcolor>FF000000</textcolor>
                <info>MusicPlayer.Title</info>
            </control>
        </control>

        <control type="progress">
            <description>Progressbar</description>
            <posx>0</posx>
            <posy>{{ vscale(102) }}</posy>
            <width>240</width>
            <height>{{ vscale(1) }}</height>
            <texturebg colordiffuse="9AFFFFFF">script.plex/white-square-1px.png</texturebg>
            <lefttexture>-</lefttexture>
            <midtexture colordiffuse="FFCC7B19">script.plex/white-square-1px.png</midtexture>
            <righttexture>-</righttexture>
            <overlaytexture>-</overlaytexture>
            <info>Player.Progress</info>
        </control>
    </control>
    <control type="label">
        <right>60</right>
        <posy>{{ vscale(35) }}</posy>
        <width>200</width>
        <height>{{ vscale(65) }}</height>
        <font>font12</font>
        <align>right</align>
        <aligny>center</aligny>
        <textcolor>FFFFFFFF</textcolor>
        <label>$INFO[System.Time]</label>
    </control>

    {% include "includes/sidebar_dropdowns.xml.tpl" %}
</control>

<control type="group">
    <visible>!String.IsEmpty(Window.Property(search.dialog))</visible>
    <control type="group" >
        <visible>!String.IsEmpty(Window.Property(search.dialog.hasresults))</visible>
        <control type="image">
            <posx>0</posx>
            <posy>0</posy>
            <width>1920</width>
            <height>1080</height>
            <texture>script.plex/home/background-fallback.png</texture>
            {% include "includes/scale_background.xml.tpl" %}
        </control>
        <control type="image">
            <posx>0</posx>
            <posy>0</posy>
            <width>1920</width>
            <height>1080</height>
            <texture background="true">$INFO[Window.Property(background)]</texture>
            {% include "includes/scale_background.xml.tpl" %}
        </control>
    </control>
    <control type="image">
        <posx>0</posx>
        <posy>0</posy>
        <width>1920</width>
        <height>1080</height>
        <texture colordiffuse="99606060">script.plex/white-square.png</texture>
        {% include "includes/scale_background.xml.tpl" %}
    </control>
</control>

<control type="group">
    <visible>String.IsEmpty(Window.Property(busy)) + !String.IsEmpty(Window.Property(no.content))</visible>
    <posx>0</posx>
    <posy>{{ vscale(465) }}</posy>
    <control type="label">
        <scroll>false</scroll>
        <posx>60</posx>
        <posy>0</posy>
        <width>1800</width>
        <height>{{ vscale(35) }}</height>
        <font>font13</font>
        <align>center</align>
        <textcolor>FFFFFFFF</textcolor>
        <label>[B]$ADDON[script.plexmod 32452][/B]</label>
    </control>
    <control type="label">
        <scroll>false</scroll>
        <posx>60</posx>
        <posy>{{ vscale(60) }}</posy>
        <width>1800</width>
        <height>{{ vscale(35) }}</height>
        <font>font13</font>
        <align>center</align>
        <textcolor>FFCCCCCC</textcolor>
        <label>$ADDON[script.plexmod 32453]</label>
    </control>
</control>

<control type="group">
    <visible>String.IsEmpty(Window.Property(busy)) + !String.IsEmpty(Window.Property(loading.content))</visible>
    <posx>0</posx>
    <posy>{{ vscale(465) }}</posy>
    <control type="label">
        <scroll>false</scroll>
        <posx>60</posx>
        <posy>0</posy>
        <width>1800</width>
        <height>{{ vscale(35) }}</height>
        <font>font13</font>
        <align>center</align>
        <textcolor>FFFFFFFF</textcolor>
        <label>[B]$ADDON[script.plexmod 34020][/B]</label>
    </control>
    <control type="label">
        <scroll>false</scroll>
        <posx>60</posx>
        <posy>{{ vscale(60) }}</posy>
        <width>1800</width>
        <height>{{ vscale(35) }}</height>
        <font>font13</font>
        <align>center</align>
        <textcolor>FFCCCCCC</textcolor>
        <label>[B]$ADDON[script.plexmod 34021][/B]</label>
    </control>
</control>

<control type="group">
    <visible>!String.IsEmpty(Window.Property(busy))</visible>
    <animation effect="fade" start="0" end="100">Visible</animation>
    <posx>840</posx>
    <posy>{{ vscale(465) }}</posy>
    <control type="image">
        <posx>0</posx>
        <posy>0</posy>
        <width>240</width>
        <height>{{ vscale(150) }}</height>
        <texture>script.plex/busy-back.png</texture>
        <colordiffuse>A0FFFFFF</colordiffuse>
    </control>
    <control type="image">
        <posx>75</posx>
        <posy>{{ vscale(56) }}</posy>
        <width>90</width>
        <height>{{ vscale(38) }}</height>
        <texture diffuse="script.plex/busy-diffuse.png">script.plex/busy.gif</texture>
    </control>
</control>

{% include "includes/sidebar.xml.tpl" %}
{% endblock header %}
