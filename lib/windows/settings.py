# coding=utf-8
from __future__ import absolute_import
from __future__ import unicode_literals

import json
import sys
import datetime
import types

import plexnet
from kodi_six import xbmc
from kodi_six import xbmcgui
from kodi_six import xbmcaddon
from threading import Timer
from iso639 import languages

import lib.cache
from lib import util
from lib import genres
from lib import actions
from lib import skin_check
from lib.util import T
from . import dialog
from .optionsdialog import messageLines


UNDEF = "__UNDEF__"


def withAddonID(text):
    """Help text naming the add-on's own folders: every translation names them with the stock add-on's ID,
    so a renamed copy (script.plexmod-uno) swaps in its own."""
    if util.ADDON_ID == util.UPSTREAM_ADDON_ID:
        return text
    return text.replace(util.UPSTREAM_ADDON_ID, util.ADDON_ID)


#MAIN_LANGUAGES = [l for l in languages if l.part1]
#SEP_LANGUAGES= [l for l in languages if l.part2t and l not in MAIN_LANGUAGES]

class Setting(object):
    type = None
    ID = None
    label = None
    desc = None
    default = None
    userAware = False
    isThemeRelevant = False
    backport_from = None
    show_cb = None

    def translate(self, val):
        return str(val)

    def should_show(self):
        return self.show_cb() if self.show_cb else True

    def get(self, *args, **kwargs):
        _id = kwargs.pop("_id", UNDEF)
        use_id = _id if _id != UNDEF else self.ID
        default = kwargs.pop("default", UNDEF)
        use_default = default if default != UNDEF else self.default

        value = util.getSetting(use_id, use_default)
        if value == use_default and self.backport_from:
            # fallback set and we're on default
            old_val = util.getSetting(self.backport_from, DEFAULT)

            # old setting was set
            if old_val != DEFAULT:
                # get correct old value
                old_val_cast = util.getSetting(self.backport_from, use_default)
                util.setSetting(self.backport_from, '')

                # old value is different from the new one, set
                if old_val_cast != use_default:
                    self.set(old_val_cast, skip_get=True)
                    value = old_val_cast
        return value

    def emit_events(self, id_, val, **kwargs):
        plexnet.util.APP.trigger('change:{0}'.format(id_), value=val)

    def emit_tr_events(self, id_, val, **kwargs):
        plexnet.util.APP.trigger('theme_relevant_setting', id=id_, value=val, **kwargs)

    def set(self, val, skip_get=False):
        if not skip_get:
            old = Setting.get(self)
            setRet = util.setSetting(self.ID, val)
            if old != val:
                util.DEBUG_LOG('Setting: {0} - changed from [{1}] to [{2}]', self.ID, old, val)
                self.emit_events(self.ID, val)
                if self.isThemeRelevant:
                    self.emit_tr_events(self.ID, val)
        else:
            setRet = util.setSetting(self.ID, val)
        return setRet

    def valueLabel(self):
        return self.translate(self.get())

    def __repr__(self):
        return '<Setting {0}={1}>'.format(self.ID, self.get())


class BasicSetting(Setting):
    def __init__(self, ID, label, default, desc='', theme_relevant=False, backport_from=None, show_cb=None):
        self.ID = ID
        self.label = label
        self.default = default
        self.desc = desc
        self.isThemeRelevant = theme_relevant
        self.backport_from = backport_from
        if show_cb:
            self.show_cb = show_cb
        util.DEFAULT_SETTINGS[ID] = default

    def description(self, desc):
        self.desc = desc
        return self


class ListSetting(BasicSetting):
    type = 'LIST'
    options = ()

    def translate(self, val):
        return self.options[len(self.options) - 1 - val]

    def optionLabels(self):
        return self.options

    def optionIndex(self):
        return len(self.options) - 1 - self.get()

    def set(self, val, skip_get=False):
        BasicSetting.set(self, len(self.options) - 1 - val, skip_get=skip_get)


class QualitySetting(ListSetting):
    options = (
        T(32001),
        T(32017),
        T(32002),
        T(32016),
        T(32003),
        T(32004),
        T(32005),
        T(32015),
        T(32006),
        T(32007),
        T(32008),
        T(32009),
        T(32010),
        T(32011),
        T(32012),
        T(32013),
        T(32014),
    )


class ThemeMusicSetting(ListSetting):
    options = [
        T(32481),
    ] + [T(32482) % {"percentage": 10+i} for i in range(0, 100, 10)]


class BoolSetting(BasicSetting):
    type = 'BOOL'


class UserAwareSetting(BasicSetting):
    """
    A user-aware BoolSetting
    """
    userAware = True

    def __init__(self, *args, **kwargs):
        super(UserAwareSetting, self).__init__(*args, **kwargs)
        util.USER_SETTINGS.append(self.ID)

    @property
    def userAwareID(self):
        if plexnet.plexapp.ACCOUNT and plexnet.plexapp.ACCOUNT.ID:
            return '{}.{}'.format(self.ID, plexnet.plexapp.ACCOUNT.ID)
        return 'USER_AWARE'

    def emit_events(self, id_, val, **kwargs):
        plexnet.util.APP.trigger('change:{0}'.format(self.ID), key=self.userAwareID, value=val, skey=self.ID)

    def get(self, *args, **kwargs):
        _id = kwargs.pop("_id", UNDEF)
        default = kwargs.pop("default", UNDEF)
        return super(UserAwareSetting, self).get(*args,
                                                 _id=_id if _id != UNDEF else self.userAwareID, default=default,
                                                 **kwargs)

    def set(self, val, skip_get=False):
        if not skip_get:
            old = self.get(_id=self.userAwareID)
            if old != val:
                util.DEBUG_LOG('Setting: {0} - changed from [{1}] to [{2}]', self.userAwareID, old, val)
                self.emit_events(self.userAwareID, val)
                if self.isThemeRelevant:
                    self.emit_tr_events(self.userAwareID, val)
        return util.setSetting(self.userAwareID, val)


class BoolUserSetting(UserAwareSetting, BoolSetting):
    pass


class OptionsSetting(BasicSetting):
    type = 'OPTIONS'

    def __init__(self, ID, label, default, options, **kwargs):
        BasicSetting.__init__(self, ID, label, default, **kwargs)
        self.options = options
        self.optionDescs = {}

    def optionDescriptions(self, descs):
        """Help for single options, {option ID: text}: shown in the description panel while that option has focus
        in the setting's picker of values (SettingsPickers.valueProps()); an option without its own shows none."""
        self.optionDescs = descs
        return self

    def translate(self, val):
        for ID, label in self.options:
            if ID == val:
                return label

    def optionLabels(self):
        return [o[1] for o in self.options]

    def optionIndex(self):
        val = self.get()
        for i, o in enumerate(self.options):
            if val == o[0]:
                return i

        return 0


DEFAULT = "__DEFAULT__"


class MultiOptionsSetting(OptionsSetting):
    type = 'MULTI'
    valueLabelDelim = ', '
    noneOption = None

    def __init__(self, ID, label, default, options, none_option=None, **kwargs):
        super(MultiOptionsSetting, self).__init__(ID, label, [], options, **kwargs)
        self.default = default
        self.noneOption = none_option
        util.JSON_SETTINGS.append(self.ID)

        # fixme: not sure why we initialize default with an empty list in the supercall
        util.DEFAULT_SETTINGS[ID] = default

    def get(self, *args, **kwargs):
        with_default = kwargs.pop('with_default', True)
        val = super(MultiOptionsSetting, self).get(*args, default=DEFAULT, **kwargs)
        if val and val != DEFAULT:
            try:
                return json.loads(val)
            except json.decoder.JSONDecodeError:
                # fallback for legacy settings that weren't json
                for o in self.options:
                    if o[0] == val:
                        return [val]
        elif val == DEFAULT:
            # backport old separated options
            ret = self.default[:]
            for o in self.options:
                lval = util.getSetting(o[0], DEFAULT)
                # we only support backporting booleans right now
                if lval != DEFAULT:
                    if lval == "true" and o[0] not in self.default:
                        ret.append(o[0])
                    elif lval == "false" and o[0] in self.default:
                        ret.remove(o[0])

            if ret != self.default:
                self.set(ret, skip_get=True)
                return ret
        return with_default and self.default or []

    def set(self, val, skip_get=False):
        super(MultiOptionsSetting, self).set(json.dumps(val), skip_get=skip_get)

    def translate(self, val, return_str=False, delim=", "):
        if isinstance(val, (list, tuple, set)):
            # keep options order
            data = [super(MultiOptionsSetting, self).translate(o[0]) for o in self.options if o[0] in val]
            if return_str:
                return delim.join(data)
            return data
        return super(MultiOptionsSetting, self).translate(val)

    def valueLabel(self, values=None):
        vals = values or self.get()
        if vals:
            return self.translate(vals, return_str=True, delim=self.valueLabelDelim)
        return T(33056, "None")

    def optionIndex(self):
        val = self.get()
        ret = []
        for i, o in enumerate(self.options):
            if o[0] in val:
                ret.append(i)
        return ret


class MultiUAOptionsSetting(MultiOptionsSetting, UserAwareSetting):
    pass


class UAListSetting(ListSetting, UserAwareSetting):
    def __init__(self, ID, label, default, options, **kwargs):
        super(UAListSetting, self).__init__(ID, label, default, **kwargs)
        self.options = options

    def set(self, val, skip_get=False):
        val = len(self.options) - 1 - val
        return UserAwareSetting.set(self, val, skip_get=True)


class KCMSetting(OptionsSetting):
    key = None

    def emit_events(self, id_, val, **kwargs):
        plexnet.util.APP.trigger('change:{0}'.format(self.ID), value=val)

    def get(self, *args, **kwargs):
        return getattr(lib.cache.kcm, self.key)

    def set(self, val, skip_get=False):
        if not skip_get:
            old = self.get()
            if old != val:
                util.DEBUG_LOG('Setting: {0} - changed from [{1}] to [{2}]', self.ID, old, val)
                self.emit_events(self.ID, val)

        lib.cache.kcm.write(**{self.key: val})


class BufferSetting(KCMSetting):
    key = "memorySize"


class ReadFactorSetting(KCMSetting):
    key = "readFactor"


class InfoSetting(BasicSetting):
    type = 'INFO'

    def __init__(self, ID, label, info):
        BasicSetting.__init__(self, ID, label, None)
        self.info = info

    def valueLabel(self):
        if isinstance(self.info, types.FunctionType):
            return self.info()
        return self.info


class PlatformSetting(InfoSetting):
    def __init__(self):
        InfoSetting.__init__(self, None, None, None)
        self.ID = 'platfom_version'
        self.label = T(32410, 'Platform Version')

    def valueLabel(self):
        plat = None
        try:
            if sys.version_info[0] >= 3:
                from lib import distro
                dist = distro.linux_distribution()
                if dist and len(dist) > 1:
                    plat = u'{0} {1}'.format(dist[0], dist[1])
            else:
                import platform
                dist = platform. dist()
                if dist and len(dist) > 1:
                   plat = u'{0} {1}'.format(dist[0], dist[1])
                else:
                   plat = platform.platform()
                   plat = u'{0} {1}'.format(plat[0], '.'.join(plat[1].split('.', 2)[:2]))
        except:
           util.ERROR()

        plat = plat.strip()

        if not plat:
            if xbmc.getCondVisibility('System.Platform.Android'):
                plat = 'Android'
            elif xbmc.getCondVisibility('System.Platform.OSX'):
                plat = 'OSX'
            elif xbmc.getCondVisibility('System.Platform.Darwin'):
                plat = 'Darwin'
            elif xbmc.getCondVisibility('System.Platform.Linux.RaspberryPi'):
                plat = 'Linux (RPi)'
            elif xbmc.getCondVisibility('System.Platform.Linux'):
                plat = 'Linux'
            elif xbmc.getCondVisibility('System.Platform.Windows'):
                plat = 'Windows'

        return plat or T(32411, 'Unknown')


class ServerVersionSetting(InfoSetting):
    def valueLabel(self):
        # each server's: the sidebar's, else every one on the account
        from . import sidebar_model
        servers = sidebar_model.sidebarServers() or plexnet.plexapp.SERVERMANAGER.getServers()
        return u' \u00b7 '.join(u'{0} {1}'.format(s.name, s.rawVersion or '?') for s in servers)


class IPSetting(BasicSetting):
    type = 'IP'


class IntegerSetting(BasicSetting):
    type = 'INTEGER'


class KeySetting(BasicSetting):
    type = 'STRING'

    def value_setter(self):
        w = SchnorchelDialog()
        timeout = Timer(w.timeout, w.close)
        timeout.start()
        w.doModal()
        timeout.cancel()
        choice = w.key
        del w
        return choice

    def get(self, as_code=False, *args, **kwargs):
        code = super(KeySetting, self).get(default=None, *args, **kwargs)
        if as_code:
            return code

        if code is not None and code != "None":
            ak = actions.ActionKey(int(code))
            return ak

class Settings(object):
    SETTINGS = {
        'main': (
            T(32000, 'Main'), (
                BoolSetting('kiosk.mode', T(32043, 'Start Plex On Kodi Startup'), False),
                OptionsSetting(
                    'kiosk.delay', T(33651, 'Start Delay'),
                    0,
                    [(0, T(32481))] + [
                        (a, T(33091).format(sec_or_ms=a, unit_s_or_ms="s")) for a in
                        list(range(1, 11, 1)) + list(range(15, 125, 5))]
                ),
                BoolSetting(
                    'auto_signin', T(32038, 'Automatically Sign In'), False
                ).description(
                    T(32100, 'Skip user selection and pin entry on startup.')
                ),
                BoolSetting(
                    'ensure_lastused', T(34062, 'Ensure Kodi Addon position'), True
                ).description(
                    T(34063, 'When not run from the Program addons section, our lastused value will not be updated. Make sure it does when the addon exits.')
                ),
                BoolSetting(
                    'search_use_kodi_kbd', T(32955, 'Use Kodi keyboard for searching'), False
                ),
                OptionsSetting(
                    'search_limit', T(35152, 'Search results per type'), 50,
                    [(a, str(a)) for a in (10, 20, 30, 50, 75, 100)]
                ).description(
                    T(35153, 'How many results of each type a search asks each server for. A title in '
                             'more than one library takes a place for each copy. More finds more, but '
                             'is slower on low-powered devices.')
                ),
                OptionsSetting(
                    'search_typing_delay', T(35154, 'Search typing delay'), 1.0,
                    [(a, T(33091).format(sec_or_ms='{0:g}'.format(a), unit_s_or_ms="s")) for a in (0.5, 1.0, 1.5, 2.0)]
                ).description(
                    T(35155, 'How long Search waits after you stop typing, or stop moving around its '
                             'keyboard, before it searches. Shorter shows results sooner; longer searches '
                             'less often while you type.')
                ),
                ThemeMusicSetting('theme_music', T(32480, 'Theme music'), 5),
                BoolSetting(
                    'theme_music_loop', T(33737, 'Loop theme music'), False
                ),
                BoolSetting('player_stop_on_exit', T(35085, 'Stop playback when exiting Plex'), True)
                .description(T(35086, "Stop whatever is playing, and clear Kodi's playlists, whenever the addon "
                                      "exits - including signing out or switching users. Off: playback carries on "
                                      "under Kodi's own player after Plex has closed.")),
            )
        ),
        'video': (
            T(32053, 'Video'), (
                QualitySetting('local_quality2', T(32020, 'Local Quality'), 16),
                QualitySetting('remote_quality2', T(32021, 'Remote Quality'), 16),
                QualitySetting('online_quality2', T(32022, 'Online Quality'), 16),
                MultiOptionsSetting(
                    'playback_features', T(33058, ''),
                    ["playback_directplay", "playback_remux", "allow_4k"],
                    (
                        ('playback_directplay', T(32025, '')),
                        ('playback_remux', T(32026, '')),
                        ('allow_4k', T(32036, '')),
                    )
                ).description(T(33060, "").format(
                    feature_ds=T(32026, ''),
                    desc_ds=T(32979, ''),
                    feature_4k=T(32036, ''),
                    desc_4k=T(32102, ''))),
                BoolSetting(
                    'disable_hdr', T(33660, 'Disable HDR'), False
                ).description(T(33661, "If you don't want your client to handle HDR (or HDR-fallback), "
                                       "enable this to force transcoding. Doesn't apply to DV Profile 5.")
                ),
                BoolSetting(
                    'clamp_video_bitrates', T(33685, 'Clamp video bitrate'), True
                ).description(T(33686, "Only show bitrate targets lower than the current video's bitrate.")
                ),
                MultiOptionsSetting(
                    'allowed_codecs', T(33059, ''),
                    ["allow_hevc", "allow_vc1"],
                    [
                        ('allow_hevc', T(32037, '')),
                        ('allow_vc1', T(32977, '')),
                    ] + ([('allow_av1', T(32601, ''))] if util.KODI_VERSION_MAJOR >= 20 else [])
                ).description(T(33061, "")),
            )
        ),
        'audio': (
            T(32931, 'Audio/Subtitles'), (
                BoolSetting('audio_clamp_to_orig', T(32058, 'Never exceed original audio codec'), True).description(
                    T(32059, 'When transcoding audio, never exceed the original audio bitrate or channel '
                             'count on the same codec.')
                ),
                BoolSetting('audio_channels_kodi', T(32060, 'Use Kodi audio channels'),
                            False).description(
                    T(32061, 'When transcoding audio, target the audio channels set in Kodi.')
                ),
                OptionsSetting(
                    'audio_force_ac3_cond',
                    T(32062, 'Transcode audio to AC3'),
                    'never',
                    (
                        ('never', T(32033, 'Never')),
                        ('always', T(32028, 'Always')),
                        ('2', '>2.0'),
                        ('3', '>2.1'),
                        ('5', '>5.0'),
                        ('6', '>5.1'),
                    )
                ).description(
                    T(32063, 'Transcode audio to AC3 in certain conditions (useful for passthrough).')
                ),
                BoolSetting('audio_ac3dts', T(32064, 'Treat DTS like AC3'),
                            True).description(
                    T(32065, 'When force AC3 settings are enabled, treat DTS the same as AC3 '
                             '(useful for Optical passthrough)')
                ),
                MultiOptionsSetting(
                    'audio_disabled_codecs', T(33665, 'Disable audio codecs'),
                    [],
                    list(sorted([(a, "{} ({})".format(b, a)) for a, b in plexnet.util.AUDIO_CODECS_VERB.items()]))
                ).description(
                    T(33666, "Audio codecs you can't play back. Disables Direct Play for such media items, "
                             "enables Direct Stream if possible, transcodes audio stream to compatible format.")
                ),
                OptionsSetting(
                    'audio_transcode_codec', T(33733, 'Transcode target codec'),
                    "default",
                    [("default", T(32030, 'Auto'))] + list(sorted([(a, "{} ({})".format(b, a)) for a, b in plexnet.util.AUDIO_CODECS_TC_VERB.items()]))
                ).description(
                    T(33734, "Sets the target codec when transcoding/direct streaming. Overridden when "
                             "\"Transcode audio to AC3\" is set.")
                ),
                BoolSetting('audio_hires', T(33079, ''),
                            True).description(
                    T(33080, '')
                ),
                MultiOptionsSetting(
                    'disable_subtitle_languages', T(33691, "Native languages"),
                    [],
                    [(b, a) for a, b in sorted([(l.name, l.part2t) for l in languages if l.part1])]  # +
                    # [(b, a) for a, b in sorted([(l.name, l.part2t) for l in SEP_LANGUAGES])]
                ).description(
                    T(33692, "When you usually watch things in a different language with subtitles, but are a"
                             " native speaker of other languages, which you don't need subtitles for, prevent Plex "
                             "from auto-selecting subtitles for those languages. Also used to match external audio "
                             "files when that setting is enabled. Your Plex \"Preferred Audio Language\" is added to "
                             "this list automatically while your Plex subtitle auto-select mode is \"Shown with "
                             "foreign audio\"; forced subtitles are always kept.")
                ),
                BoolSetting('use_external_audio', T(34098, 'Honor external audio files'), False)
                .description(T(34099, 'When external audio files are found alongside the video '
                                      '(e.g. a separate .dts or .ac3 file), use them. A single external '
                                      'audio file is always used. When multiple are present, the '
                                      'Plex-selected audio language is preferred, then native languages. '
                                      'Selectable in preplay and playback audio settings. '
                                      'Only for mapped Direct Play.')),
                OptionsSetting(
                    'subtitle_download_from',
                    T(33693, 'Download subtitles using'),
                    'plex',
                    (
                        ('ask', T(33694, 'Ask')),
                        ('plex', 'Plex'),
                        ('kodi', 'Kodi'),
                    )
                ).description(T(33695, "Where do you want to download subtitles from? Applies to Download "
                                       "subtitles in the player, from the Subtitles button or the player's Settings. "
                                       "Before playback it always uses Plex.")),
                BoolSetting('subtitle_download_fallback', T(33701, 'Fallback to Kodi'),
                            True).description(
                    T(33702, "When no subtitles are found via the Plex subtitle search, fall back to Kodi "
                             "subtitle search. Only in the player: before playback, subtitles always come from Plex.")
                ),
                OptionsSetting(
                    'burn_subtitles',
                    T(32031, 'Burn-in Subtitles'),
                    'auto',
                    (('auto', T(32030, 'Auto')), ('image', T(32029, 'Only Image Formats')),
                     ('always', T(32028, 'Always')))
                ),
                BoolSetting('burn_ssa', T(32944, 'Burn-in SSA subtitles'),
                            True).description(
                    T(32945, 'When Direct Streaming instruct the Plex Server to burn in SSA/ASS subtitles (thus '
                             'transcoding the video stream). If disabled it will not touch the video stream, but '
                             'will convert the subtitle to unstyled text.')
                ),
                BoolUserSetting('auto_sync', T(33655, 'Auto-Sync Subtitles'),
                            True).description(
                    T(33656, 'Only for External SRT subtitles. The PMS setting for voice activity detection '
                             'has to be enabled for this to work.')
                ),
                BoolSetting('forced_subtitles_override', T(32941, 'Forced subtitles fix'),
                            False).description(
                    T(32493, 'When a media file has a forced/foreign subtitle for a subtitle-enabled language, the Plex'
                             ' Media Server preselects it. This behaviour is usually not necessary and not configurable'
                             '. This setting fixes that by ignoring the PMSs decision and selecting the same language '
                             'without a forced flag if possible. This is skipped when the audio is one of your Native '
                             'languages, so forced subtitles are kept in that case.')
                ),
                BoolSetting('calculate_oshash', T(32958, 'Calculate OpenSubtitles.com hash'),
                            False).description(
                    T(32959, '')
                ),
            )
        ),
        'ui': (
            T(32467, 'User Interface'), (
                BoolSetting(
                    'plextuary_offer', T(35102, 'Offer Plextuary on startup'), True
                ).description(
                    T(35103, "When Plex starts under a different skin, or with a Plextuary font set other than "
                             "Inter UI, offer to switch, installing Plextuary if needed; and remind you when "
                             "Plextuary is too old. Plex's screens are designed around Plextuary's Inter UI "
                             "fonts.")
                ),
                OptionsSetting(
                    'plextuary_variant', T(35099, 'Plextuary variant'), skin_check.AUTO,
                    [(skin_check.AUTO, T(35100, 'Automatic ({0})').format(
                        skin_check.variantName(skin_check.detectedVariant())))] + list(skin_check.VARIANTS),
                    show_cb=lambda: util.getSetting('plextuary_offer', True)
                ).description(
                    T(35101, "Which Plextuary skin to offer when Plex starts. Automatic picks the one built for this "
                             "device; choose another to override it. Takes effect the next time Plex starts.")
                ),
                OptionsSetting(
                    'watched_indicators', T(33022, ''),
                    "modern_2024",
                    (
                        ('none', T(32309, 'None')),
                        ('modern', T(32985, 'Modern')),
                        ('modern_2024', T(33076, 'Modern (2024)')),
                    ),
                    theme_relevant=True
                ).description(
                    T(33023, "")
                ),
                BoolSetting(
                    'hide_aw_bg', T(33024, ''), False, theme_relevant=True
                ).description(
                    T(33025, "")
                ),
                BoolSetting(
                    'clear_logos', T(35046, 'Show title logos on detail screens'), True
                ).description(
                    T(35047, "Replace the written title with the logo image your server has stored for the "
                             "item. Items without a logo keep their written title.")
                ),
                BoolUserSetting(
                    'use_watchlist', T(34007, 'Use Watchlist'), True
                ).description(
                    T(34008, "Activates the current user's Plex watchlist as a section item. Adds watchlist "
                             "functionality to certain media screens. Per-user setting. Default: On")
                ),
                BoolUserSetting(
                    'watchlist_auto_remove', T(34009, 'Watchlist auto-remove'), True
                ).description(
                    T(34010, "Automatically remove fully watched items from watchlist. Default: On")
                ),
                MultiOptionsSetting(
                    'show_ratings', T(33709, 'Show ratings for'),
                    ["series", "movies"],
                    [
                        ('series', T(32393, 'TV Shows')),
                        ('movies', T(32348, 'Movies')),
                    ]
                ),
                MultiOptionsSetting(
                    'show_reviews1', T(33710, 'Show reviews for'),
                    ["watched", "unwatched"],
                    [
                        ('watched', T(33718, 'Watched')),
                        ('unwatched', T(33010, 'Unwatched')),
                    ]
                ),
                BoolUserSetting(
                    'show_directors', T(34061, 'Show directors in cast lists'), True
                ),
                # hub_limits.py
                OptionsSetting(
                    'see_more_recent_months', T(35167, 'Recently released and watched rows go back'), 12,
                    [(a, T(35169, '{0} months').format(a)) for a in (3, 6, 9, 12)]
                ).description(
                    T(35168, 'How far back the Recently Released and Recently Watched rows reach, and '
                             'the See more grids behind them.')
                ),
                IntegerSetting(
                    'see_more_added_limit', T(35170, 'Recently added: See more shows up to'), 50
                ).description(
                    T(35171, "How many items a Recently Added row's See more shows. Recently Added TV "
                             "and Photos are limited to 50 by the Plex server.")
                ),
                MultiOptionsSetting(
                    'no_episode_spoilers4', T(33006, ''),
                    ['unwatched', 'blur_images', 'hide_summary'],
                    (
                        ('unwatched', T(33010, '')),
                        ('in_progress', T(33011, '')),
                        ('no_unwatched_episode_titles', T(33012, '')),
                        ('blur_images', T(33706, '')),
                        ('blur_resume_images', T(33707, '')),
                        # stored as blur_chapters, its name when it blurred them (docs/spoiler-previews.md)
                        ('blur_chapters', T(35190, 'Hide preview thumbnails and chapter images')),
                        ('hide_summary', T(33708, '')),
                        ('hide_ratings', T(33705, '')),
                    )
                ).description(T(35193, "")).optionDescriptions({
                    'no_unwatched_episode_titles': T(35192, ''),
                    'blur_chapters': T(35191, ''),
                }),
                MultiOptionsSetting(
                    'spoilers_allowed_genres2', T(33016, ''),
                    ["Reality", "Game Show", "Documentary", "Sport"],
                    [(g, g) for g in genres.GENRES_TV]
                ).description(T(33017, "")),
                BoolSetting(
                    'home_confirm_actions', T(33663, 'Confirm item actions'), True
                ).description(
                    T(33664, "When acting on items, such as mark played, hide from continue watching etc., "
                             "show a confirmation dialog.")
                ),
                BoolSetting(
                    'disable_exit_on_back', T(35007, 'Home: Disable exit on Back'), False
                ).description(
                    T(35008, "When enabled, pressing Back on the Home screen no longer shows the "
                             "exit prompt and will not exit Plex. You can still exit from the Exit "
                             "option in your username menu.")
                ),
                BoolSetting(
                    'hub_season_thumbnails', T(33740, 'Episodes season thumbnails'), True
                ).description(
                    T(33741, "Use season thumbnails/posters when displaying episodes in hubs instead of "
                             "the TV show's.")
                ),
                BoolSetting(
                    'home_inprogress_resume', T(33713, 'Resume in-progress items'), False
                ).description(
                    T(33714, 'Resume in-progress items directly instead of visiting the media.')
                ),
                BoolSetting(
                    'path_mapping_indicators', T(33032, 'Show path mapping indicators'), True
                ).description(
                    T(33033, "When path mapping is active for a library, display an indicator.")
                ),
                KeySetting('map_button_home', T(33085), None).description(T(33087))
            )
        ),
        'player': (
            T(32940, 'Player UI'), (
                BoolSetting('player_official', T(33045, 'Behave like official Plex clients'), True).description(
                    T(33046, '')),
                BoolUserSetting('preplay_preroll', T(34051, 'Movies: Play pre-rolls'), False).description(
                    T(34052, 'Plays pre-roll clips (server-defined) before playing a movie without a resume '
                             'point. User-specific.')),
                BoolUserSetting('preplay_preroll_first', T(34054, 'Play pre-rolls before trailers'), True).description(
                    T(34055, 'Official Plex clients play the trailers first, then the preroll clips. Enabling '
                             'this will do the opposite. Default: On. User-specific.')),
                UAListSetting(
                    'preplay_trailers', T(34053, 'Cinema Trailers to Play Before Movies'),
                    5,
                    list(map(str, list(range(6))))
                ),
                BoolSetting('no_osd_time_spoilers', T(33004, ''), False, backport_from="no_spoilers").description(
                    T(33005, '')),
                MultiUAOptionsSetting(
                    'player_show_buttons', T(33057, 'Show buttons'),
                    ['subtitle_downloads', 'skip_intro', 'skip_credits'] + (['video_show_vs10'] if util.CE_VS10 else []),
                    (
                        ('subtitle_downloads', T(32932, 'Show subtitle quick-actions button')),
                        ('skip_intro', T(32495, 'Skip Intro')),
                        ('skip_credits', T(32496, 'Skip Credits')),
                    ) + (
                        (('video_show_vs10', T(34090, 'VS10 Mode')),) if util.CE_VS10 else ()
                    )
                ).description(T(32939, 'Only applies to video player UI')),
                BoolSetting('video_hold_to_scan', T(35188, 'Hold left/right to scan'), False).description(
                    T(35189, 'Hold Left or Right during playback to pause and scan the timeline. Press again to '
                             'change speed, OK or Play to play from there, Back to cancel. Needs a remote that '
                             'repeats a held key.')),
                MultiUAOptionsSetting(
                    'fast_pause_resume', T(34012, 'Fast pause/resume'),
                    [],
                    (
                        ('paused', T(34013, 'when paused')),
                        ('playing', T(34014, 'when playing')),
                    )
                ).description(T(34015, 'User-specific. Use OK/ENTER button to pause instead of showing the OSD'
                                       ' (which can then only be accessed using DOWN), or resume when paused. '
                                       'Only works with \'Behave like official Plex clients\' enabled.')),
                OptionsSetting(
                    'player_stop_on_idle',
                    T(32946, 'Stop video playback on idle after'),
                    0,
                    ((0, T(32033, 'Never')), (30, '30s'), (60, '1m'), (120, '2m'), (300, '5m'), (600, '10m'),
                     (900, '15m'), (1200, '20m'), (1800, '30m'), (2700, '45m'), (3600, '1h'),)
                ),
                BoolSetting(
                    'player_stop_on_screensaver', T(32947, 'Stop video playback on screensaver'), False
                ),
            )
        ),
        'player_user': (
            T(32631, 'Playback'), (
                BoolUserSetting(
                    'show_chapters', T(33601, 'Show video chapters'), True
                ).description(
                    T(33602, "If available, show the video file's chapters in a row below the player's buttons "
                             "(press down to reach it).")
                ),
                BoolUserSetting(
                    'virtual_chapters', T(33603, 'Use virtual chapters'), True
                ).description(
                    T(33604, 'When the above is enabled and no video chapters are available, simulate them by using the'
                             ' markers identified by the Plex Server (Intro, Credits).')
                ),
                BoolUserSetting(
                    'combined_chapters', T(35001, 'Combine video & virtual chapters'), True
                ).description(
                    T(35002, 'Combine video & virtual chapters when both are available.')
                ),
                BoolUserSetting(
                    'auto_skip_in_transcode', T(32948, 'Allow auto-skip when transcoding'), True
                ).description(
                    T(32949, 'When transcoding/DirectStreaming, allow auto-skip functionality.')
                ),
                BoolUserSetting(
                    'post_play_never', T(33652, 'Never show Post Play'), False
                ),
                # the rest of post-play's options only apply while it's shown at all
                BoolUserSetting(
                    'post_play_auto', T(32039, 'Post Play Auto Play'), True,
                    show_cb=lambda: not util.getUserSetting('post_play_never', False)
                ).description(
                    T(35098, "When playback ends and a 'Next Up' item is available, play it automatically once the "
                             "post-play countdown finishes.")
                ),
                OptionsSetting(
                    'postplay_timeout', T(32501, 'Time-to-wait between videos on post-play'),
                    10,
                    [(a, T(33091).format(sec_or_ms=a, unit_s_or_ms="s")) for a in range(2, 61)],
                    show_cb=lambda: not util.getUserSetting('post_play_never', False)
                ),
                BoolSetting(
                    'postplay_always', T(35096, 'Show post-play for short videos'), False,
                    show_cb=lambda: not util.getUserSetting('post_play_never', False)
                ).description(
                    T(35097, 'Post-play is normally skipped when a video of 5 minutes or less ends. Turn this on to '
                             'show it for those too.')
                ),
                BoolUserSetting(
                    'binge_mode', T(33618, 'TV binge-viewing mode'), False
                ).description(
                    T(33619, 'Automatically skips episode intros, credits and tries to skip episode recaps. Doesn\'t '
                             'skip the intro of the first episode of a season and doesn\'t skip the final credits of a '
                             'show.\n\nCan be disabled/enabled per TV show.'
                             '\n\nOverrides any playback setting below.')
                ),
                BoolUserSetting(
                    'auto_skip_intro', T(32522, 'Automatically Skip Intro'), False
                ).description(
                    T(32523, 'Automatically skip intros if available. Doesn\'t override enabled binge mode.\nCan be disabled/enabled per TV show.')
                ),
                BoolUserSetting(
                    'auto_skip_credits', T(32526, 'Auto Skip Credits'), False
                ).description(
                    T(32527, 'Automatically skip credits if available. Doesn\'t override enabled binge mode.\nCan be disabled/enabled per TV show.')
                ),
                BoolUserSetting(
                    'show_intro_skip_early', T(33505, 'Show intro skip button early'), False
                ).description(
                    T(33506, 'Show the intro skip button from the start of a video with an intro marker. The auto-skipp'
                             'ing setting applies. Doesn\'t override enabled binge mode.\nCan be disabled/enabled per TV show.')
                ),
                BoolUserSetting(
                    'skip_post_play_tv', T(32973, 'Episodes: Continuous playback'), False
                ).description(
                    T(32974, 'When finishing an episode, don\'t show Post Play but go to the next one immediately.'
                             '\nCan be disabled/enabled per TV show. Doesn\'t override enabled binge mode. '
                             'Overrides the Post Play setting.')
                ),
                OptionsSetting(
                    'tv_specials_order',
                    T(34103, 'Specials in episode queue'),
                    'default',
                    (
                        ('default', T(34105, 'Library default')),
                        ('interleave', T(34107, 'Interleave by air date')),
                    )
                ).description(
                    T(34104, "Library default keeps Plex's order in the queue, with specials at the "
                             "front - playback skips past them and starts at the first regular episode, "
                             "so they appear in the queue but won't play. "
                             "Interleave inserts each special by its original air date and plays them "
                             "between regular episodes.")
                ),
                IntegerSetting(
                    'shuffle_catchup_series_count', T(35014, 'Shuffle Catchup: number of series'), 5
                ).description(
                    T(35015, 'How many series to queue in Catchup shuffle mode.')
                ),
                IntegerSetting(
                    'shuffle_catchup_episode_threshold',
                    T(35016, 'Shuffle Catchup: max unwatched episodes per series'), 3
                ).description(
                    T(35017, 'Only include a series in Catchup mode when it has this many or fewer '
                             'unwatched episodes left.')
                ),
            )
        ),
        'playback_advanced': (
            T(35178, 'Playback (advanced)'), (
                OptionsSetting(
                    'resume_offset', T(34075, "Resume offset adjustment"), -3500,
                    [(0, T(32481))] + [
                        (a, T(33091).format(sec_or_ms=a if a > -1000 else "{:.1f}".format(a / 1000),
                                            unit_s_or_ms="ms" if a > -1000 else "s")) for a in
                        [-100] + list(range(-250, -1000, -250)) + list(range(-1000, -30000, -500))]
                ).description(T(34076, 'When resuming media with a resume point, negatively adjust it by this '
                                       'amount of milliseconds to avoid lost content due to keyframes/seek behaviour. '
                                       'Default: -3.5s')),
                OptionsSetting(
                    'resume_seek_behind', T(33089, ''), 0,
                    [(0, T(32481))] + [
                        (a, T(33091).format(sec_or_ms=a if a < 1000 else int(a / 1000),
                                            unit_s_or_ms="ms" if a < 1000 else "s")) for a in
                        [100] + list(range(250, 1000, 250)) + list(range(1000, 61000, 1000))]
                ).description(T(33090, '')),
                BoolSetting('resume_seek_behind_pause', T(33092, ''), False).description(
                    T(33095, '')),
                OptionsSetting(
                    'resume_seek_behind_after', T(33093, ''), 0,
                    [(0, T(32481))] + [
                        (a, T(33091).format(sec_or_ms=a if a < 1000 else int(a / 1000),
                                            unit_s_or_ms="ms" if a < 1000 else "s")) for a in
                        list(range(250, 1000, 250)) + list(range(1000, 61000, 1000))]
                ).description(T(33094, '')),
                BoolSetting('resume_seek_behind_onlydp', T(33096, ''), True).description(
                    T(33097, '')),
                BoolSetting('seek_back_on_start', T(34049, 'Seek back on start'), util.altSeekRecommended).description(
                    T(34050, "Issue a quick seek forward then back to the start of the video, when we start "
                             "fresh (no resume point, no marker to immediately skip). Can fix A/V desync issues (e.g. "
                             "CoreELEC on Ugoos with passthrough) and embedded subtitles showing late, with certain "
                             "setups. Only for DirectPlay. This still requires a sensible value for \"Delay after "
                             "change of refresh rate\" in Kodi (default: Off, CE/LG: On)")),
                BoolSetting('initial_seek_blackout', T(34060, 'Blackout screen during initial seek'), True)
                .description(T(35176, "While a video that starts part-way in (a resume, a skipped intro or Seek "
                                      "back on start) makes its first seek, keep the screen black so its "
                                      "opening frames don't flash up first.")),
                BoolSetting('use_alternate_seek2', T(33667, 'Use alternate seek'), util.altSeekRecommended).description(
                    T(33668, 'ATTENTION: Only enable this if you have reproducible audio issues after '
                             'seeking/resuming.\n\nUse an alternative seek method in videos, which can help in '
                             'problematic scenarios; brings its own issues/quirks. Disabled by default (enabled by '
                             'default for CoreELEC and LG WebOS)'
                )),
                BoolSetting('lav_mode_auto_switch', T(34073, 'Seamless branching fix'), True)
                .description(withAddonID(T(34074, "Automatically temporarily activate LAV Full or SB mode in "
                                                  "CoreELEC on supported builds to alleviate audio dropouts on "
                                                  "certain titles, if necessary. Based on \"seamless_branching.json\", "
                                                  "can be user-amended by putting a file with the same name and "
                                                  "structure into userdata/addon_data/script.plexmod.")))
                if util.CE_SB_LAV_SWITCH else None,
            )
        ),
        'network': (
            T(33624, 'Network'), (
                BoolSetting('local_mode', T(35021, 'Local mode (no plex.tv)'), False)
                    .description(
                    T(35029, "Only talk to local Plex Media Servers and never contact plex.tv. "
                             "Best enabled via \"Go local\" in the user menu, which prepares local user "
                             "switching while plex.tv is still reachable. Watchlist, Discover and other "
                             "plex.tv-based features are disabled. Takes full effect after a restart of "
                             "the addon.")
                ),
                OptionsSetting(
                    'allow_insecure', T(32032), 'never',
                    (('never', T(32033)), ('same_network', T(32034)), ('always', T(32035)))
                ).description(
                    T(32104, 'When to connect to servers with no secure connections...')
                ),
                BoolSetting('smart_discover_local', T(33625, 'Smart LAN/local server discovery'), True)
                    .description(
                    T(33626, "Checks whether servers returned from Plex.tv are actually local/in your LAN. "
                             "For specific setups (e.g. Docker) Plex.tv might not properly detect a local "
                             "server.\n\nNOTE: Only works on Kodi 19 or above."
                      )
                ),
                BoolSetting('prefer_local', T(33627, 'Prefer LAN/local servers over security'), False)
                    .description(
                    T(33628, "Prioritizes local connections over secure ones. Needs the proper setting in \"Allow "
                             "Insecure Connections\" and the Plex Server's \"Secure connections\" at \"Preferred\". "
                             "Can be used to enforce manual servers."
                      )
                ),
                BoolSetting('gdm_discovery', T(32042, 'Server Discovery (GDM)'), False),
                OptionsSetting(
                    'handle_plexdirect', T(32990), 'ask',
                    (('ask', T(32991)), ('always', T(32035)), ('never', T(32033)))
                ).description(
                    T(32992, 'stub')
                ),
                BoolSetting(
                    'force_pd_mapping', T(34038, 'Force plex.direct mapping'), False
                ).description(T(34039, 'stub')),
                IPSetting('manual_ip_0', T(32044, 'Connection 1 IP'), ''),
                IntegerSetting('manual_port_0', T(32045, 'Connection 1 Port'), 32400),
                IPSetting('manual_ip_1', T(32046, 'Connection 2 IP'), ''),
                IntegerSetting('manual_port_1', T(32047, 'Connection 2 Port'), 32400),
            )
        ),
        'system': (
            T(33600, 'System'), (
                BoolSetting('auto_update_check', T(33672, 'Check for updates'), True)
                .description(T(33673, "Automatically check for updates periodically. If installed from a "
                                      "Kodi repository and the Update Source setting is set to Repository, Kodi "
                                      "itself will handle the updating of this addon. "
                                      "Needs a Kodi restart when changed.")) if util.UPDATER_ENABLED else None,
                BoolSetting('update_check_startup', T(33674, 'Check for updates on start'), True)
                .description(T(33675, "Automatically check for updates on startup. "
                                      "Doesn't do much when Update source is Repository."
                                      "Needs a Kodi restart when changed.")) if util.UPDATER_ENABLED else None,
                OptionsSetting(
                    'update_source',
                    T(33676, 'Update source'),
                    'repository',
                    (('beta', T(33678, 'Beta')), ('stable', T(33679, 'Stable')),
                     ('repository', T(33680, 'Repository')))
                ).description(T(33677, 'Specifies the update mode. Will immediately check for a new version '
                                       'when changed and closing settings.\nDefault: Repository\n\nBeta: Bleeding '
                                       'edge (possibly unstable)\nStable: Stable branch (faster than Repository)\n'
                                       'Repository: Kodi repository (official (slow) or Don\'t Panic)')
                              ) if util.UPDATER_ENABLED else None,
                MultiOptionsSetting(
                    'cache_requests', T(33724, 'Cache Plex data for'),
                    [],
                    [
                        ('items', T(33723, 'Media Items')),
                        ('libraries', T(33722, 'Libraries')),
                    ]
                ).description(T(33727, "Store Plex server responses for items and library views in a local "
                                       "SQLite database. Doesn't cache anything else (Home/Hubs are always up to date)."
                                       " Massively speeds up consecutive visits to items and libraries. Certain "
                                       "important events, such as watch state changes, automatically delete the item "
                                       "cache and its corresponding library cache. The complete cache gets cleared "
                                       "when exiting the addon. (Default: Off)")),
                BoolSetting('persist_requests_cache', T(33725, 'Persist cached Plex data'), False)
                .description(T(33726, "Instead of clearing the cache when exiting the addon, persist it "
                                      "instead. Warning: You'll most likely encounter missing items in libraries "
                                      "or outdated data. Use the corresponding menu functionalities to clear the "
                                      "cache for specific items or libraries.")),
                BoolSetting('exit_default_is_quit', T(32965, 'Quit Kodi on exit by default'), False)
                .description(T(32966, "stub")),
                BoolSetting('path_mapping', T(33000, ''), True).description(withAddonID(T(33001, ''))),
                BufferSetting('cache_size',
                              T(33613, 'Kodi Buffer Size (MB)'),
                              20,
                              [(mem, '{} MB'.format(mem)) for mem in lib.cache.kcm.viableOptions])
                .description(
                    '{}{}'.format(T(33614, 'stub1').format(
                        lib.cache.kcm.free, lib.cache.kcm.recMax),
                        '' if lib.cache.kcm.useModernAPI else ' ' + withAddonID(T(32954, 'stub2')))
                ) if not util.FROM_KODI_REPOSITORY or lib.cache.kcm.useModernAPI else None,
                ReadFactorSetting('readfactor',
                                  T(32922, 'Kodi Cache Readfactor'),
                                  4,
                                  [(rf, str(rf) if rf > 0 else T(32976, 'stub')) for rf in lib.cache.kcm.readFactorOpts])
                .description(
                    T(32923, 'Sets the Kodi cache readfactor value. Default: {0}, recommended: {1}.'
                             'With "Slow connection" enabled this will be set to {2}, as otherwise the cache doesn\'t'
                             'fill fast/aggressively enough.').format(lib.cache.kcm.defRF,
                                                                      lib.cache.kcm.recRFRange,
                                                                      lib.cache.kcm.defRFSM)
                ) if not util.FROM_KODI_REPOSITORY or lib.cache.kcm.useModernAPI else None,
                BoolSetting(
                    'slow_connection', T(32915, 'Slow connection'), False
                ).description(T(32916, "Use with a wonky/slow connection, "
                                       "e.g. in a hotel room. Adjusts the UI to visually "
                                       "wait for item refreshes, asks for library grids' next page further "
                                       "ahead, and waits for the buffer to fill when starting "
                                       "playback.")),
                BoolSetting(
                    'onss_library_back_home', T(34064, 'Return to Home on Screensaver'), util.CE_NEEDS_HOME_ON_SCREENSAVER
                ).description(T(34065, 'When Kodi starts its screensaver, and we are in a library view, '
                                       'return to home. This saves idle energy as the library views are very heavy '
                                       'on the CPU even on idle due to a Kodi bug.'),),
                BoolSetting(
                    'disable_mouse_input', T(35053, 'Ignore mouse and touch input'), True
                ).description(T(35054, 'Turns off Kodi\'s "Enable mouse and touch screen support" setting while '
                                       'PlexMod is running, so controls no longer highlight, focus, or activate on '
                                       'mouseover/click/touch. The original setting is restored when PlexMod exits, '
                                       'so other addons/skins are unaffected. Remote/keyboard navigation is '
                                       'unaffected.\n\nWarning: Mouse/touch navigation isn\'t fully supported and '
                                       'may cause PlexMod to behave unexpectedly. Leave this enabled unless you '
                                       'have a specific reason to use mouse/touch.')),
                OptionsSetting(
                    'action_on_sleep',
                    T(32700, 'Action on Sleep event'),
                    'none',
                    (('none', T(32702, 'Nothing')), ('stop', T(32703, 'Stop playback')),
                     ('home', T(34097, 'Go Home')),
                     ('quit', T(32704, 'Quit Kodi')), ('reboot', T(32426, 'Reboot')),
                     ('shutdown', T(32423, 'Shutdown')),
                     ('hibernate', T(32425, 'Hibernate')), ('suspend', T(32424, 'Suspend')),
                     ('cecstandby', T(32705, 'CEC Standby')), ('logoff', T(32421, 'Sign Out')))
                ).description(T(32701, 'When Kodi receives a sleep event from the system, run the following action.')),
                OptionsSetting(
                    'action_on_wake',
                    T(33070, 'Action on Wake event'),
                    util.altSeekRecommended and 'wait_5' or 'wait_1',
                    [('none', T(32702, 'Nothing')), ('restart', T(33071, 'Restart PM4K'))]
                    + [('wait_{}'.format(s), T(33072, '').format(s)) for s in [1, 2, 3] + list(range(5, 65, 5))]
                ).description(T(33075, '')),
                BoolSetting('debug', T(32024, 'Debug Logging'), False),
                BoolSetting('dump_config', T(33642, 'Debug Logging'), False).description(T(33643)),
            )
        ),
        'about': (
            T(32052, 'About'), (
                InfoSetting('addon_version', T(32054, 'Addon Version'), util.ADDON.getAddonInfo('version')),
                InfoSetting('kodi_version', T(32055, 'Kodi Version'), xbmc.getInfoLabel('System.BuildVersion')),
                PlatformSetting(),
                InfoSetting('screen_res', T(32056, 'Screen Resolution'),
                            xbmc.getInfoLabel('System.ScreenResolution').split('-')[0].strip()),
                ServerVersionSetting('server_version', T(32057, 'Current Server Version'), None),
                InfoSetting('addon_path', T(33616, 'Addon Path'), util.ADDON.getAddonInfo("path")),
                InfoSetting('userdata_path', T(33617, 'Userdata/Profile Path'),
                            util.translatePath("special://profile")),
                InfoSetting('service_status', T(33689, 'Service running'),
                            lambda: "{} ({})".format(
                                util.getGlobalProperty(util.SERVICE_STARTED_PROP) and T(32328, "Yes") or T(32329, "No"),
                                util.getGlobalProperty(util.SERVICE_VERSION_PROP))),
                InfoSetting('i_last_update_check', T(33690, "Last update check"),
                            lambda: util.getGlobalProperty('last_update_check', datetime.datetime.fromtimestamp(0).strftime('%Y-%m-%dT%H:%M:%S.%f')))
                if util.UPDATER_ENABLED else None,
            )
        ),
    }

    SECTION_IDS = ('main', 'video', 'audio', 'ui', 'player', 'player_user', 'playback_advanced', 'network', 'system', 'about')

    def __getitem__(self, key):
        return self.SETTINGS[key]


class SchnorchelDialog(xbmcgui.WindowXMLDialog):
    """
    inspired by https://github.com/pkscout/script.keymap/blob/main/editor.py
    """

    def __new__(cls, *args, **kwargs):
        gui_api = tuple(map(int, xbmcaddon.Addon('xbmc.gui').getAddonInfo('version').split('.')))
        file_name = "DialogNotification.xml" if gui_api >= (5, 11, 0) else "DialogKaiToast.xml"
        return super(SchnorchelDialog, cls).__new__(cls, file_name, "")

    def __init__(self, timeout=10):
        self.key = None
        self.timeout = timeout
        self._winID = None

        self.setProperty("no.image", "1")

    def onInit(self):
        ctrl1, ctrl2 = 401, 402
        if util.SKIN_PLEXTUARY:
            ctrl1, ctrl2 = 1401, 1402
        # each skin decides which of the two is a fadelabel (Plextuary: 1401 is, 1402 is a plain label)
        for controlID, text in ((ctrl1, T(33085)), (ctrl2, T(33086).format(self.timeout))):
            control = self.getControl(controlID)
            if isinstance(control, xbmcgui.ControlFadeLabel):
                control.addLabel(text)
            else:
                control.setLabel(text)

    def setProperty(self, key, value):
        if not self._winID:
            self._winID = xbmcgui.getCurrentWindowId()

        try:
            xbmcgui.Window(self._winID).setProperty(key, value)
            xbmcgui.WindowXML.setProperty(self, key, value)
        except RuntimeError:
            xbmc.log('kodigui.BaseWindow.setProperty: Missing window', xbmc.LOGDEBUG)
        except TypeError:
            # python 2.7
            pass

    def onAction(self, action):
        code = action.getButtonCode()
        action_id = action.getId()
        self.key = None
        if action_id not in (xbmcgui.ACTION_SELECT_ITEM, xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_PREVIOUS_MENU):
            self.key = None if code == 0 else actions.ActionKey(code)
        elif action_id in (xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_PREVIOUS_MENU):
            self.key = None
        else:
            self.key = -1
        self.close()
        return


class SettingsPickerDialog(dialog.SelectDialog):
    """
    The add-on's Settings, as pickers (script-plex-settings_picker.xml.tpl): the option picker beside the sidebar, as
    the Libraries picker - the sections, a section's settings over them and a setting's values over those
    (SettingsPickers) - with the focused row's description (its 'description' property) in a panel to the right,
    as tall as its text. on_context: called with the focused row's choice on Stop or the context menu (a key
    setting's clear), returning (options, selected_idx) to show, or None.
    """
    xmlFile = 'script-plex-settings_picker.xml'

    DESC_BACKDROP_ID = 301
    DESC_SHADOW_ID = 302
    DESC_TEXT_ID = 303
    # The confirm box's message's (optionsdialog.OptionsDialog): font10's 28 lines, and 4 past the last for its
    # descenders. 20 above and below; at most the frame's 876, then it scrolls.
    LINE_HEIGHT = 28
    DESCENDER_ROOM = 4
    PAD = 20
    MAX_LINES = 29

    # the pickers open now, the topmost last: each hides the panel of the one under it, whose place its own takes
    _open = []

    def __init__(self, *args, **kwargs):
        dialog.SelectDialog.__init__(self, *args, **kwargs)
        self.onContext = kwargs.get('on_context')
        self._desc = ''
        self._descHeight = None
        self._descLines = {}

    def onFirstInit(self):
        if self._open:
            self._open[-1].setProperty('covered', '1')
        self._open.append(self)
        dialog.SelectDialog.onFirstInit(self)

    def onClosed(self):
        if self in self._open:
            self._open.remove(self)
        if self._open:
            self._open[-1].setProperty('covered', '')
        dialog.SelectDialog.onClosed(self)

    def onAction(self, action):
        if action in (xbmcgui.ACTION_STOP, xbmcgui.ACTION_CONTEXT_MENU):
            if self.onContext and self.getFocusId() == self.OPTIONS_LIST_ID:
                refreshed = self.onContext(self.options[self.optionsList.getSelectedPosition()][0])
                if refreshed is not None:
                    self.options, self.selectedIdx = refreshed
                    self.showOptions()
            return

        dialog.SelectDialog.onAction(self, action)
        self.fitDescription()

    def showOptions(self):
        if not self.optionsList.size():
            dialog.SelectDialog.showOptions(self)
        else:
            # A refresh (a change, or back from a value picker): the rows updated in place, so the list keeps its
            # scroll and the row stays where it was. Emptied and refilled, the list scrolled from the top just
            # far enough to show it, at the bottom.
            self.optionsList.replaceItems(self.optionItems())
            self.fitFrame(len(self.options))
            self.selectOption()
        self.fitDescription()

    def fitDescription(self):
        """The panel for the row focus is on, its description (the option's 'description' property): the box sized to
        it first, then the text (the template's 'description'), so the textbox lays its lines out in the new size.
        The row is the one SelectDialog has focus going to (lastSelectedItem), not the list's: a selectItem() of
        its own - a refresh, a wrap round - is queued, so the list still reports the row before. None, the panel
        hides (the template), its size kept while it fades. Nothing changed, no GUI calls: this runs on every move."""
        if self._closing:
            return
        pos = self.lastSelectedItem
        option = self.options[pos] if 0 <= pos < len(self.options) else ()
        desc = len(option) > 3 and option[3].get('description') or ''
        if desc == self._desc:
            return
        self._desc = desc
        if desc:
            lines = self._descLines.get(desc)
            if lines is None:
                lines = self._descLines[desc] = max(1, min(messageLines(desc), self.MAX_LINES))
            height = lines * self.LINE_HEIGHT + 2 * self.PAD
            if height != self._descHeight:
                self._descHeight = height
                try:
                    self.getControl(self.DESC_TEXT_ID).setHeight(
                        util.vscalei(lines * self.LINE_HEIGHT + self.DESCENDER_ROOM))
                    self.getControl(self.DESC_BACKDROP_ID).setHeight(util.vscalei(height))
                    self.getControl(self.DESC_SHADOW_ID).setHeight(util.vscalei(height + 80))
                except (RuntimeError, SystemError) as e:
                    util.LOG('SettingsPickerDialog: no description panel to fit: {}', e)
        self.setProperty('description', desc)


class SettingsPickers(object):
    """
    The add-on's Settings (openWindow()): a picker of the sections, a section's settings over it, and a setting's
    values over that, each Back to the one under it. A setting's row: its name over its value, ticked when it's a
    switch that's on, a chevron when it opens a picker of values. A change is saved as it's made, and each picker
    under it shows it on return (show_cb's rows, there or not, too).
    """
    def __init__(self):
        self.settings = Settings()
        # Settings kept per Plex Home user are marked (a line heading the description, settingRow()) only when
        # there's more than one user to keep them for.
        account = plexnet.plexapp.ACCOUNT
        multiUser = bool(account and len(account.homeUsers or ()) > 1)
        self.userNote = multiUser and T(35179, 'Saved for this user ({0}) only.').format(
            account.title or account.username) or ''

    @staticmethod
    def picker(heading, options, **kwargs):
        # no wrap round from one end to the other
        return dialog.showOptionsDialog(heading, options, non_playback=True, trim=False, beside_sidebar=True,
                                        cls=SettingsPickerDialog, round_robin=False, **kwargs)

    def show(self):
        sections = [(sectionID, self.settings[sectionID][0], False, {'more': '1'})
                    for sectionID in self.settings.SECTION_IDS]

        def onSection(sectionID):
            self.showSection(sectionID)
            return sections, self.settings.SECTION_IDS.index(sectionID)

        self.picker(T(32343, 'Settings'), sections, on_choice=onSection, menu=True)

    def showSection(self, sectionID):
        label, settings = self.settings[sectionID]

        def rows():
            return [self.settingRow(s) for s in settings if s is not None and s.should_show()]

        def refreshed(setting):
            options = rows()
            return options, next((i for i, o in enumerate(options) if o[0] is setting), 0)

        def onSetting(setting):
            self.editSetting(setting)
            return refreshed(setting)

        def onContext(setting):
            if setting.type != 'STRING':
                return None
            self.editString(setting, clear=True)
            return refreshed(setting)

        self.picker(label, rows(), on_choice=onSetting, on_context=onContext, menu=True)

    def settingRow(self, setting):
        props = {}
        desc = setting.desc or ''
        if setting.userAware and self.userNote:
            # the note first, on its own line, in bold white over the description's grey
            note = u'[B][COLOR FFFFFFFF]{0}[/COLOR][/B]'.format(self.userNote)
            desc = u'{0}\n{1}'.format(note, desc) if desc else note
        if desc:
            props['description'] = desc
        if setting.type in ('LIST', 'OPTIONS', 'MULTI'):
            props['more'] = '1'

        value = ''
        if setting.type != 'BOOL':
            value = setting.valueLabel()
            value = u'{0}'.format(value) if value not in (None, '') else ''
        return (setting, (setting.label, value) if value else setting.label,
                setting.type == 'BOOL' and bool(setting.get()), props)

    @staticmethod
    def valueProps(setting, value):
        """A value's row's properties: its own description, if it has one (OptionsSetting.optionDescriptions()) -
        none of the setting's, which the picker under it had."""
        desc = getattr(setting, 'optionDescs', {}).get(value)
        return desc and {'description': desc} or {}

    def editSetting(self, setting):
        if setting.type == 'BOOL':
            setting.set(not setting.get())
        elif setting.type in ('LIST', 'OPTIONS'):
            self.chooseValue(setting)
        elif setting.type == 'MULTI':
            self.chooseValues(setting)
        elif setting.type == 'IP':
            self.editIP(setting)
        elif setting.type == 'INTEGER':
            self.editInteger(setting)
        elif setting.type == 'STRING':
            self.editString(setting)
        # INFO (About's): nothing to change

    def chooseValue(self, setting):
        if setting.type == 'LIST':
            values = list(enumerate(setting.optionLabels()))
        else:
            values = list(setting.options)
        idx = setting.optionIndex()
        options = [(value, label, i == idx, self.valueProps(setting, value))
                   for i, (value, label) in enumerate(values)]
        choice = self.picker(setting.label, options, selected_idx=idx)
        if choice is not None:
            setting.set(choice)

    def chooseValues(self, setting):
        """A multiple choice: Select ticks and unticks a value, saved as it's made; Back is done."""
        def options():
            current = setting.get()
            return [(value, label, value in current, self.valueProps(setting, value))
                    for value, label in setting.options]

        def onToggle(value):
            values = list(setting.get())
            if value in values:
                values.remove(value)
            else:
                values.append(value)
            setting.set(values)
            refreshed = options()
            return refreshed, next((i for i, o in enumerate(refreshed) if o[0] == value), 0)

        ticked = setting.optionIndex()
        self.picker(setting.label, options(), on_choice=onToggle, selected_idx=ticked[-1] if ticked else None)

    def editIP(self, setting):
        current = setting.get()
        edit = True
        if current:
            edit = xbmcgui.Dialog().yesno(
                T(32412, 'Edit Or Clear'),
                T(32413, 'Edit IP address or clear the current setting?'),
                nolabel=T(32414, 'Clear'),
                yeslabel=T(32415, 'Edit')
            )

        if edit:
            result = xbmcgui.Dialog().input(T(32416, 'Enter IP Address'), current, xbmcgui.INPUT_IPADDRESS)
            if not result:
                return
        else:
            result = ''

        setting.set(result)

    def editInteger(self, setting):
        result = xbmcgui.Dialog().input(setting.label, str(setting.get()), xbmcgui.INPUT_NUMERIC)
        if not result:
            return
        setting.set(int(result))

    def editString(self, setting, clear=False):
        if clear:
            setting.set(None)
            return
        if hasattr(setting, "value_setter"):
            # a key setting's: the key pressed (SchnorchelDialog), None for none in time or Back, -1 for Select
            result = setting.value_setter()
            if result is not None and result != -1:
                setting.set(result.code)
            return
        result = xbmcgui.Dialog().input(T(32417, 'Enter Port Number'), str(setting.get()), xbmcgui.INPUT_STRING)
        if result is None:
            return
        elif result == -1:
            setting.set(None)
            return
        setting.set(result)


def openWindow():
    SettingsPickers().show()
