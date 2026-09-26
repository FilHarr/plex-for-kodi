from __future__ import absolute_import

import threading

from kodi_six import xbmcgui

from lib import util
from . import kodigui


class BusyWindow(kodigui.BaseDialog):
    xmlFile = 'script-plex-busy.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080


class BlockingBusyWindow(BusyWindow):
    def onAction(self, action):
        if action in (xbmcgui.ACTION_PREVIOUS_MENU, xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_STOP):
            return False


class BusyClosableWindow(BusyWindow):
    ctx = None

    def onAction(self, action):
        if action in (xbmcgui.ACTION_PREVIOUS_MENU, xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_STOP):
            self.ctx.shouldClose = True


class BusyClosableMsgWindow(BusyClosableWindow):
    xmlFile = 'script-plex-busy_msg.xml'

    def setMessage(self, msg):
        self.setProperty("message", msg)


def dialog(msg='LOADING', condition=None, delay=True, delay_time=1.5):
    def methodWrap(func):
        def inner(*args, **kwargs):
            timer = None
            w = BusyWindow.create(show=not delay)

            if delay:
                timer = threading.Timer(delay_time, w.show)
                timer.start()

            try:
                return func(*args, **kwargs)
            finally:
                # Stop the timer before closing, not after. The other way round, a timer that
                # came due in the moment between the two called show() on a window that had
                # already been closed - and the show/close pair that close together leaves
                # XMLBase.onInit() looking for control 666 in a window whose controls are being
                # torn down underneath it, which it reads as a broken XML file and answers with a
                # full template recompilation (live, 2026-09-19, on a 234-row play queue refill
                # that took longer than delay_time).
                #
                # cancel() only stops a timer that has not started; join() then waits for one
                # that has, so by the time doClose() runs, show() has either never been called or
                # has finished.
                if timer:
                    timer.cancel()
                    timer.join()
                del timer
                w.doClose()
                try:
                    del w
                except:
                    pass

        if condition is not None:
            return condition() and inner or func
        return inner

    return methodWrap


def busy_property(delay=True, delay_time=0.5):
    def methodWrap(func):
        def inner(win, *args, **kwargs):
            def setProp(w):
                w.setProperty('busy', '1')

            timer = None
            if delay:
                timer = threading.Timer(delay_time, lambda: setProp(win))
                timer.start()
            else:
                setProp(win)
            try:
                return func(win, *args, **kwargs)
            finally:
                if timer and timer.is_alive():
                    timer.cancel()
                    timer.join()
                del timer
                win.setProperty('busy', '')
        return inner
    return methodWrap



def widthDialog(method, msg, *args, **kwargs):
    condition = kwargs.pop("condition", None)
    delay = kwargs.pop("delay", False)
    delay_time = kwargs.pop("delay_time", 0.5)
    return dialog(msg or 'LOADING', condition=condition, delay=delay, delay_time=delay_time)(method)(*args, **kwargs)


class BusyContext(object):
    w = None
    timer = None
    shouldClose = False
    window_cls = BusyWindow
    delay = False

    def __init__(self, delay=False, delay_time=0.5):
        self.delay = delay
        self.delayTime = delay_time

    def __enter__(self):
        self.w = self.window_cls.create(show=not self.delay)
        self.w.ctx = self
        if self.delay:
            self.timer = threading.Timer(self.delayTime, lambda: self.w.show())
            self.timer.start()
        return self

    def __exit__(self, exc_type, exc_value, tb):
        # The exception is passed on (False below), not swallowed: the caller used to carry on as
        # if the block had succeeded (S3 in the navigation review). A site that should carry on
        # catches it itself; whoever does gets the traceback, so this only notes it.
        if exc_type is not None:
            util.DEBUG_LOG("Busy context: {0} raised inside, passing it on", exc_type.__name__)

        if self.timer and self.timer.is_alive():
            self.timer.cancel()
            self.timer.join()

        self.w.doClose()
        ref = util.windowRef(self.w)
        del self.w
        self.w = None
        util.collectIfAlive(ref)
        return False


class BusyMsgContext(BusyContext):
    window_cls = BusyClosableMsgWindow

    def setMessage(self, msg):
        self.w.setMessage(msg)


class BusySignalContext(BusyMsgContext):
    """
    Duplicates functionality of plex.CallbackEvent to a certain degree
    """
    window_cls = BusyWindow
    delay = True

    def __init__(self, context, signal, wait_max=10, delay=True, delay_time=0.5):
        self.wfSignal = signal
        self.signalEmitter = context
        self.waitMax = wait_max
        self.ignoreSignal = False
        self.signalReceived = False

        super(BusySignalContext, self).__init__(delay=delay, delay_time=delay_time)

        context.on(signal, self.onSignal)

    def onSignal(self, *args, **kwargs):
        self.signalReceived = True

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            # A block that raised won't bring its signal: don't wait up to waitMax for it.
            if not self.ignoreSignal and exc_type is None:
                tries = 0
                while not self.signalReceived and tries < util.MONITOR.waitAmount(self.waitMax):
                    util.MONITOR.waitFor()
                    tries += 1
        finally:
            self.signalEmitter.off(self.wfSignal, self.onSignal)

        return super(BusySignalContext, self).__exit__(exc_type, exc_val, exc_tb)


class BusyClosableMsgContext(BusyMsgContext):
    pass


class BusyBlockingContext(BusyContext):
    window_cls = BlockingBusyWindow


class ProgressDialog(object):
    dialog = None
    header = None
    message = None

    def __init__(self, header, message=None, bg=True, raise_hard=False):
        self.header = header
        self.message = message
        self.bg = bg
        self.raise_hard = raise_hard

    def __enter__(self):
        self.dialog = xbmcgui.DialogProgressBG() if self.bg else xbmcgui.DialogProgress()
        self.dialog.create(self.header, self.message)
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if exc_type is not None:
            util.ERROR()

        # A plain Kodi dialog holds no Python references, so it can't be in a cycle and goes as soon
        # as it's dropped: no collection needed (E4 in the navigation review).
        self.dialog.close()
        del self.dialog
        self.dialog = None
        if exc_type is not None and self.raise_hard:
            raise exc_value
        return True

    def update(self, perc, header=None, message=None):
        if self.bg:
            self.dialog.update(perc, header or self.header, message or self.message)
        else:
            self.dialog.update(perc, message or self.message)

    def isCanceled(self):
        if self.bg:
            return False
        return self.dialog.iscanceled()
