"""加载 workflow 与节点配置。"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


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
    project_rules_dir: str = "project-rules"
    e2e_enabled: bool = True
    e2e_base_url: str = "http://localhost:8080"


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


def _parse_extend_rules(cfg: dict[str, Any]) -> list[str]:
    raw = cfg.get("extend_rules")
    if raw is None:
        raw = cfg.get("extend-rules")
    if not isinstance(raw, list):
        return []
    return [str(item).strip() for item in raw if str(item).strip()]


def load_workflow_config(config_path: Path) -> WorkflowConfig:
    with open(config_path, encoding="utf-8") as f:
        data: dict[str, Any] = yaml.safe_load(f)

    workflow = data["workflow"]
    nodes_raw: dict[str, Any] = data["nodes"]

    e2e = workflow.get("e2e") or {}
    if not isinstance(e2e, dict):
        e2e = {}
    e2e_base_url = str(e2e.get("base_url") or "http://localhost:8080").strip().rstrip("/")
    e2e_enabled = _parse_bool(e2e.get("enabled"), default=True)

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
            extend_rules=_parse_extend_rules(cfg),
        )

    return WorkflowConfig(
        docs_dir=workflow.get("docs_dir", "docs"),
        project_rules_dir=workflow.get("project_rules_dir", "project-rules"),
        e2e_enabled=e2e_enabled,
        e2e_base_url=e2e_base_url,
        nodes=nodes,
    )
