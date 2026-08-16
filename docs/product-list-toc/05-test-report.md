# 测试报告：产品列表与目录导航（TOC）

> 节点 ID: `verify_tests`  
> 执行时间: 2026-08-16T16:38:20+08:00  
> 工程根: `/Users/feiwang/Documents/interview/ai-workflow-verification`（`pom.xml`）  
> 依据: `02-test-cases.md`（approved）、`04-implementation.md`、DDD 四层规范

```yaml test_result
test_passed: true
p0_gate: passed
e2e_enabled: false
executed_at: "2026-08-16T16:38:20+08:00"
command: "mvn test"
summary: "Tests run: 39, Failures: 0, Errors: 0, Skipped: 0; BUILD SUCCESS"
```

## 测试结论

**`test_passed: true`**

- **P0 门禁（验收 #11）**：全部 `TC-API` P0 通过；全部 `TC-E2E` P0 因 `workflow.e2e.enabled=false` 标记 **skip**（不算失败）。
- **P1 推荐**：`TC-API-09/14`、`TC-DOM-*`、应用层单测均通过；E2E P1/P2 一并 skip。
- 说明：用例规格中领域规则编号为 `TC-DOM-*`，无独立 `TC-UNIT-*` 前缀；单元层以 `TC-DOM-*` + 应用层 Mockito 单测追溯。

---

## 1. 执行环境与命令

| 项 | 值 |
|----|-----|
| 业务工程根 | 仓库根（非 `dev-workflow/`） |
| JDK | 24.0.2（编译目标 Java 17 / Spring Boot 3.3.5） |
| 构建 | Maven Surefire |
| 命令 | `mvn test`（cwd = 仓库根） |
| 结果 | `Tests run: 39, Failures: 0, Errors: 0, Skipped: 0` / **BUILD SUCCESS** |
| E2E | `workflow.e2e.enabled: false` → 跳过 Playwright MCP |

测试框架：JUnit 5、Mockito、Spring Boot `@SpringBootTest` + MockMvc（沿用既有栈，未自建独立测试体系）。

---

## 2. 用例追溯总表

| 用例编号 | 优先级 | 门禁 | 测试方法 / 位置 | 结果 |
|----------|--------|------|-----------------|------|
| TC-API-01 | P0 | 是 | `CatalogApiIntegrationTest.tcApi01_defaultListReturnsActiveProducts` | **pass** |
| TC-API-02 | P0 | 是 | `...tcApi02_categoryFilter` | **pass** |
| TC-API-03 | P0 | 是 | `...tcApi03_paginationPagesDoNotOverlap` | **pass** |
| TC-API-04 | P0 | 是 | `...tcApi04_categoriesDoNotShrinkWithFilter` | **pass** |
| TC-API-05 | P0 | 是 | `...tcApi05_unknownCategoryEmptyList` | **pass** |
| TC-API-06 | P0 | 是 | `...tcApi06_outOfRangePageKeepsRealTotal` | **pass** |
| TC-API-07 | P0 | 是 | `...tcApi07_illegalPageReturns400` | **pass** |
| TC-API-08 | P0 | 是 | `...tcApi08_illegalPageSizeReturns400` | **pass** |
| TC-API-09 | P1 | 否 | `...tcApi09_pageSizeBoundaries` | **pass** |
| TC-API-10 | P0 | 是 | `...tcApi10_itemFieldsPresent` | **pass** |
| TC-API-11 | P0 | 是 | `...tcApi11_activeDetailReturns200` | **pass** |
| TC-API-12 | P0 | 是 | `...tcApi12_missingDetailReturns404` | **pass** |
| TC-API-13 | P0 | 是 | `...tcApi13_inactiveDetailReturns404` | **pass** |
| TC-API-14 | P1 | 否 | `...tcApi14_anonymousAccessAllowed` | **pass** |
| TC-DOM-01 | P1 | 否 | `CatalogDomainRulesTest.defaultVisibleScopeIsActiveOnly` | **pass** |
| TC-DOM-02 | P1 | 否 | `...categoriesExcludeInactiveOnlyCategories` | **pass** |
| TC-DOM-03 | P1 | 否 | `...inactiveOrMissingIsNotVisible`（应用层 `getProductRejectsInactiveAndMissing` 补充） | **pass** |
| TC-E2E-01 | P0 | 是* | — | **skip**（e2e.enabled=false） |
| TC-E2E-02 | P0 | 是* | — | **skip** |
| TC-E2E-03 | P0 | 是* | — | **skip** |
| TC-E2E-04 | P0 | 是* | — | **skip** |
| TC-E2E-05 | P0 | 是* | — | **skip** |
| TC-E2E-06 | P1 | 否 | — | **skip** |
| TC-E2E-07 | P1 | 否 | — | **skip** |
| TC-E2E-08 | P1 | 否 | — | **skip** |
| TC-E2E-08b | P2 | 否 | — | **skip** |
| TC-E2E-09 | P0 | 是* | — | **skip** |

\* E2E P0 在开关关闭时 skip，不计入失败，不阻塞本节点在 `e2e.enabled=false` 下的通过判定。

---

## 3. 单元测试（领域 / 应用）

### 3.1 领域规则 `CatalogDomainRulesTest`

| 方法 | 覆盖 | 结果 |
|------|------|------|
| `defaultVisibleScopeIsActiveOnly` | TC-DOM-01：仅 active 进入可见范围 | pass |
| `categoriesExcludeInactiveOnlyCategories` | TC-DOM-02：TOC 分类排除「仅 inactive」分类 | pass |
| `inactiveOrMissingIsNotVisible` | TC-DOM-03：inactive/缺失不可见 | pass |
| `moneyRejectsNegativeAmount` / `moneyRequiresScaleTwo` | 金额不变式（支撑 T4） | pass |

**类结果**：5 tests, 0 failures。

### 3.2 应用层 `CatalogApplicationServiceTest`（Mock Repository）

| 方法 | 覆盖要点 | 结果 |
|------|----------|------|
| `listProductsPaginatesAndKeepsFullCategories` | 分页切片；categories 不随过滤收缩 | pass |
| `outOfRangePageReturnsEmptyItemsWithRealTotal` | R1：越界页 `total` 真实 | pass |
| `unknownCategoryReturnsEmptyWithZeroTotal` | 无匹配 `total=0` 且 categories 仍全量 | pass |
| `invalidPaginationThrows` | 非法 page/pageSize → `InvalidPaginationException` | pass |
| `getProductRejectsInactiveAndMissing` | TC-DOM-03 用例语义在应用编排中的落地 | pass |

**类结果**：5 tests, 0 failures。  
**DDD**：应用层仅依赖 `ProductRepository` Port + `CatalogQueryDomainService`，无 infrastructure 具体类 import。

---

## 4. API / 集成测试

**类**：`src/test/java/com/zeiss/ecp/assistant/catalog/interfaces/CatalogApiIntegrationTest.java`  
**方式**：`@SpringBootTest` + `@AutoConfigureMockMvc`；`@BeforeEach` 用 `ProductDataInitializer.seedProducts()` 重置（5 active + 1 inactive）。  
**断言约定**：响应 snake_case（`page_size`）；查询参数字面 `page` / `pageSize` / `category`。

| 用例 | 关键断言摘要 | 结果 |
|------|--------------|------|
| TC-API-01 | 200；`total=5`；`page=1`；`page_size=10`；items 全 active；不含 `p-006` | pass |
| TC-API-02 | category=显微镜 → 仅该分类；`total=3`；不含影像系统 | pass |
| TC-API-03 | pageSize=2 两页 id 无交集 | pass |
| TC-API-04 | 过滤前后 `categories` 相等；集合为 {显微镜, 影像系统} | pass |
| TC-API-05 | 不存在分类 → items=[]；`total=0`；categories 仍 ≥2 | pass |
| TC-API-06 | page=999 → items=[]；`total=5`（真实总数） | pass |
| TC-API-07 | page=0/-1/abc → 400 + `error=bad_request` + message | pass |
| TC-API-08 | pageSize=0/-3/51 → 400 + `bad_request` | pass |
| TC-API-09 | pageSize=1/50 → 200；长度符合边界 | pass |
| TC-API-10 | 必填字段齐全；`price` 为 number 且两位小数语义 | pass |
| TC-API-11 | `/api/products/p-001` → 200 + active 对象 | pass |
| TC-API-12 | 不存在 id → 404 `not_found` | pass |
| TC-API-13 | inactive `p-006` → 404 `not_found` | pass |
| TC-API-14 | 无凭证列表/详情均为 200（非 401/403） | pass |

**类结果**：14 tests, 0 failures。既有 `AuthApiIntegrationTest`（10）仍全部通过，产品放行未破坏 auth 受保护路径语义。

---

## 5. E2E / 浏览器验收

| 配置 | 值 |
|------|-----|
| `workflow.e2e.enabled` | **false** |
| `workflow.e2e.base_url` | `http://localhost:8080` |

**处理**：全部 `TC-E2E-*` 标记 **skip**，未调用 Playwright MCP，无截图产出。  
场景与选择器仍见 `docs/product-list-toc/e2e-scenarios.md`（实现阶段已提供），待开关开启后于后续验证执行。

| 用例 | 结果 |
|------|------|
| TC-E2E-01～05、09（P0） | skip |
| TC-E2E-06～08（P1）、08b（P2） | skip |

---

## 6. 架构自检（对照 DDD 规范）

| 自检项 | 结论 |
|--------|------|
| 四层包结构 `catalog.domain` / `application` / `interfaces` / `infrastructure` | 通过 |
| `domain` 无 Spring/JPA/Servlet/Jackson outward 依赖 | 通过（grep 无违规 import） |
| Repository Port 在 domain，实现在 infrastructure | 通过 |
| Controller 仅依赖 ApplicationService（+ Assembler） | 通过 |
| 可见性 / 金额规则在领域层 | 通过（`Product.isVisibleInCatalog`、`Money`、`CatalogQueryDomainService`） |
| 出站外部 HTTP | 本期无 |
| 入站 Filter 放行在 infrastructure | 通过（`JwtAuthFilter`） |
| 测试在业务工程 `src/test`，未自建独立体系 | 通过 |

---

## 7. 问题与建议

1. **E2E 未跑**：当前 workflow 关闭浏览器验收；开启 `workflow.e2e.enabled` 后需补跑 TC-E2E P0（`/products` TOC/分页/匿名）方可完整覆盖验收标准 7–10、11 的浏览器半边。
2. **种子 inactive 分类**：API 种子中 inactive（`p-006`）挂在「影像系统」（同时有 active），故「仅 inactive 分类」由 TC-DOM-02 夹具覆盖，而非 API 种子直接断言——可接受，与 R5（TC-DOM 不进 P0）一致。
3. **列表页默认 pageSize=2**：仅 UI 侧便于翻页；API 默认仍为配置 10。E2E 开启时注意与 API 对照时使用相同 `pageSize`。

---

## 8. Workflow 状态

| 字段 | 值 |
|------|-----|
| node | verify_tests |
| status | completed |
| test_passed | true |
| next_node | —（本节点为产出终点） |
| phase | verify |
| updated_at | 2026-08-16T16:38:20+08:00 |

## Workflow 状态

| 字段 | 值 |
|------|-----|
| node | verify_tests |
| status | completed |
| next_node |  |
| phase | verify |
| pending_count | 0 |
| all_resolved | true |
| updated_at | 2026-08-16T16:38:46 |
