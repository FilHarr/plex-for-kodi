{% extends "base.xml.tpl" %}
{% block window_animation %}{% include "includes/dialog_close_fade.xml.tpl" %}{% endblock %}
{% block backgroundcolor %}{% endblock %}
{% block headers %}
<!-- above the video player's OSD (script-plex-seek_dialog's 100): a dialog without a zorder draws
     beneath it, the OSD's gradients, buttons and bar over this -->
<zorder>101</zorder>
{% endblock %}
{% block controls %}
<!-- The Settings dialog (playersettings.VideoSettingsDialog: the video player's, pre-play's, the episodes'):
     the option pickers' frame - 876 high, 103-979, its right edge 10 from the screen's, 13 rows of 61 - so
     each picker opens exactly over it. -->
{% include "includes/settings_card_frame.xml.tpl" with list_height=793 & row_height=61 & card_height=55 & frame_x=1290 & frame_y=169 & backdrop_height=876 & shadow_height=956 %}
{% endblock controls %}
