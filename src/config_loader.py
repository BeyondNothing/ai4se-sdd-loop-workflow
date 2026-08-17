"""加载 workflow 与节点配置。"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

AI_RULES_CONFIG_FILENAME = "ai-rules.yaml"


@dataclass
class NodeInput:
    kind: str  # "state" | "doc"
    key: str


@dataclass
class NodeConfig:
    node_id: str
    name: str
    tool: str
    prompt_file: str
    output_file: str
    mode: str = "headless"  # headless | interactive
    inputs: list[NodeInput] = field(default_factory=list)
    extend_rules: list[str] = field(default_factory=list)


@dataclass
class WorkflowConfig:
    docs_dir: str
    nodes: dict[str, NodeConfig]
    ai_rules_dir: str = "ai-rules"
    app_root: str = ".."
    e2e_enabled: bool = True
    e2e_base_url: str = "http://localhost:8080"
    e2e_headless: bool = False


def _parse_bool(value: Any, default: bool = True) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in ("true", "1", "yes", "on"):
        return True
    if text in ("false", "0", "no", "off"):
        return False
    return default


def _parse_input(raw: dict[str, str]) -> NodeInput:
    if "state" in raw:
        return NodeInput(kind="state", key=raw["state"])
    if "doc" in raw:
        return NodeInput(kind="doc", key=raw["doc"])
    raise ValueError(f"Invalid node input config: {raw}")


def _parse_rule_list(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    return [str(item).strip() for item in raw if str(item).strip()]


def load_ai_rules_config(workflow_config_path: Path) -> tuple[str, dict[str, list[str]]]:
    """加载与 workflow.yaml 同级的 ai-rules.yaml（本地配置，不提交仓库）。"""
    path = workflow_config_path.parent / AI_RULES_CONFIG_FILENAME
    if not path.is_file():
        example = workflow_config_path.parent / "ai-rules.example.yaml"
        hint = f"（可参考 {example.name}）" if example.is_file() else ""
        logger.warning(
            "未找到 %s %s，各节点将不注入扩展规则",
            path,
            hint,
        )
        return "ai-rules", {}

    with open(path, encoding="utf-8") as f:
        data: dict[str, Any] = yaml.safe_load(f) or {}

    ai_rules_dir = str(data.get("ai_rules_dir") or "ai-rules").strip() or "ai-rules"

    nodes_raw = data.get("nodes") or {}
    node_rules: dict[str, list[str]] = {}
    if isinstance(nodes_raw, dict):
        for node_id, raw in nodes_raw.items():
            rules = _parse_rule_list(raw)
            if rules:
                node_rules[str(node_id)] = rules

    return ai_rules_dir, node_rules


def load_workflow_config(config_path: Path) -> WorkflowConfig:
    with open(config_path, encoding="utf-8") as f:
        data: dict[str, Any] = yaml.safe_load(f)

    workflow = data["workflow"]
    nodes_raw: dict[str, Any] = data["nodes"]
    ai_rules_dir, node_extend_rules = load_ai_rules_config(config_path)

    e2e = workflow.get("e2e") or {}
    if not isinstance(e2e, dict):
        e2e = {}
    e2e_base_url = str(e2e.get("base_url") or "http://localhost:8080").strip().rstrip("/")
    e2e_enabled = _parse_bool(e2e.get("enabled"), default=True)
    e2e_headless = _parse_bool(e2e.get("headless"), default=False)
    app_root = str(workflow.get("app_root") or "..").strip() or ".."

    nodes: dict[str, NodeConfig] = {}
    for node_id, cfg in nodes_raw.items():
        nodes[node_id] = NodeConfig(
            node_id=node_id,
            name=cfg["name"],
            tool=cfg["tool"],
            prompt_file=cfg["prompt"],
            output_file=cfg["output"],
            mode=cfg.get("mode", "headless"),
            inputs=[_parse_input(i) for i in cfg.get("inputs", [])],
            extend_rules=node_extend_rules.get(node_id, []),
        )

    return WorkflowConfig(
        docs_dir=workflow.get("docs_dir", "docs"),
        ai_rules_dir=ai_rules_dir,
        app_root=app_root,
        e2e_enabled=e2e_enabled,
        e2e_base_url=e2e_base_url,
        e2e_headless=e2e_headless,
        nodes=nodes,
    )
