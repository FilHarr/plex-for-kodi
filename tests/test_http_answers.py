# coding=utf-8
"""
Callers of async plex.tv / PMS requests that get a failed answer: an error status, or (once
requests always answer) no response at all.

A failed play queue request used to leave waitForInitialization() spinning until canceled, failed
home users crashed on None, and plex.tv failing with nothing cached stripped every plex.tv
connection (and its token) from the servers already known.
"""

from __future__ import absolute_import

from kodienv import ENV

ENV.abort_requested = True
from plexnet import http, myplexaccount, myplexmanager, plexapp, playqueue, plexresult, plexserver  # noqa: E402
from plexnet import util as pnUtil  # noqa: E402

from .base import KodiTestCase, ensure_plex_interface  # noqa: E402

try:
    from unittest import mock
except ImportError:
    import mock

UUID = "50c3d0b05067c152d84935cdea0ac8af7fc31d06"


def failed_result(server=None, path="/"):
    result = plexresult.PlexServerResult(server, path)
    result.setResponse(None)
    return result


class FailingCallersTest(KodiTestCase):
    """Callers that only ever saw error statuses before, and now also see connection failures."""

    def setUp(self):
        KodiTestCase.setUp(self)
        ensure_plex_interface()

    def test_a_failed_play_queue_request_ends_the_wait(self):
        pq = playqueue.PlayQueue(plexserver.createPlexServerForName(UUID, "Oscar"), "audio")
        ctx = http.RequestContext()
        ctx.requestType = "create"
        pq.onResponse(None, failed_result(), ctx)
        self.assertTrue(pq.failed)
        # returns at once instead of spinning on responded
        self.assertFalse(pq.waitForInitialization())

    def test_failed_home_users_keep_the_known_list(self):
        account = myplexaccount.MyPlexAccount()
        account.homeUsers = ["kept"]
        account.onHomeUsersUpdateResponse(None, failed_result(), None)
        self.assertEqual(["kept"], account.homeUsers)

    def test_no_resources_and_no_cache_keeps_the_known_servers(self):
        manager = myplexmanager.MyPlexManager()
        servers = mock.Mock()
        with mock.patch.object(pnUtil.INTERFACE, "getRegistry", return_value=None), \
                mock.patch.object(plexapp, "SERVERMANAGER", servers):
            manager.onResourcesResponse(None, failed_result(), None)
        servers.resourcesUnavailable.assert_called_once_with()
        servers.updateFromConnectionType.assert_not_called()
