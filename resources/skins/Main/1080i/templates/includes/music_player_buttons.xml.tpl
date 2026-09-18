{# The music player's / current-playlist window's transport row, in the treatment every other
   button row has (pre_play/seasons/episodes/artist/album/library grids): theme.music_player's
   70x70 icon boxes and hitrects (context.py), themed_button.xml.tpl's own textures and colours,
   and a label-on-focus pill per button (episode_button_label.xml.tpl - see that file for the
   width formula; every label_width here is PIL-measured at font10 + 4, pill = +62, group = +18).
   Prev/next/queue/more go through themed_button itself; the rest can't (a 3-state icon,
   togglebuttons, an onclick) and are written out to its box/hitrect/texture recipe instead.
   Prev/next keep their disabled twins (424/419, 25% alpha, enable=false) in place of hiding, so
   the row never reflows on a track change; the twins can't take focus, so they get no overlays.
   Overlay ids are 451-464; the row's own ids are unchanged, so the Python side (musicplayer.py /
   currentplaylist.py) needs nothing.

   Overlay nav follows the recipe (onleft = own button, onright = the next one); where the next
   one is a shown/hidden pair, onright_cond picks the visible member - for prev/next that's the
   enabled one, else the disabled twin is skipped over since it can't take focus anyway.

   Shared with the current-playlist window unchanged, apart from the queue button's own onclick
   (see its comment). "onup 100" on repeat/remote-shuffle is that window's queue list; in the
   music player there's no 100 and it falls through to the grouplist's own onup. #}
{% with attr = theme.music_player.buttons & template = "includes/themed_button.xml.tpl" & hitrect = theme.music_player.buttons_hitrect & ol = "includes/episode_button_label.xml.tpl" %}

{# REPEAT - cycles off -> all -> one -> off (repeatButtonClicked(), musicplayer.py /
   currentplaylist.py, both for Kodi's own PlayerControl(Repeat) and the remote-queue path).
   Unfocused it shows its own state, on-states in the focus gold; focused, one of the three
   overlays below redraws the current icon and labels the NEXT state - what a click will do -
   with the same state tests as the images, made mutually exclusive. #}
<control type="group" id="421">
    <width>{{ attr.width }}</width>
    <height>{{ attr.height|vscale }}</height>
    <control type="button" id="401">
        <hitrect x="{{ hitrect.x }}" y="{{ hitrect.y|vscale }}" w="{{ hitrect.w }}" h="{{ hitrect.h|vscale }}" />
        <posx>0</posx>
        <posy>0</posy>
        <width>{{ attr.width }}</width>
        <height>{{ attr.height|vscale }}</height>
        {# Explicit nav, unlike the row's direct children: a grouplist wires left/right (and copies
           its own up/down) onto its direct children only (CGUIControlGroupList::AddControl), and
           this button sits inside group 421. Left is a dead stop (noop), not the old wrap to 411;
           right picks whichever shuffle is showing; up is the queue window's list (100) where it
           exists, else what the grouplist's own onup would have given. #}
        <onup condition="Control.IsVisible(100)">100</onup>
        <onup>500</onup>
        <onleft>noop</onleft>
        <onright condition="String.IsEmpty(Window.Property(pq.isremote))">402</onright>
        <onright>422</onright>
        <font>font12</font>
        <texturefocus>-</texturefocus>
        <texturenofocus>-</texturenofocus>
        <label> </label>
    </control>
    <control type="group">
        <visible>!Control.HasFocus(401)</visible>
        <control type="image">
            <visible>!Playlist.IsRepeatOne + !Playlist.IsRepeat + String.IsEmpty(Window.Property(pq.repeat))</visible>
            <posx>0</posx>
            <posy>0</posy>
            <width>{{ attr.width }}</width>
            <height>{{ attr.height|vscale }}</height>
            <texture{% if theme.buttons.useNoFocusColor %} colordiffuse="{{ theme.buttons.noFocusColor|default('99FFFFFF') }}"{% endif %}>{{ theme.assets.buttons.base }}repeat.png</texture>
        </control>
        <control type="image">
            <visible>!Playlist.IsRepeatOne + [Playlist.IsRepeat | !String.IsEmpty(Window.Property(pq.repeat))]</visible>
            <posx>0</posx>
            <posy>0</posy>
            <width>{{ attr.width }}</width>
            <height>{{ attr.height|vscale }}</height>
            <texture colordiffuse="{{ theme.buttons.focusColor|default('FFE5A00D') }}">{{ theme.assets.buttons.base }}repeat.png</texture>
        </control>
        <control type="image">
            <visible>Playlist.IsRepeatOne</visible>
            <posx>0</posx>
            <posy>0</posy>
            <width>{{ attr.width }}</width>
            <height>{{ attr.height|vscale }}</height>
            <texture colordiffuse="{{ theme.buttons.focusColor|default('FFE5A00D') }}">{{ theme.assets.buttons.base }}repeat-one.png</texture>
        </control>
    </control>
</control>
{# off -> "Repeat all" #}
{% include ol with id=451 & visible="Control.HasFocus(401) + !Playlist.IsRepeatOne + !Playlist.IsRepeat + String.IsEmpty(Window.Property(pq.repeat))" & name="repeat" &
    label="$ADDON[script.plexmod 35082]" & label_suffix_info="" &
    label_width=110 & pill_width=172 & group_width=128 &
    onleft=401 & onright_cond="String.IsEmpty(Window.Property(pq.isremote))" & onright=402 & onright_else=422
%}
{# all -> "Repeat one" #}
{% include ol with id=452 & visible="Control.HasFocus(401) + !Playlist.IsRepeatOne + [Playlist.IsRepeat | !String.IsEmpty(Window.Property(pq.repeat))]" & name="repeat" &
    label="$ADDON[script.plexmod 35083]" & label_suffix_info="" &
    label_width=125 & pill_width=187 & group_width=143 &
    onleft=401 & onright_cond="String.IsEmpty(Window.Property(pq.isremote))" & onright=402 & onright_else=422
%}
{# one -> "Repeat off" #}
{% include ol with id=462 & visible="Control.HasFocus(401) + Playlist.IsRepeatOne" & name="repeat-one" &
    label="$ADDON[script.plexmod 35084]" & label_suffix_info="" &
    label_width=116 & pill_width=178 & group_width=134 &
    onleft=401 & onright_cond="String.IsEmpty(Window.Property(pq.isremote))" & onright=402 & onright_else=422
%}

{# SHUFFLE - local Kodi playlist: a togglebutton on Playlist.IsRandom, on-state in the focus
   gold. Two overlays, labelling what a click will do. #}
<control type="togglebutton" id="402">
    <visible>String.IsEmpty(Window.Property(pq.isremote))</visible>
    <hitrect x="{{ hitrect.x }}" y="{{ hitrect.y|vscale }}" w="{{ hitrect.w }}" h="{{ hitrect.h|vscale }}" />
    <width>{{ attr.width }}</width>
    <height>{{ attr.height|vscale }}</height>
    <font>font12</font>
    {# No focus textures of its own - the overlay redraws the focused icon, see themed_button.xml.tpl's
       own overlay param for why drawing it here too made it look bolder. #}
    <texturefocus>-</texturefocus>
    <texturenofocus{% if theme.buttons.useNoFocusColor %} colordiffuse="{{ theme.buttons.noFocusColor|default('99FFFFFF') }}"{% endif %}>{{ theme.assets.buttons.base }}shuffle.png</texturenofocus>
    <usealttexture>Playlist.IsRandom</usealttexture>
    <alttexturefocus>-</alttexturefocus>
    <alttexturenofocus colordiffuse="{{ theme.buttons.focusColor|default('FFE5A00D') }}">{{ theme.assets.buttons.base }}shuffle.png</alttexturenofocus>
    <onclick>PlayerControl(RandomOn)</onclick>
    <altclick>PlayerControl(RandomOff)</altclick>
    <label> </label>
</control>
{% include ol with id=453 & visible="Control.HasFocus(402) + !Playlist.IsRandom" & name="shuffle" &
    label="$ADDON[script.plexmod 35080]" & label_suffix_info="" &
    label_width=117 & pill_width=179 & group_width=135 &
    onleft=402 & onright_cond="MusicPlayer.HasPrevious | !String.IsEmpty(Window.Property(pq.hasprev))" & onright=404 & onright_else=406
%}
{% include ol with id=463 & visible="Control.HasFocus(402) + Playlist.IsRandom" & name="shuffle" &
    label="$ADDON[script.plexmod 35081]" & label_suffix_info="" &
    label_width=121 & pill_width=183 & group_width=139 &
    onleft=402 & onright_cond="MusicPlayer.HasPrevious | !String.IsEmpty(Window.Property(pq.hasprev))" & onright=404 & onright_else=406
%}

{# SHUFFLE - remote Plex play queue: state from pq.shuffled (Python toggles it, setShuffle()).
   Same unfocused-only state images as repeat, on-state in the focus gold; two overlays
   labelling what a click will do. #}
<control type="group" id="432">
    <visible>!String.IsEmpty(Window.Property(pq.isremote))</visible>
    <width>{{ attr.width }}</width>
    <height>{{ attr.height|vscale }}</height>
    <control type="button" id="422">
        <hitrect x="{{ hitrect.x }}" y="{{ hitrect.y|vscale }}" w="{{ hitrect.w }}" h="{{ hitrect.h|vscale }}" />
        <posx>0</posx>
        <posy>0</posy>
        <width>{{ attr.width }}</width>
        <height>{{ attr.height|vscale }}</height>
        {# Nested in group 432, so explicit nav for the same reason as repeat's 401 above. #}
        <onup condition="Control.IsVisible(100)">100</onup>
        <onup>500</onup>
        <onleft>401</onleft>
        <onright condition="MusicPlayer.HasPrevious | !String.IsEmpty(Window.Property(pq.hasprev))">404</onright>
        <onright>406</onright>
        <font>font12</font>
        <texturefocus>-</texturefocus>
        <texturenofocus>-</texturenofocus>
        <label> </label>
    </control>
    <control type="group">
        <visible>!Control.HasFocus(422)</visible>
        <control type="image">
            <visible>String.IsEmpty(Window.Property(pq.shuffled))</visible>
            <posx>0</posx>
            <posy>0</posy>
            <width>{{ attr.width }}</width>
            <height>{{ attr.height|vscale }}</height>
            <texture{% if theme.buttons.useNoFocusColor %} colordiffuse="{{ theme.buttons.noFocusColor|default('99FFFFFF') }}"{% endif %}>{{ theme.assets.buttons.base }}shuffle.png</texture>
        </control>
        <control type="image">
            <visible>!String.IsEmpty(Window.Property(pq.shuffled))</visible>
            <posx>0</posx>
            <posy>0</posy>
            <width>{{ attr.width }}</width>
            <height>{{ attr.height|vscale }}</height>
            <texture colordiffuse="{{ theme.buttons.focusColor|default('FFE5A00D') }}">{{ theme.assets.buttons.base }}shuffle.png</texture>
        </control>
    </control>
</control>
{% include ol with id=454 & visible="Control.HasFocus(422) + String.IsEmpty(Window.Property(pq.shuffled))" & name="shuffle" &
    label="$ADDON[script.plexmod 35080]" & label_suffix_info="" &
    label_width=117 & pill_width=179 & group_width=135 &
    onleft=422 & onright_cond="MusicPlayer.HasPrevious | !String.IsEmpty(Window.Property(pq.hasprev))" & onright=404 & onright_else=406
%}
{% include ol with id=464 & visible="Control.HasFocus(422) + !String.IsEmpty(Window.Property(pq.shuffled))" & name="shuffle" &
    label="$ADDON[script.plexmod 35081]" & label_suffix_info="" &
    label_width=121 & pill_width=183 & group_width=139 &
    onleft=422 & onright_cond="MusicPlayer.HasPrevious | !String.IsEmpty(Window.Property(pq.hasprev))" & onright=404 & onright_else=406
%}

{# PREVIOUS, and its disabled twin. previous.png is next.png mirrored (added with this row's
   restyle, modern set only) - the row used to flipx next.png here, but the overlay redraws its
   icon by name, unflipped, so the flipped-at-render form can't be used by the pill. #}
{% include template with name="previous" & id=404 & overlay=True & visible="MusicPlayer.HasPrevious | !String.IsEmpty(Window.Property(pq.hasprev))" %}
{% include ol with id=455 & visible="Control.HasFocus(404)" & name="previous" &
    label="$ADDON[script.plexmod 32438]" & label_suffix_info="" &
    label_width=97 & pill_width=159 & group_width=115 &
    onleft=404 & onright=406
%}
<control type="button" id="424">
    <enable>false</enable>
    <visible>!MusicPlayer.HasPrevious + String.IsEmpty(Window.Property(pq.hasprev))</visible>
    <width>{{ attr.width }}</width>
    <height>{{ attr.height|vscale }}</height>
    <font>font12</font>
    <texturefocus colordiffuse="40FFFFFF">{{ theme.assets.buttons.base }}previous.png</texturefocus>
    <texturenofocus colordiffuse="40FFFFFF">{{ theme.assets.buttons.base }}previous.png</texturenofocus>
    <label> </label>
</control>

{# PLAY/PAUSE - a togglebutton on the player state, with themed_button's own Play zoom (35,35 is
   the centre of its 70x70 box, as there). Two overlays, one per state, so the pill's icon and
   label follow the button. #}
<control type="togglebutton" id="406">
    <hitrect x="{{ hitrect.x }}" y="{{ hitrect.y|vscale }}" w="{{ hitrect.w }}" h="{{ hitrect.h|vscale }}" />
    {% if theme.buttons.zoomPlayButton %}
    <animation effect="zoom" start="100" end="124" time="100" center="35,{{ vscale(35) }}" reversible="false" condition="Control.HasFocus(406)">Conditional</animation>
    <animation effect="zoom" start="124" end="100" time="100" center="35,{{ vscale(35) }}" reversible="false" condition="!Control.HasFocus(406)">Conditional</animation>
    {% endif %}
    <width>{{ attr.width }}</width>
    <height>{{ attr.height|vscale }}</height>
    <font>font12</font>
    <texturefocus>-</texturefocus>
    <texturenofocus{% if theme.buttons.useNoFocusColor %} colordiffuse="{{ theme.buttons.noFocusColor|default('99FFFFFF') }}"{% endif %}>{{ theme.assets.buttons.base }}pause.png</texturenofocus>
    <usealttexture>Player.Paused | Player.Forwarding | Player.Rewinding</usealttexture>
    <alttexturefocus>-</alttexturefocus>
    <alttexturenofocus{% if theme.buttons.useNoFocusColor %} colordiffuse="{{ theme.buttons.noFocusColor|default('99FFFFFF') }}"{% endif %}>{{ theme.assets.buttons.base }}play.png</alttexturenofocus>
    <onclick>PlayerControl(Play)</onclick>
    <label> </label>
</control>
{% include ol with id=456 & visible="Control.HasFocus(406) + !Player.Paused + !Player.Forwarding + !Player.Rewinding" & name="pause" &
    label="$ADDON[script.plexmod 35076]" & label_suffix_info="" &
    label_width=70 & pill_width=132 & group_width=88 &
    onleft=406 & onright=407
%}
{% include ol with id=457 & visible="Control.HasFocus(406) + [Player.Paused | Player.Forwarding | Player.Rewinding]" & name="play" &
    label="$ADDON[script.plexmod 33020]" & label_suffix_info="" &
    label_width=50 & pill_width=112 & group_width=68 &
    onleft=406 & onright=407
%}

{# STOP #}
<control type="button" id="407">
    <hitrect x="{{ hitrect.x }}" y="{{ hitrect.y|vscale }}" w="{{ hitrect.w }}" h="{{ hitrect.h|vscale }}" />
    <width>{{ attr.width }}</width>
    <height>{{ attr.height|vscale }}</height>
    <font>font12</font>
    <texturefocus>-</texturefocus>
    <texturenofocus{% if theme.buttons.useNoFocusColor %} colordiffuse="{{ theme.buttons.noFocusColor|default('99FFFFFF') }}"{% endif %}>{{ theme.assets.buttons.base }}stop.png</texturenofocus>
    <onclick>PlayerControl(Stop)</onclick>
    <label> </label>
</control>
{% include ol with id=458 & visible="Control.HasFocus(407)" & name="stop" &
    label="$ADDON[script.plexmod 35077]" & label_suffix_info="" &
    label_width=54 & pill_width=116 & group_width=72 &
    onleft=407 & onright_cond="MusicPlayer.HasNext | !String.IsEmpty(Window.Property(pq.hasnext))" & onright=409 & onright_else=410
%}

{# NEXT, and its disabled twin. #}
{% include template with name="next" & id=409 & overlay=True & visible="MusicPlayer.HasNext | !String.IsEmpty(Window.Property(pq.hasnext))" %}
{% include ol with id=459 & visible="Control.HasFocus(409)" & name="next" &
    label="$ADDON[script.plexmod 35078]" & label_suffix_info="" &
    label_width=55 & pill_width=117 & group_width=73 &
    onleft=409 & onright=410
%}
<control type="button" id="419">
    <enable>false</enable>
    <visible>!MusicPlayer.HasNext + String.IsEmpty(Window.Property(pq.hasnext))</visible>
    <width>{{ attr.width }}</width>
    <height>{{ attr.height|vscale }}</height>
    <font>font12</font>
    <texturefocus colordiffuse="40FFFFFF">{{ theme.assets.buttons.base }}next.png</texturefocus>
    <texturenofocus colordiffuse="40FFFFFF">{{ theme.assets.buttons.base }}next.png</texturenofocus>
    <label> </label>
</control>

{# PLAY QUEUE. "Close" is no builtin: Kodi's action translator maps it to ACTION_NAV_BACK, sent
   to whichever window is current. In the current-playlist window that IS this button's
   implementation - Back closes it, returning to the player. In the music player the queue is
   opened by Python instead (onClick -> showPlaylist(), musicplayer.py), and the same Back would
   close the player underneath it; it was only ever dropped by that window's not-current-window
   guard in onAction(), i.e. by winning a race. Undefined is falsy here, so the current-playlist
   window keeps the tag unchanged. #}
<control type="button" id="410">
    <hitrect x="{{ hitrect.x }}" y="{{ hitrect.y|vscale }}" w="{{ hitrect.w }}" h="{{ hitrect.h|vscale }}" />
    <width>{{ attr.width }}</width>
    <height>{{ attr.height|vscale }}</height>
    <font>font12</font>
    <texturefocus>-</texturefocus>
    <texturenofocus{% if theme.buttons.useNoFocusColor %} colordiffuse="{{ theme.buttons.noFocusColor|default('99FFFFFF') }}"{% endif %}>{{ theme.assets.buttons.base }}pqueue.png</texturenofocus>
    <label> </label>
    {% if not music_player %}<onclick>Close</onclick>{% endif %}
</control>
{% include ol with id=460 & visible="Control.HasFocus(410)" & name="pqueue" &
    label="$ADDON[script.plexmod 35079]" & label_suffix_info="" &
    label_width=124 & pill_width=186 & group_width=142 &
    onleft=410 & onright=411
%}

{# MORE - last in the row, so no onright on its overlay. #}
{% include template with name="more" & id=411 & overlay=True %}
{% include ol with id=461 & visible="Control.HasFocus(411)" & name="more" &
    label="$ADDON[script.plexmod 32307]" & label_suffix_info="" &
    label_width=60 & pill_width=122 & group_width=78 &
    onleft=411
%}

{% endwith %}
