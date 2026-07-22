import unittest
from unittest.mock import AsyncMock

from comet.core.schema_migrations import (
    MigrationContext,
    _add_column_if_missing,
    _column_exists,
    _drop_column_if_exists,
    _ensure_managed_table,
    _rename_column_if_missing,
)
from comet.core.schema_specs import ManagedTableSpec


class SchemaMigrationMetadataCacheTests(unittest.IsolatedAsyncioTestCase):
    async def test_column_metadata_is_loaded_once_per_table(self):
        database = AsyncMock()
        database.fetch_one.return_value = {"exists": 1}
        database.fetch_all.return_value = [{"name": "id"}, {"name": "value"}]
        context = MigrationContext(database, is_sqlite=True, is_postgres=False)

        self.assertTrue(await _column_exists(context, "items", "id"))
        self.assertTrue(await _column_exists(context, "items", "value"))
        self.assertFalse(await _column_exists(context, "items", "missing"))

        database.fetch_one.assert_awaited_once()
        database.fetch_all.assert_awaited_once_with(
            "PRAGMA table_info(items)", force_primary=True
        )

    async def test_new_managed_table_checks_existence_once(self):
        database = AsyncMock()
        database.fetch_one.return_value = None
        context = MigrationContext(database, is_sqlite=True, is_postgres=False)
        spec = ManagedTableSpec(
            table_name="items",
            create_sql="CREATE TABLE {table_name} (id INTEGER PRIMARY KEY)",
        )

        existed = await _ensure_managed_table(context, spec)

        self.assertFalse(existed)
        database.fetch_one.assert_awaited_once()
        database.execute.assert_awaited_once_with(
            "CREATE TABLE items (id INTEGER PRIMARY KEY)"
        )

    async def test_column_cache_tracks_schema_mutations(self):
        database = AsyncMock()
        context = MigrationContext(database, is_sqlite=True, is_postgres=False)
        context.table_exists_cache["items"] = True
        context.table_columns_cache["items"] = {"old_name"}

        renamed = await _rename_column_if_missing(
            context, "items", "old_name", "new_name"
        )
        await _add_column_if_missing(context, "items", "extra", "extra TEXT")
        dropped = await _drop_column_if_exists(context, "items", "new_name")

        self.assertTrue(renamed)
        self.assertTrue(dropped)
        self.assertEqual(context.table_columns_cache["items"], {"extra"})
        database.fetch_one.assert_not_awaited()
        database.fetch_all.assert_not_awaited()
        self.assertEqual(database.execute.await_count, 3)
