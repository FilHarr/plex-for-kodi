# coding=utf-8
"""
The confirm and message box (lib/windows/optionsdialog.py) is as tall as its message: messageLines() counts the
message's wrapped lines in font10, and OptionsDialog.fitFrame() sizes the message box, the panel and its shadow to
them, puts the answers under the message and centres the panel. The real methods are bound onto a small double whose
controls record what they're given.

Importing lib.windows.* starts lib.player's monitor thread unless abort_requested is set first - same guard the other
lib.windows.* tests use for the same reason.
"""

from __future__ import absolute_import

from kodienv import ENV

ENV.abort_requested = True
from lib import util  # noqa: E402
from lib.windows import optionsdialog  # noqa: E402

from .base import KodiTestCase  # noqa: E402


class FakeControl(object):
    def __init__(self):
        self.height = None
        self.position = None

    def setHeight(self, height):
        self.height = height

    def setPosition(self, x, y):
        self.position = (x, y)


class FakeDialog(object):
    D = optionsdialog.OptionsDialog
    FRAME_WIDTH, HEADING, LINE_HEIGHT, MAX_LINES, GAP, BUTTONS = (D.FRAME_WIDTH, D.HEADING, D.LINE_HEIGHT, D.MAX_LINES,
                                                                 D.GAP, D.BUTTONS)
    DESCENDER_ROOM = D.DESCENDER_ROOM
    BUTTONS_GROUP_ID, FRAME_GROUP_ID, FRAME_BACKDROP_ID, FRAME_SHADOW_ID, MESSAGE_ID = (
        D.BUTTONS_GROUP_ID, D.FRAME_GROUP_ID, D.FRAME_BACKDROP_ID, D.FRAME_SHADOW_ID, D.MESSAGE_ID)
    width, height = D.width, D.height
    fitFrame = D.fitFrame

    def __init__(self, info):
        self.info = info
        self.controls = dict((cid, FakeControl()) for cid in (self.BUTTONS_GROUP_ID, self.FRAME_GROUP_ID,
                                                               self.FRAME_BACKDROP_ID, self.FRAME_SHADOW_ID,
                                                               self.MESSAGE_ID))

    def getControl(self, cid):
        if cid not in self.controls:
            # as Kodi answers for the answers' grouplist (100)
            raise RuntimeError('Unknown control type for python')
        return self.controls[cid]


class MessageLinesTest(KodiTestCase):
    def test_a_short_message_is_one_line(self):
        self.assertEqual(1, optionsdialog.messageLines('Are you ready to exit Plex?'))

    def test_a_long_message_wraps(self):
        text = ' '.join(['word'] * 60)
        self.assertGreater(optionsdialog.messageLines(text), 2)

    def test_line_breaks_and_empty_lines_count(self):
        self.assertEqual(4, optionsdialog.messageLines('one\n\ntwo\nthree'))

    def test_formatting_tags_take_no_room(self):
        plain = 'Delete episode S05E14 from The Lord of the Rings: The Rings of Power?'
        self.assertEqual(optionsdialog.messageLines(plain),
                         optionsdialog.messageLines('[B]' + plain.replace('Delete', '[COLOR FFD45B55]Delete[/COLOR]') + '[/B]'))

    def test_nothing_is_one_line(self):
        self.assertEqual(1, optionsdialog.messageLines(''))
        self.assertEqual(1, optionsdialog.messageLines(None))


class FitFrameTest(KodiTestCase):
    def fit(self, info):
        d = FakeDialog(info)
        d.fitFrame()
        return d.controls

    def test_a_one_line_message(self):
        c = self.fit('Are you ready to exit Plex?')
        D = optionsdialog.OptionsDialog
        # room under the last line for a g's tail, the layout still a line's
        self.assertEqual(util.vscalei(D.LINE_HEIGHT + D.DESCENDER_ROOM), c[D.MESSAGE_ID].height)
        height = D.HEADING + D.LINE_HEIGHT + D.GAP + D.BUTTONS + D.GAP
        self.assertEqual(util.vscalei(height), c[D.FRAME_BACKDROP_ID].height)
        self.assertEqual(util.vscalei(height + 80), c[D.FRAME_SHADOW_ID].height)
        # the answers just under the message, the panel centred
        self.assertEqual((20, util.vscalei(D.HEADING + D.LINE_HEIGHT + D.GAP)), c[D.BUTTONS_GROUP_ID].position)
        self.assertEqual(((1920 - 640) // 2, util.vscalei((1080 - height) // 2)), c[D.FRAME_GROUP_ID].position)

    def test_more_lines_make_it_taller_and_keep_it_centred(self):
        D = optionsdialog.OptionsDialog
        short = self.fit('one')
        tall = self.fit('one\ntwo\nthree')
        self.assertGreater(tall[D.FRAME_BACKDROP_ID].height, short[D.FRAME_BACKDROP_ID].height)
        self.assertLess(tall[D.FRAME_GROUP_ID].position[1], short[D.FRAME_GROUP_ID].position[1])

    def test_every_control_is_fitted(self):
        # a getControl() Kodi refuses stops the rest: the frame then stays one line tall round a taller message
        D = optionsdialog.OptionsDialog
        c = self.fit('one\ntwo\nthree')
        for cid in (D.MESSAGE_ID, D.FRAME_BACKDROP_ID, D.FRAME_SHADOW_ID):
            self.assertIsNotNone(c[cid].height)
        for cid in (D.BUTTONS_GROUP_ID, D.FRAME_GROUP_ID):
            self.assertIsNotNone(c[cid].position)

    def test_the_message_box_stops_growing_at_its_cap(self):
        D = optionsdialog.OptionsDialog
        c = self.fit('\n'.join(['line'] * 40))
        self.assertEqual(util.vscalei(D.MAX_LINES * D.LINE_HEIGHT + D.DESCENDER_ROOM), c[D.MESSAGE_ID].height)

    def test_no_message_leaves_the_heading_and_the_answers(self):
        # an item action's confirm ("Mark Played?"): the answers straight under the heading, no empty line
        D = optionsdialog.OptionsDialog
        for info in ('', None, '  '):
            c = self.fit(info)
            self.assertEqual(0, c[D.MESSAGE_ID].height)
            self.assertEqual((20, util.vscalei(D.HEADING)), c[D.BUTTONS_GROUP_ID].position)
            self.assertEqual(util.vscalei(D.HEADING + D.BUTTONS + D.GAP), c[D.FRAME_BACKDROP_ID].height)

    def test_the_room_under_the_last_line_is_less_than_a_line(self):
        # Kodi's textbox shows floor(height / 27.8) lines: the room must never let part of a 13th show
        D = optionsdialog.OptionsDialog
        self.assertEqual(D.MAX_LINES, int((D.MAX_LINES * D.LINE_HEIGHT + D.DESCENDER_ROOM) / 27.8))


class ConfirmDeleteTest(KodiTestCase):
    class Item(dict):
        def __init__(self, TYPE, defaultTitle, **fields):
            dict.__init__(self, fields)
            self.TYPE, self.defaultTitle = TYPE, defaultTitle

    def asked(self, item, answer):
        shown = []

        def show(*args, **kwargs):
            shown.append(args)
            return answer
        real, optionsdialog.show = optionsdialog.show, show
        try:
            return optionsdialog.confirmDelete(item), shown[0]
        finally:
            optionsdialog.show = real

    def test_names_the_item_under_the_heading_as_its_menu_does(self):
        episode = self.Item('episode', 'Pilot', grandparentTitle='The Show', parentIndex=1, index=2)
        yes, args = self.asked(episode, 0)
        self.assertTrue(yes)
        self.assertEqual((util.T(32326, 'Really delete?'), u'The Show (S1 • E2)'), args[:2])
        self.assertEqual(u'Heat (1995)', self.asked(self.Item('movie', 'Heat', year=1995), 0)[1][1])

    def test_anything_but_yes_is_no(self):
        for answer in (1, None):
            self.assertFalse(self.asked(self.Item('movie', 'Heat', year=1995), answer)[0])


class DestructiveTest(KodiTestCase):
    def test_wraps_the_label_in_the_muted_red(self):
        self.assertEqual(u'[COLOR FFD45B55]Yes[/COLOR]', optionsdialog.destructive(u'Yes'))
