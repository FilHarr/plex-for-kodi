# TV spoilers on every screen (plan)

## Status

Written 2026-10-20 against `c536b8f9` (spoilers hide the player's previews). Steps 1-5 built the same day
(`SpoilersMixin.spoilerCovered()`, tests in `tests/test_spoiler_covered.py`); step 6, the live checks, to do.

## Why

The "No TV spoilers" options (`no_episode_spoilers4`) are applied on the Episodes screen, in the video player (OSD,
chapter row, play queue row) and on post-play - each through `SpoilersMixin` (`lib/windows/mixins/spoilers.py`),
for an episode the conditions cover: unwatched, or not fully watched with "In progress", outside the allowed genres
(`hideSpoilers()`). Elsewhere an episode's title, picture or summary shows whatever the settings say. Home's and the
libraries' rows were rebuilt for Uno without upstream's handling (upstream itself only covered Home's Continue
Watching and On Deck), and the playlist screen never had any.

## Survey

What each screen shows of an episode, and what gives the story away:

| Screen | Shows of an episode | Spoils | Where |
|---|---|---|---|
| Row tiles (Home, libraries) | only the picture - the season's (or show's) poster - with progress and watched marks, and on a 16:9 tile an "E3" badge; no text (the code sets labels, the tile templates don't draw them) | nothing | `LibraryWindow.createEpisodeListItem()` (`library_hubs.py`); `Episode.defaultThumb`; `includes/hub_*layout_*.xml.tpl` |
| Hero area over the rows | show's logo or name, **episode title** under it, **summary**, S/E, duration, air date, content rating; background the show's art | title, summary | `LibraryWindow.setHeroInfo()` (`library_hubs.py`) |
| See more: Recently Added TV (three lines) | show name, S/E, **episode title** as the third line; poster | title | `grid_labels.lines()` (`RECENTLY_ADDED_TV`) |
| See more: other grids | poster grids: show name, S/E, last played / aired date; the 16:9 grid only the picture (the same poster) | nothing | `grid_labels.lines()`, `see_more.HubGridWindow.thumbFor()` |
| Library grid, episodes view | show name, S/E; poster | nothing | `library_grid.py` (`defaultTitle`, `defaultThumb`) |
| Playlist screen | **episode title**, show and S/E, **the episode's own still** | title, picture | `PlaylistWindow.createEpisodeListItem()` (`playlist.py`) |
| Search results | **episode title**, show, S/E, **the episode's own still** | title, picture | `SearchWindow._listItem()` / `createListItem()` (`search.py`) |

The playlist screen's header shows the playlist's own summary, not an episode's. Search finds what was typed, so an
episode found by its own title spoils little; but searching a show's name lists its episodes, titles and stills.

## What changes

The same options, the same conditions, the same treatment as the Episodes screen (`EpisodesWindow`'s
`setItemInfo()`, `episodes.py`):

- **"No unplayed episode titles"**: the title reads "[Spoilers removed]" (33008) - the hero's second line, the
  Recently Added grid's third line, the playlist row's title, the search result's title. The show's name and S/E
  stay everywhere, so it's still clear what the item is.
- **"Blur images"**: the episode's own still blurred by Plex (`getThumbnailOpts()`, `episode_no_spoiler_blur`) - the
  playlist row and the search result. Elsewhere the picture is the season's or show's already.
- **"Hide summaries"**: the hero's summary reads "[Spoilers removed]".
- **"In progress" means until played once.** It hid an episode until it was fully watched - played, with no
  resume point - so a re-watch in progress (the watched tick still on) was hidden again, on every screen: seen live
  on For All Mankind S1E1 in Continue Watching. Now an episode played once is never covered, here and in
  `hideSpoilers()` (the Episodes screen, the player, post-play); a first watch part way through still is.
- **"Hide ratings"**: no screen in the survey shows an episode's audience or critic rating (the hero's is the content
  rating, TV-MA etc.), so nothing to do.

**"Blur images on home (in progress)"** (`blur_resume_images`) has nothing to act on in Uno: upstream used it for
Continue Watching tiles showing the episode's still, and Uno's tiles show the season's poster. Left as it is for now;
the planned rework of the spoiler settings (a when-setting, then the genre exemptions and a what-to-hide setting)
decides whether it stays.

## Design

- **One place for the decision.** `SpoilersMixin.hideSpoilers()` needs an episode's show genres when allowed genres
  are set: from the data cache (`dcm`, `show_genres`), else `item.show()` - a request. `LibraryWindow`,
  `HubGridWindow`, `PlaylistWindow` and `SearchWindow` gain `SpoilersMixin` (its `cacheSpoilerSettings()` reads the
  settings once, at open; re-read on each screen's reopen, as Episodes does).
- **No request on the GUI thread per item.** The hero changes on every focus move, and a playlist or search builds
  many items at once:
  - genres are looked up once per show (`grandparentRatingKey`) and kept for the screen, filled from the data
    cache first;
  - where a show's genres aren't known yet, the item is treated as covered until they are (hiding is the safe way to
    be wrong), and its genres are fetched on a worker; the item is updated when they arrive. With no allowed genres
    set (the default list is Reality, Game Show, Documentary, Sport - so usually set), no lookup is needed.
- **Hero**: `setHeroInfo()` takes the decision for the focused episode; `hero.subtitle` and `summary` get the
  replacement text.
- **See more**: `grid_labels.lines()` gets a `hide_title` argument for the third line; `HubGridWindow.fillItem()`
  passes it (it fills on a worker already, so a genre request there is fine).
- **Playlist**: `PlaylistWindow.createEpisodeListItem()` - title and still. Its list fills in chunks on a worker.
- **Search**: `createListItem()` for episodes - title and still.
- **Watched state**: as everywhere else, from the item as listed (`isWatched`, `isFullyWatched`); the rows already
  refresh after playback.

## Steps

1. `SpoilersMixin` on the four screens; a per-screen genre cache with the worker fetch.
2. Hero title and summary.
3. See-more third line.
4. Playlist rows: title and still.
5. Search results: title and still.
6. Live checks on the PC, with "No unplayed episode titles", "Blur images" and "Hide summaries" on: an unwatched
   episode (hidden), a watched one, one in an allowed genre (shown), "In progress" with a part-watched episode - in
   the hero, a Recently Added TV see-more grid, a playlist with episodes, and a search for a show's name. Then one
   AM6B pass for the hero's feel moving along a row (no lag from the genre lookups).
