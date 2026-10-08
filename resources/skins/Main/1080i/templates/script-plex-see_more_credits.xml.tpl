{% extends "see_more.xml.tpl" %}
{# A film's or show's every credit (see_more.CreditsGridWindow), Cast or Crew, in the Cast & Crew
   rows' own tile (includes/role_tile.xml.tpl), on request (2026-10-08). The row pitch is 360 -
   309 of card and captions and the gap - which the panel's height depends on (see_more.xml.tpl's
   GRID comment). The card sits 277 down its cell: the panel starts at the screen's top, the
   buttons end at 255, and 22 below them leaves room for the focused card's 104% zoom. #}
{% block layouts %}
<itemlayout width="270" height="{{ vscale(360) }}">
    {% include "includes/role_tile.xml.tpl" with list_id=101 & focused=False & py=277 %}
</itemlayout>
<focusedlayout width="270" height="{{ vscale(360) }}">
    {% include "includes/role_tile.xml.tpl" with list_id=101 & focused=True & py=277 %}
</focusedlayout>
{% endblock layouts %}
