"""Echo 工具 — 用于本地调试，不调用外部 AI。"""

from datetime import datetime

from .base import AITool, AIToolResult


class EchoTool(AITool):
    name = "echo"

    def run(self, prompt: str, cwd: str) -> AIToolResult:
        content = (
            f"# Echo 模式输出\n\n"
            f"> 生成时间: {datetime.now().isoformat(timespec='seconds')}\n"
            f"> 工作目录: {cwd}\n\n"
            "---\n\n"
            "## Prompt\n\n"
            f"{prompt}\n"
        )
        return AIToolResult(content=content, tool_name=self.name, success=True)

    def run_interactive(
        self,
        prompt: str,
        cwd: str,
        *,
        completion_check=None,
    ) -> AIToolResult:
        print("\n[echo] 交互澄清需要真实 AI CLI；echo 模式跳过交互会话。\n")
        return AIToolResult(
            content="",
            tool_name=self.name,
            success=True,
            message="echo 模式未启动交互 CLI",
        )
