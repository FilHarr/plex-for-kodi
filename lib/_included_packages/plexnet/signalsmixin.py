from __future__ import absolute_import
from . import signalslot

# Optional hook, called as AUDIT(emitter, signalName, slots) before each emit. The addon installs
# one (kodigui) to log windows that get signals off the main thread or after they've closed.
AUDIT = None


class SignalsMixin(object):
    def __init__(self, *args, **kwargs):
        self._signals = {}

    def on(self, signalName, callback):
        if signalName not in self._signals:
            self._signals[signalName] = signalslot.Signal(threadsafe=True)

        signal = self._signals[signalName]
        if self.has_signal(signalName, callback):
            return

        signal.connect(callback)

    def has_signal(self, signalName, callback):
        if not self._signals:
            return

        return signalName in self._signals and self._signals[signalName].is_connected(callback)

    def off(self, signalName, callback):
        if not self._signals:
            return

        if not signalName:
            if not callback:
                self._signals = {}
            else:
                for name in self._signals:
                    self.off(name, callback)
        else:
            if not callback:
                if signalName in self._signals:
                    del self._signals[signalName]
            else:
                if self.has_signal(signalName, callback):
                    self._signals[signalName].disconnect(callback)

    def trigger(self, signalName, **kwargs):
        if not self._signals:
            return

        if signalName not in self._signals:
            return

        signal = self._signals[signalName]
        if AUDIT is not None:
            AUDIT(self, signalName, signal.slots)
        signal.emit(**kwargs)
