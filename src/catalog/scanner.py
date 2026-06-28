"""Scanner orchestrator.

scan_root walks the data root, runs the gating check, dispatches per-sample
to the assembler + persistence layer inside a transaction, and tracks the
overall run via the `scans` table (one row per invocation, status running/
completed/failed) and a per-sample ScanReport returned to the caller.

Single-writer contract: running two scan_root calls against the same
DB simultaneously is undefined. The CLI takes no advisory lock; the operator
is responsible for serializing scans.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal
from uuid import uuid4

from loguru import logger
from sqlalchemy import Engine
from sqlalchemy.orm import sessionmaker

from catalog import (
    assembler,
    discovery,
    md_previews,
    orm,
    persistence,
    state,
    thumbnails,
)
from catalog.assembler import FieldConflict, ScanWarning


@dataclass
class ScanReport:
    upserted: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[ScanWarning] = field(default_factory=list)
    # Run-level warnings not tied to a sample (e.g. unknown MdSimulation subdir).
    run_warnings: list[ScanWarning] = field(default_factory=list)
    conflicts: list[FieldConflict] = field(default_factory=list)
    soft_deleted: int = 0
    # populated only on prune_dry_run=True
    would_soft_delete: list[str] | None = None
    # Per-sample membership behind the counts above, persisted to scan_samples
    # so the /manage view can list which samples sit behind each tally.
    upserted_ids: list[str] = field(default_factory=list)
    skipped_ids: list[str] = field(default_factory=list)
    # (sample_id, error message) — sample-level failures only.
    failed_samples: list[tuple[str, str]] = field(default_factory=list)
    thumbnails_healed: int = 0
    md_previews_healed: int = 0


def scan_root(
    engine: Engine,
    root: Path,
    *,
    force: bool = False,
    prune: bool = False,
    prune_dry_run: bool = False,
    prune_safety_floor: float = 0.5,
    on_error: Literal["collect", "raise"] = "collect",
    thumbnail_dir: Path | None = None,
    md_preview_dir: Path | None = None,
) -> ScanReport:
    """Walk ``root``, assemble + persist each sample, return a ScanReport.

    Mtime gating: a sample is skipped if every parse-target file's mtime is
    unchanged AND the parse-target set is unchanged AND the sample is not
    soft-deleted. ``force=True`` bypasses the gate.

    ``prune=True`` runs ``soft_delete_missing_samples`` after the per-sample
    loop. ``prune_dry_run=True`` reports what would be deleted without writing.
    ``prune_safety_floor`` (0..1.0) caps the fraction of live samples that may
    be deleted in one run; raise PruneSafetyFloorExceeded otherwise.

    ``on_error='collect'`` records sample-level exceptions to ``report.errors``
    and continues. ``'raise'`` propagates the first exception.
    """
    SessionFactory = sessionmaker(bind=engine, future=True, expire_on_commit=False)
    report = ScanReport()
    scan_run_id = uuid4().hex

    session = SessionFactory()
    try:
        # Open scan_run + catalog_meta in their own transaction so they're
        # visible to subsequent transactions.
        with session.begin():
            state.start_scan(session, scan_run_id, root)

        # One SELECT before the loop for soft-deleted ids.
        with session.begin():
            soft_deleted_ids = state.load_soft_deleted_ids(session)

        sample_locs = list(discovery.iter_samples(root))
        total = len(sample_locs)
        logger.info(
            "scanning {} — {} sample(s) discovered "
            "(force={}, thumbnails={}, md_previews={})",
            root,
            total,
            force,
            "on" if thumbnail_dir is not None else "off",
            "on" if md_preview_dir is not None else "off",
        )
        run_started = time.perf_counter()

        fs_sample_ids: set[str] = set()
        for idx, sample_loc in enumerate(sample_locs, start=1):
            fs_sample_ids.add(sample_loc.sample_id)
            logger.info("[{}/{}] {}", idx, total, sample_loc.sample_id)

            # Per-sample work in its own transaction
            try:
                _scan_one_sample(
                    session,
                    sample_loc,
                    force=force,
                    soft_deleted_ids=soft_deleted_ids,
                    scan_run_id=scan_run_id,
                    report=report,
                    thumbnail_dir=thumbnail_dir,
                    md_preview_dir=md_preview_dir,
                )
            except Exception as e:  # noqa: BLE001
                # Make sure no partial transaction is left dangling.
                if session.in_transaction():
                    session.rollback()
                report.errors.append(f"{sample_loc.sample_id}: {e}")
                report.failed_samples.append((sample_loc.sample_id, str(e)))
                if on_error == "raise":
                    raise

        # Run-level warnings: subdirs under MdSimulation/ that aren't one of
        # the four dataset-type dirs hold no cataloguable sample and were
        # skipped by discovery. Surface them so operators see misplaced data.
        run_warnings = [
            ScanWarning(
                category="unknown_md_simulation_subdir",
                location=str(subdir),
                message=(
                    f"'{subdir.name}' is not a recognized MdSimulation "
                    "dataset-type directory (expected one of Bulk, "
                    "SingleMolecule, Slab); any samples under "
                    "it were skipped."
                ),
            )
            for subdir in discovery.iter_unknown_md_subdirs(root)
        ]
        # Samples placed outside the two recognized top-level arms
        # (root/{other}/{sample}/sample.toml) are never discovered and never
        # catalogued. Surface each so operators can move it under Experimental/
        # or MdSimulation/.
        run_warnings.extend(
            ScanWarning(
                category="sample_outside_arm",
                location=str(sample_dir),
                message=(
                    f"sample '{sample_dir.name}' is not under a recognized "
                    "top-level arm (expected Experimental/ or MdSimulation/); "
                    "it was skipped and not catalogued."
                ),
            )
            for sample_dir in discovery.iter_misplaced_samples(root)
        )
        if run_warnings:
            report.run_warnings.extend(run_warnings)
            with session.begin():
                persistence.persist_run_warnings(
                    session, scan_run_id, run_warnings
                )

        # After the loop: optional prune
        if prune or prune_dry_run:
            with session.begin():
                try:
                    persistence.soft_delete_missing_samples(
                        session,
                        fs_sample_ids,
                        dry_run=prune_dry_run,
                        safety_floor=prune_safety_floor,
                        report=report,
                    )
                except persistence.PruneSafetyFloorExceeded as exc:
                    report.errors.append(
                        f"prune aborted: would soft-delete {len(exc.missing)} "
                        f"samples ({exc.ratio:.1%} > floor "
                        f"{exc.threshold:.1%}); missing={exc.missing}"
                    )
                    raise

        with session.begin():
            state.finish_scan(
                session, scan_run_id, status="completed", report=report
            )
        logger.info(
            "scan complete in {:.1f}s — upserted={}, skipped={}, "
            "healed={}, warnings={}, errors={}",
            time.perf_counter() - run_started,
            report.upserted,
            report.skipped,
            report.thumbnails_healed,
            len(report.warnings),
            len(report.errors),
        )
    except Exception:
        # Mark the scan failed; let the exception propagate per on_error semantics.
        try:
            if session.in_transaction():
                session.rollback()
            with session.begin():
                state.finish_scan(
                    session, scan_run_id, status="failed", report=report
                )
        except Exception:
            pass  # don't mask the original
        raise
    finally:
        session.close()

    return report


def _scan_one_sample(
    session,
    sample_loc,
    *,
    force: bool,
    soft_deleted_ids: set[str],
    scan_run_id: str,
    report: ScanReport,
    thumbnail_dir: Path | None,
    md_preview_dir: Path | None = None,
) -> None:
    """Per-sample scan inside its own transaction. Mutates ``report`` in place."""
    parse_targets = discovery.parse_targets_for_sample(sample_loc)

    # Gating check (read state in its own short transaction)
    with session.begin():
        sample_state = state.load_sample_state(session, sample_loc.sample_id)

    is_soft_deleted = sample_loc.sample_id in soft_deleted_ids
    if (
        not force
        and not is_soft_deleted
        and not state.parse_target_set_changed(sample_state, parse_targets)
        and not any(state.is_file_changed(sample_state, p) for p in parse_targets)
    ):
        if thumbnail_dir is not None:
            with session.begin():
                stored = session.get(orm.SampleORM, sample_loc.sample_id)
                rel = stored.thumbnail_path if stored else None
                if rel and not (thumbnail_dir / rel).is_file():
                    logger.info(
                        "  thumbnail missing on disk — re-generating for {}",
                        sample_loc.sample_id,
                    )
                    new_rel = thumbnails.generate_thumbnails(
                        sample_loc.sample_id,
                        thumbnails.refs_from_db(session, sample_loc.sample_id),
                        thumbnail_dir,
                        skip_existing=True,
                    )
                    stored.thumbnail_path = new_rel
                    session.add(stored)
                    report.thumbnails_healed += 1
        if md_preview_dir is not None:
            refs = md_previews.refs_from_location(sample_loc)
            expected = {
                r.md_run_id: md_previews.relpath(sample_loc.sample_id, r.md_run_id)
                for r in refs
                if r.dump_path
            }
            if any(not (md_preview_dir / rel).is_file() for rel in expected.values()):
                logger.info(
                    "  md preview missing on disk — re-generating for {}",
                    sample_loc.sample_id,
                )
                with session.begin():
                    rels = md_previews.generate_md_previews(
                        sample_loc.sample_id, refs, md_preview_dir,
                        skip_existing=True,
                    )
                    for run_id, rel in rels.items():
                        row = session.get(
                            orm.MdRunORM, (sample_loc.sample_id, run_id)
                        )
                        if row is not None:
                            row.preview_path = rel
                            session.add(row)
                report.md_previews_healed += 1
        logger.debug("  skipped (unchanged): {}", sample_loc.sample_id)
        report.skipped += 1
        report.skipped_ids.append(sample_loc.sample_id)
        return

    # Assemble + persist in one transaction
    with session.begin():
        result = assembler.assemble_sample(sample_loc)
        report.warnings.extend(result.warnings)
        report.conflicts.extend(result.conflicts)

        if result.record is None:
            report.errors.extend(
                f"{sample_loc.sample_id}: {e}" for e in result.errors
            )
            report.failed_samples.append(
                (sample_loc.sample_id, "; ".join(result.errors))
            )
            return
        for e in result.errors:
            report.errors.append(f"{sample_loc.sample_id}: {e}")

        disk_size = discovery.dir_size_bytes(sample_loc.path)
        thumb_rel = None
        if thumbnail_dir is not None:
            n_acqs = len(result.record.acquisitions)
            logger.info(
                "  generating thumbnails for {} acquisition(s)…", n_acqs
            )
            thumb_started = time.perf_counter()
            thumb_rel = thumbnails.generate_thumbnails(
                sample_loc.sample_id,
                thumbnails.refs_from_record(result.record),
                thumbnail_dir,
                skip_existing=False,
            )
            logger.info(
                "  thumbnails done in {:.1f}s (representative={})",
                time.perf_counter() - thumb_started,
                thumb_rel or "none",
            )
        md_preview_paths = None
        if md_preview_dir is not None:
            refs = md_previews.refs_from_location(sample_loc)
            n_runs = sum(1 for r in refs if r.dump_path)
            if n_runs:
                logger.info("  generating md previews for {} run(s)…", n_runs)
                md_started = time.perf_counter()
                md_preview_paths = md_previews.generate_md_previews(
                    sample_loc.sample_id, refs, md_preview_dir,
                    skip_existing=False,
                )
                logger.info(
                    "  md previews done in {:.1f}s ({} rendered)",
                    time.perf_counter() - md_started,
                    len(md_preview_paths),
                )
        persistence.upsert_sample_record(
            session,
            result.record,
            extras=result.extras,
            warnings=result.warnings,
            scan_run_id=scan_run_id,
            disk_size_bytes=disk_size,
            thumbnail_path=thumb_rel,
            md_preview_paths=md_preview_paths,
        )
        # Update mtime state for every parse target.
        for p in parse_targets:
            try:
                mtime = p.stat().st_mtime
            except FileNotFoundError:
                continue  # file disappeared between discovery and stat — skip
            state.record_file_scan(session, p, sample_loc.sample_id, mtime)
        # Prune scan_state rows for files that are no longer parse targets.
        state.prune_missing(
            session, sample_loc.sample_id, kept_paths=set(parse_targets)
        )
        report.upserted += 1
        report.upserted_ids.append(sample_loc.sample_id)


__all__ = ["ScanReport", "scan_root"]
