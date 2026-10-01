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
            {# The count is drawn at font32_title's 32px and zoomed down, so this label has to hold the
               unzoomed text: a label narrower than it cuts it to "1..." before the zoom. 3 digits are
               ~63px (Inter Bold, tabular), which wbg_w + 40 didn't hold on the small grid (wbg_w 20.3:
               60.3 - on request, 2026-10-01). wbg_w + 64 holds them on every caller; the label has no
               background, and its centre - the zoom's centre - is unchanged (posx moved by half the
               extra width), so nothing visible moves. #}
            <control type="label">{# this label uses a nasty hack to get a smaller fitting font size: use a larger font, increase the label size, then zoom it down #}
                <animation effect="zoom" start="{{ count_zoom }}" end="{{ count_zoom }}" time="0" reversible="false" center="auto" condition="true">Conditional</animation>
                <visible>String.IsEmpty({{ itemref|default("ListItem") }}.Property(unwatched.count.large))</visible>
                <posx>{{ xoff - wbg_w - 32 }}</posx>
                <posy>{{ (yoff - 8)|vscale }}</posy>
                <width>{{ wbg_w + 64 }}</width>
                <height>{{ (wbg_h + 16)|vscale }}</height>
                <font>font32_title</font>
                <align>center</align>
                <aligny>center</aligny>
                <textcolor>{{ indicators.textcolor|default("FF000000") }}</textcolor>
                <label>$INFO[{{ itemref|default("ListItem") }}.Property(unwatched.count)]</label>
            </control>
            {# 4+ digits (unwatched.count.large, > 999): same reasoning - ~84px for 4, so wbg_w + 96,
               centred where wbg_w + 56 was (the widened badge's middle, 8px left of the normal one). #}
            <control type="label">{# this label uses a nasty hack to get a smaller fitting font size: use a larger font, increase the label size, then zoom it down #}
                <animation effect="zoom" start="{{ count_zoom }}" end="{{ count_zoom }}" time="0" reversible="false" center="auto" condition="true">Conditional</animation>
                <visible>!String.IsEmpty({{ itemref|default("ListItem") }}.Property(unwatched.count.large))</visible>
                <posx>{{ xoff - wbg_w - 56 }}</posx>
                <posy>{{ (yoff - 8)|vscale }}</posy>
                <width>{{ wbg_w + 96 }}</width>
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