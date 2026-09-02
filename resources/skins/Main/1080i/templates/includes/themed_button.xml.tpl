<control type="button" id="{{ id }}">
    {% if visible %}<visible{% if allowhiddenfocus %} allowhiddenfocus="true"{% endif %}>{{ visible }}</visible>{% endif %}
    <hitrect x="{{ hitrect.x|default(40) }}" y="{{ hitrect.y|default(40)|vscale }}" w="{{ hitrect.w|default(96) }}" h="{{ hitrect.h|default(60)|vscale }}" />
    {% if enable %}<enable>{{ enable }}</enable>{% endif %}
    {% if elements %}{% spaceless %} {# simple key/value elements #}
        {% for var, value in elements %}<{{ var }}>{{ value }}</{{ var }}>{% endfor %}{% endspaceless %}
    {% endif %}
    {% if name == "play" and theme.buttons.zoomPlayButton %}
        {# 35,35: the "modern" theme's own box is 70x70 (episodes/seasons/pre_play - see context.py's
           own comment on why); not exact for any other caller's box size, but this was already just
           an approximate center (63,50) tuned for the old 152x121 one, not something every caller
           overrode either. #}
        <animation effect="zoom" start="100" end="124" time="100" center="35,{{ vscale(35) }}" reversible="false" condition="Control.HasFocus({{ id }})">Conditional</animation>
        <animation effect="zoom" start="124" end="100" time="100" center="35,{{ vscale(35) }}" reversible="false" condition="!Control.HasFocus({{ id }})">Conditional</animation>
    {% endif %}
    {% for direction in ("onleft", "onright", "onup", "ondown") %}{% spaceless %}
        {% if resolve("direction") %}<{{ direction }}>{{ resolve("direction") }}</{{ direction }}>{% endif %}
    {% endspaceless %}{% endfor %}
    <posx>{{ attr.posx|default(0) }}</posx>
    <posy>{{ attr.posy|default(0)|vscale }}</posy>
    <width>{{ attr.width }}</width>
    <height>{{ attr.height|vscale }}</height>
    <font>{{ font|default("font12") }}</font>
    <texturefocus{% if theme.buttons.useFocusColor %} colordiffuse="{{ theme.buttons.focusColor|default("FFE5A00D") }}"{% endif %}>{{ theme.assets.buttons.base }}{{ name }}{{ theme.assets.buttons.focusSuffix }}.png</texturefocus>
    <texturenofocus{% if theme.buttons.useNoFocusColor %} colordiffuse="{{ theme.buttons.noFocusColor|default('99FFFFFF') }}"{% endif %}>{{ theme.assets.buttons.base }}{{ name }}.png</texturenofocus>
    <label> </label>
    {% if xml %}{% spaceless %} {# complex elements #}
        {% for element in xml %}
            <{{ element.type}}{% if element.attrs %} {% for name, value in attrs %}{{ name }}="{{ value }}"{% if not loop.is_last %} {% endif %}{% endfor %}{% endif %}>{{ element.value }}</{{ element.type }}>
        {% endfor %}
    {% endspaceless %}{% endif %}
</control>