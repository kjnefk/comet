import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from comet.cometnet.pools import MemberRole, PoolManifest, PoolMember, PoolStore


class CometNetPoolStoreTests(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    def _manifest(display_name="Original"):
        return PoolManifest(
            pool_id="pool-a",
            creator_key="creator-key",
            display_name=display_name,
            members=[
                PoolMember(
                    public_key="creator-key",
                    role=MemberRole.CREATOR,
                    added_by="creator-key",
                )
            ],
        )

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

    async def test_manifest_snapshots_require_an_explicit_successful_store(self):
        with tempfile.TemporaryDirectory() as directory:
            store = PoolStore(directory)
            await store.store_manifest(self._manifest())

            detached = store.get_manifest("pool-a")
            detached.display_name = "Mutated outside store"

            self.assertEqual(store.get_manifest("pool-a").display_name, "Original")

    async def test_failed_manifest_store_preserves_published_state_and_disk(self):
        with tempfile.TemporaryDirectory() as directory:
            store = PoolStore(directory)
            await store.store_manifest(self._manifest())
            manifest_path = Path(directory, "manifests", "pool-a.json")
            original_bytes = manifest_path.read_bytes()
            updated = store.get_manifest("pool-a")
            updated.display_name = "Updated"

            with patch(
                "comet.cometnet.pools.write_text_atomic",
                side_effect=OSError("disk unavailable"),
            ):
                with self.assertRaisesRegex(OSError, "disk unavailable"):
                    await store.store_manifest(updated)

            self.assertEqual(store.get_manifest("pool-a").display_name, "Original")
            self.assertEqual(manifest_path.read_bytes(), original_bytes)

    async def test_failed_member_update_does_not_mutate_trusted_manifest(self):
        class Identity:
            public_key_hex = "creator-key"

            async def sign_hex_async(self, payload):
                del payload
                return "signature"

        with tempfile.TemporaryDirectory() as directory:
            store = PoolStore(directory)
            await store.store_manifest(self._manifest())

            with patch(
                "comet.cometnet.pools.write_text_atomic",
                side_effect=OSError("disk unavailable"),
            ):
                with self.assertRaisesRegex(OSError, "disk unavailable"):
                    await store.add_member("pool-a", "new-key", Identity())

            manifest = store.get_manifest("pool-a")
            self.assertEqual(
                [member.public_key for member in manifest.members], ["creator-key"]
            )
            self.assertEqual(manifest.version, 1)

    async def test_failed_invite_store_is_visible_and_not_published(self):
        class Identity:
            public_key_hex = "creator-key"

            async def sign_hex_async(self, payload):
                del payload
                return "signature"

        with tempfile.TemporaryDirectory() as directory:
            store = PoolStore(directory)
            await store.store_manifest(self._manifest())

            with patch(
                "comet.cometnet.pools.write_text_atomic",
                side_effect=OSError("disk unavailable"),
            ):
                with self.assertRaisesRegex(OSError, "disk unavailable"):
                    await store.create_invite("pool-a", Identity())

            self.assertEqual(store.get_invites("pool-a"), [])

    async def test_invite_snapshots_require_an_explicit_successful_save(self):
        class Identity:
            public_key_hex = "creator-key"

            async def sign_hex_async(self, payload):
                del payload
                return "signature"

        with tempfile.TemporaryDirectory() as directory:
            store = PoolStore(directory)
            await store.store_manifest(self._manifest())
            created = await store.create_invite("pool-a", Identity(), max_uses=2)

            detached = store.get_invite("pool-a", created.invite_code)
            detached.uses = 2

            self.assertEqual(store.get_invite("pool-a", created.invite_code).uses, 0)

    async def test_membership_save_failure_propagates(self):
        with tempfile.TemporaryDirectory() as directory:
            store = PoolStore(directory)
            store._memberships.add("pool-a")

            with patch(
                "comet.cometnet.pools.write_text_atomic",
                side_effect=OSError("disk unavailable"),
            ):
                with self.assertRaisesRegex(OSError, "disk unavailable"):
                    await store._save_memberships()
