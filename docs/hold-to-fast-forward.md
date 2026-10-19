# Hold left/right to scan the timeline (plan)

## Status

A plan only, nothing is built yet. First written against `9f78d31` (Plex Uno 0.2.0), and updated for `e80db309` (the video player's OSD redesign). Line numbers are as of `e80db309`.

An earlier version of this plan used Kodi's own fast-forward and rewind (`PlayerControl(Forward)`/`PlayerControl(Rewind)`). It was replaced by this approach: the video pauses, only the seek bar moves, and the player seeks once at the end. See "Why not Kodi's fast-forward" below.

## What it does

During video playback, holding Right or Left starts a scan:

1. The video pauses.
2. The OSD opens and the seek bar's marker moves forward or back on its own, with the seek point's times and, where the server has them, preview thumbnails following it.
3. While scanning, taps change the speed and direction.
4. Select (OK) seeks once to the scan position and plays from there, or stays paused if the video was paused before the scan. Play/Pause also seeks there, and always plays. Back cancels: the video resumes where it was paused. A scan is only ever applied by the user pressing one of those: auto-seek never applies it.

The scan is latched: it carries on after the key is let go, until Select or Back.

| While | Short Right | Short Left | Select (OK) / Play | Back |
|---|---|---|---|---|
| Scanning forward | faster | slower; past the slowest, 0x (stopped) | seek there and play | cancel, play from where it paused |
| Stopped (0x) | scan forward at 2x | scan back at 2x | seek there and play | cancel, play from where it paused |
| Scanning back | slower; past the slowest, 0x (stopped) | faster | seek there and play | cancel, play from where it paused |

Speeds: 2x, 4x, 8x, 16x, where 1x is 30 seconds of video per second (the OSD-hidden skip's step). So 2x scans a minute of video a second and 16x eight minutes a second: a two-hour film end to end in 15 seconds. The speeds are one scale, -16x to 16x through 0x: a Right tap is a step towards forward, a Left tap a step towards back, and the ends stay at 16x. Nothing is decoded while scanning, so speeds are not limited by the player or the stream.

A short press when not scanning does exactly what it does today (a skip). Holding left/right is off by default and needs a setting turned on.

**A remote's FF and RW buttons** (`ACTION_PLAYER_FORWARD`/`ACTION_PLAYER_REWIND`) start a scan too, anywhere in the player and whatever the setting: FF at ▶▶ 2x, RW at ◀◀ 2x. During a scan they step the speed as Right and Left taps do. They replace Kodi's own trick-play fast-forward, which the add-on used to leave to Kodi, with the problems listed under "Why not Kodi's fast-forward".

Kodi acts on these keys before the add-on sees them (`CApplication::OnAction`, Kodi 21): on a playing video they set the speed to 2x or -2x; on a paused one they do nothing. And `PlayerControl(Play)`, which the add-on's pause sends, only returns a sped-up video to normal speed rather than pausing it. So a scan started by FF/RW on a playing video sends `PlayerControl(Play)` first, to get back to normal speed, then pauses (`startScan(trick_play=True)`). During a scan the video is paused, so Kodi ignores the keys and only the scan acts on them. Where there can't be a scan (§7), Kodi's trick-play happens as before.

## What the add-on already has

- **A seek point that moves without the video moving.** Skips set `selectedOffset` and redraw the bar with `updateProgress(set_to_current=False)` (`lib/windows/seekdialog.py:2220`), which moves the marker and sets the seek point's times (`time.seek.current` and the rest, `seekdialog.py:2268`). Nothing seeks until `doSeek()` (`seekdialog.py:2119`).
- **Preview thumbnails at the seek point.** If the Plex server has generated video preview thumbnails, `updateProgress()` shows the frame for the selected time above the bar (`seekdialog.py:2248–2256`, URL from `PlexPlayer.getBifUrl()` in `lib/_included_packages/plexnet/plexplayer.py:650`).
- **Pausing for a seek.** Since `e80db309`, seeking pauses playback and resumes it when the seek lands. `seekByOffset()` pauses a playing video and calls `setSeekPaused('seeking')` (`seekdialog.py:2156–2160`). `doSeek()` moves that on to `'applying'` and sets `handler.unPauseAfterSeek` so the handler resumes playback once the seek is done (`seekdialog.py:2130–2134`, `lib/player.py:1493`), or, when a transcode restarts, starts it playing (`player.py:580`). `resetSeeking()` resumes an abandoned seek (`seekdialog.py:370–376`). `onPlayBackPaused()`/`onPlayBackResumed()` skip the idle timer and seek-behind for these pauses (`seekdialog.py:2459–2464`, `2406–2411`). A video that was already paused stays paused.
- **The ends of the timeline.** `seekByOffset()` refuses to go past 5s before the end (`seekdialog.py:2153`) or before 1ms.
- **Left/right skips.** On the timeline (`MAIN_BUTTON_ID`) they call `skipForward()`/`skipBack()` (`seekdialog.py:796–816`). With the OSD hidden (`NO_OSD_BUTTON_ID`, or `passThroughMain` while the skip button shows) they call `skipForward(without_osd=True)`/`skipBack(without_osd=True)` (`seekdialog.py:827–845`). Both use the same steps (+30s/−10s, or Kodi's own with `kodi_skip_stepping`). A skip is pending until auto-seek applies it (`delayedSeek()`, `seekdialog.py:1321`) or Select does; `resetSeeking()` drops it.
- **The first step waits.** With auto-seek on, a seek's first step waits at least `FIRST_SEEK_STEP_DELAY` (1s, `seekdialog.py:161`, applied at `1328–1334`) so a held key can start repeating before the step applies.
- **Holding a key already does something.** With Kodi's skip steps, the repeats walk up the step list (`determineSkipStep()`, `seekdialog.py:1221`). The new behaviour replaces this only when its setting is on.

## Design

### 1. Detecting a hold

Python add-ons get no hold time and no key-release event: `xbmcgui.Action` has only `getId()`, `getButtonCode()`, `getAmount1()` and `getAmount2()`. A held key arrives as the same action repeated, so a hold is inferred from timing.

What sets a held key apart from taps is its pace once it repeats. Measured from the debug log on 2026-10-16:

- A PC keyboard repeats every 25-60ms after a ~0.5s delay.
- An Nvidia Shield remote repeats every 40-80ms after ~0.33-0.42s, but Kodi takes input once a frame - 24 a second during a film - so its repeats come in clumps: two at once, then a gap of up to 0.156s.
- The AM6B's two remotes (2026-10-17) repeat about every 83ms after ~0.38-0.42s, also in frame-sized steps: four presses took 0.17-0.25s - the edge of the first limit, 0.25s, so it went to 0.3s.
- Taps were 0.12s apart at the quickest (once 0.084s on the PC); four in a row took at least 0.39s (the PC), 0.66s on the AM6B.

Two earlier rules failed on device: presses within 0.25s for 0.6s took quick tapping for a hold; a 0.3-0.65s repeat-delay gap followed by two repeats within 0.15s broke on the Shield's clumps (a 0.156s gap mid-hold read as taps, racing to 16x) and lost taps that came quickly after a pause.

`HoldDetector`, a Kodi-free class so it can be unit-tested against those logged sequences:

- A hold is `HOLD_REPEATS` (3) gaps in a row - four presses - adding up to no more than `HOLD_SPAN` (0.3s). Taps can't; clumps don't break it.
- `press(direction, now)` returns `'hold'` once, for the press that makes one; `'repeat'` for a press within `REPEAT_GAP` (0.1s) of the last - too quick for a tap; `REPEAT_GAP x HOLD_REPEATS` stays within `HOLD_SPAN`, so a key whose every repeat is that quick is always a hold - and for a held key's presses after its hold, which may come up to `HELD_GAP` (0.17s) apart (the first tap after letting go came 0.19s after the last repeat at the quickest); and `'press'` for a tap.
- A held key's press and its first repeat are taps by then, so before a scan starts there are two skips; the fast repeats after them don't skip.
- A run ends when a different action or the other direction arrives. `held(direction, now)` marks the hold that started a scan, so its repeats are ignored while the key stays down.
- Each left/right press's gap and answer go to the debug log (`SeekDialog: Hold detector: ...`).

Where there can't be a scan (§7), everything skips as before. With a default ~0.5s repeat delay, a hold is seen by about 0.8s, before the 1s `FIRST_SEEK_STEP_DELAY`, so the first press's pending skip is dropped before it applies. A key with a longer repeat delay can be seen after the first skip has applied; the scan then starts from there. A key that repeats slower than every 0.1s on average doesn't scan; it skips as before.

**The auto-seek delay's lowest setting is 0.5s** (`SeekDialog.MIN_AUTO_SEEK_DELAY`; anything lower saved before counts as 0.5s). It used to go down to 0, where `delayedSeek()` made a seek on every press and skipped the first-step minimum - a jerky mess, and the first press of a hold would have restarted a transcode. So every auto-seek gets the 1s first-step minimum and hold-to-scan needs nothing extra.

### 2. The scan

`Scan`, also Kodi-free, holds the state and the arithmetic:

- `start(offset, direction, now)`: the starting position, direction and the lowest speed.
- `press(direction, now)`: a step along the scale -16, -8, -4, -2, 0, 2, 4, 8, 16, towards forward for Right and back for Left, staying at the ends.
- `advance(now)`: moves the offset by speed × 30s × the real time since the last call (`SCAN_UNIT = 30000` ms of video per second at 1x) (not a fixed step per tick, so it stays smooth if a tick is late), clamped to `1 … duration − 5000`. At a clamp, the offset stops there and the scan stays on, so a press can still reverse it.
- `offset`, `direction` (0 when stopped), `speed`, `label` (for the OSD, such as "▶▶ 4x", or "0x").

Both classes go in a new module, `lib/windows/seek_scan.py`.

### 3. In `SeekDialog`

**Starting.** On `'hold'`, only where left/right currently mean "skip" (the timeline, the OSD-hidden button and the `passThroughMain` case):

- Drop the pending skip from the first press and its repeats, and stop both auto-seeks so neither can apply anything during the scan: clear `_delayedSeekTimeout` (`delayedSeek()`'s) and `resetAutoSeekTimer(None)` (the tick's own, which seeks once `autoSeekTimeout` passes, `seekdialog.py:2889`), and clear the skip-step state. Don't call `resetSeeking()` here: it would resume a video the first press has just paused.
- Start the scan from where the marker is: `selectedOffset` while seeking (after the hold's press and first repeat, or earlier taps), else the playing position (`trueOffset()`). Starting from the playing position made the marker jump back by every skip made before the hold was seen.
- Pause the video if it's playing (§4).
- Show the OSD with focus on the timeline, and set the `scan.active` and `scan.label` properties.
- Start a scan thread, like `_delayedSeek()` (`seekdialog.py:1344`): every 0.1s, `advance()`, set `selectedOffset`, call `updateProgress(set_to_current=False)`, update `scan.label`, and `resetTimeout()` so the OSD doesn't hide. It stops on abort, on the session ending, or when the scan ends.
- The rest of the hold's repeats are dropped, not taken as speed presses.

**While scanning.** At the top of `onAction`, before the existing handling:

- Right/Left: a tap steps the speed (`Scan.press()`), as in the table above. `HoldDetector` tells taps from a held key's repeats here too: only its `'press'` answers count. So quick taps all count with no wait; a key held during the scan counts twice (the press and its first repeat), then not; and the hold that started the scan does nothing while it stays down.
- Select (OK): apply (below). This comes before the timeline's own OK, which plays and pauses.
- Play, Pause, Play/Pause: apply, and play. Kodi acts on these keys before the add-on sees them (`onPlayBackResumed()`, `seekdialog.py:2399`), so the video has usually already resumed from where it paused, or briefly will. The seek then lands while it plays. If the add-on gets the key while the video is still paused for the scan, `doSeek()`'s `unPauseAfterSeek` resumes it as for OK. Either order ends playing at the scan position, maybe after a moment of playback from the old one.
- Back: cancel (below). This comes before the existing cancel handling, so the OSD stays open and a second Back does what Back does today.
- Up/Down, Page Up/Down: ignored, so they don't leave the timeline (which would abandon the seek), close the OSD or skip chapters mid-scan.
- Stop: stop the scan thread, then the existing stop handling.
- Anything else: ignored.

**Applying.** Stop the thread, then `doSeek(offset=scan.offset)`. If the scan paused the video, `doSeek()` already has the handler resume it when the seek lands (§4). If it was already paused, it stays paused at the new position.

**Cancelling.** Stop the thread, then `resetSeeking()`: it clears the seek, and if the scan paused the video it resumes it. Then `updateProgress()` to put the bar back. No seek.

**Ending for other reasons.** The session ending, playback stopping, or the dialog closing stops the thread and clears the scan state, with no seek.

### 4. Pausing

Reuse the seek pause from `e80db309` rather than a new flag. On starting a scan, if the video is playing: `setSeekPaused('seeking')` and `player.control('pause')`, as `seekByOffset()` does. If the first press of the hold has already done that, there's nothing more to do. Applying and cancelling then resume through `doSeek()` and `resetSeeking()` as they do for a skip, and `onPlayBackPaused()`/`onPlayBackResumed()` already keep the idle timer, `pausedAt` and seek-behind-on-pause (`resume_seek_behind_pause`) out of it.

One gap: the idle check in `onTimeKeeperCallback()` (`seekdialog.py:2545`) starts the idle time whenever `Player.Paused`, the seek pause included. Today each key press clears it (`onAction()`), but a latched scan can run with no presses, and stop-on-idle (`player_stop_on_idle`) could stop playback mid-scan. Skip that check while `_seekPaused` is set. That also covers a skip left pending with auto-seek off.

Plex progress: `tick()` keeps reporting "paused" while scanning. That's accurate, and the seek sends a new position when it's applied.

### 5. Preview thumbnails

Each new thumbnail URL is an HTTP fetch from the server, and the scan thread redraws ten times a second. Even at 2x a tick moves the seek point 6s, and at 16x 48s, so nearly every tick lands on a new thumbnail.

- Change `bif.image` at most every 0.4s while scanning (2.5 fetches a second at most, whatever the speed). That's the limit that matters at these speeds.
- Round the offset passed to `getBifUrl()` to a fixed step (2s to start; to be checked against the server's thumbnail interval), so going back over the same stretch, or the thumbnail shown when the scan stops, reuses a URL already in Kodi's image cache.
- `updateProgress()` blanks `bif.image` before setting it (`seekdialog.py:2244`). While scanning, set it only when the rounded URL changes, so the thumbnail doesn't flicker.
- No thumbnails on the server: the times and the marker still move. Nothing else changes.
- The `blur_chapters` spoiler setting is applied as it is now.

### 6. OSD

- A scan label (`scan.label`, such as "▶▶ 4x" or "◀◀ 8x") in the tempo label's place under the seek point's elapsed time (the `Player.PlaySpeed` label, `script-plex-seek_dialog.xml.tpl:221`, posx 212, posy 30 in the times group), visible while `scan.active` is set, with the tempo label hidden while it is. Skins are templates, so they are recompiled.
- The OSD doesn't hide while scanning: the scan thread calls `resetTimeout()`, and the hide check in `tick()` (`seekdialog.py:2878–2883`, which already postpones hiding for a pending seek) skips hiding while scanning.
- The timeline shows the playing position and the scan position as it does for skips now, and the seek-point times (`time.seek.*`) follow the scan.
- The pending-seek state (`button.seek`) stays set while scanning, so the user can see the position is not applied yet.
- The skip button follows the scan position on each `tick()`, which checks markers at the seek point while `_seeking` (`seekdialog.py:2860–2861`).

### 7. When it's available

- **Direct play, path-mapped and transcoded items.** There's a single seek at the end, as for a skip today, so transcodes work too.
- **Not while waiting for the start-of-playback seek** (`handler.waitingForSOS`), as for skips now.
- **Not for external players** (`player.isExternal`).
- **Not while a seek is already being applied** (`_applyingSeek`).

### 8. Setting

A `BoolSetting` in "Player UI" (`lib/windows/settings.py:791`, next to `player_show_buttons`):

- ID `video_hold_to_scan`, default off.
- Label: "Hold left/right to scan".
- Description: "Hold Left or Right during playback to pause and scan the timeline. Press again to change speed, OK or Play to play from there, Back to cancel. Needs a remote that repeats a held key."
- Strings 35188 and 35189.
- New strings go in `resources/language/resource.language.en_gb/strings.po`.

Read once when the OSD initialises, beside `player_show_buttons` (`seekdialog.py:555`).

## Why not Kodi's fast-forward

Kodi's fast-forward plays the video at 2–32x real time by seeking and showing frames. The speeds here are 60–480x real time, out of its reach. Even at its own speeds:

- Transcodes would stall: a Plex transcode is made as it plays and can't keep up at speed, so it would have to be direct play only.
- Playback passes through intro and credits markers, so auto-skip, countdowns and post-play would need suppressing.
- The handlers would need `onPlayBackSpeedChanged`, and Plex would see a fast-moving "playing" position.
- The picture is jerky, more so over the network.

Scanning the timeline with the video paused has none of these problems. What it loses is a moving picture, which preview thumbnails mostly make up for.

## Not using a keymap

Kodi keymaps support `mod="longpress"`, which would give a real long press. But the add-on would have to write a keymap into the user's `userdata/keymaps`, which applies to all of Kodi, survives uninstalling the add-on, and conflicts with the user's own keymaps. Timing in the add-on is less exact but stays inside it.

## Risks

- **Remotes that don't repeat.** Some HDMI-CEC remotes send one press for a hold. There a hold looks like a short press and nothing new happens: no harm, but no feature. The setting's description says so.
- **Repeat timing differs by device.** If the §1 values are wrong on some remotes, make them advanced settings, not more code.
- **Fast tapping.** Four taps within 0.3s would look like a hold; the quickest measured took 0.39s. A tap within 0.1s of the last is taken as a repeat and ignored (seen once, 0.084s).
- **The pause and the first scan tick race.** Pausing takes a moment. The scan works on `selectedOffset` only, so it doesn't matter where the video stops; the seek goes to the scan position either way. Cancelling resumes from wherever it paused, a fraction of a second after the hold started.
- **Marker jumps on short items.** At 16x a 0.1s tick moves the seek point 48s: about 10px along the bar on a two-hour film, but 60px on a 20-minute episode. A shorter tick would smooth it, but each tick is several Python GUI calls, and Kodi slows its render loop while those keep coming. Check on the AM6B before shortening it.
- **Thumbnail load on the server.** Covered by the rounding and throttling in §5; to check on a slow server.
- **A long scan and the Plex session.** Plex sees a paused session for as long as the scan lasts, as with any pause. No change needed.

## Steps

1. `HoldDetector` and `Scan` in `lib/windows/seek_scan.py`, with unit tests (`tests/test_seek_scan.py`):
   - `HoldDetector`: press, the first repeat's longer gap, repeat, hold after the threshold, two taps not a hold, a gap ending a run, a direction change ending a run, `'hold'` reported once per run.
   - `Scan`: speed steps up and down, staying at the top speed, flipping direction past the slowest, advancing by elapsed time, clamping at both ends, reversing from a clamp.
2. The idle check skipped during the seek pause (§4).
3. The setting and its strings.
4. `SeekDialog`: starting, keys while scanning, applying, cancelling and ending (§3), with the conditions in §7.
5. Thumbnail rounding and throttling (§5).
6. The OSD label and hide checks (§6).
7. Device testing: a keyboard, an Android TV remote, a CEC remote and a Kodi app remote (Kore/Yatse), on direct play, path-mapped and transcoded items, with and without preview thumbnails. Check that the video resumes (or stays paused if it was paused), that Back resumes without a seek, Plex's reported progress, the ends of the timeline, the skip button during a scan, and that stop-on-idle and seek-behind-on-pause don't fire.
8. Tune the §1 values, the speed list and the thumbnail step from step 7.

## Decided

- **Latched**, not while-held: the scan carries on after the key is let go. Taps change the speed; past the slowest, 0x stops it, then it reverses.
- **Only the user applies a scan**, with OK or Play/Pause; auto-seek never does. OK keeps a video that was paused before the scan paused; Play/Pause plays.
- **No auto-seek delay of 0:** the setting's lowest is now 0.5s, for everyone (§1).

## Open questions

- **Snap to chapters?** When applying, a scan position within a few seconds of a chapter start could snap to it. After the first build.
