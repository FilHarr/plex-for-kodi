{% extends "see_more.xml.tpl" %}
{# A row's every item in the library poster grid's card with three caption lines (episode rows:
   Recently Released, Recently Added TV, Recently Watched Episodes). Row pitch 480: the card and
   three lines are 453, then the gap. The second row's foot starts below the screen, as the
   library grid's does; the page slide brings it up as focus reaches it (see_more.xml.tpl).
   Cell 272 wide, the rows' own. The card sits 180 down its cell, just under the title: a row's
   grid has no group buttons (see_more.HubGridWindow). #}
{% block header_scroll %}
        <animation effect="slide" start="0,0" end="0,{{ vscale(-480) }}" time="200" tween="quadratic" easing="out" reversible="false" condition="Container(101).HasPrevious">Conditional</animation>
        <animation effect="slide" start="0,{{ vscale(-480) }}" end="0,0" time="200" tween="quadratic" easing="out" reversible="false" condition="!Container(101).HasPrevious">Conditional</animation>
{% endblock header_scroll %}
{% block hitrect_y %}{{ vscale(175) }}{% endblock %}
{% block layouts %}
<itemlayout width="272" height="{{ vscale(480) }}">
    {% include "includes/grid_tile_poster.xml.tpl" with focused=False & py=180 %}
</itemlayout>
<focusedlayout width="272" height="{{ vscale(480) }}">
    {% include "includes/grid_tile_poster.xml.tpl" with focused=True & py=180 %}
</focusedlayout>
{% endblock layouts %}
