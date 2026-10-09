{% extends "script-plex-posters.xml.tpl" %}
{# The library grid of an Other Videos section (library.Ar16x9Window): the poster grid as it is -
   header, filter and button rows, scrubber, scrollbar - with the Recommended 16:9 row's card
   three to a row (includes/library_tile_ar16x9.xml.tpl), on request (2026-10-09). Its only view,
   so no Change view button.

   Three columns of 544 (the six 272s of the poster grid, so the last column's art ends on its
   1718). Row pitch 388: the poster grid's own 41 between a row's captions and the next row's art.
   The panel is 1160 tall, not 1190: Kodi scrolls a panel as focus passes the last row its height
   holds whole (height over pitch, rounded down), and at 1190 that's three of these, the third off
   the screen's foot; 1160 holds two, as the poster grid does, and still reaches past the screen's
   foot once the page has slid up its 115, so rows clip only at the screen's edge.

   The poster grid's first-row numbers follow its column count: its last index (2), its size (3),
   and up off the first row going to the filter row from the left two columns, the buttons from
   the third. #}
{% block header_animation %}<animation effect="slide" end="0,{{ vscale(-125) }}" time="200" tween="quadratic" easing="out" condition="Integer.IsGreater(Container(101).ListItem.Property(index),2) + !ControlGroup(200).HasFocus(0) + String.IsEmpty(Window.Property(content.filling))">Conditional</animation>{% endblock %}
{% block hide_filter_from_index %}2{% endblock %}
{% block header_bg %}
<control type="image">
    <animation effect="fade" start="0" end="100" time="200" tween="quadratic" easing="out" reversible="true">VisibleChange</animation>
    <visible>ControlGroup(200).HasFocus(0) + Integer.IsGreater(Container(101).ListItem.Property(index),2)</visible>
    <posx>0</posx>
    <posy>0</posy>
    <width>1920</width>
    <height>{{ vscale(125) }}</height>
    <texture>script.plex/white-square.png</texture>
    <colordiffuse>C0000000</colordiffuse>
</control>
{% endblock %}
{% block first_row_end %}2{% endblock %}
{% block row_size %}3{% endblock %}
{% block onup_split %}2{% endblock %}
{# Play and Shuffle are the whole button row here (More is Photos' only) #}
{% block rightmost_button %}302{% endblock %}
{% block filteropts_onright_last %}{% endblock %}
{% block view_button %}{% endblock %}
{% block panel_height %}1160{% endblock %}
{% block grid_layouts %}
            <itemlayout width="544" height="{{ vscale(388) }}">
                {% include "includes/library_tile_ar16x9.xml.tpl" with focused=False %}
            </itemlayout>
            <focusedlayout width="544" height="{{ vscale(388) }}">
                {% include "includes/library_tile_ar16x9.xml.tpl" with focused=True %}
            </focusedlayout>
{% endblock grid_layouts %}
