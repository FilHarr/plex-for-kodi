{% extends "script-plex-subdir.xml.tpl" %}
{# A folder of an Other Videos section (collection.SubDirAr16x9Window): the folder screen with the
   section's own 16:9 library grid tile, three to a row (script-plex-ar16x9.xml.tpl,
   includes/library_tile_ar16x9.xml.tpl), on request (2026-10-09). The same pitch, 388, and the
   same 1160 panel: at 1190 Kodi holds three of these rows as on screen, the third past its foot. #}
{% block panel_height %}1160{% endblock %}
{% block grid_layouts %}
            <itemlayout width="544" height="{{ vscale(388) }}">
                {% include "includes/library_tile_ar16x9.xml.tpl" with focused=False %}
            </itemlayout>
            <focusedlayout width="544" height="{{ vscale(388) }}">
                {% include "includes/library_tile_ar16x9.xml.tpl" with focused=True %}
            </focusedlayout>
{% endblock grid_layouts %}
