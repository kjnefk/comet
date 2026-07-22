import asyncio
import unittest

from comet.cometnet.relay import CometNetRelay


class FakeSession:
    def __init__(self, response=None):
        self.closed = False
        self.response = response

    def get(self, *args, **kwargs):
        return self.response

    async def close(self):
        self.closed = True


class FakeResponse:
    def __init__(self, status, payload=None):
        self.status = status
        self.payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        return False

    async def json(self):
        return self.payload


class CometNetRelayTests(unittest.IsolatedAsyncioTestCase):
    async def test_cancelled_flush_restores_batch_in_front(self):
        relay = CometNetRelay("http://relay")
        relay._session = FakeSession()
        relay._batch = [
            {"info_hash": "old-1"},
            {"info_hash": "old-2"},
        ]
        sending = asyncio.Event()

        async def block_send(torrents):
            sending.set()
            await asyncio.Event().wait()

        relay._send_batch = block_send
        task = asyncio.create_task(relay._flush_batch())
        await sending.wait()
        relay._batch.append({"info_hash": "new"})

        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task

        self.assertEqual(
            [item["info_hash"] for item in relay._batch],
            ["old-1", "old-2", "new"],
        )

    async def test_waiting_producer_does_not_append_after_stop(self):
        relay = CometNetRelay("http://relay")
        relay._running = True
        await relay._batch_lock.acquire()
        task = asyncio.create_task(relay.relay_torrent("a" * 40, "title", 1))
        await asyncio.sleep(0)

        relay._running = False
        relay._batch_lock.release()

        self.assertFalse(await task)
        self.assertEqual(relay._batch, [])

    async def test_stop_drains_existing_flush_before_closing_session(self):
        relay = CometNetRelay("http://relay")
        relay._running = True
        session = FakeSession()
        relay._session = session
        finished = asyncio.Event()

        async def active_flush():
            try:
                await asyncio.sleep(0)
            finally:
                finished.set()

        task = asyncio.create_task(active_flush())
        relay._flush_tasks.add(task)

        await relay.stop()

        self.assertTrue(finished.is_set())
        self.assertFalse(task.cancelled())
        self.assertTrue(session.closed)

    async def test_get_pools_requires_current_standalone_endpoint(self):
        pools = {"pools": {}, "memberships": [], "subscriptions": []}
        relay = CometNetRelay("http://relay")
        relay._running = True
        relay._session = FakeSession(FakeResponse(200, pools))

        self.assertEqual(await relay.get_pools(), pools)

        relay._session = FakeSession(FakeResponse(404))
        with self.assertRaisesRegex(ValueError, "Pool not found"):
            await relay.get_pools()

    async def test_get_pools_rejects_invalid_current_shape(self):
        relay = CometNetRelay("http://relay")
        relay._running = True
        relay._session = FakeSession(FakeResponse(200, {"pools": []}))

        with self.assertRaisesRegex(ValueError, "Invalid pools response"):
            await relay.get_pools()
