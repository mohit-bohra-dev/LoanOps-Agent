# /check-providers

Verify the Provider Abstraction invariants hold across the codebase.

1. `grep -R "from packages.common.providers.*import.*Provider" apps/ packages/agent_core packages/rag packages/safety packages/eval` â€” must return zero matches for concrete classes.
2. `grep -RnE "os\.environ|os\.getenv" --include="*.py" .` excluding `settings.py` and `tests/` â€” must be empty.
3. Run `pytest packages/common/providers/contract_tests` â€” all green.
4. Run `mypy --strict packages/common` â€” no errors.
