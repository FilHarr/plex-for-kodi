{% extends "base.xml.tpl" %}
{% block window_animation %}{% include "includes/dialog_close_fade.xml.tpl" %}{% endblock %}
{% block backgroundcolor %}{% endblock %}
{% block controls %}
<!-- The sidebar's user menu (dialog.UserMenuDialog, from its user button): the option pickers' frame and cards
     (includes/option_card_frame.xml.tpl) without the heading, as wide as its options want and as tall as there are
     of them (UserMenuDialog.fitFrame()). Its panel's top at 42, where the menu it replaces (an in-screen dropdown)
     started, and its left edge at 325, the sidebar's other menus' (the list at 345): a 300 list, its cards' text
     260 wide (no ticks), 20 of panel round it; 17 above the first row and below the last, their cards 3 in, so 20
     to each card. -->
{% include "includes/option_card_frame.xml.tpl" with list_height=793 & row_height=61 & card_height=55 & line1_y=7.5 & line2_y=31.5 & tick_y=17.5 & frame_x=345 & frame_y=59 & backdrop_height=400 & shadow_height=480 & list_width=300 & text_width=260 & label_width=260 & tick_x=254 & backdrop_y=-17 & backdrop_width=340 & shadow_y=-57 & shadow_width=420 & scrollbar_x=304 %}
{% endblock controls %}
