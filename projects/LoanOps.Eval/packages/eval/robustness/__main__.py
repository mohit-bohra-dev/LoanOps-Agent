"""``python -m packages.eval.robustness`` → Layer 7 runner."""

from __future__ import annotations

import sys

from packages.eval.robustness.layer7 import main

if __name__ == "__main__":
    sys.exit(main())
