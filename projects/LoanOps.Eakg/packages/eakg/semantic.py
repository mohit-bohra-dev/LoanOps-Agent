"""Semantic proposals — LLM may only propose labels/groupings/rationale (never structure)."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from packages.eakg.models import Proposal, RepoInterface, utc_now_iso
from packages.eakg.store import ShardStore

ALLOWED_KINDS = frozenset({"capability_label", "capability_group", "overlap_wording", "rationale"})


def op_content_hash(op: dict[str, Any]) -> str:
    blob = json.dumps(
        {
            "method": op.get("method"),
            "path": op.get("path"),
            "action": op.get("action"),
            "summary": op.get("summary"),
        },
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def _heuristic_label(action: str) -> str:
    # GetLoanSummary → "Get loan summary"
    spaced = re_sub_camel(action)
    return spaced.strip().capitalize()


def re_sub_camel(name: str) -> str:
    import re

    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1 \2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", s1)


async def propose_for_repo(
    iface: RepoInterface,
    store: ShardStore,
    *,
    use_llm: bool = False,
    chat_complete: Any | None = None,
) -> list[Proposal]:
    """Generate proposals for ops missing from proposal cache.

    Default path is heuristic (no LLM). When use_llm and chat_complete provided,
    model may only return label/intent/rationale JSON — never routes/edges.
    """
    existing = {str(p.get("content_hash")) for p in store.read_proposals(iface.repository_id)}
    proposals: list[Proposal] = []
    for op in iface.operations:
        ch = op_content_hash(op)
        if ch in existing:
            continue
        action = str(op.get("action") or "operation")
        label = _heuristic_label(action)
        intent = f"Capability for {op.get('method')} {op.get('path')}"
        rationale = "Heuristic label from action name; structural facts from extractor."

        if use_llm and chat_complete is not None:
            prompt = (
                "Propose a short capability label and one-sentence intent for this API "
                "operation. Reply JSON only with keys label, intent, rationale. "
                "Do not invent routes, permissions, or dependencies.\n"
                f"action={action} method={op.get('method')} path={op.get('path')} "
                f"summary={op.get('summary')}"
            )
            try:
                raw = await chat_complete(prompt)
                data = json.loads(raw) if isinstance(raw, str) else raw
                if isinstance(data, dict):
                    label = str(data.get("label") or label)
                    intent = str(data.get("intent") or intent)
                    rationale = str(data.get("rationale") or rationale)
            except Exception:  # noqa: BLE001
                pass

        prop = Proposal(
            proposal_id=f"prop_{ch[:16]}",
            kind="capability_label",
            repository_id=iface.repository_id,
            content_hash=ch,
            payload={
                "action": action,
                "label": label,
                "intent": intent,
                "operation_key": op.get("key"),
            },
            confidence=0.6 if use_llm else 0.55,
            evidence_refs=[str(op.get("key") or "")],
            status="pending_review",
            created_at=utc_now_iso(),
        )
        assert prop.kind in ALLOWED_KINDS
        store.append_proposal(iface.repository_id, prop.to_dict())
        proposals.append(prop)
        existing.add(ch)
    return proposals
