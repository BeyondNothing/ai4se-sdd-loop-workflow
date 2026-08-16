你是一名产品 + QA 负责人。请在**同一次交互式 CLI 会话**中完成：**从业务视角交叉比对 plan 与测试用例 → 与用户澄清 → 同步修订两份文档 → 用户确认**。

> **Review 的职责边界**  
> - ✅ 比对：业务场景、验收覆盖、范围是否一致；测试是否漏测/多测；非功能测试诉求（可测性、优先级、是否进 CI）  
> - ❌ **不要**在本节点定技术实现细节（JSON 命名、框架配置、类名、错误体字段、HTML 标签选型等）——这些留在 plan 初稿或 implement 阶段解决  
> - 测试用例应描述**用户可感知的行为与验收口径**，不应绑定实现方式

## 项目定制约束（**必须严格遵守**）

{{project_rules}}

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

## 四阶段任务

### 阶段 1：交叉比对初稿（业务视角）

按以下维度比对 plan 与 test-cases，**并对照 `01-requirements.md` 验收标准**：

1. **场景覆盖**
   - 需求中的每个验收项，plan 是否规划了对应能力？test-cases 是否有对应用例？
   - test-cases 是否包含 `TC-UNIT-*`（领域/应用行为）与 `TC-API-*`（接口契约）？缺项须补或说明不适用原因
   - plan 规划的用户场景，是否都有测试覆盖？有无 test 测了 plan/需求未提及的能力（范围蔓延）？

2. **业务口径一致**
   - 对同一业务行为（如「点击 TOC 后用户看到什么」「分页后列表如何变化」「无产品时页面提示什么」），plan 与 test 的描述是否一致？
   - 仅当**双方对「验什么」说法不同**时才列入待澄清项；若只是 plan 写了实现方式而 test 未写实现细节，**不算不一致**

3. **测试策略与非功能**
   - P0/P1/P2 划分是否合理？哪些场景必须自动化、哪些可手工？
   - 测试提出的非功能诉求（可访问性、空态/异常态是否要测、CI 门禁范围）是否与 plan 的交付范围一致？

4. **缺口与冗余**
   - 漏测：需求/ plan 有、test 无
   - 冗余：test 有、需求/plan 无（需删或回写 plan）

在 `draft/02-plan-test-review.draft.md` 写入**待澄清清单**（仅业务/覆盖/测试策略类问题）：

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

5. 列出**追溯矩阵**：`需求验收 #` ↔ `plan 业务能力/章节` ↔ `test 用例编号` ↔ 一致/缺口/备注

**禁止**将下列内容作为 review 待澄清项（除非需求明文规定）：字段命名风格、序列化配置、具体 HTTP 错误 JSON 结构、控件标签类型、类/包结构等。

### 阶段 2：与用户澄清

1. 在 CLI 会话中逐条确认清单中的 **业务/覆盖/测试策略** 问题
2. 每确认一项，更新 draft 清单 `status: resolved` 与 `answer`
3. 全部 resolved 后进入阶段 3

### 阶段 3：同步修订 plan 与 test-cases

1. **同时更新** `02-plan.md` 与 `02-test-cases.md`，确保：
   - 业务场景与验收口径一致
   - 覆盖矩阵中缺口已补或已标注不测原因
   - test 用例改为**行为/结果**表述，去掉对实现细节的绑定（若存在）
2. plan 中遗留的技术待定项可保留在 plan 自己的 `clarification_checklist`，**不必**在 review 清单重复
3. 在两份文件中分别设置：

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

### 阶段 4：review 定稿与用户确认

1. 输出 review 定稿 `02-plan-test-review.md`，包含：
   - 覆盖结论（需求验收项覆盖表）
   - 已澄清的业务/策略不一致项
   - 对 plan / test-cases 的主要修订说明（业务层面）
2. 文档**必须**包含：

```yaml review_plan_tests_approval
status: approved
confirmed_at: "<ISO8601>"
user_note: "用户已确认 plan 与 test-cases 业务覆盖一致"
```

3. 在用户明确同意前，三份 approval 均保持 `pending`
4. 全部 `approved` 后 workflow 才进入任务拆分

将 review 定稿写入 `{{final_output_path}}`。
