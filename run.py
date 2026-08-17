#!/usr/bin/env python3
"""运行 dev-workflow 的 CLI 入口。"""

import argparse
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from src.workflow import DevWorkflow  # noqa: E402
from src.mcp import ensure_mcp_for_agents  # noqa: E402
from src.config_loader import load_workflow_config  # noqa: E402
from src.requirement_dir import resolve_app_root, resolve_docs_path  # noqa: E402


def main():
    load_dotenv(PROJECT_ROOT / ".env")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    parser = argparse.ArgumentParser(description="需求 → 代码 → 测试 工程化 Workflow")
    parser.add_argument(
        "requirement",
        nargs="?",
        help="原始需求描述（也可用 --file 传入）",
    )
    parser.add_argument(
        "--file", "-f",
        type=Path,
        help="从文件读取需求",
    )
    parser.add_argument(
        "--name", "-n",
        default=None,
        help="需求目录名（默认从文件名或需求首行推导），产出落在 <应用根>/docs/<name>/",
    )
    parser.add_argument(
        "--docs-dir",
        default=None,
        help="覆盖完整产出目录（相对应用根或绝对路径；默认 <应用根>/docs/<需求名>/）",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=PROJECT_ROOT / "config" / "workflow.yaml",
        help="workflow 配置文件路径",
    )
    parser.add_argument(
        "--tool",
        choices=["cursor", "claude_code", "oh_my_pi", "omp", "echo"],
        help="覆盖所有节点的 AI 工具（调试用，修改 config/workflow.yaml 可永久配置）",
    )
    parser.add_argument(
        "--skip-clarification",
        action="store_true",
        help="跳过需求澄清 loop（适用于 echo 调试或非交互场景）",
    )
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="清除该需求目录下已有产出（保留 00-requirement.md），从头开始",
    )
    parser.add_argument(
        "--skip-mcp-setup",
        action="store_true",
        help="跳过 Playwright MCP 自动配置（调试用）",
    )
    args = parser.parse_args()
    wf_cfg = load_workflow_config(args.config)
    app_root = resolve_app_root(PROJECT_ROOT, wf_cfg.app_root)

    source_file = None
    requirement = None

    if args.file:
        source_file = args.file.resolve()
        requirement = source_file.read_text(encoding="utf-8")
    elif args.requirement:
        requirement = args.requirement
    elif args.name:
        existing = resolve_docs_path(
            app_root, f"{wf_cfg.docs_dir.strip('/')}/{args.name}"
        ) / "00-requirement.md"
        if existing.is_file():
            source_file = existing
            requirement = existing.read_text(encoding="utf-8")
            logging.info("从已有产出读取需求: %s", existing)

    if requirement is None:
        if args.name:
            named_sample = (
                app_root / wf_cfg.docs_dir / "requirements" / f"{args.name}-requirement.md"
            )
            if named_sample.is_file():
                source_file = named_sample
                requirement = named_sample.read_text(encoding="utf-8")
                logging.info("从 docs/requirements 读取需求: %s", named_sample)

    if requirement is None:
        default_sample = app_root / wf_cfg.docs_dir / "requirements" / "jwt-login-requirement.md"
        if default_sample.is_file():
            source_file = default_sample
            requirement = default_sample.read_text(encoding="utf-8")
            logging.info("未传需求，使用默认: %s", default_sample)
        else:
            parser.error("请提供 requirement、--file，或 --name（且 docs/<name>/00-requirement.md 已存在）")

    if not args.skip_mcp_setup:
        if wf_cfg.e2e_enabled:
            mcp_result = ensure_mcp_for_agents(
                PROJECT_ROOT,
                e2e_headless=wf_cfg.e2e_headless,
            )
            logging.info(
                "MCP 已同步 (servers=%s, headless=%s, cursor=%s, omp=%s, omp_cfg=%s)",
                mcp_result.get("servers", []),
                wf_cfg.e2e_headless,
                ", ".join(mcp_result.get("cursor_mcp_files", [])),
                ", ".join(mcp_result.get("omp_mcp_files", [])),
                ", ".join(mcp_result.get("omp_config_files", [])),
            )
            verify_tool = wf_cfg.nodes.get("verify_tests")
            active_tool = args.tool or (verify_tool.tool if verify_tool else None)
            if active_tool in ("oh_my_pi", "omp"):
                from src.agents.oh_my_pi_agent import OhMyPiTool

                ok = OhMyPiTool.verify_playwright_mcp(str(app_root))
                if ok:
                    logging.info("Oh My Pi Playwright MCP 预检通过")
                else:
                    logging.warning(
                        "Oh My Pi Playwright MCP 预检失败：请确认已在项目根执行 ./start.sh，"
                        "且 .omp/config.yml + .omp/mcp.json 存在；进入 omp 后执行 /mcp list 查看 playwright"
                    )
        else:
            logging.info(
                "E2E 已关闭 (workflow.e2e.enabled=false)，跳过 Playwright MCP 配置"
            )

    workflow = DevWorkflow(PROJECT_ROOT, args.config)

    if args.tool:
        for node in workflow.workflow_config.nodes.values():
            node.tool = args.tool

    result = workflow.run(
        requirement=requirement,
        docs_dir=args.docs_dir,
        name=args.name,
        source_file=source_file,
        skip_clarification=args.skip_clarification,
        fresh=args.fresh,
    )

    if not result.get("resume_from_node") and result.get("test_passed"):
        print("\n=== Workflow 已完成（无需续跑）===")
        print(f"需求目录: {result.get('docs_dir', '')}")
        return

    print("\n=== Workflow 完成 ===")
    print(f"需求目录: {result.get('docs_dir', '')}")
    print(f"需求 slug: {result.get('requirement_slug', '')}")
    print(f"启动节点: {result.get('resume_from_node', '')}")
    print(f"澄清轮次: {result.get('clarification_round', 0)}")
    print(f"澄清完成: {result.get('clarification_resolved', False)}")
    print(f"需求类型: {result.get('requirement_type', 'unknown')}")
    print(f"需求摘要: {result.get('requirement_summary', '')}")
    print(f"变更范围: {result.get('change_scope', '')}")
    print(f"影响模块: {result.get('affected_modules', [])}")
    print(f"兼容风险: {result.get('compatibility_risk', 'unknown')}")
    print(f"测试通过: {result.get('test_passed', False)}")
    print("产出文档:")
    for node_id, path in result.get("node_outputs", {}).items():
        print(f"  - [{node_id}] {path}")
    if result.get("last_error"):
        print(f"最后错误: {result['last_error']}")


if __name__ == "__main__":
    main()
