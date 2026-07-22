import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

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

    async def test_auxiliary_state_is_published_only_after_successful_save(self):
        with tempfile.TemporaryDirectory() as directory:
            store = PoolStore(directory)

            with patch(
                "comet.cometnet.pools.write_text_atomic",
                side_effect=OSError("disk unavailable"),
            ):
                operations = [
                    store.add_membership("pool-a"),
                    store.subscribe("pool-a"),
                    store.add_pool_peer("pool-a", "wss://peer"),
                ]
                for operation in operations:
                    with self.subTest(operation=operation):
                        with self.assertRaisesRegex(OSError, "disk unavailable"):
                            await operation

            self.assertEqual(store.get_memberships(), set())
            self.assertEqual(store.get_subscriptions(), set())
            self.assertEqual(store.get_all_pool_peers(), {})

    async def test_delete_pool_cleans_persisted_and_published_state(self):
        class Identity:
            public_key_hex = "creator-key"

            async def sign_hex_async(self, payload):
                del payload
                return "signature"

        with tempfile.TemporaryDirectory() as directory:
            store = PoolStore(directory)
            await store.store_manifest(self._manifest())
            await store.add_membership("pool-a")
            await store.subscribe("pool-a")
            await store.add_pool_peer("pool-a", "wss://peer")
            await store.create_invite("pool-a", Identity())

            self.assertTrue(await store.delete_pool("pool-a"))

            self.assertIsNone(store.get_manifest("pool-a"))
            self.assertEqual(store.get_memberships(), set())
            self.assertEqual(store.get_subscriptions(), set())
            self.assertEqual(store.get_all_pool_peers(), {})
            self.assertEqual(store.get_invites("pool-a"), [])
            self.assertFalse(Path(directory, "manifests", "pool-a.json").exists())
            self.assertFalse(Path(directory, "invites", "pool-a").exists())

    async def test_delete_failure_is_visible_without_hiding_cached_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            store = PoolStore(directory)
            await store.store_manifest(self._manifest())
            await store.add_membership("pool-a")
            await store.subscribe("pool-a")
            await store.add_pool_peer("pool-a", "wss://peer")
            manifest_path = Path(directory, "manifests", "pool-a.json")

            with patch(
                "comet.cometnet.pools.run_in_executor",
                new=AsyncMock(side_effect=OSError("unlink failed")),
            ):
                with self.assertRaisesRegex(OSError, "unlink failed"):
                    await store.delete_pool("pool-a")

            self.assertIsNotNone(store.get_manifest("pool-a"))
            self.assertTrue(manifest_path.exists())
            self.assertEqual(store.get_memberships(), set())
            self.assertEqual(store.get_subscriptions(), set())
            self.assertEqual(store.get_all_pool_peers(), {})

    async def test_concurrent_join_requests_cannot_overuse_invite(self):
        class Identity:
            public_key_hex = "creator-key"

            async def sign_hex_async(self, payload):
                del payload
                return "signature"

        with tempfile.TemporaryDirectory() as directory:
            store = PoolStore(directory)
            await store.store_manifest(self._manifest())
            invite = await store.create_invite("pool-a", Identity(), max_uses=1)

            results = await asyncio.gather(
                store.accept_invite_member(
                    "pool-a",
                    invite.invite_code,
                    "member-a",
                    signing_identity=Identity(),
                ),
                store.accept_invite_member(
                    "pool-a",
                    invite.invite_code,
                    "member-b",
                    signing_identity=Identity(),
                ),
            )

            self.assertEqual(sum(result is not None for result in results), 1)
            self.assertEqual(store.get_invite("pool-a", invite.invite_code).uses, 1)
            member_keys = {
                member.public_key for member in store.get_manifest("pool-a").members
            }
            self.assertEqual(len(member_keys & {"member-a", "member-b"}), 1)

    async def test_invite_limits_reject_boolean_zero_and_non_finite_values(self):
        class Identity:
            public_key_hex = "creator-key"

            async def sign_hex_async(self, payload):
                del payload
                return "signature"

        with tempfile.TemporaryDirectory() as directory:
            store = PoolStore(directory)
            await store.store_manifest(self._manifest())

            for arguments in [
                {"max_uses": True},
                {"max_uses": 0},
                {"expires_in": True},
                {"expires_in": 0},
            ]:
                with self.subTest(arguments=arguments):
                    with self.assertRaises(ValueError):
                        await store.create_invite("pool-a", Identity(), **arguments)
