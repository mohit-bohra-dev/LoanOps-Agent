"""Pinned extract prompt + schema versions (cache key inputs)."""

from __future__ import annotations

PROMPT_VERSION = "1"
SCHEMA_VERSION = "1"

EXTRACT_SYSTEM = """You extract policy entities and relations from mortgage servicing SOP text.
Return ONLY JSON matching this schema:
{"entities":[{"name":"string","type":"string"}],"relations":[{"source":"string","target":"string","type":"string"}]}
Rules:
- Use verbatim names that appear in the text (policies, states, agencies, products, procedures).
- Prefer short names (e.g. "forbearance", "Florida", "SCRA").
- Relations must connect two entity names that both appear in the text.
- No PII (no person names, phones, emails, SSNs).
- Empty lists are OK if nothing clear.
"""

EXTRACT_USER_TEMPLATE = """Chunk path: {path}

Text:
{text}
"""
