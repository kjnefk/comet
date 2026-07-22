import unittest
from contextlib import asynccontextmanager
from unittest.mock import patch

from comet.metadata.episode_index import EpisodeIndexService, database


class EpisodeIndexRefreshTests(unittest.IsolatedAsyncioTestCase):
    async def test_rows_and_refresh_marker_share_one_transaction(self):
        service = EpisodeIndexService(session=None)
        events = []

        @asynccontextmanager
        async def transaction():
            events.append("begin")
            try:
                yield
            except Exception:
                events.append("rollback")
                raise

        async def upsert_rows(rows):
            events.append(("rows", rows))

        async def fail_marker(series_id, refreshed_at):
            events.append(("marker", series_id, refreshed_at))
            raise RuntimeError("marker failed")

        rows = [{"season": 1, "episode": 1}]
        with (
            patch.object(database, "transaction", new=transaction),
            patch.object(service, "_upsert_series_air_dates", new=upsert_rows),
            patch.object(service, "_upsert_series_refresh", new=fail_marker),
        ):
            with self.assertRaisesRegex(RuntimeError, "marker failed"):
                await service._replace_series_index("tt123", 42.0, rows)

        self.assertEqual(
            events,
            [
                "begin",
                ("rows", rows),
                ("marker", "tt123", 42.0),
                "rollback",
            ],
        )
