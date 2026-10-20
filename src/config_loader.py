"""加载 workflow 与节点配置。"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .requirement_dir import resolve_app_root

logger = logging.getLogger(__name__)

# 业务项目根下的扩展配置目录（init 生成；运行时读 ai-rules + workflow 运行时项）
APP_CONFIG_DIR_NAME = "sdd-loop-workflow-config"
AI_RULES_CONFIG_FILENAME = "ai-rules.yaml"
APP_WORKFLOW_CONFIG_FILENAME = "workflow.yaml"
DEFAULT_AI_RULES_SUBDIR = "ai-rules"
DEFAULT_DOCS_DIR = "spec"
DEFAULT_APP_ROOT = ".."
DEFAULT_E2E_BASE_URL = "http://localhost:8080"


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
    # 无人值守（--auto）专用 prompt；缺省时与 prompt_file 相同
    prompt_file_auto: str = ""
    inputs: list[NodeInput] = field(default_factory=list)
    extend_rules: list[str] = field(default_factory=list)

    def resolve_prompt_file(self, auto: bool) -> str:
        """按是否 --auto 选择人工介入 / 无人值守 prompt。"""
        if auto and self.prompt_file_auto:
            return self.prompt_file_auto
        return self.prompt_file


@dataclass
class WorkflowConfig:
    docs_dir: str
    nodes: dict[str, NodeConfig]
    ai_rules_dir: str = DEFAULT_AI_RULES_SUBDIR
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


def app_config_dir(app_root: Path) -> Path:
    """业务项目根下的 sdd-loop-workflow-config 目录。"""
    return app_root.resolve() / APP_CONFIG_DIR_NAME


def load_ai_rules_config(app_root: Path) -> tuple[str, dict[str, list[str]]]:
    """从业务根 sdd-loop-workflow-config/ai-rules.yaml 加载扩展规则映射。"""
    path = app_config_dir(app_root) / AI_RULES_CONFIG_FILENAME
    if not path.is_file():
        logger.warning(
            "未找到 %s，各节点将不注入扩展规则"
            "（请在业务项目根执行 sdd-loop-workflow:init）",
            path,
        )
        return DEFAULT_AI_RULES_SUBDIR, {}

    with open(path, encoding="utf-8") as f:
        data: dict[str, Any] = yaml.safe_load(f) or {}

    ai_rules_dir = (
        str(data.get("ai_rules_dir") or DEFAULT_AI_RULES_SUBDIR).strip()
        or DEFAULT_AI_RULES_SUBDIR
    )

    nodes_raw = data.get("nodes") or {}
    node_rules: dict[str, list[str]] = {}
    if isinstance(nodes_raw, dict):
        for node_id, raw in nodes_raw.items():
            rules = _parse_rule_list(raw)
            if rules:
                node_rules[str(node_id)] = rules

    return ai_rules_dir, node_rules


def _parse_e2e_block(e2e: Any) -> tuple[bool, bool, str]:
    if not isinstance(e2e, dict):
        e2e = {}
    return (
        _parse_bool(e2e.get("enabled"), default=True),
        _parse_bool(e2e.get("headless"), default=False),
        str(e2e.get("base_url") or DEFAULT_E2E_BASE_URL).strip().rstrip("/")
        or DEFAULT_E2E_BASE_URL,
    )


def load_app_runtime_settings(app_root: Path) -> dict[str, Any]:
    """从业务根 sdd-loop-workflow-config/workflow.yaml 读取 docs_dir / e2e 等。"""
    path = app_config_dir(app_root) / APP_WORKFLOW_CONFIG_FILENAME
    if not path.is_file():
        logger.warning(
            "未找到 %s，将使用引擎 config/workflow.yaml 中的兜底 docs_dir/e2e"
            "（请在业务项目根执行 sdd-loop-workflow:init）",
            path,
        )
        return {}

    with open(path, encoding="utf-8") as f:
        data: dict[str, Any] = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        return {}
    # 兼容误包一层 workflow:
    if "workflow" in data and isinstance(data["workflow"], dict):
        nested = dict(data["workflow"])
        for key in ("docs_dir", "app_root", "e2e"):
            if key not in nested and key in data:
                nested[key] = data[key]
        return nested
    return data


def load_workflow_config(config_path: Path) -> WorkflowConfig:
    with open(config_path, encoding="utf-8") as f:
        data: dict[str, Any] = yaml.safe_load(f)

    engine_workflow = data.get("workflow") or {}
    if not isinstance(engine_workflow, dict):
        engine_workflow = {}
    nodes_raw: dict[str, Any] = data["nodes"]

    # 先用引擎兜底 + 环境变量定位业务根，再读业务侧运行时配置覆盖
    fallback_app_root = (
        str(engine_workflow.get("app_root") or DEFAULT_APP_ROOT).strip() or DEFAULT_APP_ROOT
    )
    workflow_root = config_path.resolve().parent.parent
    resolved_app = resolve_app_root(workflow_root, fallback_app_root)
    app_settings = load_app_runtime_settings(resolved_app)

    docs_dir = str(
        app_settings.get("docs_dir")
        or engine_workflow.get("docs_dir")
        or DEFAULT_DOCS_DIR
    ).strip() or DEFAULT_DOCS_DIR

    e2e_src = app_settings.get("e2e")
    if e2e_src is None:
        e2e_src = engine_workflow.get("e2e")
    e2e_enabled, e2e_headless, e2e_base_url = _parse_e2e_block(e2e_src)

    ai_rules_dir, node_extend_rules = load_ai_rules_config(resolved_app)

    nodes: dict[str, NodeConfig] = {}
    for node_id, cfg in nodes_raw.items():
        prompt = str(cfg["prompt"]).strip()
        prompt_auto = str(cfg.get("prompt_auto") or "").strip() or prompt
        nodes[node_id] = NodeConfig(
            node_id=node_id,
            name=cfg["name"],
            tool=cfg["tool"],
            prompt_file=prompt,
            prompt_file_auto=prompt_auto,
            output_file=cfg["output"],
            mode=cfg.get("mode", "headless"),
            inputs=[_parse_input(i) for i in cfg.get("inputs", [])],
            extend_rules=node_extend_rules.get(node_id, []),
        )

    return WorkflowConfig(
        docs_dir=docs_dir,
        ai_rules_dir=ai_rules_dir,
        # app_root 仍作引擎侧兜底；sdd-loop-workflow:start 用环境变量覆盖
        app_root=fallback_app_root,
        e2e_enabled=e2e_enabled,
        e2e_base_url=e2e_base_url,
        e2e_headless=e2e_headless,
        nodes=nodes,
    )
