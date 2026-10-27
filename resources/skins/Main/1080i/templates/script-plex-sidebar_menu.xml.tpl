{% extends "script-plex-settings_select_dialog.xml.tpl" %}
{# A sidebar section's menu (dialog.SidebarMenuDialog): the option picker, without its zorder. 101 keeps a picker above
   the video player's OSD, which this menu never opens over, and put this over what its rows open over it - Manage
   recommended rows (no zorder) and Kodi's folder browser - so they opened behind it. With none, they stack in the
   order they open, as over the add-on's Settings (script-plex-settings_picker.xml.tpl). #}
{% block headers %}{% endblock %}
