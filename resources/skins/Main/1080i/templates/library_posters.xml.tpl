{% extends "library.xml.tpl" %}
{% block filteropts_grouplist %}
<control type="grouplist" id="600">
    <visible>String.IsEmpty(Window.Property(hide.filteroptions))</visible>
    <visible>!Integer.IsGreater(Container(101).ListItem.Property(index),{% block hide_filter_from_index %}5{% endblock %}) + String.IsEmpty(Window.Property(no.content)) + !String.IsEmpty(Window.Property(initialized))</visible>
    <animation effect="slide" time="200" end="0,{{ vscale(-115) }}" tween="quadratic" easing="out" condition="Integer.IsGreater(Container(101).ListItem.Property(index),{% block hide_filter_from_index %}5{% endblock %}) + String.IsEmpty(Window.Property(content.filling))">Conditional</animation>
    {% block filteropts_animation %}
        <animation effect="fade" start="0" end="100" time="200" reversible="true">VisibleChange</animation>
    {% endblock %}
    <!-- Swapped with the buttons row (300): this row now sits where 300 used to (left,
         next to the sidebar), so it needs the same expand-slide the content/scrubber use. -->
    <animation effect="slide" end="220,0" time="200" tween="sine" easing="inout" condition="ControlGroup(9000).HasFocus(0)">Conditional</animation>
    <posx>90</posx>
    <posy>{{ vscale(127.5) }}</posy>
    <width>870</width>
    <height>{{ vscale(65) }}</height>
    <align>left</align>
    <itemgap>15</itemgap>
    <orientation>horizontal</orientation>
    <onleft>9000</onleft>
    <onright>300</onright>
    <ondown>101</ondown>
    <onup condition="Player.HasAudio + String.IsEmpty(Window(10000).Property(script.plex.theme_playing))">204</onup>
    <control type="button" id="311">
        <visible>!String.IsEqual(Window.Property(media.itemType),folder)</visible>
        <enable>false</enable>
        <width max="300">auto</width>
        <height>{{ vscale(65) }}</height>
        <font>font10</font>
        <textcolor>A0FFFFFF</textcolor>
        <focusedcolor>A0FFFFFF</focusedcolor>
        <disabledcolor>A0FFFFFF</disabledcolor>
        <align>center</align>
        <aligny>center</aligny>
        <texturefocus>-</texturefocus>
        <texturenofocus>-</texturenofocus>
        <textoffsetx>0</textoffsetx>
        <textoffsety>0</textoffsety>
        <label>[UPPERCASE]$INFO[Window.Property(filter2.display)][/UPPERCASE]</label>
    </control>
    <control type="button" id="211">
        <visible>!String.IsEqual(Window.Property(media.itemType),folder)</visible>
        <width max="400">auto</width>
        <height>{{ vscale(65) }}</height>
        <font>font10</font>
        <textcolor>FFFFFFFF</textcolor>
        <focusedcolor>FFFFFFFF</focusedcolor>
        <align>center</align>
        <aligny>center</aligny>
        <texturefocus colordiffuse="33FFFFFF" border="10">script.plex/white-square-rounded.png</texturefocus>
        <texturenofocus>-</texturenofocus>
        <textoffsetx>20</textoffsetx>
        <textoffsety>0</textoffsety>
        <label>[UPPERCASE]$INFO[Window.Property(filter1.display)][/UPPERCASE]</label>
    </control>
    <control type="button" id="310">
        <visible>String.IsEqual(Window.Property(subDir),1) | ![String.IsEqual(Window.Property(media),show) | String.IsEqual(Window.Property(media),movie) | String.IsEqual(Window.Property(media),movies_shows)]</visible>
        <enable>false</enable>
        <width max="300">auto</width>
        <height>{{ vscale(65) }}</height>
        <font>font10</font>
        <textcolor>FFFFFFFF</textcolor>
        <focusedcolor>FFFFFFFF</focusedcolor>
        <disabledcolor>FFFFFFFF</disabledcolor>
        <align>center</align>
        <aligny>center</aligny>
        <texturenofocus>-</texturenofocus>
        <texturenofocus>-</texturenofocus>
        <textoffsetx>20</textoffsetx>
        <textoffsety>0</textoffsety>
        <label>[UPPERCASE]$INFO[Window.Property(media.type)][/UPPERCASE]</label>
    </control>
    <control type="button" id="312">
        <visible>!String.IsEqual(Window.Property(subDir),1) + [String.IsEqual(Window.Property(media),show) | String.IsEqual(Window.Property(media),movie) | String.IsEqual(Window.Property(media),movies_shows)]</visible>
        <width max="300">auto</width>
        <height>{{ vscale(65) }}</height>
        <font>font10</font>
        <textcolor>FFFFFFFF</textcolor>
        <focusedcolor>FFFFFFFF</focusedcolor>
        <disabledcolor>FFFFFFFF</disabledcolor>
        <align>center</align>
        <aligny>center</aligny>
        <texturefocus colordiffuse="33FFFFFF" border="10">script.plex/white-square-rounded.png</texturefocus>
        <texturenofocus>-</texturenofocus>
        <textoffsetx>20</textoffsetx>
        <textoffsety>0</textoffsety>
        <label>[UPPERCASE]$INFO[Window.Property(media.type)][/UPPERCASE]</label>
    </control>
    <control type="button" id="314">
        <!-- Same disabled-button placeholder trick as 311/310/313: a plain <label> here
             would sit mid-list rather than trailing, so it wouldn't break onright the way
             313 did, but it's kept as a button for consistency with the rest of the row. -->
        <visible>!String.IsEqual(Window.Property(media.itemType),folder)</visible>
        <enable>false</enable>
        <width max="60">auto</width>
        <height>{{ vscale(65) }}</height>
        <font>font10</font>
        <textcolor>gray</textcolor>
        <disabledcolor>gray</disabledcolor>
        <align>center</align>
        <aligny>center</aligny>
        <texturefocus>-</texturefocus>
        <texturenofocus>-</texturenofocus>
        <textoffsetx>0</textoffsetx>
        <textoffsety>0</textoffsety>
        <label>$ADDON[script.plexmod 35052]</label>
    </control>
    <control type="button" id="210">
        <visible>!String.IsEqual(Window.Property(media.itemType),folder)</visible>
        <!-- Explicit, not relying on the grouplist's own onright: the trailing item-count
             label below is non-focusable, which stops the grouplist from falling through to
             its container-level onright when 210 is the last focusable (but not last
             declared) child. -->
        <onright>300</onright>
        <width max="300">auto</width>
        <height>{{ vscale(65) }}</height>
        <font>font10</font>
        <textcolor>FFFFFFFF</textcolor>
        <focusedcolor>FFFFFFFF</focusedcolor>
        <align>center</align>
        <aligny>center</aligny>
        <texturefocus colordiffuse="33FFFFFF" border="10">script.plex/white-square-rounded.png</texturefocus>
        <texturenofocus>-</texturenofocus>
        <textoffsetx>20</textoffsetx>
        <textoffsety>0</textoffsety>
        <label>[UPPERCASE]$INFO[Window.Property(sort.display)][/UPPERCASE]</label>
    </control>
    <control type="button" id="313">
        <!-- type=button + enable=false, not a plain label: a trailing plain <label> as the
             grouplist's last child breaks the list's onright boundary-fallback for whichever
             button precedes it (210 couldn't reach 300 on the right with a label here) - a
             disabled button matches the already-working 311/310 placeholder pattern above. -->
        <enable>false</enable>
        <width max="400">auto</width>
        <height>{{ vscale(65) }}</height>
        <font>font10</font>
        <textcolor>gray</textcolor>
        <disabledcolor>gray</disabledcolor>
        <align>left</align>
        <aligny>center</aligny>
        <texturefocus>-</texturefocus>
        <texturenofocus>-</texturenofocus>
        <label>$INFO[Window.Property(items.count)] $INFO[Window.Property(screen.title)]</label>
    </control>
</control>
{% endblock filteropts_grouplist %}