# coding=utf-8
"""A film's or show's cast & crew: Discover's whole list when it answers, the server's own
otherwise.

The server keeps only a short list - a film's cast plus its directors, writers and producers, a
show's cast - where Discover has everyone (Gravity: 12 on the server, 293 on Discover; checked
2026-10-08). The film and show screens' Cast & Crew row shows the first ROW_MAX of them, the rest
behind its "See more" tile (see_more.py's credits grid), on request (2026-10-08)."""
from __future__ import absolute_import

import threading
from collections import OrderedDict
from xml.etree import ElementTree

from lib import util
from plexnet import media
from plexnet import plexapp
from plexnet import util as pnUtil

# How many credits the row shows before its "See more" tile
ROW_MAX = 20
# How many of the directors the row puts first, when show_directors is on - as many as the server
# list's combined_roles always put first
ROW_DIRECTORS = 2
# Titles whose Discover credits are kept, most recently asked last: Back to a title, and its grid,
# find them without asking again
CACHE_SIZE = 30

_cache = OrderedDict()
_cacheLock = threading.Lock()


class Credits(object):
    """cast and crew: lists of media.Role, in their source's order. directors: the crew's directors,
    for the row's lead (row())."""
    def __init__(self, cast, crew, directors, source):
        self.cast = cast
        self.crew = crew
        self.directors = directors
        self.source = source

    @property
    def total(self):
        return len(self.cast) + len(self.crew)

    def row(self, directors_first=True):
        """The row's credits: up to ROW_DIRECTORS directors, then the cast and the rest of the crew
        in order, ROW_MAX in all. A director who is also a writer keeps that second credit - the
        lead is taken by object, not by person."""
        lead = self.directors[:ROW_DIRECTORS] if directors_first else []
        taken = set(id(role) for role in lead)
        rest = [role for role in self.cast + self.crew if id(role) not in taken]
        return (lead + rest)[:ROW_MAX]


def forItem(item):
    """The credits of item, a full Movie or Show: Discover's when it has them for the item's plex://
    guid, the server's otherwise - an unmatched item, local mode, no plex.tv account, or Discover
    not answering. Asks Discover, so not on the UI thread."""
    discoverId = _discoverId(item)
    if discoverId:
        credits = _cached(discoverId)
        if credits is None:
            credits = _fromDiscover(item, discoverId)
            if credits is not None:
                _store(discoverId, credits)
        if credits is not None:
            return credits
    return _fromServer(item)


def cachedForItem(item):
    """forItem() without asking anyone: the credits already fetched for item, or its server's. For
    the UI thread - the grid, opened from a row forItem() filled, or rebuilt by Back."""
    discoverId = _discoverId(item)
    credits = _cached(discoverId) if discoverId else None
    return credits if credits is not None else _fromServer(item)


def _discoverId(item):
    guid = str(item.get('guid') or '')
    if not guid.startswith('plex://'):
        return None
    return guid.rsplit('/', 1)[-1] or None


def _cached(discoverId):
    with _cacheLock:
        credits = _cache.get(discoverId)
        if credits is not None:
            _cache.move_to_end(discoverId)
        return credits


def _store(discoverId, credits):
    with _cacheLock:
        _cache[discoverId] = credits
        _cache.move_to_end(discoverId)
        while len(_cache) > CACHE_SIZE:
            _cache.popitem(last=False)


def _fromDiscover(item, discoverId):
    """GET /library/metadata/{id}/credits on Discover: <CreditGroup title="Cast" type="actor"> and
    <CreditGroup title="Crew" type="other">, each a list of <Role id tag role thumb .../>. Always
    the whole list - X-Plex-Container-Size, count and limit are all ignored (checked 2026-10-08).
    Through the Discover server's query() for its 429 cooldown and token masking, as the Watchlist
    asks it (mixins/watchlist.py). None when it can't be had."""
    if pnUtil.LOCAL_MODE:
        return None
    account = plexapp.ACCOUNT
    if not account or not account.authToken:
        return None
    try:
        data = pnUtil.SERVERMANAGER.getDiscoverServer().query(
            '/library/metadata/{0}/credits'.format(discoverId))
    except Exception as e:
        util.DEBUG_LOG('Credits: no Discover credits for {0}: {1}', discoverId, e)
        return None
    if data is None:
        return None

    cast, crew, directors = [], [], []
    for group in data.findall('CreditGroup'):
        isCast = group.get('type') == 'actor'
        for elem in group.findall('Role'):
            role = _role(elem, item.server, isCast)
            if role is None:
                continue
            if isCast:
                cast.append(role)
            else:
                crew.append(role)
                if elem.get('role') == 'Director':
                    directors.append(role)
    if not cast and not crew:
        return None
    return Credits(cast, crew, directors, 'discover')


def _role(elem, server, isCast):
    """A Discover credit as the media.Role the row and the person screen take. Discover's id is the
    person's tagKey on every server (checked live, Alien's 16 people), which is what the person
    screen opens by (person.personKey()). A crew job the add-on has a string for (Director, Writer,
    Producer) is translated; the others stay in Discover's English."""
    key = elem.get('id')
    if not key or not elem.get('tag'):
        return None
    attrib = {'id': key, 'tagKey': key, 'tag': elem.get('tag')}
    if elem.get('thumb'):
        attrib['thumb'] = elem.get('thumb')
    job = elem.get('role') or ''
    if not isCast and job in util.TRANSLATED_ROLES:
        job = util.TRANSLATED_ROLES[job]
    if job:
        attrib['role'] = job
    return media.Role(ElementTree.Element('Role', attrib), server=server)


def _tags(item, name):
    tags = getattr(item, name, None)
    return list(tags()) if tags else []


def _fromServer(item):
    """The server's own credits: a film's cast, then its directors, writers and producers as the
    crew; a show's cast and directors (the show level has no writers or producers)."""
    directors = _tags(item, 'directors')
    crew = directors + _tags(item, 'writers') + _tags(item, 'producers')
    return Credits(_tags(item, 'roles'), crew, directors, 'server')
