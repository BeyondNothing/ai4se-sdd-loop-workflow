# ai4se-sdd-loop-workflow

从**需求 → 计划/用例 → 评审 → 任务 → 代码 → 测试**的工程化 Workflow。配置和产出写在业务项目里。

---

## 1. 快速使用

```bash
git clone <本仓库地址>
cd ai4se-sdd-loop-workflow
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
```

装好后可在各个业务项目根目录直接用：

```bash
sdd-loop-workflow:init
sdd-loop-workflow:start --tool cursor --file "/path/to/prd.md" --name login
sdd-loop-workflow:start --tool cursor --name login --auto      # 无人值守
sdd-loop-workflow:start --tool cursor --name login             # 续跑，勿加 --fresh
```

| 开关 | 作用 |
|------|------|
| `--file` | 需求文件 |
| `--name` | 产出目录名（默认落在 `spec/<name>/`） |
| `--auto` | 无人值守 |
| `--fresh` | 清空该需求产出后重来 |
| `--tool` | `cursor` / `claude_code` / `omp` / `echo` |

需要 Python 3.10+ 和已登录的 AI CLI。找不到引擎时加 `--workflow-root <引擎目录>`。
---

## 2. `init` 在业务项目里生成什么

```text
your-project/
├── sdd-loop-workflow-config/     # 业务配置（改这里）
│   ├── workflow.yaml             # docs_dir
│   ├── ai-rules.yaml             # 各节点用哪些扩展 rule
│   └── ai-rules/*.md             # 规则正文
└── .cursor|claude|omp/skills/start-workflow/   # 拼启动命令的 skill（不在对话里执行）
```

| 文件 | 作用 |
|------|------|
| `workflow.yaml` | 产出目录名（`docs_dir`）等 |
| `ai-rules.yaml` + `ai-rules/` | 项目扩展规范，注入各节点；优先级高于引擎通用 prompt |
| `start-workflow` skill | 根据上下文拼 `sdd-loop-workflow:start ...`，须在 AI session **外**执行 |

跑起来后，需求文档在 `<docs_dir>/<name>/`（如 `spec/login/01-requirements.md` … `05-test-report.md`）。

---

## 3. 有哪些节点

```text
需求 → 并行(计划+用例) → 评审 → 任务拆分 → 实现 → 测试
```

| 节点 | 产出 | 做什么 |
|------|------|--------|
| 需求分析 | `01-requirements.md` | 澄清与定稿 |
| 制定计划 / 设计用例 | `02-plan.md`、`02-test-cases.md` | 并行初稿 |
| 计划与用例评审 | `02-plan-test-review.md` | 对齐并确认 |
| 任务拆分 | `03-tasks.md` | 任务 + API 详细设计 |
| 代码实现 | `04-implementation.md` + 业务代码 | 只写生产代码 |
| 测试自验证 | `05-test-report.md` | 按项目 AS IS 跑单测；API/E2E 有栈才跑 |

- 人工：`prompts/*.md`，澄清与审批需确认  
- `--auto`：`prompts/*.auto.md`，按扩展 rule 自决，不提问  
- 测试代码只在「测试自验证」写；实现节点不写 `src/test`

---

## 4. 扩展点

1. **项目规范（最常用）**  
   改 `sdd-loop-workflow-config/ai-rules/` 与 `ai-rules.yaml`，不必改引擎。

2. **docs_dir 等业务运行时**  
   改 `sdd-loop-workflow-config/workflow.yaml`。

3. **节点 prompt / 默认工具**  
   改引擎仓库 `config/workflow.yaml` 与 `prompts/`（人工与 `.auto` 成对）。

4. **流程拓扑 / 门禁 / 新 AI 后端**  
   改引擎代码：`src/workflow.py`、`router.py`、`phase_gate.py`、`agents/`。
