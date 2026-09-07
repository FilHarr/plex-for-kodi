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
    <posx>105</posx>
    <posy>{{ vscale(127.5) }}</posy>
    <width>870</width>
    <height>{{ vscale(65) }}</height>
    <align>left</align>
    <itemgap>0</itemgap>
    <orientation>horizontal</orientation>
    <onleft>9000</onleft>
    <!-- Right into the button row lands on its LEFTMOST button, not on whatever it happened to
         have focused last. Targeting the grouplist (300) by id makes Kodi restore the row's own
         remembered child, which is what you want entering from above or below but not from the
         side - it let a press of right from here land on the rightmost button (Change view).
         Naming a child control by id is how the button row's own <onleft>210</onleft> already
         crosses back into this row, so this is the symmetric form of what that already does.

         Three clauses because the leftmost button is not always 301: Play and Shuffle share one
         visibility condition (disable_playback / collection item type), so when Play is hidden
         Shuffle is too and the leftmost visible button is More, or View when More is hidden as
         well. View carries no visibility condition in this chain, so it is the safe fallback. -->
    <onright condition="Control.IsVisible(301)">301</onright>
    <onright condition="!Control.IsVisible(301) + Control.IsVisible(303)">303</onright>
    <onright>304</onright>
    <ondown>101</ondown>
    <onup condition="Control.IsVisible(320)">320</onup>
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
        <label>[CAPITALIZE]$INFO[Window.Property(filter2.display)][/CAPITALIZE]</label>
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
        <label>[CAPITALIZE]$INFO[Window.Property(filter1.display)][/CAPITALIZE]</label>
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
        <textoffsetx>20</textoffsetx>
        <textoffsety>0</textoffsety>
        <label>[CAPITALIZE]$INFO[Window.Property(media.type)][/CAPITALIZE]</label>
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
        <label>[CAPITALIZE]$INFO[Window.Property(media.type)][/CAPITALIZE]</label>
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
    <control type="button" id="215">
        <!-- TEMP: blank 15px gap before the sort-direction icon, while itemgap is 0 for
             testing - disabled button (not a plain image), matching the same nav-safe
             placeholder pattern used elsewhere in this row. Remove alongside the itemgap/posx
             testing changes. -->
        <visible>!String.IsEqual(Window.Property(media.itemType),folder)</visible>
        <enable>false</enable>
        <width>{{ vscale(15) }}</width>
        <height>{{ vscale(65) }}</height>
        <texturefocus>-</texturefocus>
        <texturenofocus>-</texturenofocus>
    </control>
    <control type="button" id="212">
        <!-- Ascending/descending indicator for the sort button below - see sortButtonClicked()/
             updateSortIcon() (library.py). type=button + enable=false, not type=image: a plain
             image here isn't a focusable-eligible control type, which breaks the grouplist's
             internal navigation - same class of issue as the plain-label case 313 already
             documents below. Direct grouplist child at the row's own full height (not a shorter
             box + <posy>, and not wrapped in a group): a shorter box with an explicit posy
             offset - even nested one level inside a group - measurably broke this row's
             right-navigation out to the play button when this sat after 210 instead of before
             it, for reasons that didn't trace back to any onright value. Matching every
             sibling's plain full-height footprint is what's proven not to disturb it, so the
             vertical offset is baked into the sort-asc/desc.png canvas's own transparent padding
             instead of a posy tag. Sits before 210 (between 314 and it), not after: 314 is
             already a proven-safe disabled placeholder ahead of a real focusable control, so
             this just extends that same already-working internal-flow skip rather than
             recreating the boundary-exit case 210's own onright comment covers. Two
             mutually-exclusive static-texture buttons, not one dynamic $INFO path -
             $INFO[Window.Property(...)] isn't evaluated inside <texturenofocus> the way it is
             inside an image control's <texture>, so that only rendered an empty box. Same
             swap-on-a-property pattern 310/312 already use above for the media-type button's
             artist variant. -->
        <visible>!String.IsEqual(Window.Property(media.itemType),folder) + !String.IsEqual(Window.Property(sort.icon),desc)</visible>
        <enable>false</enable>
        <width>{{ vscale(30) }}</width>
        <height>{{ vscale(65) }}</height>
        <texturefocus>-</texturefocus>
        <texturenofocus>script.plex/indicators/sort-asc.png</texturenofocus>
    </control>
    <control type="button" id="213">
        <visible>!String.IsEqual(Window.Property(media.itemType),folder) + String.IsEqual(Window.Property(sort.icon),desc)</visible>
        <enable>false</enable>
        <width>{{ vscale(30) }}</width>
        <height>{{ vscale(65) }}</height>
        <texturefocus>-</texturefocus>
        <texturenofocus>script.plex/indicators/sort-desc.png</texturenofocus>
    </control>
    <control type="button" id="210">
        <visible>!String.IsEqual(Window.Property(media.itemType),folder)</visible>
        <!-- Explicit, not relying on the grouplist's own onright: the trailing item-count
             label below is non-focusable, which stops the grouplist from falling through to
             its container-level onright when 210 is the last focusable (but not last
             declared) child. Targets 301 (the play button) directly, not container 300. -->
        <onright>301</onright>
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
        <label>[CAPITALIZE]$INFO[Window.Property(sort.display)][/CAPITALIZE]</label>
    </control>
    <control type="button" id="313">
        <!-- type=button + enable=false, not a plain label: a trailing plain <label> as the
             grouplist's last child breaks the list's onright boundary-fallback for whichever
             button precedes it (210 couldn't reach 300 on the right with a label here) - a
             disabled button matches the already-working 311/310 placeholder pattern above.
             Explicit onright of its own (previously relied only on being unreachable since
             disabled): belt-and-suspenders alongside 210/212/213's own onright, in case Kodi's
             right-navigation ever lands focus attempts here instead of falling through. -->
        <enable>false</enable>
        <onright>301</onright>
        <width max="400">auto</width>
        <height>{{ vscale(65) }}</height>
        <font>font10</font>
        <textcolor>gray</textcolor>
        <disabledcolor>gray</disabledcolor>
        <align>left</align>
        <aligny>center</aligny>
        <texturefocus>-</texturefocus>
        <texturenofocus>-</texturenofocus>
        <label>($INFO[Window.Property(items.count)] [LOWERCASE]$INFO[Window.Property(media.type)][/LOWERCASE])</label>
    </control>
</control>
{% endblock filteropts_grouplist %}