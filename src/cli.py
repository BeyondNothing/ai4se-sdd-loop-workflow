"""sdd-loop-workflow 命令入口。

  sdd-loop-workflow:init / sdd-loop-workflow init
  sdd-loop-workflow:start / sdd-loop-workflow start
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

SKILL_NAME = "start-workflow"

# 相对业务项目根 → (目录, --tool 取值)
AGENT_SKILL_DIRS = {
    "cursor": (".cursor/skills", "cursor"),
    "claude_code": (".claude/skills", "claude_code"),
    "omp": (".omp/skills", "omp"),
}

USAGE = """\
用法:
  sdd-loop-workflow:init [--app-root DIR] [--workflow-root DIR]
  sdd-loop-workflow:start [start.sh 同样的选项...]

  sdd-loop-workflow init   # 同上
  sdd-loop-workflow start  # 同上
"""


def _engine_root() -> Path:
    return Path(__file__).resolve().parent.parent


def skill_template_path(engine: Path) -> Path:
    path = engine / "skills" / SKILL_NAME / "SKILL.md"
    if not path.is_file():
        raise SystemExit(f"错误: 找不到 skill 模板: {path}")
    return path


def _is_engine(path: Path) -> bool:
    return (path / "start.sh").is_file() and (path / "config" / "workflow.yaml").is_file()


def find_engine_root(explicit: Path | None) -> Path:
    if explicit is not None:
        engine = explicit.expanduser().resolve()
        if not _is_engine(engine):
            raise SystemExit(f"错误: 不是 workflow 引擎目录: {engine}")
        return engine

    source = _engine_root()
    if _is_engine(source):
        return source

    cwd = Path.cwd().resolve()
    if _is_engine(cwd):
        return cwd

    children = [p for p in cwd.iterdir() if p.is_dir() and _is_engine(p)]
    if len(children) == 1:
        return children[0].resolve()
    preferred = [p for p in children if p.name == "ai4se-sdd-loop-workflow"]
    if len(preferred) == 1:
        return preferred[0].resolve()
    if len(children) > 1:
        listed = "\n".join(f"  - {p}" for p in children)
        raise SystemExit(f"错误: 多个引擎目录，请用 --workflow-root:\n{listed}")

    for parent in cwd.parents:
        if _is_engine(parent):
            return parent.resolve()

    raise SystemExit("错误: 找不到 workflow 引擎，请传入 --workflow-root。")


def resolve_app_root(engine: Path, explicit: Path | None) -> Path:
    if explicit is not None:
        app_root = explicit.expanduser().resolve()
    else:
        # 与 start 一致：默认绑定运行时当前目录（业务项目根）
        app_root = Path.cwd().resolve()
    if not app_root.is_dir():
        raise SystemExit(f"错误: 业务项目根不存在: {app_root}")
    return app_root


def install_skills(engine: Path, app_root: Path) -> list[Path]:
    template = skill_template_path(engine).read_text(encoding="utf-8")
    written: list[Path] = []
    for _agent, (relative_dir, tool) in AGENT_SKILL_DIRS.items():
        dest = app_root / relative_dir / SKILL_NAME
        if dest.exists():
            shutil.rmtree(dest)
        dest.mkdir(parents=True)
        skill_file = dest / "SKILL.md"
        skill_file.write_text(template.format(tool=tool), encoding="utf-8")
        written.append(skill_file)
    return written


def command_init(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="sdd-loop-workflow:init",
        description="安装 start-workflow skill 到 Cursor / Claude Code / omp",
    )
    parser.add_argument("--app-root", type=Path, default=None, help="业务项目根")
    parser.add_argument("--workflow-root", type=Path, default=None, help="引擎目录（含 start.sh）")
    args = parser.parse_args(argv)

    engine = find_engine_root(args.workflow_root)
    app_root = resolve_app_root(engine, args.app_root)
    written = install_skills(engine, app_root)

    print(f"==> 引擎目录: {engine}")
    print(f"==> 业务项目根: {app_root}")
    for path in written:
        print(f"==> 已安装: {path}")
    return 0


def command_start(argv: list[str]) -> int:
    """转调引擎目录里的 start.sh / start.cmd，参数原样透传。

    启动前把运行时 cwd 写入 SDD_LOOP_WORKFLOW_APP_ROOT，docs 产出落到该目录。
    """
    engine = find_engine_root(None)
    os.environ["SDD_LOOP_WORKFLOW_APP_ROOT"] = str(Path.cwd().resolve())
    if sys.platform == "win32":
        script = engine / "start.cmd"
        if not script.is_file():
            raise SystemExit(f"错误: 找不到 {script}")
        return subprocess.call(
            [str(script), *argv],
            cwd=str(engine),
            env=os.environ.copy(),
        )

    script = engine / "start.sh"
    if not script.is_file():
        raise SystemExit(f"错误: 找不到 {script}")
    if not os.access(script, os.X_OK):
        script.chmod(script.stat().st_mode | 0o111)
    os.execv(str(script), [str(script), *argv])
    return 1  # pragma: no cover


def main(argv: list[str] | None = None) -> None:
    if argv is None:
        argv = sys.argv[1:]
        invoked = Path(sys.argv[0]).name
    else:
        invoked = ""

    if invoked.endswith(":init") or invoked.endswith("-init"):
        raise SystemExit(command_init(argv))
    if invoked.endswith(":start") or invoked.endswith("-start"):
        raise SystemExit(command_start(argv))

    if not argv or argv[0] in {"-h", "--help"}:
        print(USAGE, end="")
        raise SystemExit(0)

    if argv[0] == "init":
        raise SystemExit(command_init(argv[1:]))
    if argv[0] == "start":
        raise SystemExit(command_start(argv[1:]))

    print(f"错误: 未知命令 {argv[0]}\n", file=sys.stderr)
    print(USAGE, file=sys.stderr, end="")
    raise SystemExit(2)


if __name__ == "__main__":
    main()
