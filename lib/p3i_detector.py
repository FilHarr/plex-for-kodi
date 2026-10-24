# coding=utf-8
"""
p3i's black-border/L5 detection (CoreELEC p3i builds): skipping it for one video.

With "Pause for black-border or L5 detection" on (p3i T5, the default), playback holds on its first frame
until detection has scanned the video. On a Direct Stream or transcode - a live stream from the server, which
can't be read at arbitrary points - that scan took minutes or never finished (AM6B, T5 dev, 2026-10-19), so
_playVideo() skips it for those. Direct Play keeps it.

p3i's P3I.Detector JSON-RPC API (docs/detector-api.md in pannal/xbmc) arms the skip for the next video
submitted, and hands back a token that clears only that publication. Stock Kodi and p3i builds without the
API are asked once, and nothing changes for them. From pannal/plex-for-kodi f6412cb5.
"""
from __future__ import absolute_import

import json
import threading

from kodi_six import xbmc

_supported = None
_lock = threading.Lock()


def _rpc(method, params=None):
    request = {'jsonrpc': '2.0', 'id': 1, 'method': 'P3I.Detector.' + method}
    if params is not None:
        request['params'] = params
    try:
        response = json.loads(xbmc.executeJSONRPC(json.dumps(request)))
        result = response.get('result')
        return result if isinstance(result, dict) else None
    except Exception:
        return None


def supported():
    """Whether this Kodi has p3i's owned skip - asked once."""
    global _supported
    with _lock:
        if _supported is None:
            result = _rpc('GetCapabilities') or {}
            _supported = bool(result.get('version') == 1 and result.get('supported') and result.get('ownedskip'))
        return _supported


def arm_skip():
    """Skip detection for the next video submitted; its token, or None where there's nothing to skip."""
    if not supported():
        return None
    result = _rpc('SetSkipNext') or {}
    return result.get('token') if result.get('status') == 'armed' else None


def clear_skip(token):
    """Take back a skip that was never submitted. Kodi checks the token, so this can't clear one a newer
    request armed since."""
    if token is not None:
        _rpc('ClearSkipNext', {'token': token})
