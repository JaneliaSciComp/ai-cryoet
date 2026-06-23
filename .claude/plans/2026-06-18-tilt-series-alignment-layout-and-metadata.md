# Tilt-series / alignment layout + metadata restructure

**Branch:** `update-tilt-series-alignment-layout-and-metadata`
**Date:** 2026-06-18
**Status:** Draft for review (no code written yet)

## Motivation

From the Slack discussion (schneiderm2): formalize the
**Frames (+Gains) → TiltSeries → [+ Alignment] → Tomogram** chain, and stop
treating alignment as a separate top-level concept.

- A tilt series can be stored raw/unaligned or already geometrically
  transformed — surface that via an `is_aligned` flag.
- Alignment is "purely transformation parameters," so fold it **into** the
  tilt series rather than carrying a parallel `Alignments/` tree.
- A tilt series may be `derived_from` either `Frames` or another tilt series.
- New on-disk shape:

  ```
  TiltSeries/
  └── {ts_id}/
      ├── stack/             # the .mrc projection stack (+ .zarr / .rawtlt); MAY be empty
      └── alignment/
          └── alignment.json # affine matrix + interpolation recipe
  ```

- Per-series metadata is a `[[tilt_series]]` block in `acquisition.toml` (NOT a
  per-folder `tiltseries.toml`).

## Locked-in decisions (from clarifying questions)

1. **Tomograms reference `tilt_series_id`** (not `alignment_id`). The
   `Alignment` entity and `[[alignment]]` block are removed; alignment metadata
   (`is_aligned`, `alignment_software`, `alignment_method`) lives on the tilt
   series.
2. The quality score **stays at the acquisition level** (it characterizes the
   raw tilt series — alignability + projection-image survival — of which there
   is one per acquisition, per the CZI rubric). It is **renamed
   `tilt_series_quality_score` → `raw_tilt_series_quality`** and its rubric
   reworded to include the alignability / projection-image language. It does
   **not** go on `[[tilt_series]]`.
3. **Unify, polar plot → acquisition.** The researcher-authored stack folder IS
   the single `TiltSeries` entity. The MDOC-derived **geometry moves off the
   tilt-series entity onto the `Acquisition`** (the MDOC stays in `Frames/` and
   already describes the acquisition's tilt scheme, shared by all its tilt
   series). The polar plot becomes **acquisition-level**. The old per-MDOC
   tilt-series *derivation* (one row per MDOC stem) is retired.
4. **Migration scope — all in one branch/PR (Phases A–D).** Example data
   (`data/Experimental/rosenlab_1210_example30bp/`) **and** all catalog fixtures
   migrate to the new `TiltSeries/{ts_id}/{stack,alignment}/` layout *within this
   same branch*. The schema change is destructive (ORM column rewrites,
   `test_orm_drift`, and `test_repo_consistency` enforces template/fixture match),
   so splitting contract from fixtures would leave `main` red between PRs.
   Phases A–D land together; tests stay green at merge. (Resolves open question
   #4.)
5. **Route shape — polar→acquisition; preview/neuroglancer stay per-series with a
   Frames fallback.**
   - **Polar** moves to a new acquisition-level endpoint
     (`/acquisitions/{sample}/{acq}/polar.png`) reading `Acquisition.tilt_angles`;
     the per-series `/tilt-series/.../polar.png` is removed.
   - **Preview + neuroglancer** stay keyed per `tilt_series_id` and re-point to
     the authored stack (`{ts_id}/stack/` → `zarr_path`/`st_path`). When a series
     has **no** stack artifact, both fall back to the **acquisition-level
     `Frames/`** images (raw frames) so previews/viewers still render. This keeps
     each raw-vs-aligned series individually viewable. Note: `mdoc_path` is
     dropped from `TiltSeries`, so the Frames fallback must resolve the
     acquisition's frames dir from the `Acquisition` (not the tilt-series row).
     (Resolves open question #5.)

## Current state (today)

- **`schema.py`**
  - `Acquisition.tilt_series_quality_score`; MDOC fields `tilt_min`,
    `tilt_max`, `tilt_axis`, `voltage`, `pixel_size`, `frame_count`, … but
    **no full `tilt_angles` list**.
  - `TiltSeries` — composite-PK child, **scanner-derived only** (keyed by MDOC
    stem; geometry: `n_tilts`, `tilt_range_*`, `tilt_axis_angle`, `voltage`,
    `pixel_spacing`, `image_format`, `tilt_angles`, `mdoc_path`/`st_path`/
    `zarr_path`, `mtime`). Powers the per-series polar plot via its
    `tilt_angles`.
  - `Alignment` — `[[alignment]]` block. **Not wired to the DB**: no
    `AlignmentORM`, not in `test_orm_drift.MAPPING`, not in `persistence.py` or
    the API. Lives only in `schema.py` + `loader.py`. → removal is mostly
    self-contained.
  - `RawTomogram.alignment_id` / `PostProcessedTomogram.alignment_id`;
    `AcquisitionFile.alignment` + `_check_cross_refs` alignment validation.
- **`TiltSeries` IS fully wired**: `TiltSeriesORM`, drift `MAPPING`,
  `persistence.py` (upsert + soft-delete), API
  `/tilt-series/{sample}/{acq}/{ts}/...` (preview + polar + neuroglancer),
  `api/schemas.py`, `frontend/src/types.ts`. The assembler **overwrites** any
  authored `tilt_series` with parser output (`assembler.py:317`).
- **Directory / docs / example data** use flat `TiltSeries/` +
  `Alignments/{alignment_id}/`; MDOCs in `Frames/`.
- **Templates**: canonical `templates/acquisition.toml` still has the OLD
  `[[alignment]]` block + acquisition-level score. User edited the *starter
  copy* toward the new shape — must move to canonical + sync.

### Corrections needed in the user's draft `acquisition.toml` edits
1. Edit belongs in **canonical** `templates/acquisition.toml` (`sync_templates`
   fans out; `test_repo_consistency` enforces match).
2. Tomogram blocks still say `alignment_id` → `tilt_series_id`.
3. "HOW TO USE" header still describes the `[[alignment]]` flow.
4. Typos: "tile series" → "tilt series".

## Target model

### `Acquisition` (gains the tilt scheme + polar-plot source)
- Keep existing MDOC fields (`tilt_min`/`tilt_max`/`tilt_axis`/`voltage`/
  `pixel_size`/`frame_count`).
- **Add `tilt_angles: list[float] | None`** — full per-image angle list parsed
  from the `Frames/` MDOC; the acquisition-level polar plot reads this.
  (Decision: keep the full list for fidelity with dose-symmetric / irregular
  schemes rather than reconstructing from min/max/step.)
- **Rename `tilt_series_quality_score` → `raw_tilt_series_quality`** (stays
  acquisition-level; `TiltQuality` 1–5 type unchanged). Rubric reworded:
  ```
  raw_tilt_series_quality  # integer 1-5, author's estimate of the RAW tilt
                           # series (alignability + projection-image survival):
                           #   5 Excellent  reconstructions could be publication-ready
                           #   4 Good       useful for analysis (subtomogram avg, segmentation)
                           #   3 Medium     minor projection images discarded before reconstruction
                           #   2 Marginal   major projection images discarded; usable only after heavy manual work
                           #   1 Low        not alignable / not useful for analysis
  ```

### `TiltSeries` (now researcher-authored; the `.mrc` stack folder)
| field | type | source |
|---|---|---|
| `tilt_series_id` (`id`) | text (PK) | directory ↔ TOML `id` (folder under `TiltSeries/`) |
| `sample_id`, `acquisition_id` | text (FK) | path-injected |
| `derived_from` | text | `"Frames"` OR another `tilt_series_id` in this acq |
| `is_aligned` | bool | TOML |
| `alignment_software` | text | TOML |
| `alignment_method` | text | TOML |
| `st_path` | text | FS (resolved under `{ts_id}/stack/`) |
| `zarr_path` | text | FS (under `{ts_id}/stack/`) |
| `alignment_files` | list[text] | FS (discovered under `{ts_id}/alignment/`) |
| `mtime` | float | FS |

**Dropped from `TiltSeries`** (moved to `Acquisition` or gone): `mdoc_path`,
`n_tilts`, `tilt_range_min`, `tilt_range_max`, `tilt_axis_angle`, `voltage`,
`pixel_spacing`, `image_format`, `tilt_angles`, `microscope`, `camera`.

### Tomograms
`alignment_id` → `tilt_series_id` (validated against the acquisition's
tilt-series ids).

### Removed entirely
`Alignment` model, `[[alignment]]` block, `Alignments/` tree, the per-MDOC
tilt-series derivation (`parse_tilt_series_dir` records/collisions), and warning
categories `tilt_series_id_collision`, `tilt_series_layout_unknown`,
`multiple_tilt_series`. (The quality score is **renamed**, not removed — see
`Acquisition` above.)

## Open questions — all resolved

_All open questions resolved. See Locked-in decisions #4 and #5 (this change)
and #6–#8 below (implemented in commits `15a25eb`/`5a527e8`)._

6. **`stack/` & `alignment/` subfolders are OPTIONAL** (proposal accepted). The
   scanner resolves `st_path`/`zarr_path` under `stack/` and collects
   `alignment_files` under `alignment/` when present; the validator does not
   require them. (`discovery.py:356`.) Resolves old question #1.
7. **`is_aligned` cross-check: warn** (proposal accepted). The assembler emits a
   `tilt_series_alignment_mismatch` warning in **both** directions —
   `is_aligned=true` with no `alignment/` artifacts, and artifacts present but
   `is_aligned` not true. (`assembler.py:329-360`.) Resolves old question #2.
8. **`derived_from` sentinel is the literal `"Frames"`** OR a known
   `tilt_series_id` in the same acquisition; validated in `_check_cross_refs`.
   (`schema.py:437-445`.) Resolves old question #3.

## Phased implementation

### Phase A — Metadata contract (schema + templates + docs)
1. `schema.py`:
   - Remove `Alignment`, `AcquisitionFile.alignment`, alignment cross-ref/dup
     logic.
   - `Acquisition`: add `tilt_angles: list[float] | None`; rename
     `tilt_series_quality_score` → `raw_tilt_series_quality`.
   - `TiltSeries`: add `id` alias + authored fields (`derived_from`,
     `is_aligned`, `alignment_software`, `alignment_method`, `alignment_files`);
     drop the MDOC-geometry fields. (No quality score here.)
   - `RawTomogram`/`PostProcessedTomogram`: `alignment_id` → `tilt_series_id`.
   - `_check_cross_refs`: validate tomogram `tilt_series_id` against
     tilt-series ids; validate `tilt_series.derived_from`; dup tilt-series-id
     check; drop alignment checks.
2. Regenerate `acquisition.schema.json` + `schema.json`; update
   `test_generate_json_schema.py` (quality-score constraint stays on
   `Acquisition`, now under the key `raw_tilt_series_quality`).
3. Canonical `templates/acquisition.toml`: new `[[tilt_series]]` block,
   retargeted tomogram refs, fixed header; `pixi run sync-templates`.
4. Directory skeletons (both `sample_id_experimental` + `sample_id_simulation`):
   `TiltSeries/{ts_id}/{stack,alignment}/.gitkeep`; remove experimental
   `Alignments/`.
5. Docs: `docs/data_organization.md` (diagrams, Gouaux example, folder-naming
   list, `Alignments/` mentions, the quality-score paragraph → rename + reworded
   rubric) and `docs/schema.md` (drop §5 Alignment; rename the acquisition
   quality field → `raw_tilt_series_quality` + reworded rubric; add `tilt_angles`
   to Acquisition table; rewrite §2a tilt-series as authored + note geometry on
   Acquisition; retarget tomogram FK to `tilt_series_id`).

### Phase B — Catalog rewire
6. `loader.py`: drop `alignment` from `_walk_extras` /
   `_format_extras_location`; add `_TILT_SERIES_PARENT_DIRS = ("TiltSeries",)`
   to the id↔folder check.
7. `discovery.py`: add `iter_tilt_series(acq)` over `TiltSeries/{ts_id}/`
   (resolve `stack/`, `alignment/`); keep MDOCs sourced from `Frames/`.
8. `parsers/tilt_series.py`: retire per-MDOC record/collision output; **retain**
   the per-tilt-vs-series-level angle-extraction logic but retarget it to
   produce a single acquisition-level `tilt_angles` list (feeds the Acquisition).
9. `assembler.py`: parse `Frames/` MDOC → set `acq.tilt_angles` (None-guarded);
   stop overwriting `tilt_series`; **enrich** authored tilt-series rows with
   `st_path`/`zarr_path`/`alignment_files`/`mtime` from disk (mirror tomogram
   enrichment); drop `multiple_tilt_series`; add `undeclared_tilt_series_folder`.
10. `orm.py`: add `AcquisitionORM.tilt_angles` (JSON), rename
    `tilt_series_quality_score` → `raw_tilt_series_quality`; rewrite
    `TiltSeriesORM` columns to match the authored model; tomogram ORMs
    `alignment_id` → `tilt_series_id`. Update `test_orm_drift.MAPPING`.
11. `persistence.py`: extend tilt-series upsert payload to the authored shape;
    verify soft-delete keep-set.

### Phase C — API + frontend
12. `api/schemas.py` + `routes/samples.py`: rename acquisition
    `tilt_series_quality_score` → `raw_tilt_series_quality`; surface authored
    tilt-series fields; add `tilt_angles` to the acquisition payload.
13. Routes (per decision #5):
    - **New `routes/acquisitions.py` (or extend `samples.py`) polar endpoint**
      `/acquisitions/{sample}/{acq}/polar.png` reading `Acquisition.tilt_angles`;
      delete the per-series `tilt_series_polar` route + `tiltSeriesPolarUrl`'s
      old target.
    - `routes/tilt_series.py`: keep per-series `preview.png` + `neuroglancer`,
      but source them from `{ts_id}/stack/` (`zarr_path`/`st_path`). Replace the
      `row.mdoc_path` Frames fallback (mdoc_path is gone from `TiltSeries`) with
      a lookup of the **acquisition's** `Frames/` dir for the raw-frames fallback
      when the series has no stack artifact.
14. `frontend/src/types.ts` + components: rename the acquisition
    `tilt_series_quality_score` field → `raw_tilt_series_quality`; surface
    per-series `is_aligned`; point the polar `PreviewThumbnail` at the new
    acquisition-level polar URL (update `tiltSeriesPolarUrl` →
    `acquisitionPolarUrl` in `Thumbnail.tsx`; `acquisitions.$acquisitionId.tsx`
    no longer keys off `tilt_series[0]`).

### Phase D — Tests + fixtures + example data
15. Migrate fixtures + `data/Experimental/rosenlab_1210_example30bp/` to the new
    layout. Touch points: `test_orm_drift`, `test_generate_json_schema`,
    `test_id_validation`, `test_repo_consistency`, `test_validate_sample`, and
    `tests/catalog/*tilt_series*`, `test_assembler*`, `test_persistence*`,
    `test_extras*`, `test_api*`.

## Risks / notes
- `test_orm_drift` fails until ORM tracks schema in the same commit.
- Moving geometry off `TiltSeries` is a destructive column change — the polar
  plot must be re-sourced from `Acquisition.tilt_angles` in the same change or
  the UI regresses.
- The acquisition-level MDOC parser must emit the full `tilt_angles` list (it
  currently feeds only the per-series parser); verify `parse_acquisition_mdocs`
  produces it.
- Removing the `multiple_tilt_series` warning is now correct: multiple tilt
  series per acquisition is a first-class, expected case (raw + aligned).
