# Plex Uno settings audit (branch `Uno-revamp` @ 9a74261, compared with upstream 1.14.1 @ 2707bbe7)

## How settings work in this add-on

There are two separate settings surfaces. Both write to the same Kodi add-on settings store.

| Surface | Defined in | Reached from | When changes are read |
|---|---|---|---|
| **Outside the add-on** (Kodi's add-on settings dialog) | `resources/settings.xml` | Kodi > Add-ons > Plex Uno > Configure, and the Screensaver "Settings" button | Most go through `lib/addonsettings.py` (`util.addonSettings`), read once at startup and again on restore from Minimise (`monitor.py` → `reInitAddon()`). Several are also baked into module-level values at import (`util.DEBUG`, `util.useSolidBackground`, `UI_INTERVAL`, the Cron tick rate, the worker count, and the HTTP timeouts in `plex.py`), so in practice they need a restart. |
| **Inside the add-on** (Plex's own Settings screen) | `lib/windows/settings.py` → `Settings.SETTINGS` | User menu > Settings (`library.py:1612/1704`) | Mostly read live with `util.getSetting()` / `getUserSetting()` at the point of use. A few relied on `change:<id>` listeners in upstream's `HomeWindow`. Those listeners went when `HomeWindow` was retired (12675d11) and nothing replaced them (see §1.2). |

The upstream convention is that settings.xml holds advanced, diagnostic and restart-only tunables, and the in-add-on screen holds what a normal user changes. That still seems the right split for Plex Uno. Two things belong in settings.xml as well: anything needed when the add-on can't start or open its own screen (debug, kiosk), and the screensaver's own options. The recommendations below use that rule.

Legend for **Verdict**: ✅ keep as is · 🔀 move · 🔧 fix (works, but something about it is wrong) · 🗑 remove or re-wire (no longer does anything).

---

## 1. Headline findings

### 1.1 Settings that no longer do anything (all pre-date the branch; the branch removed their only consumer)

| Setting | Surface | Why it's dead now |
|---|---|---|
| `handle_plexdirect` (partly; see §1.6) | in-add-on, Network | Upstream `HomeWindow.checkPlexDirectHosts()` wrote plex.direct host entries to advancedsettings.xml. It was deleted with `HomeWindow` in 12675d11 and not ported. The commit message says "Everything HomeWindow did now lives on LibraryWindow", so this looks accidental. The only remaining read is `plex.py:429`, where "never" turns off the native-resolve check. **"Ask" and "Always" now behave identically and never write a mapping.** |
| `force_pd_mapping` | in-add-on, Network | Only consumer was `checkPlexDirectHosts()`. |
| `honor_plextv_dnsrebind`, `honor_plextv_pam` | settings.xml, System | Only consumer was `checkPlexDirectHosts()`. |
| `ignore_docker_v4` | settings.xml, System | Read only in `PlexHostsManager.newHosts()` (`plex_hosts.py:61`), which nothing calls any more. |
| `hubs_linear` | in-add-on, UI | Upstream `HomeWindow.showHubs()` re-fetched random hubs sorted ("Linear Hubs"). Neither `library_hubs.py` nor `library.py` reads it. |
| `path_mapping_indicators` (see §1.7) | in-add-on, UI | Upstream used `PathMappingProbeTask` to set `is.mapped` on section items. `sidebar.xml.tpl:178/187` still draws the indicator, but nothing in Python sets `is.mapped` any more, and `PathMappingProbeTask` is unreferenced. |
| `continue_use_thumb` | settings.xml, UI | Only consumer was `HomeWindow` (episode stills in the 16:9 Continue Watching row). Episode tiles in `library_hubs.createEpisodeListItem()` now always use `Episode.defaultThumb`, which is the season or show poster depending on `hub_season_thumbnails`. |
| `background_art_opacity_amount2` | settings.xml, UI | The hero art passes `opacity=100` explicitly (`kodigui.py:628`). The only other caller is the music track ListItem's `landscape` art (`player.py:3062`), and no template reads `landscape`. |
| `use_bg_fallback` | settings.xml, UI | In `default_background.xml.tpl` the fallback image sits under the flat `FF111111` fill whenever dynamic backgrounds are on. When they're off, the solid-colour path hides the whole group. Its XML dependency only enables it when dynamic backgrounds are **on**, which is exactly when it's covered. It's only visible on the user-select screen (`script-plex-user_select.xml.tpl`). |
| `hubs_rr_max` (no UI any more) | `addonsettings.py` proxy | The XML entry was removed with round-robin. The proxy remains, and its only reader is `ExtendHubTask` (`home.py:614`), which 12675d11 left unreferenced. |
| `low_drift_timer`, `intro_skip_early` | `addonsettings.py` proxy | No UI and no reader. This was already the case upstream. |
| `'privacy'` section | in-add-on | An empty tuple in `Settings.SETTINGS` that isn't in `SECTION_IDS`. This was already the case upstream. |

### 1.2 Settings that are saved but no longer take effect when changed in the add-on

Upstream `HomeWindow` subscribed to `change:<id>` and `theme_relevant_setting` (home.py:2300–2317 @ 2707bbe7). `LibraryWindow.hookSignals()` (`library.py:1779`) only re-subscribes `change:update_source`. As a result:

| Setting | Effect of changing it now |
|---|---|
| `watched_indicators`, `hide_aw_bg` (both `theme_relevant=True`) | They are baked into the compiled XML by `render_templates()`. Nothing listens to `theme_relevant_setting`, so **the change only shows after something else forces a recompile**: an add-on update, a display-resolution change, or `always_compile_templates` turned on. |
| `debug` (in-add-on copy) | `logging.DEBUG_LOG` checks `addonSettings.debug`, which is cached. Upstream's `setDebugFlag` refreshed it. Now it only applies after a restart or restore from Minimise. |
| `map_button_home` | `util.homeButtonMapped()` runs once at import. Upstream re-ran it on `change:map_button_home`. A newly bound key now only works after a restart. |
| `no_episode_spoilers4`, `spoilers_allowed_genres2`, `hub_season_thumbnails`, `use_watchlist` | Upstream marked Home dirty so it rebuilt on return. They are still read when a screen or row is built, so the effect is delayed rather than lost. Rows already on screen keep the old images or titles until they're rebuilt. |

### 1.3 Update settings are inert in Plex Uno

`service_runner.py:39` only runs the update loop when `ADDON_ID == UPSTREAM_ADDON_ID`, which is deliberate so Uno never installs `script.plexmod` zips. `FROM_KODI_REPOSITORY` checks `name == "PM4K for Plex"`, so the settings are still **shown**:
- `auto_update_check`, `update_check_startup`, `update_source` (in-add-on, System) do nothing.
- In About, "Last update check" always shows the epoch, and "Service running" shows an empty version because `service.version` is only set inside the update loop.
- `update_interval_hours` and `update_branch` (no UI) are also inert.

Recommendation: hide these while `ADDON_ID != UPSTREAM_ADDON_ID`, until Uno has its own update source.

### 1.4 Wording that the branch has made inaccurate

- **"Home:" prefixes**: `home_confirm_actions` is also read by `library_grid.py:557` and `mixins/common.py:100`. `home_inprogress_resume` applies to hub rows on every Recommended tab (`library_hubs.py`). `hub_season_thumbnails` changes `Episode.defaultThumb`, which is used everywhere. The prefix should go, or become "Rows:".
- **Old add-on ID in help text**: help text names `addon_data/script.plexmod` or `script.plexmod/...`, but the files are read from Uno's own profile or path. Affected: `path_mapping` (33001), `use_cert_bundle` (33052), `cache_size`/`readfactor` (32954). Only `lav_mode_auto_switch` gets the `.replace()` fix.
- **"PM4K" / "PlexMod"** in `kiosk.always` (33736) and `disable_mouse_input` (35054).
- **`osd_hide_delay`** help says "Only works with Plextuary skin". Uno now requires Plextuary.
- **`dynamic_backgrounds`** ("Show dynamic background art") now also gates the hero-art box and the 4-corner colour panel, which are the core of Uno's look. The label undersells what turning it off does.
- **Integer editors** (`IntegerSetting` → `editInteger()`) always title the input "Enter Port Number" (T 32417). That is wrong for the newer integer settings `see_more_added_limit`, `shuffle_catchup_series_count` and `shuffle_catchup_episode_threshold`.
- **Per-user settings aren't marked**. `showSettings()` sets the `useraware` property, but `script-plex-settings.xml.tpl` never reads it. Users rely on descriptions saying "User-specific", and some don't.

### 1.5 Pre-existing quirks worth fixing while you're there

- `osd_hide_delay` has `<dependency type="enable" setting="auto_seek">`. The OSD hide delay has nothing to do with auto-seek, so turning off auto-seek greys it out for no reason (upstream bug).
- Readers and definitions disagree on some defaults. This only matters if the stored value is empty:
  - `auto_skip_offset`: proxy 2.5 vs XML 1.
  - `intro_marker_max_offset`: proxy 600 vs XML 1400.
  - `audio_ac3dts`: `mediadecisionengine.py:230` reads with default False vs definition True.
  - `gdm_discovery`: `gdm.py:37` reads with default True vs False elsewhere.
- `requests_timeout_read` help says "Default: 10", but the default is 5.
- `worker_count` slider goes to 32, but `backgroundthread.py:314` caps it at 3 unless Python is free-threaded.
- `initial_seek_blackout` has no description.

### 1.6 Detail: plex.direct handling (`handle_plexdirect` and its four companion settings)

**The problem it solved.** Plex servers mostly advertise secure connections as `https://1-2-3-4.<hash>.plex.direct:32400`. That hostname is meant to resolve through public DNS to the IP embedded in it (`1.2.3.4`). Many routers and DNS filters (Pi-hole, pfSense, Fritz!Box and others) have DNS-rebind protection: they refuse to return a private LAN IP for a public domain name, so the name doesn't resolve.

The add-on has two kinds of network traffic, and only one is affected:
- **The add-on's own Python requests** never hit the problem. `plexnet/http.py:39` (`pgetaddrinfo`) replaces `socket.getaddrinfo` and reads the IP straight out of the hostname. Its docstring says this "does not apply to Kodi requests (assets etc.)".
- **Kodi's own requests** do hit it, because they go through Kodi's resolver. That covers posters and artwork, which Kodi's texture loader fetches, and the video stream when Kodi's player opens the URL. With rebind protection on, the add-on connects fine, but artwork is blank and playback fails.

**What upstream did** (`HomeWindow.checkPlexDirectHosts()`, home.py @ 2707bbe7, plus `lib/plex_hosts.py`):
1. **When it ran:** on `loaded:server_connections` (servers loaded from cache or from plex.tv), and again on Home re-init after `force_pd_mapping` changed (`setHostsDirty`).
2. **Which connections it collected:** plex.direct connections from stored and plex.tv servers.
   - It **skipped a server** when `honor_plextv_dnsrebind` (the server's `dnsRebindingProtection` flag is 0) or `honor_plextv_pam` (not on the same network and never seen on the LAN) said the server didn't need it. The exception was a server with a plex.direct name that actually failed to resolve (`anyPDHostNotResolvable`).
   - It **always included a server** when its active connection was a plex.direct name that didn't resolve natively. Each connection's `PlexConnection.checkNativeResolve()` records that check. `force_pd_mapping` also forced inclusion.
3. **How it compared:** it checked those hostnames against the `<hosts>` block already in `special://profile/advancedsettings.xml` (`PlexHostsManager.load()`).
4. **New hostnames** went into `pdm.newHosts()`. It left out Docker-internal `172.16.0.0/12` addresses (`ignore_docker_v4`), unless that address was the one that wasn't resolving.
5. **If there were new ones:**
   - With `handle_plexdirect = ask`, it showed a dialog (T 32993/32994): "N unhandled plex.direct connections found… write them to advancedsettings.xml?" The answers were **Yes**, **Always** (switches the setting to `always`) and **Never** (switches it to `never`).
   - With `ask` (after Yes) or `always`, `pdm.write()` rewrote advancedsettings.xml with a managed block:
     ```xml
     <hosts><!-- managed by PM4K -->
       <entry name="192-168-1-10.abc123.plex.direct">192.168.1.10</entry>
     </hosts>
     ```
     Kodi's `<hosts>` works like a hosts file, so after a Kodi restart Kodi resolved those names itself. Upstream then showed a notice saying a restart was needed (T 32995/32996): a dialog the first time, a notification after that.
6. **`never`** skipped all of the above and set `plexnet.util.NO_HOST_CHECK`, so connections didn't test native resolution either.

**What the branch kept.** Only step 6's flag survives (`plex.py:429`), along with startup loading of the existing mappings: `pdm.getOrigHosts()` → `SKIP_HOST_CHECK`, so mapped names aren't re-tested. `plex_hosts.py` is intact, but nothing calls `newHosts()` or `write()`. `checkPlexDirectHosts()` and its `loaded:server_connections` hook were deleted with `HomeWindow` in 12675d11 and not ported.

**What losing it means in practice.**
- **Existing users still work.** Mappings already in advancedsettings.xml stay, and they belong to the Kodi profile, not the add-on. Plex Uno installed beside the stock add-on inherits whatever the stock add-on wrote.
- **New cases silently break.** A fresh Kodi profile, a new server, a server whose IP changes, or a new connection behind rebind protection gets no mapping. The symptom is missing artwork and failed playback, with no prompt explaining why.
- **Multiple servers widen the gap.** More servers means more plex.direct hostnames that may need mapping.

**Options.**
- **Restore it (recommended).** Port `checkPlexDirectHosts()` onto `LibraryWindow`: hook `loaded:server_connections` in `hookSignals()` and show the Ask dialog on the main thread with `postUI()`. It's mostly the deleted method plus its signal hook.
- **Retire it.** Collapse `handle_plexdirect` to an on/off "Check plex.direct resolution" switch. Delete `force_pd_mapping`, `honor_plextv_dnsrebind`, `honor_plextv_pam` and `ignore_docker_v4`, and document the router DNS-rebind exemption as what users should do instead.

### 1.7 Detail: path-mapping indicators (`path_mapping_indicators`, and the broken-share check it sat beside)

**What it was.** The setting drew a small status dot on each library entry in the section list whose files are path-mapped. Path mapping means the library is played straight from a Kodi-side share (SMB, NFS or a local path, via `path_mapping.json`) instead of being streamed over HTTP from the server.

**What upstream did** (`HomeWindow.showSections()` and `PathMappingProbeTask`, home.py @ 2707bbe7):
- **Building the list:** whenever `pmm.mapping` was non-empty, each library item got two properties.
  - `is.mapped` showed a grey dot meaning "this library plays from a mapped path". It was only set when `path_mapping_indicators` was on, so the setting was purely decorative.
  - `is.mapped.broken` showed a red dot meaning "this library's mapped share is unreachable". It was set whether or not the setting was on, because a broken mapping is an error rather than decoration.
- **Checking the shares:** `PathMappingProbeTask` checked each mapped library's Kodi-side root with `pmm.verifyMapping()`, which asks Kodi whether the folder exists. It ran on a background thread because a dead SMB or NFS share blocks until the mount times out.
  - It ran when the list was built, then again every 60 seconds (`PATH_MAPPING_PROBE_INTERVAL`) from `HomeWindow.tick()` while nothing was playing. That way a share that came back lost its red dot without a full refresh.
- **Notifying you:** an unreachable share raised one notification for the whole run, "Path mapping unavailable for: Movies / TV…" (T 35037), rather than one per library. Each failure was announced once (`pmm.claimNotification()`).
- **Applying changes:** `change:path_mapping_indicators` marked Home dirty, so the dots appeared or disappeared on return.

**What the branch kept.**
- **Template:** `includes/sidebar.xml.tpl:176–193` still draws both dots on the sidebar icon, grey (`FF666666`) and red (`FFCC2222`).
- **Data:** the section properties `isMapped`, `mappedPaths` and `mappingBroken` (`plexlibrary.py:184–215`) and the `pmm` state machine (`path_mapping.py`) are intact.
- **Playback:** if a mapped file is missing at play time, `plexpart.py:192` calls `pmm.reportMappedFileMissing()`. That re-checks the share, notifies "Mapped path unavailable" (T 35035) or "Mapped file missing, streaming from the server instead" (T 35036), and playback falls back to the server.

**What's gone.**
- **Nothing sets `is.mapped` or `is.mapped.broken`.** `SidebarMixin.buildSectionList()` (`windowutils.py`) doesn't read the setting, so neither dot ever shows.
- **`PathMappingProbeTask` (`home.py:522`) is unreferenced.** Its commit (12675d11) lists it as deliberately left dead code. There is no background check of the shares and no notification while browsing. You only find out a share is down when you press play, and then only for that title.

So the setting is dead, and the more useful part beside it is gone too: the red "share is down" dot and its notification weren't controlled by the setting.

**Options.**
- **Restore it (recommended, at least the red dot).**
  1. In `SidebarMixin.buildSectionList()`, when `pmm.mapping` is set, set `is.mapped.broken` on each library entry, plus `is.mapped` when `path_mapping_indicators` is on.
  2. Start `PathMappingProbeTask` from `LibraryWindow` after the sidebar is built.
  3. Re-run the check from `LibraryWindow.tick()` every 60 seconds while nothing is playing, next to the reachability check.
  4. In the probe's callback, refresh `is.mapped.broken` on the sidebar items.

  The sidebar is built per screen, so every screen showing it should read the current state from `section.mappingBroken`, not only Home.
- **Retire it.** Remove the setting and the two template dots. The playback-time notification would then be the only signal that a share is down.

---

## 2. Settings outside the add-on (`resources/settings.xml`)

### 2.1 General (category `general`)

This category is a grab-bag. It mixes diagnostics, kiosk, subtitle titles, a video cap, image scaling, library paging, playlists and the user cache.

| Setting | What it does | Where read | Still makes sense? | Location / verdict |
|---|---|---|---|---|
| `debug` | Debug logging | `util.py:125`, `logging.py:82` (cached) | Yes | 🔧 Keep a copy here, because you need it when the add-on won't start. It is the same ID as the in-add-on System copy. Fix live refresh (§1.2). Move to System in this file. |
| `debug_requests` | Logs HTTP requests | `main.py:63`, `plex.py:420` (startup) | Yes | 🔀 Keep outside, but move to System next to `debug`. |
| `kiosk.always` | Auto-start even when Kodi isn't on a Home-type window | `service_runner.py:34` (only when `kiosk.mode` is on) | Yes | 🔀 It is split from its parents `kiosk.mode` and `kiosk.delay`, which are in-add-on Main. Move it in-add-on next to them; the service reads it with `ADDON.getSetting`, so either surface works. Fix "PM4K" in the help text. |
| `subtitle_use_extended_title` | Use Plex's `extendedDisplayTitle` for subtitle names | `plexstream.py:57` (live) | Yes | 🔀 It's user-facing. Move in-add-on to Audio/Subtitles. |
| `unlock_res` | Allow Direct Play above 4K | `plex.py:336` | Yes | 🔀 Move in-add-on to Video next to `allow_4k`, or at least out of General. |
| `poster_resolution_scale_perc` | Thumbnail transcode size % | `util.py:482` (restart) | Yes | ✅ Restart-only tunable, fine outside. Better under a UI/Images group. |
| `background_resolution_scale_perc` | Background transcode size % | `util.py:1016` (now also sizes the hero art) | Yes | ✅ Same as above. |
| `retrieve_all_media_up_front` | Load whole library at once | `library_grid.py:1773/2212` | Yes | ✅ Advanced. A "Library" group would read better than General. |
| `library_chunk_size` | Items per library page | `library.py:676/678` | Yes | ✅ As above. |
| `playlist_max_size` | Items loaded into a Kodi playlist before PlayQueue windowing | `playlist.py`, `playqueue.py:810` (the music player rebuilt on PlayQueues uses it) | Yes, more so now | ✅ Advanced. Better under Player or Playlists than General. |
| `cache_home_users` | Cache Plex Home users | `library.py:1599`, `myplexaccount.py:40` | Yes | ✅ Better under System or Network. |

### 2.2 Player (category `player`)

| Setting | What it does | Where read | Still makes sense? | Location / verdict |
|---|---|---|---|---|
| `osd_hide_delay` | Seconds before the OSD hides | `seekdialog.py:188` (overridden by `Skin.String(SkinHelper.AutoCloseVideoOSD)`) | Yes | 🔧🔀 Remove the bogus `auto_seek` dependency and the outdated Plextuary caveat. User-facing, so move in-add-on to Player UI. |
| `auto_seek` | Seek after a delay instead of OK | `seekdialog.py:189/235` | Yes | 🔀 User-facing seek behaviour. Move in-add-on to Player UI with its delay. |
| `auto_seek_delay` | The delay | `seekdialog.py:189` | Yes | 🔀 With `auto_seek`. |
| `kodi_skip_stepping` | Use Kodi's skip steps | `seekdialog.py:263` | Yes | ✅/🔀 Could go in-add-on with the seek group. Fine here as advanced. |
| `dynamic_timeline_seek` | Apply those steps on the timeline too | `seekdialog.py:236` | Yes | Same as above. |
| `coreelec_resume_seek_wait2` | Alt-seek retry wait | `player.py:1236` | Yes (when alt-seek is on) | ✅ Expert tunable. Its parent `use_alternate_seek2` is in-add-on Main, so group these under an "Alternate seek (advanced)" heading whose help says where the toggle lives. |
| `altseek_valid_seek_window` | Alt-seek tolerance | `player.py`, `seekdialog.py` | Yes | ✅ As above. |
| `coreelec_seek_prefer_reported` | Alt-seek uses reported time | `player.py:712/1099` | Yes | ✅ As above. |
| `coreelec_wait_player_time1` | Alt-seek waits for valid time | `player.py:719` | Yes | ✅ As above. |
| `seamless_branching_lav_mode` | LAV mode used by the SB fix | `seamless_branching.py:274` | Yes, on CoreELEC builds that support it | 🔀 Its parent `lav_mode_auto_switch` is in-add-on Main and only shown when `CE_SB_LAV_SWITCH`. This one shows on every platform. Fine as expert, but say what it depends on. |
| `seekbackonstart_delay` | Delay inside "Seek back on start" | `player.py:1069/1072` | Yes | ✅ Expert. Parent `seek_back_on_start` is in-add-on Player UI. |
| `show_media_ends_info` | Show time left / ends-at | `seekdialog.py:253` | Yes | 🔀 User-facing OSD option. Move in-add-on to Player UI. |
| `show_media_ends_label` | "Ends at" label | `seekdialog.py:254` | Yes | 🔀 With the above. |
| `player_show_buffer` | Buffer on timeline | `seekdialog.py:595/2014` | Yes | 🔀 OSD option. Move in-add-on to Player UI, or keep as advanced. |
| `buffer_wait_max` | Slow-connection buffer wait | `seekdialog.py:2231` | Yes (only with `slow_connection`) | ✅ Expert. Parent `slow_connection` is in-add-on System, so mention that in the help. |
| `buffer_insufficient_wait` | As above | `seekdialog.py:2287` | Yes | ✅ As above. |
| `consecutive_video_pb_wait` | Pause between queued videos | `player.py:2668` | Yes | ✅ Compatibility workaround. Fine outside. |

### 2.3 Markers (category `markers`)

| Setting | What it does | Where read | Still makes sense? | Location / verdict |
|---|---|---|---|---|
| `auto_skip_offset` | Shift auto-skip target | `seekdialog.py:2575/2663` | Yes | ✅ Tunable. Align the proxy default (§1.5). |
| `skip_intro_button_timeout` | How long Skip Intro shows | `seekdialog.py:251` | Yes | 🔀 User-facing. Move in-add-on next to Player UI's "Show buttons → Skip Intro". |
| `skip_credits_button_timeout` | Same for credits | `seekdialog.py:252` | Yes | 🔀 As above. |
| `skip_intro_button_show_early_threshold2` | Window for "show intro skip early" | `seekdialog.py:460` | Yes | ✅ Tunable. Parent `show_intro_skip_early` is in-add-on (per user / per show). |
| `intro_marker_max_offset` | Ignore late intro markers | `seekdialog.py:417` | Yes | ✅ Tunable. Align the proxy default (§1.5). |
| `skip_marker_timer_cancel` | Back cancels an auto-skip countdown | `seekdialog.py:939/941` | Yes | 🔀 User-facing behaviour. Better in-add-on next to the auto-skip options. |
| `skip_marker_timer_immediate` | OK skips immediately | `seekdialog.py:940/948/1064` | Yes | 🔀 As above. |

### 2.4 User Interface (category `user_interface`)

| Setting | What it does | Where read | Still makes sense? | Location / verdict |
|---|---|---|---|---|
| `fast_back` | Back leaves instead of first jumping to item 0 | `library_grid.py:431`, `mixins/common.py:85` (hub rows now always reset first via `backResetRows`) | Partly; it now only affects grids and extras | 🔧 Reword it to say what it covers now. Could move in-add-on. |
| `dynamic_backgrounds` | Art backgrounds; now also the hero-art box and colour panel | `util.py:131` (startup), `kodigui.py`, `library_grid.py`, `videoplayer.py`, `currentplaylist.py` | Yes, and central to Uno | 🔧 Relabel or describe (§1.4). Keep outside, because `useSolidBackground` is computed at import. |
| `dbg_crossfade` | Crossfade hero art and panel | `kodigui.py:472/709/733` | Yes | ✅ |
| `background_colour` | Solid colour when dynamic backgrounds are off | `util.py:131`, `kodigui.py:451` | Yes | ✅ |
| `custom_background_colour` | Custom AARRGGBB | `kodigui.py:454` | Yes | ✅ |
| `background_art_blur_amount2` | Server-side blur of background art | `util.py:1019` (now blurs the hero-art box) | Questionable: a blurred focal box next to a sharp colour panel works against the new design | 🔧 Decide whether the hero box should take it. If not, pass `blur=0` as with opacity and drop the setting. |
| `background_art_opacity_amount2` | Server-side dimming | Effectively nowhere (§1.1) | No | 🗑 |
| `use_bg_fallback` | Legacy fallback image | Only visible on user-select (§1.1) | Barely | 🗑, or re-scope it to "sign-in background" and fix the inverted dependency. |
| `continue_use_thumb` | Episode stills in Continue row | Nowhere (§1.1) | No longer wired | 🗑, or re-wire it in `createEpisodeListItem()` if you want episode stills in 16:9 rows. |
| `episode_no_spoiler_blur` | Blur strength for spoiler images | `seekdialog.py:1916/2169`, `mixins/spoilers.py:95` | Yes | 🔀 Its siblings (`no_episode_spoilers4`, `spoilers_allowed_genres2`) are in-add-on UI. Move it next to them. |
| `playlist_visit_media` | Playlist item opens the item instead of playing it | `playlist.py:247/298` | Yes | 🔀 User-facing. Move in-add-on to UI. |
| `theme_music_fade` | Fade theme music | `library.py:2687`, `mixins/thememusic.py` | Yes | 🔀 Move in-add-on to Main next to `theme_music` and `theme_music_loop`. |

### 2.5 Screensaver (category `screensaver`)

| Setting | What it does | Where read | Still makes sense? | Location / verdict |
|---|---|---|---|---|
| `screensaver_quiz` | Quiz mode in the photo screensaver | `slidehshow.py:30` | Yes | ✅ Correctly outside. Kodi's Screensaver "Settings" button opens this dialog. |

### 2.6 System (category `system`)

| Setting | What it does | Where read | Still makes sense? | Location / verdict |
|---|---|---|---|---|
| `cache_templates` | Keep template sources in memory | `render.py:111` | Yes | ✅ Dev/advanced. |
| `always_compile_templates` | Recompile every start | `render.py:101` | Yes; it's also currently the only way to apply indicator changes (§1.2) | ✅ |
| `cache_theme_music` | Cache theme music locally | `mixins/thememusic.py:27` | Yes | ✅ or 🔀 with the other theme-music settings. |
| `verify_mapped_files` | Check mapped paths exist | `plexpart.py:172` | Yes | ✅ Parent `path_mapping` is in-add-on System. |
| `ignore_docker_v4` | Skip Docker IPs in plex.direct mapping | Nowhere live (§1.1) | No | 🗑, or restore plex.direct mapping. |
| `max_shutdown_wait` | Hard-exit timer | `main.py:79/103/196/454` | Yes | ✅ |
| `honor_plextv_dnsrebind` | plex.direct mapping filter | Nowhere (§1.1) | No | 🗑, or restore the mapping. |
| `honor_plextv_pam` | As above | Nowhere | No | 🗑, or restore the mapping. |
| `recheck_server_connections` | Every 60 s alive check, every 10 min full reachability round | `library.py:1833` (`LibraryWindow.tick`) | Yes. Renamed from `periodic_reachability_check` with the default now On, and multi-server makes it more useful | 🔀 This is now a user-visible behaviour of multi-server, so it fits better in-add-on Network. Fine outside if you want it as advanced. The help mentions only the 10-minute round, not the 1-minute alive check. |
| `use_cert_bundle` | CA bundle choice | `plex.py:422–424` | Yes | ✅ Fix the folder name in its help (§1.4). |
| `requests_timeout_connect` | PMS connect timeout | `plex.py:400`, `update_checker.py:130` | Yes | ✅ |
| `requests_timeout_read` | PMS read timeout | `plex.py:399` | Yes | ✅ Help states the wrong default (§1.5). |
| `plextv_timeout_connect` | plex.tv connect timeout | `plex.py:402`, `main.py:123` | Yes | ✅ |
| `plextv_timeout_read` | plex.tv read timeout | `plex.py:401`, `main.py:124` | Yes | ✅ |
| `conn_check_timeout` | Connectivity test timeout | `plex.py:403`, `main.py:125` | Yes, and used more with multi-server | ✅ |
| `local_reach_timeout` | LAN ping timeout | `plex.py:410` | Yes | ✅ |
| `max_retries1` | HTTP retries | `plex.py:419`, `main.py`, `update_checker.py` | Yes | ✅ |
| `tickrate` | Cron Hz | `main.py:246` | Yes | ✅ |
| `ui_wait_rate` | UI poll Hz | `util.py:56` | Yes | ✅ |
| `worker_count` | Background threads | `backgroundthread.py:314` | Yes | 🔧 The slider allows 32, but the value is capped at 3 (§1.5). |
| `requests_cache_expiry` | Expiry for the cached Plex data | `plex.py:421` | Yes | ✅ Parent `cache_requests` is in-add-on System. Say so in the help. |

---

## 3. Settings inside the add-on (`lib/windows/settings.py`)

### 3.1 Main

| Setting | What it does | Where read | Still makes sense? | Location / verdict |
|---|---|---|---|---|
| `kiosk.mode` | Start Plex when Kodi starts | `service_runner.py:32`, `userselect.py:154` | Yes; migration deliberately skips it so Uno and stock don't race | ✅ Bring `kiosk.always` alongside. |
| `kiosk.delay` | Start delay | `service_runner.py:35` | Yes | ✅ |
| `auto_signin` | Skip user select and PIN | `myplexaccount.py:39` | Yes | ✅ |
| `ensure_lastused` | Keep Kodi's last-used add-on position | `main.py:117` | Yes | ✅ or System. |
| `search_use_kodi_kbd` | Kodi keyboard for search | `search.py:107` | Yes; still supported by the rebuilt Search | ✅ The three search settings would read better as a group, or in their own section now that Search is a sidebar screen. |
| `search_limit` *(new)* | Results per type per server | `search.py:850` | Yes | ✅ |
| `search_typing_delay` *(new)* | Debounce | `search.py:328` | Yes | ✅ |
| `theme_music` | Theme music volume / off | `plex.py:339` | Yes | ✅ Add `theme_music_fade` and `cache_theme_music` here. |
| `theme_music_loop` | Loop theme | `player.py:2311` | Yes | ✅ |
| `player_stop_on_exit` *(new)* | Stop playback when Plex exits | `main.py:482` | Yes | ✅ or Player. |
| `use_alternate_seek2` | Alternate seek method | `player.py:317`, `seekdialog.py:222` | Yes | 🔀 A playback mechanic, not a general preference. Move to a Playback section with `seek_back_on_start` and the resume options. |
| `lav_mode_auto_switch` | CoreELEC seamless-branching fix (CE only) | `player.py:2677` | Yes | 🔀 As above, or Video. |
| `assume_resume` | Always resume in-progress items | `windowutils.py:464`, `episodes.py`, `playlist.py`, `preplay.py` | Yes | ✅ or Playback. |

### 3.2 Video

| Setting | What it does | Where read | Still makes sense? | Location / verdict |
|---|---|---|---|---|
| `local_quality2` / `remote_quality2` / `online_quality2` | Max quality per connection type | `plex.py:313–317`, `plexapp.py`; overridden per video from player settings | Yes | ✅ |
| `playback_features` | Direct Play / Direct Stream / 4K | `plex.py:141` | Yes | ✅ |
| `disable_hdr` | Force transcode for HDR | `plexplayer.py:594`, `mediadecisionengine.py:311` | Yes | ✅ |
| `clamp_video_bitrates` | Hide bitrates above source | `playersettings.py:336` | Yes | ✅ |
| `allowed_codecs` | HEVC / VC-1 / AV1 | `plex.py:147` | Yes | ✅ Bring `unlock_res` in here. |

### 3.3 Audio/Subtitles

| Setting | What it does | Where read | Still makes sense? | Location / verdict |
|---|---|---|---|---|
| `audio_clamp_to_orig` | Don't exceed original audio | `plexplayer.py:394` | Yes | ✅ |
| `audio_channels_kodi` | Target Kodi's channel count | `plexplayer.py:395` | Yes | ✅ |
| `audio_force_ac3_cond` | Transcode to AC3 when… | `plexplayer.py:396`, `mediadecisionengine.py:226` | Yes | ✅ |
| `audio_ac3dts` | Treat DTS as AC3 | `plexplayer.py:397`, `mediadecisionengine.py:230` | Yes | 🔧 Default mismatch (§1.5). |
| `audio_disabled_codecs` | Codecs you can't play | `plexplayer.py:434`, `mediadecisionengine.py:254` | Yes | ✅ |
| `audio_transcode_codec` | Transcode target | `plexplayer.py:439` | Yes | ✅ |
| `audio_hires` | Hi-res music Direct Play | `mediadecisionengine.py:491` | Yes | ✅ Arguably a Music setting now that music has its own player. |
| `disable_subtitle_languages` | "Native languages" | Many: `player.py`, `video.py`, `playersettings.py`, `preplay.py`, `episodes.py`, `seekdialog.py`, `subitems.py` | Yes | ✅ |
| `use_external_audio` | External audio files | `player.py:1746`, `video.py:958`, `episodes.py`, `preplay.py` | Yes | ✅ |
| `subtitle_download_from` | Plex / Kodi / Ask | `seekdialog.py:1542` | Yes | ✅ |
| `subtitle_download_fallback` | Fall back to Kodi | `seekdialog.py:1564` | Yes | ✅ |
| `burn_subtitles` | Burn-in policy | `mediadecisionengine.py:375` | Yes | ✅ |
| `burn_ssa` | Burn SSA when Direct Streaming | `plexplayer.py:422` | Yes | ✅ |
| `auto_sync` (per user, per show) | Auto-sync external SRT | `media.py:207`, `playback_utils`, `seekdialog.py` | Yes | ✅ Not marked as per-user in the UI (§1.4). |
| `forced_subtitles_override` | Forced-subtitle fix | `video.py:688` and others | Yes | ✅ |
| `calculate_oshash` | OpenSubtitles hash | `seekdialog.py:1571` | Yes | ✅ Bring `subtitle_use_extended_title` in here. |

### 3.4 User Interface

| Setting | What it does | Where read | Still makes sense? | Location / verdict |
|---|---|---|---|---|
| `plextuary_offer` *(new)* | Offer or install Plextuary at start | `skin_check.py` | Yes | ✅ |
| `plextuary_variant` *(new)* | Which Plextuary build | `skin_check.py:76/222` | Yes; applies next start | ✅ |
| `watched_indicators` | Played-indicator style | `render.py:63` (compile time) | Yes | 🔧 Doesn't apply when changed (§1.2). `hide_aw_bg` could `show_cb` only when the style isn't `none`. |
| `hide_aw_bg` | Hide indicator backdrop | `render.py:81` (compile time) | Yes | 🔧 As above. |
| `clear_logos` *(new)* | Logo instead of title | `util.py:1107` | Yes | ✅ |
| `use_watchlist` (per user) | Watchlist sidebar entry and features | `sidebar_model.py`, `library.py:3116`, `mixins/watchlist.py` | Yes, and more prominent now that it's a sidebar entry | ✅ The sidebar picks it up when next built. Could move to a "Sidebar/Navigation" group. |
| `watchlist_auto_remove` (per user) | Remove watched items | `mixins/watchlist.py:248` | Yes | ✅ |
| `show_ratings` | Ratings on detail screens | `mixins/ratings.py` | Yes | ✅ |
| `show_reviews1` | Reviews on pre-play | `preplay.py:315/1159` | Yes | ✅ |
| `show_directors` (per user) | Directors in cast rows | `episodes.py:3044`, `mixins/roles.py:82` | Yes | ✅ |
| `see_more_recent_months` *(new)* | Reach of recently released/watched rows | `hub_limits.py:53` | Yes | ✅ The editor title is wrong for `see_more_added_limit` (§1.4). |
| `see_more_added_limit` *(new)* | Recently-added See more cap | `hub_limits.py:57` | Yes | 🔧 The editor title says "Enter Port Number". |
| `no_episode_spoilers4` | Spoiler rules | `seekdialog.py:203`, `mixins/spoilers.py:21` | Yes | ✅ Bring `episode_no_spoiler_blur` here. |
| `spoilers_allowed_genres2` | Genres exempt | `mixins/spoilers.py:27` | Yes | ✅ |
| `home_confirm_actions` | Confirm mark played and similar | `library_grid.py:557`, `library_hubs.py:2096/2121`, `mixins/common.py:100` | Yes | 🔧 Drop "Home:" (§1.4). |
| `disable_exit_on_back` | Back at Home root never exits | `library.py:2706` | Yes; still reached at Home's root | ✅ |
| `hub_season_thumbnails` | Season vs show poster for episodes | `video.py:1223` (`Episode.defaultThumb`, global) | Yes | 🔧 Drop "Home:". It now also decides the 16:9 episode tile image (§1.1, `continue_use_thumb`). |
| `home_inprogress_resume` | Resume from rows directly | `library_hubs.py:1916/2058` | Yes | 🔧 Drop "Home:"; it also applies on Recommended tabs. |
| `hubs_linear` | Non-random hub variants | Nowhere | No | 🗑, or re-implement in `library_hubs`. |
| `path_mapping_indicators` | Sidebar mapped-library badge | Nowhere (template still draws it) | No | 🗑, or re-wire `PathMappingProbeTask` to set `is.mapped` in `SidebarMixin.buildSectionList()`. |
| `map_button_home` | Key for Home | `util.py:118` (import time) | Yes; Home is still a destination | 🔧 Change needs a restart (§1.2). |

### 3.5 Player UI

| Setting | What it does | Where read | Still makes sense? | Location / verdict |
|---|---|---|---|---|
| `player_official` | Plex-style OSD navigation | `seekdialog.py:205` | Yes | ✅ |
| `preplay_preroll` (per user) | Play pre-rolls | `preplay.py:771` | Yes | ✅ These three are pre-play behaviour, not player UI. A "Movies/Cinema" or Playback group fits better. |
| `preplay_preroll_first` (per user) | Pre-rolls before trailers | `preplay.py:772` | Yes | As above. |
| `preplay_trailers` (per user) | Cinema trailers count | `preplay.py:773` | Yes | As above. |
| `no_osd_time_spoilers` | Hide time without OSD | `seekdialog.py:204` | Yes | ✅ |
| `player_show_buttons` (per user) | Which OSD buttons | `seekdialog.py:240/512` | Yes | ✅ Bring the skip-button timeouts here. |
| `fast_pause_resume` (per user) | OK pauses / resumes | `seekdialog.py:206` | Yes | ✅ `show_cb` on `player_official` would match its own description. |
| `video_show_playlist` | Playlist button | `seekdialog.py:526` | Yes | ✅ |
| `video_show_prevnext` | Prev/next button | `seekdialog.py:534` | Yes | ✅ |
| `resume_offset` | Resume-point adjustment | `plexplayer.py:211/214` | Yes | 🔀 These and the next six are playback mechanics, not UI. A Playback section would hold them with `use_alternate_seek2`, `lav_mode_auto_switch` and `assume_resume`. |
| `resume_seek_behind` | Seek back after pause | `seekdialog.py:218` | Yes | 🔀 As above. |
| `resume_seek_behind_pause` | …on pause | `seekdialog.py:219` | Yes | 🔀 As above; `show_cb` on `resume_seek_behind`. |
| `resume_seek_behind_after` | …after N s | `seekdialog.py:220` | Yes | 🔀 As above. |
| `resume_seek_behind_onlydp` | …only Direct Play | `seekdialog.py:221` | Yes | 🔀 As above. |
| `seek_back_on_start` | Seek forward then back at start | `player.py:2764` | Yes | 🔀 As above. |
| `initial_seek_blackout` | Black screen during initial seek | `player.py:2752` | Yes | 🔀🔧 As above, plus it needs a description. |
| `player_stop_on_idle` | Stop after idle | `seekdialog.py:217` | Yes | ✅ |
| `player_stop_on_screensaver` | Stop on screensaver | `monitor.py:178` | Yes | ✅ or System with the sleep/wake actions. |

### 3.6 Playback (user-specific)

| Setting | What it does | Where read | Still makes sense? | Location / verdict |
|---|---|---|---|---|
| `show_chapters` (per user) | Chapters on timeline | `seekdialog.py:634` | Yes | ✅ |
| `virtual_chapters` (per user) | Markers as chapters | `seekdialog.py:635/1931` | Yes | ✅ `show_cb` on `show_chapters`. |
| `combined_chapters` (per user) | Both | `seekdialog.py:1931` | Yes | ✅ As above. |
| `auto_skip_in_transcode` (per user) | Auto-skip when transcoding | `seekdialog.py:620` | Yes | ✅ |
| `post_play_never` (per user) | No post-play | `player.py:431/494` | Yes | ✅ |
| `post_play_auto` (per user) | Autoplay next | `videoplayer.py:518` | Yes | ✅ |
| `postplay_timeout` (**global**) | Countdown. Moved in from settings.xml by a7d98ec6; default now 10 (was 16) | `player.py:448`, `videoplayer.py:537` | Yes | 🔧 Global setting in a "user-specific" section. Make it per user, or move it. |
| `postplay_always` (**global**) | Post-play for videos of 5 minutes or less. Moved in by a7d98ec6 | `player.py:447` | Yes | 🔧 As above. |
| `binge_mode` (per user, per show) | Binge mode | `playback_utils`, `playbacksettings.py` | Yes | ✅ |
| `auto_skip_intro` (per user, per show) | | `playback_utils` | Yes | ✅ |
| `auto_skip_credits` (per user, per show) | | `playback_utils` | Yes | ✅ |
| `show_intro_skip_early` (per user, per show) | | `playback_utils`, `seekdialog.py:624` | Yes | ✅ |
| `skip_post_play_tv` (per user, per show) | Continuous episodes | `playback_utils` | Yes | ✅ |
| `tv_specials_order` (**global**) | Specials in the queue | `subitems.py`, `episodes.py:2116`, `library_grid.py:750` | Yes | 🔧 Global in the user section. |
| `shuffle_catchup_series_count` (**global**) | Catch-up shuffle | `library_grid.py:749` | Yes | 🔧 Global in the user section, and the editor title is wrong. |
| `shuffle_catchup_episode_threshold` (**global**) | Catch-up shuffle | `library_grid.py:748` | Yes | 🔧 As above. |

### 3.7 Network

| Setting | What it does | Where read | Still makes sense? | Location / verdict |
|---|---|---|---|---|
| `local_mode` | No plex.tv | `main.py`, `plex.py:430`, `localmode.py` (with change listener) | Yes | ✅ |
| `allow_insecure` | Insecure connection policy | `plexconnection.py:233`, `plexserver.py:879`, `localmode.py` | Yes | ✅ |
| `smart_discover_local` | Check servers really are LAN | `plex.py:395` (with listener) | Yes | ✅ |
| `prefer_local` | Local over secure | `plex.py:396` (with listener) | Yes | ✅ |
| `gdm_discovery` | GDM | `gdm.py` | Yes, and local mode uses GDM regardless | 🔧 Default mismatch (§1.5). |
| `handle_plexdirect` | plex.direct DNS handling | `plex.py:429` only | Partly (§1.1) | 🔧 Restore the mapping, or reduce it to a single on/off "Check plex.direct resolution". |
| `force_pd_mapping` | Force mapping | Nowhere | No | 🗑, or restore. |
| `manual_ip_0/1`, `manual_port_0/1` | Manual servers | `plex.py:151–155` (`getManualConnections`, with listeners) | Yes. Local mode adds `local_servers_json` beside them | ✅ Bring `recheck_server_connections` here. |

### 3.8 System

| Setting | What it does | Where read | Still makes sense? | Location / verdict |
|---|---|---|---|---|
| `auto_update_check` | Periodic update check | `service_runner.py:41`, `update_checker.py:255` | Not in Uno (§1.3) | 🔧 Hide for Uno. |
| `update_check_startup` | Check at start | `update_checker.py:47` | Not in Uno | 🔧 Hide for Uno. |
| `update_source` | Beta / Stable / Repository | `update_checker.py:49`, `library.py:1779` | Not in Uno | 🔧 Hide for Uno. |
| `cache_requests` | SQLite cache for items and libraries | `plexobjects.py`, `video.py`, `plexlibrary.py`, `library.py` and others | Yes | ✅ |
| `persist_requests_cache` | Keep cache across runs | `plex.py:185/215` | Yes | ✅ |
| `exit_default_is_quit` | Exit dialog defaults to Quit Kodi | `library.py:1525` | Yes | ✅ or Main. The code's fallback label is a copy-paste ("Start Plex On Kodi Startup"); harmless because T(32965) exists. |
| `path_mapping` | Honour path_mapping.json | `path_mapping.py:62`, `util.py:830`, `library.py:3290` | Yes | 🔧 Fix the folder name in its help. |
| `cache_size` | Kodi buffer MB (writes advancedsettings) | `lib/cache.py` (kcm) | Yes | ✅ |
| `readfactor` | Kodi read factor | `lib/cache.py` (kcm) | Yes | ✅ |
| `slow_connection` | Wait for buffer and refreshes | `episodes.py`, `seekdialog.py`, `preplay.py`, `thememusic.py`, `cache.py` listener | Yes | ✅ |
| `onss_library_back_home` | Go to Home root on screensaver | `monitor.py:181` → `LibraryWindow.goHomeRoot` | Yes. Still meaningful, though Home and libraries are now the same window | ✅ The rationale in its description (heavy library views) may want re-checking against the new screens. |
| `disable_mouse_input` *(new)* | Turn off Kodi mouse while running | `plex.py:393` (with listener) | Yes | ✅ Fix "PlexMod" in the text. |
| `action_on_sleep` | Sleep action | `monitor.py:111` | Yes | ✅ |
| `action_on_wake` | Wake action / wait | `library.py:1910` | Yes | ✅ |
| `debug` | Debug logging (same ID as the XML copy) | as in §2.1 | Yes | 🔧 No live effect (§1.2). |
| `dump_config` | Dump settings to log | `main.py:296` | Yes | ✅ |

### 3.9 About (read-only info)

`addon_version`, `kodi_version`, `platfom_version` (sic), `screen_res`, `addon_path`, `userdata_path` are fine. `server_version` was updated by the branch to list every sidebar server, which is good. `service_status` and `i_last_update_check` are meaningless for Uno (§1.3).

---

## 4. Suggested target layout

**Outside (settings.xml)**: advanced, diagnostic, restart-only and screensaver settings.
- *Diagnostics*: `debug`, `debug_requests`, `dump_config` (duplicate it here too)
- *Images & templates*: `poster_resolution_scale_perc`, `background_resolution_scale_perc`, `dbg_crossfade`, `background_colour`, `custom_background_colour`, `background_art_blur_amount2` (if kept), `cache_templates`, `always_compile_templates`
- *Library & playlists*: `retrieve_all_media_up_front`, `library_chunk_size`, `playlist_max_size`, `cache_home_users`, `requests_cache_expiry`, `verify_mapped_files`
- *Playback (advanced)*: the alt-seek and CoreELEC tunables, `seekbackonstart_delay`, `seamless_branching_lav_mode`, `buffer_wait_max`, `buffer_insufficient_wait`, `consecutive_video_pb_wait`, `unlock_res` (if not moved in)
- *Markers (advanced)*: `auto_skip_offset`, `intro_marker_max_offset`, `skip_intro_button_show_early_threshold2`
- *Network & performance*: timeouts, retries, `use_cert_bundle`, `tickrate`, `ui_wait_rate`, `worker_count`, `max_shutdown_wait`
- *Screensaver*: `screensaver_quiz`

**Inside (Plex Settings)**: everyday preferences.
- *Main*: kiosk (`kiosk.mode`, `kiosk.delay`, + `kiosk.always`), `auto_signin`, `ensure_lastused`, theme music (+ `theme_music_fade`, `cache_theme_music`), `exit_default_is_quit`, `player_stop_on_exit`
- *Search*: the three search settings
- *Video / Audio & Subtitles*: as now, + `unlock_res`, `subtitle_use_extended_title`
- *Interface*: as now, minus the dead ones, + `episode_no_spoiler_blur`, `playlist_visit_media`, `fast_back`, `dynamic_backgrounds` (relabelled; needs a restart prompt or live handling)
- *Player UI*: OSD, buttons and seeking UX (+ `osd_hide_delay`, `auto_seek`, `auto_seek_delay`, `show_media_ends_*`, `player_show_buffer`, skip-button timeouts, `skip_marker_timer_*`)
- *Playback*: resume and seek mechanics, alternate seek, SB fix, pre-rolls and trailers, `assume_resume`, specials order, catch-up shuffle, post-play timeout and short videos
- *Playback (per user)*: only genuinely per-user settings
- *Network*: as now (+ `recheck_server_connections`)
- *System*: as now, minus the update settings for Uno

Moving an XML-proxied setting in-add-on needs two changes: replace its `addonSettings.<x>` reads with live `getSetting()` reads (or a change listener), and remove it from `_proxiedSettings`. Otherwise it will only apply on restart, which surprises users in a screen where everything else applies at once.

---

## 5. Out of scope (internal state keys, not user settings)

These are stored through the same API but aren't preferences: `auth.token`, `client.ID`, `myplex.*`, `lastServerId.*`, `library.settings.*`, `viewtype.*`, `sort*`, `filter*`, `previous_user`, `theme_version`, `theme_addon_id`, `last_resolution`, `last_update_check`, `last_good_volume`, `migrated_from`, `local_profiles_json`, `local_servers_json`, and the `<setting>.<userID>` per-user copies.
