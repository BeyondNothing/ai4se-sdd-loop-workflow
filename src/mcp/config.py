"""MCP 配置加载。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_SERVERS_PATH = Path(__file__).resolve().parents[2] / "config" / "mcp" / "servers.json"
PLAYWRIGHT_SERVER_NAME = "playwright"
_CLI_SERVER_KEYS = frozenset({"command", "args", "url", "env", "headers", "type"})


def _load_servers_file(config_path: Path | None = None) -> dict[str, Any]:
    path = config_path or DEFAULT_SERVERS_PATH
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_mcp_meta(config_path: Path | None = None) -> dict[str, Any]:
    data = _load_servers_file(config_path)
    return data.get("_meta") or {}


def load_cli_mcp_servers(config_path: Path | None = None) -> dict[str, Any]:
    """供 Cursor / Claude CLI 使用的 mcpServers 片段（仅进程/连接字段）。"""
    data = _load_servers_file(config_path)
    raw_servers = data.get("servers") or data.get("mcpServers") or {}
    cli_servers: dict[str, Any] = {}
    for name, raw in raw_servers.items():
        if not isinstance(raw, dict) or raw.get("enabled") is False:
            continue
        cli_entry = {
            key: raw[key]
            for key in _CLI_SERVER_KEYS
            if key in raw and raw[key] is not None
        }
        wrapper = raw.get("wrapper")
        if wrapper:
            cli_entry["wrapper"] = str(wrapper)
        if cli_entry.get("command") or cli_entry.get("url") or cli_entry.get("wrapper"):
            cli_servers[name] = cli_entry
    return cli_servers
