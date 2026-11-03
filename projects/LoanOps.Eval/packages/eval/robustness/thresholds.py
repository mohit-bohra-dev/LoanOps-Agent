"""Layer 7 robustness thresholds — separate from sacred golden thresholds.py."""

from __future__ import annotations

# Default minimum pass-rate across N repeats for a case/variant.
DEFAULT_MIN_PASS_RATE: float = 0.8

# Wilson score confidence level for the lower bound (informational).
WILSON_Z: float = 1.96  # ~95%
