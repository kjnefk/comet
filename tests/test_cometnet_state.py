import json
import tempfile
import unittest
from pathlib import Path

from comet.cometnet.manager import CometNetService


def current_state():
    return {
        "saved_at": 1.0,
        "node_id": "self",
        "reputation": {
            "peers": {
                "peer": {
                    "reputation": 50.0,
                    "first_seen": 1.0,
                    "last_seen": 2.0,
                    "valid_contributions": 3,
                    "invalid_contributions": 1,
                    "is_blacklisted": False,
                }
            },
            "blacklist": [],
        },
        "keystore": {
            "keys": {
                "peer": {
                    "public_key_hex": "abcd",
                    "first_seen": 1.0,
                    "last_seen": 2.0,
                    "verified": True,
                }
            }
        },
        "discovery": {
            "known_peers": [
                {
                    "address": "wss://peer.example",
                    "node_id": "peer",
                    "source": "pex",
                    "last_seen": 2.0,
                }
            ]
        },
        "gossip": {
            "stats": {
                "torrents_received": 1,
                "torrents_propagated": 2,
                "torrents_repropagated": 3,
                "messages_sent": 4,
                "messages_received": 5,
                "invalid_messages": 6,
                "duplicates_ignored": 7,
                "validation_skipped_exists": 8,
                "torrents_filtered_untrusted": 9,
                "torrents_filtered_blacklisted": 10,
                "torrents_skipped_mode": 11,
            }
        },
        "integrity_hash": "hash",
    }


class Recorder:
    def __init__(self):
        self.calls = []

    def from_dict(self, data):
        self.calls.append(data)


class AsyncRecorder(Recorder):
    async def from_dict(self, data):
        self.calls.append(data)


class FailingAsyncRecorder(Recorder):
    async def from_dict(self, data):
        raise RuntimeError("address validation failed")


class CometNetStateTests(unittest.IsolatedAsyncioTestCase):
    async def test_invalid_late_section_does_not_partially_restore_state(self):
        state = current_state()
        state["gossip"]["stats"]["messages_sent"] = "4"

        with tempfile.TemporaryDirectory() as directory:
            Path(directory, CometNetService.STATE_FILE).write_text(json.dumps(state))
            service = CometNetService(keys_dir=directory)
            service.reputation = Recorder()
            service.keystore = Recorder()
            service.discovery = AsyncRecorder()
            service.gossip = Recorder()

            await service._load_state()

        self.assertEqual(service.reputation.calls, [])
        self.assertEqual(service.keystore.calls, [])
        self.assertEqual(service.discovery.calls, [])
        self.assertEqual(service.gossip.calls, [])

    async def test_address_validation_failure_does_not_restore_other_sections(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, CometNetService.STATE_FILE).write_text(
                json.dumps(current_state())
            )
            service = CometNetService(keys_dir=directory)
            service.reputation = Recorder()
            service.keystore = Recorder()
            service.discovery = FailingAsyncRecorder()
            service.gossip = Recorder()

            await service._load_state()

        self.assertEqual(service.reputation.calls, [])
        self.assertEqual(service.keystore.calls, [])
        self.assertEqual(service.gossip.calls, [])

    async def test_current_state_restores_every_section(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, CometNetService.STATE_FILE).write_text(
                json.dumps(current_state())
            )
            service = CometNetService(keys_dir=directory)
            service.reputation = Recorder()
            service.keystore = Recorder()
            service.discovery = AsyncRecorder()
            service.gossip = Recorder()

            await service._load_state()

        self.assertEqual(len(service.reputation.calls), 1)
        self.assertEqual(len(service.keystore.calls), 1)
        self.assertEqual(len(service.discovery.calls), 1)
        self.assertEqual(len(service.gossip.calls), 1)
