import asyncio
import time
import unittest
from unittest.mock import AsyncMock, patch

from comet.cometnet.protocol import HandshakeMessage
from comet.cometnet.transport import ConnectionManager, NodeIdentity, PeerConnection


class _Identity:
    node_id = "local"
    public_key_hex = "local-key"

    async def sign_hex_async(self, payload):
        del payload
        return "signature"


class _Peer:
    def __init__(self):
        self.node_id = "peer"
        self.last_activity = time.time()
        self.pending_pings = {}
        self.latency_samples = []
        self.latency_ms = 0
        self.send_started = asyncio.Event()
        self.send_cancelled = asyncio.Event()

    async def send(self, message):
        del message
        self.send_started.set()
        try:
            await asyncio.Event().wait()
        finally:
            self.send_cancelled.set()


class CometNetTransportTests(unittest.IsolatedAsyncioTestCase):
    async def test_duplicate_inbound_handshake_releases_reserved_ip_slot(self):
        manager = ConnectionManager(_Identity())
        manager._connections["peer"] = object()
        manager._connections_per_ip["203.0.113.1"] = 1
        handshake = HandshakeMessage(
            sender_id="peer",
            public_key="peer-key",
            signature="signature",
        )

        class WebSocket:
            closed = False

            async def recv(self):
                return handshake.to_bytes()

            async def send(self, payload):
                del payload

            async def close(self):
                self.closed = True

        websocket = WebSocket()
        with (
            patch.object(
                NodeIdentity,
                "verify_hex_async",
                new=AsyncMock(return_value=True),
            ),
            patch.object(
                NodeIdentity,
                "node_id_from_public_key",
                return_value="peer",
            ),
        ):
            node_id = await manager.handle_incoming_connection(
                websocket,
                "203.0.113.1",
            )

        self.assertIsNone(node_id)
        self.assertTrue(websocket.closed)
        self.assertEqual(manager._connections_per_ip["203.0.113.1"], 1)

    async def test_disconnect_tolerates_receive_loop_removing_connection(self):
        manager = ConnectionManager(_Identity())

        class Connection:
            async def close(inner_self):
                del inner_self
                manager._connections.pop("peer", None)

        manager._connections["peer"] = Connection()

        await manager.disconnect_peer("peer")

        self.assertNotIn("peer", manager._connections)

    async def test_old_receive_loop_does_not_remove_replacement_connection(self):
        manager = ConnectionManager(_Identity())
        old_connection = PeerConnection(
            node_id="peer",
            address="ws://old",
            websocket=object(),
        )
        replacement = object()
        manager._connections["peer"] = replacement

        await manager._receive_loop(old_connection)

        self.assertIs(manager._connections["peer"], replacement)

    async def test_ping_loop_owns_and_cancels_send_operations(self):
        manager = ConnectionManager(_Identity())
        peer = _Peer()
        manager._connections[peer.node_id] = peer
        manager._running = True

        with patch(
            "comet.cometnet.transport.settings.COMETNET_TRANSPORT_PING_INTERVAL",
            0,
        ):
            ping_loop = asyncio.create_task(manager._ping_loop())
            await peer.send_started.wait()
            ping_loop.cancel()
            await ping_loop

        self.assertTrue(peer.send_cancelled.is_set())
