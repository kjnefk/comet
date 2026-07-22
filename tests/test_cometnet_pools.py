import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from comet.cometnet.pools import PoolStore


class CometNetPoolStoreTests(unittest.IsolatedAsyncioTestCase):
    async def test_load_uses_only_current_container_shapes_and_string_items(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "memberships.json").write_text(
                '["member-b",null,"member-a","member-a",3,""]'
            )
            (root / "subscriptions.json").write_text('"not-a-list"')
            (root / "pool_peers.json").write_text(
                '{"pool-a":["wss://one",null,"wss://one",""],'
                '"pool-b":"not-a-list","pool-c":[]}'
            )

            with patch(
                "comet.cometnet.pools.settings.COMETNET_TRUSTED_POOLS",
                ["configured"],
            ):
                store = PoolStore(directory)
                await store.load()

            self.assertEqual(store._memberships, {"member-a", "member-b"})
            self.assertEqual(store._subscriptions, {"configured"})
            self.assertEqual(
                store._pool_peers,
                {"pool-a": {"wss://one"}, "pool-c": set()},
            )
