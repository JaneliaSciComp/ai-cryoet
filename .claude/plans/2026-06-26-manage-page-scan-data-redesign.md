# Manage page redesign — scan data model rebuilt from scratch

**Date:** 2026-06-26
**Branch:** `surface-warnings-and-errors-from-scans` (current)
**Status:** Draft for review (no code written yet)
**Wireframe:** `/workspace/manage-redesign.html`

## 1. Context

The current Manage page (`frontend/src/routes/manage.index.tsx`) shows five
accordion sections built around a single scan run: "Samples with warnings",
"Scan-level issues", and "Samples upserted / skipped / failed". The user finds
these not useful. The wireframe reorganizes the page around three priorities:

1. **Outstanding warnings & errors** — a *current-state* table of which
   `sample.toml` / `acquisition.toml` files still have warnings/errors, with
   **severity** (error vs warning), the **list of issues**, a **first-seen**
   date, and a **still-present-as-of** date — shown next to the scan cadence so
   a researcher knows when a fix they just made will appear. A companion
   **"Recently resolved (last 24h)"** view (decision §9.3) closes the loop: it
   shows issues the most recent scans *cleared*, so a fix gets positive
   confirmation rather than just disappearing.
2. **Freshness & provenance** — per sample and per acquisition: when it was
   *last scanned* vs *last actually updated*, the **thumbnail source file**, and
   when the **thumbnail was generated** (including the "no preview source" and
   "never generated" cases). **Surfaced on the sample/acquisition detail pages,
   not as a Manage-page table** (decision §1.6): this data is inherently per-
   entity, so it belongs with the entity, not in a cross-entity triage table.
3. **Scan logs (developer view)** — durable, persisted logs from every scan that
   has run. **Scope trimmed (see §1.5):** logs are persisted to the DB and shown
   in a per-run expandable panel on the run-detail view; the polished standalone
   "Scan logs" page and cross-run log search are deferred from the first cut.

The user explicitly authorized **designing the scan data model, DB, and API
from scratch** — no need to preserve the existing scan model.

### 1.1 Why the existing model can't serve this (gap analysis)

Current scan tables: `scans`, `scan_warnings`, `scan_run_warnings`,
`scan_samples`, `scan_state` (all in `src/catalog/orm.py:419-516`).

| Need (wireframe) | Today | Gap |
|---|---|---|
| Severity error vs warning | `ScanWarning` has only `category/location/message` (`assembler.py:65-69`); hard errors live separately as bare strings in `scan_samples.detail` | No unified severity; errors and warnings are different shapes in different tables |
| Which `.toml` file | `location` is a *schema path* (`acquisitions.{id}.tomogram[..]`), not a file path | File must be inferred; no `file_path` / `file_kind` recorded |
| Acquisition attribution | only embedded in the `location` string | No structured `acquisition_id` on warnings |
| First-seen date | persistence is **delete-then-insert per sample** (`persistence.py:366-382`), stamping `detected_at = now` every run | No memory of when an issue first appeared |
| Still-present-as-of | warnings keyed to the run that *processed* the sample; a **skipped** sample keeps its old `scan_run_id`, so `/scans/latest/warnings` (filters `scan_run_id == latest`) **drops still-outstanding warnings on skipped samples** | "Currently outstanding" is not reliably queryable |
| Per-acq / per-sample freshness | only per-*file* `scan_state(mtime,last_scanned)`; acquisition `date_collected` is collection date, not freshness | No per-sample / per-acquisition last-scanned / last-changed rollup |
| Thumbnail provenance | sample-level `thumbnail_path` only (`SampleORM`, `persistence.py:166`); generated per acquisition (`thumbnails.py`) | Source file, generated-at timestamp, per-acq status all unrecorded |
| Full scan logs | loguru → stderr only (`cli.py:85-101`); k8s captures pod logs | Logs are never persisted; cannot retrieve a past run's output |

**The core conceptual problem:** the current model is *per-scan-run* ("what did
this run find?"). Priorities 1 and 2 need a *current, deduplicated, entity-keyed*
view ("what is broken right now, and since when; how fresh is each entity").
Those are different queries, and the skipped-sample behavior makes "latest run's
warnings ≠ currently outstanding warnings".

### 1.2 Architectural decision: split *event history* from *current state*

The new model separates two concerns that the old one conflated:

- **Run history (append-only):** one row per scan run + its full log lines +
  its per-sample outcomes. Serves Priority 3 and audit.
- **Current materialized state (entity-keyed):** the live set of outstanding
  issues (with first/last-seen + resolution), and the freshness + thumbnail
  provenance per sample & acquisition. Serves Priorities 1 & 2.

This is the standard "event log + materialized projection" split. The current
state is **reconcilable** on every scan: each sample's fresh issue set is diffed
against its stored outstanding issues, so first-seen survives across runs and
resolution is detected when a re-evaluated sample stops emitting an issue.

### 1.3 Reconstructability (enables a clean cutover)

Every scan fact is derivable from the filesystem by re-scanning. So the
migration can be **destructive** (drop old scan tables, create new ones, no data
backfill) and the **first post-migration scan rebuilds everything** — provided
that scan is a full re-evaluation. We achieve that by running `scan --force` once
at cutover while **keeping `scan_state`** (decision §9.2 / §6), rather than
dropping the ledger.

### 1.4 Constraints confirmed from the codebase

- **Backend:** FastAPI + SQLAlchemy 2.0, SQLite (dev) / Postgres (prod). ORM is
  hand-written in `src/catalog/orm.py`. **Alembic is NOT in use yet** (decision
  §9.9): the runtime still bootstraps the schema with
  `Base.metadata.create_all(engine)` in `init_schema` (`db.py:37`), and there is
  no `migrations/versions/` history (the Alembic scaffold exists but is dormant;
  `test_init_schema.py:35-36` pins "no `alembic_version` table"). Schema changes
  therefore ship as ORM edits plus an **idempotent in-`init_schema` migration step**
  (drop legacy tables, then `create_all`), not as an Alembic revision (§4.1, §6).
- **Drift test** (`tests/catalog/test_orm_drift.py`) pins only the *content*
  tables (Sample, Acquisition, …) to the Pydantic schema. **Scan tables are not
  in `MAPPING`**, so the new scan model needs **no `schema/schema.py` change and
  no drift-test change**.
- **Scanner:** `scanner.py:scan_root()`, CLI `python -m catalog scan <root>`,
  run **hourly** by a k8s CronJob (`deploy/k8s/base/scanner.yaml`,
  `schedule: "0 * * * *"`, `concurrencyPolicy: Forbid`). Logging via **loguru**
  to stderr (`cli.py:_configure_logging`).
- **k8s log access (decided):** there is **no log-aggregation backend** in
  `deploy/` (no Loki/Fluent/ES/CloudWatch). CronJob logs are only reachable via
  `kubectl logs` while the Job/pod is retained. We bumped
  `successful/failedJobsHistoryLimit` from 3 → **48** (≈48h of recent runs) for
  ad-hoc `kubectl` access. Anything older than that window is **only** available
  if the scanner persists logs itself — which motivates §1.5.
- **Frontend:** TanStack Start + React 19 + MUI 6 + **material-react-table**.
  Routes `/manage/`, `/manage/all-scans`, `/manage/$scanId`; query hooks in
  `frontend/src/utils/queryOptions.ts`; types in `frontend/src/types.ts`.

### 1.5 Priority 3 scope: persist logs, defer the polished log UI

Old CronJob logs are practically unavailable today: no aggregation backend, and
even with history bumped to 48 (§1.4) only ~48h is reachable, `kubectl`-only,
unsearchable. Durable history therefore requires the scanner to persist logs to
the DB regardless. **But** the audience for old logs is one person (the
maintainer) looking occasionally, so a full log-analytics UI is not worth it for
the first cut. Decision:

- **Keep:** persist logs to the DB (`scan_log_lines`), plus `scan_runs` and
  `scan_sample_outcomes`. Surface them via a **per-run expandable log panel** on
  the run-detail view (`/manage/scans/$scanId`), which falls out of the data
  model for free.
- **Defer:** the standalone `/manage/logs` page and the cross-run
  `GET /manage/logs/search` endpoint. Both are additive later if cross-run search
  becomes a real need.

### 1.6 Priority 2 placement: detail pages, not a Manage table

Freshness + thumbnail provenance is **inherently per-entity, 1:1, current-state**
data (one current status per sample, one per acquisition). It reads naturally on
the **sample/acquisition detail pages**, not in a cross-entity Manage table — you
look at it when you're already on the entity. So:

- The data shape is unchanged (still a per-entity current-state projection), but
  it is **split per entity type** and surfaced through the existing detail
  endpoints rather than a `/manage/freshness` table (§3.2, §4.5, §4.6).
- The Manage page's Priority 2 section / `FreshnessTable` is **dropped**. Manage
  becomes Priority 1 (issues) + the status/cadence card. An optional small
  staleness rollup on Manage (e.g. "N samples not scanned in >7 days") is left as
  a later additive nicety, not part of this cut.

**Storage decision — 1:1 side tables, not columns on the content tables.** The
content tables (`SampleORM`/`AcquisitionORM`) are pinned 1:1 to the Pydantic
*source* schema by the drift test; freshness/provenance is catalog-operational
metadata, not source data. Rather than grow the `db_only_columns` carve-out
(esp. on `AcquisitionORM`, which has none today), keep the content tables a clean
schema mirror and store scan status in two 1:1 side tables joined into the detail
endpoints. (`SampleORM` already carries `deleted_at`/`disk_size_bytes`/
`thumbnail_path` as carve-outs; `thumbnail_path` stays there, but the *new* fields
go to the side tables.)

Contrast: **Priority 1 stays on Manage** — it's an aggregated triage worklist
("which of my files are broken right now"), not a per-entity readout. The same
`issues` table can *also* feed a per-sample warnings block on the detail page
(there is already a `/samples/{id}/warnings` endpoint), so it's one data source,
two views.

## 2. Goals

1. A Manage page = Priority 1 (issues) + status/cadence card; Priority 2 lives on
   the sample/acquisition detail pages; Priority 3 = persisted logs (trimmed UI).
2. **Priority 1** answerable directly: "list every sample/acquisition file that
   currently has an outstanding warning or error, with severity, messages,
   first-seen, and still-present-as-of" — correct even when the owning sample
   was skipped in the latest scan.
3. **Priority 2** answerable directly *per entity*: for a given sample/acquisition,
   last-scanned vs last-changed + outcome, plus thumbnail source file /
   generated-at / status — returned by the entity's own detail endpoint.
4. **Priority 3**: full persisted logs per scan run (per-run panel; cross-run
   search deferred — §1.5).
5. Clean cutover: an idempotent `init_schema` drop/`create_all` step (no Alembic),
   no data backfill, one `scan --force` rebuilds.
6. No regression to the catalog content model or the drift test.

### Non-goals

- No change to the Pydantic content schema or content tables.
- No UI-triggered rescans (rescans stay CLI/cron, per prior decisions).
- No per-acquisition *change detection* (gating stays whole-sample; per-acq
  freshness is derived from the parent sample's outcome — see §4.5).
- No log streaming/tailing of in-progress scans (logs are persisted at run end).

## 3. New scan data model

All tables live in `src/catalog/orm.py`. Enums use `SAEnum`. Timestamps are
float epoch seconds (matching existing convention).

### 3.1 Run history

**`scan_runs`** (replaces `scans`)
| column | type | notes |
|---|---|---|
| `scan_run_id` | String PK | uuid hex |
| `started_at` | Float | |
| `ended_at` | Float? | null while running |
| `status` | Enum(`running`/`completed`/`failed`) | |
| `root` | String | |
| `trigger` | Enum(`cron`/`cli`/`manual`)? | best-effort from CLI flag/env |
| `n_upserted` / `n_skipped` / `n_failed` | Integer? | |
| `n_new_issues` / `n_resolved_issues` | Integer? | issues opened/closed this run |
| `n_warning_active` / `n_error_active` | Integer? | outstanding totals snapshot at run end |

**`scan_log_lines`** (NEW — Priority 3)
| column | type | notes |
|---|---|---|
| `id` | Integer PK autoinc | |
| `scan_run_id` | String FK→scan_runs, indexed | |
| `seq` | Integer | monotonic order within run |
| `ts` | Float | |
| `level` | Enum(`DEBUG`/`INFO`/`WARNING`/`ERROR`), indexed | |
| `sample_id` | String?, indexed | bound context when available |
| `message` | String | |

**`scan_sample_outcomes`** (replaces `scan_samples`)
| column | type | notes |
|---|---|---|
| `id` | Integer PK autoinc | |
| `scan_run_id` | String FK→scan_runs, indexed | |
| `sample_id` | String, indexed | no FK (failed sample may not exist) |
| `outcome` | Enum(`upserted`/`skipped`/`failed`) | |
| `detail` | String? | error message for failures |
| | | Unique(`scan_run_id`,`sample_id`) |

### 3.2 Current state

**`issues`** (replaces `scan_warnings` + `scan_run_warnings`; the heart of P1)
| column | type | notes |
|---|---|---|
| `id` | Integer PK autoinc | |
| `fingerprint` | String, **unique**, indexed | stable identity (see §4.4) |
| `severity` | Enum(`error`/`warning`), indexed | |
| `scope` | Enum(`sample`/`acquisition`/`run`) | |
| `sample_id` | String?, indexed | null for run-scope |
| `acquisition_id` | String? | set for acquisition-scope |
| `file_kind` | Enum(`sample_toml`/`acquisition_toml`/`md_run_toml`/`mdoc`/`mrc_header`/`zarr_attrs`/`frames`/`filesystem`/`other`) | |
| `file_path` | String? | actual offending file when known |
| `location` | String | schema path / sub-location within file |
| `category` | String | existing categories + error categories |
| `message` | String | latest message text |
| `first_seen_at` | Float | first run that detected it |
| `first_seen_run_id` | String | |
| `last_seen_at` | Float | last run that re-evaluated owner & re-emitted |
| `last_seen_run_id` | String | |
| `resolved_at` | Float? | **NULL = outstanding** |
| `resolved_run_id` | String? | |
| | | index on (`resolved_at`,`severity`) for the outstanding query |

**Priority 2 freshness/provenance — two 1:1 side tables** (decision §1.6). Kept
as side tables rather than columns on the content tables so the content tables
stay a clean Pydantic-schema mirror (no `db_only_columns` growth, drift test
untouched). Joined into the existing `/samples/{id}` and `/acquisitions/{…}`
endpoints; not surfaced on Manage.

**`sample_scan_status`** (1:1 with `samples`)
| column | type | notes |
|---|---|---|
| `sample_id` | String **PK**, FK→samples | |
| `last_scanned_at` | Float | last run that evaluated it (upsert OR skip) |
| `last_changed_at` | Float? | last run that **upserted** (content changed) |
| `last_outcome` | Enum(`upserted`/`skipped`/`failed`) | |
| `last_scan_run_id` | String | |

(The representative sample thumbnail already lives on `SampleORM.thumbnail_path`;
no new thumbnail columns needed here. Source/generated-at provenance is per
acquisition — below.)

**`acquisition_scan_status`** (1:1 with `acquisitions`)
| column | type | notes |
|---|---|---|
| `sample_id` | String | PK part, FK→samples |
| `acquisition_id` | String | PK part |
| `last_scanned_at` | Float | |
| `last_changed_at` | Float? | |
| `last_outcome` | Enum(`upserted`/`skipped`/`failed`) | |
| `last_scan_run_id` | String | |
| `thumbnail_path` | String? | the acquisition's preview |
| `thumbnail_source_kind` | Enum(`zarr`/`st`/`frames`/`none`)? | matches the renderer's real source vocabulary (`zarr_path`/`st_path`/`frames_dir`), **not** `mrc_stack`/`raw_frames` (§4.5) |
| `thumbnail_source_path` | String? | the file the preview was actually rendered from (post-fallback) |
| `thumbnail_generated_at` | Float? | |
| `thumbnail_status` | Enum(`ok`/`missing_source`/`render_failed`)? | drives "— no preview source —" / "never" |
| | | PK(`sample_id`,`acquisition_id`) |

Both are keyed to survive the acquisition keyed-upsert (`persistence.py:201-346`
upserts on the same PK + prunes orphans) — the status row is upserted on its own
PK and is **not** deleted with content rewrites.

**Orphan handling on genuine deletion (decision §9.10).** Samples are
soft-deleted (`persistence.py:417` sets `deleted_at`, no row DELETE) so
`sample_scan_status` FKs stay valid. **Acquisitions are hard-deleted** by
`_delete_stale_children(AcquisitionORM, …)` (`persistence.py:307`), which would
otherwise leave orphaned `acquisition_scan_status` rows and zombie
acquisition-scope `issues` (`resolved_at IS NULL` forever). We do **not** rely on
SQLite FK cascade (`PRAGMA foreign_keys` is off by default and unset here).
Instead, `upsert_sample_record` adds an **explicit prune** mirroring
`_delete_stale_children`: any `acquisition_scan_status` row and any
acquisition-scope `issue` whose `(sample_id, acquisition_id)` is no longer in
`keep_acq_pks` is deleted (issues are resolved-then-deleted, or simply deleted —
see §4.4). This keeps the side tables and the issue table consistent with the
content tables without FK enforcement.

### 3.3 Kept / dropped

- **Kept:** `scan_state` (per-file mtime ledger — pure change-detection
  mechanics; unrelated to the user-facing rollups). `catalog_meta`.
  `SampleORM.thumbnail_path` (representative sample thumbnail).
- **Dropped:** `scans`, `scan_warnings`, `scan_run_warnings`, `scan_samples`.

### 3.4 Cadence (status card)

Not a table. Add config `SCAN_CADENCE_CRON` (default `"0 * * * *"`, mirroring
`scanner.yaml`) read by the API and returned from `/manage/summary`. The
frontend computes the next run from the cron expression using a **cron-parse
dependency** (decision §9.1; e.g. `cron-parser` for the next-fire time +
`cronstrue` for a human-readable cadence string). Because the CronJob fires in
the **cluster timezone** while the browser is in the user's timezone, the API
also returns the cron's timezone (config `SCAN_CADENCE_TZ`, default the cluster
TZ) so the frontend computes "next ≈ HH:MM" correctly and renders it in the
user's local time. Documented as config-sourced, not introspected from k8s.

## 4. Backend implementation

### 4.1 ORM + migration (foundation)

1. Edit `src/catalog/orm.py`: remove the four dropped classes; add
   `ScanRunORM`, `ScanLogLineORM`, `ScanSampleOutcomeORM`, `IssueORM`,
   `SampleScanStatusORM`, `AcquisitionScanStatusORM` per §3.
2. **No Alembic revision (decision §9.9).** The runtime bootstraps via
   `Base.metadata.create_all` (`db.py:37`), so a revision would never run and
   `create_all` alone would create the new tables but **never drop the old ones**.
   Instead, add an **idempotent migration step inside `init_schema`** that runs
   *before* `create_all`: `DROP TABLE IF EXISTS scans, scan_warnings,
   scan_run_warnings, scan_samples` (guard on dialect for the multi-table form;
   one `DROP TABLE IF EXISTS` per table is the portable shape). **Keep
   `scan_state`** (decision §9.2 / §6 — the cutover uses `scan --force`, not a
   `scan_state` drop). Then `create_all` materializes the six new tables. Update
   the stale `db.py` docstring (it claims Alembic is wired up) and adjust
   `test_init_schema.py` only if it asserts on the dropped tables.
3. Confirm `tests/catalog/test_orm_drift.py` is untouched: scan tables and the
   two `*_scan_status` side tables are **not** in `MAPPING`, and no new columns
   land on `SampleORM`/`AcquisitionORM` (the `scan_status` blocks are surfaced via
   JOINs in the read endpoints — §4.6 — not as ORM columns/relationships on the
   content classes), so the drift boundary is preserved. Add a one-line comment
   there noting these tables are intentionally excluded.

### 4.2 Assembler: structured issues with severity + file attribution

Replace the `ScanWarning` dataclass with a richer `ScanIssue`
(`assembler.py:65-69`), keeping `category/location/message` and adding
`severity`, `scope`, `acquisition_id`, `file_kind`, `file_path`:

```python
@dataclass
class ScanIssue:
    severity: str          # "error" | "warning"
    scope: str             # "sample" | "acquisition" | "run"
    category: str
    location: str          # schema path within the file
    message: str
    sample_id: str | None = None
    acquisition_id: str | None = None
    file_kind: str = "other"
    file_path: str | None = None
```

- Migrate every existing `ScanWarning(...)` emit site to `ScanIssue(severity="warning", ...)`.
- Convert `AssemblyResult.errors: list[str]` into `severity="error"` issues. The
  assembler holds the sample dir and per-acquisition `path`, so it can attach
  `file_path`/`file_kind`. The catch-all assembly failure becomes
  `category="assembly_failed", severity="error", file_kind="sample_toml"`.
- Fold `FieldConflict` into issues (it already carries `severity`).
- Add a `_resolve_file(location, sample_loc) -> (file_kind, file_path, acquisition_id)`
  helper using the known prefixes (`assembler.py:93-146`): `<root>`→`sample_toml`;
  `acquisitions.{id}…`→that acq's `acquisition.toml` + `acquisition_id`;
  `md_source.{id}`/`md_run`→`md_run.toml`; parser categories (`unparseable_mdoc`,
  `unparseable_mrc_header`, `unparseable_zarr_attrs`) carry their concrete file
  path from the parser. Run-level scanner warnings → `file_kind="filesystem"`,
  `scope="run"`.

### 4.3 Log capture sink (Priority 3)

In `scan_root` (`scanner.py`), install a loguru sink that buffers records **in
memory** and persists them in a **single bulk insert at run end** (decision
§9.11). It does **not** write to the DB mid-scan — the scanner is a single SQLite
writer (`scanner.py:8-11`), and a mid-scan flush (especially loguru's
`enqueue=True` background thread, which is not safe to share a SQLAlchemy
`Session` with) would contend for the SQLite write lock against the in-progress
per-sample `with session.begin()` transaction (which can be held for seconds
across a thumbnail render). Design:

- The sink is **synchronous** (`enqueue=False`) and only appends each record to an
  in-process list, assigning a monotonic `seq` from a simple counter (so order is
  deterministic and independent of `ts` granularity).
- Wrap the per-sample loop body — **including** the `"[{idx}/{total}] {sample_id}"`
  line (`scanner.py:103`) — in `logger.contextualize(sample_id=...)` so each
  buffered record carries `sample_id` via `record["extra"]`. Run-level lines
  (`scanner.py:91,187`) simply have `sample_id=None`.
- Persist the buffer in **one bulk insert inside `finish_scan`** (the completed
  path) and in the `except`/failed path (status `failed`), so a crashed scan still
  records the partial log it accumulated before dying. Worst case (hard process
  kill) loses the in-memory buffer — acceptable, since k8s pod logs still cover
  that ~48h window (§1.4).
- **Engine hardening (decision §9.11):** switch the SQLite engine to
  `journal_mode=WAL` + a `busy_timeout` (via a connect event) regardless. This is
  cheap insurance for the existing per-sample transactions too, independent of the
  log feature.
- Min level configurable (`SCAN_LOG_DB_LEVEL`, default `INFO`) to bound volume;
  DEBUG opt-in.
- **Retention:** at end of scan, prune `scan_log_lines` for runs older than the
  most recent `N` (config `SCAN_LOG_RETENTION_RUNS`, **default 720 ≈ 30 days** at
  the hourly cadence) — keep the `scan_runs` rows (so the run history stays
  complete and cheap), drop only their log lines. Log the prune count.
  - **Sizing rationale (start at 30 days):** at INFO level a run emits roughly
    1–3 lines per sample plus a handful of run-level lines — on the order of a
    few hundred lines for a catalog this size. 720 runs × ~300 lines ≈ ~200k rows
    at ~200 B/row ≈ **~40 MB** in the shared SQLite DB — negligible. 30 days
    comfortably covers the gap beyond k8s's 48h window for occasional lookback,
    with headroom to raise to 90 days (`N=2160`, ~120 MB) or lower it if the DB
    file size ever matters. The `scan_runs`/`scan_sample_outcomes` rows are tiny,
    so they are **not** pruned — only the verbose `scan_log_lines` are.

### 4.4 Issue reconciliation (Priority 1 core)

New `persistence.reconcile_sample_issues(session, run_id, sample_id, fresh_issues, now)`:

- **Single run-level `now` (decision §9.6).** `now` is computed **once** per run
  (= `scan_runs.started_at`) and threaded through reconciliation **and**
  `upsert_sample_record` (which today computes its own `time.time()` —
  `persistence.py:158`) and the §4.5 status upserts, so all `first_seen_at` /
  `last_seen_at` / `resolved_at` / `last_scanned_at` values for one run share a
  single timestamp. This keeps the "resolved in last 24h" grouping (§4.4 below /
  §9.3) consistent and avoids per-issue timestamp skew within a run.
- **Fingerprint** = `sha1(scope | sample_id | acquisition_id | file_kind | location | category)`.
  Deliberately **excludes `message`** so wording/count changes update the message
  text but preserve `first_seen_at` (the identity is "this file has this category
  of problem at this location"). Documented trade-off.
- Load this sample's outstanding issues (`sample_id=?, resolved_at IS NULL`).
- For each fresh issue: upsert by fingerprint — existing → set
  `last_seen_at/last_seen_run_id`, refresh `message/severity`; missing → insert
  with `first_seen_*` = `last_seen_*` = now.
- Outstanding issues **absent** from the fresh set → `resolved_at=now,
  resolved_run_id=run_id`.
- **Skipped sample:** do nothing (issues persist; `last_seen` unchanged).
- **Failed sample:** upsert the `assembly_failed` error issue; do **not** resolve
  the sample's other outstanding issues (we couldn't re-evaluate them).
- **Run-scope issues** (`scope="run"`): reconcile against the whole run once
  (fresh run-level set replaces prior outstanding run-scope issues). **Only when
  the run finishes with status `completed` (decision §9.6).** A run that crashed
  or was killed (`concurrencyPolicy: Forbid`) may not have finished discovery, so
  "replace all run-scope issues" would wrongly resolve real issues that simply
  weren't re-emitted. On a non-`completed` run, run-scope issues are left
  untouched. (Per-sample reconciliation is naturally safe under a partial crash:
  reached samples get correct state, un-reached ones keep their prior issues.)

**"Still present as of" semantics (decision §9.7).** An unresolved issue whose
owner was *actually re-evaluated* in the latest run is present as of that scan, so
the UI shows the global latest-scan timestamp. But a **skipped** sample's issues
were **not** re-checked this run (its `last_seen_at` deliberately stays stale —
see the skipped-sample rule above), so claiming "present as of latest scan" would
overstate currency. The endpoint therefore returns, per issue group, both the
global latest-scan timestamp **and** the group's `last_seen_at` plus whether
`last_seen_run_id == latest_run_id`; the UI shows the global timestamp only when
the owner was re-evaluated this run, and otherwise shows the per-issue
`last_seen_at` (with a tooltip explaining the owner was skipped). This is the
honest reading and avoids re-introducing the skipped-sample staleness bug the
redesign set out to fix.

The `resolved_at`/`resolved_run_id` stamped here are also what powers the
**"Recently resolved (last 24h)"** view (decision §9.3) — no extra write path; the
view is just a `resolved_at >= now - 24h` query over the same `issues` table.

### 4.5 Freshness + thumbnail provenance (Priority 2)

In the scanner per-sample path, after the outcome is known, upsert the two
status side tables (§3.2) by PK:

- `sample_scan_status[sample_id]`: `last_scanned_at=now` always;
  `last_changed_at=now` only on `upserted`; `last_outcome`, `last_scan_run_id`.
  Done for upserted **and** skipped samples (skip still updates `last_scanned_at`).
  **Note the skip path writes:** today the gating branch (`scanner.py:233-260`)
  opens a transaction only when a thumbnail is missing; the status upsert adds a
  small explicit write there so a skipped sample still records `last_scanned_at`.
- `acquisition_scan_status[(sample_id, acquisition_id)]` per acquisition: same
  freshness fields. **Per-acquisition freshness derives from the parent sample's
  outcome** (gating is whole-sample; per-acq change detection is out of scope —
  see §9.6) — documented.
- Thumbnail provenance (acquisition table) — **full refactor (decision §9.5).**
  The renderer chooses its source *internally with fallback* (`zarr_path →
  st_path → frames_dir`; `imaging/_tilt_series.py:116-122`), so the only way to
  record the source that **actually** rendered (not the pre-call guess at
  `thumbnails.py:53-55`) is to plumb it out:
  - `render_tilt_series_median_png` returns the source branch it took;
  - `_render_one` returns `(ok, source_kind, source_path)` instead of bare `bool`;
  - `generate_thumbnails` returns a per-acquisition result list (plus the existing
    representative relpath) — rippling to both call sites (`scanner.py:248`
    healing, `:287` full).
  - The enum vocabulary is normalized to the code's real names **`zarr`/`st`/
    `frames`/`none`** (the plan's earlier `mrc_stack`/`raw_frames` were wrong).
  The scanner then writes `thumbnail_path/source_kind/source_path/status` and
  `thumbnail_generated_at=now` on (re)generation. `missing_source` is detected by
  the existing `if not (zarr or st or frames)` guard (`thumbnails.py:97`);
  `render_failed` vs `ok` comes from the `_render_one` bool now surfaced.
  `missing_source` / `render_failed` drive the "— no preview source found —" and
  "never" states on the detail page. Healing path (`scanner.py:239-256`) updates
  `thumbnail_generated_at` and the provenance fields for the re-rendered
  acquisitions.
- Because both tables are keyed by their own PK, they are upserted independently
  of the content keyed-upsert and survive it (§3.2).

### 4.6 New API (`/manage` router)

Replace `src/catalog/api/routes/scans.py` with `routes/manage.py` (+ new Pydantic
schemas in `api/schemas.py`):

- `GET /manage/summary` → `{ latest_scan: {started_at,ended_at,status,duration},
  cadence_cron, outstanding: {errors, warnings} }`.
- `GET /manage/issues?severity=&file_kind=&q=` → **outstanding** issues
  (`resolved_at IS NULL`) **grouped by (entity, file_kind)**: each group =
  `{ scope, sample_id, acquisition_id, file_kind, file_path, severity (max),
  issues: [{category,message}], first_seen_at (min), last_seen_at (max) }`.
- `GET /manage/issues/resolved?within_hours=24` → **recently-resolved** issues
  (decision §9.3): same grouping shape, filtered to `resolved_at >= now -
  within_hours*3600`, plus `resolved_at` and `resolved_run_id` per group. Default
  window 24h.
- `GET /manage/scans` → `scan_runs` list (replaces all-scans).
- `GET /manage/scans/{id}` → run detail incl. counts.
- `GET /manage/scans/{id}/logs?level=&q=` → log lines for one run (powers the
  per-run expandable panel; `q`/`level` filter *within* the run).
- `GET /manage/scans/{id}/samples?outcome=` → per-run outcome drilldown (optional).
- **Deferred (§1.5):** `GET /manage/logs/search?q=&level=&status=` (cross-run
  search) — not built in the first cut.

Keep route-ordering discipline (literal paths before `/{id}`), mirroring the
existing file's note (`scans.py:198-200`).

**Priority 2 — surfaced on the detail endpoints, not Manage (§1.6).** No
`/manage/freshness`. Instead, extend the existing entity endpoints:

- `GET /samples/{id}` response gains a `scan_status` block from
  `sample_scan_status` (`last_scanned_at`, `last_changed_at`, `last_outcome`).
- `GET /acquisitions/{sample}/{acq}` (and the acquisition rows embedded in the
  sample detail payload) gain a `scan_status` block from
  `acquisition_scan_status`, including the thumbnail provenance fields.
- Both are simple PK joins (LEFT JOIN — a freshly-migrated entity not yet
  re-scanned returns nulls). Add the corresponding Pydantic fields to the
  existing sample/acquisition response schemas.

### 4.7 Wire-up & cleanup

- `state.py`: rework `start_scan`/`finish_scan`/`_record_scan_membership` for
  `scan_runs` + `scan_sample_outcomes`; keep `scan_state` helpers as-is.
- `persistence.py`: delete `persist_run_warnings` + the `scan_warnings` refresh
  block (`persistence.py:366-410`); route all issues through §4.4; add the
  `sample_scan_status` / `acquisition_scan_status` upserts (§4.5) and the
  acquisition-orphan prune (§3.2 — prune `acquisition_scan_status` rows and
  acquisition-scope issues not in `keep_acq_pks`).
- `scanner.py` `ScanReport`: carry `ScanIssue` lists instead of `ScanWarning`.
- **`routes/warnings.py`** (`GET /samples/{id}/warnings`, `:31-36`): currently
  reads `ScanWarningsORM` filtered to the latest `ScansORM` — and has the **same
  skipped-sample bug** the redesign targets. Rewrite it against `issues`
  (`sample_id=?, resolved_at IS NULL`); this also fixes the bug for free. (Dropping
  `scan_warnings`/`scans` breaks it at import/query time otherwise.)
- **`routes/samples.py`** (`:112-115`, `:278-280`): the `has_warnings` filter and
  warning counts join `ScanWarningsORM`. Rewrite both against `issues`
  (`resolved_at IS NULL`).
- Sample/acquisition read endpoints + their Pydantic schemas: add the
  `scan_status` blocks (§4.6).

## 5. Frontend implementation

### 5.1 Routes

- `/manage/` (`manage.index.tsx`) → status/cadence card + **Priority 1**
  outstanding-issues section + a **"Recently resolved (last 24h)"** section
  (§9.3). (No freshness section — Priority 2 moved to detail pages, §1.6.)
- `/manage/scans` (repurpose `manage.all-scans.tsx`) → scan-history table
  (`scan_runs`), each row linking to its run-detail page. Stays as the
  list-of-scans view; the polished standalone "Scan logs" page is **deferred**
  (§1.5).
- `/manage/scans/$scanId` (rename from `manage.$scanId.tsx`) → deep-linkable
  single-run view with the **per-run expandable log panel** (Priority 3, trimmed).
- **Sample/acquisition detail pages** (existing routes) → gain a "Data freshness
  & preview" block fed by the entity's `scan_status` (Priority 2, §1.6).

### 5.2 Components (material-react-table, MUI Accordion `ManageSection`)

- `StatusCadenceCard` (repurpose `LastScanCard`) — last started/ended/status +
  "Scan cadence … next ≈" (computed from `cadence_cron`/`cadence_tz` via the
  cron-parse dependency, rendered in local time — §3.4) + the "edited a .toml?
  appears after next scan" hint.
- `OutstandingIssuesTable` — cols: Sample/Acquisition (link), File
  (`file_kind` chip + truncated `file_path`), Severity (pill), Issues (bulleted
  messages), First seen, Still present as of — the global latest-scan ts when the
  owner was re-evaluated this run, else the per-issue `last_seen_at` with a
  "owner skipped — not re-checked" tooltip (decision §9.7). Toolbar: text filter,
  severity select, file-kind select.
- `RecentlyResolvedTable` (§9.3) — a collapsed-by-default `ManageSection` under
  the outstanding table. Same column shape but with **Resolved at** (and
  First seen) instead of "still present as of"; reads
  `GET /manage/issues/resolved?within_hours=24`. Empty state: "Nothing resolved
  in the last 24 hours."
- `ScanHistoryTable` (repurpose `AllScansTable`) — scan-history rows (id, started,
  duration, status, counts, warns/errs), each linking to the run-detail page.
- `RunLogPanel` (on `/manage/scans/$scanId`) — the per-run expandable `log-panel`
  showing `scan_log_lines`, with a within-run text/level filter. This is the only
  log UI in the first cut (§1.5); no cross-run search component.
- `EntityFreshnessCard` (Priority 2 — on the sample & acquisition detail pages,
  **not** Manage) — last outcome (pill), last updated, last scanned; and for
  acquisitions, thumbnail source file + generated-at + the "no preview source" /
  "never" states. Reads the entity's `scan_status` block (§4.6).
- Remove `SamplesWithWarningsTable`, `ScanRunWarningsTable`, `ScanSamplesTable`.
  No `FreshnessTable` is built (Priority 2 is per-entity now).

### 5.3 Data layer

- `frontend/src/types.ts`: add `ManageSummary`, `IssueGroup`, `ScanRun`,
  `ScanLogLine`, and an `EntityScanStatus` block added to the existing
  `Sample`/`Acquisition` types; remove `ScanOut`/`ScanSampleOut`/
  `SampleWarningsGroup`/`RunWarningOut`/`WarningOut`.
- `frontend/src/utils/queryOptions.ts`: replace the nine `scans` hooks with
  `useManageSummaryQuery`, `useOutstandingIssuesQuery(filters)`,
  `useRecentlyResolvedQuery(withinHours = 24)`, `useScanRunsQuery`,
  `useScanRunQuery(id)`, `useScanLogsQuery(id, filters)`. Keep `fetchOrEmpty`.
  Priority 2 needs **no new hook** — `scan_status` rides on the existing
  sample/acquisition detail queries. (`useLogSearchQuery` deferred — §1.5.)
- `frontend/package.json`: add the cron-parse dependency (e.g. `cron-parser` +
  `cronstrue`) used by `StatusCadenceCard` (§3.4). `ManageSummary` carries
  `cadence_cron` + `cadence_tz`; `IssueGroup` carries both the global latest-scan
  ts and the group `last_seen_at` + `last_seen_run_id` for the skipped-owner label
  (§9.7).

## 6. Migration & cutover

1. Ship the ORM change + the idempotent in-`init_schema` migration step (§4.1 —
   **no Alembic**, decision §9.9): `DROP TABLE IF EXISTS` the four old scan tables,
   then `create_all` the six new ones. **`scan_state` is kept** (decision §9.2).
2. Deploy backend, then **run one `scan --force` manually** (decision §9.2): this
   re-evaluates every sample even though `scan_state` mtimes are unchanged,
   populating `issues` / `*_scan_status` / provenance and regenerating any missing
   thumbnails. This is the **reversible** cutover — `scan_state` is intact, so if
   the forced scan crashes partway, normal hourly cron resumes from the existing
   ledger rather than re-scanning everything from an empty state.
   - **Why not drop `scan_state`?** Dropping it would force a full rebuild
     automatically, but a partway crash on that first all-or-nothing scan would
     leave the old tables gone, the ledger gone, and `issues`/`*_scan_status`
     half-populated — a misleading Manage view until the next cron run heals it.
     Keeping `scan_state` + an explicit `--force` is the safer default.
   - **Sanity check before step 3:** after the forced scan, confirm
     `scan_runs.status == completed`, `n_skipped == 0`, and the `issues` /
     `sample_scan_status` row counts are non-zero. Only then deploy the frontend.
3. Deploy frontend pointed at `/manage/*`.

No data backfill — all state is reconstructed from the filesystem (§1.3).

## 7. Phasing

1. **Foundation:** ORM + the idempotent `init_schema` drop/`create_all` step
   (no Alembic — §9.9) + the WAL/`busy_timeout` engine change (§4.3) + drift-test
   comment (§4.1).
2. **Issues pipeline:** `ScanIssue` + file resolver (§4.2) → reconciliation
   (§4.4) → `/manage/issues` + `/manage/issues/resolved` + `/manage/summary`
   (§4.6) → `OutstandingIssuesTable` + `RecentlyResolvedTable` + status card.
   *Delivers Priority 1 (incl. the recently-resolved view) end-to-end first* —
   it's the branch's name.
3. **Freshness/provenance (detail pages — §1.6):** `sample_scan_status` /
   `acquisition_scan_status` writes + thumbnail return values (§4.5) →
   `scan_status` blocks on the `/samples/{id}` & `/acquisitions/{…}` endpoints
   (§4.6) → `EntityFreshnessCard` on the detail pages.
4. **Logs (trimmed — §1.5):** log sink + retention (§4.3) →
   `scan_runs`/`scan_sample_outcomes` rework (§4.7) → `/manage/scans` +
   `/manage/scans/{id}/logs` → `ScanHistoryTable` + `RunLogPanel` on the
   run-detail route. (No `/manage/logs` page, no cross-run search.)
5. **Cleanup:** delete old routes/components/endpoints/schemas; tests.

## 8. Testing

- ORM round-trip + `init_schema` smoke: the idempotent drop step removes legacy
  scan tables and `create_all` materializes the new ones on an empty DB (and is
  safe to run twice). No Alembic (§9.9).
- Reconciliation unit tests: new issue inserts with first_seen; recurring issue
  preserves first_seen + bumps last_seen; fixed issue (re-evaluated sample) gets
  resolved_at; **skipped sample leaves issues outstanding** (and `last_seen`
  unchanged); failed sample adds `assembly_failed` without resolving others;
  message-only change preserves first_seen (fingerprint excludes message).
- Crash/partial-run reconciliation: a run that ends non-`completed` does **not**
  resolve run-scope issues (§9.6); per-sample state for reached samples is still
  correct. All timestamps in a run share the single run-level `now` (§9.6).
- Orphan prune (§9.10): a removed acquisition's `acquisition_scan_status` row and
  its acquisition-scope issues are deleted on the next sample upsert; a
  soft-deleted sample keeps its `sample_scan_status` row.
- File-resolver tests: each `location` prefix → expected `(file_kind, file_path,
  acquisition_id)`.
- Freshness tests: upsert sets `last_changed_at`; skip updates `last_scanned_at`
  but leaves `last_changed_at`; thumbnail status transitions
  (`ok`/`missing_source`/`render_failed`); status row survives the acquisition
  keyed-upsert. Thumbnail-source-after-fallback (§9.5): zarr absent → renderer
  falls back to `st` → records `st`/its path, not the pre-call guess.
- Detail-endpoint tests: `/samples/{id}` & `/acquisitions/{…}` include the
  `scan_status` block; a not-yet-rescanned entity returns nulls (LEFT JOIN).
- Log capture (§9.11): lines bulk-inserted once at run end with `sample_id`
  context and monotonic `seq`; no DB writes occur mid-scan; retention prunes old
  runs; a crashed scan still persists its buffered partial log + `failed` status
  via the except path.
- Recently-resolved view: an issue resolved <24h ago appears; one resolved >24h
  ago does not; `within_hours` widens the window; grouping/shape matches the
  outstanding endpoint plus `resolved_at`.
- API contract tests for each `/manage/*` endpoint (filters, grouping, 404s).
- Frontend: render tests for the outstanding + recently-resolved tables (incl.
  the "nothing resolved in 24h" empty state) and the `EntityFreshnessCard` empty
  states ("never", "no preview source").

## 9. Decisions (all resolved)

1. **Cadence source — config, with a frontend cron-parse dependency.**
   `SCAN_CADENCE_CRON` (default `0 * * * *`) + `SCAN_CADENCE_TZ` (cluster TZ)
   surfaced via `/manage/summary`; the frontend uses a cron-parse dependency
   (e.g. `cron-parser` + `cronstrue`) to compute the next-fire time and render it
   in the user's local timezone (cron fires in cluster TZ). Not introspected from
   k8s. (§3.4)
2. **`scan_state` on migration — keep it; cut over with `scan --force`** (not a
   `scan_state` drop). Reversible; avoids the all-or-nothing first-scan risk. A
   post-cutover sanity check (`completed`, `n_skipped == 0`, non-zero issue/status
   counts) gates the frontend deploy. (§6)
3. **Resolved-issue history — IN SCOPE: a "Recently resolved" view (last 24h).**
   Manage shows, below the outstanding-issues table, a companion section listing
   issues whose `resolved_at` is within the last 24 hours — so a researcher who
   just fixed a `.toml` gets positive confirmation that the next scan picked the
   fix up. Powered by the `resolved_at`/`resolved_run_id` already written in §4.4;
   new endpoint + component in §4.6 / §5. (24h is a fixed default window; the
   endpoint takes a `within_hours` param so it's tunable.)
4. **Fingerprint excludes `message`** — re-worded/re-counted messages keep their
   original first-seen; identity = scope+ids+file_kind+location+category. (§4.4)
5. **Log retention — 720 runs ≈ 30 days**, DB log level INFO (DEBUG opt-in). (§4.3)
6. **Per-acquisition freshness — derive from the parent sample's outcome; no
   per-acq change detection in this cut.** Detection itself is ~free (the scanner
   already `stat()`s every parse-target during gating — `scanner.py:237,308`;
   grouping those by acquisition is in-memory only). The cost is *acting* on it:
   realizing the savings needs partial-update assembly/persistence (the loader
   builds a whole `SampleRecord`; child rows are keyed-upserted per sample). No
   runtime upside at the hourly cadence, so defer (revisit only if scans start
   bumping the hour).
7. **Priority 2 placement** — detail pages via two 1:1 side tables; not a Manage
   table, not content-table columns. (§1.6)
8. **Extra wireframe priorities** (per-lab/project rollups, new-vs-updated counts
   per scan, a Manage staleness rollup) — **deferred**; additive later, not part
   of this cut.
9. **No Alembic yet.** The runtime stays on `Base.metadata.create_all` (`db.py:37`);
   the schema change ships as an idempotent `DROP TABLE IF EXISTS` (legacy scan
   tables) inside `init_schema` before `create_all`, **not** as an Alembic
   revision. The dormant Alembic scaffold is left untouched. (§1.4, §4.1, §6)
10. **Orphan cleanup — explicit prune, not FK cascade.** Hard-deleted acquisitions
    would orphan `acquisition_scan_status` rows and acquisition-scope `issues`;
    `upsert_sample_record` prunes them by `keep_acq_pks` (mirroring
    `_delete_stale_children`). SQLite `PRAGMA foreign_keys` stays off; no FK
    cascade dependency. (§3.2, §4.7)
11. **Log persistence — in-memory buffer + single run-end bulk insert** (sink is
    `enqueue=False`, appends to a list with a monotonic `seq`); no mid-scan DB
    writes, preserving the single-writer contract. The SQLite engine is also
    switched to WAL + `busy_timeout` as general hardening. (§4.3)
