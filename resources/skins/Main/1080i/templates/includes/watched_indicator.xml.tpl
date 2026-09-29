    {% if indicators.show %}
    {% with xoff = xoff|default(158) & yoff = yoff|default(0) & uw_size = uw_size|default(32) & wbg_w = wbg_w|default(32) & wbg_h = wbg_h|default(32) & count_zoom = count_zoom|default(40) %}
        <control type="group">
            <visible>!String.IsEmpty({{ itemref|default("ListItem") }}.Property(watched)) + String.IsEmpty({{ itemref|default("ListItem") }}.Property(unwatched.count))</visible>
            <posx>{{ xoff - wbg_w }}</posx>
            <posy>{{ yoff|vscale }}</posy>
            {% if not indicators.hide_aw_bg and not force_nowbg %}
            <control type="image">
                <posx>0</posx>
                <posy>0</posy>
                <width>{{ wbg_w }}</width>
                <height>{{ wbg_h|vscale }}</height>
                <texture diffuse="{{ wbg|default('script.plex/masks/badge-mask-tr.png') }}">script.plex/white-square.png</texture>
                <colordiffuse>{{ indicators.watched_bg|default("CC000000") }}</colordiffuse>
            </control>
            {% endif %}
            <control type="image">
                <posx>{{ wbg_w / 2 - 8 }}</posx>
                <posy>{{ (wbg_h / 2 - 8)|vscale }}</posy>
                <width>16</width>
                <height>{{ vscale(16) }}</height>
                <texture fallback="script.plex/indicators/{{ indicators.assets.watched }}">special://profile/addon_data/script.plexmod/media/{{ indicators.assets.watched }}</texture>
            </control>
        </control>
        {% if with_count %}
        <control type="group">
            <visible>!String.IsEmpty({{ itemref|default("ListItem") }}.Property(unwatched.count))</visible>
            <control type="image">
                <visible>String.IsEmpty({{ itemref|default("ListItem") }}.Property(unwatched.count.large))</visible>
                <posx>{{ xoff - wbg_w }}</posx>
                <posy>{{ yoff|vscale }}</posy>
                <width>{{ wbg_w }}</width>
                <height>{{ wbg_h|vscale }}</height>
                <texture diffuse="{{ wbg|default('script.plex/masks/badge-mask-tr.png') }}">script.plex/white-square.png</texture>
                <colordiffuse>{{ indicators.unwatched_count_bg|default("FFCC7B19") }}</colordiffuse>
            </control>
            <control type="image">
                <visible>!String.IsEmpty({{ itemref|default("ListItem") }}.Property(unwatched.count.large))</visible>
                <posx>{{ xoff - wbg_w - 16 }}</posx>
                <posy>{{ yoff|vscale }}</posy>
                <width>{{ wbg_w + 16 }}</width>
                <height>{{ wbg_h|vscale }}</height>
                <texture diffuse="{{ wbg|default('script.plex/masks/badge-mask-tr.png') }}">script.plex/white-square.png</texture>
                <colordiffuse>{{ indicators.unwatched_count_bg|default("FFCC7B19") }}</colordiffuse>
            </control>
            <control type="label">{# this label uses a nasty hack to get a smaller fitting font size: use a larger font, increase the label size, then zoom it down #}
                <animation effect="zoom" start="{{ count_zoom }}" end="{{ count_zoom }}" time="0" reversible="false" center="auto" condition="true">Conditional</animation>
                <visible>String.IsEmpty({{ itemref|default("ListItem") }}.Property(unwatched.count.large))</visible>
                <posx>{{ xoff - wbg_w - 20 }}</posx>
                <posy>{{ (yoff - 8)|vscale }}</posy>
                <width>{{ wbg_w + 40 }}</width>
                <height>{{ (wbg_h + 16)|vscale }}</height>
                <font>font32_title</font>
                <align>center</align>
                <aligny>center</aligny>
                <textcolor>{{ indicators.textcolor|default("FF000000") }}</textcolor>
                <label>$INFO[{{ itemref|default("ListItem") }}.Property(unwatched.count)]</label>
            </control>
            <control type="label">{# this label uses a nasty hack to get a smaller fitting font size: use a larger font, increase the label size, then zoom it down #}
                <animation effect="zoom" start="{{ count_zoom }}" end="{{ count_zoom }}" time="0" reversible="false" center="auto" condition="true">Conditional</animation>
                <visible>!String.IsEmpty({{ itemref|default("ListItem") }}.Property(unwatched.count.large))</visible>
                <posx>{{ xoff - wbg_w - 36 }}</posx>
                <posy>{{ (yoff - 8)|vscale }}</posy>
                <width>{{ wbg_w + 56 }}</width>
                <height>{{ (wbg_h + 16)|vscale }}</height>
                <font>font32_title</font>
                <align>center</align>
                <aligny>center</aligny>
                <textcolor>{{ indicators.textcolor|default("FF000000") }}</textcolor>
                <label>$INFO[{{ itemref|default("ListItem") }}.Property(unwatched.count)]</label>
            </control>
        </control>
        {% endif %}
    {% endwith %}
{% endif %}