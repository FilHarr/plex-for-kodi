# Sidebar Nav rollout — status and pattern reference

Written 2026-08-05, on branch `Sidebar-Nav`. Purpose: onboard a fresh session continuing this rollout without
re-deriving the pattern from scratch. For the separate, larger-scoped future initiative (folding Library/
Categories into Home behind a focus-driven tab row), see `sidebar-tab-unification-scope.md` in this same
directory — that's a different, bigger piece of work, not a prerequisite for finishing the per-screen rollout
described here.

## Goal

Roll the persistent left-side sidebar rail (`includes/sidebar.xml.tpl`, control group id `9000`) out from Home
to every other screen. Already done, in order: **Home**, **Library**, **Pre-play**, **Episodes**, **Seasons**.

**Not yet started / deliberately deferred: `ArtistWindow`** (`lib/windows/subitems.py:712`, subclasses
`ShowWindow`). It picked up `windowutils.SidebarMixin` and `SECTION_LIST_ID`-handling for free via inheritance
when `ShowWindow` was updated for Seasons, but it renders through its own separate template
(`script-plex-artist.xml.tpl`) that was **not** touched — that template still shows the default header's
Home/Search buttons (ids `201`/`202`), which is why `ShowWindow.HOME_BUTTON_ID`/`SEARCH_BUTTON_ID` and their
`onClick` branches were deliberately *kept* (not removed, unlike Episodes/Pre-play) — removing them would have
broken Artist's still-live Home/Search buttons. Porting the sidebar to Artist is its own follow-up: different
layout (square poster, similar-artists row, no seasons/roles/extras hubs), needs its own posx/clip-fix pass,
and — once done — the now-dead `HOME_BUTTON_ID`/`SEARCH_BUTTON_ID`/onClick branches on `ShowWindow` can finally
be removed.

## Commits so far (Pre-play + Episodes + Seasons phase)
- `9141e78a` Pre-play: adopt the persistent sidebar, shrink the poster to make room
- `4d6d194c` Pre-play: fix sidebar sliding off-screen with the header on scroll
- `c86d1936` Episodes: adopt the persistent sidebar
- `b933fdf3` Pre-play: let Related/Collection rows escape left into the sidebar
- (uncommitted) Seasons: adopt the persistent sidebar — see below

## The established pattern (apply this to Seasons)

**Template — header wiring (get this right from the start):**
```
{% block header_topleft %}{% endblock %}
{% block header %}
    {{ super() }}
    {% include "includes/sidebar.xml.tpl" %}
{% endblock header %}
```
- `default.xml.tpl`'s own `header_sidebar` block sits *inside* header group `id="200"`, which has a scroll-away
  slide animation (`header_anim`, tied to `Window.Property(on.extras)`). Filling that block directly (the first
  attempt on pre_play) makes the rail incorrectly slide away with the header. **Always use the super()+append
  pattern above instead** — verified via a structural check (parse the rendered XML, confirm the `id="9000"`
  control has zero `<control>` ancestors).
- Blanking `header_topleft` removes the default Home/Search buttons; ids `201`/`202` are reused by the rail's
  server/user buttons (`SidebarMixin.SERVER_BUTTON_ID`/`USER_BUTTON_ID`, in `lib/windows/windowutils.py`).
- If the screen has its own `header_search_onright`/`header_audiowidget_onleft`-style overrides, check whether
  they still make sense: `header_search_onright` becomes dead code once `header_topleft` is blank and should be
  removed; anything wired to the old id `202` should retarget to `9000`.

**Content layout shift:**
- Shift the outer content group (usually `id="50"`) `posx` from `0` to `60` — clears the collapsed rail's icon
  column. Everything nested inside moves with it automatically; don't touch children's own relative posx.
- Add the standard expand-slide animation to that same group:
  `<animation effect="slide" end="220,0" time="200" tween="sine" easing="inout" condition="ControlGroup(9000).HasFocus(0)">Conditional</animation>`.
- Compensate every element positioned with **absolute, screen-edge-relative** coordinates (not relative to the
  shifted group) by `-60`, so it stays where it visually was: ratings badges, right-anchored media-info-pills
  rows, etc. Also check anything whose *width* was tuned to "stop just short of" one of those now-compensated
  elements — its width may need to shrink by the same 60.
- Wire `onleft` into the rail (`9000`) on any left-edge control with none, or with `onleft=noop`.
  - **Check whether `noop` is actually load-bearing first.** It protects two real things: (a) a *bidirectional*
    paginator's left-boundary marker (an item with `left.boundary` property, used to trigger loading the
    previous page), or (b) a fixed-center carousel's own boundary-chevron display. If the list's paginator
    always starts at `offset=0` and never produces a left-boundary marker (true for
    `RelatedPaginator`/`CollectionPaginator`/`BaseRelatedPaginator` subclasses — check by seeing if they
    override `initialPage` with a nonzero offset), `onleft=noop` there is just a dead end and can go straight
    to `9000` unconditionally.
  - For genuinely bidirectional carousels, use the conditional form:
    ```xml
    <onleft condition="!String.IsEmpty(Container(ID).ListItem.Property(left.boundary))">noop</onleft>
    <onleft>9000</onleft>
    ```

**Collapsed-rail thumbnail clipping fix** (if the screen has a horizontal carousel near the left edge):
whichever control is the actual clipping container (a `grouplist`, since plain `group` doesn't clip) needs its
`posx` pushed to absolute x=100 (not just 60) so departing items clear the rail's icon column before getting
clipped. Shrink that container's `width` by the same delta to keep its right edge fixed, and compensate the
child list's own `posx` by subtracting the same delta so resting/focused positions don't move.

**Round-robin wrap:** if the screen has a carousel using `MCLPaginator.wrap()` (grep `\.wrap(` in the window's
`.py` file), decide whether it should keep wrapping now the sidebar occupies the left edge — for Episodes it
was disabled (override `wrap()` to return `None` in the paginator subclass).

**Python side (mirror `PrePlayWindow`/`EpisodesWindow` exactly):**
1. Mix in `windowutils.SidebarMixin`.
2. Remove any `HOME_BUTTON_ID`/`SEARCH_BUTTON_ID` class constants and their `onClick` branches.
3. In the first-init method: `self.sectionList = kodigui.ManagedControlList(self, self.SECTION_LIST_ID, 15)`,
   then `self.buildSectionList()`, `self.displayServerAndUser()`. No "already built" guard needed unless the
   window is a `MultiWindow`/reused-instance type (`LibraryWindow` needs one; single-use windows like
   Pre-play/Episodes don't).
4. `onClick()`: add `elif controlID == self.SECTION_LIST_ID: self.sectionClicked()`.
5. Add `buildSectionList()`, `sectionClicked()`, `displayServerAndUser()` — copy verbatim from
   `preplay.py`/`episodes.py`, swapping the "current library section" expression for `activeSectionId`
   (`self.video.getLibrarySectionId()` in pre_play, `self.show_.getLibrarySectionId()` in episodes — check
   what's available on `ShowWindow`).
6. Imports if missing: `import json`, `from . import home`, `from . import playlists`.

## Verification checklist used each time
- `python -m pytest tests/ -q -k "not ClearLogoTest"` — the two `ClearLogoTest` subfailures (`pre_play`,
  `pre_play-wl`) are pre-existing/unrelated.
- Structural nesting check (throwaway test, delete after): render the theme, parse the rendered XML, confirm
  `id="9000"` has zero `<control>` ancestors, and optionally that ids `201`/`202` each appear exactly once.

## Bugs found and fixed along the way (worth checking for on Seasons too)
- **Header/content desync**: if the screen has `hub.focus`-driven row-collapse animations separate from
  `on.extras`-driven header hide/show, check whether `hub.focus` resets when focus leaves the row stack for a
  button row outside the numeric id range `onFocus` watches. On Episodes it didn't, so the header reappeared
  one step before the content above it scrolled into view. Fix: reset `hub.focus` to `'0'` in the same branch
  that clears `on.extras`.
- Pre-play also got a poster resize (~10% smaller) — that was a separate, explicit request unrelated to the
  sidebar; don't assume Seasons needs it.

## Reference files
- `includes/sidebar.xml.tpl` — the rail itself.
- `lib/windows/windowutils.py` — `SidebarMixin`.
- `script-plex-pre_play.xml.tpl` + `lib/windows/preplay.py` — cleanest reference implementation.
- `script-plex-episodes.xml.tpl` + `lib/windows/episodes.py` — reference for carousel clip/wrap treatment.
- `library.xml.tpl` + `lib/windows/library.py` — reference for the `MultiWindow` "already built" guard case.

## Seasons phase notes (worth knowing before Artist)
- Python window code actually lives at `lib/windows/…`, not `resources/lib/windows/…` (the latter path doesn't
  exist in this checkout — a correction to earlier phrasing in this doc).
- `windowutils.SidebarMixin` is id-constants-only (no methods) — `buildSectionList`/`sectionClicked`/
  `displayServerAndUser` are hand-duplicated per window, copied verbatim from `episodes.py` with only the
  "current library section" expression swapped (`self.mediaItem.getLibrarySectionId()` for `ShowWindow`,
  vs. `self.show_.getLibrarySectionId()` on Episodes / `self.video.getLibrarySectionId()` on Pre-play — check
  what attribute the target window actually holds its media item under).
- Seasons' four hub carousels (`400` Seasons, `401` Roles, `402` Extras, `403` Related) are plain `<list>`
  controls, not a `fixedlist`-in-`grouplist` wrapper like Episodes' fixed-center carousel — so the clip-fix
  here shifts the list's own `posx`/`width` and compensates by reducing the itemlayout/focusedlayout
  wrapper group's own `posx` (`55`→`15`, a `40`-delta) by the same amount, rather than compensating a
  separate child list's posx inside a wrapper grouplist.
- `ShowWindow.HOME_BUTTON_ID`/`SEARCH_BUTTON_ID` and their `onClick` branches were **kept**, unlike
  Episodes/Pre-play where they were removed — see the "Not yet started" note above on `ArtistWindow`.
- `onFocus`'s `hub.focus`-reset fix (same latent bug as Episodes, see "Bugs found and fixed") was applied
  using just `ControlGroup(300)` in the clearing condition (Seasons has no second button group like
  Episodes' `1300`).
- Verified via a throwaway structural test (rendered `seasons.xml`, confirmed `id="9000"` has zero
  `<control>` ancestors and ids `201`/`202`/`9000`/`9001` each appear exactly once) — deleted after passing,
  per the standing convention.

## Not yet started
`ArtistWindow` (`script-plex-artist.xml.tpl` + the `ArtistWindow` class in `subitems.py`) — see the note under
Goal above. Start by reading the artist template's current layout in full (it's structurally quite different
from Seasons: single square poster + similar-artists row, no seasons/roles/extras hubs) before assuming any
of Seasons' specific pixel deltas carry over.
