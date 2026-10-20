# Hiding preview pictures for spoilers (plan)

## Status

Written 2026-10-20 against `d37ce004` (previews from the whole index file). Steps 1-3 built the same day; checked on the PC
(an episode with named chapters not yet), the AM6B pass to do.

## Why

The "No TV spoilers" option "Blur chapter images" (`blur_chapters` in `no_episode_spoilers4`) blurs the video
player's moving preview over the seek bar and every card in its chapter row - file chapters, and the Intro / Main /
Credits cards made from Plex's markers - through Plex's photo transcoder. Two problems:

- **A blurred moving preview has no purpose.** It's there to show where a seek lands; blurred, it can't.
- **It ignores the spoiler conditions.** The other spoiler options act only on an episode that qualifies -
  unwatched (or not fully watched, with "in progress"), and not in an allowed genre (`SpoilersMixin.hideSpoilers()`).
  `blur_chapters` is read on its own (`SeekDialog.no_spoilers`), so films and watched episodes are blurred too.

Local blurring was looked at first (shrinking each picture through Kodi's `image://...?width=&height=` and letting the
GUI enlarge it, with or without a frost or grain overlay): workable, but only the shrink hides anything, and a
moving preview blurred enough to hide spoilers still can't show where a seek lands.

## What changes

The option becomes **"Hide preview images"**, applied only when the spoiler conditions apply to the item playing:

- **The moving preview isn't shown.** The time bubble over the seek bar stays.
- **Every card in the chapter row shows a "hidden" placeholder** in place of its picture - file chapters and marker
  cards alike, so the row never mixes pictures and placeholders. Names and times stay; selecting a card still seeks.
- **The placeholder is distinct from "no picture"**: the card's dark fill with the eye-slash icon
  (`indicators/hidden.png`, already used for hidden hubs and offline servers), so hidden-for-spoilers doesn't look
  like an item without previews (the grey film placeholder).
- **The preview index isn't downloaded** for an item whose previews are hidden; nothing would use it.
- **Films and watched episodes keep their previews**, as with the other spoiler options. The decision is made once
  per item when its playback is set up (not on a transcode's seek), so an episode passing the watched mark mid-play
  doesn't suddenly reveal its previews.

No blurred pictures are left in the player.

**Chapter names** go with episode titles: with **"No unplayed episode titles"** (`no_unwatched_episode_titles`) on,
under the same conditions, a file's chapter names (which can be as telling as a picture - "The Betrayal") show as
"Chapter 1", "Chapter 2"... by position, the wording already used for unnamed chapters. In the player's chapter row,
and in the media details' "Chapters:" line (`info.formatMediaDetails()`). Intro / Main / Credits are the add-on's own
labels for Plex's markers and stay. The OSD's own episode title follows the same conditions (it used to hide for
any episode, watched or not, with the option on). That option gets its own help line too: "Also replaces chapter names with
'Chapter 1', 'Chapter 2'...".

## Design

- **Setting**: the stored key stays `blur_chapters`, so anyone who had it on gets "Hide" with no migration; a
  comment says why the key and the label differ. The label gets a **new string ID** (not a re-worded 33081), so
  translations of "Blur chapter images" don't keep labelling the new behaviour. It names both things it hides:
  **"Hide preview thumbnails and chapter images"**.
- **Option help**: the settings screen shows only the setting's description (Container(100)'s `description`), also
  while its options are open. Options gain an optional description of their own, shown in that place while the
  option has focus (Container(125)), the setting's otherwise. This one's spells out the two behaviours:
  "For episodes these settings cover: the preview thumbnail above the seek bar isn't shown at all, and the chapter
  row's pictures are covered with a placeholder - the chapters' names and times still show." The setting's own
  description drops "previews", as a new string (35193) beside the old 33007: Kodi matches translations by their
  English text, so rewording 33007 would have orphaned every translation of it (tests/test_i18n.py guards this).
- **Decision**: `SeekDialog.setup()` (when not `keepMarkerDef`) sets `self.hidePreviews` from
  `'blur_chapters' in self.no_spoilers and self.hideSpoilers(video, use_cache=False)`.
- **Moving preview**: `updateProgress()` leaves `bif.image` empty while `hidePreviews`, so the template's group 300
  stays hidden (it needs a non-empty `bif.image`).
- **Cards**: `updateChapters()` gives every card the placeholder while `hidePreviews` (file chapters' Plex chapter
  pictures included); `onPreviewsReady()` has nothing to swap. The placeholder is drawn by the template, keyed on a
  list item property, so the icon can be sized and centred on the card rather than baked into a picture.
- **Download**: `startPreviews()` returns early while `hidePreviews`.
- **Chapter names**: `setup()` also sets `self.hideChapterNames` from `self.noTitles and self.hideSpoilers(...)`;
  `updateChapters()` uses `T(33607, 'Chapter {}')` for file chapters while it's set. The media details take a flag
  from their caller. For an episode that's always `EpisodesWindow`, which has `SpoilersMixin`: the opener sends
  every episode there (`opener.open()`), and `PrePlayWindow` only shows films. (`CollectionWindow` sends anything
  that isn't a collection, a show or a folder to `PrePlayWindow`, which would include an episode in a collection;
  but no collection on Animal holds episodes - its one TV collection is of shows - and it isn't clear Plex allows
  it, so that's left alone. Pre-play's episode branches are leftovers, also left alone.)
- **Blur code removed**: `previewImage()`'s blur branch and its `dims`/`blur_opts`, the cards' `thumb_opts`, and
  `CHAPTER_THUMB_DIM`'s comment about blur strength. `episode_no_spoiler_blur` stays: episode thumbnails elsewhere
  still use it.

## Steps

1. Setting label, option help (with the settings screen's per-option description) and strings; the per-item decision.
2. Moving preview, cards, download skip; remove the blur paths. Chapter names in the row and the media details.
3. Template: the hidden placeholder on the card (both layouts, the itemlayout and focusedlayout).
4. Live checks on the PC: an unwatched episode (hidden), a watched episode and a film (shown), an episode in an
   allowed genre (shown), "in progress" on and off; a file with named chapters, with "No unplayed episode titles" on
   and off, in the player and the media details; then one AM6B pass.
