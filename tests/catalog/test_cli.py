"""CLI exit-code behavior for `python -m catalog scan`.

These focus on the scan command's exit contract and patch out the actual
scan so they stay fast and independent of the fixture data tree:

* per-sample errors are isolated → exit 0 (a k8s Job/CronJob must not be
  marked failed just because one sample errored)
* a genuine whole-scan failure (scan_root raises) → exit 1
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from catalog import cli, scanner


def _run_scan(tmp_path: Path):
    """Invoke `scan <tmp_path> --init` against a throwaway in-memory DB."""
    return cli.main(
        ["scan", str(tmp_path), "--db", "sqlite:///:memory:", "--init"]
    )


def test_per_sample_errors_exit_zero(tmp_path, capsys):
    report = scanner.ScanReport(
        upserted=2,
        errors=["sample_bad: boom"],
        failed_samples=[("sample_bad", "boom")],
    )
    with patch.object(scanner, "scan_root", return_value=report):
        rc = _run_scan(tmp_path)

    assert rc == 0
    err = capsys.readouterr().err
    # The bad sample is still surfaced loudly on stderr.
    assert "sample_bad: boom" in err
    assert "per-sample error" in err


def test_whole_scan_failure_exits_one(tmp_path, capsys):
    with patch.object(
        scanner, "scan_root", side_effect=RuntimeError("db exploded")
    ):
        rc = _run_scan(tmp_path)

    assert rc == 1
    assert "scan failed: db exploded" in capsys.readouterr().err


def test_clean_scan_exits_zero(tmp_path):
    report = scanner.ScanReport(upserted=3)
    with patch.object(scanner, "scan_root", return_value=report):
        rc = _run_scan(tmp_path)

    assert rc == 0
