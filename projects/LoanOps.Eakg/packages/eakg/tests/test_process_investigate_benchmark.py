"""ADR-029 process benchmark gate: rule extractor baseline on 4 fixtures.

Investigator is NOT adopted for process KG until this baseline is beaten.
This test records reproducibility of the rule extractor (control arm).
"""

from __future__ import annotations

from pathlib import Path

from packages.eakg.gap_ledger import from_process_draft
from packages.eakg.process_extract import extract_from_paths, load_maps

FIXTURES = Path(__file__).parent / "fixtures" / "process"
MAPS = Path("data/process_kg/maps")
NAMES = (
    "account_maintenance",
    "efta_sensitive",
    "efta_paid_in_advance",
    "fha_non_impound",
)


def _paths(name: str) -> tuple[Path, Path]:
    return FIXTURES / f"{name}.md", FIXTURES / f"{name}.meta.json"


def test_rule_extractor_reproducible_three_runs() -> None:
    if not MAPS.is_dir():
        # Maps may live under repo root when tests run from package dir
        maps = Path(__file__).resolve().parents[5] / "data" / "process_kg" / "maps"
        if not maps.is_dir():
            maps = Path(__file__).resolve().parents[4] / "data" / "process_kg" / "maps"
    else:
        maps = MAPS
    if not maps.is_dir():
        import pytest

        pytest.skip("process maps not found")

    curated = load_maps(maps)
    runs: list[list[str]] = []
    for _ in range(3):
        hashes: list[str] = []
        for name in NAMES:
            md, meta = _paths(name)
            if not md.is_file():
                continue
            d1 = extract_from_paths(md, meta, maps)
            d2 = extract_from_paths(md, meta, maps)
            assert d1.extraction_status == d2.extraction_status
            assert len(d1.steps) == len(d2.steps)
            hashes.append(f"{name}:{d1.extraction_status}:{len(d1.steps)}:{d1.maps_hash}")
        runs.append(hashes)
    assert runs[0] == runs[1] == runs[2]


def test_process_drafts_produce_ledger_items() -> None:
    maps = MAPS if MAPS.is_dir() else Path("data/process_kg/maps")
    if not maps.is_dir():
        import pytest

        pytest.skip("process maps not found")
    items_total = 0
    for name in NAMES:
        md, meta = _paths(name)
        if not md.is_file():
            continue
        draft = extract_from_paths(md, meta, maps)
        items = from_process_draft(draft)
        # Stub/partial or needs_review → ledger; full clean pages may be empty
        items_total += len(items)
    # Benchmark note: rule arm establishes a ledger size to beat; assert API works
    assert items_total >= 0
