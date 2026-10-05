# coding=utf-8

import os
import json
import time
import copy
import zlib

from kodi_six import xbmcvfs

from plexnet import plexapp

from . util import translatePath, ADDON, ERROR, DEBUG_LOG, LOG


class DataCacheManager(object):
    # store arbitrary data in JSON on disk
    DATA_CACHES_VERSION = 2
    DATA_CACHES = {
        "general": {},
        "cache": {}
    }
    DC_LAST_UPDATE = None
    DC_PATH = os.path.join(translatePath(ADDON.getAddonInfo("profile")), "data_cache.json")
    DC_LRU_TIMEOUT = 30
    DC_LRUP_TIMEOUT = 90
    USE_GZ = False

    def __init__(self):
        if self.USE_GZ:
            self.DC_PATH += "z"
        if xbmcvfs.exists(self.DC_PATH):
            try:
                f = xbmcvfs.File(self.DC_PATH)
                try:
                    d = f.readBytes() if self.USE_GZ else f.read()
                finally:
                    f.close()

                tdc = json.loads(zlib.decompress(d).decode("utf-8") if self.USE_GZ else d)
                old_ver = tdc["general"].get("version", 0)
                if old_ver < self.DATA_CACHES_VERSION:
                    # this is where we migrate
                    if old_ver == 1:
                        tdc = self.DATA_CACHES.copy()
                    tdc["general"]["version"] = self.DATA_CACHES_VERSION
                    tdc["general"]["updated"] = time.time()
                    self.DATA_CACHES = tdc
                    self.storeDataCache()
                else:
                    tdc["general"]["version"] = self.DATA_CACHES_VERSION
                    self.DATA_CACHES.update(tdc)
                self.dataCacheCleanup()
                self.DC_LAST_UPDATE = self.DATA_CACHES["general"]["updated"]
            except:
                ERROR("Couldn't read data_cache.json")
                self.DATA_CACHES["general"]["updated"] = time.time()
                self.storeDataCache()

    def _scope(self, server):
        """The cache's per-server part: the item's own server."""
        uuid = getattr(server, 'uuid', None)
        return uuid[-8:] if uuid else None

    def getCacheData(self, context, identifier, server=None):
        scope = self._scope(server)
        ret = self.DATA_CACHES["cache"].get(scope, {}).get(context, {}).get(identifier, {})
        if "data" in ret and ret["data"]:
            # purge old data (> X days last updated)
            if ret["updated"] < time.time() - self.DC_LRUP_TIMEOUT * 3600 * 24:
                del self.DATA_CACHES["cache"][scope][context][identifier]
                return None

            self.DATA_CACHES["cache"][scope][context][identifier]["last_access"] = time.time()
            return ret["data"]

    def setCacheData(self, context, identifier, value, server=None):
        scope = self._scope(server)
        if scope not in self.DATA_CACHES["cache"]:
            self.DATA_CACHES["cache"][scope] = {}
        if context not in self.DATA_CACHES["cache"][scope]:
            self.DATA_CACHES["cache"][scope][context] = {}
        if identifier not in self.DATA_CACHES["cache"][scope][context]:
            self.DATA_CACHES["cache"][scope][context][identifier] = {}
        t = time.time()
        self.DATA_CACHES["general"]["updated"] = t
        self.DATA_CACHES["cache"][scope][context][identifier] = {
            "updated": t,
            "last_access": t,
            "data": value
        }

    def dataCacheCleanup(self):
        d = copy.deepcopy(self.DATA_CACHES)
        t = time.time()
        for k, contexts in d["cache"].items():
            for context, identifiers in contexts.items():
                for identifier, iddata in identifiers.items():
                    # clean up anything not accessed during the last X days
                    if iddata["last_access"] < t - self.DC_LRU_TIMEOUT * 3600 * 24:
                        DEBUG_LOG("Clearing cached data for: {}: {}".format(context, identifier))
                        del self.DATA_CACHES["cache"][k][context][identifier]

    def storeDataCache(self):
        lu = self.DATA_CACHES["general"].get("updated")
        if self.DATA_CACHES and lu and self.DC_LAST_UPDATE != lu:
            try:
                dcf = xbmcvfs.File(self.DC_PATH, "w")
                try:
                    self.dataCacheCleanup()
                    d = json.dumps(self.DATA_CACHES)
                    if self.USE_GZ:
                        d = zlib.compress(d.encode("utf-8"))
                    dcf.write(d)
                finally:
                    dcf.close()
                LOG("Data cache written to: addon_data/script.plexmod/data_cache.json")
            except:
                ERROR("Couldn't write data_cache.json")


dcm = DataCacheManager()
