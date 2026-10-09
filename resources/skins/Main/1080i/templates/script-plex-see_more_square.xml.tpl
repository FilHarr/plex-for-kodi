{% extends "see_more.xml.tpl" %}
{# A row's every item in the Recommended square card with up to three caption lines (albums,
   artists, playlists, photos). Row pitch 380, the credits grid's: 3 + 240 + 3 lines is 332.
   Cell 272 wide, the rows' own. The card sits 180 down its cell, just under the title: a row's
   grid has no group buttons (see_more.HubGridWindow). #}
{% block header_scroll %}
        <animation effect="slide" start="0,0" end="0,{{ vscale(-380) }}" time="200" tween="quadratic" easing="out" reversible="false" condition="Container(101).HasPrevious">Conditional</animation>
        <animation effect="slide" start="0,{{ vscale(-380) }}" end="0,0" time="200" tween="quadratic" easing="out" reversible="false" condition="!Container(101).HasPrevious">Conditional</animation>
{% endblock header_scroll %}
{% block hitrect_y %}{{ vscale(175) }}{% endblock %}
{% block layouts %}
<itemlayout width="272" height="{{ vscale(380) }}">
    {% include "includes/grid_tile_square.xml.tpl" with focused=False & py=180 %}
</itemlayout>
<focusedlayout width="272" height="{{ vscale(380) }}">
    {% include "includes/grid_tile_square.xml.tpl" with focused=True & py=180 %}
</focusedlayout>
{% endblock layouts %}
