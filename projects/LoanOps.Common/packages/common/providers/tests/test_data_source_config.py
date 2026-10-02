"""Tests for independent loan / SOP source selection."""

from __future__ import annotations

from packages.common.settings import DataConfig


def test_defaults_are_mock_local_cache() -> None:
    cfg = DataConfig()
    assert cfg.loan_source == "mock"
    assert cfg.sop_source == "local"
    assert cfg.sop_confluence_mode == "cache"
    assert cfg.mode == "mock"


def test_legacy_mode_real_maps_to_both_live() -> None:
    cfg = DataConfig(mode="real")
    assert cfg.loan_source == "real"
    assert cfg.sop_source == "both"
    assert cfg.sop_confluence_mode == "live"


def test_legacy_mode_mock_maps_to_local() -> None:
    cfg = DataConfig(mode="mock")
    assert cfg.loan_source == "mock"
    assert cfg.sop_source == "local"


def test_explicit_confluence_only_overrides_legacy() -> None:
    cfg = DataConfig(
        mode="mock",
        sop_source="confluence",
        sop_confluence_mode="cache",
    )
    assert cfg.loan_source == "mock"
    assert cfg.sop_source == "confluence"
    assert cfg.sop_confluence_mode == "cache"


def test_explicit_loan_and_sop_without_mode() -> None:
    cfg = DataConfig(
        loan_source="mock",
        sop_source="confluence",
        sop_confluence_mode="cache",
    )
    assert cfg.loan_source == "mock"
    assert cfg.sop_source == "confluence"
    assert cfg.mode == "mock"
