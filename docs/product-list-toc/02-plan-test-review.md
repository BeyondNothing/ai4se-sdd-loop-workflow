# Plan × Test Cases 交叉比对定稿

> 节点 ID: `review_plan_and_tests`  
> AI 工具: `cursor`  
> 模式: `interactive`  
> 生成时间: 2026-08-16T16:08:00+08:00  
> 对照: `01-requirements.md`、`02-plan.md`、`02-test-cases.md`  
> 初稿: `draft/02-plan-test-review.draft.md`

---

```yaml clarification_checklist
all_resolved: true
pending_count: 0
items:
  - id: R1
    category: scenario
    question: "用户请求的页码超出末页时，列表 API 的 total 应仍是「当前过滤条件下的真实匹配总数」，还是也变成 0？"
    why_it_matters: "验收「空页」与「无匹配分类」语义不同。"
    suggestion: "越界页：HTTP 200、items=[]、total 仍为真实匹配总数。"
    status: resolved
    answer: "越界页：HTTP 200、items=[]、total 仍为当前过滤条件下的真实匹配总数；与「不存在的 category → total:0」区分。"
  - id: R2
    category: coverage
    question: "「仅 1 个有效分类时仍展示 TOC」是否必须在本期 E2E 自动化中覆盖？"
    why_it_matters: "影响数据夹具与门禁范围。"
    suggestion: "本期 P0 以多分类为主；单分类 TOC 降为 P2。"
    status: resolved
    answer: "本期 P0 以多分类种子为主；单分类 TOC 展示降为 P2（可手工冒烟）；文档标注需求有述、自动化本期不强制。"
  - id: R3
    category: test_strategy
    question: "列表页描述「摘要截断」是否要求断言具体字符长度？"
    why_it_matters: "避免用例绑定实现细节。"
    suggestion: "不强制具体截断长度；摘要可识别即可。"
    status: resolved
    answer: "不强制具体截断长度；有描述时页面展示可识别为同源内容的摘要/前缀即可。"
  - id: R4
    category: scenario
    question: "分页「页间不重复」是否依赖稳定排序？用例是否断言具体排序键？"
    why_it_matters: "统一分页验收口径。"
    suggestion: "实现保证稳定序；用例不断言排序键。"
    status: resolved
    answer: "实现保证稳定序；用例不断言具体排序键，只断言同条件下页间 id 不重复且与 API 当页一致。"
  - id: R5
    category: test_strategy
    question: "领域规则支撑用例 TC-DOM-* 是否纳入本期自动化门禁？"
    why_it_matters: "门禁范围与验收 #11。"
    suggestion: "P0 门禁 = TC-API P0 + TC-E2E P0；TC-DOM 为 P1。"
    status: resolved
    answer: "P0 门禁 = 全部 TC-API P0 + TC-E2E P0；TC-DOM-* 为 P1 推荐，不阻塞验收 #11。"
```

```yaml review_plan_tests_approval
status: approved
confirmed_at: "2026-08-16T16:12:00+08:00"
user_note: "用户已确认 plan 与 test-cases 业务覆盖一致"
```

---

## 1. 覆盖结论

需求验收 **1–11** 在修订后的 plan 与 test-cases 中均可追溯；无写操作/鉴权/滚动 TOC 等范围蔓延。业务口径 R1–R5 已澄清并回写两份文档。

| 验收 # | 要点 | plan | test | 结论 |
|--------|------|------|------|------|
| 1 | 默认列表 active，`total`/items | §2.1、§6 | TC-API-01/10、TC-DOM-01 | 覆盖 |
| 2 | category 过滤 | §2.1 | TC-API-02 | 覆盖 |
| 3 | 分页页间不重复 | §2.1 稳定序、§6 | TC-API-03/09 | 覆盖（R4） |
| 4 | categories 不收缩 | §2.1、§5.1 | TC-API-04、TC-DOM-02 | 覆盖 |
| 5 | 详情 200/404 | §2.2 | TC-API-11/12/13、TC-DOM-03 | 覆盖 |
| 6 | 非法 400；无匹配空列表；越界页真实 total | §2.1 | TC-API-05/06/07/08 | 覆盖（R1） |
| 7 | 打开页见 TOC+列表 | §4 | TC-E2E-01 | 覆盖 |
| 8 | TOC 过滤+高亮 | §4.2 | TC-E2E-02/03 | 覆盖 |
| 9 | 列表与 API 一致 | §4.1 | TC-E2E-04 | 覆盖（R3） |
| 10 | 分页 UI | §4.1 | TC-E2E-05 | 覆盖 |
| 11 | 自动化通过 | §5.3 门禁 | TC-API P0 + TC-E2E P0 | 覆盖（R5） |

**补充**：匿名（TC-API-14、TC-E2E-09）；空/加载/错态（E2E-06/07 P1）；键盘 TOC（E2E-08 P1）；单分类 TOC（E2E-08b P2，本期不强制自动化）。

---

## 2. 已澄清业务/策略项

| ID | 结论（用户确认：R1=A；R2–R5=建议默认） |
|----|------------------------------------------|
| R1 | 越界页 `items=[]`，`total`=真实匹配总数 |
| R2 | 单分类 TOC：产品须支持；E2E 自动化本期不强制（P2） |
| R3 | 描述摘要可识别，不断言截断长度 |
| R4 | 稳定排序；不断言排序键 |
| R5 | P0 门禁不含 TC-DOM |

技术项 **D1–D4**（JSON 命名、path、Filter、price 类型）保留在 `02-plan.md` checklist，**不在**本 review 定稿。

---

## 3. 对 plan / test-cases 的主要修订（业务层面）

### `02-plan.md`

- §2.1 明确：稳定排序；无匹配 `total:0` vs 越界页「空 items + 真实 total」
- §4.1–4.2：描述摘要口径；单分类 TOC 产品必做、E2E P2
- §5.1 / §5.3 / §6：越界页语义、P0 门禁范围
- §8.2 写入 R1–R5 业务结论；D1–D4 仍为技术 pending

### `02-test-cases.md`

- TC-API-06：去掉「待 review」，固定真实 `total`
- TC-API-03 / TC-E2E-05：稳定序、不断言排序键
- TC-E2E-04：不断言截断长度
- TC-E2E-08 拆为键盘（P1）与单分类 08b（P2）
- §6 改为已澄清结论；验收 #11 门禁写清

---

## 4. Workflow 状态

| 字段 | 值 |
|------|-----|
| node | review_plan_and_tests |
| status | awaiting_user_approval |
| phase | review |
| pending_count | 0 |
| all_resolved | true |
| plan_approval | pending（待本定稿一并确认） |
| test_cases_approval | pending |
| review_plan_tests_approval | pending |
| next_node | create_tasks（全部 approved 后） |
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
