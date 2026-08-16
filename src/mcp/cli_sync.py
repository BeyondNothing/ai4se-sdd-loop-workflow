"""将 servers.json 同步到 Cursor / Claude / Codex 的项目级 MCP 配置。

唯一真源：dev-workflow/config/mcp/servers.json
各 CLI 读取位置（由本模块自动生成，勿手改）：
  - Cursor:  {repo}/.cursor/mcp.json
  - Claude:  {repo}/.mcp.json
  - Codex:   {repo}/.codex/config.toml  （项目需被 Codex trust）

Playwright 通过仓库内 scripts/playwright-mcp.sh 启动；sync 时写入本机 clone 内脚本的绝对路径
（非 nvm/node 路径，每台机器 clone 位置不同，由 start.sh / run.py 自动解析）。
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .config import PLAYWRIGHT_SERVER_NAME, load_cli_mcp_servers

logger = logging.getLogger(__name__)


def workspace_roots(project_root: Path) -> list[Path]:
    project_root = project_root.resolve()
    roots = [project_root]
    parent = project_root.parent
    if parent != project_root and (parent / ".git").exists():
        roots.insert(0, parent)
    return roots


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        logger.warning("MCP 配置文件 JSON 无效，将覆盖重建: %s", path)
        return {}
    return data if isinstance(data, dict) else {}


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _merge_servers(existing: dict[str, Any], servers: dict[str, Any]) -> dict[str, Any]:
    merged = dict(existing.get("mcpServers") or {})
    merged.update(servers)
    return {"mcpServers": merged}


def _playwright_wrapper_entry(project_root: Path, wrapper: str) -> dict[str, Any]:
    script = (project_root / wrapper).resolve()
    if not script.exists():
        logger.warning("Playwright wrapper 脚本不存在: %s", script)
    elif not os.access(script, os.X_OK):
        script.chmod(script.stat().st_mode | 0o111)
    return {"command": str(script), "args": []}


def _prepare_cli_servers(project_root: Path, servers: dict[str, Any]) -> dict[str, Any]:
    """将 servers.json 转为各 CLI 可用的 mcpServers。"""
    prepared: dict[str, Any] = {}
    for name, server in servers.items():
        if not isinstance(server, dict):
            continue
        if server.get("url"):
            prepared[name] = server
            continue
        wrapper = server.get("wrapper")
        if wrapper:
            entry = _playwright_wrapper_entry(project_root, str(wrapper))
            env = server.get("env") or {}
            if env:
                entry["env"] = env
            prepared[name] = entry
            continue
        prepared[name] = server
    return prepared


def _toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _server_to_codex_toml(name: str, server: dict[str, Any]) -> str:
    lines = [f"[mcp_servers.{name}]"]
    if server.get("url"):
        lines.append(f"url = {_toml_string(server['url'])}")
        return "\n".join(lines) + "\n"

    command = server.get("command")
    if not command:
        return ""

    lines.append(f"command = {_toml_string(command)}")
    args = server.get("args") or []
    if args:
        args_literal = ", ".join(_toml_string(arg) for arg in args)
        lines.append(f"args = [{args_literal}]")
    env = server.get("env") or {}
    if env:
        env_pairs = ", ".join(
            f"{_toml_string(str(key))} = {_toml_string(str(val))}"
            for key, val in env.items()
        )
        lines.append(f"env = {{ {env_pairs} }}")
    return "\n".join(lines) + "\n"


def sync_codex_mcp(project_root: Path, servers: dict[str, Any]) -> list[Path]:
    written: list[Path] = []
    for root in workspace_roots(project_root):
        codex_dir = root / ".codex"
        codex_dir.mkdir(parents=True, exist_ok=True)
        config_file = codex_dir / "config.toml"
        existing = config_file.read_text(encoding="utf-8") if config_file.exists() else ""
        blocks: list[str] = []

        for name, server in servers.items():
            marker = f"[mcp_servers.{name}]"
            if marker in existing:
                continue
            block = _server_to_codex_toml(name, server)
            if block:
                blocks.append(block)

        if not blocks and config_file.exists():
            written.append(config_file)
            continue

        payload = existing.rstrip()
        if payload:
            payload += "\n\n"
        payload += "\n".join(blocks).rstrip() + "\n"
        config_file.write_text(payload, encoding="utf-8")
        written.append(config_file)
        logger.info("Codex MCP 配置已同步: %s", config_file)
    return written


def sync_cursor_mcp(project_root: Path, servers: dict[str, Any]) -> list[Path]:
    written: list[Path] = []
    for root in workspace_roots(project_root):
        mcp_file = root / ".cursor" / "mcp.json"
        payload = _merge_servers(_read_json(mcp_file), servers)
        _write_json(mcp_file, payload)
        written.append(mcp_file)
        logger.info("Cursor MCP 配置已同步: %s", mcp_file)
    return written


def sync_claude_mcp(project_root: Path, servers: dict[str, Any]) -> list[Path]:
    written: list[Path] = []
    claude_bin = shutil.which("claude")

    for root in workspace_roots(project_root):
        mcp_file = root / ".mcp.json"
        playwright = servers.get(PLAYWRIGHT_SERVER_NAME, {})
        if claude_bin and playwright and _register_claude_project_mcp(claude_bin, root, playwright):
            if mcp_file.exists():
                written.append(mcp_file)
            continue

        payload = _merge_servers(
            _read_json(mcp_file),
            {
                PLAYWRIGHT_SERVER_NAME: {
                    "type": "stdio",
                    "command": playwright.get("command", "npx"),
                    "args": playwright.get("args", []),
                    "env": playwright.get("env") or {},
                }
            }
            if playwright
            else {},
        )
        if payload.get("mcpServers"):
            _write_json(mcp_file, payload)
            written.append(mcp_file)
            logger.info("Claude MCP 配置已同步: %s", mcp_file)
    return written


def _register_claude_project_mcp(
    claude_bin: str, root: Path, playwright: dict[str, Any]
) -> bool:
    mcp_file = root / ".mcp.json"
    if mcp_file.exists():
        existing = _read_json(mcp_file).get("mcpServers") or {}
        if PLAYWRIGHT_SERVER_NAME in existing:
            return True

    command = playwright.get("command")
    args = playwright.get("args") or []
    if not command:
        return False

    cmd = [
        claude_bin,
        "mcp",
        "add",
        "--scope",
        "project",
        PLAYWRIGHT_SERVER_NAME,
        "--",
        command,
        *args,
    ]
    env = playwright.get("env") or {}
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
            env={**os.environ, **{str(k): str(v) for k, v in env.items()}},
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        logger.warning("Claude MCP 注册失败 (%s)，将回退写入 .mcp.json", exc)
        return False

    if proc.returncode != 0:
        stderr = (proc.stderr or proc.stdout or "").strip()
        if "already" in stderr.lower():
            return True
        logger.warning("Claude MCP 注册失败: %s", stderr[:300])
        return False

    logger.info("Claude MCP 已通过 CLI 注册 (project): %s", root)
    return True


def sync_cli_agent_configs(
    project_root: Path,
    *,
    config_path: Path | None = None,
) -> dict[str, Any]:
    """将 config/mcp/servers.json 同步到 Cursor / Claude / Codex 的项目级 MCP 配置。"""
    from .config import load_mcp_meta

    servers = _prepare_cli_servers(project_root, load_cli_mcp_servers(config_path))
    if not servers:
        return {
            "cursor_mcp_files": [],
            "claude_mcp_files": [],
            "codex_mcp_files": [],
            "servers": [],
            "modelscope": "",
        }

    cursor_files = sync_cursor_mcp(project_root, servers)
    claude_files = sync_claude_mcp(project_root, servers)
    codex_files = sync_codex_mcp(project_root, servers)
    meta = load_mcp_meta(config_path)
    return {
        "cursor_mcp_files": [str(p) for p in cursor_files],
        "claude_mcp_files": [str(p) for p in claude_files],
        "codex_mcp_files": [str(p) for p in codex_files],
        "servers": list(servers.keys()),
        "modelscope": meta.get(
            "modelscope",
            "https://modelscope.cn/mcp/servers/@microsoft/playwright-mcp",
        ),
    }


def ensure_mcp_for_agents(
    project_root: Path,
    *,
    config_path: Path | None = None,
) -> dict[str, Any]:
    """启动 workflow 前调用：让 Cursor / Claude / Codex CLI 子进程能直接使用 MCP 工具。"""
    return sync_cli_agent_configs(project_root, config_path=config_path)
