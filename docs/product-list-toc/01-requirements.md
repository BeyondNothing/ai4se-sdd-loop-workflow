# 需求分析与澄清

> 节点 ID: `analyze_requirements`
> AI 工具: `cursor`
> 模式: `interactive`
> 生成时间: 2026-08-16T15:53:53+08:00
> 执行状态: 待用户确认定稿
> 备注: 已跳过交互澄清；定稿待 requirement_approval

---

```yaml requirement_metadata
requirement_type: new
requirement_summary: "新增 catalog 限界上下文：产品列表/详情 API、列表页 TOC 分类过滤与分页，及 API/E2E 验收"
judgment_basis: "仓库尚无统一产品目录与 TOC 导航能力，本次从零建设读模型、API、最小列表页与测试"
change_scope: "新建 catalog 四层模块（domain/application/interfaces/infrastructure）、静态产品列表页、种子数据、配置项、API 与 E2E 测试"
affected_modules:
  - "catalog.domain"
  - "catalog.application"
  - "catalog.interfaces"
  - "catalog.infrastructure"
compatibility_risk: low
needs_clarification: false
open_questions_count: 0
```

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

```yaml requirement_approval
status: pending
confirmed_at: "2026-08-16T15:55:00+08:00"
user_note: "确认"
```

# 需求定稿：产品列表与目录导航（TOC）

## 1. 需求判断

| 项 | 结论 |
|----|------|
| 需求类型 | **新需求** |
| 判断依据 | 系统尚无统一产品目录、结构化产品 API 与 TOC 导航；本次从零建设 |
| 变更范围 | 新建 `catalog` 限界上下文（DDD 四层）+ 静态列表页 + 种子数据、配置与测试 |
| 兼容性风险 | **低**（无既有产品列表/API 契约需兼容） |
| 待澄清 | 无（已跳过交互澄清，默认结论见「澄清结论」） |

## 2. 澄清结论

| ID | 结论 |
|----|------|
| Q1 | 本地**文件**持久化产品；预置 ≥2 分类、每类 ≥2 active；建议含 inactive 样本；不引入外部 DB |
| Q2 | **实现**详情 API；active→200，缺失/inactive→404 |
| Q3 | TOC 采用**分类过滤**（非滚动定位）；含「全部」恢复；激活项高亮 |
| Q4 | **同源同进程**提供 UI 与 API；默认端口 **8080**（可配置） |
| Q5 | 独立 **catalog** 限界上下文，严格 **DDD 四层** 与依赖方向 |
| Q6 | UI **页码分页**，与 API `page`/`pageSize` 一致 |
| Q7 | **匿名可访问**；本期不鉴权、不耦合 auth |
| Q8 | 列表默认仅 **active**；`categories` 为全部有效分类，**不随**当前过滤收缩 |

## 3. 背景与目标

### 背景

系统需要向用户展示可浏览的产品目录。当前缺少统一的产品列表页与**目录导航（TOC）**能力，用户难以按分类快速定位产品，也无法通过 API 获取结构化产品数据。

### 目标

实现可落地的**产品列表 API + 列表页 Web UI + TOC 导航**，覆盖：

1. API 分页查询与分类过滤
2. 浏览器列表页通过 TOC 按分类过滤定位
3. 端到端验收（页面加载、TOC 切换、列表展示、分页）

## 4. 现状与差距

- 无 catalog 限界上下文与产品聚合模型
- 无产品列表/详情用例与 REST 暴露
- 无带 TOC 的列表页与联调/E2E 路径
- 需按 DDD 四层新建，依赖方向：interfaces → application → domain ← infrastructure

## 5. 范围

### 5.1 本次包含

- 产品**读**能力：列表（分页、分类过滤）+ 单产品详情
- 产品最小字段：`id`、`name`、`category`、`price`（元，展示保留 2 位小数）、`description`（可选）、`status`（`active`/`inactive`）
- 本地文件存储 + 预置种子数据（≥2 分类、每类 ≥2 active，合计 ≥4；建议含 ≥1 inactive）
- 列表响应须含 `items`、`total`、`page`、`pageSize`、`categories`（口径见澄清 Q8）
- 非法分页等参数返回 `400` 与明确错误信息；无匹配时 `200` + 空列表、`total: 0`
- 最小 Web UI：产品列表页（path 在实现阶段写入 `04-implementation.md`，示例 `/products`）+ TOC 过滤 + 页码分页
- 空列表友好文案；加载中与错误态基本提示
- TOC：与分类一一对应；键盘可 Tab 聚焦；仅 1 个分类时仍展示 TOC（或单条目，实现中说明）
- 可配置：服务端口、分页默认值等；访问基址对齐 `workflow.e2e.base_url`（`http://localhost:8080`）
- API 自动化测试 + 浏览器 E2E（打开列表页 → TOC 可见 → 点击 TOC 过滤 → 列表符合预期）
- 清晰本地启动说明

### 5.2 本次不包含

- 产品新增/编辑/删除后台管理
- 购物车、下单、支付
- 全文检索、多条件复杂搜索
- 登录鉴权与权限体系
- 完整 SPA 框架与设计系统（最小可用页面即可）
- TOC「页面滚动定位」交互（本期明确采用过滤模式）

## 6. 角色与用户场景

| 角色 | 目标 | 主路径 |
|------|------|--------|
| 终端用户 | 浏览产品并按分类快速筛选 | 打开列表页 → 查看 TOC 与产品 → 点击 TOC 过滤 → 翻页 |
| API 调用方 | 获取结构化产品数据 | `GET /api/products`（可选 category/page/pageSize）；可选 `GET /api/products/{id}` |
| 开发/测试 | 稳定验收 | 种子数据 + API 测试 + E2E |

### 关键场景

- 无匹配分类/页码超出：返回空 `items`、`total: 0`，HTTP 200；页面展示空状态文案
- 非法参数（如 `page` < 1、`pageSize` > 50 或非正）：HTTP 400 + 明确错误信息
- 详情：无效 id 或 inactive → 404
- 仅 1 个有效分类：仍展示 TOC

## 7. 功能需求（按 DDD 四层）

> 需求层只描述能力与归属；类名、框架选型、详细 API schema 由 plan/implement 节点展开。下列路径/字段为验收口径约定，非接口详细设计。

### 7.1 领域层（domain）

- **产品聚合**：唯一标识、名称、分类、价格、描述、状态；对外通过聚合/领域行为维护一致性（避免贫血纯 setter 堆逻辑）
- **业务规则**：列表默认仅面向 `active`；`inactive` 不出现在默认列表与 TOC 分类来源；价格展示语义为元、保留 2 位小数（格式化可在接口/展示层完成，不变式如状态枚举留在领域）
- **Port**：产品仓储接口（按聚合根查询列表/按 id 加载等），定义在 domain，实现在 infrastructure
- **领域异常**：产品不可见/不存在等语义，供上层映射为 HTTP 404/400

### 7.2 应用层（application）

- 用例编排（各一 public 用例方法即可）：
  - **列表查询**：按可选分类过滤、分页；默认仅 active；组装 `total`/`page`/`pageSize`；提供全部有效分类列表供 TOC
  - **详情查询**：按 id 加载；仅 active 可见，否则按不存在处理
- 事务边界放在本层；只依赖 domain Port，不依赖 infrastructure 具体类
- 核心不变式留在领域对象/领域服务，避免上帝 ApplicationService

### 7.3 接口层（interfaces）

- REST 适配：`GET /api/products`、`GET /api/products/{id}`
- 列表查询参数约定（均可选）：`category`、`page`（默认 1）、`pageSize`（默认 10，最大 50）
- 列表成功响应约定含：`items`（产品字段）、`total`、`page`、`pageSize`、`categories`
- Request/Response DTO 与领域模型分离；Controller：参数格式校验 → 调 ApplicationService → 组装响应
- 统一异常处理：非法参数 → 400；详情不可见 → 404
- 禁止 Controller 直接操作 Entity / Repository

### 7.4 基础设施层（infrastructure）

- 实现产品仓储（本地文件）；PO/文件模型与领域对象互转留在本层
- 启动或初始化时写入/加载种子数据
- 同源托管静态产品列表页（或等价静态资源适配）
- 框架配置与 Bean 装配；分页默认值、端口等来自配置/环境变量
- 无入站 Webhook/MQ 要求；无出站第三方 HTTP 强制要求（若后续增加，须按 DIP 定义 Port）

### 7.5 最小 Web UI

- 产品列表页（示例 path `/products`，最终 path 写入实现报告）
- **TOC 区域**：展示 API `categories`（或等价数据）；点击后**过滤**列表为该分类；「全部」恢复；当前项高亮/aria-current；可 Tab 聚焦
- **列表区域**：展示名称、分类、价格、描述摘要（可截断）
- **分页**：页码翻页，与 API 分页一致
- 空状态、加载中、错误态有基本提示
- 匿名可访问，无需登录

## 8. 非功能需求

| 类别 | 要求 |
|------|------|
| 可配置 | 监听端口、分页默认值等可通过环境变量或配置文件注入 |
| 可测试 | API：分页、分类过滤、空结果、非法参数、详情 200/404；E2E：打开列表页 → TOC → 过滤 → 列表符合预期 |
| 可运行 | 依赖明确、本地可启动；默认基址 `http://localhost:8080` |
| 安全/权限 | 本期匿名只读；不引入鉴权；无敏感写操作 |
| 架构合规 | 四层包结构清晰；domain 无 outward 依赖；仓储 Port 在 domain 定义、infrastructure 实现；Controller 仅依赖 ApplicationService |

## 9. 变更影响分析

| 影响面 | 说明 |
|--------|------|
| 新增模块 | catalog 四层全套（无既有模块替换） |
| 配置 | 新增端口、分页默认、数据文件路径等 |
| 数据 | 本地产品文件及种子数据初始化 |
| 兼容性 | 低；无旧产品接口需双轨 |
| 与 auth | 本期不耦合；列表匿名访问 |
| 测试 | 新增领域单测、应用/接口测试、E2E |

## 10. 验收标准

### API

1. `GET /api/products` 返回预置 active 产品，`total` 与当页 `items` 长度正确
2. `category` 过滤后仅返回该分类产品
3. 分页生效（第二页与第一页数据不重复）
4. 响应含 `categories`，且与全部 active 产品分类一致（不因当前过滤收缩）
5. `GET /api/products/{id}`：有效 active id → 200；无效或 inactive → 404
6. 非法参数 → 400 与明确错误信息；无匹配 → 200 空列表、`total: 0`

### 列表页 / TOC / E2E

7. 浏览器打开列表页，可见 TOC 与产品列表
8. 点击 TOC 某分类后，列表仅显示该分类产品；激活 TOC 项有视觉区分
9. 列表展示字段与 API 数据一致（名称、价格等）
10. 分页行为正确（翻页后列表变化且与 API 一致）
11. 相关自动化测试通过（含 API；浏览器场景可用 Playwright 或等价方式）

### 架构自检（实现阶段对照）

- 四层放置正确；domain 无 Spring/JPA/Web 等基础设施依赖
- Repository Port 在 domain，实现在 infrastructure
- Controller 仅调用 ApplicationService
- 产品状态/可见性等核心规则可在领域模型或领域服务中定位

## 11. 已知限制与后续可选

- 本期仅读、匿名、文件存储；不支持管理后台写操作
- TOC 不提供滚动锚点模式（若产品后续需要可另开需求）
- 登录鉴权、复杂搜索、购物流程可作为后续迭代

## 12. 与定制约束的符合性说明

本需求按 **DDD 四层** 描述模块与职责：用例在应用层，核心规则与 Port 在领域层，REST/DTO 在接口层，文件仓储与静态页托管在基础设施层；依赖仅外→内。后续 plan / tasks / implement / test 须继续遵守同一规范，冲突须显式提出、不得静默违反。

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
