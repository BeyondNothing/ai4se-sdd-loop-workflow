"""解析 / 写入 Markdown 产出中的 Workflow 状态表。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


STATUS_HEADING = "## Workflow 状态"
VALID_STATUS = frozenset({"completed", "in_progress", "failed"})


@dataclass
class WorkflowStatus:
    node: str = ""
    status: str = "completed"
    next_node: str = ""
    phase: str = ""
    pending_count: int = 0
    all_resolved: bool = True
    updated_at: str = ""
    test_passed: bool | None = None

    @classmethod
    def from_mapping(cls, data: dict[str, str]) -> WorkflowStatus:
        pending_raw = data.get("pending_count", "0").strip()
        try:
            pending_count = int(pending_raw or 0)
        except ValueError:
            pending_count = 0

        all_raw = data.get("all_resolved", "true").strip().lower()
        all_resolved = all_raw in ("true", "yes", "1", "是")

        status = data.get("status", "completed").strip().lower()
        if status not in VALID_STATUS:
            status = "completed"

        return cls(
            node=data.get("node", "").strip(),
            status=status,
            next_node=data.get("next_node", "").strip(),
            phase=data.get("phase", "").strip(),
            pending_count=pending_count,
            all_resolved=all_resolved,
            updated_at=data.get("updated_at", "").strip(),
            test_passed=_parse_optional_bool(data.get("test_passed")),
        )

    def to_mapping(self) -> dict[str, str]:
        data = {
            "node": self.node,
            "status": self.status,
            "next_node": self.next_node,
            "phase": self.phase,
            "pending_count": str(self.pending_count),
            "all_resolved": str(self.all_resolved).lower(),
            "updated_at": self.updated_at or datetime.now().isoformat(timespec="seconds"),
        }
        if self.test_passed is not None:
            data["test_passed"] = "true" if self.test_passed else "false"
        return data


def parse_workflow_status(content: str) -> WorkflowStatus | None:
    """从 Markdown 正文解析 `## Workflow 状态` 表格。"""
    idx = content.find(STATUS_HEADING)
    if idx < 0:
        return None

    section = content[idx:]
    rows = _parse_markdown_table(section)
    if not rows:
        return None
    return WorkflowStatus.from_mapping(rows)


def parse_workflow_status_file(path: Path) -> WorkflowStatus | None:
    if not path.exists():
        return None
    return parse_workflow_status(path.read_text(encoding="utf-8"))


def render_workflow_status_table(status: WorkflowStatus) -> str:
    data = status.to_mapping()
    lines = [
        STATUS_HEADING,
        "",
        "| 字段 | 值 |",
        "|------|-----|",
    ]
    for key, value in data.items():
        lines.append(f"| {key} | {value} |")
    return "\n".join(lines)


def upsert_workflow_status(content: str, status: WorkflowStatus) -> str:
    """替换或追加 Workflow 状态表。"""
    table = render_workflow_status_table(status)
    if STATUS_HEADING in content:
        prefix = content.split(STATUS_HEADING, 1)[0].rstrip()
        return f"{prefix}\n\n{table}\n"
    return f"{content.rstrip()}\n\n{table}\n"


def _parse_optional_bool(raw: str | None) -> bool | None:
    if raw is None:
        return None
    value = raw.strip().lower()
    if not value:
        return None
    if value in ("true", "yes", "1", "通过"):
        return True
    if value in ("false", "no", "0", "失败"):
        return False
    return None


def _parse_markdown_table(section: str) -> dict[str, str]:
    rows: dict[str, str] = {}
    in_table = False
    for line in section.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            if in_table:
                break
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) < 2:
            continue
        if cells[0] in ("字段", "---", ":---"):
            in_table = True
            continue
        in_table = True
        rows[cells[0]] = cells[1]
    return rows
