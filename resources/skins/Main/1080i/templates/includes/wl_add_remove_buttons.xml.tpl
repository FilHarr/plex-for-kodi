{# The watchlist pair, 308/309 on every screen (WatchlistUtilsMixin.WL_BTN_STATE_*). skip_children_card: Episodes'
   button row, where it's a skipChildren show's card only (script-plex-episodes.xml.tpl). #}
{% if skip_children_card %}
{% include template with name="watchlist" & id=308 & overlay=True & visible="!String.IsEmpty(Window.Property(watchlist_enabled)) + String.IsEmpty(Window.Property(is_watchlisted)) + !String.IsEmpty(Container(400).ListItem.Property(is.skip.children.card))" %}
{% include template with name="watchlisted" & id=309 & overlay=True & visible="!String.IsEmpty(Window.Property(watchlist_enabled)) + !String.IsEmpty(Window.Property(is_watchlisted)) + !String.IsEmpty(Container(400).ListItem.Property(is.skip.children.card))" %}
{% else %}
{% include template with name="watchlist" & id=308 & overlay=True & visible="!String.IsEmpty(Window.Property(watchlist_enabled)) + String.IsEmpty(Window.Property(is_watchlisted))" %}
{% include template with name="watchlisted" & id=309 & overlay=True & visible="!String.IsEmpty(Window.Property(watchlist_enabled)) + !String.IsEmpty(Window.Property(is_watchlisted))" %}
{% endif %}
