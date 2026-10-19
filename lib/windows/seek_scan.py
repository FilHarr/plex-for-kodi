# coding=utf-8
"""
Hold left/right to scan the timeline (docs/hold-to-fast-forward.md): telling a held key from taps, and the scan's
position and speed. Kodi-free, so both are unit-tested (tests/test_seek_scan.py); SeekDialog feeds them times and
key presses and draws the result.
"""
from __future__ import absolute_import

FORWARD = 1
BACK = -1

# 1x is 30s of video a second, the OSD-hidden skip's step
SCAN_UNIT = 30000
SPEEDS = (2, 4, 8, 16)
# a scan stops this far short of the end, as seekByOffset() does
END_MARGIN = 5000


class HoldDetector(object):
    """
    Python add-ons get no hold time and no key-up: a held key is the same action repeated. What sets it apart from
    taps is its pace once it repeats: four presses in a row (HOLD_REPEATS gaps) within HOLD_SPAN, faster than anyone
    taps. Measured (2026-10-16/17, debug log): a PC keyboard repeats every 25-60ms; an Nvidia Shield remote every
    40-80ms, but Kodi takes its input once a frame - 24 a second during a film - so repeats come in clumps, two at once
    then a gap of up to 0.156s; the AM6B's remotes about every 83ms, four presses taking up to 0.25s. Taps were 0.12s
    apart at the quickest (once 0.084s); four took at least 0.39s.

    press() answers 'hold' once, for the press that makes one; 'repeat' for a press under REPEAT_GAP after the last -
    too quick for a tap - and for a held key's presses after its hold, which may come up to HELD_GAP apart; and
    'press' for anything else, a tap. A held key's press and first repeat (after its repeat delay, about 0.5s) are
    taps by then, so its hold comes after two skips.

    The same answers serve during a scan: a 'press' changes the speed, the rest are ignored - so taps count, and a key
    held during the scan counts twice (press and first repeat), then not.
    """
    # REPEAT_GAP x HOLD_REPEATS mustn't pass HOLD_SPAN: a key whose every repeat is too quick for a tap is always a hold
    REPEAT_GAP = 0.1
    HOLD_REPEATS = 3
    HOLD_SPAN = 0.3
    HELD_GAP = 0.17

    def __init__(self):
        self.reset()

    def reset(self):
        """Ends the run: some other action arrived."""
        self._direction = None
        self._last = None
        self._gaps = []  # the run's last HOLD_REPEATS gaps
        self._held = False
        self.gap = None  # the last press's gap from the one before in the run (for the log)

    def held(self, direction, now):
        """The hold that started a scan: while the key stays down, its repeats are ignored."""
        self.reset()
        self._direction = direction
        self._last = now
        self._held = True

    def press(self, direction, now):
        gap = now - self._last if direction == self._direction and self._last is not None else None
        self.gap = gap
        self._direction = direction
        self._last = now

        if gap is None:
            self._gaps = []
            self._held = False
            return 'press'

        if self._held:
            if gap <= self.HELD_GAP:
                return 'repeat'
            # let go, and pressed again
            self._held = False
            self._gaps = []

        self._gaps = (self._gaps + [gap])[-self.HOLD_REPEATS:]
        if len(self._gaps) == self.HOLD_REPEATS and sum(self._gaps) <= self.HOLD_SPAN:
            self._held = True
            return 'hold'
        return 'repeat' if gap <= self.REPEAT_GAP else 'press'


class Scan(object):
    """
    A scan's position: moving on its own at speed x SCAN_UNIT a second of real time, between 1 (0 isn't a seek) and
    END_MARGIN short of the end. Latched: it runs until SeekDialog applies or cancels it.

    Its speeds are one scale, -16x to 16x through 0x (stopped): a tap right moves a step towards forward, left a step
    towards back. So with the scan, a tap speeds it up (staying at the top speed); against it, slows it down, past the
    slowest stops it, and then reverses it.
    """
    def __init__(self, duration, speeds=SPEEDS, unit=SCAN_UNIT, end_margin=END_MARGIN):
        self.speeds = speeds
        self.unit = unit
        self.low = 1
        self.high = max(self.low, duration - end_margin)
        self._offset = 0
        self._level = 0  # the speed's place on the scale: 0 stopped, +n speeds[n - 1] forward, -n back
        self._last = None

    def _clamp(self, offset):
        return min(max(offset, self.low), self.high)

    def start(self, offset, direction, now):
        self._offset = self._clamp(offset)
        self._level = direction
        self._last = now

    @property
    def offset(self):
        return int(self._offset)

    @property
    def direction(self):
        """FORWARD, BACK, or 0 stopped."""
        return (self._level > 0) - (self._level < 0)

    @property
    def speed(self):
        return self._level and self.speeds[abs(self._level) - 1]

    @property
    def label(self):
        """The speed, such as "4x"; the OSD draws the direction's icon beside it (SeekDialog.showScanSpeed())."""
        return u'{0}x'.format(self.speed)

    def advance(self, now):
        """
        Moves by the real time since the last call, not a fixed step, so a late tick doesn't slow it. At either end it
        stops there and stays on, so a tap can still reverse it.
        """
        elapsed = max(0.0, now - self._last)
        self._last = now
        self._offset = self._clamp(self._offset + self.direction * self.speed * self.unit * elapsed)
        return self.offset

    def press(self, direction, now):
        """A tap during the scan: a step along the scale, at the speed so far up to now."""
        self.advance(now)
        top = len(self.speeds)
        self._level = min(max(self._level + direction, -top), top)
