# coding=utf-8
from plexnet.util import INTERFACE

from lib.util import T
from .dialog import showOptionsDialog


class PlaybackSettingsMixin(object):
    def playbackSettings(self, show):
        """
        A show's own playback switches (binge mode, auto-skips...) in the option picker: each named, ticked while
        it's on. Choosing one flips it and the picker stays open; Back closes it and saves any change. Binge mode
        switches the others off (auto-sync aside), and switching another on switches binge mode off.
        """
        pbs = INTERFACE.playbackManager(show)
        transMap = INTERFACE.playbackManager.transMap
        currentSettings = dict((key, getattr(pbs, key)) for key in transMap)
        # changed freely while the picker is open, written once it's closed
        newSettings = currentSettings.copy()

        def options():
            return [(key, T(transID), bool(newSettings[key])) for key, transID in transMap.items()]

        def toggle(key):
            on = not newSettings[key]
            if key == "binge_mode" and on:
                for other in newSettings:
                    if other not in ("binge_mode", "auto_sync"):
                        newSettings[other] = False
            elif key not in ("binge_mode", "auto_sync") and on:
                newSettings["binge_mode"] = False
            newSettings[key] = on
            # stay open, on the row just flipped
            return options(), list(transMap).index(key)

        showOptionsDialog(u"{}: {}".format(T(32925, 'Playback Settings'), show.defaultTitle), options(),
                          non_playback=True, on_choice=toggle)

        # write new settings for item if necessary
        if newSettings != currentSettings:
            INTERFACE.playbackManager(show, kv_dict=newSettings)
