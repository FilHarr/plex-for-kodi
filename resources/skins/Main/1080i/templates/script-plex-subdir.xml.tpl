{% extends "default.xml.tpl" %}
{# Bounded grid view for a folder browsed within a section (subDir) - see lib/windows/collection.py's
   BoundedGridWindow/SubDirWindow. Same shape as script-plex-collection.xml.tpl minus the info panel
   (a folder has no comparable metadata to a Collection's summary/childCount/clearLogo) - see
   hashed-orbiting-pizza.md's Phase 4. With no info panel pushing the grid down, this keeps
   script-plex-posters.xml.tpl's own untouched production panel numbers (height/hitrect/itemlayout-
   posy) rather than script-plex-collection.xml.tpl's compressed, 1-row-trigger ones - those were
   specifically compensating for the info panel's vertical cost, which doesn't apply here. Retune
   live if this doesn't hold once tested against a real deep folder tree. #}
{% block header %}
    {{ super() }}
    {% include "includes/sidebar.xml.tpl" %}
    <!-- Declared last so groups 802/901 draw on top - see script-plex-pre_play.xml.tpl's own copy
         of this include for the full reasoning (this window is one of the seven real hosted-shell
         types too, same _sidebarTarget()-aware Python side, same onClick forwarding). -->
    {% include "includes/sidebar_dropdowns.xml.tpl" %}
{% endblock header %}
{% block content %}
<control type="group" id="50">
    <!-- Slide right while the sidebar rail is expanded (focused), matching every other
         sidebar-opted-in window (Library/Pre-play/Episodes/Collection). -->
    <animation effect="slide" end="220,0" time="200" tween="sine" easing="inout" condition="ControlGroup(9000).HasFocus(0)">Conditional</animation>
    <posx>60</posx>
    <posy>{{ vscale(155) }}</posy>
    <defaultcontrol>101</defaultcontrol>

    <!-- GRID ################################################## -->
    <control type="group" id="100">
        <visible>Integer.IsGreater(Container(101).NumItems,0) + String.IsEmpty(Window.Property(drawing))</visible>
        <defaultcontrol>101</defaultcontrol>
        <posx>-5</posx>
        <posy>0</posy>
        <width>1920</width>
        <height>1080</height>
        {# Lifted from script-plex-posters.xml.tpl's own panel/itemlayout/focusedlayout
           (script-plex-posters.xml.tpl:17-219), same as script-plex-collection.xml.tpl. onup/
           onright to the dropped filter-row/scrubber (600/151) removed - nothing above/right of
           the grid in this template either. #}
        <control type="panel" id="101">
            <hitrect x="0" y="95" w="1780" h="1185" />
            <posx>0</posx>
            <posy>0</posy>
            <width>1800</width>
            <height>{% block panel_height %}1190{% endblock %}</height>
            <onleft>9000</onleft>
            <!-- wraparound=false alone didn't stop top<->bottom wrapping live for the collection
                 grid this is lifted from - 'noop' (this codebase's own established "consume the
                 press, don't move anywhere" idiom, includes/sidebar.xml.tpl:322) is needed too. -->
            <ondown>noop</ondown>
            <onup>noop</onup>
            <scrolltime>200</scrolltime>
            <orientation>vertical</orientation>
            <preloaditems>2</preloaditems>
            <wraparound>false</wraparound>
            {% block grid_layouts %}
            <!-- ITEM LAYOUT ########################################## -->
            <!-- The poster grid's own tile (script-plex-posters.xml.tpl), copied as is on request
                 (2026-09-29): this screen's panel sits where the poster grid's does, and its old
                 tile predated the grid's current poster style (64b44b54). Keep the two in step. -->
            <itemlayout width="272" height="{{ vscale(460) }}">
                <control type="group">
                    <posx>55</posx>
                    <posy>{{ vscale(137) }}</posy>
                    <control type="image">
                        <posx>0</posx>
                        <posy>0</posy>
                        <width>264</width>
                        <height>{{ vscale(384) }}</height>
                        <texture border="24">script.plex/drop-shadow-directional.png</texture>
                    </control>
                    <control type="group">
                        <posx>3</posx>
                        <posy>3</posy>
                        <control type="image">
                            <posx>0</posx>
                            <posy>0</posy>
                            <width>240</width>
                            <height>{{ vscale(360) }}</height>
                            <texture background="true" diffuse="script.plex/masks/poster-mask.png" fallback="$INFO[ListItem.Property(thumb.fallback)]">$INFO[ListItem.Thumb]</texture>
                            <aspectratio scalediffuse="false">scale</aspectratio>
                        </control>
                        <control type="group">
                            <!-- Matches the recommended-row/pre_play/seasons poster style: inset,
                                 pill-shaped via the same diffuse-mask technique as the poster
                                 corners themselves, rather than a full-bleed flat bar. -->
                            <visible>!String.IsEmpty(ListItem.Property(progress))</visible>
                            <posx>8</posx>
                            <posy>{{ vscale(344) }}</posy>
                            <control type="image">
                                <posx>0</posx>
                                <posy>0</posy>
                                <width>224</width>
                                <height>{{ vscale(8) }}</height>
                                <texture diffuse="script.plex/masks/progress-bar-mask.png">script.plex/white-square.png</texture>
                                <colordiffuse>E60A0F1A</colordiffuse>
                            </control>
                            <control type="image">
                                <posx>0</posx>
                                <posy>0</posy>
                                <width>224</width>
                                <height>{{ vscale(8) }}</height>
                                <texture diffuse="script.plex/masks/progress-bar-mask.png">$INFO[ListItem.Property(progress)]</texture>
                                <colordiffuse>FFE5A00D</colordiffuse>
                            </control>
                        </control>
                        {% include "includes/watched_indicator.xml.tpl" with xoff=240 & uw_size=48 & wbg_w=34.4 & wbg_h=34.4 & with_count=True & scale="medium" %}
                        <control type="label">
                            <scroll>false</scroll>
                            <posx>0</posx>
                            <posy>{{ vscale(371) }}</posy>
                            <width>240</width>
                            <height>{{ vscale(72) }}</height>
                            <font>font10</font>
                            <align>center</align>
                            <textcolor>FFFFFFFF</textcolor>
                            <label>$INFO[ListItem.Label]</label>
                        </control>
                        <control type="label">
                            <visible>!String.IsEmpty(ListItem.Property(subtitle))</visible>
                            <scroll>false</scroll>
                            <posx>0</posx>
                            <posy>{{ vscale(401) }}</posy>
                            <width>240</width>
                            <height>{{ vscale(72) }}</height>
                            <font>font8</font>
                            <align>center</align>
                            <textcolor>A0FFFFFF</textcolor>
                            <label>$INFO[ListItem.Property(subtitle)]</label>
                        </control>
                        <control type="label">
                            <visible>!String.IsEmpty(ListItem.Property(year)) + String.IsEmpty(ListItem.Property(subtitle))</visible>
                            <scroll>false</scroll>
                            <posx>0</posx>
                            <posy>{{ vscale(401) }}</posy>
                            <width>240</width>
                            <height>{{ vscale(72) }}</height>
                            <font>font8</font>
                            <align>center</align>
                            <textcolor>A0FFFFFF</textcolor>
                            <label>$INFO[ListItem.Property(year)]</label>
                        </control>
                    </control>
                </control>
            </itemlayout>

            <!-- FOCUSED LAYOUT ####################################### -->
            <focusedlayout width="272" height="{{ vscale(460) }}">
                <control type="group">
                    <posx>55</posx>
                    <posy>{{ vscale(137) }}</posy>
                    <control type="group">
                        <!-- center = half the focus ring's own size, not half the poster's: the ring
                             (246x366 at posx/posy 0, below) and the poster (240x360 at the inner
                             group's 3,3) share a centre exactly, since the ring is 6px larger and
                             starts 3px earlier - so both centre on 123,183. The old 120,180 was
                             half the poster's own dimensions with the 3px inset forgotten, which
                             pivoted 3px up and left of the real centre. Only ~0.25px of asymmetry
                             at this zoom, so invisible here, but script-plex-posters-small.xml.tpl
                             had the same class of error at 52px and was very visible. -->
                        <animation effect="zoom" start="100" end="104" time="100" center="123,{{ vscale(183) }}" reversible="false">Focus</animation>
                        <animation effect="zoom" start="104" end="100" time="100" center="123,{{ vscale(183) }}" reversible="false">UnFocus</animation>
                        <posx>0</posx>
                        <posy>0</posy>
                        <!-- No Control.HasFocus(101) gate on the drop shadow, unlike the focus ring
                             at the end of this layout. The ring genuinely should only show while
                             the grid holds focus; the shadow should not, because every unfocused
                             item in itemlayout draws it unconditionally. Gating it made the
                             selected item the only poster on screen without a shadow the moment
                             focus moved to the button row/sidebar/scrubber, and the shadow
                             visibly popped back in as Kodi settled the item's layout. -->
                        <control type="image">
                            <posx>0</posx>
                            <posy>0</posy>
                            <width>264</width>
                            <height>{{ vscale(384) }}</height>
                            <texture border="24">script.plex/drop-shadow-directional.png</texture>
                        </control>
                        <control type="group">
                            <posx>3</posx>
                            <posy>3</posy>
                            <control type="image">
                                <posx>0</posx>
                                <posy>0</posy>
                                <width>240</width>
                                <height>{{ vscale(360) }}</height>
                                <texture background="true" diffuse="script.plex/masks/poster-mask.png" fallback="$INFO[ListItem.Property(thumb.fallback)]">$INFO[ListItem.Thumb]</texture>
                                <aspectratio scalediffuse="false">scale</aspectratio>
                            </control>
                            <control type="group">
                                <visible>!String.IsEmpty(ListItem.Property(progress))</visible>
                                <posx>8</posx>
                                <posy>{{ vscale(344) }}</posy>
                                <control type="image">
                                    <posx>0</posx>
                                    <posy>0</posy>
                                    <width>224</width>
                                    <height>{{ vscale(8) }}</height>
                                    <texture diffuse="script.plex/masks/progress-bar-mask.png">script.plex/white-square.png</texture>
                                    <colordiffuse>E60A0F1A</colordiffuse>
                                </control>
                                <control type="image">
                                    <posx>0</posx>
                                    <posy>0</posy>
                                    <width>224</width>
                                    <height>{{ vscale(8) }}</height>
                                    <texture diffuse="script.plex/masks/progress-bar-mask.png">$INFO[ListItem.Property(progress)]</texture>
                                    <colordiffuse>FFE5A00D</colordiffuse>
                                </control>
                            </control>
                            {% include "includes/watched_indicator.xml.tpl" with xoff=240 & uw_size=48 & wbg_w=34.4 & wbg_h=34.4 & with_count=True & scale="medium" %}
                            <control type="label">
                                <scroll>true</scroll>
                                <posx>0</posx>
                                <posy>{{ vscale(371) }}</posy>
                                <width>240</width>
                                <height>{{ vscale(72) }}</height>
                                <font>font10</font>
                                <align>center</align>
                                <textcolor>FFFFFFFF</textcolor>
                                <label>$INFO[ListItem.Label]</label>
                            </control>
                            <control type="label">
                                <visible>!String.IsEmpty(ListItem.Property(subtitle))</visible>
                                <scroll>false</scroll>
                                <posx>0</posx>
                                <posy>{{ vscale(401) }}</posy>
                                <width>240</width>
                                <height>{{ vscale(72) }}</height>
                                <font>font8</font>
                                <align>center</align>
                                <textcolor>A0FFFFFF</textcolor>
                                <label>$INFO[ListItem.Property(subtitle)]</label>
                            </control>
                            <control type="label">
                                <visible>!String.IsEmpty(ListItem.Property(year)) + String.IsEmpty(ListItem.Property(subtitle))</visible>
                                <scroll>false</scroll>
                                <posx>0</posx>
                                <posy>{{ vscale(401) }}</posy>
                                <width>240</width>
                                <height>{{ vscale(72) }}</height>
                                <font>font8</font>
                                <align>center</align>
                                <textcolor>A0FFFFFF</textcolor>
                                <label>$INFO[ListItem.Property(year)]</label>
                            </control>
                        </control>
                        <control type="image">
                            <visible>Control.HasFocus(101)</visible>
                            <posx>0</posx>
                            <posy>0</posy>
                            <width>246</width>
                            <height>{{ vscale(366) }}</height>
                            <texture diffuse="script.plex/masks/ring-mask-poster.png">script.plex/white-square.png</texture>
                            <colordiffuse>FFE9A20D</colordiffuse>
                        </control>
                    </control>
                </control>
            </focusedlayout>
            {% endblock grid_layouts %}
        </control>
    </control>
</control>
{% endblock content %}
