    <!-- Two stacked lines, matching official Plex's own grouping, instead of one wide merged line:
         duration/date/content-rating (+ remaining-time/unavailable pill) on line 1, genres + studios on
         line 2. Each field after the first only carries a leading bullet-space prefix (via $INFO's 2nd
         arg, ASCII bullet entity &#8226; - keep any bullets in comments as the entity too, not a literal
         Unicode character: the template writer's write() in lib/templating/core.py compares Python
         len(data) against the UTF-8-encoded file's on-disk byte size, so one literal multibyte character
         anywhere in a .tpl file - comments included - makes that equality permanently false and the
         write times out on every retry), which only renders when that field itself is non-empty - avoids
         both a doubled separator (the old single-line version's trailing-suffix-then-leading-prefix
         pattern produced a double bullet whenever a middle field was empty) and a missing one
         (content.rating had neither here before - reported as "year and content rating joined"). Single
         control, not duplicated: with the poster-shown layout removed there's only one position to tune
         any more. -->
    <control type="grouplist">
        <posx>60</posx>
        <posy>{{ vscale(124) }}</posy>
        <width>708</width>
        <height>{{ vscale(30) }}</height>
        <align>left</align>
        <itemgap>0</itemgap>
        <orientation>horizontal</orientation>
        <usecontrolcoords>true</usecontrolcoords>
        <control type="label">
            <width>auto</width>
            <height>{{ vscale(30) }}</height>
            <font>font10</font>
            <align>left</align>
            <textcolor>FFD2CCCE</textcolor>
            <shadowcolor>66000000</shadowcolor>
            <label>$INFO[Window.Property(duration)]$INFO[Window.Property(date), &#8226; ]$INFO[Window.Property(content.rating), &#8226; ]</label>
        </control>
        <control type="button">
            <visible>!String.IsEmpty(Window.Property(remainingTime))</visible>
            <posx>10</posx>
            <width>auto</width>
            <height>{{ vscale(30) }}</height>
            <font>font10</font>
            <align>center</align>
            <aligny>top</aligny>
            <focusedcolor>FFE5A00D</focusedcolor>
            <textcolor>FFE5A00D</textcolor>
            <textoffsetx>15</textoffsetx>
            <texturefocus colordiffuse="40000000" border="8">script.plex/white-square-rounded-top-padded.png</texturefocus>
            <texturenofocus colordiffuse="40000000" border="8">script.plex/white-square-rounded-top-padded.png</texturenofocus>
            <label>$INFO[Window.Property(remainingTime)]</label>
        </control>
        <control type="button">
            <visible>!String.IsEmpty(Window.Property(unavailable))</visible>
            <posx>10</posx>
            <width>auto</width>
            <height>{{ vscale(30) }}</height>
            <font>font10</font>
            <align>center</align>
            <aligny>top</aligny>
            <focusedcolor>FFFFFFFF</focusedcolor>
            <textcolor>FFFFFFFF</textcolor>
            <textoffsetx>15</textoffsetx>
            <texturefocus colordiffuse="FFAC3223" border="8">script.plex/white-square-rounded-top-padded.png</texturefocus>
            <texturenofocus colordiffuse="FFAC3223" border="8">script.plex/white-square-rounded-top-padded.png</texturenofocus>
            <label>$ADDON[script.plexmod 32312]</label>
        </control>
    </control>
    <control type="label">
        <posx>60</posx>
        <posy>{{ vscale(156) }}</posy>
        <width>708</width>
        <height>{{ vscale(30) }}</height>
        <font>font10</font>
        <align>left</align>
        <textcolor>FFD2CCCE</textcolor>
        <shadowcolor>66000000</shadowcolor>
        <label>$INFO[Window.Property(info)]$INFO[Window.Property(studios), &#8226; ]</label>
    </control>
