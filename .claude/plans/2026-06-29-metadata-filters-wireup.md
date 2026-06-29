# Wire metadata fields into the /data, /experimental, /md-simulation filters

**Date:** 2026-06-29
**Branch:** `add-metadata-filters`

## Goal

Expose almost every data-model metadata field as a filter on the three browse
routes (`/data`, `/experimental`, `/md-simulation`). Filters are organized into
two collapsible **sections** (Sample properties, Acquisition properties), each
holding **groups** (general, chromatin, …) with a per-group expand/collapse-all
control, and each group holding **properties** that are individually expandable
(collapsed by default). Sample filters match sample metadata; acquisition
filters select samples that have ≥1 matching acquisition and additionally filter
each sample's acquisition subtable down to the matching acquisitions (expanding
all subtables by default when any acquisition filter is active).

## Confirmed decisions

1. **Acquisition subtable filtering = client-side.** `AcquisitionsSubTable`
   already fetches the full `SampleDetail` (all acquisitions + nested
   tilt_series/tomograms/annotations). Filter that array in the browser with a
   predicate that mirrors the backend `EXISTS` semantics. No detail-endpoint
   change.
2. **Exclude the per-image MDOC arrays** (`tilt_angles`, `defocus_per_image`,
   `dose_per_tilt`) as filters.
3. **One phased, registry-driven plan.** A single field registry (mirrored on
   each side) drives the URL schema, query string, backend filters, options
   endpoint, and UI — instead of ~50 hand-coded filters.

## Current architecture (verified)

- **Filtering is 100% server-side.** URL params (`samplesSearchSchema`, zod, in
  `frontend/src/utils/samplesSearch.ts`) → `buildSamplesQueryString` →
  `GET /samples` (`src/catalog/api/routes/samples.py`) → SQLAlchemy `EXISTS`
  subqueries. URL is the single source of truth (TanStack Router); query is
  debounced 300 ms, URL updates immediately.
- **Sidebar UI:** `LandingFilters` (single-arm) / `AllDataFilters` (`/data`)
  with `DropdownFilter` + `MinMaxRow` subcomponents. `AllDataBrowser` /
  `SamplesBrowser` translate URL↔drawer state via `searchToFilters` /
  `applyFilterPatch` and own the mobile `Drawer`.
- **Options:** `GET /filters/options` → `FiltersOptionsOut`
  (`src/catalog/api/routes/filters.py`), hand-coded per field, cached forever
  client-side (`filtersOptionsQueryOptions`, `useSuspenseQuery`).
- **Table:** `SamplesPortalTable` (MRT) renders `SampleSummary` rows; detail
  panel = `AcquisitionsSubTable`, which fetches `sampleDetailQueryOptions` and
  renders **all** acquisitions. MRT detail panels mount lazily on expand.
- **ORM tables exist** for every sub-entity: `ChromatinORM`, `LabelORM`,
  `FiducialORM`, `FreezingORM`, `MillingORM`, `SimulationORM`, `MdRunORM`,
  `AcquisitionORM`, `TiltSeriesORM`, `RawTomogramORM`,
  `PostProcessedTomogramORM`, `AnnotationORM`.
- **Enums** (`src/schema/schema.py`): `LabName` (collepardo/gouaux/rosen/villa),
  `DataSource` (experimental/simulation), `Project`
  (chromatin/synapse/nanogold), `DatasetType` (bulk/single_molecule/slab).

## Input-type rules (from the request)

- integer / float / list-of-number → **range** selector (`min`/`max`)
- text / list-of-text / enum → **checkboxes**, multi-select within a property
  (OR within facet, AND across facets)
- boolean → **radio buttons** (Yes / No / Any)
- "has X?" → **existence checkbox** (checked ⇒ require the thing exists)

---

## The field registry (single source of truth)

Mirrored as a TS array (`frontend/src/utils/filterFields.ts`) and a Python list
(`src/catalog/api/filter_fields.py`). Each entry:

```
key            URL param base (range fields emit {key}_min / {key}_max)
label          UI label
entity         'sample' | 'acquisition'
group          group id (see below)
kind           'text' | 'range' | 'boolean' | 'existence'
table          ORM table for backend EXISTS (sample = direct column)
column         ORM column (or, for 'existence', the predicate id)
```

Group metadata (`appliesTo`, `requiresProject`) is attached at the **group**
level, not per field.

### Section A — Sample properties

| Group | appliesTo | requiresProject | Field (key) | kind | table.column |
|---|---|---|---|---|---|
| **general** | — | — | `lab_name` | text(enum) | sample.lab_name |
| | | | `data_source` | text(enum) | sample.data_source · *gating control; hidden on single-arm routes* |
| | | | `project` | text(enum) | sample.project · *gating control* |
| | | | `type` | text | sample.type |
| | | | `cell_type` | text | sample.cell_type |
| **chromatin** | — | chromatin | `substrate` | text | chromatin.substrate |
| | | | `linker_length_bp` | range | chromatin.linker_length_bp |
| | | | `linker_pattern` | text‡ | chromatin.linker_pattern (list[int], stringified) |
| | | | `linker_distribution` | text | chromatin.linker_distribution |
| | | | `buffer` | text | chromatin.buffer |
| | | | `ptm` | text | chromatin.ptm |
| | | | `histone_variants` | text | chromatin.histone_variants |
| | | | `transcription_factors` | text | chromatin.transcription_factors |
| | | | `nucleosome_count` | range | chromatin.nucleosome_count |
| | | | `dna_length_bp` | range | chromatin.dna_length_bp |
| | | | `nucleosome_uM` | range | chromatin.nucleosome_uM |
| | | | `sequence_identity` | text | chromatin.sequence_identity |
| | | | `nucleosome_footprint` | text‡ | chromatin.nucleosome_footprint (list[int], stringified) |
| | | | `linker_length_fraction` | range | chromatin.linker_length_fraction |
| **labels** | experimental | — | `label_target` | text | label.label_target |
| | | | `aunp_type` | text | label.aunp_type |
| | | | `label_aunp_size_nm` | text‡ | label.aunp_size_nm (float\|list[float], categorical) |
| | | | `conjugation` | text | label.conjugation |
| | | | `conjugation_target` | text | label.conjugation_target |
| | | | `fluorophore` | text | label.fluorophore |
| **fiducial AuNP** | experimental | — | `fiducial_aunp_size_nm` | range | fiducial.aunp_size_nm |
| | | | `vendor` | text | fiducial.vendor |
| | | | `catalog_number` | text | fiducial.catalog_number |
| | | | `product_name` | text | fiducial.product_name |
| | | | `concentration_value` | range | fiducial.concentration_value |
| | | | `concentration_unit` | text | fiducial.concentration_unit |
| **freezing** | experimental | — | `grid_type` | text | freezing.grid_type |
| | | | `solution_type` | text | freezing.solution_type |
| | | | `cryoprotectant` | text | freezing.cryoprotectant |
| | | | `freezing_method` | text | freezing.method |
| | | | `planchette_size` | text | freezing.planchette_size |
| | | | `spacer_thickness` | text | freezing.spacer_thickness |
| **milling** | experimental | — | `milling_scheme` | text | milling.scheme |
| | | | `milling_quality` | text | milling.quality |
| **simulation** | simulation | — | `dataset_type` | text(enum) | simulation.dataset_type |

†list-of-number range — see ceiling note in Open Questions.

### Section B — Acquisition properties (all `entity: 'acquisition'`)

| Group | Field (key) | kind | table.column |
|---|---|---|---|
| **general** | `resolution` | range | acquisition.resolution |
| | `tilt_spacing` | range | acquisition.tilt_spacing |
| | `defocus_range` | text | acquisition.defocus_range (free-text string) |
| | `energy_filter` | text | acquisition.energy_filter |
| | `phase_plate` | boolean | acquisition.phase_plate |
| | `microscope` | text | acquisition.microscope *(existing)* |
| | `facility` | text | acquisition.facility |
| | `acquisition_quality` | text | acquisition.acquisition_quality (checkboxes 1–5) |
| | `pixel_size` | range | acquisition.pixel_size *(existing)* |
| | `total_dose` | range | acquisition.total_dose |
| | `tilt_min` | range | acquisition.tilt_min |
| | `tilt_max` | range | acquisition.tilt_max |
| | `tilt_axis` | range | acquisition.tilt_axis |
| | `voltage` | text§ | acquisition.voltage *(existing multi)* |
| | `energy_filter_slit_width` | range | acquisition.energy_filter_slit_width |
| | `frame_count` | range | acquisition.frame_count |
| | `camera` | text | acquisition.camera *(existing)* |
| **tilt series** | `has_unaligned_tilt_series` | existence | tilt_series WHERE is_aligned IS NOT TRUE |
| | `has_aligned_tilt_series` | existence | tilt_series WHERE is_aligned IS TRUE |
| | `has_tilt_series_zarr` | existence | tilt_series WHERE zarr_path IS NOT NULL |
| **tomograms** | `has_raw_tomogram` | existence | raw_tomogram exists |
| | `has_post_processed_tomogram` | existence | post_processed_tomogram exists |
| | `has_tomogram_zarr` | existence | (raw ∪ post) WHERE zarr_path IS NOT NULL |
| **annotations** | `annotation_type` | text | annotation.type |

‡`label_aunp_size_nm` (`float|list[float]`), `linker_pattern` /
`nucleosome_footprint` (`list[int]`) are filtered as **data-derived categorical
facets**: the options endpoint runs `SELECT DISTINCT col` and offers each
*exact stored value* as a checkbox; the filter matches `col IN (...)` using
those same exact strings. Because both sides use the literal stored value the
match is byte-identical by construction — no canonicalization, no `json_each`,
no dialect risk, and the facet self-populates from whatever researchers
actually author. Trade-off: whole-value match only (pattern *is* `[197, 172]`),
not per-element (*contains* `197`), and `label_aunp_size_nm` is a pick-list, not
a numeric range. `// ponytail:` upgrade path — once real data shows per-element
matching or a numeric range is wanted, swap that one field to `json_each` /
range then.
§`voltage` stays a multi-select checkbox facet (discrete kV values, existing
param) rather than a range.

Excluded by decision: `tilt_angles`, `defocus_per_image`, `dose_per_tilt`,
`date_collected`, all `*_id` and `*_path` fields, `label.notes`, `milling.date`.

---

## Phases

### Phase 0 — Registry
- `src/catalog/api/filter_fields.py`: Python registry + group metadata.
- `frontend/src/utils/filterFields.ts`: mirrored TS registry + group metadata
  (`GROUPS: {section, id, title, appliesTo?, requiresProject?, fields[]}`).
- The two registries are **hand-mirrored** (not codegen — this repo has no
  cross-language build step and `types.ts` already hand-mirrors `schemas.py`).
- A drift test (`tests/catalog/test_filter_fields_drift.py`) that (a) asserts
  every Python registry `table.column` exists on the named ORM model, and (b)
  reads `filterFields.ts` and asserts key/kind/table/column parity with the
  Python registry — guards both ORM drift and TS↔Python mirror drift. Mirrors
  the existing `test_orm_drift.py` pattern; ~15 lines, no build coupling.

### Phase 1 — Backend filters (`samples.py`)
- Replace the hand-coded `Query(...)` params with registry-driven handling.
  Accept the full param set; group by `table` and build one `EXISTS` per table:
  - **sample-direct** (`lab_name`, `data_source`, `project`, `type`,
    `cell_type`): `WHERE col IN (...)`.
  - **1:1 sub-entities** (chromatin/fiducial/simulation/freezing/milling):
    `EXISTS(select 1 from <table> where sample_id == sample AND <all conds>)`.
  - **label** (1:N): `EXISTS` on `LabelORM` with AND of all label conds inside
    one `EXISTS` — so all checked label facets must hold on the **same label
    row** (per-row, consistent with the acquisition rule below).
  - **acquisition**: `EXISTS` on `AcquisitionORM` correlated to sample with AND
    of scalar conds **and** nested existence conds (tilt_series / tomogram /
    annotation correlated to the acquisition) — so all acquisition filters hold
    on the *same* acquisition.
- Match kinds: text → `col.in_(values)`; range → NULL-tolerant
  `or_(col.is_(None), col >= lo)` / `<= hi` (reuse existing pattern); boolean →
  `col.is_(True/False)`; existence → correlated `EXISTS`/`~EXISTS`.
- Keep existing params working (`microscope`, `camera`, `voltage`,
  `pixel_size_*`, `dataset_type`, `type`, `q`, sort/pagination unchanged).
- **Remove** three existing filters that don't fit the registry and are being
  retired by decision:
  - `voxel_size_*` range (the raw∪post union range) — dropped. (The frontend's
    `voxel_spacing_*` param never matched the backend's `voxel_size_*` and was
    already dead; remove the dead frontend wiring too — see Phase 3.)
  - `has_tomograms` (raw∪post existence) — superseded by the registry's
    `has_raw_tomogram` / `has_post_processed_tomogram` existence filters.
  - `has_warnings` — dropped (backend-only today, never surfaced in the UI).
  - `n_tilts_*` — dropped; dead end-to-end today (frontend-only, no backend
    param). Remove its frontend wiring in Phase 3.
- Tests: representative cases per kind (chromatin `substrate` IN, label
  `conjugation` EXISTS, acquisition `resolution` range, `has_aligned_tilt_series`,
  `annotation_type`, cross-facet AND, OR-within-facet).

### Phase 2 — Backend options (`filters.py`)
- Make `FiltersOptionsOut` generic:
  `{ categorical: dict[str, list[str]], ranges: dict[str, RangeOut] }`.
- Generate by iterating the registry: for each `text` field, `SELECT DISTINCT
  col` joined through `samples` (deleted_at IS NULL); for each `range` field,
  `MIN/MAX`. Enum values come through distinct too (auto-scoped to present data).
- `existence`/`boolean` fields need no options.
- The `‡` JSON facets (`label_aunp_size_nm`, `linker_pattern`,
  `nucleosome_footprint`) are plain `text` fields here: `SELECT DISTINCT col`
  returns the **exact stored strings**, which become the checkbox options and
  are matched verbatim in Phase 1 — no special-casing, no voxel-style union.
- No raw∪post union queries remain (voxel range / `has_tomograms` are removed).
- Update the TS `FiltersOptionsOut` type. ~30 distinct queries, run once and
  cached forever client-side — acceptable.
- Tests: options shape + a couple of populated keys.

### Phase 3 — Frontend URL schema + query string (`samplesSearch.ts`)
- Build the zod shape by reducing over the registry: `text`/`existence` →
  `stringArray`/`booleanish`; `range` → `{key}_min` + `{key}_max` coerced
  numbers. Merge with the existing hand-written canonical fields (`q`, `sort`,
  `order`, `limit`, `offset`).
- `buildSamplesQueryString` reducer over the registry (addMany / addOne / range
  bounds). Keep the existing manual fields.
- **Remove the dead params** while here: `voxel_spacing_min/max` and
  `n_tilts_min/max` from the zod schema, the query-string builder,
  `LandingFilterState`, and the `SamplesBrowser` chip list — none reach a live
  backend param today. (Voxel filtering is dropped entirely per Phase 1; if it
  returns later it does so as `voxel_size_*` to match the backend.)
- Test: round-trip a populated `SamplesSearchParams` through build → parse.

### Phase 4 — Filter UI shell
New components under `frontend/src/components/landing/filters/`:
- `FilterSection` — top-level collapsible (MUI `Accordion`, `defaultExpanded`),
  title "Sample properties" / "Acquisition properties".
- `FilterGroup` — group title row + `IconButton` (`UnfoldMore`/`UnfoldLess`)
  that expands/collapses all member properties; accepts `disabled`.
- `FilterProperty` — per-field `Accordion`, **collapsed by default**, controlled
  (so the group's expand-all works). Renders by `kind`:
  - text → `Checkbox` list over `options.categorical[key]` (multi-select)
  - range → `MinMaxRow` (reuse)
  - boolean → `RadioGroup` (Yes / No / Any)
  - existence → single `Checkbox` ("Has …")
- `FilterPanel` — iterates the registry/groups, lays out both sections, owns
  UI-only expand state (`Record<fieldKey, boolean>` + per-section + per-group),
  takes `values`, `options`, `onChange(patch)`, `disabledGroups`, `lockedDataSource`.
- Replaces `LandingFilters` / `AllDataFilters` body; rendered identically in the
  desktop sidebar and the mobile `Drawer`.
- Styling matches the reference image: borderless rows, plus/minus expander per
  property, bold group titles.

### Phase 5 — Gating (data_source + project)
The auto-select still happens in the browser's `patch` handler wrapper (it
navigates), but the user-facing notice is **derived state, not an imperative
dismissable alert** — extend the existing `armWarnings` pattern (a pure
function of current filter state) so there is no separate dismissal state to
track and the notice clears automatically when the condition no longer holds.
- **Disable:** group `appliesTo === 'experimental'` disabled when
  `data_source === 'simulation'`, and vice-versa; chromatin
  (`requiresProject: 'chromatin'`) disabled when `project` ∈ {synapse, nanogold}.
- **Auto-select:** setting a field whose group is
  `appliesTo: 'experimental'|'simulation'` while `data_source` is unset → also
  set `data_source` (the derived notice explains why it was set). Setting a
  chromatin field while `project` is unset → also set `project=['chromatin']`.
- On `/experimental` and `/md-simulation`, `data_source` is **locked** to the
  route's arm: hide the `data_source` property and pre-disable the opposite
  arm's groups (`lockedDataSource` prop). On `/data` it is user-selectable.
- Reuse the existing inline-notice placement near the table in both browsers;
  generalize `armWarnings` to cover the data_source/project derivations.

### Phase 6 — Acquisition subtable
- `frontend/src/utils/acquisitionMatch.ts`: `matchAcquisition(acq, filters)`
  predicate mirroring the backend acquisition `EXISTS` (scalar IN/range/boolean
  + nested existence over `tilt_series` / `raw_tomogram` /
  `post_processed_tomograms` / `annotations`). `// ponytail:` comment noting it
  duplicates `samples.py` semantics.
- **Sync enforcement:** a single shared test-vector fixture
  (`tests/fixtures/acquisition_match_cases.json`: `[{acq, filters, expected}]`)
  consumed by **both** the pytest backend test and the vitest
  `matchAcquisition` test, so the two implementations are checked against the
  same cases and can't silently drift. This replaces "keep the two in sync by
  comment" as the actual guard.
- `AcquisitionsSubTable` takes the active acquisition filters, filters
  `data.acquisitions` through the predicate, and shows "X of Y acquisitions".
  Empty-result note: a sample only reaches the list if the server found ≥1
  matching acquisition, so a "0 of N" subtable means the two predicates have
  drifted — surface it as a visible dev signal rather than a silently empty
  table (ties to the shared fixture above).
- `SamplesPortalTable` gains `expandAllDetails?: boolean` → MRT
  `state.expanded = true`; the browser sets it true when any acquisition-entity
  filter is active (derived from the registry). Gate this on the **committed**
  (debounced) filter state, not raw keystrokes, so range-input typing doesn't
  thrash expansions. Fetch cost is bounded by pagination (≤ `pageSize` ≈ 10
  detail fetches per page, re-fetched on page change) — acceptable; documented
  here so it isn't a surprise.
- Test: `matchAcquisition` unit test driven by the shared fixture, covering each
  kind + a no-match case.

### Phase 7 — Polish
- Active-filter chips / "Filtered by" summary generalized over the registry
  (label + value), `Reset`, count badge on the mobile Filters button.
- a11y: each property accordion labelled; radio/checkbox groups have legends.
- "Showing X of Y" unchanged.

---

## Files touched

**Backend**
- `src/catalog/api/filter_fields.py` *(new)*
- `src/catalog/api/routes/samples.py`
- `src/catalog/api/routes/filters.py`
- `src/catalog/api/schemas.py` (`FiltersOptionsOut`)
- `tests/catalog/test_filter_fields_drift.py` *(new)*, plus samples/filters tests
- `tests/fixtures/acquisition_match_cases.json` *(new — shared by Python + TS predicate tests)*

**Frontend**
- `src/utils/filterFields.ts` *(new)*
- `src/utils/samplesSearch.ts`
- `src/utils/acquisitionMatch.ts` *(new)*
- `src/types.ts` (`FiltersOptionsOut`)
- `src/components/landing/filters/*` *(new: FilterSection/Group/Property/Panel)*
- `src/components/landing/LandingFilters.tsx`, `AllDataFilters.tsx` (slim to wrappers or remove)
- `src/components/landing/AllDataBrowser.tsx`, `SamplesBrowser.tsx` (state, gating, derived notices, expand-all; remove dead voxel/n_tilts wiring)
- `src/components/landing/SamplesPortalTable.tsx`, `AcquisitionsSubTable.tsx`

---

## Resolved decisions (2026-06-29)

1. **`linker_pattern`, `nucleosome_footprint`, `label.aunp_size_nm`** →
   **data-derived categorical checkbox facet**. Options come from `SELECT
   DISTINCT col`; the filter matches `col IN (...)` against those exact stored
   strings, so the match is byte-identical by construction — no canonicalization,
   no `json_each`, no dialect risk, and the facet self-populates from whatever
   researchers author. Whole-value match only (not per-element); `aunp_size_nm`
   is a pick-list, not a range. `// ponytail:` upgrade path — swap a single
   field to `json_each` / range once real data shows it's needed. *(Chosen over
   `json_each`/range because the real data shape is still unknown; this is the
   most flexible option while we wait to see how the data is authored.)*
2. **`voltage`** → multi-select **checkboxes** (discrete kV, existing param).
3. **`date_collected`** → **excluded**.
4. **`acquisition_quality`** (1–5) → **checkboxes** (1–5).
5. **`defocus_range`** → free-text **checkbox** facet (not a numeric range).
6. **Predicate duplication** accepted, but guarded by a **shared test-vector
   fixture** consumed by both the Python and TS test suites (Phase 6), not just
   a `// ponytail:` comment.
7. **Voxel range, `has_tomograms`, `has_warnings`, `n_tilts` filters removed.**
   They don't fit the `table.column` registry and are retired: voxel range
   dropped (frontend `voxel_spacing_*` was already dead — never matched the
   backend `voxel_size_*`); `has_tomograms` superseded by the registry's
   `has_raw_tomogram` / `has_post_processed_tomogram`; `has_warnings` dropped
   (backend-only, never surfaced); `n_tilts_*` dropped (dead frontend-only).
   Dead frontend wiring removed in Phase 3.
8. **Registry kept in sync by hand-mirror + drift test**, not codegen — this
   repo has no cross-language build step and `types.ts` already hand-mirrors
   `schemas.py`. The drift test checks both Python↔ORM and TS↔Python parity.
9. **Label 1:N matching is per-row:** all checked label facets must hold on the
   same label, consistent with the acquisition rule.
10. **Gating notice is derived state**, not an imperative dismissable alert —
    extend the existing `armWarnings` pattern (clears automatically, no
    dismissal state).
