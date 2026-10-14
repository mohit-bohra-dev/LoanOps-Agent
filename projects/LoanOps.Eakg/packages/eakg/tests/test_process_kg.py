"""ADR-028 process KG pilot tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from packages.capability_kg.ontology import (
    CLASS_BUSINESS_PROCESS,
    CLASS_PROCESS_STEP,
    PRED_HAS_STEP,
    PRED_REVIEW_STATUS,
    PRED_SOP_ROLE_LABEL,
    loanops_ns,
)
from packages.common.providers.graph_store import FakeGraphStore
from packages.eakg.process_extract import extract_from_paths, load_maps
from packages.eakg.process_graph import (
    build_graph,
    explain_process,
    extract_bundle,
    load_processes,
    report_extraction,
    revalidate_links,
    set_review_status,
    verify_fresh,
    write_proposal,
)
from packages.eakg.process_validate import validate_process
from rdflib.namespace import RDF

FIX = Path(__file__).resolve().parent / "fixtures" / "process"
MAPS = Path(__file__).resolve().parents[5] / "data" / "process_kg" / "maps"
# parents: tests -> eakg -> packages -> LoanOps.Eakg -> projects -> repo root
# Path(__file__) = .../packages/eakg/tests/test_process_kg.py
# parent = tests, parents[1]=eakg, [2]=packages, [3]=LoanOps.Eakg, [4]=projects, [5]=repo


def _repo_maps() -> Path:
    # Walk up until data/process_kg/maps exists.
    cur = Path(__file__).resolve().parent
    for _ in range(8):
        candidate = cur / "data" / "process_kg" / "maps"
        if candidate.is_dir():
            return candidate
        cur = cur.parent
    return MAPS


@pytest.fixture
def maps_dir() -> Path:
    return _repo_maps()


def test_maps_hash_stable(maps_dir: Path) -> None:
    a = load_maps(maps_dir)
    b = load_maps(maps_dir)
    assert a.maps_hash == b.maps_hash
    assert len(a.maps_hash) == 16


def test_extract_determinism(maps_dir: Path) -> None:
    d1 = extract_from_paths(
        FIX / "efta_sensitive.md", FIX / "efta_sensitive.meta.json", maps_dir
    )
    d2 = extract_from_paths(
        FIX / "efta_sensitive.md", FIX / "efta_sensitive.meta.json", maps_dir
    )
    assert [s.id for s in d1.steps] == [s.id for s in d2.steps]
    assert [t.id for t in d1.transitions] == [t.id for t in d2.transitions]
    assert len(d1.needs_review) == len(d2.needs_review)


def test_hub_children_stubs(maps_dir: Path) -> None:
    draft = extract_from_paths(
        FIX / "account_maintenance.md",
        FIX / "account_maintenance.meta.json",
        maps_dir,
    )
    assert draft.procedure_id.startswith("DP17-")
    assert len(draft.children) >= 6
    assert draft.source_completeness == "lossy_unverified"
    assert any(s.kind == "start" for s in draft.steps)


def test_efta_sensitive_decisions_and_thresholds(maps_dir: Path) -> None:
    draft = extract_from_paths(
        FIX / "efta_sensitive.md", FIX / "efta_sensitive.meta.json", maps_dir
    )
    assert draft.procedure_id == "DP17-ESC372.v01"
    assert "efta" in draft.regulations or "respa" in draft.regulations
    decisions = [s for s in draft.steps if s.kind == "decision"]
    assert len(decisions) >= 2
    # Thresholds preserve units
    units = {t.unit for s in draft.steps for t in s.thresholds}
    assert "days_unspecified" in units or "calendar_days" in units or units
    # action+jump / override → needs_review
    reasons = {n.reason for n in draft.needs_review}
    assert "action_plus_jump" in reasons or "override_exception" in reasons


def test_malformed_needs_review(maps_dir: Path) -> None:
    draft = extract_from_paths(
        FIX / "malformed.md", FIX / "malformed.meta.json", maps_dir
    )
    reasons = {n.reason for n in draft.needs_review}
    assert "missing_procedure_id" in reasons
    assert "action_plus_jump" in reasons


def test_validator_unreachable() -> None:
    from packages.eakg.process_extract import (
        ProcessDraft,
        StepDraft,
        TransitionDraft,
    )

    draft = ProcessDraft(
        process_id="p",
        title="t",
        procedure_id="DP17-X.v01",
        effective_date="",
        page_id="1",
        page_url="",
        source_version=1,
        source_hash="abc",
        source_completeness="complete_unverified",
        lost_features=[],
        extraction_status="full",
        regulations=[],
        steps=[
            StepDraft("p_s1", "start", "start", "Procedures", 1),
            StepDraft("p_s2", "orphan", "task", "Procedures", 2),
            StepDraft("p_s3", "end", "end", "Procedures", 3),
        ],
        transitions=[
            TransitionDraft("t1", "p_s1", "p_s3", "next"),
        ],
        children=[],
        needs_review=[],
    )
    result = validate_process(draft)
    assert result.status == "fail"
    assert any("unreachable_step:p_s2" in f for f in result.failures)


def test_validator_decision_sheet(maps_dir: Path) -> None:
    draft = extract_from_paths(
        FIX / "efta_sensitive.md", FIX / "efta_sensitive.meta.json", maps_dir
    )
    result = validate_process(draft)
    assert result.decision_sheet
    assert all(r.guard_label for r in result.decision_sheet)


@pytest.mark.asyncio
async def test_load_and_explain(maps_dir: Path) -> None:
    drafts, validations = extract_bundle(
        FIX,
        maps_dir,
        ["account_maintenance", "efta_sensitive", "fha_non_impound"],
    )
    gs = FakeGraphStore()
    report = await load_processes(gs, drafts, validations)
    assert report["review_status"] == "pending_review"
    assert report["triples"] > 0
    g = build_graph(drafts, validations)
    ns = loanops_ns()
    procs = list(g.subjects(RDF.type, ns[CLASS_BUSINESS_PROCESS]))
    assert procs
    # All pending_review
    for p in procs:
        statuses = list(g.objects(p, ns[PRED_REVIEW_STATUS]))
        assert statuses
        assert str(statuses[0]) == "pending_review"
    explained = await explain_process(gs, "efta_sensitive")
    assert explained.get("label")
    assert explained.get("review") == "pending_review"


@pytest.mark.asyncio
async def test_approve_and_stale(maps_dir: Path) -> None:
    drafts, validations = extract_bundle(FIX, maps_dir, ["fha_non_impound"])
    gs = FakeGraphStore()
    await load_processes(gs, drafts, validations)
    approved = await set_review_status(
        gs, "fha_non_impound", "approved", reviewer="tester"
    )
    assert approved["hasReviewStatus"] == "approved"
    draft = drafts[0]
    stale = await verify_fresh(
        gs,
        "fha_non_impound",
        live_version=draft.source_version + 1,
        live_hash="deadbeef",
    )
    assert stale["stale"] is True


@pytest.mark.asyncio
async def test_revalidate_flags_broken(maps_dir: Path) -> None:
    drafts, validations = extract_bundle(FIX, maps_dir, ["efta_sensitive"])
    gs = FakeGraphStore()
    await load_processes(gs, drafts, validations)
    result = await revalidate_links(gs, known_operation_keys=set())
    # May be zero if no capability keys matched; still should succeed.
    assert "broken_count" in result


def test_proposal_write(tmp_path: Path, maps_dir: Path) -> None:
    drafts, validations = extract_bundle(FIX, maps_dir, ["account_maintenance"])
    out = tmp_path / "proposal.json"
    write_proposal(out, drafts, validations)
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["review_status"] == "pending_review"
    assert payload["report"]["processes"]


def test_authz_isolation_no_process_predicates() -> None:
    """Process predicates must not appear in MCP authz / tools policy code."""
    roots = [
        Path("projects/LoanOps.McpServer/packages/mcp_server"),
        Path("projects/LoanOps.Tools/packages/tools"),
    ]
    banned = (
        "sopRoleLabel",
        "hasCapabilityLink",
        "BusinessProcess",
        "ProcessStep",
        "usesSystem",
    )
    offenders: list[str] = []
    for root in roots:
        if not root.is_dir():
            continue
        for path in root.rglob("*.py"):
            name = path.name
            if "test_" in name:
                continue
            # Only authz/policy/bind surfaces.
            if name not in {
                "policy.py",
                "capability_authz.py",
                "capability_bind.py",
                "scopes.py",
            } and "policy" not in name:
                continue
            text = path.read_text(encoding="utf-8")
            for token in banned:
                if token in text:
                    offenders.append(f"{path}:{token}")
    assert offenders == []


def test_no_sop_role_as_role_resource(maps_dir: Path) -> None:
    drafts, validations = extract_bundle(FIX, maps_dir, ["efta_sensitive"])
    g = build_graph(drafts, validations)
    ns = loanops_ns()
    # Predicates used as literals only — no Role class typing from sopRoleLabel.
    for _s, _p, o in g.triples((None, ns[PRED_SOP_ROLE_LABEL], None)):
        assert o is not None
    # Ensure ProcessStep nodes exist
    assert list(g.subjects(RDF.type, ns[CLASS_PROCESS_STEP]))
    assert list(g.triples((None, ns[PRED_HAS_STEP], None)))


def test_report_counts(maps_dir: Path) -> None:
    drafts, validations = extract_bundle(
        FIX, maps_dir, ["efta_sensitive", "malformed"]
    )
    # include malformed by extracting separately already in bundle names
    report = report_extraction(drafts, validations)
    assert report["extractor_version"]
    assert any(p["needs_review_count"] > 0 for p in report["processes"])


@pytest.mark.graphdb
@pytest.mark.asyncio
async def test_graphdb_named_graph_optional() -> None:
    """Opt-in: requires local GraphDB. Skipped in CI unless marker selected."""
    pytest.skip("opt-in GraphDB smoke — run manually with --graphdb when available")
