# 需求分析与澄清

> 节点 ID: `analyze_requirements`
> AI 工具: `cursor`
> 模式: `interactive`
> 生成时间: 2026-08-16T15:53:53+08:00
> 执行状态: 进行中
> 备注: 已声明跳过交互澄清；清单项按建议默认值全部 resolved

---

```yaml clarification_checklist
all_resolved: true
pending_count: 0
items:
  - id: Q1
    category: data
    question: "产品数据采用何种本地存储方式（内存 / 文件 / 数据库）？"
    why_it_matters: "影响基础设施层仓储实现选型、启动依赖与验收环境准备。"
    suggestion: "采用本地文件持久化（如 JSON）；预置 ≥2 分类、每类 ≥2 产品；不引入外部独立数据库服务。"
    status: resolved
    answer: "采用本地文件持久化；预置至少 2 个分类、每类至少 2 条 active 产品（合计 ≥4）；可另含至少 1 条 inactive 便于验证默认过滤。不引入外部独立数据库服务。"
  - id: Q2
    category: scope
    question: "是否实现单产品详情 API（GET /api/products/{id}）？"
    why_it_matters: "影响验收条目、应用用例与接口层暴露范围。"
    suggestion: "本期实现；active 返回 200，不存在或 inactive 返回 404。"
    status: resolved
    answer: "本期实现 GET /api/products/{id}：存在且 active 返回 200 与产品对象；不存在或 inactive 返回 404。"
  - id: Q3
    category: scope
    question: "TOC 点击后采用「页面滚动定位」还是「过滤列表仅显示该分类」？"
    why_it_matters: "决定 UI 交互与 E2E 断言口径，须在实现报告中可说明。"
    suggestion: "采用过滤模式：点击 TOC 项后列表仅显示该分类（可带「全部」恢复未过滤）；当前 TOC 项高亮。"
    status: resolved
    answer: "采用过滤模式：点击 TOC 分类后列表仅展示该分类产品（调用或等价于带 category 的列表查询）；提供「全部」或等价入口恢复未按分类过滤；激活 TOC 项须有视觉区分（高亮或 aria-current）。实现报告中说明该选择。"
  - id: Q4
    category: compatibility
    question: "产品列表页与产品 API 是否由同一后端进程同源提供？"
    why_it_matters: "影响 CORS、部署与本地启动；workflow e2e.base_url 为 http://localhost:8080。"
    suggestion: "同一服务同源提供静态列表页与 /api/products*；默认监听 8080（可配置）。"
    status: resolved
    answer: "同一后端进程同源提供最小产品列表页与产品 API；默认端口 8080，可通过环境变量或配置文件设置，与 workflow.e2e.base_url 对齐。"
  - id: Q5
    category: architecture
    question: "产品目录能力是否作为独立限界上下文按 DDD 四层落地？"
    why_it_matters: "项目定制约束要求需求/计划/实现按四层描述与拆分。"
    suggestion: "新建 catalog（或 product）限界上下文，包结构按 interfaces / application / domain / infrastructure 划分。"
    status: resolved
    answer: "作为独立 catalog 限界上下文新建；严格按 DDD 四层：interfaces（REST/页面入口适配）→ application（列表查询、详情查询用例）→ domain（产品聚合、分类/状态规则与仓储 Port）→ infrastructure（文件仓储实现、配置、静态页托管）。禁止 Controller 直调仓储或跨层违规依赖。"
  - id: Q6
    category: scope
    question: "列表页分页交互采用页码分页还是「加载更多」？"
    why_it_matters: "影响 UI 与 E2E 步骤；须与 API 分页语义一致。"
    suggestion: "采用页码分页（上一页/下一页或页码），与 API page/pageSize 一致。"
    status: resolved
    answer: "列表页采用页码分页（至少支持上一页/下一页或等价翻页），请求参数与 API 的 page、pageSize 一致；默认 page=1、pageSize=10、pageSize 最大 50。"
  - id: Q7
    category: security
    question: "产品列表 API 与列表页是否要求登录鉴权？"
    why_it_matters: "决定是否与 auth 模块耦合及 E2E 前置步骤。"
    suggestion: "本期匿名可访问；不做登录拦截。"
    status: resolved
    answer: "本期列表 API 与列表页默认可匿名访问，不要求登录鉴权；不与 auth 登录流程耦合。权限控制留后续迭代。"
  - id: Q8
    category: acceptance
    question: "列表默认过滤与 categories 字段的口径如何约定？"
    why_it_matters: "影响 API 验收与 TOC 数据来源一致性。"
    suggestion: "列表默认仅返回 active；categories 为当前数据集中所有有效（active）产品的去重分类，不随当前 category 过滤结果收缩。"
    status: resolved
    answer: "列表默认仅返回 status=active 的产品。categories 为数据集中全部 active 产品的去重分类列表（供 TOC），即使请求带了 category 过滤，categories 仍反映全部有效分类，不因当前过滤结果而缩小。"
```

# 需求分析初稿：产品列表与目录导航（TOC）

> 状态：初稿（已跳过交互澄清；清单项按建议默认值全部 resolved）

## 1. 需求判断

| 项 | 结论 |
|----|------|
| 需求类型 | **新需求** |
| 判断依据 | 系统尚无统一产品列表、结构化产品 API 与 TOC 导航能力；本次从零建设 |
| 变更范围 | 新建 catalog 限界上下文（DDD 四层）+ 最小产品列表页 + 配置与 API/E2E 测试 |
| 兼容性风险 | **低**（无既有产品 API/列表页契约需兼容） |

## 2. 背景与目标

### 背景

系统需要向用户展示可浏览的产品目录。当前缺少统一的产品列表页与目录导航（TOC）能力，用户难以按分类快速定位产品，也无法通过 API 获取结构化产品数据。

### 目标

实现产品列表 API + 列表页 Web UI + TOC 导航，使用户可以：

1. 通过 API 分页查询产品列表
2. 在浏览器打开列表页，通过 TOC 按分类过滤定位产品
3. 完成端到端验收（页面加载、TOC 切换、列表展示）

## 3. 现状与差距

- 无产品领域模型与仓储
- 无 `GET /api/products`（及详情）能力
- 无带 TOC 的产品列表页与 E2E 路径
- 需按 DDD 四层新建 catalog 模块，而非在既有模块上打补丁

## 4. 范围

### 本次包含

- 产品读能力：列表分页/分类过滤 + 单产品详情
- 预置种子数据（≥2 分类、每类 ≥2 active；建议含 inactive 样本）
- 列表页 + TOC（过滤模式）+ 分页
- API 测试 + 浏览器 E2E
- 可配置端口与分页默认值；同源可运行

### 本次不包含

- 产品新增/编辑/删除后台
- 购物车、下单、支付
- 全文检索/多条件复杂搜索
- 登录鉴权（列表匿名可访问）
- 完整 SPA/设计系统

## 5. 角色与场景（摘要）

| 角色 | 主路径 |
|------|--------|
| 终端用户 | 打开列表页 → 看 TOC 与产品 → 点 TOC 过滤 → 翻页 |
| API 调用方 | `GET /api/products`（可选 category/page/pageSize）及详情 |
| 开发/测试 | 种子数据 + API 测试 + E2E |

## 6. 功能需求要点（按 DDD 四层归属）

- **domain**：产品聚合（id/name/category/price/description/status）；列表仅 active 等规则；ProductRepository Port
- **application**：列表查询、详情查询用例；编排聚合与 Port；事务边界在本层
- **interfaces**：`GET /api/products`、`GET /api/products/{id}`；DTO；薄 Controller
- **infrastructure**：文件仓储实现、种子数据、静态列表页托管、配置
- **Web UI**：列表页（path 实现阶段确认，示例 `/products`）；TOC 过滤；分页；空/加载/错误态

## 7. 非功能与验收（摘要）

- 可配置、可测试（API + E2E）、默认可访问 `http://localhost:8080`
- 验收覆盖：列表/过滤/分页/categories、详情 200/404、TOC 可见与过滤、字段一致、自动化通过
- 架构须符合 DDD 四层与依赖方向

## 8. 假设与默认（跳过澄清已固化）

见顶部 `clarification_checklist` 各条目 `answer`。

## Workflow 状态

| 字段 | 值 |
|------|-----|
| node | analyze_requirements |
| status | completed |
| next_node | parallel_plan_and_tests |
| phase | requirements |
| pending_count | 0 |
| all_resolved | true |
| updated_at | 2026-08-16T15:55:12 |
