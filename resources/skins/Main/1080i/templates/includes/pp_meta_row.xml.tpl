    <!-- Single line: episode code, duration, date, genres, content rating (+ remaining-time/unavailable
         pill), font20 (on request, 2026-10-01 - after font_flag and font8, both 18px). Used to be two stacked lines matching official Plex's own grouping, with
         genres + studios on a second line below this one - dropped, this is the only line now.
         Each field is its own auto-width label, 23px apart via an inner grouplist's itemgap, rather
         than one label joined with bullet separators (on request, 2026-10-01 - 21px, what the
         space-bullet-space separator measured in font_flag, then 2px more by eye at font20). A grouplist skips hidden controls, so
         an empty field takes no room and leaves no gap: no separator can lead, trail or double up,
         which the joined label needed $INFO prefixes and a second, no-duration copy to avoid. The
         inner grouplist reports its content's width to the outer one, so the pills after it keep
         their own spacing (posx) - a negative posx to cancel a shared itemgap broke the time-left
         pill live. The time-left pill's posx matches the fields' gap (on request).
         episode.code is "S{season} E{episode}" for an episode on the hub rows (setHeroInfo(),
         library_hubs.py), empty otherwise. date is the item's year normally, the air or release
         date ("1 Sep 2026") for an episode or album. (Keep any non-ASCII character in a .tpl as an
         entity, comments included: lib/templating/core.py's write() compares len(data) against the
         UTF-8 file's byte size, so one multibyte character makes every write time out.) -->
    <!-- Unavailable replaces the whole row (on request, 2026-09-25): with it set, the text and the
         time-left pill are hidden and the red pill shows alone, flush left (posx 0, not the 23px gap it
         keeps from the text otherwise). Everything together overflowed the row's 708px - the
         unavailable pill was cut in half - and the rest isn't much use for an item that can't play. -->
    <control type="grouplist">
        <!-- 61, not the old 60: reaches absolute x=113 (host group's own posx=52 + this 61), matching
             the shared baseline every includer (Seasons/Pre-play/Recommended) and Episodes' own inline
             copy of this row now use - see script-plex-episodes.xml.tpl's header block comment. -->
        <posx>61</posx>
        <posy>{{ vscale(175) }}</posy>
        <width>708</width>
        <height>{{ vscale(30) }}</height>
        <align>left</align>
        <itemgap>0</itemgap>
        <orientation>horizontal</orientation>
        <usecontrolcoords>true</usecontrolcoords>
        <control type="grouplist">
            <width>708</width>
            <height>{{ vscale(30) }}</height>
            <itemgap>23</itemgap>
            <orientation>horizontal</orientation>
            {% for prop in ('episode.code', 'duration', 'date', 'genres.short', 'content.rating') %}
            <control type="label">
                <visible>String.IsEmpty(Window.Property(unavailable)) + !String.IsEmpty(Window.Property({{ prop }}))</visible>
                <width>auto</width>
                <height>{{ vscale(30) }}</height>
                <font>font20</font>
                <align>left</align>
                <textcolor>FFD2CCCE</textcolor>
                <shadowcolor>66000000</shadowcolor>
                <label>$INFO[Window.Property({{ prop }})]</label>
            </control>
            {% endfor %}
        </control>
        <control type="button">
            <visible>!String.IsEmpty(Window.Property(remainingTime)) + String.IsEmpty(Window.Property(unavailable))</visible>
            <!-- The fields' own 23px gap (the inner grouplist's itemgap above). -->
            <posx>23</posx>
            <width>auto</width>
            <!-- 30 tall on white-square-rounded.png (on request, 2026-10-01): the pill fills its box,
                 centred 15px down - on font20's digits, whose middle sits 14.9px below the text top
                 (Inter at 20px) - with ~8px clear above and below them. Height follows the font: the
                 centre of the digits is at 0.745 x the size below the text top, so 18px wanted 27.
                 Was 30 on white-square-rounded-top-padded (the same corners, 3px clear at the top, so
                 showing from 3 to 30): centred on font10's digits (17.1px down). The box stays at the
                 row's top so its text, drawn from the box's top, stays level with the fields; moving
                 the box up instead moved the text with it. textoffsetx 10, not 15, for the smaller
                 text. -->
            <height>{{ vscale(30) }}</height>
            <font>font20</font>
            <align>center</align>
            <aligny>top</aligny>
            <focusedcolor>FFE5A00D</focusedcolor>
            <textcolor>FFE5A00D</textcolor>
            <textoffsetx>10</textoffsetx>
            <texturefocus colordiffuse="40000000" border="8">script.plex/white-square-rounded.png</texturefocus>
            <texturenofocus colordiffuse="40000000" border="8">script.plex/white-square-rounded.png</texturenofocus>
            <label>$INFO[Window.Property(remainingTime)]</label>
        </control>
        <control type="button">
            <visible>!String.IsEmpty(Window.Property(unavailable))</visible>
            <posx>0</posx>
            <width>auto</width>
            <!-- 30, white-square-rounded.png, textoffsetx 10: as the time-left pill above. -->
            <height>{{ vscale(30) }}</height>
            <font>font20</font>
            <align>center</align>
            <aligny>top</aligny>
            <focusedcolor>FFFFFFFF</focusedcolor>
            <textcolor>FFFFFFFF</textcolor>
            <textoffsetx>10</textoffsetx>
            <texturefocus colordiffuse="FFAC3223" border="8">script.plex/white-square-rounded.png</texturefocus>
            <texturenofocus colordiffuse="FFAC3223" border="8">script.plex/white-square-rounded.png</texturenofocus>
            <label>$ADDON[script.plexmod 32312]</label>
        </control>
    </control>
