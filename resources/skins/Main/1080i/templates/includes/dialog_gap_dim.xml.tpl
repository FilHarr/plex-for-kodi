<!-- The settings and pickers' 30% full-screen dim (includes/option_card_frame.xml.tpl), held on the screen while
     one dialog hands over to the next: More settings, or a sidebar section's menu, closes before the screen runs
     the action chosen from it, which may open a confirm box, a picker or Manage recommended rows (the card list) -
     without this the screen showed undimmed in between, a flash.
     Held from the action's choice (playersettings.py) until the next window or dialog initialises or the
     action is done (kodigui.holdDialogDim()); hidden while one of those dialogs shows its own, so the two never
     stack. A global property, as nav_hidden: the dialogs above this window are what's visible. -->
<control type="image">
    <visible>!String.IsEmpty(Window(10000).Property(script.plex.dialog_dim)) + !Window.IsVisible(script-plex-video_settings_dialog.xml) + !Window.IsVisible(script-plex-settings_select_dialog.xml) + !Window.IsVisible(script-plex-options_dialog.xml) + !Window.IsVisible(script-plex-card_list.xml) + !Window.IsVisible(script-plex-user_menu.xml)</visible>
    <posx>0</posx>
    <posy>0</posy>
    <width>1920</width>
    <height>1080</height>
    <texture>script.plex/white-square.png</texture>
    <colordiffuse>4D000000</colordiffuse>
</control>
