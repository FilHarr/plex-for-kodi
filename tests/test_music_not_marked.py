# coding=utf-8
"""
Music isn't marked played or unplayed, as in Plex's own apps: plexnet's Audio items have no markWatched(), and
CommonMixin.toggleWatched() - every mark, the watched key's included - leaves them alone without asking, rather
than asking and then erroring. Video still marks.

Importing lib.windows.* starts lib.player's monitor thread unless abort_requested is set first - same guard the other
lib.windows.* tests use for the same reason.
"""

from __future__ import absolute_import

from kodienv import ENV

ENV.abort_requested = True
from plexnet import audio, video  # noqa: E402
from lib.windows.mixins import common  # noqa: E402

from .base import KodiTestCase  # noqa: E402


class Screen(common.CommonMixin):
    pass


class MusicNotMarkedTest(KodiTestCase):
    def test_audio_items_cannot_be_marked(self):
        for cls in (audio.Artist, audio.Album, audio.Track):
            self.assertFalse(callable(getattr(cls, 'markWatched', None)), cls)
        for cls in (video.Movie, video.Episode, video.Season, video.Show):
            self.assertTrue(callable(getattr(cls, 'markWatched', None)), cls)

    def test_music_is_left_alone_without_asking(self):
        asked = []
        real = common.optionsdialog.show
        common.optionsdialog.show = lambda *a, **k: asked.append(a)
        try:
            track = audio.Track.__new__(audio.Track)
            self.assertIsNone(Screen().toggleWatched(track, state=True))
        finally:
            common.optionsdialog.show = real
        self.assertEqual([], asked)
