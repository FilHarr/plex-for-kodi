# coding=utf-8
"""
lib/windows/seek_scan.py - hold left/right to scan the timeline (docs/hold-to-fast-forward.md): HoldDetector tells a
held key from taps by its pace, and Scan moves the scan position at its speed.

Importing lib.windows.* starts lib.player's monitor thread unless abort_requested is set first.
"""

from __future__ import absolute_import

import unittest

from kodienv import ENV

ENV.abort_requested = True
from lib.windows import seek_scan  # noqa: E402
from lib.windows.seek_scan import BACK, FORWARD, HoldDetector, Scan  # noqa: E402


def held(detector, direction=FORWARD, delay=0.5, interval=0.033, until=1.0, start=0.0):
    """A held key's presses: one, then repeats after delay, every interval, to until. Returns each answer."""
    answers = [detector.press(direction, start)]
    t = start + delay
    while t <= start + until:
        answers.append(detector.press(direction, t))
        t += interval
    return answers


class HoldDetectorTest(unittest.TestCase):
    """Sequences are from the debug log (2026-10-16): a PC keyboard and an Nvidia Shield remote."""

    def setUp(self):
        self.d = HoldDetector()

    def taps(self, times, direction=FORWARD):
        return [self.d.press(direction, t) for t in times]

    def test_a_single_press(self):
        self.assertEqual(self.d.press(FORWARD, 0.0), 'press')

    def test_a_held_pc_key(self):
        # press, its first repeat after the delay (both taps so far), fast repeats, the hold at the third
        answers = self.taps([41.033, 41.541, 41.583, 41.608, 41.633, 41.674, 41.700, 41.741])
        self.assertEqual(answers, ['press', 'press', 'repeat', 'repeat', 'hold', 'repeat', 'repeat', 'repeat'])

    def test_a_held_shield_key_in_clumps(self):
        # repeats two at once then a gap, up to 0.156s once held
        answers = self.taps([38.702, 39.115, 39.197, 39.238, 39.241, 39.397, 39.398, 39.398, 39.532, 39.534, 39.615,
                             39.656, 39.657, 39.782, 39.783, 39.866, 39.908, 39.989, 39.990, 40.073])
        self.assertEqual(answers[:5], ['press', 'press', 'repeat', 'repeat', 'hold'])
        self.assertEqual(set(answers[5:]), {'repeat'})

    def test_a_held_shield_key_with_a_slow_first_repeat(self):
        answers = self.taps([50.291, 50.625, 50.749, 50.792, 50.833])
        self.assertEqual(answers, ['press', 'press', 'press', 'repeat', 'hold'])

    def test_a_held_am6b_key(self):
        # four presses in 0.247s, at the edge of the first limit (0.25)
        answers = self.taps([44.025, 44.402, 44.488, 44.569, 44.650, 44.736])
        self.assertEqual(answers, ['press', 'press', 'repeat', 'repeat', 'hold', 'repeat'])

    def test_a_remote_repeating_every_tenth_of_a_second(self):
        self.assertIn('hold', held(self.d, delay=0.5, interval=0.098, until=1.0))

    def test_a_generic_held_key(self):
        answers = held(self.d)
        self.assertEqual(answers.count('hold'), 1)
        self.assertEqual(answers[:2], ['press', 'press'])

    def test_repeats_too_quick_for_taps_always_make_a_hold(self):
        self.assertLessEqual(HoldDetector.REPEAT_GAP * HoldDetector.HOLD_REPEATS, HoldDetector.HOLD_SPAN + 1e-9)

    def test_repeats_too_slow_are_taps(self):
        self.assertNotIn('hold', held(self.d, delay=0.5, interval=0.11, until=2.0))

    def test_the_quickest_pc_tapping_is_never_a_hold(self):
        answers = self.taps([49.366, 49.533, 49.617, 49.783, 50.008, 50.133, 50.275, 50.399, 50.541, 50.666, 50.791,
                             50.933, 51.074, 51.216, 51.341, 51.483])
        self.assertNotIn('hold', answers)
        # the one 0.084s gap is taken as a repeat: too quick for a tap
        self.assertEqual(answers.count('repeat'), 1)

    def test_steady_taps_are_never_a_hold(self):
        for gap in (0.12, 0.17, 0.25, 0.5):
            self.d.reset()
            self.assertEqual(set(self.taps([i * gap for i in range(20)])), {'press'}, gap)

    def test_a_tap_after_a_pause_counts(self):
        # lost on the Shield by the first version: a quick tap after a repeat-delay-like pause
        self.assertEqual(self.taps([44.138, 44.680, 44.823]), ['press'] * 3)
        self.d.reset()
        self.assertEqual(self.taps([27.163, 27.704, 27.830]), ['press'] * 3)

    def test_a_tap_then_a_hold(self):
        answers = self.taps([0.0, 0.2]) + held(self.d, start=0.2)[1:]
        self.assertIn('hold', answers)

    def test_a_direction_change_ends_the_run(self):
        self.taps([0.0, 0.5, 0.53, 0.56, 0.59])
        self.assertEqual(self.d.press(BACK, 0.6), 'press')

    def test_another_action_ends_the_run(self):
        self.taps([0.0, 0.5, 0.53, 0.56])
        self.d.reset()
        self.assertEqual(self.taps([0.58]), ['press'])

    def test_a_new_hold_after_letting_go(self):
        first = held(self.d, until=1.0)
        second = held(self.d, start=2.0, until=1.0)
        self.assertEqual((first.count('hold'), second.count('hold')), (1, 1))
        self.assertEqual(second[0], 'press')

    def test_the_hold_comes_before_the_first_seek_step(self):
        # a default repeat delay (0.5s), then the slowest repeats that still make a hold
        from lib.windows.seekdialog import SeekDialog
        step = HoldDetector.HOLD_SPAN / HoldDetector.HOLD_REPEATS - 1e-6
        times = [0.0, 0.5] + [0.5 + step * (i + 1) for i in range(HoldDetector.HOLD_REPEATS)]
        self.assertEqual(self.taps(times)[-1], 'hold')
        self.assertLess(times[-1], SeekDialog.FIRST_SEEK_STEP_DELAY)

    # during a scan: 'press' is a tap that changes the speed, anything else is ignored

    def test_the_starting_hold_does_nothing(self):
        self.d.held(FORWARD, 39.238)
        self.assertEqual(set(self.taps([39.241, 39.397, 39.398, 39.532])), {'repeat'})

    def test_a_tap_after_letting_go_of_the_starting_hold(self):
        # the quickest seen: 0.192s after the hold's last repeat
        self.d.held(FORWARD, 42.291)
        self.assertEqual(self.taps([42.333, 42.441, 42.633, 42.849]), ['repeat', 'repeat', 'press', 'press'])

    def test_taps_during_a_scan_all_count(self):
        self.d.held(FORWARD, 0.0)
        self.assertEqual(self.taps([1.0, 1.208, 1.376, 1.581, 1.749]), ['press'] * 5)

    def test_a_key_held_during_a_scan_counts_twice_then_not(self):
        self.d.held(FORWARD, 0.0)
        answers = self.taps([1.0, 1.5, 1.533, 1.566, 1.6, 1.633, 2.0])
        self.assertEqual([a == 'press' for a in answers], [True, True, False, False, False, False, True])

    def test_a_tap_the_other_way_counts_at_once(self):
        self.d.held(FORWARD, 0.0)
        self.assertEqual(self.taps([0.03], direction=BACK), ['press'])


class ScanTest(unittest.TestCase):
    DURATION = 2 * 60 * 60 * 1000

    def scan(self, offset=60000, direction=FORWARD):
        s = Scan(self.DURATION)
        s.start(offset, direction, 0.0)
        return s

    def test_starts_at_the_slowest(self):
        s = self.scan()
        self.assertEqual((s.offset, s.speed, s.direction), (60000, 2, FORWARD))

    def test_1x_is_30s_a_second(self):
        s = self.scan()
        self.assertEqual(s.advance(1.0), 60000 + 2 * 30000)

    def test_advances_by_elapsed_time_not_by_tick(self):
        late, steady = self.scan(), self.scan()
        late.advance(0.35)
        for t in (0.1, 0.2, 0.3, 0.35):
            steady.advance(t)
        self.assertEqual(late.offset, steady.offset)

    def test_scans_back(self):
        s = self.scan(offset=600000, direction=BACK)
        self.assertEqual(s.advance(1.0), 600000 - 60000)

    def test_presses_with_it_speed_up_to_the_top(self):
        s = self.scan()
        speeds = []
        for t in (0.0, 0.0, 0.0, 0.0):
            s.press(FORWARD, t)
            speeds.append(s.speed)
        self.assertEqual(speeds, [4, 8, 16, 16])
        self.assertEqual(s.advance(1.0), 60000 + 16 * 30000)  # eight minutes a second

    def test_presses_against_it_slow_down_stop_then_reverse(self):
        s = self.scan()
        s.press(FORWARD, 0.0)
        s.press(FORWARD, 0.0)
        steps = []
        for _ in range(5):
            s.press(BACK, 0.0)
            steps.append((s.direction, s.speed))
        self.assertEqual(steps, [(FORWARD, 4), (FORWARD, 2), (0, 0), (BACK, 2), (BACK, 4)])

    def test_reversing_from_back(self):
        s = self.scan(offset=600000, direction=BACK)
        s.press(FORWARD, 0.0)
        self.assertEqual((s.direction, s.speed), (0, 0))
        s.press(FORWARD, 0.0)
        self.assertEqual((s.direction, s.speed), (FORWARD, 2))

    def test_back_to_the_top_speed_and_no_further(self):
        s = self.scan()
        for _ in range(12):
            s.press(BACK, 0.0)
        self.assertEqual((s.direction, s.speed), (BACK, 16))

    def test_0x_stands_still(self):
        s = self.scan()
        s.press(BACK, 1.0)  # 1s at 2x, then stopped
        self.assertEqual(s.advance(5.0), 60000 + 2 * 30000)

    def test_a_press_keeps_the_distance_at_the_old_speed(self):
        s = self.scan()
        s.press(FORWARD, 1.0)  # 1s at 2x, then 4x
        self.assertEqual(s.advance(2.0), 60000 + 2 * 30000 + 4 * 30000)

    def test_stops_short_of_the_end_and_stays_on(self):
        s = self.scan(offset=self.DURATION - 20000)
        self.assertEqual(s.advance(10.0), self.DURATION - seek_scan.END_MARGIN)
        s.press(BACK, 10.0)  # stops, then reverses at the slowest
        s.press(BACK, 10.0)
        self.assertEqual(s.advance(11.0), self.DURATION - seek_scan.END_MARGIN - 60000)

    def test_stops_at_the_start(self):
        s = self.scan(offset=30000, direction=BACK)
        self.assertEqual(s.advance(10.0), 1)
        s.press(FORWARD, 10.0)
        s.press(FORWARD, 10.0)
        self.assertEqual(s.advance(11.0), 1 + 60000)

    def test_a_start_outside_the_range_is_clamped(self):
        self.assertEqual(self.scan(offset=0).offset, 1)
        self.assertEqual(self.scan(offset=self.DURATION).offset, self.DURATION - seek_scan.END_MARGIN)

    def test_a_clip_shorter_than_the_margin(self):
        s = Scan(3000)
        s.start(1500, FORWARD, 0.0)
        self.assertEqual(s.advance(1.0), 1)

    def test_label(self):
        s = self.scan()
        self.assertEqual((s.direction, s.label), (FORWARD, u'2x'))
        s.press(BACK, 0.0)
        self.assertEqual((s.direction, s.label), (0, u'0x'))
        s.press(BACK, 0.0)
        self.assertEqual((s.direction, s.label), (BACK, u'2x'))


if __name__ == '__main__':
    unittest.main()
