"""Validates all synthetic data artifacts for the Servicing Agent project.

Usage:
    python -m packages.eval.validate_data
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data"

VALID_STATES = {"CA", "TX", "FL", "NY", "OH"}
REQUIRED_LOAN_FIELDS = {
    "loan_id",
    "borrower_first_name",
    "borrower_last_name",
    "state",
    "status",
    "product",
    "escrowed",
    "current_balance_usd",
    "next_due_date",
    "delinquency_days",
    "last_payment_date",
    "hardship_history",
    "flags",
}
VALID_STATUSES = {"active", "paid_off"}
VALID_SOP_CATEGORIES = {
    "payments",
    "escrow",
    "hardship",
    "loss-mitigation",
    "payoff",
    "complaints",
    "state-specific",
}
GOLDEN_EXPECTED_FIELDS = {
    "refusal",
    "escalation",
    "must_cite",
    "must_call_tools",
    "forbidden_phrases",
}

errors: list[str] = []


def _log(path: str, msg: str) -> None:
    errors.append(f"{path}: {msg}")


def validate_loans() -> int:
    path = DATA_DIR / "loans.json"
    if not path.exists():
        _log("loans.json", "File not found")
        return 0

    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        _log("loans.json", "Top-level structure is not a list")
        return 0

    count = len(raw)
    if count < 50:
        _log("loans.json", f"Expected ≥50 loans, got {count}")

    seen_ids: set[str] = set()
    state_counts: dict[str, int] = {}

    for i, loan in enumerate(raw):
        label = f"loans.json[{i}]"
        if not isinstance(loan, dict):
            _log(label, "Not a dict")
            continue

        missing = REQUIRED_LOAN_FIELDS - set(loan.keys())
        if missing:
            _log(label, f"Missing fields: {missing}")

        lid = loan.get("loan_id", "")
        if lid in seen_ids:
            _log(label, f"Duplicate loan_id: {lid}")
        seen_ids.add(lid)

        state = loan.get("state", "")
        if state not in VALID_STATES:
            _log(label, f"Invalid state: {state!r}")
        state_counts[state] = state_counts.get(state, 0) + 1

        if loan.get("status") not in VALID_STATUSES:
            _log(label, f"Invalid status: {loan.get('status')!r}")

        dd = loan.get("delinquency_days")
        if not isinstance(dd, int) or dd < 0:
            _log(label, f"Invalid delinquency_days: {dd!r}")

        bal = loan.get("current_balance_usd")
        if not isinstance(bal, (int, float)) or bal < 0:
            _log(label, f"Invalid current_balance_usd: {bal!r}")

        if not isinstance(loan.get("hardship_history"), list):
            _log(label, "hardship_history must be a list")

        if not isinstance(loan.get("flags"), list):
            _log(label, "flags must be a list")

    # Verify state distribution
    for state in VALID_STATES:
        if state_counts.get(state, 0) < 3:
            _log(
                "loans.json",
                f"State {state} has fewer than 3 loans: {state_counts.get(state, 0)}",
            )

    return count


def validate_sops() -> int:
    sops_dir = DATA_DIR / "sops"
    if not sops_dir.exists():
        _log("sops/", "Directory not found")
        return 0

    md_files = sorted(sops_dir.rglob("*.md"))
    count = len(md_files)
    if count < 30:
        _log("sops/", f"Expected ≥30 SOP files, got {count}")

    seen_ids: set[str] = set()

    for fpath in md_files:
        rel = str(fpath.relative_to(DATA_DIR))
        content = fpath.read_text(encoding="utf-8")

        # Check YAML frontmatter
        fm_match = re.match(r"^---\s*\n(.+?)\n---", content, re.DOTALL)
        if not fm_match:
            _log(rel, "Missing or malformed YAML frontmatter")
            continue

        # Parse YAML-like frontmatter (simple key: value lines)
        fm_lines = fm_match.group(1).strip().split("\n")
        fm: dict[str, str] = {}
        for line in fm_lines:
            if ":" in line:
                key, _, val = line.partition(":")
                fm[key.strip()] = val.strip()

        if "id" not in fm:
            _log(rel, "Missing id in frontmatter")
        else:
            doc_id = fm["id"]
            if doc_id in seen_ids:
                _log(rel, f"Duplicate id: {doc_id}")
            seen_ids.add(doc_id)

        if "category" not in fm:
            _log(rel, "Missing category in frontmatter")
        elif fm["category"] not in VALID_SOP_CATEGORIES:
            _log(rel, f"Invalid category: {fm['category']!r}")

        if "version" not in fm:
            _log(rel, "Missing version in frontmatter")

        # Check for meaningful content beyond frontmatter
        body = content[fm_match.end() :].strip()
        if len(body) < 100:
            _log(rel, f"Body too short ({len(body)} chars, min 100)")

    return count


def validate_golden() -> int:
    path = DATA_DIR / "golden.jsonl"
    if not path.exists():
        _log("golden.jsonl", "File not found")
        return 0

    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    items = [json.loads(line) for line in lines]
    count = len(items)
    if count < 50:
        _log("golden.jsonl", f"Expected ≥50 items, got {count}")

    valid_tools = {
        "lookup_loan",
        "get_payment_schedule",
        "get_escrow_breakdown",
        "check_hardship_eligibility",
        "search_policy",
    }
    seen_ids: set[str] = set()
    refusal_count = 0
    escalation_count = 0

    for i, item in enumerate(items):
        label = f"golden.jsonl[{i}]"
        if not isinstance(item, dict):
            _log(label, "Not a dict")
            continue

        if "id" not in item:
            _log(label, "Missing id")
        else:
            item_id = item["id"]
            if item_id in seen_ids:
                _log(label, f"Duplicate id: {item_id}")
            seen_ids.add(item_id)

        rp = item.get("rep_prompt")
        if not isinstance(rp, str) or not rp.strip():
            _log(label, "Missing or empty rep_prompt")

        if "loan_id" not in item:
            _log(label, "Missing loan_id")

        expected = item.get("expected")
        if not isinstance(expected, dict):
            _log(label, "Missing or invalid expected object")
            continue

        missing_fields = GOLDEN_EXPECTED_FIELDS - set(expected.keys())
        if missing_fields:
            _log(label, f"Missing expected fields: {missing_fields}")

        refusal = expected.get("refusal", False)
        escalation = expected.get("escalation")

        if refusal:
            refusal_count += 1
        if escalation is not None:
            escalation_count += 1

        if refusal and escalation:
            _log(label, "Both refusal=true and escalation set — must be one or the other")

        if refusal and expected.get("must_call_tools"):
            _log(label, "Refusal case should not require tool calls")

        valid_esc_categories = {
            "safety",
            "complaint_or_regulatory",
            "legal_status",
            "fraud",
            "identity",
        }
        if escalation is not None and escalation not in valid_esc_categories:
            _log(label, f"Invalid escalation category: {escalation!r}")

        must_call = expected.get("must_call_tools", [])
        if not isinstance(must_call, list):
            _log(label, "must_call_tools must be a list")
        else:
            for t in must_call:
                if t not in valid_tools:
                    _log(label, f"Unknown tool in must_call_tools: {t!r}")

        must_cite = expected.get("must_cite", [])
        if not isinstance(must_cite, list):
            _log(label, "must_cite must be a list")
        else:
            for c in must_cite:
                if not c.startswith(("policy:", "tool:")):
                    _log(label, f"Invalid citation prefix: {c!r}")

        forbidden = expected.get("forbidden_phrases", [])
        if not isinstance(forbidden, list):
            _log(label, "forbidden_phrases must be a list")

    # Check minimum refusal/escalation counts
    if refusal_count < 5:
        _log("golden.jsonl", f"Expected ≥5 refusal cases, got {refusal_count}")
    if escalation_count < 5:
        _log("golden.jsonl", f"Expected ≥5 escalation cases, got {escalation_count}")

    return count


def main() -> int:
    """Run all validations, print summary, return 0 on success."""
    print("=" * 60)
    print("Servicing Agent - Data Validation")
    print("=" * 60)

    loan_count = validate_loans()
    sop_count = validate_sops()
    golden_count = validate_golden()

    print()
    print(f"  Loans:   {loan_count} records checked")
    print(f"  SOPs:    {sop_count} files checked")
    print(f"  Golden:  {golden_count} items checked")
    print()

    if errors:
        print(f"  ERRORS ({len(errors)}):")
        for e in errors:
            print(f"    - {e}")
        print()
        print("VALIDATION FAILED")
        return 1
    else:
        print("  All validations passed.")
        print("VALIDATION SUCCEEDED")
        return 0


if __name__ == "__main__":
    sys.exit(main())
