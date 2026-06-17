"""Unit tests for PiiTokenizer."""

from packages.safety.models import PiiSpan
from packages.safety.tokenizer import PiiTokenizer


def test_tokenize_single_person() -> None:
    """Single PERSON span is replaced with [PERSON_1]."""
    text = "last pay date for Sam Patel"
    spans = [PiiSpan(entity_type="PERSON", start=18, end=27, original_text="Sam Patel")]
    tokenized, token_map = PiiTokenizer.tokenize(text, spans)

    assert tokenized == "last pay date for [PERSON_1]"
    assert token_map == {"[PERSON_1]": "Sam Patel"}


def test_tokenize_multiple_same_type() -> None:
    """Multiple PERSON spans get distinct numbered tokens."""
    text = "Transfer from Alex Rivera to Jamie Chen"
    spans = [
        PiiSpan(entity_type="PERSON", start=14, end=25, original_text="Alex Rivera"),
        PiiSpan(entity_type="PERSON", start=29, end=39, original_text="Jamie Chen"),
    ]
    tokenized, token_map = PiiTokenizer.tokenize(text, spans)

    assert "[PERSON_1]" in tokenized
    assert "[PERSON_2]" in tokenized
    assert token_map["[PERSON_1]"] == "Alex Rivera"
    assert token_map["[PERSON_2]"] == "Jamie Chen"


def test_tokenize_no_spans() -> None:
    """Text with no PII spans passes through unchanged."""
    text = "What is the balance on loan 100245?"
    tokenized, token_map = PiiTokenizer.tokenize(text, [])

    assert tokenized == text
    assert token_map == {}


def test_detokenize_roundtrip() -> None:
    """Detokenize reverses tokenize."""
    text = "last pay date for Sam Patel"
    spans = [PiiSpan(entity_type="PERSON", start=18, end=27, original_text="Sam Patel")]
    tokenized, token_map = PiiTokenizer.tokenize(text, spans)
    restored = PiiTokenizer.detokenize(tokenized, token_map)

    assert restored == text


def test_detokenize_dict_resolves_string_values() -> None:
    """detokenize_dict resolves tokens in tool call arguments."""
    token_map = {"[PERSON_1]": "Sam Patel"}
    args = {"name": "[PERSON_1]", "k": 5}
    resolved = PiiTokenizer.detokenize_dict(args, token_map)

    assert resolved["name"] == "Sam Patel"
    assert resolved["k"] == 5


def test_detokenize_dict_nested() -> None:
    """detokenize_dict handles nested dicts."""
    token_map = {"[PERSON_1]": "Sam Patel"}
    args = {"filter": {"borrower": "[PERSON_1]"}, "limit": 10}
    resolved = PiiTokenizer.detokenize_dict(args, token_map)

    assert resolved["filter"]["borrower"] == "Sam Patel"
    assert resolved["limit"] == 10


def test_detokenize_empty_map() -> None:
    """Empty token map returns text unchanged."""
    assert PiiTokenizer.detokenize("hello [PERSON_1]", {}) == "hello [PERSON_1]"
    assert PiiTokenizer.detokenize_dict({"name": "[PERSON_1]"}, {}) == {"name": "[PERSON_1]"}


def test_detokenize_unbracketed() -> None:
    """detokenize handles tokens without brackets (e.g. PERSON_1)."""
    token_map = {"[PERSON_1]": "Sam Patel"}
    assert PiiTokenizer.detokenize("hello PERSON_1", token_map) == "hello Sam Patel"
    assert PiiTokenizer.detokenize_dict({"name": "PERSON_1"}, token_map) == {"name": "Sam Patel"}
