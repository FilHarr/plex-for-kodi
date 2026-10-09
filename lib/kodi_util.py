# coding=utf-8

import os
import sys
import shutil
import platform
from xml.etree import ElementTree

# noinspection PyUnresolvedReferences
from kodi_six import xbmc, xbmcgui, xbmcvfs, xbmcaddon

ADDON = xbmcaddon.Addon()
# Read from addon.xml rather than hard-coded, so a renamed copy (script.plexmod-uno) can sit beside a stock
# install. UPSTREAM_ADDON_ID is the stock add-on's ID.
ADDON_ID = ADDON.getAddonInfo('id')
UPSTREAM_ADDON_ID = 'script.plexmod'

_build = None
# buildversion looks like: XX.X[-TAG] (a+.b+.c+) (.+); there are kodi builds that don't set the build version
sys_ver = xbmc.getInfoLabel('System.BuildVersion')
_ver = sys_ver

try:
    if ' ' in sys_ver and '(' in sys_ver:
        _ver, _build = sys_ver.split()[:2]

    _splitver = _ver.split(".")
    KODI_VERSION_MAJOR, KODI_VERSION_MINOR = int(_splitver[0].split("-")[0].strip()), \
                                             int(_splitver[1].split(" ")[0].split("-")[0].strip())
except:
    xbmc.log(ADDON_ID + ': Couldn\'t determine Kodi version, assuming 19.4. Got: {}'.format(sys_ver), xbmc.LOGINFO)
    # assume something "old"
    KODI_VERSION_MAJOR = 19
    KODI_VERSION_MINOR = 4

_bmajor, _bminor, _bpatch = (KODI_VERSION_MAJOR, KODI_VERSION_MINOR, 0)
parsedBuild = False
if _build:
    try:
        _bmajor, _bminor, _bpatch = _build[1:-1].split(".")
        parsedBuild = True
    except:
        pass
if not parsedBuild:
    xbmc.log(ADDON_ID + ': Couldn\'t determine build version, falling back to Kodi version', xbmc.LOGINFO)

# calculate a comparable build number
KODI_BUILD_NUMBER = int("{0}{1:02d}{2:03d}".format(_bmajor, int(_bminor), int(_bpatch)))

FROM_KODI_REPOSITORY = ADDON.getAddonInfo('name') == "PM4K for Plex"

try:
    PYTHON_VERSION = platform.python_version()
    PYTHON_VERSION_TUPLE = tuple(map(int, platform.python_version_tuple()))
except:
    # assume something old
    PYTHON_VERSION = "3.8.15"
    PYTHON_VERSION_TUPLE = (3, 8, 15)


# no GIL anymore?
ENABLE_HIGH_CONCURRENCY = False
try:
    ENABLE_HIGH_CONCURRENCY = not sys._is_gil_enabled()
except:
    pass


if KODI_VERSION_MAJOR > 18:
    translatePath = xbmcvfs.translatePath
else:
    translatePath = xbmc.translatePath


ICON_PATH = translatePath(ADDON.getAddonInfo('icon'))


# settings a migrated copy must not inherit:
# - sign-in: this copy is its own device (client.ID - tokens are issued per device) and signs in afresh, so
#   leave out the account and everything MyPlexAccount.signOut() clears with it
# - kiosk.mode: two copies with kiosk mode on race to auto-start at boot
# - the state of this copy's own install: its rendered skin and update checks
_MIGRATION_SKIP = (
    'client.ID', 'auth.token', 'myplex.MyPlexAccount', 'myplex.LocalUsers', 'None.PlexServerManager',
    'xml_cache.mpaResources', 'xml_cache.mpaResources2', 'show_welcome',
    'kiosk.mode',
    'theme_version', 'last_resolution', 'last_update_check',
    'migrated_from',
)
# local mode's avatars of the account's users, harvested again with them after signing in
_MIGRATION_SKIP_FILES = ('settings.xml', 'local_avatars')


def migrateFromUpstream():
    """
    A renamed copy (script.plexmod-uno) starts with an empty addon_data. On its first run, take the stock
    add-on's preferences and files, but not its sign-in (see _MIGRATION_SKIP).
    Settings go through setSetting() rather than a settings.xml copy, as Kodi may already hold this add-on's
    settings in memory and would save them back over a copied file.
    """
    if ADDON_ID == UPSTREAM_ADDON_ID or ADDON.getSetting('migrated_from'):
        return

    # claimed before copying: the service and the script can both start at once
    ADDON.setSetting('migrated_from', '-')

    src = translatePath('special://profile/addon_data/{}/'.format(UPSTREAM_ADDON_ID))
    dst = translatePath(ADDON.getAddonInfo('profile'))
    settings_fn = os.path.join(src, 'settings.xml')
    if not os.path.isfile(settings_fn):
        return

    try:
        if not os.path.isdir(dst):
            os.makedirs(dst)
        for name in os.listdir(src):
            if name in _MIGRATION_SKIP_FILES:
                continue
            s, d = os.path.join(src, name), os.path.join(dst, name)
            if os.path.isdir(s):
                shutil.copytree(s, d, dirs_exist_ok=True)
            else:
                shutil.copy2(s, d)

        # Kodi writes default="true" both on a declared setting left at its default and on every setting
        # resources/settings.xml doesn't declare - which is most of them (in-app preferences, hub/sidebar/
        # library state), so only the declared ones can be skipped as defaults
        declared_fn = os.path.join(translatePath(ADDON.getAddonInfo('path')), 'resources', 'settings.xml')
        declared = set(el.get('id') for el in ElementTree.parse(declared_fn).getroot().iter('setting'))

        count = 0
        for el in ElementTree.parse(settings_fn).getroot().iter('setting'):
            key = el.get('id')
            if not key or key in _MIGRATION_SKIP or (el.get('default') == 'true' and key in declared):
                continue
            ADDON.setSetting(key, el.text or '')
            count += 1

        ADDON.setSetting('migrated_from', UPSTREAM_ADDON_ID)
        xbmc.log('{}: Migrated {} settings and files from {}'.format(ADDON_ID, count, UPSTREAM_ADDON_ID),
                 xbmc.LOGINFO)
    except Exception as e:
        xbmc.log('{}: Migration from {} failed: {}'.format(ADDON_ID, UPSTREAM_ADDON_ID, e), xbmc.LOGERROR)


migrateFromUpstream()


def ensureHome():
    if xbmcgui.getCurrentWindowId() != 10000:
        xbmc.log("Switching to home screen before starting addon: {}".format(xbmcgui.getCurrentWindowId()),
                 xbmc.LOGINFO)
        xbmc.executebuiltin('Action(back)')
        xbmc.executebuiltin('Dialog.Close(all,1)')
        xbmc.executebuiltin('ActivateWindow(home)')
        ct = 0
        while xbmcgui.getCurrentWindowId() != 10000 and ct <= 50:
            xbmc.Monitor().waitForAbort(0.1)
            ct += 1
        if ct > 50:
            xbmc.log("Still active window: {}", xbmc.LOGINFO)
