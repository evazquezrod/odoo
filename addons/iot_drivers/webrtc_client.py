import asyncio
import json
import logging
import pprint
from threading import Thread
from aiortc import RTCPeerConnection, RTCSessionDescription

_logger = logging.getLogger(__name__)


class WebRtcClient(Thread):
    daemon = True

    def __init__(self):
        super().__init__()
        self.connections = set()
        self.event_loop = asyncio.get_event_loop_policy().get_event_loop()

    def offer(self, request):
        return asyncio.run_coroutine_threadsafe(
            self._offer(request), self.event_loop
        ).result()

    async def _offer(self, request):
        offer = RTCSessionDescription(sdp=request["sdp"], type=request["type"])

        peer_connection = RTCPeerConnection()
        self.connections.add(peer_connection)

        @peer_connection.on("datachannel")
        def on_datachannel(channel):
            @channel.on("message")
            def on_message(message_str):
                message = json.loads(message_str)
                message_type = message["message_type"]
                _logger.critical("Received message of type %s:\n%s", message_type, pprint.pformat(message))

        @peer_connection.on("connectionstatechange")
        async def on_connectionstatechange():
            if peer_connection.connectionState == "failed":
                await peer_connection.close()
                self.connections.discard(peer_connection)

        # handle offer
        await peer_connection.setRemoteDescription(offer)

        # send answer
        answer = await peer_connection.createAnswer()
        await peer_connection.setLocalDescription(answer)

        return {"sdp": peer_connection.localDescription.sdp, "type": peer_connection.localDescription.type}

    def run(self):
        self.event_loop.run_forever()


webrtc_client = WebRtcClient()
webrtc_client.start()
