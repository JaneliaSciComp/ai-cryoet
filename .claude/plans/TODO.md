# TODO — Dashboard MVP

Source: `.claude/plans/2026-05-08-dashboard-mvp.md`

Execution mode: **stop after each phase for manual review**.

---

## Phase 0 — Frontend foundation prove-out  ✅
- [x] Add `apiFetch(path, init)` that switches base URL: SSR reads `process.env.CRYOET_API_BASE_URL` (default `http://localhost:8000`); browser uses `/api`. Lives at `frontend/src/utils/api.ts`.
- [x] Convert `frontend/src/routes/samples.tsx` to `loader: ensureQueryData` + component: `useSuspenseQuery`. Query options + `SampleSummary` type extracted to `frontend/src/hooks/useSamples.ts` (per agreed structure).
- [x] Devtools surfaced via the **TanStack Query browser extension**: `router.tsx` exposes `queryClient` on `window.__TANSTACK_QUERY_CLIENT__` (browser-only). The lazy floating-button setup was removed — the user prefers the extension since the floating button has historically not rendered for them.
- [x] **Frontend directory restructure** (agreed before Phase 1): no separate `api/` folder. Final layout:
  - `src/assets/`, `src/components/` (split by feature later), `src/hooks/` (queries live here, types co-located), `src/routes/`, `src/styles/` (renamed from `setup/`; now also holds `index.css`), `src/utils/` (helpers including `api.ts`).
  - `src/setup/` and `src/api/` directories removed.
  - `Counter.tsx` deleted (TanStack scaffold cruft); `CustomLink.tsx` and `CustomButtonLink.tsx` kept (former is used by Header; latter retained pending later cleanup).
- [x] Hydration-blocking bug fixed: `client.tsx` was using the old `@tanstack/react-start` API (`StartClient` from the package root with a `router` prop). The current API exports `StartClient` from `@tanstack/react-start/client` parameterless — it invokes `getRouter()` internally via a Vite alias and handles hydration itself. Without this fix the SyntaxError at hydration meant nothing on the client side ran and `window.__TANSTACK_QUERY_CLIENT__` stayed undefined.
- [x] Demo: `/samples` renders, queries appear in the TanStack Query browser-extension panel, no console errors after a hard reload. — **confirmed by user 2026-05-08**

## Phase 1 — Schema + Alembic  ✅
(See main plan)

## Phase 2 — Parsers  ✅
(See main plan)

## Phase 3 — API: read endpoints  ✅
(See main plan)

## Phase 4 — API: rendering + Neuroglancer  ✅
(See main plan)

## Phase 4.5 — Real-data integration checkpoint  ✅
(See main plan)

## Phase 4.6 — Gouauxlab per-tilt MDOC parser fix  ✅
(See main plan)

## Phase 5 — Frontend infrastructure  ✅
(See main plan)

---

## Phase 6 — Frontend home + scans

### 6.1 Add `@mui/x-data-grid` dependency
- [x] Add `@mui/x-data-grid` to `frontend/package.json` (compatible with `@mui/material@6.4.7` — use `^7.x`). — already present (`^7.29.13`); no change needed.
- [x] Run `npm install` in `frontend/`. — already installed in node_modules.

### 6.2 New data hooks
- [x] `frontend/src/hooks/useStatsOverview.ts` — `queryOptions(['stats','overview'])` → `apiFetch<StatsOverviewOut>('/stats/overview')`; export `useStatsOverviewQuery()`.
- [x] `frontend/src/hooks/useLatestScan.ts` — `queryOptions(['scans','latest'])` → `apiFetch<ScanOut | null>('/scans/latest')`. Must tolerate 404 ("no completed scan") → return null. Implement with a wrapper that catches the 404 response specifically.
- [x] `frontend/src/hooks/useScans.ts` — `queryOptions(['scans','list'])` → `apiFetch<ScanOut[]>('/scans')`; export `useScansQuery()`.

### 6.3 Home page rewrite (`frontend/src/routes/index.tsx`)
- [x] Replace placeholder content. Loader pre-fetches stats + latest-scan in parallel via `Promise.all([queryClient.ensureQueryData(statsOpts), queryClient.ensureQueryData(latestScanOpts)])`.
- [x] Sections, top to bottom:
  - Page title `CryoET Catalog`.
  - **Project Summary** row: `Grid` of `ProjectSummaryCard`s — one per `stats.by_project`.
  - **Totals** row: `Grid` of `StatCard`s — samples / acquisitions / tilt series / tomograms / annotations.
  - **Browse** row: outlined `Button` links to `/samples` and `/scans`.
  - **Last scan**: inline status — show `started_at` / `ended_at` (formatted dates) + status chip + link to `/scans`. If no completed scan, show "No scans yet."
- [x] Use `<Link>` from `@tanstack/react-router` for the Browse buttons (component prop).
- [x] Format timestamps via `new Date(seconds * 1000).toLocaleString()` — scan times are unix seconds (number).
- [x] Format bytes inline (or reuse the existing `formatBytes` helper in `ProjectSummaryCard.tsx` — extract to a shared `frontend/src/utils/format.ts` if it ends up needed in two more places, otherwise leave it). — reused via `ProjectSummaryCard`; no extraction needed yet.

### 6.4 New `/scans` route (`frontend/src/routes/scans.tsx`)
- [x] `createFileRoute('/scans')` with loader pre-fetching via `useScansQuery`.
- [x] `DataGrid` columns:
  - `started_at` (date, sortable, default sort desc)
  - `ended_at` (date, blank if null)
  - `root` (string, truncated with title attribute) — used MUI `Tooltip` + ellipsis Box rather than a raw `title` attribute for a better UX.
  - `status` (string with chip: running=warning, completed=success, failed=error — render via `renderCell`)
  - `samples_upserted` (number)
  - `samples_skipped` (number)
  - `samples_failed` (number)
- [x] `density="compact"` (plan §9.7 — small density for tables).
- [x] Refresh button (header) calls `queryClient.invalidateQueries(['scans','list'])`. No polling (decision §11.21).
- [x] Use `getRowId={(row) => row.scan_run_id}`.

### 6.5 Validation
- [x] `npm run build` clean (runs `vite build && tsc --noEmit`). — Vite build clean; tsc reports only pre-existing errors in `src/ssr.tsx` unrelated to Phase 6 (verified by reverting Phase 6 changes and seeing identical errors).
- [ ] Smoke: `/` shows stats + project cards + "Last scan" inline; `/scans` shows the history table; Refresh button re-fetches. — manual smoke deferred to reviewer.

---

## Phase 7 — Frontend CryoET browser

### 7.1 Restructure `/samples` to a layout route with nested detail

Goal: `/samples` becomes a layout route showing the filter drawer + table; `/samples/$sampleId` opens the same page with the right pane populated by sample detail.

- [x] Move existing logic out of `frontend/src/routes/samples.tsx`. Convert it to a **layout route** (`<Outlet />` only — owns the AppShell + Splitter + filter drawer + table).
- [x] New `frontend/src/routes/samples/index.tsx` — empty-state placeholder for the right pane (no sample selected).
- [x] New `frontend/src/routes/samples/$sampleId.tsx` — loads `/samples/{id}` and renders `SampleDetailPanel`.
- [x] Update `samplesSearchSchema` / `SamplesSearchParams` export path so child routes can import (keep co-located with layout route). — **Deviation:** moved schema + type + `buildSamplesQueryString` to `frontend/src/utils/samplesSearch.ts` (instead of co-locating with the layout route) to avoid a circular import between `useSamples.ts` and `routes/samples.tsx`. `FilterDrawer` import updated.
- [x] Verify `routeTree.gen.ts` regenerates correctly (TanStack Router auto-regenerates via vite plugin in dev). — Regenerated automatically on `vite build`; both `/samples/$sampleId` and `/samples/` (index) appear as nested children of `/samples`.

### 7.2 Extend `useSamples.ts` for filters
- [x] Replace single static `samplesQueryOptions` with `samplesQueryOptions(params: SamplesSearchParams)` — query key includes serialized params; query fn builds URLSearchParams (repeatable for arrays) and appends to `/samples`.
- [x] Export `useSamplesQuery(params)` using `useSuspenseQuery`.
- [x] Update the layout route loader to call `samplesQueryOptions(deps.search)` via `loaderDeps: ({ search }) => ({ search })`.

### 7.3 New data hooks
- [x] `frontend/src/hooks/useSampleDetail.ts` — `sampleDetailQueryOptions(sampleId)` → `apiFetch<SampleDetail>('/samples/${id}')`; `useSampleDetailQuery(id)`.
- [x] `frontend/src/hooks/useSampleWarnings.ts` — `sampleWarningsQueryOptions(id)` → `apiFetch<WarningOut[]>('/samples/${id}/warnings')`; `useSampleWarningsQuery(id)`.
- [x] `frontend/src/hooks/useFiltersOptions.ts` — `filtersOptionsQueryOptions` → `apiFetch<FiltersOptionsOut>('/filters/options')`; `useFiltersOptionsQuery()`.

### 7.4 Samples layout route (`frontend/src/routes/samples.tsx`)
- [x] Replace plain-HTML table with `AppShell` (drawer = `FilterDrawer`) wrapping `Splitter` (left = `SamplesTable`, right = `<Outlet />`).
- [x] Drawer open state in local React state (default true on desktop).
- [x] Filter drawer wired: initial state derived from search params on mount; `onChange` calls `router.navigate({ search: { ...minimalParams } })` for URL-canonical params **only** (project, data_source, q, sort, order, limit, offset) so URLs stay minimal (§11.19). Drawer state for extended fields stays local; URL doesn't get pushed back.
- [x] `onCopyUrl(params)` serializes ALL drawer fields into URL + copies via `navigator.clipboard.writeText(window.location.origin + window.location.pathname + '?' + qs)`. — **Deviation from container hint:** chose `position: fixed; top: 64; left/right/bottom: 0` to break out of the root `<Container>` (cleanest; doesn't require negotiating Container max-width + paddings).

### 7.5 `SamplesTable` (`frontend/src/components/samples/SamplesTable.tsx`)
- [x] `DataGrid` keyed by `sample_id` (`getRowId={(row) => row.sample_id}`).
- [x] Columns: Project, Sample, Type, Acquisitions, Tilt series, Tomograms, Warnings.
- [x] Controlled single-row selection (`rowSelectionModel`); on change, `router.navigate({ to: '/samples/$sampleId', params: { sampleId }, search: (prev) => prev })`.
- [x] Highlight current row from `useParams({ from: '/samples/$sampleId', shouldThrow: false })` or `useMatch`.
- [x] `density="compact"` (plan §9.7).

### 7.6 `SampleDetailPanel` (`frontend/src/components/samples/SampleDetailPanel.tsx`)
- [x] Takes `sampleId: string` prop. Uses `useSampleDetailQuery(sampleId)` + `useSampleWarningsQuery(sampleId)`.
- [x] Renders: `SampleHeader` → `WarningList` → `SubEntityBlock`s → `AcquisitionCard`s.
- [x] Each `AcquisitionCard` renders its acquisition + nested `TiltSeriesCard`s + `TomogramCard`s + `AnnotationList`.

### 7.7 `SampleHeader` (`frontend/src/components/samples/SampleHeader.tsx`)
- [x] Title: `{project} / {sample_id}`.
- [x] Type chip + warning-count chip (warning-count via prop; parent passes from warnings query).

### 7.8 `SubEntityBlock` (`frontend/src/components/samples/SubEntityBlock.tsx`)
- [x] Generic block: takes `title` + `entries: Array<[label, value]>` (skipping null / undefined entries). Render as a definition list (`<Stack>` of label/value rows). For array values (e.g. `linker_pattern`, `zarr_scale`), render as a space-joined string.
- [x] Don't render anything if no entries.

### 7.9 `AcquisitionCard` (`frontend/src/components/samples/AcquisitionCard.tsx`)
- [x] `Card` with header = `acquisition_id`.
- [x] Key/value table: resolution, microscope, voltage, camera, pixel_size, path (with `CopyButton`).
- [x] Inside the card, render: `TiltSeriesCard` (per `tilt_series`), `TomogramCard` (per `tomograms`), `AnnotationList`.

### 7.10 `AnnotationList` (`frontend/src/components/samples/AnnotationList.tsx`)
- [x] List of annotations with badge chip for type, files listed below.
- [x] Empty → return null (parent decides whether to render an empty header).

### 7.11 `WarningList` (`frontend/src/components/samples/WarningList.tsx`)
- [x] Collapsible (MUI `Accordion`) with header showing count; collapsed by default if count > 0; hidden entirely if count is 0.
- [x] Each warning row: category chip + location + message.

### 7.12 `TomogramCard` (`frontend/src/components/samples/TomogramCard.tsx`)
- [x] Header: `tomogram_id`.
- [x] Metadata: shape (`{x}×{y}×{z}`), voxel spacing (Å), pipeline / software, MRC + zarr paths (with `CopyButton`), size (formatted bytes).
- [x] `<img loading="lazy" src="/api/tomograms/{sample_id}/{acquisition_id}/{tomogram_id}/preview.png">` wrapped in `LoadingSkeleton variant="image"` until loaded (use `onLoad`). On click → `Lightbox`. Add `onError` fallback that shows an `EmptyState` with "Preview unavailable". — Used a `Skeleton` overlay (positioned absolute) directly rather than the `LoadingSkeleton` wrapper component so the placeholder can vanish on `onLoad` without re-mounting the `<img>`.
- [x] `NeuroglancerButton launchPath={`/tomograms/${sample_id}/${acquisition_id}/${tomogram_id}/neuroglancer`}`.

### 7.13 `TiltSeriesCard` (`frontend/src/components/samples/TiltSeriesCard.tsx`)
- [x] Header: `tilt_series_id` + `NeuroglancerButton launchPath={`/tilt-series/${sample_id}/${acquisition_id}/${tilt_series_id}/neuroglancer`}`.
- [x] Metadata row: n_tilts, tilt range, voltage, pixel size, image format, microscope, camera, file size (if applicable — note `size_bytes` isn't on TiltSeriesOut so skip that field unless we add it).
- [x] Two-column grid:
  - Left: polar plot `<img src="/api/tilt-series/{...}/polar.png">` (click → Lightbox). `onError` → empty state.
  - Right: median-tilt preview `<img loading="lazy" src="/api/tilt-series/{...}/preview.png">` (click → Lightbox). `onError` → empty state.

### 7.14 Validation
- [x] `npm run build` clean. — Vite build succeeds and `tsc --noEmit` is clean for all Phase 7 code. Only remaining `tsc` errors are in `src/ssr.tsx` (pre-existing, unrelated to Phase 7 — verified by running `tsc` on a stash of the prior state, same two errors appear).
- [ ] Smoke: drawer filters update table; selecting a row navigates to `/samples/$sampleId`; detail panel renders header / warnings / sub-entities / acquisition cards / tilt-series cards / tomogram cards; lightbox opens on image click. — Requires manual browser verification (deferred to reviewer).

---

## Phase 8 — Polish (NOT in scope for this run)

(See main plan)
