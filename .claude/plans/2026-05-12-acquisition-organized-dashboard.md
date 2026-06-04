# Acquisition-organized dashboard

**Date:** 2026-05-12
**Author:** allison-truhlar (planning via Claude)
**Target branch:** `dev` (new feature branch off `dev`)
**Predecessor:** [`2026-05-08-dashboard-mvp.md`](./2026-05-08-dashboard-mvp.md)

## 1. Context

The current dashboard (built per the MVP plan, now landed on `dev`) is organized **by sample**:

- `GET /samples` returns one row per `samples.sample_id`, with intrinsic child counts (`n_acquisitions`, `n_tilt_series`, `n_tomograms`) and a warning count.
- Filters use `EXISTS` subqueries against `acquisitions` / `tilt_series` / `tomograms`, so a sample matches if *any* child row qualifies.
- `/samples/$sampleId` shows the sample header, sub-entities (chromatin/synapse/etc.), and a list of acquisition cards — each acquisition card embeds its tilt-series, tomograms, annotations.

The NiceGUI prototype in `aicryoet-tools/src/aicryoet_tools/dashboard/pages/cryoet.py` is organized **by acquisition**:

- The table shows one row per acquisition (columns: Lab, Sample, Name, Tomograms).
- Filters apply directly to acquisition-level fields (voltage / microscope / camera / pixel-spacing / n_tilts / voxel-size / has-tomograms).
- The detail pane is scoped to one acquisition: its tilt-series cards + tomogram cards + annotations, with a small sample-context header.

This plan covers the work to reorient the current dashboard around acquisitions while preserving sample-level context.

## 2. Goals

1. The browse table shows **one row per acquisition**, identified by `(sample_id, acquisition_id)`.
2. Filters apply directly to the visible row (per-acquisition WHERE clauses) rather than EXISTS-over-children at sample scope.
3. The detail pane shows a single acquisition's tilt-series / tomograms / annotations, plus a collapsible "Sample context" section carrying the parent sample's sub-entities.
4. URL-shareable filter state is preserved; the selected-row URL becomes `/acquisitions/$sampleId/$acquisitionId` (or equivalent compound segment).
5. No regressions in image previews, polar plots, Neuroglancer launches, or scan history.

## 3. Non-goals

- No changes to the underlying schema (`samples`, `acquisitions`, `tomograms`, `tilt_series`, `annotations`, `scan_warnings`).
- No backfill or restructuring of `scan_warnings` to be acquisition-scoped (see §4 open question).
- No additional viewers or new image renderings.
- No MD / simulation work — still deferred per the MVP plan §14.

## 4. Settled design decisions

These were initially open questions; the user confirmed each recommendation on 2026-05-12.

1. **Replace, don't coexist.** `/samples` is dropped entirely. The app reorients around `/acquisitions`; home and header link to it; the listing endpoint `GET /samples` is removed.
2. **Empty samples disappear.** Samples with zero acquisitions no longer appear in the browse table. They remain reachable by sample-id via the detail endpoint (§8).
3. **Warnings = sample-scoped, shown in detail pane only.** No warning column on the acquisition table. The acquisition detail pane's sample-context section surfaces "sample has N warnings" via the existing `GET /samples/{id}/warnings`. (Per-acquisition warnings would require schema + scanner work; deferred.)
4. **Row key uses slash separator.** DataGrid `getRowId` returns `` `${sample_id}/${acquisition_id}` ``, matching the URL path segments. Before committing, audit the current dataset to confirm no id contains `/`; fallback is `encodeURIComponent` on each segment.
5. **All surfaced columns are sortable.** Default sort is `(sample_id, acquisition_id) asc`; `sort` enum includes `sample_id`, `acquisition_id`, `project`, `microscope`, `voltage`, `pixel_size`. The composite `(sample_id, acquisition_id)` tiebreaker still applies for stable pagination.

## 5. Backend (`cryoet_catalog/api/`)

### 5.1 New route module `routes/acquisitions.py`

Mirrors the structure of `routes/samples.py`, but the row unit is `AcquisitionORM` joined to `SampleORM`.

#### `GET /acquisitions` — list

- Query params (mostly preserved from `/samples`):
  - **Sample-level filters** (still useful as facets): `project`, `data_source`, `type`, `q`.
  - **Acquisition-level filters** (direct WHERE on `AcquisitionORM`): `microscope`, `voltage`, `camera`, `pixel_size_min/max`.
  - **Tilt-series / tomogram filters** (EXISTS against children of the *current acquisition*, not sample-wide): `n_tilts_min/max`, `image_format`, `voxel_spacing_min/max`, `has_tomograms`.
  - **Pagination/sort**: per §4-D5, `sort` enum is `sample_id | acquisition_id | project | microscope | voltage | pixel_size`. Default `sample_id` with stable `(sample_id, acquisition_id)` tiebreaker.
- Response shape (new `AcquisitionRow` Pydantic model in `api/schemas.py`):
  ```python
  class AcquisitionRow(BaseModel):
      sample_id: str
      acquisition_id: str
      project: str
      data_source: str
      type: str | None
      microscope: str | None
      voltage: float | None
      camera: str | None
      pixel_size: float | None
      n_tilt_series: int      # scoped to this acquisition
      n_tomograms: int        # scoped to this acquisition
      # No warning_count — warnings are sample-scoped, shown only in the
      # detail pane's sample-context section (§4-D3).
  ```
- Implementation notes:
  - SELECT FROM `acquisitions a JOIN samples s ON s.sample_id = a.sample_id WHERE s.deleted_at IS NULL`.
  - Per-acquisition child counts via correlated scalar subqueries on `(sample_id, acquisition_id)` rather than `sample_id` alone — this is the main divergence from `routes/samples.py:97`. Example:
    ```python
    n_tomo_sq = (
        select(func.count())
        .select_from(orm.TomogramORM)
        .where(orm.TomogramORM.sample_id == orm.AcquisitionORM.sample_id)
        .where(orm.TomogramORM.acquisition_id == orm.AcquisitionORM.acquisition_id)
        .correlate(orm.AcquisitionORM)
        .scalar_subquery()
    )
    ```
  - Tilt-series/tomogram EXISTS filters must correlate on the **acquisition** composite key, not just `sample_id`:
    ```python
    exists(
        select(1)
        .where(orm.TiltSeriesORM.sample_id == orm.AcquisitionORM.sample_id)
        .where(orm.TiltSeriesORM.acquisition_id == orm.AcquisitionORM.acquisition_id)
        .where(and_(*ts_conds))
        .correlate(orm.AcquisitionORM)
    )
    ```
  - Range filters stay NULL-tolerant for acquisition-level fields (`pixel_size`) to match the existing semantics. Direct (non-EXISTS) acquisition-level filters should treat NULL the same way `/samples` does to avoid surprise drops on partial metadata.

#### `GET /acquisitions/{sample_id}/{acquisition_id}` — detail

- New Pydantic `AcquisitionDetail` that bundles:
  - Sample context: `sample_id`, `project`, `data_source`, `type`, `cell_type`, `description`, plus the typed sub-entities (`chromatin`, `synapse`, `simulation`, `freezing`, `milling`, `aunp`) — reuses the `_SUB_ENTITY_MAP` + `_build_sub_entity` helpers from `routes/samples.py:34`.
  - Acquisition payload: every field already on `AcquisitionOut` (resolution, microscope, voltage, etc.).
  - Children scoped to this acquisition: `tomograms`, `annotations`, `tilt_series` (reuse `TomogramOut`, `AnnotationOut`, `TiltSeriesOut`).
- 404 when the acquisition row doesn't exist OR when its sample is soft-deleted.
- This endpoint subsumes most of what `GET /samples/{sample_id}` currently returns. The sample-detail endpoint stays (§8).

### 5.2 `GET /filters/options`

- The current implementation (`routes/filters.py`) already pulls categorical options and numeric ranges from `acquisitions` / `tilt_series` / `tomograms` joined to `samples` for live-sample filtering. It needs **no changes** — every option it returns is still meaningful when filtering acquisition rows.
- `data_sources`, `projects`, `types` remain sample-level facets but apply via the JOIN.

### 5.3 Warning endpoints

- `GET /samples/{sample_id}/warnings` stays as-is (`routes/warnings.py`). The acquisition detail view will fetch this for the sample-context section to surface "sample has N warnings" (§4-D3).

### 5.4 Register / remove routers

- `cryoet_catalog/api/main.py`: include the new `acquisitions.router` at prefix `/acquisitions`.
- Remove the `GET /samples` listing endpoint per §4-D1 (the detail endpoint stays; §8). This happens in the cutover step (§7 step 3), not the initial backend addition.

### 5.5 Tests

- New `tests/cryoet_catalog/api/test_acquisitions.py`, modeled on the existing `test_samples.py`:
  - One row per acquisition; samples with multiple acquisitions appear multiple times.
  - Per-acquisition counts match what's in the DB for that `(sample_id, acquisition_id)` pair.
  - Soft-deleted samples are filtered out.
  - Each filter (categorical, range, EXISTS-child) returns the expected subset.
  - NULL-tolerance for range filters matches `/samples` behavior.
  - Sort + pagination stability.
- Detail endpoint tests: 404 paths (missing acquisition, missing sample, soft-deleted sample), sub-entity loading, children scoped to the requested acquisition.

## 6. Frontend (`frontend/src/`)

### 6.1 Route restructure

- **Delete** `routes/samples.tsx`, `routes/samples/index.tsx`, `routes/samples/$sampleId.tsx` (per §4-D1, in the cutover step §7).
- **Add**:
  - `routes/acquisitions.tsx` — layout route. Owns `AppShell` + `FilterDrawer` + `Splitter` (left = `AcquisitionsTable`, right = `<Outlet />`).
  - `routes/acquisitions/index.tsx` — empty-state placeholder for the right pane.
  - `routes/acquisitions/$sampleId.$acquisitionId.tsx` — loader fetches `/acquisitions/{sampleId}/{acquisitionId}` and renders `AcquisitionDetailPanel`.
- `routeTree.gen.ts` regenerates automatically via the TanStack Router Vite plugin.
- Update `Header.tsx` nav: rename "Samples" → "Acquisitions" (or "Browse"); update internal links from `/samples` → `/acquisitions`. Audit `routes/index.tsx` (home page) for any links to `/samples`.

### 6.2 Search params

- Move `utils/samplesSearch.ts` → `utils/acquisitionsSearch.ts` (or rename `samples*` → `acquisitions*` throughout).
- Schema stays almost identical — the same filter keys are still relevant. Update the `sort` enum to include `acquisition_id`, `microscope`, `voltage`, `pixel_size`.
- The 300 ms debounce inside `FilterDrawer` for slider drags stays as-is.

### 6.3 Data hooks (`frontend/src/hooks/` or wherever they currently live)

- New `useAcquisitions.ts`:
  - `acquisitionsQueryOptions(params: AcquisitionsSearchParams)` keyed by `['acquisitions', serializedParams]`, query fn `apiFetch<AcquisitionRow[]>('/acquisitions?…')`.
  - `useAcquisitionsQuery(params)` wraps `useSuspenseQuery`.
- New `useAcquisitionDetail.ts`:
  - `acquisitionDetailQueryOptions({ sampleId, acquisitionId })` → `apiFetch<AcquisitionDetail>('/acquisitions/${sampleId}/${acquisitionId}')`.
- `useFiltersOptions.ts` and `useSampleWarnings.ts` stay (warnings still fetched by `sampleId` for the detail pane).
- Delete `useSamples.ts` and `useSampleDetail.ts` in the cutover step (§4-D1).

### 6.4 Components

#### New: `components/acquisitions/AcquisitionsTable.tsx`

Mirrors `components/samples/SamplesTable.tsx:13` but with new columns:

- `getRowId={(r) => `${r.sample_id}/${r.acquisition_id}`}`
- Columns (initial set):
  - Project (flex 1, min 120)
  - Sample (flex 1.5, min 160)
  - Acquisition (flex 1.5, min 160)
  - Microscope (flex 1, min 140)
  - Voltage (number, width 90)
  - Pixel size (number, width 100)
  - Tilt series (number, width 90)
  - Tomograms (number, width 100)
- Selection model: `[`${sampleId}/${acquisitionId}`]` when both URL params are present.
- On selection change: `navigate({ to: '/acquisitions/$sampleId/$acquisitionId', params, search: (prev) => prev })`.

#### New: `components/acquisitions/AcquisitionDetailPanel.tsx`

Composes:

- `SampleContextHeader` (new, small): project / sample_id / type / cell_type chip, and a "View other acquisitions in this sample" link that navigates back to `/acquisitions?project=…&q=${sampleId}` (or similar).
- Collapsible `SampleContextBlock` (new, MUI `Accordion`, collapsed by default): renders the same `SubEntityBlock`s currently used in `SampleDetailPanel.tsx` (chromatin/synapse/simulation/freezing/milling/aunp/description). Reuses the existing `chromatinEntries`/etc. helpers from `SampleDetailPanel.tsx` — move them into a shared module (`utils/sampleEntries.ts`) since both panels need them.
- `WarningList` (existing) — fed by `useSampleWarningsQuery(sampleId)`.
- `AcquisitionBody` (new): the contents that `AcquisitionCard.tsx` currently renders for a single acquisition — the metadata table, copy-path row, and the per-acquisition `TiltSeriesCard` / `TomogramCard` / `AnnotationList`. Effectively `AcquisitionCard.tsx` minus the `<Card>` wrapper, since the panel itself owns the layout.

#### Reuse without changes

- `TiltSeriesCard.tsx`, `TomogramCard.tsx`, `AnnotationList.tsx`, `SubEntityBlock.tsx`, `WarningList.tsx` — all parameterized on `(sample_id, acquisition_id, …)` already, no signature changes needed.
- `FilterDrawer.tsx`, `RangeSlider.tsx`, `ChipSelect.tsx`, `FilterClearButton.tsx` — unchanged.

#### Delete in the cutover step (§4-D1)

- `components/samples/SamplesTable.tsx`
- `components/samples/SampleDetailPanel.tsx`
- `components/samples/SampleHeader.tsx`
- `components/samples/AcquisitionCard.tsx` (its body folds into `AcquisitionBody`)

### 6.5 Types (`frontend/src/types.ts`)

- Add `AcquisitionRow` (the list-row shape) and `AcquisitionDetail` (the detail shape).
- Remove `SampleSummary` in the cutover step (the listing endpoint is gone). Keep `SampleDetail` — `GET /samples/{id}` stays (§8) and the type is still useful for any sample-id-driven callers.

### 6.6 Home page + scans page

- `routes/index.tsx`: update the "Browse" button from `/samples` → `/acquisitions`. The project-summary cards continue to count samples (intrinsic, unchanged). Optionally add an "Acquisitions" stat to the Totals row.
- `routes/scans.tsx`: no functional change.

## 7. Migration / rollout

Sequencing (each step is a self-contained PR):

1. **Backend addition** (no removal): add `routes/acquisitions.py`, register at `/acquisitions`, add tests, ship. `/samples` still works.
2. **Frontend addition** (no removal): add `/acquisitions` route + components alongside `/samples`. Header gains an "Acquisitions" link. User validates UX in the browser against real data, including a quick A/B against `/samples`.
3. **Cutover** (per §4-D1): point home/header to `/acquisitions` only; delete the `/samples` frontend route, `SamplesTable`, `SampleDetailPanel`, `SampleHeader`, `AcquisitionCard`, `useSamples.ts`, `useSampleDetail.ts`, `SampleSummary` type. Remove the `GET /samples` listing handler from `routes/samples.py` (keep the detail endpoint per §8). Audit `routes/index.tsx` and `Header.tsx` for any lingering `/samples` links.

Splitting the work this way means the dashboard never goes dark in the middle of the refactor, and the two views can be A/B compared briefly before deletion.

## 8. Sample endpoints — what stays

- `GET /samples` (list) — **dropped** in the cutover step (§4-D1, §7 step 3). No remaining caller.
- `GET /samples/{id}` (detail) — **kept.** The new `AcquisitionDetail` carries the sub-entities for the panel, but a sample-level detail endpoint is still a clean way for future code (CLI tools, scripts) to fetch a sample by id without going through one of its acquisitions.
- `GET /samples/{id}/warnings` — **kept**; the acquisition detail panel calls it.

## 9. Risks / gotchas

- **Composite-key URL encoding**: if any `sample_id` or `acquisition_id` ever contains `/`, the route param will misbehave. Audit the current dataset as the first concrete step (§4-D4). Fallback: `encodeURIComponent` both segments before building the URL and decoding inside the route component.
- **Filter mental-model shift**: users accustomed to the sample view's "show samples with at least one matching child" semantics may be surprised that an acquisition view drops siblings that don't individually match. Worth a one-line tooltip on the drawer or a brief note in the empty-state.
- **Per-row query cost**: per-acquisition child counts via correlated subqueries are fine at current dataset scale (low thousands), but two extra correlated counts per row will be slower than the sample-scoped version. If pagination feels sluggish, switch to LEFT JOIN + GROUP BY on the visible page.
- **Warning surface**: per §4-D3, warnings remain sample-scoped. If the user later wants per-acquisition warnings, `ScanWarningsORM` needs an `acquisition_id` column, the scanner needs to emit it, and the migration needs a backfill or "unknown" fallback. Out of scope here but worth noting.

## 10. Out of scope

- Schema changes to `scan_warnings`.
- New parsers, new image renderings, new Neuroglancer wiring.
- Multi-select / bulk operations on acquisitions.
- Saved filter presets.
- MD / simulation surfacing (still deferred from MVP §14).
