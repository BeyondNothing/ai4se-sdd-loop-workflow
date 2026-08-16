"""AI 编程工具抽象层 — 每个节点独立调用，互不影响。"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass


@dataclass
class AIToolResult:
    content: str
    tool_name: str
    success: bool
    message: str = ""


CompletionCheck = Callable[[], bool]


class AITool(ABC):
    name: str

    @abstractmethod
    def run(self, prompt: str, cwd: str) -> AIToolResult:
        """非交互模式（headless）执行 prompt，返回 markdown 内容。"""

    def run_interactive(
        self,
        prompt: str,
        cwd: str,
        *,
        completion_check: CompletionCheck | None = None,
    ) -> AIToolResult:
        """交互模式：继承终端 stdin/stdout，用户在 CLI 中与 AI 对话。"""
        return self.run(prompt, cwd)
