{% extends "base.xml.tpl" %}
{% block window_animation %}{% include "includes/dialog_close_fade.xml.tpl" %}{% endblock %}
{% block backgroundcolor %}{% endblock %}
{% block controls %}
<!-- The add-on's Settings (settings.SettingsPickerDialog): the option picker (script-plex-settings_select_dialog's
     frame) beside the sidebar, as the Libraries picker - its sections, a section's settings and a setting's
     values, each opened over the one before - with the focused row's help in a panel to its right. -->
{% include "includes/option_card_frame.xml.tpl" with list_height=793 & row_height=61 & card_height=55 & line1_y=7.5 & line2_y=31.5 & tick_y=17.5 & frame_x=1290 & frame_y=169 & backdrop_height=876 & shadow_height=956 & list_width=600 & text_width=520 & label_width=560 & tick_x=554 & backdrop_y=-66 & backdrop_width=640 & shadow_y=-106 & shadow_width=720 & scrollbar_x=604 %}
<!-- The focused row's description: shown while it has one, and while no picker of these is open over this one
     ('covered'), whose own panel is in its place. 20 right of the frame's panel (325-965), its top level with the
     frame's (103) and as tall as the text: 20 above and below lines of font10, 25 in from each side, as the confirm
     box's message. The text is a window property, not the focused item's, so that SettingsPickerDialog.fitDescription()
     sizes the box before the text arrives: a textbox lays out its lines when its text changes, so a box resized
     after that showed the previous row's number of lines. -->
<control type="group" id="300">
    <visible>!String.IsEmpty(Window.Property(description)) + String.IsEmpty(Window.Property(covered))</visible>
    <animation effect="fade" start="0" end="100" time="150">Visible</animation>
    <animation effect="fade" start="100" end="0" time="150">Hidden</animation>
    <posx>985</posx>
    <posy>{{ vscale(103) }}</posy>
    <control type="image" id="302">
        <posx>-40</posx>
        <posy>{{ vscale(-40) }}</posy>
        <width>720</width>
        <height>{{ vscale(148) }}</height>
        <texture border="42">script.plex/drop-shadow.png</texture>
    </control>
    <control type="image" id="301">
        <posx>0</posx>
        <posy>0</posy>
        <width>640</width>
        <height>{{ vscale(68) }}</height>
        <texture colordiffuse="F2111111" border="10">script.plex/white-square-rounded.png</texture>
    </control>
    <control type="textbox" id="303">
        <posx>25</posx>
        <posy>{{ vscale(20) }}</posy>
        <width>590</width>
        <height>{{ vscale(32) }}</height>
        <font>font10</font>
        <align>left</align>
        <textcolor>FFDDDDDD</textcolor>
        <scrolltime>200</scrolltime>
        <autoscroll delay="5000" time="4000" repeat="15000"></autoscroll>
        <label>$INFO[Window.Property(description)]</label>
    </control>
</control>
{% endblock controls %}
