    <!-- Single control, not duplicated: width/height are identical in both poster states, only posx/posy
         shift (poster-shown here; a zero-duration Conditional slide moves it when hide.poster is set), so
         this does the job of the two xoff/yoff-parameterized <visible>-switched copies this used to be
         included as. Title/clearlogo stay duplicated (their own width/height differ per state, which a
         slide animation can't reproduce) - see script-plex-pre_play.xml.tpl for both. -->
    <control type="grouplist">
        <animation effect="slide" end="-373,{{ vscale(30) }}" time="0" condition="!String.IsEmpty(Window.Property(hide.poster))">Conditional</animation>
        <posx>433</posx>
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
            <font>font10</font>
            <align>left</align>
            <textcolor>FFFFFFFF</textcolor>
            <label>$INFO[Window.Property(duration),, &#8226; ]$INFO[Window.Property(info)]$INFO[Window.Property(date), &#8226; ]$INFO[Window.Property(content.rating), &#8226; ]$INFO[Window.Property(studios), &#8226; ]</label>
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
