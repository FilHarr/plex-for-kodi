# Preview thumbnails from the whole index file (plan)

## Status

Written 2026-10-20 against `d3f9f17a` (hold/FF to scan). Steps 1-5 built the same day (`lib/windows/bif_index.py`,
`lib/windows/previews.py`, `SeekDialog.startPreviews()`/`previewImage()`), checked against Animal outside Kodi;
step 6 under way: the PC and the AM6B (2026-10-20, scanning felt fine on both; 8 downloads on the AM6B, each ready
in 0.2-0.6 s); a transcode on the PC (three seeks restarting the stream, a scan; one download, kept throughout, folder
emptied at the end). No multi-part item to hand: its offset-to-part mapping (previews.part_at()) is unit-tested
instead. No remote server to test against: the code path is the same, the risk a slow link (see Risks). The
Shield is optional: its remote and key timing were covered by the scan work. Cleanup is at the next item and when the player closes - not on Kodi's "stopped",
which a transcode's seek may also send.

## Why

The video player's preview thumbnails - the moving preview over the seek bar, and the chapter row's cards for
intro/credits markers - are fetched one picture at a time from Plex: `GET /library/parts/<id>/indexes/sd/<ms>`
(`PlexPlayer.getBifUrl()`, `lib/_included_packages/plexnet/plexplayer.py:650`). Plex cuts each picture out of the
item's preview index file (a BIF: a header, an offset table, then the JPEGs) and sends it.

Findings (2026-10-19, Animal, PMS 1.43.5.11029, indexes written by a third-party tool at 5s):

- **The single-picture request can serve the wrong bytes.** For two items (1923 S02E07, Masters of the Universe)
  Plex located every picture as if the index were 10-second with half the pictures, so it returned slices from
  the wrong place - green blocks or black in Kodi, and 500s from Plex's own photo transcoder. The files themselves
  were valid, and structurally identical to working ones; freshly written indexes (1923 S02E06) and Chef were
  served correctly. Most likely Plex kept details of an earlier version of those two files.
- **The official Android TV app didn't use that request** (the only official app checked). On a Shield it made one request per item at
  playback start - `GET /library/parts/<id>/indexes/sd?interval=10000` (5.5MB in 110ms; 4MB in 259ms) - and cut
  every preview out locally. Its previews were clean and frequent during scanning.
- **The whole file was always correct**, at either interval.

## What changes

Each item's index is downloaded once, in the background, soon after its playback starts, and previews are cut out of
it locally. Until it's ready, or if it fails, previews come from the single-picture request as now.

- **Faster previews**: no server round trip per picture. During a scan every update can show a new picture.
- **No dependence on the single-picture request**, so no broken previews from it.
- **One request per item** instead of one per preview.
- **Kodi's texture database stops filling with previews**: images under `special://temp` count as already cached
  (`CTextureCache::IsCachedImage`, Kodi 21), so Kodi loads them directly; each per-picture URL is cached today.

## Design

### 1. Reading an index: `BifIndex`

A Kodi-free class in a new module, `lib/windows/bif_index.py`, so it can be unit-tested:

- `BifIndex(path)`: opens a downloaded index file and reads the header (magic `89 42 49 46 0D 0A 1A 0A`, version,
  picture count, interval in ms - 0 means 1000) and the offset table (timestamp, offset pairs, ending at
  `0xFFFFFFFF`). Raises on a bad magic, a short file or offsets past its end. The file stays on disk; only the
  table is held (8 bytes a picture).
- `index_at(ms)`: the picture at or before a time in that part, from the table's timestamps x interval (not
  assumed even).
- `picture(index)`: that picture's bytes, read from the file.

### 2. Downloading: per part

- **What**: the part's whole index at its own spacing - `part.getIndexPath('sd')` (or `'hd'`, as `getBifUrl()`
  prefers) with no `interval`, so the add-on's previews match the file.
- **When**: once the video is playing - after `onAVStarted` and any resume seek (`handler.waitingForSOS` clear) -
  so it stays out of start-up buffering, and is ready long before anyone opens the OSD. Every part of a multi-part
  item at once (they're small).
- **Where**: `special://temp/<addon id>-previews/<part id>.bif`, written to a `.part` name and renamed when
  complete, so a half-written file is never read.
- **How**: a background thread, with the add-on's own HTTP handling (timeouts, the server's connection). The debug
  log gets its size and time.
- **Remote connections too**, to start with.
- A failure (HTTP error, timeout, a file `BifIndex` rejects) is logged once and leaves that part on the
  single-picture request.

### 3. Showing a preview

- `SeekDialog.updateProgress()` and the marker cards ask for a preview by time, through one method that returns
  either a local path or today's URL: the local picture once its part's index is ready, else `getBifUrl()`.
- A local picture is written once to `special://temp/<addon id>-previews/<part id>/<index>.jpg` and reused - a
  name per picture, so Kodi never shows a stale image under a reused name.
- **Blurred previews** (the `blur_chapters` spoiler setting) stay on the server path: Plex's image service blurs
  them, and Kodi's Python has no image library to do it locally.
- **Scanning**: with local pictures the 0.4s limit on changing the picture (`SCAN_BIF_INTERVAL`) only protected the
  server, so it drops to every scan update - to check on the AM6B, where each change is a JPEG decode. The scan's
  rounding step (`SCAN_BIF_STEP`) only matters for the fallback; local pictures are picked by the index's own
  timestamps.

### 4. Cleaning up

- An item's index and pictures are deleted when its playback ends or the next item in a play queue starts.
- At the first playback of a session, the previews folder is cleared of anything left by a crash.

## Parked: chapter cards

File chapters' cards still use Plex's chapter pictures through its photo transcoder. For Masters of the Universe
(101044) the transcoder served stale copies of chapters 2-11 after they were regenerated (keyed by the source
address, at any size; a changed address gave the current ones), Kodi's texture cache keeps whatever it got, and
Plex gives one version's chapter pictures (the 1080p) whichever version plays. Proposed: cut file chapters' cards
from the downloaded index too, as marker cards already are (onPreviewsReady()); blurred ones stay on the server.

## Options for later

Not built at first; added if the defaults prove wrong somewhere:

- Preview thumbnails: download the whole index (default) / one picture at a time (today's behaviour).
- Download over remote connections: on (default) / local network only.
- Index spacing: the file's own (default) / 10 seconds (the official apps', half the download).

## Risks

- **The download competes with playback** on a slow remote connection. It starts after playback is under way and
  is small (4-11MB for a 5s index of a 2-hour film); the remote option above is the fallback if it matters.
- **Storage**: up to the index plus the pictures cut from it in the temp folder - about 11MB + 8MB for a long film
  - on the AM6B's internal storage, deleted when playback ends.
- **Many small file writes** while scanning on the AM6B. Each is a single ~6KB write; check scanning feel there.
- **Index variants**: `hd` indexes, and items whose index Plex lists but can't serve - both fall back.

## Steps

1. `BifIndex` with unit tests (`tests/test_bif_index.py`): synthetic indexes - header fields, the table, `index_at()`
   at and between pictures and past the end, interval 0, bad magic, a truncated file, offsets past the end.
2. The per-part download and its temp file handling, with the fallback on failure.
3. Previews through the one lookup method: the moving preview and the marker cards; blurred previews unchanged.
4. Cleanup at the end of playback, at the next queue item, and at the first playback.
5. Scanning: drop the 0.4s limit when local; check on the PC, the Shield and the AM6B.
6. Live checks: 1923 S02E07 and Masters (broken single pictures) show clean previews; a multi-part item; a
   transcode; a remote connection; the temp folder empties after playback.
