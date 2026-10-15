# EAKG pattern files (ADR-029)

Declarative rules loaded by deterministic extractors/detectors. Reviewed in git.

- `sdk_suffixes.yaml` — NuGet package suffixes for `consumesSdk` / `sharesDto`
- `datastore_owners.yaml` — connection catalog → owning `application_id`

New patterns need a passing `python -m packages.eakg patterns backtest` and human merge.
Patterns only **widen** detection; they never set capability semantics, authz, or callable.
