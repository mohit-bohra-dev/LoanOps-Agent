"""LLM investigator over the gap ledger (ADR-029). Coverage never delegated."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from packages.eakg.candidate_gate import (
    CandidateProposal,
    GateVerdict,
    ProposalKind,
    validate_candidate,
)
from packages.eakg.gap_ledger import LedgerItem, shapes_eligible_for_pattern
from packages.eakg.models import Proposal, utc_now_iso
from packages.eakg.store import ShardStore

PROMPT_VERSION = "investigate_v1"
MAX_ROUNDS_DEFAULT = 8

# Avoid importing ToolDefinition at module load if provider_contracts path differs —
# use duck typing for chat.complete(tools=...).


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]


@dataclass
class InvestigateResult:
    ledger_item_id: str
    proposals: list[CandidateProposal] = field(default_factory=list)
    verdicts: list[GateVerdict] = field(default_factory=list)
    tool_log: list[dict[str, Any]] = field(default_factory=list)
    closed_as: str = ""  # proposed | no_finding | skipped | error

    def to_dict(self) -> dict[str, Any]:
        return {
            "ledger_item_id": self.ledger_item_id,
            "proposals": [p.to_dict() for p in self.proposals],
            "verdicts": [v.to_dict() for v in self.verdicts],
            "tool_log": list(self.tool_log),
            "closed_as": self.closed_as,
        }


def _tool_defs() -> list[ToolSpec]:
    empty_obj: dict[str, Any] = {"type": "object", "properties": {}}
    return [
        ToolSpec(
            "read_file_window",
            "Read lines from a repo file (start/end 1-based inclusive).",
            {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "start": {"type": "integer"},
                    "end": {"type": "integer"},
                },
                "required": ["path", "start", "end"],
            },
        ),
        ToolSpec(
            "read_spec_section",
            "Read a JSON path prefix from the cached OpenAPI document.",
            {
                "type": "object",
                "properties": {
                    "path_prefix": {"type": "string"},
                },
                "required": ["path_prefix"],
            },
        ),
        ToolSpec(
            "read_interface",
            "Summarize stored RepoInterface for this repository.",
            empty_obj,
        ),
        ToolSpec(
            "read_manifest",
            "Read coverage / onboard manifest for this repository.",
            empty_obj,
        ),
        ToolSpec(
            "propose_operation",
            "Propose an API operation candidate (pending_review).",
            {"type": "object", "properties": {"payload": {"type": "object"}}, "required": ["payload"]},
        ),
        ToolSpec(
            "propose_relationship",
            "Propose a cross-app relationship candidate.",
            {"type": "object", "properties": {"payload": {"type": "object"}}, "required": ["payload"]},
        ),
        ToolSpec(
            "propose_process_step",
            "Propose a process step / transition candidate.",
            {"type": "object", "properties": {"payload": {"type": "object"}}, "required": ["payload"]},
        ),
        ToolSpec(
            "propose_capability_link",
            "Propose a process→capability link (governed; gate checks boundary).",
            {"type": "object", "properties": {"payload": {"type": "object"}}, "required": ["payload"]},
        ),
        ToolSpec(
            "propose_conflict_resolution",
            "Propose resolution for a ConflictRecord (does not auto-apply).",
            {"type": "object", "properties": {"payload": {"type": "object"}}, "required": ["payload"]},
        ),
        ToolSpec(
            "propose_pattern",
            "Propose a declarative pattern YAML for data/eakg/patterns/ (needs backtest).",
            {
                "type": "object",
                "properties": {
                    "pattern_file": {"type": "string"},
                    "yaml_fragment": {"type": "string"},
                    "rationale": {"type": "string"},
                },
                "required": ["pattern_file", "yaml_fragment"],
            },
        ),
        ToolSpec(
            "propose_extractor_change",
            "Request a code-level extractor change (lands in TASKS; no auto path).",
            {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "detail": {"type": "string"},
                },
                "required": ["title", "detail"],
            },
        ),
        ToolSpec(
            "propose_no_finding",
            "Close the ledger item without inventing a fact.",
            {
                "type": "object",
                "properties": {"rationale": {"type": "string"}},
                "required": ["rationale"],
            },
        ),
    ]


def _to_provider_tools(specs: list[ToolSpec]) -> list[Any]:
    try:
        from provider_contracts.llm import ToolDefinition
    except ImportError:  # pragma: no cover
        from packages.common.providers.chat import ToolDefinition  # type: ignore[attr-defined]

    return [
        ToolDefinition(name=s.name, description=s.description, parameters=s.parameters)
        for s in specs
    ]


class InvestigateContext:
    """Read-only tool backends for one investigation."""

    def __init__(
        self,
        *,
        repo_root: Path | None = None,
        store: ShardStore | None = None,
        repository_id: str = "",
        spec: dict[str, Any] | None = None,
        established_op_keys: set[str] | None = None,
    ) -> None:
        self.repo_root = repo_root
        self.store = store
        self.repository_id = repository_id
        self.spec = spec or {}
        self.established_op_keys = established_op_keys or set()

    def dispatch(self, name: str, args: dict[str, Any]) -> str:
        if name == "read_file_window":
            return self._read_file_window(
                str(args.get("path") or ""),
                int(args.get("start") or 1),
                int(args.get("end") or 1),
            )
        if name == "read_spec_section":
            return self._read_spec_section(str(args.get("path_prefix") or ""))
        if name == "read_interface":
            return self._read_interface()
        if name == "read_manifest":
            return self._read_manifest()
        return json.dumps({"error": f"unknown_or_sink_tool:{name}"})

    def _read_file_window(self, path: str, start: int, end: int) -> str:
        if self.repo_root is None:
            return json.dumps({"error": "no_repo_root"})
        target = (self.repo_root / path).resolve()
        try:
            target.relative_to(self.repo_root.resolve())
        except ValueError:
            return json.dumps({"error": "path_outside_repo"})
        if not target.is_file():
            return json.dumps({"error": "not_found", "path": path})
        lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
        start = max(1, start)
        end = min(len(lines), max(start, end))
        window = "\n".join(f"{i}:{lines[i - 1]}" for i in range(start, end + 1))
        return json.dumps({"path": path, "start": start, "end": end, "text": window[:8000]})

    def _read_spec_section(self, prefix: str) -> str:
        # Walk dotted / slash path into OpenAPI dict
        node: Any = self.spec
        for part in prefix.replace("/", ".").split("."):
            if not part:
                continue
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                return json.dumps({"error": "not_found", "prefix": prefix})
        text = json.dumps(node, indent=2)[:8000]
        return json.dumps({"prefix": prefix, "text": text})

    def _read_interface(self) -> str:
        if self.store is None or not self.repository_id:
            return json.dumps({"error": "no_interface"})
        iface = self.store.read_interface(self.repository_id)
        if iface is None:
            return json.dumps({"error": "missing"})
        return json.dumps(
            {
                "repository_id": iface.repository_id,
                "application_id": iface.application_id,
                "operations": len(iface.operations),
                "packages": len(iface.packages),
                "service_url_keys": iface.service_url_keys[:40],
                "sample_ops": iface.operations[:5],
            }
        )

    def _read_manifest(self) -> str:
        if self.store is None or not self.repository_id:
            return json.dumps({"error": "no_manifest"})
        path = self.store.repo_dir(self.repository_id) / "manifest.json"
        if not path.is_file():
            return json.dumps({"error": "missing"})
        return path.read_text(encoding="utf-8")[:8000]


_SINK_TO_KIND: dict[str, ProposalKind] = {
    "propose_operation": "operation",
    "propose_relationship": "relationship",
    "propose_process_step": "process_step",
    "propose_capability_link": "capability_link",
    "propose_conflict_resolution": "conflict_resolution",
    "propose_pattern": "pattern",
    "propose_extractor_change": "extractor_change",
    "propose_no_finding": "no_finding",
}


def _cache_key(
    *,
    repository_id: str,
    commit_sha: str,
    item: LedgerItem,
    patterns_hash: str,
) -> str:
    blob = "|".join(
        [
            repository_id,
            commit_sha,
            item.item_id,
            item.shape_key,
            PROMPT_VERSION,
            patterns_hash,
        ]
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


async def investigate_item(
    item: LedgerItem,
    *,
    chat: Any,
    ctx: InvestigateContext,
    max_rounds: int = MAX_ROUNDS_DEFAULT,
    allow_pattern: bool = False,
    model_id: str = "",
    commit_sha: str = "",
    patterns_hash: str = "",
) -> InvestigateResult:
    """Run one ledger item through a tool-calling loop. temperature=0 expected at provider."""
    result = InvestigateResult(ledger_item_id=item.item_id)
    tools = _to_provider_tools(_tool_defs())
    system = (
        "You investigate one EAKG gap ledger item. Use read tools for evidence. "
        "Propose candidates only via propose_* tools. Prefer propose_no_finding "
        "over inventing facts. You do not control extractor coverage. "
        f"Pattern proposals allowed={allow_pattern}. "
        f"prompt_version={PROMPT_VERSION}."
    )
    user = json.dumps(
        {
            "item": item.to_dict(),
            "instruction": "Investigate and propose or close with no_finding.",
        },
        indent=2,
    )
    messages: list[Any] = []
    try:
        from provider_contracts.llm import LLMMessage
    except ImportError:  # pragma: no cover
        from packages.common.providers.chat import LLMMessage  # type: ignore[attr-defined]

    messages.append(LLMMessage(role="system", content=system))
    messages.append(LLMMessage(role="user", content=user))

    for _round in range(max_rounds):
        response = await chat.chat(
            messages,
            tools=tools,
            temperature=0,
            max_tokens=2048,
        )
        tool_calls = getattr(response, "tool_calls", None) or []
        content = getattr(response, "content", "") or ""
        if not tool_calls:
            if content:
                result.tool_log.append({"assistant": content[:500]})
            result.closed_as = result.closed_as or "skipped"
            break

        messages.append(
            LLMMessage(role="assistant", content=content or json.dumps([tc.name for tc in tool_calls]))
        )
        for tc in tool_calls:
            name = tc.name
            args = dict(tc.arguments or {})
            result.tool_log.append({"tool": name, "args": args})

            if name in _SINK_TO_KIND:
                kind = _SINK_TO_KIND[name]
                if kind == "pattern" and not allow_pattern:
                    tool_result = json.dumps({"error": "pattern_not_eligible_need_3_same_shape"})
                else:
                    payload = dict(args.get("payload") or args)
                    if kind == "pattern":
                        payload = {
                            "pattern_file": args.get("pattern_file"),
                            "yaml_fragment": args.get("yaml_fragment"),
                            "rationale": args.get("rationale") or "",
                        }
                    if kind == "extractor_change":
                        payload = {
                            "title": args.get("title"),
                            "detail": args.get("detail"),
                        }
                    if kind == "no_finding":
                        payload = {"rationale": args.get("rationale") or ""}
                    prop = CandidateProposal(
                        kind=kind,
                        repository_id=item.repository_id or ctx.repository_id,
                        ledger_item_id=item.item_id,
                        payload=payload,
                        evidence=list(payload.pop("evidence", []) or []),
                        model_id=model_id or getattr(response, "model", "") or "",
                        prompt_version=PROMPT_VERSION,
                        rationale=str(args.get("rationale") or payload.get("rationale") or ""),
                        source_tool=name,
                        detector_id=f"llm_investigate_{item.source}",
                    )
                    verdict = validate_candidate(
                        prop, established_op_keys=ctx.established_op_keys
                    )
                    result.proposals.append(prop)
                    result.verdicts.append(verdict)
                    tool_result = json.dumps(
                        {"accepted": verdict.accepted, "reasons": verdict.reasons}
                    )
                    if kind == "no_finding" and verdict.accepted:
                        result.closed_as = "no_finding"
                    elif verdict.accepted:
                        result.closed_as = "proposed"
            else:
                tool_result = ctx.dispatch(name, args)

            messages.append(LLMMessage(role="tool", content=tool_result))

        if result.closed_as in {"proposed", "no_finding"}:
            break
    else:
        result.closed_as = result.closed_as or "error"

    result.tool_log.append(
        {
            "cache_key": _cache_key(
                repository_id=ctx.repository_id,
                commit_sha=commit_sha,
                item=item,
                patterns_hash=patterns_hash,
            )
        }
    )
    return result


def persist_accepted_proposals(
    store: ShardStore,
    result: InvestigateResult,
) -> list[Proposal]:
    """Append accepted candidates as pending_review Proposal rows."""
    written: list[Proposal] = []
    for prop, verdict in zip(result.proposals, result.verdicts, strict=False):
        if not verdict.accepted:
            continue
        if prop.kind == "no_finding":
            continue
        ch = hashlib.sha256(
            json.dumps(prop.to_dict(), sort_keys=True).encode("utf-8")
        ).hexdigest()
        # Extend kind via payload; Proposal.kind Literal stays label-compatible
        kind_map = {
            "operation": "rationale",
            "relationship": "rationale",
            "process_step": "rationale",
            "capability_link": "rationale",
            "conflict_resolution": "rationale",
            "pattern": "rationale",
            "extractor_change": "rationale",
        }
        p = Proposal(
            proposal_id=f"inv_{ch[:16]}",
            kind=kind_map.get(prop.kind, "rationale"),  # type: ignore[arg-type]
            repository_id=prop.repository_id or "enterprise",
            content_hash=ch,
            payload={
                "investigate_kind": prop.kind,
                "ledger_item_id": prop.ledger_item_id,
                "candidate": prop.payload,
                "evidence": prop.evidence,
                "detector_id": prop.detector_id,
                "model_id": prop.model_id,
                "prompt_version": prop.prompt_version,
                "rationale": prop.rationale,
                "callable": False,
                "gate": verdict.to_dict(),
            },
            confidence=0.55,
            evidence_refs=[prop.ledger_item_id],
            status="pending_review",
            created_at=utc_now_iso(),
        )
        store.append_proposal(p.repository_id, p.to_dict())
        written.append(p)
    return written


def write_run_log(store: ShardStore, repository_id: str, result: InvestigateResult) -> Path:
    dest = store.repo_dir(repository_id) / "investigate" / f"{result.ledger_item_id}.jsonl"
    dest.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps({**result.to_dict(), "written_at": utc_now_iso()})
    with dest.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    return dest


async def investigate_ledger(
    items: list[LedgerItem],
    *,
    chat: Any,
    ctx: InvestigateContext,
    store: ShardStore | None = None,
    max_rounds: int = MAX_ROUNDS_DEFAULT,
    commit_sha: str = "",
    patterns_hash: str = "",
    limit: int | None = None,
) -> list[InvestigateResult]:
    """Investigate open ledger items. Pattern propose only when shape count ≥ 3."""
    eligible = shapes_eligible_for_pattern(items)
    open_items = [i for i in items if i.status == "open"]
    if limit is not None:
        open_items = open_items[:limit]
    results: list[InvestigateResult] = []
    for item in open_items:
        res = await investigate_item(
            item,
            chat=chat,
            ctx=ctx,
            max_rounds=max_rounds,
            allow_pattern=item.shape_key in eligible,
            commit_sha=commit_sha,
            patterns_hash=patterns_hash,
        )
        if store is not None:
            persist_accepted_proposals(store, res)
            write_run_log(store, item.repository_id or ctx.repository_id or "enterprise", res)
        results.append(res)
    return results
