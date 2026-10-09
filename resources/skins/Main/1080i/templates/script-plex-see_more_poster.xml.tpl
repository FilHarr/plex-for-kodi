{% extends "see_more.xml.tpl" %}
{# A row's every item in the library poster grid's card with up to two caption lines (films, shows,
   seasons). Row pitch 455: the card and two lines are 426, then the gap.
   Cell 272 wide, the rows' own. The card sits 180 down its cell, just under the title: a row's
   grid has no group buttons (see_more.HubGridWindow). #}
{% block header_scroll %}
        <animation effect="slide" start="0,0" end="0,{{ vscale(-455) }}" time="200" tween="quadratic" easing="out" reversible="false" condition="Container(101).HasPrevious">Conditional</animation>
        <animation effect="slide" start="0,{{ vscale(-455) }}" end="0,0" time="200" tween="quadratic" easing="out" reversible="false" condition="!Container(101).HasPrevious">Conditional</animation>
{% endblock header_scroll %}
{% block hitrect_y %}{{ vscale(175) }}{% endblock %}
{% block layouts %}
<itemlayout width="272" height="{{ vscale(455) }}">
    {% include "includes/grid_tile_poster.xml.tpl" with focused=False & py=180 %}
</itemlayout>
<focusedlayout width="272" height="{{ vscale(455) }}">
    {% include "includes/grid_tile_poster.xml.tpl" with focused=True & py=180 %}
</focusedlayout>
{% endblock layouts %}
