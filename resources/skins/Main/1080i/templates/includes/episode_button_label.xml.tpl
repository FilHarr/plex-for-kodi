<!-- Label-on-focus overlay for an episode button-row icon (script-plex-episodes.xml.tpl's button
     row) - reveals a text label on a pill background when its button has focus. A hidden/zero-width
     grouplist child is excluded from layout/reflow entirely (no reserved width, no itemgap either),
     so this costs nothing unless its own button has focus, at which point the grouplist reflows
     every button after it to the right automatically. Originally prototyped for the Play button
     only (this file's own earlier history) - a separate always-present overlay is needed here
     rather than two focus/nofocus variants of the button sharing one id, since
     Control.HasFocus(own-id) can't gate a control's own visibility.

     Params:
       id - this overlay's own control id
       visible - the Control.HasFocus(...) condition(s) that reveal it (supports "a | b")
       name - icon to redraw, must match one of the button PNGs (e.g. "info")
       label - its own static label markup (usually a single $ADDON string)
       label_suffix_info - optional ListItem property name; when given, appends
         " <bullet> $INFO[Container(400).ListItem.Property(name)]" after label - used for Resume's
         dynamic time-left text, nothing else needs it
       label_width, pill_width, group_width - tuned per label's own text length, see call sites;
         passed as literals rather than computed here since
         ibis's inline math doesn't reliably resolve variables as arithmetic operands (confirmed
         earlier this session - raised "Malformed 'with' tag" on a dotted-path case, not trusted
         since even for plain ones). Formula: pill_width = label_width + 62, group_width =
         label_width + 18 (both derived from the label's own -8 posx and the pill's own -62 posx
         below) - NOT +64/+22 despite the label's own -8/pill's own -62 math implying that: every
         call site's label_width already carries a buffer over its actually-measured text width
         (InterUI.ttf, font10/23px) - originally +2px clipping safety, +2px more on top of that
         (2026-09-04, every call site in this file/episodes/seasons/posters) - so sizing the pill
         directly off label_width would show that buffer as extra empty pill space past the text
         instead of keeping it invisible - confirmed live (pill's right-side gap read visibly
         bigger than the left's). The formula's own +62/+18 nets that buffer back out regardless
         of its size, since it's baked into label_width itself, not added again on top of it.
         ibis's inline math doesn't reliably resolve variables as arithmetic operands (confirmed
         earlier this session - raised "Malformed 'with' tag" on a dotted-path case, not trusted
         since even for plain ones)
       onleft, onright - this overlay's own nav, mirroring its button's own neighbours rather than
         left unset - live-confirmed necessary for the original Play overlay (Kodi's
         usecontrolcoords geometric nav can pick this overlay itself as the nearest control once
         it's reflowed into the list, rather than honouring the real button's own onright) -
         applied to every overlay here for consistency, not individually re-confirmed for each one

     attr/theme must still be in scope from the enclosing themed_button.xml.tpl with-block (icon
     height/theme colours). -->
<control type="group" id="{{ id }}">
    <visible>{{ visible }}</visible>
    <onleft>{{ onleft }}</onleft>
    {% if onright %}<onright>{{ onright }}</onright>{% endif %}
    <width>{{ group_width }}</width>
    <height>{{ attr.height|vscale }}</height>
    <control type="image">
        <!-- -62, not -58: a 10px gap from the icon glyph's own left edge, on request (was 8px) -
             measured per icon (this session), majority (5 of 7 button-row icons, left edge ~-52.5)
             used as the reference rather than Play specifically, same reasoning as the label's own
             -8 posx below - Play is the bigger outlier here though (left edge ~-49.2, a 3.3px gap
             from the majority vs. only ~1.1px on the right side), so it'll read closer to 13px than
             10px - not perfectly split the way the right edge is, flagged rather than chased further
             given the whole spread is still sub-pixel-at-viewing-distance territory. Pill still spans
             icon-through-label as one continuous piece - see the label's own comment. -->
        <posx>-62</posx>
        <posy>{{ vscale(10) }}</posy>
        <width>{{ pill_width }}</width>
        <height>{{ vscale(51) }}</height>
        <!-- 33FFFFFF: matches the library filter/sort dropdowns' own focus background
             (library_posters.xml.tpl) and the sidebar's own focused-item highlight - see the
             original Play overlay's own comment (this file's history) for why, not FFE5A00D. -->
        <texture colordiffuse="33FFFFFF" border="10">script.plex/white-square-rounded.png</texture>
    </control>
    <control type="image">
        <!-- Full 70-wide box, not shrunk to just the glyph - Kodi stretches to fit, it doesn't crop.
             Redrawn here (same texture/colordiffuse as themed_button.xml.tpl's own texturefocus)
             because this whole group draws on top of the real button in z-order - without
             redrawing it, the pill beneath would sit over and dim the real icon. -->
        <posx>-70</posx>
        <posy>0</posy>
        <width>70</width>
        <height>{{ attr.height|vscale }}</height>
        <texture colordiffuse="{{ theme.buttons.focusColor|default('FFE5A00D') }}">{{ theme.assets.buttons.base }}{{ name }}{{ theme.assets.buttons.focusSuffix }}.png</texture>
    </control>
    <control type="label">
        <!-- -8, not the icon glyph's own right edge: a 10px gap, on request (was 5px). Measured per
             icon (this session) rather than assumed from Play alone - Play/Resume actually sit ~1px
             wider (glyph right edge ~-18.6) than the other 5 button-row icons (~-17.5, the majority,
             used here) - -8 splits the difference evenly (9.5px for the majority, 10.6px for
             Play/Resume) rather than favoring either group outright. -->
        <posx>-8</posx>
        <posy>0</posy>
        <width>{{ label_width }}</width>
        <height>{{ attr.height|vscale }}</height>
        <!-- font10, not font12 - max size requested for these pill labels. -->
        <font>font10</font>
        <align>left</align>
        <aligny>center</aligny>
        <textcolor>FFFFFFFF</textcolor>
        <!-- &#8226;, not a literal bullet character: written directly here (not passed through the
             label param) since it's plain unescaped template text, not a variable substitution -
             the pp_meta_row.xml.tpl separator already establishes this is the safe way to get a
             literal bullet into one of these files (see its own comment on why - the template
             writer's byte-length check breaks on a literal multibyte character anywhere in the
             file, comments included). -->
        <label>{{ label }}{% if label_suffix_info %} &#8226; $INFO[Container(400).ListItem.Property({{ label_suffix_info }})]{% endif %}</label>
    </control>
</control>
