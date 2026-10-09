{% extends "see_more.xml.tpl" %}
{# A film's or show's every credit (see_more.CreditsGridWindow), Cast or Crew, in the Cast & Crew
   rows' own tile (includes/role_tile.xml.tpl), on request (2026-10-08). The card sits 277 down its
   cell: the panel starts at the screen's top, the buttons end at 255, and 22 below them leaves room
   for the focused card's 104% zoom. Row pitch 380 - 309 of card and captions, then the gap - the
   least over 1139 / 3 (see_more.xml.tpl), so the panel holds two whole rows. #}
{% block header_scroll %}
        <animation effect="slide" start="0,0" end="0,{{ vscale(-380) }}" time="200" tween="quadratic" easing="out" reversible="false" condition="Container(101).HasPrevious">Conditional</animation>
        <animation effect="slide" start="0,{{ vscale(-380) }}" end="0,0" time="200" tween="quadratic" easing="out" reversible="false" condition="!Container(101).HasPrevious">Conditional</animation>
{% endblock header_scroll %}
{% block layouts %}
<itemlayout width="270" height="{{ vscale(380) }}">
    {% include "includes/role_tile.xml.tpl" with list_id=101 & focused=False & py=277 %}
</itemlayout>
<focusedlayout width="270" height="{{ vscale(380) }}">
    {% include "includes/role_tile.xml.tpl" with list_id=101 & focused=True & py=277 %}
</focusedlayout>
{% endblock layouts %}
