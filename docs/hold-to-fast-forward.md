# Hold left/right to fast-forward and rewind (plan)

## Status

A plan only, nothing is built yet. Written against `9f78d31` (Plex Uno 0.2.0).

## What it does

During video playback, holding Right starts Kodi's fast-forward and holding Left starts its rewind. While scanning, a short press changes the speed:

| While | Short Right | Short Left | Select / Play / Back |
|---|---|---|---|
| Forwarding | faster (2x → 4x → 8x → 16x → 32x) | slower; past 2x, into rewind | back to 1x |
| Rewinding | slower; past 2x, into forward | faster (2x → … → 32x) | back to 1x |

A short press when not scanning does exactly what it does today (a skip). The feature is off by default and needs a setting turned on.

## How playback and the keys work today

- **Kodi's player plays the video.** `PlexPlayer` (`lib/player.py:2390`) subclasses `xbmc.Player`, so Kodi's `PlayerControl(Forward)`, `PlayerControl(Rewind)` and `PlayerControl(Play)` work on it. Kodi steps the speed itself: Forward while rewinding slows the rewind, and the other way round.
- **Nothing in the add-on uses fast-forward or rewind.** The "FFWD/RWD" buttons (`video_show_ffwdrwd`, controls 405/408) are skip buttons: they call `skipBack()` and `skipForward()` (`lib/windows/seekdialog.py:1109–1112`).
- **Left/right are skips.** On the timeline (`MAIN_BUTTON_ID`) they call `skipForward()`/`skipBack()` or `seekByOffset(±10000)` (`seekdialog.py:785–800`). With the OSD hidden (`NO_OSD_BUTTON_ID`, or `passThroughMain` while the skip-marker button shows) they call `skipForward(without_osd=True)`/`skipBack(without_osd=True)` (`seekdialog.py:836–852`).
- **A skip is pending until it's applied.** With auto-seek on it applies after a delay (`delayedSeek()`, `seekdialog.py:1366`). With auto-seek off it waits for Select. `resetSeeking()` discards it.
- **Holding a key already does something.** With Kodi-style skip steps, the repeats walk up the step list (`determineSkipStep()`, `seekdialog.py:1268`), so holding gives a fast-moving pending seek with no picture. The new behaviour replaces this only when its setting is on.
- **The OSD knows about scanning.** It stays open while `Player.Forwarding`/`Player.Rewinding` (`seekdialog.py:2106`, `2752`), and the skin swaps the play/pause icon (`script-plex-seek_dialog.xml.tpl:694–722`). `Player.PlaySpeed` is shown, but only when `Player.IsTempo` (`script-plex-seek_dialog.xml.tpl:148–158`).
- **No speed callback.** No handler implements `onPlayBackSpeedChanged`.

## Design

### 1. Detecting a hold

Python add-ons get no hold time and no key-release event: `xbmcgui.Action` has only `getId()`, `getButtonCode()`, `getAmount1()` and `getAmount2()`. A held key arrives as the same action repeated. So a hold is inferred from timing.

A small, Kodi-free class, `HoldDetector`, in a new module `lib/windows/hold_detector.py`, so it can be unit-tested:

- `press(direction, now)` returns one of `'press'` (first of a run), `'repeat'` (same direction within `REPEAT_GAP` of the last), or `'hold'` (the run has lasted `HOLD_AFTER` and this is the first time it says so).
- A run ends when a different action arrives, or the gap since the last press is over `REPEAT_GAP`.
- Starting values: `HOLD_AFTER = 0.6s`, `REPEAT_GAP = 0.25s`. To be tuned on real remotes. Keyboard repeat is ~30/s after ~0.5s; remotes vary.

### 2. In `SeekDialog.onAction`

Only where left/right currently mean "skip": the timeline button, the OSD-hidden button and the `passThroughMain` case. Not on the big seek list, the chapters list or other buttons.

- **Not scanning, first press of a run:** the skip happens as now.
- **Not scanning, `'repeat'`:** as now (the step walk), so a press-and-hold below the threshold feels the same as today.
- **`'hold'`:** `resetSeeking()` to drop the pending skip, then `PlayerControl(Forward)` or `PlayerControl(Rewind)`. Mark the run as consumed, so its remaining repeats are dropped instead of changing the speed.
- **Scanning, a new run (`'press'`):** Right sends `PlayerControl(Forward)`, Left sends `PlayerControl(Rewind)`. Kodi does the stepping in the table above. Repeats are dropped.
- **Scanning, Select, Play/Pause or Back:** `PlayerControl(Play)` to return to 1x. Back returns to 1x and keeps the OSD; a second Back does what Back does today. This has to come before the existing `fast_pause_resume` and cancel handling.
- **Scanning, up/down:** ignored, so they don't start chapter skips or the big seek list mid-scan.

"Scanning" comes from `xbmc.getCondVisibility('Player.Forwarding | Player.Rewinding')`, not our own flag, so it stays right if Kodi changes the speed itself (for example at the start of the file).

### 3. When it's available

- **Direct play and path-mapped files only** (`self.isDirectPlay`, `seekdialog.py:582`). A Plex transcode is made as it plays, and 16–32x will outrun it. For transcodes, holding keeps today's behaviour.
- **Not while waiting for the start-of-playback seek** (`self.handler.waitingForSOS`), as for skips now.
- **Not for external players** (`self.player.isExternal`).

### 4. Playback tracking while scanning

Add `onPlayBackSpeedChanged(speed)` to `PlexPlayer`, passed on to the handler like the other callbacks (`lib/player.py:3148–3206`). `SeekPlayerHandler` keeps `self.playSpeed`.

- **Plex progress:** `tick()` → `updateNowPlaying()` (`lib/player.py:1867`, `171`) keeps reporting while scanning, state "playing". To check: that Plex accepts the jumping position without odd "watched" results. If it doesn't, skip timeline updates while `playSpeed != 1` and send one when it returns to 1.
- **Markers:** passing an intro or credits marker while scanning must not auto-skip, start a countdown or open post-play. `displayMarkers()` (`seekdialog.py:2541`) returns early while scanning, and runs once when speed returns to 1x so a marker you stop inside still shows.
- **Resume point and watched state:** unchanged; they're taken from the position when playback stops.
- **End of file:** fast-forwarding into the end ends playback as it would normally (post-play or the next episode). To be tested, no change planned.
- **Start of file:** Kodi drops to 1x at the start when rewinding. The speed callback covers it.
- **Pause:** check what Kodi does with Forward while paused. If it resumes at speed, fine; if not, ignore holds while paused.

### 5. OSD

- **Speed indicator:** show `Player.PlaySpeed` while forwarding or rewinding: change the visibility at `script-plex-seek_dialog.xml.tpl:149` to `Player.IsTempo | Player.Forwarding | Player.Rewinding`. Skins are templates, so they are recompiled.
- **OSD stays open while scanning:** already true via the existing checks. A hold with the OSD hidden opens it, so the speed and the timeline show.
- **Timeline:** check that the progress bar follows the position during scanning, and that the pending-skip marker (`button.seek`) is cleared by `resetSeeking()`.

### 6. Setting

A `BoolSetting` in "Player UI" (`lib/windows/settings.py`, next to `player_show_buttons`):

- ID `video_hold_to_scan`, default off.
- Label: "Hold left/right to fast-forward or rewind".
- Description: "Hold Left or Right during playback to rewind or fast-forward. Press again to change speed, Select to play. Direct play only. Needs a remote that repeats a held key."
- New strings go in `resources/language/resource.language.en_gb/strings.po`.

Read once when the OSD initialises (`seekdialog.py:510`, beside `player_show_buttons`).

### Not using a keymap

Kodi keymaps support `mod="longpress"`, which would give a real long press. But the add-on would have to write a keymap into the user's `userdata/keymaps`, which applies to all of Kodi, survives uninstalling the add-on, and conflicts with the user's own keymaps. Timing in the add-on is less exact but stays inside it.

## Risks

- **Remotes that don't repeat.** Some HDMI-CEC remotes send one press for a hold. There a hold looks like a short press and nothing new happens: no harm, but no feature. Worth saying in the setting's description (done above).
- **Repeat timing differs by device.** If 0.6s/0.25s are wrong on some remotes, make them advanced settings, not more code.
- **Kodi's scan quality.** Kodi scans by seeking and showing frames, so it's jerky, more so over the network. Not something the add-on can fix.
- **Interaction with skips already in flight.** A hold that starts while an earlier skip is still pending should drop that skip too. `resetSeeking()` does this; the tests should cover it.

## Steps

1. `HoldDetector` and its unit tests (`tests/test_hold_detector.py`): press, repeat, hold after the threshold, a gap ending a run, a direction change ending a run, `'hold'` reported once per run.
2. `onPlayBackSpeedChanged` in `PlexPlayer` and `SeekPlayerHandler`, with debug logging. Nothing else uses it yet.
3. The setting and its strings.
4. `SeekDialog.onAction`: the hold and scanning handling in §2, with the conditions in §3.
5. Marker suppression while scanning (§4).
6. The OSD speed indicator (§5).
7. Device testing: a keyboard, an Android TV remote, a CEC remote and a Kodi app remote (Kore/Yatse), on direct play, path-mapped and transcoded items. Check Plex's reported progress, markers, end of file, start of file and pause.
8. Tune `HOLD_AFTER` and `REPEAT_GAP` from step 7.

## Open questions

- Should Back during scanning return to 1x and keep the OSD (as planned), or return to 1x and close it?
- Should the existing "FFWD/RWD" buttons be renamed, since they skip and don't scan? Or should they scan when this setting is on?
- Is direct play only the right line, or should transcodes get scanning capped at a lower speed, such as 4x?
