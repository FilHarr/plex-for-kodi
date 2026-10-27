{% extends "base.xml.tpl" %}
{% block window_animation %}{% include "includes/dialog_close_fade.xml.tpl" %}{% endblock %}
{% block headers %}<!-- over the option pickers (101), which a choice can leave open beneath this, and the video player's
     OSD (100) -->
<zorder>102</zorder><defaultcontrol>1001</defaultcontrol>{% endblock %}
{% block backgroundcolor %}{% endblock %}
{% block controls %}
<!-- The confirm and message box (optionsdialog.py) in the settings and pickers' style
     (includes/option_card_frame.xml.tpl): the 30% full-screen dim, a 640-wide F2111111 panel with their shadow,
     the heading in font25_title centred in its top 66, the message in font10 25 in from there, and the answers
     as a centred row of cards along the bottom - each sized to its label - Left and Right between them.
     Centred on the screen. OptionsDialog.fitFrame() sizes the message to its lines and the panel round it,
     and centres it; the sizes here are only a start (a one-line message). -->
<control type="image">
    <!-- none over an open picker, whose dim is already behind this (nested: dialog.pickerOpen()) -->
    <visible>String.IsEmpty(Window.Property(nested))</visible>
    <posx>0</posx>
    <posy>0</posy>
    <width>1920</width>
    <height>1080</height>
    <texture>script.plex/white-square.png</texture>
    <colordiffuse>4D000000</colordiffuse>
</control>
<control type="group" id="200">
    <visible>!String.IsEmpty(Window.Property(initialized))</visible>
    <posx>640</posx>
    <posy>{{ vscale(445) }}</posy>
    <control type="image" id="202">
        <posx>-40</posx>
        <posy>{{ vscale(-40) }}</posy>
        <width>720</width>
        <height>{{ vscale(269) }}</height>
        <texture border="42">script.plex/drop-shadow.png</texture>
    </control>
    <control type="image" id="201">
        <posx>0</posx>
        <posy>0</posy>
        <width>640</width>
        <height>{{ vscale(189) }}</height>
        <texture colordiffuse="F2111111" border="10">script.plex/white-square-rounded.png</texture>
    </control>
    <control type="label">
        <posx>40</posx>
        <posy>0</posy>
        <width>560</width>
        <height>{{ vscale(66) }}</height>
        <font>font25_title</font>
        <align>center</align>
        <aligny>center</aligny>
        <textcolor>FFEEEEEE</textcolor>
        <scroll>true</scroll>
        <scrollspeed>15</scrollspeed>
        <label>$INFO[Window.Property(header)]</label>
    </control>
    <!-- auto-scrolls only if a message ever outgrows its box (fitFrame() caps it at 12 lines) -->
    <control type="textbox" id="300">
        <posx>25</posx>
        <posy>{{ vscale(66) }}</posy>
        <width>590</width>
        <height>{{ vscale(32) }}</height>
        <font>font10</font>
        <align>left</align>
        <textcolor>FFDDDDDD</textcolor>
        <scrolltime>200</scrolltime>
        <autoscroll delay="3000" time="3000" repeat="3000"></autoscroll>
        <label>$INFO[Window.Property(info)]</label>
    </control>
    <!-- The answers: the picker rows' cards side by side - 55 high, 6 apart, a 99111111 card lit to the
         focused row's colour (the card under the pickers' 33FFFFFF, as one colour: a button has one texture),
         font8 - each as wide as its label and 24 either side of it, the row centred. In a plain group (203)
         that fitFrame() moves: Kodi's Python can't fetch a grouplist ("Unknown control type for python"). -->
    <control type="group" id="203">
    <posx>20</posx>
    <posy>{{ vscale(114) }}</posy>
    <control type="grouplist" id="100">
        <defaultcontrol always="true">1001</defaultcontrol>
        <posx>0</posx>
        <posy>0</posy>
        <width>600</width>
        <height>{{ vscale(55) }}</height>
        <align>center</align>
        <itemgap>6</itemgap>
        <orientation>horizontal</orientation>
        <scrolltime>0</scrolltime>
        <onleft>noop</onleft>
        <onright>noop</onright>
        <onup>noop</onup>
        <ondown>noop</ondown>
        {% for n, cid in ((0, 1001), (1, 1002), (2, 1003)) %}
        <control type="button" id="{{ cid }}">
            <visible{% if n == 0 %} allowhiddenfocus="true"{% endif %}>!String.IsEmpty(Window.Property(button.{{ n }}))</visible>
            <enable>String.IsEmpty(Window.Property(delay_buttons)) | !String.IsEmpty(Window.Property(enable_buttons))</enable>
            <width min="120">auto</width>
            <height>{{ vscale(55) }}</height>
            <font>font8</font>
            <align>center</align>
            <aligny>center</aligny>
            <textoffsetx>24</textoffsetx>
            <texturefocus colordiffuse="FF414141" border="10">script.plex/white-square-rounded.png</texturefocus>
            <texturenofocus colordiffuse="99111111" border="10">script.plex/white-square-rounded.png</texturenofocus>
            <textcolor>DDFFFFFF</textcolor>
            <focusedcolor>FFFFFFFF</focusedcolor>
            <disabledcolor>55FFFFFF</disabledcolor>
            <label>$INFO[Window.Property(button.{{ n }})]</label>
        </control>
        {% endfor %}
    </control>
    </control>
</control>
{% endblock controls %}
