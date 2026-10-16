{% extends "base.xml.tpl" %}
{% block backgroundcolor %}{% endblock %}
{% block headers %}
<!-- above the video player's OSD (script-plex-seek_dialog's 100): a dialog without a zorder draws
     beneath it, the OSD's gradients, buttons and bar over this -->
<zorder>101</zorder>
{% endblock %}
{% block controls %}
{% include "includes/option_card_frame.xml.tpl" with list_height=640 & row_height=64 & card_height=58 & line1_y=9 & line2_y=33 & tick_y=19 %}
{% endblock controls %}
