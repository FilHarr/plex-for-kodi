    <!-- Single control, not duplicated: width/height are identical in both poster states, only posx/posy
         shift, so a zero-duration Conditional slide does the job of the <visible>-switched pair used where
         size also changes (title/clearlogo) - see includes/pp_meta_row.xml.tpl's identical treatment on
         Pre-play, which this mirrors (same content Seasons already showed here; not Pre-play's own fields -
         Seasons' rating-stars moved into the ratings box instead, matching Pre-play's content split there). -->
    <control type="grouplist">
        <!-- -316, not -373: the poster-shown base posx moved from 433 to 376 (Seasons' poster shrink -
             see script-plex-seasons.xml.tpl's own poster group comment), so the slide distance back to
             the poster-hidden x=60 shrank by the same 57 (376-60=316). -->
        <animation effect="slide" end="-316,{{ vscale(30) }}" time="0" condition="!String.IsEmpty(Window.Property(hide.poster))">Conditional</animation>
        <posx>376</posx>
        <posy>{{ vscale(126) }}</posy>
        <width>1360</width>
        <height>{{ vscale(30) }}</height>
        <align>left</align>
        <itemgap>0</itemgap>
        <orientation>horizontal</orientation>
        <usecontrolcoords>true</usecontrolcoords>
        <control type="label">
            <width>auto</width>
            <height>{{ vscale(30) }}</height>
            <font>font12</font>
            <align>left</align>
            <textcolor>FFFFFFFF</textcolor>
            <label>$INFO[Window.Property(duration)]$INFO[Window.Property(info), &#8226; ]$INFO[Window.Property(date), &#8226; ]$INFO[Window.Property(content.rating), &#8226; ]$INFO[Window.Property(studio), &#8226; ]</label>
        </control>
    </control>
