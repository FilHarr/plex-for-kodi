{% extends "base.xml.tpl" %}
{% block backgroundcolor %}{% endblock %}
{% block headers %}
<!-- above the video player's OSD (script-plex-seek_dialog's 100): a dialog without a zorder draws
     beneath it, the OSD's gradients, buttons and bar over this -->
<zorder>101</zorder>
{% endblock %}
{% block controls %}
<control type="group">
    <visible>String.IsEmpty(Window.Property(is_plextuary)) + !String.IsEmpty(Window.Property(via.OSD)) + !Window.IsVisible(sliderdialog)</visible>
    <animation effect="fade" start="100" end="0">Hidden</animation>
    <posx>0</posx>
    <posy>0</posy>
    <control type="image">
        <posx>0</posx>
        <posy>0</posy>
        <width>1920</width>
        <height>1080</height>
        <texture>script.plex/player-fade.png</texture>
        <colordiffuse>FF080808</colordiffuse>
    </control>
</control>
<!-- The video player's Settings dialog (Settings from its OSD, playersettings.SideVideoSettingsDialog):
     the option pickers' tall frame at the right - 876 high, 103-979, its right edge 10 from the screen's,
     13 rows of 61 - so each picker opens exactly over it. -->
{% include "includes/settings_card_frame.xml.tpl" with list_height=793 & row_height=61 & card_height=55 & frame_x=1290 & frame_y=169 & backdrop_height=876 & shadow_height=956 %}
{% endblock controls %}
