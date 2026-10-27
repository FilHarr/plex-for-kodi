{% extends "base.xml.tpl" %}
{% block window_animation %}{% include "includes/dialog_close_fade.xml.tpl" %}{% endblock %}
{% block backgroundcolor %}{% endblock %}
{% block headers %}
<!-- above the video player's OSD (script-plex-seek_dialog's 100): a dialog without a zorder draws
     beneath it, the OSD's gradients, buttons and bar over this -->
<zorder>101</zorder>
{% endblock %}
{% block controls %}
<!-- The option pickers (dialog.SelectDialog: the Settings dialog's, the video player's buttons'): fixed 876
     high - the 66 heading, 13 rows of 61 (793) and the 17 that leave 20 under the last card - centred between
     the video player's clock and elapsed time (their boxes end at 100 and start at 982, so 103-979), its right
     edge 10 from the screen's. -->
{% include "includes/option_card_frame.xml.tpl" with list_height=793 & row_height=61 & card_height=55 & line1_y=7.5 & line2_y=31.5 & tick_y=17.5 & frame_x=1290 & frame_y=169 & backdrop_height=876 & shadow_height=956 & list_width=600 & text_width=520 & label_width=560 & tick_x=554 & backdrop_y=-66 & backdrop_width=640 & shadow_y=-106 & shadow_width=720 & scrollbar_x=604 %}
{% endblock controls %}
