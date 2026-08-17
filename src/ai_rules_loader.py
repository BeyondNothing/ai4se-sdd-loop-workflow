"""加载应用项目 ai-rules 目录下的扩展规则，并按节点 inject 到 prompt。"""

from __future__ import annotations

import logging
from pathlib import Path

from .requirement_dir import resolve_app_root

logger = logging.getLogger(__name__)

DEFAULT_AI_RULES_DIR = "ai-rules"
EMPTY_RULES_HINT = "（无额外项目约束）"


def resolve_ai_rules_dir(
    workflow_root: Path,
    rules_dir: str | None,
    *,
    app_root: str | None = None,
) -> Path:
    """规则目录相对 app_root；rules_dir 为绝对路径时直接使用。"""
    base = resolve_app_root(workflow_root, app_root)
    raw = (rules_dir or DEFAULT_AI_RULES_DIR).strip() or DEFAULT_AI_RULES_DIR
    path = Path(raw)
    if not path.is_absolute():
        path = base / path
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
    """按节点 extend_rules 配置，拼接 ai-rules 下 rule 文件内容。"""
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
