"""Run the MCP listener. Chat on :8000 is unchanged."""

from __future__ import annotations

import uvicorn
from packages.common.settings import get_settings
from packages.mcp_server.server import create_app


def main() -> None:
    cfg = get_settings()
    uvicorn.run(create_app(cfg), host=cfg.mcp.host, port=cfg.mcp.port, log_level="info")


if __name__ == "__main__":
    main()
