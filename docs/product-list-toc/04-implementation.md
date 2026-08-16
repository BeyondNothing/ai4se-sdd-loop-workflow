# 实现报告：产品列表与目录导航（TOC）

> 节点 ID: `implement_code`  
> 生成时间: 2026-08-16T16:19:00+08:00  
> 工程根: 仓库根目录（`pom.xml`，包根 `com.zeiss.ecp.assistant.catalog`，与 `auth` 并列）

---

## 1. 已完成任务

| ID | 标题 | 状态 |
|----|------|------|
| TASK-01 | 领域层：Product 聚合、Port、可见性/金额规则与异常 | 完成 |
| TASK-02 | 基础设施：JSON 产品仓储、种子数据、Catalog 配置 | 完成 |
| TASK-03 | 基础设施：JwtAuthFilter 放行产品 API（匿名 GET/HEAD） | 完成 |
| TASK-04 | 应用层：listProducts / getProduct 用例编排 | 完成 |
| TASK-05 | 接口层：ProductController、DTO、Assembler、异常映射 | 完成 |
| TASK-06 | 最小静态 UI：产品列表页 TOC 过滤 + 页码分页 | 完成 |
| TASK-07 | API 自动化测试（TC-API P0 门禁） | 完成（`mvn test` 通过） |
| TASK-08 | 浏览器 E2E 场景说明 + README / 本报告 | 完成（浏览器 E2E 由 verify_tests / Playwright MCP 执行） |

---

## 2. 变更文件列表及说明

### 领域层（TASK-01）

| 路径 | 说明 |
|------|------|
| `.../catalog/domain/model/Product.java` | 聚合根；`isVisibleInCatalog()` 仅 ACTIVE |
| `.../catalog/domain/model/ProductId.java` | 标识值对象 |
| `.../catalog/domain/model/ProductStatus.java` | ACTIVE / INACTIVE；wire 值为小写 |
| `.../catalog/domain/model/Money.java` | BigDecimal scale=2、非负 |
| `.../catalog/domain/repository/ProductRepository.java` | 仓储 Port |
| `.../catalog/domain/service/CatalogQueryDomainService.java` | 可见过滤、分类去重、按 id 升序 |
| `.../catalog/domain/exception/ProductNotFoundException.java` | 映射 404 |
| `.../catalog/domain/exception/InvalidPaginationException.java` | 映射 400 |
| `src/test/.../catalog/domain/CatalogDomainRulesTest.java` | TC-DOM 支撑单测 |

### 基础设施层（TASK-02 / TASK-03 / 视图映射）

| 路径 | 说明 |
|------|------|
| `.../infrastructure/persistence/FileProductRepository.java` | JSON 文件仓储；独立 ObjectMapper；读写锁 |
| `.../infrastructure/persistence/ProductFileRecord.java` | 文件 PO |
| `.../infrastructure/persistence/ProductDataInitializer.java` | 空文件时种子：5 active + 1 inactive |
| `.../infrastructure/config/CatalogProperties.java` | `catalog.products.file` / paging 默认值 |
| `.../infrastructure/config/CatalogInfrastructureConfig.java` | Bean；`/products` → `forward:/products.html` |
| `.../auth/infrastructure/security/JwtAuthFilter.java` | 放行 GET/HEAD `/api/products` 与 `/api/products/**` |
| `src/main/resources/application.yml` | catalog 配置默认项 |

### 应用层（TASK-04）

| 路径 | 说明 |
|------|------|
| `.../application/service/CatalogApplicationService.java` | `listProducts` / `getProduct`；分页校验；categories 全量口径 |
| `.../application/dto/ProductView.java` / `ProductListResult.java` | 只读视图 |
| `src/test/.../catalog/application/CatalogApplicationServiceTest.java` | Mock Repository 单测 |

### 接口层（TASK-05）

| 路径 | 说明 |
|------|------|
| `.../interfaces/rest/ProductController.java` | `GET /api/products`、`GET /api/products/{id}` |
| `.../interfaces/rest/ProductResponse.java` / `ProductListResponse.java` | 响应 DTO（Jackson SNAKE_CASE → `page_size`） |
| `.../interfaces/assembler/ProductAssembler.java` | 应用视图 → 响应 |
| `.../auth/interfaces/exception/GlobalExceptionHandler.java` | 扩展 catalog 异常 → 400/404 |

### UI / 测试 / 文档（TASK-06–08）

| 路径 | 说明 |
|------|------|
| `src/main/resources/static/products.html` | 列表页：TOC 过滤、「全部」、页码翻页（默认 pageSize=2 便于 E2E） |
| `src/main/resources/static/css/products.css` | 列表页布局样式 |
| `src/test/.../catalog/interfaces/CatalogApiIntegrationTest.java` | TC-API-01～14（含 P0） |
| `src/test/resources/application.yml` | 测试用产品文件路径 |
| `README.md` | 启动、catalog 配置、API、限制 |
| `docs/product-list-toc/e2e-scenarios.md` | Playwright E2E 步骤与选择器 |

---

## 3. 关键设计决策（T1–T8）

| ID | 决议 | 落地 |
|----|------|------|
| T1 | 全局 Jackson SNAKE_CASE；查询参数字面 `page`/`pageSize` | 响应含 `page_size`；Controller `@RequestParam Integer pageSize` |
| T2 | 友好路径 `/products` | `CatalogInfrastructureConfig` forward → `/products.html` |
| T3 | JwtAuthFilter 放行产品 GET/HEAD | `isPublicProductApi`；不引入 spring-boot-starter-security |
| T4 | `price` 为 JSON number；领域 Money scale=2 | API number；页面 `toFixed(2)` |
| T6 | 列表按 `id` 字符串升序 | `CatalogQueryDomainService.sortByIdAscending` |
| T7 | 无效/缺失/inactive 详情统一 404 | `ProductNotFoundException` |
| T8 | 错误体 `{error,message}` | `bad_request` / `not_found` |

其它：

1. **TOC 采用过滤模式**（非滚动锚点）：点击分类带 `category` 重查并将 `page` 重置为 1。
2. **越界页**：`items=[]`，`total` 仍为当前过滤下真实匹配数。
3. **应用层不依赖 infrastructure**：分页默认值经 `@Value` 注入，避免 import `CatalogProperties`。
4. **列表页默认 pageSize=2**：种子 5 条 active，便于 E2E 翻页；API 默认仍为配置的 10。

---

## 4. Web / E2E 入口

基址：`http://localhost:8080`（`workflow.e2e.base_url`）。

| 入口 | 完整 URL | 说明 |
|------|----------|------|
| 产品列表页 | http://localhost:8080/products | 匿名；TOC + 分页 |
| 产品列表静态文件 | http://localhost:8080/products.html | 同源静态资源 |
| 产品列表 API | http://localhost:8080/api/products | 匿名 GET |
| 产品详情 API | http://localhost:8080/api/products/{id} | 匿名 GET；inactive/缺失 → 404 |
| 登录页（既有） | http://localhost:8080/login | 与 catalog 无耦合 |
| 受保护首页（既有） | http://localhost:8080/ | 需前端 token |

E2E 场景表：`docs/product-list-toc/e2e-scenarios.md`。

---

## 5. 架构自检

- [x] 四层包结构清晰（`catalog.domain` / `application` / `interfaces` / `infrastructure`）
- [x] `domain` 无 Spring/JPA/Web/Jackson 依赖
- [x] Repository Port 在 domain，实现在 infrastructure
- [x] Controller 仅依赖 ApplicationService
- [x] 可见性/金额规则在领域模型与领域服务中
- [x] 无出站第三方 HTTP；入站 Filter 放行在 infrastructure
- [x] 依赖方向外 → 内

---

## 6. 已知限制

- 产品只读；无管理后台写操作。
- 本地 JSON 文件存储；无外部数据库。
- 列表 API / 页匿名；不与 auth 登录流程耦合。
- TOC 不提供滚动锚点模式。
- 浏览器 E2E 由后续 `verify_tests` / Playwright MCP 执行；本节点已提供场景与选择器。

---

## 7. 本地验证

```bash
mvn test
mvn spring-boot:run
# 浏览器打开 http://localhost:8080/products
# curl http://localhost:8080/api/products
```

`mvn clean test` 已在本机通过（含既有 auth 集成测试与 catalog TC-API）。

## Workflow 状态

| 字段 | 值 |
|------|-----|
| node | implement_code |
| status | completed |
| next_node | verify_tests |
| phase | implement |
| pending_count | 0 |
| all_resolved | true |
| updated_at | 2026-08-16T16:19:28 |
