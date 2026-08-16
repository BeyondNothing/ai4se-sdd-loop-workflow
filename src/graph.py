"""LangGraph 图导出 — 供 langgraph dev 使用。"""

from pathlib import Path

from src.workflow import DevWorkflow

PROJECT_ROOT = Path(__file__).parent.parent
graph = DevWorkflow(PROJECT_ROOT).graph
