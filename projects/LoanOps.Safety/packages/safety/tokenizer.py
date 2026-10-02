"""PII tokenizer — reversible token replacement for PII spans."""

from __future__ import annotations

from collections import Counter
from typing import Any

from .models import PiiSpan


class PiiTokenizer:
    """Replace detected PII spans with numbered tokens and provide reversal.

    Example::

        tokenizer = PiiTokenizer()
        text = "last pay date for Sam Patel"
        spans = [PiiSpan(entity_type="PERSON", start=18, end=27, original_text="Sam Patel")]
        tokenized, token_map = tokenizer.tokenize(text, spans)
        # tokenized  == "last pay date for [PERSON_1]"
        # token_map  == {"[PERSON_1]": "Sam Patel"}
    """

    @staticmethod
    def tokenize(
        text: str,
        spans: list[PiiSpan],
    ) -> tuple[str, dict[str, str]]:
        """Replace PII spans with deterministic numbered tokens.

        Args:
            text: The original text containing PII.
            spans: Detected PII spans (from Presidio via the safety middleware).

        Returns:
            A tuple of (tokenized_text, token_map) where token_map maps
            token strings like ``[PERSON_1]`` to their original values.
        """
        if not spans:
            return text, {}

        # Sort spans by start offset descending so replacements don't shift indices
        sorted_spans = sorted(spans, key=lambda s: s.start, reverse=True)

        # Count occurrences per entity type for numbering
        entity_counter: Counter[str] = Counter()
        # First pass: assign numbers in forward order
        span_tokens: dict[int, str] = {}
        for span in sorted(spans, key=lambda s: s.start):
            entity_counter[span.entity_type] += 1
            count = entity_counter[span.entity_type]
            token = f"[{span.entity_type}_{count}]"
            span_tokens[span.start] = token

        # Second pass: replace in reverse order to preserve offsets
        token_map: dict[str, str] = {}
        result = text
        for span in sorted_spans:
            token = span_tokens[span.start]
            original_value = result[span.start : span.end]
            token_map[token] = original_value
            result = result[: span.start] + token + result[span.end :]

        return result, token_map

    @staticmethod
    def detokenize(text: str, token_map: dict[str, str]) -> str:
        """Resolve tokens back to their original PII values.

        Args:
            text: Text containing tokens like ``[PERSON_1]``.
            token_map: Mapping from token to original value.

        Returns:
            Text with tokens replaced by original PII values.
        """
        if not token_map:
            return text

        result = text
        for token, original in token_map.items():
            result = result.replace(token, original)
            # Also handle if brackets were stripped (e.g. PERSON_1 instead of [PERSON_1])
            unbracketed = token.strip("[]")
            if unbracketed:
                result = result.replace(unbracketed, original)
        return result

    @staticmethod
    def detokenize_dict(
        args: dict[str, Any],
        token_map: dict[str, str],
    ) -> dict[str, Any]:
        """Walk a dictionary and detokenize all string values.

        This is used to resolve PII tokens in tool call arguments
        before the HTTP call leaves the trust boundary.

        Args:
            args: Tool call arguments (may contain tokens as string values).
            token_map: Mapping from token to original value.

        Returns:
            A new dictionary with all string values detokenized.
        """
        if not token_map:
            return args

        resolved: dict[str, Any] = {}
        for key, value in args.items():
            if isinstance(value, str):
                resolved[key] = PiiTokenizer.detokenize(value, token_map)
            elif isinstance(value, dict):
                resolved[key] = PiiTokenizer.detokenize_dict(value, token_map)
            elif isinstance(value, list):
                resolved[key] = [
                    PiiTokenizer.detokenize(item, token_map) if isinstance(item, str) else item
                    for item in value
                ]
            else:
                resolved[key] = value
        return resolved
