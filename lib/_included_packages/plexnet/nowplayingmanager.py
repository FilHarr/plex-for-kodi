# Most of this is ported from Roku code and much of it is currently unused
# TODO: Perhaps remove unnecessary code
from __future__ import absolute_import
import time

from . import util
from six import moves
import six.moves.urllib.request, six.moves.urllib.parse, six.moves.urllib.error
import six.moves.urllib.parse
from . import plexrequest
from . import callback
from . import http


class ServerTimeline(util.AttributeDict):
    def reset(self):
        self.expires = time.time() + 10

    def isExpired(self):
        return time.time() > self.get('expires', 0)


class TimelineData(util.AttributeDict):
    def __init__(self, timelineType, *args, **kwargs):
        util.AttributeDict.__init__(self, *args, **kwargs)
        self.type = timelineType
        self.state = "stopped"
        self.itemData = None
        self.playQueue = None

        self.controllable = util.AttributeDict()
        self.controllableStr = None

        self.attrs = util.AttributeDict()

        # Set default controllable for all content. Other controllable aspects
        # will be set based on the players content.
        #
        self.setControllable("playPause", True)
        self.setControllable("stop", True)

    def setControllable(self, name, isControllable):
        if isControllable:
            self.controllable[name] = ""
        else:
            if name in self.controllable:
                del self.controllable[name]

        self.controllableStr = None

    def updateControllableStr(self):
        if not self.controllableStr:
            self.controllableStr = ""
            prependComma = False

            for name in self.controllable:
                if prependComma:
                    self.controllableStr += ','
                else:
                    prependComma = True
                self.controllableStr += name


class NowPlayingManager(object):
    def __init__(self):
        # Constants
        self.NAVIGATION = "navigation"
        self.FULLSCREEN_VIDEO = "fullScreenVideo"
        self.FULLSCREEN_MUSIC = "fullScreenMusic"
        self.FULLSCREEN_PHOTO = "fullScreenPhoto"
        self.TIMELINE_TYPES = ["video", "music", "photo"]

        # Members
        self.location = self.NAVIGATION

        self.textFieldName = None
        self.textFieldContent = None
        self.textFieldSecure = None

        # timeline reports sent and not answered yet (waitForTimelines())
        self._pendingTimelines = set()

        # Initialization
        self.reset()

    def reset(self):
        self.serverTimelines = util.AttributeDict()
        self.subscribers = util.AttributeDict()
        self.pollReplies = util.AttributeDict()
        self.timelines = util.AttributeDict()
        for timelineType in self.TIMELINE_TYPES:
            self.timelines[timelineType] = TimelineData(timelineType)

    def updatePlaybackState(self, timelineType, itemData, state, t, playQueue=None, duration=0, force=False,
                            continuing=False, force_time=False, server=None):
        timeline = self.timelines[timelineType]
        old_item_data = None
        if timeline.itemData:
            old_item_data = timeline.itemData.copy()

        timeline.itemData = itemData
        timeline.playQueue = playQueue
        old_time = timeline.attrs.get("time")
        old_state = timeline.state
        time_updated = False
        if state != "stopped" or force_time:
            timeline.attrs["time"] = str(t)
            time_updated = True

        elif old_time and (not old_item_data or old_item_data.ratingKey == itemData.ratingKey): # the second part might be unnecessary, check
            if old_state != "stopped":
                # use old timeline state's time for stopped states
                util.DEBUG_LOG("Using previous timeline state as we're stopped now: {}", old_time)
            else:
                util.DEBUG_LOG("Possibly using bad time for timeline state as we're stopped now but can't find a "
                               "non-stopped time: {}", old_time)

            # reuse old timestamp
            t = int(timeline.attrs["time"])
        else:
            util.DEBUG_LOG("Possibly using bad time for timeline state as we're stopped now but never seen a good time")
            timeline.attrs["time"] = str(t)
            time_updated = True
        timeline.state = state
        timeline.duration = duration

        self.sendTimelineToServer(timelineType, timeline, t, force=force, continuing=continuing, server=server)
        return time_updated

    def sendTimelineToServer(self, timelineType, timeline, t, force=False, continuing=False, server=None):
        # the item's own server (every caller passes it): there's no selected one to fall back on
        if not server:
            return

        serverTimeline = self.getServerTimeline(timelineType)

        # Only send timeline if it's the first, item changes, playstate changes or timer pops
        itemsEqual = timeline.itemData and serverTimeline.itemData \
            and timeline.itemData.ratingKey == serverTimeline.itemData.ratingKey
        if itemsEqual and timeline.state == serverTimeline.state and not serverTimeline.isExpired() and not force:
            return

        serverTimeline.reset()
        serverTimeline.itemData = timeline.itemData
        serverTimeline.state = timeline.state

        # It's possible with timers and in player seeking for the time to be greater than the
        # duration, which causes a 400, so in that case we'll set the time to the duration.
        duration = timeline.itemData.duration or timeline.duration
        if t > duration:
            t = duration

        params = util.AttributeDict()
        params["time"] = t
        params["duration"] = duration
        params["state"] = timeline.state
        params["guid"] = timeline.itemData.guid
        params["ratingKey"] = timeline.itemData.ratingKey
        params["url"] = timeline.itemData.url
        params["key"] = timeline.itemData.key
        params["containerKey"] = timeline.itemData.containerKey
        params["playbackTime"] = timeline.itemData.playbackTime
        params["continuing"] = continuing and "1" or "0"
        if timeline.itemData.additional_params:
            params.update(timeline.itemData.additional_params)

        if timeline.playQueue:
            params["playQueueItemID"] = timeline.playQueue.selectedId

        path = "/:/timeline"
        for paramKey in params:
            if params[paramKey]:
                path = http.addUrlParam(path, paramKey + "=" + six.moves.urllib.parse.quote(str(params[paramKey])))

        request = plexrequest.PlexRequest(server, path)

        context = request.createRequestContext("timelineUpdate", callback.Callable(self.onTimelineResponse))
        context.playQueue = timeline.playQueue
        context.timelineToken = token = object()
        self._pendingTimelines.add(token)
        if not util.APP.startRequest(request, context):
            self._pendingTimelines.discard(token)

    def waitForTimelines(self, timeout):
        """Until every timeline report sent has been answered, or timeout seconds. Back from
        playback, a screen that reloads what was played asks the server after its stop report has
        reached it - the server decides what counts as watched from it."""
        end = time.time() + timeout
        while self._pendingTimelines and time.time() < end:
            time.sleep(0.05)
        if self._pendingTimelines:
            util.DEBUG_LOG("NowPlaying: {0} timeline report(s) still unanswered after {1} s".format(
                len(self._pendingTimelines), timeout))

    def getServerTimeline(self, timelineType):
        if not self.serverTimelines.get(timelineType):
            serverTL = ServerTimeline()
            serverTL.reset()

            self.serverTimelines[timelineType] = serverTL

        return self.serverTimelines[timelineType]

    def nowPlayingSetControllable(self, timelineType, name, isControllable):
        self.timelines[timelineType].setControllable(name, isControllable)

    def onTimelineResponse(self, request, response, context):
        self._pendingTimelines.discard(getattr(context, 'timelineToken', None))
        context.request.server.trigger("np:timelineResponse", response=response)

        # Server may signal that the current stream was killed (admin "stop stream",
        # plan/concurrent-limit, server shutdown, etc.) by returning terminationCode
        # on the MediaContainer of the timeline reply. Surface it as a discrete signal
        # so the player can stop gracefully and tell the user why.
        #
        # The async timeline reply is a PlexResult whose .container is lazily built;
        # we must parseResponse() before the container is available.
        if response is not None:
            try:
                if getattr(response, "container", None) is None and hasattr(response, "parseResponse"):
                    response.parseResponse()
            except Exception:
                util.ERROR()

            container = getattr(response, "container", None)
            # What the server made of the report, which its status (200 regardless) doesn't say:
            # the reply's playbackState - "ignore" (thrown away), "progress" (resume point kept) or
            # "complete" (marked played). A report past the played threshold is ignored when the
            # session has had no progress accepted yet - start, seek straight to the end, stop:
            # nothing recorded (live on both servers, 2026-10-10). The request lines' own log is cut
            # short at the masked token, status and all.
            path = getattr(context.request, "path", "") or ""
            query = dict(six.moves.urllib.parse.parse_qsl(path.partition("?")[2]))
            event = getattr(response, "event", None)
            util.DEBUG_LOG("NowPlaying: timeline {0} at {1} for {2}: HTTP {3}, playbackState={4}".format(
                query.get("state"), query.get("time"), query.get("ratingKey"),
                event.status_code if event is not None else None,
                container.get("playbackState") if container is not None else None))
            if container is not None:
                try:
                    terminationCode = container.get("terminationCode", "-1").asInt()
                except Exception:
                    terminationCode = -1
                if terminationCode > -1:
                    terminationText = container.get("terminationText")
                    terminationText = str(terminationText) if terminationText else "Unknown"
                    util.WARN_LOG("Server terminated playback: code={0} text={1}",
                                  terminationCode, terminationText)
                    context.request.server.trigger(
                        "np:streamTerminated", code=terminationCode, reason=terminationText
                    )

        if not context.playQueue or not context.playQueue.refreshOnTimeline:
            return
        context.playQueue.refreshOnTimeline = False
        context.playQueue.refresh(False)
