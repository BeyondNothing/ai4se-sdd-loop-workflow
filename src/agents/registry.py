"""AI 工具注册表。"""

from .base import AITool
from .claude_code_agent import ClaudeCodeTool
from .cursor_agent import CursorTool
from .echo_agent import EchoTool

_TOOLS: dict[str, AITool] = {
    "cursor": CursorTool(),
    "claude_code": ClaudeCodeTool(),
    "echo": EchoTool(),
}


def get_ai_tool(name: str) -> AITool:
    if name not in _TOOLS:
        raise ValueError(
            f"Unknown AI tool: {name}. Available: {', '.join(_TOOLS.keys())}"
        )
    return _TOOLS[name]
