# Plan: Show tilt-series polar plots in the acquisition detail UI

**Date:** 2026-06-08
**Status:** Ready for implementation (open questions resolved)
**Author:** planning session (Claude)

## Summary

Surface the tilt-angle **polar plot** (the same semicircular plot
`aicryoet-tools` renders for each tilt series) in this app's acquisition detail
page. The plot draws a radial line per tilt image, colored by acquisition order
on a viridis scale, over a 0°→180° semicircle.

**Key finding: the backend already exists.** The polar render pipeline is fully
built and tested — this is a **frontend-only** task. Specifically:

- `cryoet_catalog/imaging/_polar.py` — `render_polar_png(angles) -> bytes`,
  matplotlib OO API, `POLAR_RENDER_VERSION` for cache-key versioning.
- `cryoet_catalog/api/routes/tilt_series.py:153-186` — the
  `GET /tilt-series/{sample_id}/{acquisition_id}/{tilt_series_id}/polar.png`
  endpoint. It reads the already-stored `tilt_angles`, renders **off the event
  loop** via `run_in_threadpool`, and memoizes with an `@lru_cache(maxsize=128)`
  keyed on `(ids, mtime, version, angles_tuple)`. Returns **422** when the row
  has no cached angles (e.g. EER-only series whose mdoc wasn't parsed).
- `TiltSeriesORM.tilt_angles` (`orm.py:371`, JSON column) and
  `cryoet_schema.schema.TiltSeries.tilt_angles` (`schema.py:328`) already
  persist the full per-image angle list at scan time, so the endpoint never
  re-parses the MDOC.

The frontend currently references neither `polar.png` nor `preview.png`; tilt
series appear only as counts. The acquisition detail page
(`acquisitions.$acquisitionId.tsx:117-124`) has a single grey **"Tilt series"**
`ThumbnailPlaceholder` hero slot that this plan fills.

## Resolved decisions

1. **Render on the fly — no filesystem cache.** (User's original question.)
   The tomogram-thumbnail filesystem cache
   (`.claude/plans/2026-06-05-tomogram-thumbnail-cache.md`) exists to avoid
   re-**decoding large MRC volumes** every request. The polar plot has no such
   expensive step: its input (`tilt_angles`) is a ~120-float JSON list already
   in the DB, and rendering is a sub-100ms matplotlib draw that is already
   threadpool-offloaded and LRU-cached in-process. Pre-baking polar PNGs into
   `CATALOG_THUMBNAIL_DIR` would add scanner generation, a serving path, and
   cache invalidation/heal logic to save a cost that is already negligible. The
   only thing on-the-fly forgoes is survival across API restarts, and the LRU
   re-warms cheaply. **Keep the existing endpoint as-is.**

2. **Display: single hero, first tilt series.** Fill the existing
   `acquisitions.$acquisitionId.tsx:118` placeholder with the polar plot of
   `acquisition.tilt_series[0]`. An acquisition can have multiple tilt series
   (`AcquisitionOut.tilt_series` is an array), but per the user we show only the
   first/representative one in the hero. If the array is empty, keep the
   placeholder.

## Non-goals

- **No filesystem caching of polar PNGs** (decision 1).
- **No tilt-series median *preview image*** (the `/preview.png` endpoint that
  decodes zarr/TIFF/MRC frames). That endpoint *does* have a tomogram-like
  expensive-decode profile and would be the candidate for the thumbnail cache —
  but it is out of scope here; this task is the polar plot only.
- **No per-tilt-series table or thumbnail strip** for the additional tilt series
  (deferred; the data shape supports it later — see Follow-ups).
- **No backend, ORM, schema, scanner, or `TiltSeriesOut` API changes.** The
  endpoint renders server-side from `tilt_angles`; the frontend does not need
  the raw angles, so `tilt_angles` stays out of `TiltSeriesOut`.

## Implementation steps

### Step 1 — Frontend URL helper

In `frontend/src/components/common/Thumbnail.tsx` (next to the existing
`tomogramThumbnailUrl` / `thumbnailUrl` helpers, ~line 146), add:

```ts
// Server renders the polar plot from cached tilt_angles; 422 when none.
// Route prefix is /tilt-series (api/main.py:211); frontend proxies under /api.
export function tiltSeriesPolarUrl(s: string, a: string, ts: string): string {
  const enc = (x: string) => x.split('/').map(encodeURIComponent).join('/')
  return `/api/tilt-series/${enc(s)}/${enc(a)}/${enc(ts)}/polar.png`
}
```

### Step 2 — Let `PreviewThumbnail` not crop the plot

`PreviewThumbnail` (`Thumbnail.tsx:87-141`) hardcodes `objectFit: 'cover'`,
which is right for the square-ish tomogram slices but would **crop** the polar
plot (a wide ~5:3 informational chart). Add an optional prop so the hero can
request `contain`:

```ts
export function PreviewThumbnail(props: {
  src?: string | null
  alt?: string
  width?: Size
  height?: Size
  clickable?: boolean
  tooltipTitle?: string
  objectFit?: 'cover' | 'contain'   // NEW, default 'cover'
}) {
  const { /* …, */ objectFit = 'cover' } = props
  // …in the <Box component="img"> sx: objectFit,  (replace the literal 'cover')
}
```

Existing call sites are unaffected (default stays `'cover'`). The lightbox
already uses `contain`.

### Step 3 — Fill the hero on the acquisition detail page

`frontend/src/routes/acquisitions.$acquisitionId.tsx`:

- Import `PreviewThumbnail` and `tiltSeriesPolarUrl` (keep `ThumbnailPlaceholder`
  import for the fallback, plus the `LayersOutlinedIcon`).
- Replace the placeholder block at lines **117-124** with logic that picks the
  first tilt series and renders its polar plot, falling back to the existing
  labeled placeholder when there are no tilt series:

```tsx
{(() => {
  const ts = acquisition.tilt_series[0]
  const polarSrc = ts
    ? tiltSeriesPolarUrl(sampleId, acquisitionId, ts.tilt_series_id)
    : null
  // No tilt series at all → keep the labeled placeholder.
  // Has a series but no cached angles → polar.png 422s → PreviewThumbnail's
  // onError swaps in the (unlabeled) placeholder automatically.
  return polarSrc ? (
    <PreviewThumbnail
      src={polarSrc}
      alt={`Tilt-angle plot for ${ts.tilt_series_id}`}
      width="100%"
      height={220}
      objectFit="contain"
      clickable
      tooltipTitle="Click to enlarge tilt-angle plot"
    />
  ) : (
    <ThumbnailPlaceholder
      width="100%"
      height={220}
      icon={<LayersOutlinedIcon />}
      label="Tilt series"
    />
  )
})()}
```

Notes:
- `sampleId` and `acquisitionId` are already in scope (`Route.useSearch()` /
  `Route.useParams()`); `acquisition` is the resolved `AcquisitionOut`.
- The **422 → placeholder** path is automatic via `PreviewThumbnail`'s `onError`
  (`Thumbnail.tsx:108`), so no need to pre-check whether angles exist. Tradeoff:
  a series with no angles falls back to the *unlabeled* placeholder rather than
  the "Tilt series" labeled one. Acceptable; if the labeled box is preferred for
  that case too, we'd need the angle count surfaced in `TiltSeriesOut` (a
  backend change we're explicitly avoiding) — so leave as-is.
- `clickable` opens the existing `ThumbnailLightbox` (renders at `contain`),
  giving a full-size view of the plot.

## Tests

- **Backend:** none. Endpoint + renderer are already covered by
  `tests/cryoet_catalog/test_api_tilt_series.py` (polar 200 / 422) and the
  imaging tests. Re-run to confirm nothing regressed:
  `pixi run -e api pytest tests/cryoet_catalog/test_api_tilt_series.py`.
- **Frontend:** if the Vitest + Testing Library harness used for
  `NeuroglancerButton` covers route components, add a test asserting:
  - acquisition with ≥1 tilt series → an `<img>` whose `src` matches
    `/api/tilt-series/{s}/{a}/{ts}/polar.png` for `tilt_series[0]`;
  - acquisition with empty `tilt_series` → the labeled "Tilt series"
    placeholder (no `<img>`);
  - `onError` on the img → placeholder (mirrors the existing
    `PreviewThumbnail` fallback behavior).
  Confirm the harness can render a TanStack route component; if not, verify
  manually in the running app.
- **Manual:** load an acquisition known to have parsed MDOC angles (rosenlab
  series-level or gouauxlab per-tilt) and confirm the plot renders un-cropped in
  the hero and enlarges in the lightbox; load an EER-only / angle-less series and
  confirm graceful fallback.

## Risks & mitigations

- **Aspect-ratio crop.** The polar PNG is wider than the 220px-tall hero;
  mitigated by the new `objectFit="contain"` (Step 2). The plot already includes
  its own title + colorbar, so letterboxing inside the hero is fine.
- **422 fallback loses the label.** Documented in Step 3; avoiding it would
  require a backend field we're not adding.
- **Render cost under load.** Already mitigated upstream (threadpool +
  `lru_cache(128)`); no action. If a future page renders *many* polar plots at
  once (e.g. a per-series table), revisit cache sizing then — not now.

## Follow-ups (non-blocking)

- Per-tilt-series table/cards for acquisitions with multiple series (polar plot +
  `n_tilts` / `tilt_range_*` / `tilt_axis_angle` metadata), reusing
  `tiltSeriesPolarUrl`.
- If the tilt-series **median preview image** (`/preview.png`) is later surfaced
  in the UI, evaluate pre-baking *that* into the `CATALOG_THUMBNAIL_DIR`
  filesystem cache — it shares the tomogram expensive-decode profile that
  motivated that cache, unlike the polar plot.
