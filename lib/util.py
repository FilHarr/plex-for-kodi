# -*- coding: utf-8 -*-
from __future__ import absolute_import

import gc
import hashlib
import os
import sys
import re
import json
import threading
import math
import colorsys
import time
import datetime
import contextlib
import subprocess
import unicodedata
import pprint

import six.moves.urllib.request, six.moves.urllib.parse, six.moves.urllib.error
import six
import struct
import requests

import plexnet.util

from .kodijsonrpc import rpc
from . import colors
# noinspection PyUnresolvedReferences
from .exceptions import NoDataException
from .logging import log, DEBUG_LOG, LOG, ERROR, setShutdown, showNotification
# noinspection PyUnresolvedReferences
from .i18n import T, TRANSLATED_ROLES
from . import aspectratio
# noinspection PyUnresolvedReferences
from .kodi_util import (ADDON, xbmc, xbmcvfs, xbmcaddon, xbmcgui, translatePath, KODI_VERSION_MAJOR, KODI_VERSION_MINOR,
                        KODI_BUILD_NUMBER, FROM_KODI_REPOSITORY, PYTHON_VERSION, ENABLE_HIGH_CONCURRENCY)
from .properties import setGlobalProperty, setGlobalBoolProperty, waitForGPEmpty, waitForConsumption, getGlobalProperty
# noinspection PyUnresolvedReferences
from .addonsettings import addonSettings, AddonSettings
from .settings_util import getSetting, getUserSetting, setSetting, USER_SETTINGS, JSON_SETTINGS, DEFAULT_SETTINGS
from .os_utils import fast_iglob
from .monitor import MONITOR


DEBUG = True

SKIN_PLEXTUARY = "skin.plextuary" in xbmc.getSkinDir()
PROFILE = translatePath(ADDON.getAddonInfo('profile'))


DEF_THEME = "modern-colored"
THEME_VERSION = 98

UI_INTERVAL = 1 / float(addonSettings.uiWaitRate)

MONITOR.wait_interval = UI_INTERVAL

xbmc.log('script.plexmod: Kodi {0}.{1} (build {2}, Python: {3}, '
         'High concurrency possible: {4})'.format(KODI_VERSION_MAJOR, KODI_VERSION_MINOR, KODI_BUILD_NUMBER,
                                         PYTHON_VERSION, ENABLE_HIGH_CONCURRENCY),
         xbmc.LOGINFO)

xbmc.log('script.plexmod: UI wait rate is {0} ({1} Hz)'.format(UI_INTERVAL, addonSettings.uiWaitRate),
         xbmc.LOGINFO)

def getChannelMapping():
    data = rpc.Settings.GetSettings(filter={"section": "system", "category": "audio"})["settings"]
    return list(filter(lambda i: i["id"] == "audiooutput.channels", data))[0]["options"]


# retrieve labels for mapping audio channel settings values
try:
    CHANNELMAPPING = dict((t["value"], t["label"]) for t in getChannelMapping())
except:
    CHANNELMAPPING = None


def getLanguageCode(add_def=None):
    data = rpc.Settings.GetSettingValue(setting='locale.language')['value'].replace('resource.language.', '')
    lang = ""
    if "_" in data:
        base, variant = data.split("_")
        lang += "{}-{},{}".format(base, variant.upper(), base)
    else:
        lang = base = data
    if add_def and lang not in add_def:
        lang += ",{}".format(add_def)
    return lang, base


try:
    ACCEPT_LANGUAGE_CODE, LANGUAGE_CODE = getLanguageCode(add_def='en-US,en')
except:
    ACCEPT_LANGUAGE_CODE, LANGUAGE_CODE = ('en-US,en', 'en')


try:
    DISPLAY_RESOLUTION = [xbmcgui.getScreenWidth(), xbmcgui.getScreenHeight()]
except:
    LOG('Couldn\'t determine display resolution')
    DISPLAY_RESOLUTION = [1920, 1080]


CURRENT_AR = DISPLAY_RESOLUTION[0] / DISPLAY_RESOLUTION[1]

# we currently only support vertical scaling for smaller ARs; change to != once we know how to scale horizontally
NEEDS_SCALING = round(CURRENT_AR, 2) < round(1920 / 1080, 2)

HOME_BUTTON_MAPPED = None

HUB_ITEM_STATES = {}


def homeButtonMapped(*args, **kwargs):
    global HOME_BUTTON_MAPPED
    data = getSetting('map_button_home', None)
    HOME_BUTTON_MAPPED = data if data != "None" else None


homeButtonMapped()


DEBUG = addonSettings.debug


hasCustomBGColour = False
useSolidBackground = False
if KODI_VERSION_MAJOR > 18:
    useSolidBackground = not addonSettings.dynamicBackgrounds and addonSettings.backgroundColour
    hasCustomBGColour = useSolidBackground and addonSettings.backgroundColour != "-"


def getAdvancedSettings():
    # yes, global, hang me!
    global addonSettings
    addonSettings = AddonSettings()


def reInitAddon():
    global ADDON
    # reinit the ADDON reference so we get the updated addon settings
    ADDON = xbmcaddon.Addon()
    getAdvancedSettings()
    populateTimeFormat()


def videoIsPlaying():
    return xbmc.getCondVisibility('Player.HasVideo')


def messageDialog(heading='Message', msg=''):
    from .windows import optionsdialog
    optionsdialog.show(heading, msg, 'OK')


def showTextDialog(heading, text):
    t = TextBox()
    t.setControls(heading, text)


def sortTitle(title):
    return title.startswith('The ') and title[4:] or title


def durationToText(seconds):
    """
    Converts seconds to a short user friendly string
    Example: 143 -> 2m 23s
    """
    days = int(seconds / 86400000)
    if days:
        return '{0} day{1}'.format(days, days > 1 and 's' or '')
    left = seconds % 86400000
    hours = int(left / 3600000)
    if hours:
        hours = '{0} hr{1} '.format(hours, hours > 1 and 's' or '')
    else:
        hours = ''
    left = left % 3600000
    mins = int(left / 60000)
    if mins:
        return hours + '{0} min{1}'.format(mins, mins > 1 and 's' or '')
    elif hours:
        return hours.rstrip()
    secs = int(left % 60000)
    if secs:
        secs /= 1000
        return '{0} sec{1}'.format(secs, secs > 1 and 's' or '')
    return '0 seconds'


def durationToShortText(ms, shortHourMins=False, shortSeconds=False, noSpaces=False):
    """
    Converts seconds to a short user friendly string
    Example: 143 -> 2m 23s
    """
    days = int(ms / 86400000)
    if days:
        return '{0}{1}d'.format(days, "" if noSpaces else " ")
    left = ms % 86400000
    hours = int(left / 3600000)
    if hours:
        hours_s = '{0}{1}h '.format(hours, "" if noSpaces else " ")
    else:
        hours_s = ''
    left = left % 3600000
    mins = int(left / 60000)
    if mins:
        if shortHourMins and hours:
            return '{0}:{1}{2}h'.format(hours, mins, "" if noSpaces else " ")
        return hours_s + '{0}{1}m'.format(mins, "" if noSpaces else " ")
    elif hours_s:
        return hours_s.rstrip()
    secs = int(left % 60000)
    if secs:
        secs /= 1000
        return '{0}{1}s'.format(round(secs) if shortSeconds and round(secs) == int(secs) else secs, "" if noSpaces else " ")
    return noSpaces and '0s' or '0 s'


def cleanLeadingZeros(text):
    if not text:
        return ''
    return re.sub(r'(?<= )0(\d)', r'\1', text)


def removeDups(dlist):
    return [ii for n, ii in enumerate(dlist) if ii not in dlist[:n]]


SIZE_NAMES = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")


def simpleSize(size):
    """
    Converts bytes to a short user friendly string
    Example: 12345 -> 12.06 KB
    """
    s = 0
    i = 0
    if size > 0:
        i = int(math.floor(math.log(size, 1024)))
        p = math.pow(1024, i)
        s = round(size / p, 2)
    if s > 0:
        return '%s %s' % (s, SIZE_NAMES[i])
    else:
        return '0B'


def timeDisplay(ms, cutHour=False):
    h = ms / 3600000
    m = (ms % 3600000) / 60000
    s = (ms % 60000) / 1000
    if h >= 1 or not cutHour:
        return '{0:0>2}:{1:0>2}:{2:0>2}'.format(int(h), int(m), int(s))
    return '{0:0>2}:{1:0>2}'.format(int(m), int(s))


def simplifiedTimeDisplay(ms):
    left, right = timeDisplay(ms).rsplit(':', 1)
    left = left.lstrip('0:') or '0'
    return left + ':' + right


def shortenText(text, size):
    if len(text) < size:
        return text

    return u'{0}\u2026'.format(text[:size - 1])


def scaleResolution(w, h, by=None):
    if by is None:
        by = addonSettings.posterResolutionScalePerc

    if 0 < by != 100.0:
        px = w * h * (by / 100.0)
        wratio = h / float(w)
        hratio = w / float(h)
        return int(round((px / wratio) ** .5)), int(round((px / hratio) ** .5))
    return w, h


def vscale(h, r=2):
    if not NEEDS_SCALING:
        return h
    ratio = aspectratio.V_AR_RATIO
    if ratio is None:
        ratio = aspectratio.v_ar_ratio(DISPLAY_RESOLUTION[0], DISPLAY_RESOLUTION[1])
    return round(ratio * h, r) if r > 0 else int(round(ratio * h, r))


def vscalei(h):
    return vscale(h, r=0)


def vperc(height, perc=50, ref=1080, rel=50, r=2):
    ret = perc * ref / 100.0 - height * rel / 100
    if r > 0:
        return round(ret, r)
    return int(round(ret, r))


def vperci(height, perc=50, ref=1080, rel=50):
    return vperc(height, perc=perc, ref=ref, rel=rel, r=0)


class TextBox:
    # constants
    WINDOW = 10147
    CONTROL_LABEL = 1
    CONTROL_TEXTBOX = 5

    def __init__(self, *args, **kwargs):
        # activate the text viewer window
        xbmc.executebuiltin("ActivateWindow(%d)" % (self.WINDOW, ))
        # get window
        self.win = xbmcgui.Window(self.WINDOW)
        # give window time to initialize
        xbmc.sleep(1000)

    def setControls(self, heading, text):
        # set heading
        self.win.getControl(self.CONTROL_LABEL).setLabel(heading)
        # set text
        self.win.getControl(self.CONTROL_TEXTBOX).setText(text)


class SettingControl(object):
    def __init__(self, setting, log_display, disable_value=''):
        self.setting = setting
        self.logDisplay = log_display
        self.disableValue = disable_value
        self._originalMode = None
        self.store()

    def disable(self):
        rpc.Settings.SetSettingValue(setting=self.setting, value=self.disableValue)
        DEBUG_LOG('{0}: DISABLED'.format(self.logDisplay))

    def set(self, value):
        rpc.Settings.SetSettingValue(setting=self.setting, value=value)
        DEBUG_LOG('{0}: SET={1}'.format(self.logDisplay, value))

    def store(self):
        try:
            self._originalMode = rpc.Settings.GetSettingValue(setting=self.setting).get('value')
            DEBUG_LOG('{0}: Mode stored ({1})'.format(self.logDisplay, self._originalMode))
        except:
            ERROR()

    def restore(self):
        if self._originalMode is None:
            return
        rpc.Settings.SetSettingValue(setting=self.setting, value=self._originalMode)
        DEBUG_LOG('{0}: RESTORED'.format(self.logDisplay))

    @property
    def original(self):
        return self._originalMode

    @contextlib.contextmanager
    def suspend(self):
        self.disable()
        yield
        self.restore()

    @contextlib.contextmanager
    def save(self):
        yield
        self.restore()


def timeInDayLocalSeconds():
    now = datetime.datetime.now()
    sod = datetime.datetime(year=now.year, month=now.month, day=now.day)
    sod = int(time.mktime(sod.timetuple()))
    return int(time.time() - sod)


def getKodiSkipSteps():
    try:
        return rpc.Settings.GetSettingValue(setting="videoplayer.seeksteps")["value"]
    except:
        return


def getKodiSlideshowInterval():
    try:
        return rpc.Settings.GetSettingValue(setting="slideshow.staytime")["value"]
    except:
        return 3


kodiSkipSteps = getKodiSkipSteps()
slideshowInterval = getKodiSlideshowInterval()


CRON = None


class CronReceiver():
    def tick(self):
        pass

    def halfHour(self):
        pass

    def day(self):
        pass


class Cron(threading.Thread):
    def __init__(self, interval):
        threading.Thread.__init__(self, name='CRON')
        self.stopped = threading.Event()
        self.force = threading.Event()
        self.interval = interval
        self._lastHalfHour = self._getHalfHour()
        self._receivers = []

        global CRON

        CRON = self

    def __enter__(self):
        self.start()
        DEBUG_LOG('Cron started with interval: {}'.format(self.interval))
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop()
        self.join()

    def _wait(self):
        ct = 0
        while ct < self.interval:
            xbmc.sleep(100)
            ct += 0.1
            if self.force.isSet():
                self.force.clear()
                return True
            if MONITOR.abortRequested() or self.stopped.isSet():
                return False
        return True

    def forceTick(self):
        self.force.set()

    def stop(self):
        self.stopped.set()

    def run(self):
        while self._wait():
            self._tick()
        DEBUG_LOG('Cron stopped')

    def _getHalfHour(self):
        tid = timeInDayLocalSeconds() / 60
        return tid - (tid % 30)

    def _tick(self):
        receivers = list(self._receivers)
        receivers = self._halfHour(receivers)
        for r in receivers:
            try:
                r.tick()
            except:
                ERROR()

    def _halfHour(self, receivers):
        hh = self._getHalfHour()
        if hh == self._lastHalfHour:
            return receivers
        try:
            receivers = self._day(receivers, hh)
            ret = []
            for r in receivers:
                try:
                    if not r.halfHour():
                        ret.append(r)
                except:
                    ret.append(r)
                    ERROR()
            return ret
        finally:
            self._lastHalfHour = hh

    def _day(self, receivers, hh):
        if hh >= self._lastHalfHour:
            return receivers
        ret = []
        for r in receivers:
            try:
                if not r.day():
                    ret.append(r)
            except:
                ret.append(r)
                ERROR()
        return ret

    def registerReceiver(self, receiver):
        if receiver not in self._receivers:
            DEBUG_LOG('Cron: Receiver added: {0}'.format(receiver))
            self._receivers.append(receiver)

    def cancelReceiver(self, receiver):
        if receiver in self._receivers:
            DEBUG_LOG('Cron: Receiver canceled: {0}'.format(receiver))
            self._receivers.pop(self._receivers.index(receiver))


def getTimeFormat():
    """
    Generic:
    Use locale.timeformat setting to get and make use of the format.

    Possible values:
    HH:mm:ss -> %H:%M:%S
    regional -> legacy
    H:mm:ss  -> %-H:%M:%S

    Legacy: Not necessarily true for Omega?; regional spices things up (depending on Kodi version?)
    Get global time format.
    Kodi's time format handling is weird, as they return incompatible formats for strftime.
    %H%H can be returned for manually set zero-padded values, in case of a regional zero-padded hour component,
    only %H is returned.

    For now, sail around that by testing the current time for padded hour values.

    Tests of the values returned by xbmc.getRegion("time") as of Kodi Nexus (I believe):
    %I:%M:%S %p = h:mm:ss, non-zero-padded, 12h PM
    %I:%M:%S = 12h, h:mm:ss, non-zero-padded, regional
    %I%I:%M:%S = 12h, zero padded, hh:mm:ss
    %H%H:%M:%S = 24h, zero padded, hh:mm:ss
    %H:%M:%S = 24h, zero padded, regional, regional (central europe)

    :return: tuple of strftime-compatible format, boolean padHour
    """

    fmt = None
    nonPadHF = "%-H" if sys.platform != "win32" else "%#H"
    nonPadIF = "%-I" if sys.platform != "win32" else "%#I"

    try:
        fmt = rpc.Settings.GetSettingValue(setting="locale.timeformat")["value"]
    except:
        DEBUG_LOG("Couldn't get locale.timeformat setting, falling back to legacy detection")

    if fmt and fmt != "regional":
        # HH = padded 24h
        # hh = padded 12h
        # H = unpadded 24h
        # h = unpadded 12h

        # handle non-padded hour first
        if fmt.startswith("H:") or fmt.startswith("h:"):
            adjustedFmt = fmt.replace("H", nonPadHF).replace("h", nonPadIF)
        else:
            adjustedFmt = fmt.replace("HH", "%H").replace("hh", "%I")

        padHour = adjustedFmt.startswith("%H") or adjustedFmt.startswith("%I")

    else:
        DEBUG_LOG("Regional time format detected, falling back to legacy detection of hour-padding")
        # regional is weirdly always unpadded (unless the broken %H%H/%I%I notation is used
        origFmt = xbmc.getRegion('time')

        adjustedFmt = origFmt.replace("%H%H", "%H").replace("%I%I", "%I")

        # Checking for %H%H or %I%I only would be the obvious way here to determine whether the hour should be padded,
        # but the formats returned for regional settings with padding might only have %H in them.
        # Use a fallback (unreliable).
        currentTime = xbmc.getInfoLabel('System.Time')
        padHour = "%H%H" in origFmt or "%I%I" in origFmt or (currentTime[0] == "0" and currentTime[1] != ":")

    # Kodi Omega on Android seems to have borked the regional format returned separately
    # (not happening on Windows at least). Format returned can be "%H:mm:ss", which is incompatible with strftime; fix.
    adjustedFmt = adjustedFmt.replace("mm", "%M").replace("ss", "%S").replace("xx", "%p")
    if "%M" not in adjustedFmt and "M" in adjustedFmt:
        adjustedFmt = adjustedFmt.replace("M", "%M")
    adjustedFmtKN = adjustedFmt.replace("%M", "mm").replace("%H", "hh").replace("%I", "h").replace("%S", "ss").\
        replace("%p", "xx").replace(nonPadIF, "h").replace(nonPadHF, "h")

    return adjustedFmt,  adjustedFmtKN, padHour


timeFormat, timeFormatKN, padHour = getTimeFormat()


def getShortDateFormat():
    try:
        fromAPI = rpc.Settings.GetSettingValue(setting="locale.shortdateformat")["value"]
        if fromAPI == "regional":
            return xbmc.getRegion('dateshort').replace('%-d', '%d')
        else:
            return fromAPI.replace("DD", "%d").replace("MM", "%m").replace("YYYY", "%Y")
    except:
        DEBUG_LOG("Couldn't get locale.shortdateformat setting, falling back to MM/DD/YYYY")
        return "%d/%m/%Y"


shortDF = getShortDateFormat()

# get mounts
KODI_SOURCES = []


def getKodiSources():
    try:
        data = rpc.Files.GetSources(media="files")["sources"]
    except:
        LOG("Couldn't parse Kodi sources")
    else:
        for d in data:
            f = d["file"]
            if f.startswith("smb://") or f.startswith("nfs://") or f.startswith("/") or ':\\\\' in f:
                KODI_SOURCES.append(d)
        LOG("Parsed {} Kodi sources: {}".format(len(KODI_SOURCES), KODI_SOURCES))


if getSetting('path_mapping', True):
    getKodiSources()


def populateTimeFormat():
    global timeFormat, timeFormatKN, padHour
    timeFormat, timeFormatKN, padHour = getTimeFormat()


def getPlatform():
    for key in [
        'System.Platform.Android',
        'System.Platform.Linux.RaspberryPi',
        'System.Platform.Linux',
        'System.Platform.Windows',
        'System.Platform.OSX',
        'System.Platform.IOS',
        'System.Platform.Darwin',
        'System.Platform.ATV2'
    ]:
        if xbmc.getCondVisibility(key):
            return key.rsplit('.', 1)[-1]


platform = getPlatform()
platform_version = None
device = None
vendor = None
model = None


CE_U3K_SB_LAV_MIN = 20251220132748  # B9
CE_AVD_SB_LAV_MIN = 20251221124544  # R2
CE_P3I_EMBED_FIXED = 20260204135007 # T2
CE_SB_LAV_SWITCH = False
CE_NEEDS_EMBEDDED_SEEKBACK = True
CE_NEEDS_HOME_ON_SCREENSAVER = True
CE_VS10 = False  # VS10 output mode switching (CoreELEC Amlogic builds: U3k, avdvplus, p3i)

def getCoreELEC():
    global platform, device, platform_version, vendor, model, CE_SB_LAV_SWITCH, CE_NEEDS_EMBEDDED_SEEKBACK, \
           CE_NEEDS_HOME_ON_SCREENSAVER, CE_VS10
    try:
        stdout = subprocess.check_output('lsb_release', shell=True).decode()
        match = re.search(r'CoreELEC', stdout)
        if match:
            if "U3k" in stdout:
                CE_VS10 = True
                try:
                    CE_SB_LAV_SWITCH = int(stdout.split("U3k_")[-1]) >= CE_U3K_SB_LAV_MIN
                    if CE_SB_LAV_SWITCH:
                        LOG("CoreELEC U3k build with LAV filters found. List-based fixing seamless branching possible.")
                except:
                    pass

            elif "avdvplus" in stdout:
                CE_VS10 = True
                try:
                    CE_SB_LAV_SWITCH = int(stdout.split("avdvplus_")[-1]) >= CE_AVD_SB_LAV_MIN
                    if CE_SB_LAV_SWITCH:
                        LOG("CoreELEC avdvplus build with LAV filters found. List-based fixing seamless branching possible.")
                except:
                    pass

            elif "p3i_" in stdout:
                CE_VS10 = True
                CE_SB_LAV_SWITCH = True
                CE_NEEDS_HOME_ON_SCREENSAVER = False
                LOG("CoreELEC p3i build with LAV filters found. List-based fixing seamless branching possible.")
                CE_NEEDS_EMBEDDED_SEEKBACK = int(stdout.split("_")[-1]) < CE_P3I_EMBED_FIXED
                if not CE_NEEDS_EMBEDDED_SEEKBACK:
                    LOG("CoreELEC p3i build with built-in embedded subtitle fix found. Disabling our fix.")

            elif "CPM" in stdout:
                CE_VS10 = True
                LOG("CoreELEC CPM build found. VS10 mode switching available.")

            platform = "Linux"
            try:
                model = subprocess.check_output(['cat', '/proc/device-tree/model']).decode().strip("\0 \n\r")
                vendor, device = model.split()
            except:
                pass
            try:
                platform_version = stdout.split(":")[1].strip()
            except:
                pass

            if model:
                #device = ("{} ({})".format(model, stdout.strip("\0 \n\r")).replace("\0", "")
                #          .replace("\n", "").replace("\r", ""))
                device = "{} (CoreELEC)".format(model).replace("\0", "").replace("\n", "").replace("\r", "")
            return True

    except:
        pass
    return False

def getWebOS():
    try:
        stdout = subprocess.check_output('uname -a', shell=True).decode()
        match = re.search(r'webos', stdout, re.IGNORECASE)
        if match:
            return True

    except:
        pass
    return False


def getPlatformFlavor():
    flavor = 'default'
    if platform in ['Linux', 'RaspberryPi']:
        flavor = "CoreELEC" if getCoreELEC() else "LG WebOS" if getWebOS() else 'default'

    if flavor != 'default':
        LOG("{} detected".format(flavor))
    return flavor


platformFlavor = getPlatformFlavor()
altSeekRecommended = platformFlavor != 'default'


def getRunningAddons():
    try:
        return xbmcvfs.listdir('addons://running/')[1]
    except:
        return []


def getUserAddons():
    try:
        return xbmcvfs.listdir('addons://user/all')[1]
    except:
        return []


USER_ADDONS = getUserAddons()


SLUGIFY_RE1 = re.compile(r'[^\w\s-]')
SLUGIFY_RE2 = re.compile(r'[-\s]+')


def slugify(value):
    """
    Converts to lowercase, removes non-word characters (alphanumerics and
    underscores) and converts spaces to hyphens. Also strips leading and
    trailing whitespace.
    """
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = SLUGIFY_RE1.sub('', value).strip().lower()
    return SLUGIFY_RE2.sub('-', value)


def getProgressImage(obj, perc=None, view_offset=None):
    if not obj and not perc:
        return ''

    if obj:
        if not view_offset:
            view_offset = obj.get('viewOffset') and obj.viewOffset.asInt()
        if not view_offset or not obj.get('duration'):
            return ''
        try:
            view_offset = int(view_offset)
        except ValueError:
            return ''
        pct = int((view_offset / obj.duration.asFloat()) * 100)
    else:
        pct = perc
    pct = pct - pct % 2  # Round to even number - we have even numbered progress only
    pct = max(pct, 2)
    return 'script.plex/progress/{0}.png'.format(pct)


def backgroundFromArt(art, width=1920, height=1080, background=colors.noAlpha.Background, opacity=None, blur=None):
    if not art:
        return

    w, h = scaleResolution(width, height, by=addonSettings.backgroundResolutionScalePerc)
    return art.asTranscodedImageURL(
        w, h,
        blur=addonSettings.backgroundArtBlurAmount2 if blur is None else blur,
        opacity=addonSettings.backgroundArtOpacityAmount2 if opacity is None else opacity,
        background=background
    )


# Hue offset per corner, applied to _fakeBackgroundPanelCorners()'s single hashed base hue - a
# small spread rather than one flat wash, so a faked panel still reads as a soft gradient like a
# real one. Kept subtle (max 0.08 = ~29 degrees) so adjacent corners stay harmonious, not clashing.
_FAKE_CORNER_HUE_OFFSETS = (('topLeft', -0.04), ('topRight', 0.04), ('bottomLeft', -0.08), ('bottomRight', 0.08))


def _fakeBackgroundPanelCorners(seed, maxValue=0.3, saturation=0.4):
    """Deterministic, neutral-but-colorful stand-in for real ultraBlurColors - used when an item
    has none (Photo/PhotoDirectory/most Music items, or any item the server just didn't return it
    for). A flat black/default panel reads as dull next to titles that do have real per-item
    color, so this hashes a stable identifier (the item's ratingKey, ideally) into a base hue and
    spreads it gently across the 4 corners (see _FAKE_CORNER_HUE_OFFSETS) - same HSV value clamp
    and a similarly modest fixed saturation as the real path, so a faked panel reads as "the same
    kind of tasteful dark panel", not a visually distinct fallback. md5, not the builtin hash():
    Python's string hash is randomized per-process (PYTHONHASHSEED) unless disabled, which would
    make the same item's fake color change every time Kodi restarts - md5 is stable forever, so a
    given item always gets the same color, no flicker across sessions or hub-row scrolling.
    """
    base_hue = (int(hashlib.md5(str(seed).encode('utf-8')).hexdigest(), 16) % 360) / 360.0
    result = {}
    for corner, offset in _FAKE_CORNER_HUE_OFFSETS:
        r, g, b = colorsys.hsv_to_rgb((base_hue + offset) % 1.0, saturation, maxValue)
        result[corner] = 'FF{:02X}{:02X}{:02X}'.format(round(r * 255), round(g * 255), round(b * 255))
    return result


def backgroundPanelCorners(ultraBlurColors, seed=None, maxValue=0.3):
    """
    Phase 1 approximation of official Plex's native per-corner art-color extraction (see
    docs/notes/hero-art-background-status.md, "Resolved: official Plex Android decompile"). Sources
    colors from the item's own ultraBlurColors PMS metadata rather than real pixel extraction from
    the art (Phase 2, not yet implemented - Kodi's Python has no PIL/Pillow and this addon has never
    done local pixel decoding).

    Clamps HSV *value* (not HSL lightness) to maxValue - confirmed against live screenshots of the
    official client's own full-background view (no hero-art box occluding it): capped corners land
    on an exact max-channel value of ~77/255 across multiple titles (Deadpool 2, Wakanda Forever,
    LOTR), consistent with a hard max(R,G,B) cap at 0.3, not a lightness ((max+min)/2) cap - an HSL
    clamp on the same swatches overshoots that ceiling substantially (e.g. Supergirl's raw
    bottomRight af1308 HSL-clamped to ~146 max channel vs officially observed ~77).

    Returns a dict of up to 4 ARGB colordiffuse-ready hex strings keyed 'topLeft'/'topRight'/
    'bottomLeft'/'bottomRight'. When the item has no ultraBlurColors data at all: falls back to
    _fakeBackgroundPanelCorners(seed) if a seed was given, otherwise returns {} (the original
    behavior - callers can leave the skin's corner-tint layers hidden and fall back to the flat
    base color only, for whatever caller doesn't have/want a seed-based fake).
    """
    if not ultraBlurColors:
        if seed is not None:
            return _fakeBackgroundPanelCorners(seed, maxValue=maxValue)
        return {}

    result = {}
    for corner in ('topLeft', 'topRight', 'bottomLeft', 'bottomRight'):
        rgbHex = ultraBlurColors.get(corner)
        if not rgbHex:
            continue
        try:
            r, g, b = (int(rgbHex[i:i + 2], 16) for i in (0, 2, 4))
        except (ValueError, TypeError):
            continue
        h, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
        if v > maxValue:
            v = maxValue
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        result[corner] = 'FF{:02X}{:02X}{:02X}'.format(round(r * 255), round(g * 255), round(b * 255))
    return result


def clearLogoFrom(item, width, height):
    """
    The item's clear logo scaled to its control, or '' when it has none or the user doesn't want them.

    Kodi loads background textures at screen size and minifies them on the GPU, so handing it the full-size
    logo gives visibly jagged edges - the server has to do the resizing. png rather than the transcoder's
    default, so the alpha channel survives.

    minSize is off, unlike everywhere else: it makes the server scale until the box is covered and crop the
    overflow, which is what you want for a poster and never for a logo - a wide wordmark would be blown up
    until its height filled the box and then have its sides cut off. Off means fit inside the box instead.
    """
    if not getSetting('clear_logos', True):
        return ''

    # anything that isn't a Video (artists, albums) has no clearLogo and yields an empty PlexValue here
    logo = getattr(item, 'clearLogo', None)
 
    return logo and logo.asTranscodedImageURL(width, height, format='png', minSize=0) or ''


def trackIsPlaying(track):
    return xbmc.getCondVisibility('String.StartsWith(MusicPlayer.Comment,{0})'.format('PLEX-{0}:'.format(track.ratingKey)))


def addURLParams(url, params):
        if '?' in url:
            url += '&'
        else:
            url += '?'
        url += six.moves.urllib.parse.urlencode(params)
        return url


OSS_CHUNK = 65536


def getOpenSubtitlesHash(size, url):
    long_long_format = "q"  # long long
    byte_size = struct.calcsize(long_long_format)
    hash_ = filesize = size
    if filesize < OSS_CHUNK * 2:
        return

    buffer = b''
    for _range in ((0, OSS_CHUNK), (filesize-OSS_CHUNK, filesize)):
        try:
            r = requests.get(url, headers={"range": "bytes={0}-{1}".format(*_range)}, stream=True)
        except:
            return ''
        buffer += r.raw.read(OSS_CHUNK)

    for x in range(int(OSS_CHUNK / byte_size) * 2):
        size = x * byte_size
        (l_value,) = struct.unpack(long_long_format, buffer[size:size + byte_size])
        hash_ += l_value
        hash_ = hash_ & 0xFFFFFFFFFFFFFFFF

    return format(hash_, "016x")

SETTING_RE = re.compile(r'<setting id="(?P<name>.+?)"[^>]*?>', re.MULTILINE | re.DOTALL)


def dumpSettings():
    from .windows import settings
    from collections import OrderedDict

    sections = set(settings.Settings.SECTION_IDS) - {"about", "player_user"}

    main_settings_dict = OrderedDict([(k,
                                       OrderedDict([(s.ID, (s.get(as_code=True), s.default))
                                                    for s in settings.Settings.SETTINGS[k][1]
                                                    if s is not None and not s.userAware])) for k in sections])
    main_revmap = {k: i for i in sections for k in main_settings_dict[i].keys()}
    adv_settings_dict = OrderedDict([(s, (getSetting(s, d), d)) for s, d in AddonSettings._proxiedSettings])

    try:
        f = xbmcvfs.File(os.path.join(translatePath(ADDON.getAddonInfo("profile")), "settings.xml"))
        try:
            data = f.read()
        finally:
            f.close()
        all_settings = SETTING_RE.findall(data)
    except:
        LOG('script.plexmod: No settings.xml found')
        return

    final = OrderedDict({"settings": OrderedDict((k, []) for k in sections), "addon_settings": [], "unspecified": []})

    for s in all_settings[:]:
        # get setting from main settings
        sec = main_revmap.get(s)

        if sec:
            ms = main_settings_dict[sec][s]
            try:
                v = json.loads(ms[0], default=ms[0])
            except:
                v = ms[0]
            final["settings"][sec].append({s: {"value": v, "default": ms[1], "changed": v != ms[1]}})
            all_settings.remove(s)
            continue
        advs = adv_settings_dict.get(s)
        if advs:
            try:
                v = json.loads(advs[0], default=advs[0])
            except:
                v = advs[0]
            final["addon_settings"].append({s: {"value": v, "default": advs[1], "changed": v != advs[1]}})
            all_settings.remove(s)
            continue

    remove_keys = ("xml_cache.mpaResources",)
    for key in remove_keys:
        all_settings.remove(key)

    def decode(v):
        try:
            return json.loads(v)
        except:
            return v

    final["unspecified"] += [{s: decode(getSetting(s))} for s in all_settings]
    final = plexnet.util.cleanObjTokens(final,
                                        mask_keys=("token", "authToken", "uuid", "name", "ID", "thumb", "email", "id",
                                                   "title", "username", "address"),
                                        dict_cls=OrderedDict)

    DEBUG_LOG("Settings dump: {}", pprint.pformat(final, compact=True))


def garbageCollect():
    gc.collect(2)


def cleanupCacheFolder():
    try:
        base = translatePath("special://temp")
        for f in fast_iglob(os.path.join(base, "theme_*.mp3")):
            fn = os.path.join(base, f)
            DEBUG_LOG("Removing leftover cached file: {}", fn)
            xbmcvfs.delete(fn)
    except:
        pass


def shutdown():
    global MONITOR, ADDON, T
    setShutdown()
    del MONITOR
    del T
    del ADDON
