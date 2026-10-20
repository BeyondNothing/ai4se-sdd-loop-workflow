# ai4se-sdd-loop-workflow

从**需求 → 计划/用例 → 评审 → 任务 → 代码 → 测试 → AI Review**的工程化 Workflow。配置和产出写在业务项目里。

**快速接入、可按项目扩展**：业务侧 `init` 即可用，规范与规则落在 `sdd-loop-workflow-config/`，不必改引擎；需要时再通过扩展 rule、prompt 与节点编排加深定制。

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

需要 Python 3.10+ 和已登录的 AI CLI。

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
| `start-workflow` skill | 准备需求文件并拼装启动命令（见下）；**不在当前 AI 对话里执行** |

跑起来后，需求文档在 `<docs_dir>/<name>/`（如 `spec/login/01-requirements.md` … `06-ai-review.md`）。

### `start-workflow` skill 用在什么时候

`init` 会把该 skill 装到业务项目的 AI 技能目录。在对话里触发它，只做两件事：**落本地需求文件** + **拼好启动命令**；真正跑 workflow 必须你自己在**终端**执行。

| 场景 | 你怎么说 | skill 做什么 |
|------|----------|--------------|
| 本地已有 PRD | 给出文件路径 | 校验路径存在，直接拼 `sdd-loop-workflow:start --file ...` |
| 需求在外部系统（Jira、Colla 等） | 告诉**卡号 / 需求标识** | 按项目已配置的 **MCP** 拉取正文 → 写入本地（如 `docs/requirements/<标识>.md`）→ 再拼启动命令 |
| 两边都没有 | — | 先问你要路径或外部来源，不瞎拼命令 |

要点：

- MCP（Jira / Colla 等）需事先在 AI 环境配好；skill **不猜** MCP 名字，步骤以项目 rule / skill 输入为准。
- skill **禁止**在当前 AI session 里执行启动命令；你复制命令到业务项目根的终端再跑（或结束对话后在系统终端跑），编排进程才能接管交互节点并续跑。
- 审批通过、续跑都**不要**再让 skill 重跑一遍；外部终端里已在跑的进程会自己进下一节点。

---

## 3. 有哪些节点

```text
需求 → 并行(计划+用例) → 评审 → 任务拆分 → 实现 → 测试 → AI Review
```

| 节点 | 产出 | 做什么 |
|------|------|--------|
| 需求分析 | `01-requirements.md` | 澄清与定稿 |
| 制定计划 / 设计用例 | `02-plan.md`、`02-test-cases.md` | 并行初稿 |
| 计划与用例评审 | `02-plan-test-review.md` | 对齐并确认 |
| 任务拆分 | `03-tasks.md` | 任务 + API 详细设计 |
| 代码实现 | `04-implementation.md` + 业务代码 | 只写生产代码 |
| 测试自验证 | `05-test-report.md` | 写测→跑绿→置信度；API/E2E 有栈才跑 |
| AI 代码评审 | `06-ai-review.md` | 针对改动代码做技术整洁度/简单重构并测绿（不读需求文档） |

- 人工：`prompts/*.md`，澄清与审批需确认  
- `--auto`：`prompts/*.auto.md`，按扩展 rule 自决，不提问  
- 测试代码只在「测试自验证」写；实现节点不写 `src/test`  
- AI Review 的语言/风格细则放在项目 `ai-rules`，引擎 prompt 只定通用整洁度闭环

---

## 4. 业务配置说明（`sdd-loop-workflow-config/`）

`init` 生成后改这里即可按项目定制，**不必改引擎**。

### `workflow.yaml` — 运行时目录

| 配置项 | 作用 |
|--------|------|
| `docs_dir` | 文档产出根目录（相对业务项目根）。默认 `spec`；需求产出为 `<业务根>/<docs_dir>/<需求名>/`，如 `spec/login/` |

节点用的 tool / prompt / mode **不在这里配**，在引擎仓库的 `config/workflow.yaml`。

### `ai-rules.yaml` — 扩展规则映射

规则正文会注入对应节点 prompt 的 `{{ai_rules}}`，**优先级高于**引擎通用提示词；`--auto` 时也优先按这里消解歧义。

| 配置项 | 作用 |
|--------|------|
| `ai_rules_dir` | 规则正文所在目录，相对本配置目录；默认 `ai-rules`（即 `sdd-loop-workflow-config/ai-rules/`） |
| `nodes.<节点ID>` | 该节点要注入的 markdown 文件列表（文件名相对 `ai_rules_dir`）。未列出的节点不注入扩展 rule |

示例：

```yaml
ai_rules_dir: ai-rules

nodes:
  implement_code:
    - coding-style.md
    - package-structure.md
  verify_tests:
    - test-conventions.md
  ai_review:
    - coding-style.md
    - security-baseline.md
```

同一 `.md` 可挂到多个节点下复用；按节点拆文件更清晰（实现吃风格与分层，验证吃测试栈，AI Review 吃风格与安全等）。

### `ai-rules/*.md` — 规则正文

每个文件写项目自己的硬约束（语言、分层、测试栈、安全基线等）。引擎 prompt 只定通用流程，**具体规范写在这里**。

**编码约定示例**（`ai-rules/coding-style.md`）：

```markdown
# 编码约定（示例）

- 新代码放在 `com.example.order` 下按应用服务 / 领域 / 基础设施分层，勿新建平行顶层包。
- 禁止为单次调用去改已被多处使用的公共 Utils；优先在本模块写私有方法。
- 魔法数字：超时、重试次数等提取为命名常量；业务状态码用枚举，勿散落字面量。
- API 入参校验失败返回统一错误码，勿直接抛未包装异常给调用方。
```

**测试约定示例**（`ai-rules/test-conventions.md`）：

```markdown
# 测试约定（示例）

- 单测用项目已有 JUnit5 + Mockito；禁止另起测试框架。
- 无 API 集成测试工程时，`TC-API-*` 标 skip，并在报告写明依据。
- 外部支付 / 短信一律 mock；不要在 CI 打真实第三方。
```
