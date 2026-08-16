"""加载 project-rules 目录下的项目定制约束，并按节点注入 prompt。"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_RULES_DIR = "project-rules"
EMPTY_RULES_HINT = "（无额外项目约束）"


def resolve_rules_dir(project_root: Path, rules_dir: str | None = None) -> Path:
    return project_root / (rules_dir or DEFAULT_RULES_DIR)


def load_rule_content(rules_dir: Path, rule_file: str) -> str:
    path = rules_dir / rule_file
    if not path.is_file():
        logger.warning("project-rules 规则文件不存在: %s", path)
        return ""
    return path.read_text(encoding="utf-8").strip()


def build_project_rules_prompt(
    project_root: Path,
    extend_rules: list[str],
    *,
    rules_dir: str | None = None,
) -> str:
    """按节点 extend_rules 配置，拼接 project-rules/ 下 rule 文件内容。"""
    if not extend_rules:
        return EMPTY_RULES_HINT

    base = resolve_rules_dir(project_root, rules_dir)
    if not base.is_dir():
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
