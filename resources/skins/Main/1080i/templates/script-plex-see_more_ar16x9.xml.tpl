{% extends "see_more.xml.tpl" %}
{# A row's every item in the Recommended 16:9 row's card with up to two caption lines (Other
   Videos rows - films and clips; every three-line row is a poster row). Row pitch 383: the card
   and two lines are 354, then the poster grid's gap (455 - 426). Over 1139 / 3, so the panel still
   holds two rows (see_more.xml.tpl).
   Three columns, cell 544 wide (the spec's: 3 x 544 = 1632, the six 272s of the other grids, so the
   edges match). The card sits 180 down its cell, just under the title: a row's grid has no group
   buttons (see_more.HubGridWindow). #}
{% block page_slide %}
    <animation effect="slide" start="0,0" end="0,{{ vscale(-60) }}" time="200" tween="quadratic" easing="out" reversible="false" condition="Integer.IsGreater(Container(101).ListItem.Property(index),2)">Conditional</animation>
    <animation effect="slide" start="0,{{ vscale(-60) }}" end="0,0" time="200" tween="quadratic" easing="out" reversible="false" condition="!Integer.IsGreater(Container(101).ListItem.Property(index),2)">Conditional</animation>
{% endblock page_slide %}
{% block header_scroll %}
        <animation effect="slide" start="0,0" end="0,{{ vscale(-383) }}" time="200" tween="quadratic" easing="out" reversible="false" condition="Container(101).HasPrevious">Conditional</animation>
        <animation effect="slide" start="0,{{ vscale(-383) }}" end="0,0" time="200" tween="quadratic" easing="out" reversible="false" condition="!Container(101).HasPrevious">Conditional</animation>
{% endblock header_scroll %}
{% block hitrect_y %}{{ vscale(175) }}{% endblock %}
{% block layouts %}
<itemlayout width="544" height="{{ vscale(383) }}">
    {% include "includes/grid_tile_ar16x9.xml.tpl" with focused=False & py=180 %}
</itemlayout>
<focusedlayout width="544" height="{{ vscale(383) }}">
    {% include "includes/grid_tile_ar16x9.xml.tpl" with focused=True & py=180 %}
</focusedlayout>
{% endblock layouts %}
