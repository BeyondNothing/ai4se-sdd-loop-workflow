# 任务拆分

> 节点 ID: `split_tasks`  
> AI 工具: `cursor`  
> 模式: `interactive`  
> 生成时间: 2026-08-16T16:13:00+08:00  
> 执行状态: 待用户确认定稿  
> 备注: 决策已全部 resolved（`skip_clarification=true`，含原 plan D1–D4）；等待用户定稿确认

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

```yaml tasks_approval
status: approved
confirmed_at: "2026-08-16T16:14:00+08:00"
user_note: "确认"
```

# 任务定稿：产品列表与目录导航（TOC）

> 节点 ID: `split_tasks`  
> 需求类型: `new`  
> 依据文档: `01-requirements.md`、`02-plan.md`、`02-test-cases.md`、`02-plan-test-review.md`  
> 决策来源: 初稿清单已全部 resolved（本节点 `skip_clarification=true`，T1–T4 对齐 plan D1–D4 suggestion）

---

## 1. 任务总览表

| ID | 标题 | 优先级 | 影响模块 | 预估工时 |
|----|------|--------|----------|----------|
| TASK-01 | 领域层：Product 聚合、Port、可见性/金额规则与异常 | P0 | `catalog.domain` | 0.5d |
| TASK-02 | 基础设施：JSON 产品仓储、种子数据、Catalog 配置 | P0 | `catalog.infrastructure` | 0.75d |
| TASK-03 | 基础设施：JwtAuthFilter 放行产品 API（匿名 GET/HEAD） | P0 | `auth.infrastructure` | 0.25d |
| TASK-04 | 应用层：listProducts / getProduct 用例编排 | P0 | `catalog.application` | 0.5d |
| TASK-05 | 接口层：ProductController、DTO、Assembler、异常映射 | P0 | `catalog.interfaces` | 0.5d |
| TASK-06 | 最小静态 UI：产品列表页 TOC 过滤 + 页码分页 | P0 | `static` + catalog infra 视图映射 | 0.5d |
| TASK-07 | API 自动化测试（TC-API P0 门禁） | P0 | `src/test` | 0.5d |
| TASK-08 | 浏览器 E2E（TC-E2E P0）+ README / 实现报告要点 | P0 | docs + e2e | 0.5d |

包根：`com.zeiss.ecp.assistant.catalog`（与现有 `..auth` 并列；工程根 `pom.xml`，Java 17 + Spring Boot 3.3）。

**P0 验收门禁（验收 #11）**：TASK-07 覆盖全部 TC-API P0 + TASK-08 覆盖全部 TC-E2E P0。TC-DOM / E2E P1–P2 推荐但不阻塞。

---

## 2. 任务详情

### TASK-01 — 领域层：Product 聚合、Port 与规则

| 项 | 内容 |
|----|------|
| **目标** | 建立 catalog 领域模型、仓储 Port 与可见性/金额不变式，供外层依赖倒置 |
| **输入** | 需求 §7.1、计划 §3.1、决策 T4/T5/T6、TC-DOM-* |
| **输出** | `Product` 聚合根、`ProductId`、`ProductStatus`（ACTIVE/INACTIVE）、金额值对象（如 `Money`/`Price`，BigDecimal scale=2 非负）；`ProductRepository` Port；可选 `CatalogQueryDomainService`（有效分类去重）；`ProductNotFoundException`、`InvalidPaginationException`（或等价）；领域单元测试（TC-DOM-01/02/03） |
| **涉及路径** | `src/main/java/.../catalog/domain/**`；`src/test/java/.../catalog/domain/**` |
| **依赖** | 无（首任务） |
| **DoD** | ① domain 无 Spring/JPA/Servlet/Jackson 等 outward 依赖；② 可见性由领域行为表达（如 `isVisibleInCatalog()` → 仅 ACTIVE）；③ 金额不变式可测；④ Port 以聚合根为粒度；⑤ 领域单测覆盖默认可见范围、TOC 分类来源排除无 active 分类、inactive/缺失详情语义 |

### TASK-02 — 基础设施：文件仓储、种子、配置

| 项 | 内容 |
|----|------|
| **目标** | 以本地 JSON 实现 `ProductRepository`，预置验收种子，配置可注入 |
| **输入** | TASK-01；需求 Q1；计划 §3.2–3.3；决策 T4 |
| **输出** | `FileProductRepository`、`ProductFileRecord`（`toDomain`/`toPo` 仅在本层）、`ProductDataInitializer`、`CatalogProperties`、`CatalogInfrastructureConfig`；`application.yml` 默认项；独立 ObjectMapper 读写文件（避免 HTTP SNAKE_CASE 污染磁盘字段） |
| **涉及路径** | `.../catalog/infrastructure/persistence/**`、`.../infrastructure/config/**`；`src/main/resources/application.yml`；默认数据文件 `./data/products.json`（运行时生成） |
| **依赖** | TASK-01 |
| **DoD** | ① 文件不存在或空时写入种子：≥2 分类、每类 ≥2 active（合计 ≥4）、≥1 inactive；条数足以用较小 `pageSize` 测第二页；② 配置：`catalog.products.file`（默认 `./data/products.json`）、`catalog.paging.default-page=1`、`default-page-size=10`、`max-page-size=50`；③ 读写锁或等价并发安全（对齐 FileUserRepository）；④ PO/SDK 类型不泄漏到 application/interfaces；⑤ Bean 绑定 Port → Impl |

### TASK-03 — 基础设施：JwtAuthFilter 产品 API 放行

| 项 | 内容 |
|----|------|
| **目标** | 使产品列表/详情 API 匿名可访问，满足 Q7 / TC-API-14 |
| **输入** | 决策 T3；现有 `JwtAuthFilter` |
| **输出** | 更新后的公开路径规则；既有 auth 公开/受保护行为不变 |
| **涉及路径** | `.../auth/infrastructure/security/JwtAuthFilter.java`（及必要时既有 Filter 单测/集成回归） |
| **依赖** | 无强依赖 catalog 代码；建议与 TASK-02 并行或紧随其后，须在 TASK-05/07 前完成 |
| **DoD** | ① GET/HEAD `/api/products` 与 GET/HEAD `/api/products/{id}`（前缀 `/api/products/`）不要求 Bearer；② 不引入 `spring-boot-starter-security`；③ `/api/auth/me`、`/api/auth/logout` 等既有受保护路径仍 401；④ catalog 不 import auth 领域模型 |

### TASK-04 — 应用层：列表与详情用例

| 项 | 内容 |
|----|------|
| **目标** | 编排 list/get 用例：分页校验、过滤、稳定排序、categories 全量口径、详情可见性 |
| **输入** | TASK-01；计划 §5.1；业务口径 R1/R4；决策 T6 |
| **输出** | `CatalogApplicationService`（或 `ProductQueryApplicationService`）：`listProducts`、`getProduct`；可选 `ListProductsQuery`；只读视图 DTO（如 `ProductView`、`ProductListResult`）；应用层单测（Mock Repository） |
| **涉及路径** | `.../catalog/application/**`；`src/test/java/.../catalog/application/**` |
| **依赖** | TASK-01（Port/领域）；运行时需 TASK-02 实现，测试可用 Mock |
| **DoD** | ① 仅依赖 domain Port/领域对象，禁止 import infrastructure 实现类；② 非法分页抛领域/应用异常供映射 400；③ 默认仅 active；分类过滤；按 id 升序稳定排序后切片；④ 越界页：`items` 空且 `total` 为真实匹配数；无匹配分类：`total=0`；⑤ `categories` 来自全部 active 去重，不随当前 category 收缩；⑥ 详情对不可见/缺失抛 `ProductNotFoundException`；⑦ 核心不变式不堆在上帝 Service（可见性/金额在领域） |

### TASK-05 — 接口层：REST 适配与异常映射

| 项 | 内容 |
|----|------|
| **目标** | 暴露 §3 约定的产品 API；薄 Controller；统一错误体 |
| **输入** | TASK-04；决策 T1/T7/T8；API 详细设计 §3 |
| **输出** | `ProductController`；`ProductResponse` / `ProductListResponse` 等；Assembler；扩展 `GlobalExceptionHandler` 或 catalog `@RestControllerAdvice`（同结构） |
| **涉及路径** | `.../catalog/interfaces/**`；可选改动 `.../auth/interfaces/exception/GlobalExceptionHandler.java` |
| **依赖** | TASK-04；TASK-03（联调匿名访问） |
| **DoD** | ① Controller **仅**依赖 ApplicationService，禁止注入 Repository/Entity；② Query：`category` 可选；`page` 默认 1；`pageSize` 默认 10、最大 50（参数名字面 `page`/`pageSize`）；③ 响应 JSON 为 snake_case（含 `page_size`）；`price` 为 number；④ 非法参数 → 400 `bad_request`；详情不可见 → 404 `not_found`；⑤ 对齐 §3.1–3.2 契约 |

**引用**：API 详细设计 §3.1、§3.2、§3.5。

### TASK-06 — 静态列表页（TOC + 分页）

| 项 | 内容 |
|----|------|
| **目标** | 同源最小可用产品列表页，落实 TOC 过滤与页码分页 |
| **输入** | TASK-05；决策 T2；需求 §7.5；TC-E2E-* |
| **输出** | `static/products.html`（及可选少量 CSS/JS）；`/products` → `forward:/products.html`（catalog infra Config，对齐 auth `/login`） |
| **涉及路径** | `src/main/resources/static/products.html`（及可选 `static/css|js`）；`.../catalog/infrastructure/config/*` |
| **依赖** | TASK-05 |
| **DoD** | ① 打开 `/products` 可见 TOC（「全部」+ categories）与列表；② 点击分类带 `category` 拉列表且 `page` 重置为 1；「全部」去 category；③ 激活项高亮或 `aria-current`；TOC 可 Tab 聚焦；④ 页码翻页（至少上一页/下一页），参数与 API 一致；⑤ 展示名称、分类、价格两位小数、描述摘要（可识别即可，不断言截断长度）；⑥ 空状态/加载中/错误态基本提示；⑦ 匿名、无登录跳转；⑧ 仅 1 个有效分类时仍展示 TOC（产品行为；E2E 自动化本期不强制） |

### TASK-07 — API 自动化测试

| 项 | 内容 |
|----|------|
| **目标** | 用 MockMvc/`@SpringBootTest` 覆盖 TC-API P0，作为验收 #11 门禁一半 |
| **输入** | TASK-05、TASK-03；`02-test-cases.md` TC-API-*；决策 T1/T4 |
| **输出** | 如 `CatalogApiIntegrationTest`（命名以实现为准）；断言字段用 **snake_case**（`page_size` 等） |
| **涉及路径** | `src/test/java/.../catalog/**` |
| **依赖** | TASK-02、TASK-03、TASK-05 |
| **DoD** | ① 覆盖 TC-API-01～08、10～13（P0）；TC-API-09/14 为 P1 推荐；② 含：默认列表、category 过滤、分页不重复、categories 不收缩、空分类、越界页真实 total、非法 page/pageSize→400、详情 200/404/inactive 404、字段完整性；③ 匿名调用不出现鉴权 401；④ 不破坏既有 auth 集成测试 |

**引用**：§3.1、§3.2。

### TASK-08 — E2E + 文档收口

| 项 | 内容 |
|----|------|
| **目标** | 浏览器验收 TC-E2E P0；启动说明与实现报告记录最终 path 与 T1–T8 决议 |
| **输入** | TASK-06、TASK-07；workflow `e2e.base_url=http://localhost:8080` |
| **输出** | Playwright（或等价）E2E 场景/脚本；根 `README.md` 更新；`04-implementation.md` 要点（path、命名、Filter、price 类型） |
| **涉及路径** | 仓库根 `README.md`；`dev-workflow/docs/product-list-toc/04-implementation.md`（实现节点）；E2E 资产 |
| **依赖** | TASK-06、TASK-07 |
| **DoD** | ① 打开 `/products` → TOC 可见 → 点击过滤 → 列表符合预期 → 「全部」恢复 → 翻页与 API 一致 → 匿名可访问（TC-E2E-01～05、09）；② README：启动、`catalog.products.file`、列表页 URL、已知限制（只读/匿名/文件存储）；③ 架构自检清单可勾选（四层、DIP、Controller 不直调仓储） |

---

## 3. API 详细设计

> 全局：`Content-Type: application/json`（错误与成功 JSON）；Jackson **SNAKE_CASE**；默认基址 `http://localhost:8080`。  
> 查询参数名按 Spring 绑定**字面**约定（camelCase：`pageSize`）；响应键为 snake_case。

### 3.1 GET `/api/products`（公开 / 匿名）

**用途**：分页查询 active 产品；可选按分类过滤；返回 TOC 用全量有效分类。

**鉴权**：无（JwtAuthFilter 放行 GET/HEAD）。

**Query**

| 参数 | 类型 | 必填 | 默认 | 约束 |
|------|------|------|------|------|
| `category` | string | 否 | — | 精确匹配产品分类；不存在则空列表 |
| `page` | int | 否 | `1`（或 `catalog.paging.default-page`） | ≥ 1；非法 → 400 |
| `pageSize` | int | 否 | `10`（或配置） | 1～50（含）；≤0 或 >50 → 400 |

**成功响应** `200 OK`

```json
{
  "items": [
    {
      "id": "p-001",
      "name": "示例显微镜 A",
      "category": "显微镜",
      "price": 12999.00,
      "description": "可选描述",
      "status": "active"
    }
  ],
  "total": 4,
  "page": 1,
  "page_size": 10,
  "categories": ["显微镜", "影像系统"]
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `items` | array | 当页产品；元素字段见下表 |
| `total` | number | 当前过滤条件下 active 匹配总数（**越界页仍为真实总数**；无匹配分类则为 0） |
| `page` | number | 请求页码 |
| `page_size` | number | 请求页大小 |
| `categories` | string[] | 数据集中全部 **active** 产品去重分类；**不因**当前 `category` 过滤收缩；不含仅 inactive 关联的分类 |

**`items[]` 元素**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | 是 | 产品 id |
| `name` | string | 是 | 名称 |
| `category` | string | 是 | 分类 |
| `price` | number | 是 | 元；两位小数语义（JSON number，非格式化 string） |
| `description` | string | 否 | 可缺省 |
| `status` | string | 是 | 列表场景均为 `active` |

**排序**：过滤后按 `id` 字符串升序（稳定）；调用方不断言键名，只依赖稳定性。

**业务规则摘要**

| 场景 | HTTP | 行为 |
|------|------|------|
| 默认列表 | 200 | 仅 active；含 `categories` 全量 |
| `category` 过滤 | 200 | 仅该分类 active；`categories` 仍全量 |
| 不存在的 category | 200 | `items=[]`，`total=0`，`categories` 仍全量 |
| `page` 超出末页（参数合法） | 200 | `items=[]`，`total`=真实匹配总数 |
| `page`&lt;1 / `pageSize` 非法或 &gt;50 / 非数字 | 400 | 见 §3.5 |

**引用任务**：TASK-05（实现）、TASK-07（测试）、TASK-06（前端消费）。

---

### 3.2 GET `/api/products/{id}`（公开 / 匿名）

**用途**：按 id 获取单个 **active** 产品。

**鉴权**：无。

**路径参数**

| 参数 | 说明 |
|------|------|
| `id` | 产品 id |

**成功响应** `200 OK` — 单个产品对象（字段同列表项）。

```json
{
  "id": "p-001",
  "name": "示例显微镜 A",
  "category": "显微镜",
  "price": 12999.00,
  "description": "可选描述",
  "status": "active"
}
```

**错误**

| 场景 | HTTP | error | 说明 |
|------|------|-------|------|
| id 不存在 | 404 | `not_found` | 统一不可见 |
| 产品 inactive | 404 | `not_found` | 与不存在同等对待，不返回正文 |
| id 形态无法解析/无效 | 404 | `not_found` | 决策 T7，不返回 400 |

**引用任务**：TASK-05、TASK-07。

---

### 3.3 页面路由（同源静态）

| 方法 | 路径 | 访问 | 行为 |
|------|------|------|------|
| GET | `/products` | 公开 | forward → `/products.html` |
| GET | `/products.html` | 公开 | 静态资源（Filter 已放行 `*.html`） |

页面匿名；不依赖登录/localStorage。前端用 `fetch` 调 §3.1，字段读 `page_size` 等 snake_case。

**引用任务**：TASK-06、TASK-08。

---

### 3.4 配置项（实现须落地）

| 配置键 | 默认 | 说明 |
|--------|------|------|
| `server.port` | `8080` | 已有；对齐 e2e.base_url |
| `catalog.products.file` | `./data/products.json` | 产品 JSON 路径 |
| `catalog.paging.default-page` | `1` | 列表默认页 |
| `catalog.paging.default-page-size` | `10` | 默认页大小 |
| `catalog.paging.max-page-size` | `50` | 上限 |

---

### 3.5 统一错误体

与 auth 对齐：

```json
{
  "error": "<code>",
  "message": "<human readable>"
}
```

| error | HTTP | 使用场景 |
|-------|------|----------|
| `bad_request` | 400 | 非法分页/参数（`page`、`pageSize` 等） |
| `not_found` | 404 | 产品详情不可见/不存在 |
| `unauthorized` | 401 | **不**应用于本期产品 API（匿名）；保留给 auth 其它路径 |

Filter 对未放行的 `/api/**` 仍写 401；产品路径须已放行故不应出现。

---

## 4. 依赖关系与建议执行顺序

```text
TASK-01 domain
    │
    ▼
TASK-02 infra（仓储/种子/配置）
    │
    ├──────────────────┐
    ▼                  ▼
TASK-04 application   TASK-03 JwtAuthFilter 放行
    │                  │
    └────────┬─────────┘
             ▼
        TASK-05 interfaces（§3 API）
             │
             ▼
        TASK-06 静态 UI `/products`
             │
             ▼
        TASK-07 API 测试（TC-API P0）
             │
             ▼
        TASK-08 E2E（TC-E2E P0）+ README
```

**建议执行顺序（串行）**：  
`TASK-01 → TASK-02 → TASK-03 → TASK-04 → TASK-05 → TASK-06 → TASK-07 → TASK-08`

说明：TASK-03 与 TASK-04 在 TASK-02 后理论上可并行；为降低联调成本推荐串行。若并行，须在 TASK-05 前两者均完成。

**本地验证顺序（实现后）**：`mvn test` → `mvn spring-boot:run` → 访问 `/products` 与 `/api/products` → Playwright E2E。

---

## 5. 与定制约束符合性说明

| 自检项 | 任务侧落实 |
|--------|------------|
| 四层包结构 | TASK-01/02/04/05 分属 domain / infrastructure / application / interfaces |
| domain 无 outward 依赖 | TASK-01 DoD |
| Repository Port 在 domain，实现在 infrastructure | TASK-01/02 |
| Controller 仅依赖 ApplicationService | TASK-05 DoD |
| 核心规则在领域（可见性/金额） | TASK-01；TASK-04 不堆上帝逻辑 |
| 依赖顺序 domain → infra → application → interfaces | §4 |
| 入站 Filter 在 infrastructure，可触发放行（非业务编排） | TASK-03 |
| 测试分层 | domain 单测 TASK-01；应用 Mock TASK-04；API TASK-07；E2E TASK-08 |
| 出站第三方 HTTP | 本期无；若后续增加须按 DIP 定义 Port |

---

## 6. Workflow 状态

| 字段 | 值 |
|------|-----|
| node | split_tasks |
| status | awaiting_user_approval |
| phase | tasks |
| pending_count | 0 |
| all_resolved | true |
| tasks_approval | pending |
| next_node | implement_code（仅当 `tasks_approval.status: approved`） |
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
