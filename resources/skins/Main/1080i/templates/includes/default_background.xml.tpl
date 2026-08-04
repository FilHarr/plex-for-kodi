<control type="group">
    <visible>String.IsEmpty(Window.Property(use_solid_background))</visible>
    <control type="image">
        <visible>String.IsEmpty(Window.Property(use_bg_fallback))</visible>
        <posx>0</posx>
        <posy>0</posy>
        <width>1920</width>
        <height>1080</height>
        <texture background="true">script.plex/home/background-fallback_black.png</texture>
    </control>
    <control type="image">
        <visible>!String.IsEmpty(Window.Property(use_bg_fallback))</visible>
        <posx>0</posx>
        <posy>0</posy>
        <width>1920</width>
        <height>1080</height>
        <texture background="true">script.plex/home/background-fallback.png</texture>
        {% include "includes/scale_background.xml.tpl" %}
    </control>
    <control type="image">
        <visible>!String.IsEmpty(Window.Property(dynamic_backgrounds))</visible>
        <posx>0</posx>
        <posy>0</posy>
        <width>1920</width>
        <height>1080</height>
        <texture background="true" fallback="script.plex/home/background-fallback_black.png">$INFO[Window.Property(background_static)]</texture>
        {% include "includes/scale_background.xml.tpl" %}
    </control>
    <control type="image">
        <visible>!String.IsEmpty(Window.Property(dynamic_backgrounds))</visible>
        <posx>0</posx>
        <posy>0</posy>
        <width>1920</width>
        <height>1080</height>
        <fadetime>1000</fadetime>
        <texture background="true">{{ background_source|default("$INFO[Window.Property(background)]") }}</texture>
        {% include "includes/scale_background.xml.tpl" %}
    </control>
    <control type="group">
        <visible>!String.IsEmpty(Window.Property(ultrablur_topleft))</visible>
        <fadetime>1000</fadetime>
        <control type="image">
            <posx>0</posx>
            <posy>0</posy>
            <width>1920</width>
            <height>1080</height>
            <texture>script.plex/gradient-corner-tl.png</texture>
            <colordiffuse>$INFO[Window.Property(ultrablur_topleft)]</colordiffuse>
        </control>
        <control type="image">
            <posx>0</posx>
            <posy>0</posy>
            <width>1920</width>
            <height>1080</height>
            <texture>script.plex/gradient-corner-tr.png</texture>
            <colordiffuse>$INFO[Window.Property(ultrablur_topright)]</colordiffuse>
        </control>
        <control type="image">
            <posx>0</posx>
            <posy>0</posy>
            <width>1920</width>
            <height>1080</height>
            <texture>script.plex/gradient-corner-bl.png</texture>
            <colordiffuse>$INFO[Window.Property(ultrablur_bottomleft)]</colordiffuse>
        </control>
        <control type="image">
            <posx>0</posx>
            <posy>0</posy>
            <width>1920</width>
            <height>1080</height>
            <texture>script.plex/gradient-corner-br.png</texture>
            <colordiffuse>$INFO[Window.Property(ultrablur_bottomright)]</colordiffuse>
        </control>
    </control>
</control>