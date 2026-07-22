import math
from typing import Any


GOSSIP_STAT_KEYS = {
    "torrents_received",
    "torrents_propagated",
    "torrents_repropagated",
    "messages_sent",
    "messages_received",
    "invalid_messages",
    "duplicates_ignored",
    "validation_skipped_exists",
    "torrents_filtered_untrusted",
    "torrents_filtered_blacklisted",
    "torrents_skipped_mode",
}


def _object(value: Any, name: str) -> dict:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be an object")
    return value


def _list(value: Any, name: str) -> list:
    if not isinstance(value, list):
        raise ValueError(f"{name} must be a list")
    return value


def _string(value: Any, name: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or (not allow_empty and not value):
        raise ValueError(f"{name} must be a string")
    return value


def _number(value: Any, name: str) -> int | float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
    ):
        raise ValueError(f"{name} must be a finite number")
    return value


def _integer(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    return value


def validate_state(value: Any) -> dict:
    """Validate the complete schema emitted by the current state writer."""
    state = _object(value, "state")
    _number(state["saved_at"], "saved_at")
    if state["node_id"] is not None:
        _string(state["node_id"], "node_id")
    if "integrity_hash" in state:
        _string(state["integrity_hash"], "integrity_hash")

    reputation = _object(state["reputation"], "reputation")
    peers = _object(reputation["peers"], "reputation.peers")
    for node_id, peer_value in peers.items():
        _string(node_id, "reputation peer ID")
        peer = _object(peer_value, f"reputation.peers.{node_id}")
        _number(peer["reputation"], f"reputation.peers.{node_id}.reputation")
        _number(peer["first_seen"], f"reputation.peers.{node_id}.first_seen")
        _number(peer["last_seen"], f"reputation.peers.{node_id}.last_seen")
        _integer(
            peer["valid_contributions"],
            f"reputation.peers.{node_id}.valid_contributions",
        )
        _integer(
            peer["invalid_contributions"],
            f"reputation.peers.{node_id}.invalid_contributions",
        )
        if not isinstance(peer["is_blacklisted"], bool):
            raise ValueError(
                f"reputation.peers.{node_id}.is_blacklisted must be a boolean"
            )
    for node_id in _list(reputation["blacklist"], "reputation.blacklist"):
        _string(node_id, "blacklisted peer ID")

    keystore = _object(state["keystore"], "keystore")
    keys = _object(keystore["keys"], "keystore.keys")
    for node_id, key_value in keys.items():
        _string(node_id, "keystore peer ID")
        key = _object(key_value, f"keystore.keys.{node_id}")
        _string(key["public_key_hex"], f"keystore.keys.{node_id}.public_key_hex")
        _number(key["first_seen"], f"keystore.keys.{node_id}.first_seen")
        _number(key["last_seen"], f"keystore.keys.{node_id}.last_seen")
        if not isinstance(key["verified"], bool):
            raise ValueError(f"keystore.keys.{node_id}.verified must be a boolean")

    discovery = _object(state["discovery"], "discovery")
    for index, peer_value in enumerate(
        _list(discovery["known_peers"], "discovery.known_peers")
    ):
        peer = _object(peer_value, f"discovery.known_peers[{index}]")
        _string(peer["address"], f"discovery.known_peers[{index}].address")
        _string(
            peer["node_id"],
            f"discovery.known_peers[{index}].node_id",
            allow_empty=True,
        )
        _string(peer["source"], f"discovery.known_peers[{index}].source")
        _number(peer["last_seen"], f"discovery.known_peers[{index}].last_seen")

    gossip = _object(state["gossip"], "gossip")
    stats = _object(gossip["stats"], "gossip.stats")
    if stats.keys() != GOSSIP_STAT_KEYS:
        raise ValueError("gossip.stats does not match the current schema")
    for key, stat_value in stats.items():
        _integer(stat_value, f"gossip.stats.{key}")

    return state
