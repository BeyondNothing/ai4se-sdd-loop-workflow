"""交互式 CLI 公共逻辑 — 轮询产出、自动结束进程组。"""

from __future__ import annotations

import logging
import os
import signal
import subprocess
import time

from .base import AIToolResult, CompletionCheck

logger = logging.getLogger(__name__)

_POLL_SECONDS = 1.0


def run_interactive_subprocess(
    cmd: list[str],
    cwd: str,
    *,
    tool_name: str,
    banner_title: str,
    completion_hint: str,
    completion_check: CompletionCheck | None = None,
) -> AIToolResult:
    print("\n" + "=" * 60)
    print(banner_title)
    if completion_check:
        print(completion_hint)
    else:
        print("退出 CLI 后 workflow 继续")
    print("=" * 60 + "\n")

    proc = subprocess.Popen(cmd, cwd=cwd, start_new_session=True)
    try:
        while proc.poll() is None:
            if completion_check and completion_check():
                logger.info("检测到节点产出已完成，结束交互 CLI")
                print("\n节点产出已完成，自动退出 CLI，workflow 继续…\n")
                _stop_process(proc)
                return AIToolResult(
                    content="",
                    tool_name=tool_name,
                    success=True,
                    message="节点产出已完成，已自动退出 CLI",
                )
            time.sleep(_POLL_SECONDS)
    except KeyboardInterrupt:
        _stop_process(proc)
        raise

    return AIToolResult(
        content="",
        tool_name=tool_name,
        success=proc.returncode == 0,
        message="" if proc.returncode == 0 else f"CLI 退出码 {proc.returncode}",
    )


def _stop_process(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    try:
        if hasattr(os, "killpg"):
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        else:
            proc.terminate()
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        try:
            if hasattr(os, "killpg"):
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            else:
                proc.kill()
            proc.wait(timeout=5)
        except (ProcessLookupError, subprocess.TimeoutExpired):
            pass
    except ProcessLookupError:
        pass
