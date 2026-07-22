import asyncio
import unittest
from unittest.mock import patch

from comet.cometnet.gossip import GossipEngine


def _engine_with_queue(*items):
    engine = GossipEngine(object(), None)
    engine._outgoing_queue.extend(items)
    engine._get_random_peers = lambda *args: []
    engine._send_message = object()
    engine._running = True
    engine.gossip_interval = 0
    return engine


class CometNetGossipTests(unittest.IsolatedAsyncioTestCase):
    async def test_stop_cancels_both_workers_and_clears_references(self):
        engine = GossipEngine(object(), None)
        engine._running = True
        engine._gossip_task = asyncio.create_task(asyncio.Event().wait())
        engine._cleanup_task = asyncio.create_task(asyncio.Event().wait())
        gossip_task = engine._gossip_task
        cleanup_task = engine._cleanup_task

        await engine.stop()

        self.assertTrue(gossip_task.cancelled())
        self.assertTrue(cleanup_task.cancelled())
        self.assertIsNone(engine._gossip_task)
        self.assertIsNone(engine._cleanup_task)

    async def test_batch_is_requeued_when_no_peer_is_reached(self):
        engine = _engine_with_queue("first", "second")

        async def no_peer(batch, ttl):
            del batch, ttl
            engine._running = False
            return 0

        with patch.object(engine, "_repropagate", new=no_peer):
            await engine._gossip_loop()

        self.assertEqual(list(engine._outgoing_queue), ["first", "second"])

    async def test_batch_is_requeued_when_propagation_fails(self):
        engine = _engine_with_queue("first", "second")

        async def fail(batch, ttl):
            del batch, ttl
            engine._running = False
            raise RuntimeError("signing failed")

        with patch.object(engine, "_repropagate", new=fail):
            await engine._gossip_loop()

        self.assertEqual(list(engine._outgoing_queue), ["first", "second"])

    async def test_batch_is_requeued_when_shutdown_cancels_propagation(self):
        engine = _engine_with_queue("first", "second")
        started = asyncio.Event()

        async def block(batch, ttl):
            del batch, ttl
            started.set()
            await asyncio.Event().wait()

        with patch.object(engine, "_repropagate", new=block):
            gossip_loop = asyncio.create_task(engine._gossip_loop())
            await started.wait()
            gossip_loop.cancel()
            await gossip_loop

        self.assertEqual(list(engine._outgoing_queue), ["first", "second"])
