## 2025-05-15 - [Redundant Database Query in Cache Freshness Check]
**Learning:** In the `stream` endpoint, `TorrentManager` already fetches all cached torrents, including their `updated_at` timestamps. However, `CacheStateManager` was performing a separate `SELECT 1` query to check for the existence of "fresh" torrents based on the same `updated_at` column.
**Action:** Track the `max_updated_at` timestamp during the initial fetch in `TorrentManager` and pass it to `CacheStateManager` to avoid the redundant database hit.
