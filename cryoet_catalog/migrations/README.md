# `cryoet_catalog` migrations

Schema evolution for the catalog SQLite DB is managed by [Alembic][alembic].
The ORM in `cryoet_catalog/orm.py` is the source of truth; revisions in
`versions/` describe the deltas between historical snapshots of that ORM.

`Base.metadata.create_all(engine)` is **not** the lifecycle entry point any
more — `cryoet_catalog.db.init_schema(engine)` runs Alembic instead. The
only place `create_all` survives is the DDL-drift sanity check in
`tests/cryoet_catalog/test_alembic.py`.

[alembic]: https://alembic.sqlalchemy.org/

## Pixi tasks

```bash
# Apply every pending revision to head (against $CATALOG_DB_URL or the default).
pixi run -e catalog migrate

# Generate a new autogenerate revision after changing the ORM.
# The message is passed after `--`:
pixi run -e catalog migrate-revision -- "description of change"
```

Both tasks resolve to `alembic -c cryoet_catalog/migrations/alembic.ini …`.
The DB URL is read from `CATALOG_DB_URL` in the environment, falling back
to `cryoet_catalog.db.DEFAULT_DB_URL` (`sqlite:///cryoet_catalog.db`).

## Workflow

1. Edit `cryoet_catalog/orm.py` (and the corresponding Pydantic model in
   `cryoet_schema/schema.py` — the drift test will yell otherwise).
2. Run `pixi run -e catalog migrate-revision -- "what changed"`.
3. **Open the generated revision under `versions/` and review every line.**
   Autogenerate is good but not perfect — see "SQLite caveats" below.
4. Apply with `pixi run -e catalog migrate`.
5. Update `tests/cryoet_catalog/test_orm_drift.py` and any tests covering
   the new column/table.

## Revision IDs

- `0001_initial.py` has its revision id pinned to the string `"0001"` because
  `init_schema` references it by name. **Do not rename it.**
- **Every other revision uses Alembic's default 12-char hex hash.** Just
  run `pixi run -e catalog migrate-revision -- "what changed"`.

## SQLite caveats

- **`render_as_batch=True` is mandatory** for `ALTER TABLE`. SQLite's
  in-place ALTER TABLE is far too narrow (no DROP COLUMN, no ALTER COLUMN
  type), so Alembic's batch mode rebuilds the whole table. That rebuild
  drops any **manual indexes, triggers, and PRAGMAs** not represented in
  the ORM. If you've added one outside Alembic, it will not survive a
  migration.
- **Autogenerate misses some changes.** It does NOT detect:
  - CHECK constraint changes,
  - server-side default changes (sometimes),
  - certain composite / functional index changes,
  - changes to type metadata that share an SA backing (e.g. `String(20)` →
    `String(40)` on SQLite where everything is TEXT — `compare_type=True`
    helps for cross-type but not always for length).
- **Review every revision diff before committing.** The `versions/` files
  are normal Python; treat them as code.
- **Migration tests assert row preservation.** `tests/cryoet_catalog/test_alembic.py`
  seeds rows in each table, runs `upgrade head`, and asserts per-table
  counts are unchanged. That is the safety net against silent
  batch-rebuild data loss.
