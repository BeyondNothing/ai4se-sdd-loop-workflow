# Plan × Test Cases 交叉比对初稿（业务视角）

> 节点 ID: `review_plan_and_tests`  
> 阶段: 2 — 澄清已完成，待同步修订与用户定稿确认  
> 生成时间: 2026-08-16T16:05:00+08:00  
> 更新时间: 2026-08-16T16:08:00+08:00  
> 对照: `01-requirements.md`、`02-plan.md`、`02-test-cases.md`  
> 备注: 本节点**不**澄清技术实现细节（JSON 命名、Filter 放行方式、类名等）；plan 自有 D1–D4 留 plan checklist。

---

```yaml clarification_checklist
all_resolved: true
pending_count: 0
items:
  - id: R1
    category: scenario
    question: "用户请求的页码超出末页时，列表 API 的 total 应仍是「当前过滤条件下的真实匹配总数」，还是也变成 0？"
    why_it_matters: "验收「空页」与「无匹配分类」语义不同：若 total 被误写成 0，分页控件与 E2E/API 断言会与真实条数矛盾；需求仅明确无匹配时 total:0，未单独写清越界页。"
    suggestion: "越界页：HTTP 200、items=[]、total 仍为当前过滤下的真实匹配总数（与「不存在的 category → total:0」区分）。"
    status: resolved
    answer: "越界页：HTTP 200、items=[]、total 仍为当前过滤条件下的真实匹配总数；与「不存在的 category → total:0」区分。"
  - id: R2
    category: coverage
    question: "「仅 1 个有效分类时仍展示 TOC」是否必须在本期 E2E 自动化中覆盖？固定种子若恒为 ≥2 类，如何验收？"
    why_it_matters: "需求 7.5 与验收延伸明确要求单分类仍展示 TOC；若本期不测，存在漏测风险；若必测则需数据夹具或手工项。"
    suggestion: "本期 P0 以多分类种子为主；单分类 TOC 展示降为 P2（或手工冒烟一次），文档标注「需求有述、自动化本期不强制」。"
    status: resolved
    answer: "本期 P0 以多分类种子为主；单分类 TOC 展示降为 P2（可手工冒烟）；文档标注需求有述、自动化本期不强制。"
  - id: R3
    category: test_strategy
    question: "列表页描述「摘要截断」是否要求断言具体字符长度？"
    why_it_matters: "过严会把实现细节绑进用例；过松则无法验收「有摘要展示」。"
    suggestion: "不强制具体截断长度；仅要求有描述时页面展示可识别为同源内容的摘要/前缀。"
    status: resolved
    answer: "不强制具体截断长度；有描述时页面展示可识别为同源内容的摘要/前缀即可。"
  - id: R4
    category: scenario
    question: "分页「页间不重复」是否依赖稳定排序？用例是否断言具体排序键（如 id/name）？"
    why_it_matters: "无稳定序时页间不重复断言不稳定；需求未规定排序键，需统一「验什么」口径。"
    suggestion: "实现保证稳定序；用例不断言具体排序键，只断言同条件下页间 id 不重复且与 API 当页一致。"
    status: resolved
    answer: "实现保证稳定序；用例不断言具体排序键，只断言同条件下页间 id 不重复且与 API 当页一致。"
  - id: R5
    category: test_strategy
    question: "领域规则支撑用例 TC-DOM-* 是否纳入本期自动化门禁（CI / 验收 #11）？"
    why_it_matters: "影响门禁范围与实现工作量；架构鼓励领域单测，但编号验收以 API+E2E 为主。"
    suggestion: "P0 门禁 = 全部 TC-API P0 + TC-E2E P0；TC-DOM-* 保持 P1 推荐，不阻塞验收 #11。"
    status: resolved
    answer: "P0 门禁 = 全部 TC-API P0 + TC-E2E P0；TC-DOM-* 为 P1 推荐，不阻塞验收 #11。"
```

---

## 1. 比对结论摘要

| 维度 | 结论 |
|------|------|
| 场景覆盖（验收 1–11） | **基本完整**：plan §6 与 test 追溯表均可映射到编号验收；无范围蔓延 |
| 业务口径 | R1–R5 已与用户确认（建议默认全部采纳） |
| 技术待定（不进本清单） | plan D1–D4 留 plan 自身 checklist |

---

## 2. 追溯矩阵（需求验收 ↔ plan ↔ test）

| 需求验收 # | plan 业务能力 / 章节 | test 用例 | 状态 |
|------------|----------------------|-----------|------|
| 1 | §2.1；§6 #1 | TC-API-01、TC-API-10、TC-DOM-01 | 一致 |
| 2 | §2.1；§6 #2 | TC-API-02 | 一致 |
| 3 | §2.1；§6 #3（稳定序） | TC-API-03、TC-API-09 | 一致（R4） |
| 4 | §2.1；§5.1；§6 #4 | TC-API-04、TC-DOM-02 | 一致 |
| 5 | §2.2；§6 #5 | TC-API-11/12/13、TC-DOM-03 | 一致 |
| 6 | §2.1（含越界页 total）；§6 #6 | TC-API-05/06/07/08 | 一致（R1） |
| 7 | §4；§6 #7 | TC-E2E-01 | 一致 |
| 8 | §4.2；§6 #8 | TC-E2E-02、TC-E2E-03 | 一致 |
| 9 | §4.1；§6 #9 | TC-E2E-04 | 一致（R3） |
| 10 | §4.1；§6 #10 | TC-E2E-05 | 一致（R4） |
| 11 | §5.3；§6 #11 | TC-API P0 + TC-E2E P0 | 一致（R5） |

---

## 5. Workflow 状态（本阶段）

| 字段 | 值 |
|------|-----|
| node | review_plan_and_tests |
| status | in_progress |
| phase | sync_revise |
| pending_count | 0 |
| all_resolved | true |
| next_step | 同步修订 plan / test-cases → 定稿确认 |
| updated_at | 2026-08-16T16:08:00+08:00 |

## Workflow 状态

| 字段 | 值 |
|------|-----|
| node | review_plan_and_tests |
| status | completed |
| next_node | split_tasks |
| phase | plan_test_review |
| pending_count | 0 |
| all_resolved | true |
| updated_at | 2026-08-16T16:12:35 |
