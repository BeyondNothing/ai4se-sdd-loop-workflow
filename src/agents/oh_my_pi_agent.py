"""Oh My Pi (omp) AI 编程工具适配器。

CLI: https://omp.sh/
Headless: omp -p --auto-approve --no-session
Interactive: omp（可选初始 prompt）
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
from pathlib import Path

from .base import AITool, AIToolResult, CompletionCheck
from .interactive_runner import run_interactive_subprocess

logger = logging.getLogger(__name__)

_EXTRA_BIN_DIRS = (Path.home() / ".local" / "bin",)
_WORKING_LINE = re.compile(r"^Working\.+$")
_MIN_NODE_MAJOR = 18


class OhMyPiTool(AITool):
    name = "oh_my_pi"

    def run(self, prompt: str, cwd: str) -> AIToolResult:
        prompt_file = self._save_prompt(prompt, cwd)
        binary = self._resolve_binary()
        if not binary:
            return AIToolResult(
                content=self._fallback_content(prompt),
                tool_name=self.name,
                success=False,
                message=f"Oh My Pi CLI (omp) 不可用，prompt 已保存至 {prompt_file}",
            )

        cmd = self._build_cmd(
            binary,
            prompt,
            headless=True,
            cwd=cwd,
        )
        try:
            logger.info("调用 Oh My Pi CLI (headless): %s", binary)
            proc = subprocess.run(
                cmd,
                cwd=cwd,
                env=self._subprocess_env(),
                capture_output=True,
                text=True,
                timeout=620,
                check=False,
            )
            content = self._extract_content(proc.stdout)
            if proc.returncode == 0 and content:
                return AIToolResult(
                    content=content,
                    tool_name=self.name,
                    success=True,
                )
            stderr = (proc.stderr or "").strip()
            if stderr:
                logger.warning("Oh My Pi CLI stderr: %s", stderr[:500])
            message = stderr or f"Oh My Pi CLI 退出码 {proc.returncode}"
            return AIToolResult(
                content=content or self._fallback_content(prompt),
                tool_name=self.name,
                success=False,
                message=message,
            )
        except subprocess.TimeoutExpired:
            return AIToolResult(
                content="",
                tool_name=self.name,
                success=False,
                message="Oh My Pi CLI 执行超时",
            )

    def run_interactive(
        self,
        prompt: str,
        cwd: str,
        *,
        completion_check: CompletionCheck | None = None,
    ) -> AIToolResult:
        prompt_file = self._save_prompt(prompt, cwd)
        binary = self._resolve_binary()
        if not binary:
            return AIToolResult(
                content="",
                tool_name=self.name,
                success=False,
                message=f"Oh My Pi CLI (omp) 不可用，prompt 已保存至 {prompt_file}",
            )

        cmd = self._build_cmd(
            binary,
            prompt,
            headless=False,
            cwd=cwd,
        )
        self._print_interactive_banner(cwd, cmd)
        try:
            logger.info("交互调用 Oh My Pi CLI: %s", binary)
            return run_interactive_subprocess(
                cmd,
                cwd,
                tool_name=self.name,
                banner_title="进入 Oh My Pi (omp) 交互会话",
                completion_hint="产出文件写入后将自动退出并继续 workflow",
                completion_check=completion_check,
                env=self._subprocess_env(),
            )
        except FileNotFoundError:
            return AIToolResult(
                content="",
                tool_name=self.name,
                success=False,
                message=f"Oh My Pi CLI (omp) 不可用，prompt 已保存至 {prompt_file}",
            )

    @classmethod
    def _build_cmd(
        cls,
        binary: str,
        prompt: str,
        *,
        headless: bool,
        cwd: str,
    ) -> list[str]:
        cmd: list[str] = [binary]
        project_root = cls._resolve_omp_project_root(cwd)
        if project_root is not None:
            cmd.extend(["--cwd", str(project_root)])
        config_overlay = cls._resolve_omp_config_overlay(cwd, project_root)
        if config_overlay:
            cmd.extend(["--config", config_overlay])
        if headless:
            cmd.extend(
                [
                    "-p",
                    "--auto-approve",
                    "--no-session",
                    "--mode",
                    "text",
                    "--max-time",
                    "600",
                ]
            )
        else:
            cmd.append("--auto-approve")
        cmd.append(prompt)
        logger.info("Oh My Pi 命令: %s", " ".join(cmd[:6]) + (" ..." if len(cmd) > 6 else ""))
        return cmd

    @classmethod
    def _resolve_omp_project_root(cls, cwd: str) -> Path | None:
        base = Path(cwd).resolve()
        for candidate in (base, base / "dev-workflow", base.parent):
            if (candidate / ".omp" / "mcp.json").is_file():
                return candidate.resolve()
        return None

    @classmethod
    def _resolve_omp_config_overlay(
        cls, cwd: str, project_root: Path | None = None
    ) -> str | None:
        roots: list[Path] = []
        if project_root is not None:
            roots.append(project_root)
        base = Path(cwd).resolve()
        roots.extend([base, base / "dev-workflow"])
        seen: set[str] = set()
        for root in roots:
            root_key = str(root)
            if root_key in seen:
                continue
            seen.add(root_key)
            for candidate in (
                root / ".omp" / "config.yml",
                root / "config" / "omp-workflow.yaml",
                root / "dev-workflow" / "config" / "omp-workflow.yaml",
            ):
                if candidate.is_file():
                    return str(candidate.resolve())
        return None

    @classmethod
    def verify_playwright_mcp(cls, cwd: str) -> bool:
        """Headless 预检：omp 会话是否可见 Playwright MCP 工具。"""
        binary = cls._resolve_binary()
        if not binary:
            return False
        probe = (
            "List tool names containing playwright only, one per line. "
            "If none, reply NONE."
        )
        cmd = cls._build_cmd(binary, probe, headless=True, cwd=cwd)
        try:
            proc = subprocess.run(
                cmd,
                cwd=cwd,
                env=cls._subprocess_env(),
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
        output = f"{proc.stdout or ''}\n{proc.stderr or ''}"
        return "playwright_browser_" in output.lower()

    @classmethod
    def _print_interactive_banner(cls, cwd: str, cmd: list[str]) -> None:
        project_root = cls._resolve_omp_project_root(cwd)
        mcp_file = (
            project_root / ".omp" / "mcp.json" if project_root is not None else None
        )
        config_file = cls._resolve_omp_config_overlay(cwd, project_root)
        print("\n--- Oh My Pi / Playwright MCP ---")
        if project_root is not None:
            print(f"项目根 (--cwd): {project_root}")
        if mcp_file is not None:
            print(f"MCP 配置: {mcp_file}")
        if config_file:
            print(f"browser 覆盖 (--config): {config_file}")
        print("进入 omp 后请先执行: /mcp list")
        print("判定 connected 即可继续 E2E；ListMcpResources 为空是正常的。")
        print("工具名形如: mcp_pi-agent_mcp__playwright_browser_navigate")
        print("---\n")

    @staticmethod
    def _save_prompt(prompt: str, cwd: str) -> Path:
        prompt_file = Path(cwd) / ".dev-workflow" / "last_prompt.txt"
        prompt_file.parent.mkdir(parents=True, exist_ok=True)
        prompt_file.write_text(prompt, encoding="utf-8")
        return prompt_file

    @classmethod
    def _subprocess_env(cls) -> dict[str, str]:
        env = os.environ.copy()
        env.setdefault("OMP_MCP_TIMEOUT_MS", "120000")
        node_bin = cls._resolve_node_bin_dir()
        if node_bin:
            env["PATH"] = f"{node_bin}{os.pathsep}{env.get('PATH', '')}"
        return env

    @classmethod
    def _resolve_node_bin_dir(cls) -> str | None:
        major = cls._node_major_version()
        if major >= _MIN_NODE_MAJOR:
            node = shutil.which("node")
            return str(Path(node).parent) if node else None

        nvm_sh = Path.home() / ".nvm" / "nvm.sh"
        if not nvm_sh.is_file():
            return None
        try:
            proc = subprocess.run(
                ["bash", "-lc", f"source {nvm_sh} && nvm use 20 >/dev/null 2>&1 || nvm use 18 >/dev/null 2>&1; dirname \"$(command -v node)\""],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return None
        path = (proc.stdout or "").strip().splitlines()
        if not path:
            return None
        node_dir = path[-1].strip()
        return node_dir or None

    @staticmethod
    def _node_major_version() -> int:
        if not shutil.which("node"):
            return 0
        try:
            proc = subprocess.run(
                ["node", "-p", "process.versions.node.split('.')[0]"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            return int((proc.stdout or "0").strip() or "0")
        except (ValueError, subprocess.TimeoutExpired):
            return 0

    @classmethod
    def _resolve_binary(cls) -> str | None:
        search_path = os.environ.get("PATH", "")
        for extra in _EXTRA_BIN_DIRS:
            if extra.is_dir():
                search_path = f"{extra}{os.pathsep}{search_path}"
        for name in ("omp", "oh-my-pi"):
            path = shutil.which(name, path=search_path)
            if path:
                return path
        return None

    @classmethod
    def _extract_content(cls, stdout: str) -> str:
        lines: list[str] = []
        for line in stdout.splitlines():
            stripped = line.strip()
            if not stripped or _WORKING_LINE.match(stripped):
                continue
            lines.append(line.rstrip())
        return "\n".join(lines).strip()

    @staticmethod
    def _fallback_content(prompt: str) -> str:
        return (
            "# Oh My Pi 工具未就绪\n\n"
            "> 请安装 omp CLI（https://omp.sh/）并配置认证后重试，或手动执行以下 prompt。\n\n"
            "---\n\n"
            f"{prompt}"
        )
