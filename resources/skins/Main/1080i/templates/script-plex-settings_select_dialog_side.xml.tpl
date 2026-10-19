{% extends "base.xml.tpl" %}
{% block backgroundcolor %}{% endblock %}
{% block headers %}
<!-- above the video player's OSD (script-plex-seek_dialog's 100): a dialog without a zorder draws
     beneath it, the OSD's gradients, buttons and bar over this -->
<zorder>101</zorder>
{% endblock %}
{% block controls %}
<!-- The video player's Subtitles picker (Settings > Subtitles, dialog.SideSelectDialog): the option picker
     fixed 876 high - the 66 heading, 13 rows of 61 (793; the other pickers' are 64) and the 17 that leave 20
     under the last card - centred between the clock and the elapsed time (their boxes end at 100 and start at
     982, so 103-979), its right edge 10 from the screen's. -->
{% include "includes/option_card_frame.xml.tpl" with list_height=793 & row_height=61 & card_height=55 & line1_y=7.5 & line2_y=31.5 & tick_y=17.5 & frame_x=1290 & frame_y=169 & backdrop_height=876 & shadow_height=956 %}
{% endblock controls %}
