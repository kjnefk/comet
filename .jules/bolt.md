## 2025-05-15 - [Redundant Database Query in Cache Freshness Check]
**Learning:** In the `stream` endpoint, `TorrentManager` already fetches all cached torrents, including their `updated_at` timestamps. However, `CacheStateManager` was performing a separate `SELECT 1` query to check for the existence of "fresh" torrents based on the same `updated_at` column.
**Action:** Track the `max_updated_at` timestamp during the initial fetch in `TorrentManager` and pass it to `CacheStateManager` to avoid the redundant database hit.

## 2026-06-30 - [Redundant Database Query when Cache is Empty]
**Learning:** If `TorrentManager` returns 0 torrents from the cache, it's logically impossible for any "fresh" torrents to exist. Calling `get_fresh_torrent_count` in this case results in a redundant `SELECT 1` database query.
**Action:** Short-circuit the `fresh_count` to 0 when `torrent_count` is 0 in `CacheStateManager.check_and_decide`.
