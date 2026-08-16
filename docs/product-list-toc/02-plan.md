# 实现计划初稿：产品列表与目录导航（TOC）

> 节点 ID: `create_plan`  
> AI 工具: `cursor`  
> 模式: `headless`  
> 生成时间: 2026-08-16T15:55:00+08:00  
> 基于: `01-requirements.md`（已定稿）  
> 备注: 业务覆盖已与 `02-test-cases.md` 在 `review_plan_and_tests` 对齐（R1–R5）；技术选型 D1–D4 仍 `pending`，实现前按 suggestion 或另行确认。

---

```yaml clarification_checklist
all_resolved: false
pending_count: 4
items:
  - id: D1
    category: api_contract
    question: "产品 API JSON 字段命名采用全局 SNAKE_CASE（如 page_size）还是与需求文档字面 camelCase（如 pageSize）？"
    why_it_matters: "现有工程 application.yml 已配置 spring.jackson.property-naming-strategy: SNAKE_CASE（auth 响应为 access_token 等）。需求验收文案使用 pageSize/items 等 camelCase。命名策略直接决定 API/E2E 断言与前端取值字段。"
    suggestion: "跟随现有全局 SNAKE_CASE：响应字段为 items、total、page、page_size、categories；产品字段 id、name、category、price、description、status。查询参数仍用 page、pageSize（Spring 绑定字面名，与需求一致）。在实现报告与测试中显式记录该约定。"
    status: pending
    answer: ""
  - id: D2
    category: routing
    question: "产品列表页最终 URL path 定为 `/products` 还是 `/products.html`（或其它）？"
    why_it_matters: "影响静态资源放置、E2E 打开地址、实现报告与 README 启动说明；需求仅给示例 `/products`。"
    suggestion: "与 auth 登录页习惯对齐：静态文件 `src/main/resources/static/products.html`，并提供友好路径 `/products`（可通过同目录无后缀映射或简单 Controller/forward；优先最小改动，最终 path 写入 04-implementation.md）。E2E 与 workflow.e2e.base_url 拼接使用该最终 path。"
    status: pending
    answer: ""
  - id: D3
    category: security
    question: "如何让 `/api/products` 与 `/api/products/{id}` 匿名可访问（现有 JwtAuthFilter 对非白名单 `/api/**` 要求 Bearer）？"
    why_it_matters: "需求明确本期列表 API/页匿名、不耦合 auth 登录流程；若不放行，API 验收与 E2E 将全部 401。"
    suggestion: "最小改动：在现有 `JwtAuthFilter` 公开路径规则中增加对 `GET/HEAD /api/products` 与 `GET/HEAD /api/products/{id}` 的放行（前缀或精确匹配）。不引入 spring-boot-starter-security；不改动登录/受保护接口语义。catalog 业务代码仍不依赖 auth 领域模型。"
    status: pending
    answer: ""
  - id: D4
    category: api_contract
    question: "列表/详情响应中 `price` 的 JSON 类型是 number 还是格式化后的 string？"
    why_it_matters: "需求要求价格语义为元、展示保留 2 位小数；类型选择影响序列化、前端展示与断言写法。"
    suggestion: "领域用不可变金额值对象（如基于 BigDecimal，scale=2）；API 以 JSON number 输出（序列化后呈现两位小数语义），页面用 toFixed(2) 或等价展示。不在 domain 做展示格式化字符串。"
    status: pending
    answer: ""
```

```yaml plan_approval
status: approved
confirmed_at: "2026-08-16T16:12:00+08:00"
user_note: "已与 test-cases 业务覆盖对齐并确认"
```

---

## 0. 计划摘要

| 项 | 内容 |
|----|------|
| 需求类型 | 新需求（new） |
| 限界上下文 | `catalog`（独立于 `auth`） |
| 技术基线 | 复用 monorepo 根工程：Spring Boot 3.3.5 / Java 17 / Maven；同源进程默认端口 8080 |
| 存储 | 本地 JSON 文件（对齐 `auth` 的 `./data/users.json` 模式） |
| 交付物 | 四层代码 + 种子数据 + 静态列表页（TOC 过滤 + 页码分页）+ API 测试 + 浏览器 E2E |
| 兼容性 | 低；需小幅触及 `JwtAuthFilter` 公开路径（见 D3） |
| 依赖方向 | interfaces → application → domain ← infrastructure |

---

## 1. 架构与模块划分

### 1.1 总体架构

在现有单体 Spring Boot 应用（`com.zeiss.ecp.assistant.AuthApplication`）内**新增** `catalog` 限界上下文，与 `auth` 并列，不合并领域模型。

```text
浏览器 / API 客户端
        │
        ▼
┌───────────────────────────────────────────────┐
│ interfaces（REST DTO + 异常映射）              │
│  ProductController → CatalogApplicationService│
└───────────────────────┬───────────────────────┘
                        ▼
┌───────────────────────────────────────────────┐
│ application（用例编排 / 事务边界）             │
│  listProducts / getProduct                    │
└───────────────────────┬───────────────────────┘
                        ▼
┌───────────────────────────────────────────────┐
│ domain（Product 聚合、状态规则、Repository Port）│
└───────────────────────▲───────────────────────┘
                        │ 实现 Port
┌───────────────────────┴───────────────────────┐
│ infrastructure                                │
│  FileProductRepository、种子初始化、静态页托管   │
│  CatalogProperties / Config                   │
└───────────────────────────────────────────────┘
```

**依赖约束（必须）：**

- Controller **仅**依赖 ApplicationService；禁止直调 Repository / Entity。
- Application **仅**依赖 domain Port / 领域对象；禁止 import infrastructure 实现类。
- Domain **零** outward 依赖（无 Spring/JPA/Web/Jackson 注解依赖）。
- Infrastructure 实现 Repository；静态资源由 Spring Boot 默认 `classpath:/static/` 托管（属基础设施适配，不在 Listener 写业务）。

### 1.2 包结构（建议）

包根：`com.zeiss.ecp.assistant.catalog`（与现有 `..auth` 对齐；最终以实现为准写入 `04-implementation.md`）。

```text
src/main/java/com/zeiss/ecp/assistant/catalog/
├── interfaces/
│   ├── rest/              # ProductController、*Response、Error 复用或 catalog 专用
│   ├── assembler/         # DTO ↔ 应用层视图
│   └── exception/         # 可选：扩展 @RestControllerAdvice 映射 catalog 领域异常
├── application/
│   ├── service/           # CatalogApplicationService（或 ProductQueryApplicationService）
│   ├── command/           # 可选：ListProductsQuery
│   └── dto/               # ProductView、ProductListResult 等只读视图
├── domain/
│   ├── model/             # Product（聚合根）、ProductId、ProductStatus、Money/Price
│   ├── service/           # 可选：CatalogQueryDomainService（分类去重、可见性规则）
│   ├── repository/        # ProductRepository（Port）
│   └── exception/         # ProductNotFoundException、InvalidPaginationException 等
└── infrastructure/
    ├── persistence/       # FileProductRepository、ProductFileRecord、ProductDataInitializer
    └── config/            # CatalogProperties、CatalogInfrastructureConfig
```

静态页：`src/main/resources/static/products.html`（及可选少量 CSS/JS；最终 path 见 D2）。

### 1.3 与 auth 的边界

| 能力 | 本期策略 |
|------|----------|
| 登录/JWT | 不耦合；列表页与产品 API 匿名 |
| JwtAuthFilter | 仅增加产品 API 公开放行（D3）；不改登录契约 |
| 全局 Jackson SNAKE_CASE | 默认跟随（D1 待确认） |
| 端口 8080 | 共用 `server.port`；与 `workflow.e2e.base_url` 对齐 |

### 1.4 技术选型（建议，待 review 确认冲突项）

| 项 | 选型 | 依据 |
|----|------|------|
| 运行时 | 现有 Spring Boot Web + Validation | 仓库已落地 |
| 持久化 | 本地 JSON 文件 + 读写锁（对齐 FileUserRepository） | 需求 Q1；无外部 DB |
| Web UI | 最小静态 HTML + 原生 JS（fetch API） | 需求排除完整 SPA |
| API 测试 | MockMvc / `@SpringBootTest`（对齐 AuthApiIntegrationTest） | 可复用工程测试基建 |
| E2E | Playwright（MCP 或等价），基址 `http://localhost:8080` | workflow 配置 |
| 领域金额 | BigDecimal 值对象（scale=2） | 避免浮点误差；展示格式见 D4 |

---

## 2. 接口/API 清单

> 路径与语义对齐定稿需求；字段命名最终以 D1 决议为准。下表「要点」使用需求口径；若确认 SNAKE_CASE，则响应 JSON 键为 snake_case。

### 2.1 `GET /api/products`

| 项 | 约定 |
|----|------|
| 鉴权 | 匿名（D3） |
| Query | `category`（可选）；`page`（默认 1）；`pageSize`（默认 10，最大 50） |
| 成功 200 | `items`、`total`、`page`、`pageSize`（或 `page_size`）、`categories` |
| `items` 元素 | `id`、`name`、`category`、`price`、`description`（可选）、`status`（列表仅 active，通常恒为 active） |
| `categories` | 数据集中全部 **active** 产品的去重分类；**不因**当前 `category` 过滤收缩 |
| 默认过滤 | 仅 `status=active` |
| 稳定排序 | 列表须有**稳定序**（具体键由实现选定，如 id）；保证同条件下分页结果可复现 |
| 无匹配 | 不存在的 `category` 等：200 + `items: []` + `total: 0`（`categories` 仍为全量有效分类） |
| 页码越界 | `page` 合法但超出末页：200 + `items: []` + **`total` 仍为当前过滤下真实匹配总数**（与「无匹配 → total:0」区分；review R1） |
| 非法参数 | 400 + 明确错误信息（如 `page < 1`、`pageSize` 非正或 `> 50`、无法解析的数字） |

### 2.2 `GET /api/products/{id}`

| 项 | 约定 |
|----|------|
| 鉴权 | 匿名（D3） |
| 成功 200 | 单个产品对象（字段同列表项） |
| 不存在或 inactive | 404 |
| 非法 id 形态（若有校验） | 404 或 400（建议：找不到统一 404，避免泄露；实现阶段固定一种并写入报告） |

### 2.3 错误响应形态（建议对齐 auth）

复用或平行于 auth 的 `{ "error": "<code>", "message": "<明文>" }`（若全局 SNAKE_CASE 则字段名仍为 `error`/`message`）。catalog 领域异常由统一 `@RestControllerAdvice` 映射：

| 语义 | HTTP |
|------|------|
| 非法分页/参数 | 400 |
| 产品不可见/不存在 | 404 |

### 2.4 非 API 页面入口

| 方法 | 路径 | 要点 |
|------|------|------|
| GET | `/products`（或 D2 决议路径） | 最小产品列表页；同源；匿名 |

---

## 3. 数据模型与存储

### 3.1 领域模型（domain）

| 概念 | 职责 |
|------|------|
| `Product`（聚合根） | 持有 id、name、category、price、description、status；封装可见性（如 `isVisibleInCatalog()` → 仅 active） |
| `ProductId` | 唯一标识值对象 |
| `ProductStatus` | `ACTIVE` / `INACTIVE` 枚举 |
| `Money`/`Price` | 非负、scale=2 的金额不变式 |
| `ProductRepository` | Port：按条件查询 active 列表、按 id 加载、列举 active 分类来源所需数据等 |

**业务规则落点（避免贫血）：**

- 默认列表/TOC 分类来源只面向 active → 领域方法或领域服务显式表达，而非仅在 SQL/文件过滤注释中。
- 详情「inactive 视同不存在」→ 应用层调用领域可见性判断后抛 `ProductNotFoundException`（或等价）。

### 3.2 文件存储（infrastructure）

| 项 | 建议 |
|----|------|
| 文件路径配置 | `catalog.products.file`（默认 `./data/products.json`），可用环境变量覆盖 |
| PO | `ProductFileRecord`；`toDomain()` / `toPo()` 仅在 infrastructure |
| 并发 | 读多写少；`ReentrantReadWriteLock`（对齐用户文件仓储） |
| Jackson 落盘 | **独立 ObjectMapper**，避免 HTTP SNAKE_CASE 污染磁盘字段（对齐 FileUserRepository） |
| 种子数据 | `ProductDataInitializer`：文件不存在或空时写入预置数据 |

**种子数据最低要求（验收）：**

- ≥ 2 个分类；
- 每类 ≥ 2 条 **active**（合计 ≥ 4）；
- 建议 ≥ 1 条 **inactive**（验证默认列表与详情 404）；
- 预置足够条数以便分页第二页可测（或测试中临时调小 `pageSize`）。

### 3.3 配置项

| 配置 | 默认 | 说明 |
|------|------|------|
| `server.port` | `8080` | 已有；对齐 e2e.base_url |
| `catalog.products.file` | `./data/products.json` | 产品 JSON 路径 |
| `catalog.paging.default-page` | `1` | 可选显式配置 |
| `catalog.paging.default-page-size` | `10` | 与需求默认一致 |
| `catalog.paging.max-page-size` | `50` | 上限 |

写入 `application.yml` 示例默认值；本地覆盖可走 `application-local.yml`（已 gitignore）。

---

## 4. Web UI / 页面

### 4.1 页面职责（最小可用）

单页静态 HTML（原生 JS），打开后：

1. 请求 `GET /api/products?page=&pageSize=`（及可选 `category`）；
2. 渲染 **TOC**（「全部」+ `categories`）；
3. 渲染 **产品列表**（名称、分类、价格两位小数、描述摘要；截断长度不强制，有描述时摘要须可识别为同源内容）；
4. **页码分页**（至少上一页/下一页；参数与 API 一致；依赖稳定排序保证页间不重复）；
5. 空列表友好文案；加载中与错误态基本提示。

### 4.2 TOC 交互（需求已定：过滤模式）

- 点击分类 → 带 `category` 重新拉列表（`page` 重置为 1）；
- 「全部」→ 去掉 category；
- 当前 TOC 项视觉高亮或 `aria-current`；
- 可键盘 Tab 聚焦（E2E P1）；
- 仅 1 个有效分类时仍展示 TOC（或单条目）：**产品行为须满足**；本期 E2E 自动化不强制（P2 / 可手工冒烟；review R2）。

### 4.3 非目标

- 不做完整 SPA/设计系统；
- 不做滚动锚点 TOC；
- 不要求登录。

---

## 5. 各层用例与实现要点

### 5.1 应用层用例

| 用例方法 | 行为 |
|----------|------|
| `listProducts(category?, page, pageSize)` | 校验分页参数 → 经 Port 取数 → 仅 active → 可选分类过滤 → **稳定排序** → 分页切片 → 组装 `total`/`items`（越界页 `items` 空但 `total` 仍为真实匹配数）→ `categories` 来自全量 active 去重（独立于当前过滤） |
| `getProduct(id)` | 加载聚合 → 不可见/缺失则领域/应用异常 → 返回只读视图 |

事务：文件仓储场景下 `@Transactional` 非必须；若使用注解，边界仍放在 application，不放 domain。

### 5.2 接口层

- 薄 Controller：解析 query → 调 ApplicationService → Assembler 转 Response。
- Bean Validation 或显式校验非法分页 → 400。
- 禁止 Controller 注入 `ProductRepository`。

### 5.3 测试分层（实现阶段）

| 层 | 策略 | 门禁 |
|----|------|------|
| domain | 纯单元测试：状态可见性、金额不变式、分类规则（对应 TC-DOM-*） | P1 推荐，**不**阻塞验收 #11（review R5） |
| application | Mock Repository：分页、过滤、categories 不收缩、详情 404 | 随实现纳入 |
| interfaces / API | MockMvc：HTTP 状态码与业务契约（TC-API P0） | **P0 门禁** |
| E2E | 浏览器：打开列表页 → TOC → 过滤 → 列表/分页（TC-E2E P0） | **P0 门禁** |

详细业务场景与用例表见 `02-test-cases.md`（已与本计划业务口径对齐）。

---

## 6. 测试与验收映射

| 验收 # | 需求要点 | 计划覆盖落点 |
|--------|----------|--------------|
| 1 | 列表返回预置 active，`total` 与当页 `items` 正确 | API 集成测试 + 种子数据 |
| 2 | `category` 过滤仅该分类 | API 测试 |
| 3 | 分页第二页与第一页不重复 | API 测试（稳定序；必要时调 pageSize） |
| 4 | `categories` 为全部有效分类且不随过滤收缩 | API 测试 |
| 5 | 详情 active→200；无效/inactive→404 | API 测试 |
| 6 | 非法参数→400；无匹配空列表；越界页空 items + 真实 total | API 测试 |
| 7 | 打开列表页可见 TOC 与列表 | E2E |
| 8 | TOC 过滤后列表仅该分类；激活项可区分 | E2E |
| 9 | 列表字段与 API 一致（描述摘要可识别，不断言截断长度） | E2E |
| 10 | 分页行为正确 | E2E |
| 11 | 自动化通过 | **P0 门禁** = TC-API P0 + TC-E2E P0；TC-DOM 不阻塞 |
| 架构 | 四层/DIP/Controller 不直调仓储 | 实现自检清单 + code review |

---

## 7. 里程碑与实施顺序

> 任务拆分阶段须按 **domain → infrastructure → application → interfaces** 依赖顺序细化；下列为计划级里程碑。

| 里程碑 | 内容 | 依赖 |
|--------|------|------|
| M1 领域模型 | Product 聚合、状态/金额规则、Repository Port、领域异常、domain 单测 | 无 |
| M2 基础设施 | JSON 文件仓储、种子初始化、CatalogProperties、配置默认值 | M1 |
| M3 应用用例 | list/get 编排、分页与 categories 语义、application 单测（Mock Port） | M1 |
| M4 接口暴露 | ProductController、DTO/Assembler、异常映射、JwtAuthFilter 放行（D3） | M2+M3 |
| M5 静态列表页 | TOC 过滤 + 页码分页 + 空/加载/错误态 | M4 |
| M6 API 自动化 | MockMvc 覆盖验收 1–6 | M4 |
| M7 E2E 与文档 | Playwright 场景、README/启动说明、实现报告写入最终 path 与 D1–D4 决议 | M5+M6 |

**建议本地验证顺序：**

1. `mvn test`
2. `mvn spring-boot:run` → 访问列表页与 `/api/products`
3. 按 e2e 基址跑浏览器场景

---

## 8. 风险与待 review 决策项

### 8.1 风险

| 风险 | 影响 | 缓解 |
|------|------|------|
| JwtAuthFilter 未放行产品 API | 全部 API/E2E 401 | D3；M4 必做 |
| JSON 命名与需求字面不一致 | 测试断言/前端字段写错 | D1 在 review 定稿后统一 |
| 种子数据不足以测分页 | 验收 #3 不稳定 | 种子条数或测试专用 pageSize |
| 误把业务规则写进 Repository/Controller | 违反 DDD 规范 | 按层拆分与自检清单 |
| 改动 Filter 影响 auth | 回归登录/受保护 API | 保留现有公开路径；仅追加 products GET；跑 auth 既有测试 |

### 8.2 业务口径（已与 test-cases / review 对齐）

| ID | 结论 |
|----|------|
| R1 | 越界页：`items=[]`，`total` 仍为真实匹配总数 |
| R2 | 单分类 TOC：产品须支持；E2E 自动化本期不强制（P2） |
| R3 | 描述摘要可识别即可，不断言截断字符数 |
| R4 | 稳定排序；用例不断言具体排序键 |
| R5 | P0 门禁 = TC-API P0 + TC-E2E P0；TC-DOM 为 P1 |

### 8.3 待实现阶段确认的技术项（摘自 checklist，非本 review 业务范围）

- **D1** API JSON 命名：SNAKE_CASE vs camelCase  
- **D2** 列表页最终 path  
- **D3** 匿名 API 放行方式（建议扩展 JwtAuthFilter）  
- **D4** `price` JSON 类型  

上述项仍给出 **suggestion**；实现前确认或按 suggestion 落地并写入 `04-implementation.md`。业务覆盖经用户确认后，`plan_approval` 转为 approved。

### 8.4 明确不在本期

- 产品写操作/管理后台、购物车/下单、全文检索、登录鉴权、TOC 滚动定位、外部 DB、出站第三方 HTTP。

---

## 9. 与定制约束符合性

| 规范点 | 计划落地 |
|--------|----------|
| 四层包结构 | §1.2 |
| 依赖外→内 | §1.1 |
| Port 在 domain、实现在 infrastructure | §3.1–3.2 |
| Controller 仅调 ApplicationService | §5.2 |
| 核心规则在领域 | §3.1、§5.1 |
| 任务顺序 domain→infra→app→interfaces | §7 |
| 测试分层 | §5.3、§6 |

---

## 10. Workflow 状态（本节点）

| 字段 | 值 |
|------|-----|
| node | create_plan |
| status | completed |
| next_node | review_plan_and_tests |
| phase | planning |
| pending_count | 4 |
| all_resolved | false |
| plan_approval | pending |
| business_aligned_with_tests | true |
| updated_at | 2026-08-16T16:08:00+08:00 |

## Workflow 状态

| 字段 | 值 |
|------|-----|
| node | create_plan |
| status | completed |
| next_node | review_plan_and_tests |
| phase | plan |
| pending_count | 4 |
| all_resolved | false |
| note | 业务口径已与 test-cases 对齐；技术 D1–D4 仍 pending；approval 待用户确认 review 定稿 |
| updated_at | 2026-08-16T16:08:00+08:00 |
