# coding=utf-8
"""
Plextuary is the skin our windows are laid out against: Kodi only reads fonts from the active skin's
Font.xml, and the text widths (windows/mixins/text_metrics.py) are measured for Plextuary's. Under
another skin, font8 doesn't exist (Kodi falls back to font13) and the typeface differs, so at startup
we offer to switch to - and if needed install - the Plextuary variant for this device. Plextuary's
other font sets change the typeface (and Arial the sizes too), so we offer its Default (Inter UI)
as well.
"""
from __future__ import absolute_import

import time

from kodi_six import xbmc, xbmcaddon, xbmcvfs

from . import util
from .util import T

AUTO = 'auto'

# A renamed copy of the add-on (script.plexmod-uno) has Plextuary builds of its own, renamed the same
# way (skin.plextuary-uno), carrying the Inter 4 fonts text_metrics.py is measured for
SKIN_SUFFIX = util.ADDON_ID[len(util.UPSTREAM_ADDON_ID):]

# All three share the same Font.xml for every font we use; they differ in PlayerProcessInfo. font8
# is only in the releases from August 2026 (pm4k1.13, pm4k1.15ce, 1.15cpm.a14.26) in FilHarr's fork of
# dontpanickodi, and in the renamed builds; pannal's upstream ones don't have it, and there Kodi falls
# back to font13 (see _checkSmallFont()).
VARIANTS = tuple((skin_id + SKIN_SUFFIX, ' '.join([name, SKIN_SUFFIX.lstrip('-').title()]).strip())
                 for skin_id, name in (
    ('skin.plextuary', 'Plextuary'),
    ('skin.plextuaryce', 'Plextuary CoreELEC'),
    ('skin.plextuarycpm', 'Plextuary CE Custom Builds'),
                 ))

# Kodi's own "Keep this change?" after the reload reverts by itself after about 10 s
SKIN_SETTLE_TIMEOUT = 15
# Kodi shows its Startup window once "Keep this change?" is answered: 0.47 s and 0.58 s after the
# dialog went on the PC, 0.47 s on the AM6B. About three times that, for slower devices.
STARTUP_QUIET_PERIOD = 1.5

# Inter UI, shown by Kodi as "Inter UI (default, bundled)"; text_metrics.py's widths are measured for it
PLEXTUARY_FONTSET = 'Default'

# FilHarr's test repository (github.com/FilHarr/maybepanic), serving the renamed add-on and skins beside
# pannal's "Don't Panic" (repository.dontpanic)
REPOSITORY_NAME = 'Maybe Panic'


def variantName(skin_id):
    return dict(VARIANTS).get(skin_id, skin_id)


def detectedVariant():
    # CE_VS10 is set for the CoreELEC custom builds (U3k, avdvplus, p3i, CPM), which all get the cpm variant
    if util.platformFlavor == 'CoreELEC':
        return ('skin.plextuarycpm' if util.CE_VS10 else 'skin.plextuaryce') + SKIN_SUFFIX
    return 'skin.plextuary' + SKIN_SUFFIX


def deviceDescription():
    if util.platformFlavor == 'CoreELEC':
        os_name = T(35112, 'CoreELEC {0} build').format(util.CE_BUILD) if util.CE_BUILD else 'CoreELEC'
        return '{0}, {1}'.format(util.model, os_name) if util.model else os_name
    if util.platformFlavor == 'LG WebOS':
        return 'LG webOS'
    return util.platform or T(32411, 'Unknown')


def _target():
    """
    The variant to offer, or None when the active skin already suits us. With Automatic, any of our
    Plextuary variants is fine (for a renamed copy, not the stock ones); an explicit choice has to be
    the active skin itself.
    """
    choice = util.getSetting('plextuary_variant', AUTO)
    if choice in dict(VARIANTS):
        return None if xbmc.getSkinDir() == choice else choice

    return None if xbmc.getSkinDir() in dict(VARIANTS) else detectedVariant()


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

    _changeLookAndFeel('lookandfeel.skin', skin_id)


def _changeLookAndFeel(setting, value):
    """Changes a skin or font set setting, which reloads the skin, and waits for Kodi to settle."""
    started = time.time()
    util.rpc.Settings.SetSettingValue(setting=setting, value=value)

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
    util.LOG("Skin check: {} is now {} (queue passed after {:.1f} s, settled after {:.1f} s)", setting,
             util.rpc.Settings.GetSettingValue(setting=setting)['value'], loaded - started, time.time() - started)


def check():
    """Returns True when Plex should exit instead of starting: the user went to update Plextuary."""
    if util.getSetting('plextuary_offer', True):
        _offerSkin()
    # Also after a skin switch or install: either can bring a Plextuary without font8, or keep a
    # font set other than Default. Each step's "Don't ask/remind" ends the rest. The update reminder
    # only for our own variants: a renamed copy's repository doesn't carry the stock ones.
    if util.getSetting('plextuary_offer', True) and util.SKIN_PLEXTUARY:
        if xbmc.getSkinDir() in dict(VARIANTS) and _checkSmallFont():
            return True
        if util.getSetting('plextuary_offer', True):
            _offerFontset()
    return False


def _hasSmallFont():
    """
    Whether the active skin defines font8. Read from its Font.xml rather than judged by version: a
    locally built Plextuary can carry an upstream version number (the PC's "pm4k1.12" has font8).
    """
    f = xbmcvfs.File('special://skin/xml/Font.xml')
    try:
        return '<name>font8</name>' in f.read()
    finally:
        f.close()


def _checkSmallFont():
    """Returns True when the user chose to update: Kodi's list of installed skins is opening."""
    try:
        if _hasSmallFont():
            return False
    except Exception:
        # Unreadable: better no reminder than a wrong one
        util.ERROR()
        return False

    skin = xbmcaddon.Addon(xbmc.getSkinDir())
    name, version = skin.getAddonInfo('name'), skin.getAddonInfo('version')
    util.LOG("Skin check: {} {} has no font8", xbmc.getSkinDir(), version)
    message = T(35116, "{0} {1} is older than Plex needs, so some small text will come out too large. Updates "
                       "come from the {2} repository.").format(name, version, REPOSITORY_NAME) + '\n\n' + \
        T(35123, "Update now closes Plex and opens Kodi's list of installed skins: select {0} there, then "
                 "Update. Start Plex again once it's updated.").format(name)
    button = _ask(message, T(35124, 'Update now'), T(35120, 'Not now'), T(35117, "Don't remind me again"))
    if button == 2:
        util.setSetting('plextuary_offer', False)
    if button != 0:
        return False

    # Kodi 21 has no way to update one add-on for us: InstallAddon() skips installed ones, and
    # UpdateAddonRepos only installs by itself with automatic updates on, at a time we can't see -
    # a skin reload under our open windows is the freeze monitor.py can't catch on stock Kodi 21.
    # So the user updates in Kodi's own screen, with Plex closed.
    util.LOG("Skin check: opening the installed skins list for an update, and exiting")
    xbmc.executebuiltin('ActivateWindow(AddonBrowser,addons://user/xbmc.gui.skin/,return)')
    return True


def _ask(info, *buttons):
    """
    Our own dialog rather than Kodi's yes/no, whose text box (the active skin's, usually not ours
    here) holds about four lines. Returns the chosen button's index, or None when backed out of.
    """
    from .windows import optionsdialog
    return optionsdialog.show('Plextuary', info, *buttons, big=True)


def _offerSkin():
    target = _target()
    if not target:
        return

    name = variantName(target)
    installed = _isInstalled(target)
    util.LOG("Skin check: active skin is {}, offering {} (installed: {})", xbmc.getSkinDir(), target, installed)

    lines = []
    # Only worth explaining when leaving a non-Plextuary skin; the variants share their fonts
    if not util.SKIN_PLEXTUARY:
        lines.append(T(35104, "Plex is designed to be used with the Plextuary skins. If you use a different skin, "
                              "text and layouts can appear wrong."))
    skin = name if util.getSetting('plextuary_variant', AUTO) == AUTO else \
        T(35122, '{0} (chosen in settings)').format(name)
    lines.append(T(35109, 'Detected platform: {0}').format(deviceDescription()) + '\n' +
                 (T(35110, 'Skin to use: {0}') if installed else T(35121, 'Skin to install: {0}')).format(skin))
    lines.append(T(35111, 'Switching skins will apply to all of Kodi, not just this addon.') + ' ' +
                 (T(35105, 'Switch to it now?') if installed else T(35106, 'Install it and switch to it now?')))

    button = _ask('\n\n'.join(lines),
                  T(35118, 'Switch') if installed else T(35119, 'Install and switch'),
                  T(35120, 'Not now'), T(35107, "Don't ask again"))
    if button == 2:
        util.setSetting('plextuary_offer', False)
        return
    if button != 0:
        return

    if not installed and not _install(target):
        util.LOG("Skin check: {} wasn't installed", target)
        _ask(T(35108, "{0} couldn't be installed. It's available from the {1} repository.").format(
            name, REPOSITORY_NAME), T(32997, 'OK'))
        return

    _switch(target)


def _offerFontset():
    # Kodi's Skin > Fonts: the same ten sets in every Plextuary variant, all at Default's sizes but
    # Arial, whose font10-14 are 3-5 px smaller
    fontset = util.rpc.Settings.GetSettingValue(setting='lookandfeel.font')['value']
    if fontset == PLEXTUARY_FONTSET:
        return

    util.LOG("Skin check: font set is {}, offering {}", fontset, PLEXTUARY_FONTSET)
    lines = [
        T(35113, "Plex is designed to use Plextuary's default font (Inter UI). If you use a different font, text "
                 "and layouts can appear wrong."),
        T(35114, 'Current font: {0}.').format(fontset),
        T(35115, 'Switching fonts will change the font for all of Kodi. Switch to Inter UI now?'),
    ]
    button = _ask('\n\n'.join(lines), T(35118, 'Switch'), T(35120, 'Not now'), T(35107, "Don't ask again"))
    if button == 2:
        util.setSetting('plextuary_offer', False)
        return
    if button != 0:
        return

    _changeLookAndFeel('lookandfeel.font', PLEXTUARY_FONTSET)
