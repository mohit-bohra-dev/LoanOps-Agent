"""ApiIndex test hooks — scale suite sizing (spec §14.2)."""

from __future__ import annotations

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--scale-profile",
        action="store",
        default="small",
        choices=("small", "full"),
        help="Scale suite size: small (CI default) or full (30×170)",
    )


@pytest.fixture
def scale_profile(request: pytest.FixtureRequest) -> str:
    return str(request.config.getoption("--scale-profile"))


@pytest.fixture
def scale_sizes(scale_profile: str) -> tuple[int, int, int]:
    """Return (apps, ops_per_app, query_count)."""
    if scale_profile == "full":
        return 30, 170, 200
    return 5, 20, 40
