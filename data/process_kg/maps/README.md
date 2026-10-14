# Process KG curated maps

Versioned gazetteers for the ADR-028 process extractor.

- Runtime extraction **never** calls an LLM.
- Change any map → bump `version`, recompute `mapsHash`, mark dependent
  processes `reextract_required`.
- `capability_phrases.yaml` maps phrases to `application|METHOD|path` keys.
