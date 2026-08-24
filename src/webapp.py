"""Lightweight web UI backend for project binding and workflow orchestration."""

from __future__ import annotations

import json
import logging
import subprocess
import sys
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import yaml

from .config_loader import load_workflow_config
from .mcp import ensure_mcp_for_agents
from .workflow import DevWorkflow

logger = logging.getLogger(__name__)

NODE_IDS = (
    "analyze_requirements",
    "create_plan",
    "design_test_cases",
    "review_plan_and_tests",
    "split_tasks",
    "implement_code",
    "verify_tests",
)


@dataclass
class ProjectBinding:
    project_id: str
    name: str
    app_root: str
    docs_dir: str = "docs"
    ai_rules_dir: str = "ai-rules"
    node_rules: dict[str, list[str]] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "name": self.name,
            "app_root": self.app_root,
            "docs_dir": self.docs_dir,
            "ai_rules_dir": self.ai_rules_dir,
            "node_rules": self.node_rules,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "ProjectBinding":
        return cls(
            project_id=str(raw["project_id"]),
            name=str(raw["name"]),
            app_root=str(raw["app_root"]),
            docs_dir=str(raw.get("docs_dir") or "docs"),
            ai_rules_dir=str(raw.get("ai_rules_dir") or "ai-rules"),
            node_rules={
                str(k): [str(item) for item in (v or [])]
                for k, v in (raw.get("node_rules") or {}).items()
            },
            created_at=str(raw.get("created_at") or datetime.now().isoformat(timespec="seconds")),
            updated_at=str(raw.get("updated_at") or datetime.now().isoformat(timespec="seconds")),
        )


@dataclass
class WorkflowRun:
    run_id: str
    project_id: str
    status: str = "queued"
    requirement: str = ""
    requirement_path: str = ""
    requirement_name: str = ""
    tool: str = "echo"
    skip_clarification: bool = True
    fresh: bool = False
    headless_all_nodes: bool = True
    skip_mcp_setup: bool = False
    docs_dir: str = ""
    started_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    ended_at: str = ""
    result: dict[str, Any] | None = None
    error: str = ""
    logs: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "project_id": self.project_id,
            "status": self.status,
            "requirement": self.requirement,
            "requirement_path": self.requirement_path,
            "requirement_name": self.requirement_name,
            "tool": self.tool,
            "skip_clarification": self.skip_clarification,
            "fresh": self.fresh,
            "headless_all_nodes": self.headless_all_nodes,
            "skip_mcp_setup": self.skip_mcp_setup,
            "docs_dir": self.docs_dir,
            "started_at": self.started_at,
            "updated_at": self.updated_at,
            "ended_at": self.ended_at,
            "result": self.result,
            "error": self.error,
            "logs": self.logs,
        }


class WebState:
    def __init__(self, workflow_root: Path):
        self.workflow_root = workflow_root.resolve()
        self.state_dir = self.workflow_root / ".dev-workflow" / "web-ui"
        self.runtime_dir = self.state_dir / "runtime"
        self.bindings_file = self.state_dir / "bindings.json"
        self.tasks_file = self.state_dir / "tasks.json"
        self.bindings: dict[str, ProjectBinding] = {}
        self.tasks_by_project: dict[str, list[dict[str, Any]]] = {}
        self.runs: dict[str, WorkflowRun] = {}
        self.lock = threading.Lock()
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        self._load_bindings()
        self._load_tasks()

    def _load_bindings(self) -> None:
        if not self.bindings_file.exists():
            self.bindings = {}
            return
        raw = json.loads(self.bindings_file.read_text(encoding="utf-8"))
        self.bindings = {
            item["project_id"]: ProjectBinding.from_dict(item)
            for item in (raw if isinstance(raw, list) else [])
        }

    def _save_bindings(self) -> None:
        payload = [binding.to_dict() for binding in self.bindings.values()]
        self.bindings_file.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def _load_tasks(self) -> None:
        if not self.tasks_file.exists():
            self.tasks_by_project = {}
            return
        raw = json.loads(self.tasks_file.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            self.tasks_by_project = {}
            return
        normalized: dict[str, list[dict[str, Any]]] = {}
        for project_id, tasks in raw.items():
            if not isinstance(tasks, list):
                continue
            normalized[str(project_id)] = [
                task
                for task in tasks
                if isinstance(task, dict) and str(task.get("task_id") or "").strip()
            ]
        self.tasks_by_project = normalized

    def _save_tasks(self) -> None:
        self.tasks_file.write_text(
            json.dumps(self.tasks_by_project, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def list_bindings(self) -> list[dict[str, Any]]:
        with self.lock:
            return [binding.to_dict() for binding in self.bindings.values()]

    def create_binding(
        self,
        *,
        name: str,
        app_root: str,
        docs_dir: str = "docs",
        ai_rules_dir: str = "ai-rules",
    ) -> dict[str, Any]:
        path = Path(app_root).expanduser().resolve()
        if not path.is_dir():
            raise ValueError(f"Project path does not exist: {path}")

        with self.lock:
            project_id = uuid.uuid4().hex[:12]
            now = datetime.now().isoformat(timespec="seconds")
            binding = ProjectBinding(
                project_id=project_id,
                name=name.strip() or path.name,
                app_root=str(path),
                docs_dir=docs_dir.strip() or "docs",
                ai_rules_dir=ai_rules_dir.strip() or "ai-rules",
                created_at=now,
                updated_at=now,
            )
            self.bindings[project_id] = binding
            self._save_bindings()
            return binding.to_dict()

    def update_binding(
        self,
        project_id: str,
        *,
        name: str,
        app_root: str,
        docs_dir: str,
        ai_rules_dir: str,
    ) -> dict[str, Any]:
        path = Path(app_root).expanduser().resolve()
        if not path.is_dir():
            raise ValueError(f"Project path does not exist: {path}")

        with self.lock:
            binding = self.bindings.get(project_id)
            if binding is None:
                raise KeyError(f"Unknown project_id: {project_id}")
            binding.name = name.strip() or path.name
            binding.app_root = str(path)
            binding.docs_dir = docs_dir.strip() or "docs"
            binding.ai_rules_dir = ai_rules_dir.strip() or "ai-rules"
            binding.updated_at = datetime.now().isoformat(timespec="seconds")
            self.bindings[project_id] = binding
            self._save_bindings()
            return binding.to_dict()

    def delete_binding(self, project_id: str) -> None:
        with self.lock:
            if project_id not in self.bindings:
                raise KeyError(f"Unknown project_id: {project_id}")
            del self.bindings[project_id]
            self.tasks_by_project.pop(project_id, None)
            stale_runs = [
                run_id for run_id, run in self.runs.items() if run.project_id == project_id
            ]
            for run_id in stale_runs:
                del self.runs[run_id]
            self._save_bindings()
            self._save_tasks()

    def get_binding(self, project_id: str) -> ProjectBinding:
        with self.lock:
            binding = self.bindings.get(project_id)
        if binding is None:
            raise KeyError(f"Unknown project_id: {project_id}")
        return binding

    def update_rules(
        self,
        project_id: str,
        *,
        ai_rules_dir: str,
        node_rules: dict[str, list[str]],
    ) -> dict[str, Any]:
        with self.lock:
            binding = self.bindings.get(project_id)
            if binding is None:
                raise KeyError(f"Unknown project_id: {project_id}")
            binding.ai_rules_dir = ai_rules_dir.strip() or "ai-rules"
            binding.node_rules = {
                node_id: [item.strip() for item in rules if item.strip()]
                for node_id, rules in node_rules.items()
                if node_id in NODE_IDS
            }
            binding.updated_at = datetime.now().isoformat(timespec="seconds")
            self.bindings[project_id] = binding
            self._save_bindings()
            return binding.to_dict()

    def list_tasks(self, project_id: str) -> list[dict[str, Any]]:
        with self.lock:
            return list(self.tasks_by_project.get(project_id, []))

    def create_task(self, project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            if project_id not in self.bindings:
                raise KeyError(f"Unknown project_id: {project_id}")
            now = datetime.now().isoformat(timespec="seconds")
            task = {
                "task_id": uuid.uuid4().hex,
                "task_name": str(payload.get("task_name") or "").strip(),
                "requirement_prd_path": str(payload.get("requirement_prd_path") or ""),
                "requirement_text": str(payload.get("requirement_text") or ""),
                "created_at": now,
                "updated_at": now,
            }
            if not task["task_name"]:
                raise ValueError("task_name is required")
            self.tasks_by_project.setdefault(project_id, [])
            self.tasks_by_project[project_id].insert(0, task)
            self._save_tasks()
            return task

    def update_task(
        self, project_id: str, task_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        with self.lock:
            tasks = self.tasks_by_project.get(project_id, [])
            for idx, task in enumerate(tasks):
                if str(task.get("task_id")) != task_id:
                    continue
                updated = dict(task)
                if "task_name" in payload:
                    name = str(payload.get("task_name") or "").strip()
                    if not name:
                        raise ValueError("task_name is required")
                    updated["task_name"] = name
                if "requirement_prd_path" in payload:
                    updated["requirement_prd_path"] = str(
                        payload.get("requirement_prd_path") or ""
                    )
                if "requirement_text" in payload:
                    updated["requirement_text"] = str(
                        payload.get("requirement_text") or ""
                    )
                updated["updated_at"] = datetime.now().isoformat(timespec="seconds")
                tasks[idx] = updated
                self.tasks_by_project[project_id] = tasks
                self._save_tasks()
                return updated
        raise KeyError(f"Unknown task_id: {task_id}")

    def delete_task(self, project_id: str, task_id: str) -> None:
        with self.lock:
            tasks = self.tasks_by_project.get(project_id, [])
            updated = [task for task in tasks if str(task.get("task_id")) != task_id]
            if len(updated) == len(tasks):
                raise KeyError(f"Unknown task_id: {task_id}")
            self.tasks_by_project[project_id] = updated
            self._save_tasks()

    def list_runs(self) -> list[dict[str, Any]]:
        with self.lock:
            runs = sorted(self.runs.values(), key=lambda item: item.started_at, reverse=True)
            return [run.to_dict() for run in runs]

    def get_run(self, run_id: str) -> WorkflowRun:
        with self.lock:
            run = self.runs.get(run_id)
        if run is None:
            raise KeyError(f"Unknown run_id: {run_id}")
        return run

    def create_run(self, run: WorkflowRun) -> None:
        with self.lock:
            self.runs[run.run_id] = run

    def update_run(self, run_id: str, **fields: Any) -> None:
        with self.lock:
            run = self.runs[run_id]
            for key, value in fields.items():
                setattr(run, key, value)
            run.updated_at = datetime.now().isoformat(timespec="seconds")
            self.runs[run_id] = run

    def append_run_log(self, run_id: str, message: str) -> None:
        stamped = f"[{datetime.now().isoformat(timespec='seconds')}] {message}"
        with self.lock:
            run = self.runs[run_id]
            run.logs.append(stamped)
            run.updated_at = datetime.now().isoformat(timespec="seconds")
            self.runs[run_id] = run


class WebApp:
    def __init__(self, workflow_root: Path):
        self.workflow_root = workflow_root.resolve()
        self.static_dir = self.workflow_root / "webui"
        self.state = WebState(self.workflow_root)

    def _runtime_config_dir(self, project_id: str, run_id: str) -> Path:
        path = self.state.runtime_dir / project_id / run_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _resolve_rules_dir(self, project_id: str, ai_rules_dir: str | None = None) -> Path:
        binding = self.state.get_binding(project_id)
        rules_dir = (ai_rules_dir or binding.ai_rules_dir or "ai-rules").strip()
        path = Path(rules_dir).expanduser()
        if not path.is_absolute():
            path = Path(binding.app_root) / path

        return path.resolve()

    @staticmethod
    def _list_directory(path: Path, *, include_files: bool = False) -> dict[str, Any]:
        resolved = path.expanduser().resolve()
        if not resolved.exists() or not resolved.is_dir():
            raise ValueError(f"Directory does not exist: {resolved}")

        entries = list(resolved.iterdir())
        dirs = sorted(
            [{"name": item.name, "path": str(item.resolve())} for item in entries if item.is_dir()],
            key=lambda x: x["name"].lower(),
        )
        files: list[dict[str, str]] = []
        if include_files:
            files = sorted(
                [{"name": item.name, "path": str(item.resolve())} for item in entries if item.is_file()],
                key=lambda x: x["name"].lower(),
            )
        return {"path": str(resolved), "dirs": dirs, "files": files}

    def _rule_files(self, project_id: str, ai_rules_dir: str | None = None) -> dict[str, Any]:
        rules_dir = self._resolve_rules_dir(project_id, ai_rules_dir=ai_rules_dir)
        files: list[str] = []
        if rules_dir.exists() and rules_dir.is_dir():
            files = sorted([str(p.relative_to(rules_dir)) for p in rules_dir.rglob("*.md") if p.is_file()])
        return {"dir": str(rules_dir), "files": files}

    @staticmethod
    def _send_json(handler: BaseHTTPRequestHandler, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        handler.send_response(status.value)
        handler.send_header("Content-Type", "application/json; charset=utf-8")
        handler.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        handler.send_header("Pragma", "no-cache")
        handler.send_header("Expires", "0")
        handler.send_header("Content-Length", str(len(body)))
        handler.end_headers()
        handler.wfile.write(body)

    @staticmethod
    def _send_text(
        handler: BaseHTTPRequestHandler,
        status: HTTPStatus,
        text: str,
        content_type: str = "text/plain; charset=utf-8",
    ) -> None:
        body = text.encode("utf-8")
        handler.send_response(status.value)
        handler.send_header("Content-Type", content_type)
        handler.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        handler.send_header("Pragma", "no-cache")
        handler.send_header("Expires", "0")
        handler.send_header("Content-Length", str(len(body)))
        handler.end_headers()
        handler.wfile.write(body)

    @staticmethod
    def _read_json_body(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
        raw_len = int(handler.headers.get("Content-Length", "0") or "0")
        if raw_len <= 0:
            return {}
        data = handler.rfile.read(raw_len).decode("utf-8")
        return json.loads(data or "{}")

    @staticmethod
    def _open_path(path: Path) -> str:
        target = path.expanduser().resolve()
        if not target.exists():
            raise ValueError(f"Path does not exist: {target}")
        if sys.platform == "darwin":
            subprocess.Popen(["open", str(target)])
        elif sys.platform.startswith("win"):
            subprocess.Popen(["cmd", "/c", "start", "", str(target)], shell=False)
        else:
            subprocess.Popen(["xdg-open", str(target)])
        return str(target)

    def _build_runtime_configs(self, run: WorkflowRun, binding: ProjectBinding) -> Path:
        runtime_dir = self._runtime_config_dir(run.project_id, run.run_id)
        base_workflow = self.workflow_root / "config" / "workflow.yaml"
        workflow_raw = yaml.safe_load(base_workflow.read_text(encoding="utf-8")) or {}
        workflow_section = workflow_raw.setdefault("workflow", {})
        workflow_section["app_root"] = binding.app_root
        workflow_section["docs_dir"] = binding.docs_dir
        e2e_section = workflow_section.setdefault("e2e", {})
        if isinstance(e2e_section, dict):
            e2e_section["headless"] = bool(run.headless_all_nodes)

        nodes = workflow_raw.get("nodes") or {}
        if isinstance(nodes, dict):
            for node_cfg in nodes.values():
                if isinstance(node_cfg, dict):
                    node_cfg["tool"] = run.tool
                    if run.headless_all_nodes:
                        node_cfg["mode"] = "headless"

        runtime_workflow = runtime_dir / "workflow.yaml"
        runtime_workflow.write_text(
            yaml.safe_dump(workflow_raw, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )

        runtime_rules = {
            "ai_rules_dir": binding.ai_rules_dir,
            "node_rules": binding.node_rules,
        }
        (runtime_dir / "ai-rules.yaml").write_text(
            yaml.safe_dump(runtime_rules, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        return runtime_workflow

    def _run_workflow(self, run_id: str) -> None:
        try:
            run = self.state.get_run(run_id)
            binding = self.state.get_binding(run.project_id)
            self.state.update_run(run_id, status="running")
            self.state.append_run_log(run_id, "Workflow started")

            config_path = self._build_runtime_configs(run, binding)
            wf_cfg = load_workflow_config(config_path)
            if not run.skip_mcp_setup and wf_cfg.e2e_enabled:
                mcp_result = ensure_mcp_for_agents(
                    self.workflow_root,
                    e2e_headless=wf_cfg.e2e_headless,
                )
                self.state.append_run_log(
                    run_id,
                    f"MCP configured: servers={mcp_result.get('servers', [])}",
                )

            workflow = DevWorkflow(self.workflow_root, config_path)
            source_file = Path(run.requirement_path) if run.requirement_path else None
            if source_file and not source_file.exists():
                source_file = None

            result = workflow.run(
                requirement=run.requirement,
                docs_dir=binding.docs_dir,
                name=run.requirement_name or None,
                source_file=source_file,
                skip_clarification=run.skip_clarification,
                fresh=run.fresh,
            )
            self.state.update_run(
                run_id,
                status="completed",
                result=result,
                ended_at=datetime.now().isoformat(timespec="seconds"),
            )
            self.state.append_run_log(run_id, "Workflow completed")
        except Exception as exc:  # noqa: BLE001
            logger.exception("Workflow run failed")
            self.state.update_run(
                run_id,
                status="failed",
                error=str(exc),
                ended_at=datetime.now().isoformat(timespec="seconds"),
            )
            self.state.append_run_log(run_id, f"Workflow failed: {exc}")

    def start_run(self, payload: dict[str, Any]) -> dict[str, Any]:
        project_id = str(payload.get("project_id") or "").strip()
        if not project_id:
            raise ValueError("project_id is required")
        binding = self.state.get_binding(project_id)
        requirement = str(payload.get("requirement") or "").strip()
        requirement_path = str(payload.get("requirement_prd_path") or "").strip()
        if not requirement and not requirement_path:
            raise ValueError("requirement or requirement_prd_path is required")
        if not requirement and requirement_path:
            prd = Path(requirement_path)
            if not prd.is_absolute():
                prd = Path(binding.app_root) / prd
            prd = prd.resolve()
            if not prd.exists():
                raise ValueError(f"PRD file does not exist: {prd}")
            requirement = prd.read_text(encoding="utf-8")
            requirement_path = str(prd)

        run = WorkflowRun(
            run_id=uuid.uuid4().hex,
            project_id=project_id,
            requirement=requirement,
            requirement_path=requirement_path,
            requirement_name=str(payload.get("requirement_name") or "").strip(),
            tool=str(payload.get("tool") or "omp").strip() or "omp",
            skip_clarification=bool(payload.get("skip_clarification", True)),
            fresh=bool(payload.get("fresh", False)),
            headless_all_nodes=bool(payload.get("headless_all_nodes", True)),
            skip_mcp_setup=bool(payload.get("skip_mcp_setup", False)),
            docs_dir=binding.docs_dir,
        )
        self.state.create_run(run)
        worker = threading.Thread(target=self._run_workflow, args=(run.run_id,), daemon=True)
        worker.start()
        return run.to_dict()

    def _serve_index(self, handler: BaseHTTPRequestHandler) -> None:
        index_file = self.static_dir / "index.html"
        if not index_file.exists():
            self._send_text(
                handler,
                HTTPStatus.NOT_FOUND,
                "index.html not found under webui/",
            )
            return
        self._send_text(
            handler,
            HTTPStatus.OK,
            index_file.read_text(encoding="utf-8"),
            "text/html; charset=utf-8",
        )

    def handle_get(self, handler: BaseHTTPRequestHandler) -> None:
        parsed = urlparse(handler.path)
        route = parsed.path.rstrip("/") or "/"
        query = parse_qs(parsed.query)

        if route in ("/", "/index.html"):
            self._serve_index(handler)
            return

        if route == "/api/projects":
            self._send_json(handler, HTTPStatus.OK, {"projects": self.state.list_bindings()})
            return

        if route == "/api/fs/roots":
            roots = [
                {"name": "Home", "path": str(Path.home().resolve())},
                {"name": "Workflow Root", "path": str(self.workflow_root)},
                {"name": "Root", "path": str(Path("/").resolve())},
            ]
            self._send_json(handler, HTTPStatus.OK, {"roots": roots})
            return

        if route == "/api/fs/list":
            target = str((query.get("path") or [""])[0]).strip() or str(Path.home())
            include_files = str((query.get("files") or ["0"])[0]).strip() == "1"
            listing = self._list_directory(Path(target), include_files=include_files)
            ext = str((query.get("ext") or [""])[0]).strip().lower()
            if ext and include_files:
                listing["files"] = [
                    item for item in listing["files"] if item["name"].lower().endswith(ext)
                ]
            self._send_json(handler, HTTPStatus.OK, listing)
            return

        parts = [segment for segment in route.split("/") if segment]
        if len(parts) >= 3 and parts[0] == "api" and parts[1] == "projects":
            project_id = parts[2]
            if len(parts) == 4 and parts[3] == "rules":
                binding = self.state.get_binding(project_id)
                self._send_json(
                    handler,
                    HTTPStatus.OK,
                    {
                        "project_id": binding.project_id,
                        "ai_rules_dir": binding.ai_rules_dir,
                        "node_rules": binding.node_rules,
                    },
                )
                return

            if len(parts) == 4 and parts[3] == "rule-files":
                ai_rules_dir = str((query.get("ai_rules_dir") or [""])[0]).strip() or None
                self._send_json(
                    handler,
                    HTTPStatus.OK,
                    self._rule_files(project_id, ai_rules_dir=ai_rules_dir),
                )
                return

            if len(parts) == 4 and parts[3] == "tasks":
                self._send_json(handler, HTTPStatus.OK, {"tasks": self.state.list_tasks(project_id)})
                return

        if route == "/api/runs":
            self._send_json(handler, HTTPStatus.OK, {"runs": self.state.list_runs()})
            return

        if route.startswith("/api/runs/"):
            run_id = route.split("/")[3]
            run = self.state.get_run(run_id)
            self._send_json(handler, HTTPStatus.OK, {"run": run.to_dict()})
            return

        self._send_json(handler, HTTPStatus.NOT_FOUND, {"error": "Not found"})

    def handle_post(self, handler: BaseHTTPRequestHandler) -> None:
        parsed = urlparse(handler.path)
        route = parsed.path.rstrip("/") or "/"

        if route == "/api/projects":
            payload = self._read_json_body(handler)
            binding = self.state.create_binding(
                name=str(payload.get("name") or "").strip(),
                app_root=str(payload.get("app_root") or "").strip(),
                docs_dir=str(payload.get("docs_dir") or "docs"),
                ai_rules_dir=str(payload.get("ai_rules_dir") or "ai-rules"),
            )
            self._send_json(handler, HTTPStatus.CREATED, {"project": binding})
            return

        parts = [segment for segment in route.split("/") if segment]
        if len(parts) >= 3 and parts[0] == "api" and parts[1] == "projects":
            project_id = parts[2]

            if len(parts) == 4 and parts[3] == "rules":
                payload = self._read_json_body(handler)
                node_rules = payload.get("node_rules") or {}
                if not isinstance(node_rules, dict):
                    raise ValueError("node_rules must be an object")
                updated = self.state.update_rules(
                    project_id,
                    ai_rules_dir=str(payload.get("ai_rules_dir") or "ai-rules"),
                    node_rules={
                        str(k): [str(item) for item in (v if isinstance(v, list) else [])]
                        for k, v in node_rules.items()
                    },
                )
                self._send_json(handler, HTTPStatus.OK, {"project": updated})
                return

            if len(parts) == 4 and parts[3] == "tasks":
                payload = self._read_json_body(handler)
                task = self.state.create_task(project_id, payload)
                self._send_json(handler, HTTPStatus.CREATED, {"task": task})
                return

        if route == "/api/runs":
            payload = self._read_json_body(handler)
            run = self.start_run(payload)
            self._send_json(handler, HTTPStatus.CREATED, {"run": run})
            return

        if route.startswith("/api/runs/") and route.endswith("/open-artifact"):
            run_id = route.split("/")[3]
            payload = self._read_json_body(handler)
            node_id = str(payload.get("node_id") or "").strip()
            if not node_id:
                raise ValueError("node_id is required")

            run = self.state.get_run(run_id)
            outputs = (run.result or {}).get("node_outputs") or {}
            rel = str(outputs.get(node_id) or "").strip()
            if not rel:
                raise ValueError(f"No artifact for node: {node_id}")

            binding = self.state.get_binding(run.project_id)
            artifact_path = (Path(binding.app_root) / rel).resolve()
            opened = self._open_path(artifact_path)
            self._send_json(
                handler,
                HTTPStatus.OK,
                {"opened": opened, "artifact": str(artifact_path)},
            )
            return

        self._send_json(handler, HTTPStatus.NOT_FOUND, {"error": "Not found"})

    def handle_put(self, handler: BaseHTTPRequestHandler) -> None:
        parsed = urlparse(handler.path)
        route = parsed.path.rstrip("/") or "/"

        parts = [segment for segment in route.split("/") if segment]
        if len(parts) == 5 and parts[0] == "api" and parts[1] == "projects" and parts[3] == "tasks":
            project_id = parts[2]
            task_id = parts[4]
            payload = self._read_json_body(handler)
            updated = self.state.update_task(project_id, task_id, payload)
            self._send_json(handler, HTTPStatus.OK, {"task": updated})
            return

        if len(parts) == 3 and parts[0] == "api" and parts[1] == "projects":
            project_id = parts[2]
            payload = self._read_json_body(handler)
            updated = self.state.update_binding(
                project_id,
                name=str(payload.get("name") or "").strip(),
                app_root=str(payload.get("app_root") or "").strip(),
                docs_dir=str(payload.get("docs_dir") or "docs"),
                ai_rules_dir=str(payload.get("ai_rules_dir") or "ai-rules"),
            )
            self._send_json(handler, HTTPStatus.OK, {"project": updated})
            return

        self._send_json(handler, HTTPStatus.NOT_FOUND, {"error": "Not found"})

    def handle_delete(self, handler: BaseHTTPRequestHandler) -> None:
        parsed = urlparse(handler.path)
        route = parsed.path.rstrip("/") or "/"

        parts = [segment for segment in route.split("/") if segment]
        if len(parts) == 5 and parts[0] == "api" and parts[1] == "projects" and parts[3] == "tasks":
            project_id = parts[2]
            task_id = parts[4]
            self.state.delete_task(project_id, task_id)
            self._send_json(handler, HTTPStatus.OK, {"deleted": task_id})
            return

        if len(parts) == 3 and parts[0] == "api" and parts[1] == "projects":
            project_id = parts[2]
            self.state.delete_binding(project_id)
            self._send_json(handler, HTTPStatus.OK, {"deleted": project_id})
            return

        self._send_json(handler, HTTPStatus.NOT_FOUND, {"error": "Not found"})



def create_handler(app: WebApp):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            try:
                app.handle_get(self)
            except KeyError as exc:
                app._send_json(self, HTTPStatus.NOT_FOUND, {"error": str(exc)})
            except Exception as exc:  # noqa: BLE001
                logger.exception("GET failed")
                app._send_json(self, HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})

        def do_POST(self) -> None:  # noqa: N802
            try:
                app.handle_post(self)
            except (ValueError, json.JSONDecodeError) as exc:
                app._send_json(self, HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            except KeyError as exc:
                app._send_json(self, HTTPStatus.NOT_FOUND, {"error": str(exc)})
            except Exception as exc:  # noqa: BLE001
                logger.exception("POST failed")
                app._send_json(self, HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})

        def do_PUT(self) -> None:  # noqa: N802
            try:
                app.handle_put(self)
            except (ValueError, json.JSONDecodeError) as exc:
                app._send_json(self, HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            except KeyError as exc:
                app._send_json(self, HTTPStatus.NOT_FOUND, {"error": str(exc)})
            except Exception as exc:  # noqa: BLE001
                logger.exception("PUT failed")
                app._send_json(self, HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})

        def do_DELETE(self) -> None:  # noqa: N802
            try:
                app.handle_delete(self)
            except KeyError as exc:
                app._send_json(self, HTTPStatus.NOT_FOUND, {"error": str(exc)})
            except Exception as exc:  # noqa: BLE001
                logger.exception("DELETE failed")
                app._send_json(self, HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
            logger.info("%s - %s", self.address_string(), format % args)

    return Handler


def serve_web_ui(workflow_root: Path, host: str = "127.0.0.1", port: int = 8787) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    app = WebApp(workflow_root)
    handler_cls = create_handler(app)
    server = ThreadingHTTPServer((host, port), handler_cls)
    logger.info("Web UI served at http://%s:%s", host, port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down Web UI server")
    finally:
        server.server_close()
