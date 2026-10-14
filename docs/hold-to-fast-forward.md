# Hold left/right to scan the timeline (plan)

## Status

A plan only, nothing is built yet. Written against `9f78d31` (Plex Uno 0.2.0).

An earlier version of this plan used Kodi's own fast-forward and rewind (`PlayerControl(Forward)`/`PlayerControl(Rewind)`). It was replaced by this approach: the video pauses, only the seek bar moves, and the player seeks once at the end. See "Why not Kodi's fast-forward" below.

## What it does

During video playback, holding Right or Left starts a scan:

1. The video pauses.
2. The OSD opens and the seek bar's selected position moves forward or back on its own, with the time and, where the server has them, preview thumbnails following it.
3. While scanning, short presses change the speed and direction.
4. Select or Play seeks once to the selected position and plays from there. Back cancels: the video resumes where it was paused.

| While | Short Right | Short Left | Select / Play | Back |
|---|---|---|---|---|
| Scanning forward | faster | slower; past the slowest, scan back | seek there and play | cancel, play from where it paused |
| Scanning back | slower; past the slowest, scan forward | faster | seek there and play | cancel, play from where it paused |

Speeds: 10x, 30x, 60x, 120x, 300x (seconds of video per second). Nothing is decoded while scanning, so speeds are not limited by the player or the stream.

A short press when not scanning does exactly what it does today (a skip). The feature is off by default and needs a setting turned on.

## What the add-on already has

- **A seek position that moves without the video moving.** Skips set `selectedOffset` and redraw the bar with `updateProgress(set_to_current=False)` (`lib/windows/seekdialog.py:2120`). The playing position and the selected position are drawn separately. Nothing seeks until `doSeek()` (`seekdialog.py:2038`).
- **Preview thumbnails at the selected position.** If the Plex server has generated video preview thumbnails, `updateProgress()` shows the frame for the selected time above the bar (`seekdialog.py:2161–2168`, URL from `PlexPlayer.getBifUrl()` in `lib/_included_packages/plexnet/plexplayer.py:650`).
- **Pausing around a seek.** `SeekPlayerHandler.seek()` can pause the player itself (`lib/player.py:730–750`). It sets `pausedForSeek`, which `onPlayBackPaused()` ignores (`player.py:1063`), and `unPauseAfterSeek`, which resumes playback once the seek is done (`player.py:1489`).
- **The ends of the timeline.** `seekByOffset()` refuses to go past 5s before the end (`seekdialog.py:2054`).
- **Left/right skips.** On the timeline (`MAIN_BUTTON_ID`) they call `skipForward()`/`skipBack()` or `seekByOffset(±10000)` (`seekdialog.py:785–800`). With the OSD hidden (`NO_OSD_BUTTON_ID`, or `passThroughMain` while the skip-marker button shows) they call `skipForward(without_osd=True)`/`skipBack(without_osd=True)` (`seekdialog.py:836–852`). A skip is pending until auto-seek applies it (`delayedSeek()`, `seekdialog.py:1366`) or Select does; `resetSeeking()` drops it.
- **Holding a key already does something.** With Kodi-style skip steps, the repeats walk up the step list (`determineSkipStep()`, `seekdialog.py:1268`). The new behaviour replaces this only when its setting is on.
- **The "FFWD/RWD" buttons are skips.** `video_show_ffwdrwd`, controls 405/408, call `skipBack()`/`skipForward()` (`seekdialog.py:1109–1112`). This plan doesn't change them.

## Design

### 1. Detecting a hold

Python add-ons get no hold time and no key-release event: `xbmcgui.Action` has only `getId()`, `getButtonCode()`, `getAmount1()` and `getAmount2()`. A held key arrives as the same action repeated, so a hold is inferred from timing.

`HoldDetector`, a Kodi-free class so it can be unit-tested:

- `press(direction, now)` returns `'press'` (first of a run), `'repeat'` (same direction within `REPEAT_GAP` of the last), or `'hold'` (the run has lasted `HOLD_AFTER` and this is the first time it says so).
- A run ends when a different action arrives, or the gap since the last press is over `REPEAT_GAP`.
- Starting values: `HOLD_AFTER = 0.6s`, `REPEAT_GAP = 0.25s`, to be tuned on real remotes.

### 2. The scan

`Scan`, also Kodi-free, holds the state and the arithmetic:

- `start(offset, direction, now)`: the starting position, direction and the lowest speed.
- `faster()`, `slower()`: step through the speed list. Slower than the lowest flips direction at the lowest speed.
- `advance(now)`: moves the offset by speed × the real time since the last call (not a fixed step per tick, so it stays smooth if a tick is late), clamped to `0 … duration − 5000`. At a clamp, the offset stops there and the scan stays on, so a press can still reverse it.
- `offset`, `direction`, `speed`, `label` (for the OSD, such as "▶▶ 30x").

Both classes go in a new module, `lib/windows/seek_scan.py`.

### 3. In `SeekDialog`

**Starting.** On `'hold'`, only where left/right currently mean "skip" (the timeline button, the OSD-hidden button and the `passThroughMain` case):

- Drop the pending skip from the first press (`resetSeeking()`, and clear `_delayedSeekTimeout` so a pending auto-seek can't fire), and start the scan from the playing position (`trueOffset()`).
- Note whether the video was playing. If it was, pause it (§4).
- Show the OSD with focus on the timeline, and set the `scan.active` and `scan.label` properties.
- Start a scan thread, like `_delayedSeek()` (`seekdialog.py:1384`): every 0.1s, `advance()`, set `selectedOffset`, call `updateProgress(set_to_current=False)`, update `scan.label`, and `resetTimeout()` so the OSD doesn't hide. It stops on abort, on the session ending, or when the scan ends.
- The rest of the hold's repeats are dropped, not taken as speed presses.

**While scanning.** At the top of `onAction`, before the existing handling:

- Right/Left (a new run): `faster()`/`slower()` by direction, as in the table above. Repeats dropped.
- Select, Play, Play/Pause: apply (below).
- Back: cancel (below). This comes before the existing cancel handling, so the OSD stays open and a second Back does what Back does today.
- Up/Down, Page Up/Down: ignored, so they don't start chapter skips or the big seek list mid-scan.
- Stop: stop the scan thread, then the existing stop handling.
- Anything else: ignored.

**Applying.** Stop the thread. If the video was playing before the scan, set `handler.unPauseAfterSeek = True` so the handler resumes playback when the seek completes (`player.py:1489`). Then `doSeek(offset=scan.offset)`. If it was already paused, it stays paused at the new position.

**Cancelling.** Stop the thread, `resetSeeking()`, `updateProgress()` to put the bar back, and if the video was playing before the scan, `player.control('play')`. No seek.

**Ending for other reasons.** The session ending, playback stopping, or the dialog closing stops the thread and clears the scan state, with no seek.

### 4. Pausing without side effects

The pause must not look like the user pausing. A new flag, `handler.pausedForScan`, set before `player.control('pause')` and honoured where a user pause has effects:

- `SeekPlayerHandler.onPlayBackPaused()` (`player.py:1063`): return early, as for `pausedForSeek`.
- `SeekDialog.onPlayBackPaused()` (`seekdialog.py:2365`): no `idleTime`, `pausedAt` or seek-behind-on-pause (`resume_seek_behind_pause`).
- The idle check in `onTimeKeeperCallback()` (`seekdialog.py:2447`): no idle time while scanning, so stop-on-idle can't fire mid-scan.
- `SeekDialog.onPlayBackResumed()` (`seekdialog.py:2319`): clear `pausedForScan` and return early, as it does for `pausedForSeek`.
- Plex progress: `tick()` keeps reporting "paused" while scanning. That's accurate, and the seek sends a new position when it's applied.

A separate flag, not `pausedForSeek`, because `tick()` stops reporting progress while `pausedForSeek` is set (`player.py:1869`) and the seek code clears it.

### 5. Preview thumbnails

Each new thumbnail URL is an HTTP fetch from the server, and the scan thread redraws ten times a second.

- In `updateProgress()`, while scanning, round the offset passed to `getBifUrl()` to a fixed step (2s to start; to be checked against the server's thumbnail interval), so ticks that land on the same thumbnail reuse the same URL and Kodi's image cache.
- Change `bif.image` at most every 0.4s while scanning.
- No thumbnails on the server: the time and the bar still move. Nothing else changes.
- The `blur_chapters` spoiler setting is applied as it is now.

### 6. OSD

- A scan label (`scan.label`, such as "▶▶ 30x" or "◀◀ 60x") near the time, visible while `scan.active` is set, in `script-plex-seek_dialog.xml.tpl` (beside the `Player.PlaySpeed` label at line 148). Skins are templates, so they are recompiled.
- The OSD doesn't hide while scanning: the scan thread calls `resetTimeout()`, and the hide check in the tick (`seekdialog.py:2746–2753`) skips hiding while scanning.
- The timeline shows the playing position and the scan position as it does for skips now.
- The pending-skip marker (`button.seek`) stays set while scanning, so the user can see the position is not applied yet.

### 7. When it's available

- **Direct play, path-mapped and transcoded items.** There's a single seek at the end, as for a skip today, so transcodes work too.
- **Not while waiting for the start-of-playback seek** (`handler.waitingForSOS`), as for skips now.
- **Not for external players** (`player.isExternal`).
- **Not while a seek is already being applied** (`_applyingSeek`).

### 8. Setting

A `BoolSetting` in "Player UI" (`lib/windows/settings.py`, next to `player_show_buttons`):

- ID `video_hold_to_scan`, default off.
- Label: "Hold left/right to scan".
- Description: "Hold Left or Right during playback to pause and scan the timeline. Press again to change speed, Select to play from there, Back to cancel. Needs a remote that repeats a held key."
- New strings go in `resources/language/resource.language.en_gb/strings.po`.

Read once when the OSD initialises (`seekdialog.py:510`, beside `player_show_buttons`).

## Why not Kodi's fast-forward

Kodi's fast-forward plays the video at 2–32x by seeking and showing frames. With it:

- Transcodes would stall: a Plex transcode is made as it plays and can't keep up at high speeds, so it would have to be direct play only.
- Playback passes through intro and credits markers, so auto-skip, countdowns and post-play would need suppressing.
- The handlers would need `onPlayBackSpeedChanged`, and Plex would see a fast-moving "playing" position.
- The picture is jerky, more so over the network.

Scanning the timeline with the video paused has none of these problems. What it loses is a moving picture, which preview thumbnails mostly make up for.

## Not using a keymap

Kodi keymaps support `mod="longpress"`, which would give a real long press. But the add-on would have to write a keymap into the user's `userdata/keymaps`, which applies to all of Kodi, survives uninstalling the add-on, and conflicts with the user's own keymaps. Timing in the add-on is less exact but stays inside it.

## Risks

- **Remotes that don't repeat.** Some HDMI-CEC remotes send one press for a hold. There a hold looks like a short press and nothing new happens: no harm, but no feature. The setting's description says so.
- **Repeat timing differs by device.** If 0.6s/0.25s are wrong on some remotes, make them advanced settings, not more code.
- **The pause and the first scan tick race.** Pausing takes a moment. The scan works on `selectedOffset` only, so it doesn't matter where the video stops; the seek goes to the scan position either way. Cancelling resumes from wherever it paused, a fraction of a second after the hold started.
- **Thumbnail load on the server.** Covered by the rounding and throttling in §5; to check on a slow server.
- **A long scan and the Plex session.** Plex sees a paused session for as long as the scan lasts, as with any pause. No change needed.

## Steps

1. `HoldDetector` and `Scan` in `lib/windows/seek_scan.py`, with unit tests (`tests/test_seek_scan.py`):
   - `HoldDetector`: press, repeat, hold after the threshold, a gap ending a run, a direction change ending a run, `'hold'` reported once per run.
   - `Scan`: speed steps up and down, flipping direction past the slowest, advancing by elapsed time, clamping at both ends, reversing from a clamp.
2. `pausedForScan` in the handler and the dialog (§4).
3. The setting and its strings.
4. `SeekDialog`: starting, keys while scanning, applying, cancelling and ending (§3), with the conditions in §7.
5. Thumbnail rounding and throttling (§5).
6. The OSD label and hide checks (§6).
7. Device testing: a keyboard, an Android TV remote, a CEC remote and a Kodi app remote (Kore/Yatse), on direct play, path-mapped and transcoded items, with and without preview thumbnails. Check that the video resumes (or stays paused if it was paused), that Back resumes without a seek, Plex's reported progress, the ends of the timeline, and that stop-on-idle and seek-behind-on-pause don't fire.
8. Tune `HOLD_AFTER`, `REPEAT_GAP`, the speed list and the thumbnail step from step 7.

## Open questions

- **Latched or while-held?** This plan latches: the scan carries on after the key is let go, until Select or Back. The alternative scrolls only while the key is held, speeding up the longer it's held; letting go leaves a pending position that applies like a skip (auto-seek, or Select). That needs no speed presses, but relies more on the remote repeating reliably. It could be a second option of the same setting.
- **Snap to chapters?** When applying, a scan position within a few seconds of a chapter start could snap to it.
- **Play/Pause while scanning:** apply and play (as planned), or apply and stay paused?
- **The "FFWD/RWD" buttons:** leave as skips, or start a scan when this setting is on?
