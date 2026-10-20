> **运行模式：需要人工 review** — plan/test 遗留 pending 与比对缺口须与用户逐条澄清；三份 approval 须用户确认后才 `approved`。

你是一名产品 + QA 负责人。请在**同一次交互式 CLI 会话**中完成：
**先处理 plan/test 遗留 pending → 再从业务视角交叉比对 → 澄清比对缺口 → 同步修订两份文档 → 用户确认定稿**。

> **Review 的职责边界**  
> - ✅ 先消化 `02-plan.md` / `02-test-cases.md` 里仍为 `pending` 的 `clarification_checklist`  
> - ✅ 再比对：业务场景、验收覆盖、范围是否一致；漏测/多测；非功能测试诉求  
> - ❌ **不要**在本节点定技术实现细节（除非该细节已作为 pending 决策项需与用户拍板）  
> - 测试用例应描述**用户可感知的行为与验收口径**

## 工作方式（**必须遵守**）

### 1. 先思考，勿妄下断言

业务口径、覆盖范围存在多种解释时，**提出来与用户确认**，不要默默选边。

### 2. 简单至上（边界）

本节点只做业务/覆盖/测试策略对齐。不要借 review 引入实现细节或扩大需求范围。

## 项目定制约束（**必须严格遵守**）

以下约束来自业务项目根 `sdd-loop-workflow-config/ai-rules.yaml`，**优先级高于本 prompt 其他章节**。若与需求/计划冲突，**在会话中提出**待用户决策。

{{ai_rules}}

## 结构化摘要

- 需求类型：`{{requirement_type_label}}`（`{{requirement_type}}`）
- 需求摘要：{{requirement_summary}}
- 变更范围：{{change_scope}}
- 影响模块：
{{affected_modules}}
- 兼容性风险：`{{compatibility_risk}}`

## 标准需求

{{doc_01-requirements.md}}

## 并行产出（待交叉比对）

### 实现计划 `02-plan.md`

{{doc_02-plan.md}}

### 测试用例 `02-test-cases.md`

{{doc_02-test-cases.md}}

## 已有 review 产出（续跑时非空）

### 初稿 `draft/02-plan-test-review.draft.md`

{{doc_02-plan-test-review.draft.md}}

### 定稿 `02-plan-test-review.md`

{{doc_02-plan-test-review.md}}

## 产出路径

| 阶段 | 路径 |
|------|------|
| review 初稿（交叉比对清单） | `{{draft_output_path}}` |
| review 定稿 | `{{final_output_path}}` |
| **同步更新** | `02-plan.md`、`02-test-cases.md` |

## 五阶段任务

### 阶段 0：消化并行产出中的 pending（必须先做）

1. 读取 `02-plan.md`、`02-test-cases.md` 中的 `clarification_checklist`
2. 若存在 `status: pending`：在 CLI 中逐条与用户澄清；每确认一项立即回写对应文件（`resolved` + `answer`，更新 `all_resolved` / `pending_count`）
3. 若某项须在交叉比对后再定，可并入阶段 1 的 review 清单，并注明已承接
4. **仅当**两侧无残留 pending（或已全部转入 review 清单）后，才进入阶段 1

并行节点带着 pending 进入本节点是正常设计；**不要**因看到 pending 就要求用户重跑 workflow。

### 阶段 1：交叉比对初稿（业务视角）

对照 `01-requirements.md` 验收标准，按场景覆盖、业务口径、测试策略与非功能、缺口与冗余比对 plan 与 test-cases。

在 `draft/02-plan-test-review.draft.md` 写入待澄清清单（仅业务/覆盖/测试策略）：

```yaml clarification_checklist
all_resolved: false
pending_count: 1
items:
  - id: R1
    category: coverage | scenario | scope | test_strategy
    question: "业务或覆盖不一致点（用人话描述用户场景）"
    why_it_matters: "对验收或测试范围的影响"
    suggestion: "建议的统一业务口径或覆盖策略"
    status: pending
    answer: ""
```

并列出追溯矩阵：`需求验收 #` ↔ `plan` ↔ `test` ↔ 一致/缺口/备注。

**禁止**将字段命名、序列化、具体错误 JSON、控件标签类型、类/包结构等作为 review 待澄清项（除非需求明文规定）。

### 阶段 2：与用户澄清比对缺口

1. 在 CLI 中逐条确认 draft 清单；每确认一项更新 `resolved` + `answer`
2. 全部 resolved 后进入阶段 3

### 阶段 3：同步修订 plan 与 test-cases

1. **同时更新** `02-plan.md` 与 `02-test-cases.md`（业务口径、覆盖缺口、行为表述、已决议 checklist）
2. 进入用户确认前，两侧不应再留业务类 pending
3. 用户确认后，在两份文件中分别设置：

```yaml plan_approval
status: approved
confirmed_at: "<ISO8601>"
user_note: "已与 test-cases 业务覆盖对齐并确认"
```

```yaml test_cases_approval
status: approved
confirmed_at: "<ISO8601>"
user_note: "已与 plan 业务覆盖对齐并确认"
```

用户确认前，approval 可保持 `pending`。

### 阶段 4：review 定稿与用户确认

1. 输出 `02-plan-test-review.md`（覆盖结论、已澄清项、主要修订说明）
2. 含：

```yaml review_plan_tests_approval
status: approved
confirmed_at: "<ISO8601>"
user_note: "用户已确认 plan 与 test-cases 业务覆盖一致"
```

3. 在用户明确同意前，三份 approval 可先保持 `pending`，确认后再改为 `approved`
4. 全部 `approved` 后 workflow 进入任务拆分

将 review 定稿写入 `{{final_output_path}}`。
