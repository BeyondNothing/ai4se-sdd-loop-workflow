# 任务拆分初稿：产品列表与目录导航（TOC）

> 节点 ID: `split_tasks`  
> AI 工具: `cursor`  
> 模式: `interactive`  
> 生成时间: 2026-08-16T16:13:00+08:00  
> 基于: `01-requirements.md`、`02-plan.md`、`02-test-cases.md`、`02-plan-test-review.md`  
> 备注: `skip_clarification=true`；技术项 D1–D4 与拆分粒度已按 plan suggestion 落定为 resolved，可直接进入定稿。

---

```yaml clarification_checklist
all_resolved: true
pending_count: 0
items:
  - id: T1
    category: api_contract
    question: "产品 API JSON 字段命名采用全局 SNAKE_CASE（如 page_size）还是与需求文档字面 camelCase（如 pageSize）？"
    why_it_matters: "现有 application.yml 已配置 SNAKE_CASE；决定 API/E2E/前端取值字段。"
    suggestion: "跟随全局 SNAKE_CASE：响应 page_size；查询参数仍用 page、pageSize（Spring 绑定字面名）。"
    status: resolved
    answer: "跟随全局 Jackson SNAKE_CASE。响应字段：items、total、page、page_size、categories；产品字段 id、name、category、price、description、status。查询参数字面名为 page、pageSize、category。实现报告与测试显式记录该约定。"
  - id: T2
    category: routing
    question: "产品列表页最终 URL path 定为 `/products` 还是 `/products.html`？"
    why_it_matters: "影响静态资源、E2E 打开地址、README 与实现报告。"
    suggestion: "static/products.html + ViewController/forward 友好路径 `/products`。"
    status: resolved
    answer: "静态文件 `src/main/resources/static/products.html`；infrastructure 注册 `/products` → forward:/products.html。E2E 与 README 以友好路径 `/products` 为准；最终 path 写入 04-implementation.md。"
  - id: T3
    category: security
    question: "如何让产品 API 匿名可访问（现有 JwtAuthFilter 对非白名单 `/api/**` 要求 Bearer）？"
    why_it_matters: "未放行则 API/E2E 全部 401；需求要求匿名且不耦合 auth 业务。"
    suggestion: "扩展 JwtAuthFilter 对 GET/HEAD 产品 API 放行；不引入 spring-boot-starter-security。"
    status: resolved
    answer: "在 JwtAuthFilter 中对 GET/HEAD `/api/products`（精确）与 GET/HEAD `/api/products/{id}`（路径前缀 `/api/products/`）放行。不引入完整 Spring Security；不改登录/受保护接口语义；catalog 业务代码不依赖 auth 领域模型。静态页 `/products` 本身已因非 `/api/**` 放行，另需 ViewController。"
  - id: T4
    category: api_contract
    question: "列表/详情响应中 `price` 的 JSON 类型是 number 还是格式化 string？"
    why_it_matters: "影响序列化、前端展示与断言。"
    suggestion: "领域 BigDecimal scale=2；API 以 JSON number 输出；页面 toFixed(2)。"
    status: resolved
    answer: "领域用不可变金额值对象（BigDecimal，scale=2，非负）；API 以 JSON number 输出（两位小数语义）；页面用 toFixed(2) 或等价展示。不在 domain 做展示格式化字符串。"
  - id: T5
    category: task_scope
    question: "任务粒度按 DDD 四层拆分还是按垂直 API 切片？"
    why_it_matters: "定制约束要求 domain → infrastructure → application → interfaces。"
    suggestion: "按层拆主任务；API 详细设计独立成章；UI/测试/文档收口。"
    status: resolved
    answer: "按 DDD 层拆分主任务并标明依赖；API 契约集中在「API 详细设计」供接口任务引用；静态 UI、API 自动化、E2E/文档分任务收口。JwtAuthFilter 放行作为独立小任务（触及 auth.infrastructure）。"
  - id: T6
    category: api_contract
    question: "列表稳定排序的具体键如何选定？"
    why_it_matters: "分页页间不重复依赖稳定序；用例不断言排序键（R4）。"
    suggestion: "按 ProductId 字符串字典序升序。"
    status: resolved
    answer: "列表在过滤后按 `id` 字符串升序稳定排序；用例与 E2E 不断言排序键，只断言页间 id 不重复及与 API 当页一致。"
  - id: T7
    category: api_contract
    question: "非法 id 形态（空段等）详情 API 返回 404 还是 400？"
    why_it_matters: "计划建议统一 404 避免泄露；需在任务契约写死。"
    suggestion: "统一 404。"
    status: resolved
    answer: "详情找不到、inactive、或无法解析为有效产品 id 的路径形态一律 HTTP 404 + 统一错误体；不区分「格式非法」与「不存在」。"
  - id: T8
    category: api_contract
    question: "catalog 错误响应是否复用 auth 的 `{error,message}`？"
    why_it_matters: "客户端与测试断言一致性；可扩展 GlobalExceptionHandler 或平行 Advice。"
    suggestion: "复用同一结构与 bad_request / not_found 码。"
    status: resolved
    answer: "统一 `{ \"error\": \"<code>\", \"message\": \"<明文>\" }`。非法分页 → 400 + error=`bad_request`；产品不可见/不存在 → 404 + error=`not_found`。可扩展现有 GlobalExceptionHandler 映射 catalog 领域异常，或 catalog 专用 Advice 输出同结构；不得另造字段集。"
```

---

## 0. 初稿摘要

| 项 | 内容 |
|----|------|
| 需求类型 | 新需求（new） |
| 限界上下文 | `catalog`（包根建议 `com.zeiss.ecp.assistant.catalog`） |
| 拆分策略 | 基础设施 → 核心能力 → 联调 → 测试；层序 domain → infra → application → interfaces |
| 决策状态 | 全部 resolved（含原 plan D1–D4 → T1–T4） |
| 下一阶段 | 输出定稿 `03-tasks.md`，待 `tasks_approval` |

## 1. 任务总览（草稿）

| ID | 标题 | 优先级 | 影响模块 | 预估 |
|----|------|--------|----------|------|
| TASK-01 | 领域层：Product 聚合、Port、规则与异常 | P0 | catalog.domain | 0.5d |
| TASK-02 | 基础设施：JSON 仓储、种子、配置 | P0 | catalog.infrastructure | 0.75d |
| TASK-03 | 基础设施：JwtAuthFilter 产品 API 放行 | P0 | auth.infrastructure | 0.25d |
| TASK-04 | 应用层：listProducts / getProduct | P0 | catalog.application | 0.5d |
| TASK-05 | 接口层：Controller、DTO、Assembler、异常映射 | P0 | catalog.interfaces | 0.5d |
| TASK-06 | 静态列表页：TOC 过滤 + 页码分页 | P0 | static + infra 视图 | 0.5d |
| TASK-07 | API 自动化（TC-API P0） | P0 | src/test | 0.5d |
| TASK-08 | E2E（TC-E2E P0）+ README / 实现报告要点 | P0 | docs + e2e | 0.5d |

## 2. 依赖草图

```text
TASK-01 domain
    │
    ▼
TASK-02 infra（文件仓储/种子/配置）
    │
    ├──────────────────┐
    ▼                  ▼
TASK-04 application   TASK-03 JwtAuthFilter 放行
    │                  │
    └────────┬─────────┘
             ▼
        TASK-05 interfaces（§API）
             │
             ▼
        TASK-06 静态 UI `/products`
             │
             ▼
        TASK-07 API 测试
             │
             ▼
        TASK-08 E2E + 文档
```

## 3. API 详细设计要点（草稿，定稿写全）

- `GET /api/products`：匿名；query `category?`/`page`/`pageSize`；响应 snake_case；越界页 `items=[]` 且 `total` 真实；非法分页 400。
- `GET /api/products/{id}`：匿名；active→200；缺失/inactive/非法形态→404。
- 页面 `GET /products` → `products.html`。
- 错误体对齐 auth：`error` + `message`。

## 4. Workflow 状态（初稿）

| 字段 | 值 |
|------|-----|
| node | split_tasks |
| status | draft_ready |
| skip_clarification | true |
| pending_count | 0 |
| all_resolved | true |
| next | finalize `03-tasks.md` |
| updated_at | 2026-08-16T16:13:00+08:00 |

## Workflow 状态

| 字段 | 值 |
|------|-----|
| node | split_tasks |
| status | completed |
| next_node | implement_code |
| phase | tasks |
| pending_count | 0 |
| all_resolved | true |
| updated_at | 2026-08-16T16:14:29 |
