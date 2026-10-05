class BadRequest(Exception):
    pass


class RateLimited(BadRequest):
    """A 429 from a server that rate-limits (plex.tv's Discover): retry_after seconds until it's
    asked again; from_cooldown when it wasn't asked at all, the wait from an earlier 429 not over
    yet (PlexServer.query()). Ported from pannal/plex-for-kodi 4f9b12d1."""
    def __init__(self, retry_after=60, from_cooldown=False):
        self.retry_after = retry_after
        self.from_cooldown = from_cooldown
        super(RateLimited, self).__init__('(429) too_many_requests; retry after {0}s'.format(retry_after))


class NotFound(Exception):
    pass


class UnknownType(Exception):
    pass


class Unsupported(Exception):
    pass


class Unauthorized(Exception):
    pass


class ServerNotOwned(Exception):
    pass


class UserSwitchForbiddenException(Exception):
    pass
