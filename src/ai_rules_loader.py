"""加载业务项目 sdd-loop-workflow-config 下的扩展规则，并按节点 inject 到 prompt。"""

from __future__ import annotations

import logging
from pathlib import Path

from .config_loader import APP_CONFIG_DIR_NAME, DEFAULT_AI_RULES_SUBDIR
from .requirement_dir import resolve_app_root

logger = logging.getLogger(__name__)

EMPTY_RULES_HINT = "（无额外项目约束）"


def resolve_ai_rules_dir(
    workflow_root: Path,
    rules_dir: str | None,
    *,
    app_root: str | None = None,
) -> Path:
    """规则 markdown 目录：相对 sdd-loop-workflow-config/；绝对路径则直接使用。"""
    app = resolve_app_root(workflow_root, app_root)
    config_root = app / APP_CONFIG_DIR_NAME
    raw = (rules_dir or DEFAULT_AI_RULES_SUBDIR).strip() or DEFAULT_AI_RULES_SUBDIR
    path = Path(raw)
    if not path.is_absolute():
        path = config_root / path
    return path.resolve()


def load_rule_content(rules_dir: Path, rule_file: str) -> str:
    path = rules_dir / rule_file
    if not path.is_file():
        logger.warning("ai-rules 规则文件不存在: %s", path)
        return ""
    return path.read_text(encoding="utf-8").strip()


def build_ai_rules_prompt(
    workflow_root: Path,
    extend_rules: list[str],
    *,
    rules_dir: str | None = None,
    app_root: str | None = None,
) -> str:
    """按节点 extend_rules 配置，拼接规则 markdown 内容。"""
    if not extend_rules:
        return EMPTY_RULES_HINT

    base = resolve_ai_rules_dir(workflow_root, rules_dir, app_root=app_root)
    if not base.is_dir():
        logger.warning("ai-rules 目录不存在: %s", base)
        return EMPTY_RULES_HINT

    sections: list[str] = []
    for rule_file in extend_rules:
        content = load_rule_content(base, rule_file)
        if not content:
            continue
        sections.append(f"### {rule_file}\n\n{content}")

    if not sections:
        return EMPTY_RULES_HINT

    return "\n\n---\n\n".join(sections)
