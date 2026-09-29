# coding=utf-8
"""
Plextuary is the skin our windows are laid out against: Kodi only reads fonts from the active skin's
Font.xml, and the text widths (windows/mixins/text_metrics.py) are measured for Plextuary's. Under
another skin, font8 doesn't exist (Kodi falls back to font13) and the typeface differs, so at startup
we offer to switch to - and if needed install - the Plextuary variant for this device.
"""
from __future__ import absolute_import

import time

from kodi_six import xbmc, xbmcgui

from . import util
from .util import T

AUTO = 'auto'

# All three share the same Font.xml for every font we use; they differ in PlayerProcessInfo.
VARIANTS = (
    ('skin.plextuary', 'Plextuary'),
    ('skin.plextuaryce', 'Plextuary CoreELEC'),
    ('skin.plextuarycpm', 'Plextuary CE Custom Builds'),
)

# Kodi's own "Keep this change?" after the reload reverts by itself after about 10 s
SKIN_SETTLE_TIMEOUT = 15
# Kodi shows its Startup window once "Keep this change?" is answered: 0.47 s and 0.58 s after the
# dialog went on the PC, 0.47 s on the AM6B. About three times that, for slower devices.
STARTUP_QUIET_PERIOD = 1.5


def variantName(skin_id):
    return dict(VARIANTS).get(skin_id, skin_id)


def detectedVariant():
    # CE_VS10 is set for the CoreELEC custom builds (U3k, avdvplus, p3i, CPM), which all get the cpm variant
    if util.platformFlavor == 'CoreELEC':
        return 'skin.plextuarycpm' if util.CE_VS10 else 'skin.plextuaryce'
    return 'skin.plextuary'


def deviceDescription():
    if util.platformFlavor == 'CoreELEC':
        os_name = T(35112, 'CoreELEC {0} build').format(util.CE_BUILD) if util.CE_BUILD else 'CoreELEC'
        return '{0}, {1}'.format(util.model, os_name) if util.model else os_name
    if util.platformFlavor == 'LG WebOS':
        return 'LG webOS'
    return util.platform or T(32411, 'Unknown')


def _target():
    """
    The variant to offer, or None when the active skin already suits us. With Automatic, any
    Plextuary variant is fine; an explicit choice has to be the active skin itself.
    """
    choice = util.getSetting('plextuary_variant', AUTO)
    if choice in dict(VARIANTS):
        return None if xbmc.getSkinDir() == choice else choice

    return None if util.SKIN_PLEXTUARY else detectedVariant()


def _isInstalled(skin_id):
    return xbmc.getCondVisibility('System.HasAddon({})'.format(skin_id))


def _install(skin_id):
    # Kodi asks the user to confirm, then installs from whichever enabled repository carries it
    xbmc.executebuiltin('InstallAddon({})'.format(skin_id), True)
    waited = 0
    while not _isInstalled(skin_id) and waited < 10 and not util.MONITOR.waitForAbort(0.5):
        waited += 0.5
    return _isInstalled(skin_id)


def _switch(skin_id):
    # Kodi may have offered the switch itself once the install finished
    if xbmc.getSkinDir() == skin_id:
        return

    if not xbmc.getCondVisibility('System.AddonIsEnabled({})'.format(skin_id)):
        util.rpc.Addons.SetAddonEnabled(addonid=skin_id, enabled=True)

    started = time.time()
    util.rpc.Settings.SetSettingValue(setting='lookandfeel.skin', value=skin_id)

    # Our windows mustn't be created while Kodi is still tearing down and loading skins. Kodi 21
    # announces nothing when a skin loads (there's no GUI.OnSkinLoaded), but the setting change has
    # queued the reload for Kodi's main thread, and a builtin we wait for queues behind it.
    xbmc.executebuiltin('Action(noop)', True)
    loaded = time.time()

    # Then Kodi's "Keep this change?" dialog, and once it's answered, the Startup window. Startup's
    # onload ReplaceWindow()s straight to the startup window setting, which would replace a window of
    # ours opened just before it (13:46:43 on the PC: Startup 17 ms ahead of our first window). It
    # can't be watched for - polling the window ID every 20 ms never saw it - so we wait for the
    # dialog to have been gone for STARTUP_QUIET_PERIOD instead.
    quiet_since = None
    while time.time() - started < SKIN_SETTLE_TIMEOUT and not util.MONITOR.waitForAbort(0.1):
        if xbmc.getCondVisibility('System.HasActiveModalDialog'):
            quiet_since = None
        elif quiet_since is None:
            quiet_since = time.time()
            # Its timestamp against Kodi's own "Loading skin file: Startup.xml" line is how long
            # STARTUP_QUIET_PERIOD has to cover on a device
            util.LOG("Skin check: no dialog up, waiting {} s for Kodi's Startup window", STARTUP_QUIET_PERIOD)
        elif time.time() - quiet_since >= STARTUP_QUIET_PERIOD:
            break

    util.SKIN_PLEXTUARY = "skin.plextuary" in xbmc.getSkinDir()
    util.LOG("Skin check: active skin is now {} (queue passed after {:.1f} s, settled after {:.1f} s)",
             xbmc.getSkinDir(), loaded - started, time.time() - started)


def check():
    if not util.getSetting('plextuary_offer', True):
        return

    target = _target()
    if not target:
        return

    name = variantName(target)
    installed = _isInstalled(target)
    util.LOG("Skin check: active skin is {}, offering {} (installed: {})", xbmc.getSkinDir(), target, installed)

    # Kept short: Kodi's yes/no text box shows about four lines before it starts scrolling
    lines = []
    # Only worth explaining when leaving a non-Plextuary skin; the variants share their fonts
    if not util.SKIN_PLEXTUARY:
        lines.append(T(35104, "Plex's screens are designed for the Plextuary skins. Under other skins, text "
                              "and layouts can come out wrong."))
    if util.getSetting('plextuary_variant', AUTO) == AUTO:
        lines.append(T(35109, 'Detected: {0}. Selected: {1}.').format(deviceDescription(), name))
    else:
        lines.append(T(35110, 'Detected: {0}. Selected in settings: {1}.').format(deviceDescription(), name))
    lines.append(T(35111, 'This changes the skin for all of Kodi.') + ' ' +
                 (T(35105, 'Switch to it now?') if installed else T(35106, 'Install it and switch to it now?')))

    button = xbmcgui.Dialog().yesnocustom('Plextuary', '\n'.join(lines), customlabel=T(35107, "Don't ask again"))
    if button == 2:
        util.setSetting('plextuary_offer', False)
        return
    if button != 1:
        return

    if not installed and not _install(target):
        util.LOG("Skin check: {} wasn't installed", target)
        xbmcgui.Dialog().ok(name, T(35108, "{0} couldn't be installed. It's available from the dontpanic "
                                           "repository.").format(name))
        return

    _switch(target)
